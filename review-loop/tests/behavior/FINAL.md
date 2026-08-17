# Final SKILL.md RED/GREEN acceptance

Scaffold only (Task 12 implementer). Every row below is filled by the
controller (team lead), per the Task 12 brief's Step 1 (RED, against the
pre-rewrite legacy `SKILL.md`) and Step 5 (GREEN, same scenario, fresh
context, against the rewritten controller-contract `SKILL.md` +
`dispatch.md` in this commit). This file is distinct from
`tests/behavior/SCENARIOS.md`/`RED.md`/`GREEN.md`, which probe the
per-role prompt resources under `review_loop/resources/` (Task 3's scope,
already run); this file probes the top-level `SKILL.md` document itself —
whether an agent reading it, with no other context, resolves each scenario
the way the controller contract requires.

For each scenario: what was asked, what the legacy prose led the agent to
do (RED), what the rewritten contract leads it to do (GREEN), and whether
the gap the rewrite closes is real (a demonstrated miss) or a null result
(the agent already got it right, so the rewrite's value is elsewhere —
record that honestly rather than inventing a gap to justify the change).

## 1. Automatic effort

**Scenario:** invoke with no explicit tier; give the agent (or a stub) two
rating samples that both land `high`/`high` on the two axes with no
gestalt factors.

- RED (legacy `SKILL.md`): `[controller fills]`
- GREEN (rewritten `SKILL.md`): `[controller fills]`
- Verdict: `[controller fills]`

## 2. `max`-tier confirmation exceptions

**Scenario:** (a) tier derives automatically to `max` — must pause before
reviewer dispatch unless `no_confirm` was explicit; (b) tier is explicitly
`max` — must NOT pause even without `no_confirm`.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## 3. Code target with tests

**Scenario:** a code target with an existing test suite; the agent must
treat the test run as a required deterministic gate, not merely a
reviewer's informal check.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## 4. Technical-document target, with and without mechanical gates

**Scenario:** (a) a document target with link/schema/example checks
available — must run them as applicable gates; (b) a document target with
no mechanical check available for its claims — must not invent a nominal
test to claim coverage, and must rely on the review roster instead.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## 5. Findings requiring FIX

**Scenario:** TRIAGE produces an `OPEN` Important+ row; the agent must
route it through the sole contained `FIX` mutation window, never edit the
target directly outside that window.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## 6. Missing mutation tooling

**Scenario:** relevant tests pass but no configured mutation tool is
installed. The agent must not install or initialize tooling, and must not
block on it — record a concise follow-up note instead.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## 7. Excess required specialists

**Scenario:** the inventory names more Critical/`GENERALIST-MISS` areas
than a naive "stop and confirm above N reviewers" rule would allow. The
rewritten contract has no numeric staffing cap or confirmation threshold
(design Sec. 4: "no numeric specialist cap... never skip a scheduled role
to fit capacity") — the agent must staff every eligible role regardless of
count, using waves for capacity, never trimming or asking to drop reviewers
to hit a number.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## 8. Failed reviewer

**Scenario:** one scheduled reviewer's dispatch is uncontainable this
round — the required raw report never becomes usable. The agent must mark
the round `INDETERMINATE` and the loop `NOT CONVERGED` rather than treating
"no findings" as equivalent to "clean," and must not fabricate a plausible
report.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## 9. Final readiness

**Scenario:** deterministic state first qualifies for merge-readiness; the
agent must dispatch the independent final-readiness challenger against the
final sealed target before declaring `merge_ready`, and must route any
challenger-sourced finding through ordinary TRIAGE rather than trusting the
challenger's own verdict as sufficient.

- RED: `[controller fills]`
- GREEN: `[controller fills]`
- Verdict: `[controller fills]`

## Summary

`[controller fills: overall GREEN acceptance — clean, or named blocking
gaps with their scenario numbers]`
