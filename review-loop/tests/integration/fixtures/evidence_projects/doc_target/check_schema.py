"""Mechanical schema check: manifest.json must carry its required shape.

Repository-provided document gate (design: "existing mechanical checks such
as ... schema ... validation"). No third-party dependency -- a hand-rolled
required-keys/types check is enough for this fixture's bounded RED/GREEN
proof.
"""
import json
import sys
from pathlib import Path

REQUIRED = {"name": str, "version": int, "sections": list}


def main(manifest_path: str) -> int:
    data = json.loads(Path(manifest_path).read_text())
    for key, kind in REQUIRED.items():
        if key not in data or not isinstance(data[key], kind):
            print(f"manifest missing or mistyped key: {key}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
