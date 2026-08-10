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


def test_skill_has_no_deprecated_workflow_content():
    """The v0.3 skill contract is single-pass only."""
    skill = SKILL.read_text()
    deprecated = {
        "mode: both",
        "write_harvest_row",
        "snapshot create",
        "if_drift: ask",
        "pending/<pair_id>",
        "build-paired",
        "harvested",
        "comparison eligibility",
        "TaskGet",
        "## Comparison workflow deprecation",
    }
    for content in deprecated:
        assert content not in skill, (
            f"SKILL.md retains deprecated workflow content: {content!r}"
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


def test_builder_autonomous_default_synthesizer_is_claude():
    """Companion guard to the reviewers pin above: the SYNTHESIZER is the
    other opt-in dimension. Nothing pins `## Defaults`' `- synthesizer: ...`
    line, so changing it to grok would auto-select grok as the consensus
    synthesizer in every `--use-defaults` build with the suite green."""
    section = _builder_defaults_section()
    matches = re.findall(r"^- synthesizer: (\S+)\s*$", section, re.MULTILINE)
    assert len(matches) == 1, (
        f"expected exactly one `- synthesizer: ...` default line, found {len(matches)}"
    )
    assert matches[0] == "claude", (
        f"builder autonomous synthesizer default {matches[0]!r} != 'claude'"
    )


def _builder_schema_block() -> str:
    """The fenced schema-template code block near the top of the builder agent
    file — this is what drives INTERACTIVE mode's authored YAML, where
    `## Defaults` (autonomous-mode only) never applies. The final whole-branch
    review found that adding grok to this block's `reviewers: [...]` line
    would leave the whole suite green, since only the `## Defaults` bullet was
    pinned. This is the companion guard.
    """
    text = (AGENTS_DIR / "multi-review-build.md").read_text()
    blocks = _fenced_blocks(text)
    assert blocks, "builder agent lost its schema fenced block"
    return blocks[0]


def test_builder_schema_prompt_format_version_is_current(tmp_path):
    from multi_review.core.promptfile import fill_defaults, validate

    block = _builder_schema_block()
    matches = re.findall(r"^prompt_format_version:\s*(\d+)\s*$", block, re.MULTILINE)
    assert matches == ["2"]

    source = tmp_path / "subject.py"
    source.write_text("")
    pf = fill_defaults({
        "prompt_format_version": int(matches[0]),
        "task": "code",
        "files": [str(source)],
    })
    validate(pf, base_dir=tmp_path)


def test_builder_schema_reviewers_line_matches_DEFAULT_REVIEWERS():
    """Pins the schema block's `reviewers: [...]` template line, not just the
    `## Defaults` bullet — see `_builder_schema_block` for why both are needed.

    Asserts there is exactly ONE `reviewers:` line in the block (same
    uniqueness pattern as the `## Defaults` guards above): `next(...)` alone
    would keep matching the first, legitimate line even if a contradictory
    `reviewers: [grok]` line were appended below it in the same block, leaving
    the builder agent with two conflicting instructions and this test green.
    """
    from multi_review.core.reviewers import DEFAULT_REVIEWERS
    block = _builder_schema_block()
    lines = [l for l in block.splitlines() if l.strip().startswith("reviewers:")]
    assert len(lines) == 1, (
        f"expected exactly one `reviewers: [...]` line in the schema block, found {len(lines)}"
    )
    line = lines[0].split("#", 1)[0]  # strip trailing comment before parsing the list
    m = re.search(r"\[([^\]]*)\]", line)
    assert m, f"builder schema reviewers line has no [...] list: {line!r}"
    listed = [s.strip() for s in m.group(1).split(",") if s.strip()]
    assert listed == DEFAULT_REVIEWERS, (
        f"builder schema reviewers template {listed} != DEFAULT_REVIEWERS {DEFAULT_REVIEWERS}"
    )


def test_builder_lists_grok_as_a_valid_synthesizer_choice():
    """grok must be nameable by the builder even though it is never a default.

    Tokenised, not a substring test: `"grok" in line` would also be satisfied by
    text like `grok-disabled`.

    Scoped to the schema block (see `_builder_schema_block`) and asserting
    there is exactly ONE `synthesizer:` line in it — same uniqueness pattern
    as the `reviewers:` guard above. An unscoped `re.search` over the whole
    document would find only the first match and stay green even if a
    contradictory `synthesizer: grok` line were appended inside the block.
    """
    block = _builder_schema_block()
    lines = [l for l in block.splitlines() if l.strip().startswith("synthesizer:")]
    assert len(lines) == 1, (
        f"expected exactly one `synthesizer: ...` line in the schema block, found {len(lines)}"
    )
    choices = {c.strip() for c in lines[0].split(":", 1)[1].split("|")}
    assert "grok" in choices, f"grok missing from synthesizer choices {choices}"
    assert "none" in choices


def _skill_step_section(step_num: int) -> str:
    """The body of `### Step <n> — ...` up to (not including) the next heading
    of depth 1-3. Same scoping idea as `_builder_defaults_section`: an
    unscoped substring search can stay green while the actual selection site
    is deleted, as long as the string survives somewhere else in the file
    (e.g. a later "Notes on ..." section, or a different step that merely
    reads what this step writes).
    """
    text = SKILL.read_text()
    m = re.search(
        rf"^### Step {step_num}\b[^\n]*\n(.*?)(?=^#{{1,3}} |\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    assert m, f"SKILL.md missing Step {step_num} section"
    return m.group(1)


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
    # 1. Fanout: which reviewers get dispatched.
    step5 = _skill_step_section(5)
    assert "every non-claude reviewer in `resolved.reviewers`" in step5, (
        "SKILL.md Step 5 fanout instruction lost its resolved-set qualifier"
    )
    # 2. Synthesis: which CLI runs the consensus pass, and with which model.
    # Scoped to Step 6 itself: "resolved.synthesizer" also appears in the
    # closing "Notes on `claude` not in reviewers" section, so an unscoped
    # search would stay green even if Step 6's own selection logic regressed.
    step6 = _skill_step_section(6)
    assert "resolved.synthesizer" in step6, (
        "SKILL.md Step 6 must select the synthesizer from the resolved object"
    )
    assert "resolved.models[resolved.synthesizer]" in step6, (
        "SKILL.md Step 6 synthesis model lookup lost its resolved qualifier"
    )
    # The substring "resolved.synthesizer" alone would still appear in the
    # <SYNTH_MODEL_FLAG> line even if the actual --cli dispatch were mutated
    # to a hardcoded CLI (e.g. "--cli grok"). Pin the literal dispatch token.
    assert "--cli <resolved.synthesizer>" in step6, (
        "SKILL.md Step 6 synthesis dispatch lost its --cli <resolved.synthesizer> binding"
    )
def test_skill_step2_pins_resolved_sole_source_provenance():
    """Step 5/6 above trust `resolved.<field>` blindly — none of those
    assertions can see WHERE `resolved` comes from. A rewrite of Step 2 that
    replaced `resolved.reviewers` with `ALL_REVIEWERS` and `resolved.synthesizer`
    with `grok` before dispatch would leave test_skill_dispatch_binds_to_resolved_reviewers
    green, since Step 5/6 would then faithfully dispatch the poisoned values.

    Pins a small set of stable, governing substrings from Step 2's provenance
    sentence — not the whole sentence, which would be brittle to harmless
    rewording.
    """
    step2 = _skill_step_section(2)
    assert "validate_prompt" in step2, (
        "SKILL.md Step 2 lost the validate_prompt provenance for `resolved`"
    )
    assert "sole" in step2, (
        "SKILL.md Step 2 lost the 'sole source' framing for `resolved`"
    )
    assert "Never derive a run set from" in step2, (
        "SKILL.md Step 2 lost the prohibition on deriving a run set"
    )
    assert "ALL_REVIEWERS" in step2, (
        "SKILL.md Step 2 lost the ALL_REVIEWERS prohibition"
    )


def test_skill_step2_all_reviewers_mentioned_only_once():
    """Narrow tripwire for the additive-contradiction failure mode: appending
    a sentence like "After validation, replace `resolved.reviewers` with
    `ALL_REVIEWERS` ..." after the legitimate prohibition above leaves every
    presence-only assertion in this file green, because none of them check
    that the governing sentence is the ONLY thing Step 2 says about
    `ALL_REVIEWERS`.

    This does NOT guarantee Step 2 is free of contradictions in general — a
    rewrite that poisons the run set without re-mentioning the literal token
    `ALL_REVIEWERS` (or that poisons `resolved.synthesizer` some other way)
    would not be caught here. It only catches the one reproduced mutation
    that happens to add a second mention of this specific token, which is
    cheap to check and worth pinning; it is not a general anti-contradiction
    guard for prose.
    """
    step2 = _skill_step_section(2)
    assert step2.count("ALL_REVIEWERS") == 1, (
        "SKILL.md Step 2 mentions ALL_REVIEWERS more than once — the sole "
        "legitimate mention is the 'Never derive a run set from ALL_REVIEWERS' "
        "prohibition; a second mention likely means a contradictory "
        "instruction was appended"
    )


def test_both_synthesis_paths_carry_the_narration_rule():
    """Narration reaches the synthesizer on every path, because
    build_synthesis_input filters on the raw state.json `ok` and runs at
    SKILL.md Step 6 — before classify_review_ok is called at Step 7/8. The two
    paths get their instructions from different places (subprocess CLIs from
    `synthesis_prompt`, claude from the agent definition), so the rule has to
    be stated in both or the default synthesizer silently misses it."""
    from multi_review.core.prompt import synthesis_prompt

    agent = (AGENTS_DIR / "multi-review-synthesizer.md").read_text().lower()
    assert "narration" in agent, (
        "multi-review-synthesizer.md lost its narration rule; the claude "
        "synthesizer (the default) does not read synthesis_prompt"
    )
    assert "narration" in synthesis_prompt("nonce").lower(), (
        "synthesis_prompt lost its narration rule; subprocess synthesizers "
        "(agy/codex/opencode/pykrete/grok) do not read the agent definition"
    )


def test_skill_step5_passes_task_to_spawn():
    """Without --task, pykrete always resolves its [defaults.general] lead —
    a user's [defaults.code] tuning is silently ignored."""
    step5 = _skill_step_section(5)
    assert "--task <resolved.task>" in step5, (
        "SKILL.md Step 5 must forward the prompt's task to spawn — without it "
        "pykrete always resolves its [defaults.general] lead"
    )


def test_skill_never_polls_a_claude_task():
    """A Claude Task blocks until it returns, so TaskGet is misleading."""
    skill = SKILL.read_text()
    assert "TaskGet" not in skill, (
        "SKILL.md must not poll a Claude Task after its synchronous result returned"
    )
