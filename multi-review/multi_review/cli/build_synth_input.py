"""mr-build-synth-input — read reviewer state.json files, emit synth prompt + nonce."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from multi_review.cli.review_state import (
    read_review_body,
    read_state_file,
    result_from_state,
)
from multi_review.core.fanout import ReviewerResult
from multi_review.core.synthesis import build_synthesis_input


def _state_to_result(sf: Path, state: object):
    cli = sf.name.removesuffix(".state.json")
    body = state.get("body") if isinstance(state, dict) else None
    if body is None:
        # state file is <cli>.state.json; sibling review file is <cli>.md
        md = sf.with_name(sf.name.replace(".state.json", ".md"))
        body, body_error = read_review_body(md)
        if body_error is not None:
            return None, body_error
    return result_from_state(cli, state, body), None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Build synthesis prompt from reviewer state.json files.",
    )
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--out-prompt-file", type=Path, required=True)
    p.add_argument("--out-nonce-file", type=Path, default=None)
    args = p.parse_args(argv)

    results: list[ReviewerResult] = []
    for sf in sorted(args.state_dir.glob("*.state.json")):
        state, state_error = read_state_file(sf)
        if state_error is not None:
            print(f"warning: skipping {sf.name}: {state_error}", file=sys.stderr)
            continue
        r, error = _state_to_result(sf, state)
        if error is not None:
            print(f"warning: skipping {sf.name}: {error}", file=sys.stderr)
            continue
        if r.ok:
            results.append(r)
        else:
            print(f"warning: skipping {sf.name}: {r.error or 'failed reviewer'}", file=sys.stderr)

    body, nonce = build_synthesis_input(results)
    args.out_prompt_file.parent.mkdir(parents=True, exist_ok=True)
    args.out_prompt_file.write_text(body, encoding="utf-8")

    if args.out_nonce_file:
        args.out_nonce_file.parent.mkdir(parents=True, exist_ok=True)
        args.out_nonce_file.write_text(nonce, encoding="utf-8")
    else:
        print(nonce)
    return 0


if __name__ == "__main__":
    sys.exit(main())
