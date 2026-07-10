# multi_review/cli/validate_prompt.py
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from multi_review.core.promptfile import load_promptfile, ValidationError

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path", type=Path)
    args = p.parse_args(argv)
    try:
        pf = load_promptfile(args.path)
    except ValidationError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    print(json.dumps({"ok": True, "resolved": asdict(pf)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
