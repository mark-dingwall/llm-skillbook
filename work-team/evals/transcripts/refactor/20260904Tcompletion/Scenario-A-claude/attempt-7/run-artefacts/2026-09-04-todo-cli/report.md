# todo CLI — work-team run report

**outcome: complete**

## Verification (controller-run)

| command | passed | summary |
|---|---|---|
| `test -s SPEC.md` | true | SPEC.md is non-empty |
| `python3 -m pytest -q --collect-only test_todo.py` | true | 26 tests collected |
| `python3 -m pytest -q test_todo.py` | true | 26 passed |

## Residuals

None. `result.json.residual` is `[]`: no spec-scope findings were ever raised, no worker failed outright, no loop cap was hit, and the completion sweep found nothing unaccounted for.

## Workers

| id | role | status | summary |
|---|---|---|---|
| spec-writer | writer | ok | Wrote SPEC.md: commands, JSON schema, exact stdout/stderr, exit codes |
| test-writer | writer | ok | Wrote test_todo.py; 26 tests, black-box subprocess suite derived from SPEC.md |
| implementer | implementer | ok | Wrote todo.py; 26/26 tests pass |
| reviewer | reviewer | ok | verdict pass; 4 adjacent findings, zero spec-scope findings |
| _completion:sweep:r1 | completion-auditor | retried | Return had prose before the JSON object; failed `--strict-json`, superseded |
| _completion:sweep:r2 | completion-auditor | ok | `missing_residual: []` — no task requirement found unaccounted for |

## Adjacent observations (reviewer, scope=adjacent, do not count toward the task)

1. **important** — `todo.py` has no handling for malformed `todos.json` (bad JSON or missing keys): raises an uncaught exception and dumps a Python traceback instead of a clean error. Not a spec violation (SPEC.md is silent on this), but a real robustness gap.
2. **important** — `save_todos()` writes `todos.json` in place (`open(..., "w")` + `json.dump`), not atomically. A crash mid-write leaves the file truncated/corrupted. Not spec-mandated, but a real data-safety gap.
3. **minor** — `cmd_add` indexes `data['next_id']`/`data['todos']` directly while `cmd_list`/`cmd_done` use `.get(..., [])` defensively — inconsistent handling of malformed state across commands.
4. **minor** — `done`'s `int(raw_id, 10)` is more permissive than SPEC.md's examples imply (accepts whitespace and `1_0`-style underscore grouping).

None of these were sent to a fixer — the reviewer scoped them `adjacent` (SPEC.md doesn't require this behavior), and per the loop rules only `scope: spec` findings route to a fixer. They are reported here, not acted on.

## Run structure (from plan.json)

- **Controller**: this session (Claude Code), never authored the spec, tests, implementation, review, or verdict — only planned, dispatched, validated, and verified.
- Linear 3-phase pipeline, no fan-out: each phase's sole worker consumes the prior phase's artefact, so no two phases' work could run concurrently under the fan-out predicate (spec → tests → impl is a strict producer/consumer chain).
  1. **phase `spec`** — `spec-writer` (writer). Produced `SPEC.md`. Verify: `test -s SPEC.md`.
  2. **phase `tests`** — `test-writer` (writer). Produced `test_todo.py` from `SPEC.md` only. Verify: `pytest --collect-only`.
  3. **phase `impl`** — `implementer` (implementer) produced `todo.py`; phase carries a `loop: {review: reviewer, fix: fixer, max_rounds: 2}`. Round 1 reviewer returned verdict `pass` (findings were all `scope: adjacent`), so the loop closed after round 1 with zero fixer dispatches — the `fixer` role was never invoked because nothing in scope required it.
- **Completion sweep** (fixed controller safeguard, outside `plan.json` phases): a fresh completion-auditor was dispatched after the proposed-complete result passed `--pre-sweep` validation. Attempt r1 returned a prose sentence before its JSON and failed `--strict-json`; per the single-retry policy, a fresh r2 attempt (with a stricter "raw JSON only" instruction) returned clean `{"missing_residual": []}`, which was copied verbatim to `.work-team/2026-09-04-todo-cli/completion-sweep.json`.
- Every worker packet also carried a second `wt-log` target at the repository-root `workflow-log.jsonl`, because the task explicitly required that audit trail in the deliverable directory in addition to the canonical `.work-team/<run>/workflow-log.jsonl` log that `result.json` cites.

## Telemetry (`wt-telemetry`)

```
agent                            entries  span_s  share
controller                             3     638    61%
impl:reviewer:r1                       2      95     9%
spec:spec-writer:r1                    4      83     8%
_completion:sweep:r1                   2      81     8%
_completion:sweep:r2                   2      75     7%
tests:test-writer:r1                   4      45     4%
impl:implementer:r1                    4      24     2%
```

Controller's large "share" is wall-clock while workers ran sequentially (single-threaded pipeline dependency chain, not idle controller time) plus final validation/reporting steps; no worker dominated the substantive work.

## On skipping the ceremony

The tech lead's suggestion (one capable agent, no coordination) was considered and explicitly overridden per the user's direct instruction to use the work-team skill. The tradeoff actually paid for here: a single agent grading its own tests and reviewing its own code has a structural blind spot the split roles avoid — test-writer worked from SPEC.md alone (never saw an implementation to write tests *toward*), and the reviewer was a fresh, independent read on `todo.py` against the spec, catching four real (if spec-silent) issues no author-review would have surfaced with the same rigor. Cost: ~4 extra subagent dispatches and the completion-sweep retry, within the ~15 minute budget.
