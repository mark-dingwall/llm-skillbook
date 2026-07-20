# tests/integration/test_cli_validate_prompt.py
import json
import subprocess
from pathlib import Path

from multi_review.core.reviewers import DEFAULT_REVIEWERS

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

def test_validate_defaults_reviewers_and_synthesizer_are_not_poisoned():
    """`resolved.reviewers`/`resolved.synthesizer` are SKILL.md Step 2's sole
    source of the run set (see test_skill_step2_pins_resolved_sole_source_provenance).
    The CLI just does `print(json.dumps({"ok": True, "resolved": asdict(pf)}))` —
    nothing asserted `resolved` actually matches the fill_defaults() output for
    a prompt file that omits `reviewers`/`synthesizer`. Inserting
    `pf.reviewers = [...all six...]` and `pf.synthesizer = "grok"` immediately
    before the `asdict(pf)` call passed every prior test in this file, since
    the only prior assertion was on `resolved["task"]`.
    """
    r = _run(str(FIX / "defaults.yaml"))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["resolved"]["reviewers"] == DEFAULT_REVIEWERS
    assert "grok" not in out["resolved"]["reviewers"]
    assert out["resolved"]["synthesizer"] == "claude"


def test_validate_invalid_returns_2_with_error():
    r = _run(str(FIX / "missing_files.yaml"))
    assert r.returncode == 2
    out = json.loads(r.stdout)
    assert out["ok"] is False
    assert "files" in out["error"].lower()
