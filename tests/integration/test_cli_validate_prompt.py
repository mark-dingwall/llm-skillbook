# tests/integration/test_cli_validate_prompt.py
import json
import subprocess
from pathlib import Path

FIX = Path(__file__).parent.parent / "fixtures" / "prompts"

def _run(*args):
    return subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.validate_prompt", *args],
        capture_output=True, text=True,
    )

def test_validate_valid_returns_0_and_json():
    r = _run(str(FIX / "valid.yaml"))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["ok"] is True
    assert out["resolved"]["task"] == "code"

def test_validate_invalid_returns_2_with_error():
    r = _run(str(FIX / "missing_files.yaml"))
    assert r.returncode == 2
    out = json.loads(r.stdout)
    assert out["ok"] is False
    assert "files" in out["error"].lower()
