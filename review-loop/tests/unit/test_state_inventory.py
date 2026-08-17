import unittest
from tests.contract.helpers import apply_bound
STALE={"status":"STALE","report_artifact_id":None,"seal":None,"owning_file_ids":[]}; FLAGS={"surface_changed":False,"dependency_changed":False,"contract_changed":False,"finding_reopened":False,"identity_changed":False,"new_depth_evidence":False}
class InventoryTests(unittest.TestCase):
 def test_refresh_and_coverage_use_compact_ids(self):
  prior={"id":"area","consequence":"Important","generalist_miss":True,"owning_file_ids":["file-1"],"coverage":{"status":"CURRENT","report_artifact_id":"report-1","seal":"seal-1","owning_file_ids":["file-1"]}}; current={"id":"area","consequence":"Minor","generalist_miss":False,"owning_file_ids":["file-1"]}
  result=apply_bound("refresh_inventory",{"prior_areas":[prior],"current_areas":[current],"mappings":[{"prior_id":"area","resolution":"continuing","active_id":"area"}],"priority_order":["area"],"invalidators":{"area":FLAGS}})
  self.assertEqual(result["active_areas"][0]["coverage"]["report_artifact_id"],"report-1")
