import unittest
from tests.contract.helpers import apply_bound
class PolicyTests(unittest.TestCase):
 def test_compact_ratings_derive_max(self):
  result=apply_bound("derive_policy",{"explicit_tier":None,"no_confirm":False,"ratings":[{"complexity":"high","risk":"high","gestalt_step":False},{"complexity":"low","risk":"low","gestalt_step":False}]})
  self.assertEqual(result["tier"],"max")
