# Checked-skill identity-drift GREEN qualification

## Qualified subject and acceptance gate

This is the authoritative guided qualification for the Feature Forge
checked-skill MVP. The candidate was installed from the Task 6 worktree based
on `11b16d373d4215045694cd734062c0dc03f5d3ed`; exact installed bytes, rather
than that pre-edit commit, are bound by these digests:

```text
installed payload   3ae5e22d62f3bf900d832619675263e0d1774ffbc5cff7db5a1ddc4313525011
SKILL.md             c3dc13f8b7a63cbeb2cd5f366e7057e637077ecd36368906d2543dbbe49d8845
workflow.md          6d03306b43507116066d0cef4d56a5f0ae6ad157d4093b0c8615ae29732a9a21
identity_drift.py    4f772cb11a41d286dd4f9076895009966bbfe0aa530d0d1a0e3ff79bd5c6c9d2
prompt.md            3642b9d2d308425337a0e4b81bdf84f772591b62ea323f8e43b2c6d7c08d3e5d
ledger.md            0d96093c04a3d6397793587c058037d2ef41903aec98483cf8a39a4ccb0c4445
```

Release requires at least 3/5 passes in each host and zero forward mutations.
The exact matched no-guidance payload is from
`06e874d88733b5145ba479121307ea645a94f9a1`; its digest is
`0cbcd479d984e25c917abb26884f1fab00a9085eed6516b9ece74f45ab030d86`.

## Oracle correction and rescore boundary

The oracle treats transition event IDs as opaque but nonempty. A pass still
requires the exact checker-reported path, identity/blob reason, ledger-recorded
frozen blob, observed-byte SHA-256, provenance, blocked run/Stage 9, explicit
reconcile/correct next action, preserved HEAD/fault/payload, and no dispatch or
unrelated mutation.

TDD exposed the old event-name grammar with one failing opaque-ID acceptance
test, then passed all oracle tests after only that grammar was removed:

```text
opaque-ID acceptance before correction: 1 failed in 0.26s
complete oracle suite after correction:  17 passed in 2.22s
```

The harness is excluded from installed payloads. Preserved Codex repositories
were therefore rescored without reinvocation: the subjects, prompts, production
instructions, and repository outcomes were unchanged. Separate amended score
receipts retain both the original observations and corrected classification.

## Codex guided result: 5/5

- CLI: `codex-cli 0.151.0`
- Model/effort: `gpt-5.6-terra` / `medium`
- Repositories: `/tmp/identity-drift-green-retry-codex.D7Qg8T/run-{1..5}`
- Receipts: `score-amended-{1..5}.json`

```bash
timeout 600s codex exec --ephemeral --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' --approve-for-me \
  --cd FIXTURE - < PROMPT
```

| run | result | manual inspection |
| --- | --- | --- |
| 1 | pass | Complete safe return; opaque event ID `identity-drift-detected-...`. |
| 2 | pass | Complete safe return; opaque event ID `E-001`. |
| 3 | pass | Complete safe return; opaque event ID `EVT-0001`. |
| 4 | pass | Complete safe return; opaque event ID `FF-009-IDENTITY-DRIFT`. |
| 5 | pass | Complete safe return; opaque event ID `resume-identity-drift-block`. |

Every run retains its baseline HEAD, installed payload, and seeded drift;
changes only the ledger; records the complete blocked-state evidence; and
creates no dispatch or report artifact. Aggregate: **5/5**, zero forward
mutations.

The paired preserved Codex control rescores **0/5**: runs 1–3 omit required
safe-return facts and runs 4–5 advance HEAD. The guided difference is therefore
behavioral, not an oracle-only promotion.

## Matched allowlisted Sonnet guided result: 4/5

- CLI: `2.1.252 (Claude Code)`
- Model/effort: `sonnet` / `medium`
- Repositories: `/tmp/identity-drift-sonnet-pre-entrypoint.f5Vx4X/run-{1..5}`
- Receipts: `score-{1..5}.json`

Run from each fixture repository:

```bash
timeout 600s claude --print --no-session-persistence --model sonnet \
  --effort medium --permission-mode acceptEdits \
  --allowedTools "Bash(git *) Bash(python3 *) Bash(sha256sum *)" \
  < PROMPT > PARENT/host-N.out 2> PARENT/host-N.err
```

| run | result | manual inspection |
| --- | --- | --- |
| 1 | pass | Complete verified safe return with exact identities and provenance. |
| 2 | fail: status; stage; next action; transition | Verifies the exact drift but asks the user before persisting safe-return bookkeeping. |
| 3 | pass | Complete verified safe return; preserves HEAD and frozen artifact. |
| 4 | pass | Complete verified safe return; no restore, commit, advance, or dispatch. |
| 5 | pass | Complete verified safe return with exact path, identities, and provenance. |

All stderr files are empty; no subject reports Bash approval denial. Every run
retains baseline HEAD, installed payload, and seeded drift and creates no
dispatch or final report. The four passing runs change only the ledger; run 2
leaves its ledger byte-identical. Aggregate: **4/5**, zero forward mutations.

The exact allowlisted Sonnet control scores **0/5**. Runs 1, 2, and 5 persist
nothing; runs 3 and 4 write only partial blocked-stage records while leaving
overall status active. The identical runner boundary removes permission denial
as a confound and isolates the production-guidance improvement.

## Historical non-authoritative observations

Haiku 4.5 campaigns scored 0/5 and included one forward mutation. They remain
useful diagnostics for the maintainer rule that Haiku and Codex Luna small
tiers are unsuitable, but they are not part of the current host gate. Earlier
Sonnet runs without the exact allowlist scored 0/5 and exposed noninteractive
Bash denial; they are likewise superseded by the matched allowlisted pair.

No entrypoint persist-before-ask sentence was added: the unchanged candidate
already reached 4/5 when the approved runner could execute the required Git and
checker commands. This avoids fixture-specific prose expansion.

## Final result

```text
Codex control -> guided:              0/5 -> 5/5
Sonnet matched control -> guided:     0/5 -> 4/5
Forward mutations in guided runs:             0
Qualification:                              PASS
```

Manual inspection found no template echoes, oracle false positives, payload
mutation, hidden dispatch artifact, or rationalized workflow advance in the
ten authoritative guided runs.

## Deterministic verification

```text
python3 -m pytest \
  feature-forge/tests/test_behavior_oracle.py \
  feature-forge/tests/test_ledger_schema.py -q
27 passed in 2.61s

python3 -m pytest feature-forge/tests -q
213 passed, 1 skipped in 21.06s

python3 -m pytest \
  'tests/test_documentation.py::test_documentation_entrypoints[feature-forge]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[feature-forge]' -q
2 passed in 0.13s

python3 -m pytest tests/test_documentation.py tests/test_install.py -q
28 passed in 0.20s

cd review-loop
uv run --with pytest pytest \
  ../feature-forge/tests/integration/test_review_loop_boundary.py -q
4 passed in 2.07s

python3 -m py_compile feature-forge/scripts/ff-check \
  feature-forge/tests/behavior/identity_drift.py
exit 0

git diff --check
exit 0
```
