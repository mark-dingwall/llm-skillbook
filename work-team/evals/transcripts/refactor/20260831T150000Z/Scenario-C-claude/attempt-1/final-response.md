## Diagnosis: `refactor-20260831T150000Z-C` run

**Skill used:** work-team → `references/report.md` §"Diagnose a run" (task named an existing run + asked why it missed something/cost what it did — that path skips Frame/Plan/Dispatch and is controller-only analysis, no subagents needed).

### 1. What was missed, and the mechanism

**Missed:** SPEC §5 (theme/animation). Three components ship with **zero CSS classes** — `SeasonPicker.tsx`, `ArchiveView.tsx`, `DueDateField.tsx:0` className hits (`css-inventory.txt:9-11`); whole app has 145 CSS lines total (`css-inventory.txt:1-6`).

**Chain that let it through** (4 links, each cites the log):
1. Plan review flagged animation/CSS ownership as an unresolved **important** conflict (T16 vs T9/T11/T15) — Orchestrator explicitly *deferred it to the phase-4 critic* instead of assigning an owner (`workflow-log.jsonl:72-73`).
2. Per-task reviewers for those exact components checked only "tests green + scope matches plan" — never styling (`workflow-log.jsonl:249,252,281-282,287`).
3. Tests structurally can't catch it: FRs assert behavior/`data-anim` attributes, not `className`/CSS (`SPEC.md:181`) — so unstyled components pass all tests.
4. The only holistic CSS check was a **single one-shot** `completeness-critic` at the very end (`workflow-log.jsonl:344-345`), and even it missed the 3 zero-styling components — it only flagged missing keyframes/tag-chips/overdue-styling/dead code.

### 2. Where wall-clock and cost concentrated

- Total run: **7877s (2h11m)**, `09:07:22Z→11:18:39Z` (`workflow-log.jsonl:1,363`).
- Phase 4 (impl) alone: ~105 min = **80%** of total run.
- One agent, **final-fixer**: 2067s span = **26% of total wall-clock**, 267 turns / 158 tool calls, **37.15M cache-read tokens** (`agents.csv:78`) — almost as much cache-read volume alone as the other 40 phase-4 agents combined (~43.6M).
- Next-largest single worker, implementer-T9: 1116s / 12.6M tokens (`agents.csv:82`) — under half final-fixer's time, a third its cost.
- final-fixer's own "final verdict" was self-graded (`workflow-log.jsonl:358`); verifier-2 only reran test/tsc/build afterward — no independent re-review of the fixes.

### 3. Silently dropped / never surfaced

- `result.json:1` reports `"residual":null` — directly contradicts the Orchestrator's own log line: *"residual: bed-reorder anim, overdue CSS, renumber unused"* (`workflow-log.jsonl:363`). That's a reporting defect, not just an incomplete build.
- Even that residual list undercounts the real gap — it never mentions the 3 zero-styling components, because the critic that fed it never caught them either.
- No verification entry ever targeted SPEC §5 as a whole; "132 tests pass" was reported as the completeness signal despite no test asserting visual styling anywhere.

### 4. Reshape for next run

1. Add a dedicated verification worker for requirements no unit test can observe (styling/animation) — e.g. assert each component has a matching non-trivial CSS module — as its own phase-4 gate, not one end-of-pipeline critic.
2. Treat an "important" unresolved plan conflict (the anim/CSS ownership gap) as a re-plan trigger, not something to defer and hope a later critic catches.
3. Split final-fixer's dual mandate (make-green vs close-spec-gaps) into two bounded, separately-reviewed workers — no single unbounded 267-turn session, no self-graded verdict.
4. Re-run the completeness-critic (or new styling verifier) *after* final-fixer — a critic finding needs a closing verification, not a claim.
5. Derive `result.json.residual` mechanically from the log (any critic finding without a matching "closed+reverified" entry) instead of hand-authoring it — this run shows hand-authored residual silently drops findings.
