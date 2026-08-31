Done. `todo` CLI delivered, tested, reviewed, one bug found and fixed.

**Run structure**
Sequential pipeline (spec → tests → impl → review), controller-orchestrated. No parallel phases — each stage strictly gates the next (can't write tests before the spec exists, can't implement before tests exist, can't review before there's an implementation). Kept the pipeline as instructed rather than collapsing to one agent per the tech lead's suggestion, since that was your explicit ask.

**Workers**
| id | phase | result |
|---|---|---|
| spec-1 | specification | `SPEC.md` — schema, id scheme, exact I/O formats, exit codes |
| tests-1 | tests | `test_todo.py`, 19 tests, written blind to implementation |
| impl-1 | implementation | `todo.py` (68 lines), reported 19/19 passing |
| review-1 | review | **verdict: fail** — found real spec violation |
| controller (me) | fix | patched bug, added regression test, re-verified |

**Unresolved → fixed**
review-1 caught that `load()` crashed with an unhandled `JSONDecodeError` on an existing-but-empty `todo.json` (spec requires empty/missing file → `No todos.`). tests-1's suite had only covered the *missing*-file case, missing that blind spot. I fixed `load()` (treat blank file content as `[]`) and added `test_list_empty_existing_file` to close the gap. Minor non-blocking note from review: `save()` isn't atomic (no temp-file+rename) — not spec-required, flagging only.

**Verification**
```
20 passed in 1.18s
```
Manual smoke test also run (add/list/done/unknown-id) — output matched spec exactly. Full audit trail in `workflow-log.jsonl` (6 lines, one per worker action).
