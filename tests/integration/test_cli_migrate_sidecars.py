import json
import subprocess
from pathlib import Path


def _seed(tmp_path: Path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "paralife-2026-05-05.md").write_text("# clean pair narrative\n")
    (notes / "exploratory.md").write_text("# legacy\n")
    log = tmp_path / "runs.jsonl"
    rows = [
        {"project": "paralife", "mode": "inline", "started_at": "2026-05-05T03:00:00Z",
         "argv": ["src/auth.ts"], "cwd": "/home/x/paralife", "pair_id": None,
         "prompt_bytes": 1000, "output_bytes": 2000,
         "usage": {"input_tokens": 1, "output_tokens": 1},
         "usage_by_reviewer": {"claude": {"comparison_eligible": True, "fallback_hops": 0}}},
        {"project": "paralife", "mode": "reference", "started_at": "2026-05-05T03:35:00Z",
         "argv": ["src/auth.ts"], "cwd": "/home/x/paralife", "pair_id": None,
         "prompt_bytes": 1000, "output_bytes": 2000,
         "usage": {"input_tokens": 1, "output_tokens": 1},
         "usage_by_reviewer": {"claude": {"comparison_eligible": True, "fallback_hops": 0}}},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    return notes, log, tmp_path / "reports", notes / "legacy"


def test_migrate_row_driven_writes_paired_and_legacies(tmp_path):
    notes, log, reports, legacy = _seed(tmp_path)
    # Confirm pair (y), assign first sidecar to pair 1, mark second sidecar legacy.
    answers = "y\n1\nlegacy\n"
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.migrate_sidecars",
         "--notes-dir", str(notes), "--log", str(log),
         "--reports-dir", str(reports), "--legacy-dir", str(legacy)],
        input=answers, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (legacy / "exploratory.md").exists()
    assert any(p.suffix == ".md" for p in reports.iterdir())
    # Row-rewrite + .bak.
    assert (log.parent / "runs.jsonl.bak").exists()
    upgraded = [json.loads(l) for l in log.read_text().splitlines()]
    assert all(r["pair_id"] is not None for r in upgraded)
