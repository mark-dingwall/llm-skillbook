"""Black-box tests for the production `review_loop.__main__` CLI surface.

Exercises the entry point exactly as a host would: `python3 -m review_loop
<subcommand>`, JSON in on stdin (or flags), JSON out on stdout. Covers the
brief's required assertions: explicit/automatic tier intent, no-confirm
semantics, profile/deadline intent, status recovery, the final report path,
invalid operator input rejection, and -- most importantly -- that no
production subcommand accepts a caller-authored projection/registry
(the authority-bypass the design forbids). The pre-existing `--test-fixture`
pure-processor path is exercised separately in tests/unit/test_state_cli.py
and stays exactly as narrow as before.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENV = dict(os.environ)
ENV["PYTHONPATH"] = "review-loop"


def run_git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def init_repo(root):
    run_git(root, "init", "-q")
    run_git(root, "config", "user.email", "test@example.com")
    run_git(root, "config", "user.name", "Test")
    (root / "a.txt").write_bytes(b"hello")
    run_git(root, "add", "a.txt")
    run_git(root, "commit", "-q", "-m", "initial")


def cli(*args, request=None, env=None):
    stdin = json.dumps(request) if request is not None else ""
    done = subprocess.run(
        [sys.executable, "-m", "review_loop", *args],
        input=stdin, text=True, capture_output=True, env=env or ENV,
    )
    try:
        payload = json.loads(done.stdout) if done.stdout.strip() else None
    except json.JSONDecodeError:
        payload = None
    return done.returncode, payload, done.stderr


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "target"
        self.target.mkdir()
        init_repo(self.target)
        self.run_root = self.root / "run"

    def create(self, env=None, **overrides):
        request = {"target": str(self.target), "base": "HEAD", "run_root": str(self.run_root)}
        request.update(overrides)
        return cli("create-run", request=request, env=env)

    # --- explicit vs. automatic tier intent -----------------------------

    def test_explicit_tier_is_recorded_verbatim(self):
        code, payload, _ = self.create(tier="high")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["resolved"]["tier"], "high")

    def test_omitted_tier_means_automatic_and_is_never_invented(self):
        code, payload, _ = self.create()
        self.assertEqual(code, 0, payload)
        self.assertIsNone(payload["resolved"]["tier"])

    def test_invalid_tier_value_is_rejected(self):
        code, payload, _ = self.create(tier="ultra")
        self.assertNotEqual(code, 0)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "invalid_tier")
        self.assertFalse(self.run_root.exists())

    # --- no-confirm semantics --------------------------------------------

    def test_no_confirm_true_round_trips(self):
        code, payload, _ = self.create(no_confirm=True)
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["resolved"]["no_confirm"])

    def test_no_confirm_defaults_false(self):
        code, payload, _ = self.create()
        self.assertEqual(code, 0, payload)
        self.assertFalse(payload["resolved"]["no_confirm"])

    def test_no_confirm_invalid_type_is_rejected(self):
        code, payload, _ = self.create(no_confirm="yes")
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "invalid_no_confirm")

    # --- profile / deadline intent ---------------------------------------

    def test_valid_profile_and_deadline_are_resolved(self):
        xdg = self.root / "xdg"
        (xdg / "review-loop" / "profiles").mkdir(parents=True)
        (xdg / "review-loop" / "profiles" / "mine.yaml").write_text("version: 1\nmax_time_seconds: 900\n")
        env = dict(ENV)
        env["XDG_CONFIG_HOME"] = str(xdg)
        code, payload, _ = self.create(review_profile="mine", env=env)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["resolved"]["selected_profile"]["max_time_seconds"], 900)
        self.assertIsNotNone(payload["resolved"]["absolute_expiry"])

    def test_missing_profile_stops_closed_never_falls_back_silently(self):
        env = dict(ENV)
        env["XDG_CONFIG_HOME"] = str(self.root / "empty-xdg")
        code, payload, _ = self.create(review_profile="does-not-exist", env=env)
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "profile_confirmation_required")
        self.assertFalse(self.run_root.exists())

    def test_max_time_seconds_sets_deadline(self):
        code, payload, _ = self.create(max_time_seconds=60)
        self.assertEqual(code, 0, payload)
        self.assertIsNotNone(payload["resolved"]["absolute_expiry"])

    def test_non_positive_max_time_seconds_is_rejected(self):
        code, payload, _ = self.create(max_time_seconds=0)
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "invalid_max_time_seconds")

    # --- status recovery ---------------------------------------------------

    def test_status_reports_preflight_stage_after_create_run(self):
        code, created, _ = self.create()
        self.assertEqual(code, 0, created)
        code, payload, _ = cli("status", "--run-root", str(self.run_root))
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["stage"], "PREFLIGHT")
        self.assertEqual(payload["governing_seal"], created["governing_seal"])

    def test_status_on_absent_run_is_rejected(self):
        code, payload, _ = cli("status", "--run-root", str(self.root / "no-such-run"))
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "no_such_run")

    # --- final report path --------------------------------------------------

    def test_report_writes_markdown_and_prints_its_path(self):
        code, created, _ = self.create()
        self.assertEqual(code, 0, created)
        code, payload, _ = cli("report", "--run-root", str(self.run_root))
        self.assertEqual(code, 0, payload)
        report_path = Path(payload["report_path"])
        self.assertTrue(report_path.is_file())
        text = report_path.read_text()
        self.assertIn("# Review Loop Report", text)
        self.assertIn("PREFLIGHT", text)

    def test_report_on_absent_run_is_rejected(self):
        code, payload, _ = cli("report", "--run-root", str(self.root / "no-such-run"))
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "no_such_run")

    # --- invalid operator input rejection -----------------------------------

    def test_missing_target_is_rejected(self):
        code, payload, _ = cli("create-run", request={"run_root": str(self.run_root)})
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "missing_field")

    def test_malformed_json_is_rejected(self):
        done = subprocess.run(
            [sys.executable, "-m", "review_loop", "create-run"],
            input="{not json", text=True, capture_output=True, env=ENV,
        )
        self.assertNotEqual(done.returncode, 0)
        payload = json.loads(done.stdout)
        self.assertEqual(payload["errors"][0]["code"], "invalid_json")

    def test_non_git_target_is_rejected(self):
        plain = self.root / "plain"
        plain.mkdir()
        code, payload, _ = self.create(target=str(plain))
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "preflight_rejected")

    def test_run_root_overlapping_target_is_rejected(self):
        code, payload, _ = self.create(run_root=str(self.target / "runs"))
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "preflight_rejected")
        self.assertFalse((self.target / "runs").exists())

    # --- absence of any caller-authored projection/registry authority ------

    def test_create_run_rejects_a_caller_supplied_snapshot_and_registry(self):
        code, payload, _ = self.create(
            snapshot={"governing_seal": "x", "artifact_registry": {"artifacts": {}, "bindings": []}},
            envelope={"operation": "derive_policy", "artifact_refs": [], "projection": {}, "expected_governing_seal": "x"},
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "unknown_field")
        self.assertFalse(self.run_root.exists())

    def test_create_run_rejects_a_bare_projection_field(self):
        code, payload, _ = self.create(projection={"explicit_tier": "max", "no_confirm": False, "ratings": []})
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["errors"][0]["code"], "unknown_field")

    def test_status_and_report_take_no_request_body_and_cannot_carry_authority(self):
        # status/report accept only --run-root; there is no stdin/body
        # channel through which a caller could hand either a projection or
        # a registry to be trusted as canonical.
        code, _, _ = self.create()
        self.assertEqual(code, 0)
        for sub in ("status", "report"):
            done = subprocess.run(
                [sys.executable, "-m", "review_loop", sub, "--run-root", str(self.run_root),
                 "--not-a-real-flag", "x"],
                capture_output=True, text=True, env=ENV,
            )
            self.assertNotEqual(done.returncode, 0)  # argparse rejects the unknown flag

    # --- "host calls" style: plain flags, no JSON authoring required -------

    def test_host_call_style_flags_equal_json_body(self):
        code, payload, _ = cli(
            "create-run", "--target", str(self.target), "--base", "HEAD",
            "--run-root", str(self.run_root), "--tier", "med", "--no-confirm",
        )
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["resolved"]["tier"], "med")
        self.assertTrue(payload["resolved"]["no_confirm"])

    # --- default run-root derivation ----------------------------------------

    def test_default_run_root_is_derived_under_xdg_state_home(self):
        state_home = self.root / "state"
        env = dict(ENV)
        env["XDG_STATE_HOME"] = str(state_home)
        code, payload, _ = cli(
            "create-run", request={"target": str(self.target), "base": "HEAD"}, env=env,
        )
        self.assertEqual(code, 0, payload)
        run_root = Path(payload["run_root"])
        self.assertTrue(str(run_root).startswith(str(state_home / "review-loop" / "runs")))
        self.assertTrue(run_root.is_dir())


if __name__ == "__main__":
    unittest.main()
