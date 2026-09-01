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
sanitized) if it contains consecutive hyphens or any non-hyphen separator, a
traversal segment, whitespace, a leading dash, or invalid Git-ref content.

## Ledger v1 head and human evidence

The first nonblank ledger content is one fenced `json` object with no comments.
It is checker-owned current state; Markdown tables retain human-owned evidence
and must not mirror any current head value. A pre-schema ledger is unsupported
and transitions `unsupported -> blocked`; never migrate it or silently treat it
as absent.

| head key | value and rule |
| --- | --- |
| `schema` | Exactly `feature-forge/ledger/v1`. |
| `run_id` | Work-unit slug. |
| `status` | `active`, `blocked`, or `complete`. |
| `worktree`, `branch`, `base_identity` | Current absolute worktree; exact `feature/<run_id>` branch; canonical full, resolvable commit OID. |
| `stage` | `{id, state}`; IDs are 1..14 and state is `pending`, `active`, `blocked`, `complete`, or `invalidated`. |
| `next_action` | Nonempty for nonterminal heads; null only when status is `complete`, which is valid only with Stage 14 complete. |
| `frozen` | `specification` and `plan`, each null or exactly `{path, blob}` strings; non-null paths are the run-derived canonical artifacts and blobs are canonical full, resolvable blob OIDs. |
| `review` | Current review control object, defined below. |

The exact top-level key set is `schema`, `run_id`, `status`, `worktree`,
`branch`, `base_identity`, `stage`, `next_action`, `frozen`, and `review`.
The head owns those current values. Tables retain intent/run evidence, authority,
implementation evidence, verification/acceptance evidence, the Finish journal,
and dated transitions. They never claim to hold a current review field; prior
review evidence belongs in transition history, not the current head.

`review` has exactly `kind`, `state`, `round`, `root_identity`, `dispatch_id`,
`run_ref`, `target_seal`, `evidence_path`, `reviewed_commit`,
`previous_open_finding_ids`, and `open_finding_ids`. `kind` is null,
`specification`, `plan`, or `implementation`; `state` is `not_started`,
`review_active`, `changes_required`, `pass`, or `blocked`. Round and finding-ID
arrays are checker-consumed control state, not coarse prose: finding IDs are
sorted, unique opaque actionable IDs and never finding text.

| review state | required values |
| --- | --- |
| `not_started` | kind, root, dispatch, run reference, target, evidence, and reviewed commit null; round 0; both arrays empty. |
| `review_active` | kind, root, dispatch, run reference, target, and evidence present; reviewed commit null; round and arrays describe completed returns for this kind/root. |
| `changes_required` | `review_active` fields; round at least 1; open IDs nonempty; reviewed commit is required only for implementation and otherwise null. |
| `pass` | `review_active` fields; open IDs empty; reviewed commit is required only for implementation and otherwise null. |
| `blocked` | kind and root present; dispatch/evidence fields are either all null for a pre-dispatch block or all present for a returned/capped review; reviewed commit is required only for a returned implementation review and otherwise null. |

Starting a different review kind creates a fresh current review object at round
0 with empty arrays and a new kind/root. Earlier review evidence remains in the
transition history; the current head does not prove that historical transition.
Only review-loop owns review target seals.

| Term | Meaning | Validator |
| --- | --- | --- |
| Candidate input identity | SHA-256 of exact uncommitted spec/plan candidate bytes | Feature Forge adapter |
| Review target seal | Seal for review-loop materialized target | review-loop only |
| Frozen identity | canonical path plus Git blob | ff-check identities |
| Reviewed implementation commit | source HEAD reviewed by the current returned implementation review | ff-check audit/reviewed-snapshot |
| Implementation source snapshot | SHA-256 seal of every reviewed source path, type, mode, and content except the mutable ledger, reserved receipt, and stage-owned final report | ff-check implementation-snapshot/reviewed-snapshot |

These identities are not interchangeable; Feature Forge cannot derive a review
target seal from a source commit. A human transition row records `event`,
`parent event`, UTC time, from/to, next action, session provenance,
reason/authority, and evidence. Session provenance records the harness, current
conversation/session ID, and root, parent, or subagent identity when materially
different and exposed.

Material dispatches, returns, corrections, authority decisions, invalidations,
and Finish transitions record the harness and available conversation/session
identity, plus any materially different root, parent, or subagent identity; use
the explicit value `unavailable` when the harness exposes none. A consistent
resume validates the ledger, Git, checker results, review evidence, and
transition evidence without depending on transcripts.

Only a mismatch enters transcript-assisted recovery. Identify the transition
entries and sessions since the last consistent event and inspect only as much
linked transcript evidence as needed. Reconcile read-only only when the ledger,
Git, checker, review, authority, and transcript evidence are unambiguous;
otherwise block for user authority. Transcripts are forensic evidence, never
workflow authority or checker input. Missing, inaccessible, or ambiguous
transcripts do not invalidate an otherwise consistent run, but block when they
are needed to resolve the mismatch.

Stage states are `pending | active | blocked | complete | invalidated`. Review
states are `not_started | review_active | pass | changes_required | blocked`.
The ledger names exactly one next permitted action except at a terminal state.
`review_active` permits only **await or recover the existing review**; it does
not permit target, ledger, downstream-stage, or new-review mutation.

Outside the head, the ledger records only human evidence: intent, authority,
execution mode, acceptance and verification evidence, blockers/change requests,
the implementation table, and the Finish journal (`finish_id`, phase, selected
choice and authority, base/feature tips, worktree, exact next side effect,
completed side-effect receipts, and durable phase receipts). Review round and
finding-ID fields are the exception: they are checker-consumed control state in
the head, with opaque IDs only and no finding prose.

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
pass on the post-fix snapshot. Preserve the TRIAGE outcome and open finding
IDs, stable run reference, stage charter, completion criterion, and content
seal for every review.

Persist a complete ledger update before each external dispatch and immediately
after each return. A transition-log row has event ID, parent event, UTC time,
from/to state, sole next permitted action, session provenance,
reason/authority, and evidence reference. A missing recorded return is
recovered from its referenced dispatch before re-dispatch.

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
affected stage and its dependents, then resumes at the root cause's correction
stage — the Resume point named in the fixed graph below — before its dependents. An unrelated dirty path blocks advancement; attributable changes must be
reconciled under the relevant stage and checkpoint rule.

For a verified frozen-identity `fail`, immediately record safe-return
bookkeeping without resolution authority: preserve `HEAD` and the frozen
artifact, with no restore, commit, advance, or dispatch; set run status
`blocked` and the current stage `blocked`; make the sole next action explicitly
reconcile or correct the exact checker-reported canonical path; and append a
reconciliation/correction material transition with a reason that explains the
identity/blob drift, evidence containing the exact path, ledger-recorded frozen
blob, and read-only SHA-256 of the current bytes, and session provenance or
explicit `unavailable`. Judge the reason semantically; do not require fixed
wording. The safe blocked state and absence of forward mutation establish lack
of resolution authority; that fact may be recorded outside the reason cell. A
later correction/invalidation requires applicable authority.

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
5. Implementation commits owned by each reviewed plan task and the selected execution method.
6. `fix: address final <feature> review findings` when Implementation review changes implementation.
7. `docs: record <feature> acceptance` for the final report, UAT/waiver, verification
   summary, traceability, branch-finishing readiness, the pending Finish outcome, and
   the active Stage 13 ledger.
8. `docs: record <feature> finish` whenever tracked Stage 14 state differs: the
   `claimed` commit, the `menu_pending` commit before menu delivery or unattended
   resolution, the atomic `choice_recorded`-then-`executing` commit before the first
   effect, one `executing` write-ahead commit before each later effect, one reconciled
   receipt commit after each effect, and the atomic terminal-or-blocked commit. The
   `blocked` overlay may also commit from any nonterminal phase — including the
   `ready -> blocked` capability-gate outcome before `claimed`.

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

- **Goal:** Select exactly one canonical run in an isolated non-primary worktree.
- **Inputs:** Repository, bounded intent, requested run ID, invocation mode, Git state, and configured review host.
- **Mechanical check:** Run `runs`; if it reports one existing nonterminal run, run `identities` before resuming it.
- **Owned action:** Record `supervised` when mode is omitted; resolve the collision inventory by mode and intent; inventory dirt; create or reuse the isolated worktree and ledger; project all stages. Resume a same-ID run only when intent and identities match. Otherwise interactive/supervised mode asks resume-versus-new; unattended mode selects the lowest unused numeric suffix only when the intents are clearly distinct and blocks when ambiguous. Validate that the authorized review host can import `review_loop.controller.Controller`, construct its contained dispatchers/strict validators, and write a disjoint run root; a CLI probe alone is insufficient. Interactive/supervised mode asks for an authorized host when none is configured; unattended mode blocks when none is pre-authorized.
- **Pass:** Git/worktree/branch, mode, collision decision, runner capability, and dirty-path reconciliation are recorded with one next action; either a no-collision run is created or one matching run is resumed.
- **Failure:** A verified `fail` routes an identity/collision mismatch to read-only reconciliation and the mode's user decision, never implicit selection; `unverifiable`, unavailable authority/runner, foreign dirt, non-Git state, or failed isolation blocks here.
- **Next:** Stage 2: Brainstorm.

### Stage 2: Brainstorm

- **Goal:** Produce one initial canonical specification under the bounded intent.
- **Inputs:** Preflight evidence, intent and authority records, canonical specification path, and the `brainstorm-return` contract.
- **Mechanical check:** Run `identities` at entry and `audit` after recording the bounded return.
- **Owned action:** Dispatch or perform `brainstorm-return`, write and self-review the specification, obtain applicable approval, and create the draft-specification checkpoint when changed.
- **Pass:** The specification, self-review/approval, checkpoint when needed, return evidence, and one next action are recorded.
- **Failure:** A verified `fail` routes identity drift through read-only reconciliation/invalidation; `unverifiable` blocks. An incomplete return remains here for recovery and missing authority blocks.
- **Next:** Stage 3: Harden.

### Stage 3: Harden

- **Goal:** Make the one specification decision-complete without widening the work unit.
- **Inputs:** Initial specification, durable intent, repository facts, and authority contract.
- **Mechanical check:** Run `identities`; there is no content checker.
- **Owned action:** Apply decision-tree hardening and integrate settled decisions, assumptions, authority, and acceptance consequences into the same specification.
- **Pass:** The hardening record shows an empty prerequisite-ready frontier and no unresolved question ready to ask.
- **Failure:** A verified `fail` routes identity drift through read-only reconciliation/invalidation; `unverifiable` blocks. Missing authority or an irresolvable contradiction also blocks.
- **Next:** Stage 4: Candidate gate.

### Stage 4: Candidate gate

- **Goal:** Establish one coherent, bounded, testable specification candidate.
- **Inputs:** Hardened specification, empty decision frontier, assumptions, and applicable approval.
- **Mechanical check:** Run `identities`; there is no content checker.
- **Owned action:** Verify `Open questions` and the frontier are empty, delegated assumptions and acceptance classifications are complete, and approval exists.
- **Pass:** Candidate-gate evidence records the exact candidate and one next action.
- **Failure:** A verified `fail` routes identity drift through read-only reconciliation/invalidation; `unverifiable` blocks. A resolvable omission returns to Harden; missing authority or material ambiguity blocks.
- **Next:** Stage 5: Specification review.

### Stage 5: Specification review

- **Goal:** Obtain an independently reviewed pass on the exact specification candidate.
- **Inputs:** Candidate-gate evidence, candidate bytes/identity, specification charter, review host, and current review control state.
- **Mechanical check:** Run `identities` then `audit` immediately before every external review dispatch; run `audit` again after mapping a returned receipt.
- **Owned action:** Execute the read-only review lifecycle in `adapters-and-reviews.md`, persisting `review_active` before semantic dispatch and applying its bounded review return rule.
- **Pass:** A valid receipt and head record `pass` for the unchanged candidate identity, with run reference and review-loop-owned target seal.
- **Failure:** A verified `fail` follows read-only reconciliation or the bounded correction/invalidation route; `unverifiable` blocks. While `review_active`, only await or recover; `changes_required` returns to the minimum specification correction stage and `blocked` remains here.
- **Next:** Stage 6: Specification freeze.

### Stage 6: Specification freeze

- **Goal:** Freeze exactly the specification bytes that passed review.
- **Inputs:** Passing specification receipt, unchanged candidate identity, canonical path, and Git worktree.
- **Mechanical check:** Run `identities` before freezing, then run `identities` immediately after recording the frozen blob and `audit` after the ledger update.
- **Owned action:** Commit the reviewed specification and record its canonical path and Git blob as the frozen baseline.
- **Pass:** The freeze checkpoint, matching blob identity, transition evidence, and one next action are durable.
- **Failure:** A verified `fail` routes seal/identity drift through read-only reconciliation and the invalidation graph; `unverifiable` or Git failure blocks.
- **Next:** Stage 7: Plan.

### Stage 7: Plan

- **Goal:** Produce a self-reviewed implementation plan faithful to the frozen specification.
- **Inputs:** Frozen specification identity, canonical plan path, repository contracts, and `plan-return` contract.
- **Mechanical check:** Run `identities` at entry and `audit` after recording the bounded return.
- **Owned action:** Execute `plan-return`, preserving frozen plan checkboxes and placing execution progress only in the ledger; create the draft-plan checkpoint when changed.
- **Pass:** The canonical plan, self-review, checkpoint when needed, return evidence, and one next action are recorded.
- **Failure:** A verified `fail` routes specification drift through read-only reconciliation/change control; `unverifiable` blocks. An incomplete return remains here for recovery.
- **Next:** Stage 8: Plan review.

### Stage 8: Plan review

- **Goal:** Independently review and freeze the exact implementation plan candidate.
- **Inputs:** Self-reviewed plan candidate/identity, frozen specification, plan charter, review host, and current review control state.
- **Mechanical check:** Run `identities` then `audit` immediately before every external review dispatch; run `audit` after mapping the return, then run `identities` and `audit` after freeze state is recorded.
- **Owned action:** Execute the read-only review lifecycle and bounded return rule; after pass, commit the unchanged candidate and record its canonical Git blob.
- **Pass:** The valid passing receipt, freeze-plan checkpoint, matching frozen identity, and one next action are durable.
- **Failure:** A verified `fail` follows read-only reconciliation or the bounded correction/invalidation route; `unverifiable` blocks. While `review_active`, only await or recover; `changes_required` returns to Plan and a specification defect follows the fixed graph.
- **Next:** Stage 9: Implement.

### Stage 9: Implement

- **Goal:** Complete every frozen plan task as committed, locally verified implementation.
- **Inputs:** Frozen specification and plan identities, implementation table, execution authority, and `execute-return` contract.
- **Mechanical check:** Run `identities` at entry and `audit` after each bounded execution return is recorded.
- **Owned action:** Select exactly one authorized execution mode, execute independently bounded tasks, and record each task's status, owned commit, and evidence without changing plan checkboxes.
- **Pass:** Every plan-task row has a verified commit/evidence record and implementation content is committed with one next action.
- **Failure:** A verified `fail` routes specification/plan drift through read-only reconciliation and the fixed graph; `unverifiable` or unavailable execution authority blocks. Recover a missing return before redispatch.
- **Next:** Stage 10: Implementation review.

### Stage 10: Implementation review

- **Goal:** Obtain a final independent pass on the clean committed implementation snapshot.
- **Inputs:** Frozen authorities, implementation table/commits, whole-tree subject, implementation charter, review host, and review control state.
- **Mechanical check:** Run `identities` then `audit` immediately before every external review dispatch; run `audit` again after mapping a returned receipt.
- **Owned action:** Execute the read-only review lifecycle and bounded return rule; fix only between fresh sealed rounds, commit accepted fixes, and re-review the post-fix snapshot.
- **Pass:** The receipt/head record `pass`, the reviewed implementation commit, target seal, run reference, and unchanged frozen identities.
- **Failure:** A verified `fail` follows read-only reconciliation or the fixed correction/invalidation route; `unverifiable` blocks. While `review_active`, only await or recover; implementation findings start a fresh round and exposed specification/plan defects follow the graph.
- **Next:** Stage 11: Final verification.

### Stage 11: Final verification

- **Goal:** Produce fresh deterministic evidence for the unchanged reviewed snapshot.
- **Inputs:** Passing implementation receipt, reviewed commit, frozen identities, permitted ledger/evidence delta, and verification commands.
- **Mechanical check:** Run `identities`, then `reviewed-snapshot`, then `audit` before verification.
- **Owned action:** Confirm the reviewed commit and sealed paths remain unchanged, compare recorded review evidence, and run fresh risk-proportionate checks.
- **Pass:** Commands/results, reviewed commit, matching identities/seal evidence, and clean verification evidence are recorded.
- **Failure:** A verified `fail` routes drift or a verification defect to read-only reconciliation and its specification/plan/implementation root; `unverifiable` or an unavailable required environment blocks.
- **Next:** Stage 12: Acceptance.

### Stage 12: Acceptance

- **Goal:** Decide every requirement/scenario using its declared acceptance method and current evidence.
- **Inputs:** Frozen specification acceptance contract, current verification evidence, reviewed commit, UAT authority/fallbacks, and acceptance table.
- **Mechanical check:** Run `identities`, then `reviewed-snapshot`, then `audit` before acceptance.
- **Owned action:** Execute each declared method and record its state, authority, evidence, and fallback without inventing human UAT.
- **Pass:** Every required behavior has current reproducible evidence, its required authority, and no open material defect.
- **Failure:** A verified `fail` routes identity/review drift or rejection through read-only reconciliation and root-cause classification; `unverifiable`, infeasible required acceptance, or missing authority blocks.
- **Next:** Stage 13: Report.

### Stage 13: Report

- **Goal:** Persist a traceable final report and a ready, not-yet-started Finish operation.
- **Inputs:** Complete acceptance table, verification evidence, implementation traceability, final-report template, ledger, and clean feature worktree.
- **Mechanical check:** Run `identities`, then `reviewed-snapshot`, then `audit` before writing the report.
- **Owned action:** Write the canonical report; allocate one stable `finish_id`; record Finish `ready` and outcome pending; commit report/ledger through checkpoint 7 while the run stays active; restore a clean worktree.
- **Pass:** Checkpoint 7 contains report and ledger, stable `finish_id`, phase `ready`, active status, clean worktree, and sole next action `claim <finish_id>`.
- **Failure:** A verified `fail` routes stale identity/review evidence through read-only reconciliation and its root cause; `unverifiable` blocks. Incomplete evidence returns to Acceptance/root cause and a dirty tree blocks.
- **Next:** Claim `<finish_id>` at Stage 14: Finish.

### Stage 14: Finish

- **Goal:** Complete or durably block the one logical Finish operation without repeating an external effect.
- **Inputs:** Report/checkpoint 7, stable `finish_id`, phase/journal receipts, selected mode authority, Git/forge observations, and clean applicable worktree.
- **Mechanical check:** At Stage 14 entry before the first integration effect, run `identities`, then `reviewed-snapshot`, then `audit`; after an effect, recover from the Finish journal instead of reinterpreting topology through these gates.
- **Owned action:** Perform the LLM-executed capability probe, then drive the protocol below one write-ahead side effect at a time. Do not invoke `superpowers:finishing-a-development-branch`.
- **Pass:** A category 8 terminal commit records durable outcome evidence, phase `terminal`, overall status `complete`, and no next action.
- **Failure:** A verified `fail` before the first effect routes implementation/review drift through read-only reconciliation/invalidation or foreign dirt to blocking; `unverifiable`, a failed capability probe, unreconcilable checkout, unresolved menu, or ambiguous recovery records the resumable blocked overlay and performs no unrecorded effect.
- **Next:** Terminal; none after `terminal`/`complete`.

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

At `ready`, before the `claimed` category-8 commit, the workflow performs a
mandatory harness-capability check for durable journal interleaving (can the
harness durably commit the journal between menu selection and each side effect)
and read-only Git/forge reconciliation (can it read Git
and, for Push-and-PR, forge state without mutating either). If either capability is
unavailable, the workflow records `ready -> blocked` under category
8, with prior phase `ready`, evidence of the missing capability, and a
resolution-only next action. It performs no claim, no menu presentation, no
unattended resolution, and no external effect. Only after that capability check
passes may it commit `claimed` in category 8.

### `claimed` through `executing`

Under the same `finish_id`, once `claimed` is committed, run the fresh full test
suite, detect the Git/common-directory and worktree state, check for a named branch,
and determine the base branch. Commit `menu_pending` in category 8 before the interactive/supervised
menu presentation or before unattended resolution:

- Interactive/supervised: the `menu_pending` receipt records the exact three
  choices and a stable presentation ID.
- Unattended: the `menu_pending` receipt instead records the named pre-authorization
  when present, or `agent:unattended default-keep` when none is pre-authorized,
  before resolution.

The choices are exactly local merge to confirmed base, Push-and-PR, and Keep
branch/worktree — no other or reduced choice set. A detached HEAD or another
environment that cannot retain all three installed choices records `blocked`
under category 8 with the missing-capability evidence and a resolution-only
next action, rather than presenting a reduced menu.

Before the first side effect, commit a complete category-8 update that records
`choice_recorded` then current `executing` atomically: selected choice, authority,
confirmed base, base/feature tips, worktree, environment evidence, and the exact
next side effect. Thereafter, reconcile and receipt each completed effect before
committing the next exact side effect. `push` and `create PR` are separate side
effects; so are every pull, merge, cleanup, and branch deletion. Each write-ahead
commit must succeed and the applicable worktree must be clean before its effect.

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
commits record the controller-owned operation; they are not callbacks around another
skill.

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
  effect whose non-occurrence is provable. A proven absent effect remains
  `executing`: perform it, reconcile it, append its receipt, and either record the
  next effect or terminalize only when the selected outcome is proven complete.
- Recovery must never repeat a claim, menu presentation, merge, pull, push, PR
  creation, cleanup, or branch deletion.
- If an external effect may have occurred but cannot be identified conclusively,
  atomically persist `blocked` under category 8 recording the ambiguity, evidence,
  **the prior phase it interrupted** (for example `executing`), and no executable
  next side effect — never guess or repeat it.
- If the selected outcome is conclusively proven complete, recovery writes the
  terminal receipt (phase `terminal`, overall run `complete`, no next action) in one
  atomic category 8 ledger/report transaction, on the correct preserved location:
  the base checkout for local merge, or the preserved feature branch/worktree for
  Push-and-PR and Keep. Proof that the recorded effect is absent is never terminal
  evidence.
