# tests/unit/test_paths.py
from pathlib import Path
from multi_review.core.paths import (
    project_state_dir, run_dir,
    central_runs_dir, generate_run_id, generate_pair_id, slugify,
)

def test_project_state_dir(tmp_path):
    assert project_state_dir(tmp_path) == tmp_path / ".multi-review"

def test_run_dir(tmp_path):
    rid = "run-20260515-1200-abcd"
    assert run_dir(tmp_path, rid) == tmp_path / ".multi-review" / "sessions" / rid

def test_central_runs_dir_honours_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = tmp_path / ".claude" / "skills" / "multi-review" / "config.json"
    cfg.parent.mkdir(parents=True)
    target = tmp_path / "custom" / "multi-review"
    target.mkdir(parents=True)
    cfg.write_text(f'{{"central_path": "{target}"}}')
    p = central_runs_dir()
    assert p == target

def test_central_runs_dir_falls_back_to_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("HOME_RUNS_OVERRIDE", raising=False)
    # Suppress dev-checkout detection so XDG resolution actually wins.
    monkeypatch.setenv("MULTI_REVIEW_NO_DEV_CHECKOUT", "1")
    # No config.json under the fake HOME, so resolution falls through to XDG.
    p = central_runs_dir()
    assert p == tmp_path / "xdg" / "multi-review"

def test_central_runs_dir_ignore_config_skips_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("MULTI_REVIEW_NO_DEV_CHECKOUT", "1")
    cfg = tmp_path / ".claude" / "skills" / "multi-review" / "config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('{"central_path": "/tmp/bogus-stale/multi-review"}')
    # Default honours config.
    assert central_runs_dir() == Path("/tmp/bogus-stale/multi-review")
    # ignore_config=True skips config.json and falls to XDG.
    assert central_runs_dir(ignore_config=True) == tmp_path / "xdg" / "multi-review"

def test_generate_run_id_format():
    rid = generate_run_id()
    assert rid.startswith("run-")
    parts = rid.split("-")
    assert len(parts) == 4 and len(parts[3]) == 4

def test_generate_pair_id_format():
    pid = generate_pair_id()
    assert pid.startswith("pair-")

def test_slugify():
    assert slugify("Auth review v2!") == "auth-review-v2"
    assert slugify("  multiple   spaces  ") == "multiple-spaces"
