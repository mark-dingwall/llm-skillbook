# tests/integration/test_cli_migrate_harvest.py
import json, subprocess
from pathlib import Path

def test_migrate_backfills_v1_rows(tmp_path):
    """Real-world v1 rows have a top-level `usage` key (not `usage_by_reviewer`).
    The migrator must rename `usage` → `usage_by_reviewer` AND preserve `usage`
    as the deprecated alias (per harvest.py schema-v2 contract), AND backfill
    the per-reviewer v2 fields. Earlier fixture wrongly seeded `usage_by_reviewer`
    on v1 rows so the rename-bug went undetected and shipped to runs.jsonl."""
    log = tmp_path / "runs.jsonl"
    v1_rows = [
        {"schema_version": 1, "run_id": "old1", "project": "p", "mode": "inline",
         "usage": {"claude": {"input_tokens": 100, "output_tokens": 50}}},
        {"schema_version": 1, "run_id": "old2", "project": "p", "mode": "reference",
         "usage": {"gemini": {"input_tokens": 200, "output_tokens": 80}}},
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
        # Canonical v2 key must exist with the renamed per-reviewer data.
        assert "usage_by_reviewer" in row, \
            "migrator must rename `usage` → `usage_by_reviewer` on v1 rows"
        assert row["usage_by_reviewer"], "usage_by_reviewer must be non-empty"
        # Deprecated alias still present (removed in v3).
        assert "usage" in row, "v2 schema keeps `usage` as deprecated alias"
        for cli, ub in row["usage_by_reviewer"].items():
            assert "input_tokens" in ub, "v1 token fields must survive rename"
            assert "telemetry_quality" in ub
            assert "comparison_eligible" in ub
            assert "fallback_hops" in ub
            assert "final_model" in ub


def test_migrate_idempotent_on_already_v2(tmp_path):
    """Re-running the migrator on an already-v2 log must be a no-op
    (does not double-rename, does not duplicate alias data)."""
    log = tmp_path / "runs.jsonl"
    v2_row = {
        "schema_version": 2, "run_id": "x", "project": "p", "mode": "inline",
        "pair_id": None, "prompt_file": None, "drift_status": "not_applicable",
        "usage_by_reviewer": {"claude": {"input_tokens": 1, "output_tokens": 2,
                                          "telemetry_quality": "reliable",
                                          "comparison_eligible": True,
                                          "fallback_hops": 0,
                                          "final_model": None}},
        "usage": {"claude": {"input_tokens": 1, "output_tokens": 2,
                              "telemetry_quality": "reliable",
                              "comparison_eligible": True,
                              "fallback_hops": 0,
                              "final_model": None}},
    }
    log.write_text(json.dumps(v2_row))
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.migrate_harvest",
         "--log", str(log), "--backup", str(tmp_path / "backup.jsonl")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    after = json.loads(log.read_text())
    assert after["usage_by_reviewer"] == v2_row["usage_by_reviewer"]
