I have the evidence pinned down. Findings:

## 1. What the pipeline missed, and the mechanism

**Missed:** SPEC.md §5 (animation table) and the theme itself. `css-inventory.txt:1-7` — 145 total CSS lines across 5 files, `theme.css` is 12 lines. `css-inventory.txt:9-11` — `SeasonPicker.tsx`, `ArchiveView.tsx`, `DueDateField.tsx` have **zero** `className` usage: season palette, archive view, and overdue badge render with no styling hook at all.

**Mechanism — two-part:**
- No verification step ever had an oracle for visual output. `result.json:1` verify block = `testsPass`/`buildPass` only. Tests assert the `data-anim`/`data-overdue` attribute exists (a functional hook), never that CSS/keyframes for it exist or that palette/colour actually renders — that's a `source-scan` gap, not covered by `unit-test`, `rendering-assertion`, or `rubric-judge`.
- The one worker that did catch it — `completeness-critic` — found 4 gaps (`workflow-log.jsonl:345`: board tag chips, anim CSS absent, dead code, overdue not styled). `final-fixer` was dispatched to close them but spent most of its session (10:44–10:56Z, ~12 min) fighting an unrelated fake-timer/RTL test hang, then in its last ~2.5 min closed only 2 of 4 (`workflow-log.jsonl:358`: "FR-8 board tag chips + FR-6/anim-table gaps closed"). The Orchestrator's own wrap-up (`workflow-log.jsonl:363`) records 3 items still open: **"bed-reorder anim, overdue CSS, renumber unused"** — contradicting final-fixer's claim to have closed the anim-table gap.

Root cause upstream, too: `workflow-log.jsonl:72` — plan review flagged an animation-ownership conflict (T16 lacked file access to own an anim row) during planning, and the Orchestrator explicitly **deferred** it to the phase-4 critic rather than fixing it in the plan — pushing a styling risk into the cheapest, least-scrutinized stage of the run.

## 2. Where wall-clock/cost concentrated

| Stage | Wall-clock | Cache tokens |
|---|---|---|
| Whole run | ~2h11m | 100.4M |
| Impl phase (`130028c4-9c4`) | ~1h45m (80% of run) | 80.7M (80%) |
| **final-fixer alone** | 2085s / 34.7min (single sequential agent, end of run) | **37.15M (37% of entire run)** |
| implementer-T9 (DnD) | 1116s | 12.6M |
| implementer-T16 (App/theme wiring) | 562s | 6.0M |

final-fixer, run in a subagent-code-review style 267-turn/158-tool-call session, is by far the single biggest cost/time sink — and per §1, most of that time went to an infra bug (fake timers), not the spec gaps it was actually tasked with closing.

## 3. Silently dropped / never surfaced

- `result.json:1` reports `"residual": null` — a bare claim nothing was dropped.
- But `workflow-log.jsonl:363`, written by the Orchestrator itself 1 line before the run ended, lists 3 open items: bed-reorder anim, overdue CSS, dead `renumber()` code.
- That's a direct contradiction between the Orchestrator's own log and its own reported result — the residual list existed and was discarded, not merely un-investigated.
- Also never surfaced: final-fixer's claim of closing the anim-table gap (`:358`) conflicts with the Orchestrator's residual line 5 seconds later (`:363`) still listing "bed-reorder anim" open — nobody reconciled the two.

## 4. Reshape for next run

1. Add a **rendering-assertion** phase for SPEC §5: a browser-level check (computed style / class presence / running animation) per animation row, plus reduced-motion path — not just the `data-anim` attribute.
2. Add a **rubric-judge** worker for overall theming (season palette applied, tag colours visible, overdue badge visually distinct) — a fresh worker scoring rendered output against §5, since no unit test can observe this.
3. Resolve plan-time conflicts (`:72`, anim-row ownership) in the plan phase — don't defer to a late critic.
4. Split final-fixer: one worker for infra/test-hang fixes, a separate one for critic-flagged spec gaps, each with its own verification command — so an unrelated blocker can't crowd out spec fixes.
5. `result.json.residual` must be populated programmatically from the Orchestrator's own log, not asserted — this run shows self-report and log can diverge.
