# Feature Forge

Feature Forge carries a bounded, nontrivial Git work unit from a settled
specification through independent review, implementation, verification,
acceptance, and branch finishing. Use it for a feature, migration, refactor, or
other work with meaningful ambiguity, risk, or cross-component coordination.
For a small mechanical edit, use the appropriate focused skill instead.

## Start a run

Invoke `feature-forge` in Claude Code or `$feature-forge` in Codex. State the
work unit and, when useful, an automation mode:

```text
Use feature-forge to add organization SSO. Automation: supervised.
```

`supervised` is the default. Feature Forge may ask for decisions that change
goals, scope, behavior, acceptance, compatibility, cross-task contracts,
security, or architecture. It records that authority rather than guessing. It
also asks before any integration action that needs user authority; unattended
runs use only recorded authority and otherwise stop safely.

## What a run needs

Feature Forge is an instruction-only outer controller, not a runtime or a
replacement for its participating skills. A run needs Git, an isolated
worktree, a configured reviewer runner for `review-loop`, and these installed
skills:

- `review-loop` for independent specification, plan, and implementation review
- Superpowers skills for brainstorming, planning, implementation, and branch
  finishing

The controller selects the appropriate execution path and prevents delegated
skills from taking over the outer workflow or finishing the branch early.

## Operating contract

[`SKILL.md`](SKILL.md) is the invocation contract. Before operating a run,
read the live owner references for the [workflow and durable state](references/workflow.md),
[authority and acceptance](references/authority.md), and [adapters and reviews](references/adapters-and-reviews.md).
The reusable ledger and final-report templates support those contracts.

Design notes, qualification records, and prior reviews under `docs/` are
lineage and evidence. They are not current execution authority; use the live
contract above when operating or maintaining Feature Forge.

## Install

See the [repository installation guide](../README.md#install) for in-repository
discovery or installation to Claude Code and Codex.
