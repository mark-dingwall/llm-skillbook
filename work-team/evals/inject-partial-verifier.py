#!/usr/bin/env python3
"""Create an eval-only verifier return missing its final candidate.

usage: inject-partial-verifier.py <complete.json> <partial.json>
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source, destination = map(Path, sys.argv[1:])
    try:
        if source.resolve() == destination.resolve():
            sys.exit("partial output must not overwrite the complete return")
        if destination.exists():
            sys.exit("refusing to overwrite existing partial output")
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        sys.exit(f"cannot read complete verifier return: {error}")
    candidates = value.get("candidates") if isinstance(value, dict) else None
    if not isinstance(candidates, list) or len(candidates) < 2:
        sys.exit("complete verifier return must contain at least two candidates")
    value["candidates"] = candidates[:-1]
    try:
        destination.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as error:
        sys.exit(f"cannot write partial verifier return: {error}")


if __name__ == "__main__":
    main()
