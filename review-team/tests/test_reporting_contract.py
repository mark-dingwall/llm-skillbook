"""Contract-wiring checks for exhaustive Review Team reporting."""

from pathlib import Path


COMPONENT = Path(__file__).resolve().parents[1]
SKILL = (COMPONENT / "SKILL.md").read_text()
REPORT = (COMPONENT / "references" / "report-contract.md").read_text()
FINDER = (COMPONENT / "references" / "finder-angles.md").read_text()
VERIFIER = (COMPONENT / "references" / "verifier.md").read_text()


def test_every_verified_survivor_is_reported() -> None:
    live_reporting_contract = "\n".join((SKILL, REPORT, FINDER, VERIFIER))

    assert "reportPolicy: allVerifiedSurvivors" in REPORT
    assert "scripts/assemble_report.py prepare" in SKILL
    assert "then use its `finalize`" in SKILL
    assert "`reported` is the number of rendered primary" in REPORT
    assert "Never reproduce its ordering" in SKILL

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


def test_semantic_merges_are_reasoned_while_accounting_is_deterministic() -> None:
    assert "one named code or test change would fix every claim in the merge" in REPORT
    assert "merge differently\nworded records" in REPORT
    assert "ASCII whitespace code points" in REPORT


def test_semantic_merge_preserves_every_member_scenario() -> None:
    assert "every member record's failure scenario" in " ".join(REPORT.split())


def test_report_fields_favor_terse_evidence_complete_language() -> None:
    assert "Keep `summary` to one terse sentence." in FINDER
    assert "Keep `failure_scenario` to one terse sentence" in FINDER
    assert "Keep `evidence` to one terse sentence when that sentence" in VERIFIER
    assert "Apply the same terse-field rules to refinements and replacements." in VERIFIER
    assert "Do not repeat the same mechanism across fields." in REPORT
    assert "Never omit evidence required by the applicable verdict ladder." in REPORT
