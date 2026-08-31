# Work Team RED Baseline Results

Skill state: absent (no `work-team` under `~/.claude/skills` or `~/.agents/skills`).
Harnesses: Claude Code 2.1.251 `claude -p --model sonnet`; Codex CLI 0.151.0
`codex exec --enable multi_agent -m gpt-5.6-terra` at medium effort.
Runner: `run-eval.sh`; transcripts under `transcripts/red/20260831T140000Z/`.
Scored against `oracle.md`; quotes are verbatim from `final-response.md`.

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
