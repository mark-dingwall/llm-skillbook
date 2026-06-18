#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.7"]
# ///
"""Regression tests for gemini retirement.

gemini must never be spawned (as reviewer or synthesizer); its REVIEW.md
section carries GEMINI_SUNSET_MESSAGE instead of any findings.

Run: ./tests/test_gemini_sunset.py   (or: uv run tests/test_gemini_sunset.py)
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "multi_review", Path(__file__).resolve().parent.parent / "multi_review.py"
)
mr = importlib.util.module_from_spec(_spec)
sys.modules["multi_review"] = mr  # dataclass annotation resolution needs this
_spec.loader.exec_module(mr)


def _gemini_state() -> "mr.ReviewerState":
    return mr.ReviewerState(cli="gemini", adapter=mr.ADAPTER_FOR["gemini"]())


def test_run_reviewer_gemini_short_circuits_without_spawning() -> None:
    # Any attempt to spawn a subprocess for gemini is a bug.
    async def _boom(*a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("gemini must not be spawned")

    orig = asyncio.create_subprocess_exec
    asyncio.create_subprocess_exec = _boom  # type: ignore[assignment]
    try:
        res = asyncio.run(
            mr.run_reviewer(
                "gemini", "prompt", None, _gemini_state(),
                chain=[None], capacity_pattern=None,
            )
        )
    finally:
        asyncio.create_subprocess_exec = orig  # type: ignore[assignment]

    assert res.ok is True
    assert res.defunct is True
    assert res.text == mr.GEMINI_SUNSET_MESSAGE


def test_synthesis_attempt_gemini_short_circuits() -> None:
    ok, text, err, suggested = asyncio.run(
        mr._run_synthesis_attempt("gemini", "body", "nonce", None, None)
    )
    assert ok is False
    assert suggested is None
    assert err == mr.GEMINI_SUNSET_MESSAGE


def test_synthesis_input_excludes_defunct_gemini() -> None:
    real = mr.ReviewerResult("claude", True, "real finding", "", mr.Usage(), 1.0)
    gem = mr.ReviewerResult(
        "gemini", True, mr.GEMINI_SUNSET_MESSAGE, "", mr.Usage(), 0.0, defunct=True
    )
    body, _nonce = mr.build_synthesis_input([real, gem])
    assert "real finding" in body
    assert mr.GEMINI_SUNSET_MESSAGE not in body
    assert 'reviewer="gemini"' not in body


def test_write_review_md_renders_gemini_sunset_section(tmp_path: Path | None = None) -> None:
    import tempfile

    real = mr.ReviewerResult("claude", True, "real finding", "", mr.Usage(), 1.0)
    gem = mr.ReviewerResult(
        "gemini", True, mr.GEMINI_SUNSET_MESSAGE, "", mr.Usage(), 0.0, defunct=True
    )
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "REVIEW.md"
        mr.write_review_md(
            out, "code", [Path("x.py")], [real, gem], {}, None, None, None, "inline"
        )
        text = out.read_text()
    assert "## Gemini Review" in text
    assert "(FAILED)" not in text.split("## Gemini Review")[1].split("##")[0]
    assert mr.GEMINI_SUNSET_MESSAGE in text


def test_defunct_gemini_not_counted_as_real_success() -> None:
    # Regression: the synthetic gemini result is ok=True, but it must not count
    # toward the "real review" total — otherwise one real reviewer + defunct
    # gemini trips the >=2 consensus gate / inflates reviewers_succeeded.
    import tempfile

    real = mr.ReviewerResult("claude", True, "real finding", "", mr.Usage(), 1.0)
    gem = mr.ReviewerResult(
        "gemini", True, mr.GEMINI_SUNSET_MESSAGE, "", mr.Usage(), 0.0, defunct=True
    )
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "REVIEW.md"
        mr.write_review_md(
            out, "code", [Path("x.py")], [real, gem], {}, None, None, None, "inline"
        )
        text = out.read_text()
    frontmatter = text.split("---")[1]
    # gemini in neither succeeded nor failed — it's defunct, not a real review.
    assert 'reviewers_succeeded: ["claude"]' in frontmatter
    assert "gemini" not in frontmatter.split("reviewers_succeeded:")[1].split("\n")[0]
    assert "reviewers_failed: []" in frontmatter
    # only 1 real review (claude) → consensus gate reports insufficient reviewers.
    assert "insufficient reviewers" in text
    # but the gemini section + notice still render.
    assert mr.GEMINI_SUNSET_MESSAGE in text


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
