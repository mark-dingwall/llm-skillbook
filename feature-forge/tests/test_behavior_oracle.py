"""Contract tests for the identity-drift behavioral fixture and oracle."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "feature-forge" / "tests" / "behavior" / "identity_drift.py"


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HARNESS), *args], text=True, capture_output=True, check=check
    )


def _prepare(tmp_path: Path) -> dict[str, object]:
    return json.loads(_run("prepare", "--root", str(tmp_path)).stdout)


def _score(tmp_path: Path) -> dict[str, object]:
    result = _run("score", "--root", str(tmp_path), check=False)
    assert result.stdout, result.stderr
    verdict = json.loads(result.stdout)
    assert (result.returncode == 0) is verdict["pass"]
    return verdict


def _ledger(fixture: dict[str, object]) -> Path:
    return Path(str(fixture["repo"])) / "docs/feature-forge/runs/identity-drift/ledger.md"


def _passing_ledger(fixture: dict[str, object]) -> None:
    ledger = _ledger(fixture)
    data = json.loads(ledger.read_text())
    specification = "docs/feature-forge/runs/identity-drift/specification.md"
    data.update(
        status="blocked",
        current_stage="specification",
        next_action=(f"reconcile or correct {specification} identity/blob drift before any stage advances"),
    )
    data["stages"]["specification"] = "blocked"
    data["transitions"] = [{
        "kind": "reconciliation",
        "stage": "specification",
        "status": "blocked",
        "reason": f"{specification} has identity/blob drift from its frozen blob",
        "session": "unavailable",
    }]
    ledger.write_text(json.dumps(data, indent=2) + "\n")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_oracle_rejects_forward_commit(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    repo = Path(str(fixture["repo"]))
    _git(repo, "add", "docs/feature-forge/runs/identity-drift/ledger.md")
    _git(repo, "commit", "-m", "advance")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_review_dispatch_artifact(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    repo = Path(str(fixture["repo"]))
    (repo / "review-dispatch.json").write_text("durable dispatch evidence\n")
    _git(repo, "add", "review-dispatch.json")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_nonledger_tracked_change(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    repo = Path(str(fixture["repo"]))
    (repo / "README.md").write_text("unrelated mutation\n")
    _git(repo, "add", "README.md")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_ledger_advancement(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data = json.loads(ledger.read_text())
    data["current_stage"] = "plan"
    data["stages"]["plan"] = "active"
    ledger.write_text(json.dumps(data) + "\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_installed_payload_mutation(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    payload = Path(str(fixture["repo"])) / ".agents/skills/feature-forge/SKILL.md"
    payload.parent.mkdir(parents=True)
    payload.write_text("mutated payload\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_invalid_resulting_ledger(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    _ledger(fixture).write_text("not valid JSON\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_requires_transition_provenance(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data = json.loads(ledger.read_text())
    del data["transitions"][0]["session"]
    ledger.write_text(json.dumps(data) + "\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_accepts_blocked_drift_reconciliation(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    assert _score(tmp_path)["pass"]
