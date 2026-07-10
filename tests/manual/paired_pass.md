# paired-pass smoke (mode: both, foreground, if_drift: ignore)

1. Build prompt with mode: both, delay_type: foreground, delay: 30, if_drift: ignore.
2. `/multi-review --prompt-files <yaml>`.
3. Verify:
   - Pass 1 completes; countdown appears.
   - Pass 2 runs automatically without drift prompt.
   - One `<cwd>/REVIEW-<slug>-<pass-1-mode>.md` at cwd root (e.g. `REVIEW-auth-review-reference.md`).
   - One `<cwd>/REVIEW-<slug>-<pass-2-mode>.md` at cwd root (e.g. `REVIEW-auth-review-inline.md`).
   - Both auto-suffixed independently on collision.
   - No `REVIEW.md` remaining under `.multi-review/sessions/<run_id>/` for either pass (Step 12 cleanup; both files were promoted in Step 11).
   - One paired report at `<CENTRAL_PATH>/reports/<project>-<date>-<pair-id>.md` (resolved from config.json).
   - EXPERIMENTS.md updated with both rows.
