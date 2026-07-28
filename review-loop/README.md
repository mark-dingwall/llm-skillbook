# review-loop

A Claude Code skill for multi-round external code review that actually
converges. Born from hand-rolled review loops that ran a dozen rounds
re-litigating the same findings; this skill makes termination a ledger
fact instead of a vibe.

**Core principle: a green verdict is a ledger fact. The loop cannot
time out, crash, scope-trick, or backlog its way to green.**

## How it works

```
0 GATE    quality gate, entry check, SCOPE seal, ROSTER
1 REVIEW  dispatch external CLI reviewers   (round 1: full scope; ≥2: fix diff)
2 TRIAGE  verify findings against sources → LEDGER
3 FIX     fix accepted findings, FIX MANIFEST (with TWINS searches)
4         back to 1                                        (cap 5 rounds)
5 CLOSE   deterministic rollup → two verdicts + hand-back
```

The rules live inside **seven forced artifacts** (seal, roster,
evidence contract, ledger, fix manifest, provenance line, close
rollup) rather than prose checklists — an executor that must fill a
field can't skip the rule it encodes. Reviewers are external CLIs
(e.g. codex) run with per-reviewer charters; a read-only adjudicator
subagent audits every green-making disposition; the close computes
**two verdicts** (convergence and merge-readiness) from the ledger
alone. Reaching the round cap with open Important+ findings produces
an honest NOT CONVERGED hand-back, never a forced green.

## Files

- `SKILL.md` — the protocol (the skill itself)
- `reviewer-addendum.md` — the prompt contract given to each reviewer
- `dispatch.md` — operational how-to: waiting, timeouts, harvest, concurrency
- `DESIGN.md` — decision record; every rule traces to a source or a cut
- `tests/baseline/` — trap fixtures + RED/GREEN results (TDD evidence)
- `REVIEW-2026-07-20.md` — the skill's 10-round review of itself
- `.ref/` — mined sources (Claude Code /code-review internals, zeroshot,
  fable-method, superpowers skills, codex design panel)

## Provenance

Built TDD-style per superpowers:writing-skills: baseline trap
scenarios were run against agents *without* the skill (RED), the
skill was written to fix the observed failures (GREEN), and
regressions re-checked at two model tiers. It was then hardened by
reviewing **itself** through ten rounds of its own loop with external
codex reviewers — 18 canonical findings, 16 verified fixed, raw
findings converging 29 → 5 as whole attack families (workspace
sealing, authority authentication, completion gaming) were closed
structurally. Several dispatch rules were adopted from real-world
failure reports from a production hand-rolled loop.

## Known limitations / backlog

- **GNU userland is assumed** (`sha256sum`, GNU `stat -c`, `sort -z`,
  `xargs -0 -r`). Fine for the current single-user MVP; a platform
  contract and an explicit fail-closed rule for a failed seal leg are
  backlogged for any wider deployment (macOS/BSD would need
  substitutes).
- The self-review closed at round 11 (hard stop): 17/18 findings
  verified fixed; the last row (an errexit guard on the expiry
  signals) is applied and probe-tested but has no verifying review
  round (`REVIEW-2026-07-20.md` §Round 11).
- **Loop artifacts need durable storage, not tmpfs** — two host
  restarts each wiped the loop's /tmp working files mid-run;
  dispatch.md guidance backlogged.
- **Adjudication has never fired in live use** (no round produced a
  refutation/downgrade/INTENTIONAL to audit) — but it is now
  fixture-tested: `tests/adjudication/` (four planted dispositions +
  crash-handling) and `tests/dispatch/` passed GREEN at sonnet and
  haiku tiers (see the RESULTS.md files).
- B3 remainder: fixtures still owed for seal/manifest checks,
  FIX-AUDIT promotion enforcement, INTENTIONAL close semantics, and
  roster scoping (2026-07-21 rule: honest scoping, no numeric cap, >8
  needs user confirmation unless `--force`, concurrency
  `min(10, cpu_cores - 2)` — RED evidence is the first real-world run's
  under-scoped roster, recorded in that run's SCOPE-ROSTER.md; GREEN
  fixture not yet run).
- PID-reuse race in long waits: real mechanism, judged below the
  finding bar for this deployment; revisit if rounds ever run hours.
