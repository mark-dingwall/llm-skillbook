# Feature Forge workflow and durable-state contract

This reference is the sole authority for canonical paths, run identity, stage
and review state, transitions, resumption, and Git checkpoints. The tracked run
ledger is the durable workflow authority; native task state is a disposable
projection and never advances the run.

## Canonical artifacts and state

Use exactly these canonical paths:

```text
docs/superpowers/specs/YYYY-MM-DD-<work-unit>-design.md
docs/superpowers/plans/YYYY-MM-DD-<work-unit>.md
docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/ledger.md
docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md
```

`<work-unit>` is the deterministic slug used in every path, the run identifier,
and `feature/<work-unit>`. It is lowercase ASCII letters and digits separated
by single hyphens, begins and ends alphanumeric, and is rejected (not silently
sanitized) if it contains a separator, traversal segment, whitespace, leading
dash, or invalid Git-ref content.

Stage states are `pending | active | blocked | complete | invalidated`. Review
states are `not_started | review_active | pass | changes_required | blocked`.
The ledger names exactly one next permitted action except at a terminal state.
`review_active` permits only **await or recover the existing review**; it does
not permit target, ledger, downstream-stage, or new-review mutation.

The ledger records coarse orchestration state only: run/mode, current stage and
sole next action, branch/worktree identity, canonical paths and frozen
identities, review summaries, approvals/authority, execution mode, acceptance
and verification state, blockers/change requests, the implementation table, and
the Finish operation journal (`finish_id`, phase, selected choice and
authority, base/feature tips, worktree, exact next side effect, and durable
receipts):

| plan task | status | commit | evidence |
|---|---|---|---|

The plan remains frozen authority: its checkboxes are never changed for progress.
The table, cross-checked against Git and its evidence on resume, is authoritative
for implementation completion.

## Identity, review seals, and resumption

Frozen identity applies only to the independently reviewed specification and
plan: record each as `<path>@<git-blob-id>` in the ledger and transition
history. Recompute and compare applicable frozen identities before every
downstream gate and on every resume. The ledger and final report are
deliberately mutable run records — their truth is transition history,
checkpoint commits, and durable Finish receipts, and neither ever receives a
frozen blob identity.

A candidate seal is the exact candidate-file content supplied to `review-loop`
for the specification or plan charter. It is not a frozen blob identity and may
change uncommitted between rounds: candidate fixes need not be committed to
start the next round, and only the passing candidate receives its freeze
checkpoint commit and `<path>@<git-blob-id>` baseline. The implementation
subject, not every review subject, begins clean, committed implementation
review and final verification: each implementation-review round is read-only
against its whole-tree content seal, fixes occur only between rounds, are
committed, re-sealed, and independently re-reviewed, and `pass` means a final
pass on the post-fix snapshot. Preserve both native verdicts, the stable report
reference, the stage charter, completion criterion, and the content seal for
every review.

Persist a complete ledger update before each external dispatch and immediately
after each return. A transition-log row has event ID, UTC time, from/to state,
sole next permitted action, reason/authority, and evidence reference. A missing
recorded return is recovered from its referenced dispatch before re-dispatch.

On resume, read the ledger plus every exact canonical artifact it names; verify
frozen blob identities, worktree/branch, commits, evidence references, and
review seals; reconstruct native tasks from it; and perform only the ledger's
sole next action. The reconstructed native display always projects all
fourteen outer stages — prior stages complete, the current ledger stage active,
later stages pending — never a plan-task list alone; within an active Implement
stage, project the implementation table underneath that one active stage, and
confine the sole next action to the single active plan task, never spanning
into pending tasks. Conversation memory or a surviving native task list never
overrides the ledger.

A mismatch, rejected approval, change request, missing review return, or dirty
path first enters **read-only drift reconciliation**: inventory and attribute
without staging, modifying, stashing, resetting, or discarding anything.
Unresolved material drift is `blocked`. An authorized correction invalidates the
affected stage and its dependents, then resumes at the earliest invalidated
node. An unrelated dirty path blocks advancement; attributable changes must be
reconciled under the relevant stage and checkpoint rule.

Before Final verification, a post-review seal comparison permits only the exact
run-ledger path and its recorded review evidence reference as a delta; inspect
both, separately confirm the reviewed implementation commit and every other
sealed path are unchanged, and block all other differences.

## Fixed change and invalidation graph

Classify changes under the authority contract. Editorial changes enter
`invalidated`, receive a scoped delta review, are committed, replace their
frozen blob identity while retaining the prior identity in transition history,
and preserve downstream evidence only when behavior and contracts are provably
unchanged. Reviewer doubt reclassifies the change as a specification or plan
defect.

For non-editorial corrections, apply this fixed graph:

| Root cause | Invalidates | Resume point |
|---|---|---|
| specification defect | plan, implementation, implementation review, verification, acceptance, report | Specification review |
| plan-only defect | affected implementation tasks, implementation review, verification, acceptance, report | Plan review |
| implementation defect | implementation review, verification, acceptance, report | Implementation review |
| acceptance defect | classify to specification, plan, or implementation root cause and apply that row | earliest resulting invalidated stage |

No later evidence survives except under the allowed editorial transition above.
New requests are deferred unless the user explicitly expands the work unit.

## Git work and checkpoints

Before the first tracked write, establish or verify an isolated non-primary
worktree. Preserve unrelated user work. Inventory every dirty path; a dirty
feature worktree may be reused only when every change belongs to this work unit
and read-only reconciliation succeeds. Never implement on `main` or `master`
without explicit authority.

Stage only each **explicit path**, inspect the staged diff, and commit only
in-scope changes. Never capture, stash, reset, discard, amend, squash, or
combine unrelated user changes. Ordinary transitions do not create commits; do
not create empty commits or commit during an active review round.

Create these eight checkpoint categories only when the corresponding tree differs:

1. `docs: draft <feature> specification` after Brainstorm.
2. `docs: freeze reviewed <feature> specification` after Harden and Specification review.
3. `docs: draft <feature> implementation plan` after Plan.
4. `docs: freeze reviewed <feature> implementation plan` after Plan review.
5. Implementation commits owned by each reviewed plan task and the selected execution skill.
6. `fix: address final <feature> review findings` when Implementation review changes implementation.
7. `docs: record <feature> acceptance` for the final report, UAT/waiver, verification
   summary, traceability, branch-finishing readiness, the pending Finish outcome, and
   the active Stage 13 ledger.
8. `docs: record <feature> finish` for Stage 14 Finish write-ahead/choice records and
   terminal-or-blocked receipts, whenever the tracked state differs. Category 8 may
   produce more than one explicit-path commit only when state differs: the `claimed`
   commit before method execution, the `menu_pending` commit before menu delivery or
   unattended resolution, the atomic `choice_recorded`-then-`executing` commit before
   any side effect, and the atomic terminal-or-blocked commit after reconciliation. No
   category 8 record commit permits another external-skill invocation; the
   finish-authority dispatch remains the sole and last external skill invocation.

Checkpoint 7 commits the final report and ledger after verification and acceptance
while the run remains **active**, Finish phase `ready`, and outcome `pending` — it is
not a completed ledger. The feature worktree must be clean before Finish begins and
before each non-read-only Stage 14 integration step. See "Stage 14: durable Finish
phase protocol and crash recovery" below for the full category 8 lifecycle.

## Ordered outer stages

Stages are the complete outer workflow; do not add component gates. A stage is
complete only when its owned action/artifact and exit evidence are present.
Blocked, contradictory, or materially ambiguous work stays active or follows
explicit change control rather than being marked complete.

### Stage 1: Preflight

- **Entry:** a bounded work unit is invoked and no canonical run has yet been selected.
- **Owned action/artifact:** confirm Git; reject invalid slug/ref content; inspect same-date run collision and every all-date same-slug branch/worktree collision; compare intent, base, and identity; choose explicit resume, new, unused suffix, or block outcome; validate a review-loop-compatible, user-authorized runner; inventory and attribute dirty paths; create or verify reuse of an isolated non-primary worktree before the first tracked write; create/reuse the ledger and project stages to native tasks.
- **Exit evidence:** Git/worktree/branch identity, collision decision, runner validation, dirty-path reconciliation, and one ledger row with exactly one next action.
- **Failure/blocked return:** unresolved collision, unauthorized/unavailable runner, non-attributable dirt, non-Git repository, or inability to isolate blocks here; identity match resumes instead of creating a duplicate.
- **Next action:** Stage 2: Brainstorm.

### Stage 2: Brainstorm

- **Entry:** Preflight is complete and the ledger permits the brainstorm-return dispatch.
- **Owned action/artifact:** use the approved brainstorming return boundary to create the initial canonical specification.
- **Exit evidence:** written specification, required self-review/approval record, draft-specification checkpoint when changed, and returned result recorded in the ledger.
- **Failure/blocked return:** unavailable or unenforceable adapter blocks; a rejected or incomplete return remains here for recovery.
- **Next action:** Stage 3: Harden.

### Stage 3: Harden

- **Entry:** an initial specification is recorded and Stage 3 is the sole next action.
- **Owned action/artifact:** apply the authority contract's decision-tree hardening and integrate settled decisions, assumptions, and authority into the same specification.
- **Exit evidence:** hardening record and updated specification with no unresolved frontier ready to ask.
- **Failure/blocked return:** missing required authority or irresolvable contradiction blocks; an authorized correction follows the invalidation graph.
- **Next action:** Stage 4: Candidate gate.

### Stage 4: Candidate gate

- **Entry:** hardening has returned a specification candidate.
- **Owned action/artifact:** verify the frontier and `Open questions` are empty, delegated assumptions are recorded, and the applicable approval exists.
- **Exit evidence:** candidate-gate ledger evidence for a coherent, bounded, testable candidate.
- **Failure/blocked return:** return to Harden for a resolvable omission; block for missing authority or material ambiguity.
- **Next action:** Stage 5: Specification review.

### Stage 5: Specification review

- **Entry:** candidate-gate evidence exists and the specification subject has its candidate seal captured.
- **Owned action/artifact:** dispatch review-loop under the specification charter over the exact candidate-file content seal and record `review_active`, then its mapped result, native verdicts, report reference, and content seal.
- **Exit evidence:** `pass` review outcome on the exact candidate content seal.
- **Failure/blocked return:** only await/recover while `review_active`; `changes_required` returns to the minimum specification correction stage, corrected uncommitted, and re-sealed for the next round; `blocked` remains here.
- **Next action:** Stage 6: Specification freeze.

### Stage 6: Specification freeze

- **Entry:** Specification review passed on the recorded candidate content seal.
- **Owned action/artifact:** commit the reviewed specification and record its `<path>@<git-blob-id>` as the frozen specification baseline.
- **Exit evidence:** freeze checkpoint, matching blob identity, and ledger transition.
- **Failure/blocked return:** seal or identity drift enters read-only reconciliation and then the invalidation graph; Git failure blocks.
- **Next action:** Stage 7: Plan.

### Stage 7: Plan

- **Entry:** the frozen specification identity matches and Plan is sole next action.
- **Owned action/artifact:** invoke the plan-return boundary against that frozen specification and add the execution note that plan checkboxes are frozen and progress lives in the ledger.
- **Exit evidence:** self-reviewed canonical plan, draft-plan checkpoint when changed, and recorded adapter return.
- **Failure/blocked return:** unavailable/unenforceable adapter blocks; specification drift follows change control.
- **Next action:** Stage 8: Plan review.

### Stage 8: Plan review

- **Entry:** a self-reviewed plan exists and frozen specification identity still matches.
- **Owned action/artifact:** dispatch review-loop under the plan charter over the exact candidate-file content seal; after pass, commit and record the frozen plan identity.
- **Exit evidence:** pass on the plan candidate content seal, freeze-plan checkpoint, and matching `<path>@<git-blob-id>` baseline.
- **Failure/blocked return:** only await/recover while `review_active`; changes required return to Plan, corrected uncommitted, and re-sealed for the next round; blocked remains here; specification defect follows the graph.
- **Next action:** Stage 9: Implement.

### Stage 9: Implement

- **Entry:** frozen specification and plan identities match, and the ledger has the sole next implementation action.
- **Owned action/artifact:** choose exactly one authorized execution mode, dispatch its execute-return boundary, and maintain the implementation table without changing plan checkboxes.
- **Exit evidence:** every plan-task row has status, owned commit, and evidence, with local verification recorded and committed implementation content.
- **Failure/blocked return:** execution return is recovered before redispatch; plan/specification drift follows the graph; unavailable execution authority blocks.
- **Next action:** Stage 10: Implementation review.

### Stage 10: Implementation review

- **Entry:** implementation is clean, committed, and traceable to frozen specification and plan identities.
- **Owned action/artifact:** review-loop the whole implementation under its implementation charter; resolve findings only between read-only sealed rounds and commit accepted fixes.
- **Exit evidence:** final `pass` on the post-fix whole-tree content seal and reviewed implementation commit.
- **Failure/blocked return:** only await/recover while `review_active`; implementation findings return here for a new sealed round; exposed plan/specification defects follow the graph.
- **Next action:** Stage 11: Final verification.

### Stage 11: Final verification

- **Entry:** final implementation-review pass, reviewed implementation commit, and permitted post-review ledger delta only.
- **Owned action/artifact:** compare the seal, confirm no implementation or other sealed path changed, and run fresh risk-proportionate deterministic checks.
- **Exit evidence:** commands/results, reviewed commit, clean verification evidence, and matching identity/seal checks recorded in the ledger.
- **Failure/blocked return:** verification defect routes to its specification, plan, or implementation root cause; unexpected drift enters read-only reconciliation; unavailable required environment blocks.
- **Next action:** Stage 12: Acceptance.

### Stage 12: Acceptance

- **Entry:** Final verification evidence is current for the reviewed snapshot.
- **Owned action/artifact:** execute each specification-defined per-requirement acceptance method and record result, authority, and evidence.
- **Exit evidence:** every required behavior has current reproducible evidence and no material defect is open.
- **Failure/blocked return:** rejection returns to root-cause classification; infeasible or missing required authority blocks; waived UAT requires its declared authority.
- **Next action:** Stage 13: Report.

### Stage 13: Report

- **Entry:** all required acceptance rows have an outcome and no required behavior lacks evidence.
- **Owned action/artifact:** write the final requirement/scenario-to-plan-task-to-evidence-to-UAT report at `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md`; allocate one stable `finish_id`; record branch-finishing readiness with Finish phase `ready` and report outcome `pending`; commit acceptance, report, and ledger evidence through checkpoint 7 while the run remains **active**; and restore a clean feature worktree.
- **Exit evidence:** checkpoint 7 commit covering the final report and ledger, `finish_id` allocated and `ready` recorded, run active, worktree clean, and the ledger's sole next action set to `claim <finish_id>`.
- **Failure/blocked return:** incomplete, stale, or non-reproducible evidence returns to Acceptance or its root-cause stage; dirty tree blocks.
- **Next action:** claim `<finish_id>` (Stage 14: Finish).

### Stage 14: Finish

- **Entry:** Report is complete, Finish phase is `ready`, and the sole next action is `claim <finish_id>`.
- **Owned action/artifact:** durably drive the one logical Finish operation for `finish_id` through `ready -> claimed -> menu_pending -> choice_recorded -> executing -> terminal`, with `blocked` as a resumable overlay reachable from any nonterminal phase, per the protocol below. Invoke `finish-authority` (`superpowers:finishing-a-development-branch`) exactly once as the sole and last external skill invocation; every category 8 record commit around it is Stage 14 bookkeeping, not a second invocation.
- **Exit evidence:** a terminal category 8 commit recording durable outcome evidence, phase `terminal`, and overall run status `complete`; or, if blocked, a category 8 commit recording evidence, the prior phase it interrupted, `blocked` run state, and no executable next action.
- **Failure/blocked return:** a failed capability check, a dirty/unreconcilable base checkout, an unresolved menu presentation, or ambiguous crash-recovery evidence records `blocked` under category 8 with a resolution-only next action; it never claims, presents a menu, resolves unattended, or invokes an external skill while blocked.
- **Next action:** terminal; no further outer action once `terminal`/`complete` is recorded.

## Stage 14: durable Finish phase protocol and crash recovery

Stage 13 allocates exactly one stable `finish_id` and persists Finish phase `ready`.
One `finish_id` represents one durable **logical** Finish operation for the run; a
process crash cannot provide physically atomic exactly-once external effects, so this
protocol makes the operation recoverable rather than claiming it is atomic. Stage 14
owns this exact phase vocabulary and transition protocol:

```text
ready -> claimed -> menu_pending -> choice_recorded -> executing -> terminal
```

`blocked` is a resumable safe overlay reachable from every nonterminal phase, not only
from `executing`. Its category 8 receipt records the prior phase it interrupted, the
blocking evidence, and a resolution-only next action; once the named authority or
conclusive evidence is supplied, recovery returns to that prior phase under the same
`finish_id` and never starts a new Finish operation.

### Capability gate at `ready`

At `ready`, before the `claimed` category-8 commit and before any logical Finish
invocation, the workflow performs a mandatory harness-capability check for durable
journal interleaving (can the harness durably commit the journal between menu
selection and side effects) and read-only Git/forge reconciliation (can it read Git
and, for Push-and-PR, forge state without mutating either). If either capability is
unavailable, **workflow — not an adapter** — records `ready -> blocked` under category
8, with prior phase `ready`, evidence of the missing capability, and a
resolution-only next action. It performs no claim, no menu presentation, no
unattended resolution, and no external branch-finishing invocation. Only after that
capability check passes may it commit `claimed` in category 8.

### `claimed` through `executing`

Under the same `finish_id`, once `claimed` is committed, perform the installed
finishing skill's test/environment/base determination steps (fresh full test suite,
Git/common-directory and worktree detection, named-branch check, and base-branch
determination). Commit `menu_pending` in category 8 before the interactive/supervised
menu presentation or before unattended resolution:

- Interactive/supervised: the `menu_pending` receipt records the exact three
  installed choices and a stable presentation ID.
- Unattended: the `menu_pending` receipt instead records the named pre-authorization
  when present, or `agent:unattended default-keep` when none is pre-authorized,
  before resolution.

The choices are exactly local merge to confirmed base, Push-and-PR, and Keep
branch/worktree — no other or reduced choice set. A detached HEAD or another
environment that cannot retain all three installed choices records `blocked`
under category 8 with the missing-capability evidence and a resolution-only
next action, rather than presenting a reduced menu.

Before any side effect, commit a single complete category-8 update that records
`choice_recorded` then current `executing` atomically: selected choice, authority,
confirmed base, base/feature tips, worktree, environment evidence, and the exact next
side effect. That commit must succeed and the feature worktree must be clean before
any non-read-only operation begins.

### Option 1 base-checkout safety

Before committing Option 1 (local merge) as `executing`, inspect the actual base
checkout that will receive the merge. If it is dirty, conflicted, owned by unrelated
work, or cannot be reconciled read-only to the confirmed base, atomically record
`blocked` under category 8 with that evidence; never stash, reset, clean, merge into,
or otherwise change that checkout.

### Terminal receipts

A terminal outcome requires durable result evidence. For local merge, write the
terminal ledger/report receipt and its category 8 commit in the **base checkout** so
it survives feature-worktree cleanup and feature-branch deletion. For Push-and-PR and
Keep, preserve the feature branch/worktree and write the terminal receipt there. The
terminal category 8 commit is one atomic transaction: it records result evidence,
changes Finish phase to `terminal`, changes overall run status to `complete`, and
removes the next action, updating ledger and report together. A blocked category 8
commit likewise updates ledger and report together: it records evidence, the prior
phase, `blocked` run state, and no executable next side effect. Stage 14 bookkeeping
commits made after the installed skill returns are permitted and are not a second
external invocation.

### Recovery

On recovery, first read the phase and receipts, then reconcile Git — comparing
both the recorded base ref and the feature ref against their recorded values —
and — only for Push-and-PR — forge state, both read-only, before taking any
action.

- `ready` with no claim commit permits exactly one claim.
- `claimed` proves the logical method already began; a fresh controller resumes its
  read-only test/environment/base steps under the same `finish_id` rather than
  claiming or dispatching again.
- Interactive/supervised `menu_pending` with no durable choice must not re-present the
  menu or invent a choice; it blocks awaiting an explicit choice against the existing
  menu record.
- Unattended `menu_pending` recovery consumes only the authority/choice already
  committed; it never resolves or chooses a new default after the crash window.
- From `choice_recorded`/`executing`, recovery takes only the recorded next side
  effect whose non-occurrence is provable.
- Recovery must never repeat a claim, menu presentation, merge, pull, push, PR
  creation, cleanup, or branch deletion.
- If an external effect may have occurred but cannot be identified conclusively,
  atomically persist `blocked` under category 8 recording the ambiguity, evidence,
  **the prior phase it interrupted** (for example `executing`), and no executable
  next side effect — never guess or repeat it.
- If instead the side effect's outcome is conclusively reconciled — proven to have
  occurred or proven not to have occurred — recovery writes the conclusive terminal
  receipt (phase `terminal`, overall run `complete`, no next action) in one atomic
  category 8 ledger/report transaction, on the correct preserved location: the base
  checkout for local merge, or the preserved feature branch/worktree for Push-and-PR
  and Keep.

## Per-stage acceptance table

Every stage below has an entry predicate, owned artifact/action, evidence gate,
failure or blocked return, and one sole next action.

| Stage | Entry predicate | Owned artifact/action | Evidence gate | Failure or blocked return | Sole next action |
|---|---|---|---|---|---|
| 1 Preflight | invoked work unit | canonical run, isolation, ledger | Git/identity/runner/dirty-path record | block or explicitly resume/new/suffix | 2 Brainstorm |
| 2 Brainstorm | preflight complete | initial specification | adapter return and draft checkpoint | recover or block | 3 Harden |
| 3 Harden | initial specification | hardened specification | decisions/authority record | harden or block | 4 Candidate gate |
| 4 Candidate gate | hardening returned | candidate validation | empty frontier/Open questions | 3 Harden or block | 5 Specification review |
| 5 Specification review | sealed candidate | specification review | pass content seal | await/recover, correct, or block | 6 Specification freeze |
| 6 Specification freeze | review pass | frozen specification | blob identity/checkpoint | reconcile or block | 7 Plan |
| 7 Plan | matching frozen spec | canonical plan | adapter return/draft checkpoint | recover or block | 8 Plan review |
| 8 Plan review | reviewed-plan candidate | plan review/freeze | pass seal/blob/checkpoint | await/recover, correct, or block | 9 Implement |
| 9 Implement | matching frozen baselines | implementation table/content | commits and local evidence | recover, invalidate, or block | 10 Implementation review |
| 10 Implementation review | clean implementation | implementation review | final pass seal | await/recover, fix, or invalidate | 11 Final verification |
| 11 Final verification | final review pass | deterministic verification | commands/results/seal comparison | root-cause return or block | 12 Acceptance |
| 12 Acceptance | current verification | acceptance outcomes | every required evidence row | root-cause return or block | 13 Report |
| 13 Report | acceptance complete | final report, ledger, `finish_id` allocation | checkpoint 7 commit, `ready` phase, clean tree | return or block | claim `<finish_id>` |
| 14 Finish | phase `ready`, sole action claim `<finish_id>` | durable `ready`-to-`terminal` Finish operation (category 8) | terminal or blocked category-8 receipt | block (never a duplicate invocation) | terminal |
