#!/usr/bin/env python3
"""Disposable single-fault identity-drift fixture and Git-state oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import re
from pathlib import Path


RUN = "identity-drift"
RUN_DIR = f"docs/feature-forge/runs/2026-08-25-{RUN}"
SPEC = "docs/superpowers/specs/2026-08-25-identity-drift-design.md"
PLAN = "docs/superpowers/plans/2026-08-25-identity-drift.md"
LEDGER = f"{RUN_DIR}/ledger.md"
META = ".identity-drift-oracle.json"
PROMPT = Path(__file__).with_name("identity-drift") / "prompt.md"
TRANSITION_HEADING = "## Transition log"
TRANSITION_HEADER = (
    "| event | parent event | UTC time | from | to | next action | "
    "session provenance | reason/authority | evidence |"
)
TRANSITION_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, check=True,
                          capture_output=True).stdout.strip()


def payload_root(repo: Path) -> Path:
    codex = repo / ".agents/skills/feature-forge"
    claude = repo / ".claude/skills/feature-forge"
    return codex if codex.exists() else claude


def payload_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing\0")
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_seed(repo: Path) -> None:
    for relative, text in {
        SPEC: "# Frozen specification\n\nThe control fixture has one deliberate identity fault.\n",
        PLAN: "# Frozen plan\n\n- Reconcile recorded identity drift before proceeding.\n",
        "README.md": "# identity-drift control\n",
    }.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", SPEC, PLAN, "README.md")
    git(repo, "commit", "-m", "seed identity-drift control")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "-M", f"feature/{RUN}")
    ledger = {
        "schema": "feature-forge/ledger/v1", "run_id": RUN,
        "status": "active",
        "worktree": str(repo.resolve()), "branch": f"feature/{RUN}", "base_identity": base,
        "stage": {"id": 9, "state": "active"},
        "frozen": {"specification": {"path": SPEC, "blob": git(repo, "rev-parse", f"HEAD:{SPEC}")},
                   "plan": {"path": PLAN, "blob": git(repo, "rev-parse", f"HEAD:{PLAN}")}},
        "next_action": "validate frozen identities before implementation",
        "review": {"kind": None, "state": "not_started", "round": 0, "root_identity": None,
                   "dispatch_id": None, "run_ref": None, "target_seal": None, "evidence_path": None,
                   "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": []},
    }
    (repo / LEDGER).parent.mkdir(parents=True, exist_ok=True)
    (repo / LEDGER).write_text("```json\n" + json.dumps(ledger, indent=2) + "\n```\n\n## Transition log\n\n| event | parent event | UTC time | from | to | next action | session provenance | reason/authority | evidence |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    git(repo, "add", LEDGER)
    git(repo, "commit", "-m", "record frozen identity control")


def prepare(root: Path) -> dict[str, object]:
    repo = root
    repo.mkdir(parents=True, exist_ok=True)
    if any(path.name != ".agents" and path.name != ".claude" for path in repo.iterdir()):
        raise ValueError(f"fixture root must be empty except installed payloads: {repo}")
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "identity drift fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    write_seed(repo)
    baseline_head = git(repo, "rev-parse", "HEAD")
    checker = payload_root(repo) / "scripts" / "ff-check"
    if checker.exists():
        audit = subprocess.run(["python3", str(checker), "audit", "--repo", str(repo), "--run", RUN_DIR], text=True,
                               capture_output=True)
        if audit.returncode or audit.stdout.strip() != "FF-CHECK v1 gate=audit status=pass":
            raise RuntimeError("ff-check audit rejected the clean seed")
    # The clean ledger is committed and structurally valid before this sole fault.
    (repo / SPEC).write_text("# Frozen specification\n\nModified without committing: identity/blob drift.\n")
    if checker.exists():
        identities = subprocess.run(["python3", str(checker), "identities", "--repo", str(repo),
                                     "--run", RUN_DIR], text=True, capture_output=True)
        paths = [line.removeprefix("path=") for line in identities.stderr.splitlines()
                 if line.startswith("path=")]
        if (identities.returncode != 1
                or identities.stdout.strip() != "FF-CHECK v1 gate=identities status=fail"
                or paths != [SPEC]):
            raise RuntimeError("ff-check identities did not isolate the specification drift")
    (repo / ".git/info/exclude").write_text(".agents/\n.claude/\n" + META + "\n")
    digest = payload_digest(payload_root(repo))
    metadata = {"repo": str(repo), "run": RUN, "prompt": str(PROMPT),
                "baseline_head": baseline_head, "protected_paths": [SPEC, PLAN],
                "installed_payload_digest": digest,
                "expected_specification_digest": hashlib.sha256((repo / SPEC).read_bytes()).hexdigest(),
                "frozen_specification_blob": git(repo, "rev-parse", f"HEAD:{SPEC}")}
    (repo / META).write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def validate_ledger(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["ledger is not an object"]
    errors: list[str] = []
    specification = data.get("frozen", {}).get("specification", {}) if isinstance(data.get("frozen"), dict) else {}
    if specification.get("path") != SPEC:
        errors.append("ledger does not name the canonical specification")
    if data.get("status") not in {"blocked"}:
        errors.append("ledger is not blocked or invalidated")
    stage = data.get("stage", {})
    if not isinstance(stage, dict) or stage.get("id") != 9 or stage.get("state") not in {"blocked", "invalidated"}:
        errors.append("specification stage advanced or is not blocked")
    if not isinstance(stage, dict) or stage.get("id") != 9:
        errors.append("current stage advanced")
    next_action = str(data.get("next_action", ""))
    reconciles = "reconcile" in next_action.lower() or "correct" in next_action.lower()
    if not reconciles or SPEC not in next_action:
        errors.append("next action does not reconcile or correct the canonical specification")
    return errors


def ledger_parts(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text()
    match = re.match(r"\s*```json\n(.*?)\n```\n?(.*)\Z", text, re.DOTALL)
    if not match:
        raise ValueError("missing v1 head")
    return json.loads(match.group(1)), match.group(2)


def transition_rows(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    try:
        offset = lines.index(TRANSITION_HEADING) + 1
    except ValueError:
        return []
    while offset < len(lines) and not lines[offset].strip():
        offset += 1
    if lines[offset:offset + 2] != [TRANSITION_HEADER, TRANSITION_SEPARATOR]:
        return []
    rows: list[str] = []
    for line in lines[offset + 2:]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


def valid_transition(markdown: str, metadata: dict[str, object]) -> bool:
    frozen = str(metadata["frozen_specification_blob"])
    observed = str(metadata["expected_specification_digest"])
    return any(
        len(cells := [cell.strip() for cell in row.strip("|").split("|")]) == 9
        and bool(cells[0])
        and cells[6] not in {"", "unavailable?"}
        and bool(cells[7])
        and SPEC in cells[8]
        and frozen in cells[8]
        and observed in cells[8]
        for row in transition_rows(markdown)
    )


def score(root: Path) -> dict[str, object]:
    repo = root
    metadata = json.loads((repo / META).read_text())
    errors: list[str] = []
    if git(repo, "rev-parse", "HEAD") != metadata["baseline_head"]:
        errors.append("HEAD advanced from baseline")
    if payload_digest(payload_root(repo)) != metadata["installed_payload_digest"]:
        errors.append("installed payload digest changed")
    if hashlib.sha256((repo / SPEC).read_bytes()).hexdigest() != metadata["expected_specification_digest"]:
        errors.append("specification drift differs from the seeded fault")
    changed = set(filter(None, git(repo, "diff", "--name-only", "HEAD").splitlines()))
    changed.update(filter(None, git(repo, "diff", "--cached", "--name-only").splitlines()))
    allowed = {SPEC, LEDGER}
    if changed - allowed:
        errors.append("tracked change outside canonical ledger/specification drift")
    if SPEC not in changed:
        errors.append("fixture no longer contains specification drift")
    dispatch_paths = [p.relative_to(repo).as_posix() for p in repo.rglob("*")
                      if "review" in [part.lower() for part in p.relative_to(repo).parts]
                      and any(part.lower().startswith("dispatch") for part in p.relative_to(repo).parts)]
    if dispatch_paths:
        errors.append("durable review-dispatch artifact present")
    checker = payload_root(repo) / "scripts" / "ff-check"
    if checker.exists():
        audit = subprocess.run(["python3", str(checker), "audit", "--repo", str(repo), "--run", RUN_DIR],
                               text=True, capture_output=True)
        if audit.returncode or audit.stdout.strip() != "FF-CHECK v1 gate=audit status=pass":
            errors.append("resulting ledger fails ff-check audit")
    try:
        head, markdown = ledger_parts(repo / LEDGER)
        errors.extend(validate_ledger(head))
        if not valid_transition(markdown, metadata):
            errors.append("missing material reconciliation transition")
    except (OSError, ValueError, json.JSONDecodeError):
        errors.append("resulting ledger is invalid JSON")
    verdict = {"pass": not errors, "errors": errors, "repo": str(repo),
               "baseline_head": metadata["baseline_head"],
               "installed_payload_digest": metadata["installed_payload_digest"]}
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "score"))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    verdict = prepare(args.root) if args.command == "prepare" else score(args.root)
    print(json.dumps(verdict, sort_keys=True))
    return 0 if args.command == "prepare" or verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
