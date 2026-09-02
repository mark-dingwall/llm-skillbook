"""Black-box tests for the reviewed implementation snapshot gate."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CHECKER, check, git, head, make_repo, run_dir, write_ledger


def assert_result(result: subprocess.CompletedProcess[str], status: str, code: int) -> None:
    assert result.returncode == code, result.stderr
    assert result.stdout == f"FF-CHECK v1 gate=reviewed-snapshot status={status}\n"
    assert result.stderr.splitlines() == sorted(result.stderr.splitlines())


def commit(repo: Path, message: str, *paths: str) -> str:
    git(repo, "add", "--", *paths)
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


def write_receipt(directory: Path, review: dict[str, object], **changes: object) -> Path:
    captured = check(
        "implementation-snapshot", "--repo", str(directory.parents[3]),
        "--run", str(directory), "--dispatch-id", str(review["dispatch_id"]),
    )
    assert captured.returncode == 0, captured.stderr
    snapshot = captured.stderr.strip().removeprefix("snapshot=")
    receipt = {
        "schema": "feature-forge/review-receipt/v1",
        "kind": "implementation",
        "dispatch_id": review["dispatch_id"],
        "run_ref": review["run_ref"],
        "target_seal": review["target_seal"],
        "source_identity": {
            "kind": "implementation_snapshot_sha256", "path": None, "value": snapshot,
        },
        "result": "pass",
        "actionable_finding_ids": [],
    }
    receipt.update(changes)
    path = directory / "reviews" / f"{review['dispatch_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, sort_keys=True))
    return path


def reviewed_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    repo = make_repo(tmp_path)
    specification = "docs/superpowers/specs/2026-08-25-alpha-design.md"
    plan = "docs/superpowers/plans/2026-08-25-alpha.md"
    implementation = "src/app.py"
    for path, contents in (
        (specification, "specification\n"), (plan, "plan\n"), (implementation, "implemented\n"),
    ):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
    reviewed_commit = commit(repo, "reviewed implementation", specification, plan, implementation)
    frozen = {
        "specification": {"path": specification, "blob": git(repo, "rev-parse", f"HEAD:{specification}")},
        "plan": {"path": plan, "blob": git(repo, "rev-parse", f"HEAD:{plan}")},
    }
    directory = run_dir(repo)
    data = head(repo, base_identity=git(repo, "rev-parse", "HEAD^"), frozen=frozen)
    data["stage"] = {"id": 11, "state": "active"}
    data["next_action"] = "verify the reviewed snapshot"
    data["review"] = {
        "kind": "implementation", "state": "pass", "round": 0,
        "root_identity": "implementation-root", "dispatch_id": "implementation-1",
        "run_ref": "/external/review-loop/run-1", "target_seal": "opaque-review-loop-seal",
        "evidence_path": (
            "docs/feature-forge/runs/2026-08-25-alpha/reviews/implementation-1.json"
        ),
        "reviewed_commit": reviewed_commit,
        "previous_open_finding_ids": [], "open_finding_ids": [],
    }
    write_receipt(directory, data["review"])
    write_ledger(directory, data)
    return repo, directory, data


def invoke(repo: Path, directory: Path) -> subprocess.CompletedProcess[str]:
    return check("reviewed-snapshot", "--repo", str(repo), "--run", str(directory))


def snapshot_digest(repo: Path, directory: Path, dispatch_id: str = "implementation-1") -> str:
    observed = check(
        "implementation-snapshot", "--repo", str(repo), "--run", str(directory),
        "--dispatch-id", dispatch_id,
    )
    assert observed.returncode == 0, observed.stderr
    return observed.stderr.strip().removeprefix("snapshot=")


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


def test_implementation_snapshot_length_frames_file_records(tmp_path: Path) -> None:
    roots = [tmp_path / "left", tmp_path / "right"]
    for root in roots:
        root.mkdir()
    left, right = (make_repo(root) for root in roots)
    left_run, right_run = run_dir(left), run_dir(right)
    second_header = b"b\x00100000:644\x00"
    (left / "a").write_bytes(b"x")
    (left / "b").write_bytes(b"p\x00" + second_header + b"q")
    (right / "a").write_bytes(b"x\x00" + second_header + b"p")
    (right / "b").write_bytes(b"q")
    assert snapshot_digest(left, left_run) != snapshot_digest(right, right_run)


def test_implementation_snapshot_hashes_the_raw_symlink_target(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    directory = run_dir(repo)
    link = repo / "link"
    os.symlink("target//file", link)
    before = snapshot_digest(repo, directory)
    link.unlink()
    os.symlink("./target/file", link)
    assert snapshot_digest(repo, directory) != before


def test_reviewed_snapshot_accepts_exact_reviewed_head_without_interpreting_target_seal(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    assert_result(invoke(repo, directory), "pass", 0)
    assert "review_loop.seals" not in CHECKER.read_text()


def test_reviewed_snapshot_accepts_only_workflow_evidence_after_review(tmp_path: Path) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    report = directory / "final-report.md"
    report.write_text("Stage 13 report\n")
    data["stage"] = {"id": 13, "state": "complete"}
    data["next_action"] = "enter Finish before its first integration effect"
    write_ledger(directory, data)
    commit(
        repo, "record Stage 13 evidence",
        data["review"]["evidence_path"],
        (directory / "ledger.md").relative_to(repo).as_posix(),
        report.relative_to(repo).as_posix(),
    )
    assert_result(invoke(repo, directory), "pass", 0)


def test_reviewed_snapshot_uses_net_endpoint_delta_so_fully_reverted_paths_are_absent(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    transient = repo / "transient.txt"
    transient.write_text("temporary\n")
    commit(repo, "temporary change", "transient.txt")
    transient.unlink()
    commit(repo, "fully revert temporary change", "transient.txt")
    assert_result(invoke(repo, directory), "pass", 0)


def test_reviewed_snapshot_rejects_non_descendant_head(tmp_path: Path) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    git(repo, "checkout", "-q", "--detach", f"{data['review']['reviewed_commit']}^")
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("identity", ["HEAD", "abbreviated"])
def test_reviewed_snapshot_requires_a_canonical_full_reviewed_commit(
    tmp_path: Path, identity: str,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    if identity == "abbreviated":
        identity = str(data["review"]["reviewed_commit"])[:12]
    data["review"]["reviewed_commit"] = identity
    write_receipt(directory, data["review"])
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("dirty", [False, True])
def test_reviewed_snapshot_rejects_unreviewed_tracked_content(tmp_path: Path, dirty: bool) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    (repo / "src/app.py").write_text("unreviewed\n")
    if not dirty:
        commit(repo, "foreign implementation change", "src/app.py")
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_rejects_untracked_content_even_beside_the_allowed_receipt(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    (directory / "reviews" / "implementation-1.json.bak").write_text("foreign\n")
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("relative", [
    "notes.txt",
    "docs/feature-forge/runs/2026-08-25-alpha/ledger.md.bak",
    "docs/feature-forge/runs/2026-08-25-alpha/final-report.md.more",
])
def test_reviewed_snapshot_forbids_untracked_and_prefix_lookalike_paths(
    tmp_path: Path, relative: str,
) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("foreign\n")
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("committed", [False, True])
def test_reviewed_snapshot_parses_both_paths_of_a_nul_delimited_rename(
    tmp_path: Path, committed: bool,
) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    target = (directory / "final-report.md").relative_to(repo).as_posix()
    git(repo, "mv", "src/app.py", target)
    if committed:
        git(repo, "add", "-u", "--", "src")
        commit(repo, "rename implementation into workflow evidence", target)
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_parses_both_paths_of_a_nul_delimited_copy(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    target = directory / "final-report.md"
    target.write_bytes((repo / "src/app.py").read_bytes())
    commit(repo, "copy implementation into workflow evidence", target.relative_to(repo).as_posix())
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_rejects_a_final_report_before_its_owning_stage(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    (directory / "final-report.md").write_text("draft final report\n")
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_rejects_a_mode_change_hidden_by_core_filemode(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    git(repo, "config", "core.fileMode", "false")
    target = repo / "src/app.py"
    target.chmod(target.stat().st_mode | 0o111)
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_uses_shared_audit_result_classification(tmp_path: Path) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    data["review"]["open_finding_ids"] = ["F-1"]
    write_receipt(directory, data["review"], actionable_finding_ids=["F-1"])
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_treats_signal_terminated_ancestry_check_as_unverifiable(
    tmp_path: Path,
) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    real_git = shutil.which("git")
    assert real_git is not None
    binary = tmp_path / "bin"
    binary.mkdir()
    wrapper = binary / "git"
    wrapper.write_text(
        "#!/bin/sh\n"
        "if [ \"$3\" = \"merge-base\" ]; then kill -TERM $$; fi\n"
        f'exec "{real_git}" "$@"\n'
    )
    wrapper.chmod(0o755)
    observed = subprocess.run(
        [sys.executable, str(CHECKER), "reviewed-snapshot", "--repo", str(repo), "--run", str(directory)],
        text=True, capture_output=True, check=False, env={**os.environ, "PATH": str(binary)},
    )
    assert_result(observed, "unverifiable", 2)


def test_reviewed_snapshot_rejects_a_symlinked_ledger(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    ledger = directory / "ledger.md"
    target = ledger.with_name("real-ledger.md")
    ledger.rename(target)
    ledger.symlink_to(target.name)
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_reviewed_snapshot_never_uses_a_ledger_selected_report_path(tmp_path: Path) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    data["final_report_path"] = "src/app.py"
    write_ledger(directory, data)
    (repo / "src/app.py").write_text("foreign content\n")
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("field", [
    "dispatch_id", "run_ref", "target_seal", "evidence_path", "reviewed_commit",
])
def test_reviewed_snapshot_treats_missing_required_review_fields_as_unverifiable(
    tmp_path: Path, field: str,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    data["review"][field] = None
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_treats_missing_receipt_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    (repo / data["review"]["evidence_path"]).unlink()
    assert_result(invoke(repo, directory), "unverifiable", 2)


@pytest.mark.parametrize("link", ["receipt", "reviews-directory"])
def test_reviewed_snapshot_rejects_symlinked_receipt_path_components(
    tmp_path: Path, link: str,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    receipt = repo / data["review"]["evidence_path"]
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


@pytest.mark.parametrize(("kind", "state"), [
    (None, "not_started"),
    ("specification", "review_active"),
    ("plan", "changes_required"),
    ("implementation", "blocked"),
    ("specification", "pass"),
])
def test_reviewed_snapshot_reports_supported_non_implementation_pass_heads_as_fail(
    tmp_path: Path, kind: str | None, state: str,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    data["review"]["kind"] = kind
    data["review"]["state"] = state
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("review", [
    {"kind": "implementation", "state": "unknown"},
    ["implementation", "pass"],
])
def test_reviewed_snapshot_treats_malformed_or_unsupported_review_state_as_unverifiable(
    tmp_path: Path, review: object,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    data["review"] = review
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)


def test_reviewed_snapshot_rejects_frozen_identity_drift(tmp_path: Path) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    (repo / data["frozen"]["specification"]["path"]).write_text("drift\n")
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("evidence_path", [
    "docs/feature-forge/runs/2026-08-25-alpha/reviews/other.json",
    "docs/feature-forge/runs/2026-08-25-other/reviews/implementation-1.json",
    "docs/feature-forge/runs/2026-08-25-alpha/reviews-prefix/implementation-1.json",
])
def test_reviewed_snapshot_requires_the_exact_current_run_dispatch_receipt_path(
    tmp_path: Path, evidence_path: str,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    data["review"]["evidence_path"] = evidence_path
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("field", "value"), [
    ("kind", "plan"),
    ("dispatch_id", "other"),
    ("run_ref", "/other/run"),
    ("target_seal", "other-seal"),
    ("result", "changes_required"),
    ("actionable_finding_ids", ["finding-1"]),
])
def test_reviewed_snapshot_rejects_receipt_head_disagreement(
    tmp_path: Path, field: str, value: object,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    write_receipt(directory, data["review"], **{field: value})
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize("source_identity", [
    {"kind": "implementation_snapshot_sha256", "path": "src/app.py", "value": "0" * 64},
    {"kind": "implementation_snapshot_sha256", "path": None, "value": "0" * 64},
    {"kind": "candidate_sha256", "path": None, "value": "0" * 64},
])
def test_reviewed_snapshot_requires_an_exact_implementation_source_identity(
    tmp_path: Path, source_identity: dict[str, object],
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    write_receipt(directory, data["review"], source_identity=source_identity)
    assert_result(invoke(repo, directory), "fail", 1)


def test_reviewed_snapshot_rejects_an_ignored_file_added_after_review(tmp_path: Path) -> None:
    repo, directory, _ = reviewed_fixture(tmp_path)
    common_dir = Path(git(repo, "rev-parse", "--git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = repo / common_dir
    (common_dir / "info" / "exclude").write_text("ignored.cache\n")
    (repo / "ignored.cache").write_text("post-review ignored content\n")
    assert_result(invoke(repo, directory), "fail", 1)


@pytest.mark.parametrize(("status", "code"), [("pass", 0), ("fail", 1), ("unverifiable", 2)])
def test_reviewed_snapshot_contract_is_read_only_for_every_result_class(
    tmp_path: Path, status: str, code: int,
) -> None:
    repo, directory, data = reviewed_fixture(tmp_path)
    if status == "fail":
        (repo / "foreign.txt").write_text("foreign\n")
    elif status == "unverifiable":
        data["review"].pop("target_seal")
        write_ledger(directory, data)
    before = fixture_snapshot(repo)
    assert_result(invoke(repo, directory), status, code)
    assert fixture_snapshot(repo) == before
