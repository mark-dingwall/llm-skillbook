# tests/integration/test_cli_prepare.py
import json
import subprocess
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
