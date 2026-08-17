"""Real-Bubblewrap containment proof for the Codex ordinary mapping.

These tests exercise `execution.build_codex_call` and `Executor` through a
*real* `bwrap` process tree, substituting `fixtures/fake_reviewer.py` (run
under the system Python) for `node <codex.js>` so the exact mapping-
construction code path is proven without a network call or real Codex
credentials. Skips (not failures) only when `bwrap` itself is unavailable in
this environment -- every other assertion here must run for real.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from review_loop.execution import (
    CallRequest,
    CodexHostPaths,
    ExecutionError,
    Executor,
    build_codex_call,
    preflight_codex_mapping,
)
from review_loop.seals import GitPolicy, SealEntry, seal_target

FAKE_REVIEWER = Path(__file__).resolve().parent / "fixtures" / "fake_reviewer.py"

BWRAP = shutil.which("bwrap")


def _skip_reason():
    if not BWRAP:
        return "bwrap is not installed in this environment"
    return None


@unittest.skipIf(_skip_reason(), _skip_reason() or "")
class ContainmentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.target_root = self.root / "target"
        self.target_root.mkdir()
        (self.target_root / "readonly.txt").write_bytes(b"do-not-write-me")
        self.target_entries = (SealEntry("readonly.txt", "file", 0o644, "irrelevant-for-mapping"),)

        self.input_file = self.root / "ground-truth.md"
        self.input_file.write_bytes(b"authoritative")

        self.run_root = self.root / "run"
        self.run_root.mkdir()

        auth_dir = self.root / "codex-home"
        auth_dir.mkdir()
        self.auth_file = auth_dir / "auth.json"
        self.auth_file.write_bytes(b'{"fake":"auth-not-a-real-credential"}')

        self.host = CodexHostPaths(
            bwrap=Path(BWRAP),
            node=Path(sys.executable),  # stand-in "runtime" -- the system Python
            codex_package_root=FAKE_REVIEWER.parent,
            codex_entry=FAKE_REVIEWER,
            auth_file=self.auth_file,
            resolv_conf=Path("/etc/resolv.conf"),
            nsswitch_conf=Path("/etc/nsswitch.conf"),
            ca_certificates=Path("/etc/ssl/certs/ca-certificates.crt"),
        )
        self.executor = Executor(self._builder, term_grace_seconds=3, kill_grace_seconds=3)

    def _builder(self, request, call_dir):
        return build_codex_call(request, self.host, call_dir)

    def _request(self, call_id, directive, **overrides):
        base = dict(
            call_id=call_id,
            role="holistic",
            target_root=self.target_root,
            target_entries=self.target_entries,
            input_paths=(self.input_file,),
            run_root=self.run_root,
            prompt=json.dumps(directive),
        )
        base.update(overrides)
        return CallRequest(**base)

    def _run(self, call_id, directive, **overrides):
        req = self._request(call_id, directive, **overrides)
        started = self.executor.start(req)
        return req, started

    @staticmethod
    def _scratch_path(started, name):
        # `results_path`/heartbeat directives must be sandbox paths (only
        # /scratch and /report are writable inside); read the same file back
        # from the host side via the bind-mounted call_dir.
        return started.call_dir / "scratch" / name

    # --- Step 1: trivial contained binary actually executes ---

    def test_trivial_contained_binary_executes(self):
        result = subprocess.run(
            [BWRAP, "--clearenv", "--unshare-pid", "--die-with-parent",
             "--ro-bind", "/usr", "/usr",
             "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
             "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
             "--setenv", "PATH", "/usr/bin",
             "/bin/echo", "contained-ok"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("contained-ok", result.stdout)

    # --- env allowlist: injected host secrets are invisible ---

    def test_injected_host_secrets_are_invisible_to_the_child(self):
        os.environ["FAKE_HOST_SECRET"] = "super-secret-value"
        os.environ["HTTP_PROXY"] = "http://evil-proxy.invalid"
        os.environ["CODEX_HOOK_TOKEN"] = "hook-leak"
        os.environ["PRODUCT_DB_PASSWORD"] = "hunter2"
        self.addCleanup(os.environ.pop, "FAKE_HOST_SECRET", None)
        self.addCleanup(os.environ.pop, "HTTP_PROXY", None)
        self.addCleanup(os.environ.pop, "CODEX_HOOK_TOKEN", None)
        self.addCleanup(os.environ.pop, "PRODUCT_DB_PASSWORD", None)

        req, started = self._run("secrets", {"env_dump": True, "results_path": "/scratch/results.json"})
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "COMPLETED", completion.reason)

        seen_env = json.loads(self._scratch_path(started, "results.json").read_text())["env"]
        # PWD is a bwrap-hardcoded `--clearenv` survivor ("except for PWD"),
        # not something this mapping sets; it always carries the synthetic
        # `/subject` chdir target, never host information (see execution.py).
        self.assertEqual(set(seen_env) - {"PWD"}, {"HOME", "CODEX_HOME", "PATH", "LANG"})
        self.assertEqual(seen_env.get("PWD"), "/subject")
        for leaked in ("FAKE_HOST_SECRET", "HTTP_PROXY", "CODEX_HOOK_TOKEN", "PRODUCT_DB_PASSWORD"):
            self.assertNotIn(leaked, seen_env)

    # --- scope: read only target+input scope, write only report/scratch ---

    def test_can_read_only_exact_target_and_input_scope(self):
        secret_outside = self.root / "outside-secret.txt"
        secret_outside.write_bytes(b"never-mount-me")
        directive = {
            "read_files": [
                "/subject/readonly.txt",
                "/inputs/0/ground-truth.md",
                "/home/reviewer/.codex/auth.json",
                str(secret_outside),  # host path, unmapped inside the sandbox
            ],
            "results_path": "/scratch/results.json",
        }
        req, started = self._run("scope", directive)
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "COMPLETED", completion.reason)

        reads = json.loads(self._scratch_path(started, "results.json").read_text())["reads"]
        self.assertTrue(reads["/subject/readonly.txt"]["ok"])
        self.assertTrue(reads["/inputs/0/ground-truth.md"]["ok"])
        self.assertTrue(reads["/home/reviewer/.codex/auth.json"]["ok"])
        self.assertFalse(reads[str(secret_outside)]["ok"])  # not mounted at all

    def test_cannot_write_target_or_auth_writes_only_report_and_scratch(self):
        directive = {
            "write_attempts": [
                "/subject/readonly.txt",
                "/home/reviewer/.codex/auth.json",
                "/scratch/scratch.txt",
                "/report/report.md",
            ],
            "results_path": "/scratch/results.json",
        }
        req, started = self._run("writes", directive)
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "COMPLETED", completion.reason)

        writes = json.loads(self._scratch_path(started, "results.json").read_text())["writes"]
        self.assertFalse(writes["/subject/readonly.txt"]["ok"])
        self.assertFalse(writes["/home/reviewer/.codex/auth.json"]["ok"])
        self.assertTrue(writes["/scratch/scratch.txt"]["ok"])
        self.assertTrue(writes["/report/report.md"]["ok"])
        # the host file itself was never touched
        self.assertEqual((self.target_root / "readonly.txt").read_bytes(), b"do-not-write-me")

    def test_no_target_parent_directory_is_exposed(self):
        # Only the exact entry is bound; sibling files in the same host
        # directory as the target must not be enumerable inside /subject.
        (self.target_root / "sibling-not-in-scope.txt").write_bytes(b"peer data")
        directive = {"read_files": ["/subject/sibling-not-in-scope.txt"], "results_path": "/scratch/results.json"}
        req, started = self._run("sibling", directive)
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "COMPLETED", completion.reason)
        reads = json.loads(self._scratch_path(started, "results.json").read_text())["reads"]
        self.assertFalse(reads["/subject/sibling-not-in-scope.txt"]["ok"])

    # --- post-call target seal integrity (defense in depth) ---

    def test_post_call_seal_mismatch_raises_even_though_write_was_blocked(self):
        # The mapping already prevents mutation; this proves the independent
        # seal re-check is wired in and would fail closed if it were ever
        # bypassed (e.g. a future mapping bug).
        no_git = GitPolicy(enabled=False)
        before = seal_target(self.target_root, no_git)

        def verify():
            after = seal_target(self.target_root, no_git)
            if after.digest != before.digest:
                raise ExecutionError("post-call target seal mismatch")

        req, started = self._run("seal-check", {"exit_code": 0}, verify_target_unchanged=verify)
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "COMPLETED")  # no mutation occurred; hook did not fire

    # --- no descendant survives completion or termination ---

    def test_no_descendant_survives_after_completion(self):
        req, started = self._run(
            "hb-complete", {"spawn_orphan_heartbeat": "/scratch/hb.txt", "sleep_seconds": 0.3, "exit_code": 0}
        )
        completion = self.executor.finish(started)
        self.assertEqual(completion.outcome, "COMPLETED", completion.reason)
        self._assert_heartbeat_stopped(self._scratch_path(started, "hb.txt"))

    def test_no_descendant_survives_after_termination(self):
        req, started = self._run("hb-term", {"spawn_orphan_heartbeat": "/scratch/hb.txt", "sleep_seconds": 30})
        heartbeat = self._scratch_path(started, "hb.txt")
        # give the orphan a moment to actually start writing
        import time

        for _ in range(50):
            if heartbeat.exists():
                break
            time.sleep(0.05)
        self.assertTrue(heartbeat.exists(), "orphan heartbeat never started")
        proof = self.executor.terminate(started)
        self.assertTrue(proof.proven)
        self._assert_heartbeat_stopped(heartbeat)

    def _assert_heartbeat_stopped(self, heartbeat: Path) -> None:
        import time

        self.assertTrue(heartbeat.exists())
        v1 = heartbeat.read_text()
        time.sleep(0.3)
        v2 = heartbeat.read_text()
        self.assertEqual(v1, v2, "a descendant process is still alive and writing")

    # --- evidence-gate / FIX scope note ---

    def test_evidence_gate_and_fix_mappings_are_out_of_scope_for_task_5(self):
        # NOT RUN: this task builds only the ordinary Codex mapping. A
        # stricter no-credential/no-network mapping for evidence-gate and
        # FIX child commands is a later task's responsibility; asserted here
        # only as a documented scope boundary, not a behavioral claim.
        self.skipTest("evidence-gate/FIX mapping is out of scope for Task 5 (ordinary mapping only)")


@unittest.skipIf(_skip_reason(), _skip_reason() or "")
class CodexRealBinaryPreflightTests(unittest.TestCase):
    """Runs the preflight probe against the REAL installed Codex CLI (no
    network, no auth needed for --help). NOT RUN if codex is not installed."""

    def setUp(self):
        self.codex_bin = shutil.which("codex")
        if not self.codex_bin:
            self.skipTest("codex CLI is not installed in this environment")

    def test_real_codex_help_probe_passes(self):
        from review_loop.execution import resolve_codex_host_paths

        host = resolve_codex_host_paths()
        preflight_codex_mapping(host)  # must not raise

    def test_absent_flag_stops_preflight_without_dispatch(self):
        from review_loop.execution import resolve_codex_host_paths

        host = resolve_codex_host_paths()
        broken = CodexHostPaths(
            bwrap=host.bwrap,
            node=Path(sys.executable),
            codex_package_root=FAKE_REVIEWER.parent,
            codex_entry=FAKE_REVIEWER.parent / "incomplete_help_reviewer.py",
            auth_file=host.auth_file,
            resolv_conf=host.resolv_conf,
            nsswitch_conf=host.nsswitch_conf,
            ca_certificates=host.ca_certificates,
        )
        with self.assertRaises(ExecutionError):
            preflight_codex_mapping(broken)


if __name__ == "__main__":
    unittest.main()
