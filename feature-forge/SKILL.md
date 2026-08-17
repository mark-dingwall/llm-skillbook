---
name: feature-forge
description: Use when implementing a bounded Git-repository feature or comparable work unit whose size, risk, ambiguity, or cross-component coordination warrants explicit specification, planning, independent review, and acceptance
---

# Feature Forge

## Core invariant

Feature Forge is the sole outer controller from preflight through acceptance
and Finish. It maintains one canonical run and advances only the ledger's sole
next permitted action; native skills and tasks do not replace that control.

## Start or resume

Verify that this is a Git repository and that work is isolated. Select the
canonical run, or recover it when resuming. For a new run, copy
[`ledger-template.md`](assets/ledger-template.md) into the canonical run
directory. On resume, read the ledger and every exact artifact it names, then
perform only its sole next permitted action. Before dispatch, load all owner
references below. Project native tasks only as display, never as workflow
state.

## Load the owner references

Read [`workflow.md`](references/workflow.md) (canonical paths, fourteen
stages, states, checkpoints, Finish lifecycle and recovery),
[`authority.md`](references/authority.md) (modes, materiality, candidate and
freeze authority, UAT), and
[`adapters-and-reviews.md`](references/adapters-and-reviews.md) (the four
adapters, worker packets, review charters) before any dispatch. Use
[`ledger-template.md`](assets/ledger-template.md) for a new run and
[`final-report-template.md`](assets/final-report-template.md) at Stage 13.

## Outer control

Intercept only the four named adapters and regain control at every return;
record the result in the ledger and follow its declared transition.

Drive the terminal recipe in this order, never any other: implementation
returns, implementation review passes, fresh verification, acceptance
evidence, Stage 13 Report, Stage 14 Finish. Stage 13 writes the final report,
allocates and persists `finish_id`, and records Finish phase `ready` while the
run stays active — this must complete and persist before Stage 14 begins.
Stage 14 then durably drives the one logical Finish operation for that
`finish_id` and invokes `finish-authority` exactly once, as the sole and last
external-skill invocation; the category 8 bookkeeping commits around it are
not additional invocations. Finish is recoverable, not physically atomic — on
resume, continue the same `finish_id` from its recorded phase rather than
re-dispatching or re-claiming.

## Quick checks

Confirm the active worktree, branch, canonical artifact paths, ledger state,
and content seals before each transition. Keep the specification, plan,
ledger, and final report synchronized with the declared state.

## Red flags

Stop and recover rather than infer state when the canonical run, ledger, exact
artifacts, sole next action, content seal, adapter result, or acceptance
authority is missing or inconsistent. Never invoke `finish-authority` before
Report has persisted `finish_id`/`ready`, treat native tasks as authoritative,
or dispatch before all owner references are loaded.
