# Review Loop Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy prose-driven review loop with the approved evidence-driven MVP that can review and fix code or technical documentation, fail closed at trust boundaries, and report the strongest verdict its evidence supports.

**Architecture:** Keep `SKILL.md` as a small controller contract over focused role resources and Python helpers. A canonical artifact registry owns rich evidence and issues compact projections to a lean deterministic state processor; separate helpers own prompt/report validation, sealing, evidence gates, bounded FIX, profiles, dispatch, and final reporting. Build and accept the ordinary end-to-end path first, then add the fixed-pair multi-review slot as a late isolated caller-side Bubblewrap adapter.

**Tech Stack:** Python 3 standard library, PyYAML only for strict YAML profile/driver parsing, `unittest`, Markdown behavioral fixtures, GNU sealing tools, Git, Bubblewrap, repo-local multi-review v2 headless driver.

## Global Constraints

- The governing authority is `docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`; archived plans and the prototype are evidence, not authority.
- Supported effort tiers are exactly `low`, `med`, `high`, and `max`; do not add `xhigh`.
- Do not add numeric specialist or finding caps. Freeze the complete required roster and batch it to host concurrency.
- An automatically derived `max` pauses before reviewer dispatch unless the operator explicitly selected `max` or explicitly disabled confirmation.
- Invocation authorizes bounded local FIX work, but never dependency installation, commit, stage, deploy, production credentials, or external side effects.
- No non-FIX target-accessing role may run without a tested read-only execution mapping; prompt wording alone is not containment.
- Tests and mutation evidence are gates or supporting evidence as classified; they never independently settle a finding.
- Use existing mutation tooling opportunistically, never install it, and permit only bounded manual mutants in a disposable copy.
- Multi-review remains an MVP requirement but is implemented after the ordinary path. Review-loop supplies the concrete whole-call `bwrap --unshare-pid --die-with-parent` wrapper and discloses that reviewers share that namespace with driver transport/output. Do not implement multi-review's planned native per-reviewer sandbox selector here; adopt its prioritized strict profile when available.
- Every code behavior change follows RED/GREEN/REFACTOR. Before changing behavior-bearing skill or role prose, run a focused fresh-context control; add guidance and a durable GREEN scenario only when that control demonstrates a real miss. Record useful null controls without manufacturing prose or a permanent provider-dependent matrix.
- Each meaningful task receives independent spec-compliance and code-quality review before the next dependent task begins.

## File Structure

| Path | Responsibility |
|---|---|
| `review-loop/pyproject.toml` | Python floor and the sole runtime dependency, PyYAML |
| `review-loop/review_loop/artifacts.py` | Controller-private registry inside canonical state, allowed evidence-file publication, seal/digest-bound transition authority |
| `review-loop/review_loop/state.py` | Pure compact-projection policy kernel and terminal computation |
| `review-loop/review_loop/prompts.py` | Declared template/fragment renderer and strict role-output validators |
| `review-loop/review_loop/seals.py` | Canonical target records, per-call input seals, Git delta contract |
| `review-loop/review_loop/profiles.py` | Strict v1 YAML profiles and capability/model overlay resolution |
| `review-loop/review_loop/execution.py` | Tested ordinary read-only/FIX mappings, process handles, deadlines, batching, recovery termination |
| `review-loop/review_loop/evidence.py` | Gate discovery validation, safe execution, opportunistic mutation evidence |
| `review-loop/review_loop/fix.py` | Ledger-bound FIX request, manifest/delta validation, post-FIX gate promotion |
| `review-loop/review_loop/multi_review.py` | Fixed Claude/Codex driver request, caller-side Bubblewrap containment, report validation, fallback reason |
| `review-loop/review_loop/controller.py` | Persisted `GATE -> REVIEW -> TRIAGE -> FIX -> CLOSE` orchestration |
| `review-loop/review_loop/report.py` | Final Markdown hand-back from canonical state |
| `review-loop/review_loop/resources/*.md` | Focused role templates and explicit fragments loaded by dispatched roles |
| `review-loop/DESIGNING_PROFILES.md` | Installed profile schema, examples, and safety limits |
| `review-loop/tests/unit/` | Pure unit tests for each helper |
| `review-loop/tests/contract/` | Cross-helper artifact/projection and multi-review fixtures |
| `review-loop/tests/integration/` | Fake-process containment, recovery, controller, and end-to-end tests |
| `review-loop/tests/behavior/` | RED/GREEN fresh-agent scenarios for behavior-bearing documentation |

Every new test directory contains `__init__.py` so both dotted invocations and
recursive `unittest` discovery work from the repository root.

---

### Task 1: Replace prototype authority with canonical-state bindings and a compact state kernel

**Files:**
- Create: `review-loop/tests/__init__.py`
- Create: `review-loop/tests/contract/__init__.py`
- Create: `review-loop/review_loop/artifacts.py`
- Modify: `review-loop/review_loop/state.py`
- Modify: `review-loop/review_loop/__main__.py`
- Create: `review-loop/tests/unit/test_artifacts.py`
- Modify: `review-loop/tests/unit/test_state_contract.py`
- Modify: `review-loop/tests/unit/test_state_cli.py`
- Modify: `review-loop/tests/unit/test_state_gates.py`
- Modify: `review-loop/tests/unit/test_state_policy.py`
- Modify: `review-loop/tests/unit/test_state_inventory.py`
- Modify: `review-loop/tests/unit/test_state_ledger.py`
- Modify: `review-loop/tests/unit/test_state_roster.py`
- Modify: `review-loop/tests/unit/test_state_terminal.py`
- Create: `review-loop/tests/contract/helpers.py`
- Create: `review-loop/tests/contract/test_projection_authority.py`

**Interfaces:**
- Produces: controller-private `CanonicalStore(run_root: Path)` whose minimal artifact/projection registry is a field inside `review-state.json`, not a sibling manifest or independent evidence database.
- Produces: `TransitionEnvelope(operation, artifact_refs, projection, expected_governing_seal)` and `state.apply(envelope: TransitionEnvelope, snapshot: dict[str, object], authority: ProjectionAuthority) -> dict[str, object]`.
- `ProjectionAuthority.validate(envelope)` verifies every referenced binding's kind, schema version, ordered source IDs, operation, projection digest, artifact digest, and exact current governing seal from the supplied canonical snapshot.
- Test-only `bound_transition_fixture(...)` constructs a self-consistent canonical snapshot, reference, and envelope; changing any returned value after construction is the negative-test mechanism and is never imported by production modules.
- Preserves processor operations `derive_policy`, `refresh_inventory`, `record_specialist_coverage`, `plan_roster`, ledger/adjudication/FIX transitions, and terminal recomputation.
- Removes rich prose, aliases, locators, and raw report schemas from processor inputs; those remain registry-owned artifacts.

- [ ] **Step 1: Add failing artifact-authority contract tests**

```python
def test_projection_must_match_registry_binding(self):
    snapshot, ref, envelope = bound_transition_fixture(
        kind="rating", schema_version=1, target_seal="seal-a",
        operation="derive_policy",
        source_ids=("raw-rater-a", "raw-rater-b"), raw_bytes=b"{}",
        projection={"complexity": "high", "risk": "med", "gestalt_step": False},
    )
    altered = dataclasses.replace(
        envelope,
        projection={"complexity": "max", "risk": "med", "gestalt_step": False},
    )
    with self.assertRaises(ArtifactMismatch):
        state.apply(altered, snapshot, ProjectionAuthority.from_snapshot(snapshot))
```

Add companion failures for invented IDs, wrong kind, wrong schema version, stale target seal, reordered source IDs, changed projection digest, altered `TransitionEnvelope` data reaching `state.apply`, a forged production authority object, and an evidence file present without a canonical-state binding.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `cd review-loop && python3 -m unittest tests.unit.test_artifacts tests.contract.test_projection_authority -v`

Expected: FAIL because `TransitionEnvelope`, `ProjectionAuthority`, and `ArtifactMismatch` do not exist.

- [ ] **Step 3: Implement atomic canonical issuance and transition**

Use immutable JSON with `sort_keys=True`, compact separators, UTF-8, and SHA-256. The controller validates a rich object, writes only an allowed evidence file (an operative ordinary raw reviewer report or the retained multi-review aggregate), computes its binding and projection, applies the transition against an in-memory copy of canonical state, then `fsync`/`os.replace`s one new `review-state.json` containing both binding and transition. A crash before state replacement may leave an orphan evidence file, but recovery ignores and removes or reports it because no canonical binding exists. Do not write sibling artifact metadata, an event log, prompt archive, profile snapshot, copied target, or hash manifest.

```python
@dataclass(frozen=True)
class ProjectionBinding:
    operation: str
    source_ids: tuple[str, ...]
    projection_digest: str

@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    kind: str
    schema_version: int
    target_seal: str
    digest: str
```

Production controller methods construct `ProjectionAuthority` internally from
the loaded canonical snapshot; no operator or production CLI accepts an
authority implementation, registry fragment, or caller-authored binding.

- [ ] **Step 4: Refactor the state processor to compact projections**

Retain the prototype's tested fixed policy and proof-critical transitions, including separate `refresh_inventory` and post-TRIAGE `record_specialist_coverage`. Delete rich validators for report prose, aliases, narrative evidence, raw locators, and full FIX objects. Migrate `test_state_cli.py`, `test_state_gates.py`, and `test_state_roster.py` to the same compact transition envelope; the test-only CLI may load a fixture authority, while production exposes no free-form projection path. Require authority validation before every transition.

- [ ] **Step 5: Verify GREEN and regression coverage**

Run: `cd review-loop && python3 -m unittest discover -s tests/unit -t . -v`

Expected: all state and artifact tests PASS; no processor test constructs a fake non-empty proof string as authority, and crash/restart tests prove orphan evidence and uncommitted bindings are non-operative.

- [ ] **Step 6: Commit the slice**

```bash
git add review-loop/review_loop review-loop/tests/__init__.py review-loop/tests/unit review-loop/tests/contract
git commit -m "refactor(review-loop): bind compact state projections to artifacts"
```

---

### Task 2: Build the canonical prompt renderer and report validators

**Files:**
- Create: `review-loop/review_loop/prompts.py`
- Create: `review-loop/review_loop/resources/safety.md`
- Create: `review-loop/review_loop/resources/review.md`
- Create: `review-loop/review_loop/resources/round-one.md`
- Create: `review-loop/review_loop/resources/later-round.md`
- Create: `review-loop/tests/unit/test_prompts.py`
- Create: `review-loop/tests/unit/test_review_reports.py`
- Create: `review-loop/tests/unit/test_strict_role_outputs.py`
- Create: `review-loop/tests/contract/fixtures/review-reports/*.md`
- Create: `review-loop/tests/contract/fixtures/triage-results/*.json`
- Create: `review-loop/tests/contract/fixtures/role-results/{evidence,inventory,inventory-challenge,rating,adjudication,fix,final-readiness}/*.json`

**Interfaces:**
- Produces: `render_prompt(template_id: str, fragment_ids: tuple[str, ...], context: Mapping[str, str]) -> bytes`.
- Produces: `validate_review_report(body: bytes, dispatch: DispatchExpectation, process: ProcessCompletion) -> ValidatedReview | UnusableReview`.
- Produces: `validate_role_json(role_id: str, body: bytes, expectation: RoleExpectation) -> ValidatedRoleArtifact`; dispatch is a closed table for evidence discovery, inventory owner/challenge/revision, rating, TRIAGE, adjudication, FIX manifest, and final readiness. Every result envelope must exactly match expected `request_id`, `role_id`, target seal, nullable Stage-0 or exact call-input seal, and expected ID universe before its typed payload is considered.
- `ValidatedReview` retains narrative bytes and exactly one strict `review-record`; `usable` requires successful process completion and terminal `REVIEW-STATUS: COMPLETE`.

`DispatchExpectation` is a frozen value carrying `request_id`, `role`,
`charter_id`, `target_seal`, nullable `round_input_seal`, and the ordered exact
`scope_locator_ids`. `ProcessCompletion` carries the same `request_id`, exit
status, and positive process-tree termination proof; report validation rejects
an absent or mismatched completion rather than inferring it from report prose.

- [ ] **Step 1: Write renderer RED tests**

Cover missing/unknown substitutions, unknown templates/fragments, unresolved tokens in source templates, opaque substituted `{{subject_text}}`, deterministic fragment order, and exact byte equality across ordinary and adapter callers.

```python
def test_substituted_braces_are_not_rescanned(self):
    rendered = render_prompt("review", ("round-one",), {**BASE, "subject": "literal {{danger}}"})
    self.assertIn(b"literal {{danger}}", rendered)
```

- [ ] **Step 2: Write report-classifier RED tests**

Fixtures must cover preamble before `## Summary`, quoted status-like source text, trailing prose after status, duplicate or malformed fenced JSON, mismatched request/role/charter/seals/scope, duplicate source-finding IDs, empty findings, `UNABLE`, and nonzero process completion.

Add TRIAGE fixtures for missing/duplicate/foreign report or finding IDs, altered raw claim/severity/required locators, omitted empty reports, invalid factual/state combinations, wrong target/TRIAGE-input seal, and one complete valid reconciliation. The validator reconstructs immutable premises from registered raw-report artifacts and emits a compact projection builder; the controller does not implement a second ad hoc parser in Task 8.

Add valid and malformed fixtures for every other strict role:

- evidence discovery: exact gate IDs, argv arrays, applicability, `required`/`supporting`, rationale, and explicit gaps;
- inventory owner/revision: complete unique semantic IDs, aliases, consequence/evidence, optional evidenced `GENERALIST-MISS`, normalized surfaces/owning files, charter, total bijective priority order, and on refresh one continuing/successor/RETIRED mapping per prior ID with retirement reasons and explicit invalidators;
- inventory challenge: exactly `UPHOLD` or an evidenced challenge list covering omission, unsupported claims, fragmentation, or unusable charters; revision must resolve every challenge in one replacement inventory;
- rating: exact `C`/`R` tier values with evidence and optional `GESTALT: +1` containing at least three individually evidenced factors;
- adjudication: exactly the expected pending IDs, each with `UPHOLD`/`BOUNCE`/`UNDECIDED`, evidence locator, positive fact-to-row linkage, and exact authority identity/linkage when file-authorized;
- FIX manifest: a non-empty subset of the authorized OPEN ledger IDs whenever changes exist, with every changed path bound to one or more IDs in that subset, plus change description, twin-search pattern/count, test-to-spec trace when tests changed, and a declaration of attempted external actions; authorized but unaddressed rows remain OPEN;
- final readiness: `UPHOLD` or material `BLOCK` with exact evidence, procedural blocker when applicable, and a canonical `source_findings` inventory for any target findings.

For each schema reject unknown/missing fields, wrong types/enums, duplicate or foreign IDs, mismatched seals, and malformed retry output. Require complete expected-ID sets for TRIAGE, inventory mapping, adjudication, challenge resolution, and other exhaustive roles; FIX alone accepts the manifest-bound authorized subset described above. Each validator retains the rich artifact and emits only the compact projection defined by the design; later controller tasks call these validators and never parse semantic JSON themselves.

- [ ] **Step 3: Run and verify RED**

Run: `cd review-loop && python3 -m unittest tests.unit.test_prompts tests.unit.test_review_reports tests.unit.test_strict_role_outputs -v`

Expected: FAIL because the renderer and classifier are absent.

- [ ] **Step 4: Implement the minimal strict boundary**

Use `string.Formatter` only to discover declared names; do one substitution pass and never parse bracketed prose. Locate exactly one fenced JSON object labelled `review-record`; reject unknown fields. The final non-blank line must equal `REVIEW-STATUS: COMPLETE` or `REVIEW-STATUS: UNABLE`. Validate `source_findings` as unique IDs with exact `claim`, severity, and non-empty locator list. Dispatch strict role JSON by the closed role-ID table above; implement each typed duplicate/coverage/seal/provenance check there and return the exact compact transition projection plus its rich validated artifact.

- [ ] **Step 5: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.unit.test_prompts tests.unit.test_review_reports tests.unit.test_strict_role_outputs -v`

Expected: all prompt and report tests PASS.

- [ ] **Step 6: Commit the slice**

```bash
git add review-loop/review_loop/prompts.py review-loop/review_loop/resources review-loop/tests/unit/test_prompts.py review-loop/tests/unit/test_review_reports.py review-loop/tests/unit/test_strict_role_outputs.py review-loop/tests/contract/fixtures
git commit -m "feat(review-loop): add canonical prompt and report contract"
```

---

### Task 3: Move semantic roles into focused, behavior-tested resources

**Files:**
- Create: `review-loop/review_loop/resources/evidence-discovery.md`
- Create: `review-loop/review_loop/resources/inventory.md`
- Create: `review-loop/review_loop/resources/inventory-challenge.md`
- Create: `review-loop/review_loop/resources/rating.md`
- Create: `review-loop/review_loop/resources/triage.md`
- Create: `review-loop/review_loop/resources/adjudication.md`
- Create: `review-loop/review_loop/resources/holistic.md`
- Create: `review-loop/review_loop/resources/adversarial.md`
- Create: `review-loop/review_loop/resources/specialist.md`
- Create: `review-loop/review_loop/resources/fix.md`
- Create: `review-loop/review_loop/resources/final-readiness.md`
- Create: `review-loop/tests/behavior/SCENARIOS.md`
- Create: `review-loop/tests/behavior/RED.md`
- Create: `review-loop/tests/behavior/GREEN.md`
- Create: `review-loop/tests/unit/test_role_contracts.py`

**Interfaces:**
- Each role resource declares one job, its primary artifacts, non-delegation, and its strict output contract.
- Review resources compose with `safety.md`, `review.md`, and exactly one round fragment through `render_prompt`; strict-JSON roles use role-specific validators registered in `prompts.py`.

- [ ] **Step 1: Run targeted fresh-context controls before changing behavior guidance**

Probe the high-risk boundaries named by the design—rating calibration, inventory identity/coverage, evidence-gate selection, inventory challenge, bounded FIX, final readiness, and canonical review output—but retain a RED/GREEN regression only where the pre-change control demonstrates a concrete miss. Record the prompt, model/runtime, raw output locator, expected behavior, and exact miss or useful null result in `RED.md`; a useful null result blocks speculative guidance rather than requiring a permanent scenario.

- [ ] **Step 2: Add failing static contract tests**

Tests require every non-FIX target role to include the read-only/data boundary and `REPORT, NEVER FIX`; FIX alone must contain `AUTHORIZED TARGET ROOT`, exact open ledger IDs, no delegation, no installation, no commit/stage/deploy, no agent-initiated network or product/production credentials beyond the provider control channel, and manifest output.

- [ ] **Step 3: Write the minimum role resources that address observed failures**

Do not copy the full controller workflow into roles. Keep area equivalence and consequence judgment in inventory; roster mechanics in state/controller; green-making verification in adjudication; implementation only in FIX; final readiness can only uphold or block.

- [ ] **Step 4: Run GREEN behavior probes and static tests**

Run: `cd review-loop && python3 -m unittest tests.unit.test_role_contracts -v`

Repeat the RED scenarios with production resources and record outcomes in `GREEN.md`. Any remaining demonstrated loophole gets one minimal guidance amendment and one rerun.

- [ ] **Step 5: Commit the slice**

```bash
git add review-loop/review_loop/resources review-loop/tests/behavior review-loop/tests/unit/test_role_contracts.py
git commit -m "feat(review-loop): add focused behavior-tested role resources"
```

---

### Task 4: Implement sealing, delta, profiles, and persisted run preflight

**Files:**
- Create: `review-loop/pyproject.toml`
- Create: `review-loop/tests/integration/__init__.py`
- Create: `review-loop/review_loop/seals.py`
- Create: `review-loop/review_loop/profiles.py`
- Create: `review-loop/review_loop/controller.py`
- Create: `review-loop/DESIGNING_PROFILES.md`
- Create: `review-loop/tests/unit/test_seals.py`
- Create: `review-loop/tests/unit/test_profiles.py`
- Create: `review-loop/tests/integration/test_preflight.py`

**Interfaces:**
- Produces: `seal_target(root: Path, git_policy: GitPolicy) -> TargetSeal`, `seal_inputs(paths: Sequence[Path], target_seal: str) -> InputSeal`, and `materialize_delta(before: TargetSeal, after: TargetSeal, output: Path) -> DeltaArtifact`.
- Produces: `load_profile(selector: str, xdg_config_home: Path | None) -> ReviewProfile` and `resolve_policy(invocation, profile, derived_tier) -> RunPolicy`.
- Produces: `Controller.create_run(intent: InvocationIntent) -> RunState` with persisted start time, optional absolute expiry, provisional identity, ground-truth inventory, and no reviewer dispatch.

- [ ] **Step 1: Write RED tests for canonical records and deltas**

Cover readable regular files/directories, symlink/FIFO/socket/device rejection, type/identity changes during enumeration, mode-only changes, empty-directory changes, content changes, index-only changes, NUL-safe path framing, run-root overlap in both directions, and absent/ambiguous Git delta contracts.

- [ ] **Step 2: Write RED tests for profile resolution**

Cover the full strict version 1 sparse overlay: optional positive `max_time_seconds`; ordinary `holistic`, `adversarial`, and `specialists` capability/model pins; `holistic.fallback_capability`/`fallback_model` inheritance; and `holistic.multi_review.models` restricted to non-empty `claude`/`codex` values. Separately test duplicate YAML keys at every nesting level, unknown keys, wrong types, safe bare-name resolution, traversal/separator rejection, explicit paths, accepted normal-role pins, rejected non-pair multi-review pins, and non-overridable tier/safety/participants/synthesis fields.

- [ ] **Step 3: Implement seals and strict YAML loading**

Set `requires-python = ">=3.11"` and declare exactly `PyYAML>=6.0,<7` as the runtime dependency; do not add a framework or CLI package. Use descriptor-relative stable open/stat checks and canonical length-prefixed records rather than shell word splitting. The Git index identity and deterministic before/after delta are separate bound records. Implement a PyYAML loader whose mapping constructor rejects duplicate keys before defaults are applied.

- [ ] **Step 4: Implement preflight persistence**

Persist invocation intent, resolved target/base/head/exclusions, run root, ground truth, target seal, delta policy, selected profile, start time, and absolute expiry atomically before semantic dispatch. Invalid explicit profiles ask the controller caller whether to proceed with tier defaults; they never fall back silently.

- [ ] **Step 5: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.unit.test_seals tests.unit.test_profiles tests.integration.test_preflight -v`

- [ ] **Step 6: Commit the slice**

```bash
git add review-loop/pyproject.toml review-loop/review_loop/seals.py review-loop/review_loop/profiles.py review-loop/review_loop/controller.py review-loop/DESIGNING_PROFILES.md review-loop/tests/integration/__init__.py review-loop/tests/unit/test_seals.py review-loop/tests/unit/test_profiles.py review-loop/tests/integration/test_preflight.py
git commit -m "feat(review-loop): add fail-closed preflight and profiles"
```

---

### Task 5: Add contained ordinary execution, batching, deadlines, and recovery

**Files:**
- Create: `review-loop/review_loop/execution.py`
- Create: `review-loop/tests/unit/test_execution.py`
- Create: `review-loop/tests/integration/test_execution_containment.py`
- Create: `review-loop/tests/integration/fixtures/fake_reviewer.py`
- Create: `review-loop/tests/manual/ordinary-codex-smoke.sh`
- Create: `review-loop/tests/manual/ordinary-codex-smoke.md`

**Interfaces:**
- Produces: `ExecutionMapping(target_ro, inputs_ro, runtime_ro, output_rw, scratch_rw, network, credentials)`.
- Produces: `Executor.start(request: CallRequest) -> CallStarted`, `finish(started) -> CallCompletion`, `terminate(started) -> TerminationProof`, and `run_waves(requests, capacity, expiry) -> tuple[CallCompletion, ...]`.
- `CallStarted` persists a unique containment/process-tree identity and termination handle before launch; incomplete calls are never harvested after recovery.
- The sole ordinary MVP backend is a tested Codex CLI mapping. It launches `codex exec --sandbox read-only --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check --json --output-last-message /report/report.md -C /subject -` inside caller-constructed Bubblewrap; append `--model <exact-pin>` only when policy resolved an explicit pin. A directly requested different CLI is rejected unless a later tested mapping exists.

- [ ] **Step 1: Write fake-process RED tests**

Assert that an ordinary reviewer can read only its exact target and input scope, write only report/scratch, cannot write the target, peer report, canonical state, or prior round, receives only the tested provider control channel plus exact minimum reviewer authentication (never arbitrary product/production credentials), and leaves no descendant after completion or termination. Evidence-gate and FIX child commands receive no provider credential or general network path.

Assert the Codex mapping uses `--clearenv`; read-only exact-file mounts; a fresh `HOME`/`CODEX_HOME`; a read-only `auth.json`; no host `config.toml`, rules, hooks, session state, or cache; and an allowlist containing only `HOME`, `CODEX_HOME`, `PATH`, `LANG`, and provider-required TLS/DNS state. Inject fake host secrets, proxy variables, hook variables, and product credentials and prove the child cannot observe them.

- [ ] **Step 2: Write deadline/wave/recovery RED tests**

Cover host-advertised capacity, conservative default when absent, complete roster scheduling without omission, absolute deadline checked before every launch, TERM/KILL bounded cleanup, `CALL_STARTED` recovery, unprovable termination causing INDETERMINATE, and no retry/harvest from partial output.

- [ ] **Step 3: Implement and preflight the tested Codex host mapping**

Resolve `codex`, its package/runtime closure, Bubblewrap, exact auth file, certificates, and DNS inputs as stable paths outside the target. Before semantic dispatch, run the contained `codex exec --help` probe and require the exact flags named above; an absent prerequisite or flag stops preflight without dispatch. Use native `--sandbox read-only` as defense in depth inside the Bubblewrap mapping. Capture stdout/stderr only as diagnostics; publish `/report/report.md` only after exit status, process-tree reaping, post-call seals, and report validation all succeed.

The outer mapping is fixed and tested: `--clearenv --unshare-pid
--die-with-parent`; read-only `/usr`, certificate/DNS files, resolved Codex
package/entry point, exact auth file, exact target files, and exact sealed
review-data files; synthetic `/proc`, `/dev`, and tmpfs `/tmp`; fresh writable
`/home/reviewer`, `/scratch`, and `/report`; synthetic empty `/subject` as cwd;
and only `HOME`, `CODEX_HOME`, `PATH`, and `LANG` in the environment. Provider
network remains available and is disclosed as a confidentiality limitation.
No target parent directory, host config/rules/hooks, canonical state, peer
artifact, prior round, or unrelated credential is mounted.

- [ ] **Step 4: Prove the real mapping starts**

`ordinary-codex-smoke.sh --preflight` runs without provider credentials and proves the real executable/runtime starts inside the declared namespace, sees no injected host secret, cannot write a read-only target, and can write only report/scratch. When valid Codex authentication is already present, the documented live mode sends a minimal fixed review fixture and requires one valid report; missing credentials record NOT RUN rather than weakening the deterministic mapping tests.

- [ ] **Step 5: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.unit.test_execution tests.integration.test_execution_containment -v`

- [ ] **Step 6: Commit the slice**

```bash
git add review-loop/review_loop/execution.py review-loop/tests/unit/test_execution.py review-loop/tests/integration/test_execution_containment.py review-loop/tests/integration/fixtures/fake_reviewer.py review-loop/tests/manual/ordinary-codex-smoke.sh review-loop/tests/manual/ordinary-codex-smoke.md
git commit -m "feat(review-loop): contain ordinary review execution"
```

---

### Task 6: Deliver Stage 0 evidence discovery and the ordinary clean tracer

**Files:**
- Create: `review-loop/review_loop/evidence.py`
- Modify: `review-loop/review_loop/controller.py`
- Create: `review-loop/review_loop/report.py`
- Create: `review-loop/tests/unit/test_evidence.py`
- Create: `review-loop/tests/integration/test_evidence_execution.py`
- Create: `review-loop/tests/integration/test_controller_clean.py`
- Create: `review-loop/tests/integration/fixtures/clean_target/`
- Create: `review-loop/tests/integration/fixtures/evidence_projects/`

**Interfaces:**
- Produces: `discover_evidence(operator, repository, scout) -> EvidencePlan`, where precedence is operator instruction, repository authority, then scout suggestion.
- Produces: `execute_gate(gate: Gate, mapping: ExecutionMapping, seal: TargetSeal) -> GateResult`.
- Controller stages become persisted enums `PREFLIGHT`, `STAGE0`, `REVIEW`, `TRIAGE`, `FIX`, `CLOSE`, `COMPLETE`, `INDETERMINATE`, and `CANCELLED_BEFORE_REVIEW`.
- Stage 0 runs the contained evidence scout and every applicable baseline gate before inventory/rating. It then dispatches inventory owner/challenger and, only for automatic effort, two raters; every result becomes a canonical artifact plus compact projection.
- Round 1 freezes holistic, adversarial, and every required specialist role; a clean report still flows through TRIAGE before CLOSE.

- [ ] **Step 1: Write evidence discovery and execution RED tests**

Cover operator/repository/scout precedence, valid empty discovery as a disclosed gap, malformed scout retry, shell/control-operator rejection, writes outside disposable scratch, credentials/network denial, exact argv/result/seal recording, required versus supporting classification, and contained process cleanup. An executed applicable failure—including a supporting gate—prevents convergence; only an unavailable supporting opportunity is a disclosed non-blocking gap.

- [ ] **Step 2: Write a failing explicit-low clean tracer through the real gate path**

The fake target exposes one safe required baseline command and one Minor inventory area. The real evidence helper validates and executes that command before any inventory/rating dispatch; two usable empty-finding reports, one usable empty TRIAGE result, and an UPHOLD final challenge follow. Assert execution order, `CONVERGED`, merge-ready, full staffing accounting, exact seals, and no FIX.

- [ ] **Step 3: Write failing automatic-tier and confirmation tests**

Assert max-of-two axes, combined high/high step-up, at-most-once gestalt step-up, malformed rater retry, explicit tier skipping raters, automatic `max` confirmation, explicit `max` no prompt, `no_confirm` no prompt, decline cancellation without CLOSE, and expiry while waiting producing INDETERMINATE.

- [ ] **Step 4: Implement the minimum ordinary lifecycle**

The scout emits argv arrays plus applicability/classification and rationale. Validate argv against a closed safe-command policy and reject shell strings. Execute baseline gates using the evidence mapping before semantic work and store command/rationale/result in canonical state while projecting only gate ID, seal, classification, applicability, and outcome. Join canonical inventory artifacts back to state-selected area IDs when rendering roles, freeze the roster before waves, run every usable raw report through strict TRIAGE, and compute CLOSE only after the final challenger and final seal check.

- [ ] **Step 5: Generate the final Markdown report from state**

Include selected policy, confirmation path, planned/completed staffing, seals, gate plan/results, evidence gaps, mutation evidence or one-line follow-up, degraded behavior, ledger counts, residual limitations, convergence, merge-readiness, and the exact failed conjunct when not green.

- [ ] **Step 6: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.unit.test_evidence tests.integration.test_evidence_execution tests.integration.test_controller_clean -v`

- [ ] **Step 7: Commit the slice**

```bash
git add review-loop/review_loop/evidence.py review-loop/review_loop/controller.py review-loop/review_loop/report.py review-loop/tests/unit/test_evidence.py review-loop/tests/integration/test_evidence_execution.py review-loop/tests/integration/test_controller_clean.py review-loop/tests/integration/fixtures/clean_target review-loop/tests/integration/fixtures/evidence_projects
git commit -m "feat(review-loop): complete gated ordinary clean tracer"
```

---

### Task 7: Extend evidence with document gates and opportunistic mutation

**Files:**
- Modify: `review-loop/review_loop/evidence.py`
- Modify: `review-loop/review_loop/controller.py`
- Modify: `review-loop/tests/unit/test_evidence.py`
- Create: `review-loop/tests/unit/test_mutation_evidence.py`
- Modify: `review-loop/tests/integration/test_evidence_execution.py`
- Modify: `review-loop/tests/integration/fixtures/evidence_projects/`

**Interfaces:**
- Produces: `run_mutation_evidence(plan, disposable_copy) -> MutationResult`; mutation is always supporting evidence.

- [ ] **Step 1: Write code and document gate RED tests**

Code fixtures cover existing safe lint/test commands and missing mutation tooling. Document fixtures cover repository-provided linters/schema/link checks plus an explicitly selected behavioral skill test; absence is a disclosed gap, not invented machinery. Reassert that any executed applicable failure blocks convergence regardless of `required`/`supporting`, while unavailable supporting evidence does not.

- [ ] **Step 2: Write mutation RED tests**

Cover configured tool success, no installation or initialization, bounded manual mutation in a disposable copy, baseline failure invalidating mutation evidence, caught/equivalent/surviving mutants, no numeric score threshold, and the single final suggestion when eligible tooling is missing.

- [ ] **Step 3: Implement document and mutation evidence**

Reuse the Task 6 discovery/safety boundary. Add document-specific applicability and bounded manual mutation in a disposable copy; rerun applicable gates after FIX. Never install or initialize mutation tooling and never turn a mutation score into terminal authority.

- [ ] **Step 4: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.unit.test_evidence tests.unit.test_mutation_evidence tests.integration.test_evidence_execution -v`

- [ ] **Step 5: Commit the slice**

```bash
git add review-loop/review_loop/evidence.py review-loop/review_loop/controller.py review-loop/tests/unit/test_evidence.py review-loop/tests/unit/test_mutation_evidence.py review-loop/tests/integration/test_evidence_execution.py review-loop/tests/integration/fixtures/evidence_projects
git commit -m "feat(review-loop): add document and mutation evidence"
```

---

### Task 8: Implement TRIAGE, adjudication, bounded FIX, and repeated rounds

**Files:**
- Create: `review-loop/review_loop/fix.py`
- Modify: `review-loop/review_loop/controller.py`
- Create: `review-loop/tests/unit/test_fix.py`
- Create: `review-loop/tests/contract/test_triage_projection.py`
- Create: `review-loop/tests/integration/test_findings_loop.py`
- Create: `review-loop/tests/integration/fixtures/fix_target/`

**Interfaces:**
- TRIAGE validates the exact usable report/finding universe, preserves immutable raw claim/severity/locators, and maps each source finding exactly once to a canonical ledger ID.
- Adjudication accepts only exact pending IDs and `UPHOLD`, `BOUNCE`, or `UNDECIDED`, with positive seal-bound proof for green-making decisions.
- Produces: `FixController.prepare(open_rows, target_seal, evidence_plan) -> FixRequest`, `validate_candidate(request, before, after, manifest) -> ValidatedFix`, and `apply(validated) -> FixTransition`.
- Produces: `build_round_scopes(round_state, delta, manifest, inventory) -> RoundScopes`. `RoundScopes` contains four distinct sealed boundaries: inventory-refresh inputs; each frozen reviewer role's exact target/review-data scope; TRIAGE's exact usable raw reports/current evidence; and adjudication's exact pending result/authority inputs.

- [ ] **Step 1: Write TRIAGE/adjudication RED contracts**

Cover missing/duplicate/foreign report or finding IDs, altered source premise, invalid factual/state pair, strict two-call adjudication, full retry after malformed first call, undecided-subset retry, atomic bounce, no call for an empty set, direct ledger-ID-bound user acceptance, and positive proof rather than absence of contradiction.

- [ ] **Step 2: Write FIX containment and manifest RED tests**

Cover exact OPEN-ID authorization, one non-delegating implementer, disposable-copy preference, tested direct-write fallback, no dependency/lockfile tooling changes, no install/commit/stage/deploy, no agent-invoked network or product/production credentials beyond the provider control channel needed to run the implementer, manifest entry per fixed ID, changed-path equality, twin search, test-to-spec trace, and unrelated/external actions.

- [ ] **Step 3: Write repeated-round RED tests**

Cover post-FIX required gates, canonical delta/patch, `OPEN -> FIX_APPLIED`, later proof-linked `FIX_VERIFIED`, `FIX_APPLIED -> OPEN`, reopened settlements, coverage invalidation, successor STALE behavior, Critical restaffing, round caps, oscillation, and honest NOT CONVERGED hand-back. Construct the inventory-refresh seal from prior mappings/coverage plus the verified delta and manifest; construct the reviewer seal only after refresh. Later holistic/adversarial scopes contain exactly changed target files plus delta, optional content patch, manifest, relevant ledger, and refreshed inventory; each specialist adds exactly its current resolved owning-surface files. TRIAGE and adjudication receive their separately sealed inputs. Reject omitted or extra target/review-data files and any pre/post-call seal mismatch before state advancement.

- [ ] **Step 4: Implement minimal triage/adjudication/FIX flow**

Compare candidate target state and manifest before recording `FIX_APPLIED`; apply validated candidate changes atomically where the host supports it. If a direct-write FIX fails or is interrupted, refuse automatic recovery and disclose that rollback is not claimed. After usable specialist TRIAGE, call `record_specialist_coverage`; a linked reopen wins and leaves coverage STALE.

- [ ] **Step 5: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.unit.test_fix tests.contract.test_triage_projection tests.integration.test_findings_loop -v`

- [ ] **Step 6: Commit the slice**

```bash
git add review-loop/review_loop/fix.py review-loop/review_loop/controller.py review-loop/tests/unit/test_fix.py review-loop/tests/contract/test_triage_projection.py review-loop/tests/integration/test_findings_loop.py review-loop/tests/integration/fixtures/fix_target
git commit -m "feat(review-loop): close the triage fix and re-review loop"
```

---

### Task 9: Harden recovery, seal drift, final readiness, and terminal reporting

**Files:**
- Modify: `review-loop/review_loop/controller.py`
- Modify: `review-loop/review_loop/report.py`
- Create: `review-loop/tests/integration/test_recovery.py`
- Create: `review-loop/tests/integration/test_final_readiness.py`
- Create: `review-loop/tests/integration/test_terminal_failures.py`

**Interfaces:**
- Recovery resumes only from an atomically published phase boundary after checking the original absolute expiry and all applicable seals.
- Final readiness returns sealed `UPHOLD` or `BLOCK`; findings always enter supplemental TRIAGE and become stale after target mutation.

- [ ] **Step 1: Write recovery and drift RED tests**

Cover restart after every published boundary, `CALL_STARTED` cleanup, deadline rebasing rejection, concurrent-writer uncertainty, Stage-0/reviewer/TRIAGE/adjudication input drift, post-FIX baseline acceptance before delta seal, and final CLOSE drift.

- [ ] **Step 2: Write final-challenge RED tests**

Assert that UPHOLD cannot create eligibility, procedural BLOCK prevents merge-readiness, Important+ findings return through TRIAGE and FIX when policy permits, Minor observations do not independently block, malformed output retries once, and target mutation requires a fresh challenge.

- [ ] **Step 3: Implement fail-closed recovery and total terminal rollup**

Every INDETERMINATE result identifies its stage, call, operative/non-operative evidence, failed conjunct, and cleanup proof. Expiry takes precedence over cancellation and CLOSE. Preserve a valid `CONVERGED, not merge-ready` result where deterministic blockers warrant it.

- [ ] **Step 4: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.integration.test_recovery tests.integration.test_final_readiness tests.integration.test_terminal_failures -v`

- [ ] **Step 5: Commit the slice**

```bash
git add review-loop/review_loop/controller.py review-loop/review_loop/report.py review-loop/tests/integration/test_recovery.py review-loop/tests/integration/test_final_readiness.py review-loop/tests/integration/test_terminal_failures.py
git commit -m "feat(review-loop): harden recovery and final readiness"
```

---

### Task 10: Add the narrow review-loop opt-in to multi-review

**Files:**
- Modify: `multi-review/multi_review/core/promptfile.py`
- Modify: `multi-review/multi_review/core/prompt.py`
- Modify: `multi-review/multi_review/core/aggregate.py`
- Modify: `multi-review/multi_review.py`
- Modify: `multi-review/tests/unit/test_promptfile.py`
- Modify: `multi-review/tests/unit/test_prompt.py`
- Modify: `multi-review/tests/unit/test_multi_review_driver.py`
- Create: `review-loop/tests/contract/test_multi_review_records.py`
- Create: `review-loop/tests/contract/fixtures/multi-review-records/`

**Interfaces:**
- Extends v2 with optional `verbatim_custom_prompt: bool = false`, `use_cli_defaults: bool = false`, `require_complete_status: bool = false`, and absent `review_record_expectation`.
- Existing callers preserve wrapped custom prompts and current defaults.
- The opt-in validates one participant `review-record`, exact terminal COMPLETE, expected shared dispatch fields, and the controller-preallocated raw report ID for that fixed slot; aggregate frontmatter safely serializes qualified records.

- [ ] **Step 1: Add RED compatibility, exact-byte, and transport-integrity tests**

Prove non-opt-in v2 behavior is byte-for-byte unchanged. For opt-in custom tasks, assert each delivered prompt body exactly equals `custom_prompt`, including final newline presence/absence, while `files` still validates readable scope without being rendered. A fake reviewer then replaces, links, truncates, or rewrites the driver-generated `prompt.txt`; after fan-out and before aggregation, the driver must byte-compare or hash-check transport against the in-memory canonical payload, remove any staged/final report, and exit unsuccessfully on mismatch.

- [ ] **Step 2: Add RED classifier/frontmatter tests**

Cover missing/duplicate/malformed records, status-looking body text, mismatched request/seals/scope, swapped raw IDs, hostile multiline/YAML/delimiter claims, duplicate YAML keys, safe round-trip, exact unpinned CLI defaults, and exact pinned models without fallback defaults.

- [ ] **Step 3: Implement the smallest opt-in extension**

Do not add `--sandbox`, participant selection beyond existing v2 fields, synthesis behavior, or a review-loop orchestration mode. Keep prompt transport out of argv. Retain the canonical prompt payload/digest in trusted driver memory, verify the on-disk transport before every fixed-client launch and again after all reviewer subprocesses are reaped but before report publication, and fail the call on drift. Serialize frontmatter through the YAML library and reject duplicate keys during adapter parsing.

- [ ] **Step 4: Verify multi-review GREEN**

Run: `cd multi-review && uv run pytest tests/unit/test_promptfile.py tests/unit/test_prompt.py tests/unit/test_multi_review_driver.py -q`

Expected: all focused tests PASS and current non-review-loop fixtures remain unchanged.

- [ ] **Step 5: Run the cross-codebase fixture contract**

Run: `cd review-loop && python3 -m unittest tests.contract.test_multi_review_records -v`

- [ ] **Step 6: Commit the slice**

```bash
git add multi-review review-loop/tests/contract
git commit -m "feat(multi-review): add strict review-loop driver opt-in"
```

---

### Task 11: Integrate the caller-contained fixed-pair multi-review slot

**Files:**
- Create: `review-loop/review_loop/multi_review.py`
- Modify: `review-loop/review_loop/controller.py`
- Create: `review-loop/tests/unit/test_multi_review_adapter.py`
- Create: `review-loop/tests/integration/test_multi_review_containment.py`
- Create: `review-loop/tests/integration/test_multi_review_fallback.py`
- Reuse: `multi-review/tests/manual/headless-driver-smoke.sh`

**Interfaces:**
- Produces: `MultiReviewAdapter.invoke(request: HolisticRequest, policy: MultiReviewPolicy) -> MultiReviewResult`.
- The adapter always writes `reviewers: [claude, codex]`, `synthesizer: none`, `task: custom`, exact `files`, exact prompt, opt-in fields, and explicit model pins when configured.
- `MultiReviewResult` is either one validated aggregate envelope with two qualified raw reports or one structured ordinary-fallback reason; target/input seal drift is INDETERMINATE, never fallback.

- [ ] **Step 1: Write adapter construction RED tests**

Assert one fresh empty output directory, driver YAML outside it, exact fixed pair, no generic CLI defaults for unpinned reviewers, no prompt bytes in argv, distinct preallocated raw IDs, driver-config seal, and exact canonical prompt bytes.

- [ ] **Step 2: Write whole-call Bubblewrap RED tests from the supported recipe**

Start with the checked-in multi-review smoke mappings. Require `--clearenv --unshare-pid --die-with-parent`, read-only driver/runtime/CLI/config and exact target/review-data mounts, one fresh whole-call home/state/scratch mapping, unlisted target unreadability, non-writable live client state, and wrapper-directed complete-tree shutdown. Inject host API/product tokens, proxy variables, hook variables, and configuration paths and prove none survives the explicit environment allowlist. Build and assert this mount policy:

```text
read-only system: /usr, /etc/ssl, /etc/ca-certificates, /etc/hosts,
                  /etc/hostname, /etc/nsswitch.conf
WSL only:         /mnt/wsl plus /etc/resolv.conf -> /mnt/wsl/resolv.conf
synthetic:        /proc, /dev, tmpfs /tmp, /bin -> /usr/bin,
                  /lib -> /usr/lib, /lib64 -> /usr/lib64
read-only runtime:/workspace/multi-review, /opt/uv/uv,
                  /opt/bin/claude, /opt/codex/package and codex symlink
read-only request:/request.yaml and each exact resolved `files` entry at its
                  original absolute path; create namespace-only ancestors
writable fresh:   /home/review, /uv-cache, /out
read-only auth:   host Codex auth file -> /home/review/.codex/auth.json
environment:      `--clearenv`, then HOME=/home/review,
                  CLAUDE_CONFIG_DIR=/home/review/.claude,
                  CODEX_HOME=/home/review/.codex, UV_CACHE_DIR=/uv-cache,
                  PATH=/opt/bin:/opt/uv:/usr/bin:/bin, LANG=C.UTF-8
network:          shared provider network; no other host paths
command:          read the Claude OAuth token from wrapper stdin, close stdin,
                  export only that token, then exec `/opt/uv/uv run
                  --offline --isolated
                  /workspace/multi-review/multi_review.py --prompt-file
                  /request.yaml --out-dir /out --timeout <remaining-seconds>`
```

Resolve every runtime and auth source as a stable regular file/tree outside the target before argv construction. Seed `/uv-cache` from already-present required runtime content only; `--offline --isolated` makes an empty or incomplete cache fail before either reviewer launches rather than resolving over the retained provider network. Assert the current limitation too: fake reviewers share the namespace containing driver transport/output. Their attempts to replace, link, or corrupt `prompt.txt`, `.REVIEW.md.tmp`, or `REVIEW.md` must fail the prompt's post-fan-out byte check, publication, or adapter validation and take ordinary fallback, never produce usable evidence. The read-only driver YAML also receives pre/post host-side seal checks.

- [ ] **Step 3: Write failure/fallback RED tests**

Cover missing/unusable Bubblewrap, incomplete offline runtime/cache before reviewer launch, target-intersecting runtime closure, leaked host environment, driver failure, malformed or single-participant result, prompt/output interference, pin rejection/downgrade, deadline/process-tree termination, pre/post YAML drift, pre/post target/input drift, no multi-review retry, fallback deadline/seal recheck, and failed fallback making the round INDETERMINATE.

- [ ] **Step 4: Implement the caller-side adapter**

Construct only the exact fixed-pair whole-call wrapper; do not add sandbox auto-detection or native per-reviewer containment to review-loop. Send termination signals to the Bubblewrap wrapper and require complete descendant cleanup before accepting output. Parse only leading frontmatter, reject special or inconsistent output artifacts, mechanically build one aggregate TRIAGE envelope from its two participant records, and include the interim shared-namespace limitation in the final run evidence.

- [ ] **Step 5: Verify GREEN**

Run: `cd review-loop && python3 -m unittest tests.unit.test_multi_review_adapter tests.integration.test_multi_review_containment tests.integration.test_multi_review_fallback -v`

- [ ] **Step 6: Run the existing live/manual compatibility gate when credentials are available**

Run: `cd multi-review && tests/manual/headless-driver-smoke.sh`

If credentials are unavailable, record the gate as NOT RUN with that exact limitation; do not weaken deterministic fake-process containment tests.

- [ ] **Step 7: Commit the slice**

```bash
git add review-loop/review_loop/multi_review.py review-loop/review_loop/controller.py review-loop/tests/unit/test_multi_review_adapter.py review-loop/tests/integration/test_multi_review_containment.py review-loop/tests/integration/test_multi_review_fallback.py
git commit -m "feat(review-loop): add contained multi-review holistic slot"
```

---

### Task 12: Rewrite the installed skill and run final forward acceptance

**Files:**
- Modify: `review-loop/SKILL.md`
- Modify: `review-loop/README.md`
- Modify: `review-loop/dispatch.md`
- Delete: `review-loop/reviewer-addendum.md`
- Modify: `review-loop/review_loop/__main__.py`
- Create: `review-loop/tests/integration/test_cli.py`
- Create: `review-loop/tests/behavior/FINAL.md`
- Create: `review-loop/tests/ACCEPTANCE.md`

**Interfaces:**
- `SKILL.md` retains only invocation interpretation, controller stages, non-obvious safety/convergence invariants, resource-loading instructions, confirmation behavior, and final hand-back contract.
- `dispatch.md` documents supported execution mappings and troubleshooting without duplicating controller policy.
- The entry point accepts controller-owned invocation JSON or host calls; it does not expose a free-form projection-plus-registry authority bypass.

- [ ] **Step 1: Run fresh-context RED controls against the legacy skill**

Exercise automatic effort, max confirmation exceptions, code target with tests, technical-document target with and without mechanical gates, findings requiring FIX, missing mutation tooling, excess required specialists, failed reviewer, and final readiness. Record observed legacy failures in `FINAL.md` before editing `SKILL.md`.

- [ ] **Step 2: Rewrite the skill to the minimum governing controller contract**

Point every semantic role to its resource; point deterministic actions to helpers. Remove quiet counters, numeric staffing confirmation/caps, old fixed five-round prose, inline reviewer prompt duplication, and manual shell state-machine instructions. Preserve the North Star and qualified evidence disclosure.

- [ ] **Step 3: Add CLI and migration tests**

Assert explicit/automatic tiers, no-confirm semantics, profile/deadline intent, status recovery, final report path, invalid operator input, and absence of any production CLI accepting caller-authored projection authority.

- [ ] **Step 4: Run the complete deterministic suite**

Run: `cd review-loop && python3 -m unittest discover -s tests -t . -v`

Run: `cd multi-review && uv run pytest -q`

Run: `git diff --check`

Expected: all deterministic tests PASS and whitespace validation is clean.

- [ ] **Step 5: Run GREEN behavioral acceptance**

Repeat every Step 1 scenario against the installed candidate skill with fresh agents. Record exact outputs, variance, remaining limitations, and whether each pressure scenario now satisfies its ground truth. A failed safety or false-green scenario blocks completion; a useful null result is recorded rather than hidden.

- [ ] **Step 6: Independently review the final implementation**

Run separate spec-compliance and code-quality reviews over the complete diff. Then run a fresh final review-loop forward test on one code fixture and one technical-document fixture. Apply accepted findings through the same RED/GREEN discipline and rerun affected gates.

- [ ] **Step 7: Record final acceptance**

`review-loop/tests/ACCEPTANCE.md` must list each design acceptance criterion, its deterministic or behavioral evidence path, PASS/FAIL/NOT RUN, and every residual limitation. It must explicitly state whether multi-review's live Bubblewrap smoke ran or was unavailable.

- [ ] **Step 8: Commit the completed MVP**

```bash
git add review-loop multi-review
git commit -m "feat(review-loop): deliver evidence-driven review MVP"
```

## Plan Self-Review Checklist

- [x] Every section 1–10 design requirement maps to at least one task above.
- [x] Ordinary review reaches a clean end-to-end tracer before multi-review work begins.
- [x] Multi-review is an MVP acceptance item but no generalized sandbox selector is introduced.
- [x] Every behavior-bearing prose change follows a focused pre-change control; only demonstrated misses create durable RED/GREEN regressions, while useful null controls are recorded without speculative guidance or permanent scenarios.
- [x] Every production-code task begins with a test that fails for the intended missing behavior.
- [x] No task authorizes dependency installation, deployment, commits by review-loop, or uncontained target access.
- [x] Final success claims are withheld until fresh deterministic, behavioral, and independent-review evidence exists.
