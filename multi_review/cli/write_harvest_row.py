"""mr-write-harvest-row — read state.json files + REVIEW.md + prompt-file,
build a v2 harvest row, append to --log (or fall back to pending-harvest)."""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

from multi_review.core.adapters import Usage
from multi_review.core.fanout import ReviewerResult
from multi_review.core.harvest import build_row, derive_project
from multi_review.core.prompt import classify_review_ok


def _state_to_result(state: dict, review_text: str = "") -> ReviewerResult:
    usage_raw = state.get("usage")
    if usage_raw is not None:
        usage = Usage(
            input_tokens=usage_raw.get("input_tokens", 0),
            output_tokens=usage_raw.get("output_tokens", 0),
            cached_tokens=usage_raw.get("cached_tokens", 0),
            tool_calls=usage_raw.get("tool_calls", 0),
        )
    else:
        usage = None
    # Shared classifier — same success decision aggregate applies, so runs.jsonl
    # and REVIEW.md can never disagree about a reviewer's success (I2).
    ok, _ = classify_review_ok(state.get("ok", False), review_text)
    return ReviewerResult(
        cli=state["cli"],
        ok=ok,
        text="",
        stderr_tail=state.get("stderr_tail", ""),
        usage=usage,
        elapsed=state.get("duration_seconds") or 0.0,
        model_used=state.get("final_model"),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Build a v2 harvest row from reviewer state files and append to --log.",
    )
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--out-review", type=Path, required=True)
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--mode", choices=["inline", "reference"], required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--pair-id", default=None)
    p.add_argument("--drift-status", default="clean",
                   choices=["clean", "drifted", "unchecked", "skipped", "not_applicable"])
    p.add_argument("--synthesizer", default=None)
    p.add_argument("--synthesis-ok", action="store_true", default=False)
    p.add_argument("--prompt-format-version", type=int, default=1)
    args = p.parse_args(argv)

    states: list[dict] = []
    for sf in sorted(args.state_dir.glob("*.state.json")):
        try:
            states.append(json.loads(sf.read_text()))
        except Exception as e:
            print(f"warning: skipping malformed {sf}: {e}", file=sys.stderr)

    # Derive timestamps from explicit ISO fields written by the SKILL.
    # spawn.py and write_task_result.py do not write started_at/finished_at today,
    # so these will be None for most runs. mtime fallback was removed (it produced
    # wrong data — mtime reflects reviewer finish time, not start time).
    # v0.2.1 will plumb proper argv + timestamps via dedicated CLI args.
    def _parse_iso(s: str) -> float:
        return datetime.datetime.fromisoformat(s.rstrip("Z")).replace(
            tzinfo=datetime.timezone.utc
        ).timestamp()

    started_ts: float | None = None
    finished_ts: float | None = None
    for s in states:
        if "started_at" in s:
            t = _parse_iso(s["started_at"])
            started_ts = min(started_ts, t) if started_ts is not None else t
        if "finished_at" in s:
            t = _parse_iso(s["finished_at"])
            finished_ts = max(finished_ts, t) if finished_ts is not None else t

    def _to_iso(ts: float) -> str:
        return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")

    started_at_iso = _to_iso(started_ts) if started_ts is not None else None
    finished_at_iso = _to_iso(finished_ts) if finished_ts is not None else None
    wall_seconds = (finished_ts - started_ts) if (started_ts is not None and finished_ts is not None) else None

    def _review_text(cli: str) -> str:
        md = args.state_dir / f"{cli}.md"
        return md.read_text() if md.exists() else ""

    results = [
        _state_to_result(s, _review_text(s["cli"]))
        for s in states if "cli" in s and not s.get("cli") == "synth"
    ]

    prompt_bytes = len(args.prompt_file.read_bytes()) if args.prompt_file.exists() else 0
    output_bytes = len(args.out_review.read_bytes()) if args.out_review.exists() else 0

    reviewers_attempted = [r.cli for r in results]

    row = build_row(
        results=results,
        run_id=args.run_id,
        started_at=started_at_iso,
        finished_at=finished_at_iso,
        wall_seconds=wall_seconds,
        cwd=str(Path.cwd()),
        prompt_bytes=prompt_bytes,
        output_bytes=output_bytes,
        mode=args.mode,
        task=args.task,
        project=args.project,
        reviewers_attempted=reviewers_attempted,
        synthesizer=args.synthesizer,
        synthesis_ok=args.synthesis_ok,
        pair_id=args.pair_id,
        prompt_file=str(args.prompt_file),
        prompt_format_version=args.prompt_format_version,
        drift_status=args.drift_status,
        telemetry_notes=[],
    )

    try:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return 0
    except (PermissionError, OSError) as e:
        pending = Path.cwd() / ".multi-review" / "pending-harvest"
        pending.mkdir(parents=True, exist_ok=True)
        (pending / f"{args.run_id}.json").write_text(json.dumps(row))
        print(f"note: central log unwritable ({e}); buffered to {pending}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
