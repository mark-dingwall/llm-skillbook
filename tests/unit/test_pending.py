import pytest
from pathlib import Path
from multi_review.core.pending import (
    PendingPair, write_meta, read_meta, transition_status,
    list_pending, sweep_expired, PENDING_TTL_DAYS,
)

def test_write_then_read_roundtrip(tmp_path):
    meta = PendingPair(
        pair_id="pair-1", pass1_run_id="r1", pass2_run_id=None,
        modes={"pass1": "reference", "pass2": "inline"},
        prompt_file="auth.yaml", status="awaiting-pass-2",
        delay_type="background", notification_task_id=None,
        created_iso="2026-05-15T00:00:00Z", git_head="abc", git_dirty=False,
        if_drift="ask",
    )
    write_meta(tmp_path, meta)
    got = read_meta(tmp_path, "pair-1")
    assert got.pair_id == "pair-1"
    assert got.modes["pass1"] == "reference"

def test_transition_status_atomic_blocks_double(tmp_path):
    meta = PendingPair(
        pair_id="pair-2", pass1_run_id="r1", pass2_run_id=None,
        modes={"pass1": "inline", "pass2": "reference"},
        prompt_file=None, status="awaiting-pass-2",
        delay_type="foreground", notification_task_id=None,
        created_iso="2026-05-15T00:00:00Z", git_head=None, git_dirty=False,
        if_drift="ignore",
    )
    write_meta(tmp_path, meta)
    ok = transition_status(tmp_path, "pair-2", expected="awaiting-pass-2", new="resuming")
    assert ok is True
    # Second attempt must fail
    ok2 = transition_status(tmp_path, "pair-2", expected="awaiting-pass-2", new="resuming")
    assert ok2 is False

def test_list_pending(tmp_path):
    for i in range(3):
        write_meta(tmp_path, PendingPair(
            pair_id=f"pair-{i}", pass1_run_id=f"r{i}", pass2_run_id=None,
            modes={}, prompt_file=None, status="awaiting-pass-2",
            delay_type="background", notification_task_id=None,
            created_iso="2026-05-15T00:00:00Z", git_head=None, git_dirty=False,
            if_drift="ignore",
        ))
    pairs = list_pending(tmp_path)
    assert len(pairs) == 3

def test_sweep_expired_removes_old(tmp_path, monkeypatch):
    write_meta(tmp_path, PendingPair(
        pair_id="pair-old", pass1_run_id="r1", pass2_run_id=None,
        modes={}, prompt_file=None, status="awaiting-pass-2",
        delay_type="background", notification_task_id=None,
        created_iso="2020-01-01T00:00:00Z", git_head=None, git_dirty=False,
        if_drift="ignore",
    ))
    swept = sweep_expired(tmp_path)
    assert "pair-old" in swept
    assert not (tmp_path / "pair-old").exists()
