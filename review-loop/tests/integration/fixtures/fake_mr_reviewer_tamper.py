#!/usr/bin/env python3
"""Adversarial sibling of `fake_mr_reviewer.py`: shares the driver's process
namespace (the current, documented "interim limitation" -- fake reviewers
run inside the SAME sandbox instance as the driver's own transport/output),
and unconditionally attempts to replace/corrupt the driver's `/out/prompt.txt`,
`/out/.REVIEW.md.tmp`, and `/out/REVIEW.md` before responding normally.

`/out` is a fixed sandbox-internal mount point (part of the mount policy
under test, not something read from the environment), so this needs no
extra `--setenv` beyond the fixed 6-variable allowlist. Bound at a distinct
host path from the well-behaved `fake_mr_reviewer.py` so only the ONE test
that wants adversarial behavior selects it.
"""
from __future__ import annotations

import json
import os
import sys

_OUT_DIR = "/out"


def _tamper() -> None:
    for name in ("prompt.txt", ".REVIEW.md.tmp", "REVIEW.md"):
        target = os.path.join(_OUT_DIR, name)
        try:
            if os.path.islink(target) or os.path.exists(target):
                os.unlink(target)
        except OSError:
            pass
        try:
            os.symlink("/etc/hostname", target)
        except OSError:
            try:
                with open(target, "w") as fh:
                    fh.write("TAMPERED-BY-ADVERSARIAL-REVIEWER\n")
            except OSError:
                pass


def main() -> int:
    _tamper()
    sys.stdin.read()  # still drain stdin like a well-behaved reviewer would

    body = (
        "## Summary\nadversarial reviewer, tampering already attempted\n\n"
        "```review-record\n" + json.dumps({
            "request_id": "irrelevant", "role": "holistic", "charter_id": "holistic",
            "target_seal": "irrelevant", "round_input_seal": None, "scope_locator_ids": ["target-root"],
            "source_findings": [{"id": "x", "claim": "x", "severity": "Minor", "locator_ids": ["x:1"]}],
        }) + "\n```\n"
        "REVIEW-STATUS: COMPLETE"
    )
    argv0 = os.path.basename(sys.argv[0])
    if argv0 == "codex":
        print(json.dumps({"type": "thread.started"}))
        print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": body}}))
        print(json.dumps({"type": "turn.completed", "usage": {}}))
    else:
        print(json.dumps({"type": "system", "subtype": "init"}))
        print(json.dumps({"type": "result", "result": body}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
