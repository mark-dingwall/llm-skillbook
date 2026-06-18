from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from multi_review.core.snapshot import create_snapshot, diff_snapshot, cleanup_snapshot

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("create", "diff"):
        sp = sub.add_parser(name)
        sp.add_argument("--snapshot-dir", type=Path, required=True)
        sp.add_argument("--file", type=Path, action="append", default=[], required=(name == "diff"))
        sp.add_argument("--context-file", type=Path, action="append", default=[])
    cu = sub.add_parser("cleanup")
    cu.add_argument("--snapshot-dir", type=Path, required=True)
    args = p.parse_args(argv)

    if args.cmd == "create":
        create_snapshot(files=args.file, context_files=args.context_file, snapshot_dir=args.snapshot_dir)
        print(json.dumps({"ok": True, "snapshot_dir": str(args.snapshot_dir)}))
        return 0
    if args.cmd == "diff":
        d = diff_snapshot(files=args.file, context_files=args.context_file, snapshot_dir=args.snapshot_dir)
        print(json.dumps({
            "status": d.status,
            "changed_files": d.changed_files,
            "deleted_files": d.deleted_files,
            "unified_diffs": d.unified_diffs,
        }))
        return 0
    if args.cmd == "cleanup":
        cleanup_snapshot(args.snapshot_dir)
        print(json.dumps({"ok": True}))
        return 0
    return 2

if __name__ == "__main__":
    sys.exit(main())
