"""The plugin's top-level agents/ must mirror their canonical agents.

Claude Code plugin subagents must be REAL files in the plugin-root agents/ dir
(symlinks and explicit-path `agents` fields both register 0). So agents/*.md are
real copies of their component definitions — this guards them against drift.

Run: python3 -m pytest tests/test_plugin_agents.py
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "agents"
CANONICAL = {
    "multi-review-build": REPO / "multi-review" / "agents",
    "multi-review-reviewer": REPO / "multi-review" / "agents",
    "multi-review-synthesizer": REPO / "multi-review" / "agents",
    "llm-skillbook-work-team-worker": REPO / "work-team" / "agents",
}


def test_plugin_agents_mirror_canonical():
    for n, canonical_root in CANONICAL.items():
        canon, plugin = canonical_root / f"{n}.md", PLUGIN / f"{n}.md"
        assert plugin.exists(), f"plugin agent {plugin} missing"
        assert plugin.read_text() == canon.read_text(), (
            f"agents/{n}.md drifted from {canon}; re-copy it"
        )


def test_plugin_agents_are_real_files_not_symlinks():
    for n in CANONICAL:
        assert not (PLUGIN / f"{n}.md").is_symlink(), (
            "plugin agents must be real files — Claude Code skips symlinked agents"
        )


def test_plugin_registers_capture_hook_only_for_work_team_worker():
    hooks = __import__("json").loads((REPO / "hooks/hooks.json").read_text())

    assert hooks["hooks"]["SubagentStop"] == [
        {
            "matcher": "llm-skillbook-work-team-worker",
            "hooks": [
                {
                    "type": "command",
                    "command": (
                        "${CLAUDE_PLUGIN_ROOT}/work-team/scripts/"
                        "wt-capture-return"
                    ),
                    "args": [],
                }
            ],
        }
    ]
