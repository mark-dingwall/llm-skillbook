"""Real-bwrap containment proof for evidence-gate execution.

Task 5's carry-forward (task-5-report.md, "CARRY-FORWARD"): the ordinary
Codex mapping always mounts auth.json and leaves network on; a gate/FIX
child MUST use a separate no-auth/no-network mapping and must not reuse
build_codex_call. These tests prove evidence.py's gate mapping is that
separate, stricter mapping -- empirically, against real bwrap, the same way
tests/integration/test_execution_containment.py proved the ordinary mapping.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from review_loop.evidence import (
    Gate,
    ManualMutation,
    MutationPlan,
    build_gate_mapping,
    execute_gate,
    make_disposable_copy,
    resolve_gate_host_paths,
    run_mutation_evidence,
)
from review_loop.seals import GitPolicy, seal_target

GATE_PROBE = Path(__file__).resolve().parent / "fixtures" / "gate_probe.py"
EVIDENCE_PROJECTS = Path(__file__).resolve().parent / "fixtures" / "evidence_projects"
DOC_TARGET = EVIDENCE_PROJECTS / "doc_target"
MUTATION_TARGET = EVIDENCE_PROJECTS / "mutation_target"

BWRAP_AVAILABLE = shutil.which("bwrap") is not None


def probe_gate(argv_tail, *, extra_inputs=(), timeout=30):
    """Run gate_probe.py under the real gate mapping; return its results dict."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    target = root / "target"
    target.mkdir()
    (target / "readonly.txt").write_bytes(b"hello")
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=target, check=True)

    seal = seal_target(target, GitPolicy(enabled=True, base="HEAD"))
    host = resolve_gate_host_paths()
    call_dir = root / "call"
    mapping = build_gate_mapping(host, seal, call_dir, inputs_ro=(GATE_PROBE, *extra_inputs))
    results_path = mapping.scratch_rw / "results.json"

    gate = Gate(
        id="tests",
        argv=("python3", "/inputs/0/gate_probe.py", *argv_tail, "--results", "/scratch/results.json"),
        applicability="applicable",
        classification="required",
        rationale="probe",
        provenance="scout",
    )
    result = execute_gate(gate, mapping, seal, timeout=timeout)
    data = json.loads(results_path.read_text()) if results_path.exists() else None
    return result, data, root, seal, mapping, tmp


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class GateContainmentTests(unittest.TestCase):
    def test_no_credential_or_secret_env_visible(self):
        import os

        os.environ["FAKE_PROVIDER_TOKEN"] = "should-never-be-visible"
        self.addCleanup(lambda: os.environ.pop("FAKE_PROVIDER_TOKEN", None))
        result, data, root, seal, mapping, tmp = probe_gate(["--env-dump"])
        try:
            self.assertEqual(result.status, "PASSED")
            env = data["env"]
            self.assertNotIn("FAKE_PROVIDER_TOKEN", env)
            # the gate mapping mounts no auth/credential file at all
            self.assertNotIn("CODEX_HOME", env)
        finally:
            tmp.cleanup()

    def test_network_is_unreachable(self):
        result, data, root, seal, mapping, tmp = probe_gate(["--connect", "127.0.0.1:80"])
        try:
            self.assertEqual(result.status, "PASSED")
            self.assertFalse(data["connects"]["127.0.0.1:80"]["ok"])
        finally:
            tmp.cleanup()

    def test_target_is_read_only_scratch_is_writable(self):
        result, data, root, seal, mapping, tmp = probe_gate([
            "--write", "/subject/readonly.txt",
            "--write", "/scratch/ok.txt",
        ])
        try:
            self.assertEqual(result.status, "PASSED")
            self.assertFalse(data["writes"]["/subject/readonly.txt"]["ok"])
            self.assertTrue(data["writes"]["/scratch/ok.txt"]["ok"])
        finally:
            tmp.cleanup()

    def test_cannot_read_an_unmounted_host_secret(self):
        with tempfile.NamedTemporaryFile(prefix="host-secret-", suffix=".txt", delete=False) as fh:
            fh.write(b"top secret")
            secret_path = fh.name
        try:
            result, data, root, seal, mapping, tmp = probe_gate(["--read", secret_path])
            try:
                self.assertEqual(result.status, "PASSED")
                self.assertFalse(data["reads"][secret_path]["ok"])
            finally:
                tmp.cleanup()
        finally:
            Path(secret_path).unlink(missing_ok=True)

    def test_argv_result_and_seal_are_recorded_exactly(self):
        result, data, root, seal, mapping, tmp = probe_gate(["--exit", "0"])
        try:
            self.assertEqual(result.gate_id, "tests")
            self.assertEqual(result.target_seal, seal.digest)
            self.assertEqual(
                result.argv,
                (
                    "python3", "/inputs/0/gate_probe.py", "--exit", "0",
                    "--results", "/scratch/results.json",
                ),
            )
            self.assertEqual(result.status, "PASSED")
            self.assertEqual(result.exit_status, 0)
        finally:
            tmp.cleanup()

    def test_gate_mapping_has_no_network_and_no_credentials(self):
        _, _, root, seal, mapping, tmp = probe_gate(["--exit", "0"])
        try:
            self.assertFalse(mapping.network)
            self.assertEqual(mapping.credentials, ())
        finally:
            tmp.cleanup()


def _document_seal(tmp_root: Path):
    """Copy ``doc_target`` (real repository fixture) into scratch and seal it.

    ``GitPolicy(enabled=False)`` -- these gates never depend on git identity;
    the point here is proving real gate execution against a document
    artifact, the same way the code-gate tests above prove it for code.
    """
    target = tmp_root / "doc"
    shutil.copytree(DOC_TARGET, target)
    return target, seal_target(target, GitPolicy(enabled=False))


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class DocumentGateContainmentTests(unittest.TestCase):
    """Document artifacts (design: "For technical documents, use existing
    mechanical checks such as link, schema ... validation, plus existing
    behavioral fixtures when the document is instructional") run through the
    exact same ``execute_gate`` containment as code gates -- no special-cased
    document path exists in evidence.py.
    """

    def _run(self, tmp, argv, classification="supporting"):
        target, seal = _document_seal(Path(tmp))
        host = resolve_gate_host_paths()
        mapping = build_gate_mapping(host, seal, Path(tmp) / "call")
        gate = Gate(
            id="doc-check", argv=argv, applicability="applicable",
            classification=classification, rationale="document gate", provenance="repository",
        )
        return execute_gate(gate, mapping, seal, host=host)

    def test_repository_link_check_passes_for_a_healthy_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(tmp, ("python3", "check_links.py", "guide.md"))
            self.assertEqual(result.status, "PASSED")

    def test_repository_link_check_fails_for_a_dangling_link_even_as_a_supporting_gate(self):
        # Reasserts design: "Any executed applicable gate that does not
        # produce its expected passing signal stops NOT CONVERGED" --
        # `supporting` never turns a real failure into an advisory one.
        # The kernel-level blocking rule itself is proven generically in
        # tests/unit/test_state_gates.py and
        # tests/integration/test_controller_clean.py; this proves the
        # document-flavored *execution* produces the FAILED status that
        # rule keys off.
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(tmp, ("python3", "check_links.py", "broken_guide.md"))
            self.assertEqual(result.status, "FAILED")
            self.assertIn("broken link", result.stderr_excerpt)

    def test_repository_schema_check_passes_for_a_well_formed_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(tmp, ("python3", "check_schema.py", "manifest.json"))
            self.assertEqual(result.status, "PASSED")

    def test_explicitly_selected_behavioral_skill_gate_passes_for_the_documented_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(tmp, ("python3", "-m", "pytest", "tests/test_behavior.py", "-q"))
            self.assertEqual(result.status, "PASSED")


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class MutationEvidenceContainmentTests(unittest.TestCase):
    """Real-bwrap proof for run_mutation_evidence: the sealed source fixture
    is never touched, every command runs contained (no credential/network,
    read-only target -- proven generically for the shared execute_gate path
    by GateContainmentTests above), and the disposable copy is discarded by
    the caller once evidence collection ends.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.source = self.root / "source"
        shutil.copytree(MUTATION_TARGET, self.source)
        self.source_before = (self.source / "calc.py").read_text()

    def _copy(self, name="copy") -> Path:
        seal = seal_target(self.source, GitPolicy(enabled=False))
        return make_disposable_copy(seal, self.root / name)

    def test_baseline_and_a_caught_mutant_run_for_real_under_bwrap(self):
        copy = self._copy()
        mutation = ManualMutation(
            id="flip-operator", target_path="calc.py",
            mutate=lambda text: text.replace("return a + b", "return a - b"),
            rationale="flips the add operator",
        )
        plan = MutationPlan(baseline_argv=("python3", "-m", "pytest", "test_calc.py", "-q"), manual_mutations=(mutation,))
        result = run_mutation_evidence(plan, copy)
        self.assertEqual(result.status, "EVALUATED")
        self.assertEqual(result.baseline.status, "PASSED")
        self.assertEqual(result.mutants[0].classification, "caught")
        # the disposable copy reverted the mutant; the sealed source was
        # never referenced by run_mutation_evidence at all
        self.assertEqual((copy / "calc.py").read_text(), self.source_before)
        self.assertEqual((self.source / "calc.py").read_text(), self.source_before)

    def test_a_surviving_mutant_runs_for_real_under_bwrap(self):
        copy = self._copy()
        mutation = ManualMutation(
            id="untested-branch", target_path="calc.py",
            mutate=lambda text: text.replace("return x * 2", "return x * 3"),
            rationale="unused_helper is not exercised by test_calc.py",
        )
        plan = MutationPlan(baseline_argv=("python3", "-m", "pytest", "test_calc.py", "-q"), manual_mutations=(mutation,))
        result = run_mutation_evidence(plan, copy)
        self.assertEqual(result.status, "EVALUATED")
        self.assertEqual(result.mutants[0].classification, "surviving")

    def test_broken_baseline_invalidates_mutation_evidence_under_bwrap(self):
        copy = self._copy()
        (copy / "test_calc.py").write_text("def test_add():\n    assert False\n")
        mutation = ManualMutation(id="flip", target_path="calc.py", mutate=lambda t: t.replace("+", "-"), rationale="flip")
        plan = MutationPlan(baseline_argv=("python3", "-m", "pytest", "test_calc.py", "-q"), manual_mutations=(mutation,))
        result = run_mutation_evidence(plan, copy)
        self.assertEqual(result.status, "BASELINE_FAILED")
        self.assertEqual(result.mutants, ())

    def test_unavailable_mutation_evidence_dispatches_nothing_under_bwrap(self):
        copy = self._copy()
        plan = MutationPlan(baseline_argv=None, unavailable_reason="no mutation tool configured")
        result = run_mutation_evidence(plan, copy)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.follow_up, "no mutation tool configured")


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class OrphanCleanupTests(unittest.TestCase):
    """A double-forked orphan spawned inside a gate cannot survive completion."""

    def test_orphan_heartbeat_stops_when_the_gate_process_tree_ends(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        target = root / "target"
        target.mkdir()
        (target / "a.txt").write_bytes(b"x")
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=target, check=True)
        subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=target, check=True)
        seal = seal_target(target, GitPolicy(enabled=True, base="HEAD"))
        host = resolve_gate_host_paths()
        call_dir = root / "call"
        mapping = build_gate_mapping(host, seal, call_dir, inputs_ro=(GATE_PROBE,))
        gate = Gate(
            id="tests",
            argv=(
                "python3", "/inputs/0/gate_probe.py",
                "--spawn-orphan", "/scratch/heartbeat",
                "--results", "/scratch/results.json",
            ),
            applicability="applicable", classification="required",
            rationale="orphan", provenance="scout",
        )
        result = execute_gate(gate, mapping, seal, timeout=10)
        self.addCleanup(tmp.cleanup)
        self.assertEqual(result.status, "PASSED")
        heartbeat = mapping.scratch_rw / "heartbeat"
        # give any surviving writer a moment to write, then confirm it stops
        self.assertTrue(heartbeat.exists())
        first = heartbeat.read_text()
        time.sleep(0.3)
        second = heartbeat.read_text()
        self.assertEqual(first, second, "orphan heartbeat kept advancing after the gate ended")


if __name__ == "__main__":
    unittest.main()
