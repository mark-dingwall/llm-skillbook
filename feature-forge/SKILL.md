---
name: feature-forge
description: Use when implementing a bounded Git-repository feature or comparable work unit whose size, risk, ambiguity, or cross-component coordination warrants explicit specification, planning, independent review, and acceptance
---

# Feature Forge

## Core invariant

Feature Forge is the sole outer controller from preflight through acceptance.
It maintains one canonical run and advances only the ledger's sole next
permitted action; native skills and tasks do not replace that control.

## Start or resume

Verify that this is a Git repository and that work is isolated. Select the
canonical run, or recover it when resuming. For a new run, copy
[`ledger-template.md`](assets/ledger-template.md) into the canonical run
directory. On resume, read the ledger and every exact artifact it names, then
perform only its sole next permitted action. Before dispatch, load all three
contracts below. Project native tasks only as display, not as workflow state.

## Outer control

Intercept the named adapters and regain control at every adapter return. Record
the returned result in the ledger and follow its declared transition. Invoke
branch finishing exactly once, only after all remaining Feature Forge gates are
satisfied; then complete the final report and acceptance.

## Load the contracts

Read [`workflow.md`](references/workflow.md),
[`authority.md`](references/authority.md), and
[`adapters-and-reviews.md`](references/adapters-and-reviews.md) before any
dispatch. Use [`ledger-template.md`](assets/ledger-template.md) for a new run
and [`final-report-template.md`](assets/final-report-template.md) at closeout.

## Quick checks

Confirm the active worktree, branch, canonical artifact paths, ledger state,
and content seals before each transition. Keep the specification, plan, ledger,
and final report synchronized with the declared state.

## Red flags

Stop and recover rather than infer state when the canonical run, ledger, exact
artifacts, sole next action, content seal, adapter result, or acceptance
authority is missing or inconsistent. Do not finish twice, treat native tasks
as authoritative, or dispatch before all three contracts are loaded.
