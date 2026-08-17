"""End-to-end findings loop: a reviewer-found bug is triaged to an OPEN row,
repaired by the sole authorized FIX window (validated candidate delta on a
disposable copy), re-gated on the verified post-FIX copy under REAL Bubblewrap,
confirmed by a clean re-review, adjudicated FIX_VERIFIED with positive proof,
and CLOSED CONVERGED.

Every subagent (scout, inventory, holistic/adversarial reviewers, triager, FIX
implementer, adjudicator, final-readiness challenger) is a FAKE that builds a
strict envelope / review-record and runs it through the REAL validators; only
provider dispatch is faked. Gate execution -- including the post-FIX rerun on
the disposable copy (Task-7 -> Task-8 carry-forward (c): the first non-synthetic
rerun_gates round-trip) -- is real bwrap.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from review_loop.artifacts import EvidenceArtifact, canonical_bytes
from review_loop.controller import Controller
from review_loop.evidence import default_gate_dispatcher, resolve_gate_host_paths
from review_loop.prompts import (
    DispatchExpectation,
    ProcessCompletion,
    RoleExpectation,
    ValidatedRoleArtifact,
    validate_role_json,
)
from review_loop.profiles import InvocationIntent
from review_loop.report import generate_report
from review_loop.seals import GitPolicy, seal_target

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIX_TARGET = FIXTURES / "fix_target"
BWRAP_AVAILABLE = shutil.which("bwrap") is not None

FIXED_CALC = (
    '"""fixed"""\n\n\ndef discount(price, percent):\n'
    "    return price - price * percent / 100\n"
)


def _run_git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _init_git_target(root: Path) -> None:
    shutil.copytree(FIX_TARGET, root)
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "t@e.com")
    _run_git(root, "config", "user.name", "T")
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-q", "-m", "initial")


def _envelope(request_id, role_id, target_seal, round_input_seal, payload) -> bytes:
    return json.dumps({
        "request_id": request_id, "role_id": role_id, "target_seal": target_seal,
        "round_input_seal": round_input_seal, "payload": payload,
    }).encode("utf-8")


def _role_artifact(request_id, role_id, target_seal, round_input_seal, payload, *, expected_ids=(), extra=None):
    body = _envelope(request_id, role_id, target_seal, round_input_seal, payload)
    expectation = RoleExpectation(
        request_id=request_id, role_id=role_id, target_seal=target_seal,
        round_input_seal=round_input_seal, expected_ids=expected_ids, extra=extra or {},
    )
    return validate_role_json(role_id, body, expectation)


def _review_report_body(expectation: DispatchExpectation, findings=()) -> bytes:
    record = {
        "request_id": expectation.request_id, "role": expectation.role,
        "charter_id": expectation.charter_id, "target_seal": expectation.target_seal,
        "round_input_seal": expectation.round_input_seal,
        "scope_locator_ids": list(expectation.scope_locator_ids),
        "source_findings": list(findings),
    }
    text = "## Summary\n\n```review-record\n" + json.dumps(record) + "\n```\nREVIEW-STATUS: COMPLETE\n"
    return text.encode("utf-8")


AREA = {
    "id": "area-calc", "aliases": [], "consequence": "Important", "generalist_miss": False,
    "generalist_miss_evidence": None, "surfaces": ["calc.py"], "owning_file_ids": ["calc.py"],
    "charter": "discount() arithmetic.",
}
DISCOUNT_FINDING = {
    "id": "h1", "claim": "discount() adds the percentage instead of subtracting",
    "severity": "Important", "locator_ids": ["calc.py:9"],
}


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class FindingsLoopTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.target = root / "target"
        _init_git_target(self.target)
        self.run_root = root / "run"
        self.seal = seal_target(self.target, GitPolicy(enabled=True, base="HEAD"))
        self.controller = Controller(xdg_config_home=root / "xdg")
        self.host = resolve_gate_host_paths()
        self._plan = {}

    # --- fakes -------------------------------------------------------

    def _intent(self):
        return InvocationIntent(
            target=self.target, base="HEAD", head=None, exclusions=(), review_profile=None,
            max_time_seconds=None, no_confirm=False, ground_truth=(), run_root=self.run_root,
        )

    def _scout(self):
        def _s():
            payload = {
                "gates": [{
                    "id": "tests", "argv": ["python3", "-c", "import calc"],
                    "applicability": "applicable", "classification": "required",
                    "rationale": "baseline: calc imports cleanly",
                }],
                "evidence_gaps": [],
            }
            return _role_artifact("req-scout", "evidence", self.seal.digest, None, payload)
        return _s

    def _gate_dispatch_on(self, root: Path):
        seal = seal_target(root, GitPolicy(enabled=False))
        return default_gate_dispatcher(self.run_root / f"gates-{root.name}", seal, self.host)

    def _inventory_owner(self):
        def _o(exp: RoleExpectation):
            payload = {"areas": [AREA], "priority_order": ["area-calc"], "mappings": []}
            return _role_artifact(exp.request_id, "inventory-owner", exp.target_seal, exp.round_input_seal, payload)
        return _o

    def _inventory_challenger(self):
        def _c(exp: RoleExpectation):
            return _role_artifact(exp.request_id, "inventory-challenge", exp.target_seal, exp.round_input_seal, {"verdict": "UPHOLD"})
        return _c

    def _dispatch_role(self, findings_for_holistic):
        def _d(exp: DispatchExpectation):
            findings = findings_for_holistic if exp.role == "holistic" else ()
            body = _review_report_body(exp, findings)
            return body, ProcessCompletion(exp.request_id, 0, True)
        return _d

    def _triager(self):
        def _t(exp: RoleExpectation):
            raw = exp.extra["raw_findings"]
            findings = []
            n = 0
            for rid in exp.expected_ids:
                for fid, (claim, sev, locs) in raw.get(rid, {}).items():
                    n += 1
                    findings.append({
                        "canonical_id": f"LEDGER-{n}",
                        "sources": [{"report_id": rid, "finding_id": fid, "claim": claim, "severity": sev, "locators": list(locs)}],
                        "current_severity": sev, "factual": "CONFIRMED", "state": "OPEN",
                        "evidence_locators": list(locs),
                    })
            payload = {"report_ids": list(exp.expected_ids), "findings": findings}
            return _role_artifact(exp.request_id, "triage", exp.target_seal, exp.round_input_seal, payload,
                                  expected_ids=exp.expected_ids, extra=exp.extra)
        return _t

    def _fix_implementer(self):
        def _f(copy_root: Path, exp: RoleExpectation):
            (copy_root / "calc.py").write_text(FIXED_CALC)
            payload = {
                "changes": [{
                    "path": "calc.py", "description": "subtract instead of add",
                    "ledger_ids": list(exp.expected_ids), "twin_search_pattern": "price +", "twin_search_count": 0,
                }],
                "test_trace": [], "external_actions_attempted": False, "external_actions_note": None,
            }
            return _role_artifact(exp.request_id, "fix", exp.target_seal, exp.round_input_seal, payload,
                                  expected_ids=exp.expected_ids)
        return _f

    def _uphold_adjudicator(self):
        def _a(exp: RoleExpectation):
            payload = {"decisions": [{
                "id": ident, "decision": "UPHOLD", "evidence_locator": "calc.py:9",
                "fact_linkage": "post-fix re-review + passing gate confirm the fix", "authority_identity": None,
            } for ident in exp.expected_ids]}
            return _role_artifact(exp.request_id, "adjudication", exp.target_seal, exp.round_input_seal, payload,
                                  expected_ids=exp.expected_ids, extra=exp.extra)
        return _a

    def _final_challenger(self):
        def _c():
            return _role_artifact("req-final", "final-readiness", self.seal.digest, None, {"verdict": "UPHOLD"})
        return _c

    # --- the loop ----------------------------------------------------

    def _to_triage(self):
        run_state = self.controller.create_run(self._intent())
        stage0 = self.controller.run_stage0(
            run_state, scout=self._scout(), gate_dispatch=self._gate_dispatch_on(self.target),
            inventory_owner=self._inventory_owner(), inventory_challenger=self._inventory_challenger(),
            explicit_tier="low",
        )
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        self._plan = stage0
        round1 = self.controller.run_round1(stage0, dispatch_role=self._dispatch_role([DISCOUNT_FINDING]))
        self.assertEqual(round1.run_state.stage, "REVIEW")
        triage = self.controller.run_triage(round1, triager=self._triager())
        return triage, round1

    def test_open_finding_is_fixed_but_close_fails_closed_until_promotion(self):
        # Rebuild the evidence plan the controller discovered (run_fix needs it).
        from review_loop.evidence import discover_evidence
        plan = discover_evidence((), (), self._scout())

        triage, _ = self._to_triage()
        rows = triage.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
        self.assertEqual([r["state"] for r in rows], ["OPEN"])
        ledger_id = rows[0]["id"]

        # FIX: disposable-copy candidate, validated, FIX_APPLIED, post-FIX rerun.
        fix = self.controller.run_fix(
            triage, target_root=self.target, fix_implementer=self._fix_implementer(),
            evidence_plan=plan, post_fix_gate_dispatch=self._gate_dispatch_on,
        )
        applied = {r["id"]: r for r in fix.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]}
        self.assertEqual(applied[ledger_id]["state"], "FIX_APPLIED")
        # non-synthetic post-FIX gate rerun really executed on the changed copy
        self.assertTrue(fix.gate_rerun.review_may_start)
        self.assertEqual([g.status for g in fix.gate_rerun.gate_results], ["PASSED"])
        # the disposable copy holds the corrected code the gate re-ran against
        self.assertIn("price -", (fix.disposable_copy / "calc.py").read_text())
        manifest_id = fix.transition.manifest_ids[ledger_id]
        gov = fix.run_state.governing_seal

        # Positive proof: post-fix re-review (clean) + passing gate evidence.
        rereview = self._dispatch_role(())(DispatchExpectation(
            request_id="rev2", role="holistic", charter_id="holistic", target_seal=gov,
            round_input_seal=None, scope_locator_ids=("calc.py",),
        ))[0]
        proof = (
            EvidenceArtifact("proof-rereview", "post-fix-review", 1, gov, rereview),
            EvidenceArtifact("proof-gate", "post-fix-gate", 1, gov,
                             canonical_bytes({"gate": "tests", "status": "PASSED"})),
        )
        settlement = [{
            "id": ledger_id, "state": "FIX_VERIFIED", "manifest_artifact_id": manifest_id,
            "proof_artifact_ids": ["proof-rereview", "proof-gate"],
        }]
        adjudicated = self.controller.run_adjudication(
            fix.run_state, settlement, adjudicator=self._uphold_adjudicator(), proof_evidence=proof,
        )
        self.assertEqual(adjudicated.status, "UPHOLD")
        self.assertEqual(adjudicated.attempts, 1)
        verified = {r["id"]: r for r in adjudicated.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]}
        self.assertEqual(verified[ledger_id]["state"], "FIX_VERIFIED")
        self.assertEqual(verified[ledger_id]["manifest_artifact_id"], manifest_id)
        self.assertEqual(sorted(verified[ledger_id]["proof_artifact_ids"]), ["proof-gate", "proof-rereview"])

        challenge = self.controller.run_final_challenge(adjudicated.run_state, final_challenger=self._final_challenger())
        final = self.controller.close(challenge)
        # HONEST fail-closed: the fix was verified only against the disposable
        # copy; the authoritative target was never written, so CLOSE must NOT
        # emit a merge-ready CONVERGED for bytes that still contain the finding.
        terminal = final.snapshot["processor_state"]["compute_terminal"]
        self.assertEqual(terminal["terminal_verdict"], "NOT_CONVERGED")
        self.assertFalse(terminal["merge_ready"])
        self.assertIn("indeterminate", terminal["failed_conditions"])
        self.assertEqual(final.stage, "INDETERMINATE")
        self.assertIn("not repaired", final.reason)
        self.assertIn("Task 9", final.reason)
        report = generate_report(final)
        self.assertIn("Merge-ready: False", report)
        self.assertNotIn("Merge-ready: True", report)

    def test_undeclared_fix_change_fails_closed_before_fix_applied(self):
        from review_loop.evidence import discover_evidence
        from review_loop.fix import FixError
        plan = discover_evidence((), (), self._scout())
        triage, _ = self._to_triage()

        def rogue_implementer(copy_root: Path, exp: RoleExpectation):
            (copy_root / "calc.py").write_text(FIXED_CALC)
            (copy_root / "sneaky.py").write_text("BACKDOOR = 1\n")  # undeclared change
            payload = {
                "changes": [{
                    "path": "calc.py", "description": "fix", "ledger_ids": list(exp.expected_ids),
                    "twin_search_pattern": "x", "twin_search_count": 0,
                }],
                "test_trace": [], "external_actions_attempted": False, "external_actions_note": None,
            }
            return _role_artifact(exp.request_id, "fix", exp.target_seal, exp.round_input_seal, payload,
                                  expected_ids=exp.expected_ids)

        with self.assertRaises(FixError):
            self.controller.run_fix(
                triage, target_root=self.target, fix_implementer=rogue_implementer,
                evidence_plan=plan, post_fix_gate_dispatch=self._gate_dispatch_on,
            )
        # no FIX_APPLIED was recorded: the ledger row is still OPEN
        rows = triage.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
        self.assertEqual(rows[0]["state"], "OPEN")


SEAL = "seal-adj"


def _open_ledger(run_root: Path, ids):
    from review_loop.artifacts import CanonicalStore
    from review_loop.controller import RunState
    store = CanonicalStore(run_root)
    store.initialize(SEAL, {})
    initial_rows = [{
        "id": i, "source_ids": [f"raw-{i}"], "reported_severity": "Important",
        "current_severity": "Important", "factual": "PLAUSIBLE", "state": "OPEN",
        "proof_artifact_ids": [], "manifest_artifact_id": None, "target_seal": SEAL,
    } for i in ids]
    decisions = [{"id": i, "state": "OPEN", "proof_artifact_ids": [], "manifest_artifact_id": None} for i in ids]
    projection = {"target_seal": SEAL, "initial_rows": initial_rows, "decisions": decisions, "manifests": [], "adjudication": None}
    evidence = (EvidenceArtifact("tri", "triage-result", 1, SEAL, canonical_bytes({"x": 1})),)
    updated = store.issue_transition(operation="apply_ledger_decisions", evidence=evidence, projection=projection)
    return RunState(run_root=run_root, governing_seal=SEAL, snapshot=updated, stage="TRIAGE")


def _adj_artifact(exp, verdicts):
    payload = {"decisions": [{
        "id": ident, "decision": verdicts[ident], "evidence_locator": "x",
        "fact_linkage": "the finding is factually wrong" if verdicts[ident] == "UPHOLD" else None,
        "authority_identity": None,
    } for ident in exp.expected_ids]}
    return _role_artifact(exp.request_id, "adjudication", exp.target_seal, exp.round_input_seal, payload,
                          expected_ids=exp.expected_ids, extra=exp.extra)


class AdjudicationTwoCallTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_root = Path(self._tmp.name) / "run"
        self.controller = Controller()

    def _refute(self, ids, proof_ids=("p",)):
        proof = tuple(EvidenceArtifact(p, "settlement-proof", 1, SEAL, canonical_bytes({"p": p})) for p in proof_ids)
        settlements = [{"id": i, "state": "REFUTED", "proof_artifact_ids": list(proof_ids), "manifest_artifact_id": None} for i in ids]
        return settlements, proof

    def test_undecided_first_call_retries_then_upholds(self):
        run_state = _open_ledger(self.run_root, ["F1", "F2"])
        settlements, proof = self._refute(["F1", "F2"])
        calls = {"n": 0}

        def adjudicator(exp):
            calls["n"] += 1
            if calls["n"] == 1:
                return _adj_artifact(exp, {"F1": "UPHOLD", "F2": "UNDECIDED"})
            return _adj_artifact(exp, {"F1": "UPHOLD", "F2": "UPHOLD"})

        out = self.controller.run_adjudication(run_state, settlements, adjudicator=adjudicator, proof_evidence=proof)
        self.assertEqual(out.attempts, 2)
        self.assertEqual(out.status, "UPHOLD")
        rows = {r["id"]: r for r in out.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]}
        self.assertEqual({rows["F1"]["state"], rows["F2"]["state"]}, {"REFUTED"})

    def test_atomic_bounce_reverts_every_green_decision(self):
        run_state = _open_ledger(self.run_root, ["F1", "F2"])
        settlements, proof = self._refute(["F1", "F2"])

        def adjudicator(exp):
            # Only F2 is bounced, but the batch reverts atomically.
            return _adj_artifact(exp, {"F1": "UPHOLD", "F2": "BOUNCE"})

        out = self.controller.run_adjudication(run_state, settlements, adjudicator=adjudicator, proof_evidence=proof)
        self.assertEqual(out.status, "BOUNCE")
        rows = {r["id"]: r for r in out.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]}
        self.assertEqual({rows["F1"]["state"], rows["F2"]["state"]}, {"OPEN"})

    def test_persistent_undecided_leaves_rows_unsettled(self):
        run_state = _open_ledger(self.run_root, ["F1"])
        settlements, proof = self._refute(["F1"])

        def adjudicator(exp):
            return _adj_artifact(exp, {"F1": "UNDECIDED"})

        out = self.controller.run_adjudication(run_state, settlements, adjudicator=adjudicator, proof_evidence=proof)
        self.assertEqual(out.attempts, 2)
        self.assertFalse(out.settled)
        rows = out.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
        self.assertEqual(rows[0]["state"], "OPEN")

    def test_malformed_first_call_is_retried_once(self):
        from review_loop.prompts import RoleValidationError
        run_state = _open_ledger(self.run_root, ["F1"])
        settlements, proof = self._refute(["F1"])
        calls = {"n": 0}

        def adjudicator(exp):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RoleValidationError("garbled adjudication")
            return _adj_artifact(exp, {"F1": "UPHOLD"})

        out = self.controller.run_adjudication(run_state, settlements, adjudicator=adjudicator, proof_evidence=proof)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(out.status, "UPHOLD")

    def test_empty_settlement_makes_no_call(self):
        from review_loop.controller import ControllerError
        run_state = _open_ledger(self.run_root, ["F1"])

        def adjudicator(exp):
            self.fail("adjudicator must not be called for an empty settlement set")

        with self.assertRaises(ControllerError):
            self.controller.run_adjudication(run_state, [], adjudicator=adjudicator)

    def test_intentional_settlement_carries_file_authorized_user_acceptance(self):
        run_state = _open_ledger(self.run_root, ["F1"])
        proof = (EvidenceArtifact("ack", "user-acceptance", 1, SEAL, canonical_bytes({"ack": 1})),)
        settlements = [{"id": "F1", "state": "INTENTIONAL", "proof_artifact_ids": ["ack"], "manifest_artifact_id": None}]

        def adjudicator(exp):
            payload = {"decisions": [{
                "id": "F1", "decision": "UPHOLD", "evidence_locator": "calc.py:9",
                "fact_linkage": "deliberate, documented design choice",
                "authority_identity": "maintainer:alice",  # file-authorized user acceptance
            }]}
            return _role_artifact(exp.request_id, "adjudication", exp.target_seal, exp.round_input_seal, payload,
                                  expected_ids=exp.expected_ids, extra=exp.extra)

        out = self.controller.run_adjudication(
            run_state, settlements, adjudicator=adjudicator,
            authority_kinds={"F1": "file_authorized"}, proof_evidence=proof,
        )
        self.assertEqual(out.status, "UPHOLD")
        rows = out.run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
        self.assertEqual(rows[0]["state"], "INTENTIONAL")


class DeferredBoundaryTests(unittest.TestCase):
    """The Task-9 deferrals must fail closed LOUDLY -- never silently no-op --
    so a real multi-round run can't quietly skip them before Task 9 exists.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_root = Path(self._tmp.name) / "run"
        self.controller = Controller()

    def test_second_triage_reconcile_is_refused(self):
        from review_loop.controller import ControllerError, Round1Outcome
        run_state = _open_ledger(self.run_root, ["F1"])  # ledger already initialized
        round1 = Round1Outcome(run_state=run_state, roster=(), raw_reports=())

        def triager(exp):
            self.fail("round-N triage must be refused before any dispatch")

        with self.assertRaises(ControllerError):
            self.controller.run_triage(round1, triager=triager)

    def test_baseline_seal_advancement_is_refused(self):
        from review_loop.controller import ControllerError
        with self.assertRaises(ControllerError):
            self.controller.promote_post_fix_baseline()

    def test_mutation_result_persistence_is_refused(self):
        from review_loop.controller import ControllerError
        with self.assertRaises(ControllerError):
            self.controller.record_mutation_result()


if __name__ == "__main__":
    unittest.main()
