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
from copy import deepcopy
from pathlib import Path

from review_loop.controller import ConfirmationExpired, Controller, ControllerError
from review_loop.artifacts import CanonicalStore
from review_loop.evidence import (
    GateResult,
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
        self.seal = seal_target(
            self.target, GitPolicy(enabled=True, base="HEAD", include_untracked=True),
        )
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

    def scout_with_failing_supporting_gate(self):
        """Proposes the passing required baseline PLUS a failing supporting
        gate -- design: "An executed applicable failure -- INCLUDING a
        supporting gate -- prevents convergence."""

        def _scout() -> ValidatedRoleArtifact:
            self.events.append("scout")
            payload = {
                "gates": [
                    {
                        "id": "tests", "argv": ["python3", "-c", "print('baseline gate ok')"],
                        "applicability": "applicable", "classification": "required",
                        "rationale": "baseline: the target must at least import cleanly",
                    },
                    {
                        "id": "lint", "argv": ["python3", "-c", "exit(1)"],
                        "applicability": "applicable", "classification": "supporting",
                        "rationale": "supporting: pretend lint check that always fails",
                    },
                ],
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

    def synthetic_gate_dispatch(self):
        def _dispatch(gate):
            self.events.append(f"gate:{gate.id}")
            return GateResult(
                gate_id=gate.id, argv=gate.argv, classification=gate.classification,
                applicability=gate.applicability, provenance=gate.provenance,
                rationale=gate.rationale, target_seal=self.seal.digest, status="PASSED",
                exit_status=0, stdout_excerpt="", stderr_excerpt="",
            )
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
        def _challenge(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("final-challenge")
            return _role_artifact(
                expectation.request_id, "final-readiness", expectation.target_seal,
                expectation.round_input_seal, {"verdict": "UPHOLD"},
            )

        return _challenge


class DispatchPolicyTests(CleanTracerFixture, unittest.TestCase):
    def _stage0(self, run_state, tier="low"):
        return self.controller.run_stage0(
            run_state, scout=self.scout(), gate_dispatch=self.synthetic_gate_dispatch(),
            inventory_owner=self.inventory_owner(), inventory_challenger=self.inventory_challenger(),
            explicit_tier=tier,
        )

    def test_normal_role_model_pins_reach_dispatch_expectations(self):
        profile = self.xdg / "review-loop" / "profiles" / "pins.yaml"
        profile.parent.mkdir(parents=True)
        profile.write_text(
            "version: 1\n"
            "holistic:\n  model: holistic-pin\n"
            "adversarial:\n  model: adversarial-pin\n"
        )
        stage0 = self._stage0(self.controller.create_run(self.intent(review_profile="pins")))
        seen = {}

        def dispatch(expectation):
            seen[expectation.role] = expectation.model
            return _review_report_body(expectation), ProcessCompletion(expectation.request_id, 0, True)

        self.controller.run_round1(stage0, dispatch_role=dispatch)
        self.assertEqual(seen, {"holistic": "holistic-pin", "adversarial": "adversarial-pin"})

    def test_low_tier_rejects_multi_review_before_dispatch(self):
        stage0 = self._stage0(self.controller.create_run(self.intent()), tier="low")

        def dispatched(_expectation):
            self.fail("low-tier multi-review must be rejected before dispatch")

        with self.assertRaises(ControllerError):
            self.controller.run_round1(
                stage0, dispatch_role=dispatched, multi_review_dispatch=dispatched,
            )

    def test_close_refuses_an_expired_persisted_deadline(self):
        stage0 = self._stage0(self.controller.create_run(self.intent(max_time_seconds=60)))
        round1 = self.controller.run_round1(stage0, dispatch_role=self.dispatch_role())
        triage = self.controller.run_triage(round1, triager=self.triager())
        challenge = self.controller.run_final_challenge(
            triage, final_challenger=self.final_challenger(),
        )
        snapshot = deepcopy(challenge.snapshot)
        snapshot["processor_state"]["preflight"]["absolute_expiry"] = "2000-01-01T00:00:00+00:00"
        CanonicalStore(self.run_root)._replace(snapshot)
        expired = type(challenge)(
            challenge.run_root, challenge.governing_seal, snapshot, challenge.stage, challenge.reason,
        )

        with self.assertRaises(ControllerError):
            self.controller.close(expired)


class Stage0IdentityTests(CleanTracerFixture, unittest.TestCase):
    def test_scout_drift_stops_before_gate_dispatch(self):
        run_state = self.controller.create_run(self.intent())
        scout = self.scout()

        def drifting_scout():
            artifact = scout()
            (self.target / "greet.py").write_text("drifted")
            return artifact

        def must_not_dispatch(_gate):
            self.fail("gate dispatch must not inspect target bytes changed by the scout")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=drifting_scout,
            gate_dispatch=must_not_dispatch,
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="low",
        )

        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")

    def test_gate_drift_stops_before_inventory_dispatch(self):
        run_state = self.controller.create_run(self.intent())
        gate_dispatch = self.synthetic_gate_dispatch()

        def drifting_gate(gate):
            result = gate_dispatch(gate)
            (self.target / "greet.py").write_text("drifted")
            return result

        def must_not_dispatch(_expectation):
            self.fail("inventory must not inspect target bytes changed by a gate")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=drifting_gate,
            inventory_owner=must_not_dispatch,
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="low",
        )

        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")

    def test_inventory_owner_drift_stops_before_challenge_dispatch(self):
        run_state = self.controller.create_run(self.intent())
        inventory_owner = self.inventory_owner()

        def drifting_owner(expectation):
            artifact = inventory_owner(expectation)
            (self.target / "greet.py").write_text("drifted")
            return artifact

        def must_not_dispatch(_expectation):
            self.fail("inventory challenge must not inspect bytes changed by the owner")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.synthetic_gate_dispatch(),
            inventory_owner=drifting_owner,
            inventory_challenger=must_not_dispatch,
            explicit_tier="low",
        )

        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")

    def test_inventory_challenge_drift_stops_before_rating_dispatch(self):
        run_state = self.controller.create_run(self.intent())
        challenger = self.inventory_challenger()

        def drifting_challenger(expectation):
            artifact = challenger(expectation)
            (self.target / "greet.py").write_text("drifted")
            return artifact

        def must_not_rate():
            self.fail("rating must not inspect bytes changed by inventory challenge")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.synthetic_gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=drifting_challenger,
            explicit_tier=None,
            raters=(must_not_rate, must_not_rate),
        )

        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")

    def test_first_rater_drift_stops_before_second_rating_dispatch(self):
        run_state = self.controller.create_run(self.intent())
        first_rater = self.rater(complexity="low", risk="low", name="rater-a")

        def drifting_rater():
            artifact = first_rater()
            (self.target / "greet.py").write_text("drifted")
            return artifact

        def must_not_rate():
            self.fail("second rating must not inspect bytes changed by first rating")

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.synthetic_gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier=None,
            no_confirm=True,
            raters=(drifting_rater, must_not_rate),
        )

        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")

    def test_inventory_revision_drift_makes_stage0_indeterminate(self):
        run_state = self.controller.create_run(self.intent())

        def challenger(expectation):
            payload = {
                "verdict": "CHALLENGE",
                "challenges": [{
                    "id": "c1", "category": "omission",
                    "statement": "inventory needs revision",
                    "evidence": "greet.py owns the reviewed behavior",
                }],
            }
            return _role_artifact(
                expectation.request_id, "inventory-challenge", expectation.target_seal,
                expectation.round_input_seal, payload,
            )

        def drifting_revision(expectation):
            payload = {
                "areas": [ONE_MINOR_AREA], "priority_order": ["area-greet"],
                "resolutions": [{"challenge_id": "c1", "resolution": "retained owning area"}],
            }
            artifact = _role_artifact(
                expectation.request_id, "inventory-revision", expectation.target_seal,
                expectation.round_input_seal, payload, expected_ids=expectation.expected_ids,
            )
            (self.target / "greet.py").write_text("drifted")
            return artifact

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.synthetic_gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=challenger,
            inventory_revision=drifting_revision,
            explicit_tier="low",
        )

        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")


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
class FailedGateBlocksReviewTests(CleanTracerFixture, unittest.TestCase):
    """An executed applicable gate failure -- including a merely
    SUPPORTING-classified one -- must prevent round 1 dispatch and end the
    run NOT_CONVERGED, end to end through the real gate-execution path.
    """

    def test_failed_supporting_gate_blocks_round1_and_yields_not_converged(self):
        run_state = self.controller.create_run(self.intent())
        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout_with_failing_supporting_gate(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="low",
        )
        self.assertEqual(stage0.run_state.stage, "STAGE0")
        gates = {g.gate_id: g for g in stage0.gate_results}
        self.assertEqual(gates["tests"].status, "PASSED")
        self.assertEqual(gates["lint"].status, "FAILED")
        self.assertFalse(stage0.review_may_start)
        self.assertIn("gate lint failed", stage0.blocking_reasons)

        def dispatch_role_must_not_be_called(expectation):
            self.fail("round 1 must never dispatch a reviewer when review_may_start is False")

        round1 = self.controller.run_round1(stage0, dispatch_role=dispatch_role_must_not_be_called)
        self.assertEqual(round1.roster, ())
        self.assertEqual(round1.raw_reports, ())
        self.assertEqual(round1.run_state.stage, "COMPLETE")

        terminal = round1.run_state.snapshot["processor_state"]["compute_terminal"]
        self.assertEqual(terminal["terminal_verdict"], "NOT_CONVERGED")
        self.assertFalse(terminal["merge_ready"])
        self.assertIn("gates_not_ready", terminal["failed_conditions"])

        # never reached REVIEW/TRIAGE/CLOSE at all
        self.assertNotIn("plan_roster", round1.run_state.snapshot["processor_state"])
        self.assertNotIn("apply_ledger_decisions", round1.run_state.snapshot["processor_state"])
        self.assertNotIn("record_final_challenge", round1.run_state.snapshot["processor_state"])

        report = generate_report(round1.run_state)
        self.assertIn("NOT_CONVERGED", report)
        self.assertIn("Merge-ready: False", report)


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

    def test_deadline_rechecked_after_confirmation_returns(self):
        run_state = self.controller.create_run(self.intent(max_time_seconds=60))

        def confirm(_reason):
            run_state.snapshot["processor_state"]["preflight"]["absolute_expiry"] = (
                "2000-01-01T00:00:00+00:00"
            )
            return True

        stage0 = self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.synthetic_gate_dispatch(),
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

        self.assertEqual(stage0.run_state.stage, "INDETERMINATE")

    def test_missing_confirm_callable_cancels_rather_than_dispatching(self):
        stage0 = self._automatic_max_stage0(confirm=None)
        self.assertEqual(stage0.run_state.stage, "CANCELLED_BEFORE_REVIEW")


if __name__ == "__main__":
    unittest.main()
