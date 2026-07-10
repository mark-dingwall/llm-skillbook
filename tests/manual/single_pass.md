# single-pass smoke

1. Build a prompt for reviewing `multi_review/core/paths.py` (or any small file).
2. `/multi-review --prompt-files <yaml>` (mode: inline, reviewers: claude+agy, synthesizer: claude).
3. Verify:
   - REVIEW.md written to `<cwd>/REVIEW-<slug>.md` (cwd root per spec §4.2 — NOT under `.multi-review/`); auto-suffix on collision.
   - Two `## <reviewer>` sections
   - Consensus Summary section
   - Filename derived from synth
   - Harvest row queued in `pending-harvest/`
   - Permission prompt for harvest write at end
4. After approving harvest, verify EXPERIMENTS.md regenerated with the new row visible.
