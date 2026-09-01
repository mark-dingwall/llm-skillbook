"""Behavioral tests for work-team's deterministic helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


COMPONENT = Path(__file__).resolve().parents[1]
VALIDATE = COMPONENT / "scripts" / "wt-validate"
SCHEMAS = COMPONENT / "references" / "schemas"
RUN_EVAL = COMPONENT / "evals" / "run-eval.sh"


def validate(schema: str, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(VALIDATE), str(SCHEMAS / schema)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )


def worker(**overrides: object) -> dict:
    value = {
        "id": "writer",
        "role": "writer",
        "goal": "Write the artefact. Done when its check passes.",
        "inputs": [],
        "owns": ["artefact.txt"],
        "verify": "test -s artefact.txt",
    }
    value.update(overrides)
    return value


def plan(worker_value: dict, *, max_rounds: int | None = None) -> dict:
    phase = {"id": "build", "workers": [worker_value]}
    if max_rounds is not None:
        phase["loop"] = {
            "review": "reviewer",
            "fix": "fixer",
            "max_rounds": max_rounds,
        }
    return {"run": "run-1", "task": "build", "phases": [phase]}


def test_plan_accepts_complete_worker_without_duplicated_return_schema() -> None:
    result = validate("plan.schema.json", plan(worker()))

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("missing", ["inputs", "verify"])
def test_plan_rejects_worker_missing_packet_input(missing: str) -> None:
    value = worker()
    value.pop(missing)

    result = validate("plan.schema.json", plan(value))

    assert result.returncode == 1
    assert f".{missing}: required" in result.stderr


def test_plan_rejects_unknown_role() -> None:
    result = validate("plan.schema.json", plan(worker(role="critic")))

    assert result.returncode == 1
    assert ".role:" in result.stderr


def test_plan_rejects_non_positive_review_loop_bound() -> None:
    result = validate("plan.schema.json", plan(worker(), max_rounds=0))

    assert result.returncode == 1
    assert ".max_rounds:" in result.stderr


def test_review_rejects_changes_required_without_findings() -> None:
    result = validate(
        "review.schema.json", {"verdict": "changes_required", "findings": []}
    )

    assert result.returncode == 1
    assert ".findings:" in result.stderr


def result_payload(**overrides: object) -> dict:
    value = {
        "run": "run-1",
        "outcome": "complete",
        "verification": [{"command": "test -s artefact.txt", "passed": True}],
        "residual": [],
        "workers": [{"id": "writer:r1", "role": "writer", "status": "ok"}],
        "plan": ".work-team/run-1/plan.json",
        "log": ".work-team/run-1/workflow-log.jsonl",
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    "verification",
    [[], [{"command": "false", "passed": False}]],
)
def test_complete_result_requires_successful_verification(verification: list) -> None:
    result = validate("result.schema.json", result_payload(verification=verification))

    assert result.returncode == 1
    assert ".verification" in result.stderr


def test_complete_result_rejects_important_finding() -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            residual=[
                {
                    "kind": "finding",
                    "detail": "required behavior remains broken",
                    "severity": "important",
                    "scope": "spec",
                }
            ]
        ),
    )

    assert result.returncode == 1
    assert ".severity:" in result.stderr


def test_finding_residual_requires_structured_severity_and_scope() -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            outcome="partial",
            residual=[{"kind": "finding", "detail": "behavior remains broken"}],
        ),
    )

    assert result.returncode == 1
    assert ".severity: required" in result.stderr
    assert ".scope: required" in result.stderr


def test_non_finding_residual_does_not_require_finding_metadata() -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            outcome="partial",
            residual=[{"kind": "worker_failed", "detail": "worker stalled"}],
        ),
    )

    assert result.returncode == 0, result.stderr


def test_verifier_return_requires_candidate_identity_and_verdict() -> None:
    valid = validate(
        "verifier.schema.json",
        {
            "candidates": [
                {"id": "candidate-1", "verdict": "confirmed", "evidence": "x.py:4"}
            ]
        },
    )
    invalid = validate(
        "verifier.schema.json",
        {"candidates": [{"verdict": "confirmed", "evidence": "x.py:4"}]},
    )

    assert valid.returncode == 0, valid.stderr
    assert invalid.returncode == 1
    assert ".id: required" in invalid.stderr


def run_codex_eval(tmp_path: Path, timestamp: str) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    codex = fake_bin / "codex"
    codex.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"progress\"}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\\ncomplete\"}}'\n"
    )
    codex.chmod(0o755)
    env = os.environ | {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "EVAL_TS": timestamp,
        "EVAL_WS": str(tmp_path / "workspace"),
    }
    return subprocess.run(
        [str(RUN_EVAL), "refactor", "A", "codex", "attempt-1"],
        text=True,
        capture_output=True,
        env=env,
    )


def eval_output(timestamp: str) -> Path:
    return (
        COMPONENT
        / "evals"
        / "transcripts"
        / "refactor"
        / timestamp
        / "Scenario-A-codex"
        / "attempt-1"
    )


def test_eval_runner_keeps_only_complete_terminal_codex_response(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-terminal"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(tmp_path, timestamp)

        assert result.returncode == 0, result.stderr
        assert (output / "final-response.md").read_text() == "final\ncomplete\n"
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_existing_output_or_workspace(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-collision"
    output = eval_output(timestamp)
    try:
        first = run_codex_eval(tmp_path, timestamp)
        second = run_codex_eval(tmp_path, timestamp)

        assert first.returncode == 0, first.stderr
        assert second.returncode != 0
        assert "already exists" in second.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)
