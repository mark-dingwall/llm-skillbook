#!/usr/bin/env python3
"""A codex-compatible stand-in used only by containment tests.

Accepts (and ignores) the real `codex exec` flags so it can be substituted
for `node <codex.js>` inside the *exact* Bubblewrap mapping the Codex
backend builds (`execution.build_codex_call`), then acts on a JSON test
directive read from stdin (the same channel a real prompt would use). This
lets containment tests exercise the real mapping-construction code path
without a network call or real Codex credentials.

Directive schema (all keys optional), given as JSON on stdin:
  env_dump: bool                 -- record os.environ
  read_files: [path, ...]        -- try reading each; record ok/error
  write_attempts: [path, ...]    -- try appending a byte to each; record ok/error
  spawn_orphan_heartbeat: path   -- double-fork a detached writer that loops
                                     incrementing a counter into `path` until
                                     the whole process tree is torn down
  sleep_seconds: float           -- sleep before finishing (deadline tests)
  exit_code: int                 -- exit status to return (default 0)
  results_path: path             -- where to write the JSON results

Non-JSON stdin is treated as an ordinary prompt: the report simply echoes it.
"""
from __future__ import annotations

import json
import os
import sys
import time


def _parse_output_path(argv: list[str]) -> str | None:
    for i, arg in enumerate(argv):
        if arg in ("--output-last-message", "-o") and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _spawn_orphan_heartbeat(path: str) -> None:
    # Double fork so the writer is reparented to init and outlives this
    # process's own lifetime; the containment test proves it cannot outlive
    # the whole bwrap process tree regardless.
    if os.fork() != 0:
        return
    if os.fork() != 0:
        os._exit(0)
    os.setsid()
    n = 0
    while True:
        with open(path, "w") as fh:
            fh.write(str(n))
        n += 1
        time.sleep(0.05)


def main(argv: list[str]) -> int:
    output_path = _parse_output_path(argv[1:])
    raw = sys.stdin.read()
    try:
        directive = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        directive = None

    results: dict[str, object] = {"ok": True}
    exit_code = 0

    if isinstance(directive, dict):
        if directive.get("env_dump"):
            results["env"] = dict(os.environ)
        if directive.get("read_files"):
            reads = {}
            for path in directive["read_files"]:
                try:
                    with open(path, "rb") as fh:
                        reads[path] = {"ok": True, "bytes": len(fh.read())}
                except OSError as exc:
                    reads[path] = {"ok": False, "error": str(exc)}
            results["reads"] = reads
        if directive.get("write_attempts"):
            writes = {}
            for path in directive["write_attempts"]:
                try:
                    with open(path, "a") as fh:
                        fh.write("x")
                    writes[path] = {"ok": True}
                except OSError as exc:
                    writes[path] = {"ok": False, "error": str(exc)}
            results["writes"] = writes
        heartbeat = directive.get("spawn_orphan_heartbeat")
        if heartbeat:
            _spawn_orphan_heartbeat(heartbeat)
            results["spawned_orphan_heartbeat"] = heartbeat
        sleep_seconds = directive.get("sleep_seconds")
        if sleep_seconds:
            time.sleep(sleep_seconds)
        results_path = directive.get("results_path")
        if results_path:
            with open(results_path, "w") as fh:
                json.dump(results, fh)
        exit_code = int(directive.get("exit_code", 0))
    else:
        results["prompt"] = raw

    if output_path:
        with open(output_path, "w") as fh:
            fh.write("fake-reviewer report\n")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
