Outcome: partial — three important, confirmed SPEC findings remain open.

| Verification | Passed | Summary |
|---|---:|---|
| `cd audit-target && python3 -m pytest -q` | yes | 1 passed in 0.13s |
| Read-only counterexamples C1-C3 | no | negative removal, equality omitted, dollar conversion incorrect |

## Residuals

| ID | Detail | Source |
|---|---|---|
| C1 | Excessive removal does not raise `ValueError` | verifier-batch-a; verifier-batch-b |
| C2 | `low_stock` excludes `qty == threshold` | verifier-batch-a; verifier-batch-b |
| C3 | CSV `price_dollars` is not converted to cents | verifier-batch-a; verifier-batch-b |

## Workers

| ID | Role | Status | Summary |
|---|---|---|---|
| finder-contracts | reviewer | ok | C1-C2 |
| finder-csv | reviewer | ok | C3 |
| finder-state | reviewer | ok | C1-C2 |
| finder-boundaries | reviewer | ok | C1-C3 |
| finder-traceability | reviewer | ok | C1-C3 |
| verifier-batch-a | verifier | ok | confirmed C1-C3 |
| verifier-batch-b | verifier | ok | confirmed C1-C3 |

## Run structure

`finders`: parallel finder-contracts, finder-csv, finder-state, finder-boundaries, finder-traceability. `verification`: parallel fresh verifier-batch-a and verifier-batch-b; each assessed C1-C3.

## Telemetry

`wt-telemetry audit-target/workflow-log.jsonl` reported controller 3 entries / 298s; verifier-batch-b 5 / 57s; verifier-batch-a 4 / 48s; finder-state 4 / 38s; finder-boundaries 3 / 37s; finder-csv 3 / 35s; finder-traceability 3 / 28s; finder-contracts 3 / 20s.
