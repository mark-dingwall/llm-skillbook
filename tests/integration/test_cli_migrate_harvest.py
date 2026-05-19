# tests/integration/test_cli_migrate_harvest.py
import json, subprocess
from pathlib import Path

def test_migrate_backfills_v1_rows(tmp_path):
    log = tmp_path / "runs.jsonl"
    v1_rows = [
        {"schema_version": 1, "run_id": "old1", "project": "p", "mode": "inline",
         "usage_by_reviewer": {"claude": {"input_tokens": 100, "output_tokens": 50}}},
        {"schema_version": 1, "run_id": "old2", "project": "p", "mode": "reference",
         "usage_by_reviewer": {"gemini": {"input_tokens": 200, "output_tokens": 80}}},
    ]
    log.write_text("\n".join(json.dumps(r) for r in v1_rows))
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.migrate_harvest",
         "--log", str(log), "--backup", str(tmp_path / "backup.jsonl")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    backup = (tmp_path / "backup.jsonl").read_text()
    assert "schema_version\": 1" in backup
    upgraded = [json.loads(l) for l in log.read_text().splitlines()]
    for row in upgraded:
        assert row["schema_version"] == 2
        assert "pair_id" in row and row["pair_id"] is None
        assert "prompt_file" in row
        assert "drift_status" in row
        for cli, ub in row["usage_by_reviewer"].items():
            assert "telemetry_quality" in ub
            assert "comparison_eligible" in ub
            assert "fallback_hops" in ub
            assert "final_model" in ub
