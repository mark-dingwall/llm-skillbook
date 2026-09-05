Outcome: partial — 3 confirmed `spec` findings remain open.

| Verification | Passed | Output |
| --- | --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider audit-target` | yes | `1 passed in 0.11s` |

## Residuals

| Candidate | Severity | Evidence-backed result |
| --- | --- | --- |
| `find:finder-state:r1:F1` | important | Confirmed by `verify:verifier-stock:r2`: removing 3 from stock of 2 returns normally and leaves `-1`, although SPEC.md requires `ValueError`. |
| `find:finder-state:r1:F2` | important | Confirmed by `verify:verifier-stock:r2`: a SKU at quantity 5 is absent from `low_stock(5)`, although SPEC.md requires `qty <= threshold`. |
| `find:finder-report:r1:F1` | important | Confirmed by `verify:verifier-csv:r1`: `12.34` raises `ValueError` and `12` stays 12 instead of 1200 cents. |

No candidates were refuted or left unverified. The finder corroborations for these three requirement/locus/root-cause combinations were consolidated rather than counted separately.

## Workers

| id | role | status | summary |
| --- | --- | --- | --- |
| `find:finder-state:r1` | reviewer | ok | state/mutation finder |
| `find:finder-report:r1` | reviewer | ok | report/API finder |
| `find:finder-contract:r1` | reviewer | ok | full-contract finder |
| `find:finder-adversarial:r1` | reviewer | ok | adversarial finder |
| `verify:verifier-stock:r1` | verifier | retried | raw response preserved; fault-injected partial copy was rejected and never accepted |
| `verify:verifier-stock:r2` | verifier | ok | fresh whole-group retry confirmed stock candidates |
| `verify:verifier-csv:r1` | verifier | ok | confirmed CSV candidate |

## Run structure

| phase | groups | workers | loop |
| --- | --- | --- | --- |
| `find` | `wave-1`, `wave-2` | finder-state, finder-report, finder-contract, finder-adversarial | none |
| `verify` | `verification-wave-1` | verifier-stock, verifier-csv | none |

Finder angles run: state/mutation; reporting/API; full explicit-contract trace; adversarial black-box boundary probes. Empty angles: none. The request's ten-finding quota was not padded: only three distinct stated-requirement/code-locus/root-cause defects survived consolidation and independent verification.

## Telemetry

```
agent                            entries  span_s  share
controller                            12     565    62%
find:finder-report:r1                  7      74     8%
find:finder-contract:r1                5      61     7%
find:finder-state:r1                   5      53     6%
find:finder-adversarial:r1             5      48     5%
verify:verifier-stock:r2               6      47     5%
verify:verifier-stock:r1               4      31     3%
verify:verifier-csv:r1                 4      25     3%

role                         agents entries max_span_s
controller                        1      12        565
find:finder-report                1       7         74
find:finder-contract              1       5         61
find:finder-state                 1       5         53
find:finder-adversarial           1       5         48
verify:verifier-stock             2      10         47
verify:verifier-csv               1       4         25
```
