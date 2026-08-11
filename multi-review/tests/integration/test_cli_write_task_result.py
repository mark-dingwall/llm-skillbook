import json
import os
import subprocess
from pathlib import Path


REVIEW_TEXT = "## Summary\nFoo bar\n## Concerns\n- bug\n"


def _run(args: list[str]):
    return subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.write_task_result", *args],
        capture_output=True, text=True, env=os.environ.copy(),
    )


def test_write_task_result_review_mode(tmp_path):
    text_file = tmp_path / "claude.txt"
    text_file.write_text(REVIEW_TEXT)
    out_dir = tmp_path / "reviews"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "3.5",
        "--task-mode", "review",
        "--model", "claude-opus-4-7",
    ])
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["ok"] is True

    review_path = Path(payload["review_path"])
    state_path = Path(payload["state_path"])
    assert review_path == out_dir / "claude.md"
    assert state_path == out_dir / "claude.state.json"
    assert review_path.read_text() == REVIEW_TEXT.strip()

    state = json.loads(state_path.read_text())
    assert state == {
        "cli": "claude",
        "ok": True,
        "duration_seconds": 3.5,
        "stderr_tail": "",
        "usage": None,
        "final_model": "claude-opus-4-7",
    }


def test_write_task_result_review_mode_no_model_defaults_attempt(tmp_path):
    text_file = tmp_path / "claude.txt"
    text_file.write_text(REVIEW_TEXT)
    out_dir = tmp_path / "reviews"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "1.0",
        "--task-mode", "review",
    ])
    assert r.returncode == 0, r.stderr
    state = json.loads((out_dir / "claude.state.json").read_text())
    assert "attempts" not in state
    assert state["final_model"] is None


def test_write_task_result_synthesize_mode(tmp_path):
    text_file = tmp_path / "synth.txt"
    synth_text = "### Headline\nLooks fine.\n"
    text_file.write_text(synth_text)
    out_dir = tmp_path / "session"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "8.1",
        "--task-mode", "synthesize",
        "--model", "claude-opus-4-7",
    ])
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["ok"] is True

    synth_path = Path(payload["synth_path"])
    state_path = Path(payload["state_path"])
    assert synth_path == out_dir / "synth.txt"
    assert state_path == out_dir / "synth.state.json"
    assert synth_path.read_text() == synth_text

    state = json.loads(state_path.read_text())
    assert state == {
        "cli": "claude",
        "ok": True,
        "duration_seconds": 8.1,
        "stderr_tail": "",
        "usage": None,
        "final_model": "claude-opus-4-7",
        "body": synth_text,
        "suggested_filename": None,
    }


def test_write_task_result_parses_filename(tmp_path):
    text = "Some headline.\n\nBody text.\n\n<filename>auth-review.md</filename>\n"
    text_file = tmp_path / "raw.txt"
    text_file.write_text(text)
    out_dir = tmp_path / "session"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "5.0",
        "--task-mode", "synthesize",
    ])
    assert r.returncode == 0, r.stderr

    state = json.loads((out_dir / "synth.state.json").read_text())
    assert state["body"] == "Some headline.\n\nBody text."
    assert state["suggested_filename"] == "auth-review.md"

    synth_path = out_dir / "synth.txt"
    assert synth_path.read_text() == "Some headline.\n\nBody text."


def test_write_task_result_no_filename_tag(tmp_path):
    text = "Some headline.\n\nBody text.\n"
    text_file = tmp_path / "raw.txt"
    text_file.write_text(text)
    out_dir = tmp_path / "session"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "5.0",
        "--task-mode", "synthesize",
    ])
    assert r.returncode == 0, r.stderr

    state = json.loads((out_dir / "synth.state.json").read_text())
    assert state["body"] == text
    assert state["suggested_filename"] is None


def test_review_trims_preamble_to_summary(tmp_path):
    text = (
        "I will read the file at /x.\nLet me reason first.\n\n"
        "## Summary\nThe code is fine.\n\n## Warnings\n- something\n"
    )
    text_file = tmp_path / "claude.txt"
    text_file.write_text(text)
    out_dir = tmp_path / "reviews"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "2.0",
        "--task-mode", "review",
    ])
    assert r.returncode == 0, r.stderr

    body = (out_dir / "claude.md").read_text()
    assert body.startswith("## Summary")
    assert "I will read the file" not in body


def test_review_without_summary_kept_raw(tmp_path):
    text = "No heading here, just prose about the code."
    text_file = tmp_path / "claude.txt"
    text_file.write_text(text)
    out_dir = tmp_path / "reviews"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "2.0",
        "--task-mode", "review",
    ])
    assert r.returncode == 0, r.stderr

    body = (out_dir / "claude.md").read_text()
    assert "No heading here" in body


def test_synthesize_output_not_trimmed(tmp_path):
    text = (
        "## Headline\nBoth reviewers agree.\n\n## Agreed Concerns\n- x\n\n"
        "<filename>foo.md</filename>\n"
    )
    text_file = tmp_path / "synth.txt"
    text_file.write_text(text)
    out_dir = tmp_path / "session"

    r = _run([
        "--cli", "claude",
        "--out-dir", str(out_dir),
        "--text-file", str(text_file),
        "--duration-seconds", "2.0",
        "--task-mode", "synthesize",
    ])
    assert r.returncode == 0, r.stderr

    body = (out_dir / "synth.txt").read_text()
    assert body.startswith("## Headline")

    state = json.loads((out_dir / "synth.state.json").read_text())
    assert state["suggested_filename"] == "foo.md"
