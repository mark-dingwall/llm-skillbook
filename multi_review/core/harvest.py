"""multi_review.core.harvest — run-metadata harvest helpers.

Schema version history
----------------------
v1  Initial schema. Top-level ``usage`` key held a flat dict of per-reviewer
    token/elapsed data.
v2  Alias-preserving rename: ``usage_by_reviewer`` is the canonical key;
    ``usage`` is retained as a deprecated read-only alias for one release
    cycle. New top-level fields: ``pair_id``, ``prompt_file``,
    ``prompt_format_version``, ``drift_status``, ``telemetry_notes``.
    Per-reviewer sub-dict gains: ``telemetry_quality``, ``comparison_eligible``,
    ``final_model``.
    **Remove ``usage`` alias in v3** — the alias is only kept for tooling
    that reads runs/runs.jsonl directly and hasn't migrated yet.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from multi_review.core.fanout import ReviewerResult

# Bump this ONLY on field rename/removal. Additive fields are safe without
# bumping. Alias-preserving renames (like usage → usage_by_reviewer in v2)
# DO require a bump; they change the schema contract.
HARVEST_SCHEMA_VERSION = 2  # Remove `usage` deprecated alias in v3.

# telemetry_quality per-CLI defaults. Update when upstream event schemas change.
# "reliable"     — token counts match what the API/billing reports.
# "known-issues" — systematic under/over-reporting observed in practice.
# "degraded"     — counts not available or structurally broken.
TELEMETRY_QUALITY: dict[str, str] = {
    "claude": "known-issues",   # input/output token under-reporting observed
    "gemini": "reliable",
    "codex": "reliable",
    "opencode": "known-issues",
}


def _iso_utc(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def derive_project(cwd: Path, override: str | None) -> str:
    """Stable project key for harvest rows.

    Precedence: explicit override > git remote origin basename > cwd basename.
    Worktrees inherit the parent repo's origin, so paired runs from
    ``Guestflow-16.1/`` and ``Guestflow/`` share one bucket.
    """
    if override:
        return override
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd, capture_output=True, text=True,
            timeout=2, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            url = out.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            for sep in ("/", ":"):
                if sep in url:
                    return url.rsplit(sep, 1)[-1]
            return url
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return cwd.name


def _usage_dict(r: ReviewerResult) -> dict:
    u = getattr(r, "usage", None)
    if u is None:
        return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "tool_calls": 0}
    return u.as_dict()


def build_row(
    *,
    results: list[ReviewerResult],
    mode: str,
    task: str,
    project: str,
    wall_seconds: float | None,
    reviewers_attempted: list[str],
    synthesizer: str | None,
    synthesis_ok: bool,
    pair_id: str | None,
    prompt_file: str | None,
    prompt_format_version: int | None,
    drift_status: str,
    telemetry_notes: list[str] | str | None,
    # New fields added in B14:
    run_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    cwd: str | None = None,
    prompt_bytes: int | None = None,
    output_bytes: int | None = None,
    # argv omitted: sys.argv inside write_harvest_row is the CLI's own argv, not
    # the SKILL's. Deferred to v0.2.1 alongside proper --argv plumbing.
) -> dict:
    """Build a v2 harvest row dict (pure — no I/O).

    ``pair_id``              paired-run correlation token (None for standalone runs).
    ``prompt_file``          path to the prompt YAML used, if any.
    ``prompt_format_version`` version of the prompt format spec.
    ``drift_status``         one of "clean", "drifted", "unchecked", "not_applicable".
    ``telemetry_notes``      freeform annotation for anomalous telemetry.
    """
    drift_blocks_eligibility = drift_status in {"drifted", "unchecked"}
    usage_by_reviewer: dict[str, dict] = {}
    for r in results:
        final_model = r.model_used
        per_rev = {
            **_usage_dict(r),
            "elapsed_s": round(r.elapsed, 1),
            # v2 additions
            "telemetry_quality": TELEMETRY_QUALITY.get(r.cli, "degraded"),
            "comparison_eligible": not drift_blocks_eligibility,
            "final_model": final_model,
        }
        usage_by_reviewer[r.cli] = per_rev

    row = {
        "schema_version": HARVEST_SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "wall_seconds": round(wall_seconds, 1) if wall_seconds is not None else None,
        "cwd": cwd,
        "mode": mode,
        "task": task,
        "project": project,
        "prompt_bytes": prompt_bytes,
        "output_bytes": output_bytes,
        "reviewers_attempted": reviewers_attempted,
        "reviewers_succeeded": [r.cli for r in results if r.ok],
        "reviewers_failed": [r.cli for r in results if not r.ok],
        "synthesizer": synthesizer,
        "synthesis_ok": synthesis_ok,
        # v2 new top-level fields
        "pair_id": pair_id,
        "prompt_file": prompt_file,
        "prompt_format_version": prompt_format_version,
        "drift_status": drift_status,
        "telemetry_notes": telemetry_notes,
        # canonical v2 key
        "usage_by_reviewer": usage_by_reviewer,
        # deprecated alias — remove in v3 (see module docstring)
        "usage": usage_by_reviewer,
    }
    return row


def harvest_run(*, log_path: Path, row: dict) -> None:
    """Append one JSONL row to log_path, creating parent dirs as needed.

    Pure append-only writer — no reads, no schema validation here.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")


def legacy_harvest_run(
    *,
    started_at: float,
    finished_at: float,
    mode: str,
    prompt_bytes: int,
    reviewers_succeeded: list[str],
    reviewers_failed: list[str],
    usage_by_reviewer: dict[str, dict],
    output_path: "Path | None",
    output_bytes: int,
    cwd: Path,
    invocation_argv: list[str],
    project_tag: str | None = None,
    log_path: Path | None = None,
) -> None:
    """Bridge for the legacy callsite in multi_review.py.

    Builds a v2 row from the flat legacy kwargs and appends it.  Fields that
    don't exist in the legacy call path (pair_id, prompt_file, etc.) are
    passed as None / "not_applicable" so consumers always see valid v2 rows.
    """
    if log_path is None:
        # Default: same location the old code used (script-file-relative).
        import multi_review as _mr_pkg
        runs_dir = Path(_mr_pkg.__file__).resolve().parent / "runs"
        log_path = runs_dir / "runs.jsonl"

    # Build a synthetic usage_by_reviewer that matches v2 shape.
    # The legacy caller already aggregated token data into usage_by_reviewer;
    # we need to add the new per-reviewer v2 fields.
    enriched: dict[str, dict] = {}
    for cli, u in usage_by_reviewer.items():
        final_model = u.get("final_model")
        enriched[cli] = {
            **u,
            "telemetry_quality": TELEMETRY_QUALITY.get(cli, "degraded"),
            "comparison_eligible": True,
            "final_model": final_model,
        }

    row = {
        "schema_version": HARVEST_SCHEMA_VERSION,
        "started_at": _iso_utc(started_at),
        "finished_at": _iso_utc(finished_at),
        "wall_seconds": round(finished_at - started_at, 1),
        "mode": mode,
        "prompt_bytes": prompt_bytes,
        "cwd": str(cwd),
        "project": derive_project(cwd, project_tag),
        "reviewers_succeeded": reviewers_succeeded,
        "reviewers_failed": reviewers_failed,
        "output_path": str(output_path) if output_path else None,
        "output_bytes": output_bytes,
        "argv": invocation_argv,
        # v2 new top-level fields (not available in legacy path)
        "pair_id": None,
        "prompt_file": None,
        "prompt_format_version": None,
        "drift_status": "not_applicable",
        "telemetry_notes": None,
        # canonical v2 key
        "usage_by_reviewer": enriched,
        # deprecated alias — remove in v3
        "usage": enriched,
    }
    harvest_run(log_path=log_path, row=row)
