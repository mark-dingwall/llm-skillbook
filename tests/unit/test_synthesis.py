"""tests/unit/test_synthesis.py — unit tests for core/synthesis.py"""
from multi_review.core.synthesis import (
    build_synthesis_input, extract_filename_from_synthesis,
    strip_filename_prefix, sanitize_review_filename,
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
