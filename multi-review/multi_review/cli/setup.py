from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from multi_review.core.prompt import SUMMARY_HEADING_CONTRACT


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir():
            _copy_tree(child, target)
        else:
            shutil.copy2(child, target)


def _symlink(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(src, target_is_directory=src.is_dir())


def _render_agent_md(template: Path, target: Path) -> None:
    """Substitute the SUMMARY_HEADING_CONTRACT sentinel comment in the agent template."""
    body = template.read_text()
    body = body.replace("<!-- SUMMARY_CONTRACT -->", SUMMARY_HEADING_CONTRACT)
    target.write_text(body)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-repo", type=Path, required=True)
    p.add_argument("--no-prompt", action="store_true")
    p.add_argument("--dev", action="store_true",
                   help="Symlink skills/ and agents/ instead of copying (iterate without re-running setup).")
    args = p.parse_args(argv)

    home = Path(os.path.expanduser("~"))
    skill_dst = home / ".claude" / "skills" / "multi-review"
    agents_dst = home / ".claude" / "agents"

    # 1. Install skill.
    src_skill = args.source_repo / "skills" / "multi-review"
    if args.dev:
        _symlink(src_skill, skill_dst)
    else:
        _copy_tree(src_skill, skill_dst)

    # 2. Install agents — reviewer.md regenerated from template that interpolates SUMMARY_HEADING_CONTRACT.
    src_agents = args.source_repo / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    for md in src_agents.glob("*.md"):
        target = agents_dst / md.name
        if md.name == "multi-review-reviewer.md":
            _render_agent_md(md, target)
        elif args.dev:
            _symlink(md, target)
        else:
            shutil.copy2(md, target)

    print(json.dumps({"skill": str(skill_dst), "agents": str(agents_dst)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
