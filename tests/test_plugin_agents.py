"""The plugin's top-level agents/ must mirror multi-review's canonical agents.

Claude Code plugin subagents must be REAL files in the plugin-root agents/ dir
(symlinks and explicit-path `agents` fields both register 0). So agents/*.md are
real copies of multi-review/agents/*.md — this guards them against drift.

Run: python3 -m pytest tests/test_plugin_agents.py
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANON = REPO / "multi-review" / "agents"
PLUGIN = REPO / "agents"
NAMES = ["multi-review-build", "multi-review-reviewer", "multi-review-synthesizer"]


def test_plugin_agents_mirror_canonical():
    for n in NAMES:
        canon, plugin = CANON / f"{n}.md", PLUGIN / f"{n}.md"
        assert plugin.exists(), f"plugin agent {plugin} missing"
        assert plugin.read_text() == canon.read_text(), (
            f"agents/{n}.md drifted from multi-review/agents/{n}.md; re-copy it"
        )


def test_plugin_agents_are_real_files_not_symlinks():
    for n in NAMES:
        assert not (PLUGIN / f"{n}.md").is_symlink(), (
            "plugin agents must be real files — Claude Code skips symlinked agents"
        )
