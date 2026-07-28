# review-loop — crystallized design (decision record)

The spec the skill is written against, and the source tests are derived
from. Each decision resolves the sources in `.ref/`; conflicts are decided
here, once. Guiding constraint: an executor juggling forty rules fails
like Meshugah — so the skill is organized around **seven mandatory
artifacts**, not rule lists. Each artifact is a forced output tied to an
action in hand (the form fable-method measured as transferring 4/4, vs
~0/4 for prose); the rules live inside the artifacts' required fields.

## The loop

```
0 GATE    quality gate + entry tier + scope seal
1 REVIEW  dispatch roster (round 1: full scope; ≥2: diff + fix manifest)
2 TRIAGE  verify findings against sources → ledger
3 FIX     fix accepted findings, re-run quality gate, fix manifest
4 REPEAT  from 1, directed re-review           (cap 5 rounds)
5 CLOSE   deterministic rollup → verdicts + hand-back
```

## The seven artifacts

**1. SCOPE seal** (per round, before dispatch). Diff command + base/head
identifiers, full workspace state (tracked, staged, unstaged, untracked),
subject vs ground-truth file split, deployment context (what this code is
for — feeds severity judgment). Tree frozen while reviewers run; a change
voids the round. The content identity is command-defined and
WHOLE-TREE (the subject list selects what is reviewed, never what is
sealed) — verbatim output of command-defined legs, NUL-safe
(`-print0 | sort -z | xargs -0` — word-splitting drops pathnames):
`find` enumeration (minus `.git`, every path incl. directories,
sorted), `sha256sum` over every regular file (`absent` for deleted
tracked paths), `stat -c '%n %a %F'` over every path, `stat -c '%N'`
per symlink with `env QUOTING_STYLE=shell-escape-always` pinned in
the command (quote-escaped `'link' -> 'target'` records — targets
bound, no delimiter collisions regardless of inherited
environment), `git
ls-files -s` (whole index; empty for non-git); out-of-tree
ground-truth files hashed too. CLOSE re-runs them all and requires
byte-identical output. Loop artifacts (ledger, prompts, manifests,
reports) live outside the sealed tree — an in-tree loop artifact
voids its own round. Base/head + subject set come from the
user's request (verbatim when stated; inferred → recorded, larger scope
preferred, echoed in the final report). Rounds ≥2 the seal carries an
`INTENTIONAL-CHECK <id>: held|invalidated` line per INTENTIONAL row;
reconciliation fails without them.
*Carries: shared scope block, laundered-scope defense, frozen tree,
snapshot-equality (clusters E, panel A5#8).*

**2. ROSTER** (before dispatch, round 1). A cheap read-only subagent
skims the sealed scope first and returns a **risk-surface inventory**:
named areas with a one-line why (money handling, auth surface,
concurrency, persistence/migrations, public contracts, …). Fresh eyes on
purpose — the orchestrator often wrote the code and underrates its own
footguns, and a pre-committed inventory stops budget pressure from
quietly deciding "nothing here is complex". The roster then follows the
formula: holistic + adversarial + one specialist per inventory area,
honestly scoped with no numeric cap — >8 reviewers needs user
confirmation unless `--force`; concurrency capped at
`min(10, cpu_cores - 2)` (was "cap 4" until 2026-07-21: user authority,
after the cap plus a stale reviewer-cost model under-scoped the first
real-world roster — cheap reviewers change fan-out economics, not
coverage honesty; rounds ≥2 default 2). Every inventory area maps to a
specialist charter or an explicit "not covered because" line — no numeric
complexity scale, areas are the unit. Round can't close until every planned reviewer
*succeeded* — CLI failure/garbage output is a failed reviewer, retried
once, else verdict INDETERMINATE. Report states planned = completed.
*Carries: under-dispatch defense, pipeline-health-≠-finding-disposition,
fail-closed on reviewer crash (cluster F).*

**3. Evidence contract** (inside every reviewer prompt; per finding).
Failing scenario (or concrete present cost, or planned-change design
cost), confidence, refutation attempt. Definitions fixed:
- **Critical**: data loss, security breach, or broken main path — you'd
  revert a merged release. **Important**: you'd block this merge alone.
  **Minor**: recorded, non-blocking.
- **CONFIRMED** = trigger-to-wrong-outcome chain traced in source.
  Mechanism traced but trigger uncertain = **PLAUSIBLE** (say what would
  confirm). (Adopts the /code-review ladder; fixes draft contradiction.)
- Absence findings: nearest anchor + `SEARCHED: <pattern> in <scope> —
  absent` (re-runnable negative evidence).
- Test findings: could a plausible wrong implementation pass? Boundary
  behaviour, not implementation shape — but ordered *external* protocols
  (write→fsync→rename) are boundary contracts, not internal sequence.
- Do not pad; "no material issue in <area>" is a valid result. No
  Strengths section required. Recommendations are informational only —
  never actioned inside the loop.
*Carries: evidence bars, severity boundaries, absence shape, present-cost
currency, scoped call-sequence rule, anti-padding (clusters G, A2 all).*

**4. LEDGER** (the loop's single state object; updated at triage; replaces
SETTLED/INTENTIONAL lists — those are derived views). One row per
canonical finding: `id | severity (reported→current) | finding | factual:
CONFIRMED/PLAUSIBLE/UNVERIFIABLE | state: OPEN/FIX_APPLIED/FIX_VERIFIED/
REFUTED/BACKLOGGED/INTENTIONAL | provenance | evidence`. (Aligned
2026-07-20 to SKILL.md, the operative schema: REFUTED is a state,
PLAUSIBLE is a factual value, reported severity is preserved so
ingestion-time downgrades are visible to adjudication.) Rules baked into
the fields:
- Reviewer reports are aliases merged by reference into canonical IDs.
- Settled = REFUTED or FIX_VERIFIED only. FIX_APPLIED *creates* next
  round's verification task — it is not settled.
- INTENTIONAL requires `AUTHORITY: <user/spec statement predating the
  finding>` + the assumption it rests on; sole predate exception:
  direct user confirmation after the fact (risk acceptance is the
  user's prerogative). No authority → stays OPEN or goes to the user.
- UNVERIFIABLE Important+ rows are never assumed true or resolved: while
  OPEN they block convergence, and at close they block merge-readiness.
- Downgrade over discard: real-but-overstated findings are re-ranked, not
  rejected. Severity changes and refutations of Important+ need quoted
  evidence in the row — the triager wrote the fixes; its green-making
  claims must be independently checkable from the row alone.
*Carries: lifecycle split (cluster A), identity/merge-by-reference (J),
disposition axes (C), INTENTIONAL authority + expiry-by-assumption (D),
DOWNGRADE-over-REJECT, judge-by-diff-not-report.*

**5. FIX MANIFEST** (after fixing, before re-dispatch). Per fix:
`finding-id → what changed → files touched → TWINS: searched <pattern> —
<n> sites`. Any changed test justified by spec trace (changed-test is
guilty until traced). Scope creep = files touched beyond what findings
named — declare or revert.
*Carries: directed re-review, fix-diff fraud catalogue, twin sweep
(redteam #1, fable #2/#8/#11).*

**6. PROVENANCE line** (every round ≥2 finding). One of:
`INCOMPLETE-FIX <id>` | `FIX-REGRESSION <introduced/exposed by the fix
diff — cite, even if the failing line is unchanged>` | `CRITICAL-ESCAPE
<conclusive trace>`. Anything else → backlog candidate, mechanically. Old
decisions aren't re-argued on old evidence; new defects in new code are
always admissible. A settled finding whose failure becomes reachable
again reactivates, and conclusive new evidence against a REFUTED row
reopens it the same way (both are INCOMPLETE-FIX descendants); an A→B→A
oscillation ends the loop early as non-convergence.
*Carries: causal admissibility (cluster B — supersedes zeroshot's
monotonic ratchet), unchanged-caller case, recurrence rule (J).*

**7. CLOSE rollup** (deterministic, from the ledger — never re-judged).
- **Converged** iff no Important+ row is OPEN or FIX_APPLIED, all
  planned reviewers succeeded, the recomputed content identity equals
  the last seal, and reconciliation passes (reports mapped, rows
  stated, INTENTIONAL-CHECK lines present). (BACKLOGGED and authorized INTENTIONAL rows
  don't block convergence; BACKLOGGED and UNVERIFIABLE Important+ block
  merge-readiness, while authorized INTENTIONAL rows are listed as
  exceptions with their authority, not blockers.) Current-round
  yield never decides; the whole ledger does.
- CLOSE is total: any failed CONVERGED conjunct (including identity
  mismatch) → **NOT CONVERGED**. Cap 5 / oscillation / budget exhaustion
  with open Important+ rows are the common cases. Hand-back: failed
  conjunct, surviving rows, fix attempts, why unresolved, current
  hypothesis. The loop cannot time out to green.
- Two verdicts: *convergence* (loop done) and *merge-readiness*
  (backlogged Important+ are surfaced as known blockers — backlog never
  hides a merge-blocker).
- Reconciliation: every raw reviewer report maps to a canonical row;
  every row has a state (OPEN Minors may remain at close, listed);
  counts printed.
- Backlog: per-reviewer cap (5), ranked, in the final report.
*Carries: ledger rollup, unresolved-at-cap==FAIL, hand-back payload,
dual verdict (clusters C, H), reconciliation (fixed counting units).*

## Stage 0 decisions

- Quality gate first: build/lint/tests must pass before any review spend.
- Entry tiers: trivial/mechanical change → single review or none (say
  which and why); full loop for explicit request or risky surface
  (security, concurrency, persistence, public contracts, large change).
- Reviewer command is a parameter; default is the user's codex invocation.
  Prompts via temp file, never hand-interpolated.
- Subject must yield a sealable snapshot + inter-round delta. Non-git
  subjects: normalized snapshot files under the seal; if no trustworthy
  delta exists, single round only.
- Dispatch mechanics (adopted 2026-07-20 from live-loop operational
  feedback; how-to in `dispatch.md`; hardened round 7): reviewers
  write final reports to per-reviewer files named in the prompt and
  located outside the sealed tree — that file is the
  completion-contract region, stdout is never harvested; waits are
  PID-based with the whole-round wall-clock ceiling enforced inside
  the wait predicate (on expiry: bounded best-effort cleanup,
  survivors recorded UNREAPED, then INDETERMINATE — never block);
  timeouts sized to scope with chosen value + observed durations
  recorded; contention-aware triage (a clean serial re-run alone
  refutes nothing — REFUTED needs evidence isolating contention as
  cause); test-bite checks mutate a throwaway copy, never the sealed
  tree, and never by disabling fixtures.

## Deliberate cuts (chosen against sources)

| Cut | From | Why |
|---|---|---|
| Split fact/rigor verifier agents, unanimous multi-verifier approval | zeroshot | Ledger evidence fields + the (mandatory, user-decided) per-round adjudication pass carry the value at far less machinery |
| Junior/senior classifier escalation, risk-matrix tiering | zeroshot | Entry tiers + roster cover it; a skill executor can judge risk directly |
| Monotonic finding-set ratchet | zeroshot | Incoherent for new-code rounds; superseded by PROVENANCE |
| 8-10 finder-angle fan-out, repeated gap sweeps | /code-review | Roster of ≤4 chartered reviewers; external CLIs are already diverse; one optional sweep at most |
| Mandatory Strengths section | superpowers template | Padding pressure; verdict + evidence is the product |
| receiving-code-review's global STOP-on-unclear | superpowers | Per-finding: unclear non-blockers → Open Questions/backlog; verified fixes proceed; pause loop only for user-authority conflicts, budget, or a blocker surviving two fix attempts |
| Durable crash-recoverable state machinery | panel J | The LEDGER lives in one working file; that's enough for a skill |
| Review lens / severity-downgrade-policy parameter | earlier drafts | User dropped it; deployment context in the SCOPE seal does the honest part |
| CLI-specific stdout extraction rules (banner/`tokens used` parsing), concurrent-suite-runner caps | live-loop feedback 2026-07-20 | File-based harvest makes the contract region exact — parsing traces is the failure mode, not the fix; contention is handled by prompt guidance + cause-isolating refutation at triage, not orchestration limits |

## Adjudication (user-decided 2026-07-20)

Green-making dispositions on Important+ rows (REFUTED, downgrade,
INTENTIONAL) are checked by **one read-only session-model subagent per
round**: it gets those ledger rows with source locators (including an
inspectable locator for any claimed AUTHORITY — file-based only:
conversation-only authority is not adjudicable and goes to the user,
whose confirmation makes the row INTENTIONAL directly, recorded as
`AUTHORITY: user-confirmed this loop`; after invalidation, re-disposal
follows the row's authority route — file authority re-enters
adjudication, user-confirmed authority returns to the user for a fresh
quoted confirmation)
and reads the sources itself, hunting for context that cuts against
each disposition — never judging triager-selected excerpts alone. A
pass counts only if it finishes cleanly with well-formed output;
decisions from a crashed pass are all discarded and the pass re-runs
once in full. A clean pass's decisions are kept (a bounce is final for
the round); undecided rows get one rerun, then bounce; a second failed pass
bounces every pending reprieve — never a third run (fail closed). A
bounce restores the full row. Revalidation = revert to OPEN, then
re-dispose via the row's authority route (file → adjudication;
user-confirmed → the user). The adjudicator never reviews
the whole subject — it audits the triager's reprieves, nothing else.
