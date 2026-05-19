from __future__ import annotations
import argparse, shutil, subprocess, sys
from pathlib import Path
from multi_review.core.pending import read_meta

def _notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", title, body], check=False); return
    if shutil.which("osascript"):
        subprocess.run(["osascript", "-e", f'display notification "{body}" with title "{title}"'], check=False); return
    if shutil.which("wsl-notify-send"):
        subprocess.run(["wsl-notify-send", "--category", title, body], check=False); return
    # Fall back to stderr — visible if the user is watching.
    sys.stderr.write(f"{title}: {body}\n")

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pending-dir", type=Path, required=True)
    p.add_argument("--pair-id", required=True)
    args = p.parse_args(argv)
    try:
        meta = read_meta(args.pending_dir, args.pair_id)
    except FileNotFoundError:
        return 0  # pair already gc'd; nothing to notify.
    if meta.status != "awaiting-pass-2":
        return 0
    _notify("multi-review cooldown elapsed", f"Resume pass 2: /multi-review --resume-pair {args.pair_id}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
