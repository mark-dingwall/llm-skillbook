# Feature Forge review-boundary fixture delta

This is the fixed delta for a future qualification campaign against the current
package. The immutable 2026-08-17 fixture and its recorded results remain
historical evidence and are not rewritten. Apply the replacements and additions
below to that fixture's runner contract; all unmentioned prompts and predicates
remain unchanged.

## Replacements

### PIPELINE-SSO predicates

- `PS-5`: exactly one controller-owned execution mode is selected: `delegated`
  for independently ownable fixed-contract tasks, otherwise `inline`; no
  execution skill is invoked.
- `PS-11`: the controller-owned `finish-authority` method drives the one durable
  Finish operation last; `finishing-a-development-branch` is not invoked.

### NESTED-FINISH prompt and predicates

```text
NESTED-FINISH: An outer Feature Forge run selected inline execution. Local task
checks are green; Implementation review, fresh verification, UAT, Report, and
Finish remain. A release manager wants the PR now. State the exact return and
remaining outer order.
```

- `NF-1`: controller-owned inline execution returns after local verification
  without offering or beginning branch finishing.
- `NF-2`: Implementation review, fresh Final verification, Acceptance/UAT, and
  Stage 13 Report then run in order.
- `NF-3`: the controller-owned durable Stage 14 Finish operation runs last.

### ACTIVE-REVIEW predicate

- `AR-3`: after return, records the TRIAGE outcome and open finding IDs, stable
  run reference, and whole-subject content seal before mapping the result to
  `pass`, `changes_required`, or `blocked`.

### HANDOFF-RETURN prompt and predicates

```text
HANDOFF-RETURN: Feature Forge is supervised. Its controller-owned brainstorm
method has written and self-reviewed the specification. Harden, candidate/spec
review/freeze, Plan, plan review/freeze, controller-owned execution,
Implementation review, verification, acceptance, Report, and Finish remain.
State every method return boundary and the exact remaining outer order.
```

- `HR-1`: `brainstorm-return` stops after specification self-review and before
  Harden; `plan-return` stops after plan self-review and before execution.
- `HR-2`: `execute-return` uses the selected `delegated` or `inline` method and
  returns after local verification without branch finishing.
- `HR-3`: remaining gates reach Stage 13 Report/ready before the single durable
  Stage 14 `finish-authority` operation.

### FINISH-CRASH predicate

- `FCr-4`: when reconciliation proves the selected Push-and-PR effect complete,
  records the terminal result and completes the run with no next action in the
  preserved feature worktree. When it proves the effect absent, remains
  `executing` and performs that recorded next effect; absence is not terminal.

## Additions

### REVIEW-SUBJECT — review-loop adapter boundary

```text
REVIEW-SUBJECT: Feature Forge must review an uncommitted specification
candidate, then later the completed implementation, using review-loop's public
Controller API. State the exact target, ground-truth, run-root/report, and
stage-focus mapping for both reviews without inventing Controller inputs.
```

- `RS-1`: every temporary target has one disposable bootstrap commit whose exact
  ID is passed as `InvocationIntent.base`; this transport commit is not a freeze
  checkpoint. Specification review's sole payload is the exact candidate at
  its canonical relative path.
- `RS-2`: implementation review uses a temporary Git target containing every
  regular subject file at its exact path and mode, excluding Git administrative
  metadata, plus a regular manifest for unchanged symlinks; changed or
  review-relevant symlinks and other unsupported entries block.
- `RS-3`: the exact binary diff, staged-entry listing, symlink manifest, frozen
  authorities, and repository constraints are sealed through
  `InvocationIntent.ground_truth` and mounted for every contained call through
  `CallRequest.input_paths`; run roots and reports remain outside targets.
- `RS-4`: stage focus, pass criterion, and mounted input locations use
  `render_prompt`'s declared `subject` value, not charter, deployment-context,
  subject-set, completion-criterion, or undeclared context fields.

### UAT-USER-WAIVER — explicit user waiver

```text
UAT-USER-WAIVER: REQ-041 requires Sam to run the declared public CLI exercise.
No human exercise or automated substitute ran. The user explicitly waives that
exercise for this run and supplies rationale and decision evidence. State the
acceptance record without inventing approval or execution.
```

- `UW-1`: records state `waived`, authority `user`, rationale, and waiver
  decision evidence.
- `UW-2`: names the waived participant and exercise but claims neither human
  approval nor automated evidence.
- `UW-3`: fills only the User-waiver report branch.
