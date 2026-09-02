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
