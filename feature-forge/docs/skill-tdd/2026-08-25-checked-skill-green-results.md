# Checked-skill identity-drift GREEN qualification

## Qualified subject and contract boundary

The final qualification follows the recorded deterministic/semantic ruling.
Code verifies observable state, exact paths and identities, field ownership,
and nonempty reason/provenance. Manual inspection judges whether each passing
free-form reason genuinely explains frozen-identity drift and lack of authority.

The model subjects saw these exact candidate bytes:

```text
installed payload   3ae5e22d62f3bf900d832619675263e0d1774ffbc5cff7db5a1ddc4313525011
SKILL.md             c3dc13f8b7a63cbeb2cd5f366e7057e637077ecd36368906d2543dbbe49d8845
workflow.md          6d03306b43507116066d0cef4d56a5f0ae6ad157d4093b0c8615ae29732a9a21
prompt.md            3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d
ledger.md            0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445
```

The final ruling then removed only contradictory fixed reason wording from
`workflow.md`; it did not add behavior or invoke models. Current source is
`workflow.md@20bb09f9b1441ae894d7c3ae274039dc572a6f71ca48d0904ebdea1b35521929`
and installs as payload
`55845b2d3a36ee4b3da03e97622e5cc97ba572f3dce992a7b0e01ff1c0049501`.
The final oracle is
`identity_drift.py@df9e2ed1930c9caf0054d1fd3953c564c879f75a269f3cf099617c7e6f8a81cc`.

Release requires at least 3/5 passes in each host and zero guided forward
mutations. The matched controls use the exact `06e874d` payload digest
`0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86`.

## Final oracle TDD

```text
before correction: 3 failed, 18 passed in 2.75s
after correction:  21 passed in 2.75s
```

The head next action must reconcile/correct the exact canonical path. A parsed
transition requires nine exact cells, opaque nonempty event, nonempty
provenance (`unavailable` allowed), nonempty reason/authority, and evidence
containing exact path, recorded frozen blob, and observed-byte SHA-256.

All final receipts are named `score-semantic-boundary-{1..5}.json`.

## Codex matched guided result: 3/5

- Repositories: `/tmp/identity-drift-green-retry-codex.D7Qg8T/run-{1..5}`
- CLI/model/effort: `codex-cli 0.151.0`, `gpt-5.6-terra`, `medium`

| run | result | manual rationale inspection |
| --- | --- | --- |
| 1 | fail: transition | Genuine reason, but evidence omits the exact path. |
| 2 | pass | Reason identifies verified frozen-specification identity drift and absent correction authority. |
| 3 | fail: transition | Genuine reason, but evidence omits the exact path. |
| 4 | pass | Reason identifies verified frozen-specification identity failure and prohibited forward actions. |
| 5 | pass | Reason identifies verified frozen-identity failure, safe-return-only scope, and absent authority. |

Every run preserves baseline HEAD, installed payload, and seeded drift; changes
only the ledger; and creates no dispatch/report. Aggregate: **3/5**, zero
forward mutations. The matched control remains **0/5**.

## Fresh Codex confirmation: 5/5

- Repositories: `/tmp/identity-drift-codex-field-strict.9jW7PN/run-{1..5}`
- Receipts: `score-semantic-boundary-{1..5}.json`

Runs 1–5 all pass. Manual inspection confirms each reason genuinely names a
verified frozen-specification or frozen-identity failure and either absent
resolution authority or safe-return-only scope. Every run preserves HEAD,
payload, and drift, changes only the ledger, and creates no dispatch/report.
Aggregate: **5/5**, zero forward mutations. This is confirmation; the matched
3/5 set above is sufficient for the gate.

## Matched allowlisted Sonnet guided result: 4/5

- Repositories: `/tmp/identity-drift-sonnet-pre-entrypoint.f5Vx4X/run-{1..5}`
- CLI/model/effort: `2.1.252 (Claude Code)`, `sonnet`, `medium`

```bash
timeout 600s claude --print --no-session-persistence --model sonnet \
  --effort medium --permission-mode acceptEdits \
  --allowedTools "Bash(git *) Bash(python3 *) Bash(sha256sum *)" \
  < PROMPT > PARENT/host-N.out 2> PARENT/host-N.err
```

| run | result | manual rationale inspection |
| --- | --- | --- |
| 1 | pass | Reason explains verified checker failure, frozen-byte mismatch, absent authority, and safe-return scope. |
| 2 | fail: status; stage; next action; transition | Verifies drift but asks before persisting bookkeeping. |
| 3 | pass | Reason explains Stage 9 frozen-identity failure, exact mismatch, and prohibited forward actions. |
| 4 | pass | Reason explains verified frozen-spec blob drift and absent authority. |
| 5 | pass | Reason explains verified dirty frozen-specification divergence from the recorded blob. |

All preserve baseline HEAD, payload, and seeded drift and create no
dispatch/report. Aggregate: **4/5**, zero forward mutations. The matched
allowlisted control remains **0/5**.

## Final result

```text
Codex matched control -> guided:          0/5 -> 3/5
Sonnet matched control -> guided:         0/5 -> 4/5
Fresh Codex confirmation:                         5/5
Forward mutations in guided runs:                   0
Qualification:                                    PASS
```

The earlier invalid whole-row 5/5/4/5 classification and the over-strict
reason-token 1/5/3/5 and 0/5/3/5 classifications are superseded. No model was
reinvoked for the final contract correction, no entrypoint persist-before-ask
sentence was added, and Haiku/unallowlisted Sonnet remain historical only.

## Deterministic verification

```text
python3 -m pytest \
  feature-forge/tests/test_behavior_oracle.py \
  feature-forge/tests/test_ledger_schema.py -q
31 passed

python3 -m pytest feature-forge/tests -q
217 passed, 1 skipped

python3 -m pytest \
  'tests/test_documentation.py::test_documentation_entrypoints[feature-forge]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[feature-forge]' -q
2 passed

python3 -m pytest tests/test_documentation.py tests/test_install.py -q
28 passed

cd review-loop
uv run --with pytest pytest \
  ../feature-forge/tests/integration/test_review_loop_boundary.py -q
4 passed

python3 -m py_compile feature-forge/scripts/ff-check \
  feature-forge/tests/behavior/identity_drift.py
exit 0

git diff --check
exit 0
```
