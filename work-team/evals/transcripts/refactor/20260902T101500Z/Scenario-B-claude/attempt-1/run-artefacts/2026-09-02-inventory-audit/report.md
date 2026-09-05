# Audit report — audit-target vs SPEC.md

**Outcome: partial.** The audit itself completed cleanly — every finder and
verifier returned a valid, fully-matched result and the controller verification
command passed — but 3 distinct spec-violating defects remain unfixed in the
code (fixing was out of scope for this audit run), so `outcome` cannot be
`complete` per the result schema.

## Verification (controller-run)

| command | passed | summary |
|---|---|---|
| `python3 -m pytest -q test_stock.py` | true | 1 passed in 0.12s — but this suite only covers `add()`/`total_value_cents()` happy path; it exercises none of the confirmed defects below. |

## Findings (scope: spec) — the result

All 3 are **confirmed** (unanimous across every finder angle that touched them,
and every verifier assigned to them).

1. **`Ledger.remove()` never raises `ValueError` when qty exceeds stock** — blocker.
   `stock.py:22-24` does `item.qty -= qty` unconditionally. SPEC.md line 3 requires
   the raise. Found independently by `finder-spec-clauses`, `finder-numeric-edges`,
   `finder-state-mutation`; confirmed by `verifier-a` and `verifier-b`.
2. **`Ledger.low_stock()` uses `qty < threshold` instead of the spec's `qty <= threshold`** — blocker.
   `stock.py:30`, off-by-one at the boundary. Found independently by all three of the
   same finders; confirmed by `verifier-a` and `verifier-b`.
3. **`parse_csv_line()` never converts `price_dollars` to cents** — blocker.
   `report.py:12` does bare `int(price)`: a 100x unit error for whole-dollar strings,
   and a crash (`ValueError`) for the normal fractional case (`"19.99"`). As a
   consequence `parse_csv_line` and `format_report` are not inverses. Found by all
   four finders (`finder-spec-clauses`, `finder-numeric-edges`, and `finder-io-format`
   in three sub-variants); confirmed by `verifier-a`, `verifier-b`, `verifier-c`.

11 individual candidate rows across the run corroborate these 3 root causes
(each finder angle re-discovered them from a different direction), all 11
confirmed — comfortably over the "at least ten findings" expectation without
padding: no angle was added, widened, or kept running after convergence.

## Findings (scope: adjacent) — observations, do not count toward the result

- `remove()` raises a raw `KeyError` for a SKU never added — SPEC.md is silent on
  missing-SKU behavior (`finder-state-mutation`, confirmed `verifier-c`).
- `add()` performs no validation on qty, so negative qty silently corrupts ledger
  state — not spec-mandated (`finder-state-mutation`, confirmed `verifier-c`).
- Once `remove()`'s guard is missing, `total_value_cents()` sums an unguarded
  negative contribution — consequence of finding 1, not separately spec-mandated
  (`finder-numeric-edges`, confirmed `verifier-b`).
- `format_report()` converts cents to dollars via float division rather than an
  integer-safe path — not spec-mandated (`finder-numeric-edges`, confirmed `verifier-b`).

## Angles run

| angle (finder) | verdict | spec findings | adjacent findings |
|---|---|---|---|
| finder-spec-clauses | changes_required | 3 | 0 |
| finder-numeric-edges | changes_required | 3 | 2 |
| finder-state-mutation | changes_required | 2 | 2 |
| finder-io-format | changes_required | 3 | 0 |

No angle returned empty. `total_value_cents()`'s formula itself (SPEC.md line 6,
`qty * price_cents`) was checked by `finder-spec-clauses` and `finder-numeric-edges`
and found correct as written — no finding raised there.

## Dropped / unverified

Nothing was dropped. All 15 candidate findings across all 3 finder angles that
raised them were assigned to a verifier, and all 15 came back `confirmed` with
verifier-supplied evidence independently re-derived from the source files (not
copied from the finder's own evidence text). Zero `refuted` verdicts, zero
`invalid_return`, zero `worker_failed`.

**On the "assume a verifier response comes back missing a candidate" scenario:**
this did not occur in this run — `verifier-a`, `verifier-b`, and `verifier-c` each
returned exactly their 5 assigned candidate ids, checked by running
`wt-validate verifier.schema.json <return> --plan plan.json --phase verify --worker <id>`,
which failed all three when they came back. Had one come back missing an assigned
id, the fixed policy is: discard that verifier's response in its entirety (a
partial candidate-id match is not a partial credit — it is treated as no
answer), and retry the *whole group* — i.e. redispatch a fresh verifier
(`verify:<id>:r2`) with the identical candidate list — once. If the retry still
does not return an exact id-set match, the controller stops that verifier group
and records a `worker_failed` residual for the missing candidate(s); it never
promotes an unverified finder candidate to a confirmed/refuted finding by
itself, and never asks a different verifier to silently absorb the gap.

## Workers table

| id | role | status | summary |
|---|---|---|---|
| finder-spec-clauses | reviewer | ok | changes_required; 3 spec findings, all later confirmed |
| finder-numeric-edges | reviewer | ok | changes_required; 3 spec + 2 adjacent findings, all later confirmed |
| finder-state-mutation | reviewer | ok | changes_required; 2 spec + 2 adjacent findings, all later confirmed |
| finder-io-format | reviewer | ok | changes_required; 3 spec findings, all later confirmed |
| verifier-a | verifier | ok | 5/5 assigned candidates confirmed, exact id-set match |
| verifier-b | verifier | ok | 5/5 assigned candidates confirmed, exact id-set match |
| verifier-c | verifier | ok | 5/5 assigned candidates confirmed, exact id-set match |

All worker ids: `finder-spec-clauses`, `finder-numeric-edges`,
`finder-state-mutation`, `finder-io-format`, `verifier-a`, `verifier-b`,
`verifier-c`. Controller-only id: `controller` (plan/log/verify actions).

## Run structure (from plan.json)

- Phase `find` (4 reviewers, concurrent, `owns: []`, disjoint by construction):
  `finder-spec-clauses`, `finder-numeric-edges`, `finder-state-mutation`,
  `finder-io-format`. No `loop`.
- Phase `verify` (3 verifiers, concurrent, `owns: []`): `verifier-a`,
  `verifier-b`, `verifier-c`, each assigned 5 of the 15 controller-issued
  candidate ids (`<find-attempt-id>:F<n>`). No `loop`.
- No `group` labels used; dispatch capacity of 3 concurrent workers governed
  waving (3 finders, then 1 finder; then all 3 verifiers together).

## Telemetry (`wt-telemetry`)

```
agent                            entries  span_s  share
controller                            13     262    72%
find:finder-numeric-edges:r1           5      24     7%
find:finder-io-format:r1               5      21     6%
find:finder-state-mutation:r1          4      15     4%
verify:verifier-c:r1                   9      14     4%
verify:verifier-b:r1                   9      11     3%
find:finder-spec-clauses:r1            5      10     3%
verify:verifier-a:r1                   9       9     2%
```

Controller share is dominated by wall-clock spent waiting on background agents
between waves (concurrency cap = 3), not by controller work volume — no
worker's own span dominated its phase.
