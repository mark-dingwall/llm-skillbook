import unittest
from tests.contract.helpers import apply_bound

LIFECYCLE={"confirmation":"confirmed","deadline_expired":False,"round1_triage_complete":True,"scheduled_reports_usable":True,"raw_reports_reconciled":True,"any_indeterminate":False,"expected_final_seal":"seal-1","actual_final_seal":"seal-1"}
GATES={"gates":[],"blocking_reasons":[],"evidence_gaps":["no applicable evidence gates discovered"],"review_may_start":True,"merge_readiness_eligible":True}
CHALLENGE={"state":"UPHELD","fresh":True,"target_seal":"seal-1","source_finding_ids":[],"artifact_id":"final","retry_required":False}
class TerminalTests(unittest.TestCase):
 def test_terminal_requires_all_lifecycle_and_seal_conjuncts(self):
  result=apply_bound("compute_terminal",{"lifecycle":LIFECYCLE,"ledger":[{"id":"F1","state":"FIX_VERIFIED","current_severity":"Important","proof_artifact_ids":["proof"]}],"gates":GATES,"areas":[],"final_challenge":CHALLENGE})
  self.assertTrue(result["merge_ready"])
  bad=dict(LIFECYCLE);bad["actual_final_seal"]="old"
  rejected=apply_bound("compute_terminal",{"lifecycle":bad,"ledger":[],"gates":GATES,"areas":[],"final_challenge":CHALLENGE})
  self.assertFalse(rejected["merge_ready"]);self.assertIn("seal",rejected["failed_conditions"])
 def test_final_challenge_retry_and_stale_are_mechanical(self):
  retry=apply_bound("record_final_challenge",{"current_seal":"seal-1","attempts":[{"status":"FAILED","target_seal":"seal-1","source_finding_ids":[],"artifact_id":"a"}]})
  self.assertEqual(retry["state"],"RETRY_REQUIRED")
  indeterminate=apply_bound("record_final_challenge",{"current_seal":"seal-1","attempts":[{"status":"FAILED","target_seal":"seal-1","source_finding_ids":[],"artifact_id":"a"},{"status":"FAILED","target_seal":"seal-1","source_finding_ids":[],"artifact_id":"b"}]})
  self.assertEqual(indeterminate["state"],"INDETERMINATE")
  stale=apply_bound("record_final_challenge",{"current_seal":"seal-1","attempts":[{"status":"UPHOLD","target_seal":"old","source_finding_ids":[],"artifact_id":"a"}]})
  self.assertEqual(stale["state"],"STALE")
