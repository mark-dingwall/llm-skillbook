# tests/integration/test_cli_prepare.py
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

def test_prepare_writes_prompt(tmp_path):
    src = tmp_path / "a.py"
    src.write_text("print('hi')\n")
    pf = tmp_path / "prompt.yaml"
    pf.write_text(f"""
prompt_format_version: 2
task: code
files: ["{src}"]
""")
    out_dir = tmp_path / "run"
    out_dir.mkdir()
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.prepare",
         "--prompt-file", str(pf), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    assert Path(j["prompt_path"]).exists()
    body = Path(j["prompt_path"]).read_text()
    assert str(src.resolve()) in body
    assert "print('hi')" not in body


def test_prepare_resolves_relative_paths_against_promptfile_dir(tmp_path):
    """Relative paths in the promptfile must be anchored to the promptfile's
    parent dir, not the invoking cwd. Authoring-time UX: a YAML can name
    `./src/foo.py` regardless of where prepare is called from."""
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "foo.py").write_text("print('relative-anchored')\n")
    pf = proj / "prompt.yaml"
    pf.write_text(
        "prompt_format_version: 2\n"
        "task: code\n"
        "files: [\"./src/foo.py\"]\n"
    )
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    out_dir = tmp_path / "run"
    out_dir.mkdir()

    project_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(project_root)}
    r = subprocess.run(
        [sys.executable, "-m", "multi_review.cli.prepare",
         "--prompt-file", str(pf), "--out-dir", str(out_dir)],
        capture_output=True, text=True, cwd=str(other_cwd), env=env,
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    body = Path(j["prompt_path"]).read_text()
    assert "relative-anchored" not in body
    expected_abs = (proj / "src" / "foo.py").resolve()
    assert f"- {expected_abs}" in body


def test_prepare_passes_absolute_paths_through_unchanged(tmp_path):
    src = tmp_path / "abs_input.py"
    src.write_text("print('absolute')\n")
    pf_dir = tmp_path / "subdir"
    pf_dir.mkdir()
    pf = pf_dir / "prompt.yaml"
    pf.write_text(
        "prompt_format_version: 2\n"
        "task: code\n"
        f"files: [\"{src}\"]\n"
    )
    out_dir = tmp_path / "run"
    out_dir.mkdir()
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.prepare",
         "--prompt-file", str(pf), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    body = Path(json.loads(r.stdout)["prompt_path"]).read_text()
    assert "print('absolute')" not in body
    assert f"- {src.resolve()}" in body


def test_prepare_removed_key_returns_json_error(tmp_path):
    src = tmp_path / "a.py"
    src.write_text("print('hi')\n")
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(
        "prompt_format_version: 2\n"
        "task: code\n"
        f"files: [\"{src}\"]\n"
        "mode: \"\"\n"
    )

    result = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.prepare",
         "--prompt-file", str(prompt), "--out-dir", str(tmp_path / "run")],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["ok"] is False
    assert "mode" in payload["error"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions required")
def test_prepare_rejects_unreadable_input_before_writing_prompt(tmp_path):
    src = tmp_path / "unreadable.py"
    src.write_text("SECRET_BODY_MUST_NOT_BE_INLINED\n")
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(
        "prompt_format_version: 2\n"
        "task: code\n"
        f"files: [\"{src}\"]\n"
    )
    out_dir = tmp_path / "run"
    src.chmod(0)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "multi_review.cli.prepare",
             "--prompt-file", str(prompt), "--out-dir", str(out_dir)],
            capture_output=True,
            text=True,
        )
    finally:
        src.chmod(0o600)

    assert result.returncode == 1
    assert "cannot read input file" in result.stderr
    assert not (out_dir / "prompt.txt").exists()
