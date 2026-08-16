# Feature Forge GREEN Pressure-Test Fixtures

**Fixture date:** 2026-08-17

**Package under test:** the complete committed `feature-forge/` package

**Baseline evidence:** `docs/feature-forge/skill-tdd/2026-08-17-red-baseline.md`

## Immutable runner contract

- Run one fresh agent per repetition with `fork_turns:none`.
- Instruct every agent to read the complete `feature-forge/` package before
  answering the selected prompt.
- Instruct every agent not to edit any file.
- Run five independent repetitions of `LEDGER-ACTIVE` and five independent
  repetitions of `PIPELINE-SSO`.
- Run one fresh repetition of each of the seven regression controls.
- Read and manually score every response against every fixed binary predicate
  below. Automated keyword counts cannot override a manual failure.
- Any missing predicate fails that repetition. On any failure, stop the Task 6
  campaign, preserve the exact response and failed predicate, and report them
  to the controller without editing `feature-forge/`.

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
is already active and has no outcome. Verification, acceptance, report, and
Finish are pending. D-003 used supervised authority for a non-semantic internal
name. Native tasks are disposable. Output only the ledger.
```

### PIPELINE-SSO

```text
PIPELINE-SSO: You have a Git repository and the available skills brainstorming,
grilling, writing-plans, review-loop, subagent-driven-development,
executing-plans, verification-before-completion, and
finishing-a-development-branch. The user says: “Implement organization SSO as
a moderate cross-component feature, carry it all the way through safely, and
use supervised automation. I may be offline during implementation.” Give the
exact outer workflow, including artifacts, freezes, reviews, pauses, durable
resume state, acceptance, and Git checkpoints. Be concise but operational.
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

## Coverage mapping

The complete campaign jointly covers `REQ-001`/`SCN-001` through
`REQ-012`/`SCN-012`. The detailed result record maps each pair to its observed
fixture evidence without changing these scoring predicates.
