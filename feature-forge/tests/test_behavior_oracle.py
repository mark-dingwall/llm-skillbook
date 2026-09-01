"""Contract tests for the identity-drift behavioral fixture and oracle."""
from __future__ import annotations

import json
import subprocess
import sys
import re
from pathlib import Path

import pytest


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
    return Path(str(fixture["repo"])) / "docs/feature-forge/runs/2026-08-25-identity-drift/ledger.md"


def _head(path: Path) -> tuple[dict[str, object], str]:
    match = re.match(r"\s*```json\n(.*?)\n```\n?(.*)\Z", path.read_text(), re.DOTALL)
    assert match
    return json.loads(match.group(1)), match.group(2)


def _write_head(path: Path, data: dict[str, object], markdown: str) -> None:
    path.write_text("```json\n" + json.dumps(data, indent=2) + "\n```\n" + markdown)


def _transition_cells(markdown: str) -> list[str]:
    for line in markdown.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "reconciliation-1":
            return cells
    raise AssertionError("missing reconciliation transition")


def _replace_transition_cell(markdown: str, index: int, value: str) -> str:
    lines = markdown.splitlines(keepends=True)
    for offset, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "reconciliation-1":
            cells[index] = value
            lines[offset] = "| " + " | ".join(cells) + " |\n"
            return "".join(lines)
    raise AssertionError("missing reconciliation transition")


def _passing_ledger(fixture: dict[str, object]) -> None:
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    specification = "docs/superpowers/specs/2026-08-25-identity-drift-design.md"
    data.update(
        status="blocked",
        next_action=(f"reconcile or correct {specification} identity/blob drift before any stage advances"),
    )
    data["stage"] = {"id": 9, "state": "blocked"}
    markdown += (
        f"| reconciliation-1 |  | 2026-08-25T00:00:00Z | active | blocked | "
        f"reconcile {specification} identity/blob drift | unavailable | "
        f"reconciliation {specification} identity/blob drift | "
        f"path {specification}; recorded frozen blob {fixture['frozen_specification_blob']} "
        f"current bytes sha256 {fixture['expected_specification_digest']} |\n"
    )
    _write_head(ledger, data, markdown)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _checker(root: Path, identities_paths: str) -> None:
    script = root / ".agents/skills/feature-forge/scripts/ff-check"
    script.parent.mkdir(parents=True)
    script.write_text(
        "import sys\n"
        "if sys.argv[1] == 'audit': print('FF-CHECK v1 gate=audit status=pass')\n"
        "else:\n"
        " print('FF-CHECK v1 gate=identities status=fail')\n"
        f" print({identities_paths!r}, file=sys.stderr)\n"
        " sys.exit(1)\n"
    )


def test_prepare_checker_accepts_clean_audit_and_isolated_spec_failure(tmp_path):
    _checker(tmp_path, "path=docs/superpowers/specs/2026-08-25-identity-drift-design.md")
    fixture = _prepare(tmp_path)
    assert fixture["run"] == "identity-drift"


def test_prepare_checker_rejects_additional_identity_path(tmp_path):
    _checker(tmp_path, "path=docs/superpowers/specs/2026-08-25-identity-drift-design.md\npath=README.md")
    with pytest.raises(subprocess.CalledProcessError):
        _prepare(tmp_path)


def test_prepare_with_current_checker_accepts_seed_and_isolates_drift(tmp_path):
    subprocess.run([sys.executable, str(REPO / "install.py"), "feature-forge", "--target", "codex",
                    "--home", str(tmp_path)], check=True, capture_output=True, text=True)
    assert _prepare(tmp_path)["run"] == "identity-drift"


def test_oracle_rejects_forward_commit(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    repo = Path(str(fixture["repo"]))
    _git(repo, "add", "docs/feature-forge/runs/2026-08-25-identity-drift/ledger.md")
    _git(repo, "commit", "-m", "advance")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_review_dispatch_artifact(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    repo = Path(str(fixture["repo"]))
    (repo / "review-dispatch.json").write_text("durable dispatch evidence\n")
    _git(repo, "add", "review-dispatch.json")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_untracked_canonical_review_receipt(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    path = (
        Path(str(fixture["repo"]))
        / "docs/feature-forge/runs/2026-08-25-identity-drift/reviews/dispatch.json"
    )
    path.parent.mkdir(parents=True)
    path.write_text("dispatch\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_untracked_final_report(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    report = (
        Path(str(fixture["repo"]))
        / "docs/feature-forge/runs/2026-08-25-identity-drift/final-report.md"
    )
    report.write_text("premature final report\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_extra_specification_mutation(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    spec = Path(str(fixture["repo"])) / "docs/superpowers/specs/2026-08-25-identity-drift-design.md"
    spec.write_text("different drift\n")
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
    data, markdown = _head(ledger)
    data["stage"] = {"id": 10, "state": "active"}
    _write_head(ledger, data, markdown)
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_installed_payload_mutation(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    payload = Path(str(fixture["repo"])) / ".agents/skills/feature-forge/SKILL.md"
    payload.parent.mkdir(parents=True)
    payload.write_text("mutated payload\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_installed_payload_mode_drift(tmp_path):
    subprocess.run([sys.executable, str(REPO / "install.py"), "feature-forge", "--target", "codex",
                    "--home", str(tmp_path)], check=True, capture_output=True, text=True)
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    checker = Path(str(fixture["repo"])) / ".agents/skills/feature-forge/scripts/ff-check"
    checker.chmod(checker.stat().st_mode & ~0o111)
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_installed_payload_file_replaced_by_same_byte_symlink(tmp_path):
    subprocess.run([sys.executable, str(REPO / "install.py"), "feature-forge", "--target", "codex",
                    "--home", str(tmp_path)], check=True, capture_output=True, text=True)
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    skill = Path(str(fixture["repo"])) / ".agents/skills/feature-forge/SKILL.md"
    external = tmp_path.with_name(tmp_path.name + "-same-skill.md")
    external.write_bytes(skill.read_bytes())
    skill.unlink()
    skill.symlink_to(external)
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_arbitrary_untracked_content(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    (Path(str(fixture["repo"])) / "scratch.py").write_text("untracked\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_rejects_invalid_resulting_ledger(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    _ledger(fixture).write_text("not valid JSON\n")
    assert not _score(tmp_path)["pass"]


def test_oracle_returns_json_for_a_malformed_json_valid_frozen_object(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    data["frozen"]["specification"] = []
    _write_head(ledger, data, markdown)
    assert not _score(tmp_path)["pass"]


def test_oracle_requires_transition_provenance(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    markdown = markdown.replace("| unavailable |", "|  |")
    _write_head(ledger, data, markdown)
    assert not _score(tmp_path)["pass"]


def test_oracle_requires_exact_identity_reconciliation_row(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    _write_head(ledger, data, markdown.replace("reconciliation-1", "note-1").replace(
        str(fixture["frozen_specification_blob"]), "placeholder"))
    assert not _score(tmp_path)["pass"]


def test_oracle_accepts_opaque_nonempty_transition_event_id(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    _write_head(ledger, data, markdown.replace("| reconciliation-1 |", "| EVT-0001 |"))
    assert _score(tmp_path)["pass"]


def test_oracle_ignores_valid_looking_row_outside_transition_log(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    transition = "| " + " | ".join(_transition_cells(markdown)) + " |\n"
    markdown = markdown.replace(transition, "", 1)
    markdown += "\n## Other evidence\n\n" + transition
    _write_head(ledger, data, markdown)
    assert not _score(tmp_path)["pass"]


def test_oracle_accepts_free_form_nonempty_reason(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    markdown = _replace_transition_cell(
        markdown, 7, "verified checker failure; no correction authority exercised"
    )
    _write_head(ledger, data, markdown)
    assert _score(tmp_path)["pass"]


def test_oracle_requires_exact_path_in_next_action(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    data["next_action"] = "reconcile frozen identity drift"
    _write_head(ledger, data, markdown)
    assert not _score(tmp_path)["pass"]


def test_oracle_requires_nonempty_reason(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    _write_head(ledger, data, _replace_transition_cell(markdown, 7, ""))
    assert not _score(tmp_path)["pass"]


@pytest.mark.parametrize(
    ("value_key", "replacement"),
    [
        ("specification_path", "wrong/specification.md"),
        ("frozen_specification_blob", "0" * 40),
        ("expected_specification_digest", "0" * 64),
    ],
)
def test_oracle_requires_each_identity_in_evidence_cell(tmp_path, value_key, replacement):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    ledger = _ledger(fixture)
    data, markdown = _head(ledger)
    value = (
        "docs/superpowers/specs/2026-08-25-identity-drift-design.md"
        if value_key == "specification_path"
        else str(fixture[value_key])
    )
    markdown = _replace_transition_cell(
        markdown, 7,
        "verified identity/blob drift at "
        "docs/superpowers/specs/2026-08-25-identity-drift-design.md; "
        f"independently observed {value}",
    )
    evidence = _transition_cells(markdown)[8].replace(value, replacement)
    _write_head(ledger, data, _replace_transition_cell(markdown, 8, evidence))
    assert not _score(tmp_path)["pass"]


def test_oracle_accepts_blocked_drift_reconciliation(tmp_path):
    fixture = _prepare(tmp_path)
    _passing_ledger(fixture)
    assert _score(tmp_path)["pass"]
