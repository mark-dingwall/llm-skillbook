#!/usr/bin/env python3
"""A codex stand-in whose `exec --help` output is missing required flags.

Used only to prove `preflight_codex_mapping` stops before dispatch when a
required flag is absent from the probe output.
"""
from __future__ import annotations

import sys

HELP_TEXT = """Run Codex non-interactively

Usage: codex exec [OPTIONS] [PROMPT]

Options:
  -s, --sandbox <SANDBOX_MODE>
  -C, --cd <DIR>
  -h, --help
"""


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "exec" and argv[2] == "--help":
        sys.stdout.write(HELP_TEXT)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
