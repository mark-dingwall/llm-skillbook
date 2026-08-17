# Feature Forge subskill adapters and review charters

This reference adapts installed skills to Feature Forge without replacing the
workflow contract's paths, stages, states, transitions, seals, ledger, or
checkpoint rules. `workflow.md` remains authoritative for those terms;
`authority.md` remains authoritative for mode, materiality, scope, and
acceptance. An adapter that cannot enforce its boundary returns `blocked` to
the controller; it must not emulate, silently weaken, or bypass the boundary.

## Adapter returns

### brainstorm-return

- **Installed skill:** `superpowers:brainstorming`.
- **Retained method:** discover intent and constraints, explore the design
  with the requester, and obtain approval before implementation-oriented
  work.
- **Return boundary:** performs the installed brainstorming method and
  returns after the written specification and its self-review, before
  Harden. It does not itself perform Harden's decision-tree hardening.
- **Feature Forge replacements:** use the one canonical specification and its
  required sections; apply the authority contract's decision-tree hardening
  in the workflow-owned Harden stage, not here; record material authority,
  assumptions, acceptance classifications, and UAT fallbacks; use the
  workflow's Brainstorm entry/exit evidence, draft checkpoint, and ledger
  return instead of the skill's own state or artifacts.
- **Return artifact:** the initial canonical specification, its self-review,
  and a concise result for the ledger.
- **Unattended substitution:** in unattended mode, the installed skill's
  synchronous brainstorming approval gates are replaced only by recorded
  standing authority under the durable intent brief plus the required
  self-review — never by silently skipping approval. The adapter continues
  only for recorded in-scope decisions and minimum coherence repairs; missing
  authority, a material/fundamental intent change, unsafe or irreversible
  action, unavailable dependency, or irresolvable contradiction blocks.
- **Block rule:** return `blocked` when the installed skill is unavailable or
  cannot retain the method while enforcing every replacement above.

### plan-return

- **Installed skill:** `superpowers:writing-plans`.
- **Retained method:** turn a settled design into small, ordered
  implementation steps with verification and review checkpoints.
- **Return boundary:** performs writing-plans' required header and
  self-review, then returns before its execution offer or start. It does not
  begin or offer execution.
- **Feature Forge replacements:** plan only against the exact frozen
  specification; preserve the workflow's canonical plan, Plan stage evidence,
  and checkpoint process; make task ownership and contracts explicit; state
  that plan checkboxes remain frozen and progress is recorded only in the
  workflow-owned implementation table and evidence.
- **Return artifact:** a self-reviewed canonical implementation plan with
  ordered plan tasks, owned contracts, dependency/verification notes, and the
  recorded adapter result.
- **Block rule:** return `blocked` if the frozen specification is unavailable
  or mismatched, or if the installed skill cannot enforce these replacements.

### execute-return

- **Installed skill:** exactly `superpowers:subagent-driven-development` when
  two or more plan tasks are independently ownable under fixed contracts, or
  exactly the installed skill `superpowers:executing-plans` for tightly
  coupled or no-delegation work. No unnamed inline substitute is used.
- **Retained method:** execute bounded, independently verifiable plan tasks
  against their fixed interfaces; verify each owned change before its
  handoff.
- **Return boundary:** returns after local verification for the dispatched
  scope, without invoking or offering branch finishing.
- **Feature Forge replacements:** use exactly the execution mode selected
  below; retain frozen specification/plan authority; never change plan
  checkboxes; use the workflow-owned implementation table, commits, evidence,
  recovery, review, and invalidation rules rather than skill-local progress
  state.
- **Return artifact:** for every plan task, its status, owned commit, local
  verification evidence, and a result suitable for the implementation table.
- **Block rule:** return `blocked` when the selected skill is unavailable, a
  fixed contract cannot be honored, required authority is missing, or the
  skill cannot enforce the replacements.

### finish-authority

- **Installed skill:** `superpowers:finishing-a-development-branch`.
- **Retained method:** verify the finished branch, present safe integration
  choices, and perform the authorized finishing action once.
- **Boundary with the workflow-owned Finish journal:** this adapter consumes
  and enforces, but does not define or write, `workflow.md`'s `finish_id`
  journal, its `ready -> claimed -> menu_pending -> choice_recorded ->
  executing -> terminal` phases, the `blocked` overlay, the pre-claim
  capability check, the `ready -> blocked` transition, or the `claimed`
  transition; it claims no runtime callback. It requires the workflow's
  already-passing pre-claim capability receipt before it can invoke branch
  finishing at all, then obeys the pre-menu, pre-side-effect, and
  terminal/block receipt conditions that `workflow.md` owns. A missing or
  pending workflow capability receipt means it may not claim, present a menu,
  resolve an unattended choice, or invoke
  `finishing-a-development-branch`.
- **Feature Forge replacements:** invoke only at the workflow's Finish stage,
  exactly once per `finish_id`; retain the workflow's prior verification,
  clean-tree, and recorded-return requirements. In interactive/supervised
  mode it otherwise preserves the exact installed menu once; in unattended
  mode it otherwise uses named pre-authorization or default Keep, never
  inferred integration authority.
- **Return artifact:** the user-authorized integration outcome or safe Keep
  outcome, finish verification evidence, and the exactly-once ledger result.
- **Block rule:** return `blocked` if the required verification cannot run,
  user authority is missing for any non-Keep action, or the boundary above
  cannot be enforced. It never performs the capability check, `ready ->
  blocked`, or `claimed` transition itself — those stay workflow-owned.

## Execution choice

The controller selects exactly one execution branch and dispatches
`execute-return` for it: `superpowers:subagent-driven-development` when two
or more plan tasks are independently ownable under fixed contracts, or
`superpowers:executing-plans` for tightly coupled shared state, or when
delegation is missing or unavailable. The selected mode and its authority are
recorded in the workflow-owned ledger. If the classification is uncertain,
apply the authority contract's upward classification rule and block where the
resulting authority is absent.

## Worker packet contract

Every worker dispatch packet — under `superpowers:subagent-driven-development`
or executed inline under `superpowers:executing-plans` — must be
independently executable under frozen specification/plan authority. A packet
contains exactly:

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

## Native review result mapping and round invariants

Map each native review result exactly as follows:

| Native review result | Workflow review result |
| --- | --- |
| `CONVERGED` + merge-ready | `pass` |
| actionable findings | `changes_required` |
| `INDETERMINATE` / no viable fix / missing authority / unavailable capability | `blocked` |
| `CONVERGED` + not merge-ready | `blocked` with the named blocker |

For every review round, the controller must:

1. Persist `review_active` before dispatch. While it is active, obey the
   workflow rule that permits only await or recovery of that existing review.
2. Pass the exact subject, frozen **ground truth**, applicable charter, and
   completion criterion to the reviewer.
3. Keep loop reports **outside the sealed tree**. During the round, mutate
   neither the target nor the ledger.
4. On return, first record both native verdicts, the stable report reference,
   and the whole-subject **content seal** — never before the round actually
   returns — and only then apply the fixed native-result mapping above to
   produce the workflow review result.

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

## Acceptance checklist

- [ ] `brainstorm-return`, `plan-return`, `execute-return`, and
  `finish-authority` are the only four adapter headings, each with an
  installed skill, retained method, return boundary, Feature Forge
  replacements, return artifact, and block-if-unenforceable rule.
- [ ] `brainstorm-return` returns before Harden; `plan-return` returns before
  its execution offer or start; `execute-return` names exactly
  `superpowers:subagent-driven-development` or exactly
  `superpowers:executing-plans`, never an unnamed inline substitute.
- [ ] `finish-authority` consumes and enforces, but never defines or writes,
  the workflow-owned `finish_id` journal, its phases, the `blocked` overlay,
  the pre-claim capability check, `ready -> blocked`, or `claimed`; it claims
  no runtime callback.
- [ ] Every worker packet field (task ID/frozen plan task, REQ-NNN/SCN-NNN,
  owned paths, interfaces/signatures, invariants, dependencies/already-verified
  inputs, exact verification command/evidence, prohibition on changing frozen
  spec/plan or inventing cross-task authority) is present, and a packet
  missing any field must not be dispatched.
- [ ] Exactly three review charters exist — Specification review, Plan
  review, Implementation review — and no fourth.
- [ ] Every native-result mapping produces `pass`, `changes_required`, or the
  prescribed `blocked` result.
- [ ] Every review persists `review_active`, passes subject/ground truth/
  charter/completion criterion, keeps reports outside the sealed tree, and on
  return records verdicts/report reference/content seal first, then applies
  the fixed mapping.
- [ ] Candidate-review (Specification/Plan) fixes need not be committed
  between rounds — only re-sealed and re-reviewed before `pass`.
  Implementation-review fixes are committed, re-sealed, and re-reviewed
  between rounds. Post-review seal comparison permits only the recorded
  controller-ledger delta before final verification.
