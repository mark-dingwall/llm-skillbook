# PR7 remediation qualification

## Frozen no-remediation baseline

This is historical qualification evidence, not operating guidance. The baseline
uses merge `da80753363a1f20bba443d892290233896f1d8ba` (main parent
`1b673eee33a9cbc360e909e3ca0015c47d65a96c`) plus Task 1's verification follow-ups,
at source HEAD `dd7a3852288a5d60701ca048287f81a3069773cf`. No Feature Forge
instruction, template, or checker changed before these observations.

Before observing responses, Codex `gpt-5.6-terra`, medium effort, was designated
the required capable qualification host. Claude `sonnet`, medium effort, is
corroborating: unavailability does not block qualification, but executed failures
remain gaps even when Codex passes. A required-host failure or unavailability
blocks qualification. This baseline records gaps; it is not a GREEN claim.

### Frozen inputs

The test-only registry, three prompts, scorer, and schema-aware fixture builder
are frozen for the later comparison. Both drift modes use identical prompt
bytes; only `fixture-input.json` selects delegated or inline execution. The
copied installed checker is loaded with `runpy`; only the known old or approved
expanded head/receipt key sets are accepted. Every clean seed passed the live
installed `ff-check audit` before the plan fault was introduced. Stage 9 retains
a passing plan review in both schemas. Expanded-schema live acceptance belongs
to the later GREEN campaign, not this record.

SHA-256:

| Input | Digest |
| --- | --- |
| `cases.json` | `20fcddfdcd41ce27b18962f17ebef4ea87acb8d77b504eadab9779dbf4abf470` |
| `worker-packet.md` | `0723fcdd926939c80ab24c571c98a01d40436de8e578a75908eb320ba98cb865` |
| `residual-minor.md` | `fd3895c85b749bf1d1000852d6fe569ff151eee4926a4f260126e045dd3b2879` |
| `post-task-plan-drift.md` | `86ea4614ce3b103204bec8313918e8df72b13319e32a99b3cbb80280db3de03f` |
| `remediation_pressure.py` | `b68473d41c6b7268a8bf361b8142b3dad1c9e139047d89495d677363171051a8` |
| Canonical specification bytes | `3210b3674e9f1cb5f8fc61fdcc7170027f90c5e9c84bdeff616f094aefc0c78b` |
| Clean frozen plan bytes | `bbe2d5867f9068f96d38d8a089619274687f9de823087203a02a5cfb32a3e819` |
| Seeded drift plan bytes | `1383d119830e03d810f442b9b2e4bbe8c62395f4a3b9e395bc1e6536079c3b5e` |
| Installed payload, both hosts | `2f1150ba0b9fe18a0775b11ecb5dde2da01f142f9eed68283648513232e01088` |

Generated `fixture-input.json` SHA-256 (equal across hosts): worker packet
`4a2f46bf24aa8b17f7cd72b13bc37c0acd48a87f3e97ef52245397ff1d3c81ff`;
residual Minor `bf73c5e091b37be1a6e214407175984795eb6c8e96807a11a2c39516ddb2f1ae`;
delegated drift `b21062c10fa916aab6b3c84112307d14dded90d419dd0e661946f6c0760c4d3c`;
inline drift `5a54e5450ca9200e75be426473bc853ad10ffe2b25c3f429ae0f6309bf1f48df`.

The payload digest hashes sorted relative entries with their types, permissions,
contents or symlink targets. It includes the installer ownership marker. Tests
confirm that the oracle, registry, test module and qualification records do not
ship in the installed payload. The fixture root retains `metadata.json`, exact
`prompt.md`, `response.txt`, `stderr.txt`, and `result.json`; metadata records
baseline HEAD, protected hashes, generated input snapshot and copied skill path.
Responses are outside the fixture repository. No fixture is deleted.

### Host execution

CLI help was checked before execution. Versions: `codex-cli 0.153.4` and
`2.1.260 (Claude Code)`. Requested models and efforts are fixed above. Codex's
stderr header exposes `model: gpt-5.6-terra` and `reasoning effort: medium`;
that is the requested name, not evidence of an immutable resolved model ID.
Claude's print output exposes no concrete resolved model ID. The floating
`sonnet` alias is not claimed as an exact model identity.

```bash
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase baseline --host codex
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase baseline --host claude
```

For every fixture the exact subprocess arguments are:

```python
[
    "codex", "exec", "--ephemeral", "--model", "gpt-5.6-terra",
    "--config", 'model_reasoning_effort="medium"', "--approve-for-me",
    "--cd", metadata["repo"], "-",
]
[
    "claude", "--print", "--no-session-persistence", "--model", "sonnet",
    "--effort", "medium", "--permission-mode", "acceptEdits",
    "--allowedTools", "Bash(git *) Bash(python3 *) Bash(sha256sum *)",
]
```

Both use the fixture repository as `cwd`, exact prompt bytes as stdin, stdout
at the external response path, stderr beside it, and a 600-second timeout. No
process HOME/CODEX_HOME override or fallback model is used. The external-model
subprocess boundary is tested with a local executable that observes actual
cwd, local payload discovery, argv and stdin; these doubles are not behavior
qualification observations.

An initial restricted-sandbox Codex campaign exited 1 before model execution
in all four fixtures: “failed to initialize in-process app-server client:
Read-only file system”. Its roots are `/tmp/ff-pr7-baseline-codex-j1xztl8w`,
`/tmp/ff-pr7-baseline-codex-28n7rpyk`, `/tmp/ff-pr7-baseline-codex-nv4gga31`,
and `/tmp/ff-pr7-baseline-codex-q5eifmbw`. The restricted Claude trial at
`/tmp/ff-pr7-baseline-claude-ty2spvp_` produced no response and was stopped when
fresh campaigns with approved host access began. These are unavailable launch
trials, not behavior failures or successful observations. The complete host
campaigns below use that host access with unchanged argument arrays and inputs.

### Observations

Each root below is prefixed `/tmp/ff-pr7-baseline-`. All eight invocations
exited 0. All eight verdicts have `head_preserved`,
`protected_paths_preserved`, and `payload_digest_preserved` true, and
`unexpected_status_paths: []`. The exact failures are:

| Host / scenario | Root suffix | Deterministic result | Classification |
| --- | --- | --- | --- |
| Codex / worker packet | `codex-j35oua_6` | FAIL: `failure-condition` | gap demonstrated |
| Codex / residual Minor | `codex-4kahh63n` | FAIL: `all-findings-actionable`, `raw-report-inventory`, `receipt-contract`, `triage-mapping` | gap demonstrated |
| Codex / delegated drift | `codex-7uzr6_yi` | PASS | already correct |
| Codex / inline drift | `codex-xbhma1co` | PASS | already correct |
| Claude / worker packet | `claude-c99x1j94` | FAIL: `failure-condition` | gap demonstrated |
| Claude / residual Minor | `claude-blnq7wxl` | FAIL: `response-shape` | gap demonstrated |
| Claude / delegated drift | `claude-f8ayjubc` | PASS | already correct |
| Claude / inline drift | `claude-ybnzcxlf` | PASS | already correct |

Codex's residual-Minor result is semantically `changes_required`, with round 2
and the old open set retained as previous evidence. Its failure on
`all-findings-actionable` is the exact mapped-ID requirement: it directly uses
`TRIAGE-MINOR-1` as a Feature Forge finding ID. This is not evidence that Codex
demoted the Minor. Its old strict receipt also lacks the complete report
inventory, charter/criterion, TRIAGE artifact and stable-ID mapping.

Claude emits prose around its proposed JSON, so the deterministic oracle
rejects the response shape before inspecting receipt fields. Manual inspection
still finds the material semantic defect: it returns `pass`, clears actionable
and open IDs, keeps round 1, proposes Stage 5 complete and specification freeze,
and omits report inventory and mapping. Its rationale is “Minor-only finding
→ `pass` per the read-only mapping table”; it calls the finding “residual human
evidence (ledger markdown)”. No ledger mutation actually occurred in this
response-only case.

### Manual North-Star assessment

The rubric is one task, scoped subject, necessary context, authority boundary,
interface boundary, goal condition, and failure condition. Every response is
read manually; string anchors never assign these judgments. Bytes and words
are diagnostics only, without a quota or pass threshold.

`Y` means satisfied, `N` means a demonstrated omission/violation. For drift,
assessment includes the durable ledger effect as well as the short response.

| Host / scenario | One task | Scoped | Necessary | Authority | Interface | Goal | Failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Codex / worker packet | Y | Y | Y | Y | Y | Y | N |
| Claude / worker packet | Y | Y | N | Y | Y | Y | N |
| Codex / residual Minor | Y | Y | Y | Y | N | N | Y |
| Claude / residual Minor | Y | Y | N | N | N | N | N |
| Codex / delegated drift | Y | Y | Y | Y | Y | Y | Y |
| Codex / inline drift | Y | Y | Y | Y | Y | Y | Y |
| Claude / delegated drift | Y | Y | Y | Y | Y | Y | Y |
| Claude / inline drift | Y | Y | Y | Y | Y | Y | Y |

Both worker packets name W-4, REQ-001, SCN-001, exact owned paths, consumed and
produced signatures, the normalization invariant, W-2/c222 and verification,
the task test command, commit/evidence return and frozen-authority boundary.
Neither tells the worker to stop or return blocked when inputs, authority or
verification are missing. Claude also surrounds the packet with commentary
and repeats the dependency evidence; its “Every field is copied verbatim”
claim does not establish the missing failure condition.

Codex's residual response uses only the requested JSON envelope and preserves
the actionable outcome, but its produced receipt and IDs fail the complete
interface and observable receipt goal. Claude substitutes Review Loop's
residual-Minor threshold for this outer-controller return, advances its
proposed head with an unresolved finding, and uses commentary to rationalize
excluding that finding from checked state.

The completed drift responses preserve the altered plan and HEAD, keep W-2
`awaiting_return`, record Stage 9 blocked, and name the exact canonical plan in
the sole reconciliation/correction action. Their ledger evidence records the
failed identity check and concrete observed plan identity. Codex delegated:
“Blocked Stage 9; W-2 remains `awaiting_return`.” Claude delegated:
“recording it complete now would be an unauthorized advance”.

Response diagnostics (UTF-8 bytes / whitespace-delimited words): Codex worker
682/91, residual 1265/12, delegated drift 435/46, inline drift 392/44; Claude
worker 1557/188, residual 1819/146, delegated drift 1345/192, inline drift
1328/189. The minified Codex
JSON illustrates why word count is not a quality measure. No numeric size
comparison contributes to any verdict.

The drift classifications cover preservation, bounded return handling and the
required reconciliation action. They do not establish every transition-log
provenance field: Claude inline wrote a midnight UTC timestamp without exposed
supporting time evidence and used `session=current`. That limitation is retained
here; the oracle has no semantic timestamp or provenance predicate. No passing
drift observation is converted into a reason to prescribe new drift wording.

### Harness verification

Before the harness existed,
`python3 -m pytest feature-forge/tests/test_remediation_pressure.py -q` collected
19 tests and failed all 19 at `assert result.returncode == 0`: the absent
script exited 2. This was a reached pytest assertion, not collection failure.
After implementation the identical command passed: **19 passed in 5.71s**.

Additional source verification: Feature Forge suite **335 passed, 1 skipped**;
its owning Review Loop integration fixture **11 passed**; root suite **33
passed**. The standalone documentation and installer gates passed **31 tests**.
The skip in the default Feature Forge suite is covered by the owning integration
environment. No user-scoped installation was changed.

## Fix Round 1 — corrected drift baseline

This appended correction supersedes the original four drift observations as
qualification evidence. Their original inputs, outputs, hashes and verdicts
remain historical above and at their retained roots. Review found that the
subject-visible `facts` included the oracle's `expected_next_action`, and that
the scorer could pass after a task-table row was deleted or altered. Those
original observations do not establish unprompted drift handling.

The registry still retains the expected action as test-only data. Preparation
now omits that field from subject inputs. The scorer compares the complete
implementation-task section to the seeded ledger at the recorded Git commit;
only the separate transition-log section may receive the intended additions.
Deletion or alteration of task state, commit, or verification evidence returns
`task-record-changed`. The prior completion/HEAD and preservation predicates
remain in force.

No prompt, registry, frozen specification/plan bytes or installed payload
changed. The corrected harness SHA-256 is
`cc9b7933755ce6ff2f5924b470cd8db0a7cf3a8ced8f1db8ba48a919276c0554`.
The installed payload remains
`2f1150ba0b9fe18a0775b11ecb5dde2da01f142f9eed68283648513232e01088`.
Corrected subject-input hashes and completed observations follow below.

Ten focused tests were added before the harness correction:

```bash
python3 -m pytest feature-forge/tests/test_remediation_pressure.py -q -k 'exclude_scorer_expected_action or rejects_task_record_changes'
```

RED: **10 failed, 19 deselected in 2.35s**. Two reached assertions found the
extra `expected_next_action` field; eight reached assertions found empty
failure lists after task deletion/state/commit/verification changes, in both
execution modes. After the correction, the identical command was GREEN:
**10 passed, 19 deselected in 2.29s**. The full focused suite passed **29 tests
in 7.74s** and the component suite passed **345 tests, 1 skipped in 46.96s**.

Only the four affected live drift observations were rerun. The retained
one-off launcher at
`.superpowers/sdd/2026-09-09-feature-forge-pr7-remediation/task-2-drift-rerun.py`
calls the corrected `prepare` and `score` functions and copies the exact pinned
host arrays from the campaign contract. It uses fixture cwd, exact unchanged
prompt bytes on stdin, response/stderr files outside the repository, and the
same 600-second timeout, without HOME/CODEX_HOME overrides or fallback models.
This is test execution, not a delegated implementer or reviewer. Commands:

```bash
python3 .superpowers/sdd/2026-09-09-feature-forge-pr7-remediation/task-2-drift-rerun.py --host codex
python3 .superpowers/sdd/2026-09-09-feature-forge-pr7-remediation/task-2-drift-rerun.py --host claude
```

Host versions, requested models and efforts are unchanged from the original
campaign. Host-access execution was approved for both launchers. The exact
resolved model identity remains unexposed beyond the requested names.

The corrected `fixture-input.json` SHA-256 is
`3ce977b8aef86fb64cce640750fe389d6e260c7ed75a489e4a5083a7c2dd1557`
for delegated execution and
`4c6d41da74bfb853e82ac3de5ea7a7053ddd5ab6d5777061c6a903cf39e3a21e`
for inline execution, equal across hosts. All four clean seeds passed their
installed audit before drift injection. All four model subprocesses exited 0;
none was unavailable. All four final verdicts have `passed: true`,
`failures: []`, `head_preserved: true`, `protected_paths_preserved: true`,
`payload_digest_preserved: true`, and `unexpected_status_paths: []`.

Retained roots below are prefixed `/tmp/ff-pr7-fix1-baseline-`; each includes
metadata, prompt, response, stderr and result JSON, plus its repository.

| Host / mode | Root suffix | Deterministic | Classification | Response bytes / words |
| --- | --- | --- | --- | --- |
| Codex / delegated | `codex-delegated-7g8k8fr7` | PASS | already correct | 493 / 61 |
| Codex / inline | `codex-inline-xfijl_xv` | PASS | already correct | 458 / 49 |
| Claude / delegated | `claude-delegated-0oupwgh_` | PASS | already correct | 1299 / 183 |
| Claude / inline | `claude-inline-ku91d3cj` | PASS | already correct | 1007 / 138 |

Manual assessment of every full response and resulting ledger diff, using the
same bounded-return rubric (`Y` means satisfied for this drift task):

| Host / mode | One task | Scoped | Necessary | Authority | Interface | Goal | Failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Codex / delegated | Y | Y | Y | Y | Y | Y | Y |
| Codex / inline | Y | Y | Y | Y | Y | Y | Y |
| Claude / delegated | Y | Y | Y | Y | Y | Y | Y |
| Claude / inline | Y | Y | Y | Y | Y | Y | Y |

Each response handles only W-2's return, confines edits to the ledger, uses the
failed identity check as the reason for blocking, preserves the exact task
table, and records the exact plan reconciliation/correction action without
advancing HEAD or altering protected bytes. Codex inline: “Blocked Stage 9 and
left W-2 `awaiting_return`”. Claude delegated: “correction is now the recorded
next action, not something I resolved unilaterally”. Claude inline:
“Controller action taken: blocked, not completed.” These corrected observations
support the targeted drift behavior without supplying its expected decision.

The earlier provenance limitation remains: the two corrected Claude ledger
rows contain midnight timestamps and parent-event identifiers without exposed
supporting evidence; those auxiliary fields are not qualified by this task's
preservation/return oracle or its bounded rubric assessment. No new drift
instruction wording is prescribed. The original worker and residual-Minor
observations remain the applicable evidence for those unchanged scenarios.

## Task 3 schema compatibility limitation

This append records controller-authorized fixture/schema exceptions, not a new
behavior observation or a rewrite of the baseline. The residual-Minor seed
keeps Stage 4 with `review_active` for the original head schema. When the
installed checker exposes the expanded head containing `mode`, setup instead
uses owning Stage 5 with `review_active`, as required by the checked lifecycle.
The exact setup difference is `stage.id: 4 -> 5`; stage state stays `active`.
The mode-bearing schema already adds the prescribed `mode: supervised` field.
Prompts, registry, all-findings expectations, and all prior baseline evidence
remain unchanged. This stage compatibility field limits strict like-for-like
comparison between baseline and later GREEN subject inputs.

The compatible harness SHA-256 is
`903f2f8516cecbcef755c537d3252a258274d9c039780d762e39dc08f913465a`.
A two-schema preparation regression observed old-schema Stage 4 passing and
expanded-schema Stage 5 failing before the change (1 failed, 1 passed). After
the one-line correction, all 31 remediation-pressure tests passed. Those are
deterministic fixture tests, not live model qualification.

The controller also authorized a matching schema-conditional scorer exception:
the old-schema return retains historical Stage 4/active; a mode-bearing
`changes_required` return must use correction Stage 3 or 4 with stage state
`active` or `complete` and the existing correction-action predicate. Retaining
Stage 5 is rejected. A new 12-case regression first failed five cases: four
valid new-schema corrections were rejected and Stage 5/active was accepted.
Seven cases, including the historical old-schema behavior, already passed.
The complete report inventory, all-findings mapping, round, identity, and
preservation predicates are unchanged. This additional oracle compatibility
exception further limits strict baseline/GREEN comparability but prevents
rewarding a current head that the binding checked lifecycle rejects. No
baseline model samples were rerun for these deterministic compatibility changes.

## Task 6 instruction qualification

These observations use the Task 5 implementation at `ba12e444` plus the Task 6
instruction delta described here. The earlier baseline and its corrections
remain unchanged. No case, pressure prompt, scorer, or fixture builder changed
in Task 6: the harness SHA-256 remains
`903f2f8516cecbcef755c537d3252a258274d9c039780d762e39dc08f913465a`,
and the four registry/prompt hashes remain those recorded above.

### Instruction changes and controls

`SKILL.md` replaces its duplicated Finish sequence with the existing workflow
owner reference, retaining the Report-before-Finish and same-operation recovery
requirements. This is equivalent prose simplification. Its diagnostic size is
2822 UTF-8 bytes / 366 whitespace-delimited words (previously 3179 / 424).

`adapters-and-reviews.md` gives the worker packet's existing fields an ordered
recipe and puts both the successful commit/evidence return and the missing
failure return in its structural Return field. The missing-field baseline
justifies that field; no new task, decision authority, artifact, or framework
is added. The success-return sentence formerly outside the block is removed as
duplicate. Its diagnostic size is 23018 bytes / 2972 words (previously
22706 / 2928); the larger reference improves the individual return contract.

`CLAUDE.md` synchronizes its review summary with zero-findings pass and the
round/repetition rule, and restores the exact documentation gate. Mode,
receipt evidence, all-findings mapping, stable allocation, same-kind retention,
Stage 4 corrections, and delegated/inline post-task identities were already
synchronized by Tasks 3 and 5 in their owning live references and were checked
against the binding contracts. `workflow.md` and `authority.md` need no Task 6
edit. The already-correct drift scenarios receive no new behavioral guidance.

The observed worker failure form was a missing required element, not a
rationalized exception: all five fresh no-guidance controls produced otherwise
bounded packets without a failure return. The test copied the full current
installed payload, used the unchanged worker pressure prompt, and invoked
the same required Codex model/effort/argument array as the baseline. One fresh
context per repetition, 600-second timeout, no fallback model or home override.

Retained roots are prefixed `/tmp/ff-pr7-micro-`. Every root keeps the prompt,
installed payload, metadata, full response, stderr and raw result JSON.

| Variant / repetition | Root suffix | Raw oracle failures | Manual content assessment |
| --- | --- | --- | --- |
| control 1 | `control-1-a9lmbzxd` | authority-boundary, failure-condition, goal-condition | Failure return absent; authority uses `spec/plan`, successful return says commit/result. |
| control 2 | `control-2-0rfkk7vs` | failure-condition | Failure return absent. |
| control 3 | `control-3-0am5vskp` | failure-condition, goal-condition | Failure return absent; successful return says commit/result. |
| control 4 | `control-4-6zx7i145` | failure-condition | Failure return absent. |
| control 5 | `control-5-bzkrak3m` | authority-boundary, failure-condition | Failure return absent; `spec/plan` abbreviation is not an authority violation. |
| candidate 1 / 1 | `candidate-1-owqr3c5m` | authority-boundary | Failure return present; `spec/plan` abbreviation only. |
| candidate 1 / 2 | `candidate-2-qmp9flhh` | none | Complete packet. |
| candidate 1 / 3 | `candidate-3-epk2jxoi` | authority-boundary | Failure return present; `spec/plan` abbreviation only. |
| candidate 1 / 4 | `candidate-4-8s44fe1t` | goal-condition | Failure return present, but successful commit/evidence return omitted. |
| candidate 1 / 5 | `candidate-5-io4dmv27` | authority-boundary, consumed-interface, goal-condition | Failure return present, but complete consumed signature and successful return omitted. |

Every control and first-candidate process exited 0 and preserved HEAD, protected
paths, and installed payload, with no unexpected status paths. Manual inspection
of every response distinguishes anchor false negatives from actual omissions.
The first candidate appended only a failure-return slot to the old semicolon
list. It is rejected because two outputs omitted the existing successful return;
the second candidate uses the ordered positive field recipe and puts both return
outcomes in one slot. No rationale table or generic prohibitions were added.

The remaining micro-observations are retained below. Candidate 2 used
"complete consumed and produced signatures"; one sample omitted the consumed
type. Candidate 3 named consumed type definitions, but self-review rejected
that wording as too narrow for function consumers or type producers. Candidate
4 preserves the general interface contract and explicitly includes both type
definitions and signatures. All final five responses satisfy the seven manual
rubric items and include both successful and blocked returns. These samples
are bounded evidence, not a statistical reliability or isolated-causation
claim: the candidate payload also contains the equivalent Finish prose cleanup.

| Variant / repetition | Root suffix | Raw oracle failures | Manual assessment |
| --- | --- | --- | --- |
| candidate 2 / 1 | `candidate2-1-hivb5rqr` | none | All seven items satisfied. |
| candidate 2 / 2 | `candidate2-2-encm7_ri` | none | All seven items satisfied. |
| candidate 2 / 3 | `candidate2-3-i59pbavm` | consumed-interface, produced-interface | Consumed type definition omitted; produced function omits `export`. |
| candidate 2 / 4 | `candidate2-4-dg38myr8` | goal-condition | Returns owned commit and verification command/result; literal `evidence` absent, no actual goal omission. |
| candidate 2 / 5 | `candidate2-5-uh0n2ye5` | none | All seven items satisfied. |
| candidate 3 / 1 | `candidate3-1-576sqnlw` | none | All seven items satisfied. |
| candidate 3 / 2 | `candidate3-2-4szn780v` | goal-condition | Complete commit and command/result return; lexical `evidence` false negative. |
| candidate 3 / 3 | `candidate3-3-og27rutc` | none | All seven items satisfied. |
| candidate 3 / 4 | `candidate3-4-0e4ehtoz` | goal-condition | Complete commit and command/result return; lexical `evidence` false negative. |
| candidate 3 / 5 | `candidate3-5-tsy4gkta` | goal-condition | Complete commit and command/result return; lexical `evidence` false negative. |
| candidate 4 / 1 retry | `candidate4-retry-1-zghjnz8b` | none | All seven items satisfied. |
| candidate 4 / 2 | `candidate4-2-75zvwbav` | goal-condition | Complete commit and command/result return; lexical `evidence` false negative. |
| candidate 4 / 3 | `candidate4-3-i5gr402_` | goal-condition | Complete commit and command/result return; lexical `evidence` false negative. |
| candidate 4 / 4 | `candidate4-4-sxa1j1ez` | none | All seven items satisfied. |
| candidate 4 / 5 | `candidate4-5-fh5894n3` | goal-condition | Complete commit and passing command/result return; lexical `evidence` false negative. |

All observed processes exited 0 and all preservation predicates passed. The
original candidate-4 repetition 1 at `candidate4-1-0415vqu6` failed during
fixture preparation before any model invocation: concurrent `runpy` temporary
module registration is unsafe. The one-off launcher serialized preparation
and reran only that unavailable sample in a fresh context. Production code and
the frozen harness were untouched. Candidate 4's other four independent fixture
subjects ran concurrently; prior variants ran sequentially. Every complete
response above was manually read, including all anchor failures.

The controller ruled to preserve raw oracle results and assign dispositions
using observed effects plus the same manual rubric, without changing the
scorer or tuning wording to lexical anchors. Cost: some passing semantic
dispositions coexist with raw anchor failures and require the documented
manual judgment; these are never reported as raw-oracle passes.

### Seven composed dispatch packets

Exact retained fixtures are under `/tmp/ff-pr7-task6-packets-scgkigym/` with
the filenames below. `inventory.json` records SHA-256, bytes, and words;
`compose.py` captures the one-off composition recipe and can be rerun from the
repository root. These are qualification fixtures, not installed prompt
machinery. Stage fixtures instantiate one small normalization work unit and
select the live method/worker sections; the brainstorming fixture also consumes
the authority-owned specification shape. Review fixtures use the live
`render_prompt("review", ("safety", "round-one", "holistic"), context)` with
Feature Forge focus/finding/criterion/mounted-input content in `subject` only.
Stable-ID input is the full normalized prior/current finding shape required by
Task 5, with an exact criterion and strict decision return. No controller
ledger or unrelated workflow history is supplied to the review packets.

Rubric columns: one task (T), scoped subject (S), necessary context (N), authority
(A), interface (I), goal (G), failure (F). `Y` means the final content judgment
satisfies that item; counts do not determine any verdict.

| Fixture `.md` basename | Live source sections | Bytes / words | T | S | N | A | I | G | F | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| brainstorm-return | adapters: brainstorm-return; authority: specification contract | 3961 / 490 | Y | Y | Y | Y | Y | Y | Y | pass |
| plan-return | adapters: plan-return | 2342 / 285 | Y | Y | Y | Y | Y | Y | Y | pass |
| execute-return-worker | adapters: worker packet | 1057 / 129 | Y | Y | Y | Y | Y | Y | Y | pass |
| stable-finding-id | adapters: stable-finding-ID judgment | 3114 / 302 | Y | Y | Y* | Y | Y | Y | Y | pass |
| specification-review | adapters: specification review/finding contract; Review Loop review + safety/round-one/holistic | 3724 / 499 | Y | Y | Y | Y | Y | Y | Y | pass |
| plan-review | adapters: plan review/finding contract; same Review Loop resources | 3750 / 506 | Y | Y | Y | Y | Y | Y | Y | pass |
| implementation-review | adapters: implementation review/finding contract; same Review Loop resources | 3995 / 525 | Y | Y | Y | Y | Y | Y | Y | pass |

Three fresh noninteractive Codex `gpt-6-astra`, high-effort test subjects
reviewed the returns/worker family, mapping family, and three-review family.
Their only supplied prompt was the composed packets plus the exact seven-item
rubric from Task 6. The first launch attempts failed before model execution
because the disposable packet directory was not a Git repository. The retry
added `--skip-git-repo-check` and all three exited 0. Initial packets, prompts,
responses and stderr remain in `/tmp/ff-pr7-task6-packets-rpqu2qau/` as
`review2-returns`, `review2-mapping`, and `review2-reviews` files. The revised
worker alone received scoped re-reviews. One found a real composition mismatch:
the fixture included the controller's "Write one packet" instructions alongside
the worker's implementation task. The existing owner now labels who fills the
fields, and the fixture contains only the resulting filled task. This is a
structural role/composition correction, not a new behavioral rule. The final
scoped re-review (seven yes verdicts) is retained as `review2-worker` files in
`/tmp/ff-pr7-task6-packets-2m0_w0kx/`; the final worker bytes are unchanged.
Self-review also corrected the synthetic mapping fixture's `source_ids` from
bare finding IDs to the live `report_id:finding_id` form. The corrected input
passes the installed pure `apply_stable_id_decisions` function; its exact input
and passing result are retained in `mapping-validation.json`. Only mapping
was re-reviewed after that fixture correction (`review2-mapping` in the final
directory), retaining the same sole necessary-context disagreement. No mapper
code or live mapping contract changed. Intermediate packet/review evidence remains at
`/tmp/ff-pr7-task6-packets-s8_l1uer/` and
`/tmp/ff-pr7-task6-packets-mt7jux6d/`. Other final packet
hashes are identical to their originally reviewed bytes.

The reviewers found every item satisfied except mapping necessary-context (*):
that reviewer called `target_seal` unused once verification is complete. The
controller ruled to retain it as the binding Task 5 normalized-object interface
and identity context tying claim/evidence locators to the prior/current sealed
subject, not as a second verification request. This disagreement is retained;
the final N verdict is the controller's content judgment, not an all-yes reviewer
claim. Cost: the semantic packet retains one identity field the reviewer judged
unnecessary. Removing it would reopen the fixed mapper interface and its full
finding evidence contract. No additional guidance or schema change followed.

`git diff --name-only origin/main...HEAD -- review-loop` identified only
`pyproject.toml`, `scripts/py`, the two containment integration tests, and
`uv.lock`. No Review Loop prompt resource is changed by integration; therefore
there are no extra Review Loop-template rows beyond the three Feature Forge
compositions above. Full normalized findings account for the mapping fixture's
size; declared input paths and strict external report fields account for the
review fixtures' size. Neither is compared against a numeric target.

### Exact GREEN campaigns and observed remaining gaps

Both exact Task 2 commands were executed with `--phase green`, against the
unchanged scenarios, host arrays, models/efforts and 600-second limits. All eight
processes exited 0; none was unavailable. Every result preserves HEAD, protected
paths and payload with no unexpected status paths. The installed payload digest
is `0095790d407f4c89c2937dc6bf9548988fcee31105ce4dd0e0521d5eaf980e50`
for all eight. Roots below have prefix `/tmp/ff-pr7-green-`.

| Host / scenario | Root suffix | Baseline classification | Raw GREEN result | Manual GREEN disposition |
| --- | --- | --- | --- | --- |
| Codex / worker | `codex-j_ocyz3c` | gap demonstrated | goal-condition anchor failure | pass: complete packet; exact command/result is evidence despite absent literal word |
| Claude / worker | `claude-37wv65fj` | gap demonstrated | goal-condition anchor failure | fail: complete packet body, but surplus commentary and adjacent ledger instruction |
| Codex / residual Minor | `codex-7u6uyk3_` | gap demonstrated | pass | pass within the criterion-fidelity limit below |
| Claude / residual Minor | `claude-b7z5u1pj` | gap demonstrated | response-shape failure | fail: correct structured content wrapped in explanatory prose |
| Codex / delegated drift | `codex-t0zgls7f` | already correct (corrected baseline) | pass | pass |
| Codex / inline drift | `codex-zn6faddm` | already correct (corrected baseline) | pass | pass |
| Claude / delegated drift | `claude-wqjpjj__` | already correct (corrected baseline) | pass | pass |
| Claude / inline drift | `claude-qsxxhvh9` | already correct (corrected baseline) | pass | pass |

The Codex worker returns "owned commit and `npm test -- tenant.normalize`
result" and the full function/type/invariant, dependency, authority and failure
fields; manual T/S/N/A/I/G/F are all Y. Claude's worker packet wraps `ASCII`
and `space` across a newline, causing the raw goal anchor failure despite a
complete invariant. That is a lexical false negative, but the independent
manual N failure is real: narration around the requested packet and an extra
instruction to complete the W-2 ledger row. Other manual worker items are Y.

Both residual responses retain every report ID, the exact allocated new stable
ID and mapping, round 2, prior `FF-OLD`, mode, root, and Stage 3 correction; no
Minor is discarded or passed. Codex returns just the requested JSON; Claude
adds explanation and a note around it (manual interface/goal fail, plus
unnecessary context). The immutable fixture supplies no exact prior
`completion_criterion`; this scenario proves only construction of a nonempty
criterion, not fidelity to the exact criterion previously delivered. Claude
explicitly calls its criterion reconstructed. The controller accepted recording
that limitation without changing the immutable scenario; live delivery remains
an adapter obligation and is not established by this fixture.

All four drift responses and ledger diffs were read. They keep W-2
`awaiting_return`, preserve the implementation table/HEAD/frozen bytes, block
Stage 9, and record the exact canonical plan reconciliation action with failed
identity evidence. Their manual T/S/N/A/I/G/F are all Y. The baseline's limited
claims about auxiliary timestamp/session provenance remain; the oracle measures
observable returned state and preservation, not every historical claim.

### Claude response-boundary controls

The two executed Claude failures above are retained, not treated as host
unavailability or erased by Codex passing. Five fresh worker controls all
reproduced surplus narration; a "filled fields only" candidate and a second
conditional "complete response / Task first, Return last" candidate each still
produced narration in all five samples. Both ineffective clauses were removed;
the tested ordered field recipe and successful/blocked Return slot remain.

Roots have prefix `/tmp/ff-pr7-micro-`. Each group lists repetitions 1 through 5:

| Group | Root suffixes | Raw failures by repetition | Manual shape result |
| --- | --- | --- | --- |
| Claude worker controls | `claude-control-1-wfrpf1uk`, `claude-control-2-z98dmnlz`, `claude-control-3-0nfyzw_x`, `claude-control-4-bw465trk`, `claude-control-5-cy89rykl` | goal, goal, goal, none, none | Surplus narration in 5/5. |
| Filled-fields candidate | `claude-packet-candidate-1-fx8eq7qv`, `claude-packet-candidate-2-a0uqluxo`, `claude-packet-candidate-3-eeeqafes`, `claude-packet-candidate-4-aio3fhed`, `claude-packet-candidate-5-e31v6gea` | none, none, none, goal, none | Surplus narration in 5/5; rejected. |
| Conditional response candidate | `claude-packet-candidate2-1-_2hy69by`, `claude-packet-candidate2-2-z0ern_q1`, `claude-packet-candidate2-3-jvti_y2r`, `claude-packet-candidate2-4-l9xjfcj6`, `claude-packet-candidate2-5-y31zcg5f` | none in all five | Surplus narration in 5/5; rejected. |
| Claude residual controls | `claude-residual-control-1-ofqd_ubu`, `claude-residual-control-2-ck4_afzt`, `claude-residual-control-3-15jgqq1y`, `claude-residual-control-4-f14xv8xe`, `claude-residual-control-5-ud0x5fdt` | response-shape in all five | Correct substantive JSON wrapped in prose in 5/5. |

"goal" above means the raw `goal-condition` anchor: worker controls 1/2 use
command/result without literal `evidence` and wrap `ASCII space`; control 3 and
filled-fields candidate 4 wrap `ASCII space`. Complete required fields remain
present. Every full response was read, not merely scored. All observed processes
exited 0 and preservation predicates passed. Residual control 5 claims a scratch
file was removed; the oracle establishes final-state preservation, not absence
of transient writes, so no stronger claim is made.

Read-only host diagnosis found a competing instruction in the user's existing
Claude configuration: "Adjacent problems: please do tell me about them — one
line at the end", along with instructions to challenge poor choices. The
outputs repeatedly correct the colleague/coordinator and add adjacent notes.
This is diagnostic context, not an excuse for the failed exact return or a new
project dependency. No host configuration was changed, and no model, prompt,
home directory or scorer substitution was used. Controller-authorized
response-boundary micro-tests add no artifact, schema, or authority; their
cost is additional qualification runs and an explicit distinction between
packet content and the complete requested response.

The bounded complete-JSON receipt recipe also failed in all five fresh samples:
`claude-residual-candidate-1-8yyxhv8s`,
`claude-residual-candidate-2-l6s0v5b9`,
`claude-residual-candidate-3-6jxhh312`,
`claude-residual-candidate-4-rlozaoql`, and
`claude-residual-candidate-5-qoevblnn` (same `/tmp/ff-pr7-micro-` prefix).
Each process exited 0 with raw `response-shape` failure and passing final-state
preservation. Each full response was read: the substantive receipt/head remains
`changes_required`, round 2, correctly mapped with mode/history retained, but
prose still surrounds the JSON. The ineffective receipt recipe was removed.
No affected GREEN replay is claimed because no wrapper-suppression candidate
qualified for retention.

**Qualification disposition: incomplete.** The seven composed packet shapes
pass their content rubric with the recorded mapping ruling, and all four
required Codex scenarios pass the manual rubric/observable predicates. The
two executed Claude response-shape gaps remain `fail`, so Task 6's no-fail-row
acceptance condition is not satisfied. Expanding prompt machinery, changing
the immutable scenario/host contract, or weakening this condition would require
a controller decision outside this implementation subtask; no such change is
implied by these records.

## Task 6 Fix Round 1: authorized Claude GREEN transport correction

The user authorized a bounded test-host adapter correction after the incomplete
disposition above. The binding design, plan and task scope now permit Claude
GREEN alone to append `--output-format json --json-schema <scenario-schema>`.
Baseline argv, every Codex argv, scenario bytes, preparation and scorer
semantics remain unchanged. No live skill instruction or host configuration
changed in this fix. Every earlier result above remains historical evidence.

Worker output is an exact object of seven required string fields: `task`,
`ownership`, `interfaces`, `dependencies`, `verification`, `authority`, `return`.
Residual output is exactly the required objects `receipt` and `head`, with deep
content left to the frozen oracle and existing checker. Drift output has only
a required `summary` string: its schema supplies no action or verdict. The
worker fields have generic implementation-role descriptions, not fixture
values, expected dispositions or scorer wording. This is schema/role
synchronization, not additional behavioral guidance in the installed skill.

Each root retains the original bytes in `claude-envelope.json` outside its
fixture repository. The adapter requires process exit 0 and a successful
result envelope with present schema-valid `structured_output`; it never falls
back to the separate conversational `result`. It renders worker fields in
fixed order, serializes receipt/head as sorted compact JSON, and materializes
the drift summary to `response.txt` for the unchanged scorer/manual rubric.
Duplicate JSON keys, non-JSON numeric constants, malformed/missing fields and
unsuccessful envelopes fail closed. An executed malformed return is a failure,
not unavailability. Generic, schema-valid but semantically wrong model output
continues to fail the oracle in the regression tests.

**Comparability cost:** the new observations qualify the structured return
channel, not suppression of Claude's separate conversational prose. The raw
envelopes preserve that prose. Comparing the old plain-text baseline/first
GREEN with these rows changes the transport as well as the earlier instruction
payload; it cannot isolate a prompt-only effect or establish reliable
plain-text conformance. Baseline reproducibility is retained through its exact
legacy invocation. No production host adapter or new installed dependency is
claimed by this test-only correction.

### Adapter RED/GREEN and first structured campaign

New CLI-boundary tests replace only the external model executable; real
preparation, installation, Git state, capture and scoring execute. They check
exact argv across host/phase combinations, all scenario schemas without oracle
answers, raw byte preservation outside the repository, deterministic extraction,
and missing, null, extra, wrongly typed or absent fields, envelope errors,
nonzero exits, malformed JSON, duplicate keys and non-JSON numbers.

- Initial adapter tests: `python3 -m pytest
  feature-forge/tests/test_remediation_pressure.py -q -k 'claude_green'` reached
  assertions and failed **11 tests**, with 44 deselected; after implementation,
  the full owning suite passed **55 tests**.
- Strict JSON follow-up: `-k 'nan or duplicate'` reached two failures; strict
  parsing fixed both. The combined harness/ledger suite then passed **67 tests**.
- After the first structured worker observation below, the generic role-field
  regression (`-k 'exact_structured_argv'`) failed at the missing description;
  adding the authorized answer-free descriptions made it pass (56 deselected).

The exact command was run twice, each time across all four scenarios:

```bash
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase green --host claude
```

The first run used bare worker field names. All four invocations exited 0,
returned successful structured envelopes, and passed preservation predicates.
Roots below use prefix `/tmp/ff-pr7-green-claude-`:

| First structured scenario | Root suffix | Raw oracle | Manual disposition |
| --- | --- | --- | --- |
| Worker | `4mt3vum7` | six failed content predicates | fail: reported the packet-composition task rather than supplying implementation-worker instructions |
| Residual Minor | `w35a9_6s` | pass | pass |
| Delegated drift | `zlib7wxx` | pass | pass |
| Inline drift | `wonnv24q` | pass | pass |

The worker failures were authority boundary, consumed interface, failure
condition, goal condition, owned paths and produced interface: these were real
semantic failures, not lexical false negatives. Bare schema labels allowed
the model to describe its own composition activity. The controller approved
only scenario-independent role descriptions to disambiguate whose task and
inputs the fields describe. The first run, including this failure and its full
envelope, remains intact; no selective erasure or scorer change occurred.
The passing residual response retains the Minor as actionable with the correct
new stable ID, report inventory, round/history and correction stage. Both
drift ledger diffs preserve the task row and frozen bytes, block Stage 9 and
record the exact plan reconciliation action. Their bounded manual
T/S/N/A/I/G/F dispositions are all Y, with the previously stated limits on
auxiliary timestamp/provenance claims.

### Corrected full Claude GREEN replay and final disposition

All four corrected invocations exited 0 with successful, schema-valid envelopes,
no transport error and no unavailability. Every raw oracle passes, including
HEAD, protected-path and installed-payload preservation with no unexpected
status paths. Each complete materialized response and both drift ledger diffs
were read. The same seven-item rubric applies; no string anchor substitutes
for these judgments. Root prefix remains `/tmp/ff-pr7-green-claude-`.

| Scenario | Root suffix | Raw oracle | T | S | N | A | I | G | F | Materialized bytes / words |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Worker | `eq3_6yl0` | pass | Y | Y | Y | Y | Y | Y | Y | 1123 / 140 |
| Residual Minor | `31sc9uva` | pass | Y | Y | Y | Y | Y | Y | Y | 2001 / 33 |
| Delegated drift | `9fb4debz` | pass | Y | Y | Y | Y | Y | Y | Y | 1059 / 154 |
| Inline drift | `tmxzqjy7` | pass | Y | Y | Y | Y | Y | Y | Y | 1291 / 178 |

The worker contains only the filled implementation packet, with W-4/REQ-001/
SCN-001, exact owned paths, complete consumed type/produced signature/invariant,
verified W-2 dependency, the verification command/result requirement, frozen
artifact and cross-task boundaries, and successful/blocked return conditions.
It does not repeat the first structured run's composition-role mistake.

The residual object retains both reports, including the empty one, exactly
maps the TRIAGE finding to the allocated stable ID, retains `FF-OLD` as previous
history, increments to round 2, preserves mode/root and sets `changes_required`
with Stage 3 correction. No Minor is downgraded or discarded. As before, the
fixture does not supply the dispatched completion criterion: this response
proves nonempty construction, not exact fidelity to a supplied prior criterion.

Both drift outputs take only the ledger action, retain W-2 `awaiting_return`
and its full row, block Stage 9, record identity-failure evidence and leave the
exact plan reconciliation as next action without restoring, committing,
advancing or dispatching. Their brief related receipt-mismatch notes do not
create another task or exercise correction authority. Inline additionally
records that mismatch in the permitted ledger; its claim that the mismatch is
"pre-existing" is not established by this run's clean seed audit. As in the
earlier drift evidence, auxiliary chronology/session assertions are not part
of the qualified observable effects and are not endorsed. Final preservation
does not establish absence of transient writes.

No new lexical false negative occurs in either structured campaign: the first
worker's failures were genuine and corrected; all latest raw rows pass. The
original Codex worker's literal-`evidence` false negative remains explicitly
itemized above and its manual disposition remains pass. Original Claude
plain-text shape failures are historical failures, resolved for the authorized
structured channel only, not relabeled as lexical errors or unavailability.

The final harness SHA-256 is
`6a124fa51102a5244c674c3b9330cfe59f4699c6aeb5d089c878b0b71429015d`.
Cases and all three prompt hashes match the original recorded values. The
installed payload remains
`0095790d407f4c89c2937dc6bf9548988fcee31105ce4dd0e0521d5eaf980e50`;
therefore the previously passing Codex campaign and seven composed-packet
reviews still apply. Their counts and mapping-context ruling are unchanged.
Structured JSON word counts are serialization diagnostics, not evidence of
prompt simplification or a pass threshold.

Fresh final verification:

```bash
python3 -m pytest feature-forge/tests/test_ledger_schema.py feature-forge/tests/test_remediation_pressure.py -q
python3 -m pytest 'tests/test_documentation.py::test_documentation_entrypoints[feature-forge]' 'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[feature-forge]' -q
python3 -m pytest tests/test_documentation.py -q
git diff --check
```

Results: **67 passed** (23.35s), **2 passed** (0.12s), **20 passed** (0.12s),
and clean diff whitespace. Self-review confirms adapter-only harness changes,
unchanged scorer/preparation and frozen inputs, append-only qualification
history, explicit five-path scope, and unchanged AGENTS symlink metadata.

**Current Task 6 disposition: qualified under the authorized structured-output
boundary.** The four required Codex manual/effect rows and all four corrected
Claude raw/manual/effect rows pass; no current fail row remains. Historical
failures and the transport, criterion-fidelity and auxiliary-provenance limits
above remain part of the evidence. Task 7 still owns cross-cutting verification.

## Task 7: Cross-cutting verification

All complete-suite evidence in this section exercised production commit
`94e10be28f99ddd1fa1f0e2da68aa33e8e65f74a` before this evidence-only record
was committed. The preflight branch was
`feature-forge-mvp...origin/feature-forge-mvp [ahead 36]`, with no uncommitted
paths. `git log --oneline --decorate --graph origin/main..HEAD`,
`git diff --stat origin/main...HEAD`, and
`git diff --name-status origin/main...HEAD` confirmed the reviewed remediation
scope: Feature Forge, the approved Task 1 Review Loop reconciliation, and
approved repository documentation, installer, and test changes.

| Command | Exit | Result / availability |
| --- | --- | --- |
| `python3 -m pytest feature-forge/tests -q` | 0 | 649 passed, 1 skipped in 88.60s. The skipped integration import is covered by the owning Review Loop invocation below. |
| `cd review-loop && uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q` | 0 | 24 passed in 13.37s. |
| `cd review-loop && uv run pytest -q` (restricted sandbox) | 1 | 27 failed, 483 passed, 1 skipped in 386.58s. Every material failure traces to the sandbox preventing bwrap network-namespace setup (`Failed to create NETLINK_ROUTE socket: Operation not permitted`) or UNIX-socket creation; this made containment gates report `FAILED` and cascaded into controller tests. This is unavailable environmental evidence, not a production defect disposition. |
| `cd review-loop && uv run pytest -q` (required host access) | 0 | 510 passed, 1 skipped in 18.51s. This is the applicable owning-suite result. |
| `python3 -m pytest tests/test_install.py -q` | 0 | 11 passed in 0.29s. |
| `python3 -m pytest tests/test_documentation.py -q` | 0 | 20 passed in 0.14s. |
| `python3 -m pytest tests/test_plugin_agents.py -q` | 0 | 2 passed in 0.11s. |
| `claude plugin validate . --strict` | 0 | Marketplace manifest validation passed. |
| `python3 -m pytest tests -q` | 0 | 33 passed in 0.28s. |
| `python3 -m py_compile feature-forge/scripts/ff-check feature-forge/tests/behavior/remediation_pressure.py` | 0 | Both target files compiled without syntax errors. |
| `git diff --check origin/main...HEAD` | 0 | No whitespace errors. |
| `git status --short --branch` | 0 | No uncommitted paths; branch was ahead of `origin/feature-forge-mvp` by 36 commits. |

**Task 7 qualification disposition:** all required production verification
gates pass at `94e10be` when containment tests run with the host capability
they require. The restricted-sandbox Review Loop attempt is retained as an
environmental limitation and was not used to waive the full owning suite.
Task 6 remains qualified under its authorized structured-output boundary; its
historical transport, criterion-fidelity, and auxiliary-provenance limits are
unchanged. No unavailable required evidence remains.

### Task 7 Fix Round 1: Review Loop skip evidence

The full owning Review Loop result above includes one intentional, documented
skip. The following narrow confirmation was run in the owning environment:

```bash
cd review-loop && uv run pytest tests/integration/test_execution_containment.py::ContainmentTests::test_evidence_gate_and_fix_mappings_are_out_of_scope_for_task_5 -q -rs
```

Exit status: 0. Result: `1 skipped in 0.02s`. Exact pytest reason:
`evidence-gate/FIX mapping is out of scope for Task 5 (ordinary mapping only)`
at `tests/integration/test_execution_containment.py:258`. This is an explicit
scope placeholder, not an unavailable test environment or an unexamined test
failure. No production behavior, previous verification result, or
qualification disposition changed.

## Final-review fix: refreshed production verification

These fresh results exercise production fix commit
`be9d3194277a4c368ccf791be0abd8e7a13d5ebb`. The fix adds type guards before
enum membership so malformed JSON values return `unverifiable` instead of a
traceback. Only the installed checker and its regression tests changed; no
dispatch composition changed, so the existing seven packet-family reviews
remain applicable. This append preserves all earlier observations.

Preflight `git status --short --branch` showed no uncommitted paths, on
`feature-forge-mvp` ahead of its remote by 39 commits. The graph, diff stat,
and name-status review of `origin/main...HEAD` confirmed the same approved
Feature Forge, Task 1 Review Loop, and repository integration scope.

| Command | Exit | Result / availability |
| --- | --- | --- |
| `python3 -m pytest feature-forge/tests/test_ff_check_audit.py -q -k unhashable --tb=short` (before the fix) | 1 | 24 failed, 360 deselected in 4.04s; each real public command raised the reported unhashable dict/list TypeError. |
| Same 24-case command after the fix | 0 | 24 passed, 360 deselected in 2.53s; each requires exit 2, exactly one unverifiable line, stable unsupported diagnostics and no traceback. |
| `python3 -m pytest feature-forge/tests/test_ff_check_runs.py feature-forge/tests/test_ff_check_audit.py feature-forge/tests/test_ff_check_reviewed_snapshot.py -q` | 0 | 525 passed in 50.33s. |
| `python3 -m pytest feature-forge/tests -q` | 0 | 673 passed, 1 skipped in 91.49s. The integration module skips when `review_loop` is unavailable to root Python; its complete owning-environment result follows. |
| `cd review-loop && uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q` | 0 | 24 passed in 9.35s. |
| `cd review-loop && uv run pytest -q -rs` (required host access) | 0 | 510 passed, 1 skipped in 25.17s. Exact skip reason: `evidence-gate/FIX mapping is out of scope for Task 5 (ordinary mapping only)` at `tests/integration/test_execution_containment.py:258`. |
| `python3 -m pytest tests/test_install.py -q` | 0 | 11 passed in 0.34s. |
| `python3 -m pytest tests/test_documentation.py -q` | 0 | 20 passed in 0.14s. |
| `python3 -m pytest tests/test_plugin_agents.py -q` | 0 | 2 passed in 0.12s. |
| `claude plugin validate . --strict` | 0 | Marketplace manifest validation passed. |
| `python3 -m pytest tests -q` | 0 | 33 passed in 0.29s. |
| `python3 -m py_compile feature-forge/scripts/ff-check feature-forge/tests/behavior/remediation_pressure.py` | 0 | Both files compiled successfully. |
| `git diff --check origin/main...HEAD` | 0 | No whitespace errors. |
| `git status --short --branch` | 0 | Clean before this evidence append; ahead 39. |

The full Feature Forge and focused checker runs preceded the production commit
and exercised its exact code bytes; the remaining gates ran after that commit.
No source files changed between those checks. The subsequent evidence commit
contains only this qualification record. There is no unavailable required
deterministic evidence; the documented Review Loop scope placeholder is not
claimed as exercised coverage.

### Fresh immutable GREEN campaigns after the checker fix

Both complete campaign commands use fresh installed fixtures and the unchanged
case registry and prompt hashes recorded above:

```bash
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase green --host codex
python3 feature-forge/tests/behavior/remediation_pressure.py campaign --phase green --host claude
```

The exact installed payload digest is
`f3f0947235ff3a23f9699cbc4ca4de1a998a2d4fd9519543507f82cbf13d06b6`.
The harness SHA-256 is
`bb4ac35880d62447601353408d859441ffbfcda1d8edf0d57f8b0ce1926c8b03`,
including the already committed Task 6 structured-timeout classification fix.
This final wave changes neither harness, scorer, preparation nor prompts.
Versions remain `codex-cli 0.153.4` and `2.1.260 (Claude Code)`; models/efforts
remain the required Codex `gpt-5.6-terra`/medium and corroborating Claude
`sonnet`/medium. Codex exposes the requested model name, not an immutable
resolved ID. Claude's worker envelope exposes `claude-sonnet-5` as its
canonical model. Full argv, response, stderr, fixture metadata and verdict are
retained in each root; Claude additionally retains the raw JSON envelope and
deterministically materialized response. No fixture was deleted.

Codex completed all four invocations with exit 0 and no unavailability. All
four preserve HEAD, protected paths and installed payload with no unexpected
status paths. Complete responses and both drift ledger diffs were read.

| Codex scenario | Root | Raw oracle | T | S | N | A | I | G | F | Manual disposition | Bytes / words |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Worker | `/tmp/ff-pr7-green-codex-yazvjy44` | goal-condition anchor failure | Y | Y | Y | Y | Y | Y | Y | pass | 805 / 96 |
| Residual Minor | `/tmp/ff-pr7-green-codex-_u9p8hc7` | pass | Y | Y | Y | Y | Y | Y | Y | pass | 1817 / 17 |
| Delegated drift | `/tmp/ff-pr7-green-codex-462o4rh6` | pass | Y | Y | Y | Y | Y | Y | Y | pass | 456 / 57 |
| Inline drift | `/tmp/ff-pr7-green-codex-rqxsc_6j` | pass | Y | Y | Y | Y | Y | Y | Y | pass | 403 / 45 |

The worker repeats the previously itemized lexical false negative: it requires
the exact verification command and its result and an owned commit, but omits
the literal word `evidence`. Its complete consumed/produced interface,
normalization invariant, exact owned paths, verified W-2 dependency, frozen
authority and blocked return condition are all present. The actual goal and
return evidence are clear; the raw anchor remains a recorded failure and the
independent manual disposition is pass. No scorer was changed.

The residual response retains both consumed reports, the actionable Minor,
one exact allocated stable-ID mapping, prior `FF-OLD` history, root/mode and
round 2, and routes correction to Stage 3. Both drift returns change only the
permitted ledger, preserve the full W-2 awaiting-return row, block Stage 9,
record exact plan path/blob/hash evidence and leave reconciliation as the
sole next action. These reproduce the earlier qualified effects. The prior
criterion-fidelity, auxiliary timestamp/provenance and transient-write limits
still apply; final preservation alone is not evidence of no transient writes.

The Claude campaign completed worker, residual and delegated drift before an
orchestrator model-capacity interruption. Their durable `result.json` files
each record host exit 0, no unavailability, schema success and all preservation
predicates passing. The interrupted inline root
`/tmp/ff-pr7-green-claude-44s37v8y` retains metadata and prompt, zero-byte
envelope/stderr, no response/result and an unchanged ledger. It proves no
completed behavioral observation and is retained as interrupted evidence,
not counted as either a pass or an executed timeout. The enclosing campaign's
exit status was not recovered; its completed per-row results remain available.

Only the missing inline observation was replayed, through
`python3 /tmp/ff-pr7-inline-replay-tNIeDU/replay.py`. This retained scratch
wrapper loads the unchanged harness's preparation, schema, materialization
and scorer functions and uses the exact Claude GREEN argv and 600-second
timeout classification. It creates a fresh fixture, records raw capture and
the ordinary per-row result, and names the interrupted root. No successful
row was rerun and no production/harness source was edited.

| Claude scenario | Root | Raw oracle | T | S | N | A | I | G | F | Manual disposition | Bytes / words |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Worker | `/tmp/ff-pr7-green-claude-2y2n7s1w` | pass | Y | Y | Y | Y | Y | Y | Y | pass | 1060 / 126 |
| Residual Minor | `/tmp/ff-pr7-green-claude-wfi1swq6` | pass | Y | Y | Y | Y | Y | Y | Y | pass | 1859 / 17 |
| Delegated drift | `/tmp/ff-pr7-green-claude-l1ldkwgo` | pass | Y | Y | Y | Y | Y | Y | Y | pass | 1537 / 212 |
| Inline drift (resumed row) | `/tmp/ff-pr7-green-claude-2lfcweb7` | pass | Y | Y | Y | Y | Y | Y | Y | pass | 1080 / 150 |

The worker artifact supplies the actual implementation packet with all seven
fields and no adjacent instruction. The residual artifact retains both reports,
one actionable Minor and exact stable mapping, mode/root/history, round 2 and
Stage 3 correction. Its completion criterion uses the imprecise phrase
"frozen specification candidate"; as in earlier runs, the fixture has no
supplied dispatched criterion, so exact criterion fidelity is not qualified.

Delegated drift preserves the full pending W-2 row and frozen bytes, blocks
Stage 9, records the exact path/blob/hash and makes reconciliation the sole
next action. Its envelope exposes one denied initial Bash invocation; the
completed artifact and observed effects still pass. Its auxiliary claim of a
"pre-existing" receipt source mismatch is not established by the clean seed
audit and is not endorsed. This is the same evidence limitation already
recorded above, not additional authority to correct that receipt.

The fresh inline replay exited 0 with a successful structured envelope, no
transport error or unavailability, and all raw predicates passing. Its complete
response and ledger diff were read: the authoritative head has status and
Stage 9 state both blocked, the full W-2 row remains awaiting_return, exact
path/blob/hash evidence is recorded and the plan reconciliation is the sole
next action. Its auxiliary transition-log shorthand does not exactly mirror
the blocked stage state, and its timestamp/parent-event assertions are not
established by this fixture; these are not endorsed by the qualification of
the authoritative head and observable effects. All four completed Claude
envelopes report canonical model `claude-sonnet-5`.

The Codex campaign command exited 0. The original Claude command's enclosing
exit is unavailable because of the orchestration interruption; all three
completed row processes and the replacement inline process exited 0, as did
the replay wrapper. This completes all four required observations per host
without rerunning a successful row. No structured-output timeout occurred.

**Current final-fix qualification disposition: qualified.** All eight current
manual rubric/observable-effect rows pass at the new installed payload, with
the one preserved Codex worker lexical false negative and the explicit
historical/evidence limitations above. The interrupted, incomplete Claude
root is retained, and its missing observation is supplied by the fresh inline
replay. No unavailable required gate or current behavioral failure remains.

## Correction: completed Claude inline failure and authorized experiment

The preceding interruption/replay account and qualified disposition were
premature. A later durable result for `/tmp/ff-pr7-green-claude-44s37v8y`
establishes completed host exit 0, successful structured output and a genuine
`task-record-changed` failure. The W-2 state cell was changed from
`awaiting_return` to `awaiting_return (return processing held for frozen-plan
drift, see Blockers)`. HEAD, frozen paths and payload were preserved, but the
implementation task table was not. Its original response, envelope, result
and ledger remain retained. The passing `2lfcweb7` replay is a separate
observation and does not replace or erase this failure. Earlier claims that
the original inline root remained incomplete or that no current failure
remained are superseded by this correction, without editing that history.

The user authorized one additional bounded final-fix continuation: five fresh
unchanged Claude inline controls; only if the exact task-table alteration
recurs, five disposable-payload candidate samples for a narrow Stage 9
safe-return rule. Retention requires all five candidate rows to preserve the
table and otherwise pass the unchanged scorer and manual rubric, followed by
fresh complete campaigns and cross-cutting verification. The cost of this
extra wave is additional host invocations and qualification evidence beyond
the original single final-fix wave; it buys a measured test of this specific
instruction gap, not a new workflow or generic prohibition layer.

### Five unchanged controls: stop condition reached

The retained runner `/tmp/ff-pr7-table-rule-dl65TE/run.py` invokes the same
unchanged preparation, structured schema, exact Claude GREEN argv, 600-second
timeout handling, materialization and scorer as the campaign, selecting inline
drift and adding only an external experiment label. Commands were
`python3 /tmp/ff-pr7-table-rule-dl65TE/run.py control-N` for N = 1 through 5.
Each used a fresh independent fixture/context and the current installed
payload `f3f0947235ff3a23f9699cbc4ca4de1a998a2d4fd9519543507f82cbf13d06b6`.
Source HEAD was `e8e903218b12e1539e68d0427e8eb105de466dce` (production
checker bytes still `be9d319`); no live instruction had changed. The exact
frozen prompt, case registry, scorer and schema were not altered.

| Control | Root | Host/wrapper exit | Raw verdict | Exact task table | T/S/N/A/I/G/F | Duration |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `/tmp/ff-pr7-table-control-1-pakzxmnw` | 0 / 0 | pass | preserved | Y/Y/Y/Y/Y/Y/Y | 105915 ms |
| 2 | `/tmp/ff-pr7-table-control-2-f9f31snv` | 0 / 0 | pass | preserved | Y/Y/Y/Y/Y/Y/Y | 57484 ms |
| 3 | `/tmp/ff-pr7-table-control-3-5q_q2rdj` | 0 / 0 | pass | preserved | Y/Y/Y/Y/Y/Y/Y | 66599 ms |
| 4 | `/tmp/ff-pr7-table-control-4-ndsyb6o4` | 0 / 0 | pass | preserved | Y/Y/Y/Y/Y/Y/Y | 81609 ms |
| 5 | `/tmp/ff-pr7-table-control-5-6f_spl3v` | 0 / 0 | pass | preserved | Y/Y/Y/Y/Y/Y/Y | 82139 ms |

Every raw envelope reports successful structured completion, canonical model
`claude-sonnet-5`, no transport error and no unavailability. HEAD, protected
paths and payload were preserved in all five, with no unexpected status paths.
The full responses and ledger diffs were read manually: all five retain the
exact task table, set the authoritative head/Stage 9 state blocked, record the
plan path and identity evidence, and leave reconciliation as the sole next
action without exercising correction authority. Their auxiliary timestamp,
parent-event and transition-label claims retain the previously recorded
evidence limits. Controls 2–5 include denied preliminary tool calls in their
envelopes; those denials and the completed effects are preserved in raw
evidence, with no claims of broader host availability.

**Experiment disposition: NEEDS_CONTEXT.** None of the five controls reproduced
the specific implementation-task-table alteration. Under the authorized
experiment and writing-skills no-guidance-control rule, this stops before
candidate wording: no candidate was created, no instruction was changed and
no production commit or replacement full campaign was run. The five successful
controls do not refute or erase the completed `44s37v8y` failure. That observed
gap remains unresolved; this experiment provides no evidence for retaining the
proposed wording. Further remediation requires a new controller/user decision,
not another repetition added to this fixed sample.

## Task 8 deterministic task-table recovery verification

Production commit under test: `01f5dac` (`fix: validate Feature Forge task
statuses`). The retained Sonnet `44s37v8y` result remains the behavioral RED:
its W-2 status was `awaiting_return (return processing held for frozen-plan
drift, see Blockers)`. The five later unchanged controls remain separate
passing observations and do not erase that failure.

Deterministic RED was recorded before checker and instruction changes with
`python3 -m pytest feature-forge/tests/test_ff_check_audit.py::test_audit_rejects_annotated_task_status feature-forge/tests/test_ff_check_audit.py::test_audit_rejects_malformed_task_table feature-forge/tests/test_ledger_schema.py::test_implementation_progress_schema_is_synchronized feature-forge/tests/test_ledger_schema.py::test_stage9_checks_task_table_before_work_and_after_return feature-forge/tests/test_ledger_schema.py::test_stage9_blocks_return_or_redispatch_without_bound_snapshot feature-forge/tests/test_remediation_pressure.py::test_drift_score_accepts_notes_only_annotation -q`: 9 failed and 2 passed. The failed nodes were the annotated-status audit node; all five parametrizations of the malformed-table audit node; and the implementation-progress, Stage 9 entry/return-gate, and Stage 9 missing-snapshot schema nodes. Audit returned a false `FF-CHECK v1 gate=audit status=pass` for invalid table states; the schema diagnostics showed the absent five-column table and old Stage 9 contract.

The canonical pressure fixture changed only implementation-table shape and the
test-only controlled-cell extraction. Scenario prompts, scenario facts, and
expected decisions were unchanged. The final deterministic GREEN command was
`python3 -m pytest feature-forge/tests/test_ff_check_audit.py feature-forge/tests/test_ledger_schema.py feature-forge/tests/test_remediation_pressure.py feature-forge/tests/test_behavior_oracle.py -q`: 517 passed in 81.02s. It verifies the exact task-status fail-closed response (`FF-CHECK v1 gate=audit status=fail` with `task-status=unsupported`), notes-only commentary pass, unchanged controlled-cell mutation failures, malformed returned-table failures, and the exact returned-audit pass protocol.

No additional stochastic campaign was run. The retained `44s37v8y` observation
already demonstrated the behavioral gap, and the amended canonical-table
fixture/extraction is intentionally not a like-for-like continuation of that
campaign.

Complete verification against `01f5dac`:

- `python3 -m pytest feature-forge/tests -q`: 704 passed, 1 skipped in 108.03s.
- `cd review-loop && uv run pytest ../feature-forge/tests/integration/test_review_loop_boundary.py -q`: 24 passed in 16.48s.
- `cd review-loop && uv run pytest -q`: non-green and incomplete after emitting broader failures; its host session stopped producing output without a live test process and was interrupted. A fresh diagnostic `uv run pytest -q -x` reproduced the first failure: `tests/integration/test_controller_clean.py::CleanTracerTests::test_full_lifecycle_converges_and_is_merge_ready`, with Stage 0 returning `FAILED` instead of `PASSED` (1 failed, 44 passed in 3.79s). The public boundary remained green; this is not claimed as a substitute for the required full review-loop gate.
- `python3 -m pytest tests/test_install.py -q`: 11 passed in 0.31s.
- `python3 -m pytest tests/test_documentation.py -q`: 20 passed in 0.11s.
- `python3 -m pytest tests/test_plugin_agents.py -q`: 2 passed in 0.11s.
- `claude plugin validate . --strict`: passed.
- `python3 -m pytest tests -q`: 33 passed in 0.27s.
- `python3 -m py_compile feature-forge/scripts/ff-check feature-forge/tests/behavior/remediation_pressure.py`: passed.
- `git diff --check origin/main...HEAD`: passed before this evidence-only append.

The non-green required full review-loop suite is an outstanding qualification
gate. This record supplies evidence only and does not describe the remediation
as mergeable.

### Correction: authorized host verification of the Review Loop full suite

The preceding Review Loop full-suite entry described a restricted outer-sandbox
observation, not a product failure. Controller evidence identified its root
cause as Bubblewrap host denial: `bwrap: loopback: Failed to create
NETLINK_ROUTE socket: Operation not permitted`. The controller then reran the
same required command with authorized host access:

```text
cd review-loop && uv run pytest -q
```

It exited 0 with `510 passed, 1 skipped in 28.80s`. This supersedes the
restricted-run NEEDS_CONTEXT classification for the full Review Loop gate;
the earlier constrained observation remains retained as environment evidence.
Together with the public boundary result, the complete Task 8 verification
set against production commit `01f5dac` is passing. This correction adds
evidence only and does not alter the retained behavioral RED, scenarios,
prompts, or historical observations.
