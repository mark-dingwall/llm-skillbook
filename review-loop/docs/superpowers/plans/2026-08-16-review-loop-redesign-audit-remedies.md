# Review Loop Redesign Audit Remedies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the written-spec audit findings in the governing review-loop redesign without expanding the internal single-user MVP into a general workflow platform.

**Architecture:** This is a documentation-only change. The governing design becomes explicit about read-only review dispatch, state-machine and TRIAGE contracts, target and artifact safety, inventory retirement, driver prompt transport, and profile parsing. No review-loop or multi-review production implementation is built in this change; the design names the focused future contracts and their acceptance tests.

**Tech Stack:** Markdown, Git, repository-local multi-review source inspection, `rg`, `git diff --check`.

## Global Constraints

- Preserve `GATE -> REVIEW -> TRIAGE -> FIX -> CLOSE`, ledger convergence, and the separate merge-readiness verdict.
- Keep tier effects limited to effort; no tier weakens completion, adjudication, sealing, or merge-readiness semantics.
- Keep the scope to the internal, single-user MVP; do not add a general workflow engine, rollback, arbitrary reviewer commands, or ordinary-call Bubblewrap.
- All semantic retirement judgment remains with the existing single inventory agent; a required one-line reason exists solely for post-run audit.
- The redesign specification supersedes archived review-loop plans for new work.

---

## Remedy Coverage

| Audit finding | Planned task |
|---|---|
| 1, 4-7 | Task 1 |
| 2, 3, 8 | Task 2 |
| 9, 10, 11 | Task 3 |
| 12 | Task 4 |
| 13-15 | Task 5 |
| Cross-cutting tests and acceptance | Task 6 |

### Task 1: Make target access, mutation, and recovery fail closed

**Files:**

- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:112-161`

**Interfaces:**

- Consumes: the controller's existing target-baseline and round-input seals.
- Produces: a complete lifecycle contract for ordinary dispatch, FIX, interruption recovery, and CLOSE.

- [ ] **Step 1: State the ordinary-dispatch read-only boundary**

  Add that every ordinary target-accessing role uses the host's supported read-only execution mode; prompt wording is not authorization. If that mode cannot be enforced, the controller refuses the dispatch. Keep the existing seal checks as detection, cancellation, and evidence invalidation; do not introduce Bubblewrap for ordinary calls or rollback.

- [ ] **Step 2: Define complete target entry and post-FIX checks**

  Specify that the whole-target sealer accepts regular files and directories only, rejects symlinks, FIFOs, sockets, devices, unreadable entries, and any entry that changes during enumeration. Require the existing quality gate after a successful FIX-delta verification and before accepting the next target baseline.

- [ ] **Step 3: Define interruption and CLOSE behavior**

  Mark a run interrupted after pre-FIX verification but before successful post-FIX verification as `INDETERMINATE` and `NOT CONVERGED`; on restart it may report retained evidence but must not continue or establish a baseline. Require one final target-baseline comparison immediately before terminal rollup; a mismatch is `NOT CONVERGED`.

- [ ] **Step 4: Verify the contract is bounded**

  Run: `rg -n 'ordinary.*read-only|special entry|interrupted FIX|final.*seal|quality gate after FIX' docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`

  Expected: every lifecycle boundary is explicit, and no ordinary-call containment or rollback subsystem was introduced.

### Task 2: Define the ledger, TRIAGE, and evidence-based settlement contracts

**Files:**

- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:285-323`
- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:420-445`

**Interfaces:**

- Consumes: usable raw reviewer reports, target/round-input seals, and immutable round-one ground truth.
- Produces: validated canonical ledger rows, bounded dispositions, adjudication inputs, and deterministic convergence and merge-readiness predicates.

- [ ] **Step 1: Define the TRIAGE boundary**

  Add one strict-JSON triage report contract that converts every usable raw report into canonical finding IDs, source locators, current severity, and proposed disposition. Reject malformed, incomplete, duplicate, or seal-incompatible output; retry once, then make the round `INDETERMINATE` without FIX or coverage updates.

- [ ] **Step 2: Define ledger states and terminal predicates**

  Name the allowed row states, allowed transitions, and the two terminal conjunct sets. Convergence requires usable scheduled reports, reconciliation, no INDETERMINATE stage, a matching final seal, and no `OPEN` or `FIX_APPLIED` Important+ row. Merge-readiness additionally requires the final-target quality gate, settled Important+ rows, and no current active Important+ specialist-coverage gap. User risk acceptance remains explicit evidence, never an implicit closure.

- [ ] **Step 3: Require proof before marking a finding fixed**

  Require a later triage disposition to cite an exact FIX-manifest change plus sealed current-target evidence for the ledger ID. An empty reviewer report, silence, or the mere presence of a manifest cannot settle a row. Green-making refutations, intentional dispositions, and severity downgrades retain the existing adjudication path.

- [ ] **Step 4: Verify the contract is complete**

  Run: `rg -n 'TRIAGE|ledger state|Convergence|Merge-readiness|FIX-manifest' docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`

  Expected: triage schema/retry, valid transitions, row-level fix evidence, and both terminal verdicts are discoverable without inference.

### Task 3: Make inventory identity, retirement, and ground truth durable

**Files:**

- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:232-282`
- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:416-444`

**Interfaces:**

- Consumes: a full inventory refresh from the single semantic inventory agent.
- Produces: a bijective current inventory, auditable retirement records, and a durable round-one authority inventory.

- [ ] **Step 1: Make area identity and priority order bijective**

  Require every active area ID to appear exactly once, every priority-order member to be an active area ID, and every active area ID to appear exactly once in that order. Reject duplicates, omissions, unknown references, and replacement graphs that do not resolve to one active successor.

- [ ] **Step 2: Add the settled RETIRED contract**

  Define `RETIRED` as no active, separate material concern in the latest sealed target, including removed/neutralized risk surfaces or a prior area proven not distinct. Exclude unstaffed/deprioritized areas, renamed/moved/merged areas, scope drift, and individual findings. Require a non-blank, single-line `retirement_reason`; preserve it for audit only. A valid retired area is not eligible for staffing and is not a merge-readiness coverage blocker.

- [ ] **Step 3: Pin reproducible ground truth**

  Require Stage 0 to persist the ordered canonical round-one ground-truth inventory, each authority locator, and each resolved immutable identity in canonical state. Require later adjudication to consume that persisted inventory, not reconstruct it from a seal digest.

- [ ] **Step 4: Verify audit trail wording**

  Run: `rg -n 'bijective|retirement_reason|not a merge-readiness|ground-truth inventory' docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`

  Expected: identity, retirement, and restart-safe authority requirements are explicit; reason text has no control-flow role.

### Task 4: Specify verbatim multi-review prompt transport

**Files:**

- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:360-410`
- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:665-715`

**Interfaces:**

- Consumes: canonical holistic prompt bytes and the sealed driver input file list.
- Produces: a versioned driver opt-in that delivers those exact prompt bytes to each fixed reviewer.

- [ ] **Step 1: Define a narrow driver opt-in**

  Require the adapter to write `verbatim_custom_prompt: true` with a non-empty `custom_prompt`. Under that opt-in, the driver validates `files` for scope and containment but passes the exact custom-prompt bytes to each reviewer without adding an injection preamble, title, context body, manifest, delimiter, or trailing newline. The existing behavior remains the default for every other driver task.

- [ ] **Step 2: Define compatibility and transport failure behavior**

  Require an older driver to reject the unknown opt-in, causing the existing ordinary holistic fallback. Require the driver itself to byte-compare the rendered canonical prompt with each driver-written per-client body before client launch; a mismatch is a driver validation failure and takes ordinary fallback while the seal still matches.

- [ ] **Step 3: Verify the change preserves the driver boundary**

  Run: `sed -n '350,410p' multi-review/multi_review/core/prompt.py`

  Expected: current behavior appends wrapper content, demonstrating why the new explicit opt-in is required rather than assuming `custom_prompt` is verbatim.

### Task 5: Close run-root and profile parsing ambiguities

**Files:**

- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:375-445`
- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:500-545`

**Interfaces:**

- Consumes: resolved target path, chosen state root, and optional profile YAML.
- Produces: non-overlapping storage and unambiguous profile resolution.

- [ ] **Step 1: Reject state roots that overlap the sealed target**

  Require preflight to resolve both paths and reject any run root that is equal to, a descendant of, or an ancestor of the sealed target. Do this before creating artifacts or sealing the target.

- [ ] **Step 2: Require duplicate-key YAML rejection**

  Require the profile and driver YAML parsers to reject duplicate mapping keys at every nesting level before defaulting or validation. Document that last-key-wins parsing is not permitted.

- [ ] **Step 3: Resolve ordinary model-pin language**

  Replace the contradictory fixed-pair statement with: normal-role `holistic`, `adversarial`, and `specialists` model pins are allowed exactly as shown in the profile schema; fixed-pair membership restrictions apply only to `multi_review.models`. Retain no-substitution failure behavior for every explicit pin.

- [ ] **Step 4: Verify profile consistency**

  Run: `rg -n 'duplicate.*key|normal-role model pin|multi_review.models|overlap.*target' docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`

  Expected: model-pin scopes do not conflict, duplicate-key rejection is explicit, and state storage cannot self-mutate the target.

### Task 6: Update validation and acceptance coverage

**Files:**

- Modify: `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md:665-747`

**Interfaces:**

- Consumes: every previous task's declared contract.
- Produces: implementation-facing deterministic and adapter test requirements that prove each audit remedy.

- [ ] **Step 1: Add deterministic state and lifecycle coverage**

  Extend the state-processor tests with ordinary dispatch refusal, special-entry rejection, post-FIX gate failure, interrupted-FIX recovery refusal, final seal drift, TRIAGE malformed/retry behavior, terminal predicates, proof-linked fixed rows, bijective inventory validation, retired areas with missing/blank/multiline reasons, and durable ground truth.

- [ ] **Step 2: Add adapter and profile coverage**

  Extend adapter tests with byte-equivalent verbatim prompt transport, wrapper/mismatch fallback, and legacy-driver rejection. Extend profile/driver YAML tests with duplicate keys, state-root overlap rejection, and separate normal-role versus fixed-pair model-pin behavior.

- [ ] **Step 3: Run documentation integrity checks**

  Run: `git diff --check`

  Expected: no whitespace errors.

  Run: `rg -n 'retirement_reason|verbatim_custom_prompt|FIX_STARTED' docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`

  Expected: the three new cross-cutting contracts are explicit in the governing specification.

- [ ] **Step 4: Commit the reviewed documentation patch**

  Run: `git add docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md docs/superpowers/plans/2026-08-16-review-loop-redesign-audit-remedies.md`

  Run: `git commit -m "docs(review-loop): resolve redesign spec audit remedies"`

  Expected: one commit contains the governing-spec correction and its implementation plan.

## Plan Self-Review

- Spec coverage: Tasks 1-5 map all fifteen reported audit findings; Task 6 maps every new contract to a future verification requirement.
- Placeholder scan: this plan contains no incomplete implementation step.
- Scope check: all changes remain within the review-loop redesign and the already-required multi-review driver interface; no production code is implemented in this documentation patch.
