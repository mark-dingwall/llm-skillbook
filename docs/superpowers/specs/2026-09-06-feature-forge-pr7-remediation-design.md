# Feature Forge PR #7 Remediation Design

**Date:** 2026-09-06

**Amended:** 2026-09-12

**Status:** Approved for implementation

**Supersedes:** Only defective or ambiguous parts of the approved
[`2026-08-25` checked-skill MVP design](2026-08-25-feature-forge-checked-skill-mvp-design.md).
All unaffected requirements in that design remain authoritative.

## Purpose

Prepare Feature Forge PR #7 for another merge decision without turning its MVP
into a larger workflow engine. Integrate the already-merged Review Team and
Review Loop work, close the verified fail-open gaps in Feature Forge's checked
state, and assess every LLM dispatch against this North Star:

> LLM output quality is maximized by small, well scoped, clearly bounded tasks
> with clear goal conditions.

Prompt byte count is diagnostic evidence, not an acceptance target. A shorter
packet that omits authority, inputs, interfaces, or its completion condition is
worse. A longer packet must still justify every field by the one task being
delegated. No task may pass merely because it beats a numeric size baseline.

## Approach

Use surgical hardening of the existing architecture.

1. Merge current `origin/main` into `feature-forge-mvp`, preserving PR #8's
   Review Loop contracts and retaining only the compatible Feature Forge
   boundary additions.
2. Keep one version-one ledger and one standard-library `ff-check`; do not add a
   workflow engine, daemon, hook, prompt compiler, or second state artifact.
3. Put deterministic claims in `ff-check` and semantic decisions in concise
   instruction contracts.
4. Give each changed deterministic behavior a focused failing regression test;
   synchronize instructions with changed schemas and contracts, and add new
   behavior-shaping guidance only for gaps observed in a fresh baseline.
5. Review prompt shapes with fresh agents and a stable rubric. Use measurements
   to locate likely duplication, never as a quota or pass/fail threshold.

Alternatives were rejected. Splitting the checker into a new package would make
the review larger without fixing a user-visible defect. Reverting PR #7 and
selectively rebuilding it would discard already-qualified behavior and make the
integration with PR #8 harder to reason about.

## Scope

### Included

- Current-main integration and conflict resolution.
- The ten verified correctness gaps from the PR #7 review.
- The automation-mode omission because mode controls later authority decisions
  and is therefore material checked state.
- Exact implementation-task status validation and a separate notes escape hatch
  for controller annotations.
- Prompt/task-shape evaluation for every Feature Forge-owned LLM dispatch and
  every Review Loop prompt composition changed by PR #7.
- Restoration of the component documentation gate.
- Focused, component, integration, packaging, documentation, and root tests.

### Excluded

- New workflow stages or finish outcomes.
- Migration of historical or pre-schema ledgers.
- A general prompt scoring framework or token-budget enforcement.
- Refactoring `ff-check` solely to reduce its line count.
- A general Markdown parser, task-transition writer, ledger migration engine,
  or automatic repair of malformed task states.
- Review Loop FIX, adjudication, promotion, challenge, or CLOSE integration.
- Cleanup findings that do not improve correctness or materially simplify a
  touched boundary.
- Changes to PR #6.

## Integration Contract

The feature branch will merge, not rebase, current `origin/main`. This avoids
rewriting the reviewed PR history and avoids a force push. The merge resolution
must preserve the merged PR #8 behavior in `review-loop/SKILL.md`,
`review_loop/resources/inventory.md`, `review_loop/resources/review.md`, and
`review-loop/tests/unit/test_role_contracts.py`. Feature Forge-specific
composition additions may be reapplied only when the merged Review Loop public
contract still supports them. The resulting Review Loop suite must pass before
Feature Forge remediation begins.

PR #9 does not overlap the Feature Forge implementation. Its merged Review Team
state is accepted from `main` without alteration.

## Ledger and Checker Corrections

### Automation mode is checked state

Add `mode` to the version-one JSON head with exactly one of `interactive`,
`supervised`, or `unattended`. The copy-time template defaults to `supervised`,
matching the live omitted-mode rule. `runs`, `identities`, and `audit` must
reject a missing or unsupported mode as an unsupported head. Human evidence may
explain mode authority but may not substitute for the checked value.

### Base identity is not merely any commit

`base_identity` remains the immutable commit selected when the isolated feature
branch is created. The checker must require it to be a canonical commit and an
ancestor of current `HEAD`. The current schema cannot reconstruct historical
branch creation or infer an "actual fork point" after merges; instructions must
not claim that it can. Run-creation evidence records the exact selected base,
and deterministic ancestry prevents an unrelated resolvable commit from being
accepted.

### Paths fail closed without tracebacks

All user- or ledger-derived path resolution must convert `OSError`,
`RuntimeError`, `UnicodeError`, and `ValueError` into one literal `FF-CHECK v1`
result. Symlink loops and malformed worktree paths must never escape as Python
tracebacks. Existing distinctions remain: malformed claims are `fail`; an
observation the host cannot safely establish is `unverifiable`.

### Run inventory is repository-scoped

`runs --repo R` may use the shared worktree inventory, but a worktree counts
only when `git -C WORKTREE rev-parse --show-toplevel` resolves to a repository
whose common Git directory equals `R`'s common Git directory. A same-named
branch in another repository is not a collision. Any candidate worktree whose
repository identity cannot be established is `unverifiable`, not silently
accepted or ignored.

### Current-head transitions are coherent

The checker must validate a declarative compatibility matrix covering:

- overall `status` versus stage state;
- stage ID/state versus `next_action` presence;
- the stage that may dispatch each review kind;
- correction stages that retain a `changes_required` review;
- later stages that retain a passing review as evidence;
- pre-dispatch and returned blocked review states;
- required frozen identities at and after each gate.

Review ownership and retained review evidence are different facts. A
specification review may be dispatched only from Stage 5, a plan review only
from Stage 8, and an implementation review only from Stage 10. A returned
`changes_required` result remains the current review while specification
correction proceeds through Stages 3 and 4, plan correction proceeds through
Stage 7, or implementation correction proceeds through Stage 9. An ordinary
same-kind correction and re-review retains the review kind, root identity,
round count, and previous/current finding history while allocating fresh
dispatch, Review Loop run, target-seal, and receipt identities.

A passing specification review may remain current through specification freeze
and planning; a passing plan review may remain current through implementation;
and a passing implementation review may remain current through verification,
acceptance, reporting, and Finish. Only dispatching a different review kind or
performing an authority-governed root-cause invalidation initializes a new
kind/root with round zero and empty finding history. An invalidation records the
replaced root, replacement root, reason, authority, and parent event; prior
evidence remains in transition history.

A pre-dispatch or returned `blocked` review remains associated with its owning
review stage, including the documented blocked overlay used for recovery. The
matrix must contain positive tests for every permitted dispatch, correction,
retained-pass, and blocked shape as well as rejection tests for incompatible
combinations. Stages 7 and 8 require a frozen specification. Stage 9 and later
require both frozen authorities.

### `next_action` is structurally checked, semantically owned

For version one, `next_action` remains controller-authored text. `ff-check`
validates only that it is a nonempty string for a nonterminal head and null for
the exact terminal Stage 14 head. The controller and transition evidence own
whether that text faithfully names the workflow's sole permitted action. The
checker must not infer action meaning from prose or claim to reject an
"unrelated" action. An enumerated action protocol is deferred because it would
expand the ledger schema and transition machinery beyond this remediation.

### Implementation task state is exact; commentary has its own cell

The canonical implementation-progress table gains one final `notes` column:

| plan task | status | commit | evidence | notes |
| --- | --- | --- | --- | --- |

The template's initial row is a placeholder only while all five cells are
empty. After trimming surrounding whitespace, every non-placeholder `status`
cell must equal exactly one of `pending`, `active`, `awaiting_return`, `blocked`,
or `complete`. `ff-check audit` parses only this bounded canonical table and
returns a literal non-pass result for a missing table, malformed row, unknown
status, or status with trailing commentary. It must not accept a prefix such as
`awaiting_return (reason)`, silently remove a suffix, or normalize an invalid
value. Focused tests cover every accepted value, surrounding whitespace, a
rejected annotated value, and the same annotation accepted in `notes`.

`plan task`, `status`, `commit`, and `evidence` remain controller-owned control
cells. The `notes` cell contains optional free-form, single-line commentary; an
empty cell is valid, and a literal Markdown table delimiter must be escaped.
Before a delegated or inline task begins, the controller retains the current
controlled cells as its pre-dispatch snapshot. On return, including a failed
post-task identity check, it preserves those values except for the
workflow-authorized transition it is recording. Explanations belong in
`notes`, Blockers, or the transition log, never in a controlled cell.

The checker proves the current table's shape and exact status vocabulary. It
does not claim to prove equality with an earlier in-memory snapshot: the
version-one ledger has no durable pre-return task-table seal. The controller
owns that comparison under the bounded return contract. Adding a second state
artifact, a new public checker command, a transition writer, historical-ledger
migration, or a general-purpose Markdown engine is outside this MVP. Because
PR #7 remains unmerged, its version-one ledger template and live instructions
are updated in place rather than supporting two task-table schemas side by
side.

A task-table `audit` failure stops forward work: no task dispatch, task
completion, stage advance, implementation mutation, progress commit, or Finish
effect may occur while the gate is non-pass. The controller may make only the
bounded ledger correction needed to restore controlled cells from its trusted
pre-dispatch snapshot, move commentary into `notes`, Blockers, or the transition
log, and rerun `audit`. That successful correction may resume the interrupted
return without abandoning the run. If the snapshot is absent or ambiguous, the
correction remains invalid, or the check is `unverifiable`, record the canonical
blocked overlay and stop for recovery rather than inventing state.

### Frozen bytes remain current during implementation

Stage 9 must run `identities` both before a plan task begins and after every
bounded task return, before recording that return as complete. This applies to
delegated and inline execution. `audit` alone does not compare current
candidate bytes. Downstream stage gates retain their existing `identities`
checks. A changed specification or plan routes through read-only reconciliation
and invalidation; it is never normalized into progress.

## Review Return Corrections

### No unadjudicated finding creates a pass

Feature Forge stops at Review Loop's read-only TRIAGE boundary and intentionally
does not call adjudication. Consequently, a read-only return maps to `pass` only
when TRIAGE contains no findings. Any TRIAGE finding, including Minor, maps to
`changes_required` unless the result is independently indeterminate or blocked.
Feature Forge may correct and submit a fresh subject to a fresh Review Loop run;
it may not make a finding green by silently accepting or downgrading it.

This is deliberately simpler than importing Review Loop's adjudication
machinery and preserves the MVP boundary.

Every Feature Forge review charter uses one positive finding definition: a
finding is a grounded discrepancy against an approved requirement, correctness
condition, applicable repository contract, or required verification result.
Preferences, optional enhancements, and speculative improvements are not
findings and do not enter the required-remediation channel. Once a valid
finding is returned, Feature Forge may not silently downgrade or discard it.

### Receipts preserve decision evidence

Upgrade the strict receipt shape in place while PR #7 is unmerged. Retain the
existing `schema`, `kind`, `dispatch_id`, `run_ref`, `target_seal`,
`source_identity`, `result`, and `actionable_finding_ids` fields. Add exactly:

- `feature_forge_charter_id`: one of
  `feature-forge/specification-review/v1`, `feature-forge/plan-review/v1`, or
  `feature-forge/implementation-review/v1`, matching `kind`; this is the outer
  stage charter, not any of Review Loop's per-reviewer charter IDs;
- `completion_criterion`: the exact nonempty criterion Feature Forge supplied
  for this review;
- `raw_report_ids`: the sorted unique IDs from the Round 1 usable-report
  inventory, including reports that contain zero findings;
- `triage_artifact_id`: the Review Loop artifact-registry ID of the
  `triage-result` evidence bound to `apply_ledger_decisions`, or null when
  TRIAGE did not complete;
- `triage_finding_ids`: every canonical TRIAGE row ID, sorted and unique;
- `stable_id_mapping`: an array containing exactly one object with
  `triage_finding_id` and `feature_forge_finding_id` for every current TRIAGE
  finding.

When TRIAGE completes, `raw_report_ids` must equal the TRIAGE payload's complete
report inventory, including zero-finding reports. Each `triage_finding_id` must
appear in `stable_id_mapping` exactly once, no unknown TRIAGE ID may appear, and
each destination `feature_forge_finding_id` must be unique within the return.
The sorted mapped Feature Forge IDs must equal `actionable_finding_ids`. A
`pass` receipt requires a nonnull
`triage_artifact_id` and empty TRIAGE, mapping, and actionable arrays. A blocked
return before TRIAGE uses a null `triage_artifact_id`, empty TRIAGE and mapping
arrays, and may retain any usable Round 1 report IDs already produced. A
completed nonempty TRIAGE maps to `changes_required` unless the round or
repetition rule requires `blocked`.

The controller validates these facts against the public Review Loop return and
its referenced external run before exclusively writing the receipt. The
checker validates the receipt's exact shape, internal set consistency, result
and round rules, and agreement with the current ledger review object. Agreement
between Feature Forge-owned records is not independent provenance proof:
Review Loop's external run remains the source evidence named by `run_ref`, and
the live contract must not claim that `ff-check` independently re-proves it.

## Prompt and Dispatch Quality

### Inventory

Evaluate these Feature Forge-owned dispatch shapes:

1. `brainstorm-return`;
2. `plan-return`;
3. one delegated `execute-return` worker packet;
4. the stable-finding-ID mapping judgment;
5. specification review subject/focus/completion composition;
6. plan review subject/focus/completion composition;
7. implementation review subject/focus/completion composition.

The stable-ID judgment receives only the preceding TRIAGE findings and their
stable IDs, the current TRIAGE findings, and the materially-same criterion. Its
strict output maps every current TRIAGE ID exactly once either to one materially
equivalent prior Feature Forge ID or to the literal decision `new`, and records
a short rationale for each reused ID. It never allocates an ID. Deterministic
code rejects an unknown or multiply reused prior ID, allocates one fresh unique
Feature Forge ID for each `new` decision, and requires every final destination
ID to be unique. The LLM owns only material equivalence; deterministic
validation owns complete coverage, allocation, uniqueness, unknown IDs, output
shape, and agreement with the receipt/ledger ID sets. Consolidating multiple
current findings remains TRIAGE's responsibility and is not repeated here.

Also evaluate only those Review Loop templates whose composed inputs are
changed by the integration merge. Unchanged Review Loop role templates remain
owned by PR #8 and are outside this remediation.

### Rubric

For each dispatch, a reviewer must be able to answer yes to every item:

- **One task:** the packet asks for one independently completable job.
- **Scoped subject:** owned paths or sealed subject are exact and exclude
  unrelated repository history and controller state.
- **Necessary context:** each supplied requirement, invariant, dependency, and
  artifact is used by that task; global prose is referenced or omitted.
- **Authority boundary:** the worker knows what it may decide, what it may
  change, and what must be returned to the controller.
- **Interface boundary:** consumed inputs and produced outputs have exact names,
  shapes, and identities that match adjacent tasks.
- **Goal condition:** completion is observable through an exact return contract
  and verification command or semantic pass criterion.
- **Failure condition:** missing authority, inputs, or verification stops or
  returns blocked rather than inviting invention.

Record bytes and words for each composed packet when reproducible. Use them to
identify repetition and unexpectedly large context, then inspect the content.
There is no numeric score, aggregate target, or rule that a new packet must be
smaller than an old one.

### Proportional skill TDD

After current `main` is integrated and before any remediation instruction is
changed, run fresh no-remediation pressure scenarios that exercise at least: an
underspecified worker packet, a tempting residual Minor pass, and a post-task
frozen-plan drift. Record the observed decisions and rationalizations in one
compact qualification record. A baseline that already behaves correctly is
valid evidence: do not manufacture a failure or add guidance for that scenario.

Each changed deterministic behavior requires a focused regression test that is
observed failing for the intended reason before implementation and passing
afterward. Update instructions as required to match changed schemas and
contracts, and remove redundant prose when the contract remains unchanged. Add
behavior-shaping guidance only for demonstrated gaps; a passing baseline does
not justify redundant guidance. After the minimal changes, rerun the same
pressure scenarios with the revised installed payload and evaluate semantic
behavior with the rubric and observable effects with deterministic oracles.
Existing PR #7 skill-TDD records remain historical evidence; they do not
replace this remediation-specific baseline and GREEN comparison. One
remediation qualification record is sufficient.

### Authorized Claude GREEN transport correction

The Task 6 requalification uses Claude's structured-output transport for GREEN
only: append `--output-format json --json-schema <scenario-schema>` to the
existing invocation. Baseline invocations and Codex remain unchanged. Worker
output has exactly seven required string fields: `task`, `ownership`,
`interfaces`, `dependencies`, `verification`, `authority`, and `return`.
Their scenario-independent descriptions identify the implementation worker's
instructions and inputs, rather than a report about composing the packet.
Residual output has exactly the required object fields `receipt` and `head`;
their deep content remains subject to the existing scorer/checker. Drift output
has only a required `summary` string. Schemas supply structure, never scenario
answers, expected actions, findings, or verdicts.

Retain the complete raw Claude JSON envelope outside the fixture repository.
Require a successful process and success envelope with schema-valid
`structured_output`; materialize only that object deterministically for the
unchanged scorer and manual rubric. A missing or malformed structured return
from an executed invocation is a failure, not host unavailability. No extraction
from conversational `result` prose or fallback to it is permitted.

Task 6 may amend only this test-host adapter and its focused tests, preserving
all cases, prompts, scorer semantics, baseline behavior, and historical results.
Qualify the adapter RED/GREEN, rerun all four Claude GREEN scenarios, and append
the new outcomes and explicit transport-comparability limitation. This tests
the structured return channel, not whether Claude suppresses its separate
conversational prose. The original failed observations remain evidence.

The later task-table correction may mechanically update the pressure fixture's
seed ledger tail and table extractor to the canonical heading and five-column
shape so the strengthened `audit` gate can prepare a valid run. It must not
change scenario facts, prompts, expected decisions, or scoring predicates.
Preserve the original raw baseline and GREEN observations as historical
evidence; results produced with the amended table are a focused regression, not
a like-for-like continuation of the earlier comparison.

## Documentation Contract

Restore the Feature Forge documentation gate to `feature-forge/CLAUDE.md`:

```bash
python3 -m pytest \
  'tests/test_documentation.py::test_documentation_entrypoints[feature-forge]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[feature-forge]' -q
```

Do not add brittle exact-prose assertions. Deterministic tests exercise checker
behavior and structured artifacts; agent pressure scenarios exercise
instruction behavior.

## Task Boundaries

Workers execute sequentially in one isolated worktree. Boundaries are chosen so
that a worker never relies on an unannounced edit by another worker:

1. **Main integration** owns only merge conflict paths and produces a tested
   merge commit.
2. **Qualification baseline** owns the compact pressure scenarios, records the
   post-integration/pre-remediation observations, and changes no instruction or
   checker behavior.
3. **Ledger and state checker** owns the head schema, lifecycle compatibility
   matrix, structural next-action boundary, mode, base ancestry, and
   frozen-stage prerequisites.
4. **Filesystem and run inventory checker** owns safe path observation and
   repository-scoped worktree discovery.
5. **Review return boundary** owns TRIAGE mapping, stable-ID mapping, receipt
   schema, Review Loop fixture, and the post-task identities gate for delegated
   and inline execution.
6. **Prompt quality and documentation** owns instruction simplification, the
   GREEN pressure-scenario comparison, the single qualification record, and the
   restored documentation command.
7. **Cross-cutting verification** changes no production behavior; it verifies
   integration, packaging, prompt inventory, and the complete suites.
8. **Task-table state boundary** owns only the canonical table/template,
   bounded audit parser, exact status tests, minimal instruction synchronization,
   and the mechanical pressure-fixture adaptation authorized above.

Tasks 3 and 4 both modify `ff-check` but are sequential. Task 3 publishes the
exact helper signatures and lifecycle matrix consumed by Task 4. Task 5
consumes the final checker interfaces from Tasks 3–4. Task 6 may edit
instruction files but may not alter checker or receipt semantics. Any needed
semantic change returns to the owning earlier task rather than being smuggled
into cleanup. Task 2's baseline artifact and scenario inputs are immutable
inputs to Task 6's GREEN comparison. The authorized Claude GREEN transport
correction above is the sole exception for the host adapter; it does not
change the frozen scorer or scenario inputs.

Task 8 is a post-qualification correction prompted by the retained Sonnet
failure evidence. It does not reopen receipt, transition-matrix, path, or Finish
architecture. After Task 8, rerun the applicable Task 7 gates and independent
review before push.

## Acceptance

The remediation is ready to push when all of the following are true:

- current `main` is integrated without losing PR #8 behavior;
- each changed deterministic behavior has a focused test observed RED then
  GREEN, and already-correct pressure behavior is recorded without manufactured
  failure or redundant guidance;
- annotated task statuses fail closed, the same commentary is accepted in the
  dedicated notes cell, and the canonical pressure fixture passes the clean-seed
  audit;
- the prompt inventory has a recorded rubric decision for every listed
  dispatch, with no unresolved failure;
- Feature Forge's complete suite passes;
- the Review Loop boundary and complete Review Loop suite pass in their owning
  environment;
- installer, documentation, plugin-agent/metadata checks affected by the diff,
  and the root suite pass;
- `git diff --check` is clean and the worktree contains only scoped changes;
- an independent final review finds no unresolved material issue;
- the branch is pushed to PR #7 without merging it.
