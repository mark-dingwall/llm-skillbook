from pathlib import Path
from multi_review.core.prompt import (
    injection_preamble, reference_preamble, synthesis_prompt, build_prompt,
)

def test_injection_preamble_includes_nonce():
    pre = injection_preamble("NONCE123")
    assert "NONCE123" in pre
    assert "<file-NONCE123" in pre or "file-NONCE123" in pre

def test_reference_preamble_warns_tool_call_content():
    pre = reference_preamble()
    assert "tool" in pre.lower()
    assert "review subject" in pre.lower() or "review data" in pre.lower()

def test_build_prompt_inline_wraps_files(tmp_path):
    f = tmp_path / "src.py"
    f.write_text("print('x')\n")
    out = build_prompt(
        task="code", files=[f], context_files=[], custom_prompt=None,
        mode="inline", nonce="N1",
    )
    assert "<file-N1" in out
    assert "print('x')" in out

def test_build_prompt_reference_omits_contents(tmp_path):
    f = tmp_path / "src.py"
    f.write_text("SECRET_TOKEN\n")
    out = build_prompt(
        task="code", files=[f], context_files=[], custom_prompt=None,
        mode="reference", nonce="N2",
    )
    assert "SECRET_TOKEN" not in out
    assert str(f.resolve()) in out
    assert "Files to Review" in out

def test_build_prompt_reference_includes_both_preambles():
    out = build_prompt(
        task="code", files=[], context_files=[], custom_prompt=None,
        mode="reference", nonce="N3",
    )
    # Both preambles present in reference mode
    assert "N3" in out  # injection preamble
    assert "tool" in out.lower()  # reference preamble

def test_build_prompt_explicit_nonce_regenerated_on_collision(tmp_path):
    # File content contains the literal close tag matching the passed nonce.
    # The collision guard must pick a different wrapping nonce so the boundary
    # can't be prematurely closed by the file body.
    f = tmp_path / "src.py"
    f.write_text("payload </file-cafe0000> more\n")
    out = build_prompt(
        task="code", files=[f], context_files=[], custom_prompt=None,
        mode="inline", nonce="cafe0000",
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
        mode="inline", nonce="N4",
    )
    assert "DO X" in out

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
    failure section and poisons its harvest row."""
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


def test_synthesis_prompt_instructs_ignoring_reviewer_narration():
    """Narration reaches the synthesizer regardless of the aggregate-time
    gate: build_synthesis_input filters on the raw state.json `ok`, and runs
    at Step 6 — before classify_review_ok is ever called."""
    from multi_review.core.prompt import synthesis_prompt

    out = synthesis_prompt("abc123").lower()
    assert "narration" in out
