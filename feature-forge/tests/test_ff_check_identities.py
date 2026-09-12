"""Black-box tests for deterministic frozen-identity observations."""
from __future__ import annotations

import os
import runpy
import shutil
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
    git(repo, "add", specification, plan)
    git(repo, "commit", "-qm", "freeze specification and plan")
    frozen = {
        "specification": {"path": specification, "blob": git(repo, "rev-parse", f"HEAD:{specification}")},
        "plan": {"path": plan, "blob": git(repo, "rev-parse", f"HEAD:{plan}")},
    }
    directory = run_dir(repo)
    data = head(repo, frozen=frozen)
    write_ledger(directory, data)
    return repo, directory, data


def test_identities_accepts_matching_worktree_branch_base_and_blobs(tmp_path: Path) -> None:
    repo, directory, _ = identity_fixture(tmp_path)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "pass", 0)


def test_canonical_run_observation_keeps_a_canonical_lstat_failure_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing an unobservable directory with a noncanonical claim hides host failure."""
    repo, directory, _ = identity_fixture(tmp_path)
    checker = runpy.run_path(str(CHECKER))
    original_lstat = Path.lstat

    def denied(path: Path):
        if path == directory:
            raise PermissionError("denied")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", denied)
    assert checker["canonical_run_observation"](repo, str(directory)) == (None, "unavailable")


def test_canonical_run_observation_rejects_a_redirected_runs_root(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    root = repo / "docs" / "feature-forge"
    root.mkdir(parents=True)
    external = tmp_path / "external-runs"
    external.mkdir()
    directory = external / "2026-08-25-alpha"
    directory.mkdir()
    (root / "runs").symlink_to(external, target_is_directory=True)
    checker = runpy.run_path(str(CHECKER))
    assert checker["canonical_run_observation"](repo, str(root / "runs" / directory.name)) == (
        None, "noncanonical",
    )


def test_identities_fails_for_a_missing_wrong_frozen_path_before_observation(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["frozen"]["specification"]["path"] = "missing-wrong-path.md"
    write_ledger(directory, data)
    observed = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(observed, "fail", 1)
    assert observed.stderr.splitlines() == ["frozen=specification:wrong-path"]


def test_identities_treats_a_non_string_frozen_path_as_unsupported(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["frozen"]["specification"]["path"] = 17
    write_ledger(directory, data)
    observed = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(observed, "unverifiable", 2)
    assert observed.stderr.splitlines() == ["frozen=specification:unsupported"]


@pytest.mark.parametrize("gate", ["identities", "audit", "runs"])
@pytest.mark.parametrize("ancestry", ["unrelated", "signalled"])
def test_base_ancestry_is_required_by_every_head_consumer(
    tmp_path: Path, gate: str, ancestry: str,
) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    environment = dict(os.environ)
    if ancestry == "unrelated":
        tree = git(repo, "rev-parse", "HEAD^{tree}")
        data["base_identity"] = subprocess.run(
            ["git", "commit-tree", tree], cwd=repo, input="unrelated root\n",
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        assert git(repo, "rev-parse", "--verify", f"{data['base_identity']}^{{commit}}") == data["base_identity"]
        status, code, finding = "fail", 1, "base-identity=not-ancestor"
    else:
        real_git = shutil.which("git")
        assert real_git is not None
        binary = tmp_path / "bin"
        binary.mkdir()
        wrapper = binary / "git"
        wrapper.write_text(
            "#!/bin/sh\n"
            'case " $* " in *" merge-base --is-ancestor "*) kill -TERM "$$";; esac\n'
            f'exec "{real_git}" "$@"\n'
        )
        wrapper.chmod(0o755)
        environment["PATH"] = str(binary)
        status, code, finding = "unverifiable", 2, "base-identity=ancestry-unavailable"
    write_ledger(directory, data)
    target = ["--run-id", "alpha"] if gate == "runs" else ["--run", str(directory)]
    observed = subprocess.run(
        [sys.executable, str(CHECKER), gate, "--repo", str(repo), *target],
        text=True, capture_output=True, env=environment,
    )
    assert observed.returncode == code, observed.stderr
    assert observed.stdout == f"FF-CHECK v1 gate={gate} status={status}\n"
    expected = [finding] if gate != "runs" else [
        "branch=feature/alpha",
        f"ledger=docs/feature-forge/runs/2026-08-25-alpha/ledger.md:{finding}",
        f"worktree={repo}",
    ]
    assert observed.stderr.splitlines() == expected


@pytest.mark.parametrize("value", [None, "automatic", "SUPERVISED", 1])
def test_identities_rejects_missing_or_unsupported_mode(tmp_path: Path, value: object) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    if value is None:
        data.pop("mode")
    else:
        data["mode"] = value
    write_ledger(directory, data)
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


def test_identities_uses_full_branch_ref_when_a_tag_has_the_same_short_name(tmp_path: Path) -> None:
    repo, directory, _ = identity_fixture(tmp_path)
    git(repo, "tag", "feature/alpha")
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "pass", 0)


@pytest.mark.parametrize("attribute", [
    "filter=demo",
    "text",
    "eol=lf",
    "ident",
    "working-tree-encoding=UTF-16",
])
def test_identities_rejects_transforming_attributes_before_hashing(
    tmp_path: Path, attribute: str,
) -> None:
    repo, directory, _ = identity_fixture(tmp_path)
    marker = tmp_path / "filter-ran"
    conversion = tmp_path / "conversion-ran"
    specification = "docs/superpowers/specs/2026-08-25-alpha-design.md"
    info_attributes = Path(git(repo, "rev-parse", "--git-path", "info/attributes"))
    if not info_attributes.is_absolute():
        info_attributes = repo / info_attributes
    info_attributes.parent.mkdir(parents=True, exist_ok=True)
    info_attributes.write_text(f"{specification} {attribute}\n")
    git(repo, "config", "filter.demo.clean", f': > "{marker}"; exit 1')
    real_git = shutil.which("git")
    assert real_git is not None
    binary = tmp_path / "bin"
    binary.mkdir()
    wrapper = binary / "git"
    wrapper.write_text(
        "#!/bin/sh\n"
        "for arg in \"$@\"; do\n"
        f'  case "$arg" in hash-object|status|checkout-index) : > "{conversion}"; exit 97;; esac\n'
        "done\n"
        f'exec "{real_git}" "$@"\n'
    )
    wrapper.chmod(0o755)
    environment = {**os.environ, "PATH": str(binary)}
    observed = subprocess.run(
        [sys.executable, str(CHECKER), "identities", "--repo", str(repo), "--run", str(directory)],
        text=True, capture_output=True, env=environment,
    )
    assert_result(observed, "unverifiable", 2)
    assert observed.stderr.splitlines() == ["transformations=unsupported"]
    assert not conversion.exists()
    assert not marker.exists()


def test_identities_rejects_builtin_eol_normalization_for_frozen_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / ".gitattributes").write_text("*.md text eol=lf\n")
    paths = {
        "specification": "docs/superpowers/specs/2026-08-25-alpha-design.md",
        "plan": "docs/superpowers/plans/2026-08-25-alpha.md",
    }
    frozen = {}
    for name, relative in paths.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((name + "\r\n").encode())
        frozen[name] = {
            "path": relative,
            "blob": git(repo, "hash-object", "-w", f"--path={relative}", "--", relative),
        }
    git(repo, "add", ".gitattributes", *paths.values())
    git(repo, "commit", "-qm", "freeze normalized specification and plan")
    directory = run_dir(repo)
    write_ledger(directory, head(repo, frozen=frozen))
    observed = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(observed, "unverifiable", 2)
    assert observed.stderr.splitlines() == ["transformations=unsupported"]


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


@pytest.mark.parametrize("source", ["dangling", "staged-only"])
def test_identities_requires_each_frozen_blob_at_its_canonical_head_path(
    tmp_path: Path, source: str,
) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    relative = data["frozen"]["specification"]["path"]
    (repo / relative).write_text(f"{source}\n")
    if source == "staged-only":
        git(repo, "add", relative)
        blob = git(repo, "rev-parse", f":{relative}")
    else:
        blob = git(repo, "hash-object", "-w", relative)
    data["frozen"]["specification"]["blob"] = blob
    write_ledger(directory, data)

    observed = check("identities", "--repo", str(repo), "--run", str(directory))

    assert_result(observed, "fail", 1)
    assert observed.stderr.splitlines() == ["frozen=specification:not-at-head"]


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
def test_identities_fails_for_a_ledger_frozen_path_escape(tmp_path: Path, path: str) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    data["frozen"]["specification"]["path"] = path
    write_ledger(directory, data)
    result = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(result, "fail", 1)
    assert result.stderr.splitlines() == ["frozen=specification:wrong-path"]


def test_identities_treats_missing_frozen_file_and_pre_schema_ledger_as_unverifiable(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    (repo / data["frozen"]["plan"]["path"]).unlink()
    result = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(result, "unverifiable", 2)
    assert not any(line.startswith("path=") for line in result.stderr.splitlines())
    write_ledger(directory, {"run_id": "alpha"})
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "unverifiable", 2)


def test_identities_reports_an_unobservable_frozen_path_without_a_traceback(tmp_path: Path) -> None:
    repo, directory, data = identity_fixture(tmp_path)
    target = repo / data["frozen"]["specification"]["path"]
    target.unlink()
    target.symlink_to(target.name)
    observed = check("identities", "--repo", str(repo), "--run", str(directory))
    assert_result(observed, "unverifiable", 2)
    assert observed.stderr.splitlines() == ["frozen=specification:unavailable"]
    assert "Traceback" not in observed.stdout + observed.stderr


def test_identities_requires_a_canonical_run_directory(tmp_path: Path) -> None:
    repo, _, _ = identity_fixture(tmp_path)
    noncanonical = repo / "docs" / "feature-forge" / "runs" / "alpha"
    noncanonical.mkdir()
    write_ledger(noncanonical, head(repo))
    assert_result(check("identities", "--repo", str(repo), "--run", str(noncanonical)), "fail", 1)


def test_identities_reports_an_unobservable_canonical_run_without_a_traceback(tmp_path: Path) -> None:
    repo, _, _ = identity_fixture(tmp_path)
    loop = repo / "docs" / "feature-forge" / "runs" / "2026-08-26-alpha"
    loop.symlink_to(loop.name)
    observed = check("identities", "--repo", str(repo), "--run", str(loop))
    assert_result(observed, "unverifiable", 2)
    assert observed.stderr.splitlines() == ["run=unavailable"]
    assert "Traceback" not in observed.stdout + observed.stderr


@pytest.mark.parametrize("run_id", ["Alpha", "alpha--beta"])
def test_identities_rejects_non_slug_dated_directory_suffix(tmp_path: Path, run_id: str) -> None:
    repo = make_repo(tmp_path)
    directory = run_dir(repo, run_id=run_id)
    write_ledger(directory, head(repo, run_id=run_id, branch=f"feature/{run_id}"))
    assert_result(check("identities", "--repo", str(repo), "--run", str(directory)), "fail", 1)


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
    assert_result(result, "fail", 1)
    assert result.stderr.splitlines() == ["frozen=specification:wrong-path"]


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
    assert_result(result, "fail", 1)
    assert result.stderr.splitlines() == ["frozen=specification:wrong-path"]


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
