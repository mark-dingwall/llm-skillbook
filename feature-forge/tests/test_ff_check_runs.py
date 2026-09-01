"""Black-box tests for `ff-check runs`; each case targets one inventory decision."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CHECKER, check, head, make_repo, run_dir, write_ledger


def assert_result(result, gate: str, status: str, code: int) -> None:
    assert result.returncode == code, result.stderr
    assert result.stdout == f"FF-CHECK v1 gate={gate} status={status}\n"
    assert result.stderr.splitlines() == sorted(result.stderr.splitlines())


def test_runs_passes_when_no_matching_inventory_exists(tmp_path: Path) -> None:
    result = check("runs", "--repo", str(make_repo(tmp_path, branch="feature/other")), "--run-id", "alpha")
    assert_result(result, "runs", "pass", 0)


def test_runs_accepts_one_matching_active_ledger_branch_and_worktree(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), head(repo))
    result = check("runs", "--repo", str(repo), "--run-id", "alpha")
    assert_result(result, "runs", "pass", 0)
    assert result.stderr.splitlines() == [
        f"branch=feature/alpha", f"ledger=docs/feature-forge/runs/2026-08-25-alpha/ledger.md",
        f"worktree={repo}",
    ]


def test_runs_accepts_blocked_ledger(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), head(repo, status="blocked"))
    result = check("runs", "--repo", str(repo), "--run-id", "alpha")
    assert_result(result, "runs", "pass", 0)


@pytest.mark.parametrize("defect", [
    "unknown-head-key", "missing-stage", "malformed-stage", "malformed-frozen", "malformed-review",
])
def test_runs_treats_exact_v1_head_shape_defects_as_unverifiable(
    tmp_path: Path, defect: str,
) -> None:
    repo = make_repo(tmp_path)
    data = head(repo)
    if defect == "unknown-head-key":
        data["unexpected"] = True
    elif defect == "missing-stage":
        del data["stage"]
    elif defect == "malformed-stage":
        data["stage"] = {"id": 1, "state": "active", "extra": True}
    elif defect == "malformed-frozen":
        data["frozen"] = {"specification": None}
    else:
        data["review"] = {"state": "not_started"}
    write_ledger(run_dir(repo), data)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_rejects_a_structurally_valid_but_inconsistent_current_head(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    data = head(repo)
    data["review"]["kind"] = "specification"
    data["review"]["state"] = "pass"
    write_ledger(run_dir(repo), data)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


def test_runs_rejects_a_noncanonical_base_ref_in_a_resumable_head(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), head(repo, base_identity="HEAD"))
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


@pytest.mark.parametrize("run_id", ["Alpha", "alpha--beta", "-alpha", "alpha-", "a/b", ""])
def test_runs_rejects_invalid_slug_or_feature_ref(tmp_path: Path, run_id: str) -> None:
    arguments = ["runs", "--repo", str(make_repo(tmp_path))]
    arguments.extend([f"--run-id={run_id}"] if run_id.startswith("-") else ["--run-id", run_id])
    result = check(*arguments)
    assert_result(result, "runs", "fail", 1)


def test_runs_rejects_completed_collision(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), head(repo, status="complete"))
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


def test_runs_rejects_multiple_matching_nonterminal_ledgers(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo, date="2026-08-25"), head(repo))
    write_ledger(run_dir(repo, date="2026-08-26"), head(repo, status="blocked"))
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


@pytest.mark.parametrize("field, value", [("branch", "feature/other"), ("worktree", "/missing/worktree")])
def test_runs_rejects_unmatched_recorded_branch_or_worktree(tmp_path: Path, field: str, value: str) -> None:
    repo = make_repo(tmp_path)
    kwargs = {field: value}
    write_ledger(run_dir(repo), head(repo, **kwargs))
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


def test_runs_rejects_an_orphan_matching_branch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="feature/other")
    subprocess.run(["git", "branch", "feature/alpha"], cwd=repo, check=True)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


def test_runs_treats_missing_or_unsupported_canonical_ledger_as_unverifiable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    run_dir(repo)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)
    write_ledger(run_dir(repo), {"schema": "unknown"})
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_treats_missing_json_head_as_unverifiable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), "old Markdown ledger", fenced=False)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_treats_malformed_json_head_as_unverifiable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (run_dir(repo) / "ledger.md").write_text("```json\n{not json}\n```\n")
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_treats_pre_schema_head_as_unverifiable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), {"run_id": "alpha"})
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_treats_nonregular_ledger_as_unreadable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (run_dir(repo) / "ledger.md").mkdir()
    result = check("runs", "--repo", str(repo), "--run-id", "alpha")
    assert_result(result, "runs", "unverifiable", 2)
    assert any(line.endswith(":unreadable") for line in result.stderr.splitlines())


@pytest.mark.parametrize("field, value", [("run_id", 42), ("worktree", "relative/worktree")])
def test_runs_treats_malformed_identity_fields_as_unverifiable(tmp_path: Path, field: str, value: object) -> None:
    repo = make_repo(tmp_path)
    data = head(repo)
    data[field] = value
    write_ledger(run_dir(repo), data)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_rejects_canonical_directory_with_a_different_supported_head(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), head(repo, run_id="other", branch="feature/other"))
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


@pytest.mark.parametrize("directory", ["2026-02-30-alpha", "prefix-alpha", "alpha"])
def test_runs_rejects_calendar_invalid_and_noncanonical_matching_locations(tmp_path: Path, directory: str) -> None:
    repo = make_repo(tmp_path)
    path = repo / "docs" / "feature-forge" / "runs" / directory
    path.mkdir(parents=True)
    write_ledger(path, head(repo))
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


def test_runs_rejects_unicode_digits_in_a_dated_identity(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    path = repo / "docs" / "feature-forge" / "runs" / "２０２６-０８-２５-alpha"
    path.mkdir(parents=True)
    write_ledger(path, head(repo))
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


@pytest.mark.parametrize("entry_kind", ["file", "broken-symlink"])
def test_runs_treats_an_occupied_canonical_non_directory_as_a_collision(
    tmp_path: Path, entry_kind: str,
) -> None:
    repo = make_repo(tmp_path, branch="feature/other")
    root = repo / "docs" / "feature-forge" / "runs"
    root.mkdir(parents=True)
    occupied = root / "2026-08-25-alpha"
    if entry_kind == "file":
        occupied.write_text("occupied\n")
    else:
        occupied.symlink_to("missing")
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "fail", 1)


def test_runs_rejects_a_symlinked_canonical_ledger(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    directory = run_dir(repo)
    ledger = write_ledger(directory, head(repo))
    external = tmp_path / "external-ledger.md"
    ledger.rename(external)
    ledger.symlink_to(external)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_rejects_a_symlinked_runs_root(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="feature/other")
    docs = repo / "docs" / "feature-forge"
    docs.mkdir(parents=True)
    external = tmp_path / "external-runs"
    external.mkdir()
    (docs / "runs").symlink_to(external, target_is_directory=True)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_parses_newline_worktree_paths_without_truncation(tmp_path: Path) -> None:
    primary = make_repo(tmp_path, branch="feature/primary")
    linked = tmp_path / "linked\nworktree"
    subprocess.run(
        ["git", "worktree", "add", "-qb", "feature/alpha", str(linked), "HEAD"],
        cwd=primary, check=True, capture_output=True,
    )
    write_ledger(run_dir(linked), head(linked))
    observed = check("runs", "--repo", str(linked), "--run-id", "alpha")
    assert observed.returncode == 0
    assert observed.stdout == "FF-CHECK v1 gate=runs status=pass\n"
    assert f"worktree={linked}\n" in observed.stderr


def test_runs_does_not_parse_a_head_shaped_line_inside_a_worktree_path(tmp_path: Path) -> None:
    primary = make_repo(tmp_path, branch="feature/primary")
    forged_head = "a" * 40
    linked = tmp_path / f"linked\nHEAD {forged_head}"
    subprocess.run(
        ["git", "worktree", "add", "-qb", "feature/alpha", str(linked), "HEAD"],
        cwd=primary, check=True, capture_output=True,
    )
    write_ledger(run_dir(linked), head(linked))
    observed = check("runs", "--repo", str(linked), "--run-id", "alpha")
    assert observed.returncode == 0
    assert observed.stdout == "FF-CHECK v1 gate=runs status=pass\n"
    assert f"worktree={linked}\n" in observed.stderr


def test_runs_fails_closed_when_git_output_is_not_utf8(tmp_path: Path) -> None:
    raw_root = os.fsencode(tmp_path) + b"/repo-\xff"
    os.mkdir(raw_root)
    subprocess.run([b"git", b"init", b"-q", raw_root], check=True)
    repo = os.fsdecode(raw_root)
    observed = check("runs", "--repo", repo, "--run-id", "alpha")
    assert_result(observed, "runs", "unverifiable", 2)


def test_runs_requires_exact_directory_id_not_suffix(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="feature/not-alpha")
    write_ledger(run_dir(repo, run_id="not-alpha"), head(repo, run_id="not-alpha", branch="feature/not-alpha"))
    result = check("runs", "--repo", str(repo), "--run-id", "alpha")
    assert_result(result, "runs", "pass", 0)


def test_runs_is_read_only_and_cli_usage_is_nonoperational(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    ledger = write_ledger(run_dir(repo), head(repo))
    before = (ledger.read_bytes(), subprocess.run(["git", "status", "--porcelain=v1"], cwd=repo,
              text=True, capture_output=True, check=True).stdout)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "pass", 0)
    after = (ledger.read_bytes(), subprocess.run(["git", "status", "--porcelain=v1"], cwd=repo,
             text=True, capture_output=True, check=True).stdout)
    assert after == before
    unknown = check("unknown", "--repo", str(repo))
    assert unknown.returncode == 2 and not unknown.stdout.startswith("FF-CHECK")
    bad_argument = check("runs", "--repo", str(repo), "--run-id", "alpha", "--unknown")
    assert bad_argument.returncode == 2 and not bad_argument.stdout.startswith("FF-CHECK")
    help_result = check("--help")
    assert help_result.returncode == 0 and not help_result.stdout.startswith("FF-CHECK")


def test_checker_has_only_stdlib_direct_imports_and_no_dynamic_imports() -> None:
    tree = ast.parse(CHECKER.read_text())
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= sys.stdlib_module_names
    assert "import_module" not in CHECKER.read_text()
