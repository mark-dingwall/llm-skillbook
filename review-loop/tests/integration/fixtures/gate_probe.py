#!/usr/bin/env python3
"""A tiny argv-driven probe used only by gate-containment integration tests.

Unlike ``fake_reviewer.py`` (a codex-CLI stand-in driven by a JSON stdin
directive), a gate command is a plain argv invocation with no stdin prompt,
so this probe takes its directives as flags instead. It never talks to a
shell; each action is a direct Python operation.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time


def _spawn_orphan_heartbeat(path: str) -> None:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-dump", action="store_true")
    parser.add_argument("--read", action="append", default=[])
    parser.add_argument("--write", action="append", default=[])
    parser.add_argument("--connect", action="append", default=[], help="host:port")
    parser.add_argument("--spawn-orphan")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--exit", type=int, default=0)
    parser.add_argument("--results", required=True)
    args = parser.parse_args(argv[1:])

    results: dict[str, object] = {}

    if args.env_dump:
        results["env"] = dict(os.environ)

    reads = {}
    for path in args.read:
        try:
            with open(path, "rb") as fh:
                reads[path] = {"ok": True, "bytes": len(fh.read())}
        except OSError as exc:
            reads[path] = {"ok": False, "error": str(exc)}
    if reads:
        results["reads"] = reads

    writes = {}
    for path in args.write:
        try:
            with open(path, "a") as fh:
                fh.write("x")
            writes[path] = {"ok": True}
        except OSError as exc:
            writes[path] = {"ok": False, "error": str(exc)}
    if writes:
        results["writes"] = writes

    connects = {}
    for spec in args.connect:
        host, _, port = spec.partition(":")
        try:
            sock = socket.create_connection((host, int(port)), timeout=2)
            sock.close()
            connects[spec] = {"ok": True}
        except OSError as exc:
            connects[spec] = {"ok": False, "error": str(exc)}
    if connects:
        results["connects"] = connects

    if args.spawn_orphan:
        _spawn_orphan_heartbeat(args.spawn_orphan)
        results["spawned_orphan_heartbeat"] = args.spawn_orphan

    if args.sleep:
        time.sleep(args.sleep)

    with open(args.results, "w") as fh:
        json.dump(results, fh)

    return args.exit


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
