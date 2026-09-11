# Feature Forge PR #7 Remediation Implementation Plan

**Status:** Approved for execution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Feature Forge PR #7 merge-ready by integrating current `main`, closing the approved checked-state and review-return defects, and qualifying every affected LLM dispatch without expanding Feature Forge into a workflow engine.

**Architecture:** Preserve Feature Forge's instruction-driven outer controller, one version-one ledger, and one read-only Python standard-library checker. Put Git, path, schema, set, result, round, and identity predicates in `ff-check`; leave material equivalence and other semantic judgments in small bounded LLM calls whose outputs are mechanically validated. Reuse Review Loop only through its public read-only path ending at TRIAGE.

**Tech Stack:** Markdown skill/reference files, Python 3 standard library, pytest, Git, the existing `review_loop` Python package and public `Controller`, Codex CLI, Claude Code CLI.

**Spec:** [Feature Forge PR #7 Remediation Design](../specs/2026-09-06-feature-forge-pr7-remediation-design.md)

## Global Constraints

- Work only in the existing isolated `feature-forge-mvp` worktree; verify it with `superpowers:using-git-worktrees` before implementation.
- Treat the approved remediation specification as binding. The earlier checked-skill MVP design remains authoritative only where the remediation specification does not supersede it.
- Merge current `origin/main`; do not rebase or force-push. Preserve PR #8's Review Loop contracts and accept PR #9's Review Team state from `main` without alteration.
- Keep one version-one ledger and one standard-library `ff-check`; do not add a workflow engine, daemon, hook, prompt compiler, second state artifact, fifth operational checker command, historical-ledger migration, or Review Loop FIX/adjudication/promotion/challenge/CLOSE integration.
- Use `superpowers:test-driven-development` for every deterministic behavior change: observe a focused failure for the intended reason before production implementation, then observe it pass.
- Use `superpowers:writing-skills` for behavior-shaping instruction changes: Task 2 records the post-integration/no-remediation baseline; Task 6 changes guidance only for a demonstrated behavior gap and reruns the same immutable scenarios. Schema and contract synchronization does not require an artificial behavioral failure.
- The North Star is: “LLM output quality is maximized by small, well scoped, clearly bounded tasks with clear goal conditions.” Packet bytes and words are diagnostic only, never a quota or pass/fail gate.
- A finding is a grounded discrepancy against an approved requirement, correctness condition, applicable repository contract, or required verification result. Preferences, optional enhancements, and speculative improvements are not findings.
- Use code for deterministic facts and LLM inference only for material-equivalence or other semantic judgments. Every LLM task has one job, exact inputs and authority, a strict output contract, an observable goal, and an explicit blocked/failure condition.
- Do not edit frozen plan checkboxes during execution. The SDD workspace ledger owns progress, task commits, review rounds, and rulings.
- SDD implementers do not dispatch helper or reviewer subagents. Codex/Claude subprocesses explicitly named as behavior-test subjects in Tasks 2 and 6 are test executions, not implementation or review delegation.
- Preserve unrelated work. Use the safe patch/edit facility for hand edits, stage only the explicit paths named by the current task, and never use `git add .` or `git add -A`.
- Run commands from the repository root unless a step explicitly enters `review-loop`. Run `superpowers:verification-before-completion` before any completion claim, commit intended for handoff, or push.
- Stop after pushing the repaired branch to PR #7. Do not merge PR #7.

## File and Interface Map

| Unit | Responsibility | Owned task |
| --- | --- | --- |
| `feature-forge/scripts/ff-check` | Four read-only operational gates; exact ledger/receipt/path/Git predicates; deterministic stable-ID formula and validation | Tasks 3–5, sequentially |
| `feature-forge/assets/ledger-template.md` | Copy-time version-one head with checked `mode` | Task 3 |
| `feature-forge/references/workflow.md` | Ledger/state lifecycle, identities gates, stage contracts | Tasks 3 and 5; Task 6 may only simplify equivalent prose |
| `feature-forge/references/adapters-and-reviews.md` | Worker packet, review charter/return, stable-ID, and receipt contracts | Task 5; Task 6 may only simplify equivalent prose |
| `feature-forge/SKILL.md` | Concise entry point and controller boundary | Task 6 |
| `feature-forge/CLAUDE.md` | Component maintainer and verification commands | Task 6 |
| `feature-forge/tests/conftest.py` | Canonical valid head and Git fixture helpers | Task 3; later tasks consume without renaming |
| `feature-forge/tests/test_ff_check_audit.py` | Head, lifecycle, review/receipt, and audit regressions | Tasks 3 and 5, sequentially |
| `feature-forge/tests/test_ff_check_identities.py` | Base ancestry and safe identity/path regressions | Tasks 3 and 4 |
| `feature-forge/tests/test_ff_check_runs.py` | Repository-scoped run/worktree inventory regressions | Task 4 |
| `feature-forge/tests/test_ff_check_reviewed_snapshot.py` | Strict receipt and reviewed-snapshot regressions | Task 5 |
| `feature-forge/tests/integration/test_review_loop_boundary.py` | Public Review Loop through-TRIAGE adapter fixture and controller-return provenance | Task 3 schema compatibility, then Task 5 behavior |
| `feature-forge/tests/behavior/identity_drift.py` | Existing installed-checker drift fixture; reuse of Task 2's schema-aware valid seed builder | Task 3; Task 5 verifies unchanged |
| `feature-forge/tests/test_behavior_oracle.py` | Existing drift-fixture compatibility gate | Tasks 3 and 5 |
| `feature-forge/tests/behavior/remediation_pressure.py` | Test-only preparation/scoring for the three remediation pressure scenarios | Task 2; Task 6 may correct Claude GREEN transport only, preserving baseline invocation and scorer semantics |
| `feature-forge/tests/behavior/pr7-remediation/` | Immutable prompts and fixture inputs for the three pressure scenarios | Task 2; Task 6 consumes unchanged |
| `feature-forge/tests/test_remediation_pressure.py` | Deterministic oracle unit tests for scenario preparation/scoring and host transport | Task 2; Task 6 adds authorized adapter regressions |
| `feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md` | One compact baseline, GREEN comparison, prompt inventory, metrics, and final verification record | Task 2 creates; Tasks 6–7 append only |

## Sequential Dependency and Ownership Table

| Producer | Consumer | Contract handed forward | Shared surface/ruling |
| --- | --- | --- | --- |
| Task 1 | Tasks 2–7 | Tested merge commit containing current PR #8 and PR #9 state | Later tasks never reopen Review Loop conflict resolutions except to fix a demonstrated integration defect |
| Task 2 | Tasks 5–6 | Immutable scenario files (including delegated and inline drift variants), scorer interface, installed-payload digest, and baseline observations | Task 5 changes the live Stage 9 contract while consuming the frozen tests; Task 6 reruns exact inputs and never rewrites the baseline or scorer |
| Task 3 | Task 4 | Unchanged public checker CLI/result contract plus `repository()`, `linked_worktree()`, `worktrees()`, and `audit_current_head()` signatures | Task 4 adds the shared path-error boundary and may harden internals but may not change these signatures or lifecycle semantics |
| Task 3 | Task 5 | `REVIEW_STAGE_RULES`, `required_frozen_authorities()`, checked `mode`, and exact head compatibility rules | Task 5 adds receipt semantics without reopening status/stage/next-action decisions |
| Task 4 | Task 5 | Final safe path observation and repository-scoped inventory helpers | Task 5 uses the helpers for receipt paths and never adds a second path-validation stack |
| Task 5 | Task 6 | Exact receipt fields, stable-ID formula, all-findings return rule, and pre/post-task identities contract | Task 6 may shorten wording but may not alter these semantics |
| Task 6 | Task 7 | Final installed payload, GREEN evidence, seven-shape rubric table, and any explicitly unresolved qualification item | Task 7 verifies; it adds no production behavior |

## Controller-Owned Post-Task Gate

This section is not an implementation task and is deliberately placed before
the numbered task headings so `task-brief` cannot include it in any worker
brief. The SDD controller performs it only after Task 7's implementer has
reported, Task 7's task review is approved, and all seven task completion lines
are in the SDD ledger.

- [ ] **Controller Step 1: Run the mandatory SDD whole-branch review**

Use `superpowers:requesting-code-review` on the most capable available model with a review package covering `origin/main...HEAD`. Point the reviewer to the approved specification, this plan, the SDD ledger's deferred/parked findings, and the qualification record. Fix any Critical/Important issue through the SDD final one-wave fix/re-review procedure; do not let the controller edit fixes directly.

- [ ] **Controller Step 2: Refresh evidence after any final-review fix**

If the final review produces a fix, the single final-fix implementer first
commits the production correction, then runs every focused test covering it
plus the complete Feature Forge, Review Loop, documentation, installer,
plugin-agent, and root gates from Task 7. If any installed Feature Forge
payload changed, reinstall that exact payload into fresh fixtures and rerun
both complete immutable pressure campaigns; if a dispatch composition changed,
recompose and re-review its affected packet family with the Task 6 rubric.
Append the new results without rewriting prior evidence and create a separate
evidence-only commit that records the production fix commit's identity. One
final-fix dispatch may therefore produce those two ordered commits. The scoped
re-review judges both commits and the refreshed evidence. Afterward, the
controller reruns the exact documentation gate, `git diff --check
origin/main...HEAD`, and status.

If there is no fix, the Task 7 evidence remains current for production files;
the controller still checks the evidence-only commit with the documentation,
diff, and status gates before proceeding.

- [ ] **Controller Step 3: Verify once more, then push without merging**

After `superpowers:verification-before-completion` confirms the post-review `HEAD` and clean worktree, run:

```bash
git push origin HEAD:feature-forge-mvp
```

Then verify PR #7 points at the pushed head and report its checks. The user has
explicitly authorized the commit and push operations required by this plan.
Do not merge PR #7.

---

### Task 1: Integrate Current `main` Without Regressing Review Loop

**Files:**
- Modify on conflict only: `review-loop/SKILL.md`
- Modify on conflict only: `review-loop/review_loop/resources/inventory.md`
- Modify on conflict only: `review-loop/review_loop/resources/review.md`
- Modify on conflict only: `review-loop/tests/unit/test_role_contracts.py`

**Interfaces:**
- Consumes: current remote refs `origin/main` and `origin/feature-forge-mvp`; the four conflict paths named above; PR #8's public `Controller.create_run` → `run_stage0` → `run_round1` → `run_triage` contract.
- Produces: one merge commit with two parents, no rewritten PR #7 history, PR #8 behavior preserved, and a passing complete Review Loop suite before remediation changes.

- [ ] **Step 1: Verify the worktree and refresh the exact merge inputs**

Run:

```bash
git status --short --branch
git fetch origin main feature-forge-mvp
git rev-parse HEAD origin/feature-forge-mvp origin/main
git rev-list --left-right --count HEAD...origin/feature-forge-mvp
```

Expected before merging: only the reviewed specification/plan commits may place local `HEAD` ahead of `origin/feature-forge-mvp`; the worktree has no uncommitted paths. Record all three object IDs in the SDD report.

- [ ] **Step 2: Preview and classify the merge conflicts**

Run:

```bash
git merge-tree "$(git merge-base HEAD origin/main)" HEAD origin/main
```

Expected: the only textual conflicts are the four Review Loop paths listed in this task. If another conflict appears, stop this task as `DONE_WITH_CONCERNS` before merging and name the path; it changes the reviewed integration surface.

- [ ] **Step 3: Merge without rebasing**

Run:

```bash
git merge --no-ff --no-commit origin/main
```

Expected: Git pauses on the predicted conflicts or stages a conflict-free merge
without committing it. Do not use `git rebase`, `git reset`, or a force option.

- [ ] **Step 4: Resolve each conflict against the live PR #8 contract**

For each conflicted file, retain the `origin/main` Review Loop lifecycle, role wording, and test expectations. Reapply only Feature Forge composition text that still calls the public path through `run_triage` and does not reintroduce FIX, adjudication, promotion, final challenge, or CLOSE. Inspect the staged resolution explicitly:

```bash
git diff --check
git diff -- review-loop/SKILL.md \
  review-loop/review_loop/resources/inventory.md \
  review-loop/review_loop/resources/review.md \
  review-loop/tests/unit/test_role_contracts.py
```

- [ ] **Step 5: Run Review Loop's complete owning suite before any remediation**

Run:

```bash
cd review-loop
uv run pytest -q
```

Expected: PASS, with only documented environment skips. Any failure must be fixed in the four conflict paths or returned as a Task 1 concern; do not begin Feature Forge remediation on a failing merge.

- [ ] **Step 6: Complete and verify the merge commit**

Stage only the four resolved paths and complete the paused merge noninteractively:

```bash
git add review-loop/SKILL.md \
  review-loop/review_loop/resources/inventory.md \
  review-loop/review_loop/resources/review.md \
  review-loop/tests/unit/test_role_contracts.py
git commit -m "Merge origin/main into feature-forge-mvp"
git show --no-patch --format='%P%n%s' HEAD
```

Expected: exactly two parent IDs and a merge subject naming `origin/main`.

---

### Task 2: Freeze the Three-Scenario No-Remediation Baseline

**Files:**
- Create: `feature-forge/tests/behavior/remediation_pressure.py`
- Create: `feature-forge/tests/behavior/pr7-remediation/cases.json`
- Create: `feature-forge/tests/behavior/pr7-remediation/worker-packet.md`
- Create: `feature-forge/tests/behavior/pr7-remediation/residual-minor.md`
- Create: `feature-forge/tests/behavior/pr7-remediation/post-task-plan-drift.md`
- Create: `feature-forge/tests/test_remediation_pressure.py`
- Create: `feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md`

**Interfaces:**
- Consumes: Task 1's merge commit and exact installed Feature Forge payload; no remediation instruction or checker edit.
- Produces: immutable scenario bytes plus schema-aware fixture construction, `prepare`/`score`/`campaign` commands, one payload digest, eight fresh baseline observations (one required Codex and one corroborating Claude run for worker packet, residual Minor, delegated drift, and inline drift), manual rubric judgments, and no behavior guidance.
- `python3 feature-forge/tests/behavior/remediation_pressure.py prepare --scenario NAME --root DIR --host HOST [--execution-mode MODE]` accepts `NAME` in `worker-packet | residual-minor | post-task-plan-drift`, `HOST` in `codex | claude`, and requires `MODE` in `delegated | inline` only for plan drift. It creates one disposable fixture and prints a JSON object with `repo`, `prompt`, `response`, `baseline_head`, `payload_digest`, `installed_skill_root`, `protected_paths`, `scenario`, and nullable `execution_mode`.
- `python3 feature-forge/tests/behavior/remediation_pressure.py score --root DIR` prints one JSON verdict with `scenario`, `passed`, `failures`, `head_preserved`, `protected_paths_preserved`, `payload_digest_preserved`, and `unexpected_status_paths`; only deterministic predicates contribute to `passed`.
- `python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase PHASE --host HOST` accepts `PHASE` in `baseline | green`, creates one fresh temporary fixture per scenario, invokes the pinned host, scores each result, and prints a JSON array containing all paths and verdicts. It never deletes the fixtures.

- [ ] **Step 1: Write the scenario registry and exact prompts**

Store exact fixture facts in `cases.json`; do not generate requirements with an LLM. Use this schema and values:

```json
{
  "schema": "feature-forge/pr7-remediation-pressure/v1",
  "worker-packet": {
    "task_id": "W-4",
    "requirement_ids": ["REQ-001"],
    "scenario_ids": ["SCN-001"],
    "owned_paths": ["src/tenant/normalize.ts", "tests/tenant/normalize.test.ts"],
    "producer": {"task_id": "W-2", "commit": "c222", "verification": "npm test -- tenant.types"},
    "consumes": "export type CanonicalTenant = { id: string; displayName: string }",
    "produces": "export function normalizeTenantName(tenant: CanonicalTenant): string",
    "invariant": "trim displayName and collapse internal whitespace to one ASCII space; never write tenant.id",
    "verification": "npm test -- tenant.normalize"
  },
  "residual-minor": {
    "review_kind": "specification",
    "dispatch_id": "specification-2",
    "triage_artifact_id": "triage-2",
    "raw_report_ids": ["report-empty", "report-minor"],
    "triage_finding_ids": ["TRIAGE-MINOR-1"],
    "severity": "Minor",
    "grounded_claim": "REQ-007 has no verification command"
  },
  "post-task-plan-drift": {
    "stage": 9,
    "task_id": "W-2",
    "execution_modes": ["delegated", "inline"],
    "frozen_plan": "docs/superpowers/plans/2026-09-09-alpha.md",
    "expected_next_action": "reconcile or correct docs/superpowers/plans/2026-09-09-alpha.md"
  }
}
```

The worker prompt asks for only the dispatch packet. The residual-Minor prompt asks for only the proposed strict receipt plus resulting head after the supplied public TRIAGE return. Each drift fixture selects exactly one execution mode and asks the controller to process a completed task return after the fixture modifies the frozen plan bytes and before that return is recorded complete. Each prompt requires use of the installed Feature Forge skill and forbids editing the fixture inputs.

- [ ] **Step 2: Write failing scorer tests before the harness**

Begin with black-box subprocess tests against the not-yet-created script so pytest reaches an assertion and reports the missing successful command as a failure rather than failing collection. Add tests that name the production behavior which will make each fail:

```python
def test_worker_packet_score_requires_every_interface_and_boundary(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "worker-packet")
    response_path(root).write_text("Dispatch W-4 to implement normalizeTenantName.\n")
    assert score(root)["failures"] == [
        "authority-boundary", "consumed-interface", "dependency-evidence",
        "failure-condition", "goal-condition", "owned-paths", "produced-interface",
    ]

def test_residual_minor_score_rejects_pass_and_missing_inventory(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "residual-minor")
    write_residual_response(root, result="pass", raw_report_ids=["report-minor"])
    assert score(root)["failures"] == ["all-findings-actionable", "raw-report-inventory"]

def test_post_task_drift_score_rejects_completion_or_forward_mutation(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode="delegated")
    mark_task_complete_and_commit(root)
    assert score(root)["failures"] == ["head-advanced", "task-return-recorded"]
```

Mirror the drift rejection for `execution_mode="inline"`. For every scenario add one complete conforming output that scores pass and one no-op or partial output that scores fail for the expected reason. The scorer must recompute the installed-payload digest, require exact scenario-specific Git-status allowlists, reject any unexpected repository mutation, and verify protected bytes and `HEAD`; response-only cases require a clean repository. Test helpers may build deliberately invalid subject outputs, but the scorer must inspect real files, exact JSON fields, Git state, and required string anchors. It must not assign a semantic rubric verdict.

- [ ] **Step 3: Run RED, implement the compact test-only harness, and run GREEN**

Run before creating `remediation_pressure.py`:

```bash
python3 -m pytest feature-forge/tests/test_remediation_pressure.py -q
```

Expected RED: pytest runs and fails an assertion because invoking the absent harness does not return success. Implement only the three commands and fixture/scoring helpers with Python standard library and the repository installer. Then rerun the same command; expected GREEN: PASS with pristine output.

- [ ] **Step 4: Prove preparation pins inputs and does not expose the oracle**

Add and pass tests that assert:

```python
assert metadata["payload_digest"] == payload_digest(installed_skill_root)
assert not any(path.name == "remediation_pressure.py" for path in installed_skill_root.rglob("*"))
assert prepared_prompt.read_bytes() == committed_prompt.read_bytes()
assert set(metadata["protected_paths"]) == {
    "docs/superpowers/specs/2026-09-09-alpha-design.md",
    "docs/superpowers/plans/2026-09-09-alpha.md",
}
assert score(root)["payload_digest_preserved"] is True
assert score(root)["unexpected_status_paths"] == []
```

For the drift case, the clean seed must pass current `ff-check audit`; preparation then changes only the frozen plan bytes. For the response-only cases, redirect host output to the response path outside the disposable repository.

Make the frozen fixture builder compatible with both known checker schemas. It
loads `HEAD_KEYS` and `RECEIPT_KEYS` from the copied installed `ff-check` with
`runpy`, rejects any key set other than the pre-remediation or approved set,
and emits exactly the fields required by that checker. Its Stage 9 clean seed
always uses a retained passing plan review—not `not_started`—so both the old and
new lifecycle accept it; include `mode: supervised` only when `HEAD_KEYS`
requires it, and include the expanded receipt evidence only when
`RECEIPT_KEYS` requires it. Unit-test both known key-set inputs before freezing
the harness. The Task 2 baseline proves the generated old-schema seed with the
live checker; Task 6 GREEN proves the generated new-schema seed with the
remediated checker. This compatibility logic is fixture setup, not a change to
scenario prompts, protected bytes, or scoring.

- [ ] **Step 5: Run one fresh baseline per scenario and host**

Confirm current CLI flags with `codex exec --help` and `claude --help`. Implement `campaign` with these exact argument arrays, substituting only the paths returned by its own `prepare` call:

```python
CODEX_ARGV = [
    "codex", "exec", "--ephemeral", "--model", "gpt-5.6-terra",
    "--config", 'model_reasoning_effort="medium"', "--approve-for-me",
    "--cd", str(metadata["repo"]), "-",
]
CLAUDE_ARGV = [
    "claude", "--print", "--no-session-persistence", "--model", "sonnet",
    "--effort", "medium", "--permission-mode", "acceptEdits",
    "--allowedTools", "Bash(git *) Bash(python3 *) Bash(sha256sum *)",
]
```

Pass the committed prompt bytes on stdin, capture stdout at the metadata response path and stderr beside it, set `cwd=str(metadata["repo"])` for both hosts, and set a 600-second subprocess timeout. Add a harness test proving each host subprocess observes the fixture repository and discovers the copied skill beneath that fixture, never the remediation worktree. Do not set process `HOME`, `CODEX_HOME`, or a fallback model.

Declare Codex `gpt-5.6-terra` at medium effort the required capable qualification host before observing any result. Claude `sonnet` at medium effort is corroborating: unavailability does not block, but an executed deterministic or rubric failure remains a real gap and cannot be erased by the Codex result. Record the requested alias and any concrete resolved model ID the CLI exposes; never claim the floating alias itself is an exact model ID. Run the two complete baseline campaigns:

```bash
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase baseline --host codex
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase baseline --host claude
```

Score each fixture after the host exits. Required-host failure or unavailability blocks qualification. Corroborating-host unavailability is recorded; a corroborating-host failure is classified and remediated like any other observed gap.

- [ ] **Step 6: Record the baseline without prescribing fixes**

Create the qualification record with: merge commit, scenario/input hashes, installed-payload hash, exact host versions/model/effort, invocation commands, deterministic verdicts, and manual North-Star rubric assessment for every response. Quote only short rationalization excerpts. Classify each scenario as `gap demonstrated`, `already correct`, or `unavailable`; do not write prospective instruction wording in this task.

- [ ] **Step 7: Commit the immutable baseline**

Run:

```bash
git diff --check
git add feature-forge/tests/behavior/remediation_pressure.py \
  feature-forge/tests/behavior/pr7-remediation/cases.json \
  feature-forge/tests/behavior/pr7-remediation/worker-packet.md \
  feature-forge/tests/behavior/pr7-remediation/residual-minor.md \
  feature-forge/tests/behavior/pr7-remediation/post-task-plan-drift.md \
  feature-forge/tests/test_remediation_pressure.py \
  feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md
git commit -m "test: record Feature Forge remediation baseline"
```

---

### Task 3: Check Mode, Base Ancestry, and the Current-Head Lifecycle

**Files:**
- Modify: `feature-forge/assets/ledger-template.md`
- Modify: `feature-forge/references/workflow.md`
- Modify: `feature-forge/scripts/ff-check`
- Modify: `feature-forge/tests/conftest.py`
- Modify: `feature-forge/tests/test_ledger_schema.py`
- Modify: `feature-forge/tests/test_ff_check_audit.py`
- Modify: `feature-forge/tests/test_ff_check_identities.py`
- Modify: `feature-forge/tests/test_ff_check_runs.py`
- Modify for head-schema compatibility only: `feature-forge/tests/integration/test_review_loop_boundary.py`
- Modify for installed-checker schema/lifecycle compatibility only: `feature-forge/tests/behavior/identity_drift.py`
- Modify if its compatibility assertions need synchronization: `feature-forge/tests/test_behavior_oracle.py`

**Interfaces:**
- Consumes: Task 2's immutable baseline; existing four-command checker CLI and literal `FF-CHECK v1` output contract.
- Produces: `mode` in `HEAD_KEYS`; `AUTOMATION_MODES = frozenset({"interactive", "supervised", "unattended"})`; `mode_error(data: dict[str, object]) -> str | None`; `base_identity_result(repo: Path, value: object) -> Result`; `REVIEW_STAGE_RULES`; `required_frozen_authorities(stage_id: int) -> tuple[str, ...]`; `head_transition_invariant(data: dict[str, object]) -> bool`; unchanged signatures for `repository`, `linked_worktree`, `worktrees`, and `audit_current_head`.

- [ ] **Step 1: Add `mode` schema tests and update only test fixtures**

First change the canonical `head()` fixture, the integration boundary's local `HEAD_KEYS`/`BoundaryFixture._head()`, and every other literal valid head to contain `"mode": "supervised"`. Add failing tests proving the template and all three head-consuming commands require the exact enum:

```python
assert head["mode"] == "supervised"
assert set(head) == {
    "schema", "run_id", "mode", "status", "worktree", "branch",
    "base_identity", "stage", "next_action", "frozen", "review",
}

@pytest.mark.parametrize("value", [None, "automatic", "SUPERVISED", 1])
def test_audit_rejects_missing_or_unsupported_mode(tmp_path: Path, value: object) -> None:
    repo, directory, data = audit_fixture(tmp_path)
    if value is None:
        data.pop("mode")
    else:
        data["mode"] = value
    write_ledger(directory, data)
    assert_result(invoke(repo, directory), "unverifiable", 2)
```

Repeat the missing/unsupported matrix through black-box `runs` and `identities` invocations. `mode_error()` is the one shared enum predicate; `run_head_error()`, `audit_head_shape()`, and `identities()` all call it rather than maintaining three lists.

Run RED:

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py \
  feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_runs.py \
  feature-forge/tests/test_ff_check_identities.py -q
```

Expected: failures identify the absent template/checker field, not malformed fixtures.

- [ ] **Step 2: Implement checked mode and synchronize the workflow contract**

Add `mode` to `HEAD_KEYS`, implement the shared `mode_error()` call in `run_head_error()`, `audit_head_shape()`, and `identities()`, and add the template default. In `workflow.md`, state that human evidence explains authority but never substitutes for the checked enum. Rerun the Step 1 command; expected: PASS.

- [ ] **Step 3: Add the base-ancestry regression before implementation**

Create a real same-repository commit that resolves but is not an ancestor of the fixture's current `HEAD`, store it in `base_identity`, and assert the same result through `identities`, `audit`, and a `runs` invocation over the matching resumable ledger:

```python
result = check("identities", "--repo", str(repo), "--run", str(directory))
assert_result(result, "fail", 1)
assert result.stderr.splitlines() == ["base-identity=not-ancestor"]
```

Also wrap `git merge-base --is-ancestor` to exit by signal and expect `unverifiable` with `base-identity=ancestry-unavailable` through all three paths. Run the new tests RED and confirm the unrelated resolvable commit is currently accepted.

- [ ] **Step 4: Enforce ancestry with Git and rerun GREEN**

Implement one shared `base_identity_result()` and call it from both `canonical_identity_claims()` and `identities()`:

```python
def base_identity_result(repo: Path, value: object) -> Result:
    identity = commit_identity(repo, value)
    if identity == "noncanonical":
        return result("fail", "base-identity=noncanonical")
    if identity == "unverifiable":
        return result("unverifiable", "base-identity=unresolvable")
    ancestry = git_status(repo, "merge-base", "--is-ancestor", str(value), "HEAD")
    if ancestry not in {0, 1}:
        return result("unverifiable", "base-identity=ancestry-unavailable")
    return result("pass") if ancestry == 0 else result("fail", "base-identity=not-ancestor")
```

Do not claim this reconstructs the historical fork point. Run the new tests and the complete identities file; expected: PASS.

- [ ] **Step 5: Encode the lifecycle matrix as data and add positive tests first**

Use this exact production representation:

```python
REVIEW_STAGE_RULES = {
    "specification": {
        "dispatch": frozenset({5}),
        "correction": frozenset({3, 4}),
        "retained_pass": frozenset({5, 6, 7, 8}),
    },
    "plan": {
        "dispatch": frozenset({8}),
        "correction": frozenset({7}),
        "retained_pass": frozenset({8, 9, 10}),
    },
    "implementation": {
        "dispatch": frozenset({10}),
        "correction": frozenset({9}),
        # At Stage 14 this applies while stage.state is active or blocked. A
        # complete Stage 14 is governed exclusively by the exact terminal triple.
        "retained_pass": frozenset({10, 11, 12, 13, 14}),
    },
}

def required_frozen_authorities(stage_id: int) -> tuple[str, ...]:
    if stage_id >= 9:
        return ("specification", "plan")
    if stage_id >= 7:
        return ("specification",)
    return ()
```

Add table-driven positive cases for these exact compatibility classes:

```text
not_started before first dispatch: stages 1–5 with active/(active or complete),
                                  or blocked/blocked
review_active dispatch: owning stage with active/active
review_active recovery overlay: owning stage with blocked/blocked
changes_required correction: correction stage with active/(active or complete),
                             or blocked/blocked
pass at owning review return: owning stage with active/complete
pass retained downstream: retained-pass stage with active/(active or complete),
                          or blocked/blocked, except Stage 14 complete is never
                          a nonterminal retained-pass case
pre-dispatch or returned blocked review: owning stage with blocked/blocked only
authority-governed invalidation: blocked/invalidated with a freshly reset
                                  not_started review; replacement-root evidence
                                  remains required in transition history
terminal: implementation pass with complete/Stage 14 complete/null next_action
```

For ordinary same-kind re-review, test three individual checker-visible heads rather than inventing a production transition helper: (1) returned `changes_required` at the correction stage; (2) blocked pre-dispatch reservation at the owning review stage, retaining `kind`, `root_identity`, `round`, `previous_open_finding_ids`, and `open_finding_ids` while clearing dispatch/run/seal/evidence and `reviewed_commit`; and (3) populated `review_active` with those retained fields plus fresh dispatch/run/seal/evidence identities and null `reviewed_commit`. State explicitly that `audit` validates each current head but cannot prove their historical succession; Task 5's public boundary fixture and Task 6 behavior evidence cover controller transition conformance.

- [ ] **Step 6: Add rejection cases for every incompatible pair**

Generate negative cases by moving each accepted review shape one stage outside its set and by crossing the right stage ID with the wrong stage/status state: `review_active` plus stage complete, review `blocked` plus overall active, correction plus an owning review stage, pass plus an earlier stage, and any current stage `pending`. Include Stage 7/8 without frozen specification, Stage 9+ without either frozen authority, empty/whitespace-only `next_action`, nonterminal null, and terminal nonnull. Expected failures are `review=inconsistent`, `status-stage=inconsistent`, `frozen=incomplete`, or `terminal=inconsistent`, never a traceback.

Run the new lifecycle tests RED. Confirm at least a wrong-stage `review_active`, a Stage 4 specification correction, and Stage 7 missing frozen specification demonstrate current behavior gaps; a test that passes before implementation must be recorded as already covered, not weakened.

- [ ] **Step 7: Implement the minimum declarative compatibility check**

Implement `head_transition_invariant()` as composition of three bounded predicates:

```python
def head_transition_invariant(data: dict[str, object]) -> bool:
    status = data["status"]
    stage = data["stage"]
    state = stage["state"]
    terminal_stage = stage == {"id": 14, "state": "complete"}
    if status == "complete" or terminal_stage:
        return (
            status == "complete"
            and terminal_stage
            and data["next_action"] is None
        )
    if data["next_action"] is None or not str(data["next_action"]).strip():
        return False
    return (
        (status == "active" and state in {"active", "complete"})
        or (status == "blocked" and state in {"blocked", "invalidated"})
    )
```

Keep `next_action` semantic meaning controller-owned. Add `review_stage_invariant(status, stage, review)` to apply the exact compatibility classes above, including stage state and overall status rather than only stage ID. Do not parse verbs, stage names, or paths from `next_action`. Apply `required_frozen_authorities()` in `audit_current_head()`.

Update the existing `identity_drift.py` fixture in this same task: its clean
Stage 9 seed must reuse Task 2's schema-aware head/receipt builder, including
`mode` and a retained passing plan review accepted by the installed checker.
Do not create a second compatibility implementation. Keep its pressure prompt
and oracle behavior unchanged.
`test_behavior_oracle.py` must exercise preparation with the installed Task 3
checker so the component suite cannot defer this compatibility failure to Task
7.

- [ ] **Step 8: Run the focused state/identity suites and commit**

Run:

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py \
  feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_identities.py \
  feature-forge/tests/test_ff_check_runs.py \
  feature-forge/tests/test_behavior_oracle.py -q
python3 -m py_compile feature-forge/scripts/ff-check
git diff --check
cd review-loop
uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q
```

Expected: PASS with pristine output. Then:

```bash
git add feature-forge/assets/ledger-template.md \
  feature-forge/references/workflow.md feature-forge/scripts/ff-check \
  feature-forge/tests/conftest.py feature-forge/tests/test_ledger_schema.py \
  feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_identities.py \
  feature-forge/tests/test_ff_check_runs.py \
  feature-forge/tests/integration/test_review_loop_boundary.py \
  feature-forge/tests/behavior/identity_drift.py \
  feature-forge/tests/test_behavior_oracle.py
git commit -m "fix: enforce Feature Forge head lifecycle"
```

---

### Task 4: Fail Closed on Paths and Scope Run Inventory to One Repository

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Modify: `feature-forge/tests/test_ff_check_runs.py`
- Modify: `feature-forge/tests/test_ff_check_identities.py`
- Modify: `feature-forge/tests/test_ff_check_reviewed_snapshot.py`

**Interfaces:**
- Consumes: Task 3's unchanged CLI/result contract and function signatures.
- Produces: `PATH_OBSERVATION_ERRORS = (OSError, RuntimeError, UnicodeError, ValueError)`; `canonical_run_observation(repo: Path, argument: str) -> tuple[Path | None, str | None]`; `common_git_directory(repo: Path) -> Path | None`; repository-filtered `worktrees(repo: Path) -> list[tuple[str, str | None]] | None`; no uncaught user/ledger-derived path resolution.

- [ ] **Step 1: Add parametrized no-traceback path regressions**

Load the extensionless checker for focused helper tests with `runpy.run_path(str(CHECKER))`, monkeypatch `Path.resolve`, and make the shared resolver raise each member of `PATH_OBSERVATION_ERRORS`. Separately use a real symlink loop at each externally reachable user/ledger-derived site: repository root, linked/common Git directory, worktree inventory path, canonical run, frozen path, receipt path, and reviewed-snapshot walk. Every CLI assertion must prove exactly one stdout result line, exit 1 or 2 according to fail/unverifiable ownership, sorted stderr diagnostics, and absence of `Traceback` on either stream.

Run only the new cases RED and confirm a real symlink-loop `RuntimeError` currently escapes at least one resolution site. The focused resolver test supplies portable coverage for `UnicodeError`, which cannot be induced reliably from a filesystem name on every supported host.

Use this classification table as the test oracle:

| Site | Input class | Result | Stable diagnostic |
| --- | --- | --- | --- |
| `--repo` | Git cannot observe/resolve repository root | `unverifiable` | `repository=unavailable` |
| `--run` | lexically outside, wrong depth/name, or redirected claim | `fail` | `run=noncanonical` |
| `--run` | canonical lexical claim whose resolution cannot be observed | `unverifiable` | `run=unavailable` |
| ledger `worktree`/frozen path | wrong, escaping, or Git-metadata-directed claim | `fail` | existing `worktree=wrong-run` or `frozen=<kind>:wrong-path` |
| ledger `worktree`/frozen path | otherwise valid claim whose current path cannot be observed | `unverifiable` | existing `worktree=unavailable` or `frozen=<kind>:unavailable` |
| worktree inventory candidate | top-level/common-Git-dir identity cannot be observed | `unverifiable` | `git-inventory=unavailable` |
| derived receipt path | symlink/non-directory ancestor or unreadable regular file | `unverifiable` | existing `receipt=unavailable`, `receipt=missing`, or `receipt=unreadable` according to entry state |
| implementation subject walk | lstat/read/resolve observation failure | `unverifiable` | `snapshot=unavailable` or the existing source-unavailable diagnostic |

Wrong types, unknown schema versions, and unknown keys remain unsupported-head/receipt `unverifiable` cases; the table changes only path claims and path observations. Tests assert one exact diagnostic per case rather than accepting either exit 1 or 2.

- [ ] **Step 2: Centralize the exception tuple without changing classifications**

Add:

```python
PATH_OBSERVATION_ERRORS = (OSError, RuntimeError, UnicodeError, ValueError)

def resolve_observed_path(path: Path) -> Path | None:
    try:
        return path.resolve()
    except PATH_OBSERVATION_ERRORS:
        return None
```

Use it, or catch the exact tuple locally where `None` has a different existing meaning. Malformed claims remain `fail`; host observations that cannot be established remain `unverifiable`. Do not collapse all errors into one classification merely to share a helper. Rerun the new cases GREEN.

Replace the ambiguous `canonical_run()` return at CLI boundaries with
`canonical_run_observation()`. Its second tuple member is null on success,
`"noncanonical"` for a lexically invalid or redirected claim, and
`"unavailable"` when a canonical lexical claim cannot currently be observed.
The command handlers translate those outcomes through the Step 1 table; they
must not infer classification from a bare `None`.

- [ ] **Step 3: Add two-repository worktree regressions before implementation**

Create repository A (the requested `--repo`) and unrelated repository B under the same temporary parent. Give both a checked-out `feature/alpha` branch. Feed `worktrees()` a combined candidate inventory and prove:

```text
B's same-named branch/worktree is not a collision for A;
A's matching linked worktree still is a collision;
a candidate whose top-level/common-Git-dir identity cannot be observed makes runs unverifiable;
relative and symlinked common-dir observations are canonicalized before comparison.
```

Run these tests RED and confirm the unrelated B worktree is currently counted.

- [ ] **Step 4: Implement repository identity filtering**

Add:

```python
def common_git_directory(repo: Path) -> Path | None:
    value = git(repo, "rev-parse", "--git-common-dir")
    if value is None:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo / candidate
    return resolve_observed_path(candidate)
```

Resolve the requested repository's common Git directory once. For every candidate returned by Git's worktree inventory, run `git -C CANDIDATE rev-parse --show-toplevel`, resolve it, derive its common Git directory, and include it only when that directory equals the requested one. Any candidate identity that cannot be established returns `None` from `worktrees()`, causing `runs` to report `unverifiable`; it is never silently dropped.

- [ ] **Step 5: Run all path-owning checker suites and commit**

Run:

```bash
python3 -m pytest feature-forge/tests/test_ff_check_runs.py \
  feature-forge/tests/test_ff_check_identities.py \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py -q
python3 -m py_compile feature-forge/scripts/ff-check
git diff --check
```

Expected: PASS. Then:

```bash
git add feature-forge/scripts/ff-check \
  feature-forge/tests/test_ff_check_runs.py \
  feature-forge/tests/test_ff_check_identities.py \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py
git commit -m "fix: scope Feature Forge path observations"
```

---

### Task 5: Make Review Returns Complete, Stable, and Mechanically Checkable

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Modify: `feature-forge/references/adapters-and-reviews.md`
- Modify: `feature-forge/references/workflow.md`
- Modify: `feature-forge/tests/test_ff_check_audit.py`
- Modify: `feature-forge/tests/test_ff_check_reviewed_snapshot.py`
- Modify: `feature-forge/tests/integration/test_review_loop_boundary.py`
- Modify: `tests/test_install.py`
- Verify unchanged: `feature-forge/tests/behavior/identity_drift.py`
- Verify unchanged: `feature-forge/tests/test_behavior_oracle.py`

**Interfaces:**
- Consumes: Tasks 3–4 checker/path interfaces and Task 2 baseline; Review Loop public return state through `run_triage`.
- Produces: exactly four public checker commands; exact expanded `RECEIPT_KEYS`; `CHARTER_BY_KIND`; `STABLE_MAPPING_KEYS`; `allocated_finding_id(dispatch_id: str, triage_finding_id: str) -> str`; installed pure `apply_stable_id_decisions(payload: object) -> dict[str, object]`; `receipt_result_invariant(payload, review) -> bool`; all-TRIAGE-finding mapping; controller provenance checks; pre/post-task identities for delegated and inline execution.

- [ ] **Step 1: Restore the authoritative four-command checker boundary**

The unaffected checked-skill MVP specification accepts exactly `runs`,
`identities`, `reviewed-snapshot`, and `audit`, but the live PR branch exposes a
fifth `implementation-snapshot` command. Add failing parser/install tests for
the exact four-name help set. Change implementation receipt source identity
back to the original contract, using the already validated ledger value:

```python
{
    "kind": "reviewed_commit",
    "path": None,
    "value": review["reviewed_commit"],
}
```

The checker first establishes that this value is the current implementation
review's nonempty, valid commit and an ancestor of `HEAD`. Tests obtain it from
the disposable repository. Remove the public `implementation-snapshot` parser
branch and its direct tests/instruction calls. Keep the internal whole-tree
digest code only if an existing `reviewed-snapshot` predicate still uses it;
otherwise remove it. `reviewed-snapshot` continues to enforce the reviewed
commit, current frozen identities, canonical receipt, committed-path
allowlist, dirty-path allowlist, and tracked mode checks. This is a correction
to an already-live authority mismatch, not a fifth remediation command.

Run RED before implementation, then GREEN:

```bash
python3 -m pytest tests/test_install.py \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py \
  feature-forge/tests/test_ff_check_audit.py -q
```

- [ ] **Step 2: Add the exact receipt shape and charter tests RED**

Set:

```python
RECEIPT_KEYS = {
    "schema", "kind", "dispatch_id", "run_ref", "target_seal",
    "source_identity", "result", "actionable_finding_ids",
    "feature_forge_charter_id", "completion_criterion", "raw_report_ids",
    "triage_artifact_id", "triage_finding_ids", "stable_id_mapping",
}
CHARTER_BY_KIND = {
    "specification": "feature-forge/specification-review/v1",
    "plan": "feature-forge/plan-review/v1",
    "implementation": "feature-forge/implementation-review/v1",
}
STABLE_MAPPING_KEYS = {"triage_finding_id", "feature_forge_finding_id"}
```

Update test receipt builders only after adding failing assertions for missing/extra fields, mismatched charter, empty criterion, unsorted/duplicate report or TRIAGE IDs, malformed mapping objects, duplicate TRIAGE sources, duplicate Feature Forge destinations, unknown sources, and mapped/actionable set disagreement. Run the new tests RED; they must fail because current `strict_receipt()` accepts the old shape.

- [ ] **Step 3: Define and test the deterministic new-ID formula**

Use one canonical, portable formula:

```python
def allocated_finding_id(dispatch_id: str, triage_finding_id: str) -> str:
    framed = json.dumps(
        [dispatch_id, triage_finding_id],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return "FF-" + hashlib.sha256(framed).hexdigest()
```

For each mapping destination, the checker accepts either one ID from the ledger's `previous_open_finding_ids` or exactly `allocated_finding_id(payload["dispatch_id"], triage_id)`. It rejects a reused prior ID more than once, a derived ID colliding with any prior ID, any other unknown destination, and duplicate destinations.

Add fixed-vector tests for ASCII and Unicode TRIAGE IDs and a two-finding test proving two `new` decisions cannot collapse. Run RED before adding the helper, then GREEN.

- [ ] **Step 4: Add result/round/set consistency tests RED**

Cover exactly:

```text
pass: triage_artifact_id is nonnull; raw_report_ids may include zero-finding reports;
      triage_finding_ids, stable_id_mapping, actionable_finding_ids are empty.
changes_required: triage_artifact_id nonnull; all three finding/mapping/actionable sets nonempty and equal by mapping.
blocked before TRIAGE: triage_artifact_id null; triage/mapping/actionable arrays empty;
                       raw_report_ids may contain already usable Round 1 reports.
blocked after TRIAGE: triage_artifact_id nonnull; nonempty complete mapping/actionable set;
                      current round cap or repeated nonempty stable-ID set is true.
nonempty completed TRIAGE: never pass, including when every row is Minor.
```

Also prove `changes_required` cannot satisfy a round/repetition must-block predicate and that a blocked nonempty return cannot occur prematurely. Run these cases RED.

The controller applies a completed nonempty return in this order: copy the old
`open_finding_ids` to `previous_open_finding_ids`; install the new mapped set;
increment `round`; then evaluate the cap (`round >= 3`) and exact repeated-set
predicate. The final receipt/head result is `blocked` when either predicate is
true and `changes_required` otherwise. A pass does not increment `round`.

- [ ] **Step 5: Implement strict internal receipt validation**

Extend `strict_receipt()` for exact shapes and local types. Implement `receipt_result_invariant(payload, review)` for the Step 4 matrix and call it from `audit_receipt()`. Keep provenance claims bounded: `ff-check` validates agreement among the receipt and current ledger only; it does not open the external Review Loop run or claim independent provenance.

Rerun Steps 2–4 GREEN, then run all of `test_ff_check_audit.py` and `test_ff_check_reviewed_snapshot.py`.

- [ ] **Step 6: Upgrade the public Review Loop boundary fixture from real returned state**

In the integration fixture, derive evidence with helpers equivalent to:

```python
def _triage_evidence(round1, outcome) -> tuple[list[str], str, list[str]]:
    processor = outcome.snapshot["processor_state"]
    rows = processor["apply_ledger_decisions"]["rows"]
    triage_ids = sorted(row["id"] for row in rows)
    report_ids = sorted(report.report_id for report in round1.raw_reports)
    registry = outcome.snapshot["artifact_registry"]
    triage_artifacts = [
        artifact_id for artifact_id, item in registry["artifacts"].items()
        if item["kind"] == "triage-result"
    ]
    assert len(triage_artifacts) == 1
    triage_id = triage_artifacts[0]
    raw = (outcome.run_root / "evidence" / triage_id).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == registry["artifacts"][triage_id]["digest"]
    artifact = json.loads(raw.decode("utf-8"))
    assert sorted(artifact["report_ids"]) == report_ids
    assert any(
        binding["operation"] == "apply_ledger_decisions"
        and triage_id in binding["source_ids"]
        for binding in registry["bindings"]
    )
    return report_ids, triage_id, triage_ids
```

Use the public `Round1Outcome.raw_reports` inventory retained by the caller; do not reconstruct report IDs by scanning files. Preserve zero-finding report IDs.

- [ ] **Step 7: Make the semantic mapper executable from installed code**

The mapping judgment input must contain the evidence needed to compare meaning:

```json
{
  "dispatch_id": "specification-2",
  "materially_same_criterion": "same grounded discrepancy against the same requirement, correctness condition, repository contract, or verification result, with no material change in the required correction",
  "prior_findings": [
    {
      "feature_forge_finding_id": "FF-prior",
      "triage_finding": {"id": "prior-triage-id", "sources": [{"report_id": "prior-report", "finding_id": "prior-finding", "claim": "REQ-007 has no acceptance check", "severity": "Minor", "locators": ["REQ-007"]}], "source_ids": ["prior-report:prior-finding"], "reported_severity": "Minor", "current_severity": "Minor", "factual": "CONFIRMED", "state": "OPEN", "evidence_locators": ["REQ-007"], "target_seal": "prior-seal"}
    }
  ],
  "current_findings": [
    {"id": "current-triage-id", "sources": [{"report_id": "current-report", "finding_id": "current-finding", "claim": "REQ-007 lacks an acceptance check", "severity": "Minor", "locators": ["REQ-007"]}], "source_ids": ["current-report:current-finding"], "reported_severity": "Minor", "current_severity": "Minor", "factual": "CONFIRMED", "state": "OPEN", "evidence_locators": ["REQ-007"], "target_seal": "current-seal"}
  ],
  "decisions": [
    {"triage_finding_id": "current-triage-id", "decision": "FF-prior", "rationale": "same missing REQ-007 verification"}
  ]
}
```

The `sources` arrays are the complete normalized source objects from Review
Loop. Obtain current full findings by reading the current bound `triage-result`
evidence file and verifying its registry digest/binding. Obtain prior full
findings from the previous receipt's
`run_ref` plus `triage_artifact_id`, verify that bound artifact the same way,
and join its TRIAGE IDs to stable IDs through that receipt's
`stable_id_mapping`. Do not use the projection rows for semantic input because
they omit claims and evidence locators.

The LLM receives only `prior_findings`, `current_findings`, and the criterion,
and returns exactly:

```json
{"decisions": [{"triage_finding_id": "current-triage-id", "decision": "FF-prior", "rationale": "same missing REQ-007 verification"}]}
```

`decision` is either one supplied prior Feature Forge ID or literal `new`;
`rationale` is a nonempty string for reuse and null for `new`.

Implement `apply_stable_id_decisions(payload)` in installed `ff-check` as a
pure, repository-read-only function. It validates exact input/output shapes,
complete current-ID coverage, known and singly reused prior IDs, rationale
rules, and final destination uniqueness; it replaces `new` with
`allocated_finding_id()` and returns this exact transient result shape:

```json
{"schema": "feature-forge/stable-id-map/v1", "status": "pass", "stable_id_mapping": [{"triage_finding_id": "current-triage-id", "feature_forge_finding_id": "FF-prior"}], "error": null}
```

Invalid input returns the same four keys with `status: "fail"`, an empty
mapping, and one stable nonempty error code. Before the exclusive receipt
write, invoke the installed pure function without adding a checker subcommand
or state artifact:

```bash
python3 -c 'import json,runpy,sys; api=runpy.run_path(sys.argv[1]); print(json.dumps(api["apply_stable_id_decisions"](json.load(sys.stdin)),sort_keys=True,separators=(",",":")))' "$SKILL_DIR/scripts/ff-check"
```

Feed the controller-assembled input plus LLM decisions on stdin. A missing
single JSON result, non-pass status, or shape mismatch blocks before receipt
creation. Record the decision/rationale rows in the existing ledger transition
evidence; do not create a mapping artifact. Unit-test the installed helper by
loading the same file with `runpy`, and make the integration fixture call that
helper rather than a test-only validator.

- [ ] **Step 8: Replace severity filtering with all-finding mapping**

Change `_map_controller_return()` so every canonical TRIAGE row participates, regardless of `current_severity`. Add integration cases for:

```text
zero findings -> pass with nonnull TRIAGE artifact and complete raw-report inventory;
one Minor -> changes_required;
Important/Critical -> changes_required;
pre-TRIAGE controller/gate/reviewer failure -> blocked with null TRIAGE artifact;
round cap/repeated stable set -> blocked with nonnull TRIAGE artifact;
zero-finding reports remain in raw_report_ids;
```

For stable-ID judgment, make the fake mapper first assert the exact semantic input above, then return one configured decision per current ID. Add positive tests for distinct new IDs and a legitimate reuse whose answer cannot be inferred from similar ID spelling, plus negative tests for missing coverage, unknown prior IDs, absent reuse rationale, and two current findings reusing one prior ID. All strict validation and allocation must call the installed helper from Step 7.

- [ ] **Step 9: Synchronize the receipt and review lifecycle instructions**

In `adapters-and-reviews.md`, replace the old Important/Critical pass table and old eight-field receipt list with the approved exact contract. State separately:

```text
LLM: material equivalence only; one current TRIAGE ID -> prior stable ID or literal new.
Code: shape, coverage, unknown/reused prior IDs, deterministic fresh allocation,
      destination uniqueness, result/round/set rules, receipt/head agreement.
TRIAGE: consolidation of current raw findings.
```

State that an ordinary same-kind correction preserves root, round, and finding history while allocating fresh dispatch/run/seal/receipt identities. Reset only for a different review kind or authority-governed root invalidation with replaced/replacement root, reason, authority, and parent event in transition history.

- [ ] **Step 10: Add the Stage 9 post-return identity gate for both execution modes**

In `workflow.md`, change Stage 9's mechanical contract to:

```text
Run identities at entry, immediately before each delegated or inline plan task,
and immediately after every bounded task return before recording that return complete;
then run audit after the ledger update.
```

Task 2 already froze separate delegated and inline plan-drift variants whose
oracle refuses task completion after the changed frozen plan. Do not edit that
fixture, prompt, or scorer here. Synchronize the live workflow contract, run
the unchanged deterministic scorer unit suite, and leave behavioral GREEN
replay to Task 6.

- [ ] **Step 11: Run focused and integration suites, then commit**

Run:

```bash
python3 -m pytest feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py \
  feature-forge/tests/test_remediation_pressure.py \
  feature-forge/tests/test_behavior_oracle.py \
  tests/test_install.py -q
cd review-loop
uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q
```

Expected: PASS. Return to the repository root, run `git diff --check`, then:

```bash
git add feature-forge/scripts/ff-check \
  feature-forge/references/adapters-and-reviews.md \
  feature-forge/references/workflow.md \
  feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py \
  feature-forge/tests/integration/test_review_loop_boundary.py \
  tests/test_install.py
git commit -m "fix: preserve Feature Forge review evidence"
```

---

### Task 6: Simplify Dispatches, Run GREEN Qualification, and Restore the Docs Gate

**Files:**
- Modify for authorized Claude GREEN transport only: `feature-forge/tests/behavior/remediation_pressure.py`
- Modify for adapter regressions: `feature-forge/tests/test_remediation_pressure.py`
- Modify: `feature-forge/SKILL.md`
- Modify as required for equivalent prose only: `feature-forge/references/workflow.md`
- Modify as required for equivalent prose only: `feature-forge/references/adapters-and-reviews.md`
- Modify if a demonstrated authority-boundary gap requires it: `feature-forge/references/authority.md`
- Modify: `feature-forge/CLAUDE.md`
- Modify: `feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md`

**Interfaces:**
- Consumes: immutable Task 2 scenarios/baseline, Task 5's exact checker/receipt/stage contracts, and live post-merge Review Loop templates.
- Produces: contract-synchronized and deduplicated Feature Forge instructions; GREEN results on unchanged scenarios; a rubric verdict and diagnostic byte/word count for all seven Feature Forge-owned dispatch shapes plus only integration-changed Review Loop compositions; restored documentation command.

- [ ] **Step 1: Build the prompt inventory from live composition points**

Record one row for each exact shape:

```text
brainstorm-return
plan-return
delegated execute-return worker packet
stable-finding-ID mapping judgment
specification review subject/focus/completion
plan review subject/focus/completion
implementation review subject/focus/completion
```

Use `git diff --name-only origin/main...HEAD -- review-loop` to identify Review Loop resources actually changed by the integration/Feature Forge composition; evaluate only those. For each row record source files, exact composed fixture path or reproducible composition command, bytes, words, and the seven binary rubric verdicts: one task, scoped subject, necessary context, authority boundary, interface boundary, goal condition, failure condition.

- [ ] **Step 2: Synchronize schemas/contracts even when the baseline passed**

Update instruction text required by checked `mode`, the receipt fields, all-findings return mapping, stable-ID mapping/allocation, same-kind re-review retention, Stage 4 correction retention, and delegated/inline post-task identities. Remove superseded duplicate prose when another owner reference states the same contract. Do not add a generic prompt framework, new reference file, numeric budget, or second template layer.

- [ ] **Step 3: Add behavioral guidance only for Task 2 gaps**

For each `gap demonstrated` scenario, name the observed failure form before editing:

```text
rule skipped under pressure -> prohibition/red flag addressing the observed rationalization;
wrong output shape -> positive ordered return recipe;
missing field -> required structural slot next to the owning template;
conditional behavior -> instruction keyed to the observable condition.
```

Do not add guidance for an `already correct` scenario. If wording is behavior-shaping, micro-test each candidate variant against five fresh repetitions of the same no-guidance control, manually inspect every result, and stop if the control does not reproduce the gap. Retain only wording that fixes the observed gap without adding another task or authority.

- [ ] **Step 4: Recompose and review all seven dispatch shapes**

Run one fresh capable reviewer per related family—stage returns/worker packet, stable-ID judgment, and three review compositions—using only the composed packet plus this exact rubric:

```text
For each packet, verdict seven items yes/no with one evidence sentence each:
one task; scoped subject; necessary context; authority boundary; interface boundary;
goal condition; failure condition. Treat bytes/words as diagnostics, never a target.
Flag a supplied field only when it is unused by this task; flag missing context only
when the worker cannot complete the exact return without inventing it.
```

These are test subjects invoked through noninteractive CLI calls, not SDD task reviewers. A failed rubric item caused by a concrete packet/schema/composition mismatch is fixed structurally in its owning existing instruction file, then only that packet is recomposed and re-reviewed. Broader behavior-shaping guidance follows Step 3's five-repetition control/candidate rule and is not justified by a reviewer opinion alone.

- [ ] **Step 5: Rerun the immutable pressure scenarios GREEN**

Use the exact Task 2 campaign commands with `--phase green`, yielding one fresh Codex and one fresh Claude context per scenario:

```bash
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase green --host codex
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase green --host claude
```

Do not edit `cases.json`, prompts, scorer, or baseline section. Score deterministic effects and manually apply the same North-Star rubric. Record unavailable host/model results as unavailable.

**Authorized fix-round transport amendment:** Preserve the legacy baseline
argv and every Codex invocation. Claude GREEN alone adds `--output-format json`
and `--json-schema` with a scenario-specific structural schema. Worker output
is exactly seven required string fields (`task`, `ownership`, `interfaces`,
`dependencies`, `verification`, `authority`, `return`); residual output is
exactly two required objects (`receipt`, `head`) with deep semantics left to
the existing scorer/checker; drift output is exactly one required `summary`
string. No schema contains scenario answers or expected actions.
Worker field descriptions identify the implementation worker's actual task,
paths, inputs and return; they remain scenario-independent and contain no
fixture values, expected disposition, or scorer-specific wording.

Capture the raw envelope separately outside the fixture repository. Require
successful process/envelope status and present schema-valid `structured_output`;
serialize only that object for the existing scorer/manual review, with no
fallback to conversational prose. Missing/malformed output after execution
fails qualification, never becomes unavailability. First add real failing
tests for phase-specific argv, schema boundaries/no oracle leakage, envelope
preservation, deterministic materialization, and malformed/missing output;
then implement the bounded adapter and rerun them GREEN. Rerun all four Claude
GREEN scenarios and append their outcomes, preserving every historical result
and recording the transport-comparability cost. No new live skill schema,
prompt machinery, or host configuration change is authorized.

- [ ] **Step 6: Complete the single qualification record**

Append, without rewriting Task 2 evidence:

- exact changed instruction files and which updates were schema/contract synchronization versus behavior guidance;
- any five-repetition micro-test and rationalizations;
- eight GREEN outcomes (four scenario variants across two hosts, including
  explicit unavailable dispositions) paired with their baseline outcomes;
- the seven-shape prompt inventory and any changed Review Loop composition rows;
- bytes/words as diagnostics with content findings, not aggregate targets;
- one disposition per scenario/packet: `pass`, `blocked-unavailable`, or `fail`.

No `fail` row may remain. Required Codex failure or unavailability blocks qualification. Corroborating Claude unavailability is recorded and does not block; if Claude executes and fails, that observed gap must be resolved and cannot be erased by Codex passing.

- [ ] **Step 7: Restore and run the exact component documentation gate**

Add this exact block to `feature-forge/CLAUDE.md` under Verification:

```bash
python3 -m pytest \
  'tests/test_documentation.py::test_documentation_entrypoints[feature-forge]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[feature-forge]' -q
```

Run it exactly. Do not add exact-prose tests.

- [ ] **Step 8: Run instruction-owned checks and commit**

Run:

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py \
  feature-forge/tests/test_remediation_pressure.py -q
python3 -m pytest \
  'tests/test_documentation.py::test_documentation_entrypoints[feature-forge]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[feature-forge]' -q
git diff --check
```

Expected: PASS. Then stage only files actually changed from the Task 6 list:

```bash
git add feature-forge/SKILL.md feature-forge/CLAUDE.md \
  feature-forge/references/workflow.md \
  feature-forge/references/adapters-and-reviews.md \
  feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md
git commit -m "docs: tighten Feature Forge dispatch contracts"
```

If `authority.md` changed for a demonstrated gap, add that one explicit path to the command; otherwise leave it untouched.

For the authorized structured-output fix, stage only its actually changed
explicit paths: `feature-forge/tests/behavior/remediation_pressure.py`,
`feature-forge/tests/test_remediation_pressure.py`, this plan, the binding
remediation design, and the appended qualification record. Preserve prior
commits/results; do not amend the original Task 6 evidence commit.

---

### Task 7: Record Cross-Cutting Verification

**Files:**
- Modify: `feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md` (append verification evidence only)

**Interfaces:**
- Consumes: Tasks 1–6 commits, qualification dispositions, exact installed payload, and repository/component verification contracts.
- Produces: fresh complete verification evidence tied to the tested production `HEAD`, a clean scoped worktree, and one evidence-only commit ready for Task 7's own SDD review.

- [ ] **Step 1: Verify the exact branch and diff scope before running suites**

Run:

```bash
git status --short --branch
git log --oneline --decorate --graph origin/main..HEAD
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
```

Expected: no uncommitted paths; changed production scope is limited to Feature Forge plus the Task 1 Review Loop conflict resolutions and approved repository docs/tests.

- [ ] **Step 2: Run Feature Forge's complete component suite**

Run:

```bash
python3 -m pytest feature-forge/tests -q
```

Expected: PASS, with only the integration import skip documented by the owning Review Loop invocation.

- [ ] **Step 3: Run the Feature Forge boundary and complete Review Loop suite**

Run:

```bash
cd review-loop
uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q
uv run pytest -q
```

Expected: both PASS with only documented environment skips.

- [ ] **Step 4: Run repository packaging, documentation, and plugin gates**

From the repository root, run:

```bash
python3 -m pytest tests/test_install.py -q
python3 -m pytest tests/test_documentation.py -q
python3 -m pytest tests/test_plugin_agents.py -q
claude plugin validate . --strict
python3 -m pytest tests -q
```

Plugin gates are required if the merged or remediation diff touches plugin metadata, agent registration/mirrors, installed payload selection, or the files those tests cover. If no such path changed, still run the inexpensive pytest plugin-agent gate and record strict plugin validation as `not affected` only when the CLI is unavailable.

- [ ] **Step 5: Run syntax, whitespace, and explicit status checks**

Run:

```bash
python3 -m py_compile feature-forge/scripts/ff-check \
  feature-forge/tests/behavior/remediation_pressure.py
git diff --check origin/main...HEAD
git status --short --branch
```

Expected: no syntax errors, whitespace errors, or uncommitted paths.

- [ ] **Step 6: Append exact verification evidence and commit only that record**

Append every command, exit status, concise result, skip/unavailable reason, tested `HEAD`, and qualification disposition to the existing record. Do not change a prior baseline or GREEN verdict. Then:

```bash
git add feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md
git commit -m "test: record Feature Forge remediation verification"
git status --short --branch
```

After the evidence-only commit, rerun the exact documentation gate from Task 6,
`git diff --check origin/main...HEAD`, and `git status --short --branch`.
Report both the production commit exercised by the complete suites and the
later evidence-only commit; do not imply the code suites ran after the
evidence-only documentation commit.

## Completion Conditions

The plan is complete only when Task 7's fresh evidence establishes all acceptance bullets in the approved specification, the SDD final whole-branch review has no unresolved material issue, `origin/feature-forge-mvp` equals local `HEAD`, PR #7 reflects that head, and the worktree is clean. The handoff reports any unavailable optional evidence and every SDD ruling; it does not describe PR #7 as mergeable when a required gate is unavailable.
