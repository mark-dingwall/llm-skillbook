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

## Use the live contract

Start with [the skill contract](SKILL.md). It defines invocation, the required
workflow, the controller boundary, and failure policy. Consult the live
[run-plan contract](references/run-plan.md),
[packet contract](references/packets.md), and
[report and diagnosis contract](references/report.md) when running or changing
the workflow. Scripts: `scripts/wt-log`, `scripts/wt-validate`,
`scripts/wt-telemetry`.

The [design records](docs/) and [evaluation evidence](evals/) are retained as
historical provenance. They document earlier decisions and validation, but are
not the operational authority.
