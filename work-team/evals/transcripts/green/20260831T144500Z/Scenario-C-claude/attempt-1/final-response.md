## Diagnosis: Trellis run (`130028c4-9c4` phase-4 dominant)

**1. What was missed, and the mechanism**

- SPEC §5 (`SPEC.md:166-181`) requires 9 animations + full theme; only the `data-anim` attribute is testable in jsdom (no real paint) — but **nothing else in the pipeline verified visual CSS**. `result.json` verification block has exactly one entry (tests/tsc/build); no design/style check ever existed.
- `completeness-critic` (the only agent that ever looked at CSS/theme completeness) ran **once**, at 10:42:18Z, near the very end — found: FR-8 tag chips missing, anim CSS absent for 6/9 rows, `overdue not visually styled`, dead code.
- Root cause traces further back: at 09:24:42Z the plan-reviewer flagged `conflicts=changes_required` — "anim-row ownership T16 vs T9/T11/T15... unpinned" — and the Orchestrator logged `"accepted, deferred to phase-4 critic"` instead of fixing ownership. Nobody owned most of the animation/theme work.
- Per-task reviewers never checked styling either — e.g. `impl-reviewer-T14` (ArchiveView) explicitly waved it off: `"no anim row applies to ArchiveView"`. Confirmed via `css-inventory.txt:9-11`: **SeasonPicker.tsx, ArchiveView.tsx, DueDateField.tsx have zero `className` usage** — not "undertheme," literally unstyled. `theme.css` is 12 lines (`css-inventory.txt:6`) — can't hold a 4-season palette.

**2. Time/cost concentration**

| Item | Value | % |
|---|---|---|
| Total run wall-clock | ~7,738s (2h9m) | — |
| Phase-4 (impl) wall-clock | ~6,317s | 82% of run |
| `final-fixer` alone | 2,085s / 267 turns / 158 tools | 33% of phase-4, 27% of run |
| `final-fixer` cache-read tokens | 37.15M | 37% of all 100 agents' cache-read (100.4M) |
| `implementer-T9` | 1,116s | fighting a pre-existing test-file bug not in its own scope |

One mega-agent (`final-fixer`) absorbed a third of the whole run's wall-clock and cost, self-grading its own fix.

**3. Silently dropped / never surfaced**

- `final-fixer`'s own final verdict (11:17:03Z) claims `"FR-6/anim-table gaps closed"` — but the Orchestrator's next log line (11:18:39Z) contradicts it: `residual: bed-reorder anim, overdue CSS, renumber unused`. Nobody reconciled this.
- `verifier-2` (11:17:24–11:17:45Z) only re-ran test/tsc/build — never re-ran the completeness-critic against the fixes.
- `result.json:1` reports `"residual": null` — none of the above 3 known-open items made it in. That's a direct reporting defect (skill's diagnose-step 2).
- The zero-`className` components were never caught by the critic at all — only visible via the independent `css-inventory.txt` audit, done outside the pipeline.

**4. Reshape next run**

1. Add a scripted CSS-completeness verification worker (cheap: `grep -c className` per component > 0, animation-name-in-css checks) — same commands as `css-inventory.txt` — as a real `verify` entry, not a one-off critic prose pass.
2. Never let a plan-review `changes_required` be silently "accepted, deferred" — resolve ownership at plan time or turn it into an explicit `residual` with an owner.
3. Split `completeness-critic → final-fixer` into: critic finds gaps → each gap becomes its own scoped fixer task with an independent reviewer (no self-grading) → re-run critic once (bounded loop) before declaring done.
4. `result.json` must be mechanically derived from the log's residual list, not hand-summarized — the Orchestrator already had the correct residual list in its own log and dropped it anyway.
