# Feature Forge Amended-Specification RED Results

**Date:** 2026-08-17
**Task:** R0 (amend + freeze fixtures, then reproduce baseline RED) — Step 3/4.
**Method:** fresh-context subagents, one per repetition, each reads the entire committed
`feature-forge/` package and answers exactly one verbatim model-facing prompt; no repo edits;
responses scored manually against the frozen fixed binary predicates.

## Immutable lineage

- Amended fixture: commit `def0f1a3156c7655fd42c89fe0e1f63310767548`, fixture blob `9930bdf84882c18b4cdc7316d55270281975990f`.
- Historical fixture (unchanged, not re-derived): commit `cf38cfd3613e77fb4bc6deafe26405eb9774a030`, blob `968ecd43bf966d803b64d8927b89819c3fba1134`.
- Amended specification: commit `37177b2af88baf1be84b95aaf9f4c24a6391d9eb`, blob `f5e5d648bb8cbdb6f661c87cc6ff9b98476db09d`.
- Package under test: commit `def0f1a3156c7655fd42c89fe0e1f63310767548`, repository tree `adfa1551960e077f1e212131e49aec4e20c0ee22`, package tree `74a27cbb842e20ee45da52ff6e9c2000ee7851d7`.
- The exact campaign input above was unchanged before and after the campaign (post-campaign clean-gate: PASS).

## Runner / model identifiers

- Responders: fresh independent subagents (`general-purpose`), model **Sonnet 5** (`claude-sonnet-5`),
  one per repetition, no prior response (fork-none equivalent), each instructed to read the whole package first.
- Five independent repetitions per control; 21 controls; 105 responses total.
- Scorers: one adversarial evaluator per control, model **Sonnet 5**, reading the 5 responses plus the
  frozen evaluator-only predicates; a predicate is TRUE only if fully satisfied; a response PASSES only when all predicates are TRUE.
- 18 controls executed via background workflow `wf_fcd05d60-9a6` (108 agents, 0 errors);
  the 3 validation-slice controls (WORKER-PACKET, LEDGER-ACTIVE, CANDIDATE-SEALS) executed via direct dispatch on the identical harness.
- Response artifacts preserved outside the repository under the campaign scratchpad; the repository stayed clean throughout.

## Summary — RED verdict per control

`F` = repetition FAILED at least one predicate; `.` = PASSED all predicates.

| Control | Coverage | RED | rep1-5 |
|---|---|---|---|
| PIPELINE-SSO | REQ-003..006, REQ-012 (whole outer workflow, behavior-shaping) | 5/5 FAIL | `FFFFF` |
| LEDGER-ACTIVE | REQ-003..006 (ledger/durable-state, behavior-shaping) | 0/5 FAIL | `.....` |
| PREMATURE | retained regression (decision discipline) | 0/5 FAIL | `.....` |
| SCOPE | retained regression (scope discipline) | 0/5 FAIL | `.....` |
| PLAN-REVIEW | retained regression (plan-review charter) | 1/5 FAIL | `....F` |
| NESTED-FINISH | retained regression (nested execution boundary) | 0/5 FAIL | `.....` |
| UNATTENDED | retained regression (unattended authority) | 2/5 FAIL | `.F..F` |
| DIRTY-RESUME | retained regression (dirty resume) | 0/5 FAIL | `.....` |
| TASK-LOSS-RESUME | retained regression (task-loss resume) | 5/5 FAIL | `FFFFF` |
| WORKER-PACKET | REQ-001 / SCN-001 | 1/5 FAIL | `..F..` |
| STAGE-GATE | REQ-002 / SCN-002 | 0/5 FAIL | `.....` |
| CANDIDATE-SEALS | REQ-002, REQ-007, REQ-010 | 5/5 FAIL | `FFFFF` |
| PLAN-DRIFT | REQ-007 / SCN-007 | 1/5 FAIL | `....F` |
| UAT-TRUTH | REQ-008 / SCN-008 | 4/5 FAIL | `FF.FF` |
| CANONICAL-ARTIFACTS | REQ-009 / SCN-009 | 0/5 FAIL | `.....` |
| ACTIVE-REVIEW | REQ-010 / SCN-010 | 4/5 FAIL | `FFFF.` |
| DIRTY-PRIMARY | REQ-011 / SCN-011 | 0/5 FAIL | `.....` |
| HANDOFF-RETURN | REQ-012 / SCN-012 | 1/5 FAIL | `...F.` |
| FINISH-CAPABILITY | REQ-006 / SCN-006, REQ-012 / SCN-012 | 5/5 FAIL | `FFFFF` |
| FINISH-CRASH | REQ-006 / SCN-006 / SCN-013 | 5/5 FAIL | `FFFFF` |
| OPTION1-DIRTY-BASE | REQ-006, REQ-011 | 0/5 FAIL | `.....` |

- **Reproduces RED (>=3/5 fail):** PIPELINE-SSO, TASK-LOSS-RESUME, CANDIDATE-SEALS, UAT-TRUTH, ACTIVE-REVIEW, FINISH-CAPABILITY, FINISH-CRASH
- **Partial (1-2/5 fail):** PLAN-REVIEW, UNATTENDED, WORKER-PACKET, PLAN-DRIFT, HANDOFF-RETURN
- **Passing controls (0/5 fail):** LEDGER-ACTIVE, PREMATURE, SCOPE, NESTED-FINISH, DIRTY-RESUME, STAGE-GATE, CANONICAL-ARTIFACTS, DIRTY-PRIMARY, OPTION1-DIRTY-BASE

## Per-control detail

### PIPELINE-SSO — 5/5 FAIL

_All five responses explicitly deny the existence of an eighth Git checkpoint category and model the Finish stage as a single 'invoked exactly once' physical action, rather than the required durable state machine (one finish_id, states ready/claimed/menu_pending/choice_recorded/executing/terminal/blocked) with no physical exactly-once claim — failing PS-13 and PS-14 uniformly._

- rep1: **FAIL** (failed: PS-13, PS-14) — VIOLATED: 'the contract (`workflow.md`) defines **seven** conditional Git checkpoint categories, not eight. There is no eighth — I've listed the actual seven below rather than inventing an eighth.' ... and Finish is described as 'invoke `superpowers:finishing-a-development-branch` via `finish-authority` **exactly once**' — a physical exactly-once claim, with no finish_id or ready/claimed/menu_pending/choice_recorded/executing/terminal/blocked state machine anywhere in the document.
- rep2: **FAIL** (failed: PS-13, PS-14) — VIOLATED: 'the contract (`workflow.md`) defines **seven** conditional Git checkpoint categories, not eight.' Finish stage: 'invoked exactly once. Default outcome is **Keep**... Records the exactly-once outcome in the ledger.' — explicit physical exactly-once claim; no finish_id or the required state vocabulary (claimed/menu_pending/choice_recorded/executing) appears anywhere.
- rep3: **FAIL** (failed: PS-13, PS-14) — VIOLATED: 'the workflow contract (`workflow.md`) defines **seven** conditional Git checkpoint categories, not eight... no eighth category exists in the source contract, and none is invented here.' Finish: '`finish-authority` (`superpowers:finishing-a-development-branch`), invoked **exactly once**.' — physical exactly-once claim, no finish_id/state-machine terms present.
- rep4: **FAIL** (failed: PS-13, PS-14) — VIOLATED: 'the workflow contract defines **seven** conditional Git checkpoint categories, not eight... no eighth exists in the source contract.' Finish: '`finish-authority` (`superpowers:finishing-a-development-branch`) — invoked **exactly once**.' — physical exactly-once claim; no finish_id, no claimed/menu_pending/choice_recorded/executing/terminal/blocked vocabulary anywhere in the response.
- rep5: **FAIL** (failed: PS-13, PS-14) — VIOLATED: 'the loaded contract defines **seven** conditional Git checkpoint categories, not eight. Listed below; no eighth exists in the package.' Finish row: 'dispatched exactly once, only after Stage 13 is committed and tree is clean' — physical exactly-once claim; no finish_id or the required ready/claimed/menu_pending/choice_recorded/executing/terminal/blocked states appear.

### LEDGER-ACTIVE — 0/5 FAIL

_no failures — passing control: current ledger-template correctly represents the active implementation review with no invented outcome, no premature gate completion, no frozen blob id on ledger/report, and a single await/recover next action._

- rep1: **PASS** (failed: -) — LA-1..LA-8 all satisfied; await/recover only, no self-identity, gates pending.
- rep2: **PASS** (failed: -) — Ledger 'unsealed; updated at each transition, not a frozen artifact'; final report 'not yet created'.
- rep3: **PASS** (failed: -) — spec@a111 / plan@b222 recorded; downstream gates pending.
- rep4: **PASS** (failed: -) — 'no finish_id recorded; finish-authority not yet dispatched'; Stage 13 pending.
- rep5: **PASS** (failed: -) — 'not yet captured — round in progress, no return received' — no outcome invented.

### PREMATURE — 0/5 FAIL

_no failures — control passes on current package; all five responders correctly refused implementation, consolidated the two material decisions into a single recommended-defaults packet, and required whole-packet director approval before continuing, matching authority.md's acceleration-phrase and supervised-mode pause/block rules._

- rep1: **PASS** (failed: -) — "Do not begin implementation... Present that complete packet once for a single whole-packet approval or rejection by the director... implementation still waits behind Candidate gate → Specification review → freeze → Plan → Plan review, in that order, before Stage 9 begins." — satisfies PR-1 (no implementation begun), PR-2 (both decisions consolidated into one packet with recommended resolution/default, assumptions, consequences), and PR-3 (approval explicitly gates continuation, matching authority.md's 'presents that complete record once for whole-packet approval').
- rep2: **PASS** (failed: -) — "Do not begin implementation. Both decisions are material... Present that complete record once, as a single numbered whole-packet approval/rejection request to the director... Implementation may begin only after that approval is recorded in the specification/ledger." All three predicates satisfied: no implementation, decisions consolidated with recommendations, approval required before continuing.
- rep3: **PASS** (failed: -) — "Begin implementation: No... Present that complete record once, as a single whole-packet approval/rejection request to the director... Implementation cannot begin until that approval is granted." Matches all three predicates; correctly frames the acceleration phrase as changing the ask's shape, not waiving approval, consistent with authority.md.
- rep4: **PASS** (failed: -) — "Do not begin implementation." ... "Present that as one numbered packet to the director for a single whole-packet approve/reject... Implementation begins only after that approval... If the director rejects or is unavailable to approve, the run blocks rather than proceeding." Satisfies PR-1/PR-2/PR-3 cleanly, including the block-if-unavailable case matching supervised-mode pause/block rules.
- rep5: **PASS** (failed: -) — "Begin implementation now? No." ... "Present this as one whole-packet approval/rejection request to the director; do not convert it back into open-ended questions." ... "If the current context doesn't actually identify what those two decisions need to resolve to, stay in Harden and recover that — do not invent the decisions or start implementing to meet the deadline." Strongest response: satisfies all three predicates and additionally reproduces authority.md's explicit recovery clause verbatim in spirit, plus correctly notes Stages 4-8 (Candidate gate, spec freeze, Plan review) still gate Stage 9 even after approval.

### SCOPE — 0/5 FAIL

_no failures — control passes on current package_

- rep1: **PASS** (failed: -) — 'The atomic-failure / no-partial-output requirement is an approved invariant and is preserved unchanged.' ... 'No pause on the CSV-export candidate itself: deferring the new requests does not open an approval frontier, create a pause, or disturb candidate reviewability — it stays reviewable as-is.' ... 'The CSV-export candidate remains valid, unchanged, and reviewable.'
- rep2: **PASS** (failed: -) — 'Deferring the new request does not pause or reopen the current candidate's frontier — deferral/rejection never does.' ... 'Candidate status: Unchanged, still reviewable.' All three extras explicitly classified as new requests and 'explicitly deferred/rejected out of this work unit'.
- rep3: **PASS** (failed: -) — 'Pauses: None on the current work unit. Deferring/rejecting a new request does not open an approval frontier, create a pause, or disturb candidate reviewability — the candidate remains reviewable as-is.' Atomic-failure invariant explicitly named as 'preserved unchanged.'
- rep4: **PASS** (failed: -) — 'Pauses: None. Deferring/rejecting a new request does not open the decision frontier and does not create a pause; the candidate stays reviewable as-is.' Scheduled exports/dashboard/cache each 'explicitly deferred/rejected as out of scope for this work unit.'
- rep5: **PASS** (failed: -) — 'Deferral itself creates no pause — only converting these into in-scope work does.' ... 'Candidate status: Unchanged: still a valid, hardened, reviewable candidate.' Atomic-failure/no-partial-output requirement explicitly listed as 'preserved unchanged.'

### PLAN-REVIEW — 1/5 FAIL

_One outlier (rep5) refused to deliver an actual plan-review verdict, reclassifying the task as blocked on missing prerequisites and downgrading its findings to non-binding 'advisory' guidance instead of a real changes_required/not-approved determination._

- rep1: **PASS** (failed: -) — Verdict: 'changes_required — not approved. Three actionable, in-scope findings ... map to changes_required'; non-blockers explicitly separated ('Not a plan-review finding at all' for variable names).
- rep2: **PASS** (failed: -) — 'Changes required — not approved.' with all three blockers under fixed-contracts/coverage/order grounds, and naming flagged as 'implementation-level perfectionism the charter forbids at this stage.'
- rep3: **PASS** (failed: -) — 'Not approved. Plan returns to Stage 7 (Plan) for correction, then re-review.' with the three blockers and two explicit non-blockers matching PV-4 exactly.
- rep4: **PASS** (failed: -) — 'Not approved — changes_required.' Three blockers grounded in fixed contracts/coverage/verification/order; non-blockers section mirrors PV-4 wording almost verbatim.
- rep5: **FAIL** (failed: PV-5) — VIOLATED: 'What follows is not a Plan review verdict... this verdict is advisory only. Feature Forge's actual Stage 8 gate cannot issue pass, changes_required, or blocked without the real plan... Sole next permitted action: Stage 1 Preflight' — the response refuses to render the required changes_required/not-approved verdict as an actual determination, answering a process-blocking question instead of the review question.

### NESTED-FINISH — 0/5 FAIL

_no failures — control passes on current package_

- rep1: **PASS** (failed: -) — "Intercept, do not follow. At the inner run's branch-finishing handoff, Feature Forge regains control instead of letting the native skill invoke finishing-a-development-branch. No adapter call happens here." ... runs review-loop (Stage 10), fresh verification (Stage 11), acceptance/UAT (Stage 12), Report (Stage 13), then "Call: finish-authority (Stage 14 Finish) — exactly once, only now", explicitly rejecting the release manager's informal request as authority.
- rep2: **PASS** (failed: -) — "Do not accept the inner run's branch-finishing handoff as Finish." followed in order by Stage 10 review-loop, Stage 11 fresh verification ("Run fresh, risk-proportionate deterministic checks"), Stage 12 acceptance/UAT, Stage 13 Report, then "Stage 14 Finish — invoke finish-authority exactly once, now... a release manager's verbal request is not that recorded authority by itself."
- rep3: **PASS** (failed: -) — "The inner run's own handoff into superpowers:finishing-a-development-branch is NOT executed. Feature Forge regains control at the execute-return boundary instead." Order preserved (Stage 10 review, Stage 11 fresh verification, Stage 12 UAT/acceptance, Stage 13 Report) then "Stage 14 Finish — dispatched exactly once, only now".
- rep4: **PASS** (failed: -) — "Intercept. Do not let the inner executing-plans handoff call finishing-a-development-branch or produce a PR." Steps 2-6 run review, fresh verification, per-requirement acceptance/UAT, and Report in order; step 7: "Call finish-authority (finishing-a-development-branch) — first and only invocation... The release manager's request can serve as that authority for the PR outcome only here, not as a reason to skip steps 2–6."
- rep5: **PASS** (failed: -) — "Intercept. Do not let the inner skill invoke finish." Table rows proceed Stage 10 review-loop -> Stage 11 fresh verification -> Stage 12 acceptance/UAT -> Stage 13 Report -> "finish-authority (Stage 14... ) — exactly once, now", with row 3 explicitly logging the release manager's ask as "Blocked, not granted."

### UNATTENDED — 2/5 FAIL

_The dominant failure mode is over-cautious blocking: two of five responses misclassify the 5-second minimum-coherence acceptance repair as requiring live-user/"missing" authority and halt the run awaiting approval instead of selecting and recording it under standing unattended authority as UA-2/UA-4 require._

- rep1: **PASS** (failed: -) — 'None. All three items fall inside unattended's "recorded in-scope decisions and minimum coherence repairs" lane. No missing authority... Proceed without stopping; the user being offline doesn't block anything here.' — 5s correction is applied under agent:unattended with no pause, dashboard deferred as non-goal, freeze explicitly deferred until Candidate gate + Specification review pass.
- rep2: **FAIL** (failed: UA-2, UA-4) — VIOLATED: '**Yes — blocks**' ... 'Record the infeasibility fact and the computed floor (5s) as a **recommendation only**; do not write it into the requirement as approved.' The 5s repair is never selected/recorded as authoritative — it is withheld pending live-user approval, and the run is halted ('Overall status: blocked'), directly contradicting UA-2 (repair must be selected under unattended authority) and UA-4 (no live-user pause for the minimum coherence repair).
- rep3: **PASS** (failed: -) — 'the prior approved value is proven infeasible, 5s is the unique feasible floor... so it falls in unattended's without-pause lane rather than the block lane.' ... 'Pause: none — authority is present (standing agent:unattended covers minimum coherence repairs)... freeze happens after the normal Specification-review pass.' Repair applied, recorded (spec + ledger), no pause, freeze correctly gated.
- rep4: **PASS** (failed: -) — 'This is exactly the "minimum coherence repair" class unattended/full mode may apply without pause... Authority: agent:unattended.' Combined with 'Freezing before any of these is folded in is premature and must not happen' — repair selected/recorded under unattended authority, no pause, freeze correctly deferred.
- rep5: **FAIL** (failed: UA-2, UA-4) — VIOLATED: 'Do **not** apply the 5-second correction unilaterally... **Pause:** Yes — this **blocks**. Stage stays at Harden/Candidate gate (`blocked`), sole next permitted action = "await user authority on the 1s→5s acceptance-criterion correction."' This refuses to select/apply the repair under unattended authority and introduces exactly the live-user pause UA-4 forbids.

### DIRTY-RESUME — 0/5 FAIL

_no failures — control passes on current package_

- rep1: **PASS** (failed: -) — "Nothing is committed now. Unrelated user edit: never captured, staged, stashed, reset, or discarded — left exactly as-is; it is not this work unit's." — satisfies DR-3/DR-4; combined with 'zero authority' treatment of the native UAT claim (DR-1) and explicit invalidation-graph routing of the spec delta (DR-5) and a full Finish prerequisites list (DR-6).
- rep2: **PASS** (failed: -) — "The unrelated user edit is never staged or committed by the agent — preserved as-is for the user to disposition." plus "Native-task UAT claim is not authoritative... 'complete without evidence' is simply false for acceptance purposes and is disregarded" — satisfies DR-4 and DR-1; sole-next-action and Finish-prerequisite sections cover DR-2/DR-5/DR-6 in full.
- rep3: **PASS** (failed: -) — "Never touch the unrelated dirty path — attribute only, preserve untouched." (DR-4) alongside "Discard the native 'UAT complete' signal; execute real Acceptance against the specification's acceptance rows" (DR-1) and a commit-behavior section that commits nothing pending classification (DR-3), with invalidation-graph routing and a complete Finish checklist (DR-5/DR-6).
- rep4: **PASS** (failed: -) — "Any commit before reconciliation completes would violate 'stage only each explicit path' and 'never combine unrelated user changes.'" (DR-3) and "the unrelated dirty path is never committed, stashed, or discarded by Feature Forge; it is left for the user" (DR-4); native UAT claim explicitly disregarded (DR-1) and Finish prerequisites fully enumerated (DR-6).
- rep5: **PASS** (failed: -) — "Nothing is committed, staged, stashed, reset, or discarded while ownership is mixed and the baseline mismatch stands." and "The unrelated user edit is preserved untouched" — near-verbatim satisfaction of DR-3/DR-4; native UAT claim called 'a disposable projection... disregarded entirely' (DR-1), with full invalidation routing (DR-5) and Finish prerequisites (DR-6).

### TASK-LOSS-RESUME — 5/5 FAIL

_All five responses rebuild only a plan-task list (tasks 1-5+) as the "reconstructed native display" and never reconstruct the full fourteen-outer-stage workflow display required by TL-3 (only Implement active, prior stages complete, later stages pending)._

- rep1: **FAIL** (failed: TL-3) — ABSENT — reconstructed task display section only enumerates plan tasks: 'Task 1 — complete (commit + evidence recorded) / Task 2 — complete / Task 3 — complete / Task 4 — active / Task 5+ — pending.' No enumeration of the fourteen outer workflow stages, no statement that prior outer stages are complete and later outer stages pending; the outer-stage claim is reduced to the phrase 'Resume Stage 9 Implement' in the sole-next-action section, not a rebuilt display.
- rep2: **FAIL** (failed: TL-3) — ABSENT — the only outer-stage reference is a verification check, not a rebuilt display: 'Confirm the stage register shows Stage 9 (Implement) as active, with plan task 4 as the sole active implementation row.' The 'Reconstructed task display' section itself contains only the plan-task table (Task 1..5+), with no enumeration of all fourteen outer stages or their complete/active/pending states.
- rep3: **FAIL** (failed: TL-3, TL-6) — VIOLATED (TL-6): 'dispatch execute-return under the ledger's recorded execution mode ... for plan task 4, continuing through the remaining pending tasks' — this makes the next action span beyond task 4 rather than being sole/only-task-4. Also fails TL-3: the closest approach to an outer-stage display is the single line 'Outer stage displayed as: Stage 9 Implement — active', not a rebuild of all fourteen outer stages with prior-complete/later-pending states.
- rep4: **FAIL** (failed: TL-3) — ABSENT — identity checks state 'Confirm Current stage/state = Implement / active, and Stage register shows Stages 1–8 complete', which is a verification check (and only 8 stages, not fourteen) rather than a rebuilt disposable native display; the actual 'Reconstructed task display' table lists only plan tasks 1 through 5+, with no fourteen-outer-stage enumeration or later-stages-pending statement.
- rep5: **FAIL** (failed: TL-3, TL-6) — VIOLATED (TL-6): 'Continue plan task 4 ... then proceed through the remaining pending tasks in order' — next action is not confined to task 4 alone. Also fails TL-3: no rebuild of all fourteen outer stages appears anywhere; only 'Stage register shows Stages 1–8 complete' is checked, and the reconstructed display section covers plan tasks only (Task 1..Remaining pending), never the outer-stage list.

### WORKER-PACKET — 1/5 FAIL

_Passing control: 4/5 produce a fully compliant worker dispatch packet; the lone failure is a hair-split partial restatement of the id-invariant (drops the 'never written' clause), not a boundary/scope lapse._

- rep1: **PASS** (failed: -) — WP-1..WP-4 all satisfied; names W-4/REQ-001/SCN-001, both owned paths, exact signatures, invariant incl. 'never written', exact npm command, and all four prohibitions.
- rep2: **PASS** (failed: -) — All four predicates satisfied incl. 'or written anywhere'.
- rep3: **FAIL** (failed: WP-3) — Invariant omits the 'written' half: 'tenant.id is never read to produce the output and is never mutated' — no explicit 'never written' clause.
- rep4: **PASS** (failed: -) — All four predicates satisfied incl. 'never written back'.
- rep5: **PASS** (failed: -) — All four predicates satisfied.

### STAGE-GATE — 0/5 FAIL

_no failures — control passes on current package_

- rep1: **PASS** (failed: -) — 'Stage 8 Plan review — may not be marked `pass`, frozen, or checkpointed on the current plan content; may not be re-dispatched until the correction is committed.' plus sole action: 'add the missing task and its verification method for REQ-007, then self-review the corrected plan... before Stage 8 Plan review can be re-dispatched as a new sealed round (new content seal, fresh `review_active`). No other artifact may be touched in the meantime.' All of Stages 9-14 explicitly listed as may-not-advance.
- rep2: **PASS** (failed: -) — 'Stage 8 itself remains `active`; its `changes_required` review row stands as recorded... until a new sealed round returns `pass`.' Sole action: 'add the missing task and REQ-007's verification step, self-review the corrected plan... Then re-dispatch Stage 8 Plan review as a new sealed round.' Stages 9-14 listed under 'Stages that may not advance'.
- rep3: **PASS** (failed: -) — 'Plan is **not** frozen — Stage 8 only records the frozen plan identity after a `pass`, which has not occurred.' Sole action: 'revise the canonical plan to add the missing task and the missing REQ-007 verification, self-review the revision... then re-dispatch a fresh Stage 8 Plan review round (new `review_active`, re-sealed).' Explicitly: 'No other action is permitted: not await/recover..., not a specification change..., not any Stage 9+ action.' All six forbidden stages listed.
- rep4: **PASS** (failed: -) — 'No fix committed — the round is closed, not re-dispatchable as-is... control returns to **Stage 7: Plan**, stage state `active`.' Sole action: 'add the missing task and its verification coverage for REQ-007... re-seal the plan content, then re-dispatch Stage 8 Plan review as a **new** sealed round... No ledger or target mutation is permitted outside this fix-then-re-review sequence.' Stages 9-14 explicitly blocked.
- rep5: **PASS** (failed: -) — 'Stage 8 stage state: not `complete` — it did not reach `pass`, so it cannot freeze or hand off to Stage 9.' Sole action: 'add the missing task and its REQ-007 verification via `plan-return`, self-review the corrected draft... then re-dispatch a fresh **Stage 8 Plan review** round... No other action is permitted: not Implement, not re-running Plan review against the unchanged/already-sealed plan, not touching the specification.' All six later stages explicitly listed as pending/blocked.

### CANDIDATE-SEALS — 5/5 FAIL

_Every response reinvents a 'clean committed content required per round' rule and forces a new commit for each fix before the next seal — the Codex-observed defect — directly contradicting the scenario premise that corrections stay uncommitted through to the passing seal. Root cause in package: workflow.md:71/73 and adapters-and-reviews.md:137._

- rep1: **FAIL** (failed: CS-1, CS-3) — VIOLATED: 'Before round 2 can dispatch, that fix must be committed (spec-fix-1) and resealed.'
- rep2: **FAIL** (failed: CS-1, CS-3) — VIOLATED: 'Inter-round fix | unnamed commit made to clear the uncommitted editorial correction before round 2 can start (review requires clean committed content).'
- rep3: **FAIL** (failed: CS-1, CS-3) — VIOLATED: 'Fixes occur only between rounds, are committed, re-sealed, and independently re-reviewed. Every fix becomes a new commit before it is resealed.'
- rep4: **FAIL** (failed: CS-1, CS-3) — VIOLATED: 'Both corrections land in one commit — this satisfies clean committed content for the next round and is re-sealed spec-seal-b.'
- rep5: **FAIL** (failed: CS-1, CS-3) — VIOLATED: 'A content seal presupposes clean committed content; nothing bearing seal plan-seal-a can simultaneously be uncommitted' — declares the scenario premise illegal.

### PLAN-DRIFT — 1/5 FAIL

_Only rep5 fails, and only by contradiction: its headline "Authoritative status" declares task 1 flatly "complete" / evidence "authoritative" before any contract-unchanged proof exists, undercutting the provisional/conditional preservation the rest of its own document (and all other reps) correctly requires._

- rep1: **PASS** (failed: -) — "Task 1's verified commit stands as recorded evidence, but whether it survives is not yet decided — that depends on reconciliation attribution below, not on the native-task claim." Combined with explicit non-editorial routing: "every invalidated implementation task (task 2, and task 1 only if the attribution shows it is affected)... are redone from that new freeze forward." All four predicates satisfied: blocked/overrides native tasks (PD-1), sole next action is read-only reconciliation with default classification before any dispatch (PD-2), full invalidate→Stage 8→re-freeze→redo chain for non-editorial (PD-3), task-1 evidence explicitly conditional (PD-4).
- rep2: **PASS** (failed: -) — "task 1 stays valid unless the edit retroactively affects what it implemented" and prerequisite #3: "downstream evidence (task 1 commit, task 2 progress) confirmed provably unchanged." Non-editorial path explicitly names invalidation, Stage 8 Plan review, new frozen blob ("re-freeze (new <path>@<blob> baseline)"), and resume-as-redo of invalidated tasks. Sole next action is read-only diff/attribution with default non-editorial classification stated before any dispatch.
- rep3: **PASS** (failed: -) — "task 1 = verified commit (pending re-confirmation, see §4)" — task-1 status flagged conditional right in the authoritative-status section itself, then confirmed in §4: "reconciliation must confirm task 1 is unaffected by the p111→p222 delta before its evidence counts toward acceptance; if affected, it is invalidated too." Non-editorial branch names invalidation, Stage 8, new frozen baseline, and resume 'at the earliest invalidated node' (revalidation).
- rep4: **PASS** (failed: -) — "Task 1's verified commit is real evidence and stands as recorded; it is not, by itself, proof the run is complete" and later "task 1's verified commit survives only if Plan review confirms its owned contract is unaffected by the delta — otherwise it too is invalidated." Non-editorial path explicitly: invalidate affected tasks → Stage 8 Plan review → freeze new blob identity → tasks redone. Sole action is read-only diff+attribution with default non-editorial classification recorded before dispatch.
- rep5: **FAIL** (failed: PD-4) — VIOLATED: "Task 1: complete — verified commit + evidence stand as authoritative, independent of the native-task claim." This headline determination asserts task-1 evidence is settled/preserved ("complete", "authoritative") unconditionally, before any contract-unchanged proof exists — contradicting the response's own later hedge, "task 1's evidence survives only if the diff doesn't affect it; that determination is itself an output of reconciliation, not assumed here." The predicate requires preservation ONLY conditional on provable-unchanged inputs/contracts; declaring task 1 'complete' up front is a premature claim that partial/contradicted language elsewhere does not cure, per strict scoring (partial or contradicted = FALSE). PD-1, PD-2, PD-3 are otherwise satisfied in this response.

### UAT-TRUTH — 4/5 FAIL

_4 of 5 responses treated the prompt's stated scenario facts (Sam's transcript/approval, the npm test's pass) as unverified claims to be denied rather than content to record, so both branches were flattened to pending/infeasible with no waived-human statement, contradicting the supplied premise instead of faithfully transcribing it into separate mode-conditioned records._

- rep1: **FAIL** (failed: UT-1, UT-3, UT-4) — VIOLATED: "none — no command transcript exists; Sam has not run `acme import --file fixtures/malformed-row-7.csv` in this session" — the prompt states as given fact that 'Sam's transcript records exit 2 and that stderr text, and Sam approves'; rep1 flatly denies this instead of recording it, and never uses a 'waived' human-UAT state (uses 'infeasible' throughout).
- rep2: **FAIL** (failed: UT-1, UT-4) — VIOLATED: "No command transcript and no test-run output has been captured in this exchange, so both rows are stated at `pending`... None of that has occurred here, so `approved` cannot be recorded." — never records Sam's supplied approval as given by the prompt; the supervised row stays an unmet requirement rather than a recorded fact, so UT-4's 'supervised branch records Sam's supplied approval' is not satisfied.
- rep3: **PASS** (failed: -) — Supervised row: acceptance state 'approved', authority 'user — Sam (support lead)', evidence 'Captured command transcript... exit status 2, stderr exactly row 7 rejected. Sam reviewed this transcript and approved.' Unattended row: state 'waived', authority 'agent:unattended — standing authority... sole authority for unattended UAT waiver', fallback 'Human UAT waived, not performed... No human/Sam approval is claimed here.' Both rows explicitly conditioned as 'applies only if the run's mode is...' satisfying UT-1 through UT-4.
- rep4: **FAIL** (failed: UT-1, UT-3, UT-4) — VIOLATED: "none captured — no command transcript exists; Sam has not run the command in this session" and "`waived` is unavailable for either row: waiving requires material authority and rationale for skipping evidence... no waiver has been invoked here." — denies the supplied approval and explicitly refuses a waived-human statement.
- rep5: **FAIL** (failed: UT-1, UT-3, UT-4) — VIOLATED: "No participant executed the command in this session and no transcript captures exit status or stderr text, so stating exit 2 / `row 7 rejected` as observed would be fabricated evidence" and "A `waived` state without that evidence would be an implicit approval, which the contract explicitly disallows." — negates the supplied approval/automated-pass facts and rejects the waived state outright.

### CANONICAL-ARTIFACTS — 0/5 FAIL

_no failures — control passes on current package_

- rep1: **PASS** (failed: -) — Names all four paths exactly (lines 7-10), rejects all four proposed files in the table (lines 18-23) assigning charter/decisions to spec, state.json to ledger, uat-signoff to ledger+final-report, and closes with: "Outer-workflow authority may create/write only the four canonical paths above." No fifth authority source invented — drafts must be "integrated into the matching section" before any stage gate is satisfied.
- rep2: **PASS** (failed: -) — "Only the four exact paths already named — nothing else" (line 3), rejects all four proposed files as outer-workflow artifacts, assigns each to spec §7/§8, ledger, or final-report in the table, and explicitly caps any adapter-produced version of these files as "a disposable projection only — never read back as authority, never advance the run" — no fifth authority source created.
- rep3: **PASS** (failed: -) — "Only these four paths may exist as outer-workflow authority. No other file may be created as such authority, regardless of directory" (line 3). All four proposed files marked "No" in the verdict column and assigned to spec §1/§7/§8, ledger, or final-report; explicitly states any draft "carries no standing" once needed for orchestration — no fifth authority invented.
- rep4: **PASS** (failed: -) — "workflow.md fixes the canonical set to exactly these four paths — no others may be created as outer-workflow authority" (line 3). Each of the four proposed files individually ruled "not created" with content redirected to spec/ledger/final-report sections; the added note on review-loop report files explicitly reaffirms "They are not outer-workflow authority themselves; only the four canonical paths are" — does not invent a fifth authority source.
- rep5: **PASS** (failed: -) — "The four paths quoted are correct and exhaustive — workflow.md mandates 'exactly these' canonical paths" (line 3). Table rejects each proposed file ("Reject") and assigns decisions/state/acceptance to spec §7-8, ledger.md, or final-report.md; closing rule states extra material may be referenced "but such references never become a fifth governing file."

### ACTIVE-REVIEW — 4/5 FAIL

_Responses correctly forbid recording native verdict/seal/mapping before the round returns, but fail to describe that AFTER the return, the recorded native result is translated via the fixed native-result-to-stage mapping table (CONVERGED+merge-ready→pass, etc.) — AR-3 requires this affirmative "then applies fixed mapping" step, not just its prohibition beforehand._

- rep1: **FAIL** (failed: AR-3) — ABSENT — action text says only 'recover it from that referenced dispatch (native verdicts, report reference, seal) and record it.' No mention anywhere in the response of pass/changes_required/blocked or any fixed mapping being applied to the recovered native result.
- rep2: **FAIL** (failed: AR-3) — VIOLATED (partial): 'No pass/changes_required/blocked mapping may be written until the actual native verdicts, report reference, and content seal are captured on return.' — states the mapping must not happen early, but never describes that a fixed mapping IS then applied once captured; the 'record it' action clause itself omits any mapping step.
- rep3: **FAIL** (failed: AR-3) — VIOLATED (partial): 'do not write native verdicts, the report reference, the content seal, or a mapped result (pass / changes_required / blocked) until the round actually returns.' — mapping is named only as a forbidden-until item; the response never states that a fixed mapping is applied to produce that mapped result once the return exists.
- rep4: **FAIL** (failed: AR-3) — VIOLATED (partial): 'Advancing the review state (e.g., to pass/changes_required/blocked), freezing the plan, or creating any commit.' — pass/changes_required/blocked appear only as forbidden-now advancement targets; no description of capturing verdict/ref/seal followed by applying a fixed mapping table.
- rep5: **PASS** (failed: -) — 'If a return is recorded, recover it — capture both native verdicts, the report reference, and the whole-subject content seal — then map it via the native-result table (CONVERGED+merge-ready → pass; actionable findings → changes_required; INDETERMINATE/no viable fix/missing authority/unavailable capability → blocked; CONVERGED+not merge-ready → blocked).' Combined with explicit sole-next-action (await/recover, no re-dispatch) and full forbidden-list covering plan-candidate, ledger, and downstream-stage mutation, all three predicates (AR-1, AR-2, AR-3) are fully satisfied.

### DIRTY-PRIMARY — 0/5 FAIL

_no failures — control passes on current package_

- rep1: **PASS** (failed: -) — 'Recorded in the ledger's drift/dirty-path inventory, not staged, not touched.' + 'No existing org-sso worktree exists → create one.' + 'Only the explicit canonical paths above... No blanket git add -A/.'
- rep2: **PASS** (failed: -) — 'Not staged, modified, stashed, reset, discarded, amended, or otherwise touched — Feature Forge preserves unrelated user work unconditionally.' + 'Create a new, non-primary worktree and branch' + 'No git add -A, git add ., or broad/glob staging.'
- rep3: **PASS** (failed: -) — 'Enter read-only drift reconciliation: inventory and attribute only — no stage/modify/stash/reset/discard.' + 'create a new isolated non-primary worktree for this run rather than proceeding in /repo' + 'Stage only the explicit canonical artifact path(s)... No git add -A, git add ., or broad/glob staging.'
- rep4: **PASS** (failed: -) — 'left completely untouched: not staged, modified, stashed, reset, discarded, or committed' + 'Create a new isolated non-primary worktree.' + 'No blanket git add -A/-u. docs/customer-notes.md is out of scope and is never staged'
- rep5: **PASS** (failed: -) — 'It's preserved as-is and logged in the ledger's dirty-path inventory... Preflight proceeds.' + 'a fresh isolated worktree (e.g. git worktree add ../org-sso feature/org-sso), distinct from /repo' + 'Never add -A/add .. docs/customer-notes.md is never staged, committed, amended, stashed, reset, or discarded'

### HANDOFF-RETURN — 1/5 FAIL

_The single failure (rep4) collapses the adapter table to bare metadata (skill/stage/consumed-flag) and drops the return-artifact description entirely for plan-return, so it never states the plan is self-reviewed before returning, even though it otherwise nails the execute-return interception and Stage-3-through-14 ordering exactly like the four passing reps._

- rep1: **PASS** (failed: -) — "the outer controller must intercept execute-return at that exact handoff point, record it as the execute-return result (status/commit/evidence per plan task, \"local checks\" as the local verification evidence), and refuse to let the native skill proceed into actual branch finishing. Control returns to the ledger at Stage 10, not Stage 14." Plan-return explicitly returns a "self-reviewed canonical plan" (Stage 7, before Stage 9 Implement); brainstorm-return closed before Stage 3 Harden; order runs Stage 3–13 before a single Stage 14 finish-authority dispatch.
- rep2: **PASS** (failed: -) — "That moment — task-by-task execution and local checks done, about to hand off to branch-finishing — is the execute-return return point. Feature Forge must regain control exactly there, before that handoff executes... and continue the outer sequence (Stage 10+) instead of letting the native handoff run." plan-return explicitly returns a "self-reviewed canonical plan" before Stage 9; table orders Stage 3–13 before the single Stage 14 finish-authority invocation.
- rep3: **PASS** (failed: -) — "that handoff must be intercepted at the execute-return boundary. Feature Forge regains control there, records the plan-task rows/commits/evidence in the ledger's implementation table (not the skill's own completion signal), and proceeds through Stages 10–13 before finish-authority is dispatched — once, only at Stage 14." plan-return row explicitly returns a "Self-reviewed canonical plan"; brainstorm-return closed before Harden.
- rep4: **FAIL** (failed: HR-1) — ABSENT — the plan-return row reads only "| `plan-return` | `superpowers:writing-plans` | Stage 7 Plan | No |" with no "Return artifact" or description column at all; the word "self-review"/"self-reviewed" appears exactly once in the whole response, attached only to brainstorm-return ("Yes — spec written + self-reviewed"), never to plan-return. HR-1 requires plan-return to return after plan/self-review, which this response never states — only the ordering (before execution) is implicit via the stage list. HR-2 and HR-3 are otherwise satisfied ("it must not treat the native handoff as authoritative, must not let it invoke branch finishing, and must not dispatch finish-authority until Stage 14 is actually reached").
- rep5: **PASS** (failed: -) — "Feature Forge intercepts it as the execute-return boundary: the handoff attempt is treated as execute-return's return, its result (status/commit/evidence per plan task) is recorded in the ledger's implementation table, and control resumes the outer order at Stage 10 — not at Stage 14. The real finish-authority dispatch happens exactly once, later, only once Stage 13 Report is complete." plan-return explicitly "Returns a self-reviewed canonical plan" before Stage 9 Implement.

### FINISH-CAPABILITY — 5/5 FAIL

_All five responses record Stage 14's ready→blocked transition with checkpoint category set to 'None' and explicitly cap the checkpoint taxonomy at seven categories, never recording the transition under the required category 8 (FC-2); rep5 additionally omits any explicit prohibition on menu presentation or unattended resolution (FC-3)._

- rep1: **FAIL** (failed: FC-2) — VIOLATED: 'Checkpoint category: None. No new checkpoint is created. ... Finish has no assigned commit-checkpoint category of its own, and since finish-authority is never dispatched, nothing is committed to trigger one.' — FC-2 requires recording the ready→blocked transition 'under category 8'; rep1 asserts no such category exists rather than recording it, so the category-8 element of FC-2 is unmet even though prior-phase-ready, capability evidence, and resolution-only next action are all otherwise present.
- rep2: **FAIL** (failed: FC-2) — VIOLATED: '## Checkpoint category\n\nNone. No new checkpoint fires. Checkpoint 7 ... is already satisfied as Stage 13's exit evidence; Finish itself owns no commit checkpoint of its own.' — same gap as rep1: FC-2's 'category 8' requirement is never invoked; the response caps the checkpoint taxonomy at 7 and records the ready→blocked transition with no checkpoint category at all.
- rep3: **FAIL** (failed: FC-2) — VIOLATED: 'Finish (Stage 14) owns no checkpoint category among the seven defined categories — the seven defined categories terminate at checkpoint 7 ... No commit is authorized at Finish entry.' — this explicitly asserts the checkpoint taxonomy terminates at 7, directly contradicting FC-2's requirement to record the transition under category 8.
- rep4: **FAIL** (failed: FC-2) — VIOLATED: 'Checkpoint category: None. Checkpoint 7 (report/acceptance) is already closed at Stage 13 exit. Stage 14 owns no checkpoint category of its own in the fixed seven-category list, and no commit may be made while the boundary is unenforceable/blocked.' — again a 'fixed seven-category' ceiling, no category-8 recording, failing FC-2's explicit category-8 requirement.
- rep5: **FAIL** (failed: FC-2, FC-3) — VIOLATED: 'Checkpoint category: None. No tracked write occurs. Finish owns no checkpoint category among the seven defined in workflow.md — the acceptance checkpoint (category 7) is already closed from Stage 13.' fails FC-2 identically to the others. Additionally rep5 never mentions the integration-choice 'menu' at all and never states resolution requires explicit user authority (only 'until the environment can (a) ... and (b) ...'), so FC-3's 'menu presentation' and 'unattended resolution' prohibitions are ABSENT — the only response missing both, on top of the shared FC-2 failure.

### FINISH-CRASH — 5/5 FAIL

_Every response's ambiguous/blocked-case ledger record captures the blocked status, evidence, and confirmation of no executed side effect, but none of the five explicitly attribute the prior state ('executing') within that same blocked record as FCr-3 requires._

- rep1: **FAIL** (failed: FCr-3) — VIOLATED (by omission): "Evidence ambiguous, conflicting, or forge unreachable → run is `blocked` at Stage 14 under read-only drift reconciliation: inventory and attribute the discrepancy in the Blockers table; take no mutating action until resolved." — records blocked status, evidence-gathering, and no-side-effect, but never attributes the prior state (`executing`) in that record as FCr-3 requires.
- rep2: **FAIL** (failed: FCr-3) — VIOLATED (by omission): "Forge unreachable / PR state unconfirmable → **Blocked.** ... block pending environment/authority, ledger sole-next-action = 'reconcile F-17 forge evidence.'" — no prior-state (`executing`) field is recorded alongside the blocked entry, only the blocked outcome and next-action note.
- rep3: **FAIL** (failed: FCr-3) — VIOLATED (by omission): "Add a blocker row: type `blocker`, description ... , authority/root cause, evidence gathered so far." — the blocker row schema lists type/description/authority/evidence but no prior-state ('executing') field, even though Rep3 does include an explicit `from: active/executing →` field for its *complete*-path transition row, showing the omission on the blocked path is a real gap not a stylistic choice.
- rep4: **FAIL** (failed: FCr-3) — VIOLATED (by omission): "F-17/Stage 14 → `blocked`; record the blocker with the exact missing/contradictory evidence; sole next permitted action is obtaining that evidence — no mutating action until it is resolved." — records evidence and no-side-effect but never records that the prior recorded state was `executing`.
- rep5: **FAIL** (failed: FCr-3) — VIOLATED (by omission): "Record blocker (type: blocker, description: 'PR step of F-17 dispatch unconfirmed after push landed', evidence: remote ref + forge query showing no PR), and require explicit authority..." — blocker record has type/description/evidence but no prior-state ('executing') attribution field.

### OPTION1-DIRTY-BASE — 0/5 FAIL

_no failures — control passes on current package: all five responses correctly refused the prompt's fabricated "category-8" label, kept inspection read-only on both the base checkout and feature worktree (treating a clean feature worktree as insufficient), forbade any base-checkout mutation, kept the next action resolution-only with merge blocked, and named the receipt location only as a contingent future outcome._

- rep1: **PASS** (failed: -) — "the unresolved dirty base checkout blocks advancement; finish-authority must return `blocked` rather than proceed... Merge stays blocked until: the dirty path is reconciled by the user (not the agent)" — inspects both trees read-only, records blocked status with evidence and a resolution-only next action, never touches the base, and only names the receipt location conditionally ("Feature Forge defines no separate 'receipt' artifact. Once reconciliation clears the base checkout... its outcome/evidence is recorded in:").
- rep2: **PASS** (failed: -) — "The base checkout that the local-merge action would operate on is dirty. That is a failed environment check under Finish's own failure/blocked-return rule, so status is **blocked**... finish-authority has not yet been dispatched, and must not be, until the entry predicate holds." Inspects base and feature worktree read-only, forbids all mutating actions, and gates the receipt on future completion ("Receipt location, once safe").
- rep3: **PASS** (failed: -) — "Feature Forge itself may not stash/discard/commit it... The unresolved dirty base checkout blocks advancement... finish-authority may not be dispatched, and no merge into `main@b333` may begin, while `/repo` is in this state." Explicitly checks base ref/identity read-only, produces a blocker row with evidence, and states "No receipt is written until the merge actually executes; none exists yet given the current block."
- rep4: **PASS** (failed: -) — "Entry predicate... is satisfied on the **feature** side (worktree clean at `f444`). But the workflow contract's dirty-path rule applies generally, not only to the feature worktree" — directly demonstrates that a clean feature worktree alone is treated as insufficient, backs the block with a formal evidence-bearing blocker row, keeps next action resolution-only, and blocks the merge ("No merge... may begin").
- rep5: **PASS** (failed: -) — "sole next action = resolve/reconcile the unrelated dirty base path (read-only on Feature Forge's side) before `finish-authority` may be dispatched" — full read-only inspection of both trees including base ref identity, formal blocker row with evidence field, merge explicitly blocked ("No."), and receipt location stated only contingently ("if later safe").

## Deterministic structural evidence

```text
=== deterministic structural checks (R0 Step 3) — 2026-08-17T05:21:00Z ===
--- quick_validate.py ---
Skill is valid!
exit=0
--- git diff --check ---
exit=0
--- SKILL.md word count (<500 expected) ---
292
--- stage headings (==14 expected) ---
14
--- defect/vocab grep (Finish/Report/checkpoint/finish_id/menu_pending) ---
feature-forge/references/workflow.md:114:Create these seven checkpoint categories only when the corresponding tree differs:
feature-forge/references/workflow.md:265:| 13 Report | acceptance complete | final report and ledger | acceptance checkpoint/clean tree | return or block | 14 Finish |
```

Two structural package defects recorded: `references/workflow.md` names **seven** checkpoint
categories (the amended specification requires **eight**, incl. category 8), and the package
contains no `finish_id` / `menu_pending` durable-Finish vocabulary.

## Failed-predicate -> owning-task routing

Only failed predicates are routed. GREEN work for the amended specification is confined to these owners.

| Control | Failed predicates | Owning task(s) / file(s) |
|---|---|---|
| PIPELINE-SSO | PS-13, PS-14 | Task 2 (references/workflow.md): 14-stage order, eight checkpoint categories, Stage 13->14 Finish records, single finish invocation |
| PLAN-REVIEW | PV-5 | Task 3/Task 4: plan-review charter blockers vs polish |
| UNATTENDED | UA-2, UA-4 | Task 3 (references/authority.md): unattended in-scope decisions without live-user pause |
| TASK-LOSS-RESUME | TL-3, TL-6 | Task 2 (references/workflow.md): frozen-identity recompute, native-task rebuild, completed-work preservation, sole-next-action |
| WORKER-PACKET | WP-3 | Task 4 (references/adapters-and-reviews.md): worker dispatch packet completeness |
| CANDIDATE-SEALS | CS-1, CS-3 | Task 2 (references/workflow.md) + Task 4 (references/adapters-and-reviews.md): remove per-round clean-commit rule; candidate corrections stay uncommitted until the passing seal |
| PLAN-DRIFT | PD-4 | Task 3 (references/authority.md) + Task 2 (references/workflow.md): plan-drift classification, invalidation, downstream revalidation |
| UAT-TRUTH | UT-1, UT-3, UT-4 | Task 3 (references/authority.md): supervised vs unattended UAT records, agent:unattended waiver truthfulness |
| ACTIVE-REVIEW | AR-3 | Task 4 (references/adapters-and-reviews.md): native-result -> stage fixed-mapping applied after review return |
| HANDOFF-RETURN | HR-1 | Task 4 (references/adapters-and-reviews.md): brainstorm/plan/execute return boundaries and finish interception |
| FINISH-CAPABILITY | FC-2, FC-3 | Task 2 (references/workflow.md) + Task 4 (finish-authority adapter): category-8 ready->blocked capability gating and durable Finish journal |
| FINISH-CRASH | FCr-3 | Task 2 (references/workflow.md) + Task 4 (finish-authority adapter): finish_id journal-first crash recovery, read-only reconcile, blocked-on-ambiguity |

## Coverage

The campaign jointly exercises REQ-001/SCN-001 through REQ-012/SCN-012 and SCN-013 via the
direct controls, with LEDGER-ACTIVE and PIPELINE-SSO covering whole-workflow behavior and the
seven retained regression controls preserving the original broad-judgment baseline.

## Status of historical evidence

The historical `docs/feature-forge/skill-tdd/2026-08-17-green-results.md` remains **historical
only**. It qualified the pre-amendment specification and does **not** qualify the amended
specification. Only a later amended-GREEN campaign that supersedes this RED evidence, run against
the corrected package under these same frozen fixtures, can qualify the amended specification.
