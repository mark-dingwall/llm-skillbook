# Review-state processor prototype results

Date: 2026-08-17

Status: prototype review complete; all correctness findings reconciled. The
prototype is accepted as evidence but rejected as the unchanged implementation
foundation because its validated projections are too broad for MVP.
These results demonstrate a tested interface; they do not authorize the rest
of the redesign.

## What was built

The prototype exposes one strict envelope through `review_loop.process()` and
`python3 -m review_loop`. It has eight operations:

| Operation | Mechanical responsibility |
|---|---|
| `derive_policy` | Combine two automatic ratings or apply an explicit tier; return confirmation and tier policy. |
| `refresh_inventory` | Validate semantic mappings supplied by the inventory role; preserve monotone lineage evidence and establish pre-roster `CURRENT`/`STALE` state. |
| `record_specialist_coverage` | After specialist review and TRIAGE, bind completed usable scheduled reports to the current seal and exact active-lineage scope. |
| `plan_roster` | Apply tier eligibility and `CURRENT`/`STALE` staffing; partition the complete roster into capacity-safe waves. |
| `reconcile_gates` | Preserve already-decided applicability/timing and compute gate blockers versus disclosed gaps. |
| `apply_ledger_decisions` | Reconcile raw findings, apply legal row transitions, and represent the bounded adjudication retry state. |
| `record_final_challenge` | Bind challenge outcomes to the final seal and represent retry, staleness, triage, block, and uphold states. |
| `compute_terminal` | Compute cancellation, convergence, merge-readiness, the qualified-claim eligibility bit, and all failed conditions. |

The processor imports no filesystem, process, network, or multi-review module.
It does not read a target, inspect evidence, run a command, dispatch an agent,
or decide semantic truth.

## Boundary examples

Explicit operator intent requires no invented rating samples:

```json
{"schema_version":1,"operation":"derive_policy","input":{"explicit_tier":"low","no_confirm":false,"raters":[]}}
```

```json
{"schema_version":1,"ok":true,"result":{"tier":"low","source":"explicit","confirmation_required":false,"round_cap":2,"normal_capability":"mid-tier","specialist_threshold":"Critical","multi_review_rounds":[]}}
```

Automatic-`max` confirmation decline remains distinct from both terminal
verdicts. A valid `compute_terminal` request with `confirmation: "declined"`
and no expired deadline returns this result shape:

```json
{"schema_version":1,"ok":true,"result":{"lifecycle_outcome":"CANCELLED_BEFORE_REVIEW","terminal_verdict":null,"merge_ready":null,"qualified_claim_eligible":false,"failed_conditions":[],"limitations":[]}}
```

## Measurements

Measured with `wc -l -w` after the full suite passed:

| Surface | Lines | Words |
|---|---:|---:|
| Production package | 2,057 | 6,525 |
| Unit tests | 1,627 | 3,913 |
| Total prototype | 3,684 | 10,438 |

The production total is dominated by `review_loop/state.py` at 2,034 lines.
This is not evidence of a small implementation. The strict schemas expose how
much state the governing design currently asks one helper to own. Splitting the
file would improve navigation but would not reduce that machinery, so no
cosmetic module split was used to claim simplicity.

The public interface has eight operations rather than a single monolithic
controller action. That separation kept tests and callers explicit, but it is
also a warning against adding more processor responsibilities during the MVP.

## Verification evidence

Fresh commands:

```text
PYTHONPATH=review-loop python3 -m unittest discover -s review-loop/tests/unit -p 'test_*.py' -v
→ 85 tests, OK

python3 -m compileall -q review-loop/review_loop
→ exit 0, no output

git diff --check
→ exit 0, no output
```

The tests cover the public JSON boundary and CLI exit behavior; tier arithmetic
and confirmation; inventory identity, retirement, coverage provenance and every
declared invalidator; complete roster waves without numeric caps; applicable
gate failure and evidence-gap behavior; ledger transitions and source premise;
the two-call full/subset adjudication retry; structured user-acceptance
round-tripping; final-challenge freshness; cancellation; convergence; and
merge-readiness.

## Initial independent review

The first high-effort review found eight distinct issues. Seven were
trust-boundary defects and one was mutable output state:

- continuing-area coverage failed open when its invalidator record was absent;
- a coverage event could let a new or successor identity skip its mandatory
  first specialist review;
- file-authorized `INTENTIONAL` disposition had no structured sealed locator,
  identity, proposition, and finding linkage;
- canonical `FIX_VERIFIED` rows did not themselves require a manifest and fix
  evidence;
- one settled state could jump directly to another without reopening;
- terminal computation trusted caller-supplied gate summary booleans;
- terminal computation accepted internally contradictory final-challenge
  summaries; and
- callers could mutate the shared tier-policy list through a returned result.

Each issue now has a regression test. The processor requires explicit
invalidators for continuing/successor lineage, separates pre-roster inventory
refresh from sealed scheduled post-review coverage, preserves structured
authority and adjudication proof on canonical rows, validates canonical
settlement invariants and transition paths, derives terminal gate state from
raw records, validates challenge-state combinations, and copies mutable policy
values at the output boundary. Focused independent re-review found and closed
three further proof-binding gaps: adjudication evidence is structured and
retained, user authority requires an actual ledger-bound acceptance record, and
fix evidence is a retained structured record bound to the operation target
seal. The final independent pass reported no remaining actionable correctness
findings.

## MVP-boundary review

The independent boundary reviewer recommends retaining the deterministic policy
kernel but not accepting this broad interface unchanged as the implementation
foundation. The processor currently duplicates rich artifact/report validation:
raw finding prose and locators, full area narrative, gate commands/results,
gestalt-factor prose, and complete final-challenge attempt records. The clean
replacement should instead consume compact validated projections plus immutable
artifact references while keeping fail-closed transition rules.

The review also identified the pre-roster/post-review coverage sequencing flaw.
That finding is already reconciled in the prototype through the separate
`record_specialist_coverage` transition. The broader projection narrowing is a
design amendment and replacement-plan task, not a reason to grow this evidence
prototype further.

## Skill prose this could replace

If the prototype survives independent review, future `SKILL.md` prose need not
teach an agent to perform these calculations manually:

- rating-axis arithmetic, gestalt step-up, tier table lookup, and automatic-max
  confirmation selection;
- specialist threshold filtering, eligible-Critical restaffing, uncovered-first
  ordering, and wave partitioning;
- inventory-map bijection, monotone evidence union, and coverage transition
  bookkeeping;
- required/supporting gate rollup;
- legal ledger transitions and adjudication retry bookkeeping; and
- convergence and merge-readiness conjunctions.

The skill would still state the operator-facing policy and explain artifacts,
but should call the processor for the authoritative calculation instead of
duplicating executable state-machine prose.

## Responsibilities that remain outside

The following remain semantic-agent or controller work and must not migrate
into this processor:

- deciding target scope, consequence, area identity, `GENERALIST-MISS`, surface
  ownership, dependency/contract relevance, or whether new evidence is material;
- discovering or classifying gates, determining command safety, running commands,
  mutation testing, and containing their execution;
- sealing the target and call inputs, resolving Git deltas and surface locators,
  enforcing deadlines, and recovering process handles;
- rendering prompts, validating raw Markdown reports, dispatching/retrying agents,
  and adapting multi-review;
- judging findings, evidence, authority, refutations, intent, severity, or final
  readiness; and
- performing and containing the sole ledger-bound FIX role.

## Provisional MVP assessment

The prototype supports the architectural claim that deterministic bookkeeping
can be removed from prompt prose and tested. It also falsifies any assumption
that the full declared state contract is tiny: strict dependency-free validation
and transitions currently cost 2,057 production lines.

The prototype gate therefore rejects adopting the broad interface unchanged.
It supports a smaller policy kernel with compact validated projections and the
explicit post-review coverage transition. The governing design and clean
replacement plan must be amended and independently reviewed before controller,
skill, or prompt implementation begins.

Do not respond by adding a framework or dependency. The next step is the
evidence-driven governing-design amendment and independently reviewed clean
replacement plan. Controller, skill, and prompt work must not begin before that
smaller boundary is approved.
