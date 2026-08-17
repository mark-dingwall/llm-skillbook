# review-loop

`review-loop` is a deterministic controller for an external code or document
review. It records a sealed target, review evidence, TRIAGE decisions, and
FIX evidence in a canonical ledger. Code, not a reviewer saying "looks
clean", derives the terminal verdict and merge-readiness from that ledger.

> No known material defect after risk-proportionate independent challenge and
> applicable deterministic evidence gates.

That is a qualified operational verdict, never proof. A hand-back must name
the evidence that ran, evidence gaps, degraded behavior, and residual limits.

## Operating the current boundary

The production CLI intentionally handles only durable mechanical operations:

- `create-run` seals the target and records invocation intent.
- `status` derives a coarse stage from the furthest durable processor
  operation.
- `report` renders the canonical run report.

The role-driving stages — Stage 0, review, TRIAGE, FIX, adjudication, final
challenge, and CLOSE — require a host/controller caller. That caller renders
the applicable role prompt, dispatches it through a tested containment mapping,
validates the raw result, and calls the controller. It must not substitute a
shell state machine or caller-authored canonical projections. See
[SKILL.md](SKILL.md) for the controller contract and [dispatch.md](dispatch.md)
for CLI requests and execution mappings.

The lifecycle is:

```
PREFLIGHT → STAGE0 → REVIEW → TRIAGE → FIX → CLOSE
```

At any unsafe or incomplete boundary, the run fails closed rather than
silently continuing. A failed applicable gate, seal mismatch, malformed role
output after its retry, expired deadline, or uncontained dispatch prevents a
green result.

## Current scope and limits

The controller supports one single-round review cycle when an external host
supplies the role rendering, strict validation, dispatch callbacks, and stage
sequencing. This component does not ship that end-to-end host driver. When
TRIAGE leaves Important or Critical findings open, the sole FIX role works in a
contained disposable copy; its candidate delta and post-FIX gates are verified
before an exact write-back can promote the result to the authoritative target.
Later-round TRIAGE reconciliation, baseline advancement, inventory refresh,
and restaffing are not wired and are refused rather than approximated.

Multi-review is available only when the host explicitly supplies its adapter;
ordinary review remains the default. Use that opt-in only for a high/max run
whose operator accepts the documented containment residuals. If its driver,
containment, or fixed participant is unavailable, the holistic slot falls back
once to ordinary review; seal drift is indeterminate, never a fallback.

There are also deliberately visible reporting and recovery limits:

- `status` cannot durably distinguish a pre-review cancellation or a
  confirmation-stage indeterminate result from a Stage 0 interruption.
- If a verified disposable-copy FIX was not promoted, CLOSE correctly
  persists `NOT_CONVERGED` and `merge_ready=false`, but `status` derives the
  coarse stage as `COMPLETE` rather than the controller's in-memory
  `INDETERMINATE` outcome.
- The generated report renders canonical verdicts and ledger state, but its
  mutation-evidence and degraded-behavior sections are not yet fully derived
  from run state.
- `merge_ready` is mechanical and conservative; the current kernel does not
  yet represent a distinct "converged but not merge-ready" terminal outcome.
- A final-readiness `BLOCK` stops closed because its supplemental-TRIAGE path
  is not yet implemented.

[DESIGNING_PROFILES.md](DESIGNING_PROFILES.md) explains the optional,
safety-bounded profile format.

## History

The [historical materials](docs/history/) preserve superseded workflows and
research as context, not operating authority. The retained [redesign
document](docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md)
is design lineage; current operation follows the shipped skill, dispatch
guidance, and controller behavior.
