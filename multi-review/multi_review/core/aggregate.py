"""multi_review.core.aggregate — output path resolution and REVIEW.md writer.

Contains:
- resolve_output_path: auto-suffix collision avoidance
- yaml_list: compact YAML list formatter
- write_review_md: emit YAML frontmatter + per-reviewer sections + Consensus Summary
- review-loop opt-in (require_complete_status): parse_review_record_expectations,
  parse_qualified_review_record — the review-record classifier for the narrow
  review-loop driver opt-in (multi-review/BACKLOG.md "Priority consumer
  contract: review-loop"). Independent of, but shape-compatible with, the
  review-loop-side classifier in review_loop/prompts.py:validate_review_report
  (pinned by review-loop/tests/contract/test_multi_review_records.py).
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
# Validates one participant's fenced ```review-record``` JSON block against a
# controller-supplied expectation (multi_review.py's --review-record-expect),
# and the exact terminal REVIEW-STATUS line. Only exercised when
# PromptFile.require_complete_status is set — every other caller's output is
# untouched. Field shape (_RECORD_KEYS/_FINDING_KEYS/_SEVERITIES) mirrors
# review_loop/prompts.py's ReviewRecord/SourceFinding so a valid review-loop
# report qualifies here too; the two classifiers are independent code (this
# repo does not import review_loop), pinned equivalent by
# review-loop/tests/contract/test_multi_review_records.py.

class ReviewRecordError(Exception):
    """A --review-record-expect argument or a reviewer's review-record body
    was rejected as malformed, mismatched, or not terminally COMPLETE."""


_EXPECTATION_KEYS = {
    "request_id", "role", "charter_id", "target_seal",
    "round_input_seal", "scope_locator_ids", "raw_report_id",
}
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


def parse_review_record_expectations(raw: str, reviewers: list[str]) -> dict[str, dict]:
    """Parse --review-record-expect JSON into a per-CLI expectation mapping.

    Every name in ``reviewers`` must have an entry with exactly
    _EXPECTATION_KEYS. Raises ReviewRecordError on any structural problem —
    this is startup-time (pre-dispatch) config validation, not a runtime
    reviewer-output classification.
    """
    try:
        data = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ReviewRecordError(f"--review-record-expect is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ReviewRecordError("--review-record-expect must be a JSON object")

    expectations: dict[str, dict] = {}
    for cli in reviewers:
        entry = data.get(cli)
        if not isinstance(entry, dict) or set(entry) != _EXPECTATION_KEYS:
            raise ReviewRecordError(
                f"--review-record-expect is missing or malformed for reviewer {cli!r}"
            )
        for key in ("request_id", "role", "charter_id", "target_seal", "raw_report_id"):
            if not _nonempty_str(entry[key]):
                raise ReviewRecordError(
                    f"--review-record-expect[{cli!r}].{key} must be a non-empty string"
                )
        if entry["round_input_seal"] is not None and not _nonempty_str(entry["round_input_seal"]):
            raise ReviewRecordError(
                f"--review-record-expect[{cli!r}].round_input_seal must be null or non-empty"
            )
        scope = entry["scope_locator_ids"]
        if (
            not isinstance(scope, list)
            or not all(_nonempty_str(s) for s in scope)
            or len(set(scope)) != len(scope)
        ):
            raise ReviewRecordError(
                f"--review-record-expect[{cli!r}].scope_locator_ids must be unique non-empty strings"
            )
        expectations[cli] = dict(entry)
    return expectations


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
