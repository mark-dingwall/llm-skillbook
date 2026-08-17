#!/usr/bin/env python3
"""A claude/codex-compatible stand-in used only by
tests/integration/test_multi_review_containment.py.

Ignores every CLI flag it is invoked with (both `claude -p --output-format
stream-json ...` and `codex exec --skip-git-repo-check --json ...` argv
shapes reach here), reads the verbatim prompt from stdin, parses its leading
`key: value` dispatch header (the same shape
multi_review.core.aggregate.parse_verbatim_dispatch_header expects), and
emits a well-formed review-record echoing those exact fields back -- wrapped
in whichever JSONL envelope its own basename (`claude` or `codex`) expects,
so the real multi-review fanout/adapter machinery parses it as a normal
successful reviewer run.

See the sibling `fake_mr_reviewer_tamper.py` for the adversarial variant that
also attempts to corrupt the driver's own shared `/out` transport/output
files before responding -- bound at a *separate* host path for the one test
that exercises it, never toggled by an extra environment variable (the
6-variable `--clearenv` allowlist under test has no room for one).
"""
from __future__ import annotations

import json
import os
import sys


def _dispatch_header(text: str) -> dict:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.strip() == "":
            break
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key] = value
    return fields


def _record(fields: dict) -> dict:
    scope = json.loads(fields["scope_locator_ids"])
    ris = fields["round_input_seal"]
    cli = os.path.basename(sys.argv[0]) or "reviewer"
    return {
        "request_id": fields["request_id"],
        "role": fields["role"],
        "charter_id": fields["charter_id"],
        "target_seal": fields["target_seal"],
        "round_input_seal": None if ris == "null" else ris,
        "scope_locator_ids": scope,
        "source_findings": [
            {"id": f"{cli}-f1", "claim": f"{cli} found a minor issue", "severity": "Minor", "locator_ids": ["foo.py:1"]}
        ],
    }


def main() -> int:
    text = sys.stdin.read()
    fields = _dispatch_header(text)
    record = _record(fields)
    body = (
        "## Summary\nfake reviewer output\n\n"
        "```review-record\n" + json.dumps(record) + "\n```\n"
        "REVIEW-STATUS: COMPLETE"
    )

    argv0 = os.path.basename(sys.argv[0])
    if argv0 == "codex":
        print(json.dumps({"type": "thread.started"}))
        print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": body}}))
        print(json.dumps({"type": "turn.completed", "usage": {}}))
    else:  # claude
        print(json.dumps({"type": "system", "subtype": "init"}))
        print(json.dumps({"type": "result", "result": body}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
