"""tests/integration/test_cli_build_synth_input.py"""
import json
import pytest
from pathlib import Path

from multi_review.cli.build_synth_input import main


def _write_state(state_dir: Path, cli: str, ok: bool, body: str | None = None) -> None:
    state = {"cli": cli, "ok": ok, "duration_seconds": 1.0, "stderr_tail": "", "usage": None, "final_model": None}
    if body is not None:
        state["body"] = f"## Summary\n\n{body}"
    (state_dir / f"{cli}.state.json").write_text(json.dumps(state))


def test_build_synth_input_writes_prompt_and_nonce_from_inline_body(tmp_path):
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _write_state(state_dir, "claude", True, body="claude's review")
    _write_state(state_dir, "codex", True, body="codex's review")

    out_prompt = tmp_path / "synth-prompt.md"
    out_nonce = tmp_path / "nonce.txt"

    rc = main(["--state-dir", str(state_dir),
               "--out-prompt-file", str(out_prompt),
               "--out-nonce-file", str(out_nonce)])
    assert rc == 0

    nonce = out_nonce.read_text().strip()
    prompt = out_prompt.read_text()
    assert nonce in prompt
    assert "claude's review" in prompt
    assert "codex's review" in prompt


def test_build_synth_input_reads_body_from_sibling_md_file(tmp_path):
    """spawn.py path: no body in state.json; body is in <cli>.md sibling."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    # spawn.py shape — no body field
    _write_state(state_dir, "codex", True)
    (state_dir / "codex.md").write_text("## Summary\n\ncodex body from file")
    _write_state(state_dir, "agy", True)
    (state_dir / "agy.md").write_text("## Summary\n\nagy body from file")

    out_prompt = tmp_path / "synth-prompt.md"
    out_nonce = tmp_path / "nonce.txt"

    rc = main(["--state-dir", str(state_dir),
               "--out-prompt-file", str(out_prompt),
               "--out-nonce-file", str(out_nonce)])
    assert rc == 0

    nonce = out_nonce.read_text().strip()
    prompt = out_prompt.read_text()
    assert nonce in prompt
    assert "codex body from file" in prompt
    assert "agy body from file" in prompt


def test_build_synth_input_skips_failed_reviewers(tmp_path):
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _write_state(state_dir, "claude", True, body="ok review")
    _write_state(state_dir, "codex", False, body="failed review")

    out_prompt = tmp_path / "synth-prompt.md"
    rc = main(["--state-dir", str(state_dir),
               "--out-prompt-file", str(out_prompt)])
    assert rc == 0
    prompt = out_prompt.read_text()
    assert "ok review" in prompt
    assert "failed review" not in prompt


def test_build_synth_input_prints_nonce_to_stdout_when_no_out_nonce_file(tmp_path, capsys):
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _write_state(state_dir, "claude", True, body="review text")
    _write_state(state_dir, "codex", True, body="another review")

    out_prompt = tmp_path / "synth-prompt.md"
    rc = main(["--state-dir", str(state_dir), "--out-prompt-file", str(out_prompt)])
    assert rc == 0

    captured = capsys.readouterr()
    nonce = captured.out.strip()
    assert len(nonce) == 8  # secrets.token_hex(4) = 8 hex chars
    assert nonce in out_prompt.read_text()


def test_build_synth_input_body_field_takes_precedence_over_md_file(tmp_path):
    """If body is in state.json AND a .md sibling exists, state.json body wins."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _write_state(state_dir, "claude", True, body="inline body")
    (state_dir / "claude.md").write_text("file body should be ignored")
    _write_state(state_dir, "codex", True, body="codex inline")

    out_prompt = tmp_path / "synth-prompt.md"
    out_nonce = tmp_path / "nonce.txt"
    rc = main(["--state-dir", str(state_dir),
               "--out-prompt-file", str(out_prompt),
               "--out-nonce-file", str(out_nonce)])
    assert rc == 0
    prompt = out_prompt.read_text()
    assert "inline body" in prompt
    assert "file body should be ignored" not in prompt


def test_build_synth_input_tuple_order_body_nonce(tmp_path):
    """build_synthesis_input returns (body, nonce) — body contains reviewer text."""
    from multi_review.core.synthesis import build_synthesis_input
    from multi_review.core.fanout import ReviewerResult

    r = ReviewerResult(cli="claude", ok=True, text="review text",
                       stderr_tail="", usage=None, elapsed=1.0)
    body, nonce = build_synthesis_input([r])
    # body should contain the review content; nonce should be a short hex token
    assert "review text" in body
    assert len(nonce) == 8


def test_build_synth_input_skips_parseable_invalid_state(tmp_path):
    """Break caught: a truthy non-boolean `ok` admitted an invalid reviewer to synthesis."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _write_state(state_dir, "claude", True, body="qualified review")
    _write_state(state_dir, "codex", True, body="must not reach synthesis")
    state = json.loads((state_dir / "codex.state.json").read_text())
    state["ok"] = "false"
    (state_dir / "codex.state.json").write_text(json.dumps(state))

    out_prompt = tmp_path / "synth-prompt.md"
    rc = main(["--state-dir", str(state_dir), "--out-prompt-file", str(out_prompt)])

    assert rc == 0
    prompt = out_prompt.read_text()
    assert "qualified review" in prompt
    assert "must not reach synthesis" not in prompt


def test_build_synth_input_rechecks_legacy_raw_success(tmp_path):
    """A stale raw-ok state must not reintroduce an unqualified review."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _write_state(state_dir, "claude", True, body="qualified review")
    _write_state(state_dir, "codex", True, body="legacy unstructured review")
    state = json.loads((state_dir / "codex.state.json").read_text())
    state["body"] = "A long response with no structural heading. " * 3
    (state_dir / "codex.state.json").write_text(json.dumps(state))

    out_prompt = tmp_path / "synth-prompt.md"
    rc = main(["--state-dir", str(state_dir), "--out-prompt-file", str(out_prompt)])

    assert rc == 0
    prompt = out_prompt.read_text()
    assert "qualified review" in prompt
    assert "structural heading" not in prompt
