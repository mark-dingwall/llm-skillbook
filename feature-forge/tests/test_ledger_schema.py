"""Contract tests for the version-one Feature Forge ledger head."""
from __future__ import annotations

import json
import re
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "ledger-template.md"
SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
WORKFLOW = Path(__file__).resolve().parents[1] / "references" / "workflow.md"
REVIEWS = Path(__file__).resolve().parents[1] / "references" / "adapters-and-reviews.md"
CURRENT_STATE_LABELS = frozenset({
    "schema", "run id", "run identity", "work unit run id", "status",
    "overall status", "worktree", "branch", "base identity", "stage",
    "current stage", "stage state", "next action", "sole next permitted action",
    "frozen", "frozen identity", "review", "kind", "review kind", "state",
    "review state", "round", "review round", "root identity",
    "review root identity", "dispatch id", "review dispatch id", "run ref",
    "review run ref", "target seal", "review target seal", "evidence path",
    "review evidence path", "reviewed commit", "previous open finding ids",
    "open finding ids",
})
REVIEW_CONTEXT_LABELS = frozenset({"kind", "state", "round"})
STAGE_LABELS = (
    "Goal", "Inputs", "Mechanical check", "Owned action", "Pass", "Failure", "Next",
)


def _head_and_markdown() -> tuple[dict[str, object], str]:
    """Extract the required first nonblank JSON fence from the ledger template."""
    text = TEMPLATE.read_text()
    match = re.match(r"\s*```json\n(?P<head>.*?)\n```\n?(?P<markdown>.*)\Z", text, re.DOTALL)
    assert match, "the ledger must begin with one fenced json block"
    return json.loads(match["head"]), match["markdown"]


def _normalise_label(label: str) -> str:
    normalised = " ".join(re.sub(r"[`_/:-]", " ", label).lower().split())
    return normalised.removeprefix("current ")


def _current_state_labels(markdown: str) -> set[str]:
    """Return current-state labels, without treating ordinary prose as fields."""
    lines = markdown.splitlines()
    labels: set[str] = set()
    section = ""

    def record(label: str) -> None:
        if label not in REVIEW_CONTEXT_LABELS or "review" in section:
            labels.add(label)

    for index, line in enumerate(lines):
        if match := re.match(r"\s*#{1,6}\s+(.+?)\s*$", line):
            section = _normalise_label(match.group(1))
            record(section)
        if match := re.match(r"\s*[-*]\s+([^:]+):", line):
            record(_normalise_label(match.group(1)))
        if section not in {"finish journal", "transition log"} and "|" in line and index + 1 < len(lines) and re.match(
            r"\s*\|?\s*:?-{3,}", lines[index + 1]
        ):
            table_labels = {
                _normalise_label(cell) for cell in line.strip().strip("|").split("|")
            }
            if "plan task" in table_labels:
                table_labels.discard("status")
            for label in table_labels:
                record(label)
    return labels & CURRENT_STATE_LABELS


def test_ledger_head_pins_the_version_one_schema() -> None:
    head, _ = _head_and_markdown()

    assert head["schema"] == "feature-forge/ledger/v1"
    assert set(head) == {
        "schema", "run_id", "status", "worktree", "branch", "base_identity",
        "stage", "next_action", "frozen", "review",
    }
    assert set(head["review"]) == {
        "kind", "state", "round", "root_identity", "dispatch_id", "run_ref",
        "target_seal", "evidence_path", "reviewed_commit",
        "previous_open_finding_ids", "open_finding_ids",
    }
    assert set(head["stage"]) == {"id", "state"}
    assert set(head["frozen"]) == {"specification", "plan"}


def test_current_state_label_detector_ignores_historical_prose() -> None:
    markdown = """\
## Transition log

Previous review round 2 passed before this transition.

| event | evidence |
| --- | --- |
| review returned | historical run_ref: prior-run |

- Current review state: pass
"""

    assert _current_state_labels(markdown) == {"review state"}


def test_current_state_label_detector_catches_direct_field_labels() -> None:
    markdown = """\
## Run identity

- Status: active

| target seal | evidence path |
| --- | --- |
| current seal | evidence.json |

## Reviews

| kind | state | round |
| --- | --- | --- |
| implementation | pass | 1 |
"""

    assert _current_state_labels(markdown) == {
        "run identity", "status", "target seal", "evidence path", "kind",
        "state", "round",
    }


def test_markdown_keeps_human_evidence_without_current_head_mirrors() -> None:
    head, markdown = _head_and_markdown()

    for section in (
        "## Intent and run evidence",
        "## Finish journal",
        "## Transition log",
        "## Current authority",
        "## Implementation progress",
        "## Verification and acceptance",
    ):
        assert section in markdown

    assert not _current_state_labels(markdown)

    assert "| event | parent event | UTC time | from | to | next action | session provenance | reason/authority | evidence |" in markdown
    assert "transcript" not in json.dumps(head).lower()
    assert "audit tip" not in json.dumps(head).lower()


def _stage_contracts() -> dict[int, str]:
    text = WORKFLOW.read_text()
    matches = list(re.finditer(r"^### Stage (\d+): .+$", text, re.MULTILINE))
    return {
        int(match.group(1)): text[match.end():matches[index + 1].start()]
        if index + 1 < len(matches) else text[match.end():]
        for index, match in enumerate(matches)
    }


def _label_value(stage: str, label: str) -> str:
    match = re.search(rf"^- \*\*{re.escape(label)}:\*\*\s*(.+)$", stage, re.MULTILINE)
    assert match, f"missing stage label: {label}"
    return match.group(1)


def _squash(text: str) -> str:
    return " ".join(text.split())


def test_skill_exposes_the_checker_result_boundary() -> None:
    text = SKILL.read_text()

    assert 'python3 "$SKILL_DIR/scripts/ff-check"' in text
    assert "missing/malformed result line" in text
    assert "unverifiable" in text and "blocked" in text


def test_all_fourteen_stages_use_the_compact_checked_contract() -> None:
    stages = _stage_contracts()

    assert set(stages) == set(range(1, 15))
    for number, stage in stages.items():
        for label in STAGE_LABELS:
            assert stage.count(f"- **{label}:**") == 1, (number, label)
        assert "fail" in _label_value(stage, "Failure")
        assert "unverifiable" in _label_value(stage, "Failure")


def test_stage_gate_sequences_match_the_approved_map() -> None:
    stages = _stage_contracts()

    assert "`runs`" in _label_value(stages[1], "Mechanical check")
    for number in range(2, 15):
        assert "`identities`" in _label_value(stages[number], "Mechanical check"), number

    for number in (5, 8, 10):
        check = _label_value(stages[number], "Mechanical check")
        assert check.index("`identities`") < check.index("`audit`")

    for number in (11, 12, 13, 14):
        check = _label_value(stages[number], "Mechanical check")
        assert check.index("`identities`") < check.index("`reviewed-snapshot`") < check.index("`audit`")


def test_bounded_review_update_and_reset_rule_has_one_owner() -> None:
    reviews = REVIEWS.read_text()
    compact_reviews = _squash(reviews).lower()
    workflow = WORKFLOW.read_text()

    assert reviews.count("## Bounded review return rule") == 1
    assert "increment `review.round`" in reviews
    assert "previous_open_finding_ids" in reviews
    assert "open_finding_ids" in reviews
    assert "third actionable return" in reviews
    assert "identical consecutive nonempty" in compact_reviews
    assert "ordinary fixes retain" in compact_reviews
    assert "old and new root identities" in compact_reviews
    assert "## Bounded review return rule" not in workflow


def test_session_provenance_and_transcripts_stay_forensic() -> None:
    _, template_markdown = _head_and_markdown()
    workflow = _squash(WORKFLOW.read_text())

    assert "| event | parent event | UTC time | from | to | next action | session provenance | reason/authority | evidence |" in template_markdown
    assert "`unavailable`" in workflow
    assert "mismatch" in workflow
    assert "forensic evidence" in workflow
    assert "never workflow authority" in workflow
    assert "consistent resume" in workflow
    assert "checker input" in workflow


def test_verified_frozen_identity_failure_has_one_safe_return_recipe() -> None:
    workflow = WORKFLOW.read_text()
    matches = re.findall(
        r"For a verified frozen-identity `fail`,(?P<recipe>.*?)(?:\n\n|\Z)",
        workflow,
        re.DOTALL,
    )

    assert len(matches) == 1
    recipe = _squash(matches[0]).lower()
    for required in (
        "without resolution authority", "preserve `head`", "frozen artifact",
        "no restore, commit, advance, or dispatch", "run status `blocked`",
        "current stage `blocked`", "reconcile or correct",
        "checker-reported canonical path", "reconciliation/correction",
        "reason that explains the drift", "evidence containing the exact path",
        "ledger-recorded frozen blob", "sha-256", "do not require fixed wording",
        "session provenance", "`unavailable`", "later correction/invalidation",
        "applicable authority",
    ):
        assert required in recipe
