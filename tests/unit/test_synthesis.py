"""tests/unit/test_synthesis.py — unit tests for core/synthesis.py"""
import asyncio
import pytest
from multi_review.core.synthesis import (
    build_synthesis_input, extract_filename_from_synthesis,
    strip_filename_prefix, sanitize_review_filename, run_synthesis,
    _run_synthesis_attempt,
)
from multi_review.core.fanout import ReviewerResult


def _r(cli: str, text: str) -> ReviewerResult:
    return ReviewerResult(
        cli=cli, ok=True, text=text, stderr_tail="",
        usage=None, elapsed=0.0,
    )


def test_build_synthesis_input_wraps_each_review():
    body, nonce = build_synthesis_input([_r("claude", "A"), _r("gemini", "B")])
    assert nonce in body
    assert "<review" in body
    assert "reviewer=" in body


def test_extract_filename_from_synthesis_finds_marker():
    text = "FILENAME: auth-review\nrest of body"
    assert extract_filename_from_synthesis(text) == "REVIEW-auth-review.md"


def test_sanitize_review_filename_rejects_path_traversal():
    assert sanitize_review_filename("../etc/passwd") is None
    assert sanitize_review_filename("review/sub") is None


def test_sanitize_review_filename_accepts_clean():
    assert sanitize_review_filename("auth-review") == "REVIEW-auth-review.md"


def test_run_synthesis_missing_config_is_failed_not_raised(monkeypatch):
    """As synthesizer, a missing PYKRETE_CONFIG must come back as a failed
    tuple — not raise ValueError out of run_synthesis (that would abort the
    whole synthesis pass instead of just recording it as a no-op)."""
    monkeypatch.delenv("PYKRETE_CONFIG", raising=False)
    ok, text, err, suggested, attempts = asyncio.run(
        run_synthesis("pykrete", "review body", "nonce123", model=None, timeout=None)
    )
    assert ok is False
    assert "PYKRETE_CONFIG" in err


def test_cancelled_synthesis_kills_child(monkeypatch):
    killed = []

    class Proc:
        async def communicate(self, payload):
            raise asyncio.CancelledError()

    async def fake_exec(*args, **kwargs):
        return Proc()

    async def fake_kill(proc):
        killed.append(proc)

    monkeypatch.setattr("multi_review.core.synthesis.build_command",
                        lambda *args, **kwargs: ["fake"])
    monkeypatch.setattr("multi_review.core.synthesis.asyncio.create_subprocess_exec", fake_exec)
    monkeypatch.setattr("multi_review.core.synthesis.kill_proc", fake_kill)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_run_synthesis_attempt("codex", "body", "nonce", None, None))
    assert len(killed) == 1
