# Manual smoke: Step 5 join barrier — BashOutput vs TaskGet

## Purpose

Verify that the join barrier uses the correct polling tool for each reviewer type,
and that mixing them produces an identifiable error.

## Setup

Run a SKILL session with at least one external reviewer (e.g. `agy`) and the `claude`
reviewer both active. Observe the join-barrier step.

## Expected polling pattern

| Reviewer type | Dispatch tool | Poll tool | ID type |
|---|---|---|---|
| `claude` | Task | `TaskGet <task_id>` | Task UUID |
| `agy`, `codex`, `opencode` | `Bash run_in_background` | `BashOutput <bash_id>` | Bash background id |

1. After dispatch, record which reviewers got a `task_id` vs a `bash_id`.
2. At the join barrier, confirm `TaskGet` is called only on Task UUIDs and
   `BashOutput` only on Bash background ids.
3. `BashOutput` returns `exited: true` when the background process finishes.
   Poll until that flag is set for every external bash_id.
4. `TaskGet` returns `status: "complete"` when the subagent finishes.

## Failure modes

- **Wrong tool — TaskGet on a bash_id**: returns an error like "task not found"
  or similar. No reviewer output is captured; the run hangs or skips a reviewer.
- **Wrong tool — BashOutput on a task_id**: returns an error like "bash not found"
  or similar. Same consequence.
- **Symptom**: join barrier exits too early (external reviewer not yet done) or
  one reviewer's `.state.json` is missing/empty when the aggregator runs.

## Pass criteria

- Each reviewer's output appears in `<REVIEWS_DIR>/` before Step 6 begins.
- No "task not found" / "bash not found" errors in the session transcript.
- `TaskGet` and `BashOutput` calls each target the correct id type.
