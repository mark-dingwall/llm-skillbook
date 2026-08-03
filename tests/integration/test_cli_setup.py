# tests/integration/test_cli_setup.py
import shutil
import subprocess
from pathlib import Path

def test_setup_installs_skill_and_writes_config(tmp_path, monkeypatch):
    import json as _json
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("MULTI_REVIEW_NO_DEV_CHECKOUT", "1")
    repo = Path(__file__).resolve().parents[2]
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.setup",
         "--source-repo", str(repo), "--no-prompt"],
        capture_output=True, text=True,
        env={**__import__("os").environ,
             "HOME": str(tmp_path),
             "XDG_DATA_HOME": str(tmp_path / "xdg"),
             "MULTI_REVIEW_NO_DEV_CHECKOUT": "1"},
    )
    assert r.returncode == 0, r.stderr
    # Skill + agents installed.
    assert (tmp_path / ".claude" / "skills" / "multi-review" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "agents" / "multi-review-reviewer.md").exists()
    # Central path written to config.json (resolution per spec §4.2; never the hardcoded ~/kramtime).
    cfg_path = tmp_path / ".claude" / "skills" / "multi-review" / "config.json"
    assert cfg_path.exists()
    cfg = _json.loads(cfg_path.read_text())
    assert "central_path" in cfg
    central = Path(cfg["central_path"])
    assert "kramtime" not in str(central)
    assert (central / "reports").is_dir()
    assert (central / "notes" / "legacy").is_dir()
    # Allowlist snippet printed.
    assert "settings.local.json" in r.stdout or "settings.local.json" in r.stderr

def test_setup_heals_stale_config(tmp_path, monkeypatch):
    import json as _json
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("MULTI_REVIEW_NO_DEV_CHECKOUT", "1")
    # Pre-seed a stale central_path that the resolver would otherwise honour.
    cfg_path = tmp_path / ".claude" / "skills" / "multi-review" / "config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text('{"central_path": "/tmp/bogus-stale/multi-review"}')
    repo = Path(__file__).resolve().parents[2]
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.setup",
         "--source-repo", str(repo), "--no-prompt"],
        capture_output=True, text=True,
        env={**__import__("os").environ,
             "HOME": str(tmp_path),
             "XDG_DATA_HOME": str(tmp_path / "xdg"),
             "MULTI_REVIEW_NO_DEV_CHECKOUT": "1"},
    )
    assert r.returncode == 0, r.stderr
    cfg = _json.loads(cfg_path.read_text())
    assert cfg["central_path"] == str(tmp_path / "xdg" / "multi-review")
    assert "bogus-stale" not in cfg["central_path"]

def test_setup_dev_mode_symlinks(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("MULTI_REVIEW_NO_DEV_CHECKOUT", "1")
    # Stage a COPY as the source repo. --dev symlinks the installed skill dir
    # at --source-repo, so setup's config.json write follows that symlink into
    # whatever tree is named here; passing the live checkout would leave a
    # pytest tmpdir in the developer's real config.json, which
    # central_runs_dir() reads before anything else. See the session guard in
    # tests/conftest.py.
    repo = Path(__file__).resolve().parents[2]
    src = tmp_path / "src"
    (src / "skills").mkdir(parents=True)
    shutil.copytree(repo / "skills" / "multi-review", src / "skills" / "multi-review")
    shutil.copytree(repo / "agents", src / "agents")
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.setup",
         "--source-repo", str(src), "--no-prompt", "--dev"],
        capture_output=True, text=True,
        env={**__import__("os").environ,
             "HOME": str(tmp_path),
             "XDG_DATA_HOME": str(tmp_path / "xdg"),
             "MULTI_REVIEW_NO_DEV_CHECKOUT": "1"},
    )
    assert r.returncode == 0, r.stderr
    assert (tmp_path / ".claude" / "skills" / "multi-review").is_symlink()
    assert (tmp_path / ".claude" / "skills" / "multi-review").resolve() == \
        (src / "skills" / "multi-review").resolve()
