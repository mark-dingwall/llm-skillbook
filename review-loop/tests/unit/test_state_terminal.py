import unittest

from review_loop.artifacts import ArtifactMismatch, ProjectionAuthority
from review_loop.state import apply
from tests.contract.helpers import (
    bound_transition_fixture,
    bound_transition_on_snapshot,
)


LIFECYCLE = {
    "confirmation": "confirmed",
    "deadline_expired": False,
    "round1_triage_complete": True,
    "scheduled_reports_usable": True,
    "raw_reports_reconciled": True,
    "any_indeterminate": False,
    "expected_final_seal": "seal-1",
    "actual_final_seal": "seal-1",
}
GATES = {
    "gates": [
        {
            "id": "tests",
            "target_seal": "seal-1",
            "applicability": "applicable",
            "classification": "required",
            "status": "PASSED",
            "artifact_id": "gate-proof",
        }
    ],
    "required_gate_ids": ["tests"],
    "blocking_reasons": [],
    "evidence_gaps": [],
    "review_may_start": True,
    "merge_readiness_eligible": True,
}
CHALLENGE = {
    "state": "UPHELD",
    "fresh": True,
    "target_seal": "seal-1",
    "source_finding_ids": [],
    "artifact_id": "final",
    "retry_required": False,
}


def policy_snapshot():
    projection = {"explicit_tier": "low", "no_confirm": False, "ratings": []}
    snapshot, _, envelope = bound_transition_fixture(
        kind="rating",
        schema_version=1,
        target_seal="seal-1",
        operation="derive_policy",
        source_ids=("terminal-rating",),
        raw_bytes=b"rating",
        projection=projection,
    )
    return apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))


def apply_terminal(projection):
    snapshot, _, envelope = bound_transition_on_snapshot(
        policy_snapshot(),
        kind="terminal",
        schema_version=1,
        target_seal="seal-1",
        operation="compute_terminal",
        source_ids=("terminal-projection",),
        raw_bytes=b"terminal",
        projection=projection,
    )
    return apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))[
        "processor_state"
    ]["compute_terminal"]


def terminal_projection(lifecycle=LIFECYCLE, ledger=None, gates=GATES):
    return {
        "lifecycle": lifecycle,
        "ledger": list(ledger or []),
        "gates": gates,
        "areas": [],
        "final_challenge": CHALLENGE,
    }


class TerminalTests(unittest.TestCase):
    def test_promoted_final_seal_can_differ_from_gate_baseline(self):
        lifecycle = dict(LIFECYCLE, expected_final_seal="seal-2", actual_final_seal="seal-2")
        projection = terminal_projection(lifecycle=lifecycle)
        projection["final_challenge"] = dict(CHALLENGE, target_seal="seal-2")

        result = apply_terminal(projection)

        self.assertTrue(result["merge_ready"])

    def test_terminal_requires_all_lifecycle_and_seal_conjuncts(self):
        result = apply_terminal(
            terminal_projection(
                ledger=[
                    {
                        "id": "F1",
                        "state": "FIX_VERIFIED",
                        "current_severity": "Important",
                        "proof_artifact_ids": ["proof"],
                    }
                ]
            )
        )
        self.assertTrue(result["merge_ready"])
        bad = dict(LIFECYCLE)
        bad["actual_final_seal"] = "old"
        rejected = apply_terminal(terminal_projection(lifecycle=bad))
        self.assertFalse(rejected["merge_ready"])
        self.assertIn("seal", rejected["failed_conditions"])

    def test_failed_gate_and_malformed_proofs_cannot_be_ready(self):
        failed = dict(GATES)
        failed["gates"] = [dict(GATES["gates"][0], status="FAILED")]
        failed["blocking_reasons"] = ["gate tests failed"]
        failed["review_may_start"] = False
        failed["merge_readiness_eligible"] = False
        result = apply_terminal(terminal_projection(gates=failed))
        self.assertFalse(result["merge_ready"])
        malformed = apply_terminal(
            terminal_projection(
                ledger=[
                    {
                        "id": "F1",
                        "state": "FIX_VERIFIED",
                        "current_severity": "Important",
                        "proof_artifact_ids": [None],
                    }
                ]
            )
        )
        self.assertFalse(malformed["merge_ready"])

    def test_terminal_gate_rollup_cannot_redefine_canonical_policy(self):
        forged = {
            "gates": [],
            "required_gate_ids": [],
            "blocking_reasons": [],
            "evidence_gaps": ["no applicable evidence gates discovered"],
            "review_may_start": True,
            "merge_readiness_eligible": True,
        }
        with self.assertRaises(ArtifactMismatch):
            apply_terminal(terminal_projection(gates=forged))

    def test_final_challenge_retry_and_stale_are_mechanical(self):
        from tests.contract.helpers import apply_bound

        retry = apply_bound(
            "record_final_challenge",
            {
                "current_seal": "seal-1",
                "attempts": [
                    {
                        "status": "FAILED",
                        "target_seal": "seal-1",
                        "source_finding_ids": [],
                        "artifact_id": "a",
                    }
                ],
            },
        )
        self.assertEqual(retry["state"], "RETRY_REQUIRED")
        indeterminate = apply_bound(
            "record_final_challenge",
            {
                "current_seal": "seal-1",
                "attempts": [
                    {
                        "status": "FAILED",
                        "target_seal": "seal-1",
                        "source_finding_ids": [],
                        "artifact_id": "a",
                    },
                    {
                        "status": "FAILED",
                        "target_seal": "seal-1",
                        "source_finding_ids": [],
                        "artifact_id": "b",
                    },
                ],
            },
        )
        self.assertEqual(indeterminate["state"], "INDETERMINATE")
        stale = apply_bound(
            "record_final_challenge",
            {
                "current_seal": "seal-1",
                "attempts": [
                    {
                        "status": "UPHOLD",
                        "target_seal": "old",
                        "source_finding_ids": [],
                        "artifact_id": "a",
                    }
                ],
            },
        )
        self.assertEqual(stale["state"], "STALE")
