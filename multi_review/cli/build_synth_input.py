"""mr-build-synth-input — read reviewer state.json files, emit synth prompt + nonce."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from multi_review.core.fanout import ReviewerResult
from multi_review.core.synthesis import build_synthesis_input


def _state_to_result(sf: Path, state: dict) -> ReviewerResult | None:
    body = state.get("body")
    if not body:
        # state file is <cli>.state.json; sibling review file is <cli>.md
        md = sf.with_name(sf.name.replace(".state.json", ".md"))
        body = md.read_text() if md.exists() else ""
    usage_raw = state.get("usage")
    from multi_review.core.adapters import Usage
    usage = (
        Usage(
            input_tokens=usage_raw.get("input_tokens", 0),
            output_tokens=usage_raw.get("output_tokens", 0),
            cached_tokens=usage_raw.get("cached_tokens", 0),
            tool_calls=usage_raw.get("tool_calls", 0),
        )
        if usage_raw
        else None
    )
    return ReviewerResult(
        cli=state["cli"],
        ok=state.get("ok", False),
        text=body,
        stderr_tail=state.get("stderr_tail", ""),
        usage=usage,
        elapsed=state.get("duration_seconds", 0.0),
        model_used=state.get("final_model"),
    )


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
        try:
            state = json.loads(sf.read_text())
        except Exception as e:
            print(f"warning: skipping malformed {sf.name}: {e}", file=sys.stderr)
            continue
        if "cli" not in state:
            continue
        r = _state_to_result(sf, state)
        if r is not None:
            results.append(r)

    body, nonce = build_synthesis_input(results)
    args.out_prompt_file.parent.mkdir(parents=True, exist_ok=True)
    args.out_prompt_file.write_text(body)

    if args.out_nonce_file:
        args.out_nonce_file.parent.mkdir(parents=True, exist_ok=True)
        args.out_nonce_file.write_text(nonce)
    else:
        print(nonce)
    return 0


if __name__ == "__main__":
    sys.exit(main())
