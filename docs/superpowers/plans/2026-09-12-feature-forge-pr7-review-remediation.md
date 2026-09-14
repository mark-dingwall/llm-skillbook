# Feature Forge PR #7 First-Review Remediation Implementation Plan

**Status:** Frozen and implementation-ready

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Apply `superpowers:test-driven-development` inside every behavioral task and record observed RED and GREEN evidence.

**Goal:** Resolve PR #7's confirmed correctness findings under the strict-MVP boundary while preserving one version-one ledger, one receipt schema, and the existing four `ff-check` commands.

**Architecture:** Treat the canonical tracked Git tree and Git modes at `reviewed_commit`, plus separately supplied frozen authorities, as the reviewed implementation. Check worktree readiness independently, reject transforming attributes and gitlinks as unsupported, and keep recovery and Finish validation inside the existing checker and ledger contracts.

**Tech Stack:** Markdown skill/reference contracts, Python 3 standard library, pytest, Git, Review Loop's existing public controller, Codex CLI, Claude Code CLI.

**Spec:** The live Feature Forge contracts (`feature-forge/SKILL.md` and its owner references) are authoritative. The approved 2026-09-06 remediation design supplies lineage where it does not conflict with those live contracts or this review-remediation plan.

## Global Constraints

- Work only in `.worktrees/feature-forge-mvp`.
- Preserve earlier plans and qualification records unchanged; create `feature-forge/docs/skill-tdd/2026-09-12-pr7-review-remediation-qualification.md`.
- Use focused RED/GREEN tests for every deterministic behavior change. Do not write production behavior before observing the intended test fail for the intended reason.
- Do not manufacture RED failures for evidence-only prose, dead-code deletion, or the conditional #23 probe.
- Preserve one version-one ledger, one receipt schema, and the four commands `runs`, `identities`, `reviewed-snapshot`, and `audit`.
- Add no state artifact, seal inventory, Review Loop API, submodule support, generalized filesystem transaction layer, caching system, or performance refactor.
- Continue deferring findings #22, #29-31, and #33-34.
- Run no new stochastic LLM campaign unless a dispatched prompt or semantic output contract changes.
- Commit each task using explicit paths; never use blanket staging. Preserve unrelated and ignored workspace content.
- After this plan is recorded, do not request another plan review. The next independent review evaluates the implemented remediation diff.
- Do not merge PR #7. Push and post the PR response only after implementation review and all required gates pass.

---

### Task 1: Harden Git and Frozen-Identity Observations

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Test: `feature-forge/tests/test_ff_check_identities.py`
- Test: `feature-forge/tests/test_ff_check_audit.py`
- Test: `feature-forge/tests/test_ff_check_runs.py`

**Interfaces:**
- Produces one shared Git argv/environment policy used by every checker Git subprocess.
- Preserves the four public commands and their exit/result protocol.

- [ ] Add focused tests proving ambient repository, index, object, and configuration routing cannot redirect observations; configured fsmonitor/hooks cannot execute; a repository path ending in a space is preserved; dangling and staged-only frozen blobs fail; deep JSON and whitespace-only identities fail without traceback.
- [ ] Run each focused test and record its expected RED result before production changes.
- [ ] Implement one shared Git policy that disables configured fsmonitor and hooks, preserves `GIT_OPTIONAL_LOCKS=0`, and removes `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`, and every `GIT_CONFIG_KEY_<digits>` / `GIT_CONFIG_VALUE_<digits>` variable.
- [ ] For textual Git output, remove only one terminating newline and preserve all other whitespace.
- [ ] Require frozen specification and plan identities to resolve as canonical blobs and equal the blobs at their canonical paths in current `HEAD`.
- [ ] Catch `RecursionError` during strict JSON parsing and apply the existing nonblank-text predicate to review/receipt identities.
- [ ] After GREEN, remove unreachable `runs` guards and unused `canonical_run` / `exact_directory`; implement exact-regular-file checks through the existing entry-state observer without adding another path walker.
- [ ] Run the focused suites, self-review, and commit explicit paths as `fix: harden Feature Forge Git identities`.

### Task 2: Reject Transforming Attributes Before Controlled Git Operations

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Test: `feature-forge/tests/test_ff_check_identities.py`
- Test: `feature-forge/tests/test_ff_check_reviewed_snapshot.py`

**Interfaces:**
- Consumes Task 1's hardened Git policy.
- Produces one NUL-safe, conversion-free attribute gate used before materialization, hashing, status, or another conversion-capable operation.

- [ ] Add focused tests proving each of `filter`, `text`, `eol`, `ident`, and `working-tree-encoding` fails before conversion; drivers literally named `unset` and `unspecified` cannot execute; marker filter programs never execute; repositories with no transforming attributes retain byte-exact behavior.
- [ ] Run the focused tests and record expected RED results.
- [ ] Enumerate controlled tracked paths using conversion-free Git plumbing, then use NUL-safe effective `check-attr --all` observation before any conversion-capable command.
- [ ] Return explicit unsupported/unverifiable whenever any controlled path reports one of the five attribute names, regardless of its reported value. Never execute clean/process filters and do not add conversion diagnostics or transformation support.
- [ ] Preserve exact symlink-target handling and explicit gitlink rejection.
- [ ] Run focused suites, self-review, and commit explicit paths as `fix: reject unsupported Git transformations`.

### Task 3: Correct Review Returns and Persisted Recovery

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Modify: `feature-forge/references/adapters-and-reviews.md`
- Test: `feature-forge/tests/test_ff_check_audit.py`
- Test: `feature-forge/tests/test_ff_check_runs.py`
- Test: `feature-forge/tests/integration/test_review_loop_boundary.py`

**Interfaces:**
- Produces one `review_must_block(round, previous_ids, current_ids)` predicate and strict persisted-return recovery validation.
- Adds no receipt field or Review Loop API.

- [ ] Add focused tests for same-kind pre-TRIAGE blocking with retained findings; repeated/third-round blocking; recoverable persisted pass, changes-required, and blocked results; malformed/mismatched/source-divergent receipts; implementation recovery across controller-only descendants; rejection after implementation-path changes.
- [ ] Run focused tests and record expected RED results.
- [ ] Use one repetition predicate for completed TRIAGE. A completed nonempty result increments round, moves the active old open IDs to returned previous IDs, installs mapped actionable IDs as returned open IDs, and applies the shared predicate.
- [ ] For pre-TRIAGE blocking, require null TRIAGE identity and empty receipt TRIAGE/mapping/actionable arrays while retaining the active round and both finding histories.
- [ ] Keep ordinary `audit` non-passing while the ledger remains `review_active`; recovery applies the validated projected result first.
- [ ] Treat a persisted receipt as recoverable only after exact-regular path, strict schema, dispatch/run/seal, result, mapping, stable-ID, round, and source validation.
- [ ] Match Specification/Plan receipts to current candidate bytes. For Implementation, require the receipt's canonical `reviewed_commit` to resolve and remain an ancestor of current `HEAD`, with every descendant difference limited to controller-owned paths permitted at that stage.
- [ ] State that partial Round 1 reports exist only when `run_round1` returns a `Round1Outcome`; an exception before return exposes no usable partial inventory.
- [ ] Run focused suites, self-review, and commit explicit paths as `fix: preserve recoverable review returns`.

### Task 4: Enforce Implementation Completion and Terminal Identity

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Modify: `feature-forge/references/workflow.md`
- Test: `feature-forge/tests/test_ff_check_audit.py`
- Test: `feature-forge/tests/test_ff_check_runs.py`
- Test: `feature-forge/tests/test_ff_check_identities.py`

**Interfaces:**
- Produces stage-aware task completion and one terminal-only primary-base identity exception shared by `audit` and `identities`.

- [ ] Add focused tests for valid Stage 9 noncomplete states; Stage 10/14 rejection of pending tasks, placeholders, and missing commit/evidence; `runs` rejection of incomplete ledgers; feature-worktree terminal outcomes; primary-base local-merge terminal outcome; linked-base rejection; no primary exception for nonterminal runs.
- [ ] Run focused tests and record expected RED results.
- [ ] At Stage 10 or later, reject the placeholder and require every row to have exact status `complete` plus nonblank commit and evidence cells. Apply the same check before `runs` classifies a ledger as resumable.
- [ ] Preserve linked `feature/<run-id>` worktree identity for every nonterminal run.
- [ ] Keep/Push-and-PR terminal ledgers in the preserved feature worktree. Support local-merge terminalization only in the repository's primary base checkout; linked base checkouts are unsupported.
- [ ] Require the terminal head to identify its containing checkout/branch and require base identity plus reviewed implementation commit to remain ancestors of terminal `HEAD`. Apply this in both `canonical_identity_claims` and standalone `identities`.
- [ ] Preserve original feature identity in existing transition/Finish evidence without schema additions.
- [ ] Run focused suites, self-review, and commit explicit paths as `fix: enforce terminal Feature Forge state`.

### Task 5: Separate Committed Integrity from Checkout Readiness

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Modify: `feature-forge/references/workflow.md`
- Modify: `feature-forge/references/adapters-and-reviews.md`
- Test: `feature-forge/tests/test_ff_check_reviewed_snapshot.py`
- Test: `feature-forge/tests/integration/test_review_loop_boundary.py`

**Interfaces:**
- Consumes Tasks 1-2's Git and attribute gates and Task 4's terminal identity.
- Defines the implementation-review subject as tracked committed content at `reviewed_commit`, with checkout readiness checked independently.

- [ ] Add focused tests for byte-exact regular files without transforming attributes; spoofed size/mtime; symlink target match/mismatch; gitlink rejection; ignored-file exclusion; owner-executable correctness with `core.fileMode=false`; first-round implementation pass followed by atomic checkpoint 7 and clean Stage 14 entry without another commit.
- [ ] Run focused tests and record expected RED results.
- [ ] Materialize tracked regular files from `reviewed_commit` blobs with Git executable/non-executable modes. Preserve the unchanged-symlink manifest; block changed/review-relevant symlinks; reject gitlinks; exclude ignored/untracked material; supply frozen authorities separately.
- [ ] Compare `reviewed_commit` to current `HEAD` with NUL-safe tree/blob identity, permitting descendant commits to change only stage-allowed controller paths and preserving rename/copy/delete/staged detection.
- [ ] After the attribute gate, compare controlled regular-file raw bytes directly with their current-`HEAD` blobs using conversion-free reads; compare symlink `readlink` bytes with symlink blobs; reject gitlinks and ordinary tracked/untracked dirt; ignore ignored entries.
- [ ] Treat permissions as checkout policy: `100755` requires owner execution, `100644` requires it absent, and successful raw reading proves readability. Do not require exact `0644`/`0755` masks.
- [ ] Make checkpoint 7 atomically commit final report, ledger, and applicable passing implementation-review receipt/evidence. The ledger already records Stage 14 active, Finish `ready`, pending outcome, stable `finish_id`, and sole next action `claim <finish_id>`.
- [ ] Require a clean worktree after checkpoint 7 and run initial Stage 14 `identities`, `reviewed-snapshot`, and `audit` against that exact committed head.
- [ ] Run focused suites, self-review, and commit explicit paths as `fix: verify canonical reviewed content`.

### Task 6: Close Qualification Execution Paths

**Files:**
- Modify: `feature-forge/tests/behavior/identity_drift.py`
- Modify: `feature-forge/tests/behavior/remediation_pressure.py`
- Test: `feature-forge/tests/test_behavior_oracle.py`
- Test: `feature-forge/tests/test_remediation_pressure.py`

**Interfaces:**
- Consumes Task 1's hardened Git policy and Task 2's attribute-first rule.
- Preserves pressure prompts, expected semantic decisions, and scorer contracts.

- [ ] Add marker regressions proving scorer fsmonitor/filter programs and model-configured filters cannot execute; nonzero model exits cannot pass; the retained checker remains authoritative after fixture replacement.
- [ ] Add the deterministic delayed-child #23 probe and run it before deciding whether process-group code is needed.
- [ ] Record expected RED results for every behavior that currently fails. If #23 passes immediately, record the probe and add no process-group implementation.
- [ ] Capture trusted `ff-check` source bytes and hardened Git helper callables before model execution. Use the same scrubbed environment, fsmonitor/hooks overrides, and attribute-first policy for every scorer Git call.
- [ ] If unsupported attributes exist, fail/unavailable the scenario before status, hashing, or conversion-capable Git operations.
- [ ] After model termination, execute retained checker source using trusted `sys.executable`, `-I`, `-c <retained-source>`, and a trusted working directory outside the fixture. Never execute a checker file from the fixture.
- [ ] Treat every nonzero Codex/Claude exit as failed/unavailable.
- [ ] If #23 reproduces, use an owned process group, terminate it on timeout, wait the bounded grace period, then kill/reap the group if needed. Promise only owned-group cleanup; a child starting another session can escape it.
- [ ] Run focused suites, self-review, and commit explicit paths as `fix: isolate Feature Forge qualification processes` when #23 reproduces, otherwise `fix: isolate Feature Forge qualification checker`.

### Task 7: Resolve Bubblewrap Test Portability

**Files:**
- Modify: `review-loop/tests/integration/test_execution_containment.py`
- Modify: `review-loop/tests/integration/test_multi_review_containment.py`
- Create only if sharing is necessary: `review-loop/tests/integration/containment_test_helpers.py`

**Interfaces:**
- Changes tests only; production Bubblewrap mappings remain unchanged.

- [ ] Add a focused test/characterization proving interpreter selection prefers resolved `sys.executable` beneath `/usr`, then `/usr/bin/python3`, then `/usr/local/bin/python3`, and reports an explicit skip when none is visible.
- [ ] Observe RED for the missing resolver behavior.
- [ ] Implement one shared resolver and use it in both containment test files.
- [ ] Run the two containment suites, self-review, and commit explicit paths as `test: resolve Bubblewrap-visible Python`.

### Task 8: Contract Documentation and Record New Evidence

**Files:**
- Modify: `feature-forge/references/workflow.md`
- Modify if both owners changed: `feature-forge/tests/conftest.py`
- Create: `feature-forge/docs/skill-tdd/2026-09-12-pr7-review-remediation-qualification.md`
- Modify: this plan only to link the completed qualification record if necessary

**Interfaces:**
- Changes no production behavior.
- Produces fresh evidence without altering historical qualification records.

- [ ] Define the common post-review integrity gate once and reference it from Stages 11-14 while preserving stage-specific action/failure routing.
- [ ] Record #22 as a live residual: symlinks are rejected at observation time, later reads are not descriptor-bound, the controller must be quiescent during gates, and generalized concurrent replacement protection is deferred.
- [ ] Move the duplicate snapshot helper to `conftest.py` only if both owning tests were already modified; otherwise record #35 as opportunistically deferred.
- [ ] Create the new qualification record containing focused RED/GREEN evidence, production commits tested, #23's result, #35's disposition, complete verification, skips/unavailable evidence, and deferred findings. Do not edit earlier records.
- [ ] Run no stochastic campaign unless an actual dispatched prompt or semantic output contract changed.
- [ ] Commit explicit evidence/documentation paths as `test: record PR 7 review remediation`.

## Deferred Findings and Boundaries

- #22: descriptor-bound protection against concurrent external path replacement.
- #29-31: batch hashing and cached/shared gate contexts.
- #33-34: test namespace caching and lifecycle-matrix restructuring.
- #35: implement only if naturally shared while both fixture owners change.
- Git transformation support is deferred until a concrete supported repository requires it.
- Local-merge terminalization from a linked base checkout is unsupported.
- Gitlinks are unsupported.
- Partial Round 1 reports lost through an exception before `Round1Outcome` are unavailable.

## Verification and Handoff

After all task reviews pass, run:

```bash
python3 -m pytest feature-forge/tests -q

cd review-loop
uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q
uv run pytest -q
cd ..

python3 -m pytest tests/test_install.py -q
python3 -m pytest tests/test_documentation.py -q
python3 -m pytest tests/test_plugin_agents.py -q
claude plugin validate . --strict
python3 -m pytest tests -q

python3 -m py_compile \
  feature-forge/scripts/ff-check \
  feature-forge/tests/behavior/identity_drift.py \
  feature-forge/tests/behavior/remediation_pressure.py

git diff --check origin/main...HEAD
git status --short --branch
```

Then request one independent whole-diff review against the current PR base, address only confirmed material findings in the one permitted final fix wave, rerun affected and complete gates, push `HEAD` to `origin/feature-forge-mvp`, verify PR #7's head/checks, and post the planned response below. Do not merge PR #7.

## Planned PR Response

Post a top-level PR comment because the original review has no inline threads:

```markdown
The 35 findings were evaluated and remediated under the strict-MVP rules.

- #1-21 were resolved through bounded correctness changes or explicit unsupported boundaries.
- #24-28 and #32 were applied only where they directly consolidated accepted fixes or removed existing duplication.
- #22 remains deferred as a documented threat-model residual: checks reject symlinks at observation time but do not provide descriptor-bound identity across a later read. The controller must remain quiescent during gates.
- #29-31 and #33-34 remain deferred performance/refactoring proposals without a merge-blocking correctness requirement.

Finding #6 is intentionally bounded: partial Round 1 reports are retained only when `run_round1` returns a `Round1Outcome`; an exception before return exposes no usable partial inventory. No Review Loop API was added.

The reviewed implementation is the canonical tracked tree and Git modes at `reviewed_commit`, with frozen authorities supplied separately. Controlled paths declaring `filter`, `text`, `eol`, `ident`, or `working-tree-encoding` are unsupported in this MVP and fail before conversion or configured-program execution. Broader transformation support is deferred until justified by a concrete supported repository.

Checkout readiness independently verifies byte-exact regular files, symlink targets, executable state, ordinary dirt, and Stage 14 cleanliness. Ignored/untracked material is outside the review subject, ordinary untracked dirt remains a readiness failure where required, unchanged symlinks preserve their manifest checks, and gitlinks fail explicitly.

Checkpoint 7 now atomically commits the final report, ledger, and passing implementation-review receipt. Its ledger already records Stage 14 active and Finish ready, allowing the initial Stage 14 gates to run against a clean committed head.

Persisted implementation receipts are recoverable only after strict schema, dispatch, result, mapping, stable-ID, historical reviewed-commit, allowed-descendant, and source validation. Local-merge terminalization is supported in the primary base checkout; linked base checkouts remain outside the MVP.
```

Append exactly one #23 paragraph based on the deterministic probe:

- Reproduced: `Finding #23 was reproduced. The qualification runner now terminates and reaps its owned process group on timeout; a child deliberately creating a new session remains outside that guarantee.`
- Not reproduced: `Finding #23 did not reproduce under the deterministic delayed-child regression, so process-group machinery was not added.`

Append exactly one #35 paragraph:

- Implemented: `Finding #35 was implemented by moving the duplicate snapshot fixture helper into the existing shared test fixture module.`
- Deferred: `Finding #35 was opportunistically deferred because the two fixture owners did not otherwise require a shared edit.`

Finish with:

```markdown
Fresh verification at the current PR head includes the complete Feature Forge suite, the Feature Forge-Review Loop boundary, the complete Review Loop suite, repository packaging/documentation/plugin gates, strict plugin validation, Python compilation, and `git diff --check`. Exact results are recorded in the new dated qualification record; historical qualification evidence remains unchanged.
```
