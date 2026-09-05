`audit-target` now contains only the original files plus `workflow-log.jsonl`. The audit is complete.

## Summary

**Outcome: partial** — audit ran to completion; 3 confirmed spec-scope blockers remain open (no fix phase was in scope for a read-only audit).

### Findings (scope: spec — count toward the task, all `confirmed` by an independent verifier)
1. **[blocker]** `Ledger.remove()` (`inventory/stock.py:22-24`) never raises `ValueError` when qty exceeds stock — subtracts unconditionally.
2. **[blocker]** `Ledger.low_stock()` (`inventory/stock.py:30`) uses `qty < threshold` instead of spec's `qty <= threshold`.
3. **[blocker]** `parse_csv_line` (`inventory/report.py:10-12`) never converts `price_dollars` to cents — bare `int(price)`.

### Findings (scope: adjacent — observations, not counted)
6 confirmed: missing test coverage for `remove()`, `low_stock()`, and `parse_csv_line`; `add()` silently discards price on a repeat add for an existing sku; `remove()` raises `KeyError` not `ValueError` for unknown skus; weak existing test (single sku, no differing-price case).

### Angles run
4 finders, each mapped 1:1 to a SPEC.md bullet — none returned empty except `finder-total` (total_value_cents formula is correct; only adjacent findings). No angle was added or widened to chase the "at least ten" language — that count is a cap, not a target, per the skill's failure policy, and the 9 real, non-duplicative findings were kept as-is.

### Dropped/unverified
Nothing — all 9 candidates were assigned to a verifier and came back `confirmed`.

### Fault-injection drill
`verifier-stock`'s first return was complete and valid (saved raw). Its last candidate was stripped via `inject-partial-verifier.py`, and the partial copy — never the complete one — was submitted to the contextual gate (`wt-validate ... --plan --phase --worker`), which correctly rejected it (id-set mismatch). Per the real incomplete-return policy, the attempt was discarded entirely and the **whole group** was retried with fresh workers (`verifier-stock:r2`, `verifier-csv:r2`), even though `verifier-csv:r1` had itself been valid. The partial copy was never accepted or reused.

### Worker ids (all in `workflow-log.jsonl`, both at `.work-team/2026-09-03-inventory-audit/` and the required `audit-target/workflow-log.jsonl`)
`controller`, `find:finder-remove:r1`, `find:finder-lowstock:r1`, `find:finder-csv:r1`, `find:finder-total:r1`, `verify:verifier-stock:r1`, `verify:verifier-stock:r2`, `verify:verifier-csv:r1`, `verify:verifier-csv:r2`.

Full detail in `.work-team/2026-09-03-inventory-audit/report.md` and `result.json`.
