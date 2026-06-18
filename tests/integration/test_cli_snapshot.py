import json
import subprocess
from pathlib import Path

def _run(*args):
    return subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.snapshot", *args],
        capture_output=True, text=True,
    )

def test_create_then_diff_clean(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("v1\n")
    snap = tmp_path / "snap"
    r = _run("create", "--snapshot-dir", str(snap), "--file", str(f))
    assert r.returncode == 0, r.stderr
    r2 = _run("diff", "--snapshot-dir", str(snap), "--file", str(f))
    assert r2.returncode == 0
    assert json.loads(r2.stdout)["status"] == "clean"

def test_diff_drifted(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("v1\n")
    snap = tmp_path / "snap"
    _run("create", "--snapshot-dir", str(snap), "--file", str(f))
    f.write_text("v2\n")
    r = _run("diff", "--snapshot-dir", str(snap), "--file", str(f))
    assert json.loads(r.stdout)["status"] == "drifted"

def test_cleanup_removes(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "y").write_text("z")
    r = _run("cleanup", "--snapshot-dir", str(snap))
    assert r.returncode == 0
    assert not snap.exists()

def test_snapshot_create_no_files(tmp_path):
    snap = tmp_path / "snap"
    r = _run("create", "--snapshot-dir", str(snap))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["ok"] is True
