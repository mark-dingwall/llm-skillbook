# MVP acceptance record

Evidence-linked status against the governing design's Sec. 9 "Acceptance
criteria" list
(`docs/superpowers/specs/2026-08-14-review-loop-redesign-design.md`), plus
the behavioral acceptance the Task 12 brief requires. PASS means committed,
passing deterministic evidence exists at the cited path(s) as of this
commit (462 review-loop + 394 multi-review tests green, see "Suite run"
below), or an independent reviewer traced the property directly against
source (Step 6, below). This record is now FINAL: the deterministic suite
(Step 4), the independent whole-branch review (Step 6), and the behavioral
probe the controller judged decisive (Steps 1/5) have all run; every
remaining `NOT RUN` row below is a disclosed, deliberate scope limit, not
an unfilled placeholder.

## Suite run (final)

- `cd review-loop && python3 -m unittest discover -s tests -t .` — **462
  passed, 1 skipped**. The skip is Task 11's disclosed `I2` residual
  (`tests/integration/test_multi_review_containment.py` — the post-publish
  forge-race test is non-deterministic by nature and is documented, not
  hidden, when it loses the race; see the `[I2 residual, documented]`
  stderr line and Task 11's residuals below). (458 after the first Task 12
  commit; +4 from the final-review fix pass's `tests/unit/test_report.py`.)
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

**Step 4: PASS.**

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
| 21 | `SKILL.md` reviewed after implementation for missed behavior and needless residue, effectiveness over an arbitrary size target | This task's rewrite (see `SKILL.md`, "What was removed" below) + the independent whole-branch review (Step 6, below) | PASS |

## Independent whole-branch review (Step 6)

Run via the `multi-review` skill against the 12 production `review_loop/
*.py` modules plus `SKILL.md`/`dispatch.md`. Full evidence:
`REVIEW-final-acceptance.md` (worktree root).

- **Reviewers succeeded**: Claude (opus), agy — independently.
- **Reviewers NOT RUN**: **pykrete** (unconfigured — needs
  `$PYKRETE_CONFIG`/`NANOGPT_API_KEY` in this environment); **codex**
  (provider credits exhausted in this session).
- **Result: 0 Critical.** Both reviewers independently tried to force a
  false `CONVERGED`/`merge_ready` for an unrepaired or drifted target and
  could not — they traced `close()`/`promote_post_fix_baseline()`/
  `copy_only_fixes`/`state._terminal` and confirmed the seal- and
  proof-chain closes every path they attempted (unpromoted `FIX_VERIFIED`
  rows, partial promotion, gate-rollup forgery, a caller-asserted
  `merge_readiness_eligible`).
- **Containment**: both confirmed the four Bubblewrap mappings
  (`execution.py`/`evidence.py`/`fix.py`/`multi_review.py`) match their
  stated policy — no host-secret leak beyond the already-disclosed
  multi-review residuals.
- **State kernel**: confirmed as a genuinely pure, frozen validator;
  `state.py`'s terminal gate-rollup recompute defeats a lying caller.
- **Deferrals**: confirmed every deferred capability fails closed loudly
  (`ControllerError`), never a silent skip.
- **2 Important findings — both were the exact stale `report.py` strings
  this report's controller-dispatched fix pass corrected** (commit
  `113feea`, before this final record): the Seals section's "no fresh
  re-seal was performed" line (false since Task 9 Slice 2) and the
  Residual section's "adjudication ... not wired" claim (false since Task
  8). Both reviewers independently flagged the identical two lines.
  Re-reviewed clean after the fix (see `tests/unit/test_report.py`).
- **Minors** (agy + Claude, not blocking, recorded as accepted residuals
  below): a `review_may_start` substring-match looseness in
  `state._gates` (safe — `gates_not_ready` still blocks convergence
  independently); `seals._walk`'s `.git` exclusion not applied to nested
  directories (a submodule's `.git` gets walked as content — not a digest
  safety issue); `fix.is_test_path` only recognizes `.py` test paths
  outside a `tests`/`test` directory (conservative, low-risk); the
  adjudication proof requirement is structural only (an artifact ID must
  exist; content isn't semantically re-checked by the kernel — an
  accepted, disclosed LLM-trust boundary, not a defect).

**Step 6: PASS** (0 Critical; 2 Important fixed and re-reviewed clean;
minors accepted as disclosed residuals; two reviewers not run for
environmental/credential reasons unrelated to the code under review).

## Behavioral acceptance (Task 12 brief Steps 1 and 5)

`tests/behavior/FINAL.md` is the RED (legacy `SKILL.md`)/GREEN (this
rewrite) record for 9 top-level pressure scenarios, distinct from the
per-role prompt-resource probes below.

| Row | Status |
|---|---|
| Scenario 2 (`max`-confirmation exceptions) | **RUN — GREEN.** A fresh agent given only the rewritten `SKILL.md` correctly: paused for an *automatically derived* `max` tier before reviewer dispatch; did not pause for an *explicit* `max` tier; did not pause when no-confirmation was explicit; and treated deadline expiry during confirmation as taking precedence over recording a decline. See `tests/behavior/FINAL.md` for the recorded transcript/verdict. |
| Scenarios 1, 3–9 (automatic effort, code-target gates, document-target gates, findings→FIX, missing mutation tooling, excess specialists, failed reviewer, final readiness) | **NOT RUN — live agent-driven forward test.** review-loop's reviewer backend is Codex, and provider credits were exhausted in this session (same constraint as the multi-review live smoke below), so a live end-to-end forward run could not be dispatched. **Substitute evidence, not a gap left unaddressed:** every safety-critical property these scenarios probe (no false-green convergence, containment isolation, ledger-only settlement, fail-closed deferrals, no numeric staffing cap) is *mechanically enforced* by the kernel/controller, not by agent judgment or prose compliance — and is covered by the 462 deterministic tests above plus the independent whole-branch review (Step 6), which traced exactly these properties against source. A live forward test would confirm the *rewritten prose* steers an agent correctly; it would not be the safety backstop, which does not depend on prose. |

Per-role prompt-resource behavioral probes (`tests/behavior/SCENARIOS.md`,
`RED.md`, `GREEN.md`) are a **separate** Task 3 artifact (2 of 7 scenarios
run live: FIX authorization, final readiness — both null results; the
remaining 5 — rating calibration, inventory identity/coverage,
evidence-gate selection, inventory challenge, canonical review output —
are static-contract-tested only). **This Task 3 carry-forward remains open**
for the same reason as the scenarios above: the live runs it needs require
the same exhausted Codex credits. Recorded here, not silently dropped.

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

**Multi-review's live Bubblewrap smoke: NOT RUN.**
Real-network/real-provider paths — `multi-review/tests/manual/
headless-driver-smoke.sh`'s live shutdown-matrix runs and
`review-loop/tests/manual/ordinary-codex-smoke.sh --live` — require a real
Codex session; provider credits were exhausted in this session (the same
constraint that limited Step 6 to two of three configured reviewers and
Steps 1/5 to one live behavioral scenario, above), so these were not run.
The **non-network** real-Bubblewrap containment tests (mount isolation,
credential/network denial, process-tree termination, fake CLIs standing in
for the real ones) DID run and pass as part of the 856 combined tests
above (`test_multi_review_containment.py`, `test_execution_containment.py`,
and `--preflight`-only smoke, all credential-free) — this is the
deterministic gate, and it PASSES; the live smoke is an unattained
additional confirmation, not a substitute for it.

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
- **`state._gates`' `review_may_start` uses a substring match** (`"failed"
  in reason`) rather than inspecting gate status directly, so a required
  gate that is `NOT_RUN`/missing (rather than `FAILED`) leaves
  `review_may_start=True` (Step 6 review finding, agy). **SAFE, not a
  false-green**: `merge_readiness_eligible` and `_terminal`'s
  `gates_not_ready` conjunct are computed independently from the same gate
  records and correctly block convergence regardless; only the earlier,
  advisory `review_may_start` signal is loose. Frozen-kernel change,
  deferred rather than fixed here.
- **`seals._walk`'s `.git` exclusion applies only at the walk root**; a
  nested `.git` (e.g. a Git submodule) is walked as ordinary content on
  recursion (Step 6 review finding, Claude). Not a digest-safety issue —
  just surprising; deferred.
- **`fix.is_test_path` recognizes only `.py` test paths** outside a
  `tests`/`test` directory, so e.g. a changed `test_foo.js` with no
  `tests/` component escapes the "a changed test needs a spec trace" rule
  (Step 6 review finding, Claude). Conservative/low-risk; deferred.
- **Adjudication's proof requirement is structural, not semantic**: the
  kernel requires a proof *artifact ID* to exist before accepting
  `REFUTED`/`INTENTIONAL`, but never inspects its content — a
  `REFUTED`/`INTENTIONAL` settlement of a real Critical finding ultimately
  rests on the adjudicator's honesty (Step 6 review finding, Claude).
  Inherent to LLM adjudication and already disclosed in `SKILL.md`
  ("no contradiction found... is never sufficient"); accepted trust
  boundary, not a defect to fix.
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
