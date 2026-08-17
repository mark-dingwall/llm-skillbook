import tempfile
import unittest
from pathlib import Path

from review_loop.artifacts import CanonicalStore


class CanonicalStoreTests(unittest.TestCase):
    def test_issuance_records_artifact_and_projection_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CanonicalStore(Path(directory))
            store.initialize("seal-a")
            snapshot = store.issue_transition(
                operation="derive_policy",
                artifact_id="rating-a",
                kind="rating",
                schema_version=1,
                target_seal="seal-a",
                raw_bytes=b"{}",
                projection={"explicit_tier": "low", "no_confirm": False, "ratings": []},
            )
            self.assertIn("rating-a", snapshot["artifact_registry"]["artifacts"])
            self.assertEqual(snapshot["artifact_registry"]["bindings"][0]["operation"], "derive_policy")

    def test_orphan_evidence_is_not_loaded_as_a_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CanonicalStore(Path(directory))
            store.initialize("seal-a")
            (Path(directory) / "evidence" / "orphan.json").write_bytes(b"{}")
            self.assertEqual(store.load()["artifact_registry"]["artifacts"], {})


if __name__ == "__main__":
    unittest.main()
