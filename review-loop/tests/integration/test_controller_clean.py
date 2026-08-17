"""The first ordinary CLEAN end-to-end tracer: PREFLIGHT -> STAGE0 -> REVIEW
-> TRIAGE -> CLOSE.

Reviewer subagents (evidence scout, inventory owner/challenger, holistic,
adversarial, triager, final-readiness challenger) are FAKES: small callables
that build a strict-JSON envelope or review-report Markdown body matching
the exact controller-issued expectation, then run it through the REAL
`prompts.validate_role_json` / `prompts.validate_review_report` validators
-- only the "dispatch a real provider" step is faked, not the validation or
state-transition wiring. Gate execution is real: the one safe required
baseline command runs through `evidence.execute_gate` under real Bubblewrap.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from review_loop.controller import ConfirmationExpired, Controller
from review_loop.evidence import (
    GateProposal,
    build_gate_mapping,
    execute_gate,
    resolve_gate_host_paths,
)
from review_loop.prompts import (
    DispatchExpectation,
    ProcessCompletion,
    RoleExpectation,
    RoleValidationError,
    ValidatedRoleArtifact,
    validate_role_json,
)
from review_loop.profiles import InvocationIntent
from review_loop.report import generate_report
from review_loop.seals import GitPolicy, seal_target

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CLEAN_TARGET = FIXTURES / "clean_target"
EVIDENCE_PROJECTS = FIXTURES / "evidence_projects"

BWRAP_AVAILABLE = shutil.which("bwrap") is not None


def _run_git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _init_git_target(root: Path) -> None:
    shutil.copytree(CLEAN_TARGET, root)
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "test@example.com")
    _run_git(root, "config", "user.name", "Test")
    _run_git(root, "add", "-A")
    _run_git(root, "commit", "-q", "-m", "initial")


def _envelope(request_id, role_id, target_seal, round_input_seal, payload) -> bytes:
    return json.dumps({
        "request_id": request_id, "role_id": role_id, "target_seal": target_seal,
        "round_input_seal": round_input_seal, "payload": payload,
    }).encode("utf-8")


def _role_artifact(request_id, role_id, target_seal, round_input_seal, payload, *, expected_ids=(), extra=None) -> ValidatedRoleArtifact:
    body = _envelope(request_id, role_id, target_seal, round_input_seal, payload)
    expectation = RoleExpectation(
        request_id=request_id, role_id=role_id, target_seal=target_seal,
        round_input_seal=round_input_seal, expected_ids=expected_ids, extra=extra or {},
    )
    return validate_role_json(role_id, body, expectation)


def _review_report_body(expectation: DispatchExpectation, findings=()) -> bytes:
    record = {
        "request_id": expectation.request_id,
        "role": expectation.role,
        "charter_id": expectation.charter_id,
        "target_seal": expectation.target_seal,
        "round_input_seal": expectation.round_input_seal,
        "scope_locator_ids": list(expectation.scope_locator_ids),
        "source_findings": list(findings),
    }
    text = (
        "## Summary\nNothing to report.\n\n"
        "```review-record\n" + json.dumps(record) + "\n```\n"
        "REVIEW-STATUS: COMPLETE\n"
    )
    return text.encode("utf-8")


ONE_MINOR_AREA = {
    "id": "area-greet",
    "aliases": [],
    "consequence": "Minor",
    "generalist_miss": True,
    "generalist_miss_evidence": "greet() has no input validation, worth a specialist look someday.",
    "surfaces": ["greet.py"],
    "owning_file_ids": ["greet.py"],
    "charter": "Check greet() formatting edge cases.",
}


class CleanTracerFixture:
    """Builds a real git target + a fresh run, and every fake role callable."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.target = root / "target"
        _init_git_target(self.target)
        self.run_root = root / "run"
        self.xdg = root / "xdg"
        self.seal = seal_target(self.target, GitPolicy(enabled=True, base="HEAD"))
        self.controller = Controller(xdg_config_home=self.xdg)
        self.events: list[str] = []

    def intent(self, **overrides):
        base = dict(
            target=self.target, base="HEAD", head=None, exclusions=(),
            review_profile=None, max_time_seconds=None, no_confirm=False,
            ground_truth=(), run_root=self.run_root,
        )
        base.update(overrides)
        return InvocationIntent(**base)

    # --- fakes -------------------------------------------------------

    def scout(self, *, malformed_first: bool = False):
        state = {"called": False}

        def _scout() -> ValidatedRoleArtifact:
            self.events.append("scout")
            if malformed_first and not state["called"]:
                state["called"] = True
                raise RoleValidationError("malformed scout output")
            payload = {
                "gates": [{
                    "id": "tests", "argv": ["python3", "-c", "print('baseline gate ok')"],
                    "applicability": "applicable", "classification": "required",
                    "rationale": "baseline: the target must at least import cleanly",
                }],
                "evidence_gaps": [],
            }
            return _role_artifact("req-scout", "evidence", self.seal.digest, None, payload)

        return _scout

    def gate_dispatch(self):
        host = resolve_gate_host_paths()

        def _dispatch(gate):
            self.events.append(f"gate:{gate.id}")
            call_dir = self.run_root / "calls" / f"gate-{gate.id}"
            mapping = build_gate_mapping(host, self.seal, call_dir)
            return execute_gate(gate, mapping, self.seal, host=host)

        return _dispatch

    def inventory_owner(self):
        def _owner(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("inventory-owner")
            payload = {"areas": [ONE_MINOR_AREA], "priority_order": ["area-greet"], "mappings": []}
            return _role_artifact(
                expectation.request_id, "inventory-owner", expectation.target_seal,
                expectation.round_input_seal, payload,
            )

        return _owner

    def inventory_challenger(self):
        def _challenger(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("inventory-challenge")
            return _role_artifact(
                expectation.request_id, "inventory-challenge", expectation.target_seal,
                expectation.round_input_seal, {"verdict": "UPHOLD"},
            )

        return _challenger

    def rater(self, *, complexity="max", risk="max", gestalt=False, name="rater", malformed_first=False):
        state = {"called": False}

        def _rate() -> ValidatedRoleArtifact:
            self.events.append(name)
            if malformed_first and not state["called"]:
                state["called"] = True
                raise RoleValidationError("malformed rating output")
            payload = {
                "complexity": complexity, "risk": risk,
                "evidence": [
                    {"axis": "complexity", "statement": "many moving parts"},
                    {"axis": "risk", "statement": "touches auth"},
                ],
                "gestalt": (
                    {"factors": ["a", "b", "c"]} if gestalt else None
                ),
            }
            return _role_artifact(f"req-{name}", "rating", self.seal.digest, None, payload)

        return _rate

    def dispatch_role(self):
        def _dispatch(expectation: DispatchExpectation):
            self.events.append(expectation.role)
            body = _review_report_body(expectation)
            process = ProcessCompletion(
                request_id=expectation.request_id, exit_status=0, process_tree_terminated=True,
            )
            return body, process

        return _dispatch

    def triager(self):
        def _triage(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("triage")
            payload = {"report_ids": list(expectation.expected_ids), "findings": []}
            return _role_artifact(
                expectation.request_id, "triage", expectation.target_seal,
                expectation.round_input_seal, payload, expected_ids=expectation.expected_ids,
                extra=expectation.extra,
            )

        return _triage

    def final_challenger(self):
        def _challenge() -> ValidatedRoleArtifact:
            self.events.append("final-challenge")
            return _role_artifact("req-final", "final-readiness", self.seal.digest, None, {"verdict": "UPHOLD"})

        return _challenge


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class CleanTracerTests(CleanTracerFixture, unittest.TestCase):
    def test_full_lifecycle_converges_and_is_merge_ready(self):
        run_state = self.controller.create_run(self.intent())
        self.assertEqual(run_state.stage, "PREFLIGHT")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="low",
            no_confirm=False,
        )
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        self.assertEqual(stage0.tier, "low")
        self.assertEqual(len(stage0.gate_results), 1)
        self.assertEqual(stage0.gate_results[0].status, "PASSED")
        self.assertEqual(stage0.gate_results[0].target_seal, self.seal.digest)
        self.assertEqual([a.id for a in stage0.areas], ["area-greet"])
        self.assertEqual(stage0.areas[0].charter, ONE_MINOR_AREA["charter"])

        round1 = self.controller.run_round1(stage0, dispatch_role=self.dispatch_role())
        self.assertEqual(round1.run_state.stage, "REVIEW")
        # the Minor area never meets the `low`-tier ("Critical"+) specialist
        # threshold, so the roster is exactly holistic + adversarial.
        self.assertEqual([r["role"] for r in round1.roster], ["holistic", "adversarial"])
        self.assertEqual(len(round1.raw_reports), 2)

        triage_state = self.controller.run_triage(round1, triager=self.triager())
        self.assertEqual(triage_state.stage, "TRIAGE")
        self.assertEqual(triage_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"], [])

        challenge_state = self.controller.run_final_challenge(triage_state, final_challenger=self.final_challenger())
        self.assertEqual(challenge_state.stage, "CLOSE")

        final_state = self.controller.close(challenge_state)
        self.assertEqual(final_state.stage, "COMPLETE")

        terminal = final_state.snapshot["processor_state"]["compute_terminal"]
        self.assertEqual(terminal["terminal_verdict"], "CONVERGED")
        self.assertTrue(terminal["merge_ready"])
        self.assertEqual(terminal["failed_conditions"], [])

        # no FIX: apply_ledger_decisions never records a manifest, and no
        # "fix" key was ever written to processor_state.
        self.assertNotIn("fix", final_state.snapshot["processor_state"])
        for row in triage_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]:
            self.assertIsNone(row.get("manifest_artifact_id"))

        # execution order: scout + its one baseline gate run before any
        # inventory/rating dispatch, which runs before round 1, which runs
        # before TRIAGE, which runs before the final challenge.
        self.assertEqual(
            self.events,
            [
                "scout", "gate:tests",
                "inventory-owner", "inventory-challenge",
                "holistic", "adversarial",
                "triage",
                "final-challenge",
            ],
        )

        report = generate_report(final_state)
        self.assertIn("CONVERGED", report)
        self.assertIn("Merge-ready: True", report)
        self.assertIn("`tests`", report)

    def test_repository_gate_is_merged_with_the_scout_baseline(self):
        repo_gates_data = json.loads((EVIDENCE_PROJECTS / "repository_lint_gate.json").read_text())
        repository_gates = [
            GateProposal(
                id=g["id"], argv=tuple(g["argv"]), applicability=g["applicability"], rationale=g["rationale"],
            )
            for g in repo_gates_data["gates"]
        ]
        run_state = self.controller.create_run(self.intent())
        stage0 = self.controller.run_stage0(
            run_state,
            repository_gates=repository_gates,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="low",
        )
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        gates = stage0.run_state.snapshot["processor_state"]["reconcile_gates"]["gates"]
        ids = {g["id"]: g for g in gates}
        self.assertEqual(set(ids), {"tests", "lint"})
        self.assertEqual(ids["lint"]["classification"], "supporting")


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class AutomaticTierTests(CleanTracerFixture, unittest.TestCase):
    def test_two_raters_merge_to_max_and_require_confirmation(self):
        run_state = self.controller.create_run(self.intent())
        confirmed = {"asked": False}

        def confirm(reason):
            confirmed["asked"] = True
            return True

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier=None,
            no_confirm=False,
            raters=(
                self.rater(complexity="max", risk="max", name="rater-a"),
                self.rater(complexity="max", risk="max", name="rater-b"),
            ),
            confirm=confirm,
        )
        self.assertEqual(stage0.tier, "max")
        self.assertTrue(confirmed["asked"])
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        self.assertEqual(
            self.events[:4],
            ["scout", "gate:tests", "inventory-owner", "inventory-challenge"],
        )
        self.assertEqual(set(self.events[4:6]), {"rater-a", "rater-b"})

    def test_malformed_rater_is_retried_once(self):
        run_state = self.controller.create_run(self.intent())
        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier=None,
            no_confirm=True,
            raters=(
                self.rater(complexity="low", risk="low", name="rater-a", malformed_first=True),
                self.rater(complexity="low", risk="low", name="rater-b"),
            ),
            confirm=None,
        )
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        self.assertEqual(stage0.tier, "low")
        self.assertEqual(self.events.count("rater-a"), 2)

    def test_rater_malformed_twice_is_stage0_indeterminate(self):
        def always_malformed():
            self.events.append("bad-rater")
            raise RoleValidationError("bad")

        run_state = self.controller.create_run(self.intent())
        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier=None,
            no_confirm=True,
            raters=(always_malformed, self.rater(name="rater-b")),
            confirm=None,
        )
        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")
        self.assertEqual(self.events.count("bad-rater"), 2)

    def test_explicit_max_does_not_prompt(self):
        run_state = self.controller.create_run(self.intent())

        def confirm(reason):
            self.fail("explicit max must never prompt for confirmation")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="max",
            no_confirm=False,
            confirm=confirm,
        )
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        self.assertEqual(stage0.tier, "max")

    def test_no_confirm_automatic_max_does_not_prompt(self):
        run_state = self.controller.create_run(self.intent())

        def confirm(reason):
            self.fail("no_confirm must suppress the automatic-max prompt")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier=None,
            no_confirm=True,
            raters=(
                self.rater(complexity="max", risk="max", name="rater-a"),
                self.rater(complexity="max", risk="max", name="rater-b"),
            ),
            confirm=confirm,
        )
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        self.assertEqual(stage0.tier, "max")


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class ConfirmationTests(CleanTracerFixture, unittest.TestCase):
    def _automatic_max_stage0(self, confirm):
        run_state = self.controller.create_run(self.intent())
        return self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier=None,
            no_confirm=False,
            raters=(
                self.rater(complexity="max", risk="max", name="rater-a"),
                self.rater(complexity="max", risk="max", name="rater-b"),
            ),
            confirm=confirm,
        )

    def test_decline_cancels_before_review_without_close(self):
        stage0 = self._automatic_max_stage0(confirm=lambda reason: False)
        self.assertEqual(stage0.run_state.stage, "CANCELLED_BEFORE_REVIEW")
        self.assertIn("declined", stage0.run_state.reason)
        # inventory/rating state is retained (design: "retain the completed
        # inventory/rating state") even though the run never entered REVIEW.
        self.assertIn("derive_policy", stage0.run_state.snapshot["processor_state"])
        self.assertNotIn("plan_roster", stage0.run_state.snapshot["processor_state"])

    def test_expiry_while_waiting_is_indeterminate_not_cancelled(self):
        def confirm(reason):
            raise ConfirmationExpired("absolute deadline passed while awaiting confirmation")

        stage0 = self._automatic_max_stage0(confirm=confirm)
        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")

    def test_missing_confirm_callable_cancels_rather_than_dispatching(self):
        stage0 = self._automatic_max_stage0(confirm=None)
        self.assertEqual(stage0.run_state.stage, "CANCELLED_BEFORE_REVIEW")


if __name__ == "__main__":
    unittest.main()
