import tempfile
import unittest
from pathlib import Path
from review_loop.artifacts import CanonicalStore, EvidenceArtifact

class CanonicalStoreTests(unittest.TestCase):
 def test_atomic_issuance_binds_ordered_multiple_sources_and_applies(self):
  with tempfile.TemporaryDirectory() as directory:
   store=CanonicalStore(Path(directory)); store.initialize("seal-a")
   snapshot=store.issue_transition(operation="derive_policy",evidence=(EvidenceArtifact("rater-a","rating",1,"seal-a",b"a"),EvidenceArtifact("rater-b","rating",1,"seal-a",b"b")),projection={"explicit_tier":None,"no_confirm":False,"ratings":[{"complexity":"low","risk":"low","gestalt_step":False},{"complexity":"low","risk":"low","gestalt_step":False}]})
   self.assertEqual(snapshot["artifact_registry"]["bindings"][0]["source_ids"],["rater-a","rater-b"])
   self.assertEqual(snapshot["processor_state"]["derive_policy"]["tier"],"low")
 def test_crash_left_orphan_is_reported_and_temp_does_not_block_restart(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory); store=CanonicalStore(root); store.initialize("seal-a")
   (root/"evidence"/"orphan").write_bytes(b"orphan"); (root/".review-state.json.tmp").write_bytes(b"stale")
   self.assertEqual(store.orphan_evidence(),["orphan"])
   store.issue_transition(operation="derive_policy",evidence=(EvidenceArtifact("rating","rating",1,"seal-a",b"{}"),),projection={"explicit_tier":"low","no_confirm":False,"ratings":[]})
   self.assertEqual(store.orphan_evidence(),["orphan"])
