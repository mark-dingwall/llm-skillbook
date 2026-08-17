# MVP acceptance record

Evidence-linked status against the governing design's Sec. 9 "Acceptance
criteria" list
(`docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`), plus
the behavioral acceptance the Task 12 brief requires. PASS means committed,
passing deterministic evidence exists at the cited path(s) as of this
commit (all 458 review-loop + 394 multi-review tests green, see "Suite
run" below). BEHAVIORAL rows are `[controller fills]` placeholders —
`tests/behavior/FINAL.md` is the scaffold; this task does not fabricate
their result.

## Suite run (this commit)

- `cd review-loop && python3 -m unittest discover -s tests -t .` — **458
  passed, 1 skipped**. The skip is Task 11's disclosed `I2` residual
  (`tests/integration/test_multi_review_containment.py` — the post-publish
  forge-race test is non-deterministic by nature and is documented, not
  hidden, when it loses the race; see the `[I2 residual, documented]`
  stderr line and Task 11's residuals below).
- `cd multi-review && uv run pytest -q` — **394 passed**. Previously 393
  passed / 1 failed (`test_headless_driver_smoke_harness.py::
  test_plain_workload_resolves_every_reviewer_from_overrides_with_restricted_path`).
  **Root-caused and fixed in this task**: `tests/manual/
  headless-driver-smoke.sh` derived `repo_root` via `git -C "$script_dir"
  rev-parse --show-toplevel`, which resolves to an *enclosing* repository
  when `multi-review/` is nested in a monorepo/worktree without its own
  `.git` (exactly this repository's layout) instead of to `multi-review/`
  itself, which every `$repo_root` use in that script actually expects.
  Fixed to derive `repo_root` from the script's own fixed location
  (`$script_dir/../..`) instead of Git. This was a path-resolution bug in
  test infrastructure, unrelated to review-loop's production code, and
  independently reproducible before the fix; the fix is a 6-line,
  git-independent path change with no behavior change once `repo_root`
  resolves correctly.
- `git diff --check` (repo root) — clean, no whitespace errors.

## Deterministic acceptance criteria

| # | Criterion (design Sec. 9, paraphrased) | Evidence | Status |
|---|---|---|---|
| 1 | Explicit and automatic tier paths produce the specified roster/round policy without changing completion semantics | `tests/unit/test_state_policy.py`, `tests/integration/test_controller_clean.py`, `tests/integration/test_cli.py` (intent capture) | PASS |
| 2 | Auto-derived `max` is the only automatic tier that pauses; explicit `max`/explicit no-confirm proceed without prompting | `tests/unit/test_state_policy.py`, `tests/integration/test_findings_loop.py` (confirmation paths) | PASS |
| 3 | One canonical inventory survives independent scope challenge; every Critical/coverage-eligible specialist is scheduled with no numeric cap; concurrency waves never omit a required role | `tests/unit/test_state_inventory.py`, `tests/unit/test_state_roster.py`, `tests/integration/test_findings_loop.py` | PASS |
| 4 | Specialist coverage changes only via declared `CURRENT`/`STALE` events; eligible Critical areas staffed every dispatched round | `tests/unit/test_state_inventory.py`, `tests/unit/test_state_roster.py`, `tests/unit/test_state_terminal.py` | PASS |
| 5 | All three helpers (state processor, prompt/report contract, multi-review adapter) fail closed at their declared boundaries | `tests/contract/test_projection_authority.py`, `tests/unit/test_role_contracts.py`, `tests/unit/test_strict_role_outputs.py`, `tests/unit/test_multi_review_adapter.py` | PASS |
| 6 | Evidence discovery records applicable gates/gaps, executes only safe validated commands under contained mapping, never installs tooling, distinguishes required vs. supporting | `tests/unit/test_evidence.py`, `tests/integration/test_evidence_execution.py` | PASS |
| 7 | Every non-FIX target-accessing role has sealed read-only inputs and isolated write surface; special entries, run-root overlap, missing delta contract, concurrent-writer uncertainty, interrupted FIX, post-FIX gate failure, final seal drift all fail closed | `tests/integration/test_execution_containment.py`, `tests/integration/test_preflight.py`, `tests/unit/test_fix.py`, `tests/integration/test_findings_loop.py` | PASS |
| 8 | The sole FIX role is ledger-bound and contained; every target change is manifest- and delta-validated; unrelated/external actions cannot advance state; passing gates alone never verify a fix | `tests/unit/test_fix.py`, `tests/integration/test_findings_loop.py` | PASS |
| 9 | Existing mutation tooling or bounded manual mutation contributes supporting evidence without installation, score thresholds, or false terminal authority | `tests/unit/test_mutation_evidence.py` | PASS |
| 10 | Every usable review report reconciled through validated TRIAGE into the ledger from its exact source-finding inventory; only evidence-linked transitions affect the two terminal verdicts | `tests/unit/test_state_ledger.py`, `tests/unit/test_state_terminal.py`, `tests/contract/test_triage_projection.py` | PASS |
| 11 | Pending green-making dispositions get tier-invariant adjudication, fail closed under malformed/failed/undecided; empty set dispatches no adjudicator | `tests/unit/test_state_ledger.py` (adjudication paths), `tests/integration/test_findings_loop.py` | PASS |
| 12 | Normal and multi-review holistic paths use the same canonical prompt | `tests/unit/test_multi_review_adapter.py` (byte-equivalent verbatim prompt tests) | PASS |
| 13 | Multi-review's verbatim custom-prompt opt-in delivers exact canonical bytes or falls back without launching a wrapped prompt | `multi-review` suite (`prompt_format_version: 2` opt-in tests), `tests/unit/test_multi_review_adapter.py` | PASS |
| 14 | Every scheduled high/max multi-review slot uses the fixed CLI pair at tested defaults or exact explicit pins, with resolved fallback | `tests/unit/test_multi_review_adapter.py`, `tests/unit/test_profiles.py` (multi-review model-pin tests) | PASS (mechanism); **NOT DEFAULT-WIRED** — see "Multi-review activation" below |
| 15 | Every multi-review call uses one fresh round output directory and disposable whole-call home/scratch; live host client state non-writable; malformed/interfered output cannot become usable evidence; shared-namespace limitation disclosed; seal drift voids the round instead of falling back | `tests/integration/test_multi_review_containment.py` (real Bubblewrap), `tests/integration/test_multi_review_fallback.py` | PASS, with disclosed residuals (I1/I2 below) |
| 16 | Profiles can refine dispatch but cannot alter safety or convergence | `tests/unit/test_profiles.py` | PASS |
| 17 | State survives host/session restarts outside the sealed target without rebasing a deadline, including round-one ground truth and audited retirement mappings | `tests/integration/test_preflight.py` (deadline persistence), `tests/unit/test_state_*` | PASS for single-round recovery; **multi-round crash-recovery from a published boundary is deferred** (Task 9 ruling — no consumer yet) |
| 18 | A fresh independent final-readiness challenge can only uphold or block the mechanically eligible verdict, routes new findings through TRIAGE, becomes stale after any target change | `tests/unit/test_state_terminal.py`, `tests/integration/test_findings_loop.py` (`run_final_challenge`) | PASS for `UPHOLD`; **`BLOCK` → supplemental-TRIAGE handling is an explicit fail-closed stub** (`Controller.run_final_challenge` raises `ControllerError` rather than silently no-op — deferred, see Task 8/9 rulings) |
| 19 | Final report explains selected policy, staffing, gates, mutation evidence, degraded/fallback, evidence gaps, ledger state, both verdicts | `review_loop/report.py`, `tests/unit/test_*` exercising `generate_report` indirectly via `tests/integration/test_cli.py::test_report_writes_markdown_and_prints_its_path` | PASS for structure; some sections are currently static placeholders, not yet state-derived (see Task 6 minor, carried) |
| 20 | Merge-ready means the qualified "no known material defect" claim, never proof | `SKILL.md` ("North Star"), `review_loop/report.py` | PASS (documentation + report wording) |
| 21 | `SKILL.md` reviewed after implementation for missed behavior and needless residue, effectiveness over an arbitrary size target | This task's rewrite (see `SKILL.md`, "What was removed" below) | PASS for the rewrite itself; independent spec-compliance/quality review is Step 6, run by the controller after this report |

## Behavioral acceptance (Task 12 brief Steps 1 and 5)

`tests/behavior/FINAL.md` is the scaffold: 9 pressure scenarios (automatic
effort, `max`-confirmation exceptions, code target with tests,
technical-document target with/without mechanical gates, findings requiring
FIX, missing mutation tooling, excess required specialists, failed
reviewer, final readiness), each with RED (legacy `SKILL.md`) and GREEN
(this rewrite) rows.

| Row | Status |
|---|---|
| All 9 scenarios | `NOT RUN` — `[controller fills]`. This task (implementer) drafted the rewrite and the scaffold only; the brief's Step 1/5 fresh-context RED/GREEN controls are the controller's dispatch, per the task split in the team-lead's message. |

Per-role prompt-resource behavioral probes (`tests/behavior/SCENARIOS.md`,
`RED.md`, `GREEN.md`) are a **separate**, already-partially-run Task 3
artifact (2 of 7 scenarios run live: FIX authorization, final readiness —
both null results; the remaining 5 — rating calibration, inventory
identity/coverage, evidence-gate selection, inventory challenge, canonical
review output — are static-contract-tested only, per Task 3's explicit
carry-forward: "run the remaining GREEN acceptance at Task 12 before
claiming end-to-end behavioral verification"). **This carry-forward is
NOT closed by this task** — it is the controller's Step 5 scope, not
drafted here beyond this disclosure.

## Multi-review activation decision

**Decision: document as available-but-not-default-wired (opt-in), not
wired into the live path.**

`MultiReviewAdapter` (`review_loop/multi_review.py`) and
`Controller.run_round1`'s `multi_review_dispatch` parameter are fully
implemented and tested (43 adapter tests including real-Bubblewrap
containment), but no production caller in this codebase constructs a
`MultiReviewAdapter` with a real OAuth credential source and
profile-derived model pins and passes it into `run_round1` for a live
`high`/`max` run — this was Task 11's explicit carry-forward to Task 12.

This task's `SKILL.md` ("Multi-review (opt-in, not default-wired)")
documents the slot, how to construct and pass it, and its disclosed
residual limitations, rather than silently wiring it in. Rationale: wiring
it into a default path requires a design decision this task is not
positioned to make silently — specifically, where the OAuth credential
source comes from for a non-interactive CLI/host driver that does not yet
exist (see "`__main__.py` scope" below) and whether every `high`/`max` run
should pay the multi-review cost and accept its residuals by default versus
opting in. Per the team-lead's message, this is a defensible honest MVP
choice for a system whose residuals (OAuth-token sharing under whole-call
containment, a post-publish forge-race) are already disclosed and
Task-11-accepted as interim limitations, not new risk introduced here.

**Multi-review's live Bubblewrap smoke: NOT RUN in this session.**
Real-network/real-provider paths — `multi-review/tests/manual/
headless-driver-smoke.sh`'s live shutdown-matrix runs and
`review-loop/tests/manual/ordinary-codex-smoke.sh --live` — require real
provider API access/spend and are explicitly out of scope for an
unattended, non-interactive automated task; they were not authorized or
run here. The **non-network** real-Bubblewrap containment tests (mount
isolation, credential/network denial, process-tree termination, fake
CLIs standing in for the real ones) DID run and pass as part of the 852
combined tests above (`test_multi_review_containment.py`,
`test_execution_containment.py`, and `--preflight`-only smoke, all
credential-free).

## Residual limitations (carried forward, not introduced by this task)

- **Single-round FIX only.** Multi-round TRIAGE-reconcile onto prior
  canonical rows (reopen, coverage invalidation, successor `STALE`,
  Critical restaffing, oscillation, round caps) needs governing-seal
  advancement that Task 9's MVP ruling explicitly deferred;
  `Controller.run_triage`/`run_adjudication` fail loudly (`ControllerError`)
  rather than silently reinitializing or skipping if called a second time.
- **Crash recovery** resumes only from a fully published phase boundary;
  there is no consumer-tested `recover()` path yet (Task 9 ruling: building
  one now would be speculative — "no consumer today").
- **`CANCELLED_BEFORE_REVIEW` and an awaiting-confirmation `INDETERMINATE`
  have no durable canonical marker** — both are in-memory-only outcomes of
  a stopped `run_stage0` call (documented in `RunState`'s own docstring).
  This task's `__main__.py status` command therefore cannot distinguish
  either from a plain mid-Stage-0 crash on recovery; it reports `STAGE0`
  for all three. Disclosed in `dispatch.md`, not hidden.
- **`MutationResult` has no durable canonical-state home** —
  `Controller.record_mutation_result` is an explicit fail-closed stub
  (Task 9 ruling: "always-supporting, never gates -> stub costs nothing").
- **Final-readiness `BLOCK`'s supplemental-TRIAGE handling is a fail-closed
  stub**, not implemented (`Controller.run_final_challenge` raises rather
  than silently no-oping).
- **The kernel's `CONVERGED`-vs-`merge_ready` collapse** (design allows
  "converged, not merge-ready"; the current kernel conflates them,
  safe-direction/over-strict per Task 9's ruling) is unresolved — flagged,
  not fixed, since it needs `state.py` kernel changes outside every task's
  file scope so far.
- **Multi-review's Task 11 disclosed residuals**, applicable whenever it
  runs: (I1) the OAuth credential is inherited by both fixed reviewer
  processes under interim whole-call containment — a prompt-injected
  reviewer could exfiltrate it (network stays on by design); (I2) a
  reviewer that wins the post-publish teardown race can in principle forge
  output that passes strict validation — protection is race timing, not
  the validator (the skipped test in this run's suite is this exact race,
  non-deterministic by nature); (interpreter) a dereferenced host
  interpreter is seeded into writable scratch because `uv --offline` could
  not otherwise find a compatible interpreter on this host. Full closure
  needs multi-review's planned per-reviewer native Bubblewrap profile
  (explicitly deferred, not an MVP prerequisite per the design).
- **`report.py`'s "Mutation evidence" and "Degraded behavior" sections are
  still static placeholder text**, not yet derived from
  `run_mutation_evidence`/roster-degradation state (Task 6 minor, carried,
  not addressed by this task — out of this task's assigned file scope).
- **`__main__.py`'s production scope is preflight/status/report only.**
  Stage 0 through CLOSE dispatch (the actual reviewer/scout/inventory/
  triage/FIX/adjudication/final-challenge calls) has no CLI or "host
  driver" implementation in this codebase yet — it must be driven by
  importing `Controller` directly and supplying real dispatch callables,
  per `SKILL.md`. Building that full driver was judged out of this task's
  scope: it requires wiring `execution.Executor` + `prompts.py` rendering
  + per-role strict validators together for all nine dispatched roles, a
  large, security-relevant surface that the brief did not list in this
  task's file scope (`controller.py`/`profiles.py` were touched only
  minimally and additively — see "Small additive changes" below — and
  `execution.py`/`prompts.py`/`evidence.py`/`fix.py` were not touched at
  all) and that deserves its own dedicated implementation + review pass
  rather than being improvised here. This is a real scope gap, disclosed
  rather than silently narrowed: an operator cannot currently run a full
  review loop through `__main__.py` alone.
- **`$XDG_STATE_HOME/review-loop/runs/<project-id>/<run-id>/` default
  run-root derivation was unimplemented anywhere in the codebase before
  this task** (design Sec. 6 names the path shape; no prior task built it).
  This task added a minimal implementation (`__main__.py::
  _default_run_root`, SHA-256-derived project-id, UUID4 run-id) scoped
  entirely to the CLI; it is not a shared/tested contract other code
  depends on, and its exact encoding is this module's own choice, per the
  design's explicit allowance ("their exact encoding is an implementation
  detail covered by unit tests" — covered here only by
  `tests/integration/test_cli.py::
  test_default_run_root_is_derived_under_xdg_state_home`).

## Small additive changes made in this task, outside the brief's listed files

- `review_loop/profiles.py`: added `InvocationIntent.tier: str | None = None`
  (new field, default `None`, keyword-only construction unaffected —
  verified against every existing `InvocationIntent(...)` call site, all
  keyword-based). Justified directly by design Sec. 4: "Resolve invocation
  intent before dispatch: optional tier, profile, maximum time in seconds,
  and confirmation override" — tier was named there as invocation-level
  intent but had no field to carry it. It is captured/disclosed, never
  derived: `Controller.create_run` still performs no rating dispatch.
- `review_loop/controller.py`: one line, threading `intent.tier` into the
  persisted `preflight.invocation_intent` dict (additive key on an existing
  dict; no test asserts exact-equality on that dict's key set — verified).

Both changes are small, additive, keep `state.py`/kernel operations
untouched, and are flagged here explicitly for the controller's independent
review (Step 6) rather than silently expanded beyond the brief's listed
file scope.
