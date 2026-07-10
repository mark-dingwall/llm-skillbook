# tests/integration/test_cli_prepare.py
import json
import subprocess
import sys
from pathlib import Path

def test_prepare_writes_prompt(tmp_path):
    src = tmp_path / "a.py"
    src.write_text("print('hi')\n")
    pf = tmp_path / "prompt.yaml"
    pf.write_text(f"""
prompt_format_version: 1
task: code
files: ["{src}"]
mode: inline
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
    assert "print('hi')" in body


def test_prepare_resolves_relative_paths_against_promptfile_dir(tmp_path):
    """Relative paths in the promptfile must be anchored to the promptfile's
    parent dir, not the invoking cwd. Authoring-time UX: a YAML can name
    `./src/foo.py` regardless of where prepare is called from."""
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "foo.py").write_text("print('relative-anchored')\n")
    pf = proj / "prompt.yaml"
    pf.write_text(
        "prompt_format_version: 1\n"
        "task: code\n"
        "files: [\"./src/foo.py\"]\n"
        "mode: inline\n"
    )
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    out_dir = tmp_path / "run"
    out_dir.mkdir()

    import os
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
    assert "relative-anchored" in body
    expected_abs = (proj / "src" / "foo.py").resolve()
    assert f'path="{expected_abs}"' in body


def test_prepare_passes_absolute_paths_through_unchanged(tmp_path):
    src = tmp_path / "abs_input.py"
    src.write_text("print('absolute')\n")
    pf_dir = tmp_path / "subdir"
    pf_dir.mkdir()
    pf = pf_dir / "prompt.yaml"
    pf.write_text(
        "prompt_format_version: 1\n"
        "task: code\n"
        f"files: [\"{src}\"]\n"
        "mode: inline\n"
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
    assert "absolute" in body
    assert f'path="{src.resolve()}"' in body
