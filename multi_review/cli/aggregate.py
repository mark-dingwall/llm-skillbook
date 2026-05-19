"""multi_review.cli.aggregate — assemble REVIEW.md from per-reviewer state files.

Reads <reviews_dir>/<cli>.md and <reviews_dir>/<cli>.state.json for every
*.state.json file found, reconstructs ReviewerResult objects, then delegates
to write_review_md.

Prints a JSON summary to stdout: {"ok": bool, "output_path": str}
Exit code: always 0 (write errors raise SystemExit internally).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from multi_review.core.aggregate import write_review_md, resolve_output_path
from multi_review.core.fanout import ReviewerResult
from multi_review.core.adapters import Usage


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Assemble REVIEW.md from per-reviewer .md + .state.json files.",
    )
    p.add_argument("--reviews-dir", type=Path, required=True,
                   help="Directory containing <cli>.md and <cli>.state.json files.")
    p.add_argument("--output", type=Path, required=True,
                   help="Destination path for REVIEW.md.")
    p.add_argument("--mode", required=True,
                   help="Review mode (inline / reference) — written to frontmatter.")
    p.add_argument("--task", required=True,
                   help="Task type (code / design / …) — written to frontmatter.")
    p.add_argument("--synthesis-text-file", type=Path, default=None,
                   help="File containing synthesis/consensus text to embed.")
    p.add_argument("--pair-id", default=None,
                   help="Pair identifier for paired-run tracking.")
    p.add_argument("--prompt-file", default=None,
                   help="Path of the prompt file used — written to frontmatter.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite output file if it exists (default: auto-suffix).")
    args = p.parse_args(argv)

    results: list[ReviewerResult] = []
    reviewers_attempted: list[str] = []

    for state_path in sorted(args.reviews_dir.glob("*.state.json")):
        cli = state_path.name.removesuffix(".state.json")
        reviewers_attempted.append(cli)
        state = json.loads(state_path.read_text())

        review_md = args.reviews_dir / f"{cli}.md"
        review_text = review_md.read_text() if review_md.exists() else ""

        usage: Usage | None = None
        if state.get("usage"):
            usage = Usage(**state["usage"])

        # Drift 2: state JSON uses "duration_seconds"; ReviewerResult field is "elapsed"
        results.append(ReviewerResult(
            cli=cli,
            ok=state["ok"],
            text=review_text,
            stderr_tail=state.get("stderr_tail", ""),
            attempts=state.get("attempts", []),
            usage=usage,
            elapsed=state.get("duration_seconds", 0.0),  # map JSON key → dataclass field
        ))

    synthesis_text: str | None = None
    if args.synthesis_text_file:
        synthesis_text = args.synthesis_text_file.read_text()

    target = resolve_output_path(args.output, force=args.force)
    write_review_md(
        path=target,
        results=results,
        synthesis_text=synthesis_text,
        mode=args.mode,
        task=args.task,
        reviewers_attempted=reviewers_attempted,
        pair_id=args.pair_id,
        prompt_file=args.prompt_file,
    )

    print(json.dumps({"ok": True, "output_path": str(target)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
