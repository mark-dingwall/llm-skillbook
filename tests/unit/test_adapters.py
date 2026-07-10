"""Fixture-replay tests for multi_review.core.adapters."""
from pathlib import Path

import pytest

from multi_review.core.adapters import (
    AgyAdapter,
    ClaudeAdapter,
    CodexAdapter,
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


def test_agy_adapter_buffers_plain_text():
    from multi_review.core.adapters import AgyAdapter
    a = AgyAdapter()
    a.feed_line("Hi from agy.")
    a.feed_line("Second line.")
    assert "".join(a.text_parts) == "Hi from agy.\nSecond line.\n"
    assert a.usage.input_tokens == 0
    assert a.usage.output_tokens == 0
    assert a.phase in ("running", "done")


def test_agy_fixture_round_trip():
    from multi_review.core.adapters import AgyAdapter
    a = AgyAdapter()
    fixture = (FIX / "agy" / "success.txt").read_text()
    for line in fixture.splitlines():
        a.feed_line(line)
    body = "".join(a.text_parts)
    assert "The auth middleware in `src/auth.py:42`" in body
    assert "LEEWAY_SECONDS = 1" in body


def test_no_gemini_adapter_export():
    import multi_review.core.adapters as m
    assert not hasattr(m, "GeminiAdapter")
    assert "gemini" not in m.ADAPTER_FOR
    assert m.ADAPTER_FOR["agy"] is m.AgyAdapter


def test_codex_adapter_success_fixture():
    a = CodexAdapter()
    _feed(a, FIX / "codex" / "success.jsonl")
    assert a.text != ""


def test_opencode_adapter_success_fixture():
    a = OpenCodeAdapter()
    _feed(a, FIX / "opencode" / "success.jsonl")
    assert a.text != ""


def test_opencode_adapter_reads_part_tokens():
    import json
    a = OpenCodeAdapter()
    a.feed_line(json.dumps({
        "type": "step_finish",
        "part": {"tokens": {"input": 100, "output": 50, "total": 150,
                            "reasoning": 0, "cache": {"write": 0, "read": 10}}},
    }))
    assert a.usage.input_tokens == 100
    assert a.usage.output_tokens == 50
    assert a.usage.cached_tokens == 10
