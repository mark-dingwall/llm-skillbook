import ast
import unittest
from pathlib import Path
class StateContractTests(unittest.TestCase):
 def test_kernel_has_no_target_access_or_legacy_fixture_adapter(self):
  text=(Path(__file__).parents[2]/"review_loop"/"state.py").read_text()
  self.assertNotIn("process_test_fixture",text)
  tree=ast.parse(text)
  self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) and "pathlib" in ast.dump(n) for n in ast.walk(tree)))
