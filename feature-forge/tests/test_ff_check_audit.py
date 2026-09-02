"""Black-box tests for the current Feature Forge ledger audit."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CHECKER, check, git, head, make_repo, run_dir, write_ledger


HEAD_KEYS = {
    "schema", "run_id", "status", "worktree", "branch", "base_identity",
    "stage", "next_action", "frozen", "review",
}


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
        captured = check(
            "implementation-snapshot", "--repo", str(repo), "--run", str(directory),
            "--dispatch-id", dispatch_id,
        )
        assert captured.returncode == 0, captured.stderr
        return {
            "kind": "implementation_snapshot_sha256", "path": None,
            "value": captured.stderr.strip().removeprefix("snapshot="),
        }
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
    path = directory / "reviews" / f"{dispatch_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "feature-forge/review-receipt/v1",
        "kind": kind, "dispatch_id": dispatch_id, "run_ref": review["run_ref"],
        "target_seal": review["target_seal"],
        "source_identity": source_identity(repo, directory, kind, dispatch_id),
        "result": receipt_result or state, "actionable_finding_ids": opened,
    }, sort_keys=True))
    write_ledger(directory, data)
    return review


def invoke(repo: Path, directory: Path) -> subprocess.CompletedProcess[str]:
    return check("audit", "--repo", str(repo), "--run", str(directory))


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


def test_audit_accepts_the_exact_clean_not_started_head(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    assert set(data) == HEAD_KEYS
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
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_audit_accepts_populated_review_active_without_a_return_receipt(tmp_path: Path) -> None:
    repo, directory, data = audit_fixture(tmp_path)
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
    assert_result(invoke(repo, directory), "pass", 0)


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
        "kind": "implementation_snapshot_sha256", "path": None,
        "value": receipt["source_identity"]["value"],
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
def test_audit_rejects_noncanonical_implementation_nonpass_snapshot_digest(
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


def test_audit_rejects_short_snapshot_digest_before_observation(
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


def test_audit_rejects_wrong_canonical_nonpass_snapshot_digest(
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
        "if [ \"$3\" = \"rev-parse\" ] && [ \"$4\" = \"--verify\" ]; then exit 1; fi\n"
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
    assert review["open_finding_ids"] == mapped
    receipt = json.loads((repo / review["evidence_path"]).read_text())
    assert receipt["result"] == "blocked" and receipt["actionable_finding_ids"] == mapped
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
    ledger.write_text(ledger.read_text() + "\nPrior transition and residual Minor F-minor remain human evidence.\n")
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
