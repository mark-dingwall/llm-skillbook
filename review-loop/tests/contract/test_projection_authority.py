import dataclasses
import unittest

from review_loop import state
from review_loop.artifacts import ArtifactMismatch, ProjectionAuthority
from tests.contract.helpers import bound_transition_fixture


class ProjectionAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot, self.ref, self.envelope = bound_transition_fixture(
            kind="rating",
            schema_version=1,
            target_seal="seal-a",
            operation="derive_policy",
            source_ids=("raw-rater-a", "raw-rater-b"),
            raw_bytes=b"{}",
            projection={"explicit_tier": "high", "no_confirm": False, "ratings": []},
        )

    def authority(self) -> ProjectionAuthority:
        return ProjectionAuthority.from_snapshot(self.snapshot)

    def assert_rejected(self, envelope) -> None:
        with self.assertRaises(ArtifactMismatch):
            state.apply(envelope, self.snapshot, self.authority())

    def test_projection_must_match_registry_binding(self) -> None:
        altered = dataclasses.replace(
            self.envelope,
            projection={"explicit_tier": "max", "no_confirm": False, "ratings": []},
        )
        self.assert_rejected(altered)

    def test_rejects_invented_id_wrong_reference_metadata_and_stale_seal(self) -> None:
        self.assert_rejected(dataclasses.replace(
            self.envelope,
            artifact_refs=(dataclasses.replace(self.envelope.artifact_refs[0], artifact_id="invented"),
                self.envelope.artifact_refs[1]),
        ))
        self.assert_rejected(dataclasses.replace(
            self.envelope,
            artifact_refs=(dataclasses.replace(self.envelope.artifact_refs[0], kind="gate"),
                self.envelope.artifact_refs[1]),
        ))
        self.assert_rejected(dataclasses.replace(
            self.envelope,
            artifact_refs=(dataclasses.replace(self.envelope.artifact_refs[0], schema_version=2),
                self.envelope.artifact_refs[1]),
        ))
        self.assert_rejected(dataclasses.replace(
            self.envelope,
            artifact_refs=(dataclasses.replace(self.envelope.artifact_refs[0], digest="0" * 64),
                self.envelope.artifact_refs[1]),
        ))
        self.assert_rejected(dataclasses.replace(self.envelope, expected_governing_seal="seal-old"))
        self.assert_rejected(dataclasses.replace(self.envelope, artifact_refs=tuple(reversed(self.envelope.artifact_refs))))

    def test_rejects_forged_authority(self) -> None:
        with self.assertRaises(ArtifactMismatch):
            state.apply(self.envelope, self.snapshot, object())

    def test_authority_must_be_derived_from_the_supplied_snapshot(self) -> None:
        altered_snapshot = dict(self.snapshot)
        altered_snapshot["processor_state"] = {"forged": True}
        with self.assertRaises(ArtifactMismatch):
            state.apply(self.envelope, altered_snapshot, self.authority())

    def test_unbound_evidence_is_not_operative(self) -> None:
        snapshot = dict(self.snapshot)
        snapshot["artifact_registry"] = {"artifacts": {}, "bindings": []}
        with self.assertRaises(ArtifactMismatch):
            state.apply(self.envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))


if __name__ == "__main__":
    unittest.main()
