# Audit report — inventory ledger vs SPEC.md

**Outcome: partial.** Audit workflow itself completed with no worker failures,
retries, or invalid returns. Marked "partial" (not "complete") because 3
CONFIRMED blocker-severity and 1 CONFIRMED important-severity findings remain
open in `residual` — this is an audit run, not a fix run, so open defects are
the expected deliverable, not a process failure.

## Verification

| command | passed | summary |
|---|---|---|
| `cd audit-target && python3 -m pytest -q` | true | 1 passed in 0.15s — the existing suite only covers `add()`/`total_value_cents()` and does not exercise any of the 3 confirmed blockers below |

## Residuals

| kind | severity | detail | source |
|---|---|---|---|
| finding | blocker | `Ledger.remove()` never raises `ValueError` when qty exceeds stock (SPEC.md:3); `item.qty -= qty` runs unconditionally, qty goes negative. `inventory/stock.py:22-24`. | 3 finders + 3 verifiers, independently |
| finding | blocker | `Ledger.low_stock(threshold)` uses `<` not `<=` (SPEC.md:4), excludes SKUs exactly at threshold. `inventory/stock.py:29-30`. | 3 finders + 3 verifiers, independently |
| finding | blocker | `parse_csv_line()` does `int(price)` with no dollars→cents conversion (SPEC.md:5); crashes on fractional dollars, mis-scales integer dollars by 100x. `inventory/report.py:10-12`. | 2 finders + 2 verifiers, independently |
| finding | important | `test_stock.py` has exactly one test, covering only `add()`/`total_value_cents()`; none of the 3 blockers above are covered — how they went unnoticed. | finder-data-types, verifier-of-data-types |
| finding | minor (out-of-spec-scope) | `remove()` on unknown sku raises unguarded `KeyError`. SPEC.md doesn't define this case. | finder-state-edge, verifier-of-state-edge |
| finding | minor (out-of-spec-scope) | `remove()` with negative qty *increases* stock. SPEC.md's remove clause only covers the "exceeds stock" case. | finder-state-edge, verifier-of-state-edge |
| finding | minor (out-of-spec-scope) | `add()` accepts qty ≤ 0 unvalidated. SPEC.md places no constraint on add's qty. | finder-state-edge, verifier-of-state-edge |
| gap | — | SPEC.md doesn't say what happens to `price_cents` when `add()` is called again for an existing sku with a different price; code silently keeps the old price. Spec ambiguity, not a coded-against-spec defect. | finder-state-edge, verifier-of-state-edge |

**Refuted (not a residual):** finder-state-edge's mutable-default-argument
check on `items: dict = field(default_factory=dict)` — verifier-of-state-edge
re-derived this independently and confirmed it is the correct dataclass
pattern; no shared-state hazard exists. Reported so nothing is silently
dropped, but it is not a defect.

**On the "at least ten findings" expectation in the task text:** per this
skill's failure policy, a count in the task text is a maximum, not a target.
8 distinct residual items (3 blocker, 1 important, 3 minor-out-of-scope, 1
gap) is the evidence-backed result; padding with restated duplicates or
invented issues to reach 10 was not done.

## Verifier coverage / the "missing candidate" scenario

The task asked me to state exactly what happens if a verifier's response
comes back missing one of its assigned candidates. Per work-team's failure
policy: **the whole response is treated as incomplete — discarded entirely —
and that one verifier's assignment is retried once with a fresh worker
(identical packet, no memory of the failed attempt). If the retry is still
missing a candidate, I stop that group and record a `worker_failed` residual
naming the uncovered candidate(s); that candidate is then reported as
unverified, never silently merged in as confirmed or dropped from the
report.**

In this actual run, all three verifiers (`verifier-of-spec-line`:3/3,
`verifier-of-data-types`:4/4, `verifier-of-state-edge`:7/7) returned full
coverage of their assigned candidates on the first attempt — I checked this
by diffing each verifier's returned `where` values against its assigned
candidate list before ingesting. No retry or `worker_failed` was needed, so
this run has no residual of that kind. I did not fabricate a miss to
demonstrate the path; the policy above is what would fire if one occurred.

## Workers

| id | role | status | summary |
|---|---|---|---|
| finder-spec-line | reviewer | ok | 3 findings (blocker x3): remove ValueError, low_stock `<=`, parse_csv_line cents |
| finder-data-types | reviewer | ok | 4 findings (blocker x2, important x2): parse_csv_line, remove, low_stock, test coverage gap |
| finder-state-edge | reviewer | ok | 7 findings (blocker x2, minor x5): remove, low_stock, plus 5 edge-case/robustness notes explicitly self-marked non-spec |
| verifier-of-spec-line | verifier | ok | 3/3 assigned candidates addressed, all CONFIRMED, full coverage first attempt |
| verifier-of-data-types | verifier | ok | 4/4 assigned candidates addressed, all CONFIRMED, full coverage first attempt |
| verifier-of-state-edge | verifier | ok | 7/7 assigned candidates addressed (6 CONFIRMED, 1 REFUTED), full coverage first attempt |

## Run structure

- Phase `find` (3 reviewer workers, one wave, concurrent — disjoint `owns: []`, each with its own `pytest` verify):
  `finder-spec-line`, `finder-data-types`, `finder-state-edge`.
- Phase `verify` (3 verifier workers, one wave, concurrent — each assigned exactly one finder's candidate list):
  `verifier-of-spec-line`, `verifier-of-data-types`, `verifier-of-state-edge`.
- No loop (audit-only plan; no fixer role — findings are reported, not applied).
- No retries, no invalid returns, no worker_failed this run.

## Telemetry

```
agent                            entries  span_s  share
controller                            11     320    54%
finder-data-types                      3      85    14%
verifier-of-state-edge                 5      66    11%
finder-state-edge                      3      41     7%
finder-spec-line                       3      38     6%
verifier-of-spec-line                  3      24     4%
verifier-of-data-types                 2      24     4%

role                         agents entries max_span_s
controller                        1      11        320
finder-data-types                 1       3         85
verifier-of-state-edge            1       5         66
finder-state-edge                 1       3         41
finder-spec-line                  1       3         38
verifier-of-spec-line             1       3         24
verifier-of-data-types            1       2         24
```

`verifier-of-data-types` logged only 2 entries against a 3-minimum protocol
(start, verify, return) — under-logged relative to the audit protocol, though
its return was schema-valid and covered all 4 assigned candidates. No other
anomalies; no agent dominates disproportionately to its assignment size.
