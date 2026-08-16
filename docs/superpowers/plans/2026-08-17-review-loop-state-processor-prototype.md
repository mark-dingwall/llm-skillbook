# Review Loop State Processor Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Apply
> `superpowers:test-driven-development` to every production-code step and keep
> this checklist current.

**Goal:** Build and review one bounded prototype that proves the deterministic
review-loop policy can be expressed as strict JSON-in/JSON-out state
transitions without reading or interpreting the review target.

**Architecture:** Add a small, dependency-free Python package under
`review-loop/`. One public `process()` boundary validates a versioned operation
envelope, dispatches to pure policy functions, and returns a validated result.
A thin `python3 -m review_loop` adapter reads one JSON value from stdin and writes
one JSON value to stdout. The prototype covers only rating/tier arithmetic,
complete roster selection and batching, inventory/coverage transitions,
evidence-gate state, adjudication bounce, ledger transitions, final-readiness
state, and terminal rollup. It has no filesystem, process, agent, prompt,
provider, sealing, or target-access implementation.

**Tech Stack:** Python 3.10+ standard library, `unittest`, JSON, Git.

## Global constraints

- Keep the prototype isolated from `multi-review`; do not add a project file,
  dependency, plugin system, controller, or compatibility layer.
- Treat every semantic judgment as already decided input. The processor may
  validate and combine values, but never infer consequence, area identity,
  relevance, evidence quality, or whether a finding is true.
- Reject unknown fields, missing fields, invalid enum values, duplicate IDs,
  ambiguous mappings, and invalid transitions. Never repair or partially accept
  malformed input.
- Preserve complete required work. Concurrency changes wave boundaries, never
  roster membership.
- Test observable contracts, not private helper structure. Each behavior change
  starts with a focused failing test and ends with the focused test plus the
  full prototype suite green.
- Do not change `review-loop/SKILL.md`, behavior-bearing prompts, the controller,
  or `multi-review` in this prototype. Those changes wait for prototype review.

## Public prototype contract

All requests have exactly:

```json
{"schema_version": 1, "operation": "<name>", "input": {}}
```

All successful responses have exactly:

```json
{"schema_version": 1, "ok": true, "result": {}}
```

Validation failures have exactly:

```json
{"schema_version": 1, "ok": false, "errors": [{"path": "...", "code": "...", "message": "..."}]}
```

`process()` returns either response shape. The CLI prints the same compact JSON;
it exits `0` for a valid request, including a mechanically negative verdict,
and `2` only when the request or JSON transport is invalid.

---

### Task 1: Establish the strict JSON boundary

**Files:**

- Create: `review-loop/review_loop/__init__.py`
- Create: `review-loop/review_loop/state.py`
- Create: `review-loop/review_loop/__main__.py`
- Create: `review-loop/tests/unit/__init__.py`
- Create: `review-loop/tests/unit/test_state_contract.py`
- Create: `review-loop/tests/unit/test_state_cli.py`

**Interfaces:**

- `review_loop.process(request: object) -> dict[str, object]`
- `review_loop.state.ValidationIssue(path, code, message)`
- `python3 -m review_loop`

- [x] **Step 1: Write failing envelope and CLI contract tests**

  Cover a non-object request, unknown/missing envelope keys, unsupported schema
  version, unknown operation, malformed stdin JSON, validation-error compact
  stdout, and exit code `2`. Also add the AST architectural-boundary test here,
  before production implementation: it rejects imports of `os`, `pathlib`,
  `subprocess`, `socket`, `urllib`, or `multi_review`. Run:

  ```bash
  PYTHONPATH=review-loop python3 -m unittest \
    review-loop/tests/unit/test_state_contract.py \
    review-loop/tests/unit/test_state_cli.py -v
  ```

  Expected: FAIL because the package does not exist.

- [x] **Step 2: Implement the minimum boundary**

  Export `process` from `__init__.py`. In `state.py`, validate the exact envelope,
  dispatch through an explicit operation table, sort validation issues by path
  then code, and return the declared response shapes. In `__main__.py`, perform
  transport only; write no diagnostics to stdout and do not catch internal bugs
  as validation failures.

- [x] **Step 3: Prove the boundary and architectural isolation**

  Rerun the focused tests; expect PASS. The AST check is a prototype boundary
  test, not a general Python sandbox. A successful operation and CLI exit `0`
  are introduced test-first with `derive_policy` in Task 2; do not add a dummy
  operation merely to make Task 1 green.

### Task 2: Derive effort policy deterministically

**Files:**

- Modify: `review-loop/review_loop/state.py`
- Create: `review-loop/tests/unit/test_state_policy.py`

**Operation:** `derive_policy`

**Input:** optional explicit tier, explicit no-confirm flag, and rater samples.
An explicit tier requires no samples and rejects supplied samples as ambiguous;
automatic selection requires exactly two validated samples containing
`complexity`, `risk`, and optional gestalt with at least three non-empty
evidenced factors.

**Result:** selected tier, source (`explicit` or `automatic`), confirmation
requirement, round cap, normal capability, specialist threshold, and
multi-review rounds.

- [x] **Step 1: Write failing tier-table and arithmetic tests**

  Cover all four explicit tiers; independent maxima of complexity and risk;
  one step when both merged axes are at least `high`; at most one gestalt step;
  `max` saturation; malformed gestalt rejection; exactly two samples; and the
  settled confirmation rule: only automatically derived `max` without
  no-confirm requires confirmation. Prove explicit selection accepts no rating
  samples and rejects supplied samples, while automatic selection rejects any
  count other than two. Extend the CLI contract test with one valid
  `derive_policy` request, compact successful stdout, and exit code `0`.

- [x] **Step 2: Implement pure lookup and arithmetic functions**

  Encode the four-row tier table once. An explicit tier selects policy without
  consulting raters. Automatic selection validates both samples and applies the
  spec's ordered arithmetic exactly; it does not decide whether factors form a
  semantic gestalt.

- [x] **Step 3: Run focused and cumulative tests**

  ```bash
  PYTHONPATH=review-loop python3 -m unittest \
    review-loop/tests/unit/test_state_policy.py -v
  PYTHONPATH=review-loop python3 -m unittest discover \
    -s review-loop/tests/unit -p 'test_*.py' -v
  ```

  Expected: PASS.

### Task 3: Preserve inventory identity, coverage, and complete staffing

**Files:**

- Modify: `review-loop/review_loop/state.py`
- Create: `review-loop/tests/unit/test_state_inventory.py`
- Create: `review-loop/tests/unit/test_state_roster.py`

**Operations:** `refresh_inventory`, `record_specialist_coverage`, `plan_roster`

**Input:** the selected tier, prior canonical areas including any exact
coverage-producing report/scope proof, a fully resolved refresh, explicit
per-area invalidator flags, the inventory's bijective priority order, completed
usable specialist-report coverage events bound to the current seal and frozen
roster, and positive dispatch capacity.

**Result:** canonical active/retired areas with `CURRENT`/`STALE` coverage,
complete specialist roster entries, and ordered capacity-safe waves.

- [x] **Step 1: Write failing strict-inventory tests**

  Cover unique stable IDs; aliases; continuing, successor, new, and `RETIRED`
  mappings; required single-line retirement reasons; consequence/evidence/surface
  union monotonicity; bijective priority order; and rejection of omitted,
  duplicated, unknown, cyclic, or ambiguously mapped IDs. Cover coverage becoming
  `CURRENT` only from a completed usable specialist report whose sealed scope
  includes every active-lineage `SURFACE` owning file. Require the canonical
  coverage record to retain the report ID, seal, resolved owning-file set, and
  reviewed scope set.

- [x] **Step 2: Implement canonical refresh transitions**

  Apply only explicit semantic mappings and invalidator flags. Continuing areas
  retain proven `CURRENT` only with no invalidator. Apply and test each named
  invalidator independently: relevant surface change, dependency change,
  contract change, linked finding reopening, semantic identity change or
  successor creation, and material new inventory evidence for specialist depth.
  Successors and newly eligible areas begin `STALE`; retired areas preserve
  audit history but leave active staffing. Keep this pre-roster refresh separate
  from `record_specialist_coverage`, which applies completed usable scheduled
  reports after specialist review and TRIAGE but before CLOSE. Never infer
  identity, relevance, or scope ownership from a locator.

- [x] **Step 3: Write failing eligibility, staffing, and wave tests**

  Cover each tier threshold; the `max` every-area rule; `GENERALIST-MISS` for
  non-max tiers; eligible Critical restaffing every dispatched round; non-Critical
  `CURRENT` reuse; uncovered-first priority; holistic and adversarial base roles;
  no numeric specialist cap; and capacities that split but never truncate the
  frozen roster.

- [x] **Step 4: Implement complete roster planning**

  Filter the validated total order to all and only required specialists, prepend
  holistic and adversarial, reserve one host slot, and partition the immutable
  roster into waves. Reject capacity below two rather than silently omitting a
  role.

- [x] **Step 5: Run focused and cumulative tests**

  Run both new modules, then the full prototype discovery command. Expected:
  PASS.

### Task 4: Reconcile evidence gates without inventing evidence

**Files:**

- Modify: `review-loop/review_loop/state.py`
- Create: `review-loop/tests/unit/test_state_gates.py`

**Operation:** `reconcile_gates`

**Input:** a target seal and exact planned gate records with controller-decided
applicability (`applicable` or `not_applicable`) and reason, timing (`baseline`
or `post_fix`), classification (`required` or `supporting`), status (`PASSED`,
`FAILED`, or `NOT_RUN`), command, result/evidence, and reason where not run.

**Result:** normalized gate state, evidence gaps, blocking reasons, and whether
semantic review may start or merge-readiness may be considered for that seal.

- [x] **Step 1: Write failing baseline and readiness tests**

  Cover valid empty discovery as a disclosed gap; every executed applicable
  failure blocking; every required gate needing to run and pass; unavailable
  supporting gates remaining non-blocking by themselves; exact seal binding;
  baseline versus post-fix records; non-applicable opportunities with explicit
  reasons; duplicate gate IDs; and missing command/result/reason fields.

- [x] **Step 2: Implement mechanical reconciliation**

  Do not discover commands or judge their safety. Accept only already-validated
  applicability, timing, and gate decisions, preserve exact records, and compute
  the two booleans and explicit reasons from their declared states.

- [x] **Step 3: Run focused and cumulative tests**

  Run `test_state_gates.py`, then full discovery. Expected: PASS.

### Task 5: Apply ledger transitions and adjudication bounce atomically

**Files:**

- Modify: `review-loop/review_loop/state.py`
- Create: `review-loop/tests/unit/test_state_ledger.py`

**Operation:** `apply_ledger_decisions`

**Input:** current rows, proposed TRIAGE decisions, exact raw-finding inventory,
manifest/evidence references, and an optional adjudication-attempt record. That
record carries the original expected ID set, attempt number, retry mode (`full`
or `undecided_subset`), already-settled first-call decisions, the exact pending
subset, and the current call outcome or failure.

**Result:** updated rows, rejected disposition history, pending FIX IDs, and
whether the round became indeterminate, plus the next adjudication-attempt
record when one retry remains.

- [x] **Step 1: Write failing schema and transition tests**

  Cover exact raw finding reconciliation; immutable reported severity/source
  premise; unique canonical IDs and aliases; the five legal states; new/reopened
  findings entering `OPEN`; manifest-bound `OPEN -> FIX_APPLIED`;
  evidence-bound `FIX_APPLIED -> FIX_VERIFIED`; invalid settlement from silence,
  empty reports, gates, or manifest presence alone; and settlement invalidation
  returning to `OPEN`.

- [x] **Step 2: Write failing adjudication tests**

  Cover the complete pending set (refutation, file-authorized intentional, and
  Important+ downgrade); a malformed/crashed first call discarding all output
  and producing one full-set retry; a clean first call retaining settled
  decisions while producing one subset-only retry for `UNDECIDED` rows; a
  malformed/crashed second call bouncing its entire attempted set; clean
  second-call `UNDECIDED` rows bouncing; individual `BOUNCE` restoring the full
  pre-disposition row; and direct ledger-ID-bound user acceptance bypassing
  file-authority adjudication. Reject attempt records whose expected, settled,
  or pending ID sets do not partition the original adjudication obligation.

- [x] **Step 3: Implement atomic copies and explicit transition tables**

  Validate the entire operation before mutating a copied ledger. Apply only
  declared transitions. Preserve rejected bases as non-operative history and
  return the original operative row on every bounce. Materialize the one allowed
  next-attempt record rather than asking the processor to run an agent. Never
  make a third-attempt state representable. Do not read source files or assess
  truth.

- [x] **Step 4: Run focused and cumulative tests**

  Run `test_state_ledger.py`, then full discovery. Expected: PASS.

### Task 6: Model final challenge freshness and terminal verdicts

**Files:**

- Modify: `review-loop/review_loop/state.py`
- Create: `review-loop/tests/unit/test_state_terminal.py`

**Operations:** `record_final_challenge`, `compute_terminal`

**Input:** lifecycle facts, final target seal, gate reconciliation, ledger,
current inventory coverage, and optional final-challenger outcome bound to a
seal.

**Result:** lifecycle outcome (`CANCELLED_BEFORE_REVIEW`, `CONVERGED`, or
`NOT_CONVERGED`), nullable terminal verdict for cancellation, merge-ready
boolean, qualified claim eligibility, and an ordered list of every failed
conjunct or limitation.

- [x] **Step 1: Write failing final-challenge tests**

  Cover `UPHOLD`, material procedural `BLOCK`, source findings requiring
  supplemental TRIAGE, malformed/failed retry exhaustion as INDETERMINATE, and
  automatic staleness whenever the current target seal differs.

- [x] **Step 2: Write failing terminal-rollup tests**

  Prove that convergence requires accepted confirmation where applicable,
  completed Round 1 through TRIAGE, usable scheduled reports, complete raw
  reconciliation, no indeterminate stage, matching final seal, and no Important+
  `OPEN`/`FIX_APPLIED` row. Prove merge-readiness additionally requires fresh
  final `UPHOLD`, all required and every executed applicable gate passing,
  settled Important+ rows, and no active non-retired Important+
  `GENERALIST-MISS` coverage blocker. Open Minor rows and unavailable supporting
  gates remain disclosed but do not independently block. A declined automatic
  `max` confirmation produces `CANCELLED_BEFORE_REVIEW` with no convergence or
  merge-ready verdict; deadline expiry while awaiting confirmation takes
  precedence and produces `NOT_CONVERGED`, never cancellation.

- [x] **Step 3: Implement total, reason-bearing rollups**

  Compute all conjuncts without early return so the hand-back can name every
  failed condition. Return only eligibility for the qualified operational claim,
  never a proof-of-safety string.

- [x] **Step 4: Run focused and cumulative tests**

  Run `test_state_terminal.py`, then full discovery. Expected: PASS.

### Task 7: Measure the prototype and hand it to independent review

**Files:**

- Create: `review-loop/tests/state-processor/RESULTS.md`
- Modify if review requires: `review-loop/review_loop/state.py`
- Modify if review requires: `review-loop/tests/unit/test_state_*.py`

- [x] **Step 1: Run fresh verification**

  ```bash
  PYTHONPATH=review-loop python3 -m unittest discover \
    -s review-loop/tests/unit -p 'test_*.py' -v
  python3 -m compileall -q review-loop/review_loop
  git diff --check
  ```

  Expected: all tests pass, compilation succeeds silently, and the diff has no
  whitespace errors.

- [x] **Step 2: Record measurements and remaining boundaries**

  In `RESULTS.md`, record the public operations, request/response examples,
  production and test line counts, full verification output summary, which
  current `SKILL.md` policy paragraphs the processor could replace, and which
  responsibilities remain semantic/controller work. Do not claim that line
  count alone proves simplicity.

- [x] **Step 3: Run independent prototype review**

  Give a fresh read-only reviewer the governing design, this plan, production
  code, tests, and `RESULTS.md`. Ask specifically about semantic leakage into
  the processor, fail-open validation, incomplete settled-decision coverage,
  accidental target/process access, and unnecessary machinery. Reconcile every
  material finding before accepting the prototype evidence gate.

- [x] **Step 4: Decide the replacement-plan boundary from evidence**

  If the prototype is accepted, write the separate clean replacement plan named
  by design section 10. That later plan applies `writing-skills` RED/GREEN
  directly to `SKILL.md` and behavior-bearing prompts; ordinary governing prose
  uses it only as inspiration. If the prototype exposes an unworkable interface,
  amend and independently review the design before expanding implementation.

## Plan self-review

- Scope: only the state processor and its tests/results are implemented.
- MVP discipline: no numeric specialist/finding caps, `xhigh`, direct external
  phase integration, dependency, workflow engine, target access, or controller.
- Coverage: every behavior required by design section 10's bounded prototype is
  assigned to one task and one focused test module.
- Trust boundary: semantic agents decide meanings; this processor validates and
  applies already-resolved facts.
- Documentation testing: `writing-skills` is direct only when later work changes
  behavior-bearing skill/prompt text, not for this ordinary implementation plan.
