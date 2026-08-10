"""tests/unit/test_aggregate.py — unit tests for core/aggregate.py"""
import os
import subprocess
import sys
from pathlib import Path
import yaml
from multi_review.core.aggregate import write_review_md, resolve_output_path
from multi_review.core.fanout import ReviewerResult

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_and_read(tmp_path, synthesis_text):
    out = tmp_path / "REVIEW.md"
    write_review_md(
        path=out,
        results=[_r("claude"), _r("gemini")],
        synthesis_text=synthesis_text,
        mode="inline",
        task="code",
        reviewers_attempted=["claude", "gemini"],
    )
    return out.read_text()


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


def test_aggregate_no_double_consensus_heading(tmp_path):
    body = "Both reviewers flagged the auth race.\n\nFix: use <=.\n"
    out = _write_and_read(tmp_path, synthesis_text=body)
    headings = [l for l in out.splitlines() if l.strip() == "## Consensus Summary"]
    assert len(headings) == 1


def test_aggregate_synthesis_already_has_heading_no_double(tmp_path):
    body = "## Consensus Summary\n\nBoth reviewers flagged the auth race.\n"
    out = _write_and_read(tmp_path, synthesis_text=body)
    headings = [l for l in out.splitlines() if l.strip() == "## Consensus Summary"]
    assert len(headings) == 1


def test_aggregate_frontmatter_parity(tmp_path):
    """Frontmatter must emit models:, mode:, and if_drift: per build-agent template."""
    out = tmp_path / "REVIEW.md"
    write_review_md(
        path=out,
        results=[_r("claude")],
        synthesis_text=None,
        mode="reference",
        task="code",
        reviewers_attempted=["claude"],
        models={"claude": "claude-opus-4-7"},
        if_drift="ignore",
    )
    body = out.read_text()
    assert "models:" in body
    assert "mode: reference" in body
    assert "if_drift: ignore" in body


def test_aggregate_frontmatter_empty_models(tmp_path):
    """models: key is always emitted even when no models dict is passed (aggregate CLI path)."""
    out = tmp_path / "REVIEW.md"
    write_review_md(
        path=out,
        results=[_r("claude")],
        synthesis_text=None,
        mode="inline",
        task="code",
        reviewers_attempted=["claude"],
    )
    body = out.read_text()
    assert "models:" in body


def test_aggregate_prompt_file_is_yaml_safe(tmp_path):
    prompt_file = "/absolute/has: a # hash/prompt.yaml"
    out = tmp_path / "REVIEW.md"
    write_review_md(
        path=out, results=[_r("claude")], synthesis_text=None,
        mode="inline", task="code", reviewers_attempted=["claude"],
        prompt_file=prompt_file,
    )
    frontmatter = out.read_text().split("---", 2)[1]
    assert yaml.safe_load(frontmatter)["prompt_file"] == prompt_file


def test_review_artifact_is_utf8_under_ascii_locale(tmp_path):
    """Unicode reviewer output must be writable under a non-UTF default locale."""
    out = tmp_path / "REVIEW.md"
    script = f"""
from pathlib import Path
from multi_review.core.aggregate import write_review_md
from multi_review.core.fanout import ReviewerResult

write_review_md(
    path=Path({str(out)!r}),
    results=[ReviewerResult("codex", True, "## Summary\\n\\ncaf\\u00e9", "", None, 1.0)],
    synthesis_text=None,
    mode="inline",
    task="code",
    reviewers_attempted=["codex"],
)
"""
    env = {
        **os.environ,
        "LC_ALL": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONPATH": str(REPO_ROOT),
        "PYTHONUTF8": "0",
    }

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "café" in out.read_bytes().decode("utf-8")
