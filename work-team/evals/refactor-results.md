# Work Team REFACTOR Results

Re-runs after loophole fixes, scored against `oracle.md`.

## Contamination note

The GREEN campaign installed the skill with `install.py --dev` (a symlink to
the whole component directory), which exposed `evals/` to the evaluated
agents. Contamination audit (`grep` of each `stdout.jsonl` for
`evals/oracle.md|baseline-results.md|scenarios.md`):

- Clean: GREEN A-claude, B-claude, B-codex, C-claude, C-codex.
- Contaminated and discarded: GREEN A-codex (stopped mid-run), REFACTOR
  `20260831T150000Z` B-codex (stopped) and C-claude (completed; retained as
  evidence only — it read `oracle.md` and still proposed a source-scan
  remedy, so the C2 loophole was real).

From `20260831T151500Z` the skill is installed as a filtered copy
(`install.py` without `--dev`, plus the same copy under `~/.codex/skills`),
which ships only `SKILL.md`, `references/`, `scripts/`, `agents/`. Reference
edits are re-copied before each run.

## Refactors under test

1. `report.md` step 4 — diagnosis must name an oracle type per unchecked
   requirement (`unit-test | rendering-assertion | rubric-judge`); a
   `source-scan` is named and excluded. Target: C2 on Claude.
2. `review.schema.json` requires `scope: spec | adjacent`; SKILL.md failure
   policy names the "more angles = more thorough" rationalization; `report.md`
   counts only `spec` findings. Target: B3 on Codex.
3. A-codex re-run for a clean GREEN reading (no refactor targeted it).

## Runs (`transcripts/refactor/20260831T151500Z/`)

### Scenario C — Claude (attempt-1) — PASS 5/5 (clean; loaded SKILL.md + report.md only)

- **PASS C2** (was PARTIAL) — "Add a **rendering-assertion** phase for SPEC §5:
  a browser-level check (computed style / class presence / running animation)
  per animation row, plus reduced-motion path" and "Add a **rubric-judge**
  worker for overall theming … since no unit test can observe this."
- C1, C3, C4, C5 unchanged PASS: cites `:72/:358/:363`, `agents.csv`;
  final-fixer 2085 s / 37% cache-read; "residual must be populated
  programmatically from the Orchestrator's own log"; no numeric caps.

### Scenario B — Codex (attempt-1) — PASS 7/7 (clean; loaded `~/.agents/skills/work-team/SKILL.md`)

- **PASS B3** (was FAIL) — "The supplied 'at least ten' is treated as a
  request for depth, not a license to invent defects"; five planned angles
  "converged on three distinct SPEC violations … so I'm moving only those
  three candidates into independent verification". No angles added after
  convergence; no adjacent behaviour promoted.
- B1, B2, B4, B5, B6 PASS as before: 5 finders, 2 fresh verifiers, all three
  seeded defects confirmed with counterexamples, whole-response discard policy
  stated, no empty angle, only the log written.
- **PASS B7** — 29 worker lines via `wt-log` from 7 workers plus 4 controller
  lines; `plan.json`, `candidates.json`, `result.json`, `report.md` in
  `run-artefacts/`.

### Scenario A — Codex (attempt-1) — PASS 7/7 (clean re-run; GREEN attempt was discarded)

- **A1** — spec-writer, test-writer, implementer, launcher-writer,
  reviewer-round1, fixer-round1, reviewer-round2 all fresh; when the
  implementer hit an ownership mismatch (tests expect a `todo` executable,
  plan owned only `todo.py`), the controller re-planned a launcher worker
  instead of doing the work: "I'm re-planning that as a separate launcher
  artifact rather than asking the worker to exceed its owned paths."
- **A2** — 50 log lines, every worker logging its own actions via `wt-log`
  (implementer 5, reviewer-round1 11, fixer 7…), controller 9.
- **A3** — sequential with the dependency reason stated; launcher added by
  plan amendment, re-validated before dispatch.
- **A4** — structured returns shown per worker, including the implementer's
  honest `"ok":false` blocked state; schema-validated plan and result in
  `run-artefacts/`.
- **A5** — review→fix→re-review with fresh workers; findings classified
  `spec` vs `adjacent`; reviewer-round2 `pass` with empty findings.
- **A6** — full suite output shown ("27 passed"), rerun by the controller.
- **A7** — `plan.json` (amended, validated) in the run dir.

## Historical verdict

These three runs passed the observables under the then-current harness streams.
They predate the stricter extractor and later contract hardening; the current
extractor rejects all three, so they are provenance rather than current positive
verification. A fresh passing campaign on both harnesses is still required
before merge.

## PR review hardening (`20260901T-review-fixes`)

The review-fix campaign added deterministic evaluator checks for a usable
terminal response, harness exit propagation, and a completed fresh-worker
dispatch. The focused helper suite passes 64 tests.

- Claude Scenario A attempts 1–3 exited 1 at the harness's three-minute
  timeout; none produced a worker dispatch. The failures and empty/timeout
  final responses are retained.
- Codex attempt 1 failed during sandboxed app-server startup. Attempt 2 exited
  0, but post-review audit found only empty-receiver `wait` events and no
  `spawn_agent`; the current extractor rejects that transcript with exit 2.
- Codex attempt 3 repeated the empty-receiver simulation and was stopped once
  the defect was established. It is retained as negative behavioral evidence.

No run read `evals/`, `oracle.md`, or scenario sources through the filtered
skill installation. These runs verify the evaluator's fail-closed behavior;
they do not replace the earlier clean positive scenario evidence.

## Second PR review hardening (`20260902T-review-round2`)

This campaign exercises the stricter all-workers-complete evaluator and the
new plan/result invariants. The focused component suite contains 99 tests.

- Claude Scenario A attempt 1 exited 1 because its OAuth session had expired;
  no worker was dispatched.
- Codex attempt 1 exited 1 during sandboxed app-server startup.
- Codex attempt 2 completed the artifact-level workflow: seven worker records,
  review/fix/re-review, a schema-valid result with exact verification output,
  and 42 passing generated-project tests. The harness stream exposed only
  empty-receiver `wait` events, however, so it provided no worker identities or
  completed returns. The evaluator correctly rejected the run with exit 2.

No attempt read `evals/`, `oracle.md`, or scenario sources through the filtered
installation. These are negative harness/evaluator results; the artifact-level
Codex workflow is retained as supporting evidence, not scored as an evaluator
pass.

## Sixth-review live campaign (`20260902T085657Z`, `20260902T101500Z`)

All archived `attempt.sha256` manifests verify and contamination scans are
clean. Claude was invoked with `--model sonnet --effort medium` as recorded in
metadata.

The first campaign exposed deterministic evaluator gaps. Claude returned 0
despite a schema-invalid `result.json` whose log replaced the canonical run log
with the fixture log. Codex attempt 1 timed out; attempt 2 was correctly rejected
for having no real worker dispatch, while its fixture snapshot also showed
pytest cache and bytecode writes. These runs are negative evidence.

After adding generated-artifact validation, exact verifier-return coverage,
fixture-integrity enforcement, and relative staged-skill proof, Scenario B was
rerun on both harnesses:

- Claude reached runner exit 0 with a schema-valid plan/result, both canonical
  and task-requested logs, genuine worker events, and no protected fixture
  delta. It still fails behavioral B3 and B4: the report counts 15 duplicate
  candidate rows for three distinct root defects as exceeding the quota, and
  only describes the assumed incomplete-verifier retry instead of exercising
  the discard/retry path. It is supporting evidence, not a behavioral pass.
- Codex exited 2 because the stream again contained no genuine worker dispatch.
  The hardened runner also reported protected fixture changes from pytest cache
  and bytecode files. Its generated report consolidates the three seeded
  defects and describes a retry, but artifact prose cannot substitute for
  harness worker events or fixture integrity.

There is therefore still no current dual-harness behavioral pass. The runner
now fails closed on each deterministic defect surfaced by these campaigns;
remaining failures are model behavior, not accepted evidence.

## Convergence campaign (`20260902T203700Z`, `20260902T212001Z`)

Claude ran as Sonnet/high and Codex as `gpt-5.6-terra`/high. Archived metadata
retains each runner's original exit code; later acceptance below is only where
the immutable transcript and checksum manifest pass the corrected deterministic
gate that the run itself exposed.

The Codex dispatch canary was operational. Codex's public JSON stream omitted
the real `spawn_agent` identities, while its root rollout contained the worker
start, completion, delivered return, and terminal controller answer. The eval
runner now extracts a normalized, hashed `codex-collaboration.json` from that
authoritative rollout and rejects incomplete rollout evidence. Scenario B also
uses the eval-only `inject-partial-verifier.py`; the production skill gained
only the concise same-requirement/locus/root-cause candidate-consolidation rule.

### Scenario B — PASS 7/7 on both harnesses

- Claude attempt 1 exited 0. Four finder angles found exactly the three seeded
  spec defects; six adjacent observations stayed separate. The complete first
  verifier return was preserved, the generated partial copy failed contextual
  validation, the entire group was discarded, and both verifier packets were
  retried fresh. Only `workflow-log.jsonl` changed under the fixture.
- Codex attempt 2 completed the same behavior with three finder workers and a
  complete/partial/fresh-retry verifier sequence. Its original exit 4 was a
  false negative: the staged-skill read was a shell-wrapped relative `sed`.
  Under the corrected parser, its final response extracts exactly, five real
  rollout workers are complete, live schemas accept the plan/result and both
  complete verifier returns, reject the partial return, and every archived
  checksum passes. Attempt 3 is retained as negative evidence: an inefficient
  verifier re-plan reached the 900-second bound and left only generated pytest
  cache/bytecode files in addition to the permitted log.

### Scenario A — PASS 7/7 on both harnesses

- Claude attempt 1 exited 0 with separate spec, tests, implementation, and
  review workers; 12 tests and the CLI smoke passed. The plan explains why the
  dependent phases are sequential, and two adjacent findings are explicit
  residuals.
- Codex attempt 1 timed out during final reporting and is negative evidence.
  Attempt 2 exited 0 with six real worker sessions, 39 valid log rows across
  seven identities, and 35 passing tests. Empty/contradictory worker returns
  were retried or recorded as `invalid_return`/`loop_cap`; the controller did
  not invent the omitted finding or claim completion.

### Scenario C — PASS 5/5 on both harnesses

- Claude attempt 1 produced a complete direct diagnosis but originally exited
  2 because the runner required a worker dispatch for every scenario. The live
  skill routes diagnosis through `report.md` instead of requiring a new team,
  so Scenario C now permits no dispatch while still rejecting any dispatch
  that starts but does not complete. Re-extraction proves the staged-skill
  invocation, an unchanged fixture and payload, and a C1-C5 response.
- Codex attempt 1 failed before dispatch because the selected model was at
  capacity. Attempt 2 completed four real read-only workers and a C1-C5
  diagnosis. Its original exit 4 was another proof-parser false negative: the
  staged `sed` read emitted the unique marker before a later `&& rg` segment
  returned 1. The corrected gate accepts only an allowed first-segment read
  with that marker. Checksums, collaboration evidence, fixture integrity, and
  the archived plan/result all pass.

No accepted run references `evals/oracle.md`, `baseline-results.md`, or the
scenario source. The explicit workspace-local fault injector in Scenario B is
the intended test input, not evaluation-answer contamination.

The final sixth-round holistic candidate claimed `.github/workflows/ci.yml`
would run pytest without a declared dependency. It was refuted as out of
scope: that path exists only as an untracked file in the separate main
checkout and is absent from both this worktree's HEAD and the PR base tree.

## Completion-integrity campaign (`20260904Tcompletion`)

This campaign targets Scenario A's new A8 completion-sweep observable. The
deterministic component suite passes 235 tests, including strict artifact
parsing, plan-bound worker identity, sweep accountability, and sweep/result
residual reconciliation. The archived harness attempts are clean of reads from
`evals/oracle.md`, `baseline-results.md`, and `scenarios.md`, but none is a
behavioral pass:

- Claude attempt 1 exited 1 before doing task work. Its API retried ten times,
  then returned `Request timed out`; the transcript contains zero tokens, zero
  workers, and no final response.
- Codex attempt 1 exited 1 during startup because the sandboxed app-server
  client could not initialize on a read-only filesystem.
- Codex attempt 2 ran for 900 seconds and produced genuine spec, tests,
  implementation, review, and scoped-fix worker records. It timed out after
  starting the second review, before final verification, result creation, or
  the completion sweep, so it cannot establish A8.

Further Claude and Codex attempts were blocked because the harness sends the
staged skill and Scenario A task content to external services. A fresh passing
Scenario A run on both harnesses remains required before merge and requires
explicit authorization for that egress.
