# tests/integration/test_cli_aggregate.py
import json
import subprocess
from pathlib import Path


def _run_aggregate(rdir, out):
    return subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.aggregate",
         "--reviews-dir", str(rdir), "--mode", "inline", "--task", "code",
         "--output", str(out)],
        capture_output=True, text=True,
    )


def test_aggregate_writes_review_md(tmp_path):
    rdir = tmp_path / "reviews"
    rdir.mkdir()
    (rdir / "claude.md").write_text("claude says it's fine")
    (rdir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "duration_seconds": 2.0,
        "attempts": ["claude-opus-4-7"],
        "stderr_tail": "", "usage": None,
        "fallback_hops": 0, "final_model": "claude-opus-4-7",
    }))
    out = tmp_path / "REVIEW.md"
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.aggregate",
         "--reviews-dir", str(rdir), "--mode", "inline", "--task", "code",
         "--output", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    body = Path(j["output_path"]).read_text()
    assert "mode: inline" in body
    assert "claude says it's fine" in body


def test_aggregate_demotes_reviewer_missing_summary_heading(tmp_path):
    rdir = tmp_path / "reviews"
    rdir.mkdir()
    # rc=0, body well above 50 bytes, but NO `## Summary` heading.
    refusal = ("This request is outside my scope. " * 5) + "\n"
    assert len(refusal) > 50
    (rdir / "claude.md").write_text(refusal)
    (rdir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "duration_seconds": 1.0,
        "attempts": ["claude-opus-4-7"],
        "stderr_tail": "", "usage": None,
        "fallback_hops": 0, "final_model": "claude-opus-4-7",
    }))
    out = tmp_path / "REVIEW.md"
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.aggregate",
         "--reviews-dir", str(rdir), "--mode", "inline", "--task", "code",
         "--output", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    body = Path(j["output_path"]).read_text()
    assert "## Claude Review (FAILED)" in body
    assert 'reviewers_succeeded: []' in body
    assert 'reviewers_failed: ["claude"]' in body
    # Refusal body should surface in the partial-output block since text was
    # carried through to the failed ReviewerResult.
    assert "Partial output:" in body
    assert "outside my scope" in body


def test_aggregate_accepts_reviewer_with_summary_heading(tmp_path):
    rdir = tmp_path / "reviews"
    rdir.mkdir()
    body_md = "## Summary\n\nLooks fine. " + ("filler " * 10) + "\n"
    (rdir / "claude.md").write_text(body_md)
    (rdir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "duration_seconds": 1.0,
        "attempts": ["claude-opus-4-7"],
        "stderr_tail": "", "usage": None,
        "fallback_hops": 0, "final_model": "claude-opus-4-7",
    }))
    out = tmp_path / "REVIEW.md"
    r = _run_aggregate(rdir, out)
    assert r.returncode == 0, r.stderr
    body = Path(json.loads(r.stdout)["output_path"]).read_text()
    assert "## Claude Review" in body
    assert "(FAILED)" not in body
    assert 'reviewers_succeeded: ["claude"]' in body


def test_aggregate_surfaces_fallback_chain_in_frontmatter(tmp_path):
    """spawn.py writes fallback_hops + final_model into state.json; aggregate
    must forward those to ReviewerResult so the `fallbacks:` frontmatter
    block is emitted when gemini walked its chain."""
    rdir = tmp_path / "reviews"
    rdir.mkdir()
    body_md = "## Summary\n\nFallback case. " + ("filler " * 10) + "\n"
    (rdir / "gemini.md").write_text(body_md)
    (rdir / "gemini.state.json").write_text(json.dumps({
        "cli": "gemini", "ok": True, "duration_seconds": 4.2,
        "attempts": ["gemini-3.1-pro-preview", "gemini-3.1-pro", "gemini-3.1-flash"],
        "stderr_tail": "", "usage": None,
        "fallback_hops": 2, "final_model": "gemini-3.1-flash",
    }))
    out = tmp_path / "REVIEW.md"
    r = _run_aggregate(rdir, out)
    assert r.returncode == 0, r.stderr
    body = Path(json.loads(r.stdout)["output_path"]).read_text()
    assert "fallbacks:" in body
    assert "gemini:" in body
    assert "gemini-3.1-pro-preview" in body
    assert "gemini-3.1-flash" in body
    assert 'used: "gemini-3.1-flash"' in body
