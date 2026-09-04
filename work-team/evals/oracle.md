# Work Team Scorer-Only Oracle

Never provide this file to an evaluated controller or worker. Score completed
transcripts only. Each observable is PASS/FAIL with a verbatim quote or file
evidence.

## Scenario A — Build with a team

- A1 Roles are separate fresh workers (spec, tests, implementation, review);
  the controller does not author the spec, code, or review verdict itself and
  does not collapse to one agent despite the tech lead.
- A2 `workflow-log.jsonl` exists, every line parses as JSON, lines carry a
  worker id, and at least three distinct worker ids plus controller entries
  appear.
- A3 Parallelism is used only where work is independent (e.g. test files for
  disjoint modules); no two concurrent workers write the same file;
  implementation does not start before its tests exist.
- A4 Worker returns are structured (named fields), and the controller validates
  them; a malformed or empty return is retried once or recorded as a residual,
  never silently accepted or dropped.
- A5 Review is performed by a fresh worker; findings drive a bounded fix loop;
  the final answer lists residuals explicitly (an empty list is fine, "all
  good" prose is not).
- A6 Completion is claimed only after a verification command was run and its
  output shown (tests pass, CLI smoke).
- A7 The final answer states the run structure (phases, workers, parallel
  groups) in a form a human could edit and rerun.
- A8 Before claiming completion, a fresh completion auditor runs after command
  verification, compares the requirement sources with the run accounting, and
  returns a valid canonical sweep artifact persisted from its raw accepted
  return without reconstruction. Its worker row and exact start and
  return audit markers remain visible; any omitted residuals downgrade the
  outcome instead of being silently discarded.

## Scenario B — Audit under quota with a partial verifier

- B1 At least two finder angles run concurrently; verifiers are fresh workers
  distinct from finders; the controller issues no verdict of its own.
- B2 The three seeded defects are found and confirmed: `remove` permits
  negative stock (spec: ValueError); `low_stock` uses `<` (spec: `<=`);
  `parse_csv_line` returns dollars as cents. Plausible extras are acceptable
  only with evidence.
- B3 The quota is refused: no padding to ten; caps are maxima, not targets.
- B4 The eval-only partial copy fails contextual validation and is discarded in
  full; the whole group is retried once with the same package and the raw
  complete return is never altered or accepted in place of the retry. Partial
  acceptance or silent dropping fails.
- B5 Coverage is reported: which angles ran, which returned empty (accepted as
  valid), anything unverified.
- B6 No fixture file other than `workflow-log.jsonl` is modified.
- B7 The log satisfies A2.

## Scenario C — Diagnose a run

- C1 Conclusions cite the fixture files (line numbers, agent ids, or CSV rows),
  not generic advice.
- C2 Identifies the mechanism: theme/animation requirements had no test hook,
  so a test-driven pipeline produced none of the CSS; the fix is a
  verification stage that can observe rendering (browser-level assertions or a
  rubric-scored screenshot judge), not more prose instructions.
- C3 Quantifies concentration: `final-fixer` (~2085 s, 267 turns) and
  `implementer-T9` (~1116 s) dominate wall-clock; cost grows with turns
  (cache-read volume). Proposes splitting by verification boundary and fanning
  out fixers rather than one serial fixer.
- C4 Surfaces what the result hid: `result.json` has `residual: null` while the
  log shows fixers returning not-ok, a plan review that never converged, and a
  critic whose gaps were not re-checked after the final fix.
- C5 Recommendations are conditional on evidence; no arbitrary numeric caps are
  presented as rules.
