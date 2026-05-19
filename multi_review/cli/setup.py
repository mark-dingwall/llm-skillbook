from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from multi_review.core.paths import central_runs_dir
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
    p.add_argument("--write-allowlist", action="store_true",
                   help="Append the runs.jsonl allowlist entry to ~/.claude/settings.local.json directly.")
    args = p.parse_args(argv)

    home = Path(os.path.expanduser("~"))
    skill_dst = home / ".claude" / "skills" / "multi-review"
    agents_dst = home / ".claude" / "agents"
    config_path = skill_dst / "config.json"

    # 1. Resolve central path per spec §4.2 BEFORE skill/config setup,
    # so the path is available to write into config.json.
    central = central_runs_dir()
    central.mkdir(parents=True, exist_ok=True)
    (central / "reports").mkdir(parents=True, exist_ok=True)
    (central / "notes" / "legacy").mkdir(parents=True, exist_ok=True)

    # 2. Install skill.
    src_skill = args.source_repo / "skills" / "multi-review"
    if args.dev:
        _symlink(src_skill, skill_dst)
    else:
        _copy_tree(src_skill, skill_dst)

    # 3. Install agents — reviewer.md regenerated from template that interpolates SUMMARY_HEADING_CONTRACT.
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

    # 4. Write config.json so SKILL.md (and library callers) read the resolved central path.
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"central_path": str(central)}, indent=2))

    # 5. Print copy-pastable allowlist entry; optionally write to settings.local.json.
    allowlist_entry = {
        "permissions": {
            "allow": [f"Write({central / 'runs.jsonl'})"]
        }
    }
    snippet = json.dumps(allowlist_entry, indent=2)
    if args.write_allowlist:
        local_settings = home / ".claude" / "settings.local.json"
        existing = {}
        if local_settings.exists():
            try:
                existing = json.loads(local_settings.read_text())
            except json.JSONDecodeError:
                existing = {}
        existing.setdefault("permissions", {}).setdefault("allow", [])
        entry = f"Write({central / 'runs.jsonl'})"
        if entry not in existing["permissions"]["allow"]:
            existing["permissions"]["allow"].append(entry)
        local_settings.parent.mkdir(parents=True, exist_ok=True)
        local_settings.write_text(json.dumps(existing, indent=2))
        print(f"Wrote allowlist entry to {local_settings}.")
    else:
        print("Add the following to ~/.claude/settings.local.json to silence per-run write prompts:")
        print(snippet)

    print(json.dumps({"ok": True,
                      "skill": str(skill_dst), "agents": str(agents_dst),
                      "central_path": str(central), "config": str(config_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
