#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.7", "pyyaml>=6.0"]
# ///
"""multi-review headless single-pass driver.

Runs one fan-out pass with no LLM in the loop, from any working directory:

    uv run <absolute-path-to-repo>/multi_review.py --prompt-file <yaml> --out-dir <dir>

Design: docs/superpowers/specs/2026-08-04-headless-driver-design.md

The PEP 723 header above is load-bearing: uv's project discovery runs from the
invoking cwd, so without it a run from a foreign directory resolves no
third-party dependencies at all and `import yaml` fails.

Imports below are bare names on purpose — the unit tests monkeypatch them as
module-level attributes, which dotted access would not allow.
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

import yaml

from multi_review.core.prompt import build_prompt
from multi_review.core.promptfile import ValidationError, _resolve_path, load_promptfile


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="multi_review.py")
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=None)
    args = p.parse_args(argv)

    # Resolve once while the caller's foreign cwd is still the reference point.
    # This same absolute path drives loading, relative input resolution, and
    # REVIEW.md attribution.
    prompt_file = args.prompt_file.resolve()

    out_dir: Path = args.out_dir
    try:
        if out_dir.exists():
            if not out_dir.is_dir():
                print(f"error: --out-dir is not a directory: {out_dir}", file=sys.stderr)
                return 2
            if any(out_dir.iterdir()):
                print(f"error: --out-dir must be empty: {out_dir}", file=sys.stderr)
                return 2
    except OSError as exc:
        print(f"error: cannot inspect --out-dir {out_dir}: {exc}", file=sys.stderr)
        return 2
    try:
        pf = load_promptfile(prompt_file)
    except (ValidationError, yaml.YAMLError, OSError) as exc:
        print(f"error: {prompt_file}: {exc}", file=sys.stderr)
        return 2
    if pf.mode == "both":
        print("error: driver takes mode inline|reference, not both", file=sys.stderr)
        return 2

    # validate() checks ALL_REVIEWERS membership but not uniqueness: [codex, codex]
    # passes today. Two concurrent run_reviewer calls for one CLI would be
    # indistinguishable in the results list and double-count toward the synthesis gate.
    reviewers = list(dict.fromkeys(pf.reviewers))

    base = prompt_file.parent

    try:
        prompt_text = build_prompt(
            task=pf.task,
            files=[_resolve_path(f, base) for f in pf.files],
            context_files=[_resolve_path(f, base) for f in pf.context_files],
            custom_prompt=pf.custom_prompt,
            mode=pf.mode,
            nonce=secrets.token_hex(4),
        )
    except SystemExit as exc:
        # build_prompt raises SystemExit on an unreadable file. Nothing has been
        # dispatched yet, so there is nothing to salvage.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = out_dir / "prompt.txt"
        prompt_path.write_text(prompt_text)
    except OSError as exc:
        # Operational output failure, before dispatch: failed run, no traceback.
        print(f"error: cannot write driver output: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
