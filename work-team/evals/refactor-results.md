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

## Verdict

All targeted loopholes closed; 3/3 clean re-runs pass every observable. The
remaining known limitation: Scenario A on Claude was scored on the GREEN run
only (7/7, clean) and not re-run after the refactors — the refactors do not
touch any behaviour that run exercised.

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
