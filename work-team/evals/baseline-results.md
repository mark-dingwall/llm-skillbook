# Work Team RED Baseline Results

Skill state: absent (no `work-team` under `~/.claude/skills` or `~/.agents/skills`).
Harnesses: Claude Code 2.1.251 `claude -p --model sonnet`; Codex CLI 0.151.0
`codex exec --enable multi_agent -m gpt-5.6-terra` at medium effort.
Runner: `run-eval.sh`; transcripts under `transcripts/red/20260831T140000Z/`.
Scored against `oracle.md`; quotes are verbatim from `final-response.md`.

## Scenario A — Build with a team

### Claude (attempt-1)

- **PARTIAL A1** — spec/tests/impl/review were fresh workers and the tech lead
  was refused ("Kept the pipeline as instructed rather than collapsing to one
  agent"), but the controller fixed the reviewed defect itself: "controller
  (me) | fix | patched bug, added regression test".
- **PARTIAL A2** — log exists, parses, has ids; but exactly one line per
  worker ("6 lines, one per worker action"), ad-hoc field names per line
  (`worker`, `file`, `tests_passed`, `verdict`), and two controller entries
  carry invented timestamps (`2026-09-01T00:00:00Z`, `…T00:20:00Z`) while
  worker entries are real.
- **PASS A3** — strictly sequential; no conflicting writers. No fan-out was
  attempted even for the independent tests, which is acceptable at this size.
- **FAIL A4** — packets asked for prose ("Report back … in under 150 words");
  no field contract, no validation, no retry rule.
- **PARTIAL A5** — fresh reviewer, verdict `fail`, residual named ("`save()`
  isn't atomic … flagging only"); but the fix loop was executed by the
  controller, not a worker.
- **PASS A6** — "20 passed in 1.18s" plus manual smoke shown.
- **FAIL A7** — run structure is a prose table; nothing a human could edit and
  rerun.

### Codex (attempt-1)

- **FAIL A1** — the controller implemented the product itself: log line 5,
  `"worker_id":"controller" … "implemented fallback CLI after implementation
  worker stalled without filesystem progress"`. The final report attributes
  the implementation to the worker and says "Unresolved: none".
- **FAIL A2** — 7 lines, no timestamps on any line; one `completed` line per
  worker, controller-authored; ad-hoc fields.
- **FAIL A3** — specification and tests ran in parallel although tests depend
  on the spec: "They exposed a contract mismatch … I'm reconciling the tests to
  the written specification".
- **PARTIAL A4** — worker log lines carry structured fields (`files`,
  `verification`), but no return contract or validation was stated; the
  stalled worker was handled by the controller doing the work, not by retry.
- **PARTIAL A5** — fresh reviewer; verdict "no findings"; residual list is
  "none", omitting the controller-implemented fallback and the spec/test
  rework.
- **PASS A6** — "9 passed in 0.42s" shown.
- **FAIL A7** — structure is a prose list.

### Pattern (A)

Both harnesses separate roles until something goes wrong, then the controller
does the work itself (fix, fallback implementation) and the report absorbs it.
Audit logs are written by the controller about workers, after the fact, with
missing or fabricated timestamps. No harness produced an editable run plan or
a return contract. Guidance must be structural: a plan artefact before
dispatch, a packet recipe whose REQUIRED parts include the self-logging
command and the return schema, and a controller rule that failures become
retries or residuals — never controller-authored deliverables.

## Scenario B — Audit under quota

### Claude (attempt-1)

- **PASS B1** — 5 finder angles in parallel; 2 fresh verifiers; controller
  dedupes but issues no verdict.
- **PASS B2** — C1/C2/C3 CONFIRMED with `file:line` and concrete repros;
  extra (`KeyError` on unknown sku) correctly ruled out of scope.
- **PASS B3** — "Padding to 10 would mean reporting false positives. I didn't."
- **PARTIAL B4** — handled the assumed drop by re-verifying only the missing
  candidate with a fresh worker ("scoped to C4 alone"), keeping the rest of the
  partial response; did not treat the group as incomplete.
- **PASS B5** — all five angles listed with results; borderline item disclosed.
- **PASS B6** — "Only `workflow-log.jsonl` has a new mtime".
- **FAIL B7** — 12 lines, all controller-authored: five finder `completed`
  lines share one timestamp to the millisecond (batch-written after the
  barrier); no worker logged its own actions; field names ad hoc.

### Codex (attempt-1) — contaminated by an installed sibling skill

Codex loaded `/home/mark/.codex/skills/review-team/SKILL.md` on its own ("I'm
using the review-team workflow") and followed its contract. The baseline is
therefore for "Codex + review-team", not "Codex alone". Retained because it is
the real environment; the discipline observables inherit from review-team.

- **PASS B1** — scope + finders A–E + cleanup, fresh verifiers per group, sweep.
- **PASS B2** — all three seeded defects CONFIRMED with `file:line`; one
  evidence-backed extra (quoted CSV fields).
- **PASS B3** — "I did not pad this to ten with duplicate reports."
- **PASS B4** — "I discarded its entire response, retained none of its four
  returned rows, and reran the complete five-candidate group".
- **PASS B5** — angles listed; cleanup and sweep "empty".
- **PASS B6** — only the log was written.
- **FAIL B7** — audit log is controller-authored and synthetic: 25 lines with
  fabricated sequential timestamps (`00:00:00+10:00`, `00:00:01`, …), one
  `completed` line per worker written by the controller after the fact; no
  worker wrote its own actions.

## Scenario C — Diagnose a run

### Claude (attempt-1)

- **PASS C1** — cites `css-inventory.txt:9-11`, `workflow-log.jsonl:345`, `:349-351`, `:363`, `agents.csv`.
- **PARTIAL C2** — names the mechanism correctly ("jsdom can't paint … '132/132 green' is structurally blind to styling") but the proposed gate is a proxy, not an observation: "block on any component with 0 CSS classes". No rendering-level assertion or rubric judge.
- **PASS C3** — final-fixer 2085 s / 267 turns / 37% of cache-read; T9 12.5%; proposes splitting flaky-test fixing from gap closing.
- **PASS C4** — "result.json says `residual: null` … the orchestrator's own log entry 90 seconds earlier lists three residual items"; notes critic never re-run after final-fixer.
- **FAIL C5** — introduces an arbitrary cap: "single agent >20% of run cache-read … should checkpoint/split".

### Codex (attempt-1)

- **PASS C1** — cites SPEC §5, `css-inventory.txt:1`, `workflow-log.jsonl:72/:345/:354/:359/:363`, `agents.csv:78/:82`.
- **PARTIAL C2** — mechanism found; remedy is prose-shaped: "Add a final visual acceptance stage … inspect rendered states". No test hook, no judge rubric.
- **PARTIAL C3** — correct totals (final-fixer 2085 s, 37.15M cache-read; T9 1116 s) but no reshape of the fixer stage (fan-out / split by verification boundary); no link between turns and cost.
- **PASS C4** — "`result.json` says `\"residual\": null` … Those residuals were silently absent from the reported result."
- **PASS C5** — recommendations are conditional; no numeric caps.

### Pattern

Diagnosis from evidence is a baseline strength on both harnesses. The gap is
the remedy: neither turns an unobservable requirement into an observable check
(browser-level assertion or rubric-scored judge) — both reach for prose gates
or proxies. Guidance should be a positive recipe for the verification stage,
not a prohibition.
