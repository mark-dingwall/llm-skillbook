from __future__ import annotations
import argparse, json, sys
from dataclasses import asdict
from pathlib import Path
from multi_review.core.pending import (
    PendingPair, write_meta, read_meta, transition_status, sweep_expired, list_pending,
)

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    wr = sub.add_parser("write"); wr.add_argument("--pending-dir", type=Path, required=True); wr.add_argument("--meta-file", type=Path, required=True)
    rd = sub.add_parser("read"); rd.add_argument("--pending-dir", type=Path, required=True); rd.add_argument("--pair-id", required=True)
    tr = sub.add_parser("transition"); tr.add_argument("--pending-dir", type=Path, required=True); tr.add_argument("--pair-id", required=True); tr.add_argument("--from", dest="expected", required=True); tr.add_argument("--to", dest="new", required=True)
    gc = sub.add_parser("gc"); gc.add_argument("--pending-dir", type=Path, required=True)
    ls = sub.add_parser("list"); ls.add_argument("--pending-dir", type=Path, required=True)
    args = p.parse_args(argv)
    if args.cmd == "write":
        data = json.loads(args.meta_file.read_text())
        meta = PendingPair(**data)
        write_meta(args.pending_dir, meta)
        print(json.dumps({"ok": True, "pair_id": meta.pair_id})); return 0
    if args.cmd == "read":
        print(json.dumps(asdict(read_meta(args.pending_dir, args.pair_id)))); return 0
    if args.cmd == "transition":
        ok = transition_status(args.pending_dir, args.pair_id, expected=args.expected, new=args.new)
        print(json.dumps({"ok": ok})); return 0 if ok else 1
    if args.cmd == "gc":
        print(json.dumps({"swept": sweep_expired(args.pending_dir)})); return 0
    if args.cmd == "list":
        print(json.dumps([asdict(m) for m in list_pending(args.pending_dir)])); return 0
    return 2

if __name__ == "__main__":
    sys.exit(main())
