# Feature Forge maintainer contract

Feature Forge is the sole outer controller for one bounded Git work unit. It
owns the progression from preflight through Finish. Native task views and
delegated skills are displays or bounded returns; neither may advance the run.
The durable ledger is the sole workflow authority and, while nonterminal,
permits exactly one next action.

## Current authority

Treat [SKILL.md](SKILL.md) and its live owner references as the operational
source of truth. The [workflow contract](references/workflow.md) owns run
identity, canonical artifacts, states, seals, transitions, checkpoints,
invalidation, and Finish recovery. The [authority contract](references/authority.md)
owns modes, materiality, scope decisions, hardening, candidate/freeze
authority, and acceptance/UAT. The [adapter and review contract](references/adapters-and-reviews.md)
owns adapter boundaries, execution selection, worker packets, review focus,
and native-verdict mapping. Templates are copy-time schemas, not competing
workflow authority.

Historical design, review, and qualification documents provide lineage only.
Do not silently revive them as operating rules or alter historical evidence to
make it look current.

## Run state and recovery

Use one canonical run. Persist the ledger before every external dispatch and
immediately after every return. On resume, read the ledger and every artifact
it names, validate its recorded identities, worktree, branch, seals, commits,
and evidence, reconstruct only a display of progress, then perform the
ledger's sole next action. A missing or inconsistent return is recovered from
the recorded dispatch; it is never guessed or blindly re-dispatched.

Stage and review states have the meanings defined by the workflow contract.
In particular, `review_active` permits only waiting for or recovering that
existing review. A nonterminal run has one next action; a terminal run has a
recorded outcome and none. Do not create a parallel state machine in native
tasks, reports, or adapters.

The specification and plan become frozen only after their applicable review
and freeze checkpoint. Record and recheck their `<path>@<git-blob-id>`
identities at every downstream gate and resume. Candidate review seals are
separate from frozen identities. The ledger and final report remain mutable
records and never receive frozen blob identities.

## Scope, authority, and change control

Default to supervised automation. Classify uncertainty upward and obtain the
required authority for material decisions. Record material authority,
assumptions, rationale, affected requirements or scenarios, and acceptance
consequences in the canonical specification. Do not treat an acceleration
request as authority to omit unresolved decisions: harden the complete
decision frontier or block.

Keep unrelated dirty work untouched and out of checkpoints. First reconcile
drift read-only. An unrelated change blocks advancement; never capture,
stash, reset, discard, amend, or combine it. A new request stays deferred
unless the user explicitly expands the work unit. Classify changes before
editing frozen artifacts; route non-editorial corrections and rejected
acceptance through the workflow-owned invalidation graph. Later evidence does
not survive an invalidated root cause unless the defined editorial transition
permits it.

Acceptance records report only evidence actually produced in the run. Each
requirement uses its declared method and records current state, authority,
evidence, and fallback. Never invent human UAT. In unattended mode, a declared
automated substitute can support only the prescribed UAT waiver when it meets
the same evidence criterion; an inadequate or unavailable substitute is
infeasible and blocks.

## Delegation and review boundaries

Use only the named adapters and regain control at every return. They preserve
their installed method while preventing planning from starting execution,
execution from changing frozen authority or finishing the branch, and Finish
from escaping the durable journal. If an adapter cannot enforce its boundary,
block rather than emulate or weaken it.

Choose one execution mode under the adapter contract. Every worker packet,
including inline execution, must be independently executable from the frozen
specification and plan: exact task and applicable requirement/scenario IDs,
owned paths, interfaces, invariants, dependencies and verified inputs, exact
verification evidence, and an explicit prohibition on altering frozen
authority or inventing cross-task authority. The controller records the
worker's commit and evidence in the ledger implementation table; a worker's
own progress report is not authoritative.

`review-loop` derives its own roster; do not invent a caller-supplied charter
interface. Provide the actual subject, frozen ground truth, deployment
context, and completion criterion. Before dispatch, persist `review_active`;
during the sealed, read-only round mutate neither target nor ledger. On return,
record both native verdicts, stable report reference, and content seal before
mapping the result: converged and merge-ready is `pass`; actionable,
correctable non-convergence is `changes_required`; indeterminate, unfixable,
or unavailable-reviewer non-convergence is `blocked`; and converged but not
merge-ready is `blocked` with its named blocker. Fix only between rounds and
re-review the required post-fix subject.

After implementation review passes and before acceptance, compare the
post-review seal, confirm the reviewed implementation commit and every other
sealed path are unchanged, and run fresh risk-proportionate deterministic
checks. Record the commands, results, reviewed commit, and matching seal and
identity evidence in the ledger. Route a verification defect through the
invalidation graph, reconcile unexpected drift read-only, and block when a
required verification environment is unavailable.

## Finish is a recoverable logical operation

Stage 13 writes the report, allocates one stable `finish_id`, records Finish as
`ready`, and keeps the run active. Stage 14 alone drives that same logical
operation through `ready`, `claimed`, `menu_pending`, `choice_recorded`,
`executing`, and `terminal`; `blocked` is a resumable overlay. Persist the
required journal receipts before a claim, menu or unattended resolution, and
side effect, then persist the reconciled terminal or blocked receipt.

Before claiming, the workflow must record a passing pre-claim capability
receipt for durable journal interleaving and read-only Git/forge
reconciliation. If that capability is missing or the receipt is not passing,
record `ready -> blocked`; do not claim, present a menu, resolve an unattended
choice, or invoke `finish-authority`.

`finish-authority` is invoked exactly once for a `finish_id`, as the sole and
last external skill invocation. This is recoverable exactly-once control, not
a claim of physically atomic external effects. On recovery, reconcile recorded
Git and, where applicable, forge evidence read-only; reuse the same
`finish_id`, never repeat a claim, menu, side effect, or cleanup. If the effect
cannot be determined conclusively, record `blocked` with the prior phase and a
resolution-only next action.
