from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from multi_review.core.harvest import harvest_run

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--row-file", type=Path)
    grp.add_argument("--flush-pending", action="store_true")
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--pending-dir", type=Path,
                   default=Path.cwd() / ".multi-review" / "pending-harvest",
                   help="Directory scanned in --flush-pending mode.")
    args = p.parse_args(argv)
    args.log.parent.mkdir(parents=True, exist_ok=True)

    if args.flush_pending:
        files = sorted(args.pending_dir.glob("*.json")) if args.pending_dir.exists() else []
        flushed = 0
        for f in files:
            row = json.loads(f.read_text())
            try:
                harvest_run(log_path=args.log, row=row)
            except OSError as e:
                # Leave remaining pending files untouched (spec §12 denial behaviour).
                print(json.dumps({"ok": False, "error": str(e),
                                  "flushed": flushed,
                                  "remaining": len(files) - flushed}), file=sys.stderr)
                return 1
            f.unlink()
            flushed += 1
        print(json.dumps({"flushed": flushed, "remaining": 0}))
        return 0

    row = json.loads(args.row_file.read_text())
    harvest_run(log_path=args.log, row=row)
    print(json.dumps({"ok": True, "log": str(args.log)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
