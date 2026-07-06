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
