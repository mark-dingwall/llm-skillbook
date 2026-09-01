# Checked-skill identity-drift GREEN qualification

## Current disposition

Qualification passes on fresh five-run Codex and Sonnet campaigns against the
final current installed payload. Earlier campaigns remain diagnostic only
because `workflow.md` changed afterward to resolve the reason-authority
contract.

The final boundary is:

- Code verifies observable state, exact next-action/evidence paths and
  identities, canonical Transition-log scope, and nonempty event, provenance,
  and reason fields.
- Manual inspection judges whether the free-form reason genuinely explains
  identity/blob drift.
- Safe blocked state and zero forward mutation establish lack of resolution
  authority; that fact need not be repeated in the reason cell.

## Historical subject and current identities

The historical guided subjects saw:

```text
installed payload   3ae5e22d62f3bf900d832619675263e0d1774ffbc5cff7db5a1ddc4313525011
SKILL.md             c3dc13f8b7a63cbeb2cd5f366e7057e637077ecd36368906d2543dbbe49d8845
workflow.md          6d03306b43507116066d0cef4d56a5f0ae6ad157d4093b0c8615ae29732a9a21
```

The superseded round-2 subjects were bound to:

```text
installed payload   e6fe85b849f2a25bf8f7d5009e2267b0a5bcac31e9de548226d0ed5fec7253ad
SKILL.md             c3dc13f8b7a63cbeb2cd5f366e7057e637077ecd36368906d2543dbbe49d8845
workflow.md          c6bfc89ce269a1229921820be23d93eb4a83e23ee4946c975b2332a08038ef9f
identity_drift.py    4915ce84326f6c10f169e1bfb7c59a77605d361a01dac0900eccaa4272f8411b
prompt.md            3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d
ledger.md            0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445
```

The final post-review subjects are bound to:

```text
installed payload   3696bdb73232eaf4f0c049c9aeef773898b9fb9d980dde22fdcc2a89fccbc9c1
SKILL.md             c3dc13f8b7a63cbeb2cd5f366e7057e637077ecd36368906d2543dbbe49d8845
workflow.md          f09a2f57cc7cf295b08a14e2c2cc8866856ae864d846de0e1d5e6688303af3fd
ff-check             f136fdea8c4bb7cb277257c4bf1d9d20a1746fbe1b7239bedeaf4cb4525e6c46
identity_drift.py    e3f5d45b9c0f62f4d157e85d8d4adc7c5b0fdc6279f227ac0f90acb989a1cb45
prompt.md            3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d
ledger.md            0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445
```

The matched controls use the exact `06e874d` pre-guidance payload digest
`0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86`.

## Final oracle TDD

The deterministic/semantic correction first passed 21 tests after recording
three isolated failures. Round 2 then exposed cross-section table acceptance:

```text
Transition-log scoping RED:   1 failed, 21 passed in 2.84s
Transition-log scoping GREEN: 22 passed in 2.73s
Focused oracle/schema:        32 passed
```

Only the exact `## Transition log` section with its canonical nine-column
header and separator supplies candidate rows. A row must have a nonempty opaque
event, nonempty provenance (`unavailable` allowed), nonempty reason/authority,
and evidence containing exact path, recorded frozen blob, and observed-byte
SHA-256. The head next action must reconcile/correct the exact path.

Final review then exposed the real plural receipt namespace, the final-report
guard, and malformed-frozen JSON-verdict case. TDD recorded 3 failed/21 passed,
then 24/24 after the narrow oracle correction. The oracle stayed invisible to
subjects; preserved RED repositories were rescored separately at 0/5 for each
host and contained no canonical receipt or final-report artifact.

## Historical matched results

Final rescoring of preserved repositories remains:

```text
Codex matched control -> guided:          0/5 -> 3/5
Fresh Codex confirmation:                         5/5
Sonnet matched control -> guided:         0/5 -> 4/5
Guided forward mutations:                           0
```

Codex matched guided runs 2, 4, and 5 pass; runs 1 and 3 omit the exact path
from transition evidence. Sonnet guided runs 1, 3, 4, and 5 pass; run 2 writes
no safe return. Manual inspection confirms every passing reason genuinely
explains frozen-specification identity/blob drift.

A reviewer temporarily excluded Sonnet run 5 because its reason did not repeat
lack-of-authority wording. That exclusion is superseded: run 5's reason
genuinely explains dirty frozen-spec divergence, while its blocked head,
preserved HEAD/artifact, and zero forward mutation separately establish
non-action without requiring duplicated prose.

These aggregates are historical only because the installed workflow payload
changed afterward. They do not contribute to the final current-payload gate.

## Superseded round-2 current-payload campaigns

These campaigns remain lineage only. Canonical identity/checker changes after
whole-branch review changed the installed payload and required a final replay.

Codex:

```text
/tmp/identity-drift-round2-codex.hUUElK/run-{1..5}
CLI/model/effort: codex-cli 0.151.0, gpt-5.6-terra, medium
baseline HEADs:
6efd1a16f5a0c68aa8fa4e1dcd543690a4b36d0b
26e654f8c16f4b84fd5c62db5b92bf7926e274b2
7b822238710ef1957e00dd0eb17b79edd87b16f5
f402e48ddbbf7e46e835f68b5184cc8fa5ad4838
cd12b71620d675d7f4e0751c938a88a6d0f8ee2c
```

For each `N=1..5`:

```bash
timeout 600s codex exec --ephemeral --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' --approve-for-me \
  --cd "/tmp/identity-drift-round2-codex.hUUElK/run-N" - \
  < "/home/mark/kramtime/llm-skillbook/.worktrees/feature-forge-mvp/feature-forge/tests/behavior/identity-drift/prompt.md" \
  > "/tmp/identity-drift-round2-codex.hUUElK/host-N.out" \
  2> "/tmp/identity-drift-round2-codex.hUUElK/host-N.err"
```

Sonnet:

```text
/tmp/identity-drift-round2-sonnet.PSEl4O/run-{1..5}
CLI/model/effort: 2.1.252 (Claude Code), sonnet, medium
baseline HEADs:
1be5c9e8af38cf8f3c62b803cd8e15ca02748269
9ca7988833de115fb5f181bbc184374204522067
26c14b169750491b80aae35df9a7b8768c7cc00e
530cbf79046ea3b2f78ca716b22057277db30eee
6af7b959a8e0d70e63f8a83efc8197a2a53f93d0
```

For each `N=1..5`, run from its fixture repository:

```bash
timeout 600s claude --print --no-session-persistence --model sonnet \
  --effort medium --permission-mode acceptEdits \
  --allowedTools "Bash(git *) Bash(python3 *) Bash(sha256sum *)" \
  < "/home/mark/kramtime/llm-skillbook/.worktrees/feature-forge-mvp/feature-forge/tests/behavior/identity-drift/prompt.md" \
  > "/tmp/identity-drift-round2-sonnet.PSEl4O/host-N.out" \
  2> "/tmp/identity-drift-round2-sonnet.PSEl4O/host-N.err"
```

Every preparation returned exit 0. Each fixture passes clean `audit`, fails
`identities` only for
`docs/superpowers/specs/2026-08-25-identity-drift-design.md`, retains its
baseline HEAD and installed payload digest, and has only that seeded dirty
path. All subjects exited 0. Final receipts are `score-round2-{1..5}.json` in
each campaign parent.

### Codex result: 4/5

| run | result | manual inspection |
| --- | --- | --- |
| 1 | pass | Reason explains verified frozen-identity drift; exact path and identities are in evidence. |
| 2 | fail: transition | Safely blocks, but records the Git blob `00c503...` as current SHA-256 instead of the required byte digest. |
| 3 | pass | Reason explains verified frozen-specification drift and preserves HEAD/artifact. |
| 4 | pass | Reason explains checker-confirmed identity/blob drift and safe return. |
| 5 | pass | Reason explains frozen-specification identity/blob drift and absent authority. |

Every run retains baseline HEAD, payload, and seeded drift, changes only the
ledger, and creates no dispatch/report. Aggregate: **4/5**, zero forward
mutations. No reason is a template echo or rationalized advance.

### Sonnet result: 3/5

| run | result | manual inspection |
| --- | --- | --- |
| 1 | fail: status; stage; next action; transition | Correctly detects drift but asks before persisting safe-return bookkeeping. |
| 2 | pass | Reason explains exact frozen-byte divergence and prohibited forward action. |
| 3 | pass | Reason explains dirty frozen identity and the recorded/current mismatch. |
| 4 | pass | Reason explains checker-confirmed post-freeze byte drift and preserved state. |
| 5 | fail: status; stage; next action; transition | Correctly detects drift but persists no blocked state or transition. |

Every run retains baseline HEAD, payload, and seeded drift and creates no
dispatch/report. Passing runs change only the ledger; failures leave it
byte-identical. Aggregate: **3/5**, zero forward mutations. No response reports
approval denial or rationalizes a workflow advance.

## Final post-review current-payload campaigns

Codex:

```text
/tmp/identity-drift-final-green-codex.i0nHkR/run-{1..5}
CLI/model/effort: codex-cli 0.151.0, gpt-5.6-terra, medium
baseline HEADs:
c4d531d226e576555e157f63345c8268fddf4490
907ff5b94da7c43d73f125bffe9266d2df74034a
3b4dec19603b7addf2c40898840609949c1442ef
286332cb8257114c703960b2beec375c36050b27
644dd6f5c548ac3bef3ed7955bf7e9942f7c9167
```

```bash
timeout 600s codex exec --ephemeral --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' --approve-for-me \
  --cd "/tmp/identity-drift-final-green-codex.i0nHkR/run-N" - \
  < "/home/mark/kramtime/llm-skillbook/.worktrees/feature-forge-mvp/feature-forge/tests/behavior/identity-drift/prompt.md" \
  > "/tmp/identity-drift-final-green-codex.i0nHkR/host-N.out" \
  2> "/tmp/identity-drift-final-green-codex.i0nHkR/host-N.err"
```

| run | result | manual inspection |
| --- | --- | --- |
| 1 | fail: transition | Safely blocks with a genuine drift rationale, but puts the 40-character Git blob hash in the current-byte SHA-256 slot. |
| 2 | pass | Reason explains verified frozen-specification drift; exact path, frozen blob, and current-byte SHA-256 are in evidence. |
| 3 | pass | Reason explains frozen identity/blob drift and the safe authority-free return. |
| 4 | pass | Reason explains checker-confirmed drift and records the exact deterministic evidence. |
| 5 | fail: transition | Safely blocks with a genuine drift rationale, but records a SHA-256 value other than the seeded current-byte digest. |

Codex aggregate: **3/5**. Every HEAD, payload, and seeded drift is preserved;
no canonical review receipt or final report exists. Passing runs change only
the ledger. Final receipts are `score-final-{1..5}.json`.

Sonnet:

```text
/tmp/identity-drift-final-green-sonnet.oUMM7H/run-{1..5}
CLI/model/effort: 2.1.252 (Claude Code), sonnet, medium
baseline HEADs:
d2d9429e7df8c7956564fe3789323cabd27b1935
9006adad17cd80b1b057d95c41b7bedc39aab58a
2e9d631790b07076749157da67b3035896214075
e6e088f0e405052805772a168ac4e78a3bc33d87
932d637fbdb23806d27c0048d92de654f1a208af
```

```bash
timeout 600s claude --print --no-session-persistence --model sonnet \
  --effort medium --permission-mode acceptEdits \
  --allowedTools "Bash(git *) Bash(python3 *) Bash(sha256sum *)" \
  < "/home/mark/kramtime/llm-skillbook/.worktrees/feature-forge-mvp/feature-forge/tests/behavior/identity-drift/prompt.md" \
  > "/tmp/identity-drift-final-green-sonnet.oUMM7H/host-N.out" \
  2> "/tmp/identity-drift-final-green-sonnet.oUMM7H/host-N.err"
```

| run | result | manual inspection |
| --- | --- | --- |
| 1 | fail: status; stage; next action; transition | Detects and explains the drift but asks before persisting safe-return bookkeeping. |
| 2 | pass | Reason explains the exact frozen/current-byte divergence and prohibited forward action. |
| 3 | pass | Reason explains the unreviewed frozen-specification edit and preserved state. |
| 4 | pass | Reason explains checker-confirmed identity/blob drift with exact evidence. |
| 5 | pass | Reason explains the HEAD/frozen match and working-tree divergence with exact evidence. |

Sonnet aggregate: **4/5**. Every HEAD, payload, and seeded drift is preserved;
no canonical review receipt or final report exists. Passing runs change only
the ledger; run 1 leaves it unchanged. Final receipts are
`score-final-{1..5}.json`.

## Final result

```text
Codex current payload:                3/5
Sonnet current payload:               4/5
Forward mutations:                      0
Qualification:                       PASS
```

The current-payload campaigns supersede every earlier GREEN classification for
release. Historical controls and guided results remain diagnostic evidence of
the wording change and oracle corrections only.

## Current deterministic verification

```text
python3 -m pytest \
  feature-forge/tests/test_behavior_oracle.py \
  feature-forge/tests/test_ledger_schema.py -q
34 passed

python3 -m pytest feature-forge/tests -q
238 passed, 1 skipped

python3 -m pytest tests/test_documentation.py tests/test_install.py -q
30 passed

python3 -m pytest tests -q
32 passed

cd review-loop
.venv/bin/pytest \
  ../feature-forge/tests/integration/test_review_loop_boundary.py \
  tests/integration/test_controller_clean.py -q
25 passed

claude plugin validate . --strict
Validation passed

python3 -m pytest tests/test_plugin_agents.py -q
2 passed

python3 -m py_compile feature-forge/scripts/ff-check \
  feature-forge/tests/behavior/identity_drift.py
exit 0

git diff --check
exit 0
```
