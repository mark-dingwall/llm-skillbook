# tests/unit/test_reviewers.py
import os
import pytest
from multi_review.core.reviewers import (
    detect_self, detect_available, resolve_reviewers,
    CLI_SPEC, build_command, make_adapter, ALL_REVIEWERS,
)

def test_all_reviewers_known():
    assert set(ALL_REVIEWERS) >= {"claude", "agy", "codex", "opencode"}

def test_cli_spec_has_every_reviewer():
    for cli in ALL_REVIEWERS:
        assert cli in CLI_SPEC
        assert "base" in CLI_SPEC[cli]

def test_detect_self_claude(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    monkeypatch.delenv("ANTIGRAVITY_AGENT", raising=False)
    assert detect_self() == "claude"

def test_detect_self_antigravity_short_circuit(monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_AGENT", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    assert detect_self() == "none"

def test_resolve_reviewers_explicit_overrides_filter():
    chosen = resolve_reviewers(
        explicit=["claude", "agy"], skip_self=True, self_cli="claude",
        available={"claude", "agy", "codex"},
    )
    assert chosen == ["claude", "agy"]

def test_resolve_reviewers_default_includes_self_unless_skip():
    chosen = resolve_reviewers(
        explicit=None, skip_self=False, self_cli="claude",
        available={"claude", "agy"},
    )
    assert "claude" in chosen

def test_resolve_reviewers_skip_self_drops_host():
    chosen = resolve_reviewers(
        explicit=None, skip_self=True, self_cli="claude",
        available={"claude", "agy"},
    )
    assert "claude" not in chosen
    assert "agy" in chosen

def test_build_command_prompt_not_in_argv():
    argv = build_command("claude", model=None, streaming=True)
    # Prompt must not appear in argv — it goes on stdin
    assert all("<prompt>" not in tok for tok in argv)

def test_make_adapter_dispatches_correct_class():
    from multi_review.core.adapters import AgyAdapter
    a = make_adapter("agy")
    assert isinstance(a, AgyAdapter)

def test_cli_spec_has_no_fallback_chain_key():
    from multi_review.core.reviewers import CLI_SPEC
    for cli, spec in CLI_SPEC.items():
        assert "fallback_chain" not in spec, f"{cli} still has fallback_chain"

def test_no_capacity_patterns_export():
    import multi_review.core.reviewers as r
    assert not hasattr(r, "CAPACITY_PATTERNS")
    assert not hasattr(r, "GEMINI_FALLBACK_CHAIN")
    assert not hasattr(r, "resolve_chain")

def test_build_command_no_chain_branch():
    from multi_review.core.reviewers import build_command
    cmd = build_command("claude", model=None, streaming=True)
    assert "--model" in cmd
    assert "opus" in cmd

def test_all_reviewers_contains_agy_not_gemini():
    from multi_review.core.reviewers import ALL_REVIEWERS
    assert "agy" in ALL_REVIEWERS
    assert "gemini" not in ALL_REVIEWERS

def test_cli_spec_agy_shape():
    from multi_review.core.reviewers import CLI_SPEC
    s = CLI_SPEC["agy"]
    assert s["base"] == ["agy", "--print"]
    assert s["model_flag"] == "--model"
    assert s["stdin_sentinel"] is None
    assert s["stream_flags"] == []
    assert s["default_args"] == []
    # agy has no stdin mode; prompt is delivered via a file path on argv.
    assert s["prompt_delivery"] == "argv_file"

def test_cli_spec_no_gemini_entry():
    from multi_review.core.reviewers import CLI_SPEC
    assert "gemini" not in CLI_SPEC

def test_build_command_agy_requires_prompt_path():
    from multi_review.core.reviewers import build_command
    # argv_file delivery cannot build a command without a prompt file to read.
    with pytest.raises(ValueError):
        build_command("agy", model=None, streaming=True)

def test_build_command_agy_with_default():
    from pathlib import Path
    from multi_review.core.reviewers import build_command, AGY_FILE_INSTRUCTION
    p = Path("/tmp/session/prompt.txt")
    cmd = build_command("agy", model=None, streaming=True, prompt_path=p)
    # The prompt-file instruction sits immediately after --print (which consumes
    # the next arg as its value), and carries the path.
    assert cmd == ["agy", "--print", AGY_FILE_INSTRUCTION.format(path=p)]
    assert str(p) in cmd[2]

def test_build_command_agy_pinned_model_not_swallowed():
    from pathlib import Path
    from multi_review.core.reviewers import build_command
    p = Path("/tmp/session/prompt.txt")
    cmd = build_command("agy", model="Gemini 3.1 Pro (High)", streaming=True, prompt_path=p)
    # --print's value must be the instruction, NOT --model (the 1.0.x bug where
    # `agy --print --model X` made --print eat the flag).
    assert cmd[cmd.index("--print") + 1].startswith("Read the file")
    assert cmd.index("--model") > cmd.index("--print") + 1
    assert cmd[cmd.index("--model") + 1] == "Gemini 3.1 Pro (High)"

def test_detect_self_no_gemini_branch(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
    monkeypatch.delenv("CODEX_ENV", raising=False)
    monkeypatch.delenv("OPENCODE", raising=False)
    monkeypatch.delenv("ANTIGRAVITY_AGENT", raising=False)
    monkeypatch.setenv("GEMINI_CLI", "1")
    from multi_review.core.reviewers import detect_self
    assert detect_self() == ""  # GEMINI_CLI no longer recognised; falls through to unknown host

def test_detect_self_antigravity_still_shortcircuits(monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_AGENT", "1")
    from multi_review.core.reviewers import detect_self
    assert detect_self() == "none"

def test_build_command_codex_no_default_model():
    from multi_review.core.reviewers import build_command
    cmd = build_command("codex", model=None, streaming=True)
    assert "--model" not in cmd
    assert "-c" in cmd
    assert 'model_reasoning_effort="high"' in cmd

def test_build_command_opencode_no_default_model():
    from multi_review.core.reviewers import build_command
    cmd = build_command("opencode", model=None, streaming=True)
    assert "--model" not in cmd

def test_build_command_codex_pinned_still_works():
    from multi_review.core.reviewers import build_command
    cmd = build_command("codex", model="gpt-5.5", streaming=True)
    assert "--model" in cmd
    assert "gpt-5.5" in cmd

def test_pykrete_known_and_default():
    from multi_review.core.reviewers import ALL_REVIEWERS, DEFAULT_REVIEWERS, CLI_SPEC
    assert "pykrete" in ALL_REVIEWERS         # known/valid
    assert "pykrete" in DEFAULT_REVIEWERS     # AND default-on (post-split proof)
    assert CLI_SPEC["pykrete"]["success_exit_codes"] == (0, 3)

def test_build_command_pykrete_family_and_config(monkeypatch):
    from multi_review.core.reviewers import build_command
    monkeypatch.setenv("PYKRETE_CONFIG", "/etc/pykrete.toml")
    cmd = build_command("pykrete", model="glm", streaming=True)
    assert cmd[0] == "pykrete"
    assert cmd[cmd.index("--config") + 1] == "/etc/pykrete.toml"
    assert cmd[cmd.index("--family") + 1] == "glm"    # family, not --model
    assert "--model" not in cmd
    assert cmd[-1] == "-"                               # stdin sentinel last
    assert "--output-format" not in cmd                # plain text

def test_build_command_pykrete_config_kept_without_family(monkeypatch):
    from multi_review.core.reviewers import build_command
    monkeypatch.setenv("PYKRETE_CONFIG", "/etc/pykrete.toml")
    cmd = build_command("pykrete", model=None, streaming=True)
    assert "--config" in cmd            # NOT dropped when no family override
    assert "--family" not in cmd
    assert cmd[-1] == "-"

def test_build_command_pykrete_requires_config(monkeypatch):
    from multi_review.core.reviewers import build_command
    monkeypatch.delenv("PYKRETE_CONFIG", raising=False)
    with pytest.raises(ValueError, match="PYKRETE_CONFIG"):
        build_command("pykrete", model=None, streaming=True)


def test_grok_is_known_but_not_default():
    from multi_review.core.reviewers import ALL_REVIEWERS, DEFAULT_REVIEWERS
    assert "grok" in ALL_REVIEWERS          # valid wherever a reviewer is named
    assert "grok" not in DEFAULT_REVIEWERS  # never auto-selected


def test_default_reviewers_is_exactly_the_five():
    from multi_review.core.reviewers import DEFAULT_REVIEWERS
    assert DEFAULT_REVIEWERS == ["claude", "agy", "codex", "opencode", "pykrete"]


def test_resolve_reviewers_never_auto_selects_grok():
    from multi_review.core.reviewers import resolve_reviewers
    chosen = resolve_reviewers(
        explicit=None, skip_self=False, self_cli="",
        available={"claude", "agy", "codex", "opencode", "pykrete", "grok"},
    )
    assert "grok" not in chosen
    assert "claude" in chosen


def test_resolve_reviewers_explicit_selection_still_passes_through():
    """Regression guard on generic explicit-selection behaviour only.

    NOT evidence that grok is a *known* reviewer: resolve_reviewers filters on
    `available` and never checks membership of any reviewer set, so this passes
    for any string. Grok's validity is proved by the validate() test in
    tests/unit/test_promptfile.py.
    """
    from multi_review.core.reviewers import resolve_reviewers
    chosen = resolve_reviewers(
        explicit=["grok"], skip_self=False, self_cli="",
        available={"claude", "grok"},
    )
    assert chosen == ["grok"]


def test_detect_available_probes_grok(monkeypatch):
    """--list-reviewers must report grok's availability even though it is opt-in."""
    import multi_review.core.reviewers as m
    monkeypatch.setattr(m.shutil, "which", lambda c: "/usr/bin/" + c)
    assert "grok" in m.detect_available()


def test_build_command_grok_argv_shape():
    from multi_review.core.reviewers import build_command
    cmd = build_command("grok", model=None, streaming=True)
    assert cmd[0] == "grok"
    # Prompt is delivered via the stdin pipe that /dev/stdin resolves to.
    assert cmd[cmd.index("--prompt-file") + 1] == "/dev/stdin"
    assert cmd[cmd.index("--sandbox") + 1] == "workspace"
    assert cmd[cmd.index("--output-format") + 1] == "streaming-json"
    assert "-" not in cmd            # no stdin sentinel; it would be a stray prompt arg


def test_build_command_grok_model_pin():
    from multi_review.core.reviewers import build_command
    cmd = build_command("grok", model="grok-4.5-build", streaming=True)
    assert cmd[cmd.index("--model") + 1] == "grok-4.5-build"


def test_build_command_grok_synthesis_drops_stream_flags():
    """streaming=False is the synthesis path: plain stdout, still stdin-delivered."""
    from multi_review.core.reviewers import build_command
    cmd = build_command("grok", model=None, streaming=False)
    assert "--output-format" not in cmd
    assert cmd[cmd.index("--prompt-file") + 1] == "/dev/stdin"


def test_grok_has_no_pykrete_machinery():
    from multi_review.core.reviewers import CLI_SPEC
    spec = CLI_SPEC["grok"]
    assert "success_exit_codes" not in spec      # succeeds only on 0
    assert "config_env" not in spec
    assert not spec.get("records_family_not_model")  # grok reports real model IDs
