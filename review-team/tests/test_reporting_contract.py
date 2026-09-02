"""Static contract checks for exhaustive Review Team reporting."""

from pathlib import Path


COMPONENT = Path(__file__).resolve().parents[1]
SKILL = (COMPONENT / "SKILL.md").read_text()
REPORT = (COMPONENT / "references" / "report-contract.md").read_text()
FINDER = (COMPONENT / "references" / "finder-angles.md").read_text()
VERIFIER = (COMPONENT / "references" / "verifier.md").read_text()


def test_every_verified_survivor_is_reported() -> None:
    live_reporting_contract = "\n".join((SKILL, REPORT, FINDER, VERIFIER))

    assert "reportPolicy: allVerifiedSurvivors" in REPORT
    assert "Backfill every unmentioned survivor in base order." in REPORT
    assert "Emit every remaining representative in survivor order." in REPORT
    assert "Every survivor `candidateId` must be accounted for exactly once" in REPORT
    assert "`reported` is the number of rendered primary findings" in REPORT
    assert "exact partition of all fallback survivor IDs" in REPORT
    assert "Retain every distinct verifier-evidence item" in REPORT
    assert "Render every distinct verifier-evidence item from a semantic merge" in REPORT
    assert "Assemble the complete report deterministically." in SKILL

    for obsolete in (
        "report cap and output",
        "Report cap",
        "report capacity remains",
        "take the report cap",
        "reportCap",
        "the report cap",
        "final cap",
        "while capacity remains",
    ):
        assert obsolete not in live_reporting_contract


def test_numeric_candidate_ceilings_are_preserved() -> None:
    assert (
        "| `high` | A-C, `3 × 6` | `1 × 30` | 48 | 0 | 48 | 48 | 96 |"
        in REPORT
    )
    assert (
        "| `xhigh` | A-E, `5 × 8` | `1 × 40` | 80 | 8 | 88 | 88 | 176 |"
        in REPORT
    )


def test_higher_priority_backfilled_survivor_precedes_accepted_lower_priority_finding() -> None:
    assert (
        "After backfill, order the complete set of accepted and backfilled primary findings\n"
        "together: correctness before Cleanup and `CONFIRMED` before `PLAUSIBLE`."
        in REPORT
    )


def test_semantic_merges_require_identical_normalized_issue_semantics() -> None:
    assert (
        "Admit a semantic merge only when the supplied summaries and verifier evidence\n"
        "make the same root cause explicit and every member has the same category and\n"
        "verdict."
        in REPORT
    )
    assert (
        "Require the normalized `summary` and `failure_scenario` values to be\n"
        "byte-identical across all members."
        in REPORT
    )
    assert "Normalize each field by trimming it and\ncollapsing internal whitespace" in REPORT
    assert "Otherwise keep the records as\nseparate primary findings." in REPORT
    assert "Preserve every affected location." in REPORT


def test_same_bucket_accepted_primaries_precede_backfilled_primaries() -> None:
    assert (
        "Within each category and verdict bucket, emit accepted primaries in Synthesis\n"
        "severity order followed by backfilled primaries in base order."
        in REPORT
    )


def test_report_fields_favor_terse_evidence_complete_language() -> None:
    assert "Keep `summary` to one terse sentence." in FINDER
    assert "Keep `failure_scenario` to one terse sentence" in FINDER
    assert "Keep `evidence` to one terse sentence when that sentence" in VERIFIER
    assert "Apply the same terse-field rules to refinements and replacements." in VERIFIER
    assert "Do not repeat the same mechanism across fields." in REPORT
    assert "Never omit evidence required by the applicable verdict ladder." in REPORT
