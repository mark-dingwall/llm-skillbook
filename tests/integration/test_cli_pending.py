# tests/integration/test_cli_pending.py
import json
import subprocess
from pathlib import Path


def _full_meta(pair_id="pair-abc123"):
    return {
        "pair_id": pair_id,
        "pass1_run_id": "run-1",
        "pass2_run_id": None,
        "modes": {"pass1": "inline", "pass2": "reference"},
        "prompt_file": "prompts/auth.yaml",
        "status": "awaiting-pass-2",
        "delay_type": "foreground",
        "notification_task_id": None,
        "created_iso": "2026-05-19T10:00:00Z",
        "git_head": "deadbeef",
        "git_dirty": False,
        "if_drift": "ask",
    }


def test_pending_write_creates_meta_yaml(tmp_path):
    pending_dir = tmp_path / "pending"
    meta_file = tmp_path / "meta.json"
    meta = _full_meta()
    meta_file.write_text(json.dumps(meta))

    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.pending", "write",
         "--pending-dir", str(pending_dir), "--meta-file", str(meta_file)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["ok"] is True
    assert out["pair_id"] == meta["pair_id"]
    assert (pending_dir / meta["pair_id"] / "meta.yaml").exists()


def test_pending_write_round_trips_through_read(tmp_path):
    pending_dir = tmp_path / "pending"
    meta_file = tmp_path / "meta.json"
    meta = _full_meta(pair_id="pair-rt")
    meta_file.write_text(json.dumps(meta))

    w = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.pending", "write",
         "--pending-dir", str(pending_dir), "--meta-file", str(meta_file)],
        capture_output=True, text=True,
    )
    assert w.returncode == 0, w.stderr

    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.pending", "read",
         "--pending-dir", str(pending_dir), "--pair-id", meta["pair_id"]],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    read_back = json.loads(r.stdout)
    for k, v in meta.items():
        assert read_back[k] == v, f"field {k} drifted: {read_back[k]!r} != {v!r}"
