"""multi_review.cli.spawn — single-reviewer subprocess runner.

Invokes one external reviewer CLI, streams its output through the relevant
ProgressAdapter, and writes two files into --out-dir:
  <cli>.md         — the review text
  <cli>.state.json — metadata for aggregate.py to consume

Prints a JSON summary to stdout: {"ok": bool, "review_path": str, "state_path": str}
Exit code: 0 if reviewer succeeded, 1 if it failed.

The --effort flag is accepted but currently a no-op; it is forwarded via a
future task that wires effort through CLI_SPEC/build_command.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from multi_review.core.fanout import ReviewerState, ReviewerResult, resolve_chain, run_reviewer, CAPACITY_PATTERNS
from multi_review.core.reviewers import ALL_REVIEWERS, make_adapter
from multi_review.core.synthesis import run_synthesis


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run one reviewer CLI, write review + state JSON.",
    )
    p.add_argument("--cli", choices=ALL_REVIEWERS, required=True)
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--model", default=None,
                   help="Pin to a specific model (disables fallback chain).")
    p.add_argument("--fallback-chain", default=None,
                   help="Comma-separated model list; empty string disables fallback.")
    p.add_argument("--effort", default=None,
                   help="Effort hint (accepted but no-op until wired through CLI_SPEC).")
    p.add_argument("--timeout", type=int, default=None,
                   help="Seconds before killing reviewer subprocess.")
    p.add_argument("--task-mode", choices=["review", "synthesize"], default="review")
    p.add_argument("--input-nonce", default=None,
                   help="Nonce token used in the synthesis review-body tags "
                        "(required with --task-mode synthesize).")
    args = p.parse_args(argv)

    if args.task_mode == "synthesize":
        if not args.input_nonce:
            print("error: --input-nonce is required with --task-mode synthesize", file=sys.stderr)
            return 2
        return _run_synthesize(args)

    if args.effort is not None:
        print(
            f"note: --effort={args.effort!r} accepted but not yet wired through CLI_SPEC; ignored.",
            file=sys.stderr,
        )

    prompt = args.prompt_file.read_text()

    # Resolve fallback chain from flags (Drift 1 correction: use resolve_chain)
    fallback_disabled = False
    override_chain: list[str] | None = None
    if args.fallback_chain is not None:
        if args.fallback_chain == "":
            fallback_disabled = True
        else:
            override_chain = args.fallback_chain.split(",")

    chain = resolve_chain(
        args.cli,
        explicit_model=args.model,
        fallback_disabled=fallback_disabled,
        override_chain=override_chain,
    )

    # Build ReviewerState with correct fields (Drift 3: inspect fanout.ReviewerState)
    state = ReviewerState(
        cli=args.cli,
        adapter=make_adapter(args.cli),
    )

    # Pull capacity pattern for the CLI
    capacity_pattern = CAPACITY_PATTERNS.get(args.cli)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()

    result: ReviewerResult = asyncio.run(
        run_reviewer(
            args.cli,
            prompt,
            args.timeout,
            state,
            chain=chain,
            capacity_pattern=capacity_pattern,
            state_callback=None,
        )
    )
    duration = time.monotonic() - start

    review_path = args.out_dir / f"{args.cli}.md"
    review_path.write_text(result.text or "")

    # Drift 2: write "duration_seconds" in JSON (aggregate.py reads this key)
    state_path = args.out_dir / f"{args.cli}.state.json"
    state_path.write_text(json.dumps({
        "cli": result.cli,
        "ok": result.ok,
        "duration_seconds": duration,          # JSON key contract: aggregate reads this
        "attempts": result.attempts,
        "stderr_tail": result.stderr_tail,
        "usage": asdict(result.usage) if result.usage else None,
        "fallback_hops": max(0, len(result.attempts) - 1),
        "final_model": result.attempts[-1] if result.attempts else None,
    }, indent=2))

    print(json.dumps({
        "ok": result.ok,
        "review_path": str(review_path),
        "state_path": str(state_path),
    }))
    return 0 if result.ok else 1


def _run_synthesize(args) -> int:
    review_body = args.prompt_file.read_text()

    fallback_disabled = False
    override_chain: list[str] | None = None
    if args.fallback_chain is not None:
        if args.fallback_chain == "":
            fallback_disabled = True
        else:
            override_chain = args.fallback_chain.split(",")
    chain = resolve_chain(
        args.cli,
        explicit_model=args.model,
        fallback_disabled=fallback_disabled,
        override_chain=override_chain,
    )
    capacity_pattern = CAPACITY_PATTERNS.get(args.cli)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    ok, text, err, suggested, attempts = asyncio.run(
        run_synthesis(
            args.cli,
            review_body,
            args.input_nonce,
            args.model,
            args.timeout,
            chain=chain,
            capacity_pattern=capacity_pattern,
        )
    )
    duration = time.monotonic() - start

    synth_path = args.out_dir / "synth.txt"
    synth_path.write_text(text or "")
    state_path = args.out_dir / "synth.state.json"
    state_path.write_text(json.dumps({
        "cli": args.cli,
        "ok": ok,
        "duration_seconds": duration,
        "attempts": attempts,
        "stderr_tail": err,
        "usage": None,
        "fallback_hops": max(0, len(attempts) - 1),
        "final_model": attempts[-1] if attempts else None,
        "suggested_filename": suggested,
    }, indent=2))

    print(json.dumps({
        "ok": ok,
        "synth_path": str(synth_path),
        "state_path": str(state_path),
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
