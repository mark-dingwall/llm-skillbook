# paired-pass smoke (mode: both, if_drift: ignore)

1. Build a prompt with `mode: both`, `if_drift: ignore`.
2. `/multi-review --prompt-files <yaml>`.
3. Verify:
   - Pass 1 completes, then pass 2 runs immediately in the same turn (no drift prompt, no countdown — there is no inter-pass delay in v0.2).
   - One `<cwd>/REVIEW-<slug>-<pass-1-mode>.md` at cwd root (e.g. `REVIEW-auth-review-reference.md`).
   - One `<cwd>/REVIEW-<slug>-<pass-2-mode>.md` at cwd root (e.g. `REVIEW-auth-review-inline.md`).
   - Both auto-suffixed independently on collision.
   - No `REVIEW.md` left under `.multi-review/sessions/<run_id>/` for either pass — Step 10 promoted both, Step 11 cleaned up.
   - One paired report at `<CENTRAL_PATH>/reports/<project>-<date>-<pair-id>.md` (path resolved from config.json).
   - `<CENTRAL_PATH>/EXPERIMENTS.md` updated with both rows.
