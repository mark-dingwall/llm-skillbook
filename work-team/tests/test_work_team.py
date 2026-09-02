"""Behavioral tests for work-team's deterministic helpers."""

from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


COMPONENT = Path(__file__).resolve().parents[1]
VALIDATE = COMPONENT / "scripts" / "wt-validate"
SCHEMAS = COMPONENT / "references" / "schemas"
RUN_EVAL = COMPONENT / "evals" / "run-eval.sh"
EXTRACT_RESPONSE = COMPONENT / "evals" / "extract-response.py"
TELEMETRY = COMPONENT / "scripts" / "wt-telemetry"
WT_LOG = COMPONENT / "scripts" / "wt-log"


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


@pytest.mark.parametrize(("field", "value"), [("id", ""), ("verify", "")])
def test_plan_rejects_blank_worker_identity_or_verification(
    field: str, value: str
) -> None:
    result = validate("plan.schema.json", plan(worker(**{field: value})))

    assert result.returncode == 1
    assert f".{field}:" in result.stderr


def test_plan_rejects_duplicate_worker_ids_within_a_phase() -> None:
    value = plan(worker())
    value["phases"][0]["workers"].append(worker(goal="A different goal. Done."))

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert ".workers:" in result.stderr


def test_plan_rejects_duplicate_phase_ids() -> None:
    value = plan(worker())
    value["phases"].append({"id": "build", "workers": [worker(id="other")]})

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert "$.phases:" in result.stderr


def test_plan_rejects_non_positive_review_loop_bound() -> None:
    result = validate("plan.schema.json", plan(worker(), max_rounds=0))

    assert result.returncode == 1
    assert ".max_rounds:" in result.stderr


@pytest.mark.parametrize(
    "run_id", ["", ".", "..", "../../outside", "/tmp/outside", "nested/run"]
)
def test_plan_rejects_unsafe_run_identifier(run_id: str) -> None:
    value = plan(worker())
    value["run"] = run_id

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert "$.run:" in result.stderr


@pytest.mark.parametrize("target", ["phase", "worker"])
def test_plan_rejects_colons_in_composed_attempt_id_parts(target: str) -> None:
    value = plan(worker())
    if target == "phase":
        value["phases"][0]["id"] = "build:one"
    else:
        value["phases"][0]["workers"][0]["id"] = "writer:one"

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert ".id:" in result.stderr


@pytest.mark.parametrize(("field", "value"), [("goal", "   "), ("verify", "   ")])
def test_plan_rejects_whitespace_only_worker_instruction(
    field: str, value: str
) -> None:
    result = validate("plan.schema.json", plan(worker(**{field: value})))

    assert result.returncode == 1
    assert f".{field}:" in result.stderr


@pytest.mark.parametrize(
    ("review_role", "fix_role"),
    [
        ("", "fixer"),
        ("writer", "fixer"),
        ("reviewer", "reviewer"),
        ("reviewer", "writer"),
    ],
)
def test_plan_rejects_invalid_review_loop_role_mapping(
    review_role: str, fix_role: str
) -> None:
    value = plan(worker(), max_rounds=1)
    value["phases"][0]["loop"].update(review=review_role, fix=fix_role)

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert ".loop." in result.stderr


def test_plan_accepts_judge_as_read_only_loop_reviewer() -> None:
    value = plan(worker(), max_rounds=1)
    value["phases"][0]["loop"]["review"] = "judge"

    result = validate("plan.schema.json", value)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("role", ["reviewer", "verifier", "judge"])
def test_plan_rejects_owned_paths_for_read_only_role(role: str) -> None:
    result = validate("plan.schema.json", plan(worker(role=role)))

    assert result.returncode == 1
    assert ".owns:" in result.stderr


@pytest.mark.parametrize("alias", ["./src/a.py", "src/dir/../a.py"])
def test_plan_rejects_canonical_owned_path_overlap(alias: str) -> None:
    value = plan(worker(id="first", owns=["src/a.py"]))
    value["phases"][0]["workers"].append(worker(id="second", owns=[alias]))

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert ".workers:" in result.stderr
    assert "src/a.py" in result.stderr


@pytest.mark.parametrize("owned_path", ["", ".", "../outside.txt", "/tmp/outside.txt"])
def test_plan_rejects_path_outside_repository_ownership(owned_path: str) -> None:
    result = validate("plan.schema.json", plan(worker(owns=[owned_path])))

    assert result.returncode == 1
    assert ".owns[0]:" in result.stderr


def test_plan_rejects_same_group_producer_consumer_dependency() -> None:
    value = plan(worker(id="producer", owns=["generated/output.json"]))
    value["phases"][0]["workers"].append(
        worker(id="consumer", inputs=["generated/output.json"], owns=["report.md"])
    )

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert ".workers:" in result.stderr
    assert "producer/consumer" in result.stderr


def test_plan_accepts_producer_consumer_in_ordered_groups() -> None:
    value = plan(
        worker(id="producer", group="first", owns=["generated/output.json"])
    )
    value["phases"][0]["workers"].append(
        worker(
            id="consumer",
            group="second",
            inputs=["generated/output.json"],
            owns=["report.md"],
        )
    )

    result = validate("plan.schema.json", value)

    assert result.returncode == 0, result.stderr


def test_plan_treats_freeform_task_input_as_data_not_a_path() -> None:
    result = validate("plan.schema.json", plan(worker(inputs=["x" * 5000])))

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("field", ["inputs", "owns"])
def test_plan_reports_malformed_worker_path_lists_without_crashing(
    field: str,
) -> None:
    value = plan(worker(**{field: None}))
    if field == "owns":
        value["phases"][0]["workers"].append(worker(id="other"))
    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert f".{field}: expected array" in result.stderr
    assert "Traceback" not in result.stderr


def test_plan_rejects_directory_and_descendant_ownership_overlap() -> None:
    value = plan(worker(id="directory-owner", owns=["src"]))
    value["phases"][0]["workers"].append(
        worker(id="file-owner", owns=["src/main.py"])
    )

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert ".workers:" in result.stderr


def test_plan_rejects_symlinked_repository_ownership_alias() -> None:
    value = plan(worker(id="canonical", owns=["work-team/SKILL.md"]))
    value["phases"][0]["workers"].append(
        worker(id="alias", owns=[".agents/skills/work-team/SKILL.md"])
    )

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert ".workers:" in result.stderr


def test_review_rejects_changes_required_without_findings() -> None:
    result = validate(
        "review.schema.json", {"verdict": "changes_required", "findings": []}
    )

    assert result.returncode == 1
    assert ".findings:" in result.stderr


def review_finding(**overrides: object) -> dict:
    value = {
        "severity": "important",
        "scope": "spec",
        "where": "src/app.py:1",
        "issue": "The required behavior is missing.",
        "fix": "Implement the required behavior.",
    }
    value.update(overrides)
    return value


def test_review_rejects_pass_with_spec_finding() -> None:
    result = validate(
        "review.schema.json",
        {"verdict": "pass", "findings": [review_finding()]},
    )

    assert result.returncode == 1
    assert ".scope:" in result.stderr


def test_review_accepts_pass_with_adjacent_observation() -> None:
    result = validate(
        "review.schema.json",
        {
            "verdict": "pass",
            "findings": [review_finding(scope="adjacent")],
        },
    )

    assert result.returncode == 0, result.stderr


def test_review_rejects_changes_required_with_only_adjacent_findings() -> None:
    result = validate(
        "review.schema.json",
        {
            "verdict": "changes_required",
            "findings": [review_finding(scope="adjacent")],
        },
    )

    assert result.returncode == 1
    assert ".findings:" in result.stderr


@pytest.mark.parametrize(
    ("field", "value"),
    [(field, value) for field in ["where", "issue", "fix"] for value in ["", "   "]],
)
def test_review_rejects_blank_actionable_finding_field(
    field: str, value: str
) -> None:
    result = validate(
        "review.schema.json",
        {
            "verdict": "changes_required",
            "findings": [review_finding(**{field: value})],
        },
    )

    assert result.returncode == 1
    assert f".{field}:" in result.stderr


def result_payload(**overrides: object) -> dict:
    value = {
        "run": "run-1",
        "outcome": "complete",
        "verification": [
            {"command": "test -s artefact.txt", "passed": True, "output": ""}
        ],
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


def test_complete_result_rejects_uncovered_requirement() -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            residual=[{"kind": "gap", "detail": "No worker covered requirement 3."}]
        ),
    )

    assert result.returncode == 1
    assert ".kind:" in result.stderr


def test_complete_result_rejects_important_capped_finding() -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            residual=[
                {
                    "kind": "loop_cap",
                    "detail": "Required behavior remains broken.",
                    "severity": "important",
                    "scope": "spec",
                }
            ]
        ),
    )

    assert result.returncode == 1
    assert ".severity:" in result.stderr


def test_capped_finding_requires_structured_severity_and_scope() -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            outcome="partial",
            residual=[{"kind": "loop_cap", "detail": "Review round capped."}],
        ),
    )

    assert result.returncode == 1
    assert ".severity: required" in result.stderr
    assert ".scope: required" in result.stderr


def test_complete_result_requires_worker_records() -> None:
    result = validate("result.schema.json", result_payload(workers=[]))

    assert result.returncode == 1
    assert ".workers:" in result.stderr


def test_complete_result_rejects_blank_verification_command() -> None:
    result = validate(
        "result.schema.json",
        result_payload(verification=[{"command": "", "passed": True, "output": ""}]),
    )

    assert result.returncode == 1
    assert ".command:" in result.stderr


def test_result_requires_exact_verification_output_field() -> None:
    result = validate(
        "result.schema.json",
        result_payload(verification=[{"command": "true", "passed": True}]),
    )

    assert result.returncode == 1
    assert ".output: required" in result.stderr


@pytest.mark.parametrize(
    ("field", "path"),
    [
        ("plan", ""),
        ("plan", "/tmp/plan.json"),
        ("plan", ".work-team/other/plan.json"),
        ("log", ""),
        ("log", "/tmp/workflow-log.jsonl"),
        ("log", ".work-team/other/workflow-log.jsonl"),
    ],
)
def test_result_artifact_paths_are_bound_to_declared_run(
    field: str, path: str
) -> None:
    result = validate("result.schema.json", result_payload(**{field: path}))

    assert result.returncode == 1
    assert f"$.{field}:" in result.stderr


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


@pytest.mark.parametrize("verify_output", [None, "", "   "])
def test_successful_worker_status_requires_verification_output(
    verify_output: str | None,
) -> None:
    payload = {"ok": True, "note": "done", "artefacts": ["artefact.txt"]}
    if verify_output is not None:
        payload["verify_output"] = verify_output

    result = validate("status.schema.json", payload)

    assert result.returncode == 1
    assert ".verify_output:" in result.stderr


def test_failed_worker_status_does_not_require_verification_output() -> None:
    result = validate(
        "status.schema.json", {"ok": False, "note": "failed", "artefacts": []}
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


def test_verifier_return_rejects_duplicate_candidate_ids() -> None:
    result = validate(
        "verifier.schema.json",
        {
            "candidates": [
                {"id": "candidate-1", "verdict": "confirmed", "evidence": "x.py:4"},
                {"id": "candidate-1", "verdict": "refuted", "evidence": "x.py:8"},
            ]
        },
    )

    assert result.returncode == 1
    assert ".candidates:" in result.stderr


@pytest.mark.parametrize("evidence", ["", "   "])
def test_verifier_return_rejects_blank_evidence(evidence: str) -> None:
    result = validate(
        "verifier.schema.json",
        {
            "candidates": [
                {"id": "candidate-1", "verdict": "confirmed", "evidence": evidence}
            ]
        },
    )

    assert result.returncode == 1
    assert ".evidence:" in result.stderr


def test_unique_id_validation_reports_unhashable_values_without_crashing() -> None:
    result = validate(
        "verifier.schema.json",
        {"candidates": [{"id": {}, "verdict": "confirmed", "evidence": "x.py:4"}]},
    )

    assert result.returncode == 1
    assert "expected string" in result.stderr
    assert "Traceback" not in result.stderr


def run_codex_eval(
    tmp_path: Path,
    timestamp: str,
    *,
    script: str | None = None,
    scenario: str = "A",
    workspace: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    codex = fake_bin / "codex"
    codex.write_text(
        script
        or (
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"thread-child\"]}}' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"receiver_thread_ids\":[\"thread-child\"],\"agents_states\":{\"thread-child\":{\"completed\":\"{}\"}}}}' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"progress\"}}' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\\ncomplete\"}}'\n"
        )
    )
    codex.chmod(0o755)
    env = os.environ | {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "EVAL_TS": timestamp,
        "EVAL_WS": str(workspace or tmp_path / "workspace"),
    }
    return subprocess.run(
        [str(RUN_EVAL), "refactor", scenario, "codex", "attempt-1"],
        text=True,
        capture_output=True,
        env=env,
    )


def eval_output(timestamp: str, *, scenario: str = "A") -> Path:
    return (
        COMPONENT
        / "evals"
        / "transcripts"
        / "refactor"
        / timestamp
        / f"Scenario-{scenario}-codex"
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


def test_eval_runner_substitutes_fixture_path_literally(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-fixture"
    output = eval_output(timestamp, scenario="B")
    workspace = tmp_path / "R&D"
    try:
        result = run_codex_eval(
            tmp_path, timestamp, scenario="B", workspace=workspace
        )

        assert result.returncode == 0, result.stderr
        fixture = (
            workspace
            / f"refactor-{timestamp}-B-codex-attempt-1"
            / "audit-target"
        )
        assert str(fixture) in (output / "prompt.txt").read_text()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_success_without_final_agent_response(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-empty"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' '{\"type\":\"thread.started\"}'\n"
            ),
        )

        assert result.returncode != 0
        assert "no final agent response" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_whitespace_only_final_agent_response(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-blank"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' "
                "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"   \"}}'\n"
            ),
        )

        assert result.returncode != 0
        assert "no final agent response" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_success_without_worker_dispatch(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-no-dispatch"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' "
                "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"simulated team\"}}'\n"
            ),
        )

        assert result.returncode != 0
        assert "no worker dispatch" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_spawn_without_worker_id(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-no-worker-id"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' "
                "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[]}}' "
                "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"simulated team\"}}'\n"
            ),
        )

        assert result.returncode != 0
        assert "no worker dispatch" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_propagates_harness_exit_status(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-exit"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' "
                "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"failed\"}}'\n"
                "exit 23\n"
            ),
        )

        assert result.returncode == 23
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_extracts_response_without_jq(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-no-jq"
    output = eval_output(timestamp)
    jq_marker = tmp_path / "jq-called"
    jq = tmp_path / "bin" / "jq"
    jq.parent.mkdir(exist_ok=True)
    jq.write_text(f"#!/usr/bin/env bash\ntouch '{jq_marker}'\nexit 99\n")
    jq.chmod(0o755)
    try:
        result = run_codex_eval(tmp_path, timestamp)

        assert result.returncode == 0, result.stderr
        assert not jq_marker.exists()
        assert (output / "final-response.md").read_text() == "final\ncomplete\n"
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_uses_python_stdlib_instead_of_shell_utilities(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-stdlib"
    output = eval_output(timestamp)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex = fake_bin / "codex"
    codex.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "events = [\n"
        "    {'type': 'item.completed', 'item': {'type': 'collab_tool_call', 'tool': 'spawn_agent', 'status': 'completed', 'receiver_thread_ids': ['worker-1']}},\n"
        "    {'type': 'item.completed', 'item': {'type': 'collab_tool_call', 'tool': 'wait', 'status': 'completed', 'receiver_thread_ids': ['worker-1'], 'agents_states': {'worker-1': {'completed': '{}'}}}},\n"
        "    {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'final'}},\n"
        "]\n"
        "for event in events:\n"
        "    print(json.dumps(event))\n"
    )
    codex.chmod(0o755)
    env = os.environ | {
        "PATH": str(fake_bin),
        "EVAL_TS": timestamp,
        "EVAL_WS": str(tmp_path / "workspace"),
    }
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(RUN_EVAL),
                "refactor",
                "A",
                "codex",
                "attempt-1",
            ],
            text=True,
            capture_output=True,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert (output / "final-response.md").read_text() == "final\n"
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_response_extractor_supports_claude_result_events(tmp_path: Path) -> None:
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "tool-agent-1",
                                    "name": "Agent",
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "tool-agent-1",
                                    "content": "worker result",
                                }
                            ]
                        },
                        "tool_use_result": {
                            "status": "async_launched",
                            "agentId": "agent-1",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "task_notification",
                        "tool_use_id": "tool-agent-1",
                        "task_id": "agent-1",
                        "status": "completed",
                        "summary": "worker result",
                    }
                ),
                json.dumps({"type": "assistant", "message": "progress"}),
                json.dumps({"type": "result", "result": "final\ncomplete"}),
            ]
        )
        + "\n"
    )

    result = subprocess.run(
        ["python3", str(EXTRACT_RESPONSE), "claude", str(transcript)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "final\ncomplete\n"


def test_response_extractor_rejects_unreturned_claude_agent_request(
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "tool-agent-1",
                                    "name": "Agent",
                                }
                            ]
                        },
                    }
                ),
                json.dumps({"type": "result", "result": "final\ncomplete"}),
            ]
        )
        + "\n"
    )

    result = subprocess.run(
        ["python3", str(EXTRACT_RESPONSE), "claude", str(transcript)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""


def test_response_extractor_rejects_unfinished_claude_agent(tmp_path: Path) -> None:
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "tool-agent-1",
                                    "name": "Agent",
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "tool-agent-1",
                                }
                            ]
                        },
                        "tool_use_result": {
                            "status": "async_launched",
                            "agentId": "agent-1",
                        },
                    }
                ),
                json.dumps({"type": "result", "result": "final\ncomplete"}),
            ]
        )
        + "\n"
    )

    result = subprocess.run(
        ["python3", str(EXTRACT_RESPONSE), "claude", str(transcript)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""


def run_response_extractor(
    tmp_path: Path, harness: str, events: list[dict]
) -> subprocess.CompletedProcess[str]:
    transcript = tmp_path / f"{harness}.jsonl"
    transcript.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    return subprocess.run(
        ["python3", str(EXTRACT_RESPONSE), harness, str(transcript)],
        text=True,
        capture_output=True,
    )


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_response_extractor_rejects_empty_claude_worker_return(
    tmp_path: Path, mode: str
) -> None:
    events = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-agent-1",
                        "name": "Agent",
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "tool-agent-1"}
                ]
            },
            "tool_use_result": {
                "status": "completed" if mode == "sync" else "async_launched",
                "agentId": "agent-1",
                "content": [],
            },
        },
    ]
    if mode == "async":
        events.append(
            {
                "type": "system",
                "subtype": "task_notification",
                "tool_use_id": "tool-agent-1",
                "task_id": "agent-1",
                "status": "completed",
                "summary": "   ",
            }
        )
    events.append({"type": "result", "result": "final"})

    result = run_response_extractor(tmp_path, "claude", events)

    assert result.returncode == 2
    assert result.stdout == ""


def test_response_extractor_requires_every_claude_worker_to_finish(
    tmp_path: Path,
) -> None:
    events = []
    for number in (1, 2):
        events.extend(
            [
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": f"tool-agent-{number}",
                                "name": "Agent",
                            }
                        ]
                    },
                },
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": f"tool-agent-{number}",
                            }
                        ]
                    },
                    "tool_use_result": {
                        "status": "async_launched",
                        "agentId": f"agent-{number}",
                    },
                },
            ]
        )
    events.extend(
        [
            {
                "type": "system",
                "subtype": "task_notification",
                "tool_use_id": "tool-agent-1",
                "task_id": "agent-1",
                "status": "completed",
            },
            {"type": "result", "result": "final"},
        ]
    )

    result = run_response_extractor(tmp_path, "claude", events)

    assert result.returncode == 2
    assert result.stdout == ""


def test_response_extractor_requires_every_codex_worker_return(tmp_path: Path) -> None:
    result = run_response_extractor(
        tmp_path,
        "codex",
        [
            {
                "type": "item.completed",
                "item": {
                    "type": "collab_tool_call",
                    "tool": "spawn_agent",
                    "status": "completed",
                    "receiver_thread_ids": ["worker-1", "worker-2"],
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "collab_tool_call",
                    "tool": "wait",
                    "status": "completed",
                    "receiver_thread_ids": ["worker-1"],
                    "agents_states": {"worker-1": {"completed": "{}"}},
                },
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "final"},
            },
        ],
    )

    assert result.returncode == 2
    assert result.stdout == ""


def test_response_extractor_requires_codex_return_before_final_response(
    tmp_path: Path,
) -> None:
    result = run_response_extractor(
        tmp_path,
        "codex",
        [
            {
                "type": "item.completed",
                "item": {
                    "type": "collab_tool_call",
                    "tool": "spawn_agent",
                    "status": "completed",
                    "receiver_thread_ids": ["worker-1"],
                },
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "premature final"},
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "collab_tool_call",
                    "tool": "wait",
                    "status": "completed",
                    "receiver_thread_ids": ["worker-1"],
                    "agents_states": {"worker-1": {"completed": "{}"}},
                },
            },
        ],
    )

    assert result.returncode == 2
    assert result.stdout == ""


@pytest.mark.parametrize(
    "malformed",
    [None, {"ts": "2026-09-01T00:00:00Z", "agent": []}],
)
def test_telemetry_skips_invalid_record_and_continues(
    tmp_path: Path, malformed: object
) -> None:
    log = tmp_path / "workflow-log.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps(malformed),
                json.dumps(
                    {
                        "ts": "2026-09-01T00:00:00Z",
                        "agent": "writer:r1",
                        "action": "start",
                        "artefacts": [],
                    }
                ),
            ]
        )
        + "\n"
    )

    result = subprocess.run(
        [str(TELEMETRY), str(log)], text=True, capture_output=True
    )

    assert result.returncode == 0, result.stderr
    assert "skip malformed line:" in result.stderr
    assert "writer:r1" in result.stdout


def test_telemetry_skips_timezone_less_timestamp_and_continues(
    tmp_path: Path,
) -> None:
    log = tmp_path / "workflow-log.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-09-01T00:00:00",
                        "agent": "writer:r1",
                        "action": "invalid",
                        "artefacts": [],
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-09-01T00:00:01Z",
                        "agent": "writer:r1",
                        "action": "valid",
                        "artefacts": [],
                    }
                ),
            ]
        )
        + "\n"
    )

    result = subprocess.run(
        [str(TELEMETRY), str(log)], text=True, capture_output=True
    )

    assert result.returncode == 0, result.stderr
    assert "skip malformed line:" in result.stderr
    assert "writer:r1" in result.stdout
    assert "      1" in result.stdout


def test_wt_log_rejects_record_at_or_above_four_kib(tmp_path: Path) -> None:
    log = tmp_path / "workflow-log.jsonl"

    result = subprocess.run(
        [str(WT_LOG), str(log), "writer:r1", "start", "x" * 5000],
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "4 KiB" in result.stderr
    assert not log.exists()


def test_wt_log_fails_when_append_is_short(tmp_path: Path) -> None:
    log = tmp_path / "workflow-log.jsonl"
    argv = [str(WT_LOG), str(log), "writer:r1", "start"]

    with patch.object(sys, "argv", argv), patch("os.write", return_value=1):
        with pytest.raises(OSError, match="short audit-log write"):
            runpy.run_path(str(WT_LOG), run_name="__main__")
