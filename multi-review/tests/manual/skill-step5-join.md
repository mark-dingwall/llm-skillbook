# Manual smoke: Step 5 join barrier — synchronous Task + BashOutput

## Purpose

Verify that the Claude Task result is captured synchronously and the join barrier
waits only for external reviewers' Bash background jobs.

## Setup

Run a SKILL session with at least one external reviewer (e.g. `agy`) and the `claude`
reviewer both active. Observe the join-barrier step.

## Expected polling pattern

| Reviewer type | Dispatch tool | Completion handling | ID type |
|---|---|---|---|
| `claude` | Task | Return value captured before join barrier | none |
| `agy`, `codex`, `opencode`, `pykrete`, `grok` | `Bash run_in_background` | `BashOutput <bash_id>` | Bash background id |

1. Confirm the Claude Task return is captured and persisted to
   `<REVIEWS_DIR>/claude.md` plus `<REVIEWS_DIR>/claude.state.json` before the
   join barrier begins.
2. At the join barrier, confirm `BashOutput` is used only for external Bash
   background ids; no follow-up polling call is made for Claude.
3. `BashOutput` returns `exited: true` when an external background process finishes.
   Poll until that flag is set for every external bash_id.

## Failure modes

- **Wrong tool — follow-up polling after the synchronous Claude Task**: treats a
  completed return as a live task and can lose or duplicate the captured review.
- **Wrong tool — BashOutput on a non-Bash id**: returns an error like "bash not
  found" or similar.
- **Symptom**: join barrier exits too early (external reviewer not yet done) or
  one reviewer's `.state.json` is missing/empty when the aggregator runs.

## Pass criteria

- Each reviewer's output appears in `<REVIEWS_DIR>/` before Step 6 begins.
- No unexpected task/polling errors in the session transcript.
- `BashOutput` targets only external-reviewer Bash ids.
