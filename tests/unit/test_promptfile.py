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
    assert pf.reviewers == ["claude", "agy"]
    assert pf.synthesizer == "agy"  # agy is a valid synthesizer post-migration

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
    assert pf.reviewers == ["claude", "agy", "codex", "opencode", "pykrete"]
    assert pf.synthesizer == "claude"
    assert pf.harvest is True
    assert pf.if_drift == "ignore"

def test_pykrete_valid_and_defaulted(tmp_path):
    f = tmp_path / "x.py"; f.write_text("")
    base = {"prompt_format_version": 1, "task": "code", "files": [str(f)]}
    pf = fill_defaults({**base, "reviewers": ["pykrete"], "synthesizer": "pykrete",
                        "models": {"pykrete": "glm"}})
    validate(pf, tmp_path)                               # must NOT raise: pykrete is a KNOWN/valid choice
    assert pf.reviewers == ["pykrete"]
    pf2 = fill_defaults(base)                            # omit reviewers -> defaults
    validate(pf2, tmp_path)
    assert "pykrete" in pf2.reviewers                    # default-on

def test_agy_is_known_reviewer_and_synthesizer(tmp_path):
    src = tmp_path / "x.py"
    src.write_text("")
    p = tmp_path / "p.yaml"
    p.write_text(
        f"prompt_format_version: 1\ntask: code\nfiles: [{src}]\nmode: inline\n"
        "reviewers: [claude, agy]\nsynthesizer: agy\n"
    )
    pf = load_promptfile(p)  # must not raise
    assert pf.reviewers == ["claude", "agy"]
    assert pf.synthesizer == "agy"

def test_dead_fallback_delay_schema_removed():
    """Phase-1 deleted the capacity-fallback subsystem. PromptFile no longer carries
    fallback_models/delay/delay_type, and passing those legacy keys is rejected."""
    pf = fill_defaults({"prompt_format_version": 1, "task": "code", "files": ["x.py"], "mode": "inline"})
    assert not hasattr(pf, "fallback_models")
    assert not hasattr(pf, "delay")
    assert not hasattr(pf, "delay_type")
    for legacy in ("fallback_models", "delay", "delay_type"):
        with pytest.raises(TypeError):  # PromptFile(**raw) rejects unknown kwarg
            fill_defaults({
                "prompt_format_version": 1, "task": "code", "files": ["x.py"],
                "mode": "inline", legacy: {} if legacy == "fallback_models" else 1,
            })

def test_invalid_enum_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("prompt_format_version: 1\ntask: bogus\nfiles: [x.py]\nmode: inline\n")
    with pytest.raises(ValidationError):
        load_promptfile(p)

def test_legacy_delay_key_rejected(tmp_path):
    """A stale prompt file carrying the removed `delay` key must not load silently."""
    p = tmp_path / "p.yaml"
    src = tmp_path / "x.py"
    src.write_text("")
    p.write_text(f"prompt_format_version: 1\ntask: code\nfiles: [{src}]\nmode: inline\ndelay: 1800\n")
    with pytest.raises(TypeError):
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
