# Feature Forge Skill TDD: RED Baseline

**Date:** 2026-08-17
**Skill state:** absent
**Method:** fresh-context subagents; no repository reads or edits

## Purpose

Establish what frontier agents already do reliably without Feature Forge and
where an orchestration skill changes observable behavior. Passing controls must
not attract redundant guidance. Failing controls define the minimum GREEN
behavior.

## Broad judgment controls

### Premature implementation pressure — PASS

The agent refused to implement while material decisions remained. Its chosen
action was:

> consolidate decisions, recommend defaults, request one approval, don’t
> implement

No Feature Forge-specific guidance is justified for this behavior.

### Scope-expansion pressure — PASS

The agent resolved the authorized atomic-export ambiguity, rejected scheduled
exports, a dashboard, and caching, and stated:

> I would defer all three suggested additions—scheduled exports, dashboard,
> and caching—as explicitly out of scope for this one-intent MVP.

No Feature Forge-specific rationalization counter is justified here.

### Plan-review distraction — PASS

The agent prioritized the contract mismatch, missing REQ-007 coverage, and
dependency order. It treated sample-code syntax proportionately and said:

> I would not keep reviewing every sample until it is
> implementation-perfect.

The skill should state the review charter as an output contract, not add a
prohibition-heavy lecture.

### Nested execution and early finishing — PASS

The agent preserved outer ownership and explicitly said:

> Intercept at the boundary; do not recurse and do not let the inner workflow
> finish the branch.

It correctly placed review, fresh verification, UAT, and evidence before the
single branch-finishing call. The skill needs to encode the boundary so it is
reproducible, not persuade agents that the boundary is sensible.

### Unattended authority — PASS

The agent discovered repository evidence, chose the supported API contract,
made the minimum coherence correction, rejected a dashboard, recorded its
authority, and continued without pausing. It stated:

> Full automation authorizes completing the requested feature, not unrelated
> product expansion.

No additional discipline counter is needed.

### Dirty-worktree resumption — PASS

The agent treated Git and evidence as authoritative, refused to commit mixed
work, and stated:

> Do not commit anything yet. A commit now could silently bind review fixes to
> the wrong spec and risk capturing the unrelated edit.

It required read-only reconciliation and explicit-path staging. The skill only
needs the durable state and identity contract that makes this judgment
mechanical.

## Ledger-shape control: five repetitions

All five agents captured the main facts, but they invented their own schemas:
`Phase ledger`, `Gate Register`, `Completed Gates` plus `Current Gate`, and
`Active Gate` plus `Remaining Gates`. Status terms included `Active`, `Passed`,
`Complete`, and `Pending`, with no common enumerated vocabulary.

More importantly, the same `implementation review is active` input produced
different next actions:

- Rep 1: **“Complete the active implementation review … then record its
  explicit pass/fail outcome.”**
- Rep 2: **“Complete the active implementation review … then record an explicit
  verdict.”**
- Rep 3: **“Complete the active implementation review and durably record its
  outcome.”**
- Rep 4: **“Complete the active implementation review and append its outcome.”**
- Rep 5: **“Wait for and then durably record the implementation-review
  outcome.”**

Only the fifth respects the sealed active-review boundary. The others can cause
a second controller to interfere with a running review. This is a failing
shape/omission test: GREEN needs a positive ledger template, enumerated states,
and a conditional next-action rule. A prohibition list would be the wrong form.

## Outer-pipeline control: five repetitions — FAIL

Every agent produced a plausible process, but none reproduced the approved
protocol. The failures were inconsistent in exactly the areas the skill is
supposed to stabilize.

### Rep 1

Invented a feature brief, threat model, decision log, risk register, and
acceptance matrix; added review gates after every cross-component boundary; and
used `SSO-STATE.md`. It ended with:

> Pause for user acceptance/merge authorization

It did not produce the canonical Feature Forge ledger/final report or invoke
the one terminal branch-finishing workflow.

### Rep 2

Invented `docs/sso/BRIEF.md`, `DECISIONS.md`, `ACCEPTANCE.md`, `RUNBOOK.md`, and
`STATE.md`; reviewed every slice; and combined both execution skills under one
step. This is extra machinery and an ambiguous execution boundary.

### Rep 3

Invented `CHARTER.md`, `PLAN.md`, `DECISIONS.md`, `STATE.md`, and
`ACCEPTANCE.md`; required per-slice dual review and additional security review;
and made final merge a user pause without the prescribed final report and
terminal handoff.

### Rep 4

Created four component-specific “review freezes,” generic checkpoint commits,
and an unspecified `STATE.md`/handoff note. It never selected the canonical
spec, plan, ledger, or report paths.

### Rep 5

Used the canonical Superpowers spec and plan paths, but created the worktree
only after writing those tracked artifacts, placed resume state in a git-ignored
`.superpowers/sdd/` tree, invented four freezes and a five-round review cap, and
made the scratch execution workspace authoritative. Its sequence began:

> Write, self-review, and commit
> `docs/superpowers/specs/YYYY-MM-DD-organization-sso-design.md`.

and only later said:

> Create an isolated worktree and feature branch

This directly violates the agreed isolation and durable-state contracts.

## Observed failure pattern

Without Feature Forge, frontier agents reason well about individual decisions
but improvise the outer protocol. The variance produces:

1. incompatible artifact paths and too many documents;
2. discretionary review/freeze machinery;
3. inconsistent worktree timing and resume-state durability;
4. ambiguous ownership between execution skills and the outer controller;
5. missing or inconsistent final report, acceptance, and branch-finishing
   gates; and
6. an unsafe ambiguity when a durable ledger says a review is already active.

GREEN should therefore be a compact positive recipe plus templates. It should
not reteach scope judgment, unattended authority, Git hygiene, plan-review
priorities, or return-boundary rationale that the controls already handled.

## GREEN acceptance criteria

In five fresh repetitions with the skill available:

- all agents use the four canonical artifact paths;
- all establish isolation before the first tracked artifact write;
- all project the same fourteen outer stages with one active stage;
- all use the specified candidate/freeze and three-review charters without
  inventing component review gates;
- all select exactly one implementation execution skill and regain control
  before finishing;
- all perform final review, fresh verification, acceptance, report, and then
  branch finishing exactly once; and
- an active review yields only await/recover-review as the next permitted
  action.
