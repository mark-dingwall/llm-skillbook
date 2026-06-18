"""mr-write-harvest-row — read state.json files + REVIEW.md + prompt-file,
build a v2 harvest row, append to --log (or fall back to pending-harvest)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from multi_review.core.adapters import Usage
from multi_review.core.fanout import ReviewerResult
from multi_review.core.harvest import build_row, derive_project


def _iso_utc(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _state_to_result(state: dict) -> ReviewerResult:
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
    return ReviewerResult(
        cli=state["cli"],
        ok=state.get("ok", False),
        text="",
        stderr_tail=state.get("stderr_tail", ""),
        usage=usage,
        elapsed=state.get("duration_seconds", 0.0),
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

    # Derive timestamps: prefer started_at/finished_at fields written into state
    # by the SKILL; fall back to state-file mtime.
    started_ts: float | None = None
    finished_ts: float | None = None
    for sf in sorted(args.state_dir.glob("*.state.json")):
        try:
            s = json.loads(sf.read_text())
        except Exception:
            continue
        # Prefer explicit ISO fields; fall back to file mtime.
        if "started_at" in s:
            import datetime
            t = datetime.datetime.fromisoformat(s["started_at"].rstrip("Z")).replace(
                tzinfo=datetime.timezone.utc
            ).timestamp()
            started_ts = min(started_ts, t) if started_ts is not None else t
        else:
            mtime = sf.stat().st_mtime
            started_ts = min(started_ts, mtime) if started_ts is not None else mtime

        if "finished_at" in s:
            import datetime
            t = datetime.datetime.fromisoformat(s["finished_at"].rstrip("Z")).replace(
                tzinfo=datetime.timezone.utc
            ).timestamp()
            finished_ts = max(finished_ts, t) if finished_ts is not None else t
        else:
            mtime = sf.stat().st_mtime
            finished_ts = max(finished_ts, mtime) if finished_ts is not None else mtime

    now = time.time()
    started_at_iso = _iso_utc(started_ts) if started_ts is not None else _iso_utc(now)
    finished_at_iso = _iso_utc(finished_ts) if finished_ts is not None else _iso_utc(now)
    wall_seconds = (finished_ts - started_ts) if (started_ts is not None and finished_ts is not None) else 0.0

    results = [_state_to_result(s) for s in states if "cli" in s and not s.get("cli") == "synth"]

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
        argv=sys.argv,
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
