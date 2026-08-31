# Verification, report, and diagnosis

## Verify

Run every phase's `verify` command from the controller after the last loop;
keep the exact output. Where the plan has a rendering assertion or rubric
judge, its verdict is a verification entry too.

## result.json

Validate with `wt-validate <skill>/references/schemas/result.schema.json`.

```json
{
  "run": "<run>",
  "outcome": "complete | partial | stopped",
  "verification": [{"command": "python3 -m pytest -q", "passed": true, "summary": "20 passed"}],
  "residual": [
    {"kind": "finding", "detail": "save() not atomic (minor)", "source": "reviewer r1"},
    {"kind": "loop_cap", "detail": "…", "source": "impl loop"}
  ],
  "workers": [{"id": "implementer", "role": "implementer", "status": "ok"}],
  "plan": ".work-team/<run>/plan.json",
  "log": ".work-team/<run>/workflow-log.jsonl"
}
```

Residual kinds: `finding` (open review finding), `gap` (spec item no worker
covered), `worker_failed`, `loop_cap`, `invalid_return`, `skipped`. Every
retry, stall, cap hit, or empty-after-retry produces one entry. `outcome` is
`complete` only when `residual` has no `blocker`/`important` finding and every
verification passed.

## report.md

Findings are counted and listed by `scope`: `spec` findings are the result;
`adjacent` observations follow in their own short section and never count
toward any requested number.

Order: outcome line → verification table → residuals → workers table
(id, role, status, one-line summary) → run structure (phases, groups, loops,
copied from plan.json) → telemetry (`wt-telemetry` output). No prose claims
that are not backed by a row above.

## Diagnose a run

When asked why a finished run missed something or cost too much:

1. `wt-telemetry <run>/workflow-log.jsonl` — who dominated wall-clock; roles
   with few entries per agent (under-logged) or very long spans (over-scoped).
2. Diff `result.json.residual` against the log: any `ok=false`, `changes_required`
   at a cap, or critic gap without a matching residual is a reporting defect.
3. Diff the spec against `verification[]`: a requirement with no verification
   entry was never checked — that is the mechanism, not a worker's fault.
4. Propose the next `plan.json`. For each unchecked requirement, name the
   verification worker and its oracle type, exactly one of:
   - `unit-test` — a test asserts the behaviour at a code boundary;
   - `rendering-assertion` — a browser-level test observes the rendered result
     (computed style, running animation, reduced-motion path, screenshot);
   - `rubric-judge` — a fresh worker scores rendered output against a written
     rubric and returns `review.schema.json`.
   A check over source text (a CSS file exists, a class name appears, a line
   count) is a `source-scan`; it is not an oracle type and may not be
   proposed as the verification for a visual requirement. Split dominating
   workers along verification boundaries; re-run any critic after the final
   fix. Cite log lines and CSV rows for every claim; do not introduce numeric
   caps as rules.
