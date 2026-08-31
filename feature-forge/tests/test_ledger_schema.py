"""Contract tests for the version-one Feature Forge ledger head."""
from __future__ import annotations

import json
import re
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "ledger-template.md"
CURRENT_STATE_LABELS = frozenset({
    "schema", "run id", "work unit run id", "overall status", "worktree",
    "branch", "base identity", "current stage", "stage", "stage state", "next action",
    "sole next permitted action", "frozen", "frozen identity", "review kind",
    "review state", "review round", "review root identity", "review dispatch id",
    "review run ref", "review target seal", "review evidence path",
    "reviewed commit", "previous open finding ids", "open finding ids",
})


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
    for index, line in enumerate(lines):
        if match := re.match(r"\s*#{1,6}\s+(.+?)\s*$", line):
            section = _normalise_label(match.group(1))
            labels.add(section)
        if match := re.match(r"\s*[-*]\s+([^:]+):", line):
            labels.add(_normalise_label(match.group(1)))
        if section not in {"finish journal", "transition log"} and "|" in line and index + 1 < len(lines) and re.match(
            r"\s*\|?\s*:?-{3,}", lines[index + 1]
        ):
            labels.update(_normalise_label(cell) for cell in line.strip().strip("|").split("|"))
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
