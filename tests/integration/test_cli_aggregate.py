# tests/integration/test_cli_aggregate.py
import json
import subprocess
from pathlib import Path


def _run_aggregate(rdir, out):
    return subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.aggregate",
         "--reviews-dir", str(rdir), "--task", "code",
         "--output", str(out)],
        capture_output=True, text=True,
    )


def test_aggregate_writes_review_md(tmp_path):
    rdir = tmp_path / "reviews"
    rdir.mkdir()
    (rdir / "claude.md").write_text("claude says it's fine")
    (rdir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "duration_seconds": 2.0,
        "stderr_tail": "", "usage": None,
        "final_model": "claude-opus-4-7",
    }))
    out = tmp_path / "REVIEW.md"
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.aggregate",
         "--reviews-dir", str(rdir), "--task", "code",
         "--output", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    body = Path(j["output_path"]).read_text()
    assert "mode:" not in body.split("---", 2)[1]
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
        "stderr_tail": "real subprocess warning", "usage": None,
        "final_model": "claude-opus-4-7",
    }))
    out = tmp_path / "REVIEW.md"
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.aggregate",
         "--reviews-dir", str(rdir), "--task", "code",
         "--output", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    body = Path(j["output_path"]).read_text()
    assert "## Claude Review (FAILED)" in body
    assert 'reviewers_succeeded: []' in body
    assert 'reviewers_failed: ["claude"]' in body
    reason = "no ## Summary heading in review body"
    assert f"**Status:** failed — {reason}" in body
    assert body.count(reason) == 1
    assert "real subprocess warning" in body
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
        "stderr_tail": "", "usage": None,
        "final_model": "claude-opus-4-7",
    }))
    out = tmp_path / "REVIEW.md"
    r = _run_aggregate(rdir, out)
    assert r.returncode == 0, r.stderr
    body = Path(json.loads(r.stdout)["output_path"]).read_text()
    assert "## Claude Review" in body
    assert "(FAILED)" not in body
    assert 'reviewers_succeeded: ["claude"]' in body


def test_aggregate_survives_truncated_and_missing_ok_state(tmp_path):
    """I3: one truncated .state.json and one missing the `ok` key must not crash
    aggregate. A valid REVIEW.md covering the good reviewer is still written; the
    bad reviewers surface as failed/skipped, not an aborted run."""
    rdir = tmp_path / "reviews"
    rdir.mkdir()

    # Good reviewer — complete, compliant.
    (rdir / "good.md").write_text("## Summary\n\nAll clear. " + ("filler " * 10) + "\n")
    (rdir / "good.state.json").write_text(json.dumps({
        "cli": "good", "ok": True, "duration_seconds": 2.0,
        "stderr_tail": "", "usage": None, "final_model": "m",
    }))

    # Truncated JSON — reviewer killed mid write_text.
    (rdir / "truncated.md").write_text("## Summary\n\npartial")
    (rdir / "truncated.state.json").write_text('{"cli": "truncated", "ok": tr')

    # Missing the `ok` key entirely.
    (rdir / "nook.md").write_text("## Summary\n\nno ok key here\n")
    (rdir / "nook.state.json").write_text(json.dumps({
        "cli": "nook", "duration_seconds": 1.0, "stderr_tail": "", "usage": None,
    }))

    out = tmp_path / "REVIEW.md"
    r = _run_aggregate(rdir, out)
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    body = Path(j["output_path"]).read_text()
    # Good reviewer's work survives.
    assert "All clear." in body
    assert 'reviewers_succeeded: ["good"]' in body
    # Missing-ok reviewer classified as failed (ok defaulted False), not a crash.
    assert "## Nook Review (FAILED)" in body


def test_aggregate_renders_with_null_duration(tmp_path):
    """M7: an explicit JSON null duration_seconds must not TypeError in the
    `{r.elapsed:.1f}` render path — REVIEW.md still renders."""
    rdir = tmp_path / "reviews"
    rdir.mkdir()
    (rdir / "claude.md").write_text("## Summary\n\nLooks fine. " + ("filler " * 10) + "\n")
    (rdir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "duration_seconds": None,
        "stderr_tail": "", "usage": None, "final_model": "m",
    }))
    out = tmp_path / "REVIEW.md"
    r = _run_aggregate(rdir, out)
    assert r.returncode == 0, r.stderr
    body = Path(json.loads(r.stdout)["output_path"]).read_text()
    assert "## Claude Review" in body
    assert "elapsed_s: 0.0" in body
