"""Guards for install.py payload boundaries and fail-closed behavior.

Run: python3 -m pytest tests/test_install.py
"""
import importlib.util
import stat
import subprocess
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


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_feature_forge_payload_ships_checker(tmp_path, host):
    install.install("feature-forge", host, tmp_path, dev=False, force=False)
    namespace = ".agents" if host == "codex" else ".claude"
    skill_root = tmp_path / namespace / "skills" / "feature-forge"
    assert (skill_root / "scripts" / "ff-check").is_file()
    assert not (skill_root / "tests").exists()
    assert not (skill_root / "reports").exists()


@pytest.mark.parametrize(
    ("host", "namespace"), [("codex", ".agents"), ("claude", ".claude")],
)
def test_feature_forge_production_checker_is_user_executable(tmp_path, host, namespace):
    source = REPO / "feature-forge" / "scripts" / "ff-check"
    assert source.stat().st_mode & stat.S_IXUSR

    install.install("feature-forge", host, tmp_path, dev=False, force=False)
    checker = tmp_path / namespace / "skills" / "feature-forge" / "scripts" / "ff-check"
    assert checker.stat().st_mode & stat.S_IXUSR

    result = subprocess.run(
        [sys.executable, str(checker), "--help"], text=True, capture_output=True,
    )
    assert result.returncode == 0
    assert "{runs,identities,reviewed-snapshot,audit}" in result.stdout
    assert "FF-CHECK" not in result.stdout


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
