#!/usr/bin/env python3
"""Disposable single-fault identity-drift fixture and Git-state oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


RUN = "identity-drift"
SPEC = f"docs/feature-forge/runs/{RUN}/specification.md"
PLAN = f"docs/feature-forge/runs/{RUN}/plan.md"
LEDGER = f"docs/feature-forge/runs/{RUN}/ledger.md"
META = ".identity-drift-oracle.json"
PROMPT = Path(__file__).with_name("identity-drift") / "prompt.md"


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
    ledger = {
        "run": RUN,
        "status": "active",
        "current_stage": "specification",
        "stages": {"specification": "frozen", "plan": "frozen", "implementation": "pending"},
        "frozen": {"specification": {"path": SPEC, "blob": git(repo, "rev-parse", f"HEAD:{SPEC}")},
                   "plan": {"path": PLAN, "blob": git(repo, "rev-parse", f"HEAD:{PLAN}")}},
        "next_action": "validate frozen identities before proceeding",
        "transitions": [],
    }
    (repo / LEDGER).write_text(json.dumps(ledger, indent=2) + "\n")
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
        audit = subprocess.run(["python3", str(checker), "audit", "--repo", str(repo)], text=True,
                               capture_output=True)
        if audit.returncode:
            raise RuntimeError("ff-check audit rejected the clean seed")
    # The clean ledger is committed and structurally valid before this sole fault.
    (repo / SPEC).write_text("# Frozen specification\n\nModified without committing: identity/blob drift.\n")
    if checker.exists():
        identities = subprocess.run(["python3", str(checker), "identities", "--repo", str(repo),
                                     "--run", RUN], text=True, capture_output=True)
        output = identities.stdout + identities.stderr
        if identities.returncode == 0 or SPEC not in output:
            raise RuntimeError("ff-check identities did not isolate the specification drift")
    (repo / ".git/info/exclude").write_text(".agents/\n.claude/\n" + META + "\n")
    digest = payload_digest(payload_root(repo))
    metadata = {"repo": str(repo), "run": RUN, "prompt": str(PROMPT),
                "baseline_head": baseline_head, "protected_paths": [SPEC, PLAN],
                "installed_payload_digest": digest,
                "expected_specification_digest": hashlib.sha256((repo / SPEC).read_bytes()).hexdigest()}
    (repo / META).write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def validate_ledger(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["ledger is not an object"]
    errors: list[str] = []
    specification = data.get("frozen", {}).get("specification", {}) if isinstance(data.get("frozen"), dict) else {}
    if specification.get("path") != SPEC:
        errors.append("ledger does not name the canonical specification")
    if data.get("status") not in {"blocked", "invalidated"}:
        errors.append("ledger is not blocked or invalidated")
    if data.get("stages", {}).get("specification") not in {"blocked", "invalidated"}:
        errors.append("specification stage advanced or is not blocked")
    if data.get("current_stage") != "specification":
        errors.append("current stage advanced")
    next_action = str(data.get("next_action", "")).lower()
    if not ("reconcile" in next_action or "correct" in next_action):
        errors.append("next action is not reconciliation or correction")
    transition = data.get("transitions", [])
    if not isinstance(transition, list) or len(transition) != 1 or not isinstance(transition[0], dict):
        return errors + ["missing material reconciliation transition"]
    record = transition[0]
    reason = str(record.get("reason", "")).lower()
    if SPEC.lower() not in reason or not ("identity" in reason and "blob" in reason):
        errors.append("transition reason lacks canonical identity/blob drift")
    if record.get("kind") not in {"reconciliation", "correction"}:
        errors.append("transition is not reconciliation/correction")
    if record.get("session") in (None, ""):
        errors.append("transition lacks harness/session provenance")
    return errors


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
    try:
        errors.extend(validate_ledger(json.loads((repo / LEDGER).read_text())))
    except (OSError, json.JSONDecodeError):
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
