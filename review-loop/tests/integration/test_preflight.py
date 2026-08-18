import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from review_loop.controller import (
    Controller,
    ControllerError,
    PreflightError,
    ProfileConfirmationRequired,
    RunState,
)
from review_loop.profiles import InvocationIntent
from review_loop.artifacts import CanonicalStore
from review_loop.seals import SealError


def run_git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def init_repo(root):
    run_git(root, "init", "-q")
    run_git(root, "config", "user.email", "test@example.com")
    run_git(root, "config", "user.name", "Test")


def write_profile(xdg, name, text):
    path = xdg / "review-loop" / "profiles" / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "target"
        self.target.mkdir()
        init_repo(self.target)
        (self.target / "a.txt").write_bytes(b"hello")
        run_git(self.target, "add", "a.txt")
        run_git(self.target, "commit", "-q", "-m", "initial")
        self.run_root = self.root / "runs" / "1"
        self.xdg = self.root / "xdg"
        self.ground_truth = self.target.parent / "ground-truth.md"
        self.ground_truth.write_bytes(b"authority")

    def intent(self, **overrides):
        base = dict(
            target=self.target,
            base="HEAD",
            head=None,
            exclusions=(),
            review_profile=None,
            max_time_seconds=None,
            no_confirm=False,
            ground_truth=(self.ground_truth,),
            run_root=self.run_root,
        )
        base.update(overrides)
        return InvocationIntent(**base)

    def test_persists_preflight_atomically_before_dispatch(self):
        controller = Controller(xdg_config_home=self.xdg)
        state = controller.create_run(self.intent())
        self.assertIsInstance(state, RunState)
        state_path = self.run_root / "review-state.json"
        self.assertTrue(state_path.exists())
        # no leftover temp file from the atomic replace
        self.assertEqual(list(self.run_root.glob(".*.tmp")), [])
        preflight = state.snapshot["processor_state"]["preflight"]
        for key in (
            "invocation_intent",
            "resolved_target",
            "resolved_base",
            "resolved_exclusions",
            "run_root",
            "ground_truth",
            "target_seal",
            "delta_policy",
            "selected_profile",
            "start_time",
            "absolute_expiry",
        ):
            self.assertIn(key, preflight)
        self.assertEqual(preflight["ground_truth"][0]["path"], str(self.ground_truth))
        self.assertEqual(preflight["target_seal"]["digest"], state.governing_seal)
        self.assertIsNone(preflight["selected_profile"])
        self.assertIsNone(preflight["absolute_expiry"])

    def test_governing_seal_matches_target_seal_digest(self):
        controller = Controller(xdg_config_home=self.xdg)
        state = controller.create_run(self.intent())
        self.assertEqual(state.snapshot["governing_seal"], state.governing_seal)

    def test_max_time_seconds_sets_absolute_expiry(self):
        controller = Controller(xdg_config_home=self.xdg)
        state = controller.create_run(self.intent(max_time_seconds=60))
        preflight = state.snapshot["processor_state"]["preflight"]
        self.assertIsNotNone(preflight["absolute_expiry"])

    def test_run_root_overlapping_target_is_rejected_before_any_write(self):
        controller = Controller(xdg_config_home=self.xdg)
        with self.assertRaises(SealError):
            controller.create_run(self.intent(run_root=self.target / "runs"))
        self.assertFalse((self.target / "runs").exists())

    def test_absent_base_rejects_the_target(self):
        controller = Controller(xdg_config_home=self.xdg)
        with self.assertRaises(SealError):
            controller.create_run(self.intent(base=None))
        self.assertFalse(self.run_root.exists())

    def test_non_git_target_is_rejected(self):
        plain = self.root / "plain"
        plain.mkdir()
        controller = Controller(xdg_config_home=self.xdg)
        with self.assertRaises(PreflightError):
            controller.create_run(self.intent(target=plain))

    def test_valid_explicit_profile_is_persisted(self):
        write_profile(self.xdg, "mine", "version: 1\nmax_time_seconds: 900\n")
        controller = Controller(xdg_config_home=self.xdg)
        state = controller.create_run(self.intent(review_profile="mine"))
        preflight = state.snapshot["processor_state"]["preflight"]
        self.assertEqual(preflight["selected_profile"]["max_time_seconds"], 900)
        self.assertIsNotNone(preflight["absolute_expiry"])

    def test_invalid_explicit_profile_without_confirmation_raises(self):
        controller = Controller(xdg_config_home=self.xdg)
        with self.assertRaises(ProfileConfirmationRequired):
            controller.create_run(self.intent(review_profile="does-not-exist"))
        self.assertFalse(self.run_root.exists())

    def test_invalid_explicit_profile_declined_confirmation_raises(self):
        controller = Controller(xdg_config_home=self.xdg)
        with self.assertRaises(ProfileConfirmationRequired):
            controller.create_run(
                self.intent(review_profile="does-not-exist"),
                confirm_tier_defaults=lambda reason: False,
            )
        self.assertFalse(self.run_root.exists())

    def test_invalid_explicit_profile_confirmed_proceeds_with_tier_defaults(self):
        controller = Controller(xdg_config_home=self.xdg)
        asked = []

        def confirm(reason):
            asked.append(reason)
            return True

        state = controller.create_run(
            self.intent(review_profile="does-not-exist"),
            confirm_tier_defaults=confirm,
        )
        self.assertTrue(asked)
        preflight = state.snapshot["processor_state"]["preflight"]
        self.assertIsNone(preflight["selected_profile"])

    def test_no_reviewer_dispatch_processor_state_has_only_preflight(self):
        controller = Controller(xdg_config_home=self.xdg)
        state = controller.create_run(self.intent())
        self.assertEqual(set(state.snapshot["processor_state"]), {"preflight"})

    def _assert_stage0_stops_before_dispatch(self, state):
        def dispatched(*_args, **_kwargs):
            self.fail("expired or drifted input must stop before semantic dispatch")

        with self.assertRaises(ControllerError):
            self.controller.run_stage0(
                state, scout=dispatched, gate_dispatch=dispatched,
                inventory_owner=dispatched, inventory_challenger=dispatched,
                explicit_tier="low",
            )

    def test_ground_truth_drift_stops_before_stage0_dispatch(self):
        self.controller = Controller(xdg_config_home=self.xdg)
        state = self.controller.create_run(self.intent())
        self.ground_truth.write_text("changed authority")
        self._assert_stage0_stops_before_dispatch(state)

    def test_expired_deadline_stops_before_stage0_dispatch(self):
        self.controller = Controller(xdg_config_home=self.xdg)
        state = self.controller.create_run(self.intent(max_time_seconds=60))
        snapshot = deepcopy(state.snapshot)
        snapshot["processor_state"]["preflight"]["absolute_expiry"] = "2000-01-01T00:00:00+00:00"
        store = CanonicalStore(self.run_root)
        store._replace(snapshot)
        expired = RunState(state.run_root, state.governing_seal, snapshot)
        self._assert_stage0_stops_before_dispatch(expired)


if __name__ == "__main__":
    unittest.main()
