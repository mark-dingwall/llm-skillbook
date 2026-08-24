# tests/integration/test_pykrete_spawn.py
"""Integration tests driving the real spawn CLI against a discriminating fake
pykrete binary (tests/fixtures/bin/pykrete). Exercises argparse, spawn.main,
exit-code mapping, and <cli>.md/.state.json writing for the pykrete reviewer
(config_env lookup, success_exit_codes {0,3}, model_flag translation, and the
FAILURE_MIN_BYTES floor) — none of which unit tests on run_reviewer() directly
would catch if build_command's argv shape drifted.
"""
import json
import os
import subprocess
from pathlib import Path

FIXTURE_BIN = Path(__file__).parent.parent / "fixtures" / "bin"


def _env(tmp_path, *, with_config=True, extra=None):
    env = {**os.environ, "PATH": f"{FIXTURE_BIN}:{os.environ['PATH']}"}
    if with_config:
        cfg = tmp_path / "pykrete.toml"
        cfg.write_text("[nanogpt]\n")
        env["PYKRETE_CONFIG"] = str(cfg)
    else:
        env.pop("PYKRETE_CONFIG", None)
    if extra:
        env.update(extra)
    return env


def test_review_exit_3_is_success_and_downgraded(tmp_path):
    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "pykrete", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=_env(tmp_path),
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    state = json.loads(Path(j["state_path"]).read_text())
    assert state["cli"] == "pykrete"
    assert state["ok"] is True
    assert state["downgraded"] is True
    review_text = Path(j["review_path"]).read_text()
    assert "## Summary" in review_text


def test_synthesize_forwards_model_as_family(tmp_path):
    argv_log = tmp_path / "argv.log"
    review_body = tmp_path / "review_body.txt"
    review_body.write_text('<review-deadbeef reviewer="pykrete">\nLooks fine.\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    env = _env(tmp_path, extra={"PYKRETE_ARGV_LOG": str(argv_log), "FAKE_PYKRETE_SYNTH": "1"})
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "pykrete", "--task-mode", "synthesize",
         "--model", "glm", "--input-nonce", "deadbeef",
         "--prompt-file", str(review_body), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    state = json.loads(Path(j["state_path"]).read_text())
    assert state["ok"] is True
    assert argv_log.exists()
    assert "--family glm" in argv_log.read_text()


def test_synthesize_records_family_not_raw_model(tmp_path):
    """Honesty rule parity with fanout.py's records_family_not_model branch:
    pykrete's "model" is really a NanoGPT family, never a concrete model.
    The reviewer path already records this as "family:<x>" — the synthesize
    path must record the same way, not the raw family string (glm)."""
    argv_log = tmp_path / "argv.log"
    review_body = tmp_path / "review_body.txt"
    review_body.write_text('<review-deadbeef reviewer="pykrete">\nLooks fine.\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    env = _env(tmp_path, extra={"PYKRETE_ARGV_LOG": str(argv_log), "FAKE_PYKRETE_SYNTH": "1"})
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "pykrete", "--task-mode", "synthesize",
         "--model", "glm", "--input-nonce", "deadbeef",
         "--prompt-file", str(review_body), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    state = json.loads(Path(j["state_path"]).read_text())
    assert state["ok"] is True
    assert state["final_model"] == "family:glm"


def test_missing_config_fails_cleanly_no_traceback(tmp_path):
    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "pykrete", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=_env(tmp_path, with_config=False),
    )
    # spawn.main returns 0 only if the reviewer succeeded; a config error is a
    # failed reviewer, so main() returns 1 (rc = 0 if result.ok else 1).
    assert r.returncode == 1, r.stderr
    assert "Traceback" not in r.stderr

    state_path = out_dir / "pykrete.state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text())
    assert state["ok"] is False
    assert "PYKRETE_CONFIG" in state["error"]


def test_short_output_fails_on_byte_floor_not_exit_code(tmp_path):
    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    env = _env(tmp_path, extra={"FAKE_PYKRETE_SHORT": "1"})
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "pykrete", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 1, r.stderr

    state = json.loads((out_dir / "pykrete.state.json").read_text())
    assert state["ok"] is False
    assert "exit 3" not in state["error"]
    assert "50" in state["error"]


def test_task_flag_reaches_pykrete_argv(tmp_path):
    """spawn --task code must land as `--task code` in pykrete's real argv —
    without it pykrete silently resolves its [defaults.general] lead."""
    prompt = tmp_path / "p.txt"
    prompt.write_text("review me")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    log = tmp_path / "argv.log"

    subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "pykrete", "--prompt-file", str(prompt),
         "--out-dir", str(out_dir), "--task", "code"],
        capture_output=True, text=True,
        env=_env(tmp_path, extra={"PYKRETE_ARGV_LOG": str(log)}),
    )

    assert "--task code" in log.read_text()


def test_synthesis_task_flag_reaches_pykrete_argv(tmp_path):
    """Break caught: synthesis dropped the prompt task and used Pykrete's wrong preset."""
    prompt = tmp_path / "review_body.txt"
    prompt.write_text('<review-deadbeef reviewer="pykrete">\n## Summary\n\nFine.\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    log = tmp_path / "argv.log"

    result = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "pykrete", "--task-mode", "synthesize", "--task", "code",
         "--input-nonce", "deadbeef", "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
        env=_env(tmp_path, extra={"PYKRETE_ARGV_LOG": str(log), "FAKE_PYKRETE_SYNTH": "1"}),
    )

    assert result.returncode == 0, result.stderr
    assert "--task code" in log.read_text()
