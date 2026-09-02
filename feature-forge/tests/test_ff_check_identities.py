"""Black-box tests for deterministic frozen-identity observations."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CHECKER, check, git, head, make_primary_repo, make_repo, run_dir, write_ledger


def assert_result(result: subprocess.CompletedProcess[str], status: str, code: int) -> None:
    assert result.returncode == code, result.stderr
    assert result.stdout == f"FF-CHECK v1 gate=identities status={status}\n"
    assert result.stderr.splitlines() == sorted(result.stderr.splitlines())


def identity_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    repo = make_repo(tmp_path)
    specification = "docs/superpowers/specs/2026-08-25-alpha-design.md"
    plan = "docs/superpowers/plans/2026-08-25-alpha.md"
    for path, contents in ((specification, "specification\n"), (plan, "plan\n")):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
    frozen = {
        "specification": {"path": specification, "blob": git(repo, "hash-object", "-w", specification)},
        "plan": {"path": plan, "blob": git(repo, "hash-object", "-w", plan)},
    }
    directory = run_dir(repo)
    data = head(repo, frozen=frozen)
    write_ledger(directory, data)
    return repo, directory, data


def test_identities_accepts_matching_worktree_branch_base_and_blobs(tmp_path: Path) -> None:
    repo, directory, _ = identity_fixture(tmp_path)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "pass", 0)


def test_identities_rejects_the_primary_checkout(tmp_path: Path) -> None:
    repo = make_primary_repo(tmp_path)
    specification = "docs/superpowers/specs/2026-08-25-alpha-design.md"
    target = repo / specification
    target.parent.mkdir(parents=True)
    target.write_text("specification\n")
    frozen = {
        "specification": {"path": specification, "blob": git(repo, "hash-object", "-w", specification)},
        "plan": None,
    }
    directory = run_dir(repo)
    write_ledger(directory, head(repo, frozen=frozen))
    assert_result(
        check("identities", "--repo", str(repo), "--run", str(directory)),
        "fail", 1,
    )


def test_identities_rejects_observed_branch_redirected_from_the_run_id(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    git(repo, "checkout", "-qb", "feature/other")
    data["branch"] = "feature/other"
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "fail", 1)


def test_identities_rejects_frozen_path_redirected_from_the_run_id(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["frozen"]["specification"] = {
        "path": "README.md", "blob": git(repo, "hash-object", "README.md"),
    }
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "fail", 1)


@pytest.mark.parametrize("field, value", [("worktree", "/other"), ("branch", "feature/other")])
def test_identities_rejects_wrong_worktree_or_branch(tmp_path: Path, field: str, value: str) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data[field] = value
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "fail", 1)


def test_identities_treats_unresolvable_base_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["base_identity"] = "0" * 40
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


@pytest.mark.parametrize("identity", ["HEAD", "abbreviated"])
def test_identities_rejects_noncanonical_base_identity(tmp_path: Path, identity: str) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    if identity == "abbreviated":
        identity = git(repo, "rev-parse", "HEAD")[:12]
    data["base_identity"] = identity
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "fail", 1)


def test_identities_treats_unresolvable_canonical_frozen_blob_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["frozen"]["specification"]["blob"] = "0" * len(git(repo, "rev-parse", "HEAD"))
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


@pytest.mark.parametrize("entry", ["specification", "plan"])
def test_identities_reports_each_frozen_blob_drift_as_a_path_failure(tmp_path: Path, entry: str) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    path = data["frozen"][entry]["path"]
    (repo / path).write_text("drift\n")
    result = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(result, "fail", 1)
    assert result.stderr.splitlines() == [f"path={path}"]


def test_identities_rejects_a_frozen_file_replaced_by_a_same_byte_symlink(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    relative = data["frozen"]["specification"]["path"]
    target = repo / "same-bytes.md"
    target.write_bytes((repo / relative).read_bytes())
    (repo / relative).unlink()
    (repo / relative).symlink_to(target)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


@pytest.mark.parametrize("path", ["../README.md", "/tmp/escape", "docs/../README.md", "."])
def test_identities_treats_path_escape_as_unverifiable(tmp_path: Path, path: str) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["frozen"]["specification"]["path"] = path
    write_ledger(directory, data)
    result = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(result, "unverifiable", 2)
    assert not any(line.startswith("path=") for line in result.stderr.splitlines())


def test_identities_treats_missing_frozen_file_and_pre_schema_ledger_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    (repo / data["frozen"]["plan"]["path"]).unlink()
    result = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(result, "unverifiable", 2)
    assert not any(line.startswith("path=") for line in result.stderr.splitlines())
    write_ledger(directory, {"run_id": "alpha"})
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


def test_identities_requires_a_canonical_run_directory(tmp_path: Path) -> None:
    repo, _, _ = identity_fixture(tmp_path)
    noncanonical = repo / "docs" / "feature-forge" / "runs" / "alpha"
    noncanonical.mkdir()
    write_ledger(noncanonical, head(repo))
    assert_result(check("identities", "--repo", str(repo), "--run", str(noncanonical)), "unverifiable", 2)


@pytest.mark.parametrize("run_id", ["Alpha", "alpha--beta"])
def test_identities_rejects_non_slug_dated_directory_suffix(tmp_path: Path, run_id: str) -> None:
    repo = make_repo(tmp_path)
    directory = run_dir(repo, run_id=run_id)
    write_ledger(directory, head(repo, run_id=run_id, branch=f"feature/{run_id}"))
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


def test_identities_requires_supported_head_id_to_match_dated_suffix(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["run_id"] = "other"
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


@pytest.mark.parametrize("path, link_target", [(".git/config", None), ("docs/git-metadata-link", ".git/config")])
def test_identities_rejects_git_metadata_paths_and_links(tmp_path: Path, path: str, link_target: str | None) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    if link_target is not None:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(repo / link_target)
    data["frozen"]["specification"]["path"] = path
    write_ledger(directory, data)
    result = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(result, "unverifiable", 2)
    assert not any(line.startswith("path=") for line in result.stderr.splitlines())


def test_identities_rejects_a_link_to_a_linked_worktree_git_marker(tmp_path: Path) -> None:
    primary = make_repo(tmp_path, branch="feature/primary")
    worktree = tmp_path / "linked-worktree"
    git(primary, "worktree", "add", "-qb", "feature/alpha", str(worktree), "HEAD")
    link = worktree / "docs" / "git-marker-link"
    link.parent.mkdir(parents=True)
    link.symlink_to("../.git")
    frozen = {
        "specification": {"path": "docs/git-marker-link", "blob": "0" * 40},
        "plan": None,
    }
    directory = run_dir(worktree)
    write_ledger(directory, head(worktree, frozen=frozen))
    result = check("identities", "--repo", str(worktree), "--run", str(directory))
    assert_result(result, "unverifiable", 2)
    assert not any(line.startswith("path=") for line in result.stderr.splitlines())


def test_identities_reports_git_observation_failure_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, _ = identity_fixture(tmp_path)
    failed = subprocess.run(
        [sys.executable, str(CHECKER), "identities", "--repo", str(repo), "--run", str(directory)],
        text=True, capture_output=True, env={**os.environ, "PATH": ""}, check=False,
    )
    assert_result(failed, "unverifiable", 2)


def test_identities_is_read_only(tmp_path: Path) -> None:
    repo, directory, _ = identity_fixture(tmp_path)
    ledger_before = (directory / "ledger.md").read_bytes()
    status_before = git(repo, "status", "--porcelain=v1")
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "pass", 0)
    assert (directory / "ledger.md").read_bytes() == ledger_before
    assert git(repo, "status", "--porcelain=v1") == status_before
