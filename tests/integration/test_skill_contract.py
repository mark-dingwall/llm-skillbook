"""Guard against SKILL.md (and agents/*.md) drifting from the actual CLI.

The final v0.2 whole-branch review had to catch by hand that SKILL.md still
referenced a removed `--fallback-chain` flag and a nonexistent `cli.pending gc`
subcommand. This test fails the suite on that class of drift instead.

For every multi-review CLI invocation documented in the skill/agent markdown it
asserts (a) the referenced module resolves under multi_review/cli/, and (b) every
`--flag` token used is present in that command's `--help` output.

Design constraint: NO false positives. It is fine to skip exotic invocation forms
(false negatives ok), but the test must never fail on a flag that genuinely exists.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "multi-review" / "SKILL.md"
AGENTS_DIR = REPO / "agents"

# Subcommand-based CLIs: {module: {known subcommands}}. The subcommand token
# precedes its flags and must be forwarded to `--help`.
SUBCOMMAND_CLIS = {
    "snapshot": {"create", "diff", "cleanup"},
    "report": {"regen", "build-paired"},
}


def _script_alias_map() -> dict[str, str]:
    """Map console-script alias (mr-spawn) -> cli module name (spawn).

    Parsed from pyproject `[project.scripts]` with a line regex rather than a
    TOML lib (system interpreter may predate tomllib); the table entries are
    a stable `alias = "multi_review.cli.<mod>:main"` shape.
    """
    text = (REPO / "pyproject.toml").read_text()
    in_scripts = False
    out = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            in_scripts = s == "[project.scripts]"
            continue
        if not in_scripts:
            continue
        m = re.match(r'([A-Za-z0-9_-]+)\s*=\s*"multi_review\.cli\.([a-z_]+):', s)
        if m:
            out[m.group(1)] = m.group(2)
    return out


ALIASES = _script_alias_map()


def _fenced_blocks(text: str) -> list[str]:
    """Return the raw content of every ``` fenced code block."""
    blocks = []
    in_block = False
    buf: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if in_block:
                blocks.append("\n".join(buf))
                buf = []
            in_block = not in_block
            continue
        if in_block:
            buf.append(line)
    return blocks


def _join_continuations(block: str) -> list[str]:
    """Collapse backslash line-continuations into single logical lines."""
    logical: list[str] = []
    cur = ""
    for line in block.splitlines():
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            cur += stripped[:-1] + " "
        else:
            cur += stripped
            logical.append(cur)
            cur = ""
    if cur:
        logical.append(cur)
    return logical


# An invocation is either `... -m multi_review.cli.<mod> ...` or a `mr-*` alias.
_MODULE_RE = re.compile(r"-m\s+multi_review\.cli\.([a-z_]+)\b(.*)$")
_ALIAS_RE = re.compile(r"\b(mr-[a-z-]+)\b(.*)$")


def _iter_invocations(text: str):
    """Yield (module, rest_of_line) for each documented invocation."""
    for block in _fenced_blocks(text):
        for line in _join_continuations(block):
            m = _MODULE_RE.search(line)
            if m:
                yield m.group(1), m.group(2)
                continue
            a = _ALIAS_RE.search(line)
            if a and a.group(1) in ALIASES:
                yield ALIASES[a.group(1)], a.group(2)


def _tokens(rest: str) -> list[str]:
    return rest.split()


def _flags(rest: str) -> list[str]:
    # A real flag starts with `--` and is not an angle-bracket placeholder.
    out = []
    for t in _tokens(rest):
        if t.startswith("--") and "<" not in t and ">" not in t:
            out.append(t.split("=", 1)[0])
    return out


def _subcommand(module: str, rest: str) -> str | None:
    if module not in SUBCOMMAND_CLIS:
        return None
    for t in _tokens(rest):
        if t.startswith("--") or t.startswith("<"):
            continue
        if t in SUBCOMMAND_CLIS[module]:
            return t
        # first bareword that isn't a known subcommand -> stop looking
        break
    return None


def _help_flags(module: str, subcommand: str | None) -> set[str]:
    cmd = [sys.executable, "-m", f"multi_review.cli.{module}"]
    if subcommand:
        cmd.append(subcommand)
    cmd.append("--help")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    text = proc.stdout + proc.stderr
    return set(re.findall(r"--[a-z][a-z-]+", text))


def _doc_paths() -> list[Path]:
    paths = [SKILL]
    if AGENTS_DIR.is_dir():
        paths.extend(sorted(AGENTS_DIR.glob("*.md")))
    return [p for p in paths if p.is_file()]


def test_skill_modules_resolve():
    """Every referenced cli.<module> exists importably under multi_review/cli/."""
    seen = set()
    for path in _doc_paths():
        for module, _ in _iter_invocations(path.read_text()):
            seen.add(module)
    assert seen, "no CLI invocations found — parser or docs regressed"
    for module in sorted(seen):
        assert (REPO / "multi_review" / "cli" / f"{module}.py").is_file(), (
            f"SKILL/agent references multi_review.cli.{module} which does not exist"
        )


def test_skill_flags_exist():
    """Every --flag in a documented invocation is a real flag of that command."""
    # cache help output per (module, subcommand)
    help_cache: dict[tuple[str, str | None], set[str]] = {}
    for path in _doc_paths():
        for module, rest in _iter_invocations(path.read_text()):
            sub = _subcommand(module, rest)
            key = (module, sub)
            if key not in help_cache:
                help_cache[key] = _help_flags(module, sub)
            valid = help_cache[key]
            for flag in _flags(rest):
                assert flag in valid, (
                    f"{path.name}: multi_review.cli.{module}"
                    f"{(' ' + sub) if sub else ''} references {flag} "
                    f"which is not a recognized flag (help: {sorted(valid)})"
                )
