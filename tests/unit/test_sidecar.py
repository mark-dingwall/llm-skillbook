import json
from pathlib import Path
from multi_review.core.sidecar import group_candidate_pairs, CandidatePair

def _row(**kw):
    base = {
        "project": "paralife", "started_at": "2026-05-05T03:00:00Z",
        "finished_at": "2026-05-05T03:10:00Z",
        "mode": "inline", "argv": ["src/auth.ts", "src/session.ts"],
        "cwd": "/home/x/paralife", "pair_id": None,
        "usage_by_reviewer": {"claude": {"comparison_eligible": True, "fallback_hops": 0}},
    }
    base.update(kw)
    return base

def test_group_pairs_same_project_complementary_modes_within_window(tmp_path):
    log = tmp_path / "runs.jsonl"
    rows = [
        _row(mode="inline", started_at="2026-05-05T03:00:00Z"),
        _row(mode="reference", started_at="2026-05-05T03:35:00Z"),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    pairs = group_candidate_pairs(log, default_delay_s=1800)
    assert len(pairs) == 1
    assert {r["mode"] for r in pairs[0].rows} == {"inline", "reference"}

def test_group_pairs_rejects_mismatched_argv(tmp_path):
    log = tmp_path / "runs.jsonl"
    rows = [
        _row(mode="inline", argv=["a.ts"]),
        _row(mode="reference", argv=["b.ts"], started_at="2026-05-05T03:20:00Z"),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    assert group_candidate_pairs(log, default_delay_s=1800) == []

def test_window_is_max_60min_or_delay_plus_slack(tmp_path):
    log = tmp_path / "runs.jsonl"
    rows = [
        _row(mode="inline", started_at="2026-05-05T03:00:00Z"),
        _row(mode="reference", started_at="2026-05-05T03:55:00Z"),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    assert len(group_candidate_pairs(log, default_delay_s=1800)) == 1

def test_rows_without_argv_are_unpairable(tmp_path):
    log = tmp_path / "runs.jsonl"
    rows = [_row(argv=None), _row(mode="reference", started_at="2026-05-05T03:20:00Z")]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    assert group_candidate_pairs(log, default_delay_s=1800) == []
