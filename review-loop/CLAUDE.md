# review-loop maintainer contract

## Authority and operating sources

[SKILL.md](SKILL.md) is the shipped controller contract. [dispatch.md](dispatch.md)
owns execution mappings and CLI mechanics; [DESIGNING_PROFILES.md](DESIGNING_PROFILES.md)
owns the profile schema. Keep these sources aligned with the controller. Do
not make installed operation depend on repository documentation, tests, or
historical records, because they are not part of the copied skill payload.

Deterministic code owns canonical state, artifact references, transitions,
seals, gate rollups, containment checks, and terminal verdicts. Semantic roles
own only their scoped judgments: evidence discovery, area identity, rating,
findings, triage, adjudication, and final challenge. A role response becomes
canonical only after its prompt-specific strict validation; never hand-author
a projection, registry entry, or completion heuristic to advance a run.

## Seals, evidence, and containment

Seal the complete target identity before work begins. Target, input, and
round-input seals are separate immutable identities; do not extend, reuse, or
replace one after dispatch. Recheck the applicable identity around every
target-accessing action. Drift voids the affected work and makes the run
indeterminate; it is never an excuse to dispatch against changed bytes or to
fall back to a weaker path.

Every non-FIX target-accessing role runs read-only through a tested containment
mapping with only its sealed subject, declared review inputs, fixed runtime
allowlist, and fresh process identity. Prompt instructions are not a security
boundary. If no tested mapping exists, stop rather than improvise a subprocess.
Gate execution has its own constrained mapping and must not install tooling.

TRIAGE must account for every usable raw report and its exact finding inventory
before the ledger changes. Never omit an inconvenient report, create a finding
without its source evidence, or treat a reviewer’s silence as settlement.

## Mutation and green-making decisions

FIX is the only mutation window. It is bound to the current open ledger IDs,
works in a contained disposable copy, validates the candidate manifest and
delta, reruns the applicable gates, and can reach the authoritative target
only through exact post-FIX promotion. A passing gate, an existing manifest,
or a disposable-copy result alone does not verify or promote a fix.

Any disposition that can make a finding green — including refutation,
intentional acceptance, or a downgrade below the reviewer’s materiality —
needs independent, positive, seal-bound adjudication. "No contradiction
found" is not proof. Adjudication can uphold, bounce, or leave a decision
undecided; it cannot create readiness by itself. A fresh final-readiness
challenge is also required before CLOSE. CLOSE derives verdicts mechanically
from canonical state and a fresh authoritative-target reseal; it must reject
drift and any verified fix that was not promoted.

## Policy, profiles, and failure behavior

Tiers change effort and staffing, never the meaning of settlement,
convergence, or merge-readiness. An automatic `max` tier requires confirmation
before reviewer dispatch; an explicit tier and explicit no-confirmation do not
introduce a confirmation prompt. Deadline expiry stops the run rather than
creating a terminal verdict.

Profiles may refine bounded dispatch settings but cannot change safety,
convergence, role policy, round limits, or participants. A missing or malformed
explicitly selected profile requires an operator decision to use defaults; do
not silently substitute defaults or model pins.

Malformed semantic output gets its defined retry and then stops the enclosing
stage indeterminate. Preserve fail-closed boundaries that are not yet wired:
later-round ledger reconciliation, inventory refresh, and baseline advancement
must not be simulated; a final-readiness block has no supplemental-TRIAGE
implementation; and some cancellation/confirmation outcomes are not durable
enough for `status` recovery to distinguish them.

## Multi-review

Multi-review is an explicit host-supplied replacement for the ordinary
holistic slot, never the default path. Restrict it to an accepted high/max
use case with the configured fixed pair and disclosed residuals. Driver,
Bubblewrap, participant, or aggregate-validation unavailability takes the
ordinary holistic fallback once; a target or input-seal mismatch is
indeterminate and must not fall back. Preserve the distinct whole-call
containment model and its credential-sharing and post-publication race
residuals in any hand-back that actually uses multi-review.
