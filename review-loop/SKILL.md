---
name: review-loop
description: Use when the user asks for a review loop or multi-round code review of completed work using external reviewer agents, when review findings keep regenerating across rounds without converging, or when a change needs adversarial review before merge.
---

# Review Loop

## North Star

> No known material defect, after the artifact has survived risk-proportionate
> independent challenge and all applicable deterministic evidence gates.

This is a qualified operational claim, never proof. Every hand-back states
what was challenged, what deterministic evidence ran, what could not run, and
which residual limitations moderate the claim (see "Hand-back" below).

## What this is

A deterministic controller (`review_loop/controller.py`) plus focused prompt
resources (`review_loop/resources/*.md`) and Python helpers. You are the
controller: drive `Controller`'s methods as a Python library, dispatch each
semantic role by rendering its resource with `review_loop/prompts.py` and
validating the raw response before it ever becomes a compact projection, and
let the deterministic helpers own sealing, gate execution, FIX containment,
and state transitions. Never hand-roll a shell state machine, invent your own
completion heuristic, or apply a semantic judgment (rating, area identity,
adjudication) yourself — that authority belongs to the dispatched role.

`review_loop/__main__.py` is a narrow, non-interactive CLI for the
mechanical edges only: `create-run` (preflight — seal the target, resolve
profile/deadline/tier *intent*), `status` (durable-stage recovery), and
`report` (write the final Markdown). It never dispatches a reviewer and never
accepts a caller-supplied canonical snapshot or artifact registry — see
`dispatch.md` for its exact request/response shapes. Stage 0 dispatch,
Round 1 review, TRIAGE, FIX, adjudication, and the final-readiness challenge
are driven by you, calling `Controller` directly, per role instructions
below.

## Invocation

Resolve, before any dispatch: target (+ optional base/head/exclusions),
optional `review_profile`, optional `max_time_seconds`, `no_confirm`, and
ground-truth sources. **Operator intent always wins** — never silently
ignore a stated tier, profile, model pin, or confirmation override, and
never silently substitute tier defaults for an invalid explicit profile.
`Controller.create_run` raises `ProfileConfirmationRequired` for that case;
ask the operator whether to proceed with tier defaults (or, non-interactively,
stop and report it — never guess).

Tier is either explicit (operator-supplied, skips rating) or automatic
(derived in Stage 0 from two `most-capable` rating samples — highest `C`,
highest `R`, one step-up if both merged axes are `high`+, a further step-up
for a validated `GESTALT: +1`, capped at `max`). **Only an *automatically
derived* `max` tier pauses for confirmation before reviewer dispatch.**
Explicit `max` and explicit no-confirmation proceed without asking. If the
operator declines or the deadline expires while awaiting confirmation, stop
without entering CLOSE — expiry takes precedence over recording a decline.

## Controller stages

```
PREFLIGHT   seal target, resolve profile/deadline/(tier intent), ground truth
STAGE0      evidence scout + gates, inventory (owner → challenge → revision),
            rating (automatic tier only), derive_policy
REVIEW      freeze roster, dispatch holistic + adversarial + eligible
            specialists (round 1: full sealed target)
TRIAGE      strict-JSON triage of every usable raw report → ledger
FIX         (only while Important+ rows are OPEN) contained mutation,
            manifest- and delta-verified, gates rerun, promote to target
CLOSE       final-readiness challenge, then the mechanical terminal rollup
```

These, plus `COMPLETE`, `INDETERMINATE`, and `CANCELLED_BEFORE_REVIEW`, are
`RunState.stage` exactly as `controller.py` sets it (`Controller.STAGES`).
Any stage that cannot complete cleanly (malformed output surviving its one
retry, a failed applicable gate, a seal mismatch, deadline expiry, an
uncontainable dispatch) makes the *stage* `INDETERMINATE` and the run
`NOT CONVERGED` — never a silent partial success.

Persisted enums you will see in canonical state: ledger `state` is exactly
one of `OPEN`, `FIX_APPLIED`, `FIX_VERIFIED`, `REFUTED`, `INTENTIONAL`.
`factual` status is `CONFIRMED`, `PLAUSIBLE`, or `UNVERIFIABLE`. Specialist
coverage is `CURRENT` or `STALE`, with no quiet counter — an eligible
Critical area is staffed every dispatched round regardless of a prior clean
report. Adjudication returns per-row `UPHOLD`, `BOUNCE`, or `UNDECIDED`.

## Safety and convergence invariants

- **Sealing is exact-comparison, whole-tree.** The target-baseline seal
  covers every path's type, mode, and content digest, not just changed
  files. Round-input and call-input seals are separate and immutable; no
  later stage extends or reuses an earlier one. Recheck the applicable seal
  immediately before *and* after every target-accessing dispatch. A mismatch
  voids the round or Stage 0, marks it `INDETERMINATE`, and is never a
  fallback condition — never dispatch against a changed tree under an old
  seal.
- **Every non-FIX target-accessing role is read-only and contained** —
  three disjoint mounts (target scope, review-data inputs, a fixed
  read-only runtime/credential allowlist) with no writable canonical state,
  peer artifact, or prior-round artifact, and a fresh non-reusable process
  identity. The prompt's read-only instruction is not the boundary; the
  execution mapping (`review_loop/execution.py`) is. If no tested mapping
  exists for a requested CLI, do not dispatch it — there is no uncontained
  bypass.
- **`FIX` is the sole mutation window**, ledger-bound to the exact current
  `OPEN` IDs, contained (`review_loop/fix.py`), and never self-delegating.
  A candidate delta is validated against the manifest before `FIX_APPLIED`,
  gates rerun on the verified post-FIX seal, and only a write-back that
  reproduces the exact verified post-FIX seal (`Controller.
  promote_post_fix_baseline`) may advance the authoritative target — a
  passing gate or an existing manifest is never itself fix verification.
- **N+1 challenge at consequential semantic gates**: the inventory owner's
  proposal is independently scope-challenged before use; every pending
  green-making disposition (`REFUTED`/`INTENTIONAL`/a downgrade below
  reviewer-stated Important+) goes through read-only adjudication
  (`run_adjudication`) with a positive proof requirement — "no contradiction
  found" is never sufficient; a fresh final-readiness challenger inspects
  the complete sealed run before CLOSE can go green. None of these three may
  themselves create readiness or settle a row merely by upholding.
- **Malformed role output gets exactly one retry**, then the enclosing stage
  is `INDETERMINATE`. Adjudication gets at most two calls total (a clean
  first pass's `UNDECIDED` subset retries once; anything else is final).
- **Tier changes effort, never completion semantics.** What counts as
  settled, what "converged" and "merge-ready" mean, and whether adjudication
  runs do not weaken at a lower tier. `CLOSE` derives both verdicts
  mechanically from canonical state (`state.py`'s kernel) — never re-judge
  them yourself.
- **Immediately before CLOSE, and again during any promotion, the
  authoritative target must reseal to the exact expected identity.** A
  mismatch is `NOT CONVERGED` — no verdict is produced for bytes no reviewer
  saw.

## Dispatching a role

For every semantic role: read its resource under `review_loop/resources/`,
render it through `review_loop/prompts.py` with the role's compact context
(never hand-interpolate), dispatch it through a tested containment mapping,
and pass the raw response through that role's strict validator before it
becomes a projection `Controller` will accept. Resource → role mapping:

| Resource | Role |
|---|---|
| `safety.md` | shared untrusted-subject boundary, included in every non-FIX prompt |
| `evidence-discovery.md` | Stage 0 evidence scout |
| `inventory.md` / `inventory-challenge.md` | inventory owner / independent scope challenger |
| `rating.md` | automatic-tier rating sample (×2) |
| `round-one.md` / `later-round.md` | round-1 full-target vs. later-round delta scope fragment |
| `review.md` | shared review dispatch/report-contract fragment |
| `holistic.md` / `adversarial.md` / `specialist.md` | the three ordinary reviewer charters |
| `triage.md` | strict-JSON triage of usable raw reports |
| `fix.md` | the sole contained implementation role |
| `adjudication.md` | read-only settlement of pending green-making dispositions |
| `final-readiness.md` | pre-CLOSE independent challenge |

Deterministic actions never belong in a prompt or in your own judgment —
call the helper: `seals.py` (target/input sealing), `evidence.py` (gate
discovery, contained gate execution, opportunistic mutation), `fix.py`
(contained FIX + candidate-delta validation), `profiles.py` (profile
resolution), `prompts.py` (render + strict per-role validators), `state.py`
(the compact-projection kernel — call it only through `Controller`/
`CanonicalStore`, never directly), `report.py` (final Markdown), and
`multi_review.py` (see below).

## Multi-review (opt-in, not default-wired)

`Controller.run_round1` accepts an optional `multi_review_dispatch`
callable that replaces the ordinary holistic slot with the caller-contained
fixed Claude+Codex pair (`review_loop/multi_review.py`), reusing the same
canonical holistic prompt verbatim. It is fully implemented and tested but
**no default caller constructs and passes it** — `run_round1` without that
argument runs ordinary single-reviewer holistic dispatch. Wire it in
yourself (construct `MultiReviewAdapter` with an OAuth credential source and
`multi_review`-profile-derived model pins) only for a `high`/`max` run where
you have accepted its disclosed residual limitations: the interim
shared-namespace containment means a compromised reviewer subprocess can see
driver transport/output and (via retained network access) exfiltrate any
mounted input or credential; the OAuth token is inherited by both fixed
clients under whole-call containment; and a reviewer winning the
post-publish race can in principle forge output that passes validation
(mitigated by teardown-race timing, not by the validator). Disclose these in
the hand-back whenever multi-review actually ran. Bubblewrap is required; an
unavailable driver, Bubblewrap, or fixed participant takes automatic
ordinary-holistic fallback (never a retry of the multi-review call) unless
the failure is itself a seal mismatch, which is `INDETERMINATE` instead.

## Confirmation behavior

Prompt only for: an automatically-derived `max` tier before reviewer
dispatch, and a missing/malformed explicitly-named profile (proceed with
tier defaults, or stop). Explicit no-confirmation changes *prompting*
only — it never authorizes dependency installation, deployment, commits, or
any other external state change. `FIX` may only ever touch the sealed
target; never install dependencies, alter manifests/lockfiles to obtain
tooling, commit, stage, deploy, or contact external systems.

## Hand-back contract

On `COMPLETE`, report both mechanical verdicts from canonical state —
`terminal_verdict` (`CONVERGED` / `NOT CONVERGED`, with the failed conjunct
named when not converged) and `merge_ready` — plus: selected policy and
tier source, planned vs. completed staffing, gate commands/results and any
evidence gaps, mutation evidence or its one-line follow-up, any
degraded/fallback behavior (including multi-review's residuals when it
ran), ledger state, and the run root (`report.generate_report` renders this
from persisted state — call the `report` CLI subcommand or the function
directly, never reconstruct it by hand). On `INDETERMINATE` or
`CANCELLED_BEFORE_REVIEW`, name the exact stage and reason and stop; do not
retry, do not fall back to a weaker path, and never claim a verdict the
ledger does not support.
