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
[`adapters-and-reviews.md`](references/adapters-and-reviews.md) (bounded stage
methods, worker packets, review charters) before any dispatch. Use
[`ledger-template.md`](assets/ledger-template.md) for a new run and
[`final-report-template.md`](assets/final-report-template.md) at Stage 13.

## Outer control

Use only the bounded stage returns and regain control at every return; record
the result in the ledger and follow its declared transition.

Invoke every mechanical gate as
`python3 "$SKILL_DIR/scripts/ff-check" COMMAND --repo REPOSITORY [OPTIONS]`,
where `$SKILL_DIR` is this installed skill directory. A well-formed verified
`fail` follows the explicit route in `workflow.md`; checker launch failure or a
missing/malformed result line is `unverifiable -> blocked`. The checker reports
facts only: Feature Forge still owns classification, invalidation, and the
ledger transition.

Follow the ordered stages and recoverable Finish protocol in `workflow.md`.
Report must persist `finish_id` and phase `ready` before Finish starts; resume
that same operation from its recorded phase. The workflow reference owns the
verification, acceptance, checkpoint, and per-effect journal requirements.

## Red flags

Stop and recover rather than infer state when the canonical run, ledger, exact
artifacts, sole next action, content seal, stage return, or acceptance
authority is missing or inconsistent. Never start Finish before Report has
persisted `finish_id`/`ready`, treat native tasks as authoritative, or dispatch
before all owner references are loaded.
