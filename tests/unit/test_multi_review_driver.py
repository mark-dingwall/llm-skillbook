import importlib.util
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_driver():
    spec = importlib.util.spec_from_file_location("mr_driver", REPO_ROOT / "multi_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = _load_driver()


def _write_promptfile(tmp_path: Path, body: str) -> Path:
    """Write a prompt YAML plus the one input file it references."""
    (tmp_path / "target.py").write_text("def f():\n    return 1\n")
    pf = tmp_path / "prompt.yaml"
    pf.write_text(textwrap.dedent(body))
    return pf


BASE_YAML = """\
    prompt_format_version: 1
    task: code
    files: [target.py]
    reviewers: [codex]
    synthesizer: none
"""


def test_out_dir_created_when_missing(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert (out / "prompt.txt").exists()


def test_prompt_txt_contains_the_input_file_body(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert "return 1" in (out / "prompt.txt").read_text()


def test_non_empty_out_dir_is_rejected(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    (out / "REVIEW.md").write_text("stale")
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_empty_out_dir_is_accepted(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert (out / "prompt.txt").exists()


def test_mode_both_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML + "    mode: both\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_malformed_yaml_exits_2_without_traceback(tmp_path):
    pf = _write_promptfile(tmp_path, "    task: [unclosed\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_unknown_top_level_key_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML + "    bogus_field: 3\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_missing_prompt_file_exits_2(tmp_path):
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(tmp_path / "nope.yaml"), "--out-dir", str(out)]) == 2


def test_schema_violation_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML.replace("task: code", "task: nonsense"))
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_validation_failure_does_not_create_out_dir(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML.replace("task: code", "task: nonsense"))
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    assert not out.exists()


def test_unreadable_input_file_exits_1(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"

    def _boom(*args, **kwargs):
        raise SystemExit("error: cannot read target.py")

    monkeypatch.setattr(driver, "build_prompt", _boom)
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_prompt_output_write_failure_exits_1_without_traceback(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    real_write_text = Path.write_text

    def _write(path, text, *args, **kwargs):
        if path.name == "prompt.txt":
            raise OSError("read-only output")
        return real_write_text(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _write)
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_argparse_usage_error_raises_systemexit(tmp_path):
    with pytest.raises(SystemExit):
        driver.main(["--prompt-file", "only-one-arg"])
