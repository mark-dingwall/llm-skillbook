import ast
import importlib
import unittest
from pathlib import Path


class StateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.process = importlib.import_module("review_loop").process

    def assert_invalid(self, request: object, path: str, code: str) -> None:
        response = self.process(request)
        self.assertEqual(response["schema_version"], 1)
        self.assertIs(response["ok"], False)
        self.assertNotIn("result", response)
        self.assertIn((path, code), [(item["path"], item["code"]) for item in response["errors"]])

    def test_rejects_non_object_request(self) -> None:
        self.assert_invalid([], "$", "type")

    def test_rejects_missing_envelope_fields(self) -> None:
        response = self.process({})
        self.assertEqual(
            [(issue["path"], issue["code"]) for issue in response["errors"]],
            [
                ("$.input", "missing"),
                ("$.operation", "missing"),
                ("$.schema_version", "missing"),
            ],
        )

    def test_rejects_unknown_envelope_fields(self) -> None:
        self.assert_invalid(
            {"schema_version": 1, "operation": "none", "input": {}, "extra": 1},
            "$.extra",
            "unknown",
        )

    def test_rejects_unsupported_schema_version(self) -> None:
        self.assert_invalid(
            {"schema_version": 2, "operation": "none", "input": {}},
            "$.schema_version",
            "unsupported",
        )

    def test_rejects_unknown_operation(self) -> None:
        self.assert_invalid(
            {"schema_version": 1, "operation": "none", "input": {}},
            "$.operation",
            "unknown",
        )

    def test_errors_are_sorted_by_path_then_code(self) -> None:
        response = self.process({"z": True})
        pairs = [(issue["path"], issue["code"]) for issue in response["errors"]]
        self.assertEqual(pairs, sorted(pairs))


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_production_modules_do_not_import_target_or_process_access(self) -> None:
        package = Path(__file__).parents[2] / "review_loop"
        modules = sorted(package.glob("*.py"))
        self.assertTrue(modules, "production package must exist")
        forbidden = {"os", "pathlib", "subprocess", "socket", "urllib", "multi_review"}
        found: list[str] = []
        for module in modules:
            tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".", 1)[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".", 1)[0]]
                else:
                    names = []
                for name in names:
                    if name in forbidden:
                        found.append(f"{module.name}:{name}")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
