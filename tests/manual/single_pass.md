# single-pass smoke

1. Build a prompt for reviewing `multi_review/core/paths.py` (or any small file).
2. `/multi-review --prompt-files <yaml>` (mode: inline, reviewers: claude+agy, synthesizer: claude).
3. Verify:
   - REVIEW.md written to `<cwd>/REVIEW-<slug>.md` (cwd root per spec §4.2 — NOT under `.multi-review/`); auto-suffix on collision.
   - Two `## <reviewer>` sections
   - Consensus Summary section
   - Filename derived from synth
   - Deprecated harvest row appended directly to `<CENTRAL_PATH>/runs.jsonl`
     (or buffered in `pending-harvest/` only if that write fails)
   - Permission prompt, if the `runs.jsonl` path is not allowlisted, occurs for
     the direct write
4. After permitting the direct write, verify the new row in
   `<CENTRAL_PATH>/runs.jsonl`; regenerate `<CENTRAL_PATH>/EXPERIMENTS.md` with
   `uv run python -m multi_review.cli.report regen` if you need the historical
   log refreshed.
