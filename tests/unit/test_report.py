import json
from pathlib import Path
from multi_review.core.report import (
    render_experiments_markdown, build_paired_report, REPORT_FORMAT_VERSION,
)

def _row(**kw):
    base = {
        "schema_version": 2, "run_id": "r1", "project": "p", "mode": "inline",
        "wall_seconds": 1.0, "reviewers_succeeded": 2, "reviewers_attempted": ["claude", "gemini"],
        "usage_by_reviewer": {
            "claude": {"telemetry_quality": "known-issues", "comparison_eligible": True,
                       "fallback_hops": 0, "final_model": "claude-opus-4-7"},
            "gemini": {"telemetry_quality": "reliable", "comparison_eligible": True,
                       "fallback_hops": 0, "final_model": "gemini-3.1-pro"},
        },
        "pair_id": None, "prompt_file": None, "prompt_format_version": 1,
        "drift_status": "not_applicable", "telemetry_notes": None,
        "timestamp": "2026-05-05T03:45:00Z",
    }
    base.update(kw)
    return base

def test_render_experiments_filters_ineligible_pairs(tmp_path):
    log = tmp_path / "runs.jsonl"
    rows = [
        _row(pair_id="pair-good", mode="inline"),
        _row(pair_id="pair-good", mode="reference"),
        _row(pair_id="pair-bad", mode="inline",
             usage_by_reviewer={"gemini": {"telemetry_quality": "reliable",
                                            "comparison_eligible": False,
                                            "fallback_hops": 1,
                                            "final_model": "gemini-3.1-flash"}}),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    md = render_experiments_markdown(log_path=log, reports_dir=tmp_path / "reports")
    assert "pair-good" in md
    assert REPORT_FORMAT_VERSION >= 1

def test_render_experiments_links_paired_reports(tmp_path):
    """Plan §11.2 / Task 30 step 5: regen surfaces paired-report file links
    under `runs/reports/` so the run-log table isn't the only entry point
    into per-pair narrative."""
    log = tmp_path / "runs.jsonl"
    rows = [
        _row(pair_id="pair-x", mode="reference", project="paralife",
             timestamp="2026-05-05T03:00:00Z"),
        _row(pair_id="pair-x", mode="inline", project="paralife",
             timestamp="2026-05-05T03:20:00Z"),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_file = reports_dir / "paralife-2026-05-05-pair-x.md"
    report_file.write_text("# placeholder paired report\n")

    md = render_experiments_markdown(log_path=log, reports_dir=reports_dir)
    assert "paralife-2026-05-05-pair-x.md" in md, "regen must link paired reports"

def test_build_paired_report_emits_format_c(tmp_path):
    log = tmp_path / "runs.jsonl"
    rows = [
        _row(pair_id="pair-x", mode="reference"),
        _row(pair_id="pair-x", mode="inline"),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    out_path = tmp_path / "reports" / "p-2026-05-05-pair-x.md"
    out_path.parent.mkdir()
    build_paired_report(log_path=log, pair_id="pair-x", out_path=out_path,
                        headline=None, mode_divergence=None, per_reviewer_notes=None)
    body = out_path.read_text()
    assert "report_format_version: 1" in body
    assert "pair_id: pair-x" in body
    assert "pair_type: paired" in body
    assert "comparison_eligible: true" in body or "comparison_eligible: True" in body
    assert "## Mode-divergence observations" in body

def test_build_paired_report_filename_format(tmp_path):
    """Filename contract: <project>-<date>-<pair-id>.md (spec §4.2 / §10.1)."""
    from multi_review.core.report import paired_report_filename
    assert paired_report_filename(
        project="paralife",
        date="2026-05-05",
        pair_id="pair-20260505-0345-9f3a",
    ) == "paralife-2026-05-05-pair-20260505-0345-9f3a.md"


def test_v2_row_missing_telemetry_is_ineligible(tmp_path):
    """H10: schema_version=2 row with no usage_by_reviewer means the migrator's
    per-reviewer backfill failed or the harness never wrote telemetry.
    Excluding from counters prevents silently degraded rows from biasing the
    next_recommended_order recommendation. Default must be False, not True."""
    log = tmp_path / "runs.jsonl"
    rows = [
        # Pair A: clean v2 reference-first → should drive counter
        _row(pair_id="pair-good", mode="reference",
             timestamp="2026-05-05T03:00:00Z"),
        _row(pair_id="pair-good", mode="inline",
             timestamp="2026-05-05T03:20:00Z"),
        # Pair B: degraded v2 inline-first WITHOUT usage_by_reviewer → ineligible
        {"schema_version": 2, "run_id": "deg1", "project": "p", "mode": "inline",
         "pair_id": "pair-degraded", "timestamp": "2026-05-04T03:00:00Z",
         "wall_seconds": 1.0, "reviewers_succeeded": 2,
         "reviewers_attempted": ["claude", "gemini"]},
        {"schema_version": 2, "run_id": "deg2", "project": "p", "mode": "reference",
         "pair_id": "pair-degraded", "timestamp": "2026-05-04T03:20:00Z",
         "wall_seconds": 1.0, "reviewers_succeeded": 2,
         "reviewers_attempted": ["claude", "gemini"]},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    md = render_experiments_markdown(log_path=log, reports_dir=tmp_path / "reports")
    # Only the clean pair (reference-first by timestamp) counts.
    assert "sessions_reference_first: 1" in md
    assert "sessions_inline_first: 0" in md


def test_v1_row_missing_telemetry_is_eligible(tmp_path):
    """H10 legacy carve-out: schema_version=1 rows pre-date per-reviewer
    telemetry. Grandfather them as eligible so historic comparison data
    keeps appearing in counters."""
    log = tmp_path / "runs.jsonl"
    rows = [
        {"schema_version": 1, "run_id": "v1a", "project": "p", "mode": "inline",
         "pair_id": "pair-legacy", "timestamp": "2026-04-01T03:00:00Z",
         "wall_seconds": 1.0, "reviewers_succeeded": 2,
         "reviewers_attempted": ["claude", "gemini"]},
        {"schema_version": 1, "run_id": "v1b", "project": "p", "mode": "reference",
         "pair_id": "pair-legacy", "timestamp": "2026-04-01T03:20:00Z",
         "wall_seconds": 1.0, "reviewers_succeeded": 2,
         "reviewers_attempted": ["claude", "gemini"]},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    md = render_experiments_markdown(log_path=log, reports_dir=tmp_path / "reports")
    assert "sessions_inline_first: 1" in md


def test_compute_pair_eligible_v2_missing_telemetry_false():
    """Pair-level: a v2 row missing usage_by_reviewer drops the pair."""
    from multi_review.core.report import _compute_pair_eligible
    rows = [
        {"schema_version": 2, "pair_id": "p", "mode": "inline"},
        {"schema_version": 2, "pair_id": "p", "mode": "reference",
         "usage_by_reviewer": {"claude": {"comparison_eligible": True}}},
    ]
    assert _compute_pair_eligible(rows) is False


def test_compute_pair_eligible_v1_carveout_true():
    """Pair-level: v1 rows grandfathered eligible."""
    from multi_review.core.report import _compute_pair_eligible
    rows = [
        {"schema_version": 1, "pair_id": "p", "mode": "inline"},
        {"schema_version": 1, "pair_id": "p", "mode": "reference"},
    ]
    assert _compute_pair_eligible(rows) is True
