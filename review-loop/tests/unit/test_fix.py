"""Unit tests for the mutation window: FIX containment, candidate validation,
FIX_APPLIED recording, and the four per-round sealed boundaries.

The FIX implementer is never a real provider here: a candidate is a
disposable-copy edit sealed before/after plus a validated ``fix`` role
manifest. Containment is asserted at the argv level against a fabricated
``CodexHostPaths`` (no bwrap run).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from review_loop.artifacts import CanonicalStore, EvidenceArtifact, canonical_bytes
from review_loop.controller import RunState
from review_loop.evidence import EvidencePlan, Gate
from review_loop.execution import CodexHostPaths
from review_loop.fix import (
    FixController,
    FixError,
    ValidatedFix,
    build_fix_call,
    build_round_scopes,
    is_test_path,
)
from review_loop.prompts import RoleExpectation, validate_role_json
from review_loop.seals import GitPolicy, materialize_delta, seal_target

SEAL = "seal-anchor"


def _host(root: Path) -> CodexHostPaths:
    return CodexHostPaths(
        bwrap=Path("/usr/bin/bwrap"),
        node=Path("/usr/bin/node"),
        codex_package_root=root / "pkg",
        codex_entry=root / "pkg" / "bin" / "codex.js",
        auth_file=root / "codex-home" / "auth.json",
        resolv_conf=Path("/etc/resolv.conf"),
        nsswitch_conf=Path("/etc/nsswitch.conf"),
        ca_certificates=Path("/etc/ssl/certs/ca-certificates.crt"),
    )


def _fix_artifact(target_seal, changes, *, expected_ids, test_trace=(), external=False, note=None):
    payload = {
        "changes": [
            {
                "path": path, "description": "fix it", "ledger_ids": list(ledger_ids),
                "twin_search_pattern": "grep x", "twin_search_count": 0,
            }
            for path, ledger_ids in changes
        ],
        "test_trace": [{"test_path": tp, "spec_ids": list(sp)} for tp, sp in test_trace],
        "external_actions_attempted": external,
        "external_actions_note": note,
    }
    body = json.dumps({
        "request_id": "req-fix", "role_id": "fix", "target_seal": target_seal,
        "round_input_seal": None, "payload": payload,
    }).encode("utf-8")
    expectation = RoleExpectation(
        request_id="req-fix", role_id="fix", target_seal=target_seal,
        round_input_seal=None, expected_ids=tuple(expected_ids),
    )
    return validate_role_json("fix", body, expectation)


class FixContainmentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.host = _host(self.root)
        self.copy = self.root / "disposable"
        self.copy.mkdir()
        self.call_dir = self.root / "run" / "calls" / "fix-1"

    def _build(self):
        return build_fix_call(
            prompt="fix the bug", host=self.host, call_dir=self.call_dir, disposable_copy=self.copy,
        )

    def test_subject_is_bound_read_write_to_the_disposable_copy(self):
        argv, _, mapping = self._build()
        # /subject is a single WRITABLE bind of the disposable copy, never a
        # per-entry read-only bind of the sealed target.
        self.assertIn(["--bind", str(self.copy), "/subject"], _pairs(argv, "--bind", 3))
        ro_subject = [t for t in _pairs(argv, "--ro-bind", 3) if t[2].startswith("/subject")]
        self.assertEqual(ro_subject, [])
        self.assertEqual(mapping.target_rw, self.copy)

    def test_provider_channel_is_present_auth_and_network(self):
        argv, _, mapping = self._build()
        # FIX keeps the provider control channel (unlike the gate mapping).
        self.assertIn(["--ro-bind", str(self.host.auth_file), "/home/reviewer/.codex/auth.json"], _pairs(argv, "--ro-bind", 3))
        self.assertNotIn("--unshare-net", argv)
        self.assertTrue(mapping.network)
        self.assertEqual(mapping.credentials, (self.host.auth_file,))

    def test_sandbox_flag_permits_workspace_writes(self):
        argv, _, _ = self._build()
        i = argv.index("--sandbox")
        self.assertEqual(argv[i + 1], "workspace-write")

    def test_differs_from_the_no_cred_no_net_gate_mapping(self):
        # The gate mapping (evidence.build_gate_mapping) unshares net and mounts
        # no credentials; FIX does the opposite. This is the load-bearing
        # distinction the Task-5 carry-forward warned against conflating.
        argv, _, mapping = self._build()
        self.assertNotIn("--unshare-net", argv)
        self.assertNotEqual(mapping.credentials, ())


class FixCandidateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.copy = self.root / "copy"
        self.copy.mkdir()
        (self.copy / "calc.py").write_text("def d(x):\n    return x + 1\n")
        self.before = seal_target(self.copy, GitPolicy(enabled=False))
        self.fixctl = FixController(_stub_run_state(self.root), self.root / "work")
        self.request = self.fixctl.prepare(
            [{"id": "F1", "state": "OPEN"}], SEAL,
            EvidencePlan(gates=(Gate("tests", ("python3", "-c", "pass"), "applicable", "required", "r", "scout"),), evidence_gaps=()),
        )

    def _reseal_after_editing(self, path, text):
        (self.copy / path).parent.mkdir(parents=True, exist_ok=True)
        (self.copy / path).write_text(text)
        return seal_target(self.copy, GitPolicy(enabled=False))

    def test_happy_path_binds_the_changed_path_to_its_open_id(self):
        after = self._reseal_after_editing("calc.py", "def d(x):\n    return x - 1\n")
        manifest = _fix_artifact(SEAL, [("calc.py", ["F1"])], expected_ids=("F1",))
        validated = self.fixctl.validate_candidate(self.request, self.before, after, manifest)
        self.assertIsInstance(validated, ValidatedFix)
        self.assertEqual(validated.bound_ids, ("F1",))
        self.assertEqual(validated.changed_paths, ("calc.py",))

    def test_prepare_authorizes_the_evidence_plan_commands(self):
        self.assertEqual(self.request.open_ids, ("F1",))
        self.assertEqual(self.request.approved_gate_argvs, (("python3", "-c", "pass"),))

    def test_unauthorized_ledger_id_is_rejected(self):
        after = self._reseal_after_editing("calc.py", "def d(x):\n    return x - 1\n")
        manifest = _fix_artifact(SEAL, [("calc.py", ["F1", "F2"])], expected_ids=("F1", "F2"))
        with self.assertRaises(FixError):
            self.fixctl.validate_candidate(self.request, self.before, after, manifest)

    def test_undeclared_actual_change_is_rejected(self):
        # Two files actually change; the manifest declares only one.
        (self.copy / "extra.py").write_text("y = 2\n")
        after = self._reseal_after_editing("calc.py", "def d(x):\n    return x - 1\n")
        manifest = _fix_artifact(SEAL, [("calc.py", ["F1"])], expected_ids=("F1",))
        with self.assertRaises(FixError):
            self.fixctl.validate_candidate(self.request, self.before, after, manifest)

    def test_declared_but_absent_change_is_rejected(self):
        after = self._reseal_after_editing("calc.py", "def d(x):\n    return x - 1\n")
        manifest = _fix_artifact(SEAL, [("calc.py", ["F1"]), ("ghost.py", ["F1"])], expected_ids=("F1",))
        with self.assertRaises(FixError):
            self.fixctl.validate_candidate(self.request, self.before, after, manifest)

    def test_declared_external_action_is_rejected(self):
        after = self._reseal_after_editing("calc.py", "def d(x):\n    return x - 1\n")
        manifest = _fix_artifact(
            SEAL, [("calc.py", ["F1"])], expected_ids=("F1",), external=True, note="tried to curl a package",
        )
        with self.assertRaises(FixError):
            self.fixctl.validate_candidate(self.request, self.before, after, manifest)

    def test_changed_test_file_without_spec_trace_is_rejected(self):
        # Task-2 carry-forward (a): a changed TEST needs a non-empty spec trace.
        after = self._reseal_after_editing("tests/test_calc.py", "assert True\n")
        manifest = _fix_artifact(SEAL, [("tests/test_calc.py", ["F1"])], expected_ids=("F1",))
        with self.assertRaises(FixError):
            self.fixctl.validate_candidate(self.request, self.before, after, manifest)

    def test_changed_test_file_with_spec_trace_is_accepted(self):
        after = self._reseal_after_editing("tests/test_calc.py", "assert True\n")
        manifest = _fix_artifact(
            SEAL, [("tests/test_calc.py", ["F1"])], expected_ids=("F1",),
            test_trace=[("tests/test_calc.py", ["SPEC-1"])],
        )
        validated = self.fixctl.validate_candidate(self.request, self.before, after, manifest)
        self.assertEqual(validated.changed_paths, ("tests/test_calc.py",))


def _stub_run_state(root: Path) -> RunState:
    return RunState(run_root=root / "run", governing_seal=SEAL, snapshot={"processor_state": {}}, stage="TRIAGE")


def _open_ledger_run_state(root: Path, ids) -> RunState:
    run_root = root / "run"
    store = CanonicalStore(run_root)
    store.initialize(SEAL, {})
    initial_rows = [
        {
            "id": i, "source_ids": [f"raw-{i}"], "reported_severity": "Important",
            "current_severity": "Important", "factual": "CONFIRMED", "state": "OPEN",
            "proof_artifact_ids": [], "manifest_artifact_id": None, "target_seal": SEAL,
        }
        for i in ids
    ]
    decisions = [
        {"id": i, "state": "OPEN", "proof_artifact_ids": [], "manifest_artifact_id": None}
        for i in ids
    ]
    projection = {
        "target_seal": SEAL, "initial_rows": initial_rows, "decisions": decisions,
        "manifests": [], "adjudication": None,
    }
    evidence = (EvidenceArtifact("triage-1", "triage-result", 1, SEAL, canonical_bytes({"x": 1})),)
    updated = store.issue_transition(operation="apply_ledger_decisions", evidence=evidence, projection=projection)
    return RunState(run_root=run_root, governing_seal=SEAL, snapshot=updated, stage="TRIAGE")


class FixApplyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.copy = self.root / "copy"
        self.copy.mkdir()
        (self.copy / "calc.py").write_text("def d(x):\n    return x + 1\n")
        self.before = seal_target(self.copy, GitPolicy(enabled=False))
        (self.copy / "calc.py").write_text("def d(x):\n    return x - 1\n")
        self.after = seal_target(self.copy, GitPolicy(enabled=False))

    def test_apply_records_fix_applied_with_manifest_linkage(self):
        run_state = _open_ledger_run_state(self.root, ["F1"])
        fixctl = FixController(run_state, self.root / "work")
        request = fixctl.prepare([{"id": "F1", "state": "OPEN"}], SEAL, EvidencePlan((), ()))
        manifest = _fix_artifact(SEAL, [("calc.py", ["F1"])], expected_ids=("F1",))
        validated = fixctl.validate_candidate(request, self.before, self.after, manifest)
        transition = fixctl.apply(validated)

        rows = {r["id"]: r for r in transition.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]}
        self.assertEqual(rows["F1"]["state"], "FIX_APPLIED")
        self.assertEqual(rows["F1"]["manifest_artifact_id"], transition.manifest_ids["F1"])
        self.assertEqual(transition.applied_ids, ("F1",))
        self.assertEqual(transition.run_state.stage, "FIX")

    def test_apply_leaves_unbound_open_rows_open(self):
        run_state = _open_ledger_run_state(self.root, ["F1", "F2"])
        fixctl = FixController(run_state, self.root / "work")
        request = fixctl.prepare(
            [{"id": "F1", "state": "OPEN"}, {"id": "F2", "state": "OPEN"}], SEAL, EvidencePlan((), ()),
        )
        manifest = _fix_artifact(SEAL, [("calc.py", ["F1"])], expected_ids=("F1", "F2"))
        validated = fixctl.validate_candidate(request, self.before, self.after, manifest)
        transition = fixctl.apply(validated)
        rows = {r["id"]: r for r in transition.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]}
        self.assertEqual(rows["F1"]["state"], "FIX_APPLIED")
        self.assertEqual(rows["F2"]["state"], "OPEN")


class RoundScopesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.copy = self.root / "copy"
        self.copy.mkdir()
        (self.copy / "calc.py").write_text("a = 1\n")
        before = seal_target(self.copy, GitPolicy(enabled=False))
        (self.copy / "calc.py").write_text("a = 2\n")
        after = seal_target(self.copy, GitPolicy(enabled=False))
        self.delta = materialize_delta(before, after, self.root / "delta.json")
        self.manifest = {"changes": [{"path": "calc.py", "ledger_ids": ["F1"]}]}
        self.inventory = {"active_areas": [{"id": "area-x", "owning_file_ids": ["deep.py", "calc.py"]}]}
        self.round_state = {
            "prior_mapping_ids": ["m1"], "prior_coverage_refs": ["c1"],
            "roster": [{"role": "holistic"}, {"role": "adversarial"}, {"role": "specialist", "area_id": "area-x"}],
            "relevant_ledger_ids": ["F1"], "usable_report_ids": ["r1", "r2"],
            "pending_adjudication_ids": ["F1"], "authority_kinds": {"F1": "reviewer"},
        }

    def test_four_boundaries_have_distinct_seals(self):
        scopes = build_round_scopes(self.round_state, self.delta, self.manifest, self.inventory)
        seals = {scopes.inventory_refresh.seal, scopes.triage.seal, scopes.adjudication.seal}
        seals |= {r.seal for r in scopes.reviewers}
        self.assertEqual(len(seals), 3 + len(scopes.reviewers))

    def test_reviewer_seal_depends_on_the_refresh_seal(self):
        # Changing a refresh input (a prior mapping) must ripple into every
        # reviewer seal -- the reviewer boundary is built only after refresh.
        base = build_round_scopes(self.round_state, self.delta, self.manifest, self.inventory)
        altered = dict(self.round_state, prior_mapping_ids=["m1", "m2"])
        changed = build_round_scopes(altered, self.delta, self.manifest, self.inventory)
        self.assertNotEqual(base.inventory_refresh.seal, changed.inventory_refresh.seal)
        for b, c in zip(base.reviewers, changed.reviewers):
            self.assertNotEqual(b.seal, c.seal)

    def test_holistic_scope_is_exactly_changed_files(self):
        scopes = build_round_scopes(self.round_state, self.delta, self.manifest, self.inventory)
        holistic = next(r for r in scopes.reviewers if r.role == "holistic")
        self.assertEqual(holistic.target_files, ("calc.py",))

    def test_specialist_adds_exactly_its_owning_surface(self):
        scopes = build_round_scopes(self.round_state, self.delta, self.manifest, self.inventory)
        specialist = next(r for r in scopes.reviewers if r.role == "specialist")
        self.assertEqual(specialist.target_files, ("calc.py", "deep.py"))

    def test_extra_owning_file_changes_the_specialist_seal(self):
        base = build_round_scopes(self.round_state, self.delta, self.manifest, self.inventory)
        wider = {"active_areas": [{"id": "area-x", "owning_file_ids": ["deep.py", "calc.py", "extra.py"]}]}
        changed = build_round_scopes(self.round_state, self.delta, self.manifest, wider)
        base_spec = next(r for r in base.reviewers if r.role == "specialist")
        new_spec = next(r for r in changed.reviewers if r.role == "specialist")
        self.assertNotEqual(base_spec.seal, new_spec.seal)
        self.assertNotEqual(base_spec.target_files, new_spec.target_files)


def _pairs(argv, flag, width):
    out = []
    for i, a in enumerate(argv):
        if a == flag:
            out.append(argv[i : i + width])
    return out


if __name__ == "__main__":
    unittest.main()
