# review-team

`review-team` is a high-confidence, read-only review workflow for changes
where an independent second look is worth the coordination cost: multi-file
changes, risky refactors, or reviews requested at `high` or `xhigh` effort.

It separates discovery from judgment. The controller first captures an
immutable review scope, then fresh workers independently look for candidates.
Separate Verifiers decide whether each candidate is supported before it can
appear as a finding. The review never edits the target, posts comments, or
changes remote state.

## Choose an effort level

- `high` provides the standard independent review pipeline.
- `xhigh` adds the gap-focused Sweep after initial verification.

The deterministic report assembler requires Python 3.10 or newer.

## What a result means

Only independently verified candidates become findings. An empty result means
none survived verification; it does not certify that the change is safe.
Every independently verified `CONFIRMED` or `PLAUSIBLE` survivor is surfaced,
as a direct finding, through an LLM-inferred same-root-cause merge, or in an
exact-duplicate fallback group. Final reporting is exhaustive rather than
numerically limited, while effort-level candidate ceilings still bound
discovery. Reports favor terse prose without omitting the trigger, consequence,
or verifier evidence.

## Use the live contract

Start with [the skill contract](SKILL.md). It defines invocation, effort
selection, phase order, read-only behavior, and failure handling. Consult the
live [controller and report contract](references/report-contract.md),
[Finder contract](references/finder-angles.md), and
[Verifier contract](references/verifier.md) when running or changing the
workflow.

The [design records](docs/) and [evaluation evidence](evals/) are retained as
historical provenance. They document earlier decisions and validation, but are
not the operational authority.
