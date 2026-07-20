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


def test_telemetry_quality_agy_not_gemini():
    """agy replaced gemini and emits plain text with no token telemetry, so its
    quality tier is the lowest (degraded), not the old gemini 'reliable'."""
    from multi_review.core.harvest import TELEMETRY_QUALITY
    assert "gemini" not in TELEMETRY_QUALITY
    assert TELEMETRY_QUALITY["agy"] == "degraded"


def test_pykrete_telemetry_degraded():
    from multi_review.core.harvest import TELEMETRY_QUALITY
    assert TELEMETRY_QUALITY["pykrete"] == "degraded"


def test_grok_telemetry_known_issues():
    """Not "reliable" (tool_calls is permanently 0, an unavailable sentinel) and
    not "degraded" (token counts are complete). A missing entry would silently
    fall back to "degraded" via TELEMETRY_QUALITY.get(cli, "degraded")."""
    from multi_review.core.harvest import TELEMETRY_QUALITY
    assert TELEMETRY_QUALITY["grok"] == "known-issues"


def test_build_row_emits_grok_telemetry_quality():
    row = build_row(
        results=[_r("grok")], mode="inline", task="code", project="p",
        wall_seconds=2.0, reviewers_attempted=["grok"],
        synthesizer="claude", synthesis_ok=True,
        pair_id=None, prompt_file="prompts/auth.yaml",
        prompt_format_version=1, drift_status="clean",
        telemetry_notes=None,
    )
    assert row["usage_by_reviewer"]["grok"]["telemetry_quality"] == "known-issues"


def test_downgraded_state_yields_ineligible_row(tmp_path):
    """A pykrete exit-3 downgrade (rc!=0, ok=True) must not count toward the
    paired-comparison log — drives the real state.json -> write_harvest_row.main
    boundary, not a direct build_row(ReviewerResult(...)) call."""
    from multi_review.cli.write_harvest_row import main as write_harvest_row_main

    state_dir = tmp_path / "states"
    state_dir.mkdir()
    (state_dir / "pykrete.state.json").write_text(json.dumps({
        "cli": "pykrete",
        "ok": True,
        "duration_seconds": 4.0,
        "stderr_tail": "",
        "usage": {"input_tokens": 10, "output_tokens": 20, "cached_tokens": 0, "tool_calls": 0},
        "final_model": "family:fallback-model",
        "downgraded": True,
        "error": None,
    }))

    review = tmp_path / "REVIEW.md"
    review.write_text("# Review\n" + ("x" * 200))
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Review this.")
    log = tmp_path / "runs.jsonl"

    rc = write_harvest_row_main([
        "--state-dir", str(state_dir),
        "--out-review", str(review),
        "--prompt-file", str(prompt),
        "--run-id", "r1",
        "--log", str(log),
        "--mode", "inline",
        "--project", "test",
        "--task", "code",
        "--drift-status", "clean",
    ])
    assert rc == 0
    row = json.loads(log.read_text().splitlines()[0])
    assert row["usage_by_reviewer"]["pykrete"]["comparison_eligible"] is False


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


def test_build_row_includes_new_fields():
    row = build_row(
        results=[_r("claude")],
        run_id="r1",
        started_at="2026-06-19T10:00:00Z",
        finished_at="2026-06-19T10:01:30Z",
        cwd="/tmp/proj",
        prompt_bytes=1234,
        output_bytes=5678,
        mode="inline", task="code", project="proj",
        wall_seconds=90.0,
        reviewers_attempted=["claude"],
        synthesizer=None, synthesis_ok=False,
        pair_id=None, prompt_file="p.md", prompt_format_version=1,
        drift_status="clean", telemetry_notes=[],
    )
    assert row["run_id"] == "r1"
    assert row["started_at"] == "2026-06-19T10:00:00Z"
    assert row["finished_at"] == "2026-06-19T10:01:30Z"
    assert row["cwd"] == "/tmp/proj"
    assert "argv" not in row
    assert row["prompt_bytes"] == 1234
    assert row["output_bytes"] == 5678


def test_build_row_guards_usage_none():
    """build_row must not crash when a ReviewerResult.usage is None."""
    rr_no_usage = ReviewerResult(
        cli="claude", ok=True, text="x" * 200, stderr_tail="",
        usage=None,
        elapsed=1.0,
        model_used="m",
    )
    row = build_row(
        results=[rr_no_usage],
        run_id="r2",
        started_at="2026-06-19T10:00:00Z",
        finished_at="2026-06-19T10:01:00Z",
        cwd="/tmp/proj",
        prompt_bytes=100,
        output_bytes=200,
        mode="inline", task="code", project="p",
        wall_seconds=60.0,
        reviewers_attempted=["claude"],
        synthesizer=None, synthesis_ok=False,
        pair_id=None, prompt_file=None, prompt_format_version=1,
        drift_status="clean", telemetry_notes=[],
    )
    assert row["usage_by_reviewer"]["claude"]["input_tokens"] == 0
    assert row["usage_by_reviewer"]["claude"]["output_tokens"] == 0
