"""multi_review.core.aggregate — output path resolution and REVIEW.md writer.

Contains:
- resolve_output_path: auto-suffix collision avoidance
- yaml_list: compact YAML list formatter
- write_review_md: emit YAML frontmatter + per-reviewer sections + Consensus Summary
"""
from __future__ import annotations

import json
import time
from pathlib import Path

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


# -------- REVIEW.md writer --------

def write_review_md(
    *,
    path: Path,
    results: list[ReviewerResult],
    synthesis_text: str | None,
    mode: str,
    task: str,
    reviewers_attempted: list[str],
    input_files: list[Path] | None = None,
    models: dict[str, str] | None = None,
    synthesizer: str | None = None,
    synthesized_at: str | None = None,
    pair_id: str | None = None,
    prompt_file: str | None = None,
) -> None:
    """Write REVIEW.md with YAML frontmatter + per-reviewer sections.

    ``pair_id`` and ``prompt_file`` are accepted now (for forward-compat) but
    wired in by later tasks. When non-null they appear in the frontmatter.
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
    lines.append(f"mode: {mode}")
    lines.append(f"reviewers_succeeded: {yaml_list([r.cli for r in succeeded])}")
    lines.append(f"reviewers_failed: {yaml_list([r.cli for r in failed])}")
    lines.append(f"reviewed_at: {reviewed_at}")
    if input_files is not None:
        lines.append(f"files: {yaml_list([str(f) for f in input_files])}")
    if pair_id is not None:
        lines.append(f"pair_id: {pair_id}")
    if prompt_file is not None:
        lines.append(f"prompt_file: {prompt_file}")
    if models:
        lines.append("models:")
        for k, v in models.items():
            lines.append(f"  {k}: {json.dumps(v)}")
    lines.append("usage:")
    lines.extend(usage_block_lines)
    if synthesizer and synthesized_at:
        lines.append(f"synthesizer: {synthesizer}")
        lines.append(f"synthesized_at: {synthesized_at}")

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

    lines.append("## Consensus Summary")
    lines.append("")
    if synthesis_text:
        lines.append(synthesis_text.strip())
    elif len(succeeded) < 2:
        lines.append("_Consensus: n/a (insufficient reviewers — need ≥2 successful reviews)_")
    else:
        lines.append("_Consensus synthesis skipped (run without --no-synthesize to populate)._")
    lines.append("")

    try:
        path.write_text("\n".join(lines))
    except OSError as e:
        raise SystemExit(f"Error writing {path}: {e}")
