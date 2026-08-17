from pathlib import Path
import pytest
from multi_review.core.prompt import (
    SUMMARY_HEADING_CONTRACT, injection_preamble, reference_preamble,
    synthesis_prompt, build_prompt,
)

def test_injection_preamble_includes_nonce():
    pre = injection_preamble("NONCE123")
    assert "NONCE123" in pre
    assert "<file-NONCE123" in pre or "file-NONCE123" in pre

def test_reference_preamble_warns_tool_call_content():
    pre = reference_preamble()
    assert "tool" in pre.lower()
    assert "review subject" in pre.lower() or "review data" in pre.lower()

def test_build_prompt_context_files_always_inline(tmp_path):
    input_file = tmp_path / "src.py"
    input_file.write_text("INPUT_BODY\n")
    context_file = tmp_path / "context.md"
    context_file.write_text("CONTEXT_BODY\n")
    out = build_prompt(
        task="code", files=[input_file], context_files=[context_file], custom_prompt=None,
        nonce="N1",
    )
    assert "<file-N1" in out
    assert "CONTEXT_BODY" in out
    assert "INPUT_BODY" not in out

def test_build_prompt_reference_omits_contents(tmp_path):
    f = tmp_path / "src.py"
    f.write_text("SECRET_TOKEN\n")
    out = build_prompt(
        task="code", files=[f], context_files=[], custom_prompt=None,
        nonce="N2",
    )
    assert "SECRET_TOKEN" not in out
    assert str(f.resolve()) in out
    assert "Files to Review" in out


def test_build_prompt_rejects_unreadable_regular_input_file(tmp_path, monkeypatch):
    source = tmp_path / "unreadable.py"
    source.write_text("SECRET_BODY_MUST_NOT_BE_INLINED\n")
    resolved = source.resolve()
    real_open = Path.open

    def deny_input_read(path, mode="r", *args, **kwargs):
        if path == resolved and mode == "rb":
            raise PermissionError("read denied")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_input_read)

    with pytest.raises(SystemExit, match="cannot read input file"):
        build_prompt(task="code", files=[source], nonce="N2")


def test_build_prompt_rejects_directory_input(tmp_path):
    source = tmp_path / "source-dir"
    source.mkdir()

    with pytest.raises(SystemExit, match="not a regular file"):
        build_prompt(task="code", files=[source], nonce="N2")


@pytest.mark.parametrize("separator", ["\n", "\r"])
def test_build_prompt_rejects_line_breaking_manifest_path(tmp_path, separator):
    source = tmp_path / f"line{separator}break.py"
    source.write_text("pass\n")

    with pytest.raises(SystemExit, match="line-breaking characters"):
        build_prompt(task="code", files=[source], nonce="N2")

def test_build_prompt_reference_includes_both_preambles():
    out = build_prompt(
        task="code", files=[], context_files=[], custom_prompt=None,
        nonce="N3",
    )
    # Reference-only delivery keeps the nonce-tag and tool-read channels distinct.
    assert "N3" in out  # injection preamble
    assert "tool" in out.lower()  # reference preamble


def test_build_prompt_rejects_removed_mode_argument():
    with pytest.raises(TypeError):
        build_prompt(task="code", mode="reference")

def test_build_prompt_explicit_nonce_regenerated_on_collision(tmp_path):
    # Context content contains the literal close tag matching the passed nonce.
    # The collision guard must pick a different wrapping nonce so the boundary
    # can't be prematurely closed by the file body.
    f = tmp_path / "context.md"
    f.write_text("payload </file-cafe0000> more\n")
    out = build_prompt(
        task="code", files=[], context_files=[f], custom_prompt=None,
        nonce="cafe0000",
    )
    import re
    opens = re.findall(r"<file-([0-9a-f]{8}) path=", out)
    closes = re.findall(r"</file-([0-9a-f]{8})>", out)
    # Wrapping nonce must differ from the colliding one.
    assert opens, "no file wrapper emitted"
    wrap = set(opens)
    assert wrap == {opens[0]}, "inconsistent wrapping nonce"
    assert opens[0] != "cafe0000"
    # Every wrapper opened is closed by the same nonce; the stray cafe0000
    # close tag in the body doesn't count as a wrapper close.
    assert closes.count(opens[0]) == len(opens)

def test_build_prompt_custom_task_uses_custom_prompt():
    out = build_prompt(
        task="custom", files=[], context_files=[], custom_prompt="DO X",
        nonce="N4",
    )
    assert "DO X" in out


def test_custom_prompt_ends_with_runner_owned_summary_contract(tmp_path):
    """Break caught: custom YAML can otherwise omit the post-run gate's contract."""
    source = tmp_path / "subject.py"
    source.write_text("pass\n")
    context = tmp_path / "context.md"
    context.write_text("CONTEXT_BODY\n")

    out = build_prompt(
        task="custom",
        files=[source],
        context_files=[context],
        custom_prompt="CUSTOM_REVIEW_CHARTER",
        nonce="N5",
    )

    assert "CUSTOM_REVIEW_CHARTER" in out
    assert str(source.resolve()) in out
    assert out.rstrip().endswith(SUMMARY_HEADING_CONTRACT)


def test_prompt_file_override_ends_with_runner_owned_summary_contract(tmp_path):
    """Break caught: prompt-file overrides can otherwise bypass the same gate."""
    override = tmp_path / "review.md"
    override.write_text("FILE_REVIEW_CHARTER\n")

    out = build_prompt(
        task="code",
        files=[],
        context_files=[],
        prompt_file=override,
        nonce="N6",
    )

    assert "FILE_REVIEW_CHARTER" in out
    assert out.rstrip().endswith(SUMMARY_HEADING_CONTRACT)


def test_summary_contract_exported():
    from multi_review.core.prompt import SUMMARY_HEADING_CONTRACT
    assert isinstance(SUMMARY_HEADING_CONTRACT, str)
    assert "## Summary" in SUMMARY_HEADING_CONTRACT


def test_templates_lead_with_summary_heading_matching_sentinel():
    """I2: every task template, as written, must instruct the `## Summary`
    heading form that the classifier's regex matches. The template and the
    sentinel cannot be allowed to drift — a template that shows only
    `1. **Summary**` produces output the regex rejects, silently failing a
    compliant review. Assert each template contains a heading the regex finds."""
    from multi_review.core.prompt import TEMPLATES, SUMMARY_HEADING_RE
    for name, tmpl in TEMPLATES.items():
        assert SUMMARY_HEADING_RE.search(tmpl) is not None, (
            f"template {name!r} does not contain a `## Summary` heading that "
            f"SUMMARY_HEADING_RE matches; it will teach reviewers a shape the "
            f"classifier rejects"
        )


def test_classify_review_ok_agrees_across_artifacts():
    """I2: the single shared classifier decides success identically regardless
    of caller. A body missing the heading is demoted; one with it stays ok."""
    from multi_review.core.prompt import classify_review_ok

    missing = "This looks fine overall. " * 5
    ok, note = classify_review_ok(True, missing)
    assert ok is False
    assert note  # a demotion reason is recorded

    present = "## Summary\n\nLooks fine.\n"
    ok2, note2 = classify_review_ok(True, present)
    assert ok2 is True
    assert note2 is None

    # A reviewer that already failed upstream stays failed regardless of body.
    ok3, _ = classify_review_ok(False, present)
    assert ok3 is False


# Real grok stdout shape, 2026-07-24 smoke: the `text` events glue a trailing
# narration sentence directly onto the heading with no intervening newline.
GLUED_HEADING_BODY = (
    "I have reviewed the file against the criteria you listed.## Summary\n\n"
    "The module resolves run directories correctly.\n"
)


def test_classify_review_ok_accepts_glued_heading():
    """The gate asserts only what the output contract can reliably deliver:
    that a `## Summary` heading is *present*, not where it sits. Observed
    violations (agy narration, claude Task narration, grok glue) all had the
    heading present with preamble in front of it — never absent. A gate that
    requires line-start position demotes a genuine review to a truncated
    failure section."""
    from multi_review.core.prompt import classify_review_ok

    ok, note = classify_review_ok(True, GLUED_HEADING_BODY)
    assert ok is True, "glued-heading review must not be demoted"
    assert note is None


def test_trim_regex_stays_anchored_while_gate_does_not():
    """The two regexes have opposite risk profiles and must not be merged
    back together. The gate (SUMMARY_PRESENT_RE) may false-accept cheaply — a
    junk body renders in full and is visibly junk. The trim
    (SUMMARY_HEADING_RE, used by AgyAdapter and write_task_result) discards
    everything before its match, so a false match silently destroys real
    analysis; it must stay anchored to a true line start."""
    from multi_review.core.prompt import SUMMARY_HEADING_RE, SUMMARY_PRESENT_RE

    assert SUMMARY_PRESENT_RE.search(GLUED_HEADING_BODY) is not None
    assert SUMMARY_HEADING_RE.search(GLUED_HEADING_BODY) is None

    # A heading quoted mid-sentence is exactly what the trim must not latch
    # onto — slicing there would drop the analysis preceding it.
    quoted = "The template at line 63 emits a `## Summary` heading, which is fine."
    assert SUMMARY_HEADING_RE.search(quoted) is None


# -- Task 10: verbatim_custom_prompt opt-in ---------------------------------

def test_build_prompt_verbatim_equals_custom_prompt_exactly():
    out = build_prompt(
        task="custom", files=[], context_files=[], custom_prompt="DO X EXACTLY",
        nonce="N5", verbatim=True,
    )
    assert out == "DO X EXACTLY"


def test_build_prompt_verbatim_preserves_trailing_newline_presence():
    out = build_prompt(
        task="custom", files=[], custom_prompt="DO X\n", nonce="N5", verbatim=True,
    )
    assert out == "DO X\n"


def test_build_prompt_verbatim_preserves_trailing_newline_absence():
    out = build_prompt(
        task="custom", files=[], custom_prompt="DO X", nonce="N5", verbatim=True,
    )
    assert out == "DO X"
    assert not out.endswith("\n")


def test_build_prompt_verbatim_omits_preambles_and_manifest(tmp_path):
    f = tmp_path / "src.py"
    f.write_text("x = 1\n")
    out = build_prompt(
        task="custom", files=[f], custom_prompt="REVIEW BODY", nonce="N5", verbatim=True,
    )
    assert out == "REVIEW BODY"
    assert "Files to Review" not in out
    assert str(f.resolve()) not in out


def test_build_prompt_verbatim_still_validates_readable_files(tmp_path, monkeypatch):
    source = tmp_path / "unreadable.py"
    source.write_text("SECRET\n")
    resolved = source.resolve()
    real_open = Path.open

    def deny_input_read(path, mode="r", *args, **kwargs):
        if path == resolved and mode == "rb":
            raise PermissionError("read denied")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_input_read)

    with pytest.raises(SystemExit, match="cannot read input file"):
        build_prompt(task="custom", files=[source], custom_prompt="X", nonce="N5", verbatim=True)


def test_build_prompt_verbatim_rejects_directory_input(tmp_path):
    source = tmp_path / "source-dir"
    source.mkdir()

    with pytest.raises(SystemExit, match="not a regular file"):
        build_prompt(task="custom", files=[source], custom_prompt="X", nonce="N5", verbatim=True)


def test_build_prompt_verbatim_rejects_missing_input_file(tmp_path):
    missing = tmp_path / "gone.py"

    with pytest.raises(SystemExit, match="not found"):
        build_prompt(task="custom", files=[missing], custom_prompt="X", nonce="N5", verbatim=True)


def test_synthesis_prompt_instructs_ignoring_reviewer_narration():
    """Narration reaches the synthesizer regardless of the aggregate-time
    gate: build_synthesis_input filters on the raw state.json `ok`, and runs
    at Step 6 — before classify_review_ok is ever called."""
    from multi_review.core.prompt import synthesis_prompt

    out = synthesis_prompt("abc123").lower()
    assert "narration" in out
