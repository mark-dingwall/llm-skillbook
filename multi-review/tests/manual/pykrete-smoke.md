# pykrete reviewer manual smoke

**Status:** updated for v0.3 on 2026-08-11. This procedure makes paid network
calls; re-run it to refresh the live evidence.

pykrete is the closest analog to `agy`: a plain-text, agentic, subprocess
reviewer (see `tests/manual/agy-smoke.md`). Unlike agy it needs external
config (`NANOGPT_API_KEY` + a `pykrete.toml`) before it will do anything but
fail clean, and it has its own success-vs-downgrade exit-code contract, so
this procedure has more setup and more branches than agy's.

## Facts this procedure relies on (verified against source, 2026-07-19)

From `multi_review/core/reviewers.py` `CLI_SPEC["pykrete"]`:
- `base = ["pykrete"]`, `stdin_sentinel = "-"` — prompt goes on stdin like codex/opencode.
- `model_flag = "--family"` — `models: {pykrete: <family>}` in a prompt YAML selects a NanoGPT **family**, not a specific model.
- `success_exit_codes = (0, 3)` — exit `3` is "success via downgrade" (pykrete's `pi`-backed failover fell through to a non-lead model in the family and still produced a review). Per the implementation plan (`docs/superpowers/plans/2026-07-11-multi-review-pykrete-reviewer.md`), the full exit-code contract is `0=success, 3=downgrade-success, 1=error, 2=config, 4=all-unavailable`.
- `config_env = "PYKRETE_CONFIG"` — `build_command` raises `ValueError` if this env var is unset, which `run_reviewer`/`run_synthesis` catch and turn into a recorded failure (never an escaped exception — see CLAUDE.md "Invariants to preserve").
- `records_family_not_model = True` — `model_used` is recorded as `f"family:{model}"` (or `None`), never a bare model id, because pykrete resolves the actual model inside the family itself.
- `PykreteAdapter` (`multi_review/core/adapters.py`) buffers stdout verbatim — no step-narration trim like agy's adapter.
- `DEFAULT_REVIEWERS = ["claude", "agy", "codex", "opencode", "pykrete"]` — pykrete is **default-on**, same posture as agy. Until configured it will surface as a failed section in every run, not just ones that explicitly ask for it. `ALL_REVIEWERS` now also contains opt-in `grok`, which is nameable but never auto-selected — its presence in the known/valid set does not make it default-on.
- A successful exit 3 sets `downgraded: true`, which `spawn` preserves in the
  raw state JSON to distinguish a fallback review from an ordinary success.
- The `## Summary` heading failure classifier (SKILL.md Step 7) applies to
  pykrete's output exactly like every other reviewer: `<REVIEWS_DIR>/pykrete.md`
  must contain a Summary or Executive Summary heading. Narration may precede it;
  a missing heading is rendered as an effective failure without rewriting the
  raw state JSON.

## How pykrete picks a model (verified against its source, 2026-08-04)

`--family` selects a candidate chain from `[families]`. The chain's lead is
`[defaults.<task>].<family>`, then `[defaults.general].<family>`, then the
family list in order (`resolve.ts:buildCandidates`).

**multi-review threads the prompt's `task` through as `--task`** (since
2026-08-04), so a `task: code` prompt runs the `[defaults.code]` lead. Absent
the flag pykrete falls back to `task = "general"` (`args.ts:28`). `generic` is
aliased to pykrete's `general`; every other task name goes verbatim, and an
unknown task warns on **stderr** only (`cli.ts:52`) and falls back to
`general` — stdout, and therefore the review body, is unaffected.

pykrete has no `--help`: any unrecognised argv is treated as the prompt, so
`pykrete --help` spends an API call answering a question about the flag.

## Prerequisites

```bash
npm link pykrete        # so `shutil.which pykrete` resolves
pykrete --version        # sanity check it's on PATH
export NANOGPT_API_KEY=...
```

Write a `pykrete.toml` naming at least one family with a multi-model failover
list (needed later to force a downgrade). Every id in a `[defaults.*]` table
must also appear in that family's `[families]` list, or config validation
fails:

```toml
default_family = "deepseek"

[families]
deepseek = ["deepseek/deepseek-v4-pro-cheaper:thinking", "deepseek/deepseek-v4-pro-cheaper"]

[defaults.general]
deepseek = "deepseek/deepseek-v4-pro-cheaper"

[defaults.code]
deepseek = "deepseek/deepseek-v4-pro-cheaper:thinking"
```

```bash
export PYKRETE_CONFIG=/path/to/pykrete.toml
```

`PYKRETE_CONFIG` is read by multi-review, not by pykrete — `build_command`
turns it into `--config <path>`. Invoking `pykrete` by hand needs the flag.

## Procedure

### A — reviewer-probe lists pykrete available

In a Claude Code session with the multi-review skill installed:

```
/multi-review --list-reviewers
```

Confirm the printed table includes a `pykrete` row marked available, with
`shutil.which pykrete` resolving and `pykrete --version` output shown (SKILL.md
Step 1: probes `claude, agy, codex, opencode, pykrete, grok` via `shutil.which` +
`<cli> --version`).

### B — single-pass review, explicit `reviewers: [pykrete]`

Build a prompt YAML (or use `/multi-review-build`) reviewing one small file,
e.g. `multi_review/core/paths.py`, with:

```yaml
prompt_format_version: 2
task: code
files:
  - multi_review/core/paths.py
synthesizer: none
reviewers:
  - pykrete
models:
  pykrete: glm
```

Run it:

```
/multi-review --prompt-files <yaml>
```

Confirm:
- The named single-pass report path printed by the skill (normally
  `<cwd>/REVIEW-<slug>.md`) has a **Pykrete** section.
- That section contains a `## Summary` heading (or the reviewer is rendered as
  a failure even though `<REVIEWS_DIR>/pykrete.state.json` keeps raw `ok: true`).
- The raw pykrete state records `final_model: "family:glm"`, never a fabricated
  concrete model id.

### C — forced downgrade (exit 3)

Edit the family list so the lead model is bad, e.g.:

```toml
[families]
glm = ["glm-9-nonexistent-lead", "glm-4.6"]
```

Re-run the same prompt YAML from B. Confirm:
- The review still lands — the named single-pass report has a **Pykrete** section with a
  `## Summary` heading, same as B (success-via-downgrade is still success).
- `<REVIEWS_DIR>/pykrete.state.json` shows `ok: true`, `downgraded: true`.
- `final_model` is still `"family:glm"` — never a specific model id (pykrete
  resolves the actual model internally; multi-review only ever records the
  family it asked for).

Restore the good family list afterward.

### D — `PYKRETE_CONFIG` unset → recorded failure, not a crash

```bash
unset PYKRETE_CONFIG
```

Re-run the same prompt YAML from B (or any run with pykrete in `reviewers`).
Confirm:
- The overall run still completes — other reviewers (if any) succeed
  normally; the fanout does not abort.
- The named single-pass report has a **Pykrete** section reporting failure, with the config
  error text surfaced (should read something like `pykrete requires
  $PYKRETE_CONFIG to point at a pykrete.toml`).
- `<REVIEWS_DIR>/pykrete.state.json` shows `ok: false` and `error` containing
  `PYKRETE_CONFIG`.
- No traceback anywhere in the session transcript or stderr — the
  `ValueError` from `build_command` is caught inside the runner, not raised
  through `asyncio.gather`.

Restore `PYKRETE_CONFIG` afterward.

## Scenario E — `--task` selects the `[defaults.<task>]` lead

Falsification test: a clean run reports *nothing* about which task table was
used, so make the `[defaults.code]` lead unreachable and watch the substitution
warning name it.

Work against a **copy** of the config, never the original:

```bash
cp ~/kramtime/pykrete/pykrete.toml "$TMP/pykrete-taskE.toml"
```

In the copy, point the `[defaults.code]` entry at a nonexistent id and add that
id to the family list (config validation requires every `[defaults.*]` id to
appear in its `[families]` list):

```toml
[families]
deepseek = ["deepseek/deepseek-v9-nonexistent-code-lead",
            "deepseek/deepseek-v4-pro-cheaper:thinking",
            "deepseek/deepseek-v4-pro-cheaper"]

[defaults.code]
deepseek = "deepseek/deepseek-v9-nonexistent-code-lead"
```

Run the B prompt (`task: code`, `models: {pykrete: deepseek}`,
`synthesizer: none`) via `spawn --task code`, with `PYKRETE_CONFIG` pointed at
the copy.

- **Expected:** stderr carries `pykrete: substituted "..." for intended lead
  "deepseek/deepseek-v9-nonexistent-code-lead"` — that line names the *code*
  lead, which is the proof `--task code` was honoured. State shows `ok: true`,
  `downgraded: true`.
- **Control:** the same run *without* `--task` must substitute the
  `[defaults.general]` lead instead (or not downgrade at all).

Delete the copy afterwards.

## Pass criteria

- [ ] A: `--list-reviewers` shows pykrete available.
- [ ] B: named single-pass report has a Pykrete `## Summary` section and raw
      state records `final_model: "family:<family>"`.
- [ ] C: downgrade still produces a landed review and raw state records
      `downgraded: true`.
- [ ] D: missing config is a recorded failed-reviewer section, not a run
      crash; no traceback.
- [ ] E: `--task code` reaches pykrete and selects the `[defaults.code]` lead.

## Failure modes to watch for

- Config `ValueError` escaping `run_reviewer`/`run_synthesis` and aborting
  the whole fanout (would violate the CLAUDE.md invariant covered by Task 3
  of the implementation plan — should not happen, but this is the first live
  chance to see it against the real binary instead of the fixture shim at
  `tests/fixtures/bin/pykrete`).
- `## Summary` heading missing from real pykrete output (e.g. if `pi`'s
  agentic narration wraps or precedes the summary) — would demote a genuinely
  successful review to a failure section. If seen, compare against how
  `AgyAdapter` trims its own narration preamble and consider whether
  `PykreteAdapter` needs the same.
- Real NanoGPT family/model names differing from the illustrative `glm`
  values above — substitute whatever `pykrete.toml` actually declares.
- `pykrete.toml` schema differing from the `default_family` /
  `[families]` / `[defaults.code]` shape assumed here — this file's TOML
  example was not checked against pykrete's own source; fix it up once the
  real schema is confirmed.
