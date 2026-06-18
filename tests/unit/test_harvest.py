"""Tests for multi_review.core.harvest — schema v2."""
import json
from pathlib import Path

from multi_review.core.harvest import (
    HARVEST_SCHEMA_VERSION, harvest_run, derive_project, build_row,
)
from multi_review.core.fanout import ReviewerResult
from multi_review.core.adapters import Usage


def test_schema_version_is_2():
    assert HARVEST_SCHEMA_VERSION == 2


def _r(cli, final_model="m"):
    """Build a ReviewerResult."""
    return ReviewerResult(
        cli=cli, ok=True, text="x" * 200, stderr_tail="",
        usage=Usage(input_tokens=10, output_tokens=20),
        elapsed=1.0,
        model_used=final_model,
    )


def test_build_row_has_new_schema_fields():
    row = build_row(
        results=[_r("claude")], mode="inline", task="code", project="p",
        wall_seconds=2.0, reviewers_attempted=["claude"],
        synthesizer="claude", synthesis_ok=True,
        pair_id="pair-x", prompt_file="prompts/auth.yaml",
        prompt_format_version=1, drift_status="not_applicable",
        telemetry_notes=None,
    )
    assert row["schema_version"] == 2
    assert row["pair_id"] == "pair-x"
    assert row["prompt_file"] == "prompts/auth.yaml"
    assert row["drift_status"] == "not_applicable"
    cur = row["usage_by_reviewer"]["claude"]
    assert "telemetry_quality" in cur
    assert "comparison_eligible" in cur
    assert "final_model" in cur


def test_comparison_eligible_factors_drift_status():
    """drift_status of "drifted" or "unchecked" disqualifies per-reviewer
    eligibility even when no fallback hops were walked. See spec §7.1."""
    def _build(drift):
        return build_row(
            results=[_r("claude")], mode="inline", task="code", project="p",
            wall_seconds=1.0, reviewers_attempted=["claude"],
            synthesizer="none", synthesis_ok=False,
            pair_id=None, prompt_file=None, prompt_format_version=1,
            drift_status=drift, telemetry_notes=None,
        )
    assert _build("clean")["usage_by_reviewer"]["claude"]["comparison_eligible"] is True
    assert _build("not_applicable")["usage_by_reviewer"]["claude"]["comparison_eligible"] is True
    assert _build("drifted")["usage_by_reviewer"]["claude"]["comparison_eligible"] is False
    assert _build("unchecked")["usage_by_reviewer"]["claude"]["comparison_eligible"] is False




def test_harvest_row_emits_both_usage_keys():
    """v2 keeps `usage` as a deprecated alias of `usage_by_reviewer` for one cycle.
    Read path: consumers should migrate to `usage_by_reviewer`; remove `usage` in v3.
    """
    row = build_row(
        results=[_r("gemini")], mode="inline", task="code", project="p",
        wall_seconds=1.0, reviewers_attempted=["gemini"],
        synthesizer="none", synthesis_ok=False,
        pair_id=None, prompt_file=None, prompt_format_version=1,
        drift_status="not_applicable", telemetry_notes=None,
    )
    assert "usage_by_reviewer" in row
    assert "usage" in row, "v2 must emit `usage` as a deprecated alias"
    # Alias matches the nested structure (read-only mirror).
    assert row["usage"] == row["usage_by_reviewer"]


def test_harvest_run_appends_jsonl(tmp_path):
    log = tmp_path / "runs.jsonl"
    harvest_run(
        log_path=log, row={"schema_version": 2, "run_id": "r1"},
    )
    assert log.exists()
    lines = log.read_text().splitlines()
    assert json.loads(lines[0])["run_id"] == "r1"


def test_derive_project_override_wins(tmp_path):
    assert derive_project(tmp_path, override="Custom") == "Custom"


def test_harvest_row_no_fallback_fields(tmp_path):
    """fallback_hops must not appear in per-reviewer dicts; fallback_attempts
    must not appear at the top level. Both were stripped in B5."""
    row = build_row(
        results=[_r("claude"), _r("gemini")],
        mode="inline", task="code", project="p",
        wall_seconds=2.0, reviewers_attempted=["claude", "gemini"],
        synthesizer="claude", synthesis_ok=True,
        pair_id=None, prompt_file=None, prompt_format_version=1,
        drift_status="not_applicable", telemetry_notes=None,
    )
    assert "fallback_attempts" not in row
    for ubr in row["usage_by_reviewer"].values():
        assert "fallback_hops" not in ubr
