# review-team

`review-team` is a high-confidence, read-only review workflow for changes
where an independent second look is worth the coordination cost: multi-file
changes, risky refactors, or reviews requested at `high`, `xhigh`, or `max`
effort.

It separates discovery from judgment. Fresh workers first pin the review scope,
then independently look for candidates. Separate Verifiers decide whether each
candidate is supported before it can appear as a finding. The review never
edits the target, posts comments, or changes remote state.

## Choose an effort level

- `high` provides the standard independent review pipeline.
- `xhigh` adds the gap-focused Sweep after initial verification.
- `max` uses the same review topology as `xhigh`, while requesting the greatest
  controller reasoning effort.

Choose the smallest level that matches the change risk. A stronger level adds
coverage; it does not turn unverified suspicions into findings.

## What a result means

Findings are reported only after independent verification. A finding explains
the concrete failure scenario or maintenance cost and preserves the verifier's
evidence. Candidates that do not survive verification are not ordinary
findings.

An empty result can be the correct, useful outcome. It means no findings
survived independent verification; it does not certify that the reviewed
change is safe.

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
