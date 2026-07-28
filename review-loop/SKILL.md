---
name: review-loop
description: Use when the user asks for a review loop or multi-round code review of completed work using external reviewer agents, when review findings keep regenerating across rounds without converging, or when a change needs adversarial review before merge.
---

# Review Loop

## Overview

Multi-round external review that actually converges. Reviewers find; you
triage against sources; fixes get re-reviewed; the loop ends on what the
ledger says, never on a round's silence.

**Core principle: a green verdict is a ledger fact. The loop cannot time
out, crash, scope-trick, or backlog its way to green.**

## When to use

- The user asks for a review loop on completed work (code or documents).
- NOT for: trivial/mechanical changes (run a single review, or none — tell
  the user which and why); code that fails build/lint/tests (fix that
  first; never spend reviewers on broken code).

## The loop

```
0 GATE    quality gate, entry check, SCOPE seal, ROSTER
1 REVIEW  dispatch the roster        (round 1: full scope; ≥2: fix diff)
2 TRIAGE  verify findings against sources → LEDGER
3 FIX     fix accepted findings, re-run quality gate, FIX MANIFEST
4         back to 1                                       (cap 5 rounds)
5 CLOSE   deterministic rollup → two verdicts + hand-back
```

Between fix and re-dispatch the tree is frozen; an edit while reviewers
run voids the round.

## Artifacts

Each stage produces its artifact before the next stage starts. If you
cannot fill a field, write `unknown` — ledger content is quoted from
sources or reviewer output, never invented.

### SCOPE seal (per round, before dispatch)

Diff command with explicit base/head; changed files *including untracked
and staged*; a **content identity** produced by commands, not judgment
— and sealed over the WHOLE tree, never the subject list (the subject
list selects what is *reviewed*; the seal binds everything): the
verbatim output of these commands, run NUL-safe exactly as written —
word-splitting a pathname silently drops it from the seal:
`find . -path ./.git -prune -o -print0 | sort -z | tr '\0' '\n'`
(enumeration — every path: files, symlinks, *and directories*);
`find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0
sha256sum` (record `absent` for a deleted tracked path);
`find . -path ./.git -prune -o -print0 | sort -z | xargs -0 stat -c
'%n %a %F'`;
`find . -path ./.git -prune -o -type l -print0 | sort -z | xargs -0
-r env QUOTING_STYLE=shell-escape-always stat -c '%N'` (`-r` skips
the call when the tree has no symlinks; the quoting style is pinned
in the command because `%N`'s escaping obeys that environment
variable — an inherited `literal` would print targets raw;
records are framed by stat as quoted `'link' ->
'target'` with control characters escaped — no delimiter collisions;
directory existence and modes, file modes, types, and link targets
all bound — a retargeted symlink or a new empty directory must not
seal identical); and
`git ls-files -s` (whole index; empty for non-git). CLOSE re-runs
them all and diffs the outputs. Ground-truth
files living outside the tree are hashed into the seal as well. The
loop's own artifacts — ledger, prompts, manifests, reports — live
*outside* the sealed tree: an in-tree loop artifact voids its own
round. Base/head and the subject set come from the user's request —
verbatim when stated; when inferred, record the inference and prefer
the larger scope, and the final report echoes base/head, subject set,
and any exclusions for the user's audit. Subject
vs ground-truth split (ground truth
is cross-checked against, never reviewed — the split is pinned at round
1, and moving a changed file into ground truth mid-loop needs user
authority); one line of deployment context (what this code is for —
reviewers calibrate severity with it). Non-git subjects: seal = per-file
hashes + snapshot copies, the inter-round diff is a diff of snapshots,
and if no trustworthy delta exists, run a single round only. The final report
re-runs the seal commands and requires byte-identical output: any
difference — added, renamed, removed, index-divergent, mode-changed, or
staging-state-changed file — is a mismatch. Rounds ≥2, the seal also
carries one line per INTENTIONAL row — `INTENTIONAL-CHECK <id>:
assumption held | invalidated` — and reconciliation fails if any
INTENTIONAL row lacks its line.

### ROSTER (round 1, before dispatch)

First, a read-only subagent skims the sealed scope and returns a
**risk-surface inventory**: named areas with a one-line why (money, auth,
concurrency, persistence, public contracts, …). Fresh eyes on purpose —
authors underrate their own footguns. Then:

```
ROSTER: holistic, adversarial[, <specialist> per inventory area]
Inventory areas not covered: <area> — <because>
```

Scope the roster honestly to what a good job needs: a specialist per
inventory area that demands depth, none where a generalist's hint
suffices — never pad, and never trim to hit a number (reviewer cost
sizes depth-per-reviewer, not whether an area gets covered; a stale
cost model shrank a real roster once). More than 8 reviewers: stop and
confirm the roster with the user before dispatch (AskUserQuestion,
offering reviewers to drop) — skipped only when the invocation passed
`--force`. Run at most `min(10, cpu_cores - 2)` reviewers at once
(dispatch.md §Concurrency).

Rounds ≥2: default holistic + adversarial only. A round closes only when
every rostered reviewer **completed**: exit 0, AND a verdict line with
severity counts, AND a charter attestation — "no material issue in
<chartered scope>" or, when findings are reported, "aside from these
findings, no material issue in <chartered scope>"; an attestation
narrower than the charter is not completion — AND — rounds ≥2 —
a FIX-AUDIT line for every
manifest entry. Completion is judged against the reviewer's **report
file**: every prompt names a fresh file path *outside the sealed tree*
that the reviewer writes its final report to, and that file alone is
the review — stdout is diagnostics, never harvested (a reasoning trace
full of draft findings and echoed prompt text can satisfy any grep). A bare verdict, a
refusal, or echoed prompt text is NOT a review. Set a timeout on every
call — sized and waited per [dispatch.md](dispatch.md); record the
chosen timeout and each reviewer's observed duration, and check for
output progress before declaring a call hung. A timeout is a failed
call. Failure → one retry → still failed → the round is INDETERMINATE,
reported as such — as is a round that exceeds its own wall-clock
ceiling (a broken wait degrades to INDETERMINATE, never hangs
silently). A reviewer that did not
complete is NOT RUN — never "no findings". Run reviewers via the CLI
command the user specified — if none was given, ask; never invent one.
Write prompts to a temp file, never hand-interpolate. Reviewer prompt =
[reviewer-addendum.md](reviewer-addendum.md) with placeholders filled.

### LEDGER (updated at triage; the loop's single state object)

One row per canonical finding. Reviewer reports are merged into rows by
reference; duplicates become aliases, not new rows.

```
| id | sev (reported→current) | finding | factual | state | provenance | evidence |
```

- `factual`: CONFIRMED / PLAUSIBLE / UNVERIFIABLE — *your* post-triage
  status, from reading the actual sources and diff (a reviewer's report
  is a claim, not evidence). PLAUSIBLE rows: verify and promote or
  refute. UNVERIFIABLE rows keep why + what evidence would decide.
  `factual` describes the claim; refutation lives on the state axis and
  needs quoted refuting evidence — so a REFUTED row is never
  factual-UNVERIFIABLE. A timing-only finding (hang, stall, flaky
  failure) may be contention from concurrent reviewers sharing the
  environment — but a clean serial re-run alone refutes nothing: one
  passing sample cannot refute observed nondeterminism. REFUTED needs
  evidence isolating contention as the cause (e.g. the failure
  reproduces under concurrent load and never serially, with the product
  path ruled out); without it the row stays PLAUSIBLE and blocks per
  the normal rules.
- `state`: OPEN / FIX_APPLIED / FIX_VERIFIED / REFUTED / BACKLOGGED /
  INTENTIONAL. No other words. Rows change atomically: a disposition
  that bounces or fails restores every field of the row to its
  pre-disposition values — for a row ingested already-downgraded, that
  means current severity := reported severity. The rejected disposition's
  evidence stays only as history marked REJECTED, never as operative
  evidence.
- **Settled = REFUTED or FIX_VERIFIED. Nothing else.** "Accepted" is
  OPEN. A fix you applied is FIX_APPLIED; it becomes FIX_VERIFIED only
  when every completed reviewer's `FIX-AUDIT <id>` line says clean — one
  dirty line blocks promotion and reopens the row (INCOMPLETE-FIX). An
  aggregate clean verdict promotes nothing, and your passing tests don't
  either.
- INTENTIONAL requires `AUTHORITY: <user/spec statement that predates
  the finding>` plus `ASSUMPTION: <the premise it rests on>` in
  evidence — with exactly one exception to the predate rule: the user,
  asked directly, may accept a finding after the fact (risk acceptance
  is the user's prerogative, never yours). No authority → the row
  stays OPEN or goes to the user. You cannot declare your own fix's
  side effect intentional.
  AUTHORITY must be independently inspectable by the adjudicator: a
  file locator (spec/doc file:line) inside the sealed ground truth.
  Authority that lives only in conversation is not adjudicable — those
  reprieves go to the user, and the user's answer is the transition:
  record `AUTHORITY: user-confirmed this loop` with the confirmation
  quoted; the row becomes INTENTIONAL without adjudication (the
  adjudicator audits file-authority reprieves only). Anything that
  invalidates a row's ASSUMPTION — a later fix, or a change in
  authority or ground truth — reverts it to OPEN. Each round's
  INTENTIONAL-CHECK line (see SCOPE seal) forces the comparison;
  `invalidated` reverts the row to OPEN. Re-disposing it to
  INTENTIONAL follows the row's authority route: file authority is a
  fresh reprieve through adjudication; user-confirmed authority
  returns to the user for a fresh quoted confirmation. A bounce or a
  declined confirmation leaves the row OPEN.
- BACKLOGGED is for verified findings out of the loop's scope. It is
  storage, not absolution: backlogged Important+ reappear in the final
  verdict as known blockers.
- **Adjudication:** one read-only subagent pass per round covers every
  pending reprieve — any row moving to REFUTED or INTENTIONAL, and any
  row whose current severity sits below a reviewer-stated Important+
  (including rows ingested that way). The adjudicator gets the rows, the
  sealed scope's full file list, and the ground-truth inventory, and
  reads the sources itself — it must look beyond the sources the triager
  cited; its charter is to hunt for context that cuts against each
  disposition. Bounce → full row restored. An adjudication pass counts
  only if it finishes cleanly with well-formed output; decisions from a
  crashed or malformed pass are ALL discarded — the crash taints them —
  and that pass is re-run once in full. A clean pass's decisions are
  kept (a bounce is final for the round); if it left rows undecided, it
  is re-run once for those rows only. Rows still undecided after the
  re-run are bounced, and a second failed pass bounces every pending
  reprieve — never a third run (fail closed). You wrote the fixes; your
  reprieves get checked.
- Fix accepted findings yourself while rounds remain — handing an OPEN
  Important+ back to the user mid-loop is only for genuine blockers
  (missing authority, environment you lack, two failed fix attempts).

### FIX MANIFEST (after fixing, before re-dispatch)

Per fix: `<id> → <what changed> → <files> → TWINS: searched <pattern> —
<n> sites`. The twin search is mandatory: a real defect is presumed to
recur until a named, re-runnable search says otherwise — fix the
siblings too. Changed a test? Trace the change to the spec in the
manifest; an unexplained weakened assertion is a defect, not a fix.
Proving a fix or a test bites: mutate the assertion target in a
throwaway copy — never disable a fixture/stub to force a failure (the
fallback may be a real, paid, network-calling binary).
Files touched beyond what findings named: declare or revert.

### PROVENANCE (every round ≥2 finding, at triage)

Rounds ≥2 review the inter-round diff plus the fix manifest. Every new
finding gets exactly one:

- `INCOMPLETE-FIX <id>` — descendant of an existing row: same root cause,
  unfixed sibling, or the failure is reachable again. **Reopens that row
  to OPEN** (it was never truly settled). Location is irrelevant — an
  unfixed sibling of an accepted finding is in scope even if its line
  predates the loop.
- `FIX-REGRESSION` — introduced or exposed by a fix diff, cite it; the
  defect may manifest in unchanged code (a caller of a changed callee).
  New row, normal severity rules. Your authorship changes nothing.
- `CRITICAL-ESCAPE` — unrelated pre-existing defect, admissible only as
  Critical with a conclusive trace.
- Anything else → BACKLOGGED row.

Precedence and edge cases: a finding matching an existing row's root
cause or failure is INCOMPLETE-FIX even when a fix also caused it —
reopen beats new-row. A duplicate of an OPEN row is an alias: merge it
(reported severity = the highest any alias states), no provenance line.
Conclusive new evidence against a REFUTED row is INCOMPLETE-FIX <id> —
refutations reopen exactly like fixes. Record every reopen on the row.

Oscillation = a reopen that resurrects a previously fixed failure (fix A
breaks B, fixing B resurrects A). It ends the loop early as NOT
CONVERGED — don't burn rounds on it. Repeated reopens for *new* missed
siblings are just incomplete fixes; those fall under the two-failed-
attempts hand-back, not oscillation.

### CLOSE rollup (deterministic — computed from the ledger, never re-judged)

- **CONVERGED** iff no Important+ row is OPEN or FIX_APPLIED (each one is
  FIX_VERIFIED, REFUTED, BACKLOGGED, or INTENTIONAL), every round's
  roster completed, the recomputed content identity equals the last
  seal, and reconciliation passes (every reviewer report mapped, every
  row has a state, every due INTENTIONAL-CHECK line present). The whole
  ledger decides — never the last round's yield.
- **NOT CONVERGED** — whenever any CONVERGED conjunct fails; CLOSE is
  total, and these are the common causes, not an exhaustive set: an
  INDETERMINATE round, oscillation, a content-identity mismatch (name
  the divergent files), or any OPEN or FIX_APPLIED Important+ row
  remaining when the cap, a budget stop, or two failed fix attempts end
  the loop. Hand back the failed conjunct, surviving rows, fix
  attempts made, why unresolved, current hypothesis. Reaching the cap
  with a convergent ledger is simply CONVERGED — the cap forces honesty,
  never failure and never green.
- Report **two verdicts**: convergence (did the loop finish its job) and
  merge-readiness — NOT merge-ready while any BACKLOGGED or
  factual-UNVERIFIABLE Important+ row exists; list each as a known
  blocker, and list INTENTIONAL Important+ rows as authorized exceptions
  with their authority. "Converged, not merge-ready" is a legitimate
  outcome.
- Reconciliation line: every reviewer finding maps to a row; every row
  has a state; counts printed. Backlog included, ranked. OPEN Minor rows
  may remain at close — list them.

## Red flags — stop if you catch yourself thinking:

| Thought | Reality |
|---|---|
| "Out of this round's diff → backlog" | Sibling/descendant of an existing row is INCOMPLETE-FIX — reopen it. Backlog never hides Important+ from the verdict. |
| "SETTLED says fixed, don't re-litigate" | Settled means FIX_VERIFIED or REFUTED. An accepted-but-unverified fix is still open. |
| "The other reviewers were clean; re-running the failed one isn't worth it" | The missing reviewer's value isn't priced by the findings others made. NOT RUN ≠ clean → INDETERMINATE. |
| "Termination condition met on the merits" (while a confirmed defect ships) | Compute both verdicts from the ledger. If a confirmed Important+ ships, the report says so in the headline. |
| "The cap forces us to conclude" | The cap with unresolved Important+ forces NOT CONVERGED + hand-back. It never forces green — and a clean ledger at cap is simply converged. |
| "Tests pass, so the fix is verified" | FIX_VERIFIED comes from next-round review of the fix diff. |
| "That behavior is intentional" (about your own fix) | INTENTIONAL needs authority predating the finding — sole exception: the user, asked directly, accepts it after the fact. Either way it is never yours to grant. |
| "I'll write something plausible for the missing detail" | Ledger content is quoted, never invented. Write `unknown`. |
