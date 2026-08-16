# Feature Forge subskill adapters and review charters

This reference adapts installed skills to Feature Forge without replacing the
workflow contract's paths, stages, states, transitions, seals, ledger, or
checkpoint rules. `workflow.md` remains authoritative for those terms;
`authority.md` remains authoritative for mode, materiality, scope, and
acceptance. An adapter that cannot enforce its boundary returns `blocked` to
the controller; it must not emulate, silently weaken, or bypass the boundary.

## Adapter returns

### `brainstorm-return`

- **Installed skill:** `superpowers:brainstorming`.
- **Retained method:** discover intent and constraints, explore the design with
  the requester, and obtain approval before implementation-oriented work.
- **Feature Forge replacements:** use the one canonical specification and its
  required sections; apply the authority contract's decision-tree hardening;
  record material authority, assumptions, acceptance classifications, and UAT
  fallbacks; use the workflow's Brainstorm entry/exit evidence, draft checkpoint,
  and ledger return instead of the skill's own state or artifacts.
- **Return artifact:** the initial canonical specification, its self-review and
  approval/standing-authority record, plus a concise result for the ledger.
- **Unattended substitution:** a required brainstorm approval is satisfied only
  by recorded standing authority under the durable intent brief. The adapter
  continues only for recorded in-scope decisions and minimum coherence repairs;
  missing authority, a material/fundamental intent change, unsafe or
  irreversible action, unavailable dependency, or irresolvable contradiction
  blocks.
- **Block rule:** return `blocked` when the installed skill is unavailable or
  cannot retain the method while enforcing every replacement above.

### `plan-return`

- **Installed skill:** `superpowers:writing-plans`.
- **Retained method:** turn a settled design into small, ordered implementation
  steps with verification and review checkpoints.
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

### `execute-return`

- **Installed skill:** `superpowers:subagent-driven-development` for delegated
  execution, or the same task-by-task implementation discipline run inline.
- **Retained method:** execute bounded, independently verifiable plan tasks
  against their fixed interfaces; verify each owned change before its handoff.
- **Feature Forge replacements:** use exactly the execution mode selected below;
  retain frozen specification/plan authority; never change plan checkboxes;
  use the workflow-owned implementation table, commits, evidence, recovery,
  review, and invalidation rules rather than skill-local progress state.
- **Return artifact:** for every plan task, its status, owned commit, local
  verification evidence, and a result suitable for the implementation table.
- **Block rule:** return `blocked` when selected delegation is unavailable, a
  fixed contract cannot be honored, required authority is missing, or the skill
  cannot enforce the replacements.

### `finish-authority`

- **Installed skill:** `superpowers:finishing-a-development-branch`.
- **Retained method:** verify the finished branch, present safe integration
  choices, and perform the authorized finishing action once.
- **Feature Forge replacements:** invoke only at the workflow's Finish stage,
  exactly once; retain the workflow's prior verification, clean-tree, and
  recorded-return requirements; use the safe **Keep** default when no explicit
  user integration authority exists. No merge, deletion, cleanup, or other
  irreversible integration action is implied by this adapter.
- **Return artifact:** the user-authorized integration outcome or safe Keep
  outcome, finish verification evidence, and exactly-once ledger result.
- **Block rule:** return `blocked` if the required verification cannot run, the
  user authority is missing for any non-Keep action, or the boundary cannot be
  enforced.

## Execution choice

The controller selects exactly one execution branch and dispatches
`execute-return` for it. Select **subagent-driven** only when two or more plan
tasks are independently ownable under fixed contracts. Select **inline** for
tightly coupled shared state, or when delegation is missing or unavailable.
The selected mode and its authority are recorded in the workflow-owned ledger.
If the classification is uncertain, apply the authority contract's upward
classification rule and block where the resulting authority is absent.

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
4. On return, capture both native verdicts, the stable report reference, and
   the whole-subject **content seal**, then map the return above.

Fixes occur only between rounds. Each fix is committed, re-sealed, and reviewed
again under the applicable charter. After review, the controller compares seals
before final verification and permits only the recorded controller-ledger delta
and its recorded review-evidence reference; it separately confirms the reviewed
implementation commit and every other sealed path remain unchanged. Any other
delta blocks advancement under the workflow contract.

## Acceptance checklist

- [ ] `brainstorm-return`, `plan-return`, `execute-return`, and
  `finish-authority` each identify their installed skill, retained method,
  Feature Forge replacements, return artifact, and block-if-unenforceable rule.
- [ ] The unattended brainstorm approval substitution and Finish verification
  with safe Keep default are preserved.
- [ ] Both execution branches are defined; exactly one is selected and uses
  `execute-return`.
- [ ] All three complete charters cover their prescribed review ground truth
  and scope.
- [ ] Every native-result mapping produces `pass`, `changes_required`, or the
  prescribed `blocked` result.
- [ ] Every review persists `review_active`, passes subject/ground truth/
  charter/completion criterion, keeps reports outside the sealed tree, and
  captures verdicts/report reference/content seal without target or ledger
  mutation during the round.
- [ ] Fixes are between rounds, re-sealed and re-reviewed; post-review seal
  comparison permits only the recorded controller-ledger delta before final
  verification.
