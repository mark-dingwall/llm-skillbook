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
