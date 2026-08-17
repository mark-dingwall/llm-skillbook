import unittest
from tests.contract.helpers import apply_bound
class LedgerTests(unittest.TestCase):
 def test_settlement_requires_artifact_proof_not_claim_text(self):
  result=apply_bound("apply_ledger_decisions",{"target_seal":"seal-1","rows":[{"id":"F1","source_ids":["raw-1"],"reported_severity":"Important","current_severity":"Important","factual":"CONFIRMED","state":"FIX_VERIFIED","proof_artifact_ids":["proof-1"],"manifest_artifact_id":"fix-1","target_seal":"seal-1"}]})
  self.assertEqual(result["pending_fix_ids"],[])
