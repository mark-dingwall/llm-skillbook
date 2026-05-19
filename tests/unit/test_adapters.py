"""Fixture-replay tests for multi_review.core.adapters."""
from pathlib import Path

import pytest

from multi_review.core.adapters import (
    ClaudeAdapter,
    CodexAdapter,
    GeminiAdapter,
    OpenCodeAdapter,
    ProgressAdapter,
)

FIX = Path(__file__).parent.parent / "fixtures" / "streams"


def _feed(adapter: ProgressAdapter, fixture: Path) -> None:
    if len(fixture.read_text()) < 50:
        pytest.skip(f"fixture {fixture} is a placeholder (<50 bytes)")
    for line in fixture.read_text().splitlines():
        if line.strip():
            adapter.feed_line(line)


def test_claude_adapter_success_fixture():
    a = ClaudeAdapter()
    _feed(a, FIX / "claude" / "success.jsonl")
    assert a.text != ""
    assert a.usage.input_tokens is not None


def test_claude_adapter_empty_fixture_yields_empty_text():
    a = ClaudeAdapter()
    _feed(a, FIX / "claude" / "empty.jsonl")
    assert a.text == ""


def test_gemini_adapter_capacity_failure_captures_error():
    a = GeminiAdapter()
    _feed(a, FIX / "gemini" / "capacity_429.jsonl")
    assert a.last_error is not None
    assert "429" in a.last_error or "quota" in a.last_error.lower()


def test_codex_adapter_success_fixture():
    a = CodexAdapter()
    _feed(a, FIX / "codex" / "success.jsonl")
    assert a.text != ""


def test_opencode_adapter_success_fixture():
    a = OpenCodeAdapter()
    _feed(a, FIX / "opencode" / "success.jsonl")
    assert a.text != ""
