#!/usr/bin/env python3
"""Install skillbook skills into Claude Code and/or Codex.

    python3 install.py <skill|all> --target claude|codex|both [--dev] [--force]

Targets (user-scoped):
  claude  ~/.claude/skills/<name>/   + Claude subagents to ~/.claude/agents/
  codex   ~/.agents/skills/<name>/

--dev symlinks the whole skill dir instead of copying (edit-in-place).
Fail-closed: refuses to overwrite a destination this installer did not create,
unless --force. Repo-scoped use needs no install: Codex reads .agents/skills/
here, and Claude reads the .claude-plugin/ marketplace.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKILLS = ["feature-forge", "multi-review", "review-loop", "review-team"]
MARKER = ".installed-by-llm-skillbook"

# Top-level entries never shipped to an install target (dev-only).
EXCLUDE_TOP = {
    "tests", "docs", "evals", "README.md", "BACKLOG.md", "CLAUDE.md",
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


def install(name: str, target: str, home: Path, dev: bool, force: bool) -> None:
    src = REPO / name
    if target in ("claude", "both"):
        _place(src, home / ".claude" / "skills" / name, dev, force)
        agents_dst = home / ".claude" / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        for md in sorted((src / "agents").glob("*.md")):  # Claude subagents only
            shutil.copy2(md, agents_dst / md.name)
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
