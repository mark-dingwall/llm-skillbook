# Review Team REFACTOR Results

Pre-REFACTOR package commit: `b73bdb94f51d0033b98274be166e1daa91c3a7d9`

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
