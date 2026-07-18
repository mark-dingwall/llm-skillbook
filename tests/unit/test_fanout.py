"""tests/unit/test_fanout.py — unit tests for core/fanout.py"""
import asyncio
import sys
import pytest
from multi_review.core.fanout import (
    ReviewerResult, ReviewerState, run_reviewer,
)
from multi_review.core.adapters import ClaudeAdapter


def test_run_reviewer_no_chain_walk(tmp_path, monkeypatch):
    """A 429-style failure from the subprocess produces a failed result — no second attempt."""
    script = tmp_path / "fake_cli.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('RESOURCE_EXHAUSTED: 429\\n')\n"
        "sys.exit(1)\n"
    )

    import multi_review.core.fanout as fanout_mod
    monkeypatch.setattr(fanout_mod, "build_command", lambda cli, model, *, streaming, prompt_path=None: [sys.executable, str(script)])
    monkeypatch.setattr(fanout_mod, "make_adapter", lambda cli: ClaudeAdapter())

    state = ReviewerState(cli="claude", adapter=ClaudeAdapter())
    result = asyncio.run(
        run_reviewer("claude", "x", model=None, timeout=None, state=state)
    )
    assert result.ok is False


def test_reviewer_ok_pykrete_accepts_downgrade_exit3():
    from multi_review.core.fanout import reviewer_ok
    body = "x" * 100
    assert reviewer_ok("pykrete", 3, body) is True
    assert reviewer_ok("pykrete", 0, body) is True
    assert reviewer_ok("pykrete", 1, body) is False
    assert reviewer_ok("pykrete", 4, body) is False
    assert reviewer_ok("pykrete", 0, "tiny") is False   # byte floor preserved
    assert reviewer_ok("codex", 3, body) is False        # default (0,) unchanged
    assert reviewer_ok("codex", 0, body) is True
