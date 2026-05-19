# multi_review/cli/prepare.py
from __future__ import annotations
import argparse
import json
import secrets
import sys
from pathlib import Path
from multi_review.core.promptfile import load_promptfile
from multi_review.core.prompt import build_prompt

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--mode-override", default=None)
    args = p.parse_args(argv)

    pf = load_promptfile(args.prompt_file)
    mode = args.mode_override or pf.mode
    if mode == "both":
        print(json.dumps({"ok": False, "error": "prepare requires single mode (inline|reference), not both"}))
        return 2

    base = args.prompt_file.parent.resolve()

    def _norm(s: str) -> Path:
        p = Path(s)
        return p if p.is_absolute() else (base / p).resolve()

    nonce = secrets.token_hex(4)
    body = build_prompt(
        task=pf.task,
        files=[_norm(f) for f in pf.files],
        context_files=[_norm(f) for f in pf.context_files],
        custom_prompt=pf.custom_prompt,
        mode=mode,
        nonce=nonce,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = args.out_dir / "prompt.txt"
    prompt_path.write_text(body)
    print(json.dumps({"ok": True, "prompt_path": str(prompt_path), "nonce": nonce, "mode": mode}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
