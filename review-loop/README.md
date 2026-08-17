# review-loop

A deterministic controller for multi-round external code/document review
that actually converges: reviewers find, TRIAGE verifies findings against
sources into a ledger, FIX resolves accepted findings under contained
mutation, and CLOSE computes both verdicts mechanically from the ledger —
never from a round's silence or an aggregate "looks clean."

**Core principle: a green verdict is a ledger fact, checked by code, not
asserted by an LLM.** State transitions, sealing, containment, and the two
terminal verdicts are owned by `review_loop/state.py`'s kernel and the
helpers around it; LLMs own only semantic judgment (risk identity, rating,
findings, adjudication) within resource-scoped prompts they cannot escape.

> No known material defect, after the artifact has survived risk-proportionate
> independent challenge and all applicable deterministic evidence gates.

This is a qualified operational claim, never proof — see `SKILL.md`'s North
Star and every hand-back's disclosed evidence and residual limitations.

## How it works

```
PREFLIGHT   seal target, resolve profile/deadline/tier intent, ground truth
STAGE0      evidence scout + gates, inventory (owner → challenge), rating
REVIEW      freeze roster, dispatch holistic + adversarial + specialists
TRIAGE      strict-JSON triage of every usable raw report → ledger
FIX         contained mutation, manifest- and delta-verified
CLOSE       final-readiness challenge, then the mechanical terminal rollup
```

See `SKILL.md` for the full controller contract (stages, invariants, role
dispatch, confirmation behavior, hand-back), and `dispatch.md` for execution
mappings, the `__main__.py` CLI, and troubleshooting.

## Files

- `SKILL.md` — the controller contract (the skill itself)
- `dispatch.md` — execution mappings, the CLI, troubleshooting
- `DESIGNING_PROFILES.md` — operator-facing profile schema and recipes
- `review_loop/` — the implementation: `controller.py` (orchestrator),
  `state.py` (compact-projection kernel), `artifacts.py` (canonical
  store + projection authority), `seals.py`, `evidence.py`, `fix.py`,
  `profiles.py`, `prompts.py`, `report.py`, `multi_review.py`,
  `resources/*.md` (per-role prompt resources), `__main__.py` (CLI)
- `tests/ACCEPTANCE.md` — MVP acceptance record: criteria, evidence, status
- `tests/behavior/` — RED/GREEN behavioral controls for `SKILL.md` itself
- `tests/{unit,integration,contract}/` — the deterministic suite

## Redesign and history

- [`Review Loop Redesign`](../docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md)
  — governing design; where this README or `SKILL.md` and that document
  disagree, the design governs.
- [`docs/history/review-loop/`](../docs/history/review-loop/) — archived
  decision record, prior tier-and-roster plan, and research inputs; retained
  for context, not implementation authority.
- `tests/baseline/`, `tests/adjudication/`, `tests/dispatch/`,
  `tests/state-processor/` — RED/GREEN and TDD evidence from the prior
  hand-rolled-loop and bounded-prototype implementations; retained as
  historical evidence, not a description of the current controller.

## Known limitations

See `tests/ACCEPTANCE.md` for the authoritative, evidence-linked list. In
summary: multi-round FIX/inventory-refresh/adjudication reconciliation onto
prior canonical rows is not yet wired (single-round FIX only); multi-review
is implemented and tested but not default-wired into ordinary Round 1
dispatch (opt-in, see `SKILL.md`); `__main__.py`'s `status` recovery cannot
yet distinguish `CANCELLED_BEFORE_REVIEW`/awaiting-confirmation from a
mid-Stage-0 crash; multi-review's disclosed OAuth-token-sharing and
post-publish-forge-race residuals apply whenever it runs.
