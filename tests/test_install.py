"""Guards for install.py payload boundaries and fail-closed behavior.

Run: python3 -m pytest tests/test_install.py
"""
import importlib.util
import json
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


def test_claude_work_team_install_preserves_settings_and_registers_hook_once(
    tmp_path,
):
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps(
            {
                "theme": "dark",
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [{"type": "command", "command": "check"}],
                        }
                    ]
                },
            }
        )
    )

    install.install("work-team", "claude", tmp_path, dev=False, force=False)
    install.install("work-team", "claude", tmp_path, dev=False, force=False)

    settings = json.loads(settings_file.read_text())
    assert settings["theme"] == "dark"
    assert settings["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    registrations = settings["hooks"]["SubagentStop"]
    assert len(registrations) == 1
    assert registrations[0]["matcher"] == "llm-skillbook-work-team-worker"
    handler = registrations[0]["hooks"][0]
    assert handler == {
        "type": "command",
        "command": str(
            tmp_path / ".claude/skills/work-team/scripts/wt-capture-return"
        ),
        "args": [],
    }
    assert (tmp_path / ".claude/agents/llm-skillbook-work-team-worker.md").is_file()


def test_claude_work_team_install_fails_before_writing_on_invalid_settings(tmp_path):
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text("not json")

    with pytest.raises(SystemExit, match="cannot update"):
        install.install("work-team", "claude", tmp_path, dev=False, force=False)

    assert settings_file.read_text() == "not json"
    assert not (tmp_path / ".claude/skills/work-team").exists()


def test_claude_work_team_install_rejects_conflicting_owned_matcher(tmp_path):
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "SubagentStop": [
                        {
                            "matcher": "llm-skillbook-work-team-worker",
                            "hooks": [{"type": "command", "command": "foreign"}],
                        }
                    ]
                }
            }
        )
    )

    with pytest.raises(SystemExit, match="conflicting"):
        install.install("work-team", "claude", tmp_path, dev=False, force=False)

    assert not (tmp_path / ".claude/skills/work-team").exists()


def test_claude_work_team_install_rejects_dangling_settings_symlink(tmp_path):
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.symlink_to(tmp_path / "missing-settings.json")

    with pytest.raises(SystemExit, match="regular file"):
        install.install("work-team", "claude", tmp_path, dev=False, force=False)

    assert settings_file.is_symlink()
    assert not (tmp_path / ".claude/skills/work-team").exists()


@pytest.mark.parametrize(
    "registration",
    [
        42,
        {"matcher": "Other", "hooks": "not-an-array"},
        {"matcher": "Other", "hooks": [{}]},
    ],
)
def test_claude_work_team_install_rejects_malformed_subagent_hook(
    tmp_path, registration
):
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps({"hooks": {"SubagentStop": [registration]}})
    )
    original = settings_file.read_bytes()

    with pytest.raises(SystemExit, match="malformed"):
        install.install("work-team", "claude", tmp_path, dev=False, force=False)

    assert settings_file.read_bytes() == original
    assert not (tmp_path / ".claude/skills/work-team").exists()
