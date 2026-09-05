#!/usr/bin/env python3
"""Install skillbook skills into Claude Code and/or Codex.

    python3 install.py <skill|all> --target claude|codex|both [--dev] [--force]

Targets (user-scoped):
  claude  ~/.claude/skills/<name>/   + Claude agents and required hooks
  codex   ~/.agents/skills/<name>/

--dev symlinks the whole skill dir instead of copying (edit-in-place).
Fail-closed: refuses to overwrite a destination this installer did not create,
unless --force. Repo-scoped use needs no install: Codex reads .agents/skills/
here, and Claude reads the .claude-plugin/ marketplace.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKILLS = ["feature-forge", "multi-review", "review-loop", "review-team", "work-team"]
MARKER = ".installed-by-llm-skillbook"
WORK_TEAM_AGENT = "llm-skillbook-work-team-worker"

# Top-level entries never shipped to an install target (dev-only).
EXCLUDE_TOP = {
    "tests", "docs", "evals", "README.md", "BACKLOG.md", "CLAUDE.md", "AGENTS.md",
    "PLAN.md", ".gitignore", ".sdd-history",
}
# Directory names pruned anywhere in the tree (build/cache artifacts).
EXCLUDE_ANY = {
    "__pycache__", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in EXCLUDE_ANY or n.endswith(".egg-info")}


def _copy_payload(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    (dst / MARKER).write_text("")
    for child in sorted(src.iterdir()):
        if child.name in EXCLUDE_TOP or child.name in EXCLUDE_ANY:
            continue
        if child.name.endswith(".egg-info"):
            continue
        target = dst / child.name
        if child.is_dir():
            shutil.copytree(child, target, ignore=_ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def _guard(src: Path, dst: Path, force: bool) -> None:
    """Refuse a destination we did not create (unless --force).

    Ours = a copy carrying MARKER, or a --dev symlink already pointing at src.
    """
    if force or not (dst.exists() or dst.is_symlink()):
        return
    if dst.is_symlink() and dst.resolve() == src.resolve():
        return
    if not (dst / MARKER).exists():
        sys.exit(f"refusing to overwrite {dst} (not installed by this tool; use --force)")


def _place(src: Path, dst: Path, dev: bool, force: bool) -> None:
    _guard(src, dst, force)
    if dst.is_symlink() or dst.exists():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dev:
        dst.symlink_to(src, target_is_directory=True)
    else:
        _copy_payload(src, dst)


def _work_team_hook(home: Path) -> dict:
    return {
        "matcher": WORK_TEAM_AGENT,
        "hooks": [
            {
                "type": "command",
                "command": str(
                    home
                    / ".claude"
                    / "skills"
                    / "work-team"
                    / "scripts"
                    / "wt-capture-return"
                ),
                "args": [],
            }
        ],
    }


def _load_claude_settings(home: Path) -> tuple[Path, dict]:
    path = home / ".claude" / "settings.json"
    if not path.exists():
        return path, {}
    if path.is_symlink() or not path.is_file():
        sys.exit(f"cannot update {path}: expected a regular file")
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        sys.exit(f"cannot update {path}: {error}")
    if not isinstance(settings, dict):
        sys.exit(f"cannot update {path}: root must be a JSON object")
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        sys.exit(f"cannot update {path}: hooks must be a JSON object")
    registrations = hooks.get("SubagentStop", [])
    if not isinstance(registrations, list):
        sys.exit(f"cannot update {path}: hooks.SubagentStop must be an array")
    expected = _work_team_hook(home)
    collisions = [
        row
        for row in registrations
        if isinstance(row, dict) and row.get("matcher") == WORK_TEAM_AGENT
    ]
    if collisions and collisions != [expected]:
        sys.exit(
            f"cannot update {path}: conflicting {WORK_TEAM_AGENT} hook exists"
        )
    return path, settings


def _register_work_team_hook(home: Path, path: Path, settings: dict) -> None:
    hooks = settings.setdefault("hooks", {})
    registrations = hooks.setdefault("SubagentStop", [])
    expected = _work_team_hook(home)
    if expected in registrations:
        return
    registrations.append(expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=".settings.json.llm-skillbook-"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(settings, stream, indent=2)
            stream.write("\n")
        temporary.chmod(previous_mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def install(name: str, target: str, home: Path, dev: bool, force: bool) -> None:
    src = REPO / name
    hook_settings = None
    if name == "work-team" and target in ("claude", "both"):
        hook_settings = _load_claude_settings(home)
    if target in ("claude", "both"):
        _place(src, home / ".claude" / "skills" / name, dev, force)
        agents_dst = home / ".claude" / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        for md in sorted((src / "agents").glob("*.md")):  # Claude subagents only
            shutil.copy2(md, agents_dst / md.name)
        if hook_settings is not None:
            _register_work_team_hook(home, *hook_settings)
    if target in ("codex", "both"):
        _place(src, home / ".agents" / "skills" / name, dev, force)
    print(f"installed {name} -> {target}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("skill", help="skill name or 'all'")
    p.add_argument("--target", choices=["claude", "codex", "both"], default="both")
    p.add_argument("--dev", action="store_true", help="symlink instead of copy")
    p.add_argument("--force", action="store_true", help="overwrite a foreign destination")
    p.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    names = SKILLS if args.skill == "all" else [args.skill]
    unknown = [n for n in names if n not in SKILLS]
    if unknown:
        sys.exit(f"unknown skill(s): {', '.join(unknown)} (known: {', '.join(SKILLS)})")
    for n in names:
        install(n, args.target, args.home, args.dev, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
