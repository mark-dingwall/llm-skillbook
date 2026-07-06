import json
import subprocess
from pathlib import Path

def _run(*args):
    return subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.harvest_row", *args],
        capture_output=True, text=True,
    )

def test_harvest_row_appends(tmp_path):
    row_in = tmp_path / "row.json"
    row_in.write_text(json.dumps({
        "schema_version": 2, "run_id": "r1", "project": "p", "mode": "inline",
    }))
    log = tmp_path / "runs.jsonl"
    r = _run("--row-file", str(row_in), "--log", str(log))
    assert r.returncode == 0, r.stderr
    assert log.exists()
    line = json.loads(log.read_text().splitlines()[0])
    assert line["run_id"] == "r1"

def test_flush_pending_drains_all(tmp_path):
    pending = tmp_path / ".multi-review" / "pending-harvest"
    pending.mkdir(parents=True)
    (pending / "r1.json").write_text(json.dumps({
        "schema_version": 2, "run_id": "r1", "project": "p", "mode": "inline",
    }))
    (pending / "r2.json").write_text(json.dumps({
        "schema_version": 2, "run_id": "r2", "project": "p", "mode": "reference",
    }))
    log = tmp_path / "runs.jsonl"
    r = _run("--flush-pending", "--log", str(log), "--pending-dir", str(pending))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out == {"flushed": 2, "remaining": 0}
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert sorted(r["run_id"] for r in rows) == ["r1", "r2"]
    assert list(pending.glob("*.json")) == []

def test_flush_pending_unwritable_log_keeps_pending(tmp_path):
    pending = tmp_path / ".multi-review" / "pending-harvest"
    pending.mkdir(parents=True)
    (pending / "r1.json").write_text(json.dumps({"schema_version": 2, "run_id": "r1"}))
    (pending / "r2.json").write_text(json.dumps({"schema_version": 2, "run_id": "r2"}))
    # log path under a read-only parent
    ro_parent = tmp_path / "ro"
    ro_parent.mkdir()
    ro_parent.chmod(0o500)
    log = ro_parent / "runs.jsonl"
    try:
        r = _run("--flush-pending", "--log", str(log), "--pending-dir", str(pending))
        assert r.returncode == 1
        assert len(list(pending.glob("*.json"))) == 2
    finally:
        ro_parent.chmod(0o700)

def test_flush_pending_skips_corrupt_file(tmp_path):
    pending = tmp_path / ".multi-review" / "pending-harvest"
    pending.mkdir(parents=True)
    (pending / "r1.json").write_text(json.dumps({
        "schema_version": 2, "run_id": "r1", "project": "p", "mode": "inline",
    }))
    corrupt = pending / "bad.json"
    corrupt.write_text("{not json")
    log = tmp_path / "runs.jsonl"
    r = _run("--flush-pending", "--log", str(log), "--pending-dir", str(pending))
    assert r.returncode == 0, r.stderr
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert [row["run_id"] for row in rows] == ["r1"]
    # corrupt file left in place for inspection
    assert corrupt.exists()

def test_row_file_and_flush_pending_mutually_exclusive(tmp_path):
    r = _run("--row-file", "x.json", "--flush-pending", "--log", "l.jsonl")
    assert r.returncode == 2
