"""Behavioral tests for deterministic Review Team report assembly."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "assemble_report.py"


def survivor(
    candidate_id: int,
    *,
    file: str,
    line: int,
    category: str = "correctness",
    verdict: str = "CONFIRMED",
    summary: str | None = None,
    failure_scenario: str | None = None,
    evidence: str | None = None,
) -> dict[str, object]:
    return {
        "candidateId": candidate_id,
        "file": file,
        "line": line,
        "category": category,
        "verdict": verdict,
        "summary": summary or f"summary {candidate_id}",
        "failure_scenario": failure_scenario or f"scenario {candidate_id}",
        "evidence": evidence or f"evidence {candidate_id}",
    }


def run_assembler(
    tmp_path: Path, command: str, payload: dict[str, object]
) -> tuple[subprocess.CompletedProcess[str], dict[str, object] | None]:
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(payload))
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            command,
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    output = json.loads(output_path.read_text()) if output_path.exists() else None
    return result, output


def test_prepare_orders_survivors_and_assigns_report_indexes(tmp_path: Path) -> None:
    payload = {
        "survivors": [
            survivor(7, file="z.py", line=2, category="cleanup"),
            survivor(3, file="b.py", line=10, verdict="PLAUSIBLE"),
            survivor(9, file="b.py", line=2),
            survivor(1, file="a.py", line=8),
        ]
    }

    result, output = run_assembler(tmp_path, "prepare", payload)

    assert result.returncode == 0, result.stderr
    assert output is not None
    assert [record["candidateId"] for record in output["survivors"]] == [1, 9, 3, 7]
    assert [record["reportIndex"] for record in output["survivors"]] == [0, 1, 2, 3]


def test_finalize_accepts_reasoned_merge_and_backfills_unmentioned_survivor(
    tmp_path: Path,
) -> None:
    payload = {
        "survivors": [
            survivor(
                0,
                file="report.md",
                line=20,
                summary="Final output can omit findings.",
            ),
            survivor(
                1,
                file="report.md",
                line=21,
                summary="Some verified records may disappear from the report.",
            ),
            survivor(2, file="a.py", line=5),
        ],
        "synthesis": {
            "summary": "One shared reporting defect plus one separate risk.",
            "decisions": [
                {
                    "reportIndex": 1,
                    "candidateId": 0,
                    "merge": [{"reportIndex": 2, "candidateId": 1}],
                    "sharedRootCause": "Backfill does not preserve every survivor.",
                    "singleFix": "Repair the backfill partition.",
                }
            ],
        },
    }

    result, output = run_assembler(tmp_path, "finalize", payload)

    assert result.returncode == 0, result.stderr
    assert output is not None
    assert output["mode"] == "synthesis"
    assert output["reported"] == 2
    assert [finding["candidateIds"] for finding in output["findings"]] == [[0, 1], [2]]
    assert output["findings"][0]["sharedRootCause"] == (
        "Backfill does not preserve every survivor."
    )
    assert [record["candidateId"] for record in output["findings"][0]["records"]] == [
        0,
        1,
    ]


def test_finalize_rejects_incompatible_merge_without_losing_candidates(
    tmp_path: Path,
) -> None:
    payload = {
        "survivors": [
            survivor(0, file="report.md", line=20),
            survivor(1, file="report.md", line=21, verdict="PLAUSIBLE"),
        ],
        "synthesis": {
            "summary": "Invalid cross-verdict merge.",
            "decisions": [
                {
                    "reportIndex": 0,
                    "candidateId": 0,
                    "merge": [{"reportIndex": 1, "candidateId": 1}],
                    "sharedRootCause": "The claims look related.",
                    "singleFix": "Change one report rule.",
                }
            ],
        },
    }

    result, output = run_assembler(tmp_path, "finalize", payload)

    assert result.returncode == 0, result.stderr
    assert output is not None
    assert output["mode"] == "fallback"
    assert [finding["candidateIds"] for finding in output["findings"]] == [[0], [1]]


def test_fallback_uses_exact_ascii_whitespace_normalization(tmp_path: Path) -> None:
    payload = {
        "survivors": [
            survivor(
                0,
                file="report.md",
                line=20,
                summary="Same\tissue",
                failure_scenario=" Same\nscenario ",
            ),
            survivor(
                1,
                file="report.md",
                line=20,
                summary="Same issue",
                failure_scenario="Same scenario",
            ),
            survivor(
                2,
                file="report.md",
                line=20,
                summary="Same\u00a0issue",
                failure_scenario="Same scenario",
            ),
        ]
    }

    result, output = run_assembler(tmp_path, "finalize", payload)

    assert result.returncode == 0, result.stderr
    assert output is not None
    assert output["mode"] == "fallback"
    assert [finding["candidateIds"] for finding in output["findings"]] == [[0, 1], [2]]


def test_duplicate_candidate_ids_fail_closed(tmp_path: Path) -> None:
    duplicate = survivor(4, file="report.md", line=20)

    result, output = run_assembler(
        tmp_path, "prepare", {"survivors": [duplicate, duplicate]}
    )

    assert result.returncode == 2
    assert output is None
    assert "duplicate candidateId: 4" in result.stderr


def test_non_string_category_fails_without_traceback(tmp_path: Path) -> None:
    record = survivor(4, file="report.md", line=20)
    record["category"] = ["correctness"]

    result, output = run_assembler(tmp_path, "prepare", {"survivors": [record]})

    assert result.returncode == 2
    assert output is None
    assert "survivors[0].category is invalid" in result.stderr
    assert "Traceback" not in result.stderr
