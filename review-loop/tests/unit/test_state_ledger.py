import unittest
from tests.contract.helpers import apply_bound

def row(state="OPEN", manifest=None):
 return {"id":"F1","source_ids":["raw-1"],"reported_severity":"Important","current_severity":"Important","factual":"CONFIRMED","state":state,"proof_artifact_ids":[],"manifest_artifact_id":manifest,"target_seal":"seal-1"}
def decision(state, proof=[], manifest=None): return {"id":"F1","state":state,"proof_artifact_ids":proof,"manifest_artifact_id":manifest}
def run(prior, item, manifests=[], adjudication=None, prior_next=None): return apply_bound("apply_ledger_decisions",{"prior_rows":[prior],"decisions":[item],"manifests":[{"id":value,"finding_id":"F1"} for value in manifests],"target_seal":"seal-1","prior_next_adjudication":prior_next,"adjudication":adjudication})
class LedgerTests(unittest.TestCase):
 def test_open_must_apply_linked_manifest_before_fix_verified(self):
  with self.assertRaises(Exception): run(row(),decision("FIX_VERIFIED",["proof"],"M1"),["M1"],{"attempt":1,"status":"UPHOLD","decided_ids":["F1"],"proof_artifact_id":"adj"})
  applied=run(row(),decision("FIX_APPLIED",[],"M1"),["M1"])
  self.assertEqual(applied["rows"][0]["state"],"FIX_APPLIED")
  verified=run(row("FIX_APPLIED","M1"),decision("FIX_VERIFIED",["proof"],"M1"),["M1"],{"attempt":1,"status":"UPHOLD","decided_ids":["F1"],"proof_artifact_id":"adj"})
  self.assertEqual(verified["rows"][0]["state"],"FIX_VERIFIED")
 def test_first_adjudication_failure_retries_then_second_bounces(self):
  first=run(row(),decision("REFUTED",["proof"]),[],{"attempt":1,"status":"FAILED","decided_ids":[],"proof_artifact_id":None})
  self.assertEqual(first["next_adjudication"],{"attempt":2,"pending_ids":["F1"]})
  with self.assertRaises(Exception): run(row(),decision("REFUTED",["proof"]),[],{"attempt":2,"status":"FAILED","decided_ids":[],"proof_artifact_id":None})
  second=run(row(),decision("REFUTED",["proof"]),[],{"attempt":2,"status":"BOUNCE","decided_ids":["F1"],"proof_artifact_id":"adj-2"},prior_next=first["next_adjudication"])
  self.assertEqual(second["rows"][0]["state"],"OPEN")
