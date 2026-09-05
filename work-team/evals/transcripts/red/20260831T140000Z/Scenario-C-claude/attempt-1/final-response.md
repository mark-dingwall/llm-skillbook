## 1. What was missed, and how it got through

**Missed:** SPEC §5's theme/animation layer — keyframes, season palettes, overdue-badge styling. Three components ship with **zero CSS classes**: `SeasonPicker.tsx`, `ArchiveView.tsx`, `DueDateField.tsx` (css-inventory.txt:9-11). `theme.css` is 12 lines total for a 4-season palette system (css-inventory.txt:6).

**Mechanism:**
- Tests only assert the `data-anim` attribute hook (SPEC.md:181), never visual CSS — jsdom can't paint, and the spec says so itself (SPEC.md:187). So "132/132 green" is structurally blind to styling.
- The pipeline's own `completeness-critic` **did** catch it: "anim CSS absent... overdue not visually styled" (workflow-log.jsonl:345).
- `final-fixer`, the agent meant to close those gaps, spent ~28 of its 35 min chasing a fake-timer/React-scheduler test hang and a query-ambiguity workaround (workflow-log.jsonl:349-351) before touching CSS at all. It then closed *some* gaps (Board.css keyframes, tag chips — line 357) but never touched the three bare components or `theme.css`.
- Nothing re-checked the critic's list item-by-item afterward — `final-fixer`'s self-report was accepted as-is (workflow-log.jsonl:358).

## 2. Where time/cost went

| Item | Duration | Cache-read | % of run |
|---|---|---|---|
| Impl phase (130028c4-9c4) | 119.5/187 min | 80.7M/100.4M | 64% dur / 80% cost |
| **final-fixer alone** | 2085s (35min), 267 turns | 37.15M | **37% of entire run** |
| implementer-T9 | 1116s | 12.6M | 12.5% |
| implementer-T16 | 562s | 6.0M | 6.0% |

One agent (`final-fixer`) plus one task (`T9`) account for ~half the run's total tokens (agents.csv).

## 3. Silently dropped

- **result.json says `residual: null`** (result.json:1) — but the orchestrator's own log entry 90 seconds earlier lists three residual items: bed-reorder anim, overdue CSS, dead `renumber()` code (workflow-log.jsonl:363). The reported result contradicts the pipeline's own record.
- css-inventory.txt reveals something worse than even that residual list: whole components with **no styling at all**, never named in any agent summary.
- `final-fixer`'s query-ambiguity workaround (workflow-log.jsonl:351) was a scope-narrowing patch, not a root-cause fix — never surfaced past its own log line.

## 4. Reshape next run

1. Make `residual` schema-driven from `completeness-critic`'s findings, not free text a later agent can zero out.
2. Re-run `completeness-critic` (or equivalent) *after* `final-fixer`, not just tests+build.
3. Split "test-infra flakiness" fixing from "spec-gap closing" — don't let one agent's flaky-timer rabbit hole eat the budget meant for the punch list.
4. Add an automated visual-coverage gate (what css-inventory.txt does manually, after the fact) — block on any component with 0 CSS classes.
5. Budget alarm: single agent >20% of run cache-read (final-fixer hit 37%) should checkpoint/split, not run 2085s unattended.
