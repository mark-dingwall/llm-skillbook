# tests/integration/test_grok_spawn.py
"""Integration tests driving the real spawn CLI against a discriminating fake
grok binary (tests/fixtures/bin/grok). Exercises argparse, spawn.main, the
GrokAdapter's streaming-json parsing, the non-streaming synthesis path, exit-code
mapping, and <cli>.md/.state.json writing — none of which unit tests on
build_command or the adapter alone would catch if the argv shape, the stdin
wiring, or the review-vs-synthesis output contract drifted.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURE_BIN = Path(__file__).parent.parent / "fixtures" / "bin"


def _env(extra=None):
    env = {**os.environ, "PATH": f"{FIXTURE_BIN}:{os.environ['PATH']}"}
    if extra:
        env.update(extra)
    return env


@pytest.fixture(scope="module", autouse=True)
def _grok_resolves_to_fixture():
    """Whole-file guard: only 2 of the tests below assert FIXTURE_GROK_MARKER.
    The rest drive behaviour purely through FAKE_GROK_* env vars that the real
    binary ignores, so a regression in _env()'s PATH prepend would silently
    turn them into live, paid calls to the real grok CLI instead of failing
    loudly. Fail here, before any subprocess is spawned, if PATH doesn't
    resolve `grok` inside the fixture bin.

    That assertion alone only validates what _env() COMPUTES, not what actually
    reaches each launch — a future edit that dropped `env=_env(...)` in favour
    of ambient `os.environ`, or added a raw subprocess call elsewhere in this
    file, would keep this guard green while resolving the real, network-calling
    `grok` off the real PATH. So also prepend FIXTURE_BIN to the process's own
    `os.environ["PATH"]` for the duration of this module, restoring it after —
    belt-and-braces: even a launch that forgets `env=_env(...)` and falls back
    to ambient os.environ still resolves the shim, not the real binary.
    """
    resolved = shutil.which("grok", path=_env()["PATH"])
    assert resolved and Path(resolved).parent == FIXTURE_BIN, (
        f"grok resolved to {resolved!r}, not the fixture bin {FIXTURE_BIN} — "
        "PATH prepend in _env() may have regressed; refusing to run this file "
        "against a possibly-real grok binary"
    )
    old_path = os.environ["PATH"]
    os.environ["PATH"] = f"{FIXTURE_BIN}:{old_path}"
    try:
        yield
    finally:
        os.environ["PATH"] = old_path


def _spawn(tmp_path, prompt_text="review this code please", extra_args=(), env_extra=None):
    prompt = tmp_path / "p.txt"
    prompt.write_text(prompt_text)
    out_dir = tmp_path / "out"
    out_dir.mkdir(exist_ok=True)
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "grok", "--prompt-file", str(prompt),
         "--out-dir", str(out_dir), *extra_args],
        capture_output=True, text=True, env=_env(env_extra), timeout=60,
    )
    return r, out_dir, prompt


def test_review_success_parses_streaming_json(tmp_path):
    r, out_dir, _ = _spawn(tmp_path)
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    state = json.loads(Path(j["state_path"]).read_text())
    # Proves the fixture shim ran, not a real grok binary picked up off PATH
    # (see tests/fixtures/bin/grok's FIXTURE_GROK_MARKER) — without this, a
    # test that lost the FIXTURE_BIN/PATH prepend would silently invoke the
    # real, network-calling grok CLI instead of failing loudly.
    assert "FIXTURE_GROK_MARKER=7f3c2e1a" in state["stderr_tail"]
    assert state["cli"] == "grok"
    assert state["ok"] is True
    assert state["downgraded"] is False
    assert state["final_model"] == "<default>"      # never a "family:" prefix
    assert state["usage"]["input_tokens"] == 1200   # from the end event
    assert state["usage"]["cached_tokens"] == 300
    assert state["usage"]["tool_calls"] == 0
    body = Path(j["review_path"]).read_text()
    assert body.startswith("## Summary")
    assert "Considering the diff." not in body      # thought narration excluded
    assert '"type"' not in body                     # JSONL envelope not leaked


def test_prompt_travels_on_stdin_not_argv(tmp_path):
    """Core invariant: prompt bytes must never reach /proc/PID/cmdline."""
    argv_log = tmp_path / "argv.log"
    stdin_log = tmp_path / "stdin.log"
    secret = "SENTINEL-PROMPT-BODY-must-not-appear-on-argv"
    r, _, _ = _spawn(
        tmp_path, prompt_text=secret,
        env_extra={"GROK_ARGV_LOG": str(argv_log), "GROK_STDIN_LOG": str(stdin_log)},
    )
    assert r.returncode == 0, r.stderr
    argv = argv_log.read_text().splitlines()
    assert secret not in argv_log.read_text()        # prompt not on argv
    assert argv[argv.index("--prompt-file") + 1] == "/dev/stdin"
    assert argv[argv.index("--sandbox") + 1] == "workspace"
    assert argv[argv.index("--output-format") + 1] == "streaming-json"
    assert stdin_log.read_text() == secret           # prompt did arrive on the pipe


def test_model_pin_forwarded_and_recorded(tmp_path):
    argv_log = tmp_path / "argv.log"
    r, out_dir, _ = _spawn(
        tmp_path, extra_args=("--model", "grok-4.5-build"),
        env_extra={"GROK_ARGV_LOG": str(argv_log)},
    )
    assert r.returncode == 0, r.stderr
    argv = argv_log.read_text().splitlines()
    assert argv[argv.index("--model") + 1] == "grok-4.5-build"
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["final_model"] == "grok-4.5-build"  # real model, not "family:..."


def test_synthesize_uses_plain_output_not_jsonl(tmp_path):
    """The synthesis path builds with streaming=False and takes stdout verbatim
    (synthesis.py:105) with no adapter. If the streaming flag leaked in, the
    JSONL envelope would become the synthesis body — and would still pass
    run_synthesis's rc+byte-count check, so only this assertion catches it."""
    argv_log = tmp_path / "argv.log"
    stdin_log = tmp_path / "stdin.log"
    review_body = tmp_path / "review_body.txt"
    review_body.write_text('<review-deadbeef reviewer="grok">\nLooks fine.\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "grok", "--task-mode", "synthesize",
         "--input-nonce", "deadbeef",
         "--prompt-file", str(review_body), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
        env=_env({"GROK_ARGV_LOG": str(argv_log), "GROK_STDIN_LOG": str(stdin_log)}),
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    synth = Path(j["synth_path"]).read_text()
    assert synth.startswith("## Summary")
    assert '"type"' not in synth                    # NOT the JSONL envelope
    argv = argv_log.read_text().splitlines()
    assert "--output-format" not in argv            # non-streaming path
    assert argv[argv.index("--prompt-file") + 1] == "/dev/stdin"
    # Non-leak assertion must key off the PROMPT CONTENT, not the parent-side
    # filename: synthesis.py:62 assembles a fresh prompt containing the nonce
    # and the wrapped review bodies, so asserting the filename is absent would
    # still pass if that assembled prompt were placed on argv.
    assert "deadbeef" not in argv_log.read_text()   # prompt content not on argv
    assert "Looks fine." not in argv_log.read_text()
    assert "deadbeef" in stdin_log.read_text()      # the wrapped reviews arrived
    state = json.loads((out_dir / "synth.state.json").read_text())
    assert state["ok"] is True
    # Same fixture-not-real-binary proof as the streaming-mode test, via the
    # non-streaming path's stderr_tail channel.
    assert "FIXTURE_GROK_MARKER=7f3c2e1a" in state["stderr_tail"]


def test_synthesize_model_pin_recorded_verbatim(tmp_path):
    """grok has no records_family_not_model, so the pinned model is recorded
    as-is — unlike pykrete, which must record "family:<x>"."""
    review_body = tmp_path / "review_body.txt"
    review_body.write_text('<review-deadbeef reviewer="grok">\nLooks fine.\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "grok", "--task-mode", "synthesize",
         "--model", "grok-4.5-build", "--input-nonce", "deadbeef",
         "--prompt-file", str(review_body), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=_env(), timeout=60,
    )
    assert r.returncode == 0, r.stderr
    state = json.loads((out_dir / "synth.state.json").read_text())
    assert state["final_model"] == "grok-4.5-build"
    assert not str(state["final_model"]).startswith("family:")


def test_nonzero_exit_is_a_recorded_failure(tmp_path):
    r, out_dir, _ = _spawn(tmp_path, env_extra={"FAKE_GROK_RC": "1"})
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["ok"] is False
    assert "exit 1" in state["error"]


def test_exit_3_is_not_success_for_grok(tmp_path):
    """pykrete's success_exit_codes widening must not leak to other CLIs."""
    r, out_dir, _ = _spawn(tmp_path, env_extra={"FAKE_GROK_RC": "3"})
    assert r.returncode == 1
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["ok"] is False


def test_short_output_fails_on_byte_floor(tmp_path):
    r, out_dir, _ = _spawn(tmp_path, env_extra={"FAKE_GROK_SHORT": "1"})
    assert r.returncode == 1
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["ok"] is False
    assert "50" in state["error"]      # byte floor, not exit code


def test_non_endturn_stop_reason_is_a_recorded_failure(tmp_path):
    """rc 0 and a well-formed, >50-byte `## Summary` body are not sufficient:
    a refusal/abort surfaces only via the `end` event's stopReason. Without
    wiring GrokAdapter.last_error into classification, this run would be
    recorded ok:true — a refusal persisted as a successful review."""
    r, out_dir, _ = _spawn(tmp_path, env_extra={"FAKE_GROK_STOP_REASON": "PermissionDenied"})
    assert r.returncode == 1
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["ok"] is False
    assert "PermissionDenied" in state["error"]
