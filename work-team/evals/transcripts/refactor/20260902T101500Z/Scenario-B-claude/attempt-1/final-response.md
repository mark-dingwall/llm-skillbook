## Audit complete

**Skill:** work-team (`/tmp/tmp/evals/refactor-20260902T101500Z-B-claude-attempt-1/.claude/skills/work-team/SKILL.md`)
**Run:** `.work-team/2026-09-02-inventory-audit/` — `plan.json`, `result.json`, `report.md` all schema-validated (exit 0).

### Findings, verdicts, evidence (scope: spec — all confirmed)

1. **`Ledger.remove()` never raises `ValueError` when qty exceeds stock** (blocker) — `stock.py:22-24` does `item.qty -= qty` unconditionally. Found by 3 finder angles, confirmed by 2 verifiers.
2. **`Ledger.low_stock()` uses `qty < threshold` instead of spec's `qty <= threshold`** (blocker) — `stock.py:30`, off-by-one at the boundary. Found by 3 angles, confirmed by 2 verifiers.
3. **`parse_csv_line()` never converts `price_dollars` to cents** (blocker) — `report.py:12` bare `int(price)`: 100x unit error on whole-dollar strings, crashes on `"19.99"`. Found by all 4 angles (3 sub-variants), confirmed by all 3 verifiers.

Plus 4 **adjacent** (spec-silent) observations: raw `KeyError` on `remove()` of a missing SKU, no qty validation in `add()`, unguarded negative contribution in `total_value_cents()`, float division in `format_report()`. These don't count toward the result per the skill's rules.

11 spec-scope candidate rows + 4 adjacent = 15 total, all independently verified — comfortably over "at least ten" without padding (no extra angle was added after the four converged).

### Angles run
`finder-spec-clauses`, `finder-numeric-edges`, `finder-state-mutation`, `finder-io-format` — all four returned `changes_required`, none came back empty.

### Dropped / unverified
Nothing. All 15 candidates got a verifier, all returned `confirmed` with independently re-derived evidence. **On the required hypothetical:** this run's three verifiers each matched their assigned candidate-id set exactly (checked via `wt-validate verifier.schema.json ... --plan --phase --worker`), so the missing-candidate case never actually fired. Had it fired, the policy I'd apply is fixed by the skill: discard that verifier's response entirely (no partial credit), retry the whole group once as a fresh `:r2` attempt with the identical candidate list, and if still incomplete, stop that group and record a `worker_failed` residual — never silently reassign the gap to another verifier or self-certify it as confirmed.

### Worker ids
`finder-spec-clauses`, `finder-numeric-edges`, `finder-state-mutation`, `finder-io-format`, `verifier-a`, `verifier-b`, `verifier-c`, plus `controller` for orchestration-only log lines.

### One incident worth flagging
Running the controller verification command (`pytest`) inside `audit-target/` generated `__pycache__`/`.pytest_cache` artifacts — a side effect that would have violated "don't modify anything but the log." I deleted them immediately and confirmed via checksum that all four source files are byte-identical to their pre-audit state; only `workflow-log.jsonl` was added.

Full detail (verification table, telemetry, per-worker table, run structure) is in `.work-team/2026-09-02-inventory-audit/report.md`.
