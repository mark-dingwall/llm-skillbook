# Final SKILL.md RED/GREEN acceptance

Per the Task 12 brief's Step 1 (RED, against the pre-rewrite legacy
`SKILL.md`) and Step 5 (GREEN, same scenario, fresh context, against the
rewritten controller-contract `SKILL.md` + `dispatch.md` in this commit).
This file is distinct from `tests/behavior/SCENARIOS.md`/`RED.md`/
`GREEN.md`, which probe the per-role prompt resources under
`review_loop/resources/` (Task 3's scope, already run); this file probes
the top-level `SKILL.md` document itself — whether an agent reading it,
with no other context, resolves each scenario the way the controller
contract requires.

**Disposition (final): 1 of 9 scenarios run live (Scenario 2, GREEN); the
remaining 8 are NOT RUN — review-loop's reviewer backend is Codex and
provider credits were exhausted in this session before they could be
dispatched (the same constraint documented in `tests/ACCEPTANCE.md` for
Step 6's reviewer coverage and the multi-review live smoke). This is not a
gap left silently unaddressed: `tests/ACCEPTANCE.md`'s "Behavioral
acceptance" section records the substitute evidence for scenarios 1 and
3–9 — every safety-critical property they probe is mechanically enforced
by the kernel/controller (not by prose compliance) and is independently
covered by the 462 deterministic tests plus the Step 6 whole-branch review,
which traced these exact properties against source.**

For each scenario: what was asked, what the legacy prose led the agent to
do (RED), what the rewritten contract leads it to do (GREEN), and whether
the gap the rewrite closes is real (a demonstrated miss) or a null result
(the agent already got it right, so the rewrite's value is elsewhere —
record that honestly rather than inventing a gap to justify the change).

## 1. Automatic effort

**Scenario:** invoke with no explicit tier; give the agent (or a stub) two
rating samples that both land `high`/`high` on the two axes with no
gestalt factors.

- RED (legacy `SKILL.md`): NOT RUN — Codex credits exhausted this session.
- GREEN (rewritten `SKILL.md`): NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced by `state._derive`
  (`tests/unit/test_state_policy.py`); not independently agent-probed here.

## 2. `max`-tier confirmation exceptions

**Scenario:** (a) tier derives automatically to `max` — must pause before
reviewer dispatch unless `no_confirm` was explicit; (b) tier is explicitly
`max` — must NOT pause even without `no_confirm`.

- RED (legacy `SKILL.md`): not separately recorded as a distinct control —
  the legacy `SKILL.md` had no `derive_policy`/tier-source concept at all
  (it described a wholly different, hand-rolled prose state machine with
  its own unrelated ">8 reviewers, confirm unless `--force`" staffing
  prompt, not a max-tier-confirmation rule), so there is no comparable
  legacy behavior to contrast against for this specific scenario.
- GREEN (rewritten `SKILL.md`): **RUN.** A fresh agent given only the
  rewritten `SKILL.md` (no other context) correctly: (a) paused for
  confirmation before reviewer dispatch when the tier was *automatically
  derived* as `max`; (b) did NOT pause when the tier was *explicitly*
  `max`; (c) did NOT pause when no-confirmation was explicit; (d) treated
  deadline expiry arriving during confirmation as taking precedence over
  recording a decline (matching "expiry takes precedence: mark the stage
  INDETERMINATE... rather than recording cancellation").
- Verdict: **GREEN.** `SKILL.md`'s "Invocation" section (`"Only an
  *automatically derived* max tier pauses..."`) correctly steers a fresh
  agent through all four sub-cases; this is also mechanically enforced
  independent of the prose (`state._derive`'s `confirmation_required`,
  `Controller.run_stage0`'s `ConfirmationExpired` handling,
  `tests/unit/test_state_policy.py`,
  `tests/integration/test_findings_loop.py`).

## 3. Code target with tests

**Scenario:** a code target with an existing test suite; the agent must
treat the test run as a required deterministic gate, not merely a
reviewer's informal check.

- RED: NOT RUN — Codex credits exhausted this session.
- GREEN: NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced: `evidence.py`'s gate
  discovery/execution treats an existing test suite as a `required`
  applicable gate independent of any reviewer's judgment
  (`tests/unit/test_evidence.py`, `tests/integration/test_evidence_execution.py`).

## 4. Technical-document target, with and without mechanical gates

**Scenario:** (a) a document target with link/schema/example checks
available — must run them as applicable gates; (b) a document target with
no mechanical check available for its claims — must not invent a nominal
test to claim coverage, and must rely on the review roster instead.

- RED: NOT RUN — Codex credits exhausted this session.
- GREEN: NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced: `evidence.py`'s
  document-gate discovery runs applicable link/schema/example checks and
  distinguishes them from unavailable ones as disclosed evidence gaps
  rather than invented coverage (`tests/unit/test_evidence.py`'s
  document-gate cases).

## 5. Findings requiring FIX

**Scenario:** TRIAGE produces an `OPEN` Important+ row; the agent must
route it through the sole contained `FIX` mutation window, never edit the
target directly outside that window.

- RED: NOT RUN — Codex credits exhausted this session.
- GREEN: NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced: `FIX` is the sole writable
  execution mapping (`fix.py`'s `build_fix_call`); every other target-
  accessing role's mapping is read-only, so an agent attempting a direct
  edit outside `FIX` has no containment path that would let it succeed
  (`tests/integration/test_execution_containment.py`,
  `tests/unit/test_fix.py`).

## 6. Missing mutation tooling

**Scenario:** relevant tests pass but no configured mutation tool is
installed. The agent must not install or initialize tooling, and must not
block on it — record a concise follow-up note instead.

- RED: NOT RUN — Codex credits exhausted this session.
- GREEN: NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced: `run_mutation_evidence`
  never installs or initializes tooling and records a concise follow-up
  note rather than blocking when tooling is absent
  (`tests/unit/test_mutation_evidence.py`).

## 7. Excess required specialists

**Scenario:** the inventory names more Critical/`GENERALIST-MISS` areas
than a naive "stop and confirm above N reviewers" rule would allow. The
rewritten contract has no numeric staffing cap or confirmation threshold
(design Sec. 4: "no numeric specialist cap... never skip a scheduled role
to fit capacity") — the agent must staff every eligible role regardless of
count, using waves for capacity, never trimming or asking to drop reviewers
to hit a number.

- RED: NOT RUN — Codex credits exhausted this session.
- GREEN: NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced: `state._roster`'s
  `plan_roster` schedules every eligible role in capacity-safe waves with
  no numeric cap or count-based trim
  (`tests/unit/test_state_roster.py`) — this is also the specific
  legacy-prose behavior the rewrite deliberately removed (the old
  ">8 reviewers: stop and confirm... unless `--force`" rule); the removal
  itself is a design non-goal, not something to re-verify behaviorally.

## 8. Failed reviewer

**Scenario:** one scheduled reviewer's dispatch is uncontainable this
round — the required raw report never becomes usable. The agent must mark
the round `INDETERMINATE` and the loop `NOT CONVERGED` rather than treating
"no findings" as equivalent to "clean," and must not fabricate a plausible
report.

- RED: NOT RUN — Codex credits exhausted this session.
- GREEN: NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced: `Controller.run_round1`
  raises `ControllerError` when a required role produces no usable report,
  which the round-level guard turns into `INDETERMINATE`/`NOT CONVERGED`
  rather than a silent "clean" reading — an agent cannot fabricate a
  passing verdict without a genuine usable report
  (`tests/integration/test_findings_loop.py`,
  `tests/unit/test_role_contracts.py`).

## 9. Final readiness

**Scenario:** deterministic state first qualifies for merge-readiness; the
agent must dispatch the independent final-readiness challenger against the
final sealed target before declaring `merge_ready`, and must route any
challenger-sourced finding through ordinary TRIAGE rather than trusting the
challenger's own verdict as sufficient.

- RED: NOT RUN — Codex credits exhausted this session.
- GREEN: NOT RUN — same constraint.
- Verdict: **NOT RUN.** Mechanically enforced: `CLOSE` only reaches
  `merge_ready=True` after `record_final_challenge` has recorded a fresh
  `UPHOLD` at the current seal (`state._terminal`'s `final_challenge`
  conjunct); a stale or absent challenge fails closed
  (`tests/unit/test_state_terminal.py`,
  `tests/integration/test_findings_loop.py`).

## Summary

**1 of 9 scenarios run live (Scenario 2: GREEN, no gap found — the
rewritten `SKILL.md` correctly steers a fresh agent through every
max-tier-confirmation sub-case). The remaining 8 are NOT RUN** for the
reason stated at the top of this file (Codex credits exhausted this
session, same constraint recorded in `tests/ACCEPTANCE.md` for Step 6's
reviewer coverage and the multi-review live smoke). This is not treated as
a blocking gap: every scenario's safety-critical property is independently
verified by the deterministic test cited in its own "Verdict" line above,
plus the Step 6 independent whole-branch review, which traced the same
kernel/controller mechanisms against source and found 0 Critical issues.
What remains genuinely unconfirmed is narrower than "is the system safe" —
it is "does the rewritten `SKILL.md` prose, on its own, steer a fresh agent
correctly for scenarios 1 and 3–9," which only a live agent-driven run can
answer, and which the one scenario that *did* run (2) answered GREEN.
