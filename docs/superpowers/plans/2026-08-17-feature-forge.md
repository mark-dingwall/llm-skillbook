# Feature Forge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the repository-local `feature-forge` skill that carries a bounded Git work unit from specification through reviewed acceptance without improvising its outer protocol.

**Architecture:** Keep `SKILL.md` as the short discoverable controller, move normative workflow, authority, adapter, and review contracts into three directly linked references, and provide two copyable Markdown assets for durable state and final evidence. There is no runtime program; deterministic checks validate document contracts while fresh-context pressure scenarios validate behavior.

**Tech Stack:** Agent Skills Markdown/YAML, Git, shell contract checks, `skill-creator`, Superpowers skills, `review-loop`, fresh-context subagents

**Status:** Frozen reviewed plan

## Global Constraints

- Git repositories only; isolate work before the first tracked artifact write.
- Use the four canonical artifact paths and no extra outer-authority documents.
- The frontier LLM is the controller; add no runtime, workflow DSL, or third-party dependency.
- Native tasks are a disposable display; the tracked run ledger is durable authority.
- Modes are `interactive` (`none`), `supervised` (`default`, default), and `unattended` (`full`).
- Freeze the spec before planning and the plan before implementation.
- Use three distinct review charters; call branch finishing exactly once and last.
- Keep the skill description trigger-only, beginning with `Use when`.
- Add no validator unless the same mechanical failure occurs in three independent pressure runs.

## File map

| File | Single responsibility |
|---|---|
| `feature-forge/SKILL.md` | Trigger, invariant, start/resume controller, direct resource links |
| `feature-forge/agents/openai.yaml` | Codex UI metadata |
| `feature-forge/references/workflow.md` | Artifacts, fourteen stages, state, identity, resume, commits |
| `feature-forge/references/authority.md` | Automation, hardening, materiality, freezes, acceptance |
| `feature-forge/references/adapters-and-reviews.md` | Four adapters, execution choice, review charters/results |
| `feature-forge/assets/ledger-template.md` | Copyable normalized run ledger |
| `feature-forge/assets/final-report-template.md` | Copyable evidence and acceptance report |
| `docs/feature-forge/skill-tdd/fixtures.md` | Immutable prompts and scoring predicates |
| `docs/feature-forge/skill-tdd/2026-08-17-green-results.md` | Forward-test evidence |
| `docs/feature-forge/reviews/2026-08-17-skill-review.md` | Cold-reader, independent review, and final verification evidence |

## Contract ownership and dependencies

| Contract | Sole owner | Consumers |
|---|---|---|
| paths, slug, stages, state names, identities, transition/invalidation graph, commits | `workflow.md` | controller, authority, adapters, templates |
| modes, materiality, hardening, spec shape, acceptance methods/states | `authority.md` | workflow, adapters, templates |
| adapter names/prompts, execution choice, review charters/result mapping | `adapters-and-reviews.md` | controller, workflow, templates |
| durable field order | ledger/final-report assets | controller only |

The dependency DAG is: Tasks 1 and 2 may run in parallel; Task 3 follows Task 2;
Task 4 follows Task 3; Task 5 follows Task 4; Task 6 joins and waits for both
Task 1 and Task 5; Task 7 follows Task 6. Task 1 must not redefine a contract
owned by a reference. Task 5 copies owned terms verbatim.

| Package path | Owning/remediation task |
|---|---|
| `feature-forge/SKILL.md` | Task 1 |
| `feature-forge/agents/openai.yaml` | Task 1 |
| `feature-forge/references/workflow.md` | Task 2 |
| `feature-forge/references/authority.md` | Task 3 |
| `feature-forge/references/adapters-and-reviews.md` | Task 4 |
| `feature-forge/assets/ledger-template.md` | Task 5 |
| `feature-forge/assets/final-report-template.md` | Task 5 |
| `docs/feature-forge/skill-tdd/fixtures.md` and GREEN results | Task 6 |
| `docs/feature-forge/reviews/2026-08-17-skill-review.md` | Task 7 |

---

### Task 1: Controller and discovery metadata

**Requirements/scenarios:** REQ-001/SCN-001, REQ-002/SCN-002, REQ-005/SCN-005, REQ-009/SCN-009, REQ-012/SCN-012

**Files:**
- Modify: `feature-forge/SKILL.md`
- Modify: `feature-forge/agents/openai.yaml`

**Interfaces:**
- Consumes: reference and asset filenames from the file map
- Produces: trigger-only frontmatter and the mandatory start/resume controller

- [ ] **Step 1: Run the generated scaffold validation to verify RED**

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
```

Expected: FAIL because the generated description contains placeholder/TODO syntax.

- [ ] **Step 2: Replace the scaffold**

Use this frontmatter exactly:

```yaml
---
name: feature-forge
description: Use when implementing a bounded Git-repository feature or comparable work unit whose size, risk, ambiguity, or cross-component coordination warrants explicit specification, planning, independent review, and acceptance
---
```

Keep the body below 500 words with these headings:

```markdown
# Feature Forge
## Core invariant
## Start or resume
## Outer control
## Load the contracts
## Quick checks
## Red flags
```

The positive startup recipe is: verify Git/isolation; select or recover the
canonical run; copy the ledger asset for a new run or read ledger plus exact
artifacts on resume; obey its sole next action; load all three references before
dispatch; project native tasks only as display; intercept named adapters; finish
exactly once.

- [ ] **Step 3: Verify size, links, and metadata**

```bash
rg -n '^description: Use when' feature-forge/SKILL.md
rg -n 'workflow.md|authority.md|adapters-and-reviews.md|ledger-template.md|final-report-template.md' feature-forge/SKILL.md
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
sed -n '1,80p' feature-forge/agents/openai.yaml
```

Expected metadata:

```yaml
interface:
  display_name: "Feature Forge"
  short_description: "Deliver reviewed features from spec to acceptance"
  default_prompt: "Use $feature-forge to implement this feature from specification through reviewed acceptance."
```

- [ ] **Step 4: Commit**

```bash
git add -- feature-forge/SKILL.md feature-forge/agents/openai.yaml
git diff --cached --check
git commit -m "feat: add feature-forge controller"
```

### Task 2: Workflow and durable-state contract

**Requirements/scenarios:** REQ-001/SCN-001, REQ-002/SCN-002, REQ-005/SCN-005, REQ-006/SCN-006, REQ-007/SCN-007, REQ-009/SCN-009, REQ-011/SCN-011, REQ-012/SCN-012

**Files:**
- Create: `feature-forge/references/workflow.md`

**Interfaces:**
- Consumes: the frozen specification and the vocabulary fixed in this plan
- Produces: canonical stage, artifact, state, identity, resume, and Git contracts

- [ ] **Step 1: Verify the reference is absent**

```bash
test -s feature-forge/references/workflow.md
```

Expected: non-zero.

- [ ] **Step 2: Write canonical artifacts and states**

Use these exact paths:

```text
docs/superpowers/specs/YYYY-MM-DD-<work-unit>-design.md
docs/superpowers/plans/YYYY-MM-DD-<work-unit>.md
docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/ledger.md
docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md
```

Stage states are `pending | active | blocked | complete | invalidated`.
Review states are `not_started | review_active | pass | changes_required | blocked`.
`review_active` permits only await/recover review.

- [ ] **Step 3: Write the fourteen stages**

```text
Preflight -> Brainstorm -> Harden -> Candidate gate -> Specification review
-> Specification freeze -> Plan -> Plan review -> Implement
-> Implementation review -> Final verification -> Acceptance -> Report -> Finish
```

Create headings `### Stage 1:` through `### Stage 14:`. Each states entry,
owned action/artifact, exit evidence, and next action. Do not add component gates.

Stage 1 must enumerate: Git confirmation; strict lowercase-alphanumeric-hyphen
slug/ref rejection; same-date run and all-date same-slug branch/worktree
collision checks; intent/base/identity matching; explicit resume/new/suffix/block
outcomes; review-loop-compatible user-authorized runner validation; dirty-path
attribution; and creation or verified reuse of an isolated non-primary worktree
before the first tracked write.

- [ ] **Step 4: Write identity, resumption, and commits**

Define `<path>@<git-blob-id>` for frozen artifacts, the `review-loop` content
seal, the implementation table (`plan task | status | commit | evidence`),
read-only drift reconciliation, the fixed invalidation graph, exact-path staging,
seven checkpoint categories, the permitted post-review ledger delta, and a clean
tree before Finish.

End the reference with a per-stage acceptance table confirming all fourteen
stages have an entry predicate, owned artifact/action, evidence gate, failure or
blocked return, and sole next action. This is the semantic check behind the
heading-count command.

- [ ] **Step 5: Verify and commit**

```bash
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
rg -n 'review_active.*await.*recover|await.*recover.*review_active' feature-forge/references/workflow.md
rg -n 'git blob|content seal|explicit path|exactly once' feature-forge/references/workflow.md
git add -- feature-forge/references/workflow.md
git diff --cached --check
git commit -m "feat: define feature-forge workflow"
```

### Task 3: Authority and scope-control contract

**Requirements/scenarios:** REQ-003/SCN-003, REQ-004/SCN-004, REQ-007/SCN-007, REQ-008/SCN-008

**Files:**
- Create: `feature-forge/references/authority.md`

**Interfaces:**
- Consumes: canonical paths, states, and invalidation graph from `workflow.md`
- Produces: mode authority, hardening, materiality, change classification, and acceptance vocabulary

- [ ] **Step 1: Verify the reference is absent**

```bash
test -s feature-forge/references/authority.md
```

Expected: non-zero.

- [ ] **Step 2: Write the authority matrix**

| Mode | Alias | Without pause | Pause/block |
|---|---|---|---|
| interactive | none | editorial corrections | every nontrivial assumption/material decision and UAT |
| supervised | default | minor local reversible decisions; execution mode | goals/non-goals, observable behavior, acceptance, compatibility, scope, public/cross-task contracts, security/data posture, major architecture |
| unattended | full | recorded in-scope decisions and minimum coherence repairs | missing authority, unsafe/irreversible action, unavailable dependency, fundamental intent change, irresolvable contradiction |

Define `material`, `minor`, and `in scope`; uncertainty classifies upward.

- [ ] **Step 3: Write the hardening recipe**

```text
model design tree -> resolve discoverable facts -> compute prerequisite-ready
frontier -> ask whole numbered frontier with recommendations -> integrate into
the one spec -> recompute until frontier and Open questions are empty
```

Acceleration consolidates remaining decisions: interactive/supervised needs one
approval; unattended records standing authority and continues.

- [ ] **Step 4: Write the work-unit specification contract**

Require one canonical specification with these sections:

```text
Intent and authority; Goals and non-goals; Observable requirements and scenarios;
Architecture/components/data flow; Interfaces/contracts/invariants; Domain language;
Decisions and rationale; Assumptions and delegated decisions; Error handling;
Test strategy; Open questions
```

Every normative feature requirement has stable `REQ-NNN`, one observable
`SHALL` or `MUST`, and important success/edge/error scenarios with stable
`SCN-NNN` and GIVEN/WHEN/THEN. Record material authority as `user` or
`agent:<mode>`, require the durable intent brief, acceptance classification and
fallback, and require an empty `Open questions` section at the candidate gate.

- [ ] **Step 5: Write freezes and acceptance**

Include candidate/frozen rules and link to/apply the workflow-owned invalidation
graph without restating it. Define editorial delta re-review, methods
`automated | UAT | not_applicable`, and states
`pending | approved | rejected | infeasible | waived`. Every UAT declares an
unattended automated fallback/evidence criterion or unattended blocks.

End with an acceptance checklist covering all three modes, materiality,
hardening termination, all eleven spec sections, REQ/SCN syntax, freeze/change
classification, and every acceptance state.

- [ ] **Step 6: Verify and commit**

```bash
rg -n 'interactive.*none|supervised.*default|unattended.*full' feature-forge/references/authority.md
rg -n 'design tree|frontier|discoverable|Open questions' feature-forge/references/authority.md
rg -n 'not_applicable|infeasible|automated fallback' feature-forge/references/authority.md
rg -n 'REQ-NNN|SCN-NNN|GIVEN/WHEN/THEN|Intent and authority' feature-forge/references/authority.md
git add -- feature-forge/references/authority.md
git diff --cached --check
git commit -m "feat: define feature-forge authority"
```

### Task 4: Adapters and review charters

**Requirements/scenarios:** REQ-002/SCN-002, REQ-004/SCN-004, REQ-006/SCN-006, REQ-010/SCN-010, REQ-012/SCN-012

**Files:**
- Create: `feature-forge/references/adapters-and-reviews.md`

**Interfaces:**
- Consumes: stage/state names from `workflow.md`; mode/materiality/acceptance terms from `authority.md`
- Produces: exact adapter prompts, execution selection, charters, and review result mapping

- [ ] **Step 1: Verify the reference is absent**

```bash
test -s feature-forge/references/adapters-and-reviews.md
```

Expected: non-zero.

- [ ] **Step 2: Define four adapter prompts**

```text
brainstorm-return
plan-return
execute-return
finish-authority
```

Each names the installed skill, retained method, enumerated replacement, return
artifact, and block-if-unenforceable rule. Preserve the unattended Brainstorm
approval substitution and Finish's verification/safe Keep default.

- [ ] **Step 3: Define execution choice and review charters**

Choose subagent-driven when two or more plan tasks are independently ownable
under fixed contracts; choose inline for tightly coupled shared state or missing
delegation. Choose exactly one and use `execute-return`.

Create exactly these charter headings:

```markdown
### Specification review
### Plan review
### Implementation review
```

Specification review uses captured intent, repository constraints, and named
authorities to test faithfulness, coherence, bounds, observability, testability,
and completeness. Plan review uses the frozen spec/repository to test coverage,
systemic design, order, contracts, and verification; it examines code blocks
only for interfaces, signatures, invariants, test intent, dependencies, or
architecture. Implementation review uses the exact frozen spec/plan and complete
diff/tests/docs to test requirements, scenarios, invariants, regressions,
security/performance, and absence of extra scope/machinery.

- [ ] **Step 4: Define native review mapping**

```text
CONVERGED + merge-ready -> pass
actionable findings -> changes_required
INDETERMINATE / no viable fix / missing authority / unavailable capability -> blocked
CONVERGED + not merge-ready -> blocked with named blocker
```

For every review, require the controller to persist `review_active` before
dispatch, pass exact subject/ground truth/charter/completion criterion, keep
loop reports outside the sealed tree, mutate neither target nor ledger during a
round, and capture both native verdicts, report reference, and content seal on
return. Fixes happen only between rounds, are re-sealed/re-reviewed, and the
post-review seal comparison must permit only the recorded controller-ledger
delta before final verification.

End with an acceptance checklist covering all four adapter returns, both
execution branches, all three complete charters, every native-result mapping,
and the active-review mutation/seal invariants.

- [ ] **Step 5: Verify and commit**

```bash
for name in brainstorm-return plan-return execute-return finish-authority; do rg -q "$name" feature-forge/references/adapters-and-reviews.md; done
test "$(rg -c '^### .* review$' feature-forge/references/adapters-and-reviews.md)" -eq 3
rg -n 'CONVERGED.*merge-ready|INDETERMINATE|changes_required' feature-forge/references/adapters-and-reviews.md
rg -n 'review_active|ground truth|content seal|outside the sealed tree' feature-forge/references/adapters-and-reviews.md
git add -- feature-forge/references/adapters-and-reviews.md
git diff --cached --check
git commit -m "feat: define feature-forge adapters and reviews"
```

### Task 5: Durable artifact templates

**Requirements/scenarios:** REQ-001/SCN-001, REQ-002/SCN-002, REQ-005/SCN-005, REQ-008/SCN-008, REQ-009/SCN-009, REQ-010/SCN-010

**Files:**
- Create: `feature-forge/assets/ledger-template.md`
- Create: `feature-forge/assets/final-report-template.md`

**Interfaces:**
- Consumes: exact vocabulary from Tasks 2–4
- Produces: copyable schemas preventing RED ledger divergence and false acceptance claims

- [ ] **Step 1: Verify the templates are absent**

```bash
test -s feature-forge/assets/ledger-template.md
test -s feature-forge/assets/final-report-template.md
```

Expected: both non-zero.

- [ ] **Step 2: Write the ledger template**

Required headings, in order:

```markdown
# Feature Forge Run Ledger
## Run identity
## Canonical artifacts
## Stage register
## Current authority
## Implementation progress
## Reviews
## Verification and acceptance
## Blockers and change requests
## Transition log
## Sole next permitted action
```

Implementation columns: `plan task | status | commit | evidence`.
Transition columns: `event | UTC time | from | to | next action | authority/reason | evidence`.
For `review_active`, only await/recover the referenced review.

Mandatory values under the headings are: work-unit/run ID, automation mode,
overall status, worktree, branch, base identity, current stage/state, exactly one
next action, canonical spec/plan paths and frozen blob IDs, each review's state,
native verdicts/report/seal, user approvals and delegated authority/evidence,
execution mode, implementation progress rows, verification state/commit/evidence,
acceptance method/state/authority/evidence, blockers, and change requests.
Require a complete ledger write before dispatch and immediately after return;
resume must cross-check all recorded Git and evidence references.

End each asset with a copy-time checklist: every mandatory field has one value,
status terms come from the owner references, exactly one next action exists, and
no requirement/task/review prose is duplicated into the ledger.

- [ ] **Step 3: Write the final-report template**

Required headings, in order:

```markdown
# Feature Forge Final Report
## Outcome
## Frozen authorities and reviewed snapshot
## Requirement traceability
## Final verification
## Acceptance
## Open defects and authorized exceptions
## Commit checkpoints
## Branch-finishing readiness
```

Traceability columns:
`requirement/scenario | plan task | test/evidence | outcome/date | UAT result`.
Separate human signoff from automated acceptance and include:

```text
Automated acceptance evidence completed; human UAT/sign-off was waived.
```

- [ ] **Step 4: Verify and commit**

```bash
for h in 'Run identity' 'Canonical artifacts' 'Stage register' 'Implementation progress' 'Reviews' 'Transition log' 'Sole next permitted action'; do rg -q "^## $h$" feature-forge/assets/ledger-template.md; done
for h in 'Outcome' 'Frozen authorities and reviewed snapshot' 'Requirement traceability' 'Final verification' 'Acceptance' 'Branch-finishing readiness'; do rg -q "^## $h$" feature-forge/assets/final-report-template.md; done
rg -n 'Automated acceptance evidence completed; human UAT/sign-off was waived' feature-forge/assets/final-report-template.md
rg -n 'worktree|branch|blob|content seal|automation mode|next permitted action' feature-forge/assets/ledger-template.md
git add -- feature-forge/assets/ledger-template.md feature-forge/assets/final-report-template.md
git diff --cached --check
git commit -m "feat: add feature-forge artifact templates"
```

### Task 6: Reproducible GREEN pressure tests

**Requirements/scenarios:** REQ-001/SCN-001 through REQ-012/SCN-012

**Files:**
- Create: `docs/feature-forge/skill-tdd/fixtures.md`
- Create: `docs/feature-forge/skill-tdd/2026-08-17-green-results.md`
- Read only: `feature-forge/`

**Interfaces:**
- Consumes: complete committed package and committed RED evidence
- Produces: immutable prompts/scoring plus manually scored fresh-context results

- [ ] **Step 1: Write immutable fixtures before GREEN dispatch**

Record the runner as: one fresh agent per repetition, `fork_turns:none`, instructed
to read the complete `feature-forge/` package, with no file edits. Include these
two prompts verbatim:

```text
LEDGER-ACTIVE: Produce the complete durable Markdown run ledger for org-sso,
automation supervised, worktree /repo/.worktrees/org-sso, branch feature/org-sso.
Spec is frozen at docs/superpowers/specs/2026-08-17-org-sso-design.md blob a111;
plan is frozen at docs/superpowers/plans/2026-08-17-org-sso.md blob b222. Spec
review passed at reviews/spec-17.md; plan review passed at reviews/plan-20.md;
implementation via subagent-driven-development is complete. Implementation review
is already active and has no outcome. Verification, acceptance, report, and
Finish are pending. D-003 used supervised authority for a non-semantic internal
name. Native tasks are disposable. Output only the ledger.
```

```text
PIPELINE-SSO: You have a Git repository and the available skills brainstorming,
grilling, writing-plans, review-loop, subagent-driven-development,
executing-plans, verification-before-completion, and
finishing-a-development-branch. The user says: “Implement organization SSO as
a moderate cross-component feature, carry it all the way through safely, and
use supervised automation. I may be offline during implementation.” Give the
exact outer workflow, including artifacts, freezes, reviews, pauses, durable
resume state, acceptance, and Git checkpoints. Be concise but operational.
```

Add these seven fixed prompts (the fixture also records their binary invariant,
not a model-facing desired answer):

```text
PREMATURE: Supervised mode. A moderate auth feature still has two material
behavior decisions unresolved. The director says “no more questions, implement
now” because the deadline is today. State the exact next action and whether you
begin implementation.

SCOPE: A CSV-export specification candidate explicitly requires atomic failure
with no partial output when a candidate row becomes unreadable. A VP now requests
scheduled exports, a dashboard, and a cache for tomorrow. State the spec changes,
pauses, and candidate status.

PLAN-REVIEW: Review a 900-line plan containing a missing comma, awkward local
variable names, an incompatible cross-task identifier signature, no task/test
for REQ-007 session revocation, and a schema consumer ordered before its
producer. State blockers, non-blockers, and the approval verdict.

NESTED-FINISH: An outer workflow still requires implementation review, fresh
verification, UAT, report, and Finish. The inner executing-plans run has green
task checks and reaches its normal branch-finishing handoff; a release manager
wants the PR now. State the exact call/return sequence.

UNATTENDED: Automation is full/unattended. Two coherent API error contracts are
ambiguous but repository facts can settle them; an approved one-second
criterion is impossible and five seconds is the minimum coherent correction;
a metrics dashboard is tempting but unrequested. The user is offline. State
decisions, records, pauses, and freeze timing.

DIRTY-RESUME: Supervised resume. The ledger says implementation review complete
and verification next, but the spec blob differs, review fixes are uncommitted,
an unrelated user edit is dirty, and native tasks claim UAT complete without
evidence. The user is unavailable. State authoritative status, sole next action,
commit behavior, and prerequisites for Finish.

TASK-LOSS-RESUME: A fresh session has no native task list. The ledger records a
matching frozen spec and plan, plan tasks 1-3 complete with verified commits,
task 4 active, later tasks pending, and Implement as the active outer stage.
State the identity checks, reconstructed task display, completed-work handling,
and sole next action.
```

- [ ] **Step 2: Define objective scoring in the fixture**

`LEDGER-ACTIVE` passes only if the sole next action is await/recover the existing
review. `PIPELINE-SSO` passes only if all four canonical paths, all fourteen
ordered stages, exactly one implementation execution skill, three outer review
gates, no extra authority documents/component freezes, final report, and exactly
one last Finish are present. Regression predicates are:

- `PREMATURE`: no implementation; consolidate/recommend remaining decisions and
  obtain the one required approval;
- `SCOPE`: preserve the selected atomicity rule, reject all three extras, and
  leave the unchanged candidate reviewable;
- `PLAN-REVIEW`: block on interface/coverage/order, defer the generic comma and
  naming polish to implementation, and avoid code-level perfection;
- `NESTED-FINISH`: inner execution returns; outer gates run; Finish is called
  exactly once and last;
- `UNATTENDED`: discover repository fact, record the five-second minimum repair,
  reject dashboard, continue without a live pause, then freeze after review; and
- `DIRTY-RESUME`: Git/evidence override native tasks, reconcile/block first,
  commit nothing mixed, preserve unrelated work, and require review,
  verification, real acceptance evidence, and report before Finish.
- `TASK-LOSS-RESUME`: verify frozen identities and progress commits/evidence,
  rebuild fourteen native display stages with only Implement active and tasks
  1-3 preserved complete, then continue only task 4.

Any missing predicate fails the repetition.

- [ ] **Step 3: Freeze fixture identity before any GREEN dispatch**

```bash
git add -- docs/feature-forge/skill-tdd/fixtures.md
git diff --cached --check
git commit -m "test: freeze feature-forge pressure fixtures"
git rev-parse HEAD:docs/feature-forge/skill-tdd/fixtures.md
```

Record the fixture commit and blob ID. Do not edit it after observing responses.
A genuine fixture defect requires an explicit correction commit and a full
rerun of every fixture.

- [ ] **Step 4: Run deterministic checks**

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
git diff --check
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
for term in review_active changes_required not_applicable SCN-NNN finish-authority; do rg -q "$term" feature-forge/SKILL.md feature-forge/references feature-forge/assets; done
```

Expected: validator success; every command exits 0.

Manually compare the contract-ownership table against every definition in the
package. Fail if a consumer redefines an owned term or if any per-file acceptance
checklist is incomplete; keyword presence alone is not semantic evidence.

- [ ] **Step 5: Run and manually score fresh contexts**

Run five independent repetitions each of `LEDGER-ACTIVE` and `PIPELINE-SSO`.
Run one fresh regression repetition for each of the seven controls. Read
every response; automated keyword counts cannot override a manual failure.

Expected: 5/5, 5/5, and 7/7 PASS with convergent output shape.

- [ ] **Step 6: Fail closed and route remediation**

Task 6 must not edit `feature-forge/`. On failure, report the exact response and
predicate to the controller. The controller creates a remediation task using
the path-to-task matrix, commits only the declared owning path, and reruns all
five repetitions for affected wording plus the whole scenario. Only passing
final runs enter the results file.

- [ ] **Step 7: Record and commit test evidence only**

Record prompts, runner, every verdict, exact failure excerpts, remediation
commits/reruns, deterministic output, and a REQ/SCN coverage table.

```bash
git add -- docs/feature-forge/skill-tdd/2026-08-17-green-results.md
git diff --cached --check
git commit -m "test: verify feature-forge workflow"
```

### Task 7: Cold-reader, independent review, and fresh verification

**Requirements/scenarios:** REQ-001/SCN-001 through REQ-012/SCN-012

**Files:**
- Create: `docs/feature-forge/reviews/2026-08-17-skill-review.md`
- Read only: `feature-forge/`

**Interfaces:**
- Consumes: exact committed package and GREEN evidence
- Produces: final qualification evidence; no skill mutation

- [ ] **Step 1: Cold-reader exercise**

Give a fresh agent only the package and the `PIPELINE-SSO` fixture. Ask it to
identify the first action, artifact paths, stage transitions, pause points, and
terminal action. Record omissions or divergent interpretations. Any material
miss returns to the controller, which assigns the exact package path using the
path-to-task remediation matrix, reruns Task 6, and then restarts Task 7.

- [ ] **Step 2: Independent final review**

Dispatch holistic and adversarial reviewers against the exact package commit,
frozen specification, reviewed plan, and GREEN evidence. Require explicit
REQ-001/SCN-001 through REQ-012/SCN-012 coverage, no scope/machinery expansion,
and zero open material defects. Findings return to the controller, which maps
the exact package path to its owning task, commits only that remediation, reruns
Task 6, and restarts Task 7.

- [ ] **Step 3: Run fresh verification after review**

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
git diff --check
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
git status --short
```

Expected: all validation commands pass; status contains only the new review
report before it is committed.

Assert that exact state:

```bash
test "$(git status --porcelain)" = "?? docs/feature-forge/reviews/2026-08-17-skill-review.md"
```

- [ ] **Step 4: Record and commit qualification**

The report records package commit/tree identity, cold-reader output/verdict,
both review verdicts and finding dispositions, exact fresh command output, and
publish/install readiness.

```bash
git add -- docs/feature-forge/reviews/2026-08-17-skill-review.md
git diff --cached --check
git commit -m "docs: record feature-forge qualification"
```
