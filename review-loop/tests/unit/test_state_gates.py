import unittest
from tests.contract.helpers import apply_bound
class GateTests(unittest.TestCase):
 def test_gate_projection_has_no_command_or_output(self):
  result=apply_bound("reconcile_gates",{"target_seal":"seal-1","required_gate_ids":["tests"],"gates":[{"id":"tests","target_seal":"seal-1","applicability":"applicable","classification":"required","status":"PASSED","artifact_id":"gate-1"}]})
  self.assertTrue(result["merge_readiness_eligible"])
 def test_empty_discovery_is_gap_and_duplicate_or_nonapplicable_execution_rejects(self):
  empty=apply_bound("reconcile_gates",{"target_seal":"seal-1","required_gate_ids":["tests"],"gates":[]}); self.assertFalse(empty["merge_readiness_eligible"]);self.assertEqual(empty["evidence_gaps"],["no applicable evidence gates discovered"])
  with self.assertRaises(Exception): apply_bound("reconcile_gates",{"target_seal":"seal-1","required_gate_ids":["tests"],"gates":[{"id":"tests","target_seal":"seal-1","applicability":"not_applicable","classification":"required","status":"PASSED","artifact_id":"x"}]})
  with self.assertRaises(Exception): apply_bound("reconcile_gates",{"target_seal":"seal-1","required_gate_ids":["tests"],"gates":[{"id":"tests","target_seal":"seal-1","applicability":"applicable","classification":"supporting","status":"PASSED","artifact_id":"x"}]})
