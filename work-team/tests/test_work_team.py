"""Behavioral tests for work-team's deterministic helpers."""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest


COMPONENT = Path(__file__).resolve().parents[1]
VALIDATE = COMPONENT / "scripts" / "wt-validate"
SCHEMAS = COMPONENT / "references" / "schemas"
RUN_EVAL = COMPONENT / "evals" / "run-eval.sh"
EXTRACT_RESPONSE = COMPONENT / "evals" / "extract-response.py"
EXTRACT_CODEX_COLLABORATION = COMPONENT / "evals" / "extract-codex-collaboration.py"
INJECT_PARTIAL_VERIFIER = COMPONENT / "evals" / "inject-partial-verifier.py"
TELEMETRY = COMPONENT / "scripts" / "wt-telemetry"
WT_LOG = COMPONENT / "scripts" / "wt-log"


def validate(schema: str, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(VALIDATE), str(SCHEMAS / schema)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )


def validate_raw(schema: str, payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(VALIDATE), str(SCHEMAS / schema)],
        input=payload,
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


@pytest.mark.parametrize("field", ["run", "phase", "worker"])
def test_plan_rejects_identifier_with_trailing_newline(field: str) -> None:
    value = plan(worker())
    if field == "run":
        value["run"] = "run-1\n"
    elif field == "phase":
        value["phases"][0]["id"] = "build\n"
    else:
        value["phases"][0]["workers"][0]["id"] = "writer\n"

    result = validate("plan.schema.json", value)

    assert result.returncode == 1


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


def test_plan_rejects_judge_as_loop_reviewer_without_rubric_inputs() -> None:
    value = plan(worker(), max_rounds=1)
    value["phases"][0]["loop"]["review"] = "judge"

    result = validate("plan.schema.json", value)

    assert result.returncode == 1


@pytest.mark.parametrize("role", ["reviewer", "verifier", "judge"])
def test_plan_rejects_owned_paths_for_read_only_role(role: str) -> None:
    result = validate("plan.schema.json", plan(worker(role=role)))

    assert result.returncode == 1
    assert ".owns:" in result.stderr


@pytest.mark.parametrize("role", ["reviewer", "verifier", "judge"])
def test_plan_does_not_require_worker_verification_from_read_only_role(
    role: str,
) -> None:
    value = worker(role=role, owns=[])
    value.pop("verify")
    if role == "verifier":
        value["candidates"] = [
            {
                "id": "review:r1:F1",
                "owner": "implementer",
                "path": "src/app.py",
                "issue": "Required behavior is missing.",
            }
        ]

    plan_value = plan(value)
    if role == "verifier":
        plan_value["phases"].insert(
            0,
            {
                "id": "implement",
                "workers": [worker(id="implementer", owns=["src/app.py"])],
            },
        )

    result = validate("plan.schema.json", plan_value)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("role", ["reviewer", "verifier", "judge"])
def test_plan_rejects_worker_verification_on_read_only_role(role: str) -> None:
    result = validate("plan.schema.json", plan(worker(role=role, owns=[])))

    assert result.returncode == 1
    assert ".verify:" in result.stderr


def test_plan_requires_explicit_candidates_for_verifier() -> None:
    value = worker(role="verifier", owns=[])
    value.pop("verify")

    result = validate("plan.schema.json", plan(value))

    assert result.returncode == 1
    assert ".candidates:" in result.stderr


@pytest.mark.parametrize(
    ("owner", "path"),
    [("ghost", "src/app.py"), ("implementer", "src/unowned.py")],
)
def test_plan_rejects_unroutable_verifier_candidate(
    owner: str, path: str,
) -> None:
    value = plan(worker(id="implementer", owns=["src/app.py"]), max_rounds=1)
    verifier = worker(
        id="verifier",
        role="verifier",
        owns=[],
        candidates=[
            {
                "id": "review:r1:F1",
                "owner": owner,
                "path": path,
                "issue": "Required behavior is missing.",
            }
        ],
    )
    verifier.pop("verify")
    value["phases"].append({"id": "verify", "workers": [verifier]})

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert "candidate owner/path" in result.stderr


def test_plan_accepts_verifier_candidate_with_owned_path() -> None:
    value = plan(worker(id="implementer", owns=["src"]), max_rounds=1)
    verifier = worker(
        id="verifier",
        role="verifier",
        owns=[],
        candidates=[
            {
                "id": "review:r1:F1",
                "owner": "implementer",
                "path": "src/app.py",
                "issue": "Required behavior is missing.",
            }
        ],
    )
    verifier.pop("verify")
    value["phases"].append({"id": "verify", "workers": [verifier]})

    result = validate("plan.schema.json", value)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("malformation", ["worker_id", "owner", "candidates", "owns"])
def test_candidate_routing_reports_malformed_values_without_traceback(
    malformation: str,
) -> None:
    value = plan(worker(id="implementer", owns=["src"]))
    verifier = worker(
        id="verifier",
        role="verifier",
        owns=[],
        candidates=[
            {
                "id": "review:r1:F1",
                "owner": "implementer",
                "path": "src/app.py",
                "issue": "Required behavior is missing.",
            }
        ],
    )
    verifier.pop("verify")
    value["phases"].append({"id": "verify", "workers": [verifier]})
    if malformation == "worker_id":
        value["phases"][0]["workers"][0]["id"] = {}
    elif malformation == "owner":
        verifier["candidates"][0]["owner"] = {}
    elif malformation == "candidates":
        verifier["candidates"] = 1
    else:
        value["phases"][0]["workers"][0]["owns"] = 1

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_plan_rejects_duplicate_mutable_worker_ids_across_phases() -> None:
    value = plan(worker(id="implementer", owns=["src/a.py"]), max_rounds=1)
    value["phases"].append(
        {
            "id": "second",
            "workers": [worker(id="implementer", owns=["src/b.py"])],
        }
    )

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert "worker id" in result.stderr


def test_plan_rejects_duplicate_candidate_ids_across_verifiers() -> None:
    value = plan(worker(id="implementer", owns=["src"]))
    for verifier_id in ("verifier-a", "verifier-b"):
        verifier = worker(
            id=verifier_id,
            role="verifier",
            owns=[],
            candidates=[
                {
                    "id": "review:r1:F1",
                    "owner": "implementer",
                    "path": "src/app.py",
                    "issue": "Required behavior is missing.",
                }
            ],
        )
        verifier.pop("verify")
        value["phases"].append(
            {"id": f"verify-{verifier_id}", "workers": [verifier]}
        )

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert "candidate id" in result.stderr


def test_plan_accepts_read_only_audit_candidates_without_mutable_owner() -> None:
    reviewer = worker(id="finder", role="reviewer", owns=[])
    reviewer.pop("verify")
    value = plan(reviewer)
    verifier = worker(
        id="verifier",
        role="verifier",
        owns=[],
        candidates=[
            {
                "id": "finder:r1:F1",
                "owner": "finder",
                "path": "audit-target/app.py",
                "issue": "Required behavior is missing.",
            }
        ],
    )
    verifier.pop("verify")
    value["phases"].append({"id": "verify", "workers": [verifier]})

    result = validate("plan.schema.json", value)

    assert result.returncode == 0, result.stderr


def test_plan_accepts_read_only_audit_alongside_unrelated_loop() -> None:
    finder = worker(id="finder", role="reviewer", owns=[])
    finder.pop("verify")
    value = plan(finder)
    verifier = worker(
        id="verifier",
        role="verifier",
        owns=[],
        candidates=[
            {
                "id": "finder:r1:F1",
                "owner": "finder",
                "path": "audit-target/app.py",
                "issue": "Required behavior is missing.",
            }
        ],
    )
    verifier.pop("verify")
    value["phases"].append({"id": "verify", "workers": [verifier]})
    loop_phase = plan(
        worker(id="implementer", owns=["src/app.py"]), max_rounds=1
    )["phases"][0]
    loop_phase["id"] = "implement"
    value["phases"].append(loop_phase)

    result = validate("plan.schema.json", value)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("owner_position", ["same", "future"])
def test_plan_rejects_candidate_owner_that_is_not_in_a_prior_phase(
    owner_position: str,
) -> None:
    verifier = worker(
        id="verifier",
        role="verifier",
        owns=[],
        candidates=[
            {
                "id": "finder:r1:F1",
                "owner": "finder",
                "path": "audit-target/app.py",
                "issue": "Required behavior is missing.",
            }
        ],
    )
    verifier.pop("verify")
    finder = worker(id="finder", role="reviewer", owns=[])
    finder.pop("verify")
    if owner_position == "same":
        value = plan(finder)
        value["phases"][0]["workers"].append(verifier)
    else:
        value = plan(verifier)
        value["phases"].append({"id": "find", "workers": [finder]})

    result = validate("plan.schema.json", value)

    assert result.returncode == 1
    assert "prior worker" in result.stderr


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


@pytest.mark.parametrize("owned_path", ["src/a\nb.py", "src/a\x7fb.py"])
def test_plan_rejects_control_characters_in_owned_path(owned_path: str) -> None:
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


def test_plan_rejects_producer_consumer_in_different_groups() -> None:
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

    assert result.returncode == 1
    assert "producer/consumer" in result.stderr


def test_plan_rejects_worker_ownership_of_controller_run_directory() -> None:
    result = validate(
        "plan.schema.json",
        plan(worker(owns=[".work-team/run-1/plan.json"])),
    )

    assert result.returncode == 1
    assert ".owns[0]:" in result.stderr


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


def test_plan_symlink_loop_is_rejected_without_traceback(tmp_path: Path) -> None:
    (tmp_path / "cycle").symlink_to("cycle")
    result = subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "plan.schema.json")],
        input=json.dumps(plan(worker(owns=["cycle/file.py"]))),
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "Traceback" not in result.stderr


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
        "owner": "implementer",
        "path": "src/app.py",
        "issue": "The required behavior is missing.",
        "fix": "Implement the required behavior.",
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize("missing", ["owner", "path"])
def test_review_requires_deterministic_fixer_routing(missing: str) -> None:
    finding = review_finding()
    finding.pop(missing)

    result = validate(
        "review.schema.json",
        {"verdict": "changes_required", "findings": [finding]},
    )

    assert result.returncode == 1
    assert f".{missing}: required" in result.stderr


@pytest.mark.parametrize(
    ("owner", "path", "expected"),
    [
        ("implementer", "src/app.py", 0),
        ("ghost", "src/app.py", 1),
        ("implementer", "docs/guide.md", 1),
    ],
)
def test_loop_review_routing_is_checked_against_plan(
    tmp_path: Path, owner: str, path: str, expected: int,
) -> None:
    plan_path = tmp_path / "plan.json"
    review_path = tmp_path / "review.json"
    plan_path.write_text(
        json.dumps(plan(worker(id="implementer", owns=["src"]), max_rounds=1))
    )
    review_path.write_text(
        json.dumps(
            {
                "verdict": "changes_required",
                "findings": [review_finding(owner=owner, path=path)],
            }
        )
    )

    result = subprocess.run(
        [
            str(VALIDATE),
            str(SCHEMAS / "review.schema.json"),
            str(review_path),
            "--plan",
            str(plan_path),
            "--phase",
            "build",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == expected, result.stderr
    if expected:
        assert "finding owner/path" in result.stderr


@pytest.mark.parametrize("schema", ["review.schema.json", "verifier.schema.json"])
def test_read_only_return_rejects_verify_output(schema: str) -> None:
    if schema == "review.schema.json":
        payload = {"verdict": "pass", "findings": [], "verify_output": "true"}
    else:
        payload = {
            "candidates": [
                {"id": "candidate-1", "verdict": "confirmed", "evidence": "x.py:4"}
            ],
            "verify_output": "true",
        }

    result = validate(schema, payload)

    assert result.returncode == 1
    assert "verify_output" in result.stderr


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


def test_complete_result_rejects_minor_capped_finding() -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            residual=[
                {
                    "kind": "loop_cap",
                    "detail": "Minor finding remains open at the cap.",
                    "severity": "minor",
                    "scope": "spec",
                }
            ]
        ),
    )

    assert result.returncode == 1
    assert ".kind:" in result.stderr


@pytest.mark.parametrize("kind", ["worker_failed", "invalid_return", "skipped"])
def test_complete_result_rejects_operational_residual(kind: str) -> None:
    result = validate(
        "result.schema.json",
        result_payload(residual=[{"kind": kind, "detail": "work remains"}]),
    )

    assert result.returncode == 1
    assert ".kind:" in result.stderr


def test_validator_rejects_prose_around_json_fence() -> None:
    payload = {
        "ok": True,
        "note": "done",
        "artefacts": ["artefact.txt"],
        "verify_output": "passed",
    }
    raw = f"preface\n```json\n{json.dumps(payload)}\n```\ntrailing"

    result = validate_raw("status.schema.json", raw)

    assert result.returncode == 2


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


@pytest.mark.parametrize("status", ["failed", "invalid"])
def test_complete_result_rejects_unsuperseded_failed_worker(status: str) -> None:
    result = validate(
        "result.schema.json",
        result_payload(
            workers=[{"id": "writer:r1", "role": "writer", "status": status}]
        ),
    )

    assert result.returncode == 1
    assert ".status:" in result.stderr


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


def test_result_sweep_path_is_bound_to_declared_run() -> None:
    result = validate(
        "result.schema.json",
        result_payload(sweep=".work-team/other/completion-sweep.json"),
    )

    assert result.returncode == 1
    assert "$.sweep:" in result.stderr


def test_result_file_requires_declared_plan_and_log_to_exist(tmp_path: Path) -> None:
    run_dir = tmp_path / ".work-team" / "run-1"
    run_dir.mkdir(parents=True)
    result_file = run_dir / "result.json"
    result_file.write_text(json.dumps(result_payload()))

    result = subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "result.schema.json"), str(result_file)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "does not exist as a regular file" in result.stderr


def write_result_run(
    tmp_path: Path,
    *,
    payload: dict | None = None,
    plan_payload: dict | None = None,
    log_records: list[dict] | None = None,
    raw_plan: str | None = None,
    raw_log: str | None = None,
) -> tuple[Path, Path]:
    run_dir = tmp_path / ".work-team" / "run-1"
    run_dir.mkdir(parents=True)
    result_file = run_dir / "result.json"
    result_file.write_text(json.dumps(payload or result_payload()))
    if raw_plan is not None:
        (run_dir / "plan.json").write_text(raw_plan)
    else:
        (run_dir / "plan.json").write_text(
            json.dumps(plan_payload or plan(worker()))
        )
    if raw_log is not None:
        (run_dir / "workflow-log.jsonl").write_text(raw_log)
    else:
        records = log_records or [
            {
                "ts": "2026-09-04T00:00:00Z",
                "agent": "build:writer:r1",
                "action": "return",
                "artefacts": ["artefact.txt"],
            }
        ]
        (run_dir / "workflow-log.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in records)
        )
    return run_dir, result_file


def validate_result_file(tmp_path: Path, result_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "result.schema.json"), str(result_file)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )


@pytest.mark.parametrize("raw_plan", ["", "{not-json}"])
def test_result_file_rejects_empty_or_malformed_plan(
    tmp_path: Path, raw_plan: str
) -> None:
    _, result_file = write_result_run(tmp_path, raw_plan=raw_plan)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "$.plan:" in result.stderr


def test_result_file_rejects_plan_for_a_different_run(tmp_path: Path) -> None:
    stale_plan = plan(worker())
    stale_plan["run"] = "stale-run"
    _, result_file = write_result_run(tmp_path, plan_payload=stale_plan)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "does not match result run" in result.stderr


@pytest.mark.parametrize("raw_log", ["", "not-json\n", "{}\n"])
def test_result_file_rejects_empty_or_malformed_log(
    tmp_path: Path, raw_log: str
) -> None:
    _, result_file = write_result_run(tmp_path, raw_log=raw_log)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "$.log:" in result.stderr


def test_pre_sweep_rejects_unknown_worker_identity(tmp_path: Path) -> None:
    _, _ = write_result_run(
        tmp_path,
        log_records=[
            {
                "ts": "2026-09-04T00:00:00Z",
                "agent": "ghost:r1",
                "action": "return",
                "artefacts": [],
            }
        ],
    )

    result = subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "result.schema.json"), "--pre-sweep"],
        cwd=tmp_path,
        input=json.dumps(result_payload()),
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "plan-derived worker attempt" in result.stderr


@pytest.mark.parametrize("attempt", ["r1", "r2"])
def test_pre_sweep_accepts_plan_derived_worker_identity(
    tmp_path: Path, attempt: str
) -> None:
    write_result_run(
        tmp_path,
        log_records=[
            {
                "ts": "2026-09-04T00:00:00Z",
                "agent": f"build:writer:{attempt}",
                "action": "return",
                "artefacts": [],
            }
        ],
    )

    result = subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "result.schema.json"), "--pre-sweep"],
        cwd=tmp_path,
        input=json.dumps(result_payload()),
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr


def test_strict_json_stdin_rejects_fenced_completion_response() -> None:
    raw = '```json\n{"missing_residual": []}\n```'

    result = subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "completion.schema.json"), "--strict-json"],
        input=raw,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "not JSON" in result.stderr


def test_ordinary_stdin_still_accepts_fenced_json() -> None:
    raw = '```json\n{"ok": false, "note": "failed", "artefacts": []}\n```'

    result = validate_raw("status.schema.json", raw)

    assert result.returncode == 0, result.stderr


def test_positional_json_file_rejects_fences(tmp_path: Path) -> None:
    value_file = tmp_path / "status.json"
    value_file.write_text(
        '```json\n{"ok": false, "note": "failed", "artefacts": []}\n```'
    )

    result = subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "status.schema.json"), str(value_file)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "not JSON" in result.stderr


@pytest.mark.parametrize(
    "record",
    [
        {"ts": "not-a-time", "agent": "build:writer:r1", "action": "return", "artefacts": []},
        {"ts": "2026-09-04T00:00:00Z", "agent": "", "action": "return", "artefacts": []},
        {"ts": "2026-09-04T00:00:00Z", "agent": "build:writer:r1", "action": " ", "artefacts": []},
        {"ts": "2026-09-04T00:00:00Z", "agent": "build:writer:r1", "action": "return", "artefacts": [1]},
    ],
)
def test_result_file_rejects_malformed_audit_record(
    tmp_path: Path, record: dict
) -> None:
    _, result_file = write_result_run(tmp_path, log_records=[record])

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "$.log[0]" in result.stderr


def test_result_file_rejects_oversized_audit_record(tmp_path: Path) -> None:
    record = {
        "ts": "2026-09-04T00:00:00Z",
        "agent": "build:writer:r1",
        "action": "x" * 4096,
        "artefacts": [],
    }
    _, result_file = write_result_run(tmp_path, log_records=[record])

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "below 4 KiB" in result.stderr


def completion_payload(**overrides: object) -> dict:
    value = {"missing_residual": []}
    value.update(overrides)
    return value


def test_completion_accepts_empty_residual_list() -> None:
    result = validate("completion.schema.json", completion_payload())

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "residual",
    [
        {"kind": "coverage_gap", "detail": "missing", "source": "sweep"},
        {"kind": "gap", "detail": "missing"},
        {"kind": "gap", "detail": " ", "source": "sweep"},
        {"kind": "finding", "detail": "missing", "source": "sweep"},
    ],
)
def test_completion_rejects_non_appendable_residual(residual: dict) -> None:
    result = validate(
        "completion.schema.json", completion_payload(missing_residual=[residual])
    )

    assert result.returncode == 1


@pytest.mark.parametrize(
    "residual",
    [
        {
            "kind": "finding",
            "detail": "required behavior remains broken",
            "severity": "important",
            "scope": "spec",
            "source": "completion sweep",
        },
        {"kind": "gap", "detail": "missing proof", "source": "completion sweep"},
        {
            "kind": "worker_failed",
            "detail": "worker failed",
            "source": "completion sweep",
        },
        {
            "kind": "loop_cap",
            "detail": "review remains open",
            "severity": "minor",
            "scope": "spec",
            "source": "completion sweep",
        },
        {
            "kind": "invalid_return",
            "detail": "return was invalid",
            "source": "completion sweep",
        },
        {
            "kind": "skipped",
            "detail": "requirement was skipped",
            "source": "completion sweep",
        },
    ],
)
def test_completion_residual_is_appendable_to_result(residual: dict) -> None:
    completion = validate(
        "completion.schema.json", completion_payload(missing_residual=[residual])
    )
    final_result = validate(
        "result.schema.json",
        result_payload(outcome="partial", residual=[residual]),
    )

    assert completion.returncode == 0, completion.stderr
    assert final_result.returncode == 0, final_result.stderr


def valid_sweep_result_payload(
    *, outcome: str = "complete", attempt: str = "r1"
) -> dict:
    workers = [
        {"id": "writer:r1", "role": "writer", "status": "ok"},
        {
            "id": f"_completion:sweep:{attempt}",
            "role": "completion-auditor",
            "status": "ok",
        },
    ]
    return result_payload(
        outcome=outcome,
        workers=workers,
        sweep=".work-team/run-1/completion-sweep.json",
    )


def valid_sweep_log(
    *, attempt: str = "r1", return_artefacts: list[str] | None = None
) -> list[dict]:
    return [
        {
            "ts": "2026-09-04T00:00:00Z",
            "agent": "build:writer:r1",
            "action": "return",
            "artefacts": ["artefact.txt"],
        },
        {
            "ts": "2026-09-04T00:00:01Z",
            "agent": f"_completion:sweep:{attempt}",
            "action": "completion_sweep_start",
            "artefacts": [],
        },
        {
            "ts": "2026-09-04T00:00:02Z",
            "agent": f"_completion:sweep:{attempt}",
            "action": "completion_sweep_return",
            "artefacts": return_artefacts
            if return_artefacts is not None
            else [".work-team/run-1/completion-sweep.json"],
        },
    ]


def write_sweep_artifact(run_dir: Path, payload: dict | None = None) -> None:
    (run_dir / "completion-sweep.json").write_text(
        json.dumps(payload or completion_payload())
    )


def test_complete_result_file_requires_completion_sweep(tmp_path: Path) -> None:
    _, result_file = write_result_run(tmp_path)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "$.sweep:" in result.stderr


@pytest.mark.parametrize("attempt", ["r1", "r2"])
def test_complete_result_file_accepts_accountable_completion_sweep(
    tmp_path: Path, attempt: str,
) -> None:
    run_dir, result_file = write_result_run(
        tmp_path,
        payload=valid_sweep_result_payload(attempt=attempt),
        log_records=valid_sweep_log(attempt=attempt),
    )
    write_sweep_artifact(run_dir)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("log_records", "message"),
    [
        (
            valid_sweep_log()[1:],
            "complete run requires a plan-derived worker attempt",
        ),
        ([valid_sweep_log()[0], valid_sweep_log()[2]], "accountable completion auditor"),
        (
            [valid_sweep_log()[0], valid_sweep_log()[2], valid_sweep_log()[1]],
            "accountable completion auditor",
        ),
        (
            valid_sweep_log(return_artefacts=["wrong.json"]),
            "accountable completion auditor",
        ),
    ],
)
def test_result_file_rejects_unaccountable_completion_sweep(
    tmp_path: Path, log_records: list[dict], message: str
) -> None:
    run_dir, result_file = write_result_run(
        tmp_path,
        payload=valid_sweep_result_payload(),
        log_records=log_records,
    )
    write_sweep_artifact(run_dir)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert message in result.stderr


@pytest.mark.parametrize("raw_sweep", [None, "{not-json}"])
def test_result_file_rejects_missing_or_malformed_sweep_artifact(
    tmp_path: Path, raw_sweep: str | None
) -> None:
    run_dir, result_file = write_result_run(
        tmp_path,
        payload=valid_sweep_result_payload(),
        log_records=valid_sweep_log(),
    )
    if raw_sweep is not None:
        (run_dir / "completion-sweep.json").write_text(raw_sweep)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "$.sweep:" in result.stderr


def test_partial_result_with_sweep_requires_completion_worker_row(
    tmp_path: Path,
) -> None:
    payload = valid_sweep_result_payload(outcome="partial")
    payload["workers"] = payload["workers"][:-1]
    run_dir, result_file = write_result_run(
        tmp_path, payload=payload, log_records=valid_sweep_log()
    )
    write_sweep_artifact(run_dir)

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "accountable completion auditor" in result.stderr


def test_partial_result_without_sweep_remains_valid(tmp_path: Path) -> None:
    _, result_file = write_result_run(
        tmp_path,
        payload=result_payload(outcome="partial", verification=[], workers=[]),
    )

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 0, result.stderr


def test_partial_result_retains_accountable_sweep(tmp_path: Path) -> None:
    residual = {
        "kind": "gap",
        "detail": "Requirement was not verified.",
        "source": "completion sweep",
    }
    payload = valid_sweep_result_payload(outcome="partial")
    payload["residual"] = [residual]
    run_dir, result_file = write_result_run(
        tmp_path, payload=payload, log_records=valid_sweep_log()
    )
    write_sweep_artifact(
        run_dir, completion_payload(missing_residual=[residual])
    )

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 0, result.stderr


def test_result_file_rejects_sweep_residual_omitted_from_result(
    tmp_path: Path,
) -> None:
    missing = {
        "kind": "finding",
        "detail": "A required behavior is still missing.",
        "severity": "important",
        "scope": "spec",
        "source": "completion sweep",
    }
    run_dir, result_file = write_result_run(
        tmp_path,
        payload=valid_sweep_result_payload(),
        log_records=valid_sweep_log(),
    )
    write_sweep_artifact(
        run_dir, completion_payload(missing_residual=[missing])
    )

    result = validate_result_file(tmp_path, result_file)

    assert result.returncode == 1
    assert "missing_residual is absent from result.residual" in result.stderr


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


def test_verifier_return_requires_exact_assigned_candidate_set(tmp_path: Path) -> None:
    value = plan(worker(id="finder", role="reviewer", owns=[]))
    value["phases"].append(
        {
            "id": "verify",
            "workers": [
                worker(
                    id="verifier",
                    role="verifier",
                    owns=[],
                    inputs=["review.json"],
                    candidates=[
                        {"id": "F1", "owner": "finder", "path": "one.py"},
                        {"id": "F2", "owner": "finder", "path": "two.py"},
                    ],
                )
            ],
        }
    )
    value["phases"][0]["workers"][0].pop("verify")
    value["phases"][1]["workers"][0].pop("verify")
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(value))
    verifier_file = tmp_path / "verifier.json"
    verifier_file.write_text(
        json.dumps(
            {
                "candidates": [
                    {"id": "F1", "verdict": "confirmed", "evidence": "one.py:1"}
                ]
            }
        )
    )

    result = subprocess.run(
        [
            str(VALIDATE),
            str(SCHEMAS / "verifier.schema.json"),
            str(verifier_file),
            "--plan",
            str(plan_file),
            "--phase",
            "verify",
            "--worker",
            "verifier",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "returned candidate ids do not exactly match" in result.stderr


def test_verifier_return_accepts_exact_assigned_candidate_set(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(
        json.dumps(
            {
                "run": "run-1",
                "task": "audit",
                "phases": [
                    {
                        "id": "verify",
                        "workers": [
                            {
                                "id": "verifier",
                                "role": "verifier",
                                "goal": "Verify candidates. Done when all are decided.",
                                "inputs": ["review.json"],
                                "owns": [],
                                "candidates": [
                                    {"id": "F1", "owner": "finder", "path": "one.py"},
                                    {"id": "F2", "owner": "finder", "path": "two.py"},
                                ],
                            }
                        ],
                    }
                ],
            }
        )
    )
    verifier_file = tmp_path / "verifier.json"
    verifier_file.write_text(
        json.dumps(
            {
                "candidates": [
                    {"id": "F2", "verdict": "refuted", "evidence": "two.py:2"},
                    {"id": "F1", "verdict": "confirmed", "evidence": "one.py:1"},
                ]
            }
        )
    )

    result = subprocess.run(
        [
            str(VALIDATE), str(SCHEMAS / "verifier.schema.json"), str(verifier_file),
            "--plan", str(plan_file), "--phase", "verify", "--worker", "verifier",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr


def test_eval_fault_injector_drops_exactly_last_verifier_candidate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "verifier.json"
    destination = tmp_path / "verifier-partial.json"
    source.write_text(
        json.dumps(
            {
                "candidates": [
                    {"id": "F1", "verdict": "confirmed", "evidence": "one.py:1"},
                    {"id": "F2", "verdict": "refuted", "evidence": "two.py:2"},
                ]
            }
        )
    )

    result = subprocess.run(
        ["python3", str(INJECT_PARTIAL_VERIFIER), str(source), str(destination)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(destination.read_text()) == {
        "candidates": [
            {"id": "F1", "verdict": "confirmed", "evidence": "one.py:1"}
        ]
    }


def test_eval_fault_injector_rejects_single_candidate_input(tmp_path: Path) -> None:
    source = tmp_path / "verifier.json"
    source.write_text(
        json.dumps(
            {
                "candidates": [
                    {"id": "F1", "verdict": "confirmed", "evidence": "one.py:1"}
                ]
            }
        )
    )

    result = subprocess.run(
        [
            "python3",
            str(INJECT_PARTIAL_VERIFIER),
            str(source),
            str(tmp_path / "partial.json"),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "at least two candidates" in result.stderr


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
    timeout_seconds: int | None = None,
    script_suffix: str = "",
    codex_home: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    codex = fake_bin / "codex"
    codex.write_text(
        (script
        or (
            "#!/usr/bin/env bash\n"
            "mkdir -p .work-team/test-run\n"
            "printf '%s\\n' '{\"run\":\"test-run\",\"task\":\"test\",\"phases\":[{\"id\":\"build\",\"workers\":[{\"id\":\"writer\",\"role\":\"writer\",\"goal\":\"Write. Done when checked.\",\"inputs\":[],\"owns\":[\"artefact.txt\"],\"verify\":\"true\"}]}]}' > .work-team/test-run/plan.json\n"
            "printf '%s\\n' '{\"ts\":\"2026-09-02T00:00:00Z\",\"agent\":\"build:writer:r1\",\"action\":\"return\",\"artefacts\":[]}' > .work-team/test-run/workflow-log.jsonl\n"
            "printf '%s\\n' '{\"run\":\"test-run\",\"outcome\":\"partial\",\"verification\":[],\"residual\":[{\"kind\":\"gap\",\"detail\":\"test harness\"}],\"workers\":[],\"plan\":\".work-team/test-run/plan.json\",\"log\":\".work-team/test-run/workflow-log.jsonl\"}' > .work-team/test-run/result.json\n"
            "marker=$(tail -n 1 .agents/skills/work-team/SKILL.md)\n"
            "printf '%s\\n' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"thread-child\"]}}' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"receiver_thread_ids\":[\"thread-child\"],\"agents_states\":{\"thread-child\":{\"completed\":\"{}\"}}}}' "
            "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"command_execution\\\",\\\"command\\\":\\\"sed -n 240p $PWD/.agents/skills/work-team/SKILL.md\\\",\\\"aggregated_output\\\":\\\"$marker\\\",\\\"exit_code\\\":0,\\\"status\\\":\\\"completed\\\"}}\" "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"progress\"}}' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\\ncomplete\"}}'\n"
        )) + script_suffix
    )
    codex.chmod(0o755)
    env = os.environ | {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "EVAL_TS": timestamp,
        "EVAL_WS": str(workspace or tmp_path / "workspace"),
    }
    if timeout_seconds is not None:
        env["EVAL_TIMEOUT_SECONDS"] = str(timeout_seconds)
    if codex_home is not None:
        env["CODEX_HOME"] = str(codex_home)
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


def test_eval_runner_uses_authoritative_codex_rollout_when_public_stream_omits_spawn(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-hidden-codex-spawn"
    output = eval_output(timestamp)
    root_id = "01a063cd-afbf-78b1-b7a5-88cbcea33d24"
    child_id = "01a063cd-bd9b-7f20-9784-62cdbc0f3481"
    script = (
        f"#!{sys.executable}\n"
        "import json\n"
        "import os\n"
        "from pathlib import Path\n"
        f"root_id = {root_id!r}\n"
        f"child_id = {child_id!r}\n"
        "run = Path.cwd() / '.work-team/test-run'\n"
        "run.mkdir(parents=True)\n"
        "(run / 'plan.json').write_text(json.dumps({'run': 'test-run', 'task': 'test', 'phases': [{'id': 'build', 'workers': [{'id': 'writer', 'role': 'writer', 'goal': 'Write. Done when checked.', 'inputs': [], 'owns': ['artefact.txt'], 'verify': 'true'}]}]}))\n"
        "(run / 'workflow-log.jsonl').write_text(json.dumps({'ts': '2026-09-02T00:00:00Z', 'agent': 'build:writer:r1', 'action': 'return', 'artefacts': []}) + '\\n')\n"
        "(run / 'result.json').write_text(json.dumps({'run': 'test-run', 'outcome': 'partial', 'verification': [], 'residual': [{'kind': 'gap', 'detail': 'test harness'}], 'workers': [], 'plan': '.work-team/test-run/plan.json', 'log': '.work-team/test-run/workflow-log.jsonl'}))\n"
        "skill = Path.cwd() / '.agents/skills/work-team/SKILL.md'\n"
        "marker = skill.read_text().splitlines()[-1]\n"
        "rollout = Path(os.environ['CODEX_HOME']) / 'sessions/2026/09/03' / ('rollout-test-' + root_id + '.jsonl')\n"
        "rollout.parent.mkdir(parents=True)\n"
        "rollout_events = [\n"
        " {'ordinal': 0, 'type': 'session_meta', 'payload': {'session_id': root_id, 'id': root_id, 'cwd': str(Path.cwd())}},\n"
        " {'ordinal': 1, 'type': 'response_item', 'payload': {'type': 'function_call', 'namespace': 'collaboration', 'name': 'spawn_agent', 'call_id': 'call-1'}},\n"
        " {'ordinal': 2, 'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': 'SubAgentActivity', 'id': 'call-1', 'kind': 'started', 'agent_thread_id': child_id, 'agent_path': '/root/finder'}}},\n"
        " {'ordinal': 3, 'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': 'SubAgentActivity', 'kind': 'completed', 'agent_thread_id': child_id, 'agent_path': '/root/finder'}}},\n"
        " {'ordinal': 4, 'type': 'response_item', 'payload': {'type': 'agent_message', 'author': '/root/finder', 'recipient': '/root', 'content': [{'type': 'input_text', 'text': 'worker result'}]}},\n"
        " {'ordinal': 5, 'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': 'AgentMessage', 'phase': 'final_answer', 'content': [{'type': 'Text', 'text': 'final'}]}}},\n"
        "]\n"
        "rollout.write_text(''.join(json.dumps(event) + '\\n' for event in rollout_events))\n"
        "events = [\n"
        " {'type': 'thread.started', 'thread_id': root_id},\n"
        " {'type': 'item.completed', 'item': {'type': 'collab_tool_call', 'tool': 'wait', 'receiver_thread_ids': []}},\n"
        " {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'sed -n 240p ' + str(skill), 'aggregated_output': marker, 'exit_code': 0}},\n"
        " {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'final'}},\n"
        "]\n"
        "for event in events:\n"
        " print(json.dumps(event))\n"
    )
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=script,
            codex_home=tmp_path / "codex-home",
        )

        assert result.returncode == 0, result.stderr
        evidence = json.loads((output / "codex-collaboration.json").read_text())
        assert evidence["root_thread_id"] == root_id
        assert [worker["thread_id"] for worker in evidence["workers"]] == [child_id]
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_malformed_authoritative_codex_rollout(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-malformed-codex-rollout"
    output = eval_output(timestamp)
    root_id = "root-1"
    script = (
        f"#!{sys.executable}\n"
        "import json\n"
        "import os\n"
        "from pathlib import Path\n"
        "run = Path.cwd() / '.work-team/test-run'\n"
        "run.mkdir(parents=True)\n"
        "(run / 'plan.json').write_text(json.dumps({'run': 'test-run', 'task': 'test', 'phases': [{'id': 'build', 'workers': [{'id': 'writer', 'role': 'writer', 'goal': 'Write. Done when checked.', 'inputs': [], 'owns': ['artefact.txt'], 'verify': 'true'}]}]}))\n"
        "(run / 'workflow-log.jsonl').write_text(json.dumps({'ts': '2026-09-02T00:00:00Z', 'agent': 'build:writer:r1', 'action': 'return', 'artefacts': []}) + '\\n')\n"
        "(run / 'result.json').write_text(json.dumps({'run': 'test-run', 'outcome': 'partial', 'verification': [], 'residual': [{'kind': 'gap', 'detail': 'test harness'}], 'workers': [], 'plan': '.work-team/test-run/plan.json', 'log': '.work-team/test-run/workflow-log.jsonl'}))\n"
        "skill = Path.cwd() / '.agents/skills/work-team/SKILL.md'\n"
        "marker = skill.read_text().splitlines()[-1]\n"
        f"root_id = {root_id!r}\n"
        "rollout = Path(os.environ['CODEX_HOME']) / 'sessions' / ('rollout-' + root_id + '.jsonl')\n"
        "rollout.parent.mkdir(parents=True)\n"
        "rollout.write_text('{')\n"
        "events = [\n"
        " {'type': 'thread.started', 'thread_id': root_id},\n"
        " {'type': 'item.completed', 'item': {'type': 'collab_tool_call', 'tool': 'spawn_agent', 'status': 'completed', 'receiver_thread_ids': ['child-1']}},\n"
        " {'type': 'item.completed', 'item': {'type': 'collab_tool_call', 'tool': 'wait', 'status': 'completed', 'receiver_thread_ids': ['child-1'], 'agents_states': {'child-1': {'completed': '{}'}}}},\n"
        " {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'sed -n 240p ' + str(skill), 'aggregated_output': marker, 'exit_code': 0}},\n"
        " {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'final'}},\n"
        "]\n"
        "for event in events:\n"
        " print(json.dumps(event))\n"
    )
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=script,
            codex_home=tmp_path / "codex-home",
        )

        assert result.returncode == 3
        assert "malformed Codex root rollout" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_allows_scenario_c_without_dispatch_in_matching_rollout(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-direct-codex-rollout"
    output = eval_output(timestamp, scenario="C")
    root_id = "root-1"
    script = (
        f"#!{sys.executable}\n"
        "import json\n"
        "import os\n"
        "from pathlib import Path\n"
        "skill = Path.cwd() / '.agents/skills/work-team/SKILL.md'\n"
        "marker = skill.read_text().splitlines()[-1]\n"
        f"root_id = {root_id!r}\n"
        "rollout = Path(os.environ['CODEX_HOME']) / 'sessions' / ('rollout-' + root_id + '.jsonl')\n"
        "rollout.parent.mkdir(parents=True)\n"
        "rollout_events = [\n"
        " {'ordinal': 0, 'type': 'session_meta', 'payload': {'session_id': root_id, 'id': root_id, 'cwd': str(Path.cwd())}},\n"
        " {'ordinal': 1, 'type': 'event_msg', 'payload': {'item': {'type': 'AgentMessage', 'phase': 'final_answer', 'content': [{'type': 'Text', 'text': 'final'}]}}},\n"
        "]\n"
        "rollout.write_text(''.join(json.dumps(event) + '\\n' for event in rollout_events))\n"
        "events = [\n"
        " {'type': 'thread.started', 'thread_id': root_id},\n"
        " {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'sed -n 240p ' + str(skill), 'aggregated_output': marker, 'exit_code': 0}},\n"
        " {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'final'}},\n"
        "]\n"
        "for event in events:\n"
        " print(json.dumps(event))\n"
    )
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            scenario="C",
            script=script,
            codex_home=tmp_path / "codex-home",
        )

        assert result.returncode == 0, result.stderr
        evidence = json.loads((output / "codex-collaboration.json").read_text())
        assert evidence["workers"] == []
        assert (output / "final-response.md").read_text() == "final\n"
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
        assert str(fixture.parent / ".eval-tools" / "inject-partial-verifier.py") in (
            output / "prompt.txt"
        ).read_text()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_canonicalizes_symlinked_workspace_base(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-workspace-symlink"
    output = eval_output(timestamp)
    real_workspace = tmp_path / "real-workspace"
    real_workspace.mkdir()
    linked_workspace = tmp_path / "linked-workspace"
    linked_workspace.symlink_to(real_workspace, target_is_directory=True)
    try:
        result = run_codex_eval(
            tmp_path, timestamp, workspace=linked_workspace
        )

        assert result.returncode == 0, result.stderr
        assert f"workspace={real_workspace.resolve()}" in (
            output / "metadata.txt"
        ).read_text()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_unsafe_timestamp_component(tmp_path: Path) -> None:
    timestamp = "unsafe/nested"

    result = run_codex_eval(tmp_path, timestamp)

    assert result.returncode != 0
    assert "timestamp" in result.stderr
    shutil.rmtree(COMPONENT / "evals" / "transcripts" / "refactor" / "unsafe", ignore_errors=True)


def test_eval_runner_stages_filtered_project_local_skill(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-staged-skill"
    output = eval_output(timestamp)
    workspace_base = tmp_path / "workspace"
    workspace = workspace_base / f"refactor-{timestamp}-A-codex-attempt-1"
    try:
        result = run_codex_eval(tmp_path, timestamp, workspace=workspace_base)

        assert result.returncode == 0, result.stderr
        for discovery in (".agents", ".claude"):
            installed = workspace / discovery / "skills" / "work-team"
            assert (installed / "SKILL.md").is_file()
            assert not (installed / "evals").exists()
        agents_hashes = (output / "skill-payload-agents.sha256").read_text()
        claude_hashes = (output / "skill-payload-claude.sha256").read_text()
        assert agents_hashes == claude_hashes
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_records_fixture_before_and_after_hashes(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-fixture-hashes"
    output = eval_output(timestamp, scenario="B")
    try:
        result = run_codex_eval(tmp_path, timestamp, scenario="B")

        assert result.returncode == 0, result.stderr
        before = (output / "fixture-before.sha256").read_text()
        after = (output / "fixture-after.sha256").read_text()
        assert before
        assert before == after
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_protected_fixture_mutation(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-fixture-mutation"
    output = eval_output(timestamp, scenario="B")
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            scenario="B",
            script_suffix="printf '\\nmutation\\n' >> audit-target/inventory/stock.py\n",
        )

        assert result.returncode == 7
        assert "modified protected fixture" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_invalid_generated_result(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-invalid-result"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script_suffix=(
                "python3 -c 'import json; p=\".work-team/test-run/result.json\"; "
                "d=json.load(open(p)); d[\"log\"]=\"outside.jsonl\"; "
                "open(p,\"w\").write(json.dumps(d))'\n"
            ),
        )

        assert result.returncode == 6
        assert "run artifacts failed validation" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_hashes_all_archived_scoring_inputs(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-all-hashes"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(tmp_path, timestamp)

        assert result.returncode == 0, result.stderr
        manifest = (output / "attempt.sha256").read_text()
        for name in (
            "final-response.md",
            "metadata.txt",
            "prompt.txt",
            "stderr.txt",
            "stdout.jsonl",
            "workspace-files.txt",
        ):
            assert f"  {name}\n" in manifest
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_symlinked_run_directory(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-run-symlink"
    output = eval_output(timestamp)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("do not archive")
    script = (
        "#!/usr/bin/env bash\n"
        f"ln -s '{outside}' .work-team\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "symlink" in result.stderr
        assert not (output / "run-artefacts" / "secret.txt").exists()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_control_characters_in_archive_paths(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-control-path"
    output = eval_output(timestamp)
    script = (
        "#!/usr/bin/env bash\n"
        "mkdir .work-team\n"
        "touch $'.work-team/bad\\n  attempt.sha256'\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"agent_message\\\",\\\"text\\\":\\\"loaded $PWD/.agents/skills/work-team/SKILL.md\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "control character" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_control_characters_in_workspace_inventory(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-workspace-control-path"
    output = eval_output(timestamp)
    script = (
        "#!/usr/bin/env bash\n"
        "touch $'bad\\nforged.txt'\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"command_execution\\\",\\\"command\\\":\\\"sed -n 240p $PWD/.agents/skills/work-team/SKILL.md\\\",\\\"aggregated_output\\\":\\\"name: work-team\\\\n# Work Team\\\\n\\\",\\\"exit_code\\\":0,\\\"status\\\":\\\"completed\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "control character" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_hardlinked_run_artifact(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-run-hardlink"
    output = eval_output(timestamp)
    outside = tmp_path / "outside.txt"
    outside.write_text("do not archive")
    script = (
        "#!/usr/bin/env bash\n"
        "mkdir .work-team\n"
        f"ln '{outside}' .work-team/leak.txt\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"command_execution\\\",\\\"command\\\":\\\"sed -n 1p $PWD/.agents/skills/work-team/SKILL.md\\\",\\\"exit_code\\\":0,\\\"status\\\":\\\"completed\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "hardlink" in result.stderr
        assert not (output / "run-artefacts" / "leak.txt").exists()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_preserves_distinct_audit_log_paths(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-audit-paths"
    output = eval_output(timestamp)
    script = (
        "#!/usr/bin/env bash\n"
        "mkdir -p a_b a/b\n"
        "printf one > a_b/workflow-log.jsonl\n"
        "printf two > a/b/workflow-log.jsonl\n"
        "mkdir -p .work-team/test-run\n"
        "printf '%s\\n' '{\"run\":\"test-run\",\"task\":\"test\",\"phases\":[{\"id\":\"build\",\"workers\":[{\"id\":\"writer\",\"role\":\"writer\",\"goal\":\"Write. Done when checked.\",\"inputs\":[],\"owns\":[\"artefact.txt\"],\"verify\":\"true\"}]}]}' > .work-team/test-run/plan.json\n"
        "printf '%s\\n' '{\"ts\":\"2026-09-02T00:00:00Z\",\"agent\":\"build:writer:r1\",\"action\":\"return\",\"artefacts\":[]}' > .work-team/test-run/workflow-log.jsonl\n"
        "printf '%s\\n' '{\"run\":\"test-run\",\"outcome\":\"partial\",\"verification\":[],\"residual\":[{\"kind\":\"gap\",\"detail\":\"test harness\"}],\"workers\":[],\"plan\":\".work-team/test-run/plan.json\",\"log\":\".work-team/test-run/workflow-log.jsonl\"}' > .work-team/test-run/result.json\n"
        "marker=$(tail -n 1 .agents/skills/work-team/SKILL.md)\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"command_execution\\\",\\\"command\\\":\\\"sed -n 240p $PWD/.agents/skills/work-team/SKILL.md\\\",\\\"aggregated_output\\\":\\\"$marker\\\",\\\"exit_code\\\":0,\\\"status\\\":\\\"completed\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode == 0, result.stderr
        assert (output / "audit-logs" / "a_b" / "workflow-log.jsonl").read_text() == "one"
        assert (output / "audit-logs" / "a" / "b" / "workflow-log.jsonl").read_text() == "two"
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_times_out_hung_harness(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-timeout"
    output = eval_output(timestamp)
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script="#!/usr/bin/env bash\nsleep 5\n",
            timeout_seconds=1,
        )

        assert result.returncode == 124
        assert "timed out" in (output / "stderr.txt").read_text()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_kills_timeout_descendants(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-timeout-child"
    output = eval_output(timestamp)
    child_pid_file = tmp_path / "child.pid"
    script = (
        "#!/usr/bin/env bash\n"
        f"(trap '' TERM; sleep 30) & echo $! > '{child_pid_file}'\n"
        "wait\n"
    )
    try:
        result = run_codex_eval(
            tmp_path, timestamp, script=script, timeout_seconds=1
        )

        assert result.returncode == 124
        child_pid = int(child_pid_file.read_text())
        for _ in range(20):
            if not Path(f"/proc/{child_pid}").exists():
                break
            time.sleep(0.05)
        assert not Path(f"/proc/{child_pid}").exists()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_kills_normal_exit_descendants_before_post_hash(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-normal-child"
    output = eval_output(timestamp)
    workspace_base = tmp_path / "workspace"
    workspace = workspace_base / f"refactor-{timestamp}-A-codex-attempt-1"
    script = (
        "#!/usr/bin/env bash\n"
        "mkdir -p .work-team/test-run\n"
        "printf '%s\\n' '{\"run\":\"test-run\",\"task\":\"test\",\"phases\":[{\"id\":\"build\",\"workers\":[{\"id\":\"writer\",\"role\":\"writer\",\"goal\":\"Write. Done when checked.\",\"inputs\":[],\"owns\":[\"artefact.txt\"],\"verify\":\"true\"}]}]}' > .work-team/test-run/plan.json\n"
        "printf '%s\\n' '{\"ts\":\"2026-09-02T00:00:00Z\",\"agent\":\"build:writer:r1\",\"action\":\"return\",\"artefacts\":[]}' > .work-team/test-run/workflow-log.jsonl\n"
        "printf '%s\\n' '{\"run\":\"test-run\",\"outcome\":\"partial\",\"verification\":[],\"residual\":[{\"kind\":\"gap\",\"detail\":\"test harness\"}],\"workers\":[],\"plan\":\".work-team/test-run/plan.json\",\"log\":\".work-team/test-run/workflow-log.jsonl\"}' > .work-team/test-run/result.json\n"
        "(trap '' TERM; sleep 1; printf '\\nlate mutation\\n' >> "
        ".agents/skills/work-team/SKILL.md) &\n"
        "marker=$(tail -n 1 .agents/skills/work-team/SKILL.md)\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"command_execution\\\",\\\"command\\\":\\\"sed -n 240p $PWD/.agents/skills/work-team/SKILL.md\\\",\\\"aggregated_output\\\":\\\"$marker\\\",\\\"exit_code\\\":0,\\\"status\\\":\\\"completed\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(
            tmp_path, timestamp, script=script, workspace=workspace_base
        )

        assert result.returncode == 0, result.stderr
        time.sleep(1.2)
        assert "late mutation" not in (
            workspace / ".agents" / "skills" / "work-team" / "SKILL.md"
        ).read_text()
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_success_without_staged_skill_evidence(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-wrong-skill"
    output = eval_output(timestamp)
    script = (
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "staged skill" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_agent_message_as_staged_skill_evidence(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-claimed-skill"
    output = eval_output(timestamp)
    script = (
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"agent_message\\\",\\\"text\\\":\\\"loaded $PWD/.agents/skills/work-team/SKILL.md\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "staged skill" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_eval_runner_rejects_codex_command_that_only_mentions_staged_skill(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-mentioned-skill"
    output = eval_output(timestamp)
    script = (
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"command_execution\\\",\\\"command\\\":\\\"printf 'name: work-team # Work Team' $PWD/.agents/skills/work-team/SKILL.md\\\",\\\"aggregated_output\\\":\\\"name: work-team # Work Team\\\",\\\"exit_code\\\":0,\\\"status\\\":\\\"completed\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "staged skill" in result.stderr
    finally:
        shutil.rmtree(output.parents[1], ignore_errors=True)


def test_claude_staged_skill_proof_matches_native_skill_events(tmp_path: Path) -> None:
    module = runpy.run_path(str(RUN_EVAL))
    workspace = tmp_path / "workspace"
    skill_dir = workspace / ".claude" / "skills" / "work-team"
    marker = "<!-- eval-marker:test -->"
    transcript = tmp_path / "stdout.jsonl"
    events = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Skill",
                        "input": {"skill": "work-team"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "isSynthetic": True,
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Base directory for this skill: {skill_dir}\\n{marker}"
                        ),
                    }
                ]
            },
        },
    ]
    transcript.write_text("".join(json.dumps(event) + "\n" for event in events))

    assert module["verify_staged_skill"](
        "claude", transcript, workspace, marker
    )


def test_codex_staged_skill_proof_accepts_workspace_relative_read(tmp_path: Path) -> None:
    module = runpy.run_path(str(RUN_EVAL))
    workspace = tmp_path / "workspace"
    transcript = tmp_path / "stdout.jsonl"
    marker = "<!-- eval-marker:test -->"
    transcript.write_text(
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "sed -n '1,240p' .agents/skills/work-team/SKILL.md",
                    "aggregated_output": marker,
                    "exit_code": 0,
                },
            }
        ) + "\n"
    )

    assert module["verify_staged_skill"]("codex", transcript, workspace, marker)


def test_codex_staged_skill_proof_accepts_shell_wrapped_relative_read(
    tmp_path: Path,
) -> None:
    module = runpy.run_path(str(RUN_EVAL))
    workspace = tmp_path / "workspace"
    transcript = tmp_path / "stdout.jsonl"
    marker = "<!-- eval-marker:test -->"
    transcript.write_text(
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": (
                        "/bin/bash -lc \"sed -n '1,260p' "
                        ".agents/skills/work-team/SKILL.md\""
                    ),
                    "aggregated_output": marker,
                    "exit_code": 0,
                },
            }
        ) + "\n"
    )

    assert module["verify_staged_skill"]("codex", transcript, workspace, marker)


def test_codex_staged_skill_proof_accepts_read_before_later_chained_failure(
    tmp_path: Path,
) -> None:
    module = runpy.run_path(str(RUN_EVAL))
    workspace = tmp_path / "workspace"
    transcript = tmp_path / "stdout.jsonl"
    marker = "<!-- eval-marker:test -->"
    transcript.write_text(
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": (
                        "/bin/bash -lc \"sed -n '1,260p' "
                        ".agents/skills/work-team/SKILL.md && rg missing .\""
                    ),
                    "aggregated_output": marker,
                    "exit_code": 1,
                },
            }
        ) + "\n"
    )

    assert module["verify_staged_skill"]("codex", transcript, workspace, marker)


def test_eval_runner_uses_requested_high_effort_for_both_harnesses(tmp_path: Path) -> None:
    module = runpy.run_path(str(RUN_EVAL))

    claude_display, claude_command = module["harness_command"](
        "claude", tmp_path, "prompt"
    )
    codex_display, codex_command = module["harness_command"](
        "codex", tmp_path, "prompt"
    )

    assert "--model sonnet --effort high" in claude_display
    assert claude_command[claude_command.index("--model"):claude_command.index("--model") + 4] == [
        "--model", "sonnet", "--effort", "high"
    ]
    assert 'model_reasoning_effort="high"' in codex_display
    assert 'model_reasoning_effort="high"' in codex_command


def test_eval_runner_codex_display_matches_prompt_argument_transport(tmp_path: Path) -> None:
    module = runpy.run_path(str(RUN_EVAL))

    display, command = module["harness_command"]("codex", tmp_path, "prompt")

    assert display.endswith("<prompt-argument>")
    assert "</dev/null" not in display
    assert command[-1] == "prompt"


def test_eval_runner_rejects_mutated_staged_skill(tmp_path: Path) -> None:
    timestamp = f"pytest-{os.getpid()}-mutated-skill"
    output = eval_output(timestamp)
    script = (
        "#!/usr/bin/env bash\n"
        "printf '\\nmutation\\n' >> .agents/skills/work-team/SKILL.md\n"
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"spawn_agent\",\"status\":\"completed\",\"receiver_thread_ids\":[\"worker-1\"]}}' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"collab_tool_call\",\"tool\":\"wait\",\"status\":\"completed\",\"agents_states\":{\"worker-1\":{\"completed\":\"{}\"}}}}' "
        "\"{\\\"type\\\":\\\"item.completed\\\",\\\"item\\\":{\\\"type\\\":\\\"command_execution\\\",\\\"command\\\":\\\"sed -n 1p $PWD/.agents/skills/work-team/SKILL.md\\\",\\\"exit_code\\\":0,\\\"status\\\":\\\"completed\\\"}}\" "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"final\"}}'\n"
    )
    try:
        result = run_codex_eval(tmp_path, timestamp, script=script)

        assert result.returncode != 0
        assert "staged skill changed" in result.stderr
        assert (output / "skill-payload-agents-after.sha256").is_file()
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


def test_eval_runner_accepts_direct_diagnosis_without_worker_dispatch(
    tmp_path: Path,
) -> None:
    timestamp = f"pytest-{os.getpid()}-diagnosis-no-dispatch"
    output = eval_output(timestamp, scenario="C")
    script = (
        "#!/usr/bin/env bash\n"
        "marker=$(tail -n 1 .agents/skills/work-team/SKILL.md)\n"
        "printf '%s\\n' "
        '"{\\"type\\":\\"item.completed\\",\\"item\\":{\\"type\\":\\"command_execution\\",\\"command\\":\\"sed -n 240p $PWD/.agents/skills/work-team/SKILL.md\\",\\"aggregated_output\\":\\"$marker\\",\\"exit_code\\":0,\\"status\\":\\"completed\\"}}" '
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"diagnosis complete\"}}'\n"
    )
    try:
        result = run_codex_eval(
            tmp_path,
            timestamp,
            script=script,
            scenario="C",
        )

        assert result.returncode == 0, result.stderr
        assert (output / "final-response.md").read_text() == "diagnosis complete\n"
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
        "import os\n"
        "from pathlib import Path\n"
        "run = Path.cwd() / '.work-team/test-run'\n"
        "run.mkdir(parents=True)\n"
        "(run / 'plan.json').write_text(json.dumps({'run': 'test-run', 'task': 'test', 'phases': [{'id': 'build', 'workers': [{'id': 'writer', 'role': 'writer', 'goal': 'Write. Done when checked.', 'inputs': [], 'owns': ['artefact.txt'], 'verify': 'true'}]}]}))\n"
        "(run / 'workflow-log.jsonl').write_text(json.dumps({'ts': '2026-09-02T00:00:00Z', 'agent': 'build:writer:r1', 'action': 'return', 'artefacts': []}) + '\\n')\n"
        "(run / 'result.json').write_text(json.dumps({'run': 'test-run', 'outcome': 'partial', 'verification': [], 'residual': [{'kind': 'gap', 'detail': 'test harness'}], 'workers': [], 'plan': '.work-team/test-run/plan.json', 'log': '.work-team/test-run/workflow-log.jsonl'}))\n"
        "skill = Path.cwd() / '.agents/skills/work-team/SKILL.md'\n"
        "marker = skill.read_text().splitlines()[-1]\n"
        "events = [\n"
        "    {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'sed -n 240p ' + str(skill), 'aggregated_output': marker, 'exit_code': 0, 'status': 'completed'}},\n"
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
    tmp_path: Path,
    harness: str,
    events: list[dict],
    evidence: Path | None = None,
    *,
    allow_no_dispatch: bool = False,
) -> subprocess.CompletedProcess[str]:
    transcript = tmp_path / f"{harness}.jsonl"
    transcript.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    command = ["python3", str(EXTRACT_RESPONSE), harness, str(transcript)]
    if evidence is not None:
        command.append(str(evidence))
    if allow_no_dispatch:
        command.append("--allow-no-dispatch")
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
    )


def test_codex_rollout_evidence_recovers_hidden_completed_dispatch(
    tmp_path: Path,
) -> None:
    root_id = "01a063cd-afbf-78b1-b7a5-88cbcea33d24"
    child_id = "01a063cd-bd9b-7f20-9784-62cdbc0f3481"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        "\n".join(
            json.dumps(event)
            for event in [
                {"type": "thread.started", "thread_id": root_id},
                {
                    "type": "item.completed",
                    "item": {"type": "collab_tool_call", "tool": "wait", "receiver_thread_ids": []},
                },
                {"type": "item.completed", "item": {"type": "agent_message", "text": "final"}},
            ]
        )
        + "\n"
    )
    sessions = tmp_path / "sessions" / "2026" / "09" / "03"
    sessions.mkdir(parents=True)
    rollout = sessions / f"rollout-test-{root_id}.jsonl"
    rollout.write_text(
        "\n".join(
            json.dumps(event)
            for event in [
                {
                    "ordinal": 0,
                    "type": "session_meta",
                    "payload": {"session_id": root_id, "id": root_id, "cwd": str(workspace)},
                },
                {
                    "ordinal": 1,
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "namespace": "collaboration",
                        "name": "spawn_agent",
                        "call_id": "call-1",
                    },
                },
                {
                    "ordinal": 2,
                    "type": "event_msg",
                    "payload": {
                        "type": "item_completed",
                        "item": {
                            "type": "SubAgentActivity",
                            "id": "call-1",
                            "kind": "started",
                            "agent_thread_id": child_id,
                            "agent_path": "/root/finder",
                        },
                    },
                },
                {
                    "ordinal": 3,
                    "type": "event_msg",
                    "payload": {
                        "type": "item_completed",
                        "item": {
                            "type": "SubAgentActivity",
                            "kind": "completed",
                            "agent_thread_id": child_id,
                            "agent_path": "/root/finder",
                        },
                    },
                },
                {
                    "ordinal": 4,
                    "type": "response_item",
                    "payload": {
                        "type": "agent_message",
                        "author": "/root/finder",
                        "recipient": "/root",
                        "content": [{"type": "input_text", "text": "worker result"}],
                    },
                },
                {
                    "ordinal": 5,
                    "type": "event_msg",
                    "payload": {
                        "type": "item_completed",
                        "item": {
                            "type": "AgentMessage",
                            "phase": "final_answer",
                            "content": [{"type": "Text", "text": "final"}],
                        },
                    },
                },
            ]
        )
        + "\n"
    )
    evidence = tmp_path / "codex-collaboration.json"

    collected = subprocess.run(
        [
            "python3",
            str(EXTRACT_CODEX_COLLABORATION),
            str(transcript),
            str(tmp_path / "sessions"),
            str(workspace),
            str(evidence),
        ],
        text=True,
        capture_output=True,
    )

    assert collected.returncode == 0, collected.stderr
    extracted = run_response_extractor(
        tmp_path,
        "codex",
        [
            {"type": "thread.started", "thread_id": root_id},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "final"}},
        ],
        evidence,
    )
    assert extracted.returncode == 0, extracted.stderr
    assert extracted.stdout == "final\n"


def test_codex_no_dispatch_mode_rejects_failed_spawn(tmp_path: Path) -> None:
    root_id = "root-1"
    evidence = tmp_path / "codex-collaboration.json"
    evidence.write_text(
        json.dumps(
            {
                "root_thread_id": root_id,
                "rollout_sha256": "unused-by-response-extractor",
                "terminal_response_sha256": hashlib.sha256(b"final").hexdigest(),
                "workers": [],
            }
        )
    )

    result = run_response_extractor(
        tmp_path,
        "codex",
        [
            {"type": "thread.started", "thread_id": root_id},
            {
                "type": "item.completed",
                "item": {
                    "type": "collab_tool_call",
                    "tool": "spawn_agent",
                    "status": "completed",
                    "receiver_thread_ids": [],
                },
            },
            {"type": "item.completed", "item": {"type": "agent_message", "text": "final"}},
        ],
        evidence,
        allow_no_dispatch=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""


def test_codex_rollout_evidence_rejects_multiple_public_roots(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        "".join(
            json.dumps({"type": "thread.started", "thread_id": root_id}) + "\n"
            for root_id in ("root-1", "root-2")
        )
    )

    result = subprocess.run(
        [
            "python3",
            str(EXTRACT_CODEX_COLLABORATION),
            str(transcript),
            str(tmp_path / "sessions"),
            str(workspace),
            str(tmp_path / "evidence.json"),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 3
    assert "multiple Codex root thread ids" in result.stderr


def test_codex_rollout_evidence_rejects_multiple_matching_rollouts(
    tmp_path: Path,
) -> None:
    root_id = "root-1"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        json.dumps({"type": "thread.started", "thread_id": root_id}) + "\n"
    )
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    for prefix in ("first", "second"):
        (sessions / f"{prefix}-{root_id}.jsonl").write_text("{}\n")

    result = subprocess.run(
        [
            "python3",
            str(EXTRACT_CODEX_COLLABORATION),
            str(transcript),
            str(sessions),
            str(workspace),
            str(tmp_path / "evidence.json"),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 3
    assert "multiple Codex root rollouts" in result.stderr


def test_codex_rollout_evidence_rejects_hidden_failed_spawn_among_workers(
    tmp_path: Path,
) -> None:
    root_id = "root-1"
    child_id = "child-1"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        json.dumps({"type": "thread.started", "thread_id": root_id}) + "\n"
    )
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    events = [
        {
            "ordinal": 0,
            "type": "session_meta",
            "payload": {"session_id": root_id, "id": root_id, "cwd": str(workspace)},
        },
        {
            "ordinal": 1,
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "call_id": "call-1",
            },
        },
        {
            "ordinal": 2,
            "type": "event_msg",
            "payload": {
                "item": {
                    "type": "SubAgentActivity",
                    "id": "call-1",
                    "kind": "started",
                    "agent_thread_id": child_id,
                    "agent_path": "/root/finder",
                }
            },
        },
        {
            "ordinal": 3,
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "call_id": "call-2",
            },
        },
        {
            "ordinal": 4,
            "type": "event_msg",
            "payload": {
                "item": {
                    "type": "SubAgentActivity",
                    "kind": "completed",
                    "agent_thread_id": child_id,
                    "agent_path": "/root/finder",
                }
            },
        },
        {
            "ordinal": 5,
            "type": "response_item",
            "payload": {
                "type": "agent_message",
                "author": "/root/finder",
                "recipient": "/root",
                "content": [{"type": "input_text", "text": "worker result"}],
            },
        },
        {
            "ordinal": 6,
            "type": "event_msg",
            "payload": {
                "item": {
                    "type": "AgentMessage",
                    "phase": "final_answer",
                    "content": [{"type": "Text", "text": "final"}],
                }
            },
        },
    ]
    (sessions / f"rollout-{root_id}.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )

    result = subprocess.run(
        [
            "python3",
            str(EXTRACT_CODEX_COLLABORATION),
            str(transcript),
            str(sessions),
            str(workspace),
            str(tmp_path / "evidence.json"),
            "--allow-no-dispatch",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "failed Codex worker dispatch" in result.stderr


def test_codex_rollout_evidence_rejects_worker_without_matching_spawn(
    tmp_path: Path,
) -> None:
    root_id = "root-1"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        json.dumps({"type": "thread.started", "thread_id": root_id}) + "\n"
    )
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    events = [
        {
            "ordinal": 0,
            "type": "session_meta",
            "payload": {"session_id": root_id, "id": root_id, "cwd": str(workspace)},
        },
        {
            "ordinal": 1,
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "call_id": "call-1",
            },
        },
    ]
    for offset, worker_id in enumerate(("child-1", "child-2"), start=2):
        events.extend(
            [
                {
                    "ordinal": offset,
                    "type": "event_msg",
                    "payload": {
                        "item": {
                            "type": "SubAgentActivity",
                            "id": f"call-{offset - 1}",
                            "kind": "started",
                            "agent_thread_id": worker_id,
                            "agent_path": f"/root/finder-{offset - 1}",
                        }
                    },
                },
                {
                    "ordinal": offset + 2,
                    "type": "event_msg",
                    "payload": {
                        "item": {
                            "type": "SubAgentActivity",
                            "kind": "completed",
                            "agent_thread_id": worker_id,
                            "agent_path": f"/root/finder-{offset - 1}",
                        }
                    },
                },
                {
                    "ordinal": offset + 4,
                    "type": "response_item",
                    "payload": {
                        "type": "agent_message",
                        "author": f"/root/finder-{offset - 1}",
                        "recipient": "/root",
                        "content": [{"type": "input_text", "text": "worker result"}],
                    },
                },
            ]
        )
    events.append(
        {
            "ordinal": 8,
            "type": "event_msg",
            "payload": {
                "item": {
                    "type": "AgentMessage",
                    "phase": "final_answer",
                    "content": [{"type": "Text", "text": "final"}],
                }
            },
        }
    )
    (sessions / f"rollout-{root_id}.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )

    result = subprocess.run(
        [
            "python3",
            str(EXTRACT_CODEX_COLLABORATION),
            str(transcript),
            str(sessions),
            str(workspace),
            str(tmp_path / "evidence.json"),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "unmatched Codex worker dispatch" in result.stderr


def test_codex_rollout_evidence_rejects_unmatched_public_response(tmp_path: Path) -> None:
    root_id = "root-1"
    evidence = tmp_path / "codex-collaboration.json"
    evidence.write_text(
        json.dumps(
            {
                "root_thread_id": root_id,
                "rollout_sha256": "unused-by-response-extractor",
                "terminal_response_sha256": (
                    "2443630b4620165c8b173e7265e17526fe2787ae594364dd6d839ad58f2fc007"
                ),
                "workers": [
                    {
                        "thread_id": "child-1",
                        "path": "/root/finder",
                        "started_ordinal": 1,
                        "completed_ordinal": 2,
                        "return_ordinal": 3,
                    }
                ],
            }
        )
    )

    result = run_response_extractor(
        tmp_path,
        "codex",
        [
            {"type": "thread.started", "thread_id": root_id},
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "progress"},
            },
        ],
        evidence,
    )

    assert result.returncode == 3
    assert result.stdout == ""


def test_codex_rollout_evidence_rejects_unfinished_worker(tmp_path: Path) -> None:
    root_id = "01a063cd-afbf-78b1-b7a5-88cbcea33d24"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(json.dumps({"type": "thread.started", "thread_id": root_id}) + "\n")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / f"rollout-test-{root_id}.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ordinal": 0,
                        "type": "session_meta",
                        "payload": {"session_id": root_id, "id": root_id, "cwd": str(workspace)},
                    }
                ),
                json.dumps(
                    {
                        "ordinal": 1,
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "namespace": "collaboration",
                            "name": "spawn_agent",
                            "call_id": "call-1",
                        },
                    }
                ),
                json.dumps(
                    {
                        "ordinal": 2,
                        "type": "event_msg",
                        "payload": {
                            "type": "item_completed",
                            "item": {
                                "type": "SubAgentActivity",
                                "id": "call-1",
                                "kind": "started",
                                "agent_thread_id": "child-1",
                                "agent_path": "/root/finder",
                            },
                        },
                    }
                ),
            ]
        )
        + "\n"
    )

    result = subprocess.run(
        [
            "python3",
            str(EXTRACT_CODEX_COLLABORATION),
            str(transcript),
            str(sessions),
            str(workspace),
            str(tmp_path / "evidence.json"),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "unfinished" in result.stderr


def test_codex_rollout_evidence_rejects_duplicate_worker_paths(tmp_path: Path) -> None:
    root_id = "root-1"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    transcript = tmp_path / "stdout.jsonl"
    transcript.write_text(
        json.dumps({"type": "thread.started", "thread_id": root_id}) + "\n"
    )
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    events = [
        {
            "ordinal": 0,
            "type": "session_meta",
            "payload": {"session_id": root_id, "id": root_id, "cwd": str(workspace)},
        },
    ]
    for offset, worker_id in enumerate(("child-1", "child-2"), start=1):
        events.extend(
            [
                {
                    "ordinal": offset,
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "namespace": "collaboration",
                        "name": "spawn_agent",
                        "call_id": f"call-{offset}",
                    },
                },
                {
                    "ordinal": offset + 2,
                    "type": "event_msg",
                    "payload": {
                        "item": {
                            "type": "SubAgentActivity",
                            "id": f"call-{offset}",
                            "kind": "started",
                            "agent_thread_id": worker_id,
                            "agent_path": "/root/reused",
                        }
                    },
                },
                {
                    "ordinal": offset + 4,
                    "type": "event_msg",
                    "payload": {
                        "item": {
                            "type": "SubAgentActivity",
                            "kind": "completed",
                            "agent_thread_id": worker_id,
                            "agent_path": "/root/reused",
                        }
                    },
                },
            ]
        )
    events.extend(
        [
            {
                "ordinal": 7,
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "author": "/root/reused",
                    "content": [{"type": "input_text", "text": "one return"}],
                },
            },
            {
                "ordinal": 8,
                "type": "event_msg",
                "payload": {"item": {"type": "AgentMessage", "phase": "final_answer"}},
            },
        ]
    )
    (sessions / f"rollout-test-{root_id}.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )

    result = subprocess.run(
        [
            "python3",
            str(EXTRACT_CODEX_COLLABORATION),
            str(transcript),
            str(sessions),
            str(workspace),
            str(tmp_path / "evidence.json"),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "duplicate Codex worker path" in result.stderr


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


def test_telemetry_rejects_csv_output_aliasing_input_log(tmp_path: Path) -> None:
    log = tmp_path / "workflow-log.jsonl"
    original = json.dumps(
        {
            "ts": "2026-09-01T00:00:00Z",
            "agent": "writer:r1",
            "action": "start",
            "artefacts": [],
        }
    ) + "\n"
    log.write_text(original)

    result = subprocess.run(
        [str(TELEMETRY), str(log), "--csv", str(log)],
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert log.read_text() == original


def test_telemetry_rejects_hard_link_alias_of_input_log(tmp_path: Path) -> None:
    log = tmp_path / "workflow-log.jsonl"
    original = '{"ts":"2026-09-01T00:00:00Z","agent":"writer:r1"}\n'
    log.write_text(original)
    alias = tmp_path / "alias.csv"
    os.link(log, alias)

    result = subprocess.run(
        [str(TELEMETRY), str(log), "--csv", str(alias)],
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert log.read_text() == original


def test_telemetry_rejects_symlink_loop_without_traceback(tmp_path: Path) -> None:
    loop = tmp_path / "cycle"
    loop.symlink_to("cycle")

    result = subprocess.run(
        [str(TELEMETRY), str(loop)], text=True, capture_output=True
    )

    assert result.returncode != 0
    assert "cannot resolve telemetry path" in result.stderr
    assert "Traceback" not in result.stderr


def test_telemetry_requires_csv_output_argument(tmp_path: Path) -> None:
    log = tmp_path / "workflow-log.jsonl"
    log.write_text("")

    result = subprocess.run(
        [str(TELEMETRY), str(log), "--csv"], text=True, capture_output=True
    )

    assert result.returncode != 0
    assert "usage:" in result.stderr
    assert "Traceback" not in result.stderr


def test_telemetry_reads_utf8_log_under_ascii_locale(tmp_path: Path) -> None:
    log = tmp_path / "workflow-log.jsonl"
    subprocess.run(
        [str(WT_LOG), str(log), "writer:r1", "wrote café"],
        check=True,
        text=True,
        capture_output=True,
    )
    env = os.environ | {
        "LC_ALL": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }

    result = subprocess.run(
        [str(TELEMETRY), str(log)], text=True, capture_output=True, env=env
    )

    assert result.returncode == 0, result.stderr
    assert "writer:r1" in result.stdout


def test_validator_decodes_utf8_stdin_independently_of_locale() -> None:
    payload = json.dumps(
        {
            "ok": True,
            "note": "café",
            "artefacts": [],
            "verify_output": "passed",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    env = os.environ | {
        "LC_ALL": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }

    result = subprocess.run(
        [str(VALIDATE), str(SCHEMAS / "status.schema.json")],
        input=payload,
        capture_output=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr.decode()
    assert json.loads(result.stdout.decode("utf-8"))["note"] == "café"


def test_plan_reports_nul_in_freeform_input_without_traceback() -> None:
    result = validate("plan.schema.json", plan(worker(inputs=["bad\x00input"])))

    assert result.returncode == 1
    assert "invalid path-like input" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        ("plan.schema.json", plan(worker(owns=["bad\x00path"]))),
        (
            "review.schema.json",
            {
                "verdict": "changes_required",
                "findings": [review_finding(path="bad\x00path")],
            },
        ),
        (
            "plan.schema.json",
            plan(
                worker(
                    role="verifier",
                    owns=[],
                    verify=None,
                    candidates=[
                        {
                            "id": "review:r1:F1",
                            "owner": "implementer",
                            "path": "bad\x00path",
                            "issue": "Required behavior is missing.",
                        }
                    ],
                )
            ),
        ),
    ],
)
def test_validator_reports_nul_in_schema_paths_without_traceback(
    schema: str, payload: dict,
) -> None:
    if payload.get("phases"):
        payload["phases"][0]["workers"][0].pop("verify", None)

    result = validate(schema, payload)

    assert result.returncode == 1
    assert "expected a path within the repository" in result.stderr
    assert "Traceback" not in result.stderr


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
