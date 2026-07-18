# pykrete reviewer manual smoke

**Status:** procedure authored 2026-07-19; not yet executed live — run it after
configuring NanoGPT creds. This environment has no `NANOGPT_API_KEY` and
pykrete is not `npm link`ed here, so nothing below has been exercised end to
end. Do not treat any pass/fail claim in this file as evidence until the
"Results" section at the bottom is filled in from a real run.

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
- `TELEMETRY_QUALITY["pykrete"] = "degraded"` (`multi_review/core/harvest.py`) — plain-text stdout, no token telemetry, `Usage` stays all-zero. Expected, not a bug.
- `PykreteAdapter` (`multi_review/core/adapters.py`) buffers stdout verbatim — no step-narration trim like agy's adapter.
- `ALL_REVIEWERS = ["claude", "agy", "codex", "opencode", "pykrete"]` — pykrete is **default-on**, same posture as agy. Until configured it will surface as a failed section in every run, not just ones that explicitly ask for it.
- `build_row` in `multi_review/core/harvest.py`: `comparison_eligible = not drift_blocks_eligibility and not r.downgraded`. This is set **per reviewer** inside `usage_by_reviewer.pykrete`, not as a row-level flag — a downgraded pykrete run does not mark other reviewers in the same row ineligible.
- The `## Summary` heading failure classifier (SKILL.md Step 7) applies to pykrete's output exactly like every other reviewer: `<REVIEWS_DIR>/pykrete.md` must start with a heading matching `^#{1,3}\s+(summary|executive summary)\b` or the reviewer gets demoted to `ok: false` regardless of exit code.

The `pykrete.toml` shape below (`default_family` / `[families]` / `[defaults.code]`)
is per the task brief's field names — it is **not** verified against pykrete's
own source (an external npm package, not vendored in this repo). Check
`pykrete --help` or pykrete's own docs before writing the real file; adjust
the example if the actual schema differs.

## Prerequisites

```bash
npm link pykrete        # so `shutil.which pykrete` resolves
pykrete --version        # sanity check it's on PATH
export NANOGPT_API_KEY=...
```

Write a `pykrete.toml` naming at least one family with a multi-model failover
list (needed later to force a downgrade), and a task default:

```toml
default_family = "glm"

[families]
glm = ["glm-4.6", "glm-4-plus"]

[defaults.code]
family = "glm"
```

```bash
export PYKRETE_CONFIG=/path/to/pykrete.toml
```

## Procedure

### A — reviewer-probe lists pykrete available

In a Claude Code session with the multi-review skill installed:

```
/multi-review --list-reviewers
```

Confirm the printed table includes a `pykrete` row marked available, with
`shutil.which pykrete` resolving and `pykrete --version` output shown (SKILL.md
Step 1: probes `claude, agy, codex, opencode, pykrete` via `shutil.which` +
`<cli> --version`).

### B — single-pass review, explicit `reviewers: [pykrete]`

Build a prompt YAML (or use `/multi-review-build`) reviewing one small file,
e.g. `multi_review/core/paths.py`, with:

```yaml
prompt_format_version: 1
task: code
files:
  - multi_review/core/paths.py
mode: reference
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
- `REVIEW.md` (cwd root) has a **Pykrete** section.
- That section starts with a `## Summary` heading (or the reviewer will have
  been demoted to a failure — check `<REVIEWS_DIR>/pykrete.state.json`
  `ok: true` if the heading looks present but the section still reads as
  failed).
- Harvest row (once flushed) has `usage_by_reviewer.pykrete.final_model` in
  the shape `"family:glm"`, `telemetry_quality: "degraded"`, and
  `comparison_eligible: true` (this run is a clean success, not a downgrade).

### C — forced downgrade (exit 3)

Edit the family list so the lead model is bad, e.g.:

```toml
[families]
glm = ["glm-9-nonexistent-lead", "glm-4.6"]
```

Re-run the same prompt YAML from B. Confirm:
- The review still lands — `REVIEW.md` has a **Pykrete** section with a
  `## Summary` heading, same as B (success-via-downgrade is still success).
- `<REVIEWS_DIR>/pykrete.state.json` shows `ok: true`, `downgraded: true`.
- The harvest row's `usage_by_reviewer.pykrete.comparison_eligible` is
  **`false`** (per `build_row`'s `not r.downgraded` term) — the rest of the
  row (other reviewers, if any) is unaffected.
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
- `REVIEW.md` has a **Pykrete** section reporting failure, with the config
  error text surfaced (should read something like `pykrete requires
  $PYKRETE_CONFIG to point at a pykrete.toml`).
- `<REVIEWS_DIR>/pykrete.state.json` shows `ok: false` and `error` containing
  `PYKRETE_CONFIG`.
- No traceback anywhere in the session transcript or stderr — the
  `ValueError` from `build_command` is caught inside the runner, not raised
  through `asyncio.gather`.

Restore `PYKRETE_CONFIG` afterward.

## Pass criteria

- [ ] A: `--list-reviewers` shows pykrete available.
- [ ] B: `REVIEW.md` has a Pykrete `## Summary` section; harvest row
      `comparison_eligible: true`, `final_model: "family:glm"`.
- [ ] C: downgrade still produces a landed review; harvest row
      `comparison_eligible: false` for pykrete only.
- [ ] D: missing config is a recorded failed-reviewer section, not a run
      crash; no traceback.

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

## Results

Not yet run. Fill in per scenario (A/B/C/D) once executed against a real
`NANOGPT_API_KEY` + linked `pykrete`: date, pass/fail, and any bug found —
including whether it needs a fix + backfilled pytest test per CLAUDE.md's
testing-discipline note, or is genuinely un-automatable and stays here.
