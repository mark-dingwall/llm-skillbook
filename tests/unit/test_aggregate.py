"""tests/unit/test_aggregate.py — unit tests for core/aggregate.py"""
from pathlib import Path
from multi_review.core.aggregate import write_review_md, resolve_output_path
from multi_review.core.fanout import ReviewerResult


def _r(cli, ok=True, text="content"):
    return ReviewerResult(cli=cli, ok=ok, text=text, stderr_tail="",
                          usage=None, elapsed=1.0)


def test_resolve_output_path_auto_suffix(tmp_path):
    target = tmp_path / "REVIEW.md"
    target.write_text("x")
    p = resolve_output_path(target, force=False)
    assert p.name == "REVIEW-2.md"


def test_resolve_output_path_no_collision_returns_target(tmp_path):
    target = tmp_path / "REVIEW.md"
    p = resolve_output_path(target, force=False)
    assert p == target


def test_write_review_md_includes_mode_in_frontmatter(tmp_path):
    out = tmp_path / "REVIEW.md"
    write_review_md(
        path=out, results=[_r("claude")], synthesis_text=None,
        mode="reference", task="code", reviewers_attempted=["claude"],
    )
    body = out.read_text()
    assert "mode: reference" in body
    assert "## Claude" in body or "## claude" in body.lower()


def test_write_review_md_includes_failed_section(tmp_path):
    out = tmp_path / "REVIEW.md"
    write_review_md(
        path=out, results=[_r("gemini", ok=False, text="")],
        synthesis_text=None, mode="inline", task="code",
        reviewers_attempted=["gemini"],
    )
    body = out.read_text()
    assert "failed" in body.lower() or "Failed" in body


def test_aggregate_no_fallbacks_frontmatter(tmp_path):
    """REVIEW.md frontmatter must never contain a `fallbacks:` block after B5."""
    out = tmp_path / "REVIEW.md"
    write_review_md(
        path=out, results=[_r("claude"), _r("gemini")],
        synthesis_text=None, mode="inline", task="code",
        reviewers_attempted=["claude", "gemini"],
    )
    body = out.read_text()
    assert "fallbacks:" not in body
