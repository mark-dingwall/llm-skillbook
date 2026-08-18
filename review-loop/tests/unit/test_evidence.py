import subprocess
import tempfile
import unittest
from pathlib import Path

from review_loop.evidence import (
    EvidenceDiscoveryIndeterminate,
    EvidenceError,
    ExecutionMapping,
    Gate,
    GateContainmentError,
    GateProposal,
    UnsafeGateCommand,
    build_gate_mapping,
    discover_evidence,
    execute_gate,
    make_disposable_copy,
    resolve_gate_host_paths,
    validate_gate_argv,
)
from review_loop.prompts import RoleValidationError, ValidatedRoleArtifact
from review_loop.controller import ControllerError, _dispatch_gates
from review_loop.seals import GitPolicy, SealEntry, TargetSeal, seal_target


def scout_artifact(gates, gaps=()):
    artifact = {"gates": list(gates), "evidence_gaps": list(gaps)}
    return ValidatedRoleArtifact(role_id="evidence", body=b"{}", artifact=artifact, projection={})


def scout_gate(gate_id, argv=("pytest", "-q"), applicability="applicable", classification="supporting", rationale="because"):
    return {
        "id": gate_id,
        "argv": list(argv),
        "applicability": applicability,
        "classification": classification,
        "rationale": rationale,
    }


class ValidateGateArgvTests(unittest.TestCase):
    def test_accepts_a_safe_listed_command(self):
        validate_gate_argv(["pytest", "-q"])  # does not raise

    def test_rejects_a_shell_interpreter(self):
        with self.assertRaises(UnsafeGateCommand):
            validate_gate_argv(["bash", "-c", "echo hi"])

    def test_rejects_an_unlisted_command(self):
        with self.assertRaises(UnsafeGateCommand):
            validate_gate_argv(["curl", "http://example.com"])

    def test_rejects_control_characters_in_a_listed_command(self):
        with self.assertRaises(UnsafeGateCommand):
            validate_gate_argv(["pytest", "-k", "foo; rm -rf /"])

    def test_rejects_command_substitution(self):
        with self.assertRaises(UnsafeGateCommand):
            validate_gate_argv(["python3", "-c", "print($(whoami))"])

    def test_rejects_empty_argv(self):
        with self.assertRaises(UnsafeGateCommand):
            validate_gate_argv([])


class DiscoverEvidenceTests(unittest.TestCase):
    def test_scout_only_produces_derived_classification(self):
        scout = lambda: scout_artifact([scout_gate("tests", classification="required")])
        plan = discover_evidence([], [], scout)
        self.assertEqual(len(plan.gates), 1)
        gate = plan.gates[0]
        self.assertEqual(gate.id, "tests")
        self.assertEqual(gate.classification, "required")
        self.assertEqual(gate.provenance, "scout")

    def test_non_required_gate_is_always_supporting(self):
        scout = lambda: scout_artifact([scout_gate("lint")])
        plan = discover_evidence([], [], scout)
        self.assertEqual(plan.gates[0].classification, "supporting")

    def test_valid_empty_discovery_is_not_an_error(self):
        scout = lambda: scout_artifact([], gaps=["no build metadata found"])
        plan = discover_evidence([], [], scout)
        self.assertEqual(plan.gates, ())
        self.assertEqual(plan.evidence_gaps, ("no build metadata found",))

    def test_repository_overrides_scout_for_the_same_id(self):
        scout = lambda: scout_artifact([scout_gate("tests", argv=("pytest",))])
        repo = [GateProposal(id="tests", argv=("make", "test"), applicability="applicable", rationale="ci config")]
        plan = discover_evidence([], repo, scout)
        self.assertEqual(plan.gates[0].argv, ("make", "test"))
        self.assertEqual(plan.gates[0].provenance, "repository")

    def test_operator_overrides_repository_and_scout(self):
        scout = lambda: scout_artifact([scout_gate("tests", argv=("pytest",))])
        repo = [GateProposal(id="tests", argv=("make", "test"), applicability="applicable", rationale="ci config")]
        op = [GateProposal(id="tests", argv=("pytest", "-x"), applicability="applicable", rationale="operator said so")]
        plan = discover_evidence(op, repo, scout)
        self.assertEqual(plan.gates[0].argv, ("pytest", "-x"))
        self.assertEqual(plan.gates[0].provenance, "operator")

    def test_repository_can_add_a_gate_the_scout_never_proposed(self):
        scout = lambda: scout_artifact([])
        repo = [GateProposal(id="lint", argv=("ruff", "check"), applicability="applicable", rationale="ci config")]
        plan = discover_evidence([], repo, scout)
        ids = {g.id for g in plan.gates}
        self.assertEqual(ids, {"lint"})

    def test_malformed_scout_output_is_retried_once(self):
        calls = []

        def scout():
            calls.append(1)
            if len(calls) == 1:
                raise RoleValidationError("bad json")
            return scout_artifact([scout_gate("tests")])

        plan = discover_evidence([], [], scout)
        self.assertEqual(len(calls), 2)
        self.assertEqual(plan.gates[0].id, "tests")

    def test_scout_malformed_twice_makes_stage_indeterminate(self):
        def scout():
            raise RoleValidationError("bad json")

        with self.assertRaises(EvidenceDiscoveryIndeterminate):
            discover_evidence([], [], scout)

    def test_operator_proposal_with_unsafe_argv_is_rejected(self):
        op = [GateProposal(id="tests", argv=("bash", "-c", "pytest"), applicability="applicable", rationale="x")]
        scout = lambda: scout_artifact([])
        with self.assertRaises(EvidenceError):
            discover_evidence(op, [], scout)


class DiscoverEvidenceDocumentGateTests(unittest.TestCase):
    """A document artifact uses the same discovery machinery as code: no
    special-cased gate shape exists (design: "For technical documents, use
    existing mechanical checks such as link, schema ... validation, plus
    existing behavioral fixtures when the document is instructional. Do not
    invent a nominal test merely to claim coverage")."""

    def test_repository_mechanical_document_checks_are_supporting_by_default(self):
        repo = [
            GateProposal(id="doc-links", argv=("python3", "check_links.py", "guide.md"), applicability="applicable", rationale="repository link checker"),
            GateProposal(id="doc-schema", argv=("python3", "check_schema.py", "manifest.json"), applicability="applicable", rationale="repository schema checker"),
        ]
        plan = discover_evidence([], repo, lambda: scout_artifact([]))
        by_id = {g.id: g for g in plan.gates}
        self.assertEqual(by_id["doc-links"].classification, "supporting")
        self.assertEqual(by_id["doc-schema"].classification, "supporting")
        self.assertEqual(by_id["doc-links"].provenance, "repository")

    def test_explicitly_selected_behavioral_skill_gate_is_not_invented_by_the_scout(self):
        # The scout proposes nothing; the repository explicitly names the
        # behavioral fixture because this document controls agent behavior.
        repo = [GateProposal(
            id="doc-behavior", argv=("python3", "-m", "pytest", "tests/test_behavior.py", "-q"),
            applicability="applicable", rationale="explicit RED/GREEN behavioral fixture for an instructional doc",
        )]
        plan = discover_evidence([], repo, lambda: scout_artifact([]))
        self.assertEqual(len(plan.gates), 1)
        self.assertEqual(plan.gates[0].provenance, "repository")
        self.assertEqual(plan.gates[0].classification, "supporting")

    def test_document_target_with_no_mechanical_checks_is_a_disclosed_gap_not_invented_machinery(self):
        scout = lambda: scout_artifact([], gaps=["no mechanical document checks configured for this target"])
        plan = discover_evidence([], [], scout)
        self.assertEqual(plan.gates, ())
        self.assertEqual(plan.evidence_gaps, ("no mechanical document checks configured for this target",))


def fake_seal(root="/tmp/does-not-matter"):
    return TargetSeal(
        schema_version=1,
        root=root,
        tree_digest="tree",
        entries=(SealEntry("a.txt", "file", 0o644, "digest"),),
        git_dir_outside_target=True,
        git_base_commit="base",
        git_head_commit=None,
        git_index_digest="index",
        digest="seal-digest",
    )


class ExecuteGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.mapping = ExecutionMapping(
            target_ro=(),
            inputs_ro=(),
            scratch_rw=root / "scratch",
            diagnostics_rw=root / "diagnostics",
            network=False,
            credentials=(),
        )
        (root / "scratch").mkdir()
        (root / "diagnostics").mkdir()
        self.gate = Gate(
            id="tests", argv=("pytest", "-q"), applicability="applicable",
            classification="required", rationale="baseline", provenance="scout",
        )
        self.seal = fake_seal()

    def test_controller_rejects_a_result_for_a_different_gate(self):
        plan = type("Plan", (), {"gates": (self.gate,)})()
        wrong = execute_gate(
            Gate(
                id="other", argv=("pytest", "other"), applicability="applicable",
                classification="supporting", rationale="other", provenance="operator",
            ),
            self.mapping,
            self.seal,
            run=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, stdout="", stderr=""),
        )
        with self.assertRaises(ControllerError):
            _dispatch_gates(plan, self.seal.digest, lambda _gate: wrong, lambda: "artifact")

    def test_zero_exit_is_passed(self):
        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout="ok\n", stderr="")

        result = execute_gate(self.gate, self.mapping, self.seal, run=fake_run)
        self.assertEqual(result.status, "PASSED")
        self.assertEqual(result.exit_status, 0)
        self.assertEqual(result.argv, ("pytest", "-q"))
        self.assertEqual(result.target_seal, "seal-digest")
        self.assertEqual(result.classification, "required")

    def test_nonzero_exit_is_failed(self):
        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

        result = execute_gate(self.gate, self.mapping, self.seal, run=fake_run)
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.exit_status, 1)
        self.assertIn("boom", result.stderr_excerpt)

    def test_timeout_is_failed_with_no_exit_status(self):
        def fake_run(argv, **kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=1, output="partial", stderr="")

        result = execute_gate(self.gate, self.mapping, self.seal, run=fake_run)
        self.assertEqual(result.status, "FAILED")
        self.assertIsNone(result.exit_status)
        self.assertIn("timed out", result.stderr_excerpt)

    def test_network_mapping_is_rejected_before_dispatch(self):
        bad_mapping = ExecutionMapping(
            target_ro=(), inputs_ro=(), scratch_rw=self.mapping.scratch_rw,
            diagnostics_rw=self.mapping.diagnostics_rw, network=True, credentials=(),
        )
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)

        with self.assertRaises(GateContainmentError):
            execute_gate(self.gate, bad_mapping, self.seal, run=fake_run)
        self.assertEqual(calls, [])

    def test_credentialed_mapping_is_rejected_before_dispatch(self):
        bad_mapping = ExecutionMapping(
            target_ro=(), inputs_ro=(), scratch_rw=self.mapping.scratch_rw,
            diagnostics_rw=self.mapping.diagnostics_rw, network=False,
            credentials=(Path("/some/auth.json"),),
        )

        def fake_run(argv, **kwargs):
            self.fail("must not dispatch a credentialed gate mapping")

        with self.assertRaises(GateContainmentError):
            execute_gate(self.gate, bad_mapping, self.seal, run=fake_run)

    def test_unsafe_gate_is_rejected_before_dispatch(self):
        unsafe = Gate(
            id="tests", argv=("bash", "-c", "pytest"), applicability="applicable",
            classification="required", rationale="baseline", provenance="scout",
        )

        def fake_run(argv, **kwargs):
            self.fail("must not dispatch an unsafe gate command")

        with self.assertRaises(UnsafeGateCommand):
            execute_gate(unsafe, self.mapping, self.seal, run=fake_run)

    def test_build_gate_mapping_creates_scratch_and_diagnostics(self):
        root = Path(self._tmp.name) / "call"
        host = type("Host", (), {"bwrap": Path("/usr/bin/bwrap"), "usr": Path("/usr")})()
        mapping = build_gate_mapping(host, self.seal, root)
        self.assertTrue(mapping.scratch_rw.is_dir())
        self.assertTrue(mapping.diagnostics_rw.is_dir())
        self.assertFalse(mapping.network)
        self.assertEqual(mapping.credentials, ())


class ResolveGateHostPathsTests(unittest.TestCase):
    def test_raises_when_bwrap_is_absent(self):
        import unittest.mock as mock

        with mock.patch("review_loop.evidence.shutil.which", return_value=None):
            with self.assertRaises(GateContainmentError):
                resolve_gate_host_paths()


class DisposableCopyTests(unittest.TestCase):
    def test_preserves_directory_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            restricted = source / "restricted"
            restricted.mkdir(mode=0o700)
            (restricted / "data.txt").write_text("sealed\n")
            seal = seal_target(source, GitPolicy(enabled=False))

            dest = make_disposable_copy(seal, root / "copy")

            self.assertEqual((dest / "restricted").stat().st_mode & 0o7777, 0o700)
            self.assertEqual(seal_target(dest, GitPolicy(enabled=False)).digest, seal.digest)


if __name__ == "__main__":
    unittest.main()
