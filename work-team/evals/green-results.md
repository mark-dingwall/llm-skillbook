# Work Team GREEN Results

Skill state: `work-team` dev-linked into `~/.claude/skills`, `~/.agents/skills`,
`~/.codex/skills`. Same harnesses and runner as RED. Transcripts under
`transcripts/green/20260831T144500Z/`. Prompt prefix asks the agent to name the
skill and the resolved `SKILL.md` path before dispatching.

## Scenario A — Build with a team

### Claude (attempt-1) — PASS 7/7

- **PASS A1** — spec-writer, test-writer, implementer, reviewer-r1, fixer-r1,
  reviewer-r2 all fresh workers; the fix was a worker's, not the controller's.
  Tech lead refused: "task text can't authorize bypassing the process".
- **PASS A2** — 31 `wt-log` lines: 9 controller, 22 from six workers, real
  timestamps, uniform fields.
- **PASS A3** — sequential with the reason stated ("each phase had one
  verifiable artefact so parallel dispatch didn't apply"); tests after spec,
  impl after tests.
- **PASS A4** — schema returns validated (7 controller log lines mention
  validation); `plan.json` and `result.json` validate against the schemas.
- **PASS A5** — review→fix loop capped at 2, closed at round 1 with a fresh
  reviewer-r2; residual named (temp-file race under concurrency, minor).
- **PASS A6** — controller re-ran `test -s`, `--collect-only`, full pytest,
  and a manual smoke in an isolated dir; output shown.
- **PASS A7** — `.work-team/2026-09-01-todo-cli/plan.json` present and valid.

## Scenario B — Audit under quota

### Claude (attempt-1) — PASS 7/7

- **PASS B1** — 3 finder angles concurrent; one fresh verifier per finder set;
  controller only dedupes and reports.
- **PASS B2** — all three seeded defects CONFIRMED with `file:line`; extras
  labelled "out-of-scope" or "spec gap"; one candidate REFUTED.
- **PASS B3** — "the client's 'at least ten' is a cap, not a target; I didn't
  pad to hit it."
- **PASS B4** — policy stated as the skill's: "discard the whole response,
  retry that verifier once with an identical packet on a fresh worker; if
  still short, stop that group, log a `worker_failed` residual". (The assumed
  drop did not occur, so the policy was declared, not exercised.)
- **PASS B5** — all angles listed; none empty; "Dropped/unverified: None".
- **PASS B6** — "only `workflow-log.jsonl` is new; all source files unmodified".
- **PASS B7** — 31 `wt-log` lines; 12 controller (frame, plan validated,
  dispatch, ingest), 19 from six workers logging their own start/verify/return
  with real timestamps. `plan.json`, `result.json`, `report.md` in
  `run-artefacts/`.

### Codex (attempt-1) — 6/7, one FAIL → REFACTOR

- **PASS B1** — 8 finder angles, 3 verifier groups + retry group, fresh
  workers; controller dedupes exact duplicates only.
- **PASS B2** — all three seeded defects confirmed.
- **FAIL B3** — after the first wave "converged on five distinct candidates",
  the controller added angles until it had twelve: "I'm adding three narrower
  discovery angles before verification so the final audit tests the
  surrounding API … rather than padding the report with duplicates." Eight of
  the twelve concern behaviour the spec is silent on (negative/fractional
  inputs, quoted CSV, float formatting) and are reported as confirmed defects
  without an out-of-scope label. The quota was met by widening scope, not by
  duplicates — a rationalization the skill text did not name.
- **PASS B4** — exercised the incomplete-verifier rule literally: "I discarded
  its entire response—including its other confirmations—logged it as invalid,
  and reran the full V5–V8 group once with fresh worker".
- **PASS B5** — angles listed; "None returned empty."
- **PASS B6** — only the log written; existing test still `1 passed`.
- **PASS B7** — 39 worker lines via `wt-log` (finders and verifiers each
  logging start/verify/return), controller lines separate in the run dir.

REFACTOR applied: `review.schema.json` now requires `scope: spec | adjacent`
on every finding (structural); SKILL.md failure policy names the "more angles
= more thorough" rationalization and rules out widening to approach a count;
`report.md` counts only `spec` findings. Re-run of Scenario B on Codex is
required (see refactor-results.md).

## Scenario C — Diagnose a run

### Codex (attempt-1) — PASS 5/5

Loaded `/home/mark/.codex/skills/work-team/SKILL.md` and `report.md`; ran the
diagnosis as a team (plan.json validated, 3 parallel read-only auditors, 1
reshaping worker, schema-validated returns). Run artefacts preserved in
`run-artefacts/`.

- **PASS C1** — every claim cites `SPEC.md:168`, log lines 209/306/345/356,
  `agents.csv:1/:66`, `result.json:1`.
- **PASS C2** — "Add a dedicated browser/rendering verifier for normal and
  reduced-motion animations … CSS presence is not a rendering oracle."
- **PASS C3** — final-fixer 2067 s (26% of span, 35% of token counter);
  "Split the catch-all final fixer into ordered functional remediation, visual
  remediation, and independent final re-review."
- **PASS C4** — `residual:null` vs logged residuals; "Partial `ok=false`
  outcomes for T10 and T16 were not reconcilable from the aggregate result."
- **PASS C5** — no caps; "Reconcile every final finding into
  `result.json.residual` before declaring completion."
- Audit fidelity: 21 `wt-log` lines, real timestamps, each worker logging its
  own start/verify/return; controller lines only for frame, plan, ingest.

### Claude (attempt-1)

- **PASS C1** — cites `SPEC.md:166-181`, `css-inventory.txt:6/9-11`,
  `result.json:1`, log timestamps for critic, plan reviewer, final-fixer,
  verifier-2.
- **PARTIAL C2** — mechanism named ("nothing else in the pipeline verified
  visual CSS"), but the remedy is still a proxy: "scripted CSS-completeness
  verification worker (cheap: `grep -c className` per component > 0)". The
  rendering-assertion / rubric-judge recipe in `run-plan.md` was not applied;
  the diagnosis path in `report.md` did not point to it. → REFACTOR: report.md
  step 4 now names the recipe and rules out count/grep proxies.
- **PASS C3** — final-fixer 2085 s / 267 turns / 37% of cache-read; proposes
  "each gap becomes its own scoped fixer task with an independent reviewer …
  re-run critic once (bounded loop)".
- **PASS C4** — "`result.json:1` reports `\"residual\": null` — none of the
  above 3 known-open items made it in"; verifier-2 never re-ran the critic;
  plan-review `changes_required` "accepted, deferred".
- **PASS C5** — no numeric caps proposed; "result.json must be mechanically
  derived from the log's residual list".
