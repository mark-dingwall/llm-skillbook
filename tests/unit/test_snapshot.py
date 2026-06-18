# tests/unit/test_snapshot.py
from pathlib import Path
from multi_review.core.snapshot import (
    create_snapshot, diff_snapshot, cleanup_snapshot, SnapshotDiff,
)

def test_create_snapshot_copies_files(tmp_path):
    src = tmp_path / "src.py"
    src.write_text("v1\n")
    snap_dir = tmp_path / "snap"
    create_snapshot(files=[src], context_files=[], snapshot_dir=snap_dir)
    snapped = snap_dir / src.resolve().relative_to(src.resolve().anchor)
    assert snapped.exists() or any(snap_dir.rglob("src.py"))

def test_snapshot_includes_context_files(tmp_path):
    src = tmp_path / "src.py"
    src.write_text("code v1\n")
    ctx = tmp_path / "threat_model.md"
    ctx.write_text("threats v1\n")
    snap_dir = tmp_path / "snap"
    create_snapshot(files=[src], context_files=[ctx], snapshot_dir=snap_dir)
    # Drift in either is detected.
    ctx.write_text("threats v2\n")
    diff = diff_snapshot(files=[src], context_files=[ctx], snapshot_dir=snap_dir)
    assert diff.status == "drifted"
    assert any(str(ctx.resolve()) == p for p in diff.changed_files)

def test_diff_clean_when_unchanged(tmp_path):
    src = tmp_path / "src.py"
    src.write_text("v1\n")
    snap_dir = tmp_path / "snap"
    create_snapshot(files=[src], context_files=[], snapshot_dir=snap_dir)
    diff = diff_snapshot(files=[src], context_files=[], snapshot_dir=snap_dir)
    assert diff.status == "clean"
    assert diff.changed_files == []

def test_diff_detects_modified(tmp_path):
    src = tmp_path / "src.py"
    src.write_text("v1\n")
    snap_dir = tmp_path / "snap"
    create_snapshot(files=[src], snapshot_dir=snap_dir)
    src.write_text("v2\n")
    diff = diff_snapshot(files=[src], snapshot_dir=snap_dir)
    assert diff.status == "drifted"
    assert src.resolve() in [Path(p) for p in diff.changed_files]

def test_diff_detects_deleted(tmp_path):
    src = tmp_path / "src.py"
    src.write_text("v1\n")
    snap_dir = tmp_path / "snap"
    create_snapshot(files=[src], snapshot_dir=snap_dir)
    src.unlink()
    diff = diff_snapshot(files=[src], snapshot_dir=snap_dir)
    assert diff.status == "drifted"

def test_diff_snapshot_detects_added(tmp_path):
    a = tmp_path / "a.py"
    a.write_text("v1\n")
    snap_dir = tmp_path / "snap"
    create_snapshot(files=[a], snapshot_dir=snap_dir)
    # b.py appears after snapshot — should be reported as added
    b = tmp_path / "b.py"
    b.write_text("new\n")
    diff = diff_snapshot(files=[a, b], snapshot_dir=snap_dir)
    assert diff.status == "drifted"
    assert str(b.resolve()) in diff.added_files


def test_cleanup_removes_dir(tmp_path):
    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    (snap_dir / "x").write_text("y")
    cleanup_snapshot(snap_dir)
    assert not snap_dir.exists()
