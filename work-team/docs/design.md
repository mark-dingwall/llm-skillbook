# work-team design (2026-09-01)

Status: design record; the live authority is `SKILL.md` and `references/`.

## Goal

A drop-in for Claude Code's dynamic Workflow tool that runs on the harness's
ordinary subagent primitive, so every part — run plan, worker packets, loops,
audit trail, telemetry — is inspectable and tunable. Parity first; tuning later.
End-to-end feature delivery stays with `feature-forge`.

## Sources

- Trellis run telemetry (100 agents, 4 chained workflows): long serial agents
  dominate wall-clock and cost; silent nulls and dropped residuals; untestable
  requirements vanish under TDD; audit trail is the only live visibility.
- `review-team`: controller-owned scope, fresh minimal-package workers, barrier
  discipline, whole-group retry, no controller verdicts, fail-closed.
- superpowers `writing-plans` / `subagent-driven-development`: a task is the
  smallest unit with its own test cycle and review gate; batch same-shape
  small work; never parallel implementers on shared files.
- Golden rules: MVP the product and prose, not the verification; code for
  deterministic steps; small bounded LLM tasks with goal conditions.

## Shape

```text
frame (controller) → run plan (JSON, editable)
→ per phase: dispatch fresh workers (parallel iff file-disjoint and
  independently verifiable) → validate returns (wt-validate)
→ bounded review→fix loops → residuals carried, never dropped
→ verify by command → report (result.json with REQUIRED residual[], telemetry)
```

Audit: every worker appends via `wt-log`; controller logs phase transitions,
dispatches, validation failures, loop decisions. Telemetry from the log via
`wt-telemetry` (harness-neutral), used to reshape the next run.

## Decisions

- Run plan is data (`plan.json`), not prose: phases, workers, packets, schema,
  parallel groups, loop caps. It is the artefact a human edits and reruns.
- Deterministic checks are scripts: file-ownership disjointness, dependency
  order, schema validation, log parsing.
- Unobservable requirements get an explicit verification stage whose oracle is
  either a rendering-level assertion or a rubric-scored judge worker; never a
  prose instruction alone.
- Deviation from SDD: parallel implementers are allowed when file ownership is
  disjoint within a wave (worked in Trellis without worktrees).
- Numbers appear only as failure detectors in scripts/plan, never as rules in
  prose.
