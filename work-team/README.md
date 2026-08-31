# work-team

`work-team` runs a task as a controller-owned team of fresh subagents: an
editable run plan, minimal worker packets, validated structured returns,
bounded review→fix loops, a per-worker audit trail, and a result that names
its residuals. It is a tunable stand-in for a built-in dynamic workflow, not an
end-to-end feature-delivery process — that is `feature-forge`.

## Use it

```text
/work-team <task>          Claude Code
$work-team <task>          Codex
```

Artefacts land in `.work-team/<run>/`: `plan.json`, `workflow-log.jsonl`,
`result.json`, `report.md`. Edit `plan.json` and rerun to tune.

## What a result means

`outcome: complete` means every verification command passed and no
blocker/important residual is open. `residual` lists everything dropped,
capped, retried, or unverified; an empty list is a claim, not a default.

## Live contract

Start with [SKILL.md](SKILL.md). Owning references: [run plan](references/run-plan.md),
[packets](references/packets.md), [report and diagnosis](references/report.md).
Scripts: `scripts/wt-log`, `scripts/wt-validate`, `scripts/wt-telemetry`.
[Design](docs/) and [evals](evals/) are provenance, not authority.
