# Feature Forge Implementation Plan

**Status:** Historical frozen plan. It records the inputs and vocabulary used
for the original implementation and is not current operational authority.
Post-freeze changes replaced the caller-supplied review charter with
review-loop's actual subject/ground-truth/deployment-context/completion inputs
and rewrote fixture predicates `FC-2`, `FCr-3`, and `FCr-4` in behavior-based
terms. Consult the live owner references and fixture for current behavior; do
not execute the superseded instructions embedded below.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Feature Forge override:** this plan returns for independent plan review and freeze before execution; it does not offer, begin, or hand off execution. Once frozen, these checkboxes are authority and are never edited for progress; the run ledger owns progress.

**Goal:** Remediate and requalify the repository-local `feature-forge` skill so it takes a bounded Git work unit from specification through one recoverable, durable logical Finish operation without expanding the MVP into a runtime.

**Architecture:** Keep `SKILL.md` as a concise discoverable controller. `workflow.md` owns stages, state, identities, invalidation, checkpoint categories, and the Finish journal; `authority.md` owns automation, change control, and acceptance; `adapters-and-reviews.md` owns the four sub-skill adapters, worker-packet contract, and review charters. The ledger and final report are mutable evidence templates, not frozen authorities. Qualification first freezes an amended fixture revision and proves its RED failures against the current package; only then do narrowly owned package remediations and a fresh immutable GREEN campaign occur.

**Tech Stack:** Agent Skills Markdown/YAML, Git, shell contract checks, `skill-creator`, Superpowers skills, `review-loop`, fresh-context agents. No Node, Python application, workflow DSL, database, daemon, or third-party dependency is added.

**Status:** Frozen reviewed amended plan — derived from frozen amended specification `docs/superpowers/specs/2026-08-17-feature-forge-design.md@f5e5d648bb8cbdb6f661c87cc6ff9b98476db09d` (commit `37177b2`).

## Global Constraints

- Git repositories only. Establish or verify an isolated non-primary worktree before the first tracked Feature Forge artifact write; preserve unrelated primary-checkout changes.
- The only outer-workflow authority artifacts are the canonical specification, canonical plan, run ledger, and final report. Qualification reports and fixture evidence are test evidence, not run authority.
- The frontier LLM is the semantic controller. Native tasks are disposable display only; the tracked run ledger is durable authority. Do not add a runtime program, parser, workflow engine, or dependency.
- Modes are `interactive` (`none`), `supervised` (`default`, the default), and `unattended` (`full`). Automation changes decision authority, never assurance gates.
- The workflow has exactly fourteen ordered stages and exactly eight conditional checkpoint categories. A clean, committed implementation subject is required for implementation review and final verification; specification and plan candidates use exact file-content seals and may remain uncommitted between review rounds.
- Frozen Git blob identities apply only to the independently reviewed specification and plan. Candidate seals are exact review subjects, while the ledger and final report remain mutable lifecycle evidence.
- Finish means one durable **logical** operation per run, not physically atomic exactly-once external effects across a crash. It has a stable `finish_id`, is the sole/last external skill invocation, and uses recovery/reconciliation instead of a second logical invocation.
- The specification and plan are frozen before implementation. Scope/machinery remains MVP-bounded; only an approved requirement or minimum blocking-defect correction can add machinery.
- `review-loop` runs only the three named charters. It receives the exact subject, ground truth, charter, and completion criterion; artifacts remain outside the sealed target tree.
- Keep `feature-forge/SKILL.md` trigger-only in frontmatter, beginning with `Use when`, and keep its body below 500 words.
- Use explicit-path staging, inspect staged content, never combine unrelated user changes, never create an empty commit, and never amend/squash automatically.
- Run `superpowers:finishing-a-development-branch` only as the Stage 14 adapter and exactly once per run. Do not use `executing-plans` as the outer controller.
- The historical fixture commit `cf38cfd3613e77fb4bc6deafe26405eb9774a030` and its blob `968ecd43bf966d803b64d8927b89819c3fba1134` are immutable historical evidence. Never edit them in place or claim they covered the amended specification.

## File map

| File | Action | Single responsibility |
|---|---|---|
| `feature-forge/SKILL.md` | Modify (Task 1) | Trigger, concise controller, correct terminal order, direct resource links |
| `feature-forge/agents/openai.yaml` | Inspect only (Task 1) | Existing Codex UI metadata; change only if validation proves it conflicts with the controller |
| `feature-forge/references/workflow.md` | Modify (Task 2) | Canonical artifacts, 14 stages, state/identity/invalidation, eight checkpoint categories, Finish state machine and recovery |
| `feature-forge/references/authority.md` | Modify (Task 3) | Automation authority, hardening, materiality, freezes/change control, complete acceptance/UAT contract |
| `feature-forge/references/adapters-and-reviews.md` | Modify (Task 4) | Four exact adapters, worker-packet schema, execution selection, review charters/result mapping |
| `feature-forge/assets/ledger-template.md` | Modify (Task 5) | Copyable mutable ledger schema including Finish journal |
| `feature-forge/assets/final-report-template.md` | Modify (Task 5) | Truthful Stage 13/14 report and acceptance/Finish receipts |
| `docs/feature-forge/skill-tdd/fixtures.md` | Modify under change control (Task R0) | New immutable amended-specification fixture revision; old blob remains in history |
| `docs/feature-forge/skill-tdd/2026-08-17-amended-red-results.md` | Create (Task R0) | Baseline direct RED failures of the current package against the newly frozen fixture revision |
| `docs/feature-forge/skill-tdd/2026-08-17-amended-green-results.md` | Create (Task 6) | Fresh direct qualification evidence for the amended package and fixture revision |
| `docs/feature-forge/reviews/2026-08-17-amended-skill-review.md` | Create (Task 7) | Cold-reader, holistic/adversarial review, and final fresh verification evidence |
| `docs/superpowers/plans/2026-08-17-feature-forge.md` | Modify now | This amendment candidate; refreeze only after independent plan review |

## Contract ownership, interfaces, and dependency order

| Contract | Sole owner | Required consumers |
|---|---|---|
| Canonical paths/slug, 14 stages, outer and review state, frozen identities, candidate seals, invalidation, checkpoint categories, Finish phases/recovery | `workflow.md` | controller, authority, adapters, templates, fixtures |
| Modes, materiality, hardening frontier, candidate/freeze authority, UAT classification/participant/exercise/substitute/evidence criterion | `authority.md` | controller, workflow by reference, adapters, templates, fixtures |
| `brainstorm-return`, `plan-return`, `execute-return`, `finish-authority`; execution choice; worker packets; review charters and native verdict mapping | `adapters-and-reviews.md` | controller, workflow by reference, fixtures |
| Field order and copy-time completeness only | ledger/final-report templates | controller and qualification fixtures |

Task R0 is a hard prerequisite, deliberately numbered separately so Tasks 1–5 retain their package-owner IDs and Task 6 retains its final-qualification ID:

```text
Task R0: amend + freeze fixture revision -> reproduce RED against current package
                                        -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 1
                                        -> Task 6: full immutable GREEN qualification
                                        -> Task 7: cold-reader + independent review + fresh verification
```

Tasks 1–5 are prohibited until Task R0's fixture and RED evidence commits exist. Execute Task 2 first because it owns workflow vocabulary; Task 3 consumes it, Task 4 consumes Tasks 2–3, Task 5 copies owned terms from Tasks 2–4, and Task 1 is last because the concise controller consumes every completed reference and asset path. No implementation owner changes a file owned by another task. Task 6 never edits `feature-forge/`; it reports failed predicates to the controller, which routes them to the sole owning Task 1–5 path and then restarts Task 6. Any material Task 7 finding restarts at that owner, then reruns Task 6 and all of Task 7.

---

### Task R0: Amend and freeze qualification fixtures, then reproduce RED

**Requirements/scenarios:** direct controls for REQ-001/SCN-001 through REQ-012/SCN-012 and SCN-013; preserves the seven historical regression controls.

**Files:**

- Modify: `docs/feature-forge/skill-tdd/fixtures.md`
- Create: `docs/feature-forge/skill-tdd/2026-08-17-amended-red-results.md`
- Read only: `feature-forge/`, historical fixture/result/baseline evidence

**Interfaces:**

- Consumes: frozen amended specification blob `f5e5d648bb8cbdb6f661c87cc6ff9b98476db09d`, historical fixture commit/blob, the complete current package
- Produces: a new committed fixture identity, an unedited historical identity, and exact baseline RED evidence that later GREEN runs must supersede
- Does not produce: package edits, a validator, a second outer-authority artifact, or retroactive coverage claims

- [ ] **Step 1: Record fixture lineage and create the amended fixture content before dispatch**

Replace `fixtures.md` with a revision headed `Feature Forge Amended-Specification Pressure-Test Fixtures`. Its immutable-lineage section names both the historical commit/blob and the amended specification commit/blob, explains that this is a new revision rather than a correction of historical evidence, and forbids mutation after dispatch.

Retain the seven original regression prompts and their binary predicates unchanged in substance:

```text
PREMATURE, SCOPE, PLAN-REVIEW, NESTED-FINISH, UNATTENDED, DIRTY-RESUME, TASK-LOSS-RESUME
```

The complete amended fixture registry follows. Every named prompt is model-facing and copied verbatim; each `XX-n` list is a fixed evaluator-only atomic predicate list and is never dispatched to a model. Run each named control five times in RED and GREEN.

Replace the historical model-facing prompts for `LEDGER-ACTIVE` and `PIPELINE-SSO` with these exact amended forms. Retain historical evaluator predicates `LA-1`–`LA-6` and `PS-1`–`PS-11` except for their former seven-category Finish expectation. Add the fixed predicates below; each retained control passes only when its retained predicates and all additions pass:

```text
LEDGER-ACTIVE: Produce the complete durable Markdown run ledger for org-sso,
automation supervised, worktree /repo/.worktrees/org-sso, branch feature/org-sso.
Spec is frozen at docs/superpowers/specs/2026-08-17-org-sso-design.md blob a111;
plan is frozen at docs/superpowers/plans/2026-08-17-org-sso.md blob b222. Spec
review passed at reviews/spec-17.md; plan review passed at reviews/plan-20.md;
implementation via subagent-driven-development is complete. Implementation review
is already active and has no outcome. Verification and acceptance are pending.
The Stage 13 report has not been written. No finish_id exists yet and Finish is
pending. D-003 used supervised authority for a non-semantic internal name. Native
tasks are disposable. Output only the ledger.

PIPELINE-SSO: You have a Git repository and available skills brainstorming,
grilling, writing-plans, review-loop, subagent-driven-development,
executing-plans, verification-before-completion, and finishing-a-development-
branch. The user says: “Implement organization SSO as a moderate cross-component
feature, carry it all the way through safely, and use supervised automation. I
may be offline during implementation.” Give the exact outer workflow, including
artifacts, freezes, reviews, pauses, durable resume state, all eight conditional
Git checkpoint categories, Stage 13/14 Finish records, acceptance, and Git
integration. Be concise but operational.
```

```text
LA-7: ledger records frozen <path>@<blob-id> identities only for specification
and plan, never for ledger or final report.
LA-8: while implementation review is active, verification, acceptance, Report,
and Finish remain pending; it does not allocate finish_id, advance Stage 13, or
invoke Finish.

PS-12: terminal order is Acceptance -> Stage 13 Report/active/ready -> Stage 14
Finish; branch finishing is not invoked before Stage 13.
PS-13: Finish is one durable logical operation under one finish_id and uses
ready, claimed, menu_pending, choice_recorded, executing, terminal, and blocked;
it makes no physical exactly-once claim.
PS-14: category 8 persists claim before method, menu_pending before menu or
unattended resolution, choice_recorded plus executing before side effects, and
terminal/blocked after reconciliation; Option 1 checks actual clean base and all
options keep durable receipts in their required locations.
```

#### WORKER-PACKET — REQ-001/SCN-001

```text
WORKER-PACKET: Dispatch isolated worker W-4 for this exact frozen plan task.
Task ID: W-4. Applicable authority: REQ-001 and SCN-001.
Owned paths: src/tenant/normalize.ts and tests/tenant/normalize.test.ts only.
Consumed verified input from completed W-2 commit c222: `export type CanonicalTenant
= { id: string; displayName: string }` from src/tenant/types.ts; W-2 verification
`npm test -- tenant.types` passed and its evidence is tests/tenant/types.test.ts.
W-4 must produce `export function normalizeTenantName(tenant: CanonicalTenant): string`.
Invariant: output is `tenant.displayName.trim()` with internal whitespace collapsed to
one ASCII space; `tenant.id` is never changed or written. W-4 depends only on W-2.
Verification command: `npm test -- tenant.normalize`. W-4 may not edit the frozen
specification or plan, change W-2's signature, add paths, or invent cross-task authority.
Write the complete Feature Forge worker dispatch packet and nothing else.
```

```text
WP-1: packet names W-4, REQ-001, SCN-001, exactly both owned paths, and frozen-task limits.
WP-2: packet repeats exact CanonicalTenant and normalizeTenantName signatures, W-2/c222,
and the verified producer input.
WP-3: packet states the whitespace/id invariant and exact `npm test -- tenant.normalize` command.
WP-4: packet prohibits frozen-authority edits, signature changes, added paths, and invented authority.
```

#### STAGE-GATE — REQ-002/SCN-002

```text
STAGE-GATE: The run is in Stage 8 Plan review. The exact sealed plan candidate has
review state changes_required because the reviewer found a material missing task and
verification for REQ-007. No fix has been made. The frozen specification is valid;
Implement and all later stages are pending. State authoritative stage/status, sole
next permitted action, and every stage that may not advance.
```

```text
SG-1: retains active Plan review or explicit plan change control; it does not mark review/plan complete.
SG-2: sole action is correct missing REQ-007 task/verification, then re-seal/re-review.
SG-3: forbids Implement, Implementation review, Final verification, Acceptance, Report, and Finish.
```

#### CANDIDATE-SEALS — REQ-002, REQ-007, REQ-010

```text
CANDIDATE-SEALS: Category 1 already committed the initial specification draft at d111.
After Harden, specification candidate docs/superpowers/specs/2026-08-17-export-design.md
has exact review-loop content seal spec-seal-a and an uncommitted editorial correction.
Its review finds another editorial ambiguity. Controller corrects only that candidate file,
gets spec-seal-b, and review passes. Category 3 then commits initial plan draft p333.
Plan candidate docs/superpowers/plans/2026-08-17-export.md is subsequently uncommitted at
plan-seal-a; review finds cross-task dependency defect, it is corrected uncommitted to
plan-seal-b, and then passes. State exact draft/freeze commit points, identity records,
allowed intermediate states, and what may never receive frozen blob identity.
```

```text
CS-1: preserves category-1 draft d111 and category-3 draft p333 while treating all four seals as candidate content seals, not frozen identities/intermediate commits.
CS-2: freezes/commits specification only after spec-seal-b pass and plan only after plan-seal-b pass, recording each resulting path@blob.
CS-3: permits stated between-round candidate edits only while no review is active; ledger/report receive no frozen blob.
CS-4: does not start Plan before specification freeze or Implement before plan freeze.
```

#### PLAN-DRIFT — REQ-007/SCN-007

```text
PLAN-DRIFT: A resumed run records frozen plan docs/superpowers/plans/2026-08-17-org-
sso.md@p111 and implementation task 2 active. Read-only recomputation of that exact
plan path returns blob p222 after an unreviewed plan-file edit. Specification identity
still matches, task 1 has a verified commit, and native tasks incorrectly say all work
is complete. State authoritative status, sole next action, classification/invalidation
path, and prerequisites before implementation may continue.
```

```text
PD-1: Git plan identity overrides native tasks and prevents implementation under p111 evidence.
PD-2: begins read-only drift reconciliation and classifies edit before any commit, advance, or dispatch.
PD-3: routes non-editorial plan defect through affected-task invalidation, plan review, new freeze blob,
and revalidated downstream evidence.
PD-4: preserves task-1 evidence only if inputs/contracts are provably unchanged; does not claim all work done.
```

#### UAT-TRUTH — REQ-008/SCN-008

```text
UAT-TRUTH: REQ-041 is UAT-classified. Human participant Sam, support lead, must run
`acme import --file fixtures/malformed-row-7.csv` in the public CLI and observe stderr
exactly contains `row 7 rejected`. The evidence criterion is a captured command transcript
showing exit status 2 and that exact stderr text. The unattended automated substitute is
`npm test -- import-cli-malformed-row-7`, which runs the same fixture and must assert exit
status 2 and the same stderr text. In supervised mode, Sam's transcript records exit 2 and
that stderr text, and Sam approves. In unattended mode, the named npm test passes with
the same asserted exit/text criterion. The invocation grants user-authorized full automation,
recorded as standing authority `agent:unattended`; it is the only authority for unattended
UAT waiver. State the complete supervised human-UAT record and complete unattended automated-
acceptance record.
```

```text
UT-1: supervised record names Sam, exact CLI exercise, supplied approval, authority, transcript, and criterion.
UT-2: unattended record names exact npm substitute and evaluates same exit-status/stderr criterion.
UT-3: unattended records `agent:unattended` standing authority as the waiver authority, uses truthful waived-human statement, and never claims Sam/human approval.
UT-4: supervised branch records Sam's supplied approval and unattended branch records supplied automated pass; neither branch is unconditionally asserted for the other mode.
```

#### CANONICAL-ARTIFACTS — REQ-009/SCN-009

```text
CANONICAL-ARTIFACTS: For org-sso the controller has exactly these paths:
docs/superpowers/specs/2026-08-17-org-sso-design.md,
docs/superpowers/plans/2026-08-17-org-sso.md,
docs/feature-forge/runs/2026-08-17-org-sso/ledger.md, and
docs/feature-forge/runs/2026-08-17-org-sso/final-report.md. A worker proposes
docs/feature-forge/org-sso-charter.md, decisions.md, state.json, and uat-signoff.md.
State where needed information belongs and which files may be created as outer-workflow authority.
```

```text
CA-1: names exactly the four supplied canonical authority paths.
CA-2: rejects all four proposed files and assigns decisions/state/acceptance to owning spec, ledger, or report.
CA-3: does not replace a canonical artifact or invent a fifth authority source.
```

#### ACTIVE-REVIEW — REQ-010/SCN-010

```text
ACTIVE-REVIEW: Ledger records Plan review state review_active for exact plan seal
plan-seal-9, dispatched to review-loop report reviews/plan-9.md. Plan candidate,
ledger, and every downstream stage are otherwise unchanged. A fresh controller resumes
while the reviewer may still run. State sole next permitted action and every mutation or
dispatch forbidden until return.
```

```text
AR-1: sole next action is await/recover named Plan review; it does not start another review.
AR-2: forbids plan-candidate, ledger, and downstream-stage mutation while active review has no return.
AR-3: records native verdict/report reference/content seal only after return, then applies fixed mapping.
```

#### DIRTY-PRIMARY — REQ-011/SCN-011

```text
DIRTY-PRIMARY: `/repo` is primary checkout on main with unrelated modified file
docs/customer-notes.md owned by another user. No Feature Forge artifact exists. The
requested work unit is org-sso. State exact preflight handling, branch/worktree for
tracked artifacts, permitted staging scope, and treatment of the unrelated primary file.
```

```text
DP-1: inventories/attributes docs/customer-notes.md without staging, stashing, resetting, cleaning, discarding, or modifying it.
DP-2: creates or verifies isolated feature/org-sso work in non-primary worktree before first tracked Feature Forge write.
DP-3: stages only explicit in-scope paths there and never starts implementation on dirty primary main.
```

#### HANDOFF-RETURN — REQ-012/SCN-012

```text
HANDOFF-RETURN: Feature Forge is supervised. Brainstorming has written and self-reviewed
the specification; Harden, candidate/spec review/freeze, Plan, plan review/freeze,
Implement, implementation review, verification, acceptance, Report, and Finish remain.
Later selected `superpowers:executing-plans` reaches its normal branch-finishing handoff
after local checks. State every adapter return boundary and exact remaining outer order.
```

```text
HR-1: brainstorm-return returns after written specification/self-review and before Harden; plan-return returns after plan/self-review and before execution.
HR-2: execute-return returns after local verification and intercepts normal branch-finish handoff without invoking it.
HR-3: orders remaining gates through Stage 13 Report/ready before single Stage 14 finish-authority operation.
```

#### FINISH-CAPABILITY — REQ-006/SCN-006, REQ-012/SCN-012

```text
FINISH-CAPABILITY: Stage 13 is complete: run is active, final report has pending Finish
outcome, finish_id F-18 has phase ready, and sole next action is claim F-18. Before Stage
14 begins, harness reports it cannot durably commit a journal record before menu delivery
and cannot reconcile a Push-and-PR forge result after process loss. State exact phase/status
transition, checkpoint category, next action, and whether claim or finishing-a-development-
branch may be invoked.
```

```text
FC-1: blocks before claimed commit and before logical Finish invocation; F-18 remains only operation.
FC-2: records ready -> blocked under category 8, prior phase ready, capability evidence, and resolution-only next action.
FC-3: forbids claim, menu presentation, unattended resolution, and every external finishing invocation until capability exists.
```

#### FINISH-CRASH — REQ-006/SCN-006/SCN-013

```text
FINISH-CRASH: Stage 14 has finish_id F-17. Category-8 receipts record claimed,
menu_pending with presentation ID menu-17, selected Push-and-PR choice under
user:release-42, then choice_recorded and executing with feature tip f333, base
main@b222, worktree /repo/.worktrees/org-sso, and exact next side effect `git push
origin feature/org-sso`. Process dies after push may have succeeded and before terminal
receipt. On resume, state allowed/forbidden actions, Git/forge evidence to reconcile,
and terminal-or-blocked record.
```

```text
FCr-1: reads F-17 journal first and creates no new claim, logical Finish, or menu presentation.
FCr-2: reconciles feature/base Git refs and Push-and-PR forge state read-only; repeats effect only when non-occurrence proven.
FCr-3: ambiguous push/PR atomically records category-8 blocked with prior executing, evidence, and no executable side effect.
FCr-4: conclusive result writes option-2 terminal receipt, terminal/complete/no-next in one category-8 ledger/report transaction on preserved feature branch/worktree.
```

#### OPTION1-DIRTY-BASE — REQ-006, REQ-011

```text
OPTION1-DIRTY-BASE: finish_id F-19 is choice_recorded for installed Option 1: local
merge into confirmed base main. Feature worktree /repo/.worktrees/org-sso is clean at
feature tip f444. Actual base checkout /repo is main@b333 but has unrelated modified
docs/customer-notes.md and no conflict markers. State required read-only inspection,
Finish phase/status and category-8 record, allowed Git actions, whether merge may begin,
and receipt location if later safe.
```

```text
OB-1: inspects actual base checkout/ref and dirty path read-only; clean feature worktree is insufficient.
OB-2: records category-8 blocked with prior phase choice_recorded, evidence, and resolution-only next action; merge does not start.
OB-3: forbids stash, reset, clean, discard, merge, or any base-checkout modification; feature branch/worktree remains intact.
OB-4: names base checkout terminal-receipt location only after safe Option 1 merge/cleanup conclusively completes.
```

- [ ] **Step 2: Freeze the new fixture revision under change control**

Inspect only the fixture path and create its new identity before any current-package pressure dispatch:

```bash
git add -- docs/feature-forge/skill-tdd/fixtures.md
git diff --cached --check
git diff --cached -- docs/feature-forge/skill-tdd/fixtures.md
git commit -m "test: amend feature-forge pressure fixtures"
git rev-parse HEAD:docs/feature-forge/skill-tdd/fixtures.md
git show cf38cfd:docs/feature-forge/skill-tdd/fixtures.md | git hash-object --stdin
```

Expected: the new fixture blob differs from the historical fixture blob; the historical command returns exactly `968ecd43bf966d803b64d8927b89819c3fba1134`. Record both commit/blob identities in the forthcoming RED result.

- [ ] **Step 3: Capture exact clean campaign inputs, then run the frozen amended fixtures**

Before any dispatch, require a completely clean worktree, including tracked and untracked paths. Capture the current package commit/tree and fixture blob; do not create the RED results file yet:

```bash
test -z "$(git status --porcelain)"
ffq_package_commit=$(git rev-parse HEAD)
ffq_repository_tree=$(git rev-parse HEAD^{tree})
ffq_package_tree=$(git rev-parse HEAD:feature-forge)
ffq_fixture_blob=$(git rev-parse HEAD:docs/feature-forge/skill-tdd/fixtures.md)
printf '%s\n' "$ffq_package_commit $ffq_repository_tree $ffq_package_tree $ffq_fixture_blob"
```

Run this capture, all read-only dispatches, and the post-campaign assertions in one persistent shell session. If the harness cannot preserve that shell, copy the four emitted literals into an external campaign worksheet and use those literal values in the post-campaign `test` operands; do not create a repository result file before the post gate.

For each behavior-shaping control (`LEDGER-ACTIVE`, `PIPELINE-SSO`, the retained seven, and all twelve direct controls above), run five fresh agents with `fork_turns:none`. Each agent reads the entire committed `feature-forge/` package, receives only the runner instruction plus one model-facing prompt, makes no edits, and has no prior response. Manually score every response using the fixed evaluator-only predicates; a keyword count never overrides a manual failure.

Run deterministic structural checks once:

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
git diff --check
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
rg -n 'Finish.*Report|Report.*Finish|seven[[:space:]]checkpoint|eight[[:space:]]checkpoint|finish_id|menu_pending' feature-forge
```

Expected: the amended prompt campaign exposes the known current defects, including reversed controller terminal order, absent durable Finish recovery, incorrect clean-commit rule for candidates, incomplete worker packets/UAT truth, weak adapter naming, and impossible self-identity in the ledger template. If a named predicate unexpectedly passes, record the complete response and explain why its full predicate still fails or why the defect is absent; do not weaken a fixture.

After every response is scored and before creating any result file, assert that the exact campaign input remains unchanged and the worktree is still clean:

```bash
test -z "$(git status --porcelain)"
test "$(git rev-parse HEAD)" = "$ffq_package_commit"
test "$(git rev-parse HEAD^{tree})" = "$ffq_repository_tree"
test "$(git rev-parse HEAD:feature-forge)" = "$ffq_package_tree"
test "$(git rev-parse HEAD:docs/feature-forge/skill-tdd/fixtures.md)" = "$ffq_fixture_blob"
```

Any failure means no valid RED campaign exists: preserve response references outside the repository if available, diagnose the mutation, and restart from a clean frozen-fixture state. Create the RED result only after this gate passes.

- [ ] **Step 4: Write and commit exact RED evidence without touching the package**

Create `2026-08-17-amended-red-results.md` with the fixture commit/blob, historical fixture lineage, current package commit/tree, every model/runner identifier available, every response verdict, decisive excerpts, direct REQ/SCN coverage map, deterministic output, and failed predicate-to-owning-task routing. State plainly that historical `2026-08-17-green-results.md` remains historical and does not qualify the amended spec.

```bash
git add -- docs/feature-forge/skill-tdd/2026-08-17-amended-red-results.md
git diff --cached --check
git commit -m "test: capture amended feature-forge RED results"
```

Expected: RED evidence is committed before any Task 1–5 package modification. Do not edit the fixture after this point; a defect in it requires a new revision and a complete campaign restart.

### Task 1: Controller and discovery metadata remediation

**Requirements/scenarios:** REQ-001/SCN-001, REQ-002/SCN-002, REQ-005/SCN-005, REQ-006/SCN-006, REQ-009/SCN-009, REQ-012/SCN-012.

**Execution prerequisite:** the committed outputs of Tasks 2, 3, 4, and 5; execute this numerically named owner task last, as shown in the dependency graph.

**Files:**

- Modify: `feature-forge/SKILL.md`
- Inspect: `feature-forge/agents/openai.yaml`

**Interfaces:**

- Consumes: paths/stages/Finish lifecycle from Task 2; authority and UAT terms from Task 3; adapter boundaries from Task 4; asset paths from Task 5
- Produces: a sub-500-word discoverable controller that refers to owner contracts instead of redefining them

- [ ] **Step 1: Confirm RED ownership and retain only controller content**

Read Task R0's failed predicates routed to Task 1. Keep the frontmatter trigger-only and retain existing UI metadata unless it conflicts with the required skill identity. Do not alter a workflow, authority, adapter, state, or template contract in this task.

- [ ] **Step 2: Correct the controller's ordered terminal recipe**

Make the controller direct the following order, verbatim in meaning:

```text
Implementation returns -> implementation review passes -> fresh verification ->
acceptance evidence -> Stage 13 report/active run/Finish ready -> Stage 14 Finish.
```

It must state that Report completes and persists `finish_id`/`ready` before Finish, then that Finish is the one durable logical Finish operation and sole final external-skill invocation. Remove every formulation that has Finish before reporting or that tells the controller to treat Finish as physical exactly-once. Keep start/resume instructions: verify Git/isolation, identify or recover the canonical run, obey the ledger's sole next action, load all owner references, and use native tasks only as display.

- [ ] **Step 3: Verify controller size and delegated ownership**

```bash
rg -n '^description: Use when' feature-forge/SKILL.md
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
rg -n 'workflow.md|authority.md|adapters-and-reviews.md|ledger-template.md|final-report-template.md' feature-forge/SKILL.md
rg -n 'Report.*Finish|finish_id|sole next' feature-forge/SKILL.md
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
```

Expected: validation succeeds. During the task review, read the complete terminal recipe in order and confirm it contains no terminal path other than Implementation return -> implementation review -> fresh verification -> acceptance -> Stage 13 report/active/ready -> Stage 14 Finish. Confirm the controller delegates state-machine detail to `workflow.md`; do not use a negative regex that would reject the correct phrase “Finish after Report.”

- [ ] **Step 4: Commit only the owned path**

```bash
git add -- feature-forge/SKILL.md
git diff --cached --check
git diff --cached -- feature-forge/SKILL.md
git commit -m "fix: correct feature-forge terminal order"
```

### Task 2: Workflow and durable Finish-journal remediation

**Requirements/scenarios:** REQ-001/SCN-001, REQ-002/SCN-002, REQ-005/SCN-005, REQ-006/SCN-006/SCN-013, REQ-007/SCN-007, REQ-009/SCN-009, REQ-010/SCN-010, REQ-011/SCN-011, REQ-012/SCN-012.

**Files:**

- Modify: `feature-forge/references/workflow.md`

**Interfaces:**

- Consumes: frozen amended specification and Task R0 RED routing
- Produces: the single authoritative vocabulary for paths, stage/state transitions, identity, checkpoint categories, Finish lifecycle, crash recovery, and resume
- Does not own: materiality/UAT fields (Task 3), adapter prompts/worker packet fields (Task 4), or template field ordering (Task 5)

- [ ] **Step 1: Establish canonical artifacts, identities, candidate seals, and cleanliness scope**

Declare exactly these artifacts:

```text
docs/superpowers/specs/YYYY-MM-DD-<work-unit>-design.md
docs/superpowers/plans/YYYY-MM-DD-<work-unit>.md
docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/ledger.md
docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md
```

Define frozen identity only as `<path>@<git-blob-id>` for the independently reviewed specification and plan. Define a candidate seal as the exact candidate-file content supplied to `review-loop`; it is not a frozen blob and may change uncommitted between rounds. State explicitly that the implementation subject, not every review subject, begins implementation review and final verification clean and committed. Ledger/report records are mutable and receive no frozen blob identity.

- [ ] **Step 2: Correct stages, review transitions, invalidation, and all eight checkpoint categories**

Keep exactly the fourteen stages:

```text
Preflight -> Brainstorm -> Harden -> Candidate gate -> Specification review ->
Specification freeze -> Plan -> Plan review -> Implement -> Implementation review ->
Final verification -> Acceptance -> Report -> Finish
```

Give every stage an entry predicate, owned action/artifact, exit evidence, blocked/change-control route, and exactly one ledger next action. During `review_active`, only await/recover the named review; no target, ledger, or downstream mutation occurs during the round. Candidate fixes occur between rounds and only a passing candidate gets its freeze checkpoint. Apply the fixed invalidation graph from the spec.

Define all eight conditional categories exactly, including category 8:

```text
1 draft specification; 2 freeze reviewed specification; 3 draft implementation plan;
4 freeze reviewed implementation plan; 5 owned implementation; 6 final-review fixes;
7 Stage 13 acceptance/report/ledger with active run and Finish ready;
8 Stage 14 Finish write-ahead, choice, terminal, or blocked lifecycle records.
```

Category 8 may produce more than one explicit-path commit only when state differs. No category 8 record commit permits another external-skill invocation.

- [ ] **Step 3: Specify Stage 13 and Stage 14 as a recoverable logical operation**

Stage 13 must allocate one stable `finish_id`, write `ready`, report outcome `pending`, leave the run `active`, create checkpoint category 7, restore a clean feature worktree, and set the sole next action to `claim <finish_id>`.

Stage 14 owns this exact phase vocabulary and transition protocol:

```text
ready -> claimed -> menu_pending -> choice_recorded -> executing -> terminal
```

`blocked` is a resumable safe overlay reachable from every nonterminal phase and records the prior phase plus a resolution-only next action. The reference must say that one `finish_id` represents one durable logical operation, while a process crash cannot provide physically atomic exactly-once external effects.

At `ready`, before the Stage 14 `claimed` category-8 commit and before any logical Finish invocation, the workflow performs a mandatory harness-capability check for durable journal interleaving and read-only Git/forge reconciliation. If either capability is unavailable, workflow—not an adapter—records `ready -> blocked` under category 8 with prior phase `ready`, evidence of the missing capability, and a resolution-only next action. It performs no claim, menu presentation, unattended resolution, or external branch-finishing invocation. Only after that workflow check passes may it commit `claimed` in category 8. Under the same `finish_id`, perform the installed skill's test/environment/base determination steps. Commit `menu_pending` in category 8 before the interactive/supervised menu presentation; record the exact three installed choices and a stable presentation ID. In unattended mode, record the named pre-authorization, or `agent:unattended default-keep`, before resolution. The choices are exactly local merge to confirmed base, Push-and-PR, and Keep branch/worktree.

Before any side effect, commit a single complete category-8 update that records `choice_recorded` then current `executing`, selected choice, authority, confirmed base, base/feature tips, worktree, environment evidence, and exact next side effect. The commit must succeed and the feature worktree be clean before a non-read-only operation.

- [ ] **Step 4: Specify Option 1 safety, receipts, and recovery without inventing a runtime**

Before Option 1 local merge, inspect the actual base checkout that will receive the merge. If it is dirty, conflicted, unrelated, or cannot be reconciled read-only to confirmed base, atomically record `blocked` under category 8; do not stash, reset, clean, merge into, or otherwise change it. For local merge, write the terminal ledger/report receipt in the base checkout so it survives feature-worktree cleanup and branch deletion. For Push-and-PR and Keep, preserve feature branch/worktree and write the terminal receipt there.

On recovery, first read the phase and receipts, then reconcile Git and—only for Push-and-PR—forge state read-only. `ready` without a claim permits one claim. `claimed` resumes test/environment/base work under the same ID. Interactive/supervised `menu_pending` with no durable choice must not re-present the menu or invent a choice; it blocks awaiting explicit choice against the existing menu record. Unattended recovery consumes only the committed authority/choice. From `choice_recorded`/`executing`, take only a recorded next side effect whose non-occurrence is provable. Never repeat merge, pull, push, PR creation, cleanup, branch deletion, claim, or menu presentation. Ambiguity atomically records `blocked` with evidence and no executable side effect.

Terminal and blocked category-8 commits must update ledger and report together: terminal records durable outcome, `terminal`, overall `complete`, and no next action; blocked records evidence, prior phase, blocked run state, and no executable next side effect. Stage 14 bookkeeping after the installed skill returns is permitted and is not a second external invocation.

- [ ] **Step 5: Verify the workflow contract before committing**

```bash
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
rg -n 'candidate.*seal|clean.*committed.*implementation|frozen.*specification.*plan' feature-forge/references/workflow.md
rg -n 'eight checkpoint|category 8|record .* finish' feature-forge/references/workflow.md
rg -n 'finish_id|ready.*claimed.*menu_pending.*choice_recorded.*executing.*terminal' feature-forge/references/workflow.md
rg -n 'capability.*claimed|ready.*blocked|base checkout|read-only|never repeat|forge state|presentation' feature-forge/references/workflow.md
rg -n 'Stage 13|active|pending|claim' feature-forge/references/workflow.md
! rg -n 'seven[[:space:]]checkpoint|ledger[[:space:]]*blob[[:space:]]*identity|final[[:space:]]report[[:space:]]*blob[[:space:]]*identity' feature-forge/references/workflow.md
```

Expected: 14 stages; all eight checkpoint categories; candidate and implementation cleanliness rules are distinguishable; Finish recovery neither claims nor presents a menu twice.

- [ ] **Step 6: Commit only the workflow reference**

```bash
git add -- feature-forge/references/workflow.md
git diff --cached --check
git diff --cached -- feature-forge/references/workflow.md
git commit -m "fix: make feature-forge Finish recoverable"
```

### Task 3: Authority, acceptance, and UAT-truth remediation

**Requirements/scenarios:** REQ-003/SCN-003, REQ-004/SCN-004, REQ-008/SCN-008, and the acceptance portions of REQ-002/REQ-006.

**Files:**

- Modify: `feature-forge/references/authority.md`

**Interfaces:**

- Consumes: workflow-owned paths/states/invalidations by reference
- Produces: the only definition of automation/materiality, hardening, candidate/freeze authority, and acceptance/UAT fields

- [ ] **Step 1: Retain authority and hardening rules while limiting change scope**

Keep the three-mode matrix, upward uncertainty classification, grilling-derived design-tree/frontier method, acceleration packet/approval rules, candidate scope constraints, and frozen change control. Point to workflow-owned invalidation and checkpoint rules rather than copying them. State that a new request remains deferred unless explicitly authorized and extra machinery is limited to a named requirement/invariant/project convention/deterministic gate.

- [ ] **Step 2: Define the complete UAT contract in this owner only**

For each UAT-classified requirement require all four specification fields:

```text
named participant; observable exercise; unattended automated substitute;
evidence criterion that the substitute must satisfy
```

The supervised/interactive record must name the participant, the observed exercise, approval/rejection, authority, and evidence against the criterion. Unattended must run the declared substitute and evaluate it against that same criterion. If no adequate substitute exists, unattended blocks rather than weakening acceptance. Only user authority waives otherwise applicable UAT; unattended records standing authority as a waiver, never human approval. Preserve states `pending | approved | rejected | infeasible | waived`; `rejected` returns to defect classification and `infeasible` blocks absent a user method/waiver decision.

Do not define stages, Finish transitions, report-template phrases, or worker packets here.

- [ ] **Step 3: Verify sole ownership and commit**

```bash
rg -n 'participant|observable exercise|automated substitute|evidence criterion' feature-forge/references/authority.md
rg -n 'pending.*approved.*rejected.*infeasible.*waived|never.*human' feature-forge/references/authority.md
rg -n 'interactive.*none|supervised.*default|unattended.*full' feature-forge/references/authority.md
! rg -n '^### Stage|finish_id|menu_pending|choice_recorded' feature-forge/references/authority.md
git add -- feature-forge/references/authority.md
git diff --cached --check
git commit -m "fix: define truthful feature-forge acceptance"
```

### Task 4: Adapter, worker-packet, and review-charter remediation

**Requirements/scenarios:** REQ-001/SCN-001, REQ-002/SCN-002, REQ-004/SCN-004, REQ-006/SCN-006/SCN-013, REQ-010/SCN-010, REQ-012/SCN-012.

**Files:**

- Modify: `feature-forge/references/adapters-and-reviews.md`

**Interfaces:**

- Consumes: workflow's stage/state/Finish-journal boundaries; authority's materiality/UAT vocabulary
- Produces: exact named adapter prompts, worker-packet completeness contract, execution selection, and three review charters

- [ ] **Step 1: Replace vague adapter prose with exactly four named contracts**

Define exactly these headings and no fifth outer adapter:

```text
brainstorm-return
plan-return
execute-return
finish-authority
```

`brainstorm-return` performs the installed brainstorming method and returns after the written specification/self-review, **before Harden**; in unattended mode it replaces only synchronous brainstorming approval gates with recorded standing authority and self-review. `plan-return` performs writing-plans' required header/self-review then returns before its execution offer or start. `execute-return` selects exactly `superpowers:subagent-driven-development` for independently ownable fixed-contract tasks, or the exact installed skill `superpowers:executing-plans` for tightly coupled/no-delegation work, then returns after local verification without branch finishing. Do not describe an unnamed inline substitute.

`finish-authority` consumes and enforces the workflow-owned journal boundaries; no runtime callback is claimed. It requires the workflow's already-passing pre-claim capability receipt before it can invoke branch finishing, then obeys the pre-menu, pre-side-effect, and terminal/block receipt conditions that `workflow.md` owns. It does not define or write the capability check, `ready -> blocked`, or `claimed` transition; a missing/pending workflow capability receipt means it may not claim, present a menu, resolve unattended choice, or invoke `finishing-a-development-branch`. In interactive/supervised it otherwise preserves the exact installed menu once; unattended otherwise uses named pre-authorization or default Keep, never inferred integration authority.

- [ ] **Step 2: Make every worker packet independently executable under frozen authority**

Define the required packet schema and dispatch rejection rule:

```text
task ID and exact frozen plan task; applicable REQ-NNN and SCN-NNN IDs;
owned paths; consumed/produced interfaces and signatures; invariants;
dependencies and already-verified inputs; exact verification command/evidence;
explicit prohibition on changing frozen spec/plan or inventing cross-task authority.
```

A packet missing any field is incomplete and must not dispatch. Worker tasks report their commit/evidence to the controller/ledger, which remains progress authority. This is a contract requirement, not an invitation to create a new packet document outside the canonical run artifacts.

- [ ] **Step 3: Preserve narrow review charters and exact native-result mapping**

Create only `### Specification review`, `### Plan review`, and `### Implementation review`. Specification review checks faithfulness, coherence, bounds, observability, testability, and completeness of an exact candidate seal. Plan review checks frozen-spec coverage, systemic design, task order, cross-task interfaces/invariants/dependencies, and verification; code blocks receive review only for contract/test-intent/architecture defects, not ordinary code perfection. Implementation review checks the clean committed implementation snapshot against frozen spec/plan, requirements/scenarios/invariants/regressions/security/performance/no extra scope.

Map native returns exactly:

```text
CONVERGED + merge-ready -> pass
actionable findings -> changes_required
INDETERMINATE / no viable fix / missing authority / unavailable capability -> blocked
CONVERGED + not merge-ready -> blocked with named blocker
```

Each dispatch persists `review_active` first, passes exact subject/ground truth/charter/completion criterion, preserves reports outside sealed tree, and records native verdicts/report reference/seal on return. Only fixes between rounds are allowed; re-seal and review them before pass.

- [ ] **Step 4: Verify adapter exactness and commit**

```bash
for name in brainstorm-return plan-return execute-return finish-authority; do rg -q "^### $name$" feature-forge/references/adapters-and-reviews.md; done
rg -n 'before Harden|writing-plans|superpowers:subagent-driven-development|superpowers:executing-plans' feature-forge/references/adapters-and-reviews.md
rg -n 'finish_id|pre-claim|pre-menu|pre-side-effect|default Keep|no runtime callback' feature-forge/references/adapters-and-reviews.md
rg -n 'REQ-NNN|SCN-NNN|interfaces|invariants|dependencies|verification|must not be dispatched' feature-forge/references/adapters-and-reviews.md
test "$(rg -c '^### .* review$' feature-forge/references/adapters-and-reviews.md)" -eq 3
git add -- feature-forge/references/adapters-and-reviews.md
git diff --cached --check
git commit -m "fix: complete feature-forge adapter contracts"
```

### Task 5: Ledger and final-report template remediation

**Requirements/scenarios:** REQ-001/SCN-001, REQ-002/SCN-002, REQ-005/SCN-005, REQ-006/SCN-006/SCN-013, REQ-008/SCN-008, REQ-009/SCN-009, REQ-010/SCN-010.

**Files:**

- Modify: `feature-forge/assets/ledger-template.md`
- Modify: `feature-forge/assets/final-report-template.md`

**Interfaces:**

- Consumes: exact vocabulary from Tasks 2–4
- Produces: copyable mutable evidence schemas that contain one next action or a terminal outcome, never their own frozen identity

- [ ] **Step 1: Repair the ledger template without self-referential identity**

Keep headings for run identity, canonical artifacts, stage register, current authority, implementation progress, reviews, verification/acceptance, blockers/change requests, transition log, and sole next action. Record frozen `<path>@<blob-id>` values only for canonical specification and plan. Remove every required ledger/final-report blob identity or mandatory `final report pending` placeholder.

Add a Finish journal section containing:

```text
finish_id; current phase; prior phase when blocked; exact menu/presentation ID;
selected choice; authority; confirmed base; base and feature tips; worktree;
environment/reconciliation evidence; exact next side effect; durable receipts.
```

The transition log includes event ID, UTC time, from/to state, next action, reason/authority, and evidence. Require one next action in every nonterminal state; terminal overall `complete` has the terminal outcome and no next action. `review_active` permits only await/recover. Copy-time checks must identify themselves as **ledger** checks and prohibit duplication of requirement/task/review prose.

- [ ] **Step 2: Make final-report acceptance and Stage 13/14 states truthful**

Keep outcome, frozen authorities/reviewed snapshot, requirement traceability, final verification, acceptance, open defects/exceptions, checkpoint, and branch-finishing readiness sections. The traceability row maps `requirement/scenario | plan task | test/evidence | outcome/date | UAT result`.

Provide mutually exclusive fillable acceptance branches:

```text
Human UAT: [participant] performed [observable exercise]; [approved/rejected];
evidence met [criterion].

Automated substitute: [substitute] evaluated [criterion]; [pass/fail].
Automated acceptance evidence completed; human UAT/sign-off was waived.
```

The report must never unconditionally assert either branch. It documents Stage 13 as active with Finish pending/`ready` and `claim <finish_id>` next; Stage 14 alone replaces it with a terminal durable receipt or blocked receipt. Use report text that supports the Option 1 base-checkout receipt and Option 2/3 preserved-feature receipt defined by workflow; it does not create a second state machine.

- [ ] **Step 3: Verify template satisfiability and commit**

```bash
rg -n 'specification.*blob|plan.*blob' feature-forge/assets/ledger-template.md
! rg -n 'ledger.*blob|final report.*blob|final report pending' feature-forge/assets/ledger-template.md
rg -n 'finish_id|prior phase|presentation|base.*tip|feature.*tip|exact next side effect|receipt' feature-forge/assets/ledger-template.md
rg -n 'exactly one next|terminal.*no next|review_active' feature-forge/assets/ledger-template.md
rg -n 'Human UAT|Automated substitute|human UAT/sign-off was waived|Stage 13|Stage 14|pending|terminal|blocked' feature-forge/assets/final-report-template.md
rg -n 'ledger.*copy-time|copy-time.*ledger' feature-forge/assets/ledger-template.md
git add -- feature-forge/assets/ledger-template.md feature-forge/assets/final-report-template.md
git diff --cached --check
git commit -m "fix: make feature-forge run evidence durable"
```

Expected: a new ledger can be completed without calculating its own blob and the report never claims waived human UAT unless that branch is selected.

### Task 6: Run amended immutable GREEN qualification and record direct evidence

**Requirements/scenarios:** direct recorded evidence for every REQ-001 through REQ-012 and SCN-001 through SCN-013.

**Files:**

- Create: `docs/feature-forge/skill-tdd/2026-08-17-amended-green-results.md`
- Read only: frozen amended `fixtures.md`, complete committed `feature-forge/`, historical and amended RED evidence

**Interfaces:**

- Consumes: Task R0's exact new fixture identity and the complete committed package from Tasks 1–5
- Produces: immutable, direct, reproducible qualification evidence; no package modifications

- [ ] **Step 1: Confirm package and fixture identities before dispatch**

```bash
test -z "$(git status --porcelain)"
ffq_green_package_commit=$(git rev-parse HEAD)
ffq_green_repository_tree=$(git rev-parse HEAD^{tree})
ffq_green_package_tree=$(git rev-parse HEAD:feature-forge)
ffq_green_fixture_blob=$(git rev-parse HEAD:docs/feature-forge/skill-tdd/fixtures.md)
printf '%s\n' "$ffq_green_package_commit $ffq_green_repository_tree $ffq_green_package_tree $ffq_green_fixture_blob"
git show cf38cfd:docs/feature-forge/skill-tdd/fixtures.md | git hash-object --stdin
```

Run this capture, all read-only dispatches, and the post-campaign assertions in one persistent shell session. If the harness cannot preserve that shell, copy the four emitted literals into an external campaign worksheet and use those literal values in the post-campaign `test` operands; do not create the GREEN result file before the post gate.

Expected: status is empty before dispatch; the captured commit/tree and fixture blob identify the only package/fixture input; the fixture identity matches Task R0; historical blob remains `968ecd43bf966d803b64d8927b89819c3fba1134`. The GREEN result file must not exist yet.

- [ ] **Step 2: Run deterministic package and ownership checks**

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
git diff --check
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
for category in 1 2 3 4 5 6 7 8; do rg -q "${category}\." feature-forge/references/workflow.md; done
for adapter in brainstorm-return plan-return execute-return finish-authority; do rg -q "^### ${adapter}$" feature-forge/references/adapters-and-reviews.md; done
rg -n 'participant|observable exercise|automated substitute|evidence criterion' feature-forge/references/authority.md
rg -n 'finish_id|menu_pending|choice_recorded|executing|terminal|blocked' feature-forge/references/workflow.md feature-forge/assets
```

Then manually audit sole ownership: workflow alone defines lifecycle/state/path/identity/checkpoints; authority alone defines UAT content; adapters alone defines four adapters/worker packets/review charters; templates copy terms/field order only. Record actual output rather than a blanket pass assertion.

- [ ] **Step 3: Dispatch the complete frozen behavior campaign and score it manually**

Run five fresh, read-only, context-isolated repetitions for every behavior-shaping fixture in the amended revision. This includes `LEDGER-ACTIVE`, `PIPELINE-SSO`, all seven historical regression controls, and every direct control added in Task R0. Preserve every response or a stable response reference, runner configuration, available model identity, predicate-by-predicate score, decisive excerpts, and convergence outcome.

Any missing predicate, invented extra authority artifact, stale fixture/package identity, or model rationalization fails the repetition. A control passes only at 5/5; otherwise stop, record all failures, route each to the sole owning Task 1–5 path, commit that remediation, and restart **all** Task 6 controls from the unchanged fixture revision. Do not edit `feature-forge/` in this task and do not amend the fixture to accommodate a response.

After scoring the entire campaign and before creating `2026-08-17-amended-green-results.md`, assert the same clean, frozen input:

```bash
test -z "$(git status --porcelain)"
test "$(git rev-parse HEAD)" = "$ffq_green_package_commit"
test "$(git rev-parse HEAD^{tree})" = "$ffq_green_repository_tree"
test "$(git rev-parse HEAD:feature-forge)" = "$ffq_green_package_tree"
test "$(git rev-parse HEAD:docs/feature-forge/skill-tdd/fixtures.md)" = "$ffq_green_fixture_blob"
```

If the identity or cleanliness gate fails, there is no valid GREEN result: preserve read-only response references if available, resolve the mutation through its owning task, and restart Task 6. Create the GREEN result only after this gate passes.

- [ ] **Step 4: Produce a direct—not inferred—coverage ledger in the GREEN result**

For every row `REQ-001`–`REQ-012` and `SCN-001`–`SCN-013`, list the named fixture/control, all five result references, the exact predicates, and outcome. Include an explicit SCN-013 row for the Finish-crash condition. Do not count nearby prose, structural scans, or an inferred implication as direct evidence. Keep the original seven regression controls visibly mapped as retained coverage, and state their original evidence remains historical rather than amended qualification.

- [ ] **Step 5: Commit evidence only**

```bash
git add -- docs/feature-forge/skill-tdd/2026-08-17-amended-green-results.md
git diff --cached --check
git diff --cached -- docs/feature-forge/skill-tdd/2026-08-17-amended-green-results.md
git commit -m "test: verify amended feature-forge workflow"
```

### Task 7: Restart qualification with cold reader, independent challenge, and fresh verification

**Requirements/scenarios:** audit all REQ-001/SCN-001 through REQ-012/SCN-012 and SCN-013, including the exact Finish protocol.

**Files:**

- Create: `docs/feature-forge/reviews/2026-08-17-amended-skill-review.md`
- Read only: committed package, frozen amended specification/plan, amended fixture identity, amended RED/GREEN evidence

**Interfaces:**

- Consumes: exact committed package/tree and Task 6 complete direct evidence
- Produces: final qualification evidence only; no package mutation

- [ ] **Step 1: Run a cold-reader exercise against the repaired package**

Give a fresh reader the complete package and the amended `PIPELINE-SSO`, `FINISH-CRASH`, and `OPTION1-DIRTY-BASE` prompts, but no prior results. Require it to identify first action, four canonical artifacts, 14-stage order, candidate/frozen distinction, review pauses, Stage 13/14 transition, all menu/recovery safety boundaries, and terminal action. Record omissions and divergent interpretations exactly.

Material misunderstanding returns to the controller. The controller maps it to the sole Task 1–5 owner, commits the focused remediation, reruns all Task 6 fixtures, and restarts this entire Task 7. Do not patch in Task 7.

- [ ] **Step 2: Obtain independent holistic and adversarial reviews**

Dispatch separate read-only reviewers against the exact package commit/tree, amended frozen specification/blob, this reviewed plan/blob, fixture revision/blob, amended RED evidence, and amended GREEN evidence. Their charter must explicitly test all 13 scenarios and all requirements, with special scrutiny for:

```text
one logical Finish rather than impossible physical exactly-once;
Stage 13 active/pending/ready and Stage 14 receipts;
no self-identity; candidate seals versus implementation cleanliness;
UAT branch truth; exact adapter names/returns; isolated worker packets;
dirty primary/base safety; crash recovery/reconciliation/no redispatch/menu replay.
```

Require zero unresolved material defects. Classify every finding and record the evidence. Material finding means qualification fails closed: remediate its owning path, restart Task 6, then rerun both independent reviews and the cold-reader exercise.

- [ ] **Step 3: Run final fresh checks over exact qualification inputs**

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
git diff --check
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
for adapter in brainstorm-return plan-return execute-return finish-authority; do rg -q "^### ${adapter}$" feature-forge/references/adapters-and-reviews.md; done
git status --short
```

Expected: all checks exit zero and status contains only the untracked new Task 7 report before its commit. Confirm that precise state:

```bash
test "$(git status --porcelain)" = "?? docs/feature-forge/reviews/2026-08-17-amended-skill-review.md"
```

- [ ] **Step 4: Record qualification and commit**

Record package commit/tree identity, frozen amended spec/plan identities, fixture lineage/identity, cold-reader inputs/results, both reviewer inputs/verdicts/finding disposition, final command output, direct 13-scenario coverage assertion tied to Task 6 evidence, and install/publish readiness.

```bash
git add -- docs/feature-forge/reviews/2026-08-17-amended-skill-review.md
git diff --cached --check
git diff --cached -- docs/feature-forge/reviews/2026-08-17-amended-skill-review.md
git commit -m "docs: record amended feature-forge qualification"
```

## Plan self-review

### Specification coverage

| Specification obligation | Plan coverage |
|---|---|
| No runtime; Git-only canonical authority and isolated worktree | Global Constraints; Tasks 1–2; Task R0 `DIRTY-PRIMARY`/`CANONICAL-ARTIFACTS` |
| Superpowers adapters return to outer controller | Task 4; Task 6 `HANDOFF-RETURN` |
| Candidate/frozen distinction, blob identities, review seals | Task 2 Steps 1–2; Task R0 `CANDIDATE-SEALS`, `PLAN-DRIFT` |
| Three review charters, active-review immutability | Task 4 Step 3; Task R0 `STAGE-GATE`/`ACTIVE-REVIEW` |
| Complete worker packet contract | Task 4 Step 2; Task R0 `WORKER-PACKET` |
| Full UAT contract and truthful waiver | Task 3 Step 2; Task 5 Step 2; Task R0 `UAT-TRUTH` |
| Stage 13/14 and eight categories | Task 2 Steps 2–4; Task 5; Task R0 `FINISH-CRASH` |
| Safe one-logical-operation Finish/recovery/options | Task 2 Steps 3–4; Task 4 Step 1; Task R0 `FINISH-CRASH`/`OPTION1-DIRTY-BASE` |
| Immutable fixture history; RED before remediation; direct full qualification | Task R0 and Task 6 |
| Cold-reader, independent review, fresh verification | Task 7 |

### Placeholder and consistency checks

Before requesting plan review, run:

```bash
sed -n '/^# Feature Forge Implementation Plan$/,/^## Plan self-review$/p' docs/superpowers/plans/2026-08-17-feature-forge.md | sed '$d' | rg -n -i 'tbd|todo|implement later|fill in details|add appropriate|write tests for the above|similar to task'
git diff --check -- docs/superpowers/plans/2026-08-17-feature-forge.md
```

Expected: the placeholder scan has no matches and the diff check exits zero. Manually confirm all owner/consumer terms match exactly: `finish_id`, eight categories, `ready`, `claimed`, `menu_pending`, `choice_recorded`, `executing`, `terminal`, `blocked`, `superpowers:executing-plans`, and `REQ-NNN`/`SCN-NNN`; confirm the controller/report ordering is Acceptance -> Stage 13 Report/ready -> Stage 14 Finish and that neither mutable run artifact receives a frozen blob identity.

## Required next gate

This amendment candidate returns to Feature Forge for the plan-review charter. It must be independently reviewed for faithful spec coverage, systemic design/dependency correctness, worker-contract completeness, and verification adequacy. Do not execute any task, offer an execution handoff, or modify package files until a passing review is committed as the new frozen-plan baseline.
