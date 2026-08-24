# tests/integration/test_cli_spawn.py
import json
import os
import stat
import subprocess
import sys
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
    assert state["ok"] is True


def test_spawn_synthesize_writes_synth_files(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    # Synth path is non-streaming; build_command appends "-" stdin sentinel.
    # Emit a synthesis-shaped body to stdout above the 50-byte threshold.
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(
        "#!/bin/sh\n"
        "cat > /dev/null\n"
        "printf '### Agreed Strengths\\n- Clear API.\\n\\n### Agreed Concerns\\n- Missing validation.\\n\\n### Divergent Views\\n- None.\\n'\n"
        "exit 0\n"
    )
    fake_claude.chmod(fake_claude.stat().st_mode | stat.S_IEXEC)

    review_body = tmp_path / "review_body.txt"
    review_body.write_text('<review-deadbeef reviewer="claude">\nText\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "claude",
         "--task-mode", "synthesize",
         "--input-nonce", "deadbeef",
         "--prompt-file", str(review_body),
         "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    assert "synth_path" in j and "state_path" in j
    assert Path(j["synth_path"]).name == "synth.txt"
    assert Path(j["state_path"]).name == "synth.state.json"
    # Must NOT write <cli>.md or <cli>.state.json under synthesize mode.
    assert not (out_dir / "claude.md").exists()
    assert not (out_dir / "claude.state.json").exists()
    state = json.loads(Path(j["state_path"]).read_text())
    assert state["cli"] == "claude"
    assert "duration_seconds" in state


def test_spawn_cli_flag_is_required(tmp_path):
    """`--cli` must have no default. If a future edit changed
    `required=True` to e.g. `default="grok"`, a bare `spawn` invocation would
    silently run grok. This never reaches subprocess-launch code: argparse
    rejects the missing required arg before `main` does anything else, so
    there is no risk of this test ever touching a real reviewer binary.
    """
    from multi_review.cli.spawn import main
    rc = main(["--prompt-file", "/nonexistent", "--out-dir", str(tmp_path)])
    assert rc == 2


def test_spawn_no_fallback_flags(tmp_path):
    from multi_review.cli.spawn import main
    rc = main(["--cli", "claude", "--prompt-file", "/nonexistent",
               "--out-dir", str(tmp_path), "--fallback-chain", "a,b,c"])
    # argparse error: unrecognized arg
    assert rc == 2


def test_spawn_no_no_fallback_flag(tmp_path):
    from multi_review.cli.spawn import main
    rc = main(["--cli", "claude", "--prompt-file", "/nonexistent",
               "--out-dir", str(tmp_path), "--no-fallback"])
    assert rc == 2


def test_spawn_review_mode_unchanged(tmp_path):
    """--task-mode review (default) keeps writing <cli>.md + <cli>.state.json."""
    fixture = Path(__file__).parent.parent / "fixtures" / "streams" / "claude" / "success.jsonl"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(f"#!/bin/sh\ncat {fixture}\nexit 0\n")
    fake_claude.chmod(fake_claude.stat().st_mode | stat.S_IEXEC)

    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "claude", "--task-mode", "review",
         "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    assert Path(j["review_path"]).name == "claude.md"
    assert Path(j["state_path"]).name == "claude.state.json"
    assert not (out_dir / "synth.txt").exists()


def test_spawn_marks_no_summary_output_failed(tmp_path):
    """Interactive state must be qualified before the synthesis gate reads it."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' '{\"type\":\"result\",\"result\":\"I cannot provide a structured review at this time, but here is some prose.\"}'\n"
    )
    fake_claude.chmod(fake_claude.stat().st_mode | stat.S_IEXEC)
    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"

    result = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "claude", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert result.returncode == 1
    state = json.loads((out_dir / "claude.state.json").read_text())
    assert state["ok"] is False
    assert "Summary" in state["error"]


def test_spawn_persists_malformed_codex_event_as_failed_state(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_codex = fake_bin / "codex"
    fake_codex.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' '{\"type\":\"thread.started\"}'\n"
        "printf '%s\\n' '{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":null}}'\n"
        "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{}}'\n"
    )
    fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IEXEC)
    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-m", "multi_review.cli.spawn",
         "--cli", "codex", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(project_root),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    assert result.returncode == 1
    assert (out_dir / "codex.md").read_text() == ""
    state = json.loads((out_dir / "codex.state.json").read_text())
    assert state["ok"] is False
    assert state["error"] == "malformed Codex agent_message text"


def test_spawn_reads_unicode_prompt_under_ascii_locale(tmp_path):
    fixture = Path(__file__).parent.parent / "fixtures" / "streams" / "claude" / "success.jsonl"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(f"#!/bin/sh\ncat {fixture}\n")
    fake_claude.chmod(fake_claude.stat().st_mode | stat.S_IEXEC)
    prompt = tmp_path / "prompt.txt"
    prompt.write_bytes("Review café handling.".encode("utf-8"))
    out_dir = tmp_path / "out"
    project_root = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "PYTHONPATH": str(project_root),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "LC_ALL": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }

    result = subprocess.run(
        [sys.executable, "-m", "multi_review.cli.spawn",
         "--cli", "claude", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (out_dir / "claude.md").exists()
