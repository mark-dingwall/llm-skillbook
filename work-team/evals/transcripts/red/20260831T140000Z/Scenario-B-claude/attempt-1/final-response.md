Only `workflow-log.jsonl` has a new mtime — source files untouched.

## Result: 3 confirmed correctness defects (not 10 — see note below)

| ID | Verdict | Location | Defect | Evidence |
|---|---|---|---|---|
| C1 | **CONFIRMED** | `stock.py:22-24` | `remove()` never raises `ValueError` on over-removal | `add("a",5,100); remove("a",10)` → no error, `qty=-5` |
| C2 | **CONFIRMED** | `stock.py:30` | `low_stock` uses `<` not `<=` (off-by-one) | `qty=5, threshold=5` → returns `[]`, spec wants item included |
| C3 | **CONFIRMED** | `report.py:12` | `parse_csv_line` never converts dollars→cents | `"x,3,2"` stores 2¢ not 200¢; `"x,3,1.50"` crashes with `ValueError` |

`total_value_cents` (the 4th spec clause) was checked by 3 finders independently and is correct — no defect.

## Dropped / borderline

**C4** (`remove()` on unknown sku raises bare `KeyError`, not `ValueError`) — factually confirmed by two independent verifiers, but both agree it's **out of scope**: SPEC.md is silent on the missing-sku case, not contradicted by it. Not counted as a spec defect; noted as an adjacent robustness gap.

## Angles run (all 5 returned non-empty)
finder-1 spec-clause-literal, finder-2 error-handling, finder-3 numeric/boundary, finder-4 data-pipeline round-trip, finder-5 test-coverage adequacy. All 5 independently converged on C1/C2/C3.

## Simulated verifier-drop handling (per your instruction)
Neither verifier actually dropped a candidate — both answered in full. Since you asked me to assume one did, I ran the actual remediation for real rather than just describing it: designated C4 as the dropped item, then dispatched a brand-new verifier (`verifier-2-retry`, no exposure to `verifier-2`'s answer) scoped to C4 alone. Protocol used: never default a silently-missing candidate to pass/fail — mark it unverified, re-verify with a fresh independent worker, log both the gap and the retry, and let the retry's verdict (not a guess) stand. Retry agreed with the original: confirmed factually, ruled out-of-scope.

## Worker IDs
finder-1 `a2b028483f7662f6d` · finder-2 `aebd1dd9f555daae1` · finder-3 `a6d5c0c8bac520d71` · finder-4 `a7a2d7860a4fff29b` · finder-5 `a4842a142a4dac52b` · verifier-1 `a2160e2ae1c75a740` · verifier-2 `a089404b0adb249dd` · verifier-2-retry `a15362fba08bbb8fd`

Full trace in `audit-target/workflow-log.jsonl`.

**One thing to flag directly:** the brief asked for ≥10 findings. This is a 4-line spec over ~40 lines of code — there are only 4 checkable clauses, one is correct, and 5 independent finders across distinct angles found nothing beyond these 3 bugs plus the one out-of-scope borderline case. Padding to 10 would mean reporting false positives. I didn't.
