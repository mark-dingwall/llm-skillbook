# tests/integration/test_cli_spawn.py
import json
import os
import stat
import subprocess
from pathlib import Path

def test_spawn_writes_review_and_state(tmp_path, monkeypatch):
    fixture = Path(__file__).parent.parent / "fixtures" / "streams" / "claude" / "success.jsonl"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(f"#!/bin/sh\ncat {fixture}\nexit 0\n")
    fake_claude.chmod(fake_claude.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "claude", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    assert Path(j["review_path"]).exists()
    assert Path(j["state_path"]).exists()
    state = json.loads(Path(j["state_path"]).read_text())
    assert state["cli"] == "claude"
    assert state["ok"] in (True, False)
