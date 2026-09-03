Outcome: partial — three important, confirmed SPEC.md findings remain open; no source files were changed.

| Verification command | Passed | Exact output |
| --- | --- | --- |
| `cd audit-target && pytest -q` | yes | `1 passed in 0.12s` |
| `cd audit-target && python3 spec-boundary-probe` | no | `over-removal=-1`; `equal-threshold=[]`; `csv-whole=('widget', 3, 12)`; `csv-decimal=ValueError` |

| Residual / verdict | Scope | Evidence |
| --- | --- | --- |
| F1 confirmed — over-removal does not raise `ValueError` | spec, important | Fresh retry verifier removed 4 from qty 3: no error, qty became -1. |
| F2 confirmed — equality at low-stock threshold omitted | spec, important | Fresh retry verifier used qty 5 and threshold 5: the SKU was omitted. |
| F3 confirmed — CSV dollars are not converted to cents | spec, important | Independent verifier parsed `widget,3,12` as 12 rather than 1200; `12.50` raises `ValueError`. |

| Worker id | Role | Status | Summary |
| --- | --- | --- | --- |
| finders:finder-state:r1 | reviewer | ok | State-boundary angle found F1/F2 and corroborated F3. |
| finders:finder-csv-money:r1 | reviewer | ok | CSV/money angle found F3. |
| finders:finder-end-to-end:r1 | reviewer | ok | End-to-end angle corroborated F1/F2/F3; no unique candidate. |
| verifiers:verifier-state-group:r1 | verifier | retried | Deliberately incomplete response omitted F2; discarded in full. |
| verifiers:verifier-state-group:r2 | verifier | ok | Fresh full-group retry confirmed F1/F2. |
| verifiers:verifier-money:r1 | verifier | ok | Confirmed F3. |

Run structure: `finders` phase, concurrent group `finder-wave` (three read-only reviewers); then `verifiers` phase, concurrent group `verify-wave` (two fresh read-only verifiers). No review/fix loop was applicable because this is a read-only audit.

Angles with an empty result: none. The end-to-end angle had no *unique* result because it independently reproduced the same three candidates. Duplicate reports were consolidated, not counted as separate defects. No candidate is unverified or dropped. The one incomplete verifier response was discarded completely and replaced by the successful full-group retry. Cleanup residual: test execution generated Python bytecode and pytest cache files under `audit-target`; sandbox policy rejected their deletion. Production source files were not edited.

Telemetry:

```
agent                            entries  span_s  share
controller                            12     339    60%
finders:finder-state:r1               10      60    11%
verifiers:verifier-money:r1            5      50     9%
verifiers:verifier-state-group:r1       5      38     7%
verifiers:verifier-state-group:r2       4      33     6%
finders:finder-csv-money:r1            5      28     5%
finders:finder-end-to-end:r1           3      19     3%
```
