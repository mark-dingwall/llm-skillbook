import copy
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


def ledger_projection(item=None, manifests=None, adjudication=None):
    projection = {
        "decisions": [] if item is None else [item],
        "manifests": [
            {"id": value, "finding_id": item["id"]}
            for value in (manifests or [])
        ],
        "target_seal": "seal-1",
        "adjudication": adjudication,
    }
    return projection


def initial_ledger_projection(
    prior=None, item=None, manifests=None, adjudication=None
):
    projection = ledger_projection(item, manifests, adjudication)
    projection["initial_rows"] = [] if prior is None else [prior]
    return projection


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
    projection = initial_ledger_projection(
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
    def test_first_transition_initializes_an_explicit_empty_ledger(self):
        applied = apply_first(initial_ledger_projection())

        self.assertEqual(
            applied["processor_state"]["apply_ledger_decisions"],
            {
                "rows": [],
                "pending_fix_ids": [],
                "round_indeterminate": False,
                "next_adjudication": None,
            },
        )

    def test_initial_rows_must_start_as_unsettled_open_rows(self):
        with self.assertRaises(ArtifactMismatch):
            apply_first(
                initial_ledger_projection(
                    row(state="FIX_APPLIED", manifest="M1"),
                    decision("FIX_APPLIED", manifest="M1"),
                    ["M1"],
                )
            )

    def test_null_canonical_ledger_cannot_reopen_initialization(self):
        initialized = apply_first(initial_ledger_projection())
        initialized["processor_state"]["apply_ledger_decisions"] = None

        with self.assertRaises(ArtifactMismatch):
            apply_next(
                initialized,
                initial_ledger_projection(row(), decision("OPEN")),
            )

    def test_open_must_apply_linked_manifest_before_fix_verified(self):
        with self.assertRaises(ArtifactMismatch):
            apply_first(
                initial_ledger_projection(
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
            initial_ledger_projection(
                row(), decision("FIX_APPLIED", manifest="M1"), ["M1"]
            )
        )
        self.assertEqual(
            applied["processor_state"]["apply_ledger_decisions"]["rows"][0]["state"],
            "FIX_APPLIED",
        )
        verified = apply_next(
            applied,
            ledger_projection(
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
        self.assertEqual(
            verified["processor_state"]["apply_ledger_decisions"]["rows"][0][
                "manifest_artifact_id"
            ],
            "M1",
        )
        self.assertEqual(
            verified["processor_state"]["apply_ledger_decisions"]["rows"][0][
                "proof_artifact_ids"
            ],
            ["proof"],
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
            second["processor_state"]["apply_ledger_decisions"]["rows"],
            first["processor_state"]["apply_ledger_decisions"]["rows"],
        )

    def test_projection_cannot_forge_canonical_prior_row_state(self):
        canonical = apply_first(initial_ledger_projection(row(), decision("OPEN")))
        forged = ledger_projection(decision("OPEN"))
        forged["prior_rows"] = [row(state="REFUTED")]

        with self.assertRaises(ArtifactMismatch):
            apply_next(canonical, forged)

    def test_attempt_two_cannot_forge_fix_applied_and_jump_to_fix_verified(self):
        first = failed_first_attempt()
        forged = ledger_projection(
            decision("FIX_VERIFIED", ["proof-2"], "M1"),
            ["M1"],
            {
                "attempt": 2,
                "status": "UPHOLD",
                "decided_ids": ["F1"],
                "proof_artifact_id": "adj-2",
            },
        )
        forged["prior_rows"] = [row(state="FIX_APPLIED", manifest="M1")]

        with self.assertRaises(ArtifactMismatch):
            apply_next(first, forged)

    def test_canonical_open_row_cannot_jump_directly_to_fix_verified(self):
        canonical = apply_first(initial_ledger_projection(row(), decision("OPEN")))

        with self.assertRaises(ArtifactMismatch):
            apply_next(
                canonical,
                ledger_projection(
                    decision("FIX_VERIFIED", ["proof-2"], "M1"),
                    ["M1"],
                    {
                        "attempt": 1,
                        "status": "UPHOLD",
                        "decided_ids": ["F1"],
                        "proof_artifact_id": "adj-2",
                    },
                ),
            )

    def test_projection_cannot_replay_stale_prior_rows(self):
        applied = apply_first(
            initial_ledger_projection(
                row(), decision("FIX_APPLIED", manifest="M1"), ["M1"]
            )
        )
        for field in ("prior_rows", "initial_rows"):
            stale = ledger_projection(
                decision("FIX_APPLIED", manifest="M2"),
                ["M2"],
            )
            stale[field] = [row()]

            with self.subTest(field=field), self.assertRaises(ArtifactMismatch):
                apply_next(applied, stale)

    def test_attempt_two_rejects_mismatched_canonical_retry_state(self):
        first_projection = initial_ledger_projection(
            row("F1"),
            decision("REFUTED", ["settlement-1"], finding_id="F1"),
            adjudication={
                "attempt": 1,
                "status": "FAILED",
                "decided_ids": [],
                "proof_artifact_id": None,
            },
        )
        first_projection["initial_rows"].append(row("F2"))
        first_projection["decisions"].append(
            decision("REFUTED", ["settlement-2"], finding_id="F2")
        )
        first = apply_first(first_projection)
        mismatched = copy.deepcopy(first)
        mismatched["processor_state"]["apply_ledger_decisions"][
            "next_adjudication"
        ]["pending_ids"] = ["F1"]
        second_projection = ledger_projection(
            decision("REFUTED", ["settlement-3"], finding_id="F1"),
            adjudication={
                "attempt": 2,
                "status": "UPHOLD",
                "decided_ids": ["F1", "F2"],
                "proof_artifact_id": "adj-2",
            },
        )
        second_projection["decisions"].append(
            decision("REFUTED", ["settlement-4"], finding_id="F2")
        )

        with self.assertRaises(ArtifactMismatch):
            apply_next(mismatched, second_projection)

    def test_attempt_two_cannot_self_assert_retry_state_or_skip_attempt_one(self):
        projection = ledger_projection(
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
            decision("REFUTED", ["settlement-2"]),
            adjudication={
                "attempt": 1,
                "status": "UPHOLD",
                "decided_ids": ["F1"],
                "proof_artifact_id": "adj-replay",
            },
        )
        with self.assertRaises(ArtifactMismatch):
            apply_next(first, replay)

    def test_decisions_must_target_canonical_rows(self):
        first = failed_first_attempt()
        mismatched = ledger_projection(
            decision("REFUTED", ["settlement-2"], finding_id="F2"),
            adjudication={
                "attempt": 2,
                "status": "UPHOLD",
                "decided_ids": ["F2"],
                "proof_artifact_id": "adj-2",
            },
        )
        with self.assertRaises(ArtifactMismatch):
            apply_next(first, mismatched)

    def test_bounce_must_cover_every_green_decision(self):
        with self.assertRaises(ArtifactMismatch):
            apply_first(
                initial_ledger_projection(
                    row(),
                    decision("REFUTED", ["settlement-1"]),
                    adjudication={
                        "attempt": 1,
                        "status": "BOUNCE",
                        "decided_ids": [],
                        "proof_artifact_id": "adj-1",
                    },
                )
            )

    def test_bounce_and_uphold_require_proof_references(self):
        first = failed_first_attempt()
        for status in ("BOUNCE", "UPHOLD"):
            projection = ledger_projection(
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
