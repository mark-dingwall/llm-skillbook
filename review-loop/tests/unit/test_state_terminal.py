import unittest
from tests.contract.helpers import apply_bound
class TerminalTests(unittest.TestCase):
 def test_terminal_uses_compact_rollups(self):
  result=apply_bound("compute_terminal",{"lifecycle":{"any_indeterminate":False},"ledger":[],"gates":{"blocking_reasons":[]},"areas":[],"final_challenge":{"state":"UPHELD"}})
  self.assertTrue(result["merge_ready"])
