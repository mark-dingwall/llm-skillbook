# Feature Forge stage methods and review charters

This reference defines Feature Forge's bounded stage methods without replacing
the workflow contract's paths, stages, states, transitions, seals, ledger, or
checkpoint rules. `workflow.md` remains authoritative for those terms;
`authority.md` remains authoritative for mode, materiality, scope, and
acceptance. The controller owns each return boundary; it does not invoke a
one-shot skill and claim to interrupt that skill before its required handoff.

## Stage returns

### brainstorm-return

- **Controller-owned brainstorm method:** discover intent and constraints,
  explore the design with the requester, obtain the applicable approval, and
  return after writing and self-reviewing the specification. Do not invoke
  `superpowers:brainstorming`, whose required handoff continues into planning.
- **Required boundary:** use the one canonical specification and its
  required sections; apply the authority contract's decision-tree hardening
  in the workflow-owned Harden stage, not here; record material authority,
  assumptions, acceptance classifications, and UAT fallbacks; use the
  workflow's Brainstorm entry/exit evidence, draft checkpoint, and ledger
  return instead of separate method-local state or artifacts.
- **Return artifact:** the initial canonical specification, its self-review,
  and a concise result for the ledger.
- **Unattended substitution:** in unattended mode, synchronous brainstorming
  approval gates are replaced only by recorded
  standing authority under the durable intent brief plus the required
  self-review — never by silently skipping approval. The method continues
  only for recorded in-scope decisions and minimum coherence repairs; missing
  authority, a material/fundamental intent change, unsafe or irreversible
  action, unavailable dependency, or irresolvable contradiction blocks.
- **Block rule:** return `blocked` when the method cannot satisfy every
  boundary above.

### plan-return

- **Controller-owned plan method:** without invoking
  `superpowers:writing-plans`, turn the exact frozen specification into small,
  ordered implementation tasks with explicit ownership, interfaces,
  verification, and review checkpoints. Write the canonical plan, run its
  coverage/placeholder/type-consistency self-review, record the return, and
  stop. Do not offer or begin execution.
- **Required boundary:** preserve the workflow's Plan evidence and checkpoint
  process; state that plan checkboxes remain frozen and progress is recorded
  only in the workflow-owned implementation table and evidence.
- **Return artifact:** a self-reviewed canonical implementation plan with
  ordered plan tasks, owned contracts, dependency/verification notes, and the
  recorded stage result.
- **Block rule:** return `blocked` if the frozen specification is unavailable
  or mismatched, or the plan cannot satisfy the required boundary.

### execute-return

- **Controller-owned execution method:** execute each bounded plan task against
  its fixed interfaces, either by dispatching an independently ownable worker
  packet or working inline for tightly coupled tasks. Do not invoke
  `superpowers:subagent-driven-development` or
  `superpowers:executing-plans`; both require a branch-finishing handoff that
  lies outside Stage 9.
- **Required boundary:** verify each task before handoff, retain frozen
  specification/plan authority, never change plan checkboxes, and return after
  the implementation table records every task's commit and evidence. Do not
  offer or begin branch finishing or delete caller-owned progress state.
- **Return artifact:** for every plan task, its status, owned commit, local
  verification evidence, and a result suitable for the implementation table.
- **Block rule:** return `blocked` when a fixed contract cannot be honored or
  authority for a material or out-of-scope decision is missing. The
  authority contract's other pause/block triggers remain blocking and are not
  gated by materiality. Non-material in-scope ambiguity alone does not block:
  the controller records the decision under the authority contract and
  continues.

### finish-authority

- **Controller-owned Finish method:** verify the finished branch, present the
  three choices in `workflow.md`, and execute the authorized choice one
  journaled side effect at a time. It does not invoke
  `superpowers:finishing-a-development-branch`; that one-shot skill exposes no
  durable callback between choice and side effects.
- **Required boundary:** consume the existing `finish_id`, prior verification,
  clean-tree evidence, and journal phase. Persist the menu before presenting
  or resolving it, persist the choice before any effect, and persist the exact
  next effect before each external mutation. Interactive/supervised mode uses
  the exact menu once; unattended mode uses named pre-authorization or default
  Keep, never inferred integration authority.
- **Return artifact:** the authorized integration or Keep outcome, finish
  verification evidence, and the reconciled journal result.
- **Block rule:** return `blocked` if required verification cannot run, user
  authority is missing for a non-Keep action, or the journal boundary cannot
  be enforced.

## Execution choice

The controller selects one execution mode: `delegated` when two or more tasks
are independently ownable under fixed contracts and a worker runner is
available, otherwise `inline`. Record the mode and authority in the ledger.
If classification is uncertain, apply the authority contract's upward
classification rule and block where the resulting authority is absent.

## Worker packet contract

Every delegated worker packet must be independently executable under frozen
specification/plan authority. It contains exactly:

```text
task ID and exact frozen plan task; applicable REQ-NNN and SCN-NNN IDs;
owned paths; consumed/produced interfaces and signatures; invariants;
dependencies and already-verified inputs; exact verification command/evidence;
explicit prohibition on changing frozen spec/plan or inventing cross-task authority.
```

A packet missing any field is incomplete and must not be dispatched. The
worker reports its commit and verification evidence back to the
controller/ledger, which remains the sole progress authority — the
implementation table, not a worker's own state, records completion. This is a
dispatch-completeness contract, not an invitation to create a new packet
document outside the canonical run artifacts named in `workflow.md`.

`review-loop` self-derives its reviewer roster from a risk-surface inventory of
the sealed target; it takes no caller-supplied *charter*, deployment-context,
or completion-criterion field. Materialize each review subject in a fresh
temporary Git repository: the exact candidate at its canonical relative path
as the sole payload for Specification and Plan review; for Implementation
review, every regular subject file in the complete isolated worktree snapshot
at its exact relative path and mode, excluding only Git administrative
metadata, plus a regular manifest recording each unchanged symlink's exact
path, mode, and link target. Also capture the source worktree's exact binary
diff and staged-entry listing. A changed or review-relevant symlink, or any
other unsupported entry, blocks because `review-loop` cannot admit it safely.
Keep each `run_root` and its reports outside the target.

Create one disposable bootstrap commit after materialization and pass its exact
commit ID as `InvocationIntent.base` so preflight can resolve the target. This
temporary transport commit is not a candidate freeze checkpoint.

Pass frozen authorities, repository constraints, the symlink manifest, diff,
and staged-entry listing in both `InvocationIntent.ground_truth` (identity) and
every contained `CallRequest.input_paths` (readable delivery). Build the normal
review prompt with `render_prompt`, placing the applicable focus, pass
criterion, and `/inputs/...` locations in its declared `subject` value; do not
invent extra context or Controller fields.

### Specification review

Review the captured intent, repository constraints, and named authorities.
Test the candidate specification for faithfulness, coherence, bounds,
observability, testability, and completeness. The reviewer may identify a
missing authority or contradiction, but must not resolve a material decision
outside the authority contract.

### Plan review

Review the frozen specification and repository context. Test the plan for
coverage, systemic design, order, fixed contracts, and verification. Examine
code blocks only for interfaces, signatures, invariants, test intent,
dependencies, or architecture; do not treat a plan review as implementation or
add unapproved machinery.

### Implementation review

Review the exact frozen specification and plan against the complete diff,
tests, and documentation. Test requirements, scenarios, invariants,
regressions, security/performance, and the absence of extra scope or machinery.
Report any finding as a grounded discrepancy to the reviewed subject, and route
root-cause classification through the workflow contract.

## Read-only review return and round invariants

Use `review-loop` as a read-only host integration, not as its full FIX/CLOSE
workflow. The controller calls its public library through
`Controller.create_run`, `Controller.run_stage0`, `Controller.run_round1`, and
`Controller.run_triage`, with the required contained role dispatchers and
validators. It then returns without calling `run_fix`, adjudication,
promotion, final challenge, or `close`. This boundary is executable because
it stops only between public controller calls; Feature Forge owns corrections
between rounds.

Map the read-only return as follows:

| Read-only return | Workflow review result |
| --- | --- |
| TRIAGE completed with no open findings and all required gates/reviewers complete | `pass` |
| TRIAGE completed with actionable open findings | `changes_required` |
| `INDETERMINATE`, failed required gate, unavailable required reviewer/runner, missing authority, or non-actionable Important+ blocker | `blocked` |

For every review round, the controller must:

1. Persist `review_active` before dispatch. While it is active, obey the
   workflow rule that permits only await or recovery of that existing review.
2. Select the exact target described above; seal frozen **ground truth** through
   `InvocationIntent.ground_truth`, mount the same paths through
   `CallRequest.input_paths`, and render the applicable focus, pass criterion,
   and mounted locations through the prompt's declared `subject` value.
3. Keep loop reports **outside the sealed tree**. During the round, mutate
   neither the target nor the ledger.
4. On return, first record the TRIAGE outcome, open finding IDs, stable run
   reference, and whole-subject **content seal** — never before the round
   actually returns — and only then apply the fixed mapping above.

Fixes occur only between rounds, never during an active round. For
Specification review and Plan review, a fix to the candidate need not be
committed to start the next round: re-seal the corrected candidate content and
review it again under the applicable charter before any `pass`; only the
passing candidate receives its freeze checkpoint commit. For Implementation
review, each accepted fix is committed, re-sealed, and independently
re-reviewed before a final `pass` on the post-fix whole-tree snapshot, per the
workflow contract. After review, the controller compares seals before final
verification and permits only the recorded controller-ledger delta and its
recorded review-evidence reference; it separately confirms the reviewed
implementation commit and every other sealed path remain unchanged. Any other
delta blocks advancement under the workflow contract.
