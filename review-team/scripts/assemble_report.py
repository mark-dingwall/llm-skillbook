#!/usr/bin/env python3
"""Prepare and finalize deterministic Review Team report manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


CATEGORIES = {"correctness": 0, "cleanup": 1}
VERDICTS = {"CONFIRMED": 0, "PLAUSIBLE": 1}
ASCII_WHITESPACE = re.compile(r"[\x09-\x0d\x20]+")


class InputError(ValueError):
    """Raised when an input manifest violates the assembler contract."""


def _integer(value: object, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} must be a non-empty string")
    return value


def _survivors(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("survivors"), list):
        raise InputError("survivors must be an array")

    records: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, value in enumerate(payload["survivors"]):
        if not isinstance(value, dict):
            raise InputError(f"survivors[{index}] must be an object")
        candidate_id = value.get("candidateId")
        if not _integer(candidate_id):
            raise InputError(f"survivors[{index}].candidateId must be a non-negative integer")
        if candidate_id in seen:
            raise InputError(f"duplicate candidateId: {candidate_id}")
        seen.add(candidate_id)

        category = value.get("category")
        verdict = value.get("verdict")
        if not isinstance(category, str) or category not in CATEGORIES:
            raise InputError(f"survivors[{index}].category is invalid")
        if not isinstance(verdict, str) or verdict not in VERDICTS:
            raise InputError(f"survivors[{index}].verdict is invalid")
        line = value.get("line")
        if line is not None and not _integer(line, minimum=1):
            raise InputError(f"survivors[{index}].line must be a positive integer")

        record: dict[str, Any] = {
            "candidateId": candidate_id,
            "file": _text(value.get("file"), f"survivors[{index}].file"),
            "category": category,
            "verdict": verdict,
            "summary": _text(value.get("summary"), f"survivors[{index}].summary"),
            "failure_scenario": _text(
                value.get("failure_scenario"),
                f"survivors[{index}].failure_scenario",
            ),
            "evidence": _text(value.get("evidence"), f"survivors[{index}].evidence"),
        }
        if line is not None:
            record["line"] = line
        records.append(record)
    return records


def _sort_key(record: dict[str, Any]) -> tuple[object, ...]:
    line = record.get("line")
    return (
        CATEGORIES[record["category"]],
        VERDICTS[record["verdict"]],
        record["file"],
        line is None,
        line if line is not None else 0,
        record["candidateId"],
    )


def _ordered(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=_sort_key)


def prepare(payload: object) -> dict[str, object]:
    records = _ordered(_survivors(payload))
    return {
        "survivors": [dict(record, reportIndex=index) for index, record in enumerate(records)]
    }


def _identity(
    value: object, ordered: list[dict[str, Any]], field: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{field} must be an object")
    report_index = value.get("reportIndex")
    candidate_id = value.get("candidateId")
    if not _integer(report_index) or report_index >= len(ordered):
        raise InputError(f"{field}.reportIndex is invalid")
    record = ordered[report_index]
    if not _integer(candidate_id) or candidate_id != record["candidateId"]:
        raise InputError(f"{field}.candidateId does not match reportIndex")
    return record


def _finding(
    records: list[dict[str, Any]],
    *,
    shared_root_cause: str | None = None,
    single_fix: str | None = None,
) -> dict[str, object]:
    finding: dict[str, object] = {
        "primaryCandidateId": records[0]["candidateId"],
        "candidateIds": [record["candidateId"] for record in records],
        "records": records,
    }
    if len(records) > 1 and shared_root_cause is not None and single_fix is not None:
        finding["sharedRootCause"] = shared_root_cause
        finding["singleFix"] = single_fix
    return finding


def _synthesis_findings(
    synthesis: object, ordered: list[dict[str, Any]]
) -> list[dict[str, object]] | None:
    if not isinstance(synthesis, dict):
        return None
    try:
        _text(synthesis.get("summary"), "synthesis.summary")
    except InputError:
        return None
    decisions = synthesis.get("decisions")
    if not isinstance(decisions, list):
        return None

    claimed: set[int] = set()
    accepted: list[dict[str, object]] = []
    for decision_index, decision in enumerate(decisions):
        try:
            primary = _identity(decision, ordered, f"decisions[{decision_index}]")
            merge_values = decision.get("merge", [])
            if not isinstance(merge_values, list):
                raise InputError("merge must be an array")
            records = [primary]
            records.extend(
                _identity(value, ordered, f"decisions[{decision_index}].merge[{index}]")
                for index, value in enumerate(merge_values)
            )
            ids = [record["candidateId"] for record in records]
            if len(set(ids)) != len(ids) or claimed.intersection(ids):
                raise InputError("a candidate may be claimed only once")
            if any(
                record["category"] != primary["category"]
                or record["verdict"] != primary["verdict"]
                for record in records[1:]
            ):
                raise InputError("merged candidates must have the same category and verdict")

            root_cause = single_fix = None
            if len(records) > 1:
                root_cause = _text(
                    decision.get("sharedRootCause"),
                    f"decisions[{decision_index}].sharedRootCause",
                )
                single_fix = _text(
                    decision.get("singleFix"),
                    f"decisions[{decision_index}].singleFix",
                )
        except InputError:
            continue

        claimed.update(ids)
        accepted.append(
            _finding(
                records,
                shared_root_cause=root_cause,
                single_fix=single_fix,
            )
        )

    if not accepted:
        return None

    accepted_by_bucket: dict[tuple[int, int], list[dict[str, object]]] = {}
    for finding in accepted:
        primary = finding["records"][0]
        bucket = (CATEGORIES[primary["category"]], VERDICTS[primary["verdict"]])
        accepted_by_bucket.setdefault(bucket, []).append(finding)

    backfill_by_bucket: dict[tuple[int, int], list[dict[str, object]]] = {}
    for record in ordered:
        if record["candidateId"] in claimed:
            continue
        bucket = (CATEGORIES[record["category"]], VERDICTS[record["verdict"]])
        backfill_by_bucket.setdefault(bucket, []).append(_finding([record]))

    findings: list[dict[str, object]] = []
    for bucket in sorted(set(accepted_by_bucket) | set(backfill_by_bucket)):
        findings.extend(accepted_by_bucket.get(bucket, []))
        findings.extend(backfill_by_bucket.get(bucket, []))
    return findings


def _normalize(value: str) -> str:
    return ASCII_WHITESPACE.sub(" ", value).strip(" \t\n\r\v\f")


def _fallback(ordered: list[dict[str, Any]]) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], list[dict[str, Any]]] = {}
    for record in ordered:
        key = (
            record["file"],
            record.get("line"),
            record["category"],
            record["verdict"],
            _normalize(record["summary"]),
            _normalize(record["failure_scenario"]),
        )
        groups.setdefault(key, []).append(record)
    return [_finding(records) for records in groups.values()]


def finalize(payload: object) -> dict[str, object]:
    ordered = _ordered(_survivors(payload))
    synthesis = payload.get("synthesis") if isinstance(payload, dict) else None
    findings = _synthesis_findings(synthesis, ordered)
    if findings is None:
        mode = "fallback"
        findings = _fallback(ordered)
        summary = None
    else:
        mode = "synthesis"
        summary = synthesis["summary"]

    accounted = [candidate_id for finding in findings for candidate_id in finding["candidateIds"]]
    expected = [record["candidateId"] for record in ordered]
    if sorted(accounted) != sorted(expected) or len(accounted) != len(set(accounted)):
        raise InputError("assembled findings do not exactly partition survivor IDs")

    result: dict[str, object] = {
        "mode": mode,
        "reported": len(findings),
        "findings": findings,
    }
    if summary is not None:
        result["summary"] = summary
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "finalize"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = json.loads(args.input.read_text())
        result = prepare(payload) if args.command == "prepare" else finalize(payload)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    except (InputError, json.JSONDecodeError, OSError) as exc:
        print(f"assemble_report: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
