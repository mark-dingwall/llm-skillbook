"""Black-box tests for the current Feature Forge ledger audit."""
from __future__ import annotations

import hashlib
import json
import os
import copy
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import (
    CHECKER, check, git, head, make_primary_repo, make_repo, run_dir,
    write_ledger as write_ledger_fixture,
)


HEAD_KEYS = {
    "schema", "run_id", "mode", "status", "worktree", "branch", "base_identity",
    "stage", "next_action", "frozen", "review",
}
TASK_STATUSES = ("pending", "active", "awaiting_return", "blocked", "complete")


def task_markdown(*rows: tuple[str, str, str, str, str]) -> str:
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return (
        "\n## Implementation progress\n\n"
        "| plan task | status | commit | evidence | notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{body}\n"
    )


COMPLETE_TASK_MARKDOWN = task_markdown((
    "W-1", "complete", "abc123", "pytest: pass", "",
))


def write_ledger(
    directory: Path,
    data: object,
    *,
    fenced: bool = True,
    markdown: str | None = None,
) -> Path:
    """Give valid Stage 10+ fixtures completed task evidence by default."""
    if markdown is None:
        stage = data.get("stage") if isinstance(data, dict) else None
        stage_id = stage.get("id") if isinstance(stage, dict) else None
        markdown = (
            COMPLETE_TASK_MARKDOWN
            if isinstance(stage_id, int) and stage_id >= 10
            else task_markdown(("", "", "", "", ""))
        )
    return write_ledger_fixture(directory, data, fenced=fenced, markdown=markdown)

# Receipt and semantic-mapping contracts are exercised through the installed file.
def receipt_payload() -> dict[str, object]:
    return {
        "schema": "feature-forge/review-receipt/v1", "kind": "specification",
        "dispatch_id": "specification-2", "run_ref": "/external/run", "target_seal": "seal",
        "source_identity": {"kind": "candidate_sha256", "path": "candidate.md", "value": "a" * 64},
        "result": "pass", "actionable_finding_ids": [],
        "feature_forge_charter_id": "feature-forge/specification-review/v1",
        "completion_criterion": "No grounded discrepancies remain.",
        "raw_report_ids": ["empty-report", "report"], "triage_artifact_id": "triage-artifact",
        "triage_finding_ids": [], "stable_id_mapping": [],
    }


def test_strict_receipt_accepts_complete_evidence_and_rejects_old_shape(tmp_path: Path) -> None:
    api = runpy.run_path(str(CHECKER))
    payload = receipt_payload()
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload))
    assert api["strict_receipt"](path) == (payload, None)
    for key in ("feature_forge_charter_id", "completion_criterion", "raw_report_ids",
                "triage_artifact_id", "triage_finding_ids", "stable_id_mapping"):
        payload.pop(key)
    path.write_text(json.dumps(payload))
    assert api["strict_receipt"](path) == (None, "receipt=unsupported")


@pytest.mark.parametrize(("field", "value"), [
    ("feature_forge_charter_id", "feature-forge/plan-review/v1"),
    ("completion_criterion", ""), ("completion_criterion", " "),
    ("raw_report_ids", ["b", "a"]), ("raw_report_ids", ["a", "a"]),
    ("triage_finding_ids", ["b", "a"]), ("triage_finding_ids", ["a", "a"]),
    ("triage_artifact_id", ""), ("stable_id_mapping", [{}]),
    ("stable_id_mapping", [{"triage_finding_id": "a", "feature_forge_finding_id": "F", "extra": 0}]),
    ("stable_id_mapping", [{"triage_finding_id": "a", "feature_forge_finding_id": "F"},
                           {"triage_finding_id": "a", "feature_forge_finding_id": "G"}]),
    ("stable_id_mapping", [{"triage_finding_id": "a", "feature_forge_finding_id": "F"},
                           {"triage_finding_id": "b", "feature_forge_finding_id": "F"}]),
])
def test_strict_receipt_rejects_malformed_evidence(tmp_path: Path, field: str, value: object) -> None:
    payload = receipt_payload()
    payload[field] = value
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload))
    assert runpy.run_path(str(CHECKER))["strict_receipt"](path) == (None, "receipt=unsupported")


@pytest.mark.parametrize("key", list(receipt_payload()) + ["extra"])
def test_strict_receipt_requires_exact_keys(tmp_path: Path, key: str) -> None:
    payload = receipt_payload()
    if key == "extra":
        payload[key] = None
    else:
        payload.pop(key)
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload))
    assert runpy.run_path(str(CHECKER))["strict_receipt"](path) == (None, "receipt=unsupported")


@pytest.mark.parametrize("field", ["dispatch_id", "run_ref", "target_seal", "source_value", "source_path"])
def test_strict_receipt_rejects_whitespace_only_identities(tmp_path: Path, field: str) -> None:
    payload = receipt_payload()
    if field.startswith("source_"):
        payload["source_identity"][field.removeprefix("source_")] = " \t"
    else:
        payload[field] = " \t"
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload))

    assert runpy.run_path(str(CHECKER))["strict_receipt"](path) == (
        None, "receipt=unsupported",
    )


@pytest.mark.parametrize(("triage_id", "expected"), [
    ("current-triage-id", "FF-8ba19360e98813264f1a2312b6cf6d0691f058ad9740655c00f6f556a4041117"),
    ("缺失-α", "FF-919d54635b202d94b3bd4c4e320557c953e6f8e0c1dd5d0cee5dfab8b96c01fc"),
])
def test_allocated_finding_id_fixed_vectors(triage_id: str, expected: str) -> None:
    allocate = runpy.run_path(str(CHECKER)).get("allocated_finding_id")
    assert callable(allocate), "installed deterministic allocator is missing"
    assert allocate("specification-2", triage_id) == expected


@pytest.mark.parametrize(("result", "triage", "ids", "round_number", "previous", "expected"), [
    ("pass", "artifact", [], 0, [], True),
    ("pass", None, [], 0, [], False),
    ("pass", "artifact", ["F"], 1, [], False),
    ("changes_required", "artifact", ["F"], 1, [], True),
    ("changes_required", None, ["F"], 1, [], False),
    ("changes_required", "artifact", [], 1, [], False),
    ("changes_required", "artifact", ["F"], 0, [], False),
    ("changes_required", "artifact", ["F"], 3, [], False),
    ("changes_required", "artifact", ["F"], 2, ["F"], False),
    ("blocked", None, [], 0, [], True),
    ("blocked", None, ["F"], 1, [], False),
    ("blocked", "artifact", [], 3, [], False),
    ("blocked", "artifact", ["F"], 1, [], False),
    ("blocked", "artifact", ["F"], 3, [], True),
    ("blocked", "artifact", ["F"], 2, ["F"], True),
])
def test_receipt_result_matrix(result, triage, ids, round_number, previous, expected) -> None:
    api = runpy.run_path(str(CHECKER))
    predicate = api.get("receipt_result_invariant")
    assert callable(predicate), "installed result predicate is missing"
    payload = receipt_payload()
    payload.update(result=result, triage_artifact_id=triage, actionable_finding_ids=ids,
                   triage_finding_ids=["T"] if ids else [],
                   stable_id_mapping=[{"triage_finding_id": "T", "feature_forge_finding_id": "F"}] if ids else [])
    review = {"round": round_number, "previous_open_finding_ids": previous or (["F", "other"] if ids else [])}
    assert predicate(payload, review) is expected


@pytest.mark.parametrize("defect", ["unknown-source", "missing-source", "wrong-actionable",
                                    "unknown-destination", "allocation-collision"])
def test_receipt_mapping_requires_complete_accounting(defect: str) -> None:
    api = runpy.run_path(str(CHECKER))
    predicate = api.get("receipt_result_invariant")
    assert callable(predicate), "installed result predicate is missing"
    payload = receipt_payload()
    payload.update(result="changes_required", triage_finding_ids=["T"], actionable_finding_ids=["F"],
                   stable_id_mapping=[{"triage_finding_id": "T", "feature_forge_finding_id": "F"}])
    review = {"round": 1, "previous_open_finding_ids": ["F", "G"]}
    if defect == "unknown-source":
        payload["stable_id_mapping"][0]["triage_finding_id"] = "unknown"
    elif defect == "missing-source":
        payload["stable_id_mapping"] = []
    elif defect == "wrong-actionable":
        payload["actionable_finding_ids"] = ["G"]
    elif defect == "unknown-destination":
        payload["actionable_finding_ids"] = ["unknown"]
        payload["stable_id_mapping"][0]["feature_forge_finding_id"] = "unknown"
    else:
        destination = api["allocated_finding_id"](payload["dispatch_id"], "T")
        payload["actionable_finding_ids"] = [destination]
        payload["stable_id_mapping"][0]["feature_forge_finding_id"] = destination
        review["previous_open_finding_ids"] = [destination, "G"]
    assert predicate(payload, review) is False


def semantic_finding(identifier: str = "current-triage-id", claim: str = "REQ-007 lacks an acceptance check") -> dict[str, object]:
    return {
        "id": identifier,
        "sources": [{"report_id": "current-report", "finding_id": "current-finding",
                     "claim": claim, "severity": "Minor", "locators": ["REQ-007"]}],
        "source_ids": ["current-report:current-finding"], "reported_severity": "Minor",
        "current_severity": "Minor", "factual": "CONFIRMED", "state": "OPEN",
        "evidence_locators": ["REQ-007"], "target_seal": "current-seal",
    }


def mapping_payload() -> dict[str, object]:
    return {
        "dispatch_id": "specification-2",
        "materially_same_criterion": "same grounded discrepancy with no material change in required correction",
        "prior_findings": [{"feature_forge_finding_id": "FF-prior",
                            "triage_finding": semantic_finding("unrelated-id-spelling")}],
        "current_findings": [semantic_finding()],
        "decisions": [{"triage_finding_id": "current-triage-id", "decision": "FF-prior",
                       "rationale": "same missing REQ-007 verification"}],
    }


def mapping_api():
    helper = runpy.run_path(str(CHECKER)).get("apply_stable_id_decisions")
    assert callable(helper), "installed stable-ID mapper is missing"
    return helper


def test_stable_id_mapper_reuses_prior_id_and_is_pure() -> None:
    payload = mapping_payload()
    before = copy.deepcopy(payload)
    assert mapping_api()(payload) == {
        "schema": "feature-forge/stable-id-map/v1", "status": "pass",
        "stable_id_mapping": [{"triage_finding_id": "current-triage-id", "feature_forge_finding_id": "FF-prior"}],
        "error": None,
    }
    assert payload == before


def test_stable_id_mapper_allocates_two_distinct_new_ids() -> None:
    payload = mapping_payload()
    payload["current_findings"].append(semantic_finding("缺失-α"))
    payload["decisions"] = [
        {"triage_finding_id": name, "decision": "new", "rationale": None}
        for name in ("缺失-α", "current-triage-id")
    ]
    observed = mapping_api()(payload)
    assert observed["status"] == "pass"
    assert observed["stable_id_mapping"] == [
        {"triage_finding_id": "current-triage-id", "feature_forge_finding_id": "FF-8ba19360e98813264f1a2312b6cf6d0691f058ad9740655c00f6f556a4041117"},
        {"triage_finding_id": "缺失-α", "feature_forge_finding_id": "FF-919d54635b202d94b3bd4c4e320557c953e6f8e0c1dd5d0cee5dfab8b96c01fc"},
    ]


@pytest.mark.parametrize("defect", [
    "missing-decision", "unknown-source", "unknown-prior", "missing-rationale", "empty-rationale",
    "new-rationale", "reused-prior", "duplicate-current", "duplicate-prior", "extra-decision-key",
    "extra-payload-key", "missing-claim", "projected-finding", "allocation-collision",
    "empty-criterion", "invalid-dispatch", "null-payload", "reuse-allocation-collision",
])
def test_stable_id_mapper_rejects_incomplete_or_ambiguous_mapping(defect: str) -> None:
    payload = mapping_payload()
    if defect == "missing-decision":
        payload["decisions"] = []
    elif defect == "unknown-source":
        payload["decisions"][0]["triage_finding_id"] = "unknown"
    elif defect == "unknown-prior":
        payload["decisions"][0]["decision"] = "unknown"
    elif defect == "missing-rationale":
        payload["decisions"][0].pop("rationale")
    elif defect == "empty-rationale":
        payload["decisions"][0]["rationale"] = " "
    elif defect == "new-rationale":
        payload["decisions"][0]["decision"] = "new"
    elif defect == "reused-prior":
        payload["current_findings"].append(semantic_finding("second"))
        payload["decisions"].append({"triage_finding_id": "second", "decision": "FF-prior", "rationale": "same"})
    elif defect == "duplicate-current":
        payload["current_findings"] *= 2
    elif defect == "duplicate-prior":
        payload["prior_findings"] *= 2
    elif defect == "extra-decision-key":
        payload["decisions"][0]["extra"] = 0
    elif defect == "extra-payload-key":
        payload["extra"] = 0
    elif defect == "missing-claim":
        payload["current_findings"][0]["sources"][0].pop("claim")
    elif defect == "projected-finding":
        payload["current_findings"][0].pop("sources")
    elif defect == "allocation-collision":
        payload["prior_findings"][0]["feature_forge_finding_id"] = "FF-8ba19360e98813264f1a2312b6cf6d0691f058ad9740655c00f6f556a4041117"
        payload["decisions"][0].update(decision="new", rationale=None)
    elif defect == "reuse-allocation-collision":
        identifier = "FF-8ba19360e98813264f1a2312b6cf6d0691f058ad9740655c00f6f556a4041117"
        payload["prior_findings"][0]["feature_forge_finding_id"] = identifier
        payload["decisions"][0]["decision"] = identifier
    elif defect == "empty-criterion":
        payload["materially_same_criterion"] = " "
    elif defect == "invalid-dispatch":
        payload["dispatch_id"] = "../escape"
    else:
        payload = None
    observed = mapping_api()(payload)
    assert set(observed) == {"schema", "status", "stable_id_mapping", "error"}
    assert observed["schema"] == "feature-forge/stable-id-map/v1"
    assert observed["status"] == "fail" and observed["stable_id_mapping"] == []
    assert isinstance(observed["error"], str) and observed["error"]



def assert_result(result: subprocess.CompletedProcess[str], status: str, code: int) -> None:
    assert result.returncode == code, result.stderr
    assert result.stdout == f"FF-CHECK v1 gate=audit status={status}\n"
    assert result.stderr.splitlines() == sorted(result.stderr.splitlines())


def audit_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    repo = make_repo(tmp_path)
    specification = repo / "docs/superpowers/specs/2026-08-25-alpha-design.md"
    plan = repo / "docs/superpowers/plans/2026-08-25-alpha.md"
    for path, content in ((specification, b"specification\n"), (plan, b"plan\n")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    git(repo, "add", specification.relative_to(repo).as_posix(), plan.relative_to(repo).as_posix())
    git(repo, "commit", "-qm", "freeze specification and plan")
    data = head(repo)
    data["frozen"] = {
        "specification": {
            "path": specification.relative_to(repo).as_posix(),
            "blob": git(repo, "hash-object", "-w", specification.relative_to(repo).as_posix()),
        },
        "plan": {
            "path": plan.relative_to(repo).as_posix(),
            "blob": git(repo, "hash-object", "-w", plan.relative_to(repo).as_posix()),
        },
    }
    directory = run_dir(repo)
    write_ledger(directory, data)
    return repo, directory, data


def source_identity(
    repo: Path, directory: Path, kind: str, dispatch_id: str,
) -> dict[str, object]:
    if kind == "implementation":
        return {"kind": "reviewed_commit", "path": None,
                "value": git(repo, "rev-parse", "HEAD")}
    relative = (
        "docs/superpowers/specs/2026-08-25-alpha-design.md"
        if kind == "specification" else "docs/superpowers/plans/2026-08-25-alpha.md"
    )
    return {
        "kind": "candidate_sha256", "path": relative,
        "value": hashlib.sha256((repo / relative).read_bytes()).hexdigest(),
    }


def returned_review(
    repo: Path,
    directory: Path,
    data: dict[str, object],
    *,
    kind: str = "specification",
    state: str = "pass",
    round_number: int = 0,
    previous: list[str] | None = None,
    opened: list[str] | None = None,
    receipt_result: str | None = None,
) -> dict[str, object]:
    opened = [] if opened is None else opened
    previous = [] if previous is None else previous
    dispatch_id = f"{kind}-review-1"
    mapping = [
        {"triage_finding_id": identifier,
         "feature_forge_finding_id": identifier if identifier in previous else
         "FF-" + hashlib.sha256(json.dumps([dispatch_id, identifier], ensure_ascii=False,
                                          separators=(",", ":")).encode()).hexdigest()}
        for identifier in opened
    ]
    opened = sorted(row["feature_forge_finding_id"] for row in mapping)
    reviewed_commit = git(repo, "rev-parse", "HEAD") if kind == "implementation" else None
    review = {
        "kind": kind, "state": state, "round": round_number,
        "root_identity": f"{kind}-root", "dispatch_id": dispatch_id,
        "run_ref": f"/external/review-loop/{dispatch_id}", "target_seal": f"seal-{dispatch_id}",
        "evidence_path": f"docs/feature-forge/runs/2026-08-25-alpha/reviews/{dispatch_id}.json",
        "reviewed_commit": reviewed_commit,
        "previous_open_finding_ids": previous, "open_finding_ids": opened,
    }
    data["review"] = review
    if data["stage"]["id"] == 1:
        owning_stage = {"specification": 5, "plan": 8, "implementation": 10}[kind]
        correction_stage = {"specification": 3, "plan": 7, "implementation": 9}[kind]
        data["stage"] = {
            "id": correction_stage if state == "changes_required" else owning_stage,
            "state": "blocked" if state == "blocked" else "complete" if state == "pass" else "active",
        }
        data["status"] = "blocked" if state == "blocked" else "active"
    path = directory / "reviews" / f"{dispatch_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "feature-forge/review-receipt/v1",
        "kind": kind, "dispatch_id": dispatch_id, "run_ref": review["run_ref"],
        "target_seal": review["target_seal"],
        "source_identity": source_identity(repo, directory, kind, dispatch_id),
        "result": receipt_result or state, "actionable_finding_ids": opened,
        "feature_forge_charter_id": f"feature-forge/{kind}-review/v1",
        "completion_criterion": "No grounded discrepancies remain.",
        "raw_report_ids": ["report"],
        "triage_artifact_id": None if state == "blocked" and not opened else "triage-artifact",
        "triage_finding_ids": sorted(row["triage_finding_id"] for row in mapping),
        "stable_id_mapping": mapping,
    }, sort_keys=True))
    write_ledger(directory, data)
    return review


def recover_review(
    repo: Path, directory: Path, data: dict[str, object],
) -> tuple[dict[str, object] | None, object]:
    checker = runpy.run_path(str(CHECKER))
    return checker["recover_review_return"](repo, directory, data)


def invoke(repo: Path, directory: Path) -> subprocess.CompletedProcess[str]:
    return check("audit", "--repo", str(repo), "--run", str(directory))


@pytest.mark.parametrize("status", TASK_STATUSES + ("  awaiting_return  ",))
def test_audit_accepts_exact_task_statuses(tmp_path: Path, status: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    write_ledger(directory, data, markdown=task_markdown(("W-2", status, "c123", "pytest: pass", "")))
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_rejects_annotated_task_status(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    write_ledger(directory, data, markdown=task_markdown((
        "W-2", "awaiting_return (see Blockers)", "c123", "pytest: pass", "",
    )))
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "task-status=unsupported\n"


def test_audit_accepts_task_commentary_only_in_notes(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    write_ledger(directory, data, markdown=task_markdown((
        "W-2", "awaiting_return", "c123", "pytest: pass",
        r"return held for drift \| see Blockers",
    )))
    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize("markdown", [
    task_markdown(("", "", "", "", "")),
    task_markdown(("W-1", "pending", "", "", "")),
    task_markdown(("W-1", "active", "", "", "work in progress")),
    task_markdown(("W-1", "awaiting_return", "", "", "worker active")),
    task_markdown(("W-1", "blocked", "", "", "await authority")),
])
def test_audit_accepts_noncomplete_task_progress_during_stage_9(
    tmp_path: Path, markdown: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(repo, directory, data, kind="plan", state="pass")
    data.update(stage={"id": 9, "state": "active"}, next_action="continue implementation")
    write_ledger(directory, data, markdown=markdown)

    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize(("stage_id", "markdown"), [
    (10, task_markdown(("", "", "", "", ""))),
    (10, task_markdown(("W-1", "pending", "", "", ""))),
    (10, task_markdown(("W-1", "complete", "", "pytest: pass", ""))),
    (14, task_markdown(("W-1", "complete", "abc123", " ", ""))),
])
def test_audit_requires_complete_task_evidence_at_stage_10_and_later(
    tmp_path: Path, stage_id: int, markdown: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(repo, directory, data, kind="implementation", state="pass")
    terminal = stage_id == 14
    data.update(
        status="complete" if terminal else "active",
        stage={"id": stage_id, "state": "complete" if terminal else "active"},
        next_action=None if terminal else "continue implementation review",
    )
    write_ledger(directory, data, markdown=markdown)

    observed = invoke(repo, directory)

    assert_result(observed, "fail", 1)
    assert observed.stderr == "task-progress=incomplete\n"


@pytest.mark.parametrize("markdown", [
    "",
    "\n## Implementation progress\n\n| plan task | status | commit | evidence |\n| --- | --- | --- | --- |\n| W-2 | active | c123 | pytest: pass |\n",
    "\n## Implementation progress\n\n| plan task | status | commit | evidence | notes |\n| --- | --- | --- | --- | --- |\n| W-2 | active | c123 | pytest: pass | note | extra |\n",
    task_markdown(
        ("", "", "", "", ""),
        ("W-2", "active", "c123", "pytest: pass", ""),
    ),
    task_markdown(("W-2", "active", "c123", "pytest: pass", ""))
    + "\nIgnored prose\n| W-3 | awaiting_return (see Blockers) | | | |\n",
])
def test_audit_rejects_malformed_task_table(tmp_path: Path, markdown: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    write_ledger(directory, data, markdown=markdown)
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "task-table=unsupported\n"


def fixture_snapshot(repo: Path) -> tuple[dict[str, bytes], bytes]:
    files = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*") if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=repo,
        capture_output=True, check=True,
    ).stdout
    return files, status


def lifecycle_head(repo: Path, directory: Path, data: dict[str, object],
                   kind: str | None, state: str) -> None:
    """Build real receipts; lifecycle expectations are supplied by each case."""
    if state == "not_started":
        return
    returned = state not in {"review_active", "reserved"}
    review = returned_review(
        repo, directory, data, kind=kind, state=state if returned else "pass",
        round_number=1 if state == "changes_required" else 0,
        opened=["F-1"] if state == "changes_required" else [],
    )
    if not returned:
        (repo / review["evidence_path"]).unlink()
        review["reviewed_commit"] = None
        review["state"] = "blocked" if state == "reserved" else state
        if state == "reserved":
            for field in ("dispatch_id", "run_ref", "target_seal", "evidence_path"):
                review[field] = None


# Literal contract cases, independent of the checker's rule data.
LIFECYCLE_PAIRS = [("active", "active"), ("active", "complete"), ("blocked", "blocked")]
LIFECYCLE_ACCEPTED = (
    [(None, "not_started", stage, status, state)
     for stage in (1, 2, 3, 4, 5) for status, state in LIFECYCLE_PAIRS]
    + [(kind, "changes_required", stage, status, state)
       for kind, stages in (("specification", (3, 4)), ("plan", (7,)), ("implementation", (9,)))
       for stage in stages for status, state in LIFECYCLE_PAIRS]
    + [(kind, "pass", stage, status, state)
       for kind, stages in (("specification", (5, 6, 7, 8)), ("plan", (8, 9, 10)),
                            ("implementation", (10, 11, 12, 13, 14)))
       for stage in stages for status, state in LIFECYCLE_PAIRS
       if (stage, state) != (14, "complete")]
    + [(kind, review, stage, "blocked", "blocked")
       for kind, stage in (("specification", 5), ("plan", 8), ("implementation", 10))
       for review in ("reserved", "blocked")]
    + [(None, "not_started", stage, "blocked", "invalidated") for stage in range(1, 15)]
    + [("implementation", "pass", 14, "complete", "complete")]
)


@pytest.mark.parametrize(("kind", "review", "stage", "status", "state"), LIFECYCLE_ACCEPTED)
def test_audit_accepts_current_head_lifecycle_classes(
    tmp_path: Path, kind: str | None, review: str, stage: int, status: str, state: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    lifecycle_head(repo, directory, data, kind, review)
    data.update(status=status, stage={"id": stage, "state": state},
                next_action=None if status == "complete" else "controller-owned action")
    if stage < 7:
        data["frozen"]["specification"] = None
    if stage < 9:
        data["frozen"]["plan"] = None
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize(("kind", "review", "stage"), [
    (None, "not_started", 6),
    ("specification", "review_active", 4), ("specification", "review_active", 6),
    ("plan", "review_active", 7), ("plan", "review_active", 9),
    ("implementation", "review_active", 9), ("implementation", "review_active", 11),
    ("specification", "changes_required", 2), ("specification", "changes_required", 5),
    ("plan", "changes_required", 6), ("plan", "changes_required", 8),
    ("implementation", "changes_required", 8), ("implementation", "changes_required", 10),
    ("specification", "pass", 4), ("specification", "pass", 9),
    ("plan", "pass", 7), ("plan", "pass", 11), ("implementation", "pass", 9),
    ("specification", "reserved", 4), ("specification", "blocked", 6),
    ("plan", "reserved", 7), ("plan", "blocked", 9),
    ("implementation", "reserved", 9), ("implementation", "blocked", 11),
])
def test_audit_rejects_review_outside_compatible_stages(
    tmp_path: Path, kind: str | None, review: str, stage: int,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    lifecycle_head(repo, directory, data, kind, review)
    blocked = review in {"reserved", "blocked"}
    data.update(status="blocked" if blocked else "active",
                stage={"id": stage, "state": "blocked" if blocked else "active"})
    write_ledger(directory, data)
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "review=inconsistent\n"


@pytest.mark.parametrize(("review", "stage", "status", "state", "finding"), [
    ("review_active", 5, "active", "complete", "review=inconsistent"),
    ("blocked", 5, "active", "active", "review=inconsistent"),
    ("reserved", 5, "active", "complete", "review=inconsistent"),
    ("changes_required", 3, "active", "blocked", "status-stage=inconsistent"),
    ("pass", 5, "blocked", "active", "status-stage=inconsistent"),
    ("not_started", 1, "active", "invalidated", "status-stage=inconsistent"),
    ("pass", 5, "blocked", "invalidated", "review=inconsistent"),
    ("review_active", 5, "blocked", "invalidated", "review=inconsistent"),
    ("changes_required", 3, "blocked", "invalidated", "review=inconsistent"),
    ("blocked", 5, "blocked", "invalidated", "review=inconsistent"),
    ("not_started", 1, "blocked", "complete", "status-stage=inconsistent"),
    ("not_started", 1, "active", "pending", "status-stage=inconsistent"),
])
def test_audit_rejects_incompatible_status_and_stage_states(
    tmp_path: Path, review: str, stage: int, status: str, state: str, finding: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    lifecycle_head(repo, directory, data, None if review == "not_started" else "specification", review)
    data.update(status=status, stage={"id": stage, "state": state})
    write_ledger(directory, data)
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == finding + "\n"


@pytest.mark.parametrize("stage", range(1, 15))
def test_audit_rejects_any_pending_current_stage(tmp_path: Path, stage: int) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["stage"] = {"id": stage, "state": "pending"}
    write_ledger(directory, data)
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "status-stage=inconsistent\n"


@pytest.mark.parametrize(("stage", "authority"),
                         [(7, "specification"), (8, "specification")]
                         + [(stage, authority) for stage in range(9, 15)
                            for authority in ("specification", "plan")])
def test_audit_requires_frozen_authority_at_each_downstream_stage(
    tmp_path: Path, stage: int, authority: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    lifecycle_head(repo, directory, data, "specification" if stage < 9 else "implementation", "pass")
    data.update(status="active", stage={"id": stage, "state": "active"})
    data["frozen"][authority] = None
    write_ledger(directory, data)
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "frozen=incomplete\n"


@pytest.mark.parametrize("action", [None, "", " \t\n"])
def test_audit_requires_a_nonblank_nonterminal_action(tmp_path: Path, action: object) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["next_action"] = action
    write_ledger(directory, data)
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "terminal=inconsistent\n"


@pytest.mark.parametrize("kind", [None, "specification", "plan"])
def test_audit_requires_implementation_pass_for_terminal_head(tmp_path: Path, kind: str | None) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    lifecycle_head(repo, directory, data, kind, "pass" if kind else "not_started")
    data.update(status="complete", stage={"id": 14, "state": "complete"}, next_action=None)
    write_ledger(directory, data)
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "review=inconsistent\n"


@pytest.mark.parametrize("kind,correction,dispatch", [("specification", 4, 5), ("plan", 7, 8), ("implementation", 9, 10)])
@pytest.mark.parametrize("phase", ["correction", "reservation", "dispatched"])
def test_audit_accepts_individual_same_kind_rereview_heads(
    tmp_path: Path, kind: str, correction: int, dispatch: int, phase: str,
) -> None:
    # Audit validates each current head, not their historical succession. The
    # public boundary and behavior fixtures verify controller transitions.
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, kind=kind, state="changes_required",
                             round_number=2, previous=["F-1"], opened=["F-2"])
    retained = {key: review[key] for key in ("kind", "root_identity", "round",
                                           "previous_open_finding_ids", "open_finding_ids")}
    data.update(status="active", stage={"id": correction, "state": "active"})
    if phase != "correction":
        review["reviewed_commit"] = None
        for field in ("dispatch_id", "run_ref", "target_seal", "evidence_path"):
            review[field] = None
        review["state"] = "blocked"
        data.update(status="blocked", stage={"id": dispatch, "state": "blocked"})
    if phase == "dispatched":
        review.update(state="review_active", dispatch_id=f"{kind}-review-3",
                      run_ref=f"/external/review-loop/{kind}-review-3", target_seal="fresh-seal",
                      evidence_path=f"docs/feature-forge/runs/2026-08-25-alpha/reviews/{kind}-review-3.json")
        data.update(status="active", stage={"id": dispatch, "state": "active"})
    assert {key: review[key] for key in retained} == retained
    write_ledger(directory, data)
    expected = "fail" if phase == "dispatched" else "pass"
    assert_result(invoke(repo, directory), expected, 1 if expected == "fail" else 0)


def test_audit_accepts_the_exact_clean_not_started_head(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    assert set(data) == HEAD_KEYS
    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize("command", ["runs", "audit", "reviewed-snapshot"])
@pytest.mark.parametrize("value", [{}, []], ids=["object", "array"])
@pytest.mark.parametrize(("field", "diagnostic"), [
    ("status", "status=unsupported"),
    ("stage.state", "stage=unsupported"),
    ("review.kind", "review=unsupported"),
    ("review.state", "review=unsupported"),
])
def test_public_commands_reject_unhashable_ledger_enums_without_a_traceback(
    tmp_path: Path, command: str, value: object, field: str, diagnostic: str,
) -> None:
    """Missing enum type guards must yield an unsupported result, not a crash."""
    repo, directory, data = audit_fixture(tmp_path)
    if "." in field:
        parent, key = field.split(".")
        data[parent][key] = value
    else:
        data[field] = value
    write_ledger(directory, data)
    if command == "runs":
        observed = check(command, "--repo", str(repo), "--run-id", "alpha")
        if field == "status":
            diagnostic = "ledger-status=unsupported"
        expected = sorted([
            "branch=feature/alpha",
            f"ledger=docs/feature-forge/runs/2026-08-25-alpha/ledger.md:{diagnostic}",
            f"worktree={repo.resolve()}",
        ])
    else:
        observed = check(command, "--repo", str(repo), "--run", str(directory))
        expected = [diagnostic]
    assert observed.returncode == 2, observed.stderr
    assert observed.stdout == f"FF-CHECK v1 gate={command} status=unverifiable\n"
    assert observed.stderr.splitlines() == expected
    assert "Traceback" not in observed.stdout + observed.stderr


@pytest.mark.parametrize("value", [None, "automatic", "SUPERVISED", 1])
def test_audit_rejects_missing_or_unsupported_mode(tmp_path: Path, value: object) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    if value is None:
        data.pop("mode")
    else:
        data["mode"] = value
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("mode", ["interactive", "supervised", "unattended"])
def test_audit_accepts_supported_modes(tmp_path: Path, mode: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["mode"] = mode
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize("redirect", ["branch", "specification-path", "base-ref", "blob-ref"])
def test_audit_rejects_redirectable_identity_values(tmp_path: Path, redirect: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    if redirect == "branch":
        data["branch"] = "feature/other"
    elif redirect == "specification-path":
        data["frozen"]["specification"] = {
            "path": "README.md", "blob": git(repo, "hash-object", "-w", "README.md"),
        }
    elif redirect == "base-ref":
        data["base_identity"] = "HEAD"
    else:
        data["frozen"]["specification"]["blob"] = "HEAD"
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("identity", ["base", "blob"])
def test_audit_treats_unresolvable_full_identity_as_unverifiable(
    tmp_path: Path, identity: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    missing = "0" * len(git(repo, "rev-parse", "HEAD"))
    if identity == "base":
        data["base_identity"] = missing
    else:
        data["frozen"]["specification"]["blob"] = missing
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_audit_rejects_a_staged_only_frozen_blob(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    relative = data["frozen"]["plan"]["path"]
    (repo / relative).write_text("staged plan\n")
    git(repo, "add", relative)
    data["frozen"]["plan"]["blob"] = git(repo, "rev-parse", f":{relative}")
    write_ledger(directory, data)

    observed = invoke(repo, directory)

    assert_result(observed, "fail", 1)
    assert observed.stderr == "frozen=plan:not-at-head\n"


@pytest.mark.parametrize(("location", "extra"), [
    ("head", "unexpected"), ("stage", "current"), ("frozen", "report"), ("review", "result"),
])
def test_audit_rejects_unknown_keys(tmp_path: Path, location: str, extra: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    target = data if location == "head" else data[location]
    target[extra] = "misspelled state"
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize(("field", "value"), [
    ("run_id", 1), ("status", "done"), ("worktree", 1), ("branch", 1),
    ("base_identity", None), ("next_action", 1),
])
def test_audit_rejects_wrong_top_level_types_and_enums(
    tmp_path: Path, field: str, value: object,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data[field] = value
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize(("stage", "status"), [
    ({"id": 0, "state": "active"}, "unverifiable"),
    ({"id": 15, "state": "active"}, "unverifiable"),
    ({"id": True, "state": "active"}, "unverifiable"),
    ({"id": 2, "state": "unknown"}, "unverifiable"),
])
def test_audit_rejects_invalid_stage_shape_range_or_enum(
    tmp_path: Path, stage: object, status: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["stage"] = stage
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), status, 2)


@pytest.mark.parametrize(("status", "stage", "next_action"), [
    ("complete", {"id": 14, "state": "complete"}, "do more"),
    ("active", {"id": 4, "state": "active"}, None),
    ("complete", {"id": 13, "state": "complete"}, None),
    ("active", {"id": 14, "state": "complete"}, "finish already complete"),
])
def test_audit_enforces_the_exact_terminal_triple(
    tmp_path: Path, status: str, stage: dict[str, object], next_action: str | None,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data.update(status=status, stage=stage, next_action=next_action)
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_accepts_only_complete_stage_14_as_terminal(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data.update(status="complete", stage={"id": 14, "state": "complete"}, next_action=None)
    returned_review(repo, directory, data, kind="implementation")
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_accepts_local_merge_terminal_state_in_the_primary_base_checkout(
    tmp_path: Path,
) -> None:
    repo = make_primary_repo(tmp_path, branch="main")
    base = git(repo, "rev-parse", "HEAD")
    feature = tmp_path / "feature-worktree"
    git(repo, "worktree", "add", "-qb", "feature/alpha", str(feature), "HEAD")
    paths = {
        "specification": "docs/superpowers/specs/2026-08-25-alpha-design.md",
        "plan": "docs/superpowers/plans/2026-08-25-alpha.md",
    }
    for name, relative in paths.items():
        target = feature / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{name}\n")
    git(feature, "add", *paths.values())
    git(feature, "commit", "-qm", "reviewed implementation")
    reviewed_commit = git(feature, "rev-parse", "HEAD")
    (repo / "base-only.txt").write_text("independent base change\n")
    git(repo, "add", "base-only.txt")
    git(repo, "commit", "-qm", "advance base")
    git(repo, "merge", "--no-ff", "-qm", "merge feature", "feature/alpha")
    frozen = {
        name: {"path": relative, "blob": git(repo, "rev-parse", f"HEAD:{relative}")}
        for name, relative in paths.items()
    }
    directory = run_dir(repo)
    data = head(
        repo, status="complete", branch="main", base_identity=base, frozen=frozen,
    )
    data["stage"] = {"id": 14, "state": "complete"}
    review = returned_review(repo, directory, data, kind="implementation")
    review["reviewed_commit"] = reviewed_commit
    receipt_path = repo / review["evidence_path"]
    receipt = json.loads(receipt_path.read_text())
    receipt["source_identity"]["value"] = reviewed_commit
    receipt_path.write_text(json.dumps(receipt, sort_keys=True))
    write_ledger(directory, data)

    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize("frozen", [
    None,
    {"specification": None},
    {"specification": {"path": "../escape", "blob": "abc"}, "plan": None},
    {"specification": {"path": ".", "blob": "abc"}, "plan": None},
    {"specification": {"path": "docs/spec.md", "blob": 1}, "plan": None},
    {"specification": {"path": "docs/spec.md", "blob": "abc", "extra": True}, "plan": None},
])
def test_audit_rejects_malformed_frozen_objects(tmp_path: Path, frozen: object) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["frozen"] = frozen
    write_ledger(directory, data)
    wrong_path = isinstance(frozen, dict) and isinstance(frozen.get("specification"), dict) and frozen["specification"].get("path") in {"../escape", "."}
    assert_result(invoke(repo, directory), "fail" if wrong_path else "unverifiable", 1 if wrong_path else 2)


def test_audit_does_not_pass_a_populated_review_active_head(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["stage"] = {"id": 8, "state": "active"}
    data["review"] = {
        "kind": "plan", "state": "review_active", "round": 2,
        "root_identity": "plan-root", "dispatch_id": "plan-review-3",
        "run_ref": "/external/review-loop/plan-review-3", "target_seal": "opaque-seal",
        "evidence_path": "docs/feature-forge/runs/2026-08-25-alpha/reviews/plan-review-3.json",
        "reviewed_commit": None,
        "previous_open_finding_ids": ["F-1"], "open_finding_ids": ["F-2"],
    }
    write_ledger(directory, data)
    assert not (directory / "reviews/plan-review-3.json").exists()
    observed = invoke(repo, directory)
    assert_result(observed, "fail", 1)
    assert observed.stderr == "review=active\n"


@pytest.mark.parametrize("receipt_result", ["pass", "changes_required", "blocked"])
def test_recovery_validates_then_projects_completed_review_returns(
    tmp_path: Path, receipt_result: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    if receipt_result == "pass":
        returned = returned_review(repo, directory, data, state="pass", round_number=2)
        active_round, active_previous, active_open = 2, ["F-old"], ["F-current"]
    elif receipt_result == "changes_required":
        returned = returned_review(
            repo, directory, data, state="changes_required", round_number=2,
            previous=["F-current"], opened=["T-new"],
        )
        active_round, active_previous, active_open = 1, ["F-old"], ["F-current"]
    else:
        returned = returned_review(
            repo, directory, data, state="blocked", round_number=2,
            previous=["F-current"], opened=["F-current"],
        )
        active_round, active_previous, active_open = 1, ["F-old"], ["F-current"]
    expected_open = copy.deepcopy(returned["open_finding_ids"])
    returned.update(
        state="review_active", round=active_round, reviewed_commit=None,
        previous_open_finding_ids=active_previous,
        open_finding_ids=active_open,
    )
    data.update(status="active", stage={"id": 5, "state": "active"})

    projected, checked = recover_review(repo, directory, data)

    assert checked.status == "pass"
    assert projected is not None
    assert projected["state"] == receipt_result
    assert projected["round"] == (active_round if receipt_result == "pass" else active_round + 1)
    assert projected["previous_open_finding_ids"] == (
        active_previous if receipt_result == "pass" else active_open
    )
    assert projected["open_finding_ids"] == expected_open


def test_recovery_pretriage_block_retains_both_finding_histories(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    active_previous, active_open = ["F-old"], ["F-current"]
    active = returned_review(repo, directory, data, state="blocked", round_number=2)
    active.update(
        state="review_active", reviewed_commit=None,
        previous_open_finding_ids=active_previous, open_finding_ids=active_open,
    )
    data.update(status="active", stage={"id": 5, "state": "active"})

    projected, checked = recover_review(repo, directory, data)

    assert checked.status == "pass"
    assert projected is not None
    assert projected["state"] == "blocked"
    assert projected["round"] == 2
    assert projected["previous_open_finding_ids"] == active_previous
    assert projected["open_finding_ids"] == active_open


@pytest.mark.parametrize("defect", ["extra", "dispatch", "mapping", "source"])
def test_recovery_rejects_malformed_mismatched_or_source_divergent_receipts(
    tmp_path: Path, defect: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    active = returned_review(repo, directory, data, state="pass")
    receipt_path = repo / active["evidence_path"]
    receipt = json.loads(receipt_path.read_text())
    active.update(state="review_active", reviewed_commit=None)
    data.update(status="active", stage={"id": 5, "state": "active"})
    if defect == "extra":
        receipt["extra"] = True
    elif defect == "dispatch":
        receipt["dispatch_id"] = "different-dispatch"
    elif defect == "mapping":
        receipt["triage_finding_ids"] = ["unmapped"]
    else:
        receipt["source_identity"]["value"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt))

    projected, checked = recover_review(repo, directory, data)

    assert projected is None
    assert checked.status != "pass"


@pytest.mark.parametrize("defect", [
    "missing-fields", "negative-round", "boolean-round", "unsorted-history", "typed-history",
])
def test_recovery_rejects_malformed_active_review_heads_without_an_exception(
    tmp_path: Path, defect: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    active = returned_review(repo, directory, data, state="pass")
    active.update(state="review_active", reviewed_commit=None)
    data.update(status="active", stage={"id": 5, "state": "active"})
    if defect == "missing-fields":
        data["review"] = {"state": "review_active"}
    elif defect == "negative-round":
        active["round"] = -1
    elif defect == "boolean-round":
        active["round"] = True
    elif defect == "unsorted-history":
        active["previous_open_finding_ids"] = ["F-2", "F-1"]
    else:
        active["open_finding_ids"] = [1]

    projected, checked = recover_review(repo, directory, data)

    assert projected is None
    assert checked.status != "pass"


@pytest.mark.parametrize(("foreign_change", "expected"), [(False, "pass"), (True, "fail")])
def test_implementation_recovery_allows_only_controller_owned_descendant_changes(
    tmp_path: Path, foreign_change: bool, expected: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    active = returned_review(repo, directory, data, kind="implementation", state="pass")
    reviewed_commit = active["reviewed_commit"]
    active.update(state="review_active", reviewed_commit=None)
    data.update(status="active", stage={"id": 10, "state": "active"})
    write_ledger(directory, data)
    controlled = [
        (directory / "ledger.md").relative_to(repo).as_posix(),
        str(active["evidence_path"]),
    ]
    if foreign_change:
        implementation = repo / "src/app.py"
        implementation.parent.mkdir()
        implementation.write_text("changed implementation\n")
        controlled.append(implementation.relative_to(repo).as_posix())
    git(repo, "add", *controlled)
    git(repo, "commit", "-qm", "persist controller recovery state")
    assert git(repo, "merge-base", "--is-ancestor", str(reviewed_commit), "HEAD") == ""

    projected, checked = recover_review(repo, directory, data)

    assert checked.status == expected
    assert (projected is not None) is (expected == "pass")
    if projected is not None:
        assert projected["reviewed_commit"] == reviewed_commit


@pytest.mark.parametrize("identity", ["HEAD", "0" * 40])
def test_implementation_recovery_rejects_noncanonical_or_unresolvable_source_commit(
    tmp_path: Path, identity: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    active = returned_review(repo, directory, data, kind="implementation", state="pass")
    receipt_path = repo / active["evidence_path"]
    receipt = json.loads(receipt_path.read_text())
    receipt["source_identity"]["value"] = identity
    receipt_path.write_text(json.dumps(receipt))
    active.update(state="review_active", reviewed_commit=None)
    data.update(status="active", stage={"id": 10, "state": "active"})

    projected, checked = recover_review(repo, directory, data)

    assert projected is None
    assert checked.status != "pass"


def test_audit_rejects_an_implementation_return_after_a_foreign_descendant_change(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(repo, directory, data, kind="implementation", state="pass")
    implementation = repo / "src/app.py"
    implementation.parent.mkdir()
    implementation.write_text("post-review change\n")
    git(repo, "add", implementation.relative_to(repo).as_posix())
    git(repo, "commit", "-qm", "change implementation after review")

    observed = invoke(repo, directory)

    assert_result(observed, "fail", 1)
    assert observed.stderr == "reviewed-commit=foreign-descendant\n"


def test_audit_rejects_a_review_reservation_beneath_a_symlinked_reviews_directory(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["stage"] = {"id": 5, "state": "active"}
    outside = tmp_path / "outside-reviews"
    outside.mkdir()
    (directory / "reviews").symlink_to(outside, target_is_directory=True)
    data["review"] = {
        "kind": "specification", "state": "review_active", "round": 0,
        "root_identity": "a" * 64, "dispatch_id": "specification-1",
        "run_ref": "/external/run", "target_seal": "opaque-seal",
        "evidence_path": (
            "docs/feature-forge/runs/2026-08-25-alpha/reviews/specification-1.json"
        ),
        "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": [],
    }
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_audit_requires_both_frozen_authorities_during_implementation(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["stage"] = {"id": 11, "state": "active"}
    returned_review(repo, directory, data, kind="implementation", state="pass")
    data["frozen"] = {"specification": None, "plan": None}
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_rejects_the_wrong_symbolic_branch_at_the_same_commit(tmp_path: Path) -> None:
    repo, directory, _ = audit_fixture(tmp_path)
    git(repo, "checkout", "-qb", "feature/other")
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("kind", "state", "round_number", "opened"), [
    ("specification", "changes_required", 1, ["F-1"]),
    ("plan", "pass", 0, []),
    ("implementation", "pass", 0, []),
])
def test_audit_accepts_each_returned_review_shape(
    tmp_path: Path, kind: str, state: str, round_number: int, opened: list[str],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(repo, directory, data, kind=kind, state=state, round_number=round_number, opened=opened)
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_accepts_a_candidate_correction_between_review_rounds(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(
        repo, directory, data, kind="specification", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    specification = repo / data["frozen"]["specification"]["path"]
    specification.write_text("corrected specification\n")
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_accepts_a_committed_implementation_correction_between_rounds(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(
        repo, directory, data, kind="implementation", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    (repo / "README.md").write_text("corrected implementation\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "correct implementation")
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_rejects_an_unrelated_reviewed_commit_for_an_implementation_return(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(
        repo, directory, data, kind="implementation", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    unrelated = subprocess.run(
        ["git", "commit-tree", tree], cwd=repo, input="unrelated\n", text=True,
        check=True, capture_output=True,
    ).stdout.strip()
    review["reviewed_commit"] = unrelated
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("state", "round_number", "opened"), [
    ("changes_required", 1, ["F-1"]),
    ("blocked", 0, []),
])
def test_audit_accepts_implementation_nonpass_receipt_with_canonical_source_commit(
    tmp_path: Path, state: str, round_number: int, opened: list[str],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(
        repo, directory, data, kind="implementation", state=state,
        round_number=round_number, opened=opened,
    )
    assert review["reviewed_commit"] == git(repo, "rev-parse", "HEAD")
    receipt = json.loads((repo / review["evidence_path"]).read_text())
    assert receipt["source_identity"] == {
        "kind": "reviewed_commit", "path": None,
        "value": review["reviewed_commit"],
    }
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_rejects_an_unrelated_implementation_commit_on_a_nonpass_return(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    unrelated = git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("reviewed implementation snapshot\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "implementation snapshot")
    review = returned_review(
        repo, directory, data, kind="implementation", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    receipt = repo / review["evidence_path"]
    payload = json.loads(receipt.read_text())
    payload["source_identity"]["value"] = "0" * 64
    receipt.write_text(json.dumps(payload))
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("identity", ["HEAD", "0" * 40, "not-a-digest"])
def test_audit_rejects_noncanonical_implementation_nonpass_source_commit(
    tmp_path: Path, identity: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(
        repo, directory, data, kind="implementation", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    receipt["source_identity"]["value"] = identity
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_rejects_short_source_commit_before_observation(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(
        repo, directory, data, kind="implementation", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    abbreviated = "0" * 12
    receipt["source_identity"]["value"] = abbreviated
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_rejects_wrong_canonical_nonpass_source_commit(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(
        repo, directory, data, kind="implementation", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    missing_oid = "0" * 64
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    receipt["source_identity"]["value"] = missing_oid
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_treats_unavailable_nonpass_receipt_commit_observation_as_unverifiable(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(
        repo, directory, data, kind="implementation", state="changes_required",
        round_number=1, opened=["F-1"],
    )
    real_git = shutil.which("git")
    assert real_git is not None
    binary = tmp_path / "bin"
    binary.mkdir()
    wrapper = binary / "git"
    wrapper.write_text(
        "#!/bin/sh\n"
        "case \" $* \" in *\" rev-parse --verify \"*) exit 1;; esac\n"
        f'exec "{real_git}" "$@"\n'
    )
    wrapper.chmod(0o755)
    observed = subprocess.run(
        [sys.executable, str(CHECKER), "audit", "--repo", str(repo), "--run", str(directory)],
        text=True, capture_output=True, check=False,
        env={**os.environ, "PATH": str(binary)},
    )
    assert_result(observed, "unverifiable", 2)


@pytest.mark.parametrize("identity", ["HEAD", "abbreviated"])
def test_audit_requires_canonical_full_populated_reviewed_commit(
    tmp_path: Path, identity: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, kind="implementation", state="pass")
    if identity == "abbreviated":
        identity = str(review["reviewed_commit"])[:12]
    review["reviewed_commit"] = identity
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    receipt["source_identity"]["value"] = identity
    path.write_text(json.dumps(receipt))
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_audit_accepts_both_blocked_dispatch_cardinalities(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data.update(status="blocked", stage={"id": 5, "state": "blocked"}, next_action="resolve block")
    data["review"] = {
        "kind": "specification", "state": "blocked", "round": 0,
        "root_identity": "spec-root", "dispatch_id": None, "run_ref": None,
        "target_seal": None, "evidence_path": None, "reviewed_commit": None,
        "previous_open_finding_ids": [], "open_finding_ids": [],
    }
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "pass", 0)
    returned_review(repo, directory, data, kind="specification", state="blocked")
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_accepts_a_between_round_pre_dispatch_reservation(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data.update(status="blocked", stage={"id": 5, "state": "blocked"}, next_action="create-or-recover")
    data["review"] = {
        "kind": "specification", "state": "blocked", "round": 1,
        "root_identity": "spec-root-2", "dispatch_id": None, "run_ref": None,
        "target_seal": None, "evidence_path": None, "reviewed_commit": None,
        "previous_open_finding_ids": [], "open_finding_ids": ["F-1"],
    }
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "pass", 0)


def test_audit_rejects_a_partial_blocked_dispatch_tuple(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["review"] = {
        "kind": "specification", "state": "blocked", "round": 0,
        "root_identity": "spec-root", "dispatch_id": "partial", "run_ref": None,
        "target_seal": None,
        "evidence_path": "docs/feature-forge/runs/2026-08-25-alpha/reviews/partial.json",
        "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": [],
    }
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("state", "changes"), [
    ("not_started", {"kind": "plan"}),
    ("not_started", {"round": 1}),
    ("review_active", {"reviewed_commit": "a" * 40}),
    ("changes_required", {"round": 0}),
    ("changes_required", {"open_finding_ids": []}),
    ("pass", {"open_finding_ids": ["F-1"]}),
    ("pass", {"reviewed_commit": "a" * 40}),
])
def test_audit_rejects_review_state_dependency_violations(
    tmp_path: Path, state: str, changes: dict[str, object],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    if state == "not_started":
        review = data["review"]
    elif state == "review_active":
        review = {
            "kind": "plan", "state": "review_active", "round": 0,
            "root_identity": "root", "dispatch_id": "active-1", "run_ref": "/run",
            "target_seal": "seal",
            "evidence_path": "docs/feature-forge/runs/2026-08-25-alpha/reviews/active-1.json",
            "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": [],
        }
        data["review"] = review
    else:
        review = returned_review(
            repo, directory, data, kind="plan", state=state,
            round_number=1 if state == "changes_required" else 0,
            opened=["F-1"] if state == "changes_required" else [],
        )
    review.update(changes)
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("field", "value"), [
    ("root_identity", 1), ("dispatch_id", []), ("run_ref", False),
    ("target_seal", {}), ("evidence_path", 1), ("reviewed_commit", []),
])
def test_audit_treats_wrong_review_scalar_types_as_unverifiable(
    tmp_path: Path, field: str, value: object,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, state="pass")
    review[field] = value
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("field", ["root_identity", "run_ref", "target_seal"])
def test_audit_rejects_whitespace_only_review_identities_without_a_traceback(
    tmp_path: Path, field: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, state="pass")
    review[field] = " \t"
    if field in {"run_ref", "target_seal"}:
        receipt = repo / review["evidence_path"]
        payload = json.loads(receipt.read_text())
        payload[field] = " \t"
        receipt.write_text(json.dumps(payload))
    write_ledger(directory, data)

    observed = invoke(repo, directory)

    assert_result(observed, "unverifiable", 2)
    assert observed.stderr == "review=unsupported\n"
    assert "Traceback" not in observed.stdout + observed.stderr


def test_audit_treats_a_nul_in_the_ledger_branch_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["branch"] = "feature/alpha\0forged"
    write_ledger(directory, data)
    observed = invoke(repo, directory)
    assert_result(observed, "unverifiable", 2)
    assert "Traceback" not in observed.stderr


def test_audit_requires_reviewed_commit_only_for_implementation_pass(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, kind="implementation", state="pass")
    review["reviewed_commit"] = None
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("round_number", "previous", "opened"), [
    (3, ["F-1"], ["F-2"]),
    (2, ["F-1", "F-2"], ["F-1", "F-2"]),
])
def test_audit_fails_unblocked_cap_or_oscillation_state(
    tmp_path: Path, round_number: int, previous: list[str], opened: list[str],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(
        repo, directory, data, state="changes_required", round_number=round_number,
        previous=previous, opened=opened,
    )
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("round_number", "previous", "current", "expected"), [
    (1, ["F-1"], ["F-2"], False),
    (2, ["F-1"], ["F-2"], False),
    (3, ["F-1"], ["F-2"], True),
    (1, ["F-1"], ["F-1"], True),
    (3, ["F-1"], [], False),
])
def test_review_must_block_uses_the_post_return_round_and_consecutive_ids(
    round_number: int, previous: list[str], current: list[str], expected: bool,
) -> None:
    checker = runpy.run_path(str(CHECKER))
    assert checker["review_must_block"](round_number, previous, current) is expected


def test_audit_rejects_blocked_before_the_actionable_return_boundary(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(
        repo, directory, data, state="blocked", round_number=1,
        previous=[], opened=["F-1"],
    )
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("prior_round", "previous", "mapped", "expected_round"), [
    (2, ["F-1"], ["F-2"], 3),
    (1, ["F-1"], ["F-1"], 2),
])
def test_audit_accepts_transition_fixture_that_maps_and_increments_before_blocking(
    tmp_path: Path, prior_round: int, previous: list[str], mapped: list[str], expected_round: int,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(
        repo, directory, data, state="blocked", round_number=prior_round + 1,
        previous=previous, opened=mapped,
    )
    assert review["round"] == expected_round
    assert len(review["open_finding_ids"]) == len(mapped)
    receipt = json.loads((repo / review["evidence_path"]).read_text())
    assert receipt["result"] == "blocked"
    assert receipt["actionable_finding_ids"] == review["open_finding_ids"]
    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize(("field", "value"), [
    ("previous_open_finding_ids", ["F-2", "F-1"]),
    ("previous_open_finding_ids", ["F-1", "F-1"]),
    ("open_finding_ids", ["F-2", "F-1"]),
    ("open_finding_ids", ["F-1", "F-1"]),
])
def test_audit_requires_both_actionable_id_arrays_sorted_and_unique(
    tmp_path: Path, field: str, value: list[str],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["review"][field] = value
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_audit_ignores_human_residual_minor_evidence_and_history(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(repo, directory, data, kind="plan", state="pass")
    ledger = directory / "ledger.md"
    ledger.write_text(
        ledger.read_text()
        + "\n## Transition log\n\nPrior transition and residual Minor F-minor remain human evidence.\n"
    )
    assert_result(invoke(repo, directory), "pass", 0)


@pytest.mark.parametrize(("state", "receipt_result", "opened"), [
    ("pass", "blocked", []),
    ("pass", "changes_required", []),
    ("changes_required", "pass", ["F-1"]),
    ("changes_required", "blocked", ["F-1"]),
    ("blocked", "pass", []),
    ("blocked", "changes_required", []),
])
def test_audit_rejects_every_receipt_result_head_state_mismatch(
    tmp_path: Path, state: str, receipt_result: str, opened: list[str],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    returned_review(
        repo, directory, data, state=state,
        round_number=1 if state == "changes_required" else 0,
        opened=opened, receipt_result=receipt_result,
    )
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("field", "value"), [
    ("kind", "plan"), ("dispatch_id", "other"), ("run_ref", "/other"),
    ("target_seal", "other"), ("actionable_finding_ids", ["F-1"]),
])
def test_audit_rejects_return_receipt_head_disagreement(
    tmp_path: Path, field: str, value: object,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, state="pass")
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    receipt[field] = value
    if field == "kind":
        receipt["feature_forge_charter_id"] = f"feature-forge/{value}-review/v1"
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("change", [
    {"source_identity": {"kind": "candidate_sha256", "path": "docs/superpowers/plans/2026-08-25-alpha.md", "value": "0" * 64}},
    {"source_identity": {"kind": "reviewed_commit", "path": None, "value": "0" * 40}},
])
def test_audit_rejects_wrong_candidate_identity_kind_path_or_digest(
    tmp_path: Path, change: dict[str, object],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, state="pass")
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    receipt.update(change)
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("entry_type", ["symlink", "fifo"])
def test_audit_requires_an_exact_regular_candidate_file(
    tmp_path: Path, entry_type: str,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["frozen"]["specification"] = None
    review = returned_review(repo, directory, data, state="pass")
    candidate = repo / "docs/superpowers/specs/2026-08-25-alpha-design.md"
    contents = candidate.read_bytes()
    candidate.unlink()
    if entry_type == "symlink":
        outside = tmp_path / "outside-candidate.md"
        outside.write_bytes(contents)
        candidate.symlink_to(outside)
    else:
        os.mkfifo(candidate)
    assert review["kind"] == "specification"
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("source", [
    {"kind": "reviewed_commit", "path": "src/app.py", "value": "COMMIT"},
])
def test_audit_requires_implementation_receipt_commit_identity(
    tmp_path: Path, source: dict[str, object],
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, kind="implementation", state="pass")
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    if source["value"] == "COMMIT":
        source["value"] = review["reviewed_commit"]
    receipt["source_identity"] = source
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_requires_implementation_pass_receipt_to_equal_the_populated_head(
    tmp_path: Path,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, kind="implementation", state="pass")
    (repo / "README.md").write_text("different existing commit\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "another commit")
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    receipt["source_identity"]["value"] = git(repo, "rev-parse", "HEAD")
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_treats_missing_return_receipt_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, state="pass")
    (repo / review["evidence_path"]).unlink()
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("link", ["receipt", "reviews-directory"])
def test_audit_rejects_symlinked_receipt_path_components(tmp_path: Path, link: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, state="pass")
    receipt = repo / review["evidence_path"]
    if link == "receipt":
        target = receipt.with_name("real-receipt.json")
        receipt.rename(target)
        receipt.symlink_to(target.name)
    else:
        reviews = receipt.parent
        target = reviews.with_name("real-reviews")
        reviews.rename(target)
        reviews.symlink_to(target.name, target_is_directory=True)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize(("field", "value"), [
    ("extra", True), ("schema", "feature-forge/review-receipt/v2"),
    ("actionable_finding_ids", [1]),
])
def test_audit_treats_non_strict_return_receipts_as_unverifiable(
    tmp_path: Path, field: str, value: object,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    review = returned_review(repo, directory, data, state="pass")
    path = repo / review["evidence_path"]
    receipt = json.loads(path.read_text())
    receipt[field] = value
    path.write_text(json.dumps(receipt))
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("artifact", ["ledger", "receipt"])
def test_audit_rejects_duplicate_json_object_keys(tmp_path: Path, artifact: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    if artifact == "ledger":
        ledger = write_ledger(directory, data)
        text = ledger.read_text().replace('"status": "active"', '"status": "active",\n  "status": "complete"')
        ledger.write_text(text)
    else:
        review = returned_review(repo, directory, data, state="pass")
        receipt = repo / review["evidence_path"]
        text = receipt.read_text().replace('"result": "pass"', '"result": "pass", "result": "blocked"')
        receipt.write_text(text)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("field", ["stage", "round"])
def test_audit_treats_oversized_json_integers_as_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str,
) -> None:
    monkeypatch.setenv("PYTHONINTMAXSTRDIGITS", "0")
    repo, directory, data = audit_fixture(tmp_path)
    ledger = write_ledger(directory, data)
    huge = "9" * 5000
    text = ledger.read_text()
    needle = '"id": 1' if field == "stage" else '"round": 0'
    ledger.write_text(text.replace(needle, f'"{ "id" if field == "stage" else "round" }": {huge}', 1))
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_audit_rejects_a_symlinked_canonical_ledger(tmp_path: Path) -> None:
    repo, directory, _ = audit_fixture(tmp_path)
    ledger = directory / "ledger.md"
    target = ledger.with_name("real-ledger.md")
    ledger.rename(target)
    ledger.symlink_to(target.name)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("array", ["previous_open_finding_ids", "open_finding_ids"])
def test_audit_requires_empty_finding_arrays_at_round_zero(tmp_path: Path, array: str) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["review"] = {
        "kind": "plan", "state": "review_active", "round": 0, "root_identity": "root",
        "dispatch_id": "active-1", "run_ref": "/run", "target_seal": "seal",
        "evidence_path": "docs/feature-forge/runs/2026-08-25-alpha/reviews/active-1.json",
        "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": [],
    }
    data["review"][array] = ["F-1"]
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


def test_audit_rejects_wrong_future_receipt_path_without_requiring_the_file(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    data["review"] = {
        "kind": "plan", "state": "review_active", "round": 0, "root_identity": "root",
        "dispatch_id": "active-1", "run_ref": "/run", "target_seal": "seal",
        "evidence_path": "docs/feature-forge/runs/2026-08-25-alpha/reviews/other.json",
        "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": [],
    }
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("status", "code"), [("pass", 0), ("fail", 1), ("unverifiable", 2)])
def test_audit_contract_is_read_only_for_every_result_class(
    tmp_path: Path, status: str, code: int,
) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    if status == "fail":
        data["next_action"] = None
    elif status == "unverifiable":
        data["stage"]["id"] = 99
    write_ledger(directory, data)
    before = fixture_snapshot(repo)
    assert_result(invoke(repo, directory), status, code)
    assert fixture_snapshot(repo) == before
