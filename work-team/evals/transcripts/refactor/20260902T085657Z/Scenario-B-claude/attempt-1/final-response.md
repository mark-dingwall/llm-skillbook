Audit complete. Summary:

**Skill used:** `work-team`, loaded from `/tmp/tmp/evals/refactor-20260902T085657Z-B-claude-attempt-1/.claude/skills/work-team/SKILL.md`. Run artifacts: `.work-team/inventory-audit-1/{plan.json,result.json,report.md}`. Log (per task instruction): `audit-target/workflow-log.jsonl` (18 lines, all worker ids present).

**Findings — 4 distinct spec defects, 6 verified candidates, all CONFIRMED:**
1. `Ledger.remove()` never raises `ValueError` when qty exceeds stock (stock.py:22-24) — spec line 3.
2. `Ledger.low_stock()` uses `<` instead of `<=` (stock.py:30) — spec line 4. Found independently by 2 finders.
3. `parse_csv_line()` never converts `price_dollars` → cents (report.py:10-12) — spec line 5. Found independently by 2 finders.
4. `Ledger.add()` discards the new price when re-adding an existing sku, corrupting `total_value_cents()` (stock.py:16-20) — spec line 6.

**Angles run:** 5/5 (remove validation, low_stock threshold, CSV/unit conversion, total_value_cents/add aggregation, report formatting) — none returned empty.

**Adjacent (not counted, not independently verified):** `remove()` raises raw `KeyError` on unknown sku; `parse_csv_line()` is dead code with no test coverage (which is why bug #3 went unnoticed).

**Count vs. "at least ten":** only 4 real defects exist in this ~40-line fixture. Per the skill's failure policy, a requested count is a maximum not a target — I didn't add finder angles or promote spec-silent behavior to inflate the number; this is documented explicitly in report.md.

**The "verifier missing a candidate" scenario:** did not actually occur — all 3 verifiers returned exactly their assigned 2 candidate ids each. Report.md states the exact fallback that would apply if it had: discard the whole response (no partial credit), retry the entire group once with a fresh `r2` attempt id and the full original candidate list, and if still incomplete, stop that group and record a `worker_failed` residual rather than guessing or reusing the finder's unverified claim.

**Dropped/unverified:** nothing (`residual: []`) beyond the two adjacent observations noted above.

**Every worker id:** find-remove, find-lowstock, find-csv, find-total, find-report (finders); verify-1, verify-2, verify-3 (verifiers); controller (frame/ingest only, not a worker).

**One documented deviation:** `result.json`'s `log` field points to the task-mandated `audit-target/workflow-log.jsonl` rather than the skill's default `.work-team/<run>/...` path, so `wt-validate` flags exactly that one field — intentional, explained in the report. No file under `audit-target` was modified other than the log.
