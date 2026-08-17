import unittest
from tests.contract.helpers import apply_bound
class PolicyTests(unittest.TestCase):
 def test_each_fixed_policy_is_independent(self):
  expected={"low":(2,"mid-tier","Critical",[]),"med":(3,"mid-tier","Important",[]),"high":(5,"one-above-mid","Important",[1]),"max":(5,"most-capable","every",[1,2])}
  for tier,values in expected.items():
   value=apply_bound("derive_policy",{"explicit_tier":tier,"no_confirm":False,"ratings":[]}); self.assertEqual((value["round_cap"],value["normal_capability"],value["specialist_threshold"],value["multi_review_rounds"]),values)
  first=apply_bound("derive_policy",{"explicit_tier":"max","no_confirm":False,"ratings":[]}); first["multi_review_rounds"].append(99)
  self.assertEqual(apply_bound("derive_policy",{"explicit_tier":"max","no_confirm":False,"ratings":[]})["multi_review_rounds"],[1,2])
 def test_compact_ratings_derive_max(self):
  result=apply_bound("derive_policy",{"explicit_tier":None,"no_confirm":False,"ratings":[{"complexity":"high","risk":"high","gestalt_step":False},{"complexity":"low","risk":"low","gestalt_step":False}]})
  self.assertEqual(result["tier"],"max")
