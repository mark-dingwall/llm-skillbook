import json
import os
import subprocess
import sys
import unittest


class StateCliTests(unittest.TestCase):
    def run_cli(self, stdin: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = "review-loop"
        return subprocess.run(
            [sys.executable, "-m", "review_loop"],
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_malformed_json_is_compact_validation_error(self) -> None:
        completed = self.run_cli("{")
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(completed.stdout.count("\n"), 1)
        response = json.loads(completed.stdout)
        self.assertEqual(completed.stdout, json.dumps(response, separators=(",", ":")) + "\n")
        self.assertEqual(response["schema_version"], 1)
        self.assertIs(response["ok"], False)
        self.assertEqual(response["errors"][0]["path"], "$")
        self.assertEqual(response["errors"][0]["code"], "invalid_json")

    def test_invalid_request_exits_two_with_compact_stdout(self) -> None:
        completed = self.run_cli("[]")
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stderr, "")
        response = json.loads(completed.stdout)
        self.assertEqual(completed.stdout, json.dumps(response, separators=(",", ":")) + "\n")
        self.assertIs(response["ok"], False)

    def test_valid_derive_policy_request_exits_zero(self) -> None:
        stdin = json.dumps(
            {
                "schema_version": 1,
                "operation": "derive_policy",
                "input": {"explicit_tier": "low", "no_confirm": False, "raters": []},
            }
        )
        completed = self.run_cli(stdin)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        response = json.loads(completed.stdout)
        self.assertEqual(completed.stdout, json.dumps(response, separators=(",", ":")) + "\n")
        self.assertEqual(response["result"]["tier"], "low")


if __name__ == "__main__":
    unittest.main()
