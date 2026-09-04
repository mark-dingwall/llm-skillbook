# Run report: 2026-09-04-todo-cli

## Outcome: partial

All controller-run verification passed (SPEC.md written, test suite collects,
and `todo.py` passes the full suite). The run is `partial`, not `complete`,
solely because the accepted reviewer left one unresolved `important`-severity
finding — per policy, an `important`/`blocker` finding blocks `complete`
regardless of whether it is `scope:spec` or `scope:adjacent`. Per the
completion-sweep rule, the sweep is not dispatched for a proposed `partial`
result, so this run carries no `sweep` field.

## Verification (run by the controller)

| command | passed | summary |
|---|---|---|
| `test -s SPEC.md` | true | SPEC.md exists and is non-empty |
| `python3 -m pytest -q --collect-only test_todo.py` | true | 20 tests collected, no collection errors |
| `python3 -m pytest -q test_todo.py` | true | 20 passed, 0 failed |

## Residuals (spec-scope findings count toward the task; none exist here)

No `scope: spec` findings were raised — nothing here counts against the task
itself. Two `scope: adjacent` observations remain open by design (adjacent
findings are reported, not fixed):

- **important** — `todo.py: save_tasks()` writes `todo.json` non-atomically
  (`open('w')` + `json.dump` straight onto the target). A crash/kill/full-disk
  mid-write can truncate/corrupt `todo.json`. SPEC.md does not require
  atomicity. *(source: reviewer:impl:reviewer:r1v2)*
- **minor** — `todo.py: load_tasks()` has no exception handling around
  `json.load()`; a malformed `todo.json` crashes with a raw traceback instead
  of a clean error + exit 1. SPEC.md is silent on malformed-file behavior.
  *(source: reviewer:impl:reviewer:r1v2)*

## Workers

| id | role | status | summary |
|---|---|---|---|
| spec-writer | writer | ok | Wrote SPEC.md: commands, `todo.json` schema, exact stdout/exit codes, Given/When/Then per command. |
| test-writer | writer | ok | Wrote `test_todo.py`, 20 black-box subprocess tests derived from SPEC.md. |
| impl:implementer:r1 | implementer | retried | Implemented `todo.py` correctly (verified independently: 20/20 passing) but returned prose wrapped around the JSON — failed the machine-read return contract, discarded, superseded by r2. |
| impl:implementer:r2 | implementer | ok | Re-verified the existing `todo.py` against SPEC.md/test_todo.py (no edits needed); pytest 20 passed. |
| impl:reviewer:r1 | reviewer | retried | Did a correct review (verdict pass, findings included) but also returned prose-wrapped JSON — discarded, superseded by r1v2. |
| impl:reviewer:r1v2 | reviewer | ok | Verdict: pass. 2 adjacent findings (non-atomic write, important; unhandled malformed JSON, minor). No `scope:spec` findings, so no fixer round was dispatched. |

## Run structure

- **Phase `spec`** (1 worker: `spec-writer`, role writer) → produced `SPEC.md`.
- **Phase `tests`** (1 worker: `test-writer`, role writer, input: `SPEC.md`) →
  produced `test_todo.py`.
- **Phase `impl`** (1 worker: `implementer`, role implementer, inputs:
  `SPEC.md`, `test_todo.py`) → produced `todo.py`, then a `loop` of
  `reviewer` → `fixer` (max_rounds: 2). Round 1 review returned `pass`
  (no fixer needed), so the loop ended after round 1.

**Nothing ran concurrently.** Every phase's sole worker consumed the prior
phase's output as an `input` (tests need SPEC.md; implementation needs
SPEC.md and test_todo.py), which the fan-out predicate forbids running in the
same phase/group — each producer/consumer pair is a strict dependency, so
phases ran strictly in sequence: spec → tests → impl → review. Each phase
also had exactly one independently-verifiable goal (one artefact, one
verification boundary), so there was no reason to split any phase into
multiple concurrent workers either.

**Two invalid-return retries occurred** (impl:implementer:r1 and
impl:reviewer:r1): both did correct underlying work but wrapped their JSON
return in prose, violating the machine-read return contract. Each was
retried once with a fresh attempt id per the fixed single-retry safeguard;
both retries succeeded cleanly. These are not counted as residual work.

## Telemetry (`wt-telemetry`)

```
agent                            entries  span_s  share
controller                             8     563    71%
impl:reviewer:r1                       2      81    10%
impl:reviewer:r1v2                     5      41     5%
spec:spec-writer:r1                    4      38     5%
tests:test-writer:r1                   4      38     5%
impl:implementer:r2                    3      17     2%
impl:implementer:r1                    4      16     2%

role                         agents entries max_span_s
controller                        1       8        563
impl:reviewer                     1       2         81
impl:reviewer:r1v2                1       5         41
spec:spec-writer                  1       4         38
tests:test-writer                 1       4         38
impl:implementer                  2       7         17
```

The controller's own span (563s) dominates wall-clock, which is expected: it
includes the idle time between dispatching one worker and receiving its
background completion notification, not actual controller compute.
