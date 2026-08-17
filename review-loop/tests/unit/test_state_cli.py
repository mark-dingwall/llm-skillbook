import json, os, subprocess, sys, unittest
from tests.contract.helpers import bound_transition_fixture
class StateCliTests(unittest.TestCase):
 def test_test_only_cli_requires_canonical_snapshot_and_envelope(self):
  snapshot,_,envelope=bound_transition_fixture(kind="rating",schema_version=1,target_seal="seal-a",operation="derive_policy",source_ids=("rater",),raw_bytes=b"{}",projection={"explicit_tier":"low","no_confirm":False,"ratings":[]})
  request={"snapshot":snapshot,"envelope":{"operation":envelope.operation,"artifact_refs":[ref.__dict__ for ref in envelope.artifact_refs],"projection":envelope.projection,"expected_governing_seal":envelope.expected_governing_seal}}
  env=dict(os.environ);env["PYTHONPATH"]="review-loop"
  done=subprocess.run([sys.executable,"-m","review_loop","--test-fixture"],input=json.dumps(request),text=True,capture_output=True,env=env)
  self.assertEqual(done.returncode,0); self.assertEqual(json.loads(done.stdout)["result"]["processor_state"]["derive_policy"]["tier"],"low")
