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


def test_agy_get_response_text_trims_agentic_narration():
    from multi_review.core.adapters import AgyAdapter
    a = AgyAdapter()
    # agy narrates its steps before the review; the review begins at ## Summary.
    for line in [
        "I will read the file at /x/prompt.txt to inspect the review request.",
        "I will run pytest to verify the tests pass.",
        "",
        "## Summary",
        "",
        "The module is sound but has an uncaught exception path.",
        "",
        "## Critical Issues",
        "- foo.py:10 crashes on null input.",
    ]:
        a.feed_line(line)
    out = a.get_response_text()
    assert out.startswith("## Summary")
    assert "I will run pytest" not in out
    assert "uncaught exception path" in out


def test_agy_get_response_text_keeps_raw_when_no_heading():
    # No ## Summary → return raw so the aggregator can demote it (not silently empty).
    from multi_review.core.adapters import AgyAdapter
    a = AgyAdapter()
    a.feed_line("I explored the repo but produced no structured review.")
    out = a.get_response_text()
    assert "explored the repo" in out


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


def test_pykrete_adapter_accumulates_plaintext():
    from multi_review.core.adapters import PykreteAdapter
    a = PykreteAdapter(); a.feed_line("## Summary"); a.feed_line("Fine.")
    assert a.text == "## Summary\nFine."
    assert a.usage.input_tokens == 0


def test_pykrete_adapter_does_not_trim_preamble():
    from multi_review.core.adapters import PykreteAdapter
    a = PykreteAdapter(); a.feed_line("Intro before heading."); a.feed_line("## Summary")
    assert a.text.startswith("Intro before heading.")


def test_pykrete_registered():
    from multi_review.core.adapters import ADAPTER_FOR, PykreteAdapter
    assert ADAPTER_FOR["pykrete"] is PykreteAdapter


def test_grok_adapter_success_fixture():
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    _feed(a, FIX / "grok" / "success.jsonl")
    assert a.text.startswith("## Summary")
    assert "two edge cases are unhandled" in a.text


def test_grok_adapter_excludes_thought_narration():
    """thought events are reasoning narration, not review body."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    _feed(a, FIX / "grok" / "success.jsonl")
    assert "The user wants a review." not in a.text
    assert "wants" not in a.text


def test_grok_adapter_phase_transitions():
    """Pinned contract: starting -> thinking -> running -> done."""
    import json
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    assert a.phase == "starting"
    a.feed_line(json.dumps({"type": "thought", "data": "hm"}))
    assert a.phase == "thinking"
    a.feed_line(json.dumps({"type": "text", "data": "body"}))
    assert a.phase == "running"
    a.feed_line(json.dumps({"type": "end", "stopReason": "EndTurn", "usage": {}}))
    assert a.phase == "done"


def test_grok_adapter_end_event_usage_is_absolute():
    import json
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    end = {"type": "end", "stopReason": "EndTurn",
           "usage": {"input_tokens": 100, "cache_read_input_tokens": 10,
                     "output_tokens": 50, "reasoning_tokens": 5,
                     "total_tokens": 165}}
    a.feed_line(json.dumps(end))
    a.feed_line(json.dumps(end))          # a second end must not double-count
    assert a.usage.input_tokens == 100
    assert a.usage.output_tokens == 50
    assert a.usage.cached_tokens == 10    # from cache_read_input_tokens
    assert a.usage.tool_calls == 0        # grok emits no tool events


def test_grok_adapter_survives_malformed_and_non_object_lines():
    """Valid-but-non-object JSON must not raise: ev.get() on a list/str/None
    would AttributeError and kill the drain task mid-review."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    for bad in ('not json at all', 'null', '[]', '"banner"', '42'):
        a.feed_line(bad)
    a.feed_line('{"type":"text","data":"ok"}')
    assert a.text == "ok"


def test_grok_adapter_ignores_non_string_text_payload():
    """data: null must not enter text_parts — "".join() would raise later."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    a.feed_line('{"type":"text","data":null}')
    a.feed_line('{"type":"text","data":"real"}')
    assert a.text == "real"


def test_grok_adapter_ignores_non_dict_usage():
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    a.feed_line('{"type":"end","stopReason":"EndTurn","usage":"nope"}')
    assert a.usage.input_tokens == 0


def test_grok_adapter_coerces_bad_token_counters():
    """Usage declares ints. A drifted counter (null / string / object / bool /
    negative) must not reach <cli>.state.json or the harvest row as a non-int."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    a.feed_line('{"type":"end","stopReason":"EndTurn","usage":'
                '{"input_tokens":null,"output_tokens":"12",'
                '"cache_read_input_tokens":{"nested":1}}}')
    assert a.usage.input_tokens == 0
    assert a.usage.output_tokens == 0
    assert a.usage.cached_tokens == 0
    for v in a.usage.as_dict().values():
        assert isinstance(v, int) and not isinstance(v, bool)


def test_grok_registered():
    from multi_review.core.adapters import ADAPTER_FOR, GrokAdapter
    assert ADAPTER_FOR["grok"] is GrokAdapter
