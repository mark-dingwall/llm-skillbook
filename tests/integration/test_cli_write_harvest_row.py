"""Integration tests for cli/write_harvest_row.py."""
import json
import os
import stat
from pathlib import Path

from multi_review.cli.write_harvest_row import main


def _make_state(state_dir: Path, cli: str, ok: bool = True, duration: float = 5.0,
                started_at: str = "2026-06-19T10:00:00Z",
                finished_at: str = "2026-06-19T10:00:05Z") -> None:
    (state_dir / f"{cli}.state.json").write_text(json.dumps({
        "cli": cli,
        "ok": ok,
        "duration_seconds": duration,
        "stderr_tail": "",
        "usage": {"input_tokens": 10, "output_tokens": 20, "cached_tokens": 0, "tool_calls": 0},
        "final_model": "test-model",
        "started_at": started_at,
        "finished_at": finished_at,
    }))


def test_write_harvest_row_appends_to_log(tmp_path):
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _make_state(state_dir, "claude")

    review = tmp_path / "REVIEW.md"
    review.write_text("# Review\nsome content")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Review this.")
    log = tmp_path / "runs.jsonl"

    rc = main([
        "--state-dir", str(state_dir),
        "--out-review", str(review),
        "--prompt-file", str(prompt),
        "--run-id", "r1",
        "--log", str(log),
        "--mode", "inline",
        "--project", "test",
        "--task", "code",
    ])
    assert rc == 0
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["run_id"] == "r1"
    assert row["schema_version"] == 2
    assert row["mode"] == "inline"
    assert row["project"] == "test"
    assert row["task"] == "code"
    assert "started_at" in row
    assert "finished_at" in row
    assert "prompt_bytes" in row
    assert "output_bytes" in row
    assert "usage_by_reviewer" in row
    assert "usage" in row


def test_write_harvest_row_appends_second_row(tmp_path):
    """Second call appends; file grows to 2 lines."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _make_state(state_dir, "claude")

    review = tmp_path / "REVIEW.md"
    review.write_text("content")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("prompt")
    log = tmp_path / "runs.jsonl"

    common = [
        "--state-dir", str(state_dir),
        "--out-review", str(review),
        "--prompt-file", str(prompt),
        "--log", str(log),
        "--mode", "inline",
        "--project", "p",
        "--task", "code",
    ]
    assert main(["--run-id", "r1"] + common) == 0
    assert main(["--run-id", "r2"] + common) == 0
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0]["run_id"] == "r1"
    assert rows[1]["run_id"] == "r2"


def test_write_harvest_row_usage_none_state(tmp_path):
    """State with usage=None must not crash (guarded in build_row)."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    (state_dir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "duration_seconds": 3.0,
        "stderr_tail": "", "usage": None, "final_model": None,
        "started_at": "2026-06-19T10:00:00Z",
        "finished_at": "2026-06-19T10:00:03Z",
    }))
    review = tmp_path / "REVIEW.md"
    review.write_text("content")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("prompt")
    log = tmp_path / "runs.jsonl"

    rc = main([
        "--state-dir", str(state_dir),
        "--out-review", str(review),
        "--prompt-file", str(prompt),
        "--run-id", "r1",
        "--log", str(log),
        "--mode", "inline",
        "--project", "p",
        "--task", "code",
    ])
    assert rc == 0
    row = json.loads(log.read_text().splitlines()[0])
    assert row["usage_by_reviewer"]["claude"]["input_tokens"] == 0


def test_write_harvest_row_no_timestamps_gives_none(tmp_path):
    """State without started_at/finished_at → row timestamps None, wall_seconds None, no argv."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    # Write state without any timestamp fields
    (state_dir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "duration_seconds": 5.0,
        "stderr_tail": "", "usage": None, "final_model": None,
    }))
    review = tmp_path / "REVIEW.md"
    review.write_text("content")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("prompt")
    log = tmp_path / "runs.jsonl"

    rc = main([
        "--state-dir", str(state_dir),
        "--out-review", str(review),
        "--prompt-file", str(prompt),
        "--run-id", "r-notimestamp",
        "--log", str(log),
        "--mode", "inline",
        "--project", "p",
        "--task", "code",
    ])
    assert rc == 0
    row = json.loads(log.read_text().splitlines()[0])
    assert row["started_at"] is None
    assert row["finished_at"] is None
    assert row["wall_seconds"] is None
    assert "argv" not in row


def test_write_harvest_row_falls_back_to_pending_on_perm_denied(tmp_path, monkeypatch):
    """PermissionError on --log path falls back to pending-harvest, returns 0."""
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    _make_state(state_dir, "claude")

    review = tmp_path / "REVIEW.md"
    review.write_text("content")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("prompt")

    # Change cwd so pending-harvest lands under tmp_path
    monkeypatch.chdir(tmp_path)

    rc = main([
        "--state-dir", str(state_dir),
        "--out-review", str(review),
        "--prompt-file", str(prompt),
        "--run-id", "test-run-1",
        "--log", "/proc/1/no-write",
        "--mode", "inline",
        "--project", "p",
        "--task", "code",
    ])
    assert rc == 0
    pending = tmp_path / ".multi-review" / "pending-harvest"
    pending_files = list(pending.glob("*.json"))
    assert len(pending_files) == 1
    row = json.loads(pending_files[0].read_text())
    assert row["run_id"] == "test-run-1"
