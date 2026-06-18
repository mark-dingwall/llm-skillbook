"""multi_review.cli.write_task_result — host-side state writer for Task-subagent reviewers.

When a reviewer or synthesizer runs inside a Claude Code Task subagent, the agent
returns its review markdown directly in its final assistant message (agent
definitions don't grant Write). The host captures that text, persists it via a
Bash heredoc, then invokes this CLI to mirror the subprocess shape produced by
spawn.py — a sibling <name>.md (or synth.txt) and <name>.state.json.

Output JSON: {"ok": true, "review_path": "...", "state_path": "..."}
  or         {"ok": true, "synth_path": "...", "state_path": "..."}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Persist a Task-subagent reviewer/synthesizer return value as state.json + body.",
    )
    p.add_argument("--cli", required=True,
                   help="Reviewer CLI name (e.g. claude) or 'synth' marker.")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--text-file", type=Path, required=True,
                   help="File on disk holding the agent's returned text.")
    p.add_argument("--duration-seconds", type=float, required=True)
    p.add_argument("--task-mode", choices=["review", "synthesize"], required=True)
    p.add_argument("--model", default=None,
                   help="Model identifier from the agent frontmatter; defaults to '<default>'.")
    args = p.parse_args(argv)

    text = args.text_file.read_text()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_attempt = args.model or "<default>"

    if args.task_mode == "review":
        review_path = args.out_dir / f"{args.cli}.md"
        review_path.write_text(text)
        state_path = args.out_dir / f"{args.cli}.state.json"
        state_path.write_text(json.dumps({
            "cli": args.cli,
            "ok": True,
            "duration_seconds": args.duration_seconds,
            "attempts": [model_attempt],
            "stderr_tail": "",
            "usage": None,
            "final_model": args.model,
        }, indent=2))
        print(json.dumps({
            "ok": True,
            "review_path": str(review_path),
            "state_path": str(state_path),
        }))
        return 0

    synth_path = args.out_dir / "synth.txt"
    synth_path.write_text(text)
    state_path = args.out_dir / "synth.state.json"
    state_path.write_text(json.dumps({
        "cli": args.cli,
        "ok": True,
        "duration_seconds": args.duration_seconds,
        "attempts": [model_attempt],
        "stderr_tail": "",
        "usage": None,
        "final_model": args.model,
        "suggested_filename": None,
    }, indent=2))
    print(json.dumps({
        "ok": True,
        "synth_path": str(synth_path),
        "state_path": str(state_path),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
