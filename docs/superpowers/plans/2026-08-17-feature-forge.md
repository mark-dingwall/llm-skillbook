# Feature Forge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the repository-local `feature-forge` skill that carries a bounded Git work unit from specification through reviewed acceptance without improvising its outer protocol.

**Architecture:** Keep `SKILL.md` as the short discoverable controller, move normative workflow, authority, adapter, and review contracts into three directly linked references, and provide two copyable Markdown assets for durable state and final evidence. There is no runtime program; deterministic checks validate document contracts while fresh-context pressure scenarios validate behavior.

**Tech Stack:** Agent Skills Markdown/YAML, Git, shell contract checks, `skill-creator`, Superpowers skills, `review-loop`, fresh-context subagents

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
| `docs/feature-forge/skill-tdd/2026-08-17-green-results.md` | Forward-test evidence |

---

### Task 1: Controller and discovery metadata

**Requirements:** REQ-001, REQ-002, REQ-005, REQ-009, REQ-012

**Files:**
- Modify: `feature-forge/SKILL.md`
- Verify: `feature-forge/agents/openai.yaml`

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

**Requirements:** REQ-001, REQ-002, REQ-005, REQ-006, REQ-007, REQ-009, REQ-011, REQ-012

**Files:**
- Create: `feature-forge/references/workflow.md`

**Interfaces:**
- Consumes: mode decisions from `authority.md`; adapter/review result names from `adapters-and-reviews.md`
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

- [ ] **Step 4: Write identity, resumption, and commits**

Define `<path>@<git-blob-id>` for frozen artifacts, the `review-loop` content
seal, the implementation table (`plan task | status | commit | evidence`),
read-only drift reconciliation, the fixed invalidation graph, exact-path staging,
seven checkpoint categories, the permitted post-review ledger delta, and a clean
tree before Finish.

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

**Requirements:** REQ-003, REQ-004, REQ-007, REQ-008

**Files:**
- Create: `feature-forge/references/authority.md`

**Interfaces:**
- Consumes: canonical spec ownership from `workflow.md`
- Produces: mode authority, hardening, materiality, invalidation, and acceptance vocabulary

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

- [ ] **Step 4: Write freezes and acceptance**

Include candidate/frozen rules, the fixed invalidation graph, editorial delta
re-review, methods `automated | UAT | not_applicable`, and states
`pending | approved | rejected | infeasible | waived`. Every UAT declares an
unattended automated fallback/evidence criterion or unattended blocks.

- [ ] **Step 5: Verify and commit**

```bash
rg -n 'interactive.*none|supervised.*default|unattended.*full' feature-forge/references/authority.md
rg -n 'design tree|frontier|discoverable|Open questions' feature-forge/references/authority.md
rg -n 'not_applicable|infeasible|automated fallback' feature-forge/references/authority.md
git add -- feature-forge/references/authority.md
git diff --cached --check
git commit -m "feat: define feature-forge authority"
```

### Task 4: Adapters and review charters

**Requirements:** REQ-002, REQ-004, REQ-006, REQ-010, REQ-012

**Files:**
- Create: `feature-forge/references/adapters-and-reviews.md`

**Interfaces:**
- Consumes: stage names from `workflow.md`; mode from `authority.md`
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

Plan review covers spec coverage, systemic design, order, contracts, and
verification. It examines code blocks only for interfaces, signatures,
invariants, test intent, dependencies, or architecture.

- [ ] **Step 4: Define native review mapping**

```text
CONVERGED + merge-ready -> pass
actionable findings -> changes_required
INDETERMINATE / no viable fix / missing authority / unavailable capability -> blocked
CONVERGED + not merge-ready -> blocked with named blocker
```

- [ ] **Step 5: Verify and commit**

```bash
for name in brainstorm-return plan-return execute-return finish-authority; do rg -q "$name" feature-forge/references/adapters-and-reviews.md; done
test "$(rg -c '^### .* review$' feature-forge/references/adapters-and-reviews.md)" -eq 3
rg -n 'CONVERGED.*merge-ready|INDETERMINATE|changes_required' feature-forge/references/adapters-and-reviews.md
git add -- feature-forge/references/adapters-and-reviews.md
git diff --cached --check
git commit -m "feat: define feature-forge adapters and reviews"
```

### Task 5: Durable artifact templates

**Requirements:** REQ-001, REQ-002, REQ-005, REQ-008, REQ-009, REQ-010

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
git add -- feature-forge/assets/ledger-template.md feature-forge/assets/final-report-template.md
git diff --cached --check
git commit -m "feat: add feature-forge artifact templates"
```

### Task 6: Structural validation and GREEN pressure tests

**Requirements:** REQ-001 through REQ-012

**Files:**
- Create: `docs/feature-forge/skill-tdd/2026-08-17-green-results.md`
- Verify: `feature-forge/`

**Interfaces:**
- Consumes: complete package plus committed RED prompts/results
- Produces: deterministic evidence and manually scored fresh-context behavior

- [ ] **Step 1: Run deterministic checks**

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
git diff --check
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
```

Expected: validator success; every command exits 0.

- [ ] **Step 2: Run five ledger micro-tests with the skill**

Use the exact RED `implementation review is active` prompt. PASS only when the
sole action is await/recover the referenced review. Read every response.

Expected: 5/5 PASS, with no duplicate review or downstream action.

- [ ] **Step 3: Run five outer-pipeline tests with the skill**

Use the exact supervised organization-SSO RED prompt. PASS requires canonical
paths, fourteen stages, one execution skill, no invented authority documents or
component gates, and Finish only after review/verification/acceptance/report.

Expected: 5/5 PASS.

- [ ] **Step 4: Re-run passing judgment controls**

Re-run premature implementation, scope expansion, plan-review distraction,
nested finishing, unattended authority, and dirty-worktree resumption.

Expected: all remain PASS without gratuitous machinery.

- [ ] **Step 5: Record evidence and refactor only observed failures**

Write prompts, per-repetition outcomes, exact failure excerpts, fixes/reruns,
deterministic output, and REQ-001..REQ-012 coverage to the GREEN results file.
For output-shape failures use a positive recipe/template; for pressure-driven
violations add the observed rationalization counter; for conditional ambiguity
use an observable predicate. Re-run five fresh samples after any wording edit.

- [ ] **Step 6: Commit**

```bash
git add -- feature-forge docs/feature-forge/skill-tdd/2026-08-17-green-results.md
git diff --cached --check
git commit -m "test: verify feature-forge workflow"
```
