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


def _r(cli, fallback_hops=0, final_model="m"):
    """Build a ReviewerResult. fallback_hops maps to len(attempts)-1."""
    # attempts: [fallback_hops intermediate models..., final_model]
    if fallback_hops == 0:
        attempts = [final_model]
    else:
        # fill intermediate slots with a placeholder, final slot = final_model
        attempts = [f"model-hop-{i}" for i in range(fallback_hops)] + [final_model]
    return ReviewerResult(
        cli=cli, ok=True, text="x" * 200, stderr_tail="",
        usage=Usage(input_tokens=10, output_tokens=20),
        elapsed=1.0,
        model_used=final_model,
        attempts=attempts,
        fallback_fired=fallback_hops > 0,
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
    assert "fallback_hops" in cur
    assert "final_model" in cur


def test_comparison_eligible_false_on_fallback():
    row = build_row(
        results=[_r("gemini", fallback_hops=1, final_model="gemini-3.1-flash")],
        mode="inline", task="code", project="p", wall_seconds=1.0,
        reviewers_attempted=["gemini"], synthesizer="none", synthesis_ok=False,
        pair_id=None, prompt_file=None, prompt_format_version=1,
        drift_status="not_applicable", telemetry_notes=None,
    )
    assert row["usage_by_reviewer"]["gemini"]["comparison_eligible"] is False


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
