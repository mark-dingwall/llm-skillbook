#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""multi-review v0.1 entry point — REMOVED.

v0.2 replaces this CLI with a Claude Code skill.
"""
import sys

BANNER = """\
multi_review.py v0.1 has been retired.

v0.2 ships as a Claude Code skill. Run `/multi-review` from inside Claude Code.

One-time install:
    uv run python -m multi_review.cli.setup --source-repo $(pwd)

Old CLI flags are now YAML prompt-file fields. See README.md for the schema.
The deprecation banner will be removed entirely in v0.3.
"""

def main() -> int:
    sys.stderr.write(BANNER)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
