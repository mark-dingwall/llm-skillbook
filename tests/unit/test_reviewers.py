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
    from multi_review.core.adapters import GeminiAdapter
    a = make_adapter("gemini")
    assert isinstance(a, GeminiAdapter)

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

def test_cli_spec_no_gemini_entry():
    from multi_review.core.reviewers import CLI_SPEC
    assert "gemini" not in CLI_SPEC

def test_build_command_agy_with_default():
    from multi_review.core.reviewers import build_command
    cmd = build_command("agy", model=None, streaming=True)
    assert cmd == ["agy", "--print"]

def test_build_command_agy_pinned():
    from multi_review.core.reviewers import build_command
    cmd = build_command("agy", model="Gemini 3.1 Pro (High)", streaming=True)
    assert "--model" in cmd
    assert "Gemini 3.1 Pro (High)" in cmd
