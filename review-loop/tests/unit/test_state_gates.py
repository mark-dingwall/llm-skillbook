import unittest

from review_loop.artifacts import ArtifactMismatch, ProjectionAuthority
from review_loop.state import apply
from tests.contract.helpers import (
    bound_transition_fixture,
    bound_transition_on_snapshot,
)


def derived_policy_snapshot():
    projection = {"explicit_tier": "low", "no_confirm": False, "ratings": []}
    snapshot, _, envelope = bound_transition_fixture(
        kind="rating",
        schema_version=1,
        target_seal="seal-1",
        operation="derive_policy",
        source_ids=("rating-1",),
        raw_bytes=b"rating",
        projection=projection,
    )
    return apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))


def apply_gates(snapshot, projection, artifact_id="gate-projection"):
    issued, _, envelope = bound_transition_on_snapshot(
        snapshot,
        kind="gate",
        schema_version=1,
        target_seal="seal-1",
        operation="reconcile_gates",
        source_ids=(artifact_id,),
        raw_bytes=artifact_id.encode("utf-8"),
        projection=projection,
    )
    return apply(envelope, issued, ProjectionAuthority.from_snapshot(issued))


def gate(classification="required", status="PASSED", applicability="applicable"):
    return {
        "id": "tests",
        "target_seal": "seal-1",
        "applicability": applicability,
        "classification": classification,
        "status": status,
        "artifact_id": "gate-1",
    }


class GateTests(unittest.TestCase):
    def test_derive_policy_establishes_fixed_required_gate_ids(self):
        policy = derived_policy_snapshot()["processor_state"]["derive_policy"]
        self.assertEqual(policy["required_gate_ids"], ["tests"])

    def test_gate_projection_uses_canonical_policy_without_policy_input(self):
        result = apply_gates(
            derived_policy_snapshot(),
            {"target_seal": "seal-1", "gates": [gate()]},
        )["processor_state"]["reconcile_gates"]
        self.assertTrue(result["merge_readiness_eligible"])
        self.assertEqual(result["required_gate_ids"], ["tests"])

    def test_empty_gate_discovery_blocks_canonical_required_gate(self):
        result = apply_gates(
            derived_policy_snapshot(),
            {"target_seal": "seal-1", "gates": []},
        )["processor_state"]["reconcile_gates"]
        self.assertFalse(result["merge_readiness_eligible"])
        self.assertEqual(
            result["blocking_reasons"], ["required gate tests missing"]
        )
        self.assertEqual(
            result["evidence_gaps"], ["no applicable evidence gates discovered"]
        )

    def test_projection_cannot_redefine_canonical_required_gate_ids(self):
        projection = {
            "target_seal": "seal-1",
            "required_gate_ids": [],
            "gates": [],
        }
        with self.assertRaises(ArtifactMismatch):
            apply_gates(derived_policy_snapshot(), projection)

    def test_required_gate_cannot_be_omitted_or_relabelled(self):
        snapshot = derived_policy_snapshot()
        with self.assertRaises(ArtifactMismatch):
            apply_gates(
                snapshot,
                {"target_seal": "seal-1", "gates": [gate("supporting")]},
                "gate-relabelled",
            )

    def test_non_applicable_gate_cannot_execute(self):
        with self.assertRaises(ArtifactMismatch):
            apply_gates(
                derived_policy_snapshot(),
                {
                    "target_seal": "seal-1",
                    "gates": [gate(status="PASSED", applicability="not_applicable")],
                },
            )
