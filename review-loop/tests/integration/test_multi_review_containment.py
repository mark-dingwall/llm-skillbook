"""Real-Bubblewrap containment proof for the caller-contained multi-review
holistic slot (Task 11).

Every mount/env assertion here runs through the REAL `build_multi_review_call`
mapping-construction code, substituting fixture scripts for `claude`/`codex`
so no network call or real credentials are needed:

  * Lightweight mount-policy probes (env leak, read/write scope, process
    cleanup) swap the trailing `/bin/bash -c <wrapper>` command for
    `fixtures/fake_reviewer.py` (Task 5's existing directive-based probe) --
    everything BEFORE that command is the exact production argv.
  * The full happy-path and tampering tests run the REAL
    `MultiReviewAdapter.invoke()` end to end (real `uv run --offline
    --isolated` against the real multi-review driver), substituting
    fixtures/fake_mr_reviewer{,_tamper}.py for claude/codex.

Skips (not failures) when `bwrap` is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from review_loop.multi_review import (
    HolisticRequest,
    MultiReviewAdapter,
    MultiReviewHostPaths,
    MultiReviewPolicy,
    build_multi_review_call,
    resolve_multi_review_host_paths,
)
from review_loop.seals import GitPolicy, seal_target

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_PROBE = FIXTURES / "fake_reviewer.py"  # Task 5's generic directive-based probe
FAKE_MR = FIXTURES / "fake_mr_reviewer.py"
FAKE_MR_TAMPER = FIXTURES / "fake_mr_reviewer_tamper.py"
FAKE_MR_FORGE = FIXTURES / "fake_mr_reviewer_forge.py"

BWRAP = shutil.which("bwrap")


def _skip_reason() -> str | None:
    if not BWRAP:
        return "bwrap is not installed in this environment"
    return None


def _make_fake_host(root: Path, *, codex_fixture: Path = FAKE_MR, claude_fixture: Path = FAKE_MR) -> MultiReviewHostPaths:
    """A real host paths resolution, EXCEPT claude/codex point at fixture
    scripts instead of real binaries -- every mount/env-construction call
    still goes through the exact same production code."""
    codex_pkg = root / "codexpkg"
    codex_pkg.mkdir(parents=True, exist_ok=True)
    codex_entry = codex_pkg / codex_fixture.name
    shutil.copy2(codex_fixture, codex_entry)
    codex_entry.chmod(0o755)
    claude_bin = root / "claude-bin"
    shutil.copy2(claude_fixture, claude_bin)
    claude_bin.chmod(0o755)

    real = resolve_multi_review_host_paths(repo_root=REPO_ROOT)
    return MultiReviewHostPaths(**{
        **real.__dict__,
        "claude": claude_bin,
        "codex_package_root": codex_pkg,
        "codex_entry": codex_entry,
    })


@unittest.skipIf(_skip_reason(), _skip_reason() or "")
class MountPolicyProbeTests(unittest.TestCase):
    """Swaps the trailing wrapper command for the generic directive-based
    probe; every mount/env argv element before it is the real mapping."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "target"
        self.target.mkdir()
        (self.target / "foo.py").write_text("do-not-write-me")
        (self.target / "sibling.py").write_text("peer data, not in scope")
        self.host = _make_fake_host(self.root / "host")
        self.seal = seal_target(self.target, GitPolicy(enabled=False))
        self.request = HolisticRequest(
            call_id="probe", request_id="req-probe", target_seal=self.seal.digest, round_input_seal=None,
            scope_locator_ids=("target-root",), target_root=self.target,
            target_entries=tuple(e for e in self.seal.entries if e.path == "foo.py"),
            run_root=self.root / "run", raw_report_ids={"claude": "c1", "codex": "x1"},
        )

    def _run_probe(self, directive: dict, *, timeout=15) -> dict:
        argv, _wrapper, paths = build_multi_review_call(
            self.request, MultiReviewPolicy(), self.host, self.root / "call", timeout_seconds=60,
        )
        results_path = paths.out_dir / "results.json"
        directive = {**directive, "results_path": "/out/results.json"}
        # the probe script itself needs a mount at its own absolute host
        # path to be reachable -- not part of the production mount plan,
        # added only for this substitution.
        probe_argv = (
            argv[:-3] + ["--ro-bind", str(FAKE_PROBE), str(FAKE_PROBE)]
            + [sys.executable, str(FAKE_PROBE)]
        )
        result = subprocess.run(
            probe_argv, input=json.dumps(directive), capture_output=True, text=True, timeout=timeout,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(results_path.read_text())

    def test_trivial_mapping_executes(self):
        out = self._run_probe({"exit_code": 0})
        self.assertTrue(out["ok"])

    def test_injected_host_secrets_are_invisible_to_the_child(self):
        import os

        os.environ["FAKE_HOST_SECRET"] = "super-secret-value"
        os.environ["HTTP_PROXY"] = "http://evil-proxy.invalid"
        os.environ["ANTHROPIC_API_KEY"] = "sk-leak-me-not"
        os.environ["MULTI_REVIEW_HOOK_TOKEN"] = "hook-leak"
        for name in ("FAKE_HOST_SECRET", "HTTP_PROXY", "ANTHROPIC_API_KEY", "MULTI_REVIEW_HOOK_TOKEN"):
            self.addCleanup(os.environ.pop, name, None)

        out = self._run_probe({"env_dump": True})
        seen = out["env"]
        self.assertEqual(set(seen) - {"PWD"}, {"HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "UV_CACHE_DIR", "PATH", "LANG"})
        for leaked in ("FAKE_HOST_SECRET", "HTTP_PROXY", "ANTHROPIC_API_KEY", "MULTI_REVIEW_HOOK_TOKEN"):
            self.assertNotIn(leaked, seen)
        # the CLAUDE_CODE_OAUTH_TOKEN channel is never `--setenv`-based; a
        # probe substituted for the wrapper command never sees it either.
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", seen)

    def test_can_read_exact_target_file_and_auth_but_not_unlisted_sibling_or_outside_secret(self):
        secret_outside = self.root / "outside-secret.txt"
        secret_outside.write_bytes(b"never-mount-me")
        target_path = str((self.target / "foo.py").resolve())
        sibling_path = str((self.target / "sibling.py").resolve())
        out = self._run_probe({
            "read_files": [
                target_path, sibling_path, "/home/review/.codex/auth.json",
                "/workspace/multi-review/multi_review.py", str(secret_outside),
            ],
        })
        reads = out["reads"]
        self.assertTrue(reads[target_path]["ok"])
        self.assertTrue(reads["/home/review/.codex/auth.json"]["ok"])
        self.assertTrue(reads["/workspace/multi-review/multi_review.py"]["ok"])
        self.assertFalse(reads[sibling_path]["ok"], "an unlisted sibling of a scoped file must not be readable")
        self.assertFalse(reads[str(secret_outside)]["ok"])

    def test_cannot_write_auth_or_request_yaml_can_write_home_uv_cache_out(self):
        auth_before = self.host.codex_auth_file.read_bytes()
        out = self._run_probe({
            "write_attempts": [
                "/home/review/.codex/auth.json", "/request.yaml",
                "/home/review/scratch-write.txt", "/uv-cache/scratch-write.txt", "/out/scratch-write.txt",
            ],
        })
        writes = out["writes"]
        self.assertFalse(writes["/home/review/.codex/auth.json"]["ok"])
        self.assertFalse(writes["/request.yaml"]["ok"])
        self.assertTrue(writes["/home/review/scratch-write.txt"]["ok"])
        self.assertTrue(writes["/uv-cache/scratch-write.txt"]["ok"])
        self.assertTrue(writes["/out/scratch-write.txt"]["ok"])
        # the host auth file itself was never touched
        self.assertEqual(self.host.codex_auth_file.read_bytes(), auth_before)

    def test_no_descendant_survives_termination(self):
        argv, _wrapper, paths = build_multi_review_call(
            self.request, MultiReviewPolicy(), self.host, self.root / "call", timeout_seconds=60,
        )
        probe_argv = (
            argv[:-3] + ["--ro-bind", str(FAKE_PROBE), str(FAKE_PROBE)]
            + [sys.executable, str(FAKE_PROBE)]
        )
        directive = {"spawn_orphan_heartbeat": "/out/hb.txt", "sleep_seconds": 30, "results_path": "/out/results.json"}
        proc = subprocess.Popen(probe_argv, stdin=subprocess.PIPE)
        proc.stdin.write(json.dumps(directive).encode())
        proc.stdin.close()
        heartbeat = paths.out_dir / "hb.txt"
        import time
        for _ in range(60):
            if heartbeat.exists():
                break
            time.sleep(0.05)
        self.assertTrue(heartbeat.exists(), "orphan heartbeat never started")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        v1 = heartbeat.read_text()
        time.sleep(0.3)
        v2 = heartbeat.read_text()
        self.assertEqual(v1, v2, "a descendant process is still alive and writing after termination")


@unittest.skipIf(_skip_reason(), _skip_reason() or "")
class EndToEndAdapterTests(unittest.TestCase):
    """Full real-bwrap round trips through `MultiReviewAdapter.invoke()`:
    real `uv run --offline --isolated` against the real multi-review driver,
    with fixture claude/codex reviewers standing in for the real CLIs."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "target"
        self.target.mkdir()
        (self.target / "foo.py").write_text("x = 1\n")
        self.run_root = self.root / "run"
        self.seal = seal_target(self.target, GitPolicy(enabled=False))
        self.request = HolisticRequest(
            call_id="e2e", request_id="req-e2e", target_seal=self.seal.digest, round_input_seal=None,
            scope_locator_ids=("target-root",), target_root=self.target, target_entries=self.seal.entries,
            run_root=self.run_root, raw_report_ids={"claude": "raw-claude", "codex": "raw-codex"},
        )

    def test_happy_path_produces_two_qualified_reports(self):
        host = _make_fake_host(self.root / "host")
        adapter = MultiReviewAdapter(host, "fake-oauth-token-not-a-real-credential", term_grace_seconds=5, kill_grace_seconds=5)
        result = adapter.invoke(self.request, MultiReviewPolicy(timeout_seconds=180))
        self.assertIsNone(result.fallback_reason, result.fallback_reason)
        self.assertEqual(len(result.reports), 2)
        by_id = {r.report_id: r for r in result.reports}
        self.assertEqual(set(by_id), {"raw-claude", "raw-codex"})
        for r in by_id.values():
            self.assertTrue(r.review.usable)
            self.assertEqual(r.review.record.target_seal, self.request.target_seal)
        # the disclosed interim limitation: fake reviewers share the
        # namespace containing driver transport/output.
        self.assertEqual(self.target.joinpath("foo.py").read_text(), "x = 1\n")

    def test_shared_namespace_tampering_yields_ordinary_fallback_never_usable_evidence(self):
        """Scope: PRE-publish tampering, during fanout (fake_mr_reviewer_tamper.py
        corrupts prompt.txt/.REVIEW.md.tmp/REVIEW.md unconditionally, at the
        very start, before any reviewer -- including itself -- has finished).
        The driver's own post-fanout `_verify_prompt_transport()` re-hash
        catches the corrupted prompt.txt and aborts before publishing.

        This does NOT cover the POST-publish race -- see
        `test_post_publish_forge_race_is_sometimes_accepted_documented_residual_risk`
        below for that separate, NOT reliably caught, residual (I2)."""
        host = _make_fake_host(self.root / "host", codex_fixture=FAKE_MR_TAMPER)
        adapter = MultiReviewAdapter(host, "fake-oauth-token-not-a-real-credential", term_grace_seconds=5, kill_grace_seconds=5)
        result = adapter.invoke(self.request, MultiReviewPolicy(timeout_seconds=180))
        self.assertIsNone(result.reports, "tampered output must never be accepted as usable evidence")
        self.assertIsNotNone(result.fallback_reason)

    def test_post_publish_forge_race_is_sometimes_accepted_documented_residual_risk(self):
        """I2 (fix round 1, honest test per team-lead request -- not a claim
        of a guaranteed catch): fake_mr_reviewer_forge.py answers honestly in
        its foreground process (fanout sees a normal successful reviewer),
        but ALSO double-forks a DETACHED background process that races the
        driver's own process-tree teardown to overwrite `/out/REVIEW.md`,
        AFTER the driver's atomic publish, with a forged aggregate built from
        information genuinely readable inside the shared sandbox (this
        reviewer's own dispatch header + both --raw-report-id values scraped
        from /proc/*/cmdline).

        Every field `MultiReviewAdapter._collect()` re-verifies is exactly
        what the forger can also read and reproduce, so a WIN is
        indistinguishable from a real successful pair: this test documents,
        honestly, that `invoke()` accepts the forged aggregate when the
        forger wins the race. The real (and only) barrier is bwrap's
        `--unshare-pid` namespace teardown timing, not this adapter's
        validation -- full closure needs native per-reviewer containment
        (deferred, out of this task's scope).
        """
        host = _make_fake_host(self.root / "host", codex_fixture=FAKE_MR_FORGE)
        adapter = MultiReviewAdapter(host, "fake-oauth-token-not-a-real-credential", term_grace_seconds=5, kill_grace_seconds=5)
        result = adapter.invoke(self.request, MultiReviewPolicy(timeout_seconds=180))
        # Whatever the real outcome is, it must be internally consistent
        # (exactly one of reports/fallback_reason) -- MultiReviewResult's own
        # __post_init__ already enforces that; asserted again here for a
        # clear, named failure if it were ever violated.
        self.assertTrue((result.reports is None) != (result.fallback_reason is None))
        if result.reports is not None:
            forged = [
                r for r in result.reports
                if any("FORGED-BY-POST-PUBLISH-RACE" in f.claim for f in r.review.record.source_findings)
            ]
            self.assertTrue(
                forged,
                "invoke() accepted a REVIEW.md that was NOT the forged one -- "
                "the forger lost this particular race (also a legitimate, "
                "honestly-reported outcome; the residual is about what "
                "happens when it wins, not that it always wins)",
            )
            # Document the residual honestly: this run accepted forged content.
            print(
                "\n[I2 residual, documented] the post-publish forge race was "
                f"WON this run: invoke() accepted {len(forged)} forged report(s) "
                "as usable evidence.",
                file=sys.stderr,
            )
        else:
            print(
                f"\n[I2 residual, documented] the forge LOST this run "
                f"(fallback_reason={result.fallback_reason!r}); the race is "
                "real but not deterministic in either direction.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    unittest.main()
