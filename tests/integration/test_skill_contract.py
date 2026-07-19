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


def _builder_defaults_section() -> str:
    """The `## Defaults` section only, up to the next heading.

    Scoping matters: an unscoped document-wide search could match a
    default-looking bullet elsewhere while the real autonomous default quietly
    gained grok.
    """
    text = (AGENTS_DIR / "multi-review-build.md").read_text()
    m = re.search(r"^## Defaults$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert m, "builder agent lost its `## Defaults` section"
    return m.group(1)


def test_builder_autonomous_default_matches_DEFAULT_REVIEWERS():
    """The builder agent's autonomous (--use-defaults) reviewer list is the
    SOURCE OF the live opt-in enforcement point: resolve_reviewers has no caller
    outside tests, and an explicit `reviewers` list in the authored YAML bypasses
    fill_defaults entirely. If someone adds grok to that prose list, opt-in is
    silently dead and every Python test still passes. This is the guard.

    Scope caveat: this asserts the REPO copy. `setup.py` copies agents into
    ~/.claude (symlinks only under --dev), so a stale install can still differ.
    That is a deployment concern, covered by the reinstall step in
    tests/manual/grok-smoke.md, not something this test can see.
    """
    from multi_review.core.reviewers import DEFAULT_REVIEWERS
    section = _builder_defaults_section()
    matches = re.findall(r"^- reviewers: \[([^\]]*)\]\s*$", section, re.MULTILINE)
    assert len(matches) == 1, (
        f"expected exactly one `- reviewers: [...]` default line, found {len(matches)}"
    )
    listed = [s.strip() for s in matches[0].split(",") if s.strip()]
    assert listed == DEFAULT_REVIEWERS, (
        f"builder autonomous default {listed} != DEFAULT_REVIEWERS {DEFAULT_REVIEWERS}"
    )


def test_builder_lists_grok_as_a_valid_synthesizer_choice():
    """grok must be nameable by the builder even though it is never a default.

    Tokenised, not a substring test: `"grok" in line` would also be satisfied by
    text like `grok-disabled`.
    """
    text = (AGENTS_DIR / "multi-review-build.md").read_text()
    m = re.search(r"^synthesizer: (.+)$", text, re.MULTILINE)
    assert m, "builder schema lost its synthesizer choice line"
    choices = {c.strip() for c in m.group(1).split("|")}
    assert "grok" in choices, f"grok missing from synthesizer choices {choices}"
    assert "none" in choices


def test_skill_dispatch_binds_to_resolved_reviewers():
    """The reviewer-selecting steps must name the validated set, not an
    unqualified `reviewers` that an LLM orchestrator could satisfy from the
    known/probed list — which contains opt-in grok.

    Pins the three sites that actually SELECT what runs. The remaining
    Task 4 edits (claude-inclusion note, pass-2 back-reference, closing rules)
    are consistency edits, not selection sites, and are deliberately not
    pinned — literal-string assertions on prose are a false-positive source,
    and this file's stated design constraint is NO false positives.
    """
    text = SKILL.read_text()
    # 1. Fanout: which reviewers get dispatched.
    assert "every non-claude reviewer in `resolved.reviewers`" in text, (
        "SKILL.md Step 5 fanout instruction lost its resolved-set qualifier"
    )
    # 2. Synthesis: which CLI runs the consensus pass, and with which model.
    assert "resolved.synthesizer" in text, (
        "SKILL.md Step 6 must select the synthesizer from the resolved object"
    )
    assert "resolved.models[resolved.synthesizer]" in text, (
        "SKILL.md Step 6 synthesis model lookup lost its resolved qualifier"
    )
    # 3. Resume: pass 2 must reuse pass 1's resolved set, not re-derive it.
    assert "pending/<pair_id>/prompt-source.txt" in text, (
        "SKILL.md resume path must read the prompt pointer pass 1 persisted"
    )
