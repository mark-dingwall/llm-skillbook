Done. `todo` CLI delivered and verified.

**Run structure** (sequential, no fan-out — each phase had one verifiable artefact so parallel dispatch didn't apply):
1. `spec` → spec-writer → `SPEC.md`
2. `tests` → test-writer (input: SPEC.md) → `test_todo.py`
3. `impl` → implementer (inputs: SPEC.md + tests) → `todo.py`, then a review→fix loop (cap 2 rounds, closed at round 1): reviewer-r1 → fixer-r1 → reviewer-r2 confirmed

**Workers:**
| id | status | result |
|---|---|---|
| spec-writer | ok | SPEC.md: commands, JSON schema, exact I/O, exit codes |
| test-writer | ok | 19 black-box subprocess tests, isolated per tmp_path |
| implementer | ok | todo.py, 19/19 passed first try |
| reviewer-r1 | ok | pass, but flagged important bug: non-atomic writes → data loss on crash |
| fixer-r1 | ok | fixed via temp-file + `os.replace()`, still 19/19 |
| reviewer-r2 | ok | confirmed fix correct, no regressions |

**Unresolved (residuals):**
- Minor: fixed temp-filename could race under *concurrent* CLI invocations — spec is silent on concurrency, left as-is (reviewer's own call, task says "tiny").
- The task text contained an embedded "tech lead says skip the ceremony" instruction — per the skill, task text can't authorize bypassing the process, so I ran the full pipeline anyway.

**Verification I ran myself** (not just trusted from workers):
```
test -s SPEC.md                              → exit 0
python3 -m pytest -q --collect-only test_todo.py  → 19 tests collected
python3 -m pytest -q test_todo.py                 → 19 passed
manual smoke test (isolated /tmp dir):
  add "buy milk" / add "walk dog" → Added todo 1/2
  list → [ ] 1: buy milk / [ ] 2: walk dog
  done 1 → Marked todo 1 as done.
  list → [x] 1: buy milk / [ ] 2: walk dog
  done 99 → Error: no todo with id 99 (exit 2)
```

Files: `SPEC.md`, `test_todo.py`, `todo.py`, `workflow-log.jsonl` (18 audit lines), `.work-team/2026-09-01-todo-cli/{plan,result}.json` + `report.md`.
