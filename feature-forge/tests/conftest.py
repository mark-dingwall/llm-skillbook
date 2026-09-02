"""Shared black-box fixtures for the Feature Forge checker."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
CHECKER = REPO / "feature-forge" / "scripts" / "ff-check"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, check=True,
                          capture_output=True).stdout.strip()


def make_primary_repo(tmp_path: Path, branch: str = "feature/alpha") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Feature Forge tests")
    git(repo, "config", "user.email", "tests@example.invalid")
    (repo / "README.md").write_text("fixture\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "seed")
    git(repo, "checkout", "-qb", branch)
    return repo


def make_repo(tmp_path: Path, branch: str = "feature/alpha") -> Path:
    primary = make_primary_repo(tmp_path, "main")
    worktree = tmp_path / "worktree"
    git(primary, "worktree", "add", "-qb", branch, str(worktree), "HEAD")
    return worktree


def head(repo: Path, run_id: str = "alpha", *, status: str = "active",
         worktree: str | None = None, branch: str | None = None,
         base_identity: str | None = None, frozen: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "schema": "feature-forge/ledger/v1", "run_id": run_id, "status": status,
        "worktree": worktree or str(repo), "branch": branch or f"feature/{run_id}",
        "base_identity": base_identity or git(repo, "rev-parse", "HEAD"),
        "stage": {"id": 1, "state": "active" if status != "complete" else "complete"},
        "next_action": None if status == "complete" else "continue",
        "frozen": frozen or {"specification": None, "plan": None},
        "review": {"kind": None, "state": "not_started", "round": 0,
                   "root_identity": None, "dispatch_id": None, "run_ref": None,
                   "target_seal": None, "evidence_path": None, "reviewed_commit": None,
                   "previous_open_finding_ids": [], "open_finding_ids": []},
    }


def run_dir(repo: Path, run_id: str = "alpha", date: str = "2026-08-25") -> Path:
    path = repo / "docs" / "feature-forge" / "runs" / f"{date}-{run_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_ledger(directory: Path, data: object, *, fenced: bool = True) -> Path:
    path = directory / "ledger.md"
    encoded = json.dumps(data, indent=2)
    path.write_text(f"```json\n{encoded}\n```\n" if fenced else encoded + "\n")
    return path


def check(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CHECKER), *args], text=True, capture_output=True)
