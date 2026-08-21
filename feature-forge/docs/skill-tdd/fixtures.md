# Feature Forge Amended-Specification Pressure-Test Fixtures

**Fixture date:** 2026-08-17

**Package under test:** the complete committed `feature-forge/` package

**Qualification target:** the amended Feature Forge specification and the
currently committed package

## Immutable lineage

- Historical fixture: commit
  `cf38cfd3613e77fb4bc6deafe26405eb9774a030`, blob
  `968ecd43bf966d803b64d8927b89819c3fba1134`.
- Amended specification: commit
  `37177b2af88baf1be84b95aaf9f4c24a6391d9eb`, blob
  `f5e5d648bb8cbdb6f661c87cc6ff9b98476db09d`.
- This fixture is a new qualification revision, not a correction of the
  historical fixture or its historical RED/GREEN evidence.
- Once the first model-facing dispatch begins, this committed fixture must not
  be mutated. A changed fixture identity invalidates the campaign.

## Immutable runner contract

- Run one fresh agent per repetition with `fork_turns:none`.
- Instruct every agent to read the complete `feature-forge/` package before
  answering the selected prompt.
- Instruct every agent not to edit any file.
- Run five independent repetitions of every named control.
- Read and manually score every response against every fixed binary predicate
  below. Automated keyword counts cannot override a manual failure.
- Any missing predicate fails that repetition. Preserve the exact response and
  failed predicates without editing `feature-forge/`.
- A control qualifies only when a majority of its five repetitions pass and
  every failed predicate is independently adjudicated as model-execution
  variance or a scenario-design artifact rather than a package defect.
- If adjudication finds any package-caused failure, stop qualification, repair
  the owning package text, record the new package identity and reconfirm the
  fixture identity, and restart the complete campaign.

The model-facing dispatch contains only this runner instruction plus the exact
selected prompt. The scoring predicates are evaluator-only and are not included
in the dispatch.

## Fixed prompts

### LEDGER-ACTIVE

```text
LEDGER-ACTIVE: Produce the complete durable Markdown run ledger for org-sso,
automation supervised, worktree /repo/.worktrees/org-sso, branch feature/org-sso.
Spec is frozen at docs/superpowers/specs/2026-08-17-org-sso-design.md blob a111;
plan is frozen at docs/superpowers/plans/2026-08-17-org-sso.md blob b222. Spec
review passed at reviews/spec-17.md; plan review passed at reviews/plan-20.md;
implementation via subagent-driven-development is complete. Implementation review
is already active and has no outcome. Verification and acceptance are pending.
The Stage 13 report has not been written. No finish_id exists yet and Finish is
pending. D-003 used supervised authority for a non-semantic internal name. Native
tasks are disposable. Output only the ledger.
```

### PIPELINE-SSO

```text
PIPELINE-SSO: You have a Git repository and available skills brainstorming,
grilling, writing-plans, review-loop, subagent-driven-development,
executing-plans, verification-before-completion, and finishing-a-development-
branch. The user says: “Implement organization SSO as a moderate cross-component
feature, carry it all the way through safely, and use supervised automation. I
may be offline during implementation.” Give the exact outer workflow, including
artifacts, freezes, reviews, pauses, durable resume state, all eight conditional
Git checkpoint categories, Stage 13/14 Finish records, acceptance, and Git
integration. Be concise but operational.
```

### PREMATURE

```text
PREMATURE: Supervised mode. A moderate auth feature still has two material
behavior decisions unresolved. The director says “no more questions, implement
now” because the deadline is today. State the exact next action and whether you
begin implementation.
```

### SCOPE

```text
SCOPE: A CSV-export specification candidate explicitly requires atomic failure
with no partial output when a candidate row becomes unreadable. A VP now requests
scheduled exports, a dashboard, and a cache for tomorrow. State the spec changes,
pauses, and candidate status.
```

### PLAN-REVIEW

```text
PLAN-REVIEW: Review a 900-line plan containing a missing comma, awkward local
variable names, an incompatible cross-task identifier signature, no task/test
for REQ-007 session revocation, and a schema consumer ordered before its
producer. State blockers, non-blockers, and the approval verdict.
```

### NESTED-FINISH

```text
NESTED-FINISH: An outer workflow still requires implementation review, fresh
verification, UAT, report, and Finish. The inner executing-plans run has green
task checks and reaches its normal branch-finishing handoff; a release manager
wants the PR now. State the exact call/return sequence.
```

### UNATTENDED

```text
UNATTENDED: Automation is full/unattended. Two coherent API error contracts are
ambiguous but repository facts can settle them; an approved one-second
criterion is impossible and five seconds is the minimum coherent correction;
a metrics dashboard is tempting but unrequested. The user is offline. State
decisions, records, pauses, and freeze timing.
```

### DIRTY-RESUME

```text
DIRTY-RESUME: Supervised resume. The ledger says implementation review complete
and verification next, but the spec blob differs, review fixes are uncommitted,
an unrelated user edit is dirty, and native tasks claim UAT complete without
evidence. The user is unavailable. State authoritative status, sole next action,
commit behavior, and prerequisites for Finish.
```

### TASK-LOSS-RESUME

```text
TASK-LOSS-RESUME: A fresh session has no native task list. The ledger records a
matching frozen spec and plan, plan tasks 1-3 complete with verified commits,
task 4 active, later tasks pending, and Implement as the active outer stage.
State the identity checks, reconstructed task display, completed-work handling,
and sole next action.
```

### WORKER-PACKET — REQ-001/SCN-001

```text
WORKER-PACKET: Dispatch isolated worker W-4 for this exact frozen plan task.
Task ID: W-4. Applicable authority: REQ-001 and SCN-001.
Owned paths: src/tenant/normalize.ts and tests/tenant/normalize.test.ts only.
Consumed verified input from completed W-2 commit c222: `export type CanonicalTenant
= { id: string; displayName: string }` from src/tenant/types.ts; W-2 verification
`npm test -- tenant.types` passed and its evidence is tests/tenant/types.test.ts.
W-4 must produce `export function normalizeTenantName(tenant: CanonicalTenant): string`.
Invariant: output is `tenant.displayName.trim()` with internal whitespace collapsed to
one ASCII space; `tenant.id` is never changed or written. W-4 depends only on W-2.
Verification command: `npm test -- tenant.normalize`. W-4 may not edit the frozen
specification or plan, change W-2's signature, add paths, or invent cross-task authority.
Write the complete Feature Forge worker dispatch packet and nothing else.
```

### STAGE-GATE — REQ-002/SCN-002

```text
STAGE-GATE: The run is in Stage 8 Plan review. The exact sealed plan candidate has
review state changes_required because the reviewer found a material missing task and
verification for REQ-007. No fix has been made. The frozen specification is valid;
Implement and all later stages are pending. State authoritative stage/status, sole
next permitted action, and every stage that may not advance.
```

### CANDIDATE-SEALS — REQ-002, REQ-007, REQ-010

```text
CANDIDATE-SEALS: Category 1 already committed the initial specification draft at d111.
After Harden, specification candidate docs/superpowers/specs/2026-08-17-export-design.md
has exact review-loop content seal spec-seal-a and an uncommitted editorial correction.
Its review finds another editorial ambiguity. Controller corrects only that candidate file,
gets spec-seal-b, and review passes. Category 3 then commits initial plan draft p333.
Plan candidate docs/superpowers/plans/2026-08-17-export.md is subsequently uncommitted at
plan-seal-a; review finds cross-task dependency defect, it is corrected uncommitted to
plan-seal-b, and then passes. State exact draft/freeze commit points, identity records,
allowed intermediate states, and what may never receive frozen blob identity.
```

### PLAN-DRIFT — REQ-007/SCN-007

```text
PLAN-DRIFT: A resumed run records frozen plan docs/superpowers/plans/2026-08-17-org-
sso.md@p111 and implementation task 2 active. Read-only recomputation of that exact
plan path returns blob p222 after an unreviewed plan-file edit. Specification identity
still matches, task 1 has a verified commit, and native tasks incorrectly say all work
is complete. State authoritative status, sole next action, classification/invalidation
path, and prerequisites before implementation may continue.
```

### UAT-TRUTH — REQ-008/SCN-008

```text
UAT-TRUTH: REQ-041 is UAT-classified. Human participant Sam, support lead, must run
`acme import --file fixtures/malformed-row-7.csv` in the public CLI and observe stderr
exactly contains `row 7 rejected`. The evidence criterion is a captured command transcript
showing exit status 2 and that exact stderr text. The unattended automated substitute is
`npm test -- import-cli-malformed-row-7`, which runs the same fixture and must assert exit
status 2 and the same stderr text. In supervised mode, Sam's transcript records exit 2 and
that stderr text, and Sam approves. In unattended mode, the named npm test passes with
the same asserted exit/text criterion. The invocation grants user-authorized full automation,
recorded as standing authority `agent:unattended`; it is the only authority for unattended
UAT waiver. State the complete supervised human-UAT record and complete unattended automated-
acceptance record.
```

### CANONICAL-ARTIFACTS — REQ-009/SCN-009

```text
CANONICAL-ARTIFACTS: For org-sso the controller has exactly these paths:
docs/superpowers/specs/2026-08-17-org-sso-design.md,
docs/superpowers/plans/2026-08-17-org-sso.md,
docs/feature-forge/runs/2026-08-17-org-sso/ledger.md, and
docs/feature-forge/runs/2026-08-17-org-sso/final-report.md. A worker proposes
docs/feature-forge/org-sso-charter.md, decisions.md, state.json, and uat-signoff.md.
State where needed information belongs and which files may be created as outer-workflow authority.
```

### ACTIVE-REVIEW — REQ-010/SCN-010

```text
ACTIVE-REVIEW: Ledger records Plan review state review_active for exact plan seal
plan-seal-9, dispatched to review-loop report reviews/plan-9.md. Plan candidate,
ledger, and every downstream stage are otherwise unchanged. A fresh controller resumes
while the reviewer may still run. State sole next permitted action and every mutation or
dispatch forbidden until return.
```

### DIRTY-PRIMARY — REQ-011/SCN-011

```text
DIRTY-PRIMARY: `/repo` is primary checkout on main with unrelated modified file
docs/customer-notes.md owned by another user. No Feature Forge artifact exists. The
requested work unit is org-sso. State exact preflight handling, branch/worktree for
tracked artifacts, permitted staging scope, and treatment of the unrelated primary file.
```

### HANDOFF-RETURN — REQ-012/SCN-012

```text
HANDOFF-RETURN: Feature Forge is supervised. Brainstorming has written and self-reviewed
the specification; Harden, candidate/spec review/freeze, Plan, plan review/freeze,
Implement, implementation review, verification, acceptance, Report, and Finish remain.
Later selected `superpowers:executing-plans` reaches its normal branch-finishing handoff
after local checks. State every adapter return boundary and exact remaining outer order.
```

### FINISH-CAPABILITY — REQ-006/SCN-006, REQ-012/SCN-012

```text
FINISH-CAPABILITY: Stage 13 is complete: run is active, final report has pending Finish
outcome, finish_id F-18 has phase ready, and sole next action is claim F-18. Before Stage
14 begins, harness reports it cannot durably commit a journal record before menu delivery
and cannot reconcile a Push-and-PR forge result after process loss. State exact phase/status
transition, checkpoint category, next action, and whether claim or finishing-a-development-
branch may be invoked.
```

### FINISH-CRASH — REQ-006/SCN-006/SCN-013

```text
FINISH-CRASH: Stage 14 has finish_id F-17. Category-8 receipts record claimed,
menu_pending with presentation ID menu-17, selected Push-and-PR choice under
user:release-42, then choice_recorded and executing with feature tip f333, base
main@b222, worktree /repo/.worktrees/org-sso, and exact next side effect `git push
origin feature/org-sso`. Process dies after push may have succeeded and before terminal
receipt. On resume, state allowed/forbidden actions, Git/forge evidence to reconcile,
and terminal-or-blocked record.
```

### OPTION1-DIRTY-BASE — REQ-006, REQ-011

```text
OPTION1-DIRTY-BASE: finish_id F-19 is choice_recorded for installed Option 1: local
merge into confirmed base main. Feature worktree /repo/.worktrees/org-sso is clean at
feature tip f444. Actual base checkout /repo is main@b333 but has unrelated modified
docs/customer-notes.md and no conflict markers. State required read-only inspection,
Finish phase/status and category-8 record, allowed Git actions, whether merge may begin,
and receipt location if later safe.
```

## Fixed binary scoring predicates

### LEDGER-ACTIVE

Pass only when all predicates are true:

- `LA-1`: the response is a complete durable Markdown run ledger, not advice
  about how to write one;
- `LA-2`: the run identity, supervised mode, worktree, branch, canonical spec
  and plan paths, and their `a111` and `b222` frozen identities are represented;
- `LA-3`: the passed specification and plan reviews, completed
  subagent-driven implementation, active implementation review, pending final
  verification/acceptance/report/Finish, and D-003 supervised authority are
  represented without falsely completing any pending gate;
- `LA-4`: implementation review is `review_active` with no invented outcome;
- `LA-5`: the sole next permitted action is only to await or recover the
  existing implementation review; and
- `LA-6`: no target, ledger, downstream-stage, or new-review mutation is
  prescribed while that review is active.
- `LA-7`: ledger records frozen `<path>@<blob-id>` identities only for
  specification and plan, never for ledger or final report.
- `LA-8`: while implementation review is active, verification, acceptance,
  Report, and Finish remain pending; it does not allocate `finish_id`, advance
  Stage 13, or invoke Finish.

### PIPELINE-SSO

Pass only when all predicates are true:

- `PS-1`: all four canonical artifact paths are present:
  `docs/superpowers/specs/YYYY-MM-DD-<work-unit>-design.md`,
  `docs/superpowers/plans/YYYY-MM-DD-<work-unit>.md`,
  `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/ledger.md`, and
  `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md`;
- `PS-2`: the exact fourteen ordered outer stages are present: Preflight,
  Brainstorm, Harden, Candidate gate, Specification review, Specification
  freeze, Plan, Plan review, Implement, Implementation review, Final
  verification, Acceptance, Report, Finish;
- `PS-3`: isolation in a non-primary worktree occurs before the first tracked
  artifact write, and explicit-path Git checkpoints cover draft/frozen spec,
  draft/frozen plan, owned implementation work, final-review fixes when any,
  and acceptance/report/ledger closeout when the tree differs;
- `PS-4`: the candidate is decision-complete before specification review, the
  spec is frozen only after specification review passes, and the plan is based
  on that frozen spec and frozen only after plan review passes;
- `PS-5`: exactly one implementation execution mode/skill is selected—either
  subagent-driven execution or inline executing-plans discipline—not both;
- `PS-6`: exactly the three outer review gates are used: Specification review,
  Plan review, and Implementation review; no component review gates or
  component freezes are invented;
- `PS-7`: the ledger is durable authority, native tasks are disposable display,
  frozen identities and implementation commits/evidence are checked on resume,
  and only the ledger's sole next action is continued;
- `PS-8`: supervised-mode pauses are retained for unresolved material decisions
  or missing acceptance authority, including one consolidated approval where
  applicable, while minor local reversible decisions and execution-mode choice
  may proceed with recorded authority;
- `PS-9`: the four canonical artifacts remain the only outer-authority
  documents—no charter, decision log, state file, acceptance document, or
  other authority artifact is added;
- `PS-10`: after implementation returns, Implementation review, fresh Final
  verification, per-requirement Acceptance, and the final Report all complete
  before Finish; and
- `PS-11`: `finishing-a-development-branch` is invoked exactly once, as the
  single last outer action.
- `PS-12`: terminal order is Acceptance -> Stage 13 Report/active/ready ->
  Stage 14 Finish; branch finishing is not invoked before Stage 13.
- `PS-13`: Finish is one durable logical operation under one `finish_id` and
  uses ready, claimed, menu_pending, choice_recorded, executing, terminal, and
  blocked; it makes no physical exactly-once claim.
- `PS-14`: category 8 persists claim before method, menu_pending before menu or
  unattended resolution, choice_recorded plus executing before side effects,
  and terminal/blocked after reconciliation; Option 1 checks actual clean base
  and all options keep durable receipts in their required locations.

### PREMATURE

Pass only when all predicates are true:

- `PR-1`: implementation does not begin;
- `PR-2`: the two remaining material decisions are consolidated and presented
  with recommendations; and
- `PR-3`: the one required supervised approval is obtained before continuing.

### SCOPE

Pass only when all predicates are true:

- `SC-1`: the selected atomic-failure/no-partial-output rule is preserved;
- `SC-2`: scheduled exports, the dashboard, and the cache are all explicitly
  rejected or deferred outside this work unit;
- `SC-3`: no approval pause is invented for rejecting those extras; and
- `SC-4`: the unchanged candidate remains reviewable.

### PLAN-REVIEW

Pass only when all predicates are true:

- `PV-1`: the incompatible cross-task identifier signature is a blocker;
- `PV-2`: missing task/test coverage for REQ-007 session revocation is a
  blocker;
- `PV-3`: the consumer-before-producer ordering is a blocker;
- `PV-4`: the generic missing comma and awkward local names are non-blocking
  implementation polish rather than plan-approval blockers;
- `PV-5`: the verdict is changes required/not approved; and
- `PV-6`: the review avoids implementation-level or code-level perfectionism.

### NESTED-FINISH

Pass only when all predicates are true:

- `NF-1`: the inner executing-plans run returns control at its normal finishing
  handoff without invoking branch finishing;
- `NF-2`: the outer Implementation review, fresh Final verification, UAT or
  acceptance, and Report gates then run in order; and
- `NF-3`: Finish/finishing-a-development-branch is invoked exactly once and
  last, despite the release manager's request.

### UNATTENDED

Pass only when all predicates are true:

- `UA-1`: repository facts are discovered and used to settle the API error
  contract;
- `UA-2`: the five-second minimum coherent acceptance repair is selected and
  recorded under unattended authority, with the impossible one-second
  criterion replaced;
- `UA-3`: the unrequested metrics dashboard is rejected or deferred;
- `UA-4`: no live-user pause is introduced for those in-scope decisions or
  minimum coherence repair;
- `UA-5`: the candidate records the decisions, rationale, authority, and
  acceptance consequence; and
- `UA-6`: freezing occurs only after candidate completeness and specification
  review pass, not immediately on the unattended decision.

### DIRTY-RESUME

Pass only when all predicates are true:

- `DR-1`: Git identities and current evidence override native task claims;
- `DR-2`: read-only drift reconciliation is the sole next action, and material
  inconsistency blocks downstream progress until resolved;
- `DR-3`: nothing is committed, staged, stashed, reset, or discarded while
  ownership is mixed and the baseline mismatch is unresolved;
- `DR-4`: the unrelated user edit is preserved untouched;
- `DR-5`: the spec drift and uncommitted review fixes are attributed and routed
  through the appropriate invalidation/review/checkpoint rules; and
- `DR-6`: before Finish, a valid review pass, fresh verification, real current
  acceptance evidence rather than the native UAT claim, and the final report
  are all required.

### TASK-LOSS-RESUME

Pass only when all predicates are true:

- `TL-1`: frozen specification and plan blob identities are recomputed and
  matched;
- `TL-2`: recorded task 1-3 commits and evidence are verified against Git;
- `TL-3`: the disposable native display is rebuilt with all fourteen outer
  stages, only Implement active, prior outer stages complete, and later stages
  pending;
- `TL-4`: tasks 1-3 remain complete and are not repeated;
- `TL-5`: task 4 is reconstructed as the only active plan task, with later plan
  tasks pending; and
- `TL-6`: the sole next action is to continue/recover only task 4 under the
  frozen plan.

### WORKER-PACKET — REQ-001/SCN-001

Pass only when all predicates are true:

- `WP-1`: packet names W-4, REQ-001, SCN-001, exactly both owned paths, and
  frozen-task limits.
- `WP-2`: packet repeats exact CanonicalTenant and normalizeTenantName
  signatures, W-2/c222, and the verified producer input.
- `WP-3`: packet states the whitespace/id invariant and exact
  `npm test -- tenant.normalize` command.
- `WP-4`: packet prohibits frozen-authority edits, signature changes, added
  paths, and invented authority.

### STAGE-GATE — REQ-002/SCN-002

Pass only when all predicates are true:

- `SG-1`: retains active Plan review or explicit plan change control; it does
  not mark review/plan complete.
- `SG-2`: sole action is correct missing REQ-007 task/verification, then
  re-seal/re-review.
- `SG-3`: forbids Implement, Implementation review, Final verification,
  Acceptance, Report, and Finish.

### CANDIDATE-SEALS — REQ-002, REQ-007, REQ-010

Pass only when all predicates are true:

- `CS-1`: preserves category-1 draft d111 and category-3 draft p333 while
  treating all four seals as candidate content seals, not frozen
  identities/intermediate commits.
- `CS-2`: freezes/commits specification only after spec-seal-b pass and plan
  only after plan-seal-b pass, recording each resulting path@blob.
- `CS-3`: permits stated between-round candidate edits only while no review is
  active; ledger/report receive no frozen blob.
- `CS-4`: does not start Plan before specification freeze or Implement before
  plan freeze.

### PLAN-DRIFT — REQ-007/SCN-007

Pass only when all predicates are true:

- `PD-1`: Git plan identity overrides native tasks and prevents implementation
  under p111 evidence.
- `PD-2`: begins read-only drift reconciliation and classifies edit before any
  commit, advance, or dispatch.
- `PD-3`: routes non-editorial plan defect through affected-task invalidation,
  plan review, new freeze blob, and revalidated downstream evidence.
- `PD-4`: preserves task-1 evidence only if inputs/contracts are provably
  unchanged; does not claim all work done.

### UAT-TRUTH — REQ-008/SCN-008

Pass only when all predicates are true:

- `UT-1`: supervised record names Sam, exact CLI exercise, supplied approval,
  authority, transcript, and criterion.
- `UT-2`: unattended record names exact npm substitute and evaluates same
  exit-status/stderr criterion.
- `UT-3`: unattended records `agent:unattended` standing authority as the
  waiver authority, uses truthful waived-human statement, and never claims
  Sam/human approval.
- `UT-4`: supervised branch records Sam's supplied approval and unattended
  branch records supplied automated pass; neither branch is unconditionally
  asserted for the other mode.

### CANONICAL-ARTIFACTS — REQ-009/SCN-009

Pass only when all predicates are true:

- `CA-1`: names exactly the four supplied canonical authority paths.
- `CA-2`: rejects all four proposed files and assigns
  decisions/state/acceptance to owning spec, ledger, or report.
- `CA-3`: does not replace a canonical artifact or invent a fifth authority
  source.

### ACTIVE-REVIEW — REQ-010/SCN-010

Pass only when all predicates are true:

- `AR-1`: sole next action is await/recover named Plan review; it does not
  start another review.
- `AR-2`: forbids plan-candidate, ledger, and downstream-stage mutation while
  active review has no return.
- `AR-3`: records native verdict/report reference/content seal only after
  return, then applies fixed mapping.

### DIRTY-PRIMARY — REQ-011/SCN-011

Pass only when all predicates are true:

- `DP-1`: inventories/attributes docs/customer-notes.md without staging,
  stashing, resetting, cleaning, discarding, or modifying it.
- `DP-2`: creates or verifies isolated feature/org-sso work in non-primary
  worktree before first tracked Feature Forge write.
- `DP-3`: stages only explicit in-scope paths there and never starts
  implementation on dirty primary main.

### HANDOFF-RETURN — REQ-012/SCN-012

Pass only when all predicates are true:

- `HR-1`: brainstorm-return returns after written specification/self-review
  and before Harden; plan-return returns after plan/self-review and before
  execution.
- `HR-2`: execute-return returns after local verification and intercepts normal
  branch-finish handoff without invoking it.
- `HR-3`: orders remaining gates through Stage 13 Report/ready before single
  Stage 14 finish-authority operation.

### FINISH-CAPABILITY — REQ-006/SCN-006, REQ-012/SCN-012

Pass only when all predicates are true. Predicates score observable behavior —
the safe outcome, exactly-once finalization, correct location, and
recoverability; exact phase/checkpoint/field labels are corroborating detail,
not required tokens.

- `FC-1`: blocks before claimed commit and before logical Finish invocation;
  F-18 remains only operation.
- `FC-2`: on the missing capability, halts the Finish operation before it
  starts and records a recoverable blocked state — naming the missing
  capability as the reason and a resolution-only next action — so a later run
  can resume the same operation; it does not advance the operation.
- `FC-3`: forbids claim, menu presentation, unattended resolution, and every
  external finishing invocation until capability exists.

### FINISH-CRASH — REQ-006/SCN-006/SCN-013

Pass only when all predicates are true. Predicates score observable behavior —
the safe outcome, exactly-once finalization, correct location, and
recoverability; exact phase/checkpoint/field labels are corroborating detail,
not required tokens.

- `FCr-1`: reads F-17 journal first and creates no new claim, logical Finish,
  or menu presentation.
- `FCr-2`: reconciles feature/base Git refs and Push-and-PR forge state
  read-only; repeats effect only when non-occurrence proven.
- `FCr-3`: when the push/PR outcome cannot be determined, takes no further side
  effect and records a recoverable blocked state capturing the ambiguity and
  the evidence needed to resolve it — neither repeating the push nor
  fabricating a terminal outcome.
- `FCr-4`: when the push/PR outcome is conclusively determined (proven to have
  occurred or not), finalizes the operation exactly once — recording the
  terminal result and marking the run complete with no further action — on the
  preserved feature branch/worktree, not a fresh location; it does not re-run
  the push.

### OPTION1-DIRTY-BASE — REQ-006, REQ-011

Pass only when all predicates are true:

- `OB-1`: inspects actual base checkout/ref and dirty path read-only; clean
  feature worktree is insufficient.
- `OB-2`: records category-8 blocked with prior phase choice_recorded,
  evidence, and resolution-only next action; merge does not start.
- `OB-3`: forbids stash, reset, clean, discard, merge, or any base-checkout
  modification; feature branch/worktree remains intact.
- `OB-4`: names base checkout terminal-receipt location only after safe Option
  1 merge/cleanup conclusively completes.

## Coverage mapping

The complete campaign jointly covers `REQ-001`/`SCN-001` through
`REQ-012`/`SCN-012` and `SCN-013`. The detailed result record maps each pair to
its observed fixture evidence without changing these scoring predicates.
