# Checked-skill identity-drift RED baseline

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

### Codex: unavailable

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

- Result: exit `1`, before an agent response; stderr was `failed to initialize
  in-process app-server client: Read-only file system (os error 30)`.
- Manual inspection: no host mutation and no response were produced. The score
  correctly remained false only because the untouched seed ledger is not a
  blocked reconciliation.
- Five scored repetitions: not run, because the required runner/model could
  not initialize. Qualification is **unavailable**, not a pass or failure rate.

### Claude Code: unavailable

- CLI/version: `2.1.251 (Claude Code)`
- Requested model/effort: `sonnet` / `medium`; this version supports
  `--effort medium`.
- Flag probe and attempted subject command:

```bash
claude --print --no-session-persistence --model sonnet --effort medium \
  --permission-mode acceptEdits \
  "$(< /home/mark/kramtime/llm-skillbook/.worktrees/feature-forge-mvp/feature-forge/tests/behavior/identity-drift/prompt.md)" \
  </dev/null
```

- Result: no output or durable mutation before the explicit 20-second runner
  timeout; exit `124`. The subsequent oracle result was false solely for the
  untouched seed ledger (`not blocked or invalidated`, no reconciliation
  transition).
- Manual inspection: both stdout and stderr were empty and the worktree held
  only the fixture seed/fault. Five scored repetitions: not run after this
  genuine unavailable probe. Qualification is **unavailable**.

Release remains blocked: neither required fixed host/model was qualified, and
no fallback model or substitute campaign was used.

## Observations

No model response was available to support a rationalization analysis. The
deterministic oracle nevertheless records the four relevant observable rules:
no HEAD advancement, no review-dispatch artifact, no tracked mutation outside
the canonical ledger plus seeded specification drift, and a precise blocked or
invalidated reconciliation record with session provenance.
