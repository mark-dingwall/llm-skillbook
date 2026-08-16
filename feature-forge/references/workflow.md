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
and verification state, blockers/change requests, and the implementation table:

| plan task | status | commit | evidence |
|---|---|---|---|

The plan remains frozen authority: its checkboxes are never changed for progress.
The table, cross-checked against Git and its evidence on resume, is authoritative
for implementation completion.

## Identity, review seals, and resumption

For every frozen canonical artifact, record its Git blob identity as
`<path>@<git-blob-id>` in the ledger and transition history. Recompute and
compare applicable identities before every downstream gate and on every resume.
The review identity is the exact `review-loop` **content seal** for its
whole-tree subject. Preserve both native verdicts, the stable report reference,
the stage charter, completion criterion, and that content seal.

Persist a complete ledger update before each external dispatch and immediately
after each return. A transition-log row has event ID, UTC time, from/to state,
sole next permitted action, reason/authority, and evidence reference. A missing
recorded return is recovered from its referenced dispatch before re-dispatch.

On resume, read the ledger plus every exact canonical artifact it names; verify
frozen blob identities, worktree/branch, commits, evidence references, and
review seals; reconstruct native tasks from it; and perform only the ledger's
sole next action. Conversation memory or a surviving native task list never
overrides the ledger.

A mismatch, rejected approval, change request, missing review return, or dirty
path first enters **read-only drift reconciliation**: inventory and attribute
without staging, modifying, stashing, resetting, or discarding anything.
Unresolved material drift is `blocked`. An authorized correction invalidates the
affected stage and its dependents, then resumes at the earliest invalidated
node. An unrelated dirty path blocks advancement; attributable changes must be
reconciled under the relevant stage and checkpoint rule.

For a review subject, begin each round with clean committed content. Review-loop
is read-only against its whole-tree content seal. Fixes occur only between
rounds, are committed, re-sealed, and independently re-reviewed; `pass` means a
final pass on the post-fix snapshot. Before Final verification, a post-review
seal comparison permits only the exact run-ledger path and its recorded review
evidence reference as a delta; inspect both, separately confirm the reviewed
implementation commit and every other sealed path are unchanged, and block all
other differences.

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

Create these seven checkpoint categories only when the corresponding tree differs:

1. `docs: draft <feature> specification` after Brainstorm.
2. `docs: freeze reviewed <feature> specification` after Harden and Specification review.
3. `docs: draft <feature> implementation plan` after Plan.
4. `docs: freeze reviewed <feature> implementation plan` after Plan review.
5. Implementation commits owned by each reviewed plan task and the selected execution skill.
6. `fix: address final <feature> review findings` when Implementation review changes implementation.
7. `docs: record <feature> acceptance` for final report, UAT/waiver, verification summary, traceability, and completed ledger.

The final report and completed ledger use checkpoint 7 after verification and
acceptance. The tree must be clean before Finish begins.

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

- **Entry:** candidate-gate evidence exists and the specification subject is clean and sealed.
- **Owned action/artifact:** dispatch review-loop under the specification charter and record `review_active`, then its mapped result, native verdicts, report reference, and content seal.
- **Exit evidence:** `pass` review outcome on the exact candidate content seal.
- **Failure/blocked return:** only await/recover while `review_active`; `changes_required` returns to the minimum specification correction stage; `blocked` remains here.
- **Next action:** Stage 6: Specification freeze.

### Stage 6: Specification freeze

- **Entry:** Specification review passed on the recorded content seal.
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
- **Owned action/artifact:** dispatch review-loop under the plan charter; after pass, commit and record the frozen plan identity.
- **Exit evidence:** pass on the plan content seal, freeze-plan checkpoint, and matching `<path>@<git-blob-id>` baseline.
- **Failure/blocked return:** only await/recover while `review_active`; changes required return to Plan; blocked remains here; specification defect follows the graph.
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
- **Owned action/artifact:** write the final requirement/scenario-to-plan-task-to-evidence-to-UAT report at `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md`, complete the ledger, and record branch-finishing readiness.
- **Exit evidence:** final report and ledger are committed through the acceptance checkpoint; worktree is clean.
- **Failure/blocked return:** incomplete, stale, or non-reproducible evidence returns to Acceptance or its root-cause stage; dirty tree blocks.
- **Next action:** Stage 14: Finish.

### Stage 14: Finish

- **Entry:** Report is complete, the branch/worktree is clean, and all prior gates are complete.
- **Owned action/artifact:** invoke the finish-authority boundary exactly once and record the user-authorized or safe default integration outcome.
- **Exit evidence:** exactly-once finish return and recorded outcome.
- **Failure/blocked return:** missing finish authority, failed environment checks, or unenforceable boundary blocks here without a duplicate invocation.
- **Next action:** terminal; no further outer action.

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
| 13 Report | acceptance complete | final report and ledger | acceptance checkpoint/clean tree | return or block | 14 Finish |
| 14 Finish | clean reported run | exactly-once branch finish | recorded return/outcome | block | terminal |
