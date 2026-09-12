"""Black-box tests for `ff-check runs`; each case targets one inventory decision."""
from __future__ import annotations

import ast
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CHECKER, check, git, head, make_primary_repo, make_repo, run_dir, write_ledger


def assert_result(result, gate: str, status: str, code: int) -> None:
    assert result.returncode == code, result.stderr
    assert result.stdout == f"FF-CHECK v1 gate={gate} status={status}\n"
    assert result.stderr.splitlines() == sorted(result.stderr.splitlines())


@pytest.mark.parametrize("error", [OSError, RuntimeError, UnicodeError, ValueError])
def test_resolve_observed_path_treats_every_path_observation_error_as_unavailable(
    monkeypatch: pytest.MonkeyPatch, error: type[Exception],
) -> None:
    """A resolver that leaks one of these errors would crash a CLI path claim."""
    checker = runpy.run_path(str(CHECKER))

    def unavailable(_self: Path, *_args: object, **_kwargs: object) -> Path:
        raise error("cannot observe path")

    monkeypatch.setattr(Path, "resolve", unavailable)
    assert checker["PATH_OBSERVATION_ERRORS"] == (OSError, RuntimeError, UnicodeError, ValueError)
    assert checker["resolve_observed_path"](Path("candidate")) is None


def test_worktrees_excludes_same_named_branches_from_another_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removing common-Git-dir filtering would make repository B collide with A."""
    parent_a, parent_b = tmp_path / "repository-a", tmp_path / "repository-b"
    parent_a.mkdir()
    parent_b.mkdir()
    repo_a, repo_b = make_repo(parent_a), make_repo(parent_b)
    checker = runpy.run_path(str(CHECKER))
    inventory = (
        f"worktree {repo_a}\0branch refs/heads/feature/alpha\0\0"
        f"worktree {repo_b}\0branch refs/heads/feature/alpha\0\0"
    ).encode()

    def combined_inventory(_repo: Path, *args: str) -> bytes | None:
        return inventory if args == ("worktree", "list", "--porcelain", "-z") else None

    monkeypatch.setitem(checker["worktrees"].__globals__, "git_bytes", combined_inventory)
    assert checker["worktrees"](repo_a) == [(str(repo_a.resolve()), "refs/heads/feature/alpha")]


def test_common_git_directory_canonicalizes_a_relative_symlink_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Comparing raw common-dir strings would split one repository into two identities."""
    repo = tmp_path / "repository"
    repo.mkdir()
    common = tmp_path / "common"
    common.mkdir()
    link = tmp_path / "common-link"
    link.symlink_to(common, target_is_directory=True)
    checker = runpy.run_path(str(CHECKER))

    def relative_common(_repo: Path, *args: str) -> str | None:
        return "../common-link" if args == ("rev-parse", "--git-common-dir") else None

    monkeypatch.setitem(checker["common_git_directory"].__globals__, "git", relative_common)
    assert checker["common_git_directory"](repo) == common.resolve()


def test_common_git_directory_treats_a_real_symlink_loop_as_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = tmp_path / "common-dir-loop"
    loop.symlink_to(loop.name)
    checker = runpy.run_path(str(CHECKER))

    def loop_common(_repo: Path, *args: str) -> str | None:
        return str(loop) if args == ("rev-parse", "--git-common-dir") else None

    monkeypatch.setitem(checker["common_git_directory"].__globals__, "git", loop_common)
    assert checker["common_git_directory"](tmp_path) is None


def test_worktrees_fails_closed_when_a_candidate_path_cannot_be_observed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Silently dropping an unobservable candidate would miss an active collision."""
    repo = make_repo(tmp_path)
    loop = tmp_path / "worktree-loop"
    loop.symlink_to(loop.name)
    checker = runpy.run_path(str(CHECKER))
    inventory = f"worktree {loop}\0branch refs/heads/feature/alpha\0\0".encode()

    def loop_inventory(_repo: Path, *args: str) -> bytes | None:
        return inventory if args == ("worktree", "list", "--porcelain", "-z") else None

    monkeypatch.setitem(checker["worktrees"].__globals__, "git_bytes", loop_inventory)
    assert checker["worktrees"](repo) is None


def test_runs_reports_an_unobservable_repository_without_a_traceback(tmp_path: Path) -> None:
    loop = tmp_path / "repository-loop"
    loop.symlink_to(loop.name)
    observed = check("runs", "--repo", str(loop), "--run-id", "alpha")
    assert_result(observed, "runs", "unverifiable", 2)
    assert observed.stderr.splitlines() == ["repository=unavailable"]
    assert "Traceback" not in observed.stdout + observed.stderr


def test_runs_keeps_an_unreadable_redirected_ledger_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A permission failure while classifying a run entry must not escape runs()."""
    repo = make_repo(tmp_path, branch="feature/other")
    external = tmp_path / "external-run"
    external.mkdir()
    write_ledger(external, head(repo))
    root = repo / "docs" / "feature-forge" / "runs"
    root.mkdir(parents=True)
    (root / "alias").symlink_to(external, target_is_directory=True)
    checker = runpy.run_path(str(CHECKER))

    def denied(_path: Path) -> bool:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "is_symlink", denied)
    observed = checker["runs"](str(repo), "alpha")
    assert observed.status == "unverifiable"
    assert observed.findings == ("ledger=docs/feature-forge/runs/alias/ledger.md:unreadable",)


def test_runs_main_treats_an_unobservable_canonical_inventory_directory_as_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed ledger-directory observation is not evidence of a collision."""
    repo = make_repo(tmp_path, branch="feature/other")
    directory = run_dir(repo)
    checker = runpy.run_path(str(CHECKER))
    original_lstat = Path.lstat

    def denied(path: Path):
        if path == directory:
            raise PermissionError("denied")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", denied)
    exit_code = checker["main"](["runs", "--repo", str(repo), "--run-id", "alpha"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == "FF-CHECK v1 gate=runs status=unverifiable\n"
    assert captured.err == "ledger=docs/feature-forge/runs/2026-08-25-alpha/ledger.md:unreadable\n"
    assert "Traceback" not in captured.out + captured.err


@pytest.mark.parametrize("failure", ["top-level", "common-dir"])
def test_runs_main_fails_closed_when_a_candidate_repository_identity_is_unobservable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failure: str,
) -> None:
    """An unknown candidate identity cannot be dropped from the collision inventory."""
    repo = tmp_path / "repository"
    repo.mkdir()
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    common = tmp_path / "common"
    common.mkdir()
    checker = runpy.run_path(str(CHECKER))
    inventory = f"worktree {candidate}\0branch refs/heads/feature/alpha\0\0".encode()

    def fake_git(observed_repo: Path, *args: str) -> str | None:
        if args == ("branch", "--list", "--format=%(refname)"):
            return ""
        if args == ("rev-parse", "--git-common-dir"):
            if failure == "common-dir" and observed_repo == candidate:
                return None
            return str(common)
        if args == ("rev-parse", "--show-toplevel"):
            return None if failure == "top-level" else str(candidate)
        return None

    def fake_git_bytes(_repo: Path, *args: str) -> bytes | None:
        return inventory if args == ("worktree", "list", "--porcelain", "-z") else None

    namespace = checker["runs"].__globals__
    monkeypatch.setitem(namespace, "repository", lambda _argument: repo)
    monkeypatch.setitem(namespace, "valid_run_id", lambda _repo, _run_id: True)
    monkeypatch.setitem(namespace, "git", fake_git)
    monkeypatch.setitem(namespace, "git_bytes", fake_git_bytes)
    exit_code = checker["main"](["runs", "--repo", str(repo), "--run-id", "alpha"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == "FF-CHECK v1 gate=runs status=unverifiable\n"
    assert captured.err == "git-inventory=unavailable\n"
    assert "Traceback" not in captured.out + captured.err


def test_runs_passes_when_no_matching_inventory_exists(tmp_path: Path) -> None:
    result = check("runs", "--repo", str(make_repo(tmp_path, branch="feature/other")), "--run-id", "alpha")
    assert_result(result, "runs", "pass", 0)


@pytest.mark.parametrize("value", [None, "automatic", "SUPERVISED", 1])
def test_runs_rejects_missing_or_unsupported_mode(tmp_path: Path, value: object) -> None:
    repo = make_repo(tmp_path)
    data = head(repo)
    if value is None:
        data.pop("mode")
    else:
        data["mode"] = value
    write_ledger(run_dir(repo), data)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_rejects_the_primary_checkout_as_a_canonical_run_worktree(tmp_path: Path) -> None:
    repo = make_primary_repo(tmp_path)
    write_ledger(run_dir(repo), head(repo))
    assert_result(
        check("runs", "--repo", str(repo), "--run-id", "alpha"),
        "runs", "fail", 1,
    )


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


def test_runs_treats_deep_json_head_as_unverifiable_without_a_traceback(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    nested = "[" * 2000 + "0" + "]" * 2000
    (run_dir(repo) / "ledger.md").write_text(
        '```json\n{"schema":"feature-forge/ledger/v1","nested":' + nested + "}\n```\n"
    )

    observed = check("runs", "--repo", str(repo), "--run-id", "alpha")

    assert_result(observed, "runs", "unverifiable", 2)
    assert "malformed-head" in observed.stderr
    assert "Traceback" not in observed.stdout + observed.stderr


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


def test_runs_treats_a_nul_in_the_ledger_worktree_as_unverifiable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    data = head(repo)
    data["worktree"] = f"{repo}\0forged"
    write_ledger(run_dir(repo), data)
    observed = check("runs", "--repo", str(repo), "--run-id", "alpha")
    assert_result(observed, "runs", "unverifiable", 2)
    assert "Traceback" not in observed.stderr


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


def test_runs_rejects_a_matching_ledger_beneath_a_noncanonical_symlink(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="feature/other")
    external = tmp_path / "external-run"
    external.mkdir()
    write_ledger(external, head(repo))
    root = repo / "docs" / "feature-forge" / "runs"
    root.mkdir(parents=True)
    (root / "alias").symlink_to(external, target_is_directory=True)
    assert_result(
        check("runs", "--repo", str(repo), "--run-id", "alpha"),
        "runs", "unverifiable", 2,
    )


def test_runs_rejects_a_symlinked_runs_root(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="feature/other")
    docs = repo / "docs" / "feature-forge"
    docs.mkdir(parents=True)
    external = tmp_path / "external-runs"
    external.mkdir()
    (docs / "runs").symlink_to(external, target_is_directory=True)
    assert_result(check("runs", "--repo", str(repo), "--run-id", "alpha"), "runs", "unverifiable", 2)


def test_runs_rejects_an_absent_runs_root_beneath_a_symlinked_ancestor(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    outside = tmp_path / "outside-docs"
    outside.mkdir()
    (repo / "docs").symlink_to(outside, target_is_directory=True)
    assert_result(
        check("runs", "--repo", str(repo), "--run-id", "beta"),
        "runs", "unverifiable", 2,
    )


def test_runs_uses_full_branch_refs_when_a_tag_has_the_same_short_name(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    directory = run_dir(repo)
    write_ledger(directory, head(repo))
    git(repo, "tag", "feature/alpha")
    assert_result(
        check("runs", "--repo", str(repo), "--run-id", "alpha"),
        "runs", "pass", 0,
    )


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


def test_runs_preserves_a_repository_path_ending_in_a_space(tmp_path: Path) -> None:
    primary = make_primary_repo(tmp_path, branch="feature/primary")
    linked = tmp_path / "linked-worktree "
    subprocess.run(
        ["git", "worktree", "add", "-qb", "feature/alpha", str(linked), "HEAD"],
        cwd=primary, check=True, capture_output=True,
    )
    write_ledger(run_dir(linked), head(linked))

    observed = check("runs", "--repo", str(linked), "--run-id", "alpha")

    assert_result(observed, "runs", "pass", 0)
    assert f"worktree={linked}\n" in observed.stderr


def test_every_git_subprocess_uses_the_hardened_argv_and_environment_policy(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    write_ledger(run_dir(repo), head(repo))
    real_git = shutil.which("git")
    assert real_git is not None
    marker = tmp_path / "unsafe-git-policy"
    binary = tmp_path / "bin"
    binary.mkdir()
    wrapper = binary / "git"
    scrubbed = [
        "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0", "GIT_CONFIG_KEY_27", "GIT_CONFIG_VALUE_27",
    ]
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        f"marker = {str(marker)!r}\n"
        f"scrubbed = {scrubbed!r}\n"
        "configs = [sys.argv[index + 1] for index, value in enumerate(sys.argv[:-1]) if value == '-c']\n"
        "unsafe = [name for name in scrubbed if name in os.environ]\n"
        "if (unsafe or os.environ.get('GIT_OPTIONAL_LOCKS') != '0'\n"
        "        or 'core.fsmonitor=false' not in configs\n"
        "        or 'core.hooksPath=/dev/null' not in configs):\n"
        "    open(marker, 'w').write(','.join(unsafe) or 'argv')\n"
        "    raise SystemExit(97)\n"
        f"os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n"
    )
    wrapper.chmod(0o755)
    hook_marker = tmp_path / "configured-program-ran"
    fsmonitor = tmp_path / "fsmonitor"
    fsmonitor.write_text(f"#!/bin/sh\nprintf ran > {str(hook_marker)!r}\nexit 1\n")
    fsmonitor.chmod(0o755)
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    post_index_change = hooks / "post-index-change"
    post_index_change.write_text(f"#!/bin/sh\nprintf ran > {str(hook_marker)!r}\n")
    post_index_change.chmod(0o755)
    git(repo, "config", "core.fsmonitor", str(fsmonitor))
    git(repo, "config", "core.hooksPath", str(hooks))
    environment = {
        **os.environ,
        "PATH": str(binary),
        **{name: "/ambient/redirect" for name in scrubbed},
    }
    environment["GIT_CONFIG_COUNT"] = "28"

    observed = subprocess.run(
        [sys.executable, str(CHECKER), "runs", "--repo", str(repo), "--run-id", "alpha"],
        text=True, capture_output=True, env=environment,
    )

    assert_result(observed, "runs", "pass", 0)
    assert not marker.exists()
    assert not hook_marker.exists()


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
