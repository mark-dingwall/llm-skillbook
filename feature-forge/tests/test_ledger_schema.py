"""Contract tests for the version-one Feature Forge ledger head."""
from __future__ import annotations

import json
import re
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "ledger-template.md"


def _head_and_markdown() -> tuple[dict[str, object], str]:
    """Extract the required first nonblank JSON fence from the ledger template."""
    text = TEMPLATE.read_text()
    match = re.match(r"\s*```json\n(?P<head>.*?)\n```\n?(?P<markdown>.*)\Z", text, re.DOTALL)
    assert match, "the ledger must begin with one fenced json block"
    return json.loads(match["head"]), match["markdown"]


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

    for obsolete_current_value_mirror in (
        "## Run identity",
        "## Stage register",
        "- Current stage/state:",
        "## Reviews",
        "| review | state |",
        "- Overall status:",
        "- Worktree:",
        "- Branch:",
        "- Base identity:",
        "- Exactly one next permitted action:",
        "stable run reference",
        "content seal",
        "TRIAGE outcome/open finding IDs",
    ):
        assert obsolete_current_value_mirror not in markdown

    assert "| event | parent event | UTC time | from | to | next action | session provenance | reason/authority | evidence |" in markdown
    assert "transcript" not in markdown.lower()
    assert "transcript" not in json.dumps(head).lower()
    assert "audit tip" not in json.dumps(head).lower()
