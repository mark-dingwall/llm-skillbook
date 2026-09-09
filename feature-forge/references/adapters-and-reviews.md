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

Every charter defines a finding as a grounded discrepancy against an approved
requirement, correctness condition, applicable repository contract, or required
verification result. Preferences, optional enhancements, and speculative
improvements are not findings. TRIAGE consolidates current raw findings;
Feature Forge neither discards nor downgrades a returned finding.

Map the read-only return as follows:

| Read-only return | Workflow review result |
| --- | --- |
| TRIAGE completed with zero findings and all required gates/reviewers complete | `pass` |
| TRIAGE completed with any finding, including Minor | `changes_required`, unless the round/repetition predicate below requires `blocked` |
| `INDETERMINATE`, failed required gate, unavailable required reviewer/runner, or missing authority before TRIAGE | `blocked` |

## Bounded review return rule

Starting a different review kind creates a fresh current review object with
`review.round` zero, empty finding-ID arrays, and a new root identity; prior
evidence stays in transition history. `root_identity` is an opaque controller
label. Ordinary fixes retain the root, round, and both finding-ID histories
through same-kind correction and re-review, while allocating fresh dispatch, external run,
target-seal, and receipt identities. Only an authority-governed root-cause
invalidation may replace it, and the transition records the old and new root
identities, reason, authority, and parent event.

After each completed nonempty TRIAGE return, apply the stable-ID judgment below
to every row, irrespective of severity. Copy the old `open_finding_ids` to
`previous_open_finding_ids`, install the new sorted mapped set in
`open_finding_ids`, and increment `review.round` before applying:

```text
must_block =
  (review.round >= 3 and open_finding_ids is nonempty)
  or
  (open_finding_ids is nonempty
   and open_finding_ids == previous_open_finding_ids)
```

The third actionable return therefore blocks, as does the first identical
consecutive nonempty finding-ID set. Write receipt/head result `blocked` when
`must_block` is true and `changes_required` otherwise. A pass leaves the round
unchanged and clears the current actionable set. `audit` validates only the
resulting current state; it does not infer finding similarity or the legitimacy
of a root reset from history.

For every review round, the controller must:

1. Capture source identity before materializing: require an exact regular file
   reached only through real-directory ancestors, then record its SHA-256 plus canonical path
   for a Specification or Plan candidate. For Implementation, require the
   clean committed subject and capture the canonical source `HEAD` as
   `reviewed_commit`. The controller retains the materialized-subject evidence
   needed to compare all sealed paths on return. Materialize the exact subject and
   create its one disposable bootstrap commit. Allocate a fresh filename-safe
   dispatch ID, caller-chosen external run root, and absent canonical receipt
   path `docs/feature-forge/runs/YYYY-MM-DD-<run-id>/reviews/<dispatch-id>.json`.
   Require every existing receipt-path ancestor to be a real directory and
   reserve the leaf for exclusive creation without following symlinks.
   Before `create_run`, persist a pre-dispatch blocked head whose sole next
   action is create-or-recover, plus transition evidence containing those exact
   three reserved identities and the captured source identity.
2. Pass the reserved external root as `InvocationIntent.run_root`, the bootstrap
   commit as `InvocationIntent.base`, and call `create_run`. Retain its returned
   run reference and target seal, then atomically replace the reservation with
   a fully populated `review_active` head before any semantic call. After an
   interruption, reuse only the recorded reservation: retry at that exact root
   when it is absent; when it already contains external state that the public
   controller cannot safely reconstruct, remain blocked rather than allocate or
   dispatch a duplicate run.
3. Select the exact target described above; seal frozen **ground truth** through
   `InvocationIntent.ground_truth`, mount the same paths through
   `CallRequest.input_paths`, and render the applicable focus, pass criterion,
   and mounted locations through the prompt's declared `subject` value. The
   containment mapping admits only the materialized target and declared ground
   truth, never the source worktree, ledger, or external run root.
4. Call `run_stage0`, then `run_round1` only for a reviewable
   Stage 0, and `run_triage` only for a usable Round 1. Stop at the first
   terminal outcome. Keep loop reports **outside the sealed tree**; during the
   round mutate neither target nor ledger.
5. Recheck the captured source identity before mapping the return or freezing:
   use the same exact-regular-file boundary for candidates; for Implementation,
   confirm the source commit and all sealed subject paths remain unchanged.
   Validate the returned evidence and stable-ID decisions as specified below,
   then exclusively write the canonical receipt. Record the captured source
   `HEAD` as `reviewed_commit` for every returned Implementation result.

### Receipt evidence contract

The exact receipt key set is:

```text
schema, kind, dispatch_id, run_ref, target_seal, source_identity, result,
actionable_finding_ids, feature_forge_charter_id, completion_criterion,
raw_report_ids, triage_artifact_id, triage_finding_ids, stable_id_mapping
```

`schema` is `feature-forge/review-receipt/v1`; kind, dispatch, run, seal, result,
and sorted unique actionable IDs agree with the current ledger review.
`source_identity` has exactly `kind`, `path`, and `value`: candidates use
`candidate_sha256`, canonical path, and SHA-256; Implementation uses
`reviewed_commit`, null path, and the ledger's reviewed commit. The checker
requires that commit to be nonempty, canonical, resolvable, and an ancestor of
current `HEAD`.

| Evidence field | Source and validation |
| --- | --- |
| `feature_forge_charter_id` | Exactly `feature-forge/specification-review/v1`, `feature-forge/plan-review/v1`, or `feature-forge/implementation-review/v1`, matching kind. This outer charter is distinct from Review Loop's per-reviewer charters. |
| `completion_criterion` | Exact nonempty criterion supplied for this review. |
| `raw_report_ids` | Sorted unique usable IDs from the caller-retained `Round1Outcome.raw_reports`, including zero-finding reports; never infer this inventory by scanning files. |
| `triage_artifact_id` | Registry ID of the `triage-result` bound to `apply_ledger_decisions`; null if TRIAGE did not complete. |
| `triage_finding_ids` | Every canonical TRIAGE row ID, sorted and unique. |
| `stable_id_mapping` | Exactly one `{triage_finding_id, feature_forge_finding_id}` per current TRIAGE ID; unique sources and destinations, no unknown sources. Sorted destination IDs equal `actionable_finding_ids`. |

Before writing, the controller reads the named external run's bound
`triage-result` evidence, verifies its registry digest and
`apply_ledger_decisions` binding, and compares its complete report inventory
with the retained Round 1 inventory and its finding IDs with the returned rows.
For a pass, TRIAGE is nonnull and all three finding/mapping/actionable arrays
are empty. A pre-TRIAGE block has null TRIAGE and empty arrays; retain any usable
Round 1 reports already produced. A completed nonempty TRIAGE has a complete
nonempty mapping and is `blocked` exactly when the round/repetition predicate
requires it, otherwise `changes_required`. A pass does not increment round.

`ff-check` validates local shape, sets, allocation, result/round rules, and
receipt/head agreement. It does not open the external Review Loop run or
independently prove provenance, charter dispatch, or criterion delivery.
Controller-written records agreeing with each other are not independent proof.

### Stable-finding-ID judgment

The LLM owns only material equivalence. Supply exactly `prior_findings`,
`current_findings`, and `materially_same_criterion`:

- The criterion is: same grounded discrepancy against the same requirement,
  correctness condition, repository contract, or verification result, with no
  material change in the required correction.
- Current findings are the complete normalized finding objects from the
  digest- and binding-verified current `triage-result`, including `id`,
  complete `sources` (`report_id`, `finding_id`, `claim`, `severity`,
  `locators`), `source_ids`, `reported_severity`, `current_severity`,
  `factual`, `state`, `evidence_locators`, and `target_seal`.
- Prior findings have exactly `feature_forge_finding_id` and `triage_finding`.
  Load full findings through the preceding receipt's `run_ref` and
  `triage_artifact_id`, verify the same digest/binding and report/ID inventories,
  then join through that receipt's `stable_id_mapping`. Require complete,
  unique coverage of the prior open IDs. Projection rows omit claims and
  evidence locators and cannot supply semantic input.

Return exactly one decision per current ID:

```json
{"decisions":[{"triage_finding_id":"current-id","decision":"FF-prior","rationale":"same missing REQ-007 verification"}]}
```

Choose one supplied prior stable ID with a nonempty rationale, or literal
`new` with null rationale. TRIAGE owns consolidation; two current findings
cannot reuse one destination. The LLM never allocates IDs.

The controller adds `dispatch_id` to those three input fields plus the exact
`decisions` array and invokes the installed pure function before receipt
creation, feeding this object on stdin:

```bash
python3 -c 'import json,runpy,sys; api=runpy.run_path(sys.argv[1]); print(json.dumps(api["apply_stable_id_decisions"](json.load(sys.stdin)),sort_keys=True,separators=(",",":")))' "$SKILL_DIR/scripts/ff-check"
```

Code validates exact shapes, complete current-ID coverage, known and singly
reused prior IDs, rationale rules, allocation, and destination uniqueness.
For `new`, it returns `FF-` plus SHA-256 of UTF-8
`json.dumps([dispatch_id, triage_finding_id], ensure_ascii=False, separators=(",", ":"))`;
a derived ID colliding with any prior ID is rejected. Each receipt destination
must be a prior open ID or that exact allocation.

The transient result has exactly `schema` (`feature-forge/stable-id-map/v1`),
`status`, `stable_id_mapping`, and `error`. Success is `pass` with sorted
mapping rows and null error; failure is `fail`, an empty mapping, and a stable
nonempty error code. A missing single JSON result, non-pass status, or shape
mismatch blocks before receipt creation. Record decisions and reuse rationales
in the existing ledger transition evidence; create no mapping artifact or
checker subcommand.

`review-loop` validates its temporary target seal during its public calls.
Feature Forge stores that returned seal, the external run reference, strict
receipt, and captured source identity; it does not recompute the seal against
the materialized tree after the run. A corrected subject always starts a fresh
linked review-loop run root and fresh dispatch/receipt rather than attempting
Round-N TRIAGE on the prior root.

On recovery from `review_active`, map a return only from an already-written,
valid Feature Forge receipt whose source identity still matches. Review-loop
status or transcripts alone cannot reconstruct a controller return; retain
`review_active` and block instead. Only explicit user authority may abandon
that review for a fresh linked round, recording the prior run reference and
reason in history.

The controller performs step 5's source comparison before recording a returned
receipt. Once `changes_required` authorizes a between-round correction, later
audits validate the historical receipt's exact source-identity shape instead of
comparing it with the corrected tree; an implementation return additionally
requires its reviewed commit to remain an ancestor of current `HEAD`. The next
review reservation captures and checks the corrected source anew.

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
