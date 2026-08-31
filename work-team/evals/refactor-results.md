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
