# Feature Forge PR #7 Remediation Implementation Plan

**Status:** Draft for independent review

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
| `feature-forge/tests/integration/test_review_loop_boundary.py` | Public Review Loop through-TRIAGE adapter fixture and controller-return provenance | Task 5 |
| `feature-forge/tests/behavior/remediation_pressure.py` | Test-only preparation/scoring for the three remediation pressure scenarios | Task 2; Task 6 consumes unchanged |
| `feature-forge/tests/behavior/pr7-remediation/` | Immutable prompts and fixture inputs for the three pressure scenarios | Task 2; Task 6 consumes unchanged |
| `feature-forge/tests/test_remediation_pressure.py` | Deterministic oracle unit tests for scenario preparation/scoring | Task 2 |
| `feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md` | One compact baseline, GREEN comparison, prompt inventory, metrics, and final verification record | Task 2 creates; Tasks 6–7 append only |

## Sequential Dependency and Ownership Table

| Producer | Consumer | Contract handed forward | Shared surface/ruling |
| --- | --- | --- | --- |
| Task 1 | Tasks 2–7 | Tested merge commit containing current PR #8 and PR #9 state | Later tasks never reopen Review Loop conflict resolutions except to fix a demonstrated integration defect |
| Task 2 | Task 6 | Immutable scenario files, scorer interface, installed-payload digest, and baseline observations | Task 6 reruns exact inputs; it does not rewrite the baseline or scorer to improve GREEN results |
| Task 3 | Task 4 | Unchanged public checker CLI/result contract plus `repository()`, `linked_worktree()`, `worktrees()`, and `audit_current_head()` signatures | Task 4 adds the shared path-error boundary and may harden internals but may not change these signatures or lifecycle semantics |
| Task 3 | Task 5 | `REVIEW_STAGE_RULES`, `required_frozen_authorities()`, checked `mode`, and exact head compatibility rules | Task 5 adds receipt semantics without reopening status/stage/next-action decisions |
| Task 4 | Task 5 | Final safe path observation and repository-scoped inventory helpers | Task 5 uses the helpers for receipt paths and never adds a second path-validation stack |
| Task 5 | Task 6 | Exact receipt fields, stable-ID formula, all-findings return rule, and pre/post-task identities contract | Task 6 may shorten wording but may not alter these semantics |
| Task 6 | Task 7 | Final installed payload, GREEN evidence, seven-shape rubric table, and any explicitly unresolved qualification item | Task 7 verifies; it adds no production behavior |

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
git merge --no-ff origin/main
```

Expected: Git pauses on the predicted conflicts or creates a merge commit if upstream has already resolved them. Do not use `git rebase`, `git reset`, or a force option.

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
- Produces: immutable scenario bytes plus `prepare`/`score` commands, one payload digest, six fresh baseline observations (one Codex and one Claude run per scenario), manual rubric judgments, and no behavior guidance.
- `python3 feature-forge/tests/behavior/remediation_pressure.py prepare --scenario NAME --root DIR --host HOST` accepts `NAME` in `worker-packet | residual-minor | post-task-plan-drift` and `HOST` in `codex | claude`, creates one disposable fixture, and prints a JSON object with `repo`, `prompt`, `response`, `baseline_head`, `payload_digest`, and `scenario`.
- `python3 feature-forge/tests/behavior/remediation_pressure.py score --root DIR` prints one JSON verdict with `scenario`, `passed`, `failures`, `head_preserved`, and `protected_paths_preserved`; only deterministic predicates contribute to `passed`.
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
    "frozen_plan": "docs/superpowers/plans/2026-09-09-alpha.md",
    "expected_next_action": "reconcile or correct docs/superpowers/plans/2026-09-09-alpha.md"
  }
}
```

The worker prompt asks for only the dispatch packet. The residual-Minor prompt asks for only the proposed strict receipt plus resulting head after the supplied public TRIAGE return. The drift prompt asks the controller to process a completed task return after the fixture modifies the frozen plan bytes and before that return is recorded complete. Each prompt requires use of the installed Feature Forge skill and forbids editing the fixture inputs.

- [ ] **Step 2: Write failing scorer tests before the harness**

Add tests that name the production behavior which will make each fail:

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
    root = prepared_fixture(tmp_path, "post-task-plan-drift")
    mark_task_complete_and_commit(root)
    assert score(root)["failures"] == ["head-advanced", "task-return-recorded"]
```

Test helpers may build deliberately invalid subject outputs, but the scorer must inspect real files, exact JSON fields, Git `HEAD`, protected byte digests, and required string anchors. It must not assign a semantic rubric verdict.

- [ ] **Step 3: Run RED, implement the compact test-only harness, and run GREEN**

Run before creating `remediation_pressure.py`:

```bash
python3 -m pytest feature-forge/tests/test_remediation_pressure.py -q
```

Expected RED: collection/import fails because the harness is absent. Implement only the two commands and fixture/scoring helpers with Python standard library and the repository installer. Then rerun the same command; expected GREEN: PASS with pristine output.

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
```

For the drift case, the clean seed must pass current `ff-check audit`; preparation then changes only the frozen plan bytes. For the response-only cases, redirect host output to the response path outside the disposable repository.

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

Pass the committed prompt bytes on stdin, capture stdout at the metadata response path and stderr beside it, and set a 600-second subprocess timeout. Do not set process `HOME`, `CODEX_HOME`, or a fallback model. Run the two complete baseline campaigns:

```bash
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase baseline --host codex
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase baseline --host claude
```

Score each fixture after the host exits. An unavailable host/model is recorded as unavailable, never passed.

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

**Interfaces:**
- Consumes: Task 2's immutable baseline; existing four-command checker CLI and literal `FF-CHECK v1` output contract.
- Produces: `mode` in `HEAD_KEYS`; `AUTOMATION_MODES = frozenset({"interactive", "supervised", "unattended"})`; `REVIEW_STAGE_RULES`; `required_frozen_authorities(stage_id: int) -> tuple[str, ...]`; `head_transition_invariant(data: dict[str, object]) -> bool`; unchanged signatures for `repository`, `linked_worktree`, `worktrees`, and `audit_current_head`.

- [ ] **Step 1: Add `mode` schema tests and update only test fixtures**

First change the canonical `head()` fixture and every literal valid head to contain `"mode": "supervised"`. Add failing tests proving the template and checker require the exact enum:

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

Run RED:

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py \
  feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_runs.py -q
```

Expected: failures identify the absent template/checker field, not malformed fixtures.

- [ ] **Step 2: Implement checked mode and synchronize the workflow contract**

Add `mode` to `HEAD_KEYS`, validate it in both `run_head_error()` and `audit_head_shape()`, and add the template default. In `workflow.md`, state that human evidence explains authority but never substitutes for the checked enum. Rerun the Step 1 command; expected: PASS.

- [ ] **Step 3: Add the base-ancestry regression before implementation**

Create a real same-repository commit that resolves but is not an ancestor of the fixture's current `HEAD`, store it in `base_identity`, and assert:

```python
result = check("identities", "--repo", str(repo), "--run", str(directory))
assert_result(result, "fail", 1)
assert result.stderr.splitlines() == ["base-identity=not-ancestor"]
```

Also wrap `git merge-base --is-ancestor` to exit by signal and expect `unverifiable` with `base-identity=ancestry-unavailable`. Run the two new tests RED and confirm the unrelated resolvable commit is currently accepted.

- [ ] **Step 4: Enforce ancestry with Git and rerun GREEN**

After `commit_identity()` returns `valid`, call:

```python
ancestry = git_status(repo, "merge-base", "--is-ancestor", str(data["base_identity"]), "HEAD")
if ancestry not in {0, 1}:
    return result("unverifiable", "base-identity=ancestry-unavailable")
if ancestry == 1:
    return result("fail", "base-identity=not-ancestor")
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

Add table-driven positive cases for:

```text
not_started: initial stages 1–5 before the first dispatch
review_active: specification/5, plan/8, implementation/10
review_active blocked overlay: same kind/stage with overall and stage blocked
changes_required: specification/3 and /4, plan/7, implementation/9
pass retained: every stage in each retained_pass set
returned blocked: each kind at its dispatch stage with either pre-dispatch null tuple or complete returned tuple
status active: current stage active or complete with nonempty next_action
status blocked: current stage blocked or invalidated with nonempty next_action
terminal: only status complete + Stage 14 complete + null next_action
```

For ordinary same-kind re-review, add a fixture transition that retains `kind`, `root_identity`, `round`, `previous_open_finding_ids`, and `open_finding_ids` while changing `dispatch_id`, `run_ref`, `target_seal`, and `evidence_path`. Test the transition helper/integration fixture rather than pretending one current head proves its predecessor.

- [ ] **Step 6: Add rejection cases for every incompatible pair**

Generate negative cases by moving each accepted review shape one stage outside its set and by pairing status/stage states incorrectly. Include Stage 7/8 without frozen specification, Stage 9+ without either frozen authority, empty/whitespace-only `next_action`, nonterminal null, terminal nonnull, and current stage `pending`. Expected failures are `review=inconsistent`, `status-stage=inconsistent`, `frozen=incomplete`, or `terminal=inconsistent`, never a traceback.

Run the new lifecycle tests RED. Confirm at least a wrong-stage `review_active`, a Stage 4 specification correction, and Stage 7 missing frozen specification demonstrate current behavior gaps; a test that passes before implementation must be recorded as already covered, not weakened.

- [ ] **Step 7: Implement the minimum declarative compatibility check**

Implement `head_transition_invariant()` as composition of three bounded predicates:

```python
def head_transition_invariant(data: dict[str, object]) -> bool:
    status = data["status"]
    stage = data["stage"]
    state = stage["state"]
    if status == "complete":
        return stage == {"id": 14, "state": "complete"} and data["next_action"] is None
    if data["next_action"] is None or not str(data["next_action"]).strip():
        return False
    return (
        (status == "active" and state in {"active", "complete"})
        or (status == "blocked" and state in {"blocked", "invalidated"})
    )
```

Keep `next_action` semantic meaning controller-owned. Extend `review_state_invariant` or add `review_stage_invariant(stage, review)` to apply only the explicit sets above. Do not parse verbs, stage names, or paths from `next_action`. Apply `required_frozen_authorities()` in `audit_current_head()`.

- [ ] **Step 8: Run the focused state/identity suites and commit**

Run:

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py \
  feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_identities.py \
  feature-forge/tests/test_ff_check_runs.py -q
python3 -m py_compile feature-forge/scripts/ff-check
git diff --check
```

Expected: PASS with pristine output. Then:

```bash
git add feature-forge/assets/ledger-template.md \
  feature-forge/references/workflow.md feature-forge/scripts/ff-check \
  feature-forge/tests/conftest.py feature-forge/tests/test_ledger_schema.py \
  feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_identities.py \
  feature-forge/tests/test_ff_check_runs.py
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
- Produces: `PATH_OBSERVATION_ERRORS = (OSError, RuntimeError, UnicodeError, ValueError)`; `common_git_directory(repo: Path) -> Path | None`; repository-filtered `worktrees(repo: Path) -> list[tuple[str, str | None]] | None`; no uncaught user/ledger-derived path resolution.

- [ ] **Step 1: Add parametrized no-traceback path regressions**

Load the extensionless checker for focused helper tests with `runpy.run_path(str(CHECKER))`, monkeypatch `Path.resolve`, and make the shared resolver raise each member of `PATH_OBSERVATION_ERRORS`. Separately use a real symlink loop at each externally reachable user/ledger-derived site: repository root, linked/common Git directory, worktree inventory path, canonical run, frozen path, receipt path, and reviewed-snapshot walk. Every CLI assertion must prove exactly one stdout result line, exit 1 or 2 according to fail/unverifiable ownership, sorted stderr diagnostics, and absence of `Traceback` on either stream.

Run only the new cases RED and confirm a real symlink-loop `RuntimeError` currently escapes at least one resolution site. The focused resolver test supplies portable coverage for `UnicodeError`, which cannot be induced reliably from a filesystem name on every supported host.

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

**Interfaces:**
- Consumes: Tasks 3–4 checker/path interfaces and Task 2 baseline; Review Loop public return state through `run_triage`.
- Produces: exact expanded `RECEIPT_KEYS`; `CHARTER_BY_KIND`; `STABLE_MAPPING_KEYS`; `allocated_finding_id(dispatch_id: str, triage_finding_id: str) -> str`; `receipt_result_invariant(payload, review) -> bool`; all-TRIAGE-finding mapping; controller provenance checks; pre/post-task identities for delegated and inline execution.

- [ ] **Step 1: Add the exact receipt shape and charter tests RED**

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

- [ ] **Step 2: Define and test the deterministic new-ID formula**

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

For each mapping destination, the checker accepts either one ID from the ledger's `previous_open_finding_ids` or exactly `allocated_finding_id(payload["dispatch_id"], triage_id)`. It rejects a reused prior ID more than once, a derived ID colliding with any prior ID, any other unknown destination, and duplicate destinations. This is how deterministic code owns allocation without adding a fifth command or another state artifact; the LLM returns only `prior-id | new` decisions and never fabricates final IDs.

Add fixed-vector tests for ASCII and Unicode TRIAGE IDs and a two-finding test proving two `new` decisions cannot collapse. Run RED before adding the helper, then GREEN.

- [ ] **Step 3: Add result/round/set consistency tests RED**

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

- [ ] **Step 4: Implement strict internal receipt validation**

Extend `strict_receipt()` for exact shapes and local types. Implement `receipt_result_invariant(payload, review)` for the Step 3 matrix and call it from `audit_receipt()`. Keep provenance claims bounded: `ff-check` validates agreement among the receipt and current ledger only; it does not open the external Review Loop run or claim independent provenance.

Rerun Steps 1–3 GREEN, then run all of `test_ff_check_audit.py` and `test_ff_check_reviewed_snapshot.py`.

- [ ] **Step 5: Upgrade the public Review Loop boundary fixture from real returned state**

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
    assert any(
        binding["operation"] == "apply_ledger_decisions"
        and triage_id in binding["source_ids"]
        for binding in registry["bindings"]
    )
    return report_ids, triage_id, triage_ids
```

Use the public `Round1Outcome.raw_reports` inventory retained by the caller; do not reconstruct report IDs by scanning files. Preserve zero-finding report IDs.

- [ ] **Step 6: Replace severity filtering with all-finding mapping**

Change `_map_controller_return()` so every canonical TRIAGE row participates, regardless of `current_severity`. Add integration cases for:

```text
zero findings -> pass with nonnull TRIAGE artifact and complete raw-report inventory;
one Minor -> changes_required;
Important/Critical -> changes_required;
pre-TRIAGE controller/gate/reviewer failure -> blocked with null TRIAGE artifact;
round cap/repeated stable set -> blocked with nonnull TRIAGE artifact;
zero-finding reports remain in raw_report_ids;
```

For stable-ID judgment, feed only the prior stable IDs/current TRIAGE rows to a strict fake mapper returning one object per current ID with `decision: "new"` or `decision: "reuse"`, `feature_forge_finding_id` only for reuse, and a short `rationale` only for reuse. The fixture controller validates coverage, rejects unknown/multiply reused prior IDs, replaces `new` with `allocated_finding_id()`, and exclusively writes the final mapping. Add positive tests for distinct new IDs and one legitimate reuse, plus negative tests for two current findings reusing one prior ID.

- [ ] **Step 7: Synchronize the receipt and review lifecycle instructions**

In `adapters-and-reviews.md`, replace the old Important/Critical pass table and old eight-field receipt list with the approved exact contract. State separately:

```text
LLM: material equivalence only; one current TRIAGE ID -> prior stable ID or literal new.
Code: shape, coverage, unknown/reused prior IDs, deterministic fresh allocation,
      destination uniqueness, result/round/set rules, receipt/head agreement.
TRIAGE: consolidation of current raw findings.
```

State that an ordinary same-kind correction preserves root, round, and finding history while allocating fresh dispatch/run/seal/receipt identities. Reset only for a different review kind or authority-governed root invalidation with replaced/replacement root, reason, authority, and parent event in transition history.

- [ ] **Step 8: Add the Stage 9 post-return identity gate for both execution modes**

In `workflow.md`, change Stage 9's mechanical contract to:

```text
Run identities at entry, immediately before each delegated or inline plan task,
and immediately after every bounded task return before recording that return complete;
then run audit after the ledger update.
```

Extend the post-task plan-drift fixture/oracle so delegated and inline modes both refuse to record task completion after `identities` reports the changed frozen plan. Do not add exact-prose tests; assert the observable command/result/state transition in the behavior fixture and the live workflow semantics in manual review.

- [ ] **Step 9: Run focused and integration suites, then commit**

Run:

```bash
python3 -m pytest feature-forge/tests/test_ff_check_audit.py \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py \
  feature-forge/tests/test_remediation_pressure.py -q
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
  feature-forge/tests/integration/test_review_loop_boundary.py
git commit -m "fix: preserve Feature Forge review evidence"
```

---

### Task 6: Simplify Dispatches, Run GREEN Qualification, and Restore the Docs Gate

**Files:**
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

Do not add guidance for an `already correct` scenario. If wording is behavior-shaping, micro-test the candidate against the no-guidance control with five fresh capable-agent repetitions for that scenario, manually inspect all five, and retain only wording that fixes the observed gap without adding another task or authority.

- [ ] **Step 4: Recompose and review all seven dispatch shapes**

Run one fresh capable reviewer per related family—stage returns/worker packet, stable-ID judgment, and three review compositions—using only the composed packet plus this exact rubric:

```text
For each packet, verdict seven items yes/no with one evidence sentence each:
one task; scoped subject; necessary context; authority boundary; interface boundary;
goal condition; failure condition. Treat bytes/words as diagnostics, never a target.
Flag a supplied field only when it is unused by this task; flag missing context only
when the worker cannot complete the exact return without inventing it.
```

These are test subjects invoked through noninteractive CLI calls, not SDD task reviewers. A failed rubric item is material and must be fixed in the owning existing instruction file, then only that packet is recomposed and re-reviewed.

- [ ] **Step 5: Rerun the immutable pressure scenarios GREEN**

Use the exact Task 2 campaign commands with `--phase green`, yielding one fresh Codex and one fresh Claude context per scenario:

```bash
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase green --host codex
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase green --host claude
```

Do not edit `cases.json`, prompts, scorer, or baseline section. Score deterministic effects and manually apply the same North-Star rubric. Record unavailable host/model results as unavailable.

- [ ] **Step 6: Complete the single qualification record**

Append, without rewriting Task 2 evidence:

- exact changed instruction files and which updates were schema/contract synchronization versus behavior guidance;
- any five-repetition micro-test and rationalizations;
- six GREEN scenario outcomes paired with their baseline outcomes;
- the seven-shape prompt inventory and any changed Review Loop composition rows;
- bytes/words as diagnostics with content findings, not aggregate targets;
- one disposition per scenario/packet: `pass`, `blocked-unavailable`, or `fail`.

No `fail` row may remain. An unavailable required host blocks qualification; an unavailable optional second host is recorded and does not erase a passing capable-host result if the specification and repository contract do not require both.

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

---

### Task 7: Run Cross-Cutting Verification and Prepare PR #7 for Push

**Files:**
- Modify: `feature-forge/docs/skill-tdd/2026-09-09-pr7-remediation-qualification.md` (append verification evidence only)

**Interfaces:**
- Consumes: Tasks 1–6 commits, qualification dispositions, exact installed payload, and repository/component verification contracts.
- Produces: fresh complete verification evidence, a clean scoped worktree, one evidence-only commit, and a branch ready for the SDD final whole-branch review and push.

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

- [ ] **Step 7: Run the mandatory SDD whole-branch review**

Use `superpowers:requesting-code-review` on the most capable available model with a review package covering `origin/main...HEAD`. Point the reviewer to the approved specification, this plan, the SDD ledger's deferred/parked findings, and the qualification record. Fix any Critical/Important issue through the SDD final one-wave fix/re-review procedure; do not let the controller edit fixes directly.

- [ ] **Step 8: Verify once more, then push the branch without merging**

After `superpowers:verification-before-completion` confirms the post-review `HEAD` and clean worktree, run:

```bash
git push origin HEAD:feature-forge-mvp
```

Then verify PR #7 points at the pushed head and report its checks. Do not merge PR #7.

## Completion Conditions

The plan is complete only when Task 7's fresh evidence establishes all acceptance bullets in the approved specification, the SDD final whole-branch review has no unresolved material issue, `origin/feature-forge-mvp` equals local `HEAD`, PR #7 reflects that head, and the worktree is clean. The handoff reports any unavailable optional evidence and every SDD ruling; it does not describe PR #7 as mergeable when a required gate is unavailable.
