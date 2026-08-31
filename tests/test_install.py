"""Guards for install.py payload boundaries and fail-closed behavior.

Run: python3 -m pytest tests/test_install.py
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("install", REPO / "install.py")
install = importlib.util.module_from_spec(_spec)
sys.modules["install"] = install
_spec.loader.exec_module(install)


def test_codex_payload_ships_runtime_excludes_dev(tmp_path):
    install.install("multi-review", "codex", tmp_path, dev=False, force=False)
    root = tmp_path / ".agents" / "skills" / "multi-review"
    for keep in ("SKILL.md", "pyproject.toml", "uv.lock", "scripts/py",
                 "agents/openai.yaml", "multi_review"):
        assert (root / keep).exists(), f"payload missing {keep}"
    for drop in ("tests", "docs", "BACKLOG.md", "CLAUDE.md", "AGENTS.md", "__pycache__"):
        assert not (root / drop).exists(), f"payload leaked dev-only {drop}"


def test_maintainer_guidance_is_excluded_by_name():
    assert {"README.md", "CLAUDE.md", "AGENTS.md"} <= install.EXCLUDE_TOP


def test_reports_are_excluded_from_production_payloads():
    assert "reports" in install.EXCLUDE_TOP


def test_claude_splits_subagents(tmp_path):
    install.install("multi-review", "claude", tmp_path, dev=False, force=False)
    agents = tmp_path / ".claude" / "agents"
    assert (agents / "multi-review-reviewer.md").exists()
    assert (tmp_path / ".claude" / "skills" / "multi-review" / "SKILL.md").exists()


def test_fail_closed_on_foreign_dir(tmp_path):
    dst = tmp_path / ".agents" / "skills" / "review-team"
    dst.mkdir(parents=True)
    (dst / "SKILL.md").write_text("foreign")
    with pytest.raises(SystemExit):
        install.install("review-team", "codex", tmp_path, dev=False, force=False)
    assert (dst / "SKILL.md").read_text() == "foreign"  # untouched


def test_force_overwrites_foreign(tmp_path):
    dst = tmp_path / ".agents" / "skills" / "review-team"
    dst.mkdir(parents=True)
    (dst / "SKILL.md").write_text("foreign")
    install.install("review-team", "codex", tmp_path, dev=False, force=True)
    assert (dst / install.MARKER).exists()
