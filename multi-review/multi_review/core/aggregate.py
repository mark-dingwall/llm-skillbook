"""multi_review.core.aggregate — output path resolution and REVIEW.md writer.

Contains:
- resolve_output_path: auto-suffix collision avoidance
- yaml_list: compact YAML list formatter
- write_review_md: emit YAML frontmatter + per-reviewer sections + Consensus Summary
- review-loop opt-in (require_complete_status): parse_raw_report_ids,
  parse_verbatim_dispatch_header, parse_qualified_review_record — the
  review-record classifier for the narrow review-loop driver opt-in
  (multi-review/BACKLOG.md "Priority consumer contract: review-loop").
  Independent of, but shape-compatible with, the review-loop-side classifier
  in review_loop/prompts.py:validate_review_report (pinned by
  review-loop/tests/contract/test_multi_review_records.py).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import yaml

from multi_review.core.fanout import ReviewerResult


# -------- Output path resolution --------

def resolve_output_path(path: Path, *, force: bool = False) -> Path:
    """Return a path that does not collide with an existing file.

    If ``path`` does not exist, return it unchanged.
    If ``path`` exists and ``force`` is False, auto-suffix: ``REVIEW.md`` →
    ``REVIEW-2.md`` → ``REVIEW-3.md`` …
    If ``force`` is True, return ``path`` as-is (caller handles overwrite).

    Preserves the no-silent-overwrite invariant: default behaviour always
    returns a path that is safe to write without clobbering existing work.
    """
    if not path.exists() or force:
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for n in range(2, 100):
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
    raise SystemExit(f"error: too many existing files matching {path}")


# -------- YAML helpers --------

def yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(json.dumps(i) for i in items) + "]"


# -------- review-loop opt-in: review-record classifier --------
#
# Validates one participant's fenced ```review-record``` JSON block against
# the dispatch fields parsed from the driver's own verbatim prompt (the
# single source of truth for what was actually sent — see
# parse_verbatim_dispatch_header) plus a driver-side raw_report_id (see
# parse_raw_report_ids), and the exact terminal REVIEW-STATUS line. Only
# exercised when PromptFile.require_complete_status is set — every other
# caller's output is untouched. Field shape (_RECORD_KEYS/_FINDING_KEYS/
# _SEVERITIES) mirrors review_loop/prompts.py's ReviewRecord/SourceFinding so
# a valid review-loop report qualifies here too; the two classifiers are
# independent code (this repo does not import review_loop), pinned
# equivalent by review-loop/tests/contract/test_multi_review_records.py.

class ReviewRecordError(Exception):
    """A --raw-report-id argument, the verbatim prompt's dispatch header, or a
    reviewer's review-record body was rejected as malformed, mismatched, or
    not terminally COMPLETE."""


_RECORD_KEYS = {
    "request_id", "role", "charter_id", "target_seal",
    "round_input_seal", "scope_locator_ids", "source_findings",
}
_FINDING_KEYS = {"id", "claim", "severity", "locator_ids"}
_SEVERITIES = {"Minor", "Important", "Critical"}
_FENCE_RE = re.compile(r"```review-record\r?\n(.*?)\r?\n```", re.DOTALL)
_TERMINAL_COMPLETE = "REVIEW-STATUS: COMPLETE"
_TERMINAL_UNABLE = "REVIEW-STATUS: UNABLE"


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """json.loads object_pairs_hook: a duplicate key silently keeps the last
    value under the stdlib default. A reviewer echoing a benign value first
    and a poisoned one second must not slip through."""
    seen: set[str] = set()
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key: {key!r}")
        seen.add(key)
        result[key] = value
    return result


def _nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def parse_raw_report_ids(pairs: list[str], reviewers: list[str]) -> dict[str, str]:
    """Parse repeated --raw-report-id CLI=ID values into a {cli: id} map.

    raw_report_id is a DRIVER-SIDE label assigned by slot — the reviewer's
    review-record body never declares it, so it is never compared against
    anything the reviewer sends. It is purely echoed into the qualified
    record for that CLI's frontmatter entry, correlating the slot to the
    controller's preallocated artifact ID. Every name in ``reviewers`` must
    have exactly one entry; a missing slot fails closed rather than silently
    omitting that reviewer's raw_report_id.
    """
    result: dict[str, str] = {}
    for pair in pairs:
        cli, sep, raw_id = pair.partition("=")
        if not sep or not cli or not raw_id:
            raise ReviewRecordError(f"--raw-report-id must be CLI=ID, got {pair!r}")
        if cli in result:
            raise ReviewRecordError(f"--raw-report-id specified more than once for {cli!r}")
        result[cli] = raw_id
    missing = [cli for cli in reviewers if cli not in result]
    if missing:
        raise ReviewRecordError(f"--raw-report-id missing for reviewer(s): {', '.join(missing)}")
    return result


_DISPATCH_HEADER_KEYS = (
    "request_id", "role", "charter_id", "target_seal", "round_input_seal", "scope_locator_ids",
)


def parse_verbatim_dispatch_header(prompt_text: str) -> dict:
    """Derive expected review-record dispatch fields from the verbatim prompt
    this driver actually sent — the single source of truth, never a second
    caller-supplied channel that could drift from what was dispatched.

    Mirrors review_loop/resources/review.md's fixed header shape: one
    ``key: value`` line per _DISPATCH_HEADER_KEYS name, in the leading block
    before the first blank line. ``round_input_seal`` is the literal token
    ``null`` for round one, else a non-empty string. ``scope_locator_ids`` is
    a JSON array of unique non-empty strings (JSON, not a bespoke delimiter,
    so it round-trips unambiguously through str.format's Mapping[str, str]
    substitution contract in review_loop/prompts.py:render_prompt).
    """
    header_lines: list[str] = []
    for line in prompt_text.splitlines():
        if line.strip() == "":
            break
        header_lines.append(line)

    fields: dict[str, str] = {}
    for line in header_lines:
        key, sep, value = line.partition(": ")
        if sep and key in _DISPATCH_HEADER_KEYS and key not in fields:
            fields[key] = value

    missing = [key for key in _DISPATCH_HEADER_KEYS if key not in fields]
    if missing:
        raise ReviewRecordError(
            f"verbatim prompt is missing dispatch header field(s): {', '.join(missing)}"
        )
    for key in ("request_id", "role", "charter_id", "target_seal"):
        if not _nonempty_str(fields[key]):
            raise ReviewRecordError(f"verbatim prompt dispatch header {key} must be non-empty")

    round_input_seal: str | None = fields["round_input_seal"]
    if round_input_seal == "null":
        round_input_seal = None
    elif not _nonempty_str(round_input_seal):
        raise ReviewRecordError(
            "verbatim prompt dispatch header round_input_seal must be 'null' or non-empty"
        )

    try:
        scope_locator_ids = json.loads(fields["scope_locator_ids"])
    except json.JSONDecodeError as exc:
        raise ReviewRecordError(
            f"verbatim prompt dispatch header scope_locator_ids is not valid JSON: {exc}"
        ) from exc
    if (
        not isinstance(scope_locator_ids, list)
        or not all(_nonempty_str(s) for s in scope_locator_ids)
        or len(set(scope_locator_ids)) != len(scope_locator_ids)
    ):
        raise ReviewRecordError(
            "verbatim prompt dispatch header scope_locator_ids must be a JSON array "
            "of unique non-empty strings"
        )

    return {
        "request_id": fields["request_id"],
        "role": fields["role"],
        "charter_id": fields["charter_id"],
        "target_seal": fields["target_seal"],
        "round_input_seal": round_input_seal,
        "scope_locator_ids": scope_locator_ids,
    }


def _parse_source_findings(raw: object) -> list[dict] | None:
    if not isinstance(raw, list):
        return None
    findings: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) != _FINDING_KEYS:
            return None
        fid, claim, severity, locators = (
            item["id"], item["claim"], item["severity"], item["locator_ids"],
        )
        if not isinstance(fid, str) or not fid or fid in seen:
            return None
        if not isinstance(claim, str) or not claim or severity not in _SEVERITIES:
            return None
        if (
            not isinstance(locators, list)
            or not locators
            or not all(isinstance(x, str) and x for x in locators)
        ):
            return None
        seen.add(fid)
        findings.append({"id": fid, "claim": claim, "severity": severity,
                         "locator_ids": list(locators)})
    return findings


def parse_qualified_review_record(body: str, expected: dict) -> dict:
    """Validate one participant's review body against its expectation entry.

    Requires exactly one fenced ```review-record``` JSON block with exactly
    the review-loop record fields, an exact match against ``expected`` on
    every dispatch-identity field, and an exact terminal
    ``REVIEW-STATUS: COMPLETE`` line as the last non-blank line. Returns a
    qualified record dict (safe to serialize into REVIEW.md frontmatter via
    the YAML library) or raises ReviewRecordError.
    """
    fences = _FENCE_RE.findall(body)
    if len(fences) != 1:
        raise ReviewRecordError("report must contain exactly one fenced review-record")

    try:
        raw = json.loads(fences[0], object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ReviewRecordError(f"review-record is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict) or set(raw) != _RECORD_KEYS:
        raise ReviewRecordError("review-record has unknown or missing fields")

    if not (
        _nonempty_str(raw["request_id"]) and _nonempty_str(raw["role"])
        and _nonempty_str(raw["charter_id"]) and _nonempty_str(raw["target_seal"])
    ):
        raise ReviewRecordError("review-record has invalid identity fields")
    if raw["round_input_seal"] is not None and not _nonempty_str(raw["round_input_seal"]):
        raise ReviewRecordError("review-record round_input_seal must be null or non-empty")

    scope = raw["scope_locator_ids"]
    if (
        not isinstance(scope, list)
        or not all(_nonempty_str(s) for s in scope)
        or len(set(scope)) != len(scope)
    ):
        raise ReviewRecordError("review-record scope_locator_ids must be unique non-empty IDs")

    findings = _parse_source_findings(raw["source_findings"])
    if findings is None:
        raise ReviewRecordError("review-record source_findings is malformed")

    actual = (
        raw["request_id"], raw["role"], raw["charter_id"], raw["target_seal"],
        raw["round_input_seal"], tuple(scope),
    )
    want = (
        expected["request_id"], expected["role"], expected["charter_id"], expected["target_seal"],
        expected["round_input_seal"], tuple(expected["scope_locator_ids"]),
    )
    if actual != want:
        raise ReviewRecordError("review-record does not match dispatch expectation")

    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if not lines or lines[-1] not in (_TERMINAL_COMPLETE, _TERMINAL_UNABLE):
        raise ReviewRecordError("report is missing its exact terminal status line")
    if lines[-1] != _TERMINAL_COMPLETE:
        raise ReviewRecordError(f"terminal status is not COMPLETE: {lines[-1]!r}")

    return {
        "request_id": raw["request_id"],
        "role": raw["role"],
        "charter_id": raw["charter_id"],
        "target_seal": raw["target_seal"],
        "round_input_seal": raw["round_input_seal"],
        "scope_locator_ids": list(scope),
        "raw_report_id": expected["raw_report_id"],
        "terminal_status": "COMPLETE",
        "source_findings": findings,
    }


# -------- REVIEW.md writer --------

def write_review_md(
    *,
    path: Path,
    results: list[ReviewerResult],
    synthesis_text: str | None,
    synthesis_error: str | None = None,
    task: str,
    reviewers_attempted: list[str],
    input_files: list[Path] | None = None,
    models: dict[str, str] | None = None,
    synthesizer: str | None = None,
    synthesized_at: str | None = None,
    prompt_file: str | None = None,
    review_records: dict[str, dict] | None = None,
) -> None:
    """Write REVIEW.md with YAML frontmatter + per-reviewer sections.

    ``prompt_file`` is accepted for forward compatibility and appears in the
    frontmatter when non-null.

    ``review_records`` (review-loop opt-in only) is a ``{cli: qualified
    record}`` mapping from ``parse_qualified_review_record``. Reviewer-derived
    strings (claims, IDs) reach this block, so it is serialized through
    ``yaml.safe_dump`` rather than hand-built lines: a claim containing
    ``---`` or a bare ``key: value`` line must not be able to inject
    frontmatter structure. Omitted entirely when empty/None, so non-opt-in
    output is byte-for-byte unchanged.
    """
    succeeded = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    reviewed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    usage_block_lines = []
    for r in results:
        u = r.usage
        if u is not None:
            usage_block_lines.append(
                f"  {r.cli}: {{ input: {u.input_tokens}, output: {u.output_tokens}, "
                f"cached: {u.cached_tokens}, tool_calls: {u.tool_calls}, "
                f"elapsed_s: {r.elapsed:.1f} }}"
            )
        else:
            usage_block_lines.append(
                f"  {r.cli}: {{ elapsed_s: {r.elapsed:.1f} }}"
            )

    lines = ["---"]
    lines.append(f"task: {task}")
    lines.append(f"reviewers_succeeded: {yaml_list([r.cli for r in succeeded])}")
    lines.append(f"reviewers_failed: {yaml_list([r.cli for r in failed])}")
    lines.append(f"reviewed_at: {reviewed_at}")
    if input_files is not None:
        lines.append(f"files: {yaml_list([str(f) for f in input_files])}")
    if prompt_file is not None:
        lines.append(f"prompt_file: {json.dumps(prompt_file)}")
    lines.append("models:")
    for k, v in (models or {}).items():
        lines.append(f"  {k}: {json.dumps(v)}")
    lines.append("usage:")
    lines.extend(usage_block_lines)
    if synthesizer and synthesized_at:
        lines.append(f"synthesizer: {synthesizer}")
        lines.append(f"synthesized_at: {synthesized_at}")
    if review_records:
        block = yaml.safe_dump({"review_records": review_records},
                               default_flow_style=False, sort_keys=False)
        lines.extend(block.rstrip("\n").splitlines())

    lines.append("---")
    lines.append("")
    lines.append("# Cross-AI Review")
    lines.append("")

    for r in results:
        header = r.cli.capitalize() + " Review"
        if not r.ok:
            header += " (FAILED)"
        lines.append(f"## {header}")
        lines.append("")
        if r.ok:
            lines.append(r.text)
        else:
            lines.append(f"**Status:** failed — {r.error or 'unknown error'}")
            lines.append("")
            lines.append(f"Elapsed: {r.elapsed:.1f}s")
            if r.stderr_tail.strip():
                lines.append("")
                lines.append("Stderr tail:")
                lines.append("```")
                lines.append(r.stderr_tail.strip())
                lines.append("```")
            if r.text.strip():
                lines.append("")
                lines.append("Partial output:")
                lines.append("```")
                lines.append(r.text.strip()[:1000])
                lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    if synthesis_text:
        body = synthesis_text.strip()
        if not body.lstrip().startswith("## Consensus Summary"):
            body = "## Consensus Summary\n\n" + body.lstrip()
        lines.append(body)
    elif synthesis_error is not None:
        lines.append("## Consensus Summary")
        lines.append("")
        lines.append("_Consensus synthesis failed._")
        lines.append("")
        diagnostic = synthesis_error.strip()[:2000] or "unknown error"
        lines.append(f"Diagnostic: {json.dumps(diagnostic)}")
    elif len(succeeded) < 2:
        lines.append("## Consensus Summary")
        lines.append("")
        lines.append("_Consensus: n/a (insufficient reviewers — need ≥2 successful reviews)_")
    else:
        lines.append("## Consensus Summary")
        lines.append("")
        lines.append("_Consensus synthesis skipped (run without --no-synthesize to populate)._")
    lines.append("")

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except OSError as e:
        raise SystemExit(f"Error writing {path}: {e}")
