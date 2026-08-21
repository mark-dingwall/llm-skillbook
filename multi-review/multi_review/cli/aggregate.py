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
from multi_review.cli.review_state import (
    failed_reviewer,
    read_review_body,
    read_state_file,
    result_from_state,
)
from multi_review.core.prompt import classify_synthesis_ok


def _load_synthesis(text_path: Path, state_path: Path | None) -> tuple[str | None, str | None]:
    if state_path is None:
        return None, "synthesis state file is required"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"invalid synthesis state: {exc}"
    if not isinstance(state, dict) or type(state.get("ok")) is not bool:
        return None, "invalid synthesis state: ok must be a boolean"
    error = state.get("error")
    if error is not None and not isinstance(error, str):
        return None, "invalid synthesis state: error must be a string or null"
    if not state["ok"]:
        return None, error or "synthesis failed"
    try:
        text = text_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return None, f"cannot read synthesis body: {exc}"
    ok, classification_error = classify_synthesis_ok(True, text)
    if not ok:
        return None, classification_error
    return text, None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Assemble REVIEW.md from per-reviewer .md + .state.json files.",
    )
    p.add_argument("--reviews-dir", type=Path, required=True,
                   help="Directory containing <cli>.md and <cli>.state.json files.")
    p.add_argument("--output", type=Path, required=True,
                   help="Destination path for REVIEW.md.")
    p.add_argument("--task", required=True,
                   help="Task type (code / design / …) — written to frontmatter.")
    p.add_argument("--synthesis-text-file", type=Path, default=None,
                   help="File containing synthesis/consensus text to embed.")
    p.add_argument("--synthesis-state-file", type=Path, default=None,
                   help="State file proving the synthesis body qualified.")
    p.add_argument("--prompt-file", default=None,
                   help="Path of the prompt file used — written to frontmatter.")
    p.add_argument("--reviewer", action="append", default=[],
                   help="Expected reviewer; repeat once for every requested slot.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite output file if it exists (default: auto-suffix).")
    args = p.parse_args(argv)

    results: list[ReviewerResult] = []
    reviewers_attempted = list(dict.fromkeys(args.reviewer)) or [
        state_path.name.removesuffix(".state.json")
        for state_path in sorted(args.reviews_dir.glob("*.state.json"))
    ]

    for cli in reviewers_attempted:
        state_path = args.reviews_dir / f"{cli}.state.json"
        review_md = args.reviews_dir / f"{cli}.md"
        review_text, body_error = read_review_body(review_md)
        state, state_error = read_state_file(state_path)
        if state_error is not None:
            results.append(failed_reviewer(cli, state_error, text=review_text))
        elif body_error is not None:
            results.append(failed_reviewer(cli, body_error, text=review_text))
        else:
            results.append(result_from_state(cli, state, review_text))

    synthesis_text: str | None = None
    synthesis_error: str | None = None
    if args.synthesis_text_file:
        synthesis_text, synthesis_error = _load_synthesis(
            args.synthesis_text_file, args.synthesis_state_file,
        )

    target = resolve_output_path(args.output, force=args.force)
    write_review_md(
        path=target,
        results=results,
        synthesis_text=synthesis_text,
        synthesis_error=synthesis_error,
        task=args.task,
        reviewers_attempted=reviewers_attempted,
        prompt_file=args.prompt_file,
    )

    print(json.dumps({"ok": True, "output_path": str(target)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
