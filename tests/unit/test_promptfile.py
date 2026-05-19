# tests/unit/test_promptfile.py
from pathlib import Path
import pytest
from multi_review.core.promptfile import (
    PromptFile, load_promptfile, validate, fill_defaults, ValidationError,
)

FIX = Path(__file__).parent.parent / "fixtures" / "prompts"

def test_load_valid_roundtrip():
    pf = load_promptfile(FIX / "valid.yaml")
    assert pf.task == "code"
    assert pf.mode == "reference"
    assert pf.reviewers == ["claude", "gemini"]

def test_validate_missing_files_fails():
    with pytest.raises(ValidationError) as e:
        load_promptfile(FIX / "missing_files.yaml")
    assert "files" in str(e.value).lower()

def test_validate_custom_task_requires_body():
    with pytest.raises(ValidationError) as e:
        load_promptfile(FIX / "custom_task_missing_body.yaml")
    assert "custom_prompt" in str(e.value)

def test_fill_defaults_populates_missing():
    raw = {"prompt_format_version": 1, "task": "code", "files": ["x.py"], "mode": "inline"}
    pf = fill_defaults(raw)
    assert pf.reviewers == ["claude", "gemini", "codex", "opencode"]
    assert pf.synthesizer == "claude"
    assert pf.harvest is True
    assert pf.if_drift == "ignore"
    assert pf.delay_type == "background"

def test_pin_model_with_empty_fallback_chain():
    raw = {
        "prompt_format_version": 1, "task": "code", "files": ["x.py"], "mode": "inline",
        "models": {"gemini": "gemini-3.1-pro"},
        "fallback_models": {"gemini": []},
    }
    pf = fill_defaults(raw)
    assert pf.fallback_models["gemini"] == []

def test_pin_without_fallback_means_no_fallback():
    """Spec §5.4: models.X: Y with absent OR empty fallback_models.X → no fallback."""
    raw_absent = {
        "prompt_format_version": 1, "task": "code", "files": ["x.py"], "mode": "inline",
        "models": {"gemini": "gemini-3.1-pro"},
    }
    pf = fill_defaults(raw_absent)
    assert pf.fallback_models.get("gemini", []) == []

def test_invalid_enum_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("prompt_format_version: 1\ntask: bogus\nfiles: [x.py]\nmode: inline\n")
    with pytest.raises(ValidationError):
        load_promptfile(p)

def test_negative_delay_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    src = tmp_path / "x.py"
    src.write_text("")
    p.write_text(f"prompt_format_version: 1\ntask: code\nfiles: [{src}]\nmode: inline\ndelay: -5\n")
    with pytest.raises(ValidationError) as e:
        load_promptfile(p)
    assert "delay" in str(e.value).lower()

def test_oversized_delay_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    src = tmp_path / "x.py"
    src.write_text("")
    p.write_text(f"prompt_format_version: 1\ntask: code\nfiles: [{src}]\nmode: inline\ndelay: 100000\n")
    with pytest.raises(ValidationError):
        load_promptfile(p)

def test_missing_required_field_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("prompt_format_version: 1\ntask: code\nmode: inline\n")  # files missing
    with pytest.raises(ValidationError):
        load_promptfile(p)

def test_nonexistent_file_path_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("prompt_format_version: 1\ntask: code\nfiles: [/does/not/exist.py]\nmode: inline\n")
    with pytest.raises(ValidationError) as e:
        load_promptfile(p)
    assert "exist" in str(e.value).lower() or "not found" in str(e.value).lower()

def test_unknown_reviewer_in_models_rejected(tmp_path):
    src = tmp_path / "x.py"
    src.write_text("")
    p = tmp_path / "p.yaml"
    p.write_text(
        f"prompt_format_version: 1\ntask: code\nfiles: [{src}]\nmode: inline\n"
        "models: {made_up_cli: foo}\n"
    )
    with pytest.raises(ValidationError):
        load_promptfile(p)
