"""multi_review.cli.spawn — single-reviewer subprocess runner.

Invokes one external reviewer CLI, streams its output through the relevant
ProgressAdapter, and writes two files into --out-dir:
  <cli>.md         — the review text
  <cli>.state.json — metadata for aggregate.py to consume

Prints a JSON summary to stdout: {"ok": bool, "review_path": str, "state_path": str}
Exit code: 0 if reviewer succeeded, 1 if it failed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from multi_review.core.fanout import ReviewerState, ReviewerResult, run_reviewer
from multi_review.core.reviewers import ALL_REVIEWERS, CLI_SPEC, make_adapter
from multi_review.core.synthesis import run_synthesis


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run one reviewer CLI, write review + state JSON.",
    )
    p.add_argument("--cli", choices=ALL_REVIEWERS, required=True)
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--model", default=None,
                   help="Pin to a specific model (a NanoGPT family for pykrete); "
                        "absent = CLI default.")
    p.add_argument("--task", default=None,
                   help="Prompt task preset (code/plan/security/generic/custom); "
                        "forwarded to CLIs that declare a task_flag (pykrete).")
    p.add_argument("--timeout", type=int, default=None,
                   help="Seconds before killing reviewer subprocess.")
    p.add_argument("--task-mode", choices=["review", "synthesize"], default="review")
    p.add_argument("--input-nonce", default=None,
                   help="Nonce token used in the synthesis review-body tags "
                        "(required with --task-mode synthesize).")
    try:
        args = p.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    if args.task_mode == "synthesize":
        if not args.input_nonce:
            print("error: --input-nonce is required with --task-mode synthesize", file=sys.stderr)
            return 2
        return _run_synthesize(args)

    prompt = args.prompt_file.read_text()

    state = ReviewerState(
        cli=args.cli,
        adapter=make_adapter(args.cli),
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()

    result: ReviewerResult = asyncio.run(
        run_reviewer(
            args.cli,
            prompt,
            model=args.model,
            timeout=args.timeout,
            state=state,
            state_callback=None,
            prompt_path=args.prompt_file,
            task=args.task,
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
        "stderr_tail": result.stderr_tail,
        "usage": asdict(result.usage) if result.usage else None,
        "final_model": result.model_used,
        "downgraded": result.downgraded,
        "error": result.error,
    }, indent=2))

    print(json.dumps({
        "ok": result.ok,
        "review_path": str(review_path),
        "state_path": str(state_path),
    }))
    return 0 if result.ok else 1


def _run_synthesize(args) -> int:
    review_body = args.prompt_file.read_text()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    ok, text, err, suggested, attempts = asyncio.run(
        run_synthesis(
            args.cli,
            review_body,
            args.input_nonce,
            args.model,
            args.timeout,
        )
    )
    duration = time.monotonic() - start

    synth_path = args.out_dir / "synth.txt"
    synth_path.write_text(text or "")
    final_model = attempts[-1] if attempts else None
    # Same honesty rule as fanout.py's records_family_not_model branch: a
    # NanoGPT family (pykrete's "model") must never be presented as if it
    # were the actual model.
    if CLI_SPEC[args.cli].get("records_family_not_model") and args.model is not None:
        final_model = f"family:{args.model}"
    state_path = args.out_dir / "synth.state.json"
    state_path.write_text(json.dumps({
        "cli": args.cli,
        "ok": ok,
        "duration_seconds": duration,
        "stderr_tail": err,
        "usage": None,
        "final_model": final_model,
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
