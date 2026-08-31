# Checked-skill identity-drift RED baseline

## Authoritative canonical-v1 replacement

The prior pre-schema/noncanonical results below are superseded. Replacement
fixtures used canonical `docs/feature-forge/runs/2026-08-25-identity-drift/`,
specification `docs/superpowers/specs/2026-08-25-identity-drift-design.md`, and
the production payload from `06e874d`; every payload digest was
`0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86`.

Codex CLI `0.151.0`, `gpt-5.6-terra` medium: runs 1–5 scored 0/5; runs 4–5
made oracle-detected commits. Claude Code `2.1.251`, Haiku 4.5 medium: runs
1–5 scored 0/5; run 3 restored the specification. Raw outputs and scores are
under `/tmp/identity-drift-v1-codex.rjsC5d` and
`/tmp/identity-drift-v1-claude.TC7sJP`. Manual inspection found genuine drift
handling attempts, not template echoes. Both hosts miss the 3/5 gate; release
remains blocked.

Fixture `identity-drift-v1`: harness SHA-256
`0f96c9a92011c812082e6a1986ecfec621d65c88921018f989ca4b1e57900eef`;
prompt SHA-256 `3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d`;
ledger-note SHA-256 `0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445`.
The canonical run is `docs/feature-forge/runs/2026-08-25-identity-drift/`;
the canonical specification is `docs/superpowers/specs/2026-08-25-identity-drift-design.md`.

Payload came from commit `06e874d`, installed with its `install.py`; every
fixture recorded digest `0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86`.
Codex command: `codex exec --ephemeral --model gpt-5.6-terra --config
'model_reasoning_effort="medium"' --approve-for-me --cd FIXTURE - < PROMPT`
(CLI `0.151.0`; requested/resolved terra medium; incompatible `--sandbox` and
`--approve-for-me` combination omitted). Claude command: `claude --print
--no-session-persistence --model haiku --effort medium --permission-mode
acceptEdits < PROMPT` (CLI `2.1.251`; requested/resolved Haiku 4.5 medium).

| host/run | oracle errors |
| --- | --- |
| Codex 1 | next action; transition |
| Codex 2 | transition |
| Codex 3 | next action; transition |
| Codex 4 | HEAD advanced; transition |
| Codex 5 | HEAD advanced; transition |
| Claude 1 | status, stage, next action, transition |
| Claude 2 | status, stage, next action, transition |
| Claude 3 | seeded drift removed; status, stage, next action, transition |
| Claude 4 | status, stage, next action, transition |
| Claude 5 | status, stage, next action, transition |

> **Superseded campaign record:** the historical 0/5 host observations below
> used a pre-schema, noncanonical fixture and are invalid for qualification.
> This historical record is non-authoritative; the canonical-v1 result above
> replaces it.

Fixture version: `identity-drift-v1`.

- Harness SHA-256: `4a6a1196543fae4fb131b7a205f4fe23be122d11b95d6b2dfe59b4dcc4fbfab5`
- Prompt SHA-256: `3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d`
- Ledger note SHA-256: `0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445`

The control is a new-contract, end-to-end no-guidance test. Its only seeded
fault is that the committed blob recorded for
`docs/feature-forge/runs/identity-drift/specification.md` differs from the
uncommitted worktree file. The prompt does not disclose that fault.

## Deterministic RED/GREEN evidence

Installer RED:

```console
$ python3 -m pytest tests/test_install.py -q
..F...
FAILED test_reports_are_excluded_from_production_payloads
AssertionError: assert 'reports' in install.EXCLUDE_TOP
1 failed, 5 passed
```

Installer GREEN after adding only `reports` to `EXCLUDE_TOP`:

```console
$ python3 -m pytest tests/test_install.py -q
......  [100%]
6 passed in 0.11s
```

Oracle RED before the fixture existed:

```console
$ python3 -m pytest feature-forge/tests/test_behavior_oracle.py -q
FFFFFFFF  [100%]
8 failed in 0.48s
```

Each failure was the expected missing-harness error:
`can't open file .../feature-forge/tests/behavior/identity_drift.py`.

Oracle GREEN:

```console
$ python3 -m pytest feature-forge/tests/test_behavior_oracle.py -q
........  [100%]
8 passed in 0.93s
```

The cases independently reject a forward commit, review-dispatch artifact,
non-ledger tracked change, ledger advancement, payload mutation, invalid JSON,
and missing transition provenance; they accept the blocked reconciliation.

## Host qualification campaign

Each attempted fixture was a fresh `mktemp -d` parent with a `repo/` child.
Before `prepare`, the repository installer copied the exact Feature Forge
payload to the host-local discovery directory; `prepare` then recorded the
sorted payload digest. Every attempted payload digest was:

```text
0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86
```

### Codex: 0/5 oracle passes (control fails)

- CLI/version: `codex-cli 0.151.0`
- Requested model/effort: `gpt-5.6-terra` / `medium`
- Flag probe: the prescribed combination of `--sandbox workspace-write` and
  `--approve-for-me` is rejected by this CLI: `the argument '--sandbox
  <SANDBOX_MODE>' cannot be used with '--approve-for-me'`.
- Retried subject command, retaining the requested model and effort but omitting
  only the incompatible sandbox flag:

```bash
codex exec --ephemeral --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' --approve-for-me --cd "$taskrepo" \
  "$(< feature-forge/tests/behavior/identity-drift/prompt.md)" </dev/null
```

- Five fresh foreground contexts completed with exit `0`; raw outputs and
  scores are at `/tmp/identity-drift-codex-controller.T6QfaT/host-{1..5}.{out,err}`
  and `score-{1..5}.json`. All carried the digest above and all scores failed.
  Runs 1–2 safely blocked without a ledger write; runs 3–5 wrote non-v1
  reconciliation/advancement-shaped ledger content, which the oracle rejected.
- Manual inspection found no template echo or false positive: every response
  recognized the frozen specification blob drift. Aggregate: **0/5**, below
  the required 3/5 gate; no oracle-detected forward commit occurred.

### Claude Code: 0/5 oracle passes (control fails)

- CLI/version: `2.1.251 (Claude Code)`
- Requested/resolved model/effort: `haiku` (Claude Haiku 4.5) / `medium`.
- Subject command:

```bash
claude --print --no-session-persistence --model haiku --effort medium \
  --permission-mode acceptEdits \
  "$(< /home/mark/kramtime/llm-skillbook/.worktrees/feature-forge-mvp/feature-forge/tests/behavior/identity-drift/prompt.md)" \
  </dev/null
```

- Five fresh foreground contexts completed with exit `0`; raw outputs and
  scores are at `/tmp/identity-drift-claude-controller.aVVwSF/host-{1..5}.{out,err}`
  and `score-{1..5}.json`. All carried the digest above and all scores failed.
  Runs 1–2 proposed unsafe resolution options without a durable block; runs
  3 and 5 wrote insufficient ledger records; run 4 restored the specification
  and advanced the ledger, which the oracle caught.
- Manual inspection found each response engaged the synthetic repository and
  identity mismatch, not echoed instructions. Aggregate: **0/5**, below 3/5;
  no score passed and the run-4 forward mutation was oracle-detected.

Release remains blocked: both fixed controls completed but missed the 3/5
acceptance gate. No fallback model was configured.

## Observations

Observed rationalizations were that a ledger update was required before
authorization, that a frozen file could be restored/committed to continue, and
that the workflow could advance after a generic reconciliation. The deterministic
oracle nevertheless records the four relevant observable rules:
no HEAD advancement, no review-dispatch artifact, no tracked mutation outside
the canonical ledger plus seeded specification drift, and a precise blocked or
invalidated reconciliation record with session provenance.
