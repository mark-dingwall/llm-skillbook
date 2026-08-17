import unittest

from review_loop.artifacts import ArtifactMismatch, ProjectionAuthority
from review_loop.state import apply
from tests.contract.helpers import (
    bound_transition_fixture,
    bound_transition_on_snapshot,
)


def row(finding_id="F1", state="OPEN", manifest=None):
    return {
        "id": finding_id,
        "source_ids": [f"raw-{finding_id}"],
        "reported_severity": "Important",
        "current_severity": "Important",
        "factual": "CONFIRMED",
        "state": state,
        "proof_artifact_ids": [],
        "manifest_artifact_id": manifest,
        "target_seal": "seal-1",
    }


def decision(state, proof=None, manifest=None, finding_id="F1"):
    return {
        "id": finding_id,
        "state": state,
        "proof_artifact_ids": list(proof or []),
        "manifest_artifact_id": manifest,
    }


def ledger_projection(prior, item, manifests=None, adjudication=None):
    return {
        "prior_rows": [prior],
        "decisions": [item],
        "manifests": [
            {"id": value, "finding_id": prior["id"]}
            for value in (manifests or [])
        ],
        "target_seal": "seal-1",
        "adjudication": adjudication,
    }


def apply_first(projection):
    snapshot, _, envelope = bound_transition_fixture(
        kind="ledger",
        schema_version=1,
        target_seal="seal-1",
        operation="apply_ledger_decisions",
        source_ids=("ledger-1",),
        raw_bytes=b"first",
        projection=projection,
    )
    return apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))


def apply_next(snapshot, projection, artifact_id="ledger-2"):
    issued, _, envelope = bound_transition_on_snapshot(
        snapshot,
        kind="ledger",
        schema_version=1,
        target_seal="seal-1",
        operation="apply_ledger_decisions",
        source_ids=(artifact_id,),
        raw_bytes=artifact_id.encode("utf-8"),
        projection=projection,
    )
    return apply(envelope, issued, ProjectionAuthority.from_snapshot(issued))


def failed_first_attempt():
    projection = ledger_projection(
        row(),
        decision("REFUTED", ["settlement-1"]),
        adjudication={
            "attempt": 1,
            "status": "FAILED",
            "decided_ids": [],
            "proof_artifact_id": None,
        },
    )
    return apply_first(projection)


class LedgerTests(unittest.TestCase):
    def test_open_must_apply_linked_manifest_before_fix_verified(self):
        with self.assertRaises(ArtifactMismatch):
            apply_first(
                ledger_projection(
                    row(),
                    decision("FIX_VERIFIED", ["proof"], "M1"),
                    ["M1"],
                    {
                        "attempt": 1,
                        "status": "UPHOLD",
                        "decided_ids": ["F1"],
                        "proof_artifact_id": "adj",
                    },
                )
            )
        applied = apply_first(
            ledger_projection(row(), decision("FIX_APPLIED", manifest="M1"), ["M1"])
        )
        self.assertEqual(
            applied["processor_state"]["apply_ledger_decisions"]["rows"][0]["state"],
            "FIX_APPLIED",
        )
        verified = apply_next(
            applied,
            ledger_projection(
                row(state="FIX_APPLIED", manifest="M1"),
                decision("FIX_VERIFIED", ["proof"], "M1"),
                ["M1"],
                {
                    "attempt": 1,
                    "status": "UPHOLD",
                    "decided_ids": ["F1"],
                    "proof_artifact_id": "adj",
                },
            ),
        )
        self.assertEqual(
            verified["processor_state"]["apply_ledger_decisions"]["rows"][0][
                "state"
            ],
            "FIX_VERIFIED",
        )

    def test_real_first_failure_then_second_bounce_uses_canonical_retry(self):
        first = failed_first_attempt()
        self.assertEqual(
            first["processor_state"]["apply_ledger_decisions"]["next_adjudication"],
            {"attempt": 2, "pending_ids": ["F1"]},
        )
        second = apply_next(
            first,
            ledger_projection(
                row(),
                decision("REFUTED", ["settlement-2"]),
                adjudication={
                    "attempt": 2,
                    "status": "BOUNCE",
                    "decided_ids": ["F1"],
                    "proof_artifact_id": "adj-2",
                },
            ),
        )
        self.assertEqual(
            second["processor_state"]["apply_ledger_decisions"]["rows"][0]["state"],
            "OPEN",
        )

    def test_attempt_two_cannot_self_assert_retry_state_or_skip_attempt_one(self):
        projection = ledger_projection(
            row(),
            decision("REFUTED", ["settlement"]),
            adjudication={
                "attempt": 2,
                "status": "UPHOLD",
                "decided_ids": ["F1"],
                "proof_artifact_id": "adj-2",
            },
        )
        projection["prior_next_adjudication"] = {
            "attempt": 2,
            "pending_ids": ["F1"],
        }
        with self.assertRaises(ArtifactMismatch):
            apply_first(projection)

    def test_attempt_one_cannot_replay_after_canonical_failure(self):
        first = failed_first_attempt()
        replay = ledger_projection(
            row(),
            decision("REFUTED", ["settlement-2"]),
            adjudication={
                "attempt": 1,
                "status": "UPHOLD",
                "decided_ids": ["F1"],
                "proof_artifact_id": "adj-replay",
            },
        )
        replay["prior_next_adjudication"] = None
        with self.assertRaises(ArtifactMismatch):
            apply_next(first, replay)

    def test_attempt_two_ids_must_match_canonical_pending_ids(self):
        first = failed_first_attempt()
        mismatched = ledger_projection(
            row("F2"),
            decision("REFUTED", ["settlement-2"], finding_id="F2"),
            adjudication={
                "attempt": 2,
                "status": "UPHOLD",
                "decided_ids": ["F2"],
                "proof_artifact_id": "adj-2",
            },
        )
        mismatched["prior_next_adjudication"] = {
            "attempt": 2,
            "pending_ids": ["F2"],
        }
        with self.assertRaises(ArtifactMismatch):
            apply_next(first, mismatched)

    def test_bounce_and_uphold_require_proof_references(self):
        first = failed_first_attempt()
        for status in ("BOUNCE", "UPHOLD"):
            projection = ledger_projection(
                row(),
                decision("REFUTED", ["settlement-2"]),
                adjudication={
                    "attempt": 2,
                    "status": status,
                    "decided_ids": ["F1"],
                    "proof_artifact_id": None,
                },
            )
            with self.subTest(status=status), self.assertRaises(ArtifactMismatch):
                apply_next(first, projection, f"ledger-{status.lower()}")
