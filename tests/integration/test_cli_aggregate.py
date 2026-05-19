# tests/integration/test_cli_aggregate.py
import json
import subprocess
from pathlib import Path

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
