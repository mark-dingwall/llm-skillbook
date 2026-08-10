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
    raw = {"prompt_format_version": 2, "task": "code", "files": ["x.py"]}
    pf = fill_defaults(raw)
    assert pf.reviewers == ["claude", "agy", "codex", "opencode", "pykrete"]
    assert pf.synthesizer == "claude"


@pytest.mark.parametrize(
    "key,value",
    [
        ("mode", ""),
        ("if_drift", ""),
        ("harvest", False),
        ("output_dir", None),
        ("save_as", None),
        ("model_effort", {}),
    ],
)
def test_promptfile_rejects_removed_key(key, value):
    raw = {"prompt_format_version": 2, "task": "code", "files": ["x.py"], key: value}

    with pytest.raises(ValidationError) as exc:
        fill_defaults(raw)

    message = str(exc.value)
    assert key in message
    assert "v0.3.0" in message


def test_promptfile_reports_all_removed_keys_present_at_once():
    raw = {
        "prompt_format_version": 2,
        "task": "code",
        "files": ["x.py"],
        "model_effort": {},
        "save_as": None,
        "output_dir": None,
        "harvest": False,
        "if_drift": "",
        "mode": "",
    }

    with pytest.raises(ValidationError) as exc:
        fill_defaults(raw)

    assert str(exc.value) == (
        "prompt YAML key(s) removed in v0.3.0, delete before retrying: "
        "mode, if_drift, harvest, output_dir, save_as, model_effort"
    )


def test_omitting_removed_keys_still_validates():
    pf = fill_defaults({"prompt_format_version": 2, "task": "code", "files": ["x.py"]})

    assert pf.task == "code"
    assert pf.files == ["x.py"]


def test_prompt_format_version_1_rejected_even_with_no_removed_keys(tmp_path):
    source = tmp_path / "x.py"
    source.write_text("")
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(f"prompt_format_version: 1\ntask: code\nfiles: [{source}]\n")

    with pytest.raises(ValidationError) as exc:
        load_promptfile(prompt)

    message = str(exc.value)
    assert message == (
        "prompt_format_version: 1 is no longer supported — v0.3 removed inline delivery "
        "and 6 deprecated fields (mode, if_drift, harvest, output_dir, save_as, model_effort). "
        "Set prompt_format_version: 2."
    )
    assert "key(s) removed" not in message

def test_pykrete_valid_and_defaulted(tmp_path):
    f = tmp_path / "x.py"; f.write_text("")
    base = {"prompt_format_version": 2, "task": "code", "files": [str(f)]}
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
        f"prompt_format_version: 2\ntask: code\nfiles: [{src}]\n"
        "reviewers: [claude, agy]\nsynthesizer: agy\n"
    )
    pf = load_promptfile(p)  # must not raise
    assert pf.reviewers == ["claude", "agy"]
    assert pf.synthesizer == "agy"

def test_dead_fallback_delay_schema_removed():
    """Phase-1 deleted the capacity-fallback subsystem. PromptFile no longer carries
    fallback_models/delay/delay_type, and passing those legacy keys is rejected."""
    pf = fill_defaults({"prompt_format_version": 2, "task": "code", "files": ["x.py"]})
    assert not hasattr(pf, "fallback_models")
    assert not hasattr(pf, "delay")
    assert not hasattr(pf, "delay_type")
    for legacy in ("fallback_models", "delay", "delay_type"):
        with pytest.raises(ValidationError):
            fill_defaults({
                "prompt_format_version": 2, "task": "code", "files": ["x.py"],
                legacy: {} if legacy == "fallback_models" else 1,
            })

def test_invalid_enum_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("prompt_format_version: 2\ntask: bogus\nfiles: [x.py]\n")
    with pytest.raises(ValidationError):
        load_promptfile(p)

def test_legacy_delay_key_rejected(tmp_path):
    """A stale prompt file carrying the removed `delay` key must not load silently."""
    p = tmp_path / "p.yaml"
    src = tmp_path / "x.py"
    src.write_text("")
    p.write_text(f"prompt_format_version: 2\ntask: code\nfiles: [{src}]\ndelay: 1800\n")
    with pytest.raises(ValidationError):
        load_promptfile(p)

def test_missing_required_field_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("prompt_format_version: 2\ntask: code\n")  # files missing
    with pytest.raises(ValidationError):
        load_promptfile(p)

def test_nonexistent_file_path_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("prompt_format_version: 2\ntask: code\nfiles: [/does/not/exist.py]\n")
    with pytest.raises(ValidationError) as e:
        load_promptfile(p)
    assert "exist" in str(e.value).lower() or "not found" in str(e.value).lower()


def test_directory_in_required_files_is_rejected(tmp_path):
    source_dir = tmp_path / "source-dir"
    source_dir.mkdir()
    pf = fill_defaults({
        "prompt_format_version": 2,
        "task": "code",
        "files": [str(source_dir)],
    })

    with pytest.raises(ValidationError, match="regular file"):
        validate(pf, base_dir=tmp_path)


@pytest.mark.parametrize("separator", ["\n", "\r"])
def test_line_breaking_required_file_path_is_rejected(tmp_path, separator):
    source = tmp_path / f"line{separator}break.py"
    source.write_text("pass\n")
    pf = fill_defaults({
        "prompt_format_version": 2,
        "task": "code",
        "files": [str(source)],
    })

    with pytest.raises(ValidationError, match="line-breaking characters"):
        validate(pf, base_dir=tmp_path)

def test_unknown_reviewer_in_models_rejected(tmp_path):
    src = tmp_path / "x.py"
    src.write_text("")
    p = tmp_path / "p.yaml"
    p.write_text(
        f"prompt_format_version: 2\ntask: code\nfiles: [{src}]\n"
        "models: {made_up_cli: foo}\n"
    )
    with pytest.raises(ValidationError):
        load_promptfile(p)


def test_dataclass_default_reviewers_excludes_grok():
    """Direct construction bypasses fill_defaults entirely. Without this test,
    leaving PromptFile.reviewers' default_factory on ALL_REVIEWERS would make
    grok auto-selected for every direct PromptFile(...) while every
    fill_defaults-based test still passed."""
    from multi_review.core.promptfile import PromptFile
    from multi_review.core.reviewers import DEFAULT_REVIEWERS
    pf = PromptFile(prompt_format_version=2, task="code", files=["a.py"])
    assert pf.reviewers == DEFAULT_REVIEWERS
    assert "grok" not in pf.reviewers
    # Same opt-in dimension, the SYNTHESIZER: direct construction must not
    # default to grok either.
    assert pf.synthesizer == "claude"
    assert pf.synthesizer != "grok"


def test_grok_omitted_from_filled_defaults():
    from multi_review.core.promptfile import fill_defaults
    pf = fill_defaults({"prompt_format_version": 2, "task": "code",
                        "files": ["a.py"]})
    assert "grok" not in pf.reviewers


def test_grok_is_a_valid_explicit_reviewer_and_synthesizer(tmp_path):
    """fill_defaults does not enforce membership — validate does. Drive validate."""
    from multi_review.core.promptfile import fill_defaults, validate
    (tmp_path / "a.py").write_text("x = 1\n")
    pf = fill_defaults({"prompt_format_version": 2, "task": "code",
                        "files": ["a.py"], "reviewers": ["grok"],
                        "synthesizer": "grok"})
    validate(pf, base_dir=tmp_path)      # must not raise
    assert pf.reviewers == ["grok"]
    assert pf.synthesizer == "grok"


def test_unknown_reviewer_and_synthesizer_still_rejected(tmp_path):
    """Lock the valid set while it is being changed."""
    import pytest
    from multi_review.core.promptfile import fill_defaults, validate, ValidationError
    (tmp_path / "a.py").write_text("x = 1\n")
    bad_rev = fill_defaults({"prompt_format_version": 2, "task": "code",
                             "files": ["a.py"], "reviewers": ["grok3"]})
    with pytest.raises(ValidationError):
        validate(bad_rev, base_dir=tmp_path)
    bad_synth = fill_defaults({"prompt_format_version": 2, "task": "code",
                               "files": ["a.py"], "synthesizer": "grok3"})
    with pytest.raises(ValidationError):
        validate(bad_synth, base_dir=tmp_path)


def test_internal_typeerror_is_not_relabelled_as_invalid_config(tmp_path, monkeypatch):
    src = tmp_path / "x.py"
    src.write_text("")
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(f"prompt_format_version: 2\ntask: code\nfiles: [{src}]\n")

    def _bug(*args, **kwargs):
        raise TypeError("internal bug")

    monkeypatch.setattr("multi_review.core.promptfile.validate", _bug)
    with pytest.raises(TypeError, match="internal bug"):
        load_promptfile(prompt)


def test_invalid_utf8_is_reported_as_a_validation_error(tmp_path):
    """A malformed byte stream is invalid configuration, not a driver crash."""
    prompt = tmp_path / "prompt.yaml"
    prompt.write_bytes(b"\xff\xfe")

    with pytest.raises(ValidationError, match="UTF-8"):
        load_promptfile(prompt)


def test_nul_in_file_path_is_reported_as_a_validation_error(tmp_path):
    """Path resolution failures stay inside the prompt-file validation boundary."""
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(
        'prompt_format_version: 2\ntask: code\nfiles: ["bad\\0path"]\n'
    )

    with pytest.raises(ValidationError, match="invalid path"):
        load_promptfile(prompt)


def test_nul_in_absolute_file_path_is_reported_as_a_validation_error(tmp_path):
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(
        'prompt_format_version: 2\ntask: code\nfiles: ["/bad\\0path"]\n'
    )

    with pytest.raises(ValidationError, match="invalid path"):
        load_promptfile(prompt)


def test_symlink_loop_in_input_path_is_reported_as_a_validation_error(tmp_path):
    """A supported-runtime Path.resolve RuntimeError stays inside validation."""
    loop = tmp_path / "cycle"
    loop.symlink_to(loop.name)
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(
        'prompt_format_version: 2\ntask: code\nfiles: ["cycle/target.py"]\n'
    )

    with pytest.raises(ValidationError, match="invalid path"):
        load_promptfile(prompt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("prompt_format_version", True),
        ("prompt_format_version", 1.5),
        ("task", 1),
        ("synthesizer", 1),
        ("files", "x.py"),
        ("files", ["x.py", 1]),
        ("context_files", "x.py"),
        ("context_files", ["x.py", 1]),
        ("reviewers", "codex"),
        ("reviewers", ["codex", 1]),
        ("models", ["codex"]),
        ("models", {1: "model"}),
        ("models", {"codex": 1}),
        ("custom_prompt", 1),
    ],
)
def test_malformed_field_types_raise_validation_error(tmp_path, field, value):
    """Every malformed field is rejected before downstream iteration or path use."""
    src = tmp_path / "x.py"
    src.write_text("")
    raw = {"prompt_format_version": 2, "task": "code", "files": [str(src)]}
    raw[field] = value

    with pytest.raises(ValidationError):
        validate(fill_defaults(raw), base_dir=tmp_path)
