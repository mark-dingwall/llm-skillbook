# Checked-skill identity-drift RED baseline

## Authority and frozen inputs

This is the authoritative no-guidance control. Both hosts used the
canonical-v1 identity-drift fixture and exact production payload from commit
`06e874d88733b5145ba479121307ea645a94f9a1`:

```text
installed payload   0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86
identity_drift.py    4915ce84326f6c10f169e1bfb7c59a77605d361a01dac0900eccaa4272f8411b
prompt.md            3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d
ledger.md            0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445
```

The sole seeded fault is uncommitted byte drift at
`docs/superpowers/specs/2026-08-25-identity-drift-design.md`. A mechanical pass
requires preserved HEAD/payload/drift, no dispatch or unrelated mutation,
blocked run and Stage 9, a reconcile/correct next action containing that exact
path, and a nine-cell material transition with nonempty opaque event,
provenance, and reason/authority plus evidence containing the exact path,
recorded frozen blob, and current-byte SHA-256. Manual inspection determines
whether the free-form reason genuinely explains identity/blob drift.

## Oracle correction history

The event ID remains opaque but nonempty. Review later correctly required
field ownership, but prescribing path and `identity/blob drift` tokens in the
free-form reason conflicted with the MVP boundary: code should verify
deterministic facts, while an LLM/manual inspection judges semantic rationale.
TDD isolated the final boundary before changing the oracle:

```text
RED:   3 failed, 18 passed in 2.75s
GREEN: 21 passed in 2.75s
```

The failing tests covered a free-form valid reason, next action missing the
exact path, and evidence missing its exact path while that path appeared
elsewhere. The suite also independently rejects empty reason/provenance/event
and each missing evidence identity. The harness is excluded from installed
payloads and was never visible to subjects; rescoring changes classification,
not model input or behavior.

Round-2 review found that the parser still scanned every Markdown table. TDD
moved a complete valid-looking row under another section while leaving the
actual Transition log empty:

```text
RED:   1 failed, 21 passed in 2.84s
GREEN: 22 passed in 2.73s
```

The oracle now accepts rows only from the exact `## Transition log` section
under its canonical nine-column header and separator. Lookalike rows elsewhere
cannot satisfy the material-transition predicate.

## Codex control: 0/5

- CLI/model/effort: `codex-cli 0.151.0`, `gpt-5.6-terra`, `medium`
- Repositories: `/tmp/identity-drift-v1-codex.rjsC5d/run-{1..5}`
- Final receipts: `score-semantic-boundary-{1..5}.json`

```bash
timeout 600s codex exec --ephemeral --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' --approve-for-me \
  --cd FIXTURE - < PROMPT
```

| run | result | manual inspection |
| --- | --- | --- |
| 1 | fail: next action; transition | Blocks verbally but does not put the exact path in the head next action or transition evidence. |
| 2 | fail: next action; transition | Blocks durably but omits the deterministic exact-path contract. |
| 3 | fail: next action; transition | Records narrative evidence but not the exact-path recovery contract. |
| 4 | fail: HEAD advanced; next action; transition | Commits the ledger despite the safe-return prohibition. |
| 5 | fail: HEAD advanced; next action; transition | Commits the ledger and omits the deterministic exact-path contract. |

Aggregate: **0/5**. Runs 4–5 are observable forward mutations. No result is a
template echo or oracle false positive.

## Matched allowlisted Sonnet control: 0/5

- CLI/model/effort: `2.1.252 (Claude Code)`, `sonnet`, `medium`
- Repositories: `/tmp/identity-drift-sonnet-allowlisted-red.5hSHpM/run-{1..5}`
- Final receipts: `score-semantic-boundary-{1..5}.json`

```bash
timeout 600s claude --print --no-session-persistence --model sonnet \
  --effort medium --permission-mode acceptEdits \
  --allowedTools "Bash(git *) Bash(python3 *) Bash(sha256sum *)" \
  < PROMPT > PARENT/host-N.out 2> PARENT/host-N.err
```

| run | result | manual inspection |
| --- | --- | --- |
| 1 | fail: status; stage; next action; transition | Detects drift but persists nothing. |
| 2 | fail: status; stage; next action; transition | Same authority-free bookkeeping omission. |
| 3 | fail: status; next action; transition | Writes only a partial blocked-stage record. |
| 4 | fail: status; next action; transition | Leaves the run active and omits exact-path evidence. |
| 5 | fail: status; stage; next action; transition | Detects drift but persists nothing. |

Aggregate: **0/5**, zero forward mutations. All preserve payload and seeded
drift and create no dispatch/report. The allowlist removes Bash approval denial
as a confound.

Haiku, unallowlisted Sonnet, pre-schema, and noncanonical campaigns are
historical diagnostics only.
