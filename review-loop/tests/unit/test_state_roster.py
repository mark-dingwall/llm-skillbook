import unittest
from tests.contract.helpers import apply_bound
class RosterTests(unittest.TestCase):
 def test_roster_contains_only_specialist_area_id(self):
  area={"id":"area","consequence":"Critical","generalist_miss":True,"owning_file_ids":["file-1"],"coverage":{"status":"STALE","report_artifact_id":None,"seal":None,"owning_file_ids":[]}}
  result=apply_bound("plan_roster",{"tier":"low","areas":[area],"priority_order":["area"],"capacity":3})
  self.assertIn({"role":"specialist","area_id":"area"},result["roster"])
