# Feature Forge PR #7 review-remediation qualification — 2026-09-12

Status: deterministic qualification complete. This dated evidence record is non-authoritative;
the live skill and owner references define operation. Earlier plans, designs,
qualification records, and historical evidence are unchanged.

## Scope and exact revision coverage

The frozen [remediation plan](../../../docs/superpowers/plans/2026-09-12-feature-forge-pr7-review-remediation.md)
defines this work. Fresh verification below covers the following exact committed
production/test changes, together with this Task 8 documentation and shared-fixture
diff applied to baseline `21e7cc87f404a162042ffd252644b637e205a339`.
Task 8 adds no production behavior. Its commit is the commit introducing this
record; the exact tested production/test revisions are listed independently so
the record does not require its own future commit ID.

| Task | Exact commit | Change |
| --- | --- | --- |
| 1 | `6b5ce0efad69afd5a6df141194387951d6765dc9` | Harden Git observations and frozen identities |
| 2 | `a01e966bef4912f9d8550502784b0b3dc0be0d4d` | Reject unsupported transforming attributes |
| 3 | `28479dd4fcec7bb2cd6f5772e72ba631f5eea24f` | Review returns and persisted recovery |
| 3 fix | `18d5d46a87a3c39000f2b3b44818dc50b6685eb8` | Validate recovered head shape |
| 4 | `dc2bbe6a8b732616059c9a75ffe1f0896d68c5c1` | Task completion and terminal identity |
| 4 fix | `6bedc0812368c4f14abb862c843de1a5b06d319c` | Validate standalone frozen shape |
| 5 | `ab0ce709f6fa0d14fb72c23f8b6e113b86362225` | Canonical reviewed content and clean checkpoint 7 |
| 5 fix | `7f9f916c4d5635df0c72ac1f0b577ad2b2a9a615` | Symlink ancestors and target bootstrap gates |
| 6 | `10d2d7334f4f8e7efe1b9e5cf6972efff848b74d` | Trusted scoring and owned process cleanup |
| 7 | `45c4c622702c4ce679508f49f03ae53f9135ac1e` | Bubblewrap-visible test Python resolver |
| 7 fix | `21e7cc87f404a162042ffd252644b637e205a339` | Require executable resolver candidates |

The local PR base used for diff verification is
`origin/main = 1b673eee33a9cbc360e909e3ca0015c47d65a96c`. This is local verification,
not evidence of a subsequent pushed PR head, CI result, or completed whole-diff
review. Independent final review, push, and PR response remain controller handoff
steps.

## Focused development evidence

The observations in this section are carried forward from the task workers'
dated reports in the controller's ignored SDD workspace, not rerun REDs or claims
that this evidence-only task repeated TDD. Test names below identify retained
regressions; numeric results describe the actual selected development runs.
Fresh complete-suite verification is recorded separately below.

### Task 1: Git and frozen identity

For each row, the command is `python3 -m pytest <node(s)> -q`, with paths under
`feature-forge/tests/`.

| Nodes | Observed RED | Observed GREEN |
| --- | --- | --- |
| `test_ff_check_identities.py::test_identities_requires_each_frozen_blob_at_its_canonical_head_path` | 2 failed: dangling and staged-only blobs incorrectly passed | 2 passed |
| `test_ff_check_audit.py::test_strict_receipt_rejects_whitespace_only_identities` and `test_ff_check_audit.py::test_audit_rejects_whitespace_only_review_identities_without_a_traceback` | 8 failed: whitespace accepted | 8 passed |
| `test_ff_check_runs.py::test_runs_treats_deep_json_head_as_unverifiable_without_a_traceback` | 1 failed: uncaught `RecursionError` | 1 passed |
| `test_ff_check_runs.py::test_runs_preserves_a_repository_path_ending_in_a_space` | 1 failed: trailing space stripped | 1 passed |
| `test_ff_check_runs.py::test_every_git_subprocess_uses_the_hardened_argv_and_environment_policy` | 1 failed: ambient routing/config and absent hooks override | 1 passed |

Process-evidence exception: the identity-level frozen-blob RED above was genuine.
The audit consumer test
`test_ff_check_audit.py::test_audit_rejects_a_staged_only_frozen_blob` observed
1 failure only after the existing shared binding was temporarily removed, then
1 pass after restoration. That consumer RED was reconstructed after the shared
behavior existed and is **not compliant TDD evidence**, despite the earlier
worker report's description of a strict cycle. The earlier report is preserved;
this record corrects its characterization. The regression still contributes
current GREEN coverage.

Post-GREEN dead-code/path-observer consolidation had no manufactured RED.
The first combined suite exposed an old EOL fixture freezing uncommitted blobs
(520 passed, 1 failed); committing those fixture blobs restored its original
assertion. Final focused Task 1 suites: 522 passed; component: 718 passed,
1 skipped.

### Task 2: attribute-first rejection

`python3 -m pytest` on the two identity nodes
`test_identities_rejects_transforming_attributes_before_hashing` and
`test_identities_rejects_builtin_eol_normalization_for_frozen_files` with `-q`
observed 6 failed, then 6 passed. Built-in transformations reached hashing or
passed normalization; filter classification did not match the common gate.

The snapshot nodes `test_reviewed_snapshot_rejects_transforming_attributes_before_conversion`,
`test_reviewed_snapshot_checks_attributes_with_nul_delimited_tracked_paths`, and
`test_reviewed_snapshot_preserves_byte_exact_content_without_transforming_attributes`
observed 8 failed, 1 passed, then 9 passed. The passing binary-content case was
characterization. Drivers literally named `unset`/`unspecified` and newline
paths were included; conversion/filter markers stayed absent after GREEN.
Final two owning suites: 134 passed; component: 728 passed, 1 skipped.

### Task 3: return projection and recovery

Focused `python3 -m pytest ... -q` groups in audit/runs recorded:

| Group | RED | GREEN |
| --- | --- | --- |
| `test_audit_does_not_pass_a_populated_review_active_head`, `test_review_must_block_uses_the_post_return_round_and_consecutive_ids`, `test_runs_does_not_classify_review_active_as_resumable` | 6 failed: active review passed and shared predicate absent | 7 passed after correcting the third-round literal before implementation |
| `test_recovery_validates_then_projects_completed_review_returns`, `test_recovery_pretriage_block_retains_both_finding_histories`, `test_recovery_rejects_malformed_mismatched_or_source_divergent_receipts` | 8 failed: recovery function absent | 8 passed |
| Historical implementation recovery/invalid source commit | 3 failed, 1 passed: foreign descendants and noncanonical/unresolvable commits accepted | 8 passed including returned-audit and existing correction coverage |
| `test_audit_rejects_an_implementation_return_after_a_foreign_descendant_change` | 1 failed | Included in preceding 8-pass GREEN |
| Fix: `test_recovery_rejects_malformed_active_review_heads_without_an_exception` | 3 failed, 2 passed: missing keys raised, negative/boolean rounds accepted | 5 passed; malformed histories were characterizations |

In `review-loop`, `uv run pytest
../feature-forge/tests/integration/test_review_loop_boundary.py::test_same_kind_pretriage_block_retains_round_and_both_finding_histories -q`
first failed because histories were lost, then failed at `review=premature-block`
after projection was corrected, and finally passed after aligning receipt audit.
Final fix-round audit/runs: 492 passed; owning boundary: 25 passed.

### Task 4: completion and terminal identity

`python3 -m pytest feature-forge/tests/test_ff_check_audit.py -q -k
'noncomplete_task_progress_during_stage_9 or requires_complete_task_evidence_at_stage_10_and_later'`
observed 4 failed, 3 passed, then 7 passed. The Stage 9 cases characterized
permitted incomplete states. The owning runs test
`test_runs_rejects_an_incomplete_stage_10_ledger_before_classifying_it_resumable`
observed 1 failed, then 1 passed.

Terminal checkout/ancestry selection observed 4 failed, 2 passed, then 6 passed.
Missing terminal implementation pass and independently advanced primary-base
merge each had a separate 1-failure/1-pass cycle. Fix-round
`test_identities_rejects_malformed_frozen_shape_without_a_traceback` observed
1 failure (`AssertionError`), then passed with the Stage 9 expansion (6 passed
combined). Final focused audit/runs/identities: 562 passed.

### Task 5: committed integrity and checkout readiness

The snapshot owner ran with `python3 -m pytest
feature-forge/tests/test_ff_check_reviewed_snapshot.py -q` and these `-k` selectors:

| Selector/group | RED or characterization | GREEN |
| --- | --- | --- |
| Baseline, no selector | Characterization only | 82 passed |
| `owner_execute or autocrlf or exact_symlink or explicitly_rejects_gitlinks or excludes_an_ignored` | 5 failed, 4 passed: ignored exclusion, owner execute, raw CRLF, explicit gitlink refusal; symlink targets and other mode bits already passed | Full owner 90 passed |
| `controller_copy or deletion_with_newline or staged_change_even` | 1 failed, 3 passed: allowed report copy falsely implicated source | Full owner 94 passed |
| `stage_14_entry_requires_checkpointed` | 2 failed: dirty checkpointed ledger/receipt accepted | Both passed |
| `attribute_gate_includes_head` | 1 failed: staged deletion bypassed attribute classification | Passed |
| `autocrlf` during self-review | 2 failed, 1 passed: frozen-authority comparison still normalized | 3 passed |
| Nested symlink ancestor, non-ignored | Passed immediately; ordinary untracked enumeration already rejected it | 1 passed |
| Fix: `symlink_target_comparison_requires` | 1 failed, 1 passed: ignored ancestor symlink bypassed target comparison | 2 passed |

Two initial newline-deletion failures were an assertion helper's line-sorting
assumption; they were corrected before recording the intended copy RED.
They were not production defects.

The public Controller boundary ran in `review-loop` with `uv run pytest
../feature-forge/tests/integration/test_review_loop_boundary.py -q`:

- `-k first_implementation_pass`: a missing fixture Finish-journal heading
  initially caused `task-table=unsupported`; fixture correction produced pass.
  This is fixture development and deterministic instruction-recipe evidence,
  not a production RED. It exercised first-round pass, canonical bytes/modes,
  frozen inputs, symlink manifest, and one clean checkpoint-7 commit.
- `-k materialization_blocks`: 1 failed, 4 passed; the recipe omitted deleted
  base symlinks. Recipe correction yielded a complete 31-pass boundary suite.
- Fix `-k bootstrap_rechecks`: 2 failed, then 2 passed. Source-only attribute
  overrides disappeared in the temporary target; a real filter marker executed
  before target-context gating was added, and remained absent afterward.
- Fix `-k bootstrap_rejects_staged`: 2 failed after real injected index blob/mode
  mutation. Exact staged-tree verification then gave 4 passed with `-k bootstrap`.

Final fix-round checker suites: 663 passed; public boundary: 35 passed.
Materialization remains a controller-owned instruction recipe exercised by
repository-only fixtures; no new production materializer command was added.

### Task 6: qualification execution and finding #23

Commands ran from the repository root. Focused oracle groups used
`python3 -m pytest feature-forge/tests/test_behavior_oracle.py
feature-forge/tests/test_remediation_pressure.py -q -k <selection> --tb=short`.

| Selection/group | RED | GREEN |
| --- | --- | --- |
| Residual seed compatibility (pressure owner only, `-k residual_seed`) | 1 failed; baseline pressure suite had 28 failed, 52 passed | 1 passed after expecting exact active-review audit non-pass |
| `nonzero_model or never_executes_replaced or configured_programs or rejects_transformations` | 16 failed, 1 passed; execution markers, nonzero exits passing, absent unsupported classification | Included in combined 26-pass GREEN |
| `ambient_routing or model_configured_filter` (pressure owner) | 7 failed: six routing failures and filter marker execution | Included in combined 26-pass GREEN |
| Combined preceding selections plus `residual_seed or timeout_23` | Intended failures recorded before implementation | 26 passed |

Finding #23 was reproduced before adding process-group machinery:
`python3 -m pytest feature-forge/tests/test_remediation_pressure.py -q -k timeout_23 --tb=short`
gave 1 failed, 95 deselected in 3.53s; the delayed child's marker appeared after
timeout/scoring. After implementation and readiness/TERM-ignore strengthening,
the same command gave 2 passed, 102 deselected in 8.11s. The stronger checks
needed no additional production change or manufactured RED.

The runner terminates its owned process group with TERM, waits a 0.25-second
grace period, sends KILL if needed, and waits/reaps its direct model process
before scoring. It does this on timeout and normal return. This is an owned
process-group cleanup guarantee; a descendant deliberately starting another
session can escape it. It does not reap arbitrary descendants or supply a
general hostile-process sandbox.

The first broader run found 1 failed, 132 passed because an old fixture metadata
assertion still required active-review audit to pass. Aligning that assertion
did not weaken semantic scoring. Final oracle owners: 134 passed; component:
810 passed, 1 skipped. Tasks 3–5's complete component runs had respectively
28 failed/713 passed/1 skipped, 28 failed/732 passed/1 skipped, and
28 failed/751 passed/1 skipped due to this known residual-minor preparation
dependency. Task 5's full run preceded its last frozen-byte adjustment; its
final focused suites, not that earlier run, established that adjustment.
Task 6 resolved the 28 failures; none is silently omitted from prior evidence.

### Task 7: test-only interpreter portability

In `review-loop`, `uv run --offline pytest
tests/integration/test_execution_containment.py::BubblewrapVisiblePythonResolverTests -q`
first failed collection because `containment_test_helpers` did not exist, then
gave 2 passed. The executable-candidate fix first gave 5 failed (missing
`is_usable` argument and predicate), then 5 passed.
Final task-owned containment modules: 15 passed, 1 skipped and 8 passed.
Production Bubblewrap mappings were unchanged. Missing usable `/usr` Python
now produces an explicit skip; candidates must be regular executable files.

### Task 8: shared fixture and contract evidence

Finding #35 was implemented because both snapshot-helper owners changed in
Tasks 1–5. Their byte-identical `fixture_snapshot` bodies moved into the existing
`feature-forge/tests/conftest.py`; the two owners only remove their copies and
import the shared helper. No test namespace caching or matrix restructuring
was added.

Characterization command, before and after:
`python3 -m pytest feature-forge/tests/test_ff_check_audit.py
feature-forge/tests/test_ff_check_reviewed_snapshot.py -q`.
Before: **534 passed in 63.57s**. After: **534 passed in 77.32s**.
No behavioral test or artificial RED was added for this refactor/prose task.
The workflow defines the common post-review gate once, references it at
Stages 11–14, and preserves each stage's owned action and failure routing.

The first full component run after documentation consolidation gave **1 failed,
809 passed, 1 skipped in 177.30s**. The existing
`test_ledger_schema.py::test_stage_gate_sequences_match_the_approved_map`
requires command-name tokens in each stage's mechanical-check sentence and
does not resolve cross-references. The references now retain compact ordered
command labels while the common gate owns the rules once. The exact focused
node rerun gave **1 passed in 0.14s**. This was a documentation compatibility
failure discovered during verification, not a planned behavioral RED cycle.

## Fresh complete verification

Commands run from the repository root unless `review-loop` is named as cwd.
All results in this section are fresh Task 8 observations, not copied totals.

| Command | Result |
| --- | --- |
| `python3 -m pytest feature-forge/tests -q`, final rerun after command-label correction | 810 passed, 1 skipped in 166.98s; exit 0 |
| In `review-loop`: `uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q` | 35 passed in 14.91s; exit 0 |
| In `review-loop`: `uv run pytest -q`, restricted sandbox attempt | 27 failed, 488 passed, 1 skipped in 23.29s; exit 1 |
| In `review-loop`: `uv run pytest -q`, host-permitted rerun | 515 passed, 1 skipped in 26.23s; exit 0 |
| `python3 -m pytest tests/test_install.py -q` | 11 passed in 0.48s; exit 0 |
| `python3 -m pytest tests/test_documentation.py -q` | Initial 20 passed in 0.17s; final record rerun 20 passed in 0.19s; exit 0 |
| `python3 -m pytest tests/test_plugin_agents.py -q` | 2 passed in 0.20s; exit 0 |
| `claude plugin validate . --strict` | Validation passed for marketplace manifest; exit 0 |
| `python3 -m pytest tests -q` | Initial 33 passed in 0.36s; final record rerun 33 passed in 0.40s; exit 0 |
| `python3 -m py_compile feature-forge/scripts/ff-check feature-forge/tests/behavior/identity_drift.py feature-forge/tests/behavior/remediation_pressure.py` | Exit 0, no output |
| `git diff --check origin/main...HEAD` | Exit 0, no output; committed comparison ends at baseline before Task 8 commit |
| `git diff --check` | Exit 0, no output for Task 8 working diff |
| `git status --short --branch` | `feature-forge-mvp...origin/feature-forge-mvp [ahead 12]`; four owned modified paths and only this new untracked record |
| `git diff --cached --check`, explicit cached diff/path and mode review | Exit 0; exactly the workflow, shared fixture, two fixture owners, and this new record staged; all regular `100644`, no symlink changes |

Precommit self-review confirmed the helper body is byte-identical to the prior
audit owner, the other owner only changes its import/removes the duplicate,
and the shared gate preserves stage-specific actions and failure routing.
The frozen plan and every earlier tracked design/qualification record remain
unchanged. A second status review after explicit staging showed only these
five staged paths and no unstaged changes. Postcommit status/diff evidence is
returned in the controller's Task 8 report; no later PR/CI outcome is inferred.

The restricted Review Loop failures were diagnosed at the execution boundary:
`bwrap --ro-bind / / --unshare-net -- /usr/bin/true` reported
`bwrap: loopback: Failed to create NETLINK_ROUTE socket: Operation not permitted`.
The failing socket seal test also raised `PermissionError` on Unix-socket bind.
The restricted attempt is retained above; the identical suite was rerun with
host permissions for its required Bubblewrap/socket execution. No production
mapping or test expectation was changed to accommodate the sandbox.

## Skips, unavailable evidence, and retained boundaries

- Root Python lacks `review_loop`, so the Feature Forge boundary module skips
  there; the owning `uv` environment's separate boundary run supplies evidence.
  Explicit diagnostic `python3 -m pytest
  feature-forge/tests/integration/test_review_loop_boundary.py -q -rs` gave
  1 skipped in 0.14s, exit 5 (no collected tests):
  `could not import 'review_loop': No module named 'review_loop'`.
- Review Loop's ordinary containment scope test intentionally skips
  evidence-gate/FIX mapping, which is outside that fixture's ordinary-mapping
  scope. Diagnostic `uv run pytest
  tests/integration/test_execution_containment.py -q -k evidence_gate_and_fix_mappings -rs`
  in `review-loop` confirmed 1 skipped, 15 deselected in 0.03s, exit 0, with
  reason `evidence-gate/FIX mapping is out of scope for Task 5 (ordinary mapping only)`.
- Finding #22 remains deferred: real-directory/regular-file checks reject
  symlinks at observation time, but later reads are not descriptor-bound.
  Supported tracked symlinks retain their separate target and manifest checks.
  The controller must remain quiescent during gates; generalized concurrent
  external path replacement protection and race resistance are not established.
- Findings #29–31 (batch hashing and cached/shared gate contexts) and #33–34
  (namespace caching and lifecycle-matrix restructuring) remain deferred.
- Controlled paths declaring `filter`, `text`, `eol`, `ident`, or
  `working-tree-encoding` are unsupported, regardless of attribute value.
  Transformation support awaits a concrete supported repository requirement.
- Gitlinks are unsupported. Ignored/untracked material is outside the reviewed
  tracked tree; ordinary untracked dirt still fails readiness where required.
  Git endpoint comparisons do not reconstruct fully reverted intermediate changes.
- Local-merge terminalization is supported only in the primary base checkout;
  linked base checkouts remain unsupported. The checker validates terminal
  topology; the controller retains responsibility for matching the journaled
  Finish choice and preserving original feature identity in existing evidence.
- Finding #6 retains usable partial Round 1 reports only when `run_round1`
  returns a `Round1Outcome`. An exception before that return exposes no usable
  partial inventory; no Review Loop API was added.
- Finding #23 excludes escaped sessions and arbitrary-descendant reaping as
  described above. These qualification controls are not a general sandbox.
- Finding #35 is implemented as the bounded helper move, not deferred.
- No stochastic LLM campaign was run. Dispatched pressure prompts, expected
  semantic decisions, and semantic output contracts did not change.
  Deterministic local executables and synthetic semantic roles verify wiring
  and execution boundaries, not new model-behavior success rates or human UAT.
- Task 1's reconstructed consumer RED is unavailable as compliant TDD evidence;
  its genuine identity-level RED and retained GREEN regression remain explicit.

No schema version, checker command, durable artifact type, Review Loop API,
installation, or runtime Bubblewrap mapping was added by this remediation.
