from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from multi_review.core.aggregate import resolve_output_path
from multi_review.core.report import render_experiments_markdown, build_paired_report

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    rg = sub.add_parser("regen")
    rg.add_argument("--log", type=Path, required=True)
    rg.add_argument("--reports-dir", type=Path, required=True)
    rg.add_argument("--output", type=Path, required=True)

    bp = sub.add_parser("build-paired")
    bp.add_argument("--log", type=Path, required=True)
    bp.add_argument("--pair-id", required=True)
    bp.add_argument("--out-dir", type=Path, required=True)
    bp.add_argument("--project", required=True)
    bp.add_argument("--date", required=True)
    bp.add_argument("--headline-file", type=Path, default=None)
    bp.add_argument("--mode-divergence-file", type=Path, default=None)
    bp.add_argument("--per-reviewer-notes-file", type=Path, default=None)

    args = p.parse_args(argv)

    if args.cmd == "regen":
        md = render_experiments_markdown(log_path=args.log, reports_dir=args.reports_dir)
        args.output.write_text(md)
        print(json.dumps({"ok": True, "output": str(args.output)}))
        return 0

    if args.cmd == "build-paired":
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out_path = resolve_output_path(args.out_dir / f"{args.project}-{args.date}-{args.pair_id}.md")
        def _read(p): return p.read_text() if p else None
        build_paired_report(
            log_path=args.log, pair_id=args.pair_id, out_path=out_path,
            headline=_read(args.headline_file),
            mode_divergence=_read(args.mode_divergence_file),
            per_reviewer_notes=_read(args.per_reviewer_notes_file),
        )
        print(json.dumps({"ok": True, "output": str(out_path)}))
        return 0
    return 2

if __name__ == "__main__":
    sys.exit(main())
