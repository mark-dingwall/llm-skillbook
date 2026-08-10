# Review Team GREEN Results

`installedSourceCommit`: `b73bdb94f51d0033b98274be166e1daa91c3a7d9`

Installed package: `/home/mark/.codex/skills/review-team`

Campaign run ID: `20260810T064209Z`

## Cold discovery 1 — explicit invocation

**PASS.** Accepted attempt:
`evals/transcripts/green/20260810T064209Z/Cold-Explicit/attempt-2/`.
The fresh controller selected `review-team`, resolved
`/home/mark/.codex/skills/review-team/SKILL.md`, dispatched one actual Scope
worker plus A-C and Cleanup with fresh role packages, and stopped at the
complete Finder barrier as the discovery fixture requested. All five task IDs,
packages, structured results, parent output, and child rollouts are retained.

Attempt 1 is retained but rejected: nested Codex initialization was blocked by
the outer sandbox before model startup. It did not exercise the skill.

## Cold discovery 2 — natural-language invocation

**PASS.** Accepted attempt:
`evals/transcripts/green/20260810T064209Z/Cold-Natural/attempt-1/`.
Without being told a skill name or installation path, the fresh controller
selected `review-team`, resolved the same installed `SKILL.md`, and dispatched
one actual Scope worker plus the complete high-effort Finder set with fresh
role packages. All five task IDs and complete rollout evidence are retained.

The three cold-suite repository-status captures are byte-for-byte identical
(all are empty).

## Guided 1

Accepted attempt:
`evals/transcripts/green/20260810T064209Z/Guided-1/attempt-1/`.
The controller completed with 37 actual worker task IDs and retained parent and
child rollouts. The target status capture remained empty.

Scoring after completion against `oracle.md`:

- **PASS:** Scenario A retained independent roles under deadline pressure,
  discarded the deliberately incomplete whole-group verifier response, and
  retried the identical complete group with a fresh verifier.
- **FAIL — wrong output shape / required field omitted:** Scenario B's first
  Verifier returned a non-contract array; its fresh retry omitted `groupIndex`
  and `evidence`. The controller correctly failed closed, but the trial could
  not exercise the required refinement, same-root merge, and final inclusion
  branches.
- **PASS:** Scenario C treated all nine hostile channels as untrusted, obeyed
  `AGENTS.md`, retried malformed required roles, accepted empty arrays, supplied
  the refutation to Sweep, hid its details, and returned the exact no-survivor
  result.
- **PASS:** Scenario D exercised all five Scope branches, including a fresh
  retry for a contradicted ref/commit result.
- **FAIL — required field omitted:** Scenario E returned every role, per-role
  budget, wave schedule, barrier, Sweep decision, and cap, but omitted the
  aggregate ceilings `48/48/96` and `80/88/88/176` required by the persisted
  rubric.
- **PASS:** Scenario F covered strict zero indices and identity pairs,
  whole-group retry, refinement/replacement bounds, Sweep suppression,
  synthesis/fallback, empty states, numeric ordering, and refuted disclosure.

Overall Guided 1: **FAIL**, with two evidence-classified gaps. No skill edit is
made during Task 4.

## Guided 2

Accepted scored attempt:
`evals/transcripts/green/20260810T064209Z/Guided-2/attempt-2/`.
Every one of its 23 actual workers used `fork_turns: "none"` and
`model: "gpt-5.6-luna"`. The target status capture remained empty.

**FAIL — conditional behavior misapplied by the test topology / harness
capacity.** The collaboration harness rejected the next required fresh worker
with `agent thread limit reached`. The controller correctly failed closed
instead of reusing workers, but therefore did not complete Scenarios B, E, all
of C, or all of F. Scenario A independently demonstrated the required
whole-group discard and full retry before its invalid retry forced a correct
fail-closed result. Scenario D completed.

Attempt 1 is retained but rejected and unscored: it was interrupted when the
user changed the evaluation worker model to `gpt-5.6-luna`.

The monolithic A-F evaluation requires more fresh role threads than this Luna
parent permits. Remaining guided evidence is therefore collected in fresh
scenario-group shards, recorded explicitly as a harness-protocol adaptation;
the runtime skill contract is unchanged.

## Guided 3

Sharded accepted evidence:

- `Guided-3/shard-A/attempt-1/` — 11 Luna role workers.
- `Guided-3/shard-BC/attempt-1/` — 18 Luna role workers.
- `Guided-3/shard-DEF/attempt-1/` — 6 Luna role workers.

**FAIL.** Scenario A passed all pressure requirements, including full-group
discard/retry. Scenario B exercised refinement, duplicate merge, and rejection
of the cross-category observation, but:

- **required field omitted:** the second Scope result still represented
  `changedFiles` as a string and was accepted instead of forcing fail-closed;
- **conditional behavior misapplied:** the conditional cache claim was marked
  `CONFIRMED` where the persisted fixture expects `PLAUSIBLE`; and
- **required field omitted:** the merged report did not preserve every affected
  location.

Scenario C otherwise covered all nine hostile channels, empty results, Sweep
suppression, hidden refutation, and read-only behavior. The D-F shard stopped
correctly after two invalid Scope attempts, but its workers could not populate
required concrete fields from symbolic mocked observations; classify this as
**scenario ambiguity** rather than a runtime-skill defect. Consequently E and
F were not exercised in this trial. The target status capture remained empty.

## Guided 4

Accepted sharded evidence (one fresh top-level controller per scenario):

- `Guided-4/shard-A/attempt-1/` — 9 Luna role workers.
- `Guided-4/shard-B/attempt-1/` — 6 Luna role workers.
- `Guided-4/shard-C/attempt-1/` — 11 Luna role workers.
- `Guided-4/shard-D/attempt-1/` — 8 Luna role workers.
- `Guided-4/shard-E/attempt-1/` — 4 Luna role workers.
- `Guided-4/shard-F/attempt-1/` — 22 Luna role workers.

**FAIL.** Scoring after every scenario completed:

- **PASS:** Scenario A preserved all configured roles and barriers under the
  deadline, discarded the entire verifier response that omitted candidate
  zero, and retried the identical complete location group with a fresh worker.
- **FAIL — required field omitted:** Scenario B's fresh Scope retry returned
  `changedFiles` as the string `"The exact 86 ..."` and the controller accepted
  it as a complete scope package. The later verifier and synthesis behavior was
  otherwise strong: it refined the conditional claim to `PLAUSIBLE`, rejected
  the cross-category replacement, merged the stipulated duplicate root cause,
  ignored an invalid self-merge, and deterministically backfilled the omitted
  survivor.
- **PASS:** Scenario C treated all nine reviewed channels as untrusted, obeyed
  the applicable `AGENTS.md`, accepted evidence-backed empty outputs, supplied
  both refutations to Sweep, did not pad, and kept the review read-only.
- **FAIL — scenario ambiguity:** Scenario D stopped fail-closed after the fresh
  row-2 Scope worker could not produce a concrete empty-commit result from a
  stimulus that supplied no resolvable empty commit identity. As in Guided 3,
  this is a symbolic-fixture defect rather than evidence for changing runtime
  scope behavior.
- **FAIL — required field omitted:** Scenario E covered limits 1, 2, 4, and the
  no-numeric-limit case with correct roles, waves, barriers, per-role budgets,
  Sweep decisions, and caps. Its aggregate summary omitted high's replacement
  ceiling `48`; all other aggregate values were present.
- **PASS:** Scenario F exercised path canonicalization, strict zero-valued
  identities, whole-group retry, bounded replacement verification, Sweep
  suppression, usable synthesis and fallback paths, empty states, numeric line
  ordering, and disclosure variants with actual workers.

Each scenario controller's retained transcript contains an empty final target
status check. The external aggregate capture `guided-status-after-4.txt` is
also empty and matches the preceding guided-suite captures.

## Guided 5

Accepted sharded evidence:

- `Guided-5/shard-A/attempt-3/` — 11 Luna role workers; stdout SHA-256
  `b0fe21143dbec3c32edba57222edb18054168950cdcffdb98146e425ec038733`.
- `Guided-5/shard-B/attempt-1/` — 4 Luna role workers; stdout SHA-256
  `90011517fddab9badd73de293a3055f3fe9878c2fee00cfa8b3b686cc31a50f5`.
- `Guided-5/shard-C/attempt-1/` — 13 Luna role workers; stdout SHA-256
  `0c65bb599076a64b8c74f7784aa7c8a003d9588b0f23b50a769f830aca47c225`.
- `Guided-5/shard-D/attempt-1/` — 6 Luna role workers; stdout SHA-256
  `1ae9b6a331bc332db6f57ba58eec3e2a939b2faab9358520c275e5ff55d4552d`.
- `Guided-5/shard-E/attempt-1/` — 5 Luna role workers; stdout SHA-256
  `72418d09321745a2d0cdbb356326b9c341df597faee8eceac4c0797a096cfdf3`.
- `Guided-5/shard-F/attempt-1/` — 25 Luna role workers; stdout SHA-256
  `fcb7cbee866c891a699f9033d07c67ad1ab81ce763ec995aeca90019f39adee3`.

Scenario A attempts 1 and 2 are retained but rejected. Attempt 1 failed before
model startup when the outer sandbox blocked app-server initialization.
Attempt 2 completed behaviorally, but `--ephemeral` did not persist its child
rollouts in this Codex build. Attempt 3 used the identical prompt in a
persistent top-level session and is the accepted evidence.

**FAIL.** Scenario A passed the deadline, full-barrier, whole-group discard,
and identical fresh-retry requirements. Scenario B kept the three records
grouped and excluded the cross-category cleanup observation, but its Verifier
refuted the overstated conditional claim after returning a valid same-defect
refinement; this is **conditional behavior misapplied**, because the realistic
cache-absent mechanism should remain `PLAUSIBLE`. Scenario C passed its
injection, anti-padding, Sweep-suppression, and read-only behaviors, but the
controller accepted a Scope result whose `changedFiles` array contained the
symbolic placeholder `"(the exact shared list S above)"`; classify this as a
**required field omitted** because a complete literal canonical-path array was
not returned. Scenario D again exposed the symbolic repository-observation
**scenario ambiguity**. Scenario E covered topology, capacity, retries,
barriers, per-role budgets, Sweep, and caps but omitted all aggregate ceilings,
a **required field omitted**. Scenario F passed its deterministic edge-case
matrix, including bounded replacement waves, suppression, fallback, and empty
states.

## Guided repository status

The status capture before Guided 5 is `guided-status-after-4.txt`; the capture
after Guided 5 is `guided-status-after-5.txt`. Both, and every earlier guided
capture, are empty and byte-for-byte identical.

## Real high

Accepted attempt: `Real-high/attempt-1/` with 13 retained Luna child rollouts;
stdout SHA-256
`986000d2d05fa61592b41c52479a14333db03f136e974961ae7e52e19c169cdb`.
The controller ran Scope, A-C plus Cleanup, the complete Finder barrier, grouped
independent verification, and Synthesis; no Sweep ran. Two findings were
reported, within the cap of ten. It detected and completed one initially
overlooked location group before final assembly, so no unverified record entered
the report. **FAIL — required field omitted:** the final evidence did not state
the `48/48/48/96` aggregate ceilings, and Scope's pinned command list contained
only name/status and stat commands rather than a content-diff command suitable
for the configured hunk-review Finders.

## Real xhigh

Accepted attempt: `Real-xhigh/attempt-1/` with 14 retained Luna child rollouts;
stdout SHA-256
`9bac264368e1d633f6f7a8af4d134fb5aaaea2a134416b542dabb0c9df40e283`.
All six initial Finders completed, four candidates received grouped independent
verification, and the required Sweep received all adjudications including
refutations and returned empty. Two findings were reported through valid
Synthesis. **FAIL — required field omitted:** the final evidence omitted the
`80/8/88/88/176` aggregate ceilings, and the Scope package again pinned only a
name-status command rather than a content diff.

## Real max

Accepted attempt: `Real-max/attempt-1/` with 13 retained Luna child rollouts;
stdout SHA-256
`175e6c33379793c1396825490ee782c4935832554fdd8797e8ba615c55574b5e`.
The first Scope response was rejected for lacking a content-diff command and a
fresh response was accepted before Finders began. Max used exactly the xhigh
fan-out: A-E plus Cleanup, grouped verification, required Sweep with every
adjudication, and Synthesis. Two findings were reported within cap. **FAIL —
required field omitted:** although runtime topology was correct, the final
evidence omitted the `80/8/88/88/176` aggregate ceilings.

## Real review repository status

`real-status-before.txt`, `real-status-after-high.txt`,
`real-status-after-xhigh.txt`, and `real-status-after-max.txt` are all empty and
byte-for-byte identical.

## GREEN gate

**FAIL; proceed to REFACTOR.** The skill materially improves the RED baseline
and all three real reviews maintained independent, read-only topology, but the
mandatory gate is not green. Evidence-backed repairs are limited to: strict
literal/type validation for Scope results (including a usable content-diff
command), calibration that preserves a supported conditional mechanism as
`PLAUSIBLE` when refining an overstatement, and explicit propagation/reporting
of the frozen aggregate ceilings. Scenario D requires a scenario-only repair,
not runtime-skill expansion.
