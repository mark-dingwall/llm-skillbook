# Codex panel — five-angle design review of the .ref pile (2026-07-20)

Five parallel codex runs (gpt-5.6-sol, high effort), each with a distinct
charter: (1) convergence adversary, (2) evidence/severity contract critic,
(3) triage & cross-round state, (4) rationalization-surface hunt,
(5) synthesis & simplification. 38 raw findings → deduped below. Raw
outputs archived in `codex-panel-raw/`. Cluster headers note how many
angles independently hit the issue — 4/5 agreement on the top two.

## A. SETTLED conflates "finding accepted" with "fix verified" (4/5 angles — CONFIRMED)

Round 1 accepts Important finding F; the fix is incomplete; round 2
receives F as SETTLED ("do not re-litigate") and the still-broken behavior
is suppressed unless promoted to Critical. Loop terminates green over an
open defect. The draft's own fix-manifest idea (redteam-prompt-notes)
directs round 2 to audit the fix — directly contradicting the SETTLED
prohibition.

**Fix (all four angles converge):** lifecycle states, not one bucket:
`ACCEPTED_OPEN → FIX_APPLIED → FIX_VERIFIED`. Only `REFUTED` and
`FIX_VERIFIED` enter SETTLED; `FIX_APPLIED` *creates* a mandatory
verification task for the next round.

## B. Later-round admissibility must be causal, not "no new findings" and not location-based (4/5 — CONFIRMED)

The zeroshot monotonic ratchet ("round 1 is the only round that may
introduce findings") is incoherent for a loop where each round reviews new
code: a fix can introduce a fresh Important regression that is neither a
refinement nor a withdrawal. Conversely the draft's location rule
("outside the diff → Critical only") misses the unchanged-caller case: a
fix changes a callee's return contract and an *unchanged* caller now
mishandles it — Important, outside the diff, wrongly backlogged.
(/code-review's own angle C explicitly checks unchanged callers.)

**Fix:** admissibility by provenance, with a forced artifact. Later-round
findings must declare one of:
`PROVENANCE: INCOMPLETE-FIX <id> | FIX-REGRESSION <introduced/exposed by fix diff, cite> | CRITICAL-ESCAPE <conclusive trace>`
— anything else is rejected mechanically. Keep monotonicity only for
unchanged old code: no re-litigating prior decisions.

## C. Unresolved states break both reconciliation and termination (3/5 — CONFIRMED)

- The reconciliation equation `surfaced = accepted + refuted + backlogged`
  has no bucket for NEEDS_EVIDENCE / UNVERIFIABLE / CONTESTED / UNTRIAGED
  / crashed-verification, and no defined counting unit (three reviewer
  reports of one defect: is surfaced 3 or 1? a downgraded-then-backlogged
  finding lands in two buckets). Needs separate axes: raw reports vs
  canonical findings; factual status vs severity vs scope vs lifecycle.
- Termination currently reads the *current round's yield*; it must roll up
  the *entire open ledger*. A production-only race marked UNVERIFIABLE in
  round 1 must still block green in round 4.
- Round-5 semantics: a fix applied in round 5 has no round 6 to verify it.
  Cap exhaustion with anything not verified-closed ends FAIL with a
  hand-back payload (surviving findings + fix attempts + why unresolved) —
  the loop must not "time out to green".

## D. The triager is the fix author — self-dealing on every green-making disposition (2/5 + implicit in 2 more — CONFIRMED)

The same agent writes the fixes, triages the findings, and holds sole
termination authority ("your post-triage status decides"). It can refute
with selectively favorable context, downgrade its own fix's side effects,
or launder them as INTENTIONAL — and declare convergence. Specific
sub-holes:
- **INTENTIONAL is unauthenticated retroactive amnesty:** a decision
  invented *after* a reviewer flags the behavior. Require
  `INTENTIONAL <id> AUTHORITY: <user/spec statement predating the finding>`
  — no authority, no amnesty; hand to the user instead.
- **INTENTIONAL never expires:** recorded intent survives even when a
  later fix invalidates its premise. Intent entries need their assumption
  named so a change to it forces revalidation.
- **Structural option** (if affordable): green-making dispositions
  (REFUTED / DOWNGRADED / INTENTIONAL) and final convergence require an
  independent check — e.g. one cheap read-only adjudicator pass, per
  zeroshot's split fact/rigor charters.

## E. Scope and snapshot integrity (2/5 — CONFIRMED/PLAUSIBLE)

- A laundered shared scope block poisons every reviewer identically
  (baseline chosen after partial fixes; staged/untracked files omitted) —
  and reconciliation still balances.
- Nothing binds the *final* tree to the last-reviewed state: an untracked
  file added post-review, or edits after reviewers finish, ship unreviewed.

**Fix:** seal a workspace manifest (tracked + staged + unstaged +
untracked) before and after each round; derive the round diff mechanically
from manifests; invalidate the round if the tree changes while reviewers
run; final report includes an equality check of shipped state vs last
reviewed snapshot.

## F. Pipeline health is a separate axis from finding disposition (2/5 — CONFIRMED)

- A reviewer CLI that times out, refuses, or emits garbage currently
  surfaces zero findings → indistinguishable from a clean pass → green.
  Each reviewer call needs exit-status capture, output-shape validation,
  one bounded retry; invalid output ≠ empty review; a round cannot
  conclude until required roles (holistic, adversarial) succeeded, else
  verdict INDETERMINATE.
- Reviewer under-dispatch is invisible: under budget pressure the
  orchestrator declares no area "high complexity", runs 2 reviewers, and
  truthfully reports "reviewers run: 2". Require a pre-dispatch roster
  (planned reviewers, from an explicit risk/surface inventory) and report
  planned = completed.

## G. Reviewer-contract defects (angle 2 — all CONFIRMED unless noted)

1. **Critical is undefined** — yet it is the only key that unlocks
   out-of-diff findings and SETTLED reopening. Base template's examples
   overlap Important's. Needs its own boundary (e.g. data loss / security
   breach / broken main path — "would you revert a merged release over it").
2. **CONFIRMED/PLAUSIBLE wording contradicts the /code-review ladder it
   borrows from:** a traced mechanism with an uncertain trigger is
   PLAUSIBLE per the ladder, CONFIRMED per the draft ("trace wherever
   possible"). Adopt the ladder's definition: CONFIRMED = trigger-to-wrong-
   outcome chain traced, not merely mechanism located.
3. **The blocking question is subjective without context:** identical code
   is blocking in a payment path, not in a dev tool. The scope block
   should carry deployment context / risk posture so severity is
   applicable-consistently and triage pushback has a standard.
4. **Design-finding path is exploitable:** "name a concrete future change"
   admits unlimited invented hypotheticals — the exact non-convergence
   vector. Constrain: the future change must be planned/likely (cite
   roadmap, issue, or stated goal) or the cost disproportionate.
5. **Confirmed absence findings have no evidence shape:** a verified
   missing guard has no offending file:line. Define a negative-evidence
   format: nearest anchor + the search performed (`SEARCHED: <pattern> in
   <scope> — absent`) — which also makes the claim re-runnable.
6. **The evidence contract accidentally outlaws present-cost findings**
   (duplication/maintainability with no failing scenario and no "future
   change"): re-admit concrete present cost as a third evidence currency,
   per /code-review's cleanup rules.
7. **Call-sequence ban is too absolute:** ordered external protocols
   (write → fsync → rename) ARE the observable contract when real fault
   injection is impractical. Scope the ban to *internal* implementation
   shape.
8. **Recommendations are an ungoverned escape hatch** (PLAUSIBLE): base
   template's Recommendations section bypasses the evidence contract and
   reconciliation. Either subject them to the contract or declare them
   informational-only, never actioned within the loop.

## H. Backlog contradictions (2/5 — CONFIRMED)

- A verified out-of-diff **Important** finding goes to backlog, backlog
  never triggers a round, loop terminates green — while Important is
  defined as merge-blocking. Separate the verdicts: loop convergence
  ("this change is done") vs merge-readiness ("known blockers exist,
  including backlogged ones"). The final verdict must surface backlogged
  Important+ items as unresolved blockers, not bury them.
- Backlog is unbounded and reviewer-controlled (DoS channel; "final report
  must include the backlog in full"). Cap per-reviewer backlog candidates,
  require ranking, overflow to appendix.

## I. Loop boundaries and budget (angle 5)

- **When NOT to run the loop:** requesting-code-review's "never skip
  because it's simple" would fire 5 multi-agent rounds at a one-line
  rename. Define entry tiers: skip (empty scope / failed deterministic
  quality gate — zeroshot's pre-review gate), single bounded review
  (low-risk mechanical), full loop (explicit request, or security/
  concurrency/persistence/public-contract/large changes). CONFIRMED.
- **Round cap ≠ cost cap:** reviewer count per round is unbounded ("one
  per area of high complexity"). Default ceiling (~4 reviewers round 1,
  ~2 directed thereafter); on budget exhaustion hand back state and ask.
  PLAUSIBLE.
- **receiving-code-review's global STOP is wrong for this loop:** one
  unclear Minor suggestion halts all fixes including a confirmed Critical.
  Override per-finding: unclear non-blockers → Open Questions/backlog;
  verified fixes proceed. Pause the *loop* only for ambiguous blocking
  intent, user-authority conflicts, budget exhaustion, or a blocker
  surviving two fix attempts. CONFIRMED.
- **Non-git subjects need a delta adapter:** "non-code: adapt" collides
  with the mandatory `{{ diff_range }}`. Require a snapshot ID + canonical
  inter-round delta (normalized patch / semantic diff / hash), else limit
  to one round. CONFIRMED.

## J. Identity, ledger, recurrence (angle 3 + 1 — PLAUSIBLE)

- No stable finding identity across reviewers/rounds: assign canonical IDs
  at ingestion; reviewer reports are aliases; record refines/duplicates/
  supersedes and fix-attempt links. (Prerequisite for A, B, C, D above —
  nearly every fix in this digest presumes IDs exist.)
- No durable round state: crash mid-triage loses verdicts and restarts
  non-convergence. Persist an append-only ledger; checkpoint each phase
  with tree OIDs.
- Semantic recurrence: fix B by reverting fix A → settled failure A is
  reachable again but suppressed as re-litigation. Prior failing scenarios
  reactivate when reachable; an A→B→A oscillation triggers early
  non-convergence hand-back.

## K. Angle 5's minimal-core proposal (PLAUSIBLE, but a good starting frame)

Six-stage kernel: `quality/scope gate → bounded round-1 review →
finding ledger + independent-ish triage → fix/test → diff + fix-manifest
directed re-review → pass or unresolved hand-back`.
- **Load-bearing:** immutable scope; evidence-bearing findings; stable
  IDs; explicit remediation states; diff-scoped directed re-review;
  backlog; deterministic reconciliation; fail-closed cap.
- **Risk-activated extras:** one specialist lens, state-space enumeration,
  changed-test scrutiny, twin search, authority order, one gap sweep.
- **Cut from v1:** split fact/rigor verifier agents, unanimous
  multi-verifier approval, junior/senior classifier escalation, exhaustive
  angle fan-out, repeated gap sweeps, mandatory Strengths/Recommendations
  sections, the monotonic finding-set rule (superseded by B), the global
  stop-on-unclear rule (superseded by I).

## Panel stats

38 raw findings → 11 clusters. Independent multi-angle agreement: cluster
A (4/5), B (4/5), C (3/5), D/E/F/H (2/5 each). No angle returned "no
material findings"; no finding was refuted by a sibling angle.
