# Review Team REFACTOR Results

Pre-REFACTOR package commit: `b73bdb94f51d0033b98274be166e1daa91c3a7d9`

Final installed source commit: `d4d2500`

Final result: **PASS**. The complete accepted suite, focused regression
fixtures, and real read-only reviews satisfy the required orchestration and
report contracts. Rejected and superseded attempts remain in the transcript
tree with explicit metadata; they are evidence of observed failure modes, not
inputs to the pass classification.

Task 4 completed without transcript truncation and classified the GREEN gate as
FAIL. All accepted Guided 5 and real-review controller transcripts reached a
terminal result, and the Task 4 evidence was committed as `172469a`.

## Failure classification

| Observation | Classification | Smallest owner |
|---|---|---|
| Scope accepted a string or symbolic placeholder where literal `changedFiles[]` paths were required, and two real runs pinned only name/status/stat commands | required structural field | `references/report-contract.md` Scope result |
| A verifier refuted an overstated universal claim even though its narrower realistic mechanism was supported | wrong conditional behavior | `references/verifier.md` refinement |
| Guided and real controllers omitted frozen aggregate ceilings from their scheduling/report evidence | required structural field | `references/report-contract.md` report output |
| Scenario D relied on an out-of-section range reference and symbolic repository observations | scenario ambiguity | Scenario D stimulus and scorer oracle only |

No hypothetical behavior was added and the frozen design documents were not
changed.

## Scenario-only repair

Commit `7683fa7` names `/home/mark/tools/superpowers`, repeats the pinned range
inside Scenario D, and provides concrete authoritative mocked outcomes for
each resolution branch. The scorer oracle was changed in lockstep. Because the
repair affects only Scenario D, the A-C no-guidance baseline and its causal RED
claim are unchanged and were not rerun. `red.sha256` was regenerated and all
six entries verified `OK` before commit.

Five targeted D trials then correctly refused to invent changed paths or diff
content for nine nominally successful cases. The fixture was still incomplete:
it specified branch resolution but not enough authoritative output to form a
strict non-empty Scope result. A second D-only repair adds concrete literal
paths and non-empty content outcomes for every successful case; the oracle was
updated in lockstep and the A-C baseline remains unaffected.

## Package wording changes

### Scope result

Before, the contract listed field names and said only that an invalid result
receives one retry. It did not define literal array/type validation or require
a patch-producing command for non-empty review scope.

After, the Scope result is an ordered structural contract: required own fields,
exact scalar and array types, literal canonical changed paths, rejection of
summaries/placeholders/references in path slots, and at least one content-bearing
diff command for non-empty scope. Any violation discards and retries the whole
Scope response.

### Conditional refinement

Before, the verifier could refine an overstatement and the ladder said
uncertainty alone is not refutation, but their interaction was implicit.

After, an observable one-fix predicate states that a supported narrower
realistic mechanism remains a refined survivor; condition-dependent triggers
are graded `PLAUSIBLE` and are not refuted merely because universal wording was
false.

### Aggregate ceilings

Before, the ceiling table existed but the report stats contract did not require
controllers to emit it.

After, scheduling evidence and final stats must include one closed `ceilings`
record with the level's exact initial, Sweep, finder-output, replacement,
all-record, and report-cap values.

The first five Scenario E micro-tests exposed residual variance: trials 3, 4,
and 5 emitted the aggregate record, while trials 1 and 2 still emitted only
per-role budgets and report/Sweep caps. This was an observed structural
omission, not a new ceiling rule. The main workflow recipe now requires the
reference-owned closed `ceilings` record before dispatch and in final stats;
the numeric values remain owned only by `report-contract.md`.

## Targeted retest

The targeted B series passed five of five runs after the Scope contract
refinement. Each controller required literal changed-file arrays and a
content-producing diff command for non-empty scope.

The first targeted D series correctly refused to invent missing fixture facts,
which exposed the remaining scenario ambiguity. After the scenario-only repair
at `50e6d93`, the five replacement D runs passed every branch of the resolution
matrix, including stop behavior and successful literal non-empty scopes.

The first targeted E series exposed residual aggregate-ceiling variance. After
the workflow recipe refinement at `2d41c4e`, all five replacement E runs emitted
the same closed level record before dispatch and in final stats. The accepted
high cases used `48/0/48/48/96/10`; accepted xhigh/max cases used
`80/8/88/88/176/15`. Cleanup caps were 30 at high and 40 at xhigh/max.

All targeted status captures are empty and byte-identical to
`targeted-status-before.txt`.

## Complete guided suite

Five complete A-F suites passed. Guided 1 used one long-lived controller;
Guided 2-5 used one fresh controller per scenario so each shard had an
independent worker-slot pool. The accepted artifacts are:

| Suite | Accepted artifacts | Result |
|---|---|---|
| Guided 1 | `Guided-1/attempt-2` | A-F pass |
| Guided 2 | `Guided-2/shard-{A..F}/attempt-1` | A-F pass |
| Guided 3 | A-D/F attempt 1; E attempt 2 | A-F pass |
| Guided 4 | A-D/F attempt 1; E attempt 2 | A-F pass |
| Guided 5 | A-D/F attempt 1; E attempt 4 | A-F pass |

The accepted suites covered strict Scope types/content diffs, the complete
Finder barrier, capacity-safe waves, mixed-category grouped verification,
whole-group retry and fail-closed behavior, refinements, initial and Sweep
replacement waves, chain rejection, Sweep suppression including refuted
records, strict Synthesis identity, merge/backfill, deterministic fallback,
empty results, and opt-in refuted disclosure.

Retained rejected attempts include the interrupted Guided 2 monolith, three
zero-turn Scenario E launches caused by the outer read-only session-state
boundary, Guided 5 E attempt 2's incorrect Cleanup cap, and Guided 5 E attempt
3's incomplete collaboration matrix. Guided 5 E attempt 4 completed all twelve
level/limit cases and is the accepted result.

Every guided status capture from `guided-status-before.txt` through
`guided-status-after-5.txt` is zero bytes and byte-identical.

## Real read-only reviews

All accepted real reviews used the exact pinned range
`05c2393b826dd0f09cd071427e62b42e6c751995..36f3883f4ef1b3ca70307fd05509c9a501d772a3`
in `/home/mark/tools/superpowers`.

| Level | Accepted artifact | Initial candidates | Sweep | Verified | Refuted | Reported |
|---|---|---:|---:|---:|---:|---:|
| high | `Real-high/attempt-1` | 7 | not configured | 7 | 3 | 3 |
| xhigh | `Real-xhigh/attempt-1` | 8 | 0 | 8 | 3 | 4 |
| max | `Real-max/attempt-3` | 10 | 0 | 10 | 0 | 7 |

High used A-C plus Cleanup and no Sweep. Xhigh and max used A-E plus Cleanup
and the required gap-only Sweep. Every candidate reaching a report was
independently verified; Synthesis received only survivors and evidence. Refuted
details remained off the cutting-room-floor report because the invocation did
not request disclosure.

Max attempts 1 and 2 are rejected evidence. Both admitted same-defect
restatements as new replacement records; attempt 1 also omitted the target
repository `AGENTS.md` from its structured scope. This repeated behavior
justified the final, bounded controller-admission refinement at `d4d2500`.
Attempt 3 lists both applicable instruction files, admits no invalid
replacement, completes every required role, and preserves a full worker ledger.
Its stdout stream logged one lag/drop warning, so the persisted
`parent-rollout.jsonl` and direct child rollouts are the authoritative complete
capture; the final stdout ledger and terminal marker agree with them.

The four real-review status captures are zero bytes and byte-identical. The
review workflow did not modify the target repository.

## Replacement-admission regression

The final refinement makes the controller independently name two fixes before
admitting a Verifier proposal as materially new. Same-defect rewordings,
relocations, or more prescriptive remedies receive no ID, no worker, and no
replacement-stat entry; a later verifier cannot retroactively validate them.

`Focused-replacement-gate/attempt-1` passed one rejected same-defect proposal
and one admitted distinct proposal. `Postfix-replacement-matrix/attempt-1`
then passed the complete affected matrix: same-defect rejection, a materially
new initial replacement, a materially new Sweep replacement, independent
verification for both, and rejection of a replacement-of-replacement without
an ID. The broad `Postfix-F/attempt-1` is retained as rejected fixture evidence:
two Scope workers returned a synthetic non-empty scope without a content diff,
and the controller correctly stopped fail-closed before downstream dispatch.

## Model and capture policy

All workers in the refactor campaign used `gpt-5.6-luna`. Earlier trials used
the then-current recorded effort (commonly medium); after the user's final
policy update, controllers and workers were explicitly pinned to Luna/high.
The accepted high, xhigh, max, focused replacement, and post-fix replacement
matrix artifacts all record Luna/high in their persisted turn contexts.
Review level and inference effort are recorded separately: max-level workflow
semantics were tested while honoring the later Luna/high cost-control override.

Each attempt directory contains its prompt, stdout JSONL when launched,
metadata, full parent rollout when a thread started, direct-child rollouts,
full child thread IDs, and a rollout index. There are 63 pre-postfix parent
controllers and 1,125 direct child rollouts in the main export; the two postfix
attempts add two parents and four children. Zero-turn startup failures retain
their empty/missing stdout boundary and metadata rather than fabricated
sessions.

## Reader audit

A fresh reader can determine the final decision without conversation context:
use only attempts whose metadata says `outcome: accepted`, verify their terminal
markers and worker ledgers against the persisted rollouts, confirm the status
series are identical, and verify the final source/install hashes against
`d4d2500`. Rejected and superseded directories explain variance but do not
contribute to the PASS result.
