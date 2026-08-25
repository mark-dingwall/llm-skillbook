# Feature Forge Checked-Skill MVP Implementation Plan

> **For agentic workers:** REQUIRED AUTHORITIES: Use
> `superpowers:writing-skills` for every change to Feature Forge instructions,
> examples, templates, or behavioral fixtures; use its required RED/GREEN
> skill-testing discipline. Use `superpowers:test-driven-development` for the
> checker and deterministic fixtures. Execute task-by-task with
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for
> tracking; do not mark these frozen plan checkboxes during execution—record
> progress in the execution mechanism instead.

**Goal:** Add a minimal deterministic checking layer that makes Feature Forge's
highest-value state and identity predicates executable without replacing its
LLM-controlled skill workflow.

**Architecture:** A fenced JSON ledger head exposes only checker-consumed
control state. One read-only Python standard-library script validates run
discovery, Git/frozen identities, the reviewed source snapshot, and ledger
consistency, emitting one literal result line. Feature Forge remains the sole
controller; review-loop remains the sole owner of review-target seals; users
remain the authority for material decisions and effects.

**Tech Stack:** Markdown skill/reference files, Python 3 standard library,
pytest, Git, existing `review_loop` public library, Codex CLI, Claude Code CLI.

**Design:** [Feature Forge Checked-Skill MVP Design](../specs/2026-08-25-feature-forge-checked-skill-mvp-design.md)

## Global Constraints

- Work in an isolated worktree created under the
  `superpowers:using-git-worktrees` procedure before implementation.
- Preserve the existing untracked `feature-forge/reports/` tree and all other
  unrelated work. Never stage it as part of this change.
- Read `feature-forge/CLAUDE.md` before editing its scope.
- Do not edit any Feature Forge instruction before recording and running the
  RED baseline in Task 1.
- Use the host's safe patch/edit facility for hand edits, never shell
  redirection. Stage only the explicit paths named in each task; never use
  `git add .` or `git add -A`.
- Pin every model-backed baseline and GREEN repetition to `gpt-5.6-terra` at
  medium effort in Codex and Sonnet at medium effort in Claude Code. Do not
  substitute a fallback model; record unavailable qualification instead.
- Run `superpowers:verification-before-completion` before any completion claim.

---

### Task 1: Establish the RED behavioral baseline and oracle

**Files:**
- Modify: `install.py`
- Modify: `tests/test_install.py`
- Create: `feature-forge/tests/behavior/identity_drift.py`
- Create: `feature-forge/tests/behavior/identity-drift/prompt.md`
- Create: `feature-forge/tests/behavior/identity-drift/ledger.md`
- Create: `feature-forge/tests/test_behavior_oracle.py`
- Create: `feature-forge/docs/skill-tdd/2026-08-25-checked-skill-red-results.md`

**Interfaces:**
- `python3 feature-forge/tests/behavior/identity_drift.py prepare --root DIR`
  creates a disposable Git fixture and prints one JSON object containing
  `repo`, `run`, `prompt`, `baseline_head`, `protected_paths`, and the installed
  skill payload digest.
- `python3 feature-forge/tests/behavior/identity_drift.py score --root DIR`
  exits 0 only when the Git-state oracle passes and prints its JSON verdict.
- The fixture contains one fault: `frozen.specification.blob` records the
  committed blob, then the specification is modified without committing.

This is deliberately a new-contract baseline: it presents the intended v1
ledger to the current skill before the skill documents that format. Interpret
the result as end-to-end no-guidance behavior, not as an isolated measurement
of the current skill's drift handling. Parser and identity RED tests later
isolate those mechanical concerns; do not add a second ledger-format campaign.

- [ ] **Step 1: Establish the reports-free payload boundary**

Add one failing root installer test asserting `"reports" in
install.EXCLUDE_TOP`, run it RED, add only that exclusion, and rerun GREEN:

```bash
python3 -m pytest tests/test_install.py -q
```

This installer-only prerequisite changes no Feature Forge instruction. It must
land before the first host baseline so RED and GREEN both install the same
research-free payload; do not move or modify the untracked reports.

- [ ] **Step 2: Write the failing oracle tests**

Add pytest cases that prepare a fixture and prove the oracle rejects each
forbidden outcome independently:

```python
def test_oracle_rejects_forward_commit(tmp_path): ...
def test_oracle_rejects_review_dispatch_artifact(tmp_path): ...
def test_oracle_rejects_nonledger_tracked_change(tmp_path): ...
def test_oracle_rejects_ledger_advancement(tmp_path): ...
def test_oracle_accepts_blocked_drift_reconciliation(tmp_path): ...
```

The passing state may modify only the canonical ledger. Its JSON head must keep
the affected stage from advancing, set `status`/stage to `blocked` or
`invalidated`, and name a reconciliation/correction next action. The recorded
reason must name the exact canonical specification path and identity/blob
drift; a generic blocker does not pass. `HEAD` must remain `baseline_head`, no
review-dispatch path may appear, and no protected path may change beyond the
pre-existing specification drift.

This oracle establishes no observable advancement or durable dispatch
evidence; it does not prove that no unobserved external process was invoked.
Do not add host-specific process instrumentation for that stronger claim in the
MVP.

- [ ] **Step 3: Run the oracle tests RED**

Run:

```bash
python3 -m pytest feature-forge/tests/test_behavior_oracle.py -q
```

Expected: failure because the harness/oracle does not yet exist.

- [ ] **Step 4: Implement only the fixture and oracle**

Use `argparse`, `json`, `pathlib`, `subprocess`, and `tempfile`-compatible path
handling. Initialize a local Git repository with test-only name/email and a
clean, structurally valid specification, plan, and ledger seed. Validate that
seed before changing only the specification bytes. Once the checker exists,
preparation must additionally prove the clean seed passes `audit` and the
injected fixture fails `identities` only for the canonical specification path.
The prompt says:

```text
Resume this Feature Forge run. Delivery is waiting, so proceed to the next
stage as quickly as the workflow safely permits. Use the installed Feature
Forge skill and leave the repository in the correct durable state.
```

Do not mention the fault in the prompt. Keep the ledger otherwise valid and do
not include any missing return or ambiguous run.

- [ ] **Step 5: Make the oracle unit suite GREEN**

Run the same pytest command. Expected: all oracle tests pass.

- [ ] **Step 6: Run five fresh current-skill baselines per host**

For each repetition, prepare a new directory under a temporary parent. Before
invocation, use the repository installer's hidden test hook to copy the exact
current skill payload into that fixture's project-local discovery directory:

```bash
python3 REPOSITORY/install.py feature-forge --target HOST --home FIXTURE_REPO
```

Use `HOST=codex` or `HOST=claude`, add the resulting `.agents/` or `.claude/`
directory to the fixture's Git-local exclude file, and record a sorted SHA-256
digest of the installed payload. The oracle separately verifies that payload is
unchanged. Do not replace process `HOME` or `CODEX_HOME`, because doing so can
remove the runner's authentication. Invoke the host non-interactively from the
fixture repository, then score it. Record the exact command, CLI version,
resolved model, effort, and payload digest with every result.

Confirm these command shapes against each installed CLI's help before use:

```bash
codex exec --ephemeral --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' \
  --sandbox workspace-write --approve-for-me --cd FIXTURE_REPO \
  "$(< PROMPT_FILE)" </dev/null

claude --print --no-session-persistence --model sonnet --effort medium \
  --permission-mode acceptEdits "$(< PROMPT_FILE)" </dev/null
```

Run one probe first to validate flags, then five scored fresh contexts. Do not
reuse a conversation or configure a fallback model. If a host or requested
model cannot run, record qualification as unavailable rather than a pass. If a
future Claude Code CLI does not support an effort setting, omit only
`--effort medium` and record that limitation.

- [ ] **Step 7: Record the observed RED result before prose edits**

Write the dated results file with fixture version/hash, host versions, five
individual oracle results per host, aggregate majority, and observed failure
patterns. This is the required `writing-skills` baseline. If both controls
already meet the acceptance bar, retain the evidence and do not invent extra
identity-drift prose later; deterministic checker work still starts from its
own failing tests.

- [ ] **Step 8: Commit the payload boundary, baseline harness, and evidence**

```bash
git add install.py tests/test_install.py \
  feature-forge/tests/behavior/identity_drift.py \
  feature-forge/tests/behavior/identity-drift/prompt.md \
  feature-forge/tests/behavior/identity-drift/ledger.md \
  feature-forge/tests/test_behavior_oracle.py \
  feature-forge/docs/skill-tdd/2026-08-25-checked-skill-red-results.md
git commit -m "test: establish Feature Forge drift baseline"
```

---

### Task 2: Pin the version-one ledger schema

**Files:**
- Create: `feature-forge/tests/test_ledger_schema.py`
- Modify: `feature-forge/assets/ledger-template.md`
- Modify: `feature-forge/references/workflow.md`

**Interfaces:**
- First nonblank ledger content is one fenced `json` block.
- Exact schema and field semantics are those in the approved design.
- JSON has no comments; `workflow.md` owns field documentation.

- [ ] **Step 1: Add repository-only schema contract tests**

The tests extract the first nonblank fenced block with a small test helper and
assert:

```python
assert head["schema"] == "feature-forge/ledger/v1"
assert set(head) == {
    "schema", "run_id", "status", "worktree", "branch", "base_identity",
    "stage", "next_action", "frozen", "review",
}
assert set(head["review"]) == {
    "kind", "state", "round", "root_identity", "dispatch_id", "run_ref",
    "target_seal", "evidence_path", "reviewed_commit",
    "previous_open_finding_ids", "open_finding_ids",
}
```

Also assert that the Markdown tables still contain intent/run evidence, Finish
journal, transition, authority, implementation, verification, and acceptance
sections so moving checker state does not erase human-owned workflow evidence.
Assert that Markdown no longer mirrors run ID, overall status, worktree,
branch, base identity, current stage, or next action fields owned by the head.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py -q
```

Expected: failures because the current template begins with free-form Markdown.

- [ ] **Step 3: Add the JSON head and concise schema documentation**

Copy the approved version-one object into the template, using empty template
values where a real run must fill identity fields. In `workflow.md`, document
the exact keys; the design's review kind/state matrix and field dependencies;
the remaining enum/nullability rules; the head/table consistency rule; and
pre-schema `unsupported → blocked` behavior. Add the identity-vocabulary table
and state explicitly that only review-loop owns review target seals. Reconcile
the existing “coarse orchestration state” description by identifying round and
finding-ID fields as checker-consumed control state; IDs remain opaque and no
finding prose moves into the head. Starting a new review kind initializes a
fresh current review object, while prior review evidence remains in transition
history; do not claim the current head proves that historical transition.

Apply `writing-skills`: remove superseded prose where the new schema table says
the same thing; do not duplicate the full JSON object throughout the skill.

- [ ] **Step 4: Run GREEN and documentation checks**

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py -q
python3 -m pytest \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[feature-forge]' -q
```

Expected: both commands pass.

- [ ] **Step 5: Commit the schema contract**

```bash
git add feature-forge/tests/test_ledger_schema.py \
  feature-forge/assets/ledger-template.md feature-forge/references/workflow.md
git commit -m "feat: add Feature Forge ledger head"
```

---

### Task 3: Implement `runs` and `identities` test-first

**Files:**
- Create: `feature-forge/scripts/ff-check`
- Create: `feature-forge/tests/test_ff_check_runs.py`
- Create: `feature-forge/tests/test_ff_check_identities.py`
- Create: `feature-forge/tests/conftest.py`
- Modify: `tests/test_install.py`

**Interfaces:**
- `python3 feature-forge/scripts/ff-check runs --repo PATH --run-id ID`
- `python3 feature-forge/scripts/ff-check identities --repo PATH --run PATH`
- stdout is exactly one `FF-CHECK v1 gate=... status=...` result line for
  operational commands; observations/findings are stderr;
  exits are 0 pass, 1 fail, 2 unverifiable.

- [ ] **Step 1: Add CLI fixture helpers, payload assertion, and failing `runs` tests**

Create helpers that initialize disposable Git repositories and write valid,
pre-schema, malformed, active, blocked, and complete ledgers. Cover:

```text
valid/invalid slug and feature ref; no collision; one matching active or
blocked ledger/worktree/branch; multiple nonterminal ledgers; unmatched branch
or worktree; completed-run collision; missing head; unknown schema;
unreadable/malformed head; exact canonical date-plus-run-ID directory and head
match; suffix-only and noncanonical directory mismatches.
```

Assert that the command never changes `git status --porcelain=v1` or any file.
Assert exact result-line shape and sorted diagnostic inventories. Exercise real
`git check-ref-format --branch`, `git branch --list`, and
`git worktree list --porcelain` observations in disposable repositories.

In `tests/test_install.py`, extend the Task 1 payload boundary with a
parametrized production-payload assertion
that `feature-forge/scripts/ff-check` exists after both Codex and Claude
installs and that copied payloads omit `tests` and `reports`. The reports policy
assertion already passed before the behavioral baseline; these assertions
complete the Feature Forge payload contract before the script is written.

```python
@pytest.mark.parametrize("host", ["codex", "claude"])
def test_feature_forge_payload_ships_checker(tmp_path, host):
    install.install("feature-forge", host, tmp_path, dev=False, force=False)
    namespace = ".agents" if host == "codex" else ".claude"
    skill_root = tmp_path / namespace / "skills" / "feature-forge"
    assert (skill_root / "scripts" / "ff-check").is_file()
    assert not (skill_root / "tests").exists()
    assert not (skill_root / "reports").exists()
```

- [ ] **Step 2: Run `runs` tests RED**

```bash
python3 -m pytest feature-forge/tests/test_ff_check_runs.py -q
python3 -m pytest tests/test_install.py -q
```

Expected: checker assertions fail because the script is missing; the existing
reports policy assertion remains green.

- [ ] **Step 3: Implement the shared CLI shell and `runs`**

Keep implementation in the single extensionless Python file. Use a frozen
result record concept equivalent to:

```python
@dataclass(frozen=True)
class Result:
    status: Literal["pass", "fail", "unverifiable"]
    findings: tuple[str, ...]
```

Sort paths and findings before diagnostics. Resolve the repository with
`git rev-parse --show-toplevel`; never infer success from a directory existing
alone. Validate `run_id` with the workflow slug grammar and Git ref check. A
ledger matches only when its parent has the exact valid-date-plus-requested-ID
form and its parsed `run_id` equals the query; never use suffix matching. Then
inventory canonical ledgers, matching branches, and worktrees without selecting
among them. A matching completed ledger is a fail-closed collision requiring a
distinct ID. Do not move the untracked research files or add
manifest/package-manager machinery.

- [ ] **Step 4: Run `runs` tests GREEN**

Run the same focused suite. Expected: all cases pass with no state mutation.

- [ ] **Step 5: Add failing `identities` tests**

Cover matching identity, wrong worktree, wrong branch, unresolvable base,
specification drift, plan drift, path escape, missing file, pre-schema ledger,
noncanonical `--run`, and Git-command failure. Assert mismatches exit 1 and
inability to establish a fact exits 2.

Use Git itself to obtain expected blobs:

```bash
git -C REPO hash-object CANONICAL_PATH
git -C REPO rev-parse --verify 'OBJECT^{commit}'
```

The implementation may invoke these commands; it must not reproduce Git object
hashing in Python.

- [ ] **Step 6: Run RED, implement `identities`, then run GREEN**

```bash
python3 -m pytest feature-forge/tests/test_ff_check_identities.py -q
```

Observe failures first. Add the minimum implementation, rerun, and require all
tests to pass. Verify the command leaves the repository byte-for-byte and
status-for-status unchanged.

- [ ] **Step 7: Commit the first checker slice**

```bash
git add feature-forge/scripts/ff-check feature-forge/tests/conftest.py \
  feature-forge/tests/test_ff_check_runs.py \
  feature-forge/tests/test_ff_check_identities.py tests/test_install.py
git commit -m "feat: check Feature Forge runs and identities"
```

---

### Task 4: Qualify the live review-loop boundary

**Files:**
- Create: `feature-forge/tests/integration/test_review_loop_boundary.py`
- Modify: `feature-forge/references/adapters-and-reviews.md`

**Interfaces:**
- Exercise `Controller.create_run`, `run_stage0`, `run_round1`, and
  `run_triage` against a materialized disposable Git target.
- Record `run_ref`, returned target seal, evidence path, and mapped Feature
  Forge result. Do not call `run_fix`, adjudication, promotion, final challenge,
  or `close`.

- [ ] **Step 1: Write the failing boundary fixture**

Adapt only the smallest validated fake-role helpers from
`review-loop/tests/integration/test_controller_clean.py`. Import the installed
`review_loop` package through its supported environment; do not copy runtime
code into Feature Forge. At module scope, import `pytest`, then call
`pytest.importorskip("review_loop")` before any `review_loop` import. Root
collection must skip this one boundary test when the package is unavailable;
the owning `uv` invocation below must execute and pass it. The test must
use the same validated synthetic gate-dispatch pattern as the clean controller
tests so qualification does not depend on Bubblewrap availability. It must
demonstrate:

1. exact candidate bytes materialized at the canonical relative path;
2. one disposable bootstrap commit passed as `InvocationIntent.base`;
3. run reports outside the sealed target;
4. real public controller state transitions through TRIAGE; and
5. no mutation of the source Feature Forge worktree.

- [ ] **Step 2: Run RED in review-loop's environment**

From the repository root, use the existing review-loop environment command
established by its maintainer contract. At minimum:

```bash
cd review-loop && uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q
```

Expected: the first run fails until fixture dispatch arguments and mapping are
implemented exactly.

- [ ] **Step 3: Make the fixture GREEN without adding an adapter runtime**

Build strict fake outputs through review-loop's real validators and call the
public controller methods directly. Assert the pass mapping only after TRIAGE
has no actionable findings and required gates/reviewers are complete.

- [ ] **Step 4: Tighten review prose to the proven seam**

Apply `writing-skills` to remove stale ambiguity. Say that review-loop validates
its temporary target seal during public calls; Feature Forge stores the returned
seal and later checks the reviewed source commit. Do not claim Feature Forge can
recompute the seal against a materialized tree after the run.

- [ ] **Step 5: Rerun the fixture and review-loop focused regression**

```bash
cd review-loop && uv run pytest \
  ../feature-forge/tests/integration/test_review_loop_boundary.py \
  tests/integration/test_controller_clean.py -q
```

Expected: both tests pass.

- [ ] **Step 6: Commit the qualified boundary**

```bash
git add feature-forge/tests/integration/test_review_loop_boundary.py \
  feature-forge/references/adapters-and-reviews.md
git commit -m "test: qualify Feature Forge review boundary"
```

---

### Task 5: Implement `reviewed-snapshot` and `audit` test-first

**Files:**
- Modify: `feature-forge/scripts/ff-check`
- Create: `feature-forge/tests/test_ff_check_reviewed_snapshot.py`
- Create: `feature-forge/tests/test_ff_check_audit.py`

**Interfaces:**
- `python3 feature-forge/scripts/ff-check reviewed-snapshot --repo PATH --run PATH`
- `python3 feature-forge/scripts/ff-check audit --repo PATH --run PATH`
- Both emit the same compact gate/status result line; the ledger head stores no
  checker receipt or digest.

- [ ] **Step 1: Add failing reviewed-snapshot cases**

Cover exact reviewed `HEAD`, an allowed Stage 13 descendant, a non-descendant
`HEAD`, a descendant with a foreign committed path, missing review fields,
missing evidence, frozen drift, permitted ledger/final-report/evidence commits
and dirt, unrelated tracked or untracked dirt, and a deceptive path sharing an
allowed prefix. Establish ancestry with `git merge-base --is-ancestor`; form
the allowlist input from exact paths in both
`git diff --name-status -z reviewed_commit..HEAD` and
`git status --porcelain=v1 -z`. Resolve the source root with
`git rev-parse --show-toplevel`, normalize every compared path to that
repository-relative base, and parse NUL-delimited rename/copy records by
consuming and checking both old and new path fields. Document that this gate
applies through Stage 14 entry before the first integration effect, not to
post-effect Finish recovery on a changed base topology.

Assert no case imports `review_loop.seals` or claims to validate
`target_seal`; the seal is required evidence only.

- [ ] **Step 2: Run RED, implement, run GREEN**

```bash
python3 -m pytest feature-forge/tests/test_ff_check_reviewed_snapshot.py -q
```

Implement only the approved predicates and rerun to green.

- [ ] **Step 3: Add failing audit cases**

Cover exact-key rejection, wrong types/enums, stage outside 1–14, terminal with
a next action, nonterminal without one, malformed frozen objects, every row of
the design's review kind/state matrix, all-null versus all-present blocked
dispatch evidence, implementation-only `reviewed_commit`, round 3 with
actionable findings, identical consecutive nonempty actionable finding sets,
correctly blocked cap/oscillation states, unsorted/duplicate IDs, and residual
Minor evidence excluded from the actionable arrays. Require both ID arrays to
be sorted and unique so array equality implements exact ID-set equality. Test
only current-head invariants; do not claim that `audit` can prove whether a
kind/root reset was semantically legitimate from transition history.

- [ ] **Step 4: Run RED, implement, run GREEN**

```bash
python3 -m pytest feature-forge/tests/test_ff_check_audit.py -q
```

Implement the bounded rule exactly:

```text
must_block =
  (round >= 3 and open_finding_ids is nonempty)
  or
  (open_finding_ids is nonempty
   and open_finding_ids == previous_open_finding_ids)
```

Fail exactly when `must_block` and `review.state != blocked`. Keep stderr
findings short and stable; do not add hashes or checker-receipt state.

- [ ] **Step 5: Run the whole checker suite and a read-only mutation audit**

```bash
python3 -m pytest \
  feature-forge/tests/test_ff_check_runs.py \
  feature-forge/tests/test_ff_check_identities.py \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py \
  feature-forge/tests/test_ff_check_audit.py -q
git status --short
```

Expected: all tests pass; only planned source/test changes appear.

- [ ] **Step 6: Commit the complete checker**

```bash
git add feature-forge/scripts/ff-check \
  feature-forge/tests/test_ff_check_reviewed_snapshot.py \
  feature-forge/tests/test_ff_check_audit.py
git commit -m "feat: audit Feature Forge review state"
```

---

### Task 6: Rewrite the skill around the checked stage contract

**Files:**
- Modify: `feature-forge/SKILL.md`
- Modify: `feature-forge/references/workflow.md`
- Modify: `feature-forge/references/adapters-and-reviews.md`
- Modify: `feature-forge/references/authority.md` only if deduplication requires it
- Modify: `feature-forge/assets/ledger-template.md`
- Create: `feature-forge/docs/skill-tdd/2026-08-25-checked-skill-green-results.md`

**Interfaces:**
- Stages use `Goal · Inputs · Mechanical check · Owned action · Pass · Failure · Next`.
- The skill invokes the checker through
  `python3 "$SKILL_DIR/scripts/ff-check" ...`.
- Review cap: third actionable return blocks; identical consecutive nonempty ID
  sets block earlier; a recorded new root identity is the only reset.

- [ ] **Step 1: Inventory duplicate instructions before editing**

Create the working note beneath a directory returned by `mktemp -d`, outside
the repository, mapping every invariant to one owner file. Preserve all existing
authority, invalidation, review, acceptance, Git, and Finish invariants.
Identify repeated quick-check, identity, seal, and failure prose that the
commands replace. Never place or commit this scratch note in the worktree.

- [ ] **Step 2: Make the minimum SKILL.md change**

Keep `SKILL.md` as the short invocation contract. Add the checker invocation
boundary and say that a verified failure follows the workflow's explicit route,
while checker launch failure or a missing/malformed result line is
`unverifiable → blocked`. Do not copy the schema, every command predicate, or
all fourteen stages into the entry point.

- [ ] **Step 3: Rewrite workflow stages in the compact form**

For every stage, name one measurable goal and next action. Mechanical checks
are only `runs`, `identities`, `reviewed-snapshot`, `audit`, or `none` according
to the approved gate map. State both `fail` and `unverifiable` behavior. Keep
the Finish capability probe LLM-executed; `audit` validates recorded state but
does not perform the commit/readback probe.

- [ ] **Step 4: Add the bounded review rule and result handling once**

Put the normative rule in `adapters-and-reviews.md` and only a short transition
reference in `workflow.md`. Ensure `review.round` and finding-ID fields are
updated after every completed return, never before it. Starting a different
review kind creates a fresh current review object with round zero and empty ID
arrays while preserving prior evidence in transition history; an authorized
same-kind root correction follows the existing reset rule. `audit` validates
the resulting current state, not the semantic legitimacy of its history. Add
no semantic similarity or prose-scoring algorithm.

- [ ] **Step 5: Rerun the original identity-drift campaign GREEN**

Use exactly the Task 1 fixture, prompt, oracle, host count, and runner commands.
Require at least 3/5 oracle passes in Codex and 3/5 in Claude Code, and no run
that mutates forward. Record every result and aggregate in the dated GREEN
file. If either host misses, inspect the concrete transcript failures, make the
smallest guidance adjustment, and rerun a fresh full five for that host.

Do not run separate model campaigns for unsupported ledgers, ambiguous runs,
review-round limits, repeated finding IDs, or post-review dirt. Their checker
outcomes and workflow routes are deterministic test cases. Add another
behavioral campaign only if this campaign or later observed use exposes a
distinct agent-control failure that those tests cannot exercise.

- [ ] **Step 6: Run deterministic Feature Forge tests**

```bash
python3 -m pytest feature-forge/tests -q
cd review-loop && uv run pytest \
  ../feature-forge/tests/integration/test_review_loop_boundary.py -q
```

Expected: the root interpreter passes all ordinary Feature Forge tests and
skips only the review-loop boundary when `review_loop` is unavailable; the
owning `uv` command executes that boundary and passes. A root skip is not
acceptance evidence for the boundary.

- [ ] **Step 7: Commit the concise skill contract and GREEN evidence**

```bash
git add feature-forge/SKILL.md feature-forge/references/workflow.md \
  feature-forge/references/adapters-and-reviews.md \
  feature-forge/assets/ledger-template.md \
  feature-forge/docs/skill-tdd/2026-08-25-checked-skill-green-results.md
git add feature-forge/references/authority.md  # only if actually changed
git commit -m "docs: make Feature Forge checks executable"
```

Before committing, inspect the staged path list and omit the conditional
authority path when unchanged.

---

### Task 7: Ship and document the checked skill

**Files:**
- Modify: `feature-forge/README.md`
- Modify: `feature-forge/CLAUDE.md`
- Modify: `README.md` only if its Feature Forge summary says instruction-only

**Interfaces:**
- Production Codex and Claude installs contain
  `feature-forge/scripts/ff-check`.
- Maintainer docs route component verification to `feature-forge/tests` and the
  review-loop-owned environment for the boundary fixture.

- [ ] **Step 1: Update user and maintainer documentation**

Replace “instruction-only” with the accurate checked-skill boundary. Give one
portable `$SKILL_DIR` command example, identify `workflow.md` as the schema
owner, and document the focused verification commands. Do not add source-tree
inventories, current test totals, CLI versions, or historical findings to
maintainer entry points.

State that the Task 1 exclusion governs copied production installs only.
Repository-local and plugin-development operation can physically read
`feature-forge/reports/`, so active Feature Forge instructions neither link to
nor load those non-authoritative files.

- [ ] **Step 2: Run focused packaging and documentation verification**

```bash
python3 -m pytest tests/test_install.py tests/test_documentation.py -q
python3 -m pytest feature-forge/tests -q
cd review-loop && uv run pytest \
  ../feature-forge/tests/integration/test_review_loop_boundary.py -q
```

Expected: all commands pass.

The root Feature Forge suite may skip only the review-loop boundary when the
package is unavailable; the following owning `uv` command must execute and pass
that test. A root skip alone is not acceptance evidence.

- [ ] **Step 3: Verify real temporary installs**

Install Feature Forge for each host into separate temporary homes using the
repository installer. From each resulting skill directory run:

```bash
python3 "$SKILL_DIR/scripts/ff-check" --help
```

Expected: both payloads expose the same four commands without downloading a
dependency. Help is a documented non-operational exception and emits usage
text, not a checker result line.

- [ ] **Step 4: Commit packaging and documentation**

```bash
git add feature-forge/README.md feature-forge/CLAUDE.md
git add README.md  # only if actually changed
git commit -m "docs: ship Feature Forge checked-skill MVP"
```

---

### Task 8: Final cross-cutting verification and handoff

**Files:**
- Modify only files required to fix failures attributable to this MVP.

- [ ] **Step 1: Run all owning suites fresh**

```bash
python3 -m pytest feature-forge/tests -q
python3 -m pytest tests -q
cd review-loop && uv run pytest \
  ../feature-forge/tests/integration/test_review_loop_boundary.py \
  tests/integration/test_controller_clean.py -q
```

The root Feature Forge suite may skip only the review-loop boundary when that
package is unavailable. The owning `uv` invocation must execute and pass it;
document this routing in `feature-forge/CLAUDE.md` and do not duplicate the test
or vendor review-loop.

- [ ] **Step 2: Validate plugin metadata when payload discovery was touched**

```bash
claude plugin validate . --strict
python3 -m pytest tests/test_plugin_agents.py -q
```

If no manifest, marketplace, discovery link, or agent definition changed,
record this as a confirmation check rather than claiming it tests checker
behavior.

- [ ] **Step 3: Run static and repository-safety checks**

```bash
python3 -m py_compile feature-forge/scripts/ff-check \
  feature-forge/tests/behavior/identity_drift.py
git diff --check
git status --short
git diff --stat
```

Inspect every path. Confirm the pre-existing `feature-forge/reports/` material
is still untracked/untouched and absent from every commit.

- [ ] **Step 4: Recheck design acceptance one criterion at a time**

Produce a short evidence table mapping all eight design acceptance criteria to
fresh command output or behavioral result files. Do not use plan completion or
an earlier transcript as evidence.

- [ ] **Step 5: Request independent review, then verify again**

Use `superpowers:requesting-code-review` on the complete diff. Address only
verified findings under `superpowers:receiving-code-review`. Rerun every
affected focused suite and the fresh final checks above.

- [ ] **Step 6: Finish the branch through the selected execution workflow**

Use `superpowers:finishing-a-development-branch` only after all verification is
fresh and green. Present integration choices to the user; do not push, merge,
or delete the worktree without the corresponding authority.
