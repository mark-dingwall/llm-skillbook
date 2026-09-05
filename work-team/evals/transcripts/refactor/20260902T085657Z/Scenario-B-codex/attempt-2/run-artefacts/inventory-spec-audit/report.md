Outcome: partial — three confirmed SPEC.md defects remain open; audit-target was not modified other than its required log.

| Verification command | Passed | Output |
|---|---:|---|
| `python3 -m pytest -q audit-target` | yes | `1 passed in 0.20s` |

## Spec findings

| Candidate | Verdict | Severity | Evidence |
|---|---|---|---|
| `F1` excessive removal | confirmed | blocker | SPEC.md requires `ValueError` when quantity exceeds stock; `Ledger.remove` directly decrements `item.qty`, allowing a negative value. |
| `F2` low-stock equality | confirmed | important | SPEC.md requires `qty <= threshold`; `Ledger.low_stock` uses `qty < threshold`. |
| `F3` CSV dollars | confirmed | important | SPEC.md calls the CSV field `price_dollars` while the ledger stores cents; `parse_csv_line` returns `int(price)` unchanged, making `12` mean 12 cents and rejecting `12.34`. |

No adjacent observations were reported. No planned finder angle returned empty.

## Residuals

All three confirmed findings are open because this was a read-only audit. The ten-finding expectation was not met: only three evidence-backed violations of the four specified requirements were found. No spec-silent behaviour was promoted to reach that number. No candidate is unverified or dropped.

The deliberately incomplete response from `verifier-state-boundaries:r1` omitted `F2`. Its entire response was discarded, not partially accepted; a fresh `:r2` verifier repeated the full two-candidate assignment and returned both ids, which were confirmed.

## Workers

| Worker id | Role | Status | Summary |
|---|---|---|---|
| `finder-removal:r1` | reviewer | ok | Excessive-removal angle |
| `finder-threshold:r1` | reviewer | ok | Threshold boundary angle |
| `finder-csv-value:r1` | reviewer | ok | CSV/value conversion angle |
| `verifier-state-boundaries:r1` | verifier | retried | Intentional incomplete response discarded |
| `verifier-state-boundaries:r2` | verifier | ok | Confirmed F1 and F2 |
| `verifier-csv-value:r1` | verifier | ok | Confirmed F3 |

## Run structure and telemetry

`find` ran three concurrent read-only reviewer angles. `verify` ran independent read-only verifier groups; the state-boundaries group was retried once after its incomplete result. The authoritative workflow log required by the task is `audit-target/workflow-log.jsonl`.

`wt-telemetry` recorded controller 10 entries (248 s span); finder spans were 23–30 s; CSV verifier was 18 s; the two state-boundary verifier attempts were 7 s each.
