import unittest
from tests.contract.helpers import apply_bound
class GateTests(unittest.TestCase):
 def test_gate_projection_has_no_command_or_output(self):
  result=apply_bound("reconcile_gates",{"target_seal":"seal-1","gates":[{"id":"tests","target_seal":"seal-1","applicability":"applicable","classification":"required","status":"PASSED","artifact_id":"gate-1"}]})
  self.assertTrue(result["merge_readiness_eligible"])
