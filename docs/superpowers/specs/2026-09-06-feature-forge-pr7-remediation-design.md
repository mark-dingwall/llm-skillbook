# Feature Forge PR #7 Remediation Design

**Date:** 2026-09-06

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
4. Add failing behavioral tests before every checker or instruction change.
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
- Prompt/task-shape evaluation for every Feature Forge-owned LLM dispatch and
  every Review Loop prompt composition changed by PR #7.
- Restoration of the component documentation gate.
- Focused, component, integration, packaging, documentation, and root tests.

### Excluded

- New workflow stages or finish outcomes.
- Migration of historical or pre-schema ledgers.
- A general prompt scoring framework or token-budget enforcement.
- Refactoring `ff-check` solely to reduce its line count.
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
- review kind versus the only stage that owns that review;
- review state versus the owning stage state;
- required frozen identities at and after each gate.

At minimum, a specification review belongs to Stage 5, a plan review belongs to
Stage 8, and an implementation review belongs to Stage 10. Stages 7 and 8
require a frozen specification. Stage 9 and later require both frozen
authorities. `blocked` is allowed only as the documented overlay on the current
stage; a nonterminal completed stage cannot claim an unrelated next action.

### Frozen bytes remain current during implementation

Stage 9 must run `identities` both before dispatch and after every bounded
worker return, before recording that return as complete. `audit` alone does not
compare current candidate bytes. Downstream stage gates retain their existing
`identities` checks. A changed specification or plan routes through read-only
reconciliation and invalidation; it is never normalized into progress.

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

### Receipts preserve decision evidence

Upgrade the strict receipt shape in place while PR #7 is unmerged. In addition
to existing identity fields, each returned receipt records:

- the exact review charter identifier;
- the exact completion criterion supplied by Feature Forge;
- every usable raw report ID consumed by TRIAGE;
- the Review Loop TRIAGE evidence artifact ID;
- every TRIAGE finding ID;
- the actionable/open Feature Forge finding IDs after stable-ID mapping.

All ID arrays are sorted, unique, and nonempty only when their source contains
rows. A `pass` receipt therefore has no TRIAGE or actionable IDs. The ledger
head remains coarse current state; receipt evidence carries the detailed
correlation needed for recovery and audit. `strict_receipt` and `audit` verify
the full exact shape and its agreement with the current review object.

## Prompt and Dispatch Quality

### Inventory

Evaluate these Feature Forge-owned dispatch shapes:

1. `brainstorm-return`;
2. `plan-return`;
3. one delegated `execute-return` worker packet;
4. specification review subject/focus/completion composition;
5. plan review subject/focus/completion composition;
6. implementation review subject/focus/completion composition.

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

### Skill TDD

Before changing instruction text, run fresh no-remediation pressure scenarios
that exercise at least: an underspecified worker packet, a tempting residual
Minor pass, and a post-worker frozen-plan drift. Record the baseline decisions
and rationalizations. After the minimal instruction/checker changes, rerun the
same scenarios with the revised installed payload and evaluate them with the
rubric and deterministic oracles. Existing PR #7 skill-TDD records remain
historical evidence; they do not replace this remediation-specific RED/GREEN
cycle.

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
2. **Ledger and state checker** owns the head schema, transition matrix, mode,
   base ancestry, and frozen-stage prerequisites.
3. **Filesystem and run inventory checker** owns safe path observation and
   repository-scoped worktree discovery.
4. **Review return boundary** owns TRIAGE mapping, receipt schema, Review Loop
   fixture, and the post-worker identities gate.
5. **Prompt quality and documentation** owns instruction simplification,
   pressure-scenario evidence, and the restored documentation command.
6. **Cross-cutting verification** changes no production behavior; it verifies
   integration, packaging, prompt inventory, and the complete suites.

Tasks 2 and 3 both modify `ff-check` but are sequential. Task 2 publishes the
exact helper signatures and state matrix consumed by Task 3. Task 4 consumes
the final checker receipt interface from Tasks 2–3. Task 5 may edit instruction
files but may not alter checker or receipt semantics. Any needed semantic change
returns to the owning earlier task rather than being smuggled into cleanup.

## Acceptance

The remediation is ready to push when all of the following are true:

- current `main` is integrated without losing PR #8 behavior;
- every included correctness requirement has a focused RED then GREEN test;
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
