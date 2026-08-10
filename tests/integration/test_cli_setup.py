# tests/integration/test_cli_setup.py
import json
import os
import shutil
import subprocess
from pathlib import Path


def test_setup_installs_skill_and_agents_only(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    repo = Path(__file__).resolve().parents[2]
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.setup",
         "--source-repo", str(repo), "--no-prompt"],
        capture_output=True, text=True,
        env={**os.environ, "HOME": str(tmp_path)},
    )
    assert r.returncode == 0, r.stderr
    # Skill + agents installed.
    skill_dst = tmp_path / ".claude" / "skills" / "multi-review"
    agents_dst = tmp_path / ".claude" / "agents"
    assert (skill_dst / "SKILL.md").exists()
    assert (agents_dst / "multi-review-reviewer.md").exists()
    assert not (skill_dst / "config.json").exists()
    assert json.loads(r.stdout) == {
        "skill": str(skill_dst),
        "agents": str(agents_dst),
    }


def test_setup_dev_mode_symlinks(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Stage a copy so the symlink target is isolated from the live checkout.
    repo = Path(__file__).resolve().parents[2]
    src = tmp_path / "src"
    (src / "skills").mkdir(parents=True)
    shutil.copytree(repo / "skills" / "multi-review", src / "skills" / "multi-review")
    shutil.copytree(repo / "agents", src / "agents")
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.setup",
         "--source-repo", str(src), "--no-prompt", "--dev"],
        capture_output=True, text=True,
        env={**os.environ, "HOME": str(tmp_path)},
    )
    assert r.returncode == 0, r.stderr
    assert (tmp_path / ".claude" / "skills" / "multi-review").is_symlink()
    assert (tmp_path / ".claude" / "skills" / "multi-review").resolve() == \
        (src / "skills" / "multi-review").resolve()
