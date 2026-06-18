import json
import subprocess
from pathlib import Path

def _rows(tmp_path):
    log = tmp_path / "runs.jsonl"
    rows = [
        {"schema_version": 2, "run_id": "r1", "project": "p", "mode": "inline",
         "wall_seconds": 1.0, "reviewers_succeeded": 2,
         "reviewers_attempted": ["claude", "gemini"],
         "usage_by_reviewer": {
             "claude": {"telemetry_quality": "known-issues", "comparison_eligible": True,
                        "final_model": "claude-opus-4-7"},
             "gemini": {"telemetry_quality": "reliable", "comparison_eligible": True,
                        "final_model": "gemini-3.1-pro"},
         },
         "pair_id": "pair-x", "prompt_file": None, "prompt_format_version": 1,
         "drift_status": "clean", "telemetry_notes": None,
         "timestamp": "2026-05-05T03:45:00Z"},
        {"schema_version": 2, "run_id": "r2", "project": "p", "mode": "reference",
         "wall_seconds": 1.0, "reviewers_succeeded": 2,
         "reviewers_attempted": ["claude", "gemini"],
         "usage_by_reviewer": {
             "claude": {"telemetry_quality": "known-issues", "comparison_eligible": True,
                        "final_model": "claude-opus-4-7"},
             "gemini": {"telemetry_quality": "reliable", "comparison_eligible": True,
                        "final_model": "gemini-3.1-pro"},
         },
         "pair_id": "pair-x", "prompt_file": None, "prompt_format_version": 1,
         "drift_status": "clean", "telemetry_notes": None,
         "timestamp": "2026-05-05T05:12:00Z"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    return log

def test_regen_writes_experiments_md(tmp_path):
    log = _rows(tmp_path)
    out = tmp_path / "EXPERIMENTS.md"
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.report",
         "regen", "--log", str(log), "--reports-dir", str(tmp_path / "reports"),
         "--output", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out.exists()
    assert "pair-x" in out.read_text()

def test_build_paired_report(tmp_path):
    log = _rows(tmp_path)
    rep_dir = tmp_path / "reports"
    rep_dir.mkdir()
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.report",
         "build-paired", "--log", str(log), "--pair-id", "pair-x",
         "--out-dir", str(rep_dir), "--project", "p", "--date", "2026-05-05"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert any(p.name.endswith("pair-x.md") for p in rep_dir.iterdir())
