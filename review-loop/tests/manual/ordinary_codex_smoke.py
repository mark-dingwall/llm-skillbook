#!/usr/bin/env python3
"""Implementation behind ordinary-codex-smoke.sh. See ordinary-codex-smoke.md.

Not part of the automated suite: `--preflight` launches the real Codex CLI
under real Bubblewrap (no credentials needed to prove startup+containment);
`--live` makes a real network call when credentials are present.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REVIEW_LOOP_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REVIEW_LOOP_ROOT))

from review_loop.execution import (  # noqa: E402
    CallRequest,
    CodexHostPaths,
    ExecutionError,
    Executor,
    codex_builder,
    preflight_codex_mapping,
    resolve_codex_host_paths,
)
from review_loop.seals import SealEntry  # noqa: E402

FAKE_REVIEWER = REVIEW_LOOP_ROOT / "tests" / "integration" / "fixtures" / "fake_reviewer.py"

PASS = "PASS"
FAIL = "FAIL"
NOT_RUN = "NOT RUN"

_results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    _results.append((name, status, detail))
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))


def _real_host_with_placeholder_auth(tmp: Path) -> CodexHostPaths:
    # A structurally-present but non-functional auth.json: enough for the
    # mapping to mount and for codex to start, never a real credential.
    codex_home = tmp / "codex-home"
    codex_home.mkdir()
    (codex_home / "auth.json").write_text(json.dumps({"placeholder": True}))
    return resolve_codex_host_paths(codex_home=codex_home)


def run_preflight() -> int:
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)

        try:
            host = _real_host_with_placeholder_auth(tmp)
            record("resolve_codex_host_paths", PASS, str(host.codex_entry))
        except ExecutionError as exc:
            record("resolve_codex_host_paths", FAIL, str(exc))
            return 1

        try:
            preflight_codex_mapping(host)
            record("codex exec --help probe (real codex, no credentials)", PASS)
        except ExecutionError as exc:
            record("codex exec --help probe", FAIL, str(exc))
            return 1

        run_root = tmp / "run"
        run_root.mkdir()

        # --- 1) the REAL codex/node runtime starts inside the mapping ---
        target_root = tmp / "target"
        target_root.mkdir()
        (target_root / "readonly.txt").write_text("smoke target\n")
        entries = (SealEntry("readonly.txt", "file", 0o644, "irrelevant"),)

        real_executor = Executor(codex_builder(host), term_grace_seconds=5, kill_grace_seconds=5)
        req = CallRequest(
            call_id="smoke-real",
            role="holistic",
            target_root=target_root,
            target_entries=entries,
            input_paths=(),
            run_root=run_root,
            prompt="say OK and stop",
        )
        started = real_executor.start(req)
        deadline = datetime.now(timezone.utc) + timedelta(seconds=15)
        completion = real_executor.finish(started, deadline=deadline)
        diagnostics = started.call_dir / "diagnostics" / "stderr.log"
        stderr_text = diagnostics.read_text(errors="replace") if diagnostics.exists() else ""
        loader_failure_markers = ("execvp", "No such file or directory", "cannot execute binary file")
        if any(marker in stderr_text for marker in loader_failure_markers):
            record(
                "real codex binary starts inside the namespace",
                FAIL,
                f"loader/exec failure in stderr: {stderr_text[:300]!r}",
            )
            return 1
        record(
            "real codex binary starts inside the namespace",
            PASS,
            f"outcome={completion.outcome} reason={completion.reason} "
            "(auth/network failure here is expected -- no real credentials were used)",
        )

        # --- 2) injected host secret is invisible; target read-only; scratch/report writable ---
        # Reuses the exact same mapping-construction path (build_codex_call)
        # with fake_reviewer.py standing in for node/codex.js, so this proves
        # the property of the mapping itself, independent of Codex's own
        # behavior (which never touches the filesystem without a real model
        # turn -- see ordinary-codex-smoke.md).
        fake_host = CodexHostPaths(
            bwrap=host.bwrap,
            node=Path(sys.executable),
            codex_package_root=FAKE_REVIEWER.parent,
            codex_entry=FAKE_REVIEWER,
            auth_file=host.auth_file,
            resolv_conf=host.resolv_conf,
            nsswitch_conf=host.nsswitch_conf,
            ca_certificates=host.ca_certificates,
        )
        os.environ["SMOKE_FAKE_SECRET"] = "should-never-be-visible"
        try:
            fake_executor = Executor(codex_builder(fake_host), term_grace_seconds=5, kill_grace_seconds=5)
            directive = {
                "env_dump": True,
                "write_attempts": ["/subject/readonly.txt", "/scratch/x.txt", "/report/report.md"],
                "results_path": "/scratch/results.json",
            }
            req2 = CallRequest(
                call_id="smoke-fake",
                role="holistic",
                target_root=target_root,
                target_entries=entries,
                input_paths=(),
                run_root=run_root,
                prompt=json.dumps(directive),
            )
            started2 = fake_executor.start(req2)
            completion2 = fake_executor.finish(started2)
        finally:
            os.environ.pop("SMOKE_FAKE_SECRET", None)

        if completion2.outcome != "COMPLETED":
            record("containment probe (fake reviewer)", FAIL, completion2.reason or "")
            return 1
        results_path = started2.call_dir / "scratch" / "results.json"
        results = json.loads(results_path.read_text())
        env_seen = results.get("env", {})
        if "SMOKE_FAKE_SECRET" in env_seen:
            record("injected host secret invisible", FAIL, "secret was visible inside the sandbox")
            return 1
        record("injected host secret invisible", PASS)

        writes = results.get("writes", {})
        if writes.get("/subject/readonly.txt", {}).get("ok"):
            record("read-only target cannot be written", FAIL)
            return 1
        record("read-only target cannot be written", PASS)

        if not (writes.get("/scratch/x.txt", {}).get("ok") and writes.get("/report/report.md", {}).get("ok")):
            record("scratch/report are writable", FAIL, json.dumps(writes))
            return 1
        record("scratch/report are writable", PASS)

    return 0


def run_live() -> int:
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    if not (codex_home / "auth.json").exists():
        record("live Codex review", NOT_RUN, f"no credentials at {codex_home}/auth.json")
        return 0

    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        host = resolve_codex_host_paths(codex_home=codex_home)
        try:
            preflight_codex_mapping(host)
        except ExecutionError as exc:
            record("live preflight probe", FAIL, str(exc))
            return 1

        target_root = tmp / "target"
        target_root.mkdir()
        (target_root / "fixture.py").write_text("def add(a, b):\n    return a + b\n")
        entries = (SealEntry("fixture.py", "file", 0o644, "irrelevant"),)
        run_root = tmp / "run"
        run_root.mkdir()

        executor = Executor(codex_builder(host), term_grace_seconds=10, kill_grace_seconds=10)
        req = CallRequest(
            call_id="smoke-live",
            role="holistic",
            target_root=target_root,
            target_entries=entries,
            input_paths=(),
            run_root=run_root,
            prompt="Reply with exactly one short sentence confirming you can see fixture.py.",
        )
        started = executor.start(req)
        deadline = datetime.now(timezone.utc) + timedelta(seconds=120)
        completion = executor.finish(started, deadline=deadline)

        if completion.outcome != "COMPLETED" or not completion.report_text:
            record("live Codex review", FAIL, f"outcome={completion.outcome} reason={completion.reason}")
            return 1
        record("live Codex review", PASS, completion.report_text.strip()[:200])
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("--preflight", "--live"):
        print("usage: ordinary_codex_smoke.py --preflight | --live", file=sys.stderr)
        return 2
    if not shutil.which("bwrap") or not shutil.which("codex"):
        print("SKIP: bwrap or codex is not installed", file=sys.stderr)
        return 0
    rc = run_preflight() if argv[1] == "--preflight" else run_live()
    failed = [r for r in _results if r[1] == FAIL]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed" + (f", {len(failed)} FAILED" if failed else ""))
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
