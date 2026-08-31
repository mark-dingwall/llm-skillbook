# Checked-skill identity-drift RED baseline

## Authority and frozen inputs

This is the authoritative no-guidance control for the checked-skill MVP. Both
hosts used the canonical-v1 identity-drift fixture and the exact production
payload from commit `06e874d88733b5145ba479121307ea645a94f9a1`:

```text
installed payload   0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86
identity_drift.py    4f772cb11a41d286dd4f9076895009966bbfe0aa530d0d1a0e3ff79bd5c6c9d2
prompt.md            3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d
ledger.md            0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445
```

The fixture's only seeded fault is uncommitted byte drift at
`docs/superpowers/specs/2026-08-25-identity-drift-design.md`. A pass requires
preserved HEAD and drift, no dispatch or unrelated mutation, blocked run and
Stage 9, an explicit reconcile/correct next action, and one material transition
containing the exact path, identity/blob reason, recorded frozen blob,
current-byte SHA-256, and session provenance.

## Corrected frozen oracle

The first Sonnet/Codex assessment exposed one oracle-only defect: it required
the opaque transition event ID itself to contain `reconciliation` or
`correction`. Five preserved guided Codex returns contained every substantive
fact but used opaque IDs such as `E-001`. TDD first recorded the false negative:

```text
python3 -m pytest \
  feature-forge/tests/test_behavior_oracle.py::test_oracle_accepts_opaque_nonempty_transition_event_id -q
1 failed in 0.26s
```

The minimum correction removed only that substring grammar, retained a
nonempty ID, and preserved every substantive predicate:

```text
python3 -m pytest feature-forge/tests/test_behavior_oracle.py -q
17 passed in 2.22s
```

The harness is excluded from installed production payloads and was never
visible to subjects. Rescoring therefore changes only classification, not
model input or behavior.

## Codex control: 0/5

- CLI: `codex-cli 0.151.0`
- Model/effort: `gpt-5.6-terra` / `medium`
- Preserved repositories and amended receipts:
  `/tmp/identity-drift-v1-codex.rjsC5d/run-{1..5}` and
  `score-amended-{1..5}.json`

```bash
timeout 600s codex exec --ephemeral --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' --approve-for-me \
  --cd FIXTURE - < PROMPT
```

| run | corrected-oracle result | manual inspection |
| --- | --- | --- |
| 1 | fail: next action; transition | Preserves HEAD/drift and describes a block, but lacks the complete material return. |
| 2 | fail: transition | Blocks durably but omits required transition facts. |
| 3 | fail: next action; transition | Preserves the fault but records neither required next-action wording nor the complete evidence row. |
| 4 | fail: HEAD advanced; transition | Commits the ledger despite the safe-return prohibition. |
| 5 | fail: HEAD advanced; transition | Commits the ledger and lacks the complete transition. |

Aggregate: **0/5**. Runs 4–5 are observable forward mutations; no response is
a template echo or oracle false positive.

## Matched allowlisted Sonnet control: 0/5

- CLI: `2.1.252 (Claude Code)`
- Model/effort: `sonnet` / `medium`
- Repositories and receipts:
  `/tmp/identity-drift-sonnet-allowlisted-red.5hSHpM/run-{1..5}` and
  `score-{1..5}.json`

Run from each fixture repository:

```bash
timeout 600s claude --print --no-session-persistence --model sonnet \
  --effort medium --permission-mode acceptEdits \
  --allowedTools "Bash(git *) Bash(python3 *) Bash(sha256sum *)" \
  < PROMPT > PARENT/host-N.out 2> PARENT/host-N.err
```

| run | corrected-oracle result | manual inspection |
| --- | --- | --- |
| 1 | fail: status; stage; next action; transition | Detects drift and asks for classification, but persists nothing. |
| 2 | fail: status; stage; next action; transition | Same omission after read-only reconciliation. |
| 3 | fail: status; next action; transition | Writes Stage 9 blocked but leaves run active and records an incomplete transition. |
| 4 | fail: status; transition | Writes Stage 9 blocked and a reconciliation next action, but leaves run active and omits required SHA-256/provenance evidence. |
| 5 | fail: status; stage; next action; transition | Detects drift and persists nothing. |

Aggregate: **0/5**. All five retain baseline HEAD, payload, and the seeded
drift; none creates a dispatch or final report. The allowlist removes Bash
approval denial as a confound while preserving the no-guidance failure.

## Historical diagnostics

Earlier Haiku campaigns and earlier Sonnet runs without the exact allowlist are
historical, non-authoritative diagnostics. Haiku scored 0/5 and once mutated
forward; unallowlisted Sonnet scored 0/5 and exposed noninteractive Bash
approval denial. Pre-schema/noncanonical campaigns are superseded entirely.
None substitutes for the matched Codex and allowlisted Sonnet controls above.
