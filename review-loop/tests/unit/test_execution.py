import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from review_loop.execution import (
    CallRequest,
    CallStarted,
    CodexHostPaths,
    ExecutionError,
    ExecutionMapping,
    Executor,
    TerminationProof,
    build_codex_call,
    default_capacity,
    load_call_started,
    resolve_codex_host_paths,
)
from review_loop.seals import SealEntry

FAKE_REVIEWER = (
    Path(__file__).resolve().parent.parent / "integration" / "fixtures" / "fake_reviewer.py"
)


def fake_builder(request, call_dir):
    call_dir.mkdir(parents=True, exist_ok=True)
    report_dir = call_dir / "report"
    scratch_dir = call_dir / "scratch"
    report_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.md"
    argv = [sys.executable, str(FAKE_REVIEWER), "--output-last-message", str(report_path)]
    mapping = ExecutionMapping((), (), (), report_dir, scratch_dir, False, ())
    return argv, {}, mapping


def request(call_id="call-1", directive=None, run_root=None):
    return CallRequest(
        call_id=call_id,
        role="holistic",
        target_root=Path("/nonexistent"),
        target_entries=(),
        input_paths=(),
        run_root=run_root,
        prompt=json.dumps(directive) if directive is not None else "plain prompt text",
    )


class ExecutorLifecycleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_root = Path(self._tmp.name)
        self.executor = Executor(fake_builder, term_grace_seconds=1, kill_grace_seconds=1)

    def test_start_persists_call_started_before_returning(self):
        req = request(run_root=self.run_root)
        started = self.executor.start(req)
        self.assertIsInstance(started, CallStarted)
        record_path = self.run_root / "calls" / req.call_id / "call_started.json"
        self.assertTrue(record_path.exists())
        recovered = load_call_started(record_path)
        self.assertEqual(recovered.call_id, req.call_id)
        self.assertEqual(recovered.pid, started.pid)
        self.executor.finish(started)

    def test_finish_completed_publishes_report(self):
        req = request(directive={"exit_code": 0}, run_root=self.run_root)
        started = self.executor.start(req)
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "COMPLETED")
        self.assertIsNotNone(completion.report_text)
        self.assertTrue(completion.report_path.exists())

    def test_finish_nonzero_exit_is_failed_never_reads_report(self):
        req = request(directive={"exit_code": 3}, run_root=self.run_root)
        started = self.executor.start(req)
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "FAILED")
        self.assertEqual(completion.reason, "nonzero_exit:3")
        self.assertIsNone(completion.report_text)

    def test_finish_missing_report_is_failed(self):
        # The fake builder only writes a report when --output-last-message is
        # honored; a directive with a bogus results_path still exits 0 but a
        # process that never touches the report file must fail validation.
        def no_report_builder(req, call_dir):
            call_dir.mkdir(parents=True, exist_ok=True)
            report_dir = call_dir / "report"
            scratch_dir = call_dir / "scratch"
            report_dir.mkdir(parents=True, exist_ok=True)
            scratch_dir.mkdir(parents=True, exist_ok=True)
            argv = [sys.executable, str(FAKE_REVIEWER)]  # no --output-last-message
            mapping = ExecutionMapping((), (), (), report_dir, scratch_dir, False, ())
            return argv, {}, mapping

        executor = Executor(no_report_builder, term_grace_seconds=1, kill_grace_seconds=1)
        req = request(directive={"exit_code": 0}, run_root=self.run_root)
        started = executor.start(req)
        completion = executor.finish(started)
        self.assertEqual(completion.outcome, "FAILED")
        self.assertEqual(completion.reason, "invalid_report")

    def test_finish_raises_when_post_call_seal_check_fails(self):
        def boom():
            raise ExecutionError("post-call target seal mismatch")

        req = CallRequest(
            call_id="c",
            role="holistic",
            target_root=Path("/nonexistent"),
            target_entries=(),
            input_paths=(),
            run_root=self.run_root,
            prompt=json.dumps({"exit_code": 0}),
            verify_target_unchanged=boom,
        )
        started = self.executor.start(req)
        with self.assertRaises(ExecutionError):
            self.executor.finish(started)

    def test_finish_unknown_call_raises(self):
        fake_started = CallStarted("nope", "holistic", "t", 999999, Path("/x"), Path("/x"))
        with self.assertRaises(ExecutionError):
            self.executor.finish(fake_started)

    def test_finish_deadline_expired_terminates_and_marks_indeterminate(self):
        req = request(directive={"sleep_seconds": 5, "exit_code": 0}, run_root=self.run_root)
        started = self.executor.start(req)
        deadline = datetime.now(timezone.utc) + timedelta(milliseconds=50)
        completion = self.executor.finish(started, deadline=deadline)
        self.assertEqual(completion.outcome, "INDETERMINATE")
        self.assertEqual(completion.reason, "deadline_expired")
        self.assertIsNone(completion.report_text)

    def test_terminate_live_process_is_proven(self):
        req = request(directive={"sleep_seconds": 30}, run_root=self.run_root)
        started = self.executor.start(req)
        proof = self.executor.terminate(started)
        self.assertIsInstance(proof, TerminationProof)
        self.assertTrue(proof.proven)
        self.assertIn(proof.method, ("term", "kill"))

    def test_terminate_unprovable_when_process_never_dies(self):
        class StubProc:
            pid = 424242
            stdin = None

            def terminate(self):
                pass

            def kill(self):
                pass

            def wait(self, timeout=None):
                raise subprocess.TimeoutExpired(cmd="stub", timeout=timeout)

        def stub_popen(*args, **kwargs):
            return StubProc()

        executor = Executor(fake_builder, popen=stub_popen, term_grace_seconds=0.05, kill_grace_seconds=0.05)
        req = request(run_root=self.run_root)
        started = executor.start(req)
        proof = executor.terminate(started)
        self.assertFalse(proof.proven)
        self.assertEqual(proof.method, "unprovable")


class RecoveryTerminationTests(unittest.TestCase):
    """A recovered CallStarted (not launched by this Executor instance) can
    never be waitpid-reaped -- proof relies purely on signal + liveness
    polling, matching the recovery path in the design."""

    def setUp(self):
        self.executor = Executor(fake_builder, recovery_poll_attempts=3, recovery_poll_interval=0.01)
        self.started = CallStarted("recovered-1", "holistic", "t", 12345, Path("/x/report.md"), Path("/x"))

    def test_already_gone_pid_is_proven(self):
        def kill_fn(pid, sig):
            raise ProcessLookupError()

        self.executor._kill_fn = kill_fn
        proof = self.executor.terminate(self.started)
        self.assertTrue(proof.proven)
        self.assertEqual(proof.method, "already_gone")

    def test_pid_that_dies_after_signal_is_proven(self):
        calls = {"n": 0}

        def kill_fn(pid, sig):
            calls["n"] += 1

        def probe_alive(pid):
            return calls["n"] < 2  # alive until the second poll

        self.executor._kill_fn = kill_fn
        self.executor._probe_alive_fn = probe_alive
        proof = self.executor.terminate(self.started)
        self.assertTrue(proof.proven)

    def test_pid_that_never_dies_is_unprovable_and_indeterminate(self):
        self.executor._kill_fn = lambda pid, sig: None
        self.executor._probe_alive_fn = lambda pid: True
        proof = self.executor.terminate(self.started)
        self.assertFalse(proof.proven)
        self.assertEqual(proof.method, "unprovable")


class CapacityTests(unittest.TestCase):
    def test_advertised_capacity_is_used_directly(self):
        self.assertEqual(default_capacity(4), 4)

    def test_advertised_non_positive_capacity_rejected(self):
        with self.assertRaises(ExecutionError):
            default_capacity(0)

    def test_conservative_default_when_host_does_not_advertise(self):
        with mock.patch("os.cpu_count", return_value=None):
            self.assertEqual(default_capacity(None), 1)

    def test_falls_back_to_cpu_count_when_no_advertisement(self):
        with mock.patch("os.cpu_count", return_value=7):
            self.assertEqual(default_capacity(None), 7)


class RunWavesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_root = Path(self._tmp.name)
        self.launch_count = {"n": 0}

        def counting_builder(req, call_dir):
            self.launch_count["n"] += 1
            return fake_builder(req, call_dir)

        self.executor = Executor(counting_builder, term_grace_seconds=1, kill_grace_seconds=1)

    def _requests(self, n, **kw):
        return [request(call_id=f"c{i}", run_root=self.run_root, **kw) for i in range(n)]

    def test_complete_roster_scheduled_no_omission(self):
        reqs = self._requests(5, directive={"exit_code": 0})
        completions = self.executor.run_waves(reqs, capacity=2, expiry=None)
        self.assertEqual(len(completions), 5)
        self.assertEqual({c.call_id for c in completions}, {r.call_id for r in reqs})
        self.assertTrue(all(c.outcome == "COMPLETED" for c in completions))
        self.assertEqual(self.launch_count["n"], 5)

    def test_capacity_of_less_than_one_is_clamped_to_one(self):
        reqs = self._requests(2, directive={"exit_code": 0})
        completions = self.executor.run_waves(reqs, capacity=0, expiry=None)
        self.assertEqual(len(completions), 2)

    def test_deadline_already_past_dispatches_nothing(self):
        reqs = self._requests(3, directive={"exit_code": 0})
        expiry = datetime.now(timezone.utc) - timedelta(seconds=1)
        completions = self.executor.run_waves(reqs, capacity=2, expiry=expiry)
        self.assertEqual(len(completions), 3)
        self.assertTrue(all(c.outcome == "INDETERMINATE" for c in completions))
        self.assertTrue(all(c.reason == "deadline_expired_before_launch" for c in completions))
        self.assertEqual(self.launch_count["n"], 0)

    def test_deadline_expiring_mid_roster_stops_further_launches(self):
        reqs = [
            request(call_id="slow", run_root=self.run_root, directive={"sleep_seconds": 0.5, "exit_code": 0}),
            request(call_id="never-launched-1", run_root=self.run_root, directive={"exit_code": 0}),
            request(call_id="never-launched-2", run_root=self.run_root, directive={"exit_code": 0}),
        ]
        expiry = datetime.now(timezone.utc) + timedelta(milliseconds=200)
        completions = self.executor.run_waves(reqs, capacity=1, expiry=expiry)
        self.assertEqual(len(completions), 3)
        by_id = {c.call_id: c for c in completions}
        self.assertEqual(by_id["slow"].outcome, "INDETERMINATE")
        self.assertEqual(by_id["slow"].reason, "deadline_expired")
        self.assertEqual(by_id["never-launched-1"].reason, "deadline_expired_before_launch")
        self.assertEqual(by_id["never-launched-2"].reason, "deadline_expired_before_launch")
        # no retry/harvest: the slow call was only ever launched once
        self.assertEqual(self.launch_count["n"], 1)

    def test_no_completion_ever_carries_partial_output(self):
        reqs = self._requests(2, directive={"exit_code": 5})
        completions = self.executor.run_waves(reqs, capacity=2, expiry=None)
        self.assertTrue(all(c.report_text is None for c in completions))


class CodexHostPathResolutionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        # stand-in executables so `.exists()`/`.is_file()` checks pass without
        # touching any real host tool
        self.bwrap = self.root / "bwrap"
        self.node = self.root / "node"
        self.codex_bin = self.root / "codex"
        for p in (self.bwrap, self.node, self.codex_bin):
            p.write_bytes(b"")

    def _which(self, mapping):
        return lambda name: mapping.get(name)

    def test_missing_bwrap_fails_closed(self):
        which = self._which({"node": str(self.node), "codex": str(self.codex_bin)})
        with mock.patch("shutil.which", side_effect=which):
            with self.assertRaises(ExecutionError):
                resolve_codex_host_paths(codex_home=self.codex_home)

    def test_missing_auth_file_fails_closed(self):
        which = self._which({"bwrap": str(self.bwrap), "node": str(self.node), "codex": str(self.codex_bin)})
        with mock.patch("shutil.which", side_effect=which):
            with self.assertRaises(ExecutionError):
                resolve_codex_host_paths(codex_home=self.codex_home)  # auth.json absent

    def test_all_prerequisites_present_resolves(self):
        # Relies on this dev host actually having /etc/resolv.conf,
        # /etc/nsswitch.conf, and a CA bundle -- confirmed present in the
        # verified environment; only the tool paths are faked.
        (self.codex_home / "auth.json").write_bytes(b"{}")
        which = self._which({"bwrap": str(self.bwrap), "node": str(self.node), "codex": str(self.codex_bin)})
        with mock.patch("shutil.which", side_effect=which):
            host = resolve_codex_host_paths(codex_home=self.codex_home)
        self.assertEqual(host.auth_file, self.codex_home / "auth.json")
        self.assertEqual(host.codex_package_root, self.codex_bin.resolve().parent.parent)


class CodexMappingArgvTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target_root = self.root / "target"
        self.target_root.mkdir()
        (self.target_root / "a.py").write_bytes(b"x")
        self.host = CodexHostPaths(
            bwrap=Path("/usr/bin/bwrap"),
            node=Path("/usr/bin/node"),
            codex_package_root=self.root / "pkg",
            codex_entry=self.root / "pkg" / "bin" / "codex.js",
            auth_file=self.root / "codex-home" / "auth.json",
            resolv_conf=Path("/etc/resolv.conf"),
            nsswitch_conf=Path("/etc/nsswitch.conf"),
            ca_certificates=Path("/etc/ssl/certs/ca-certificates.crt"),
        )
        self.call_dir = self.root / "run" / "calls" / "call-1"

    def _request(self, **overrides):
        base = dict(
            call_id="call-1",
            role="holistic",
            target_root=self.target_root,
            target_entries=(SealEntry("a.py", "file", 0o644, "deadbeef"),),
            input_paths=(),
            run_root=self.root / "run",
            prompt="ignored",
        )
        base.update(overrides)
        return CallRequest(**base)

    def test_fixed_outer_flags_present(self):
        argv, env, mapping = build_codex_call(self._request(), self.host, self.call_dir)
        self.assertIn("--clearenv", argv)
        self.assertIn("--unshare-pid", argv)
        self.assertIn("--die-with-parent", argv)

    def test_env_allowlist_is_exactly_four_names(self):
        argv, env, mapping = build_codex_call(self._request(), self.host, self.call_dir)
        self.assertEqual(set(env), {"HOME", "CODEX_HOME", "PATH", "LANG"})
        # every --setenv pair in argv must be one of the allowed names
        setenv_names = [argv[i + 1] for i, a in enumerate(argv) if a == "--setenv"]
        self.assertEqual(set(setenv_names), {"HOME", "CODEX_HOME", "PATH", "LANG"})

    def test_auth_file_bound_read_only_no_host_config_or_rules(self):
        argv, env, mapping = build_codex_call(self._request(), self.host, self.call_dir)
        ro_pairs = [(argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == "--ro-bind"]
        self.assertIn((str(self.host.auth_file), "/home/reviewer/.codex/auth.json"), ro_pairs)
        for src, _dst in ro_pairs:
            self.assertNotIn("config.toml", src)
            self.assertNotIn("hooks.json", src)
            self.assertNotIn("/rules", src)
            self.assertNotIn("session", src)
        self.assertIn(self.host.auth_file, mapping.credentials)

    def test_target_bound_by_exact_entry_not_whole_directory(self):
        argv, env, mapping = build_codex_call(self._request(), self.host, self.call_dir)
        ro_pairs = [(argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == "--ro-bind"]
        self.assertIn((str(self.target_root / "a.py"), "/subject/a.py"), ro_pairs)
        self.assertNotIn((str(self.target_root), "/subject"), ro_pairs)
        dir_dests = [argv[i + 1] for i, a in enumerate(argv) if a == "--dir"]
        self.assertIn("/subject", dir_dests)  # synthetic empty /subject created first

    def test_input_paths_bound_read_only_under_inputs(self):
        gt = self.root / "ground-truth.md"
        gt.write_bytes(b"truth")
        argv, env, mapping = build_codex_call(self._request(input_paths=(gt,)), self.host, self.call_dir)
        ro_pairs = [(argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == "--ro-bind"]
        self.assertIn((str(gt), "/inputs/0/ground-truth.md"), ro_pairs)
        self.assertIn(gt, mapping.inputs_ro)

    def test_model_flag_appended_only_when_pinned(self):
        argv_no_model, _, _ = build_codex_call(self._request(), self.host, self.call_dir)
        self.assertNotIn("--model", argv_no_model)
        argv_model, _, _ = build_codex_call(self._request(model="gpt-5-pinned"), self.host, self.call_dir)
        self.assertIn("--model", argv_model)
        i = argv_model.index("--model")
        self.assertEqual(argv_model[i + 1], "gpt-5-pinned")
        self.assertEqual(argv_model[-1], "-")  # stdin marker always trails

    def test_exact_ordinary_backend_flags(self):
        argv, _, _ = build_codex_call(self._request(), self.host, self.call_dir)
        inner = argv[argv.index(str(self.host.node)):]
        self.assertEqual(
            inner,
            [
                str(self.host.node),
                str(self.host.codex_entry),
                "exec",
                "--sandbox", "read-only",
                "--ignore-user-config",
                "--ignore-rules",
                "--ephemeral",
                "--skip-git-repo-check",
                "--json",
                "--output-last-message", "/report/report.md",
                "-C", "/subject",
                "-",
            ],
        )

    def test_escaping_target_entry_rejected(self):
        bad = self._request(target_entries=(SealEntry("../outside.py", "file", 0o644, "d"),))
        with self.assertRaises(ExecutionError):
            build_codex_call(bad, self.host, self.call_dir)

    def test_empty_directory_entry_uses_dir_not_ro_bind(self):
        req = self._request(target_entries=(SealEntry("emptydir", "dir", 0o755, None),))
        argv, _, _ = build_codex_call(req, self.host, self.call_dir)
        self.assertIn("/subject/emptydir", argv)
        dir_dests = [argv[i + 1] for i, a in enumerate(argv) if a == "--dir"]
        self.assertIn("/subject/emptydir", dir_dests)


if __name__ == "__main__":
    unittest.main()
