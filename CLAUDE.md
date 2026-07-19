# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Single-file Python tool (`multi_review.py`) that fans out one review prompt to multiple AI CLIs in parallel (`claude`, `gemini`, `codex`, `opencode`), aggregates responses into `REVIEW.md`, and optionally runs a consensus-synthesis pass.

No packaging. No test suite. Runs via `uv` using a PEP 723 inline script header (`#!/usr/bin/env -S uv run --script`); `rich>=13.7` is declared inline and resolved on first run.

## Commands

```bash
# Run directly (uv resolves deps)
./multi_review.py [files...]

# Show detected CLIs + self-detection (no network calls)
./multi_review.py --list-reviewers

# Assemble prompt + print, no reviewers invoked
./multi_review.py --dry-run --task code src/*.py

# Force explicit reviewer set (bypasses --skip-self and availability filter)
./multi_review.py --reviewers gemini,codex file.py

# Per-reviewer model override
./multi_review.py --model claude=claude-opus-4-7 --model codex=gpt-5.6-sol file.py
```

No `make`, `lint`, or `test` targets exist. Manual smoke test only. Linting/typing is not wired up — don't assume a tool is available without checking.

## Testing discipline

When fixing a bug or shipping a behavioural change in an untested area, write the test as part of the fix. The v0.2 work landed a pytest suite under `tests/{unit,integration}/` — `uv run pytest tests/ -q` is the baseline; every bugfix is an opportunity to backfill the test that would have caught it. Do not ship a fix to a regressed path without leaving an executable check behind. Applies to: adapter JSONL parsing, harvest schema, prompt assembly, snapshot/drift detection, aggregation, sidecar grouping, report rendering. Skill-level interactive flows that genuinely can't be automated → document a manual smoke step under `tests/manual/*.md` instead.

## v0.2 manual-smoke note

v0.2 introduces skill-level interactive flows that bypass the test suite. When you hit a bug in
SKILL.md procedure (a step doesn't fan out right, a Task subagent loses context, an
AskUserQuestion sequence misbehaves), add or update the corresponding `tests/manual/*.md`
procedure as part of the fix — and where the bug surface is automatable (parsing,
sidecar classification, harvest fields), backfill a pytest test under
`tests/{unit,integration}/`. Skill bugs are exactly the category that "manual only" excuses
get used to skip — don't.

## Architecture

### Data flow

1. `parse_args` → `detect_self` + `resolve_reviewers` filter the reviewer list (availability by `shutil.which`; host CLI included by default — `--skip-self` opt-in to drop it from auto-resolved set).
2. `build_prompt` assembles `INJECTION_PREAMBLE` + task template (or custom/`--prompt-file`) + context files + input files. Context files are always wrapped inline in `<file-NONCE path="…">…</file-NONCE>`. Input files are inline-wrapped under `--mode inline` (default) or emitted as a manifest of resolved absolute paths under `--mode reference` (model reads them via its own tools). Reference mode prepends a second injection preamble (`reference_preamble()`) warning that file *contents* read at tool-call time are review subjects, not instructions.
3. `run_all_reviewers` spawns one `asyncio.subprocess` per reviewer. Each child's stdout is fed line-by-line into a per-CLI `ProgressAdapter`. `claude`/`codex`/`opencode` parse a JSONL event stream; `agy`/`pykrete` are plain-text (no structured events — the whole stdout is the review body). A `rich.Live` dashboard (`build_table`) polls adapter state at ~6Hz.
4. `run_synthesis` (if ≥2 reviewers succeeded and `--synthesize` is on) pipes `build_synthesis_input(results)` through `--synthesizer` CLI for a Consensus Summary block.
5. `write_review_md` emits YAML frontmatter + one section per reviewer + Consensus Summary.

### Key abstractions

- **`CLI_SPEC` table** (multi_review.py:458): single source of truth for each CLI's invocation — `base` args, streaming flags, `--model` flag name, and optional `stdin_sentinel` (the `-` arg some CLIs need to read prompt from stdin). `build_command` composes argv from this; both `run_reviewer` (streaming) and `run_synthesis` (non-streaming) consume it.
- **Adding a new reviewer**: add to `ALL_REVIEWERS`, add a `CLI_SPEC` entry, write a `ProgressAdapter` subclass, register in `ADAPTER_FOR`. README *Not in v0.1* names `coderabbit`, `qwen`, `cursor` as open candidates.
- **`ProgressAdapter` subclasses** (one per CLI): parse that CLI's JSON event stream into a `Usage` dataclass + accumulated text. Each CLI has different telemetry fidelity — see README table. Keep the adapter defensive: upstream event schemas drift.
- **`ReviewerState` / `ReviewerResult`**: mutable state the dashboard watches vs. final result returned from `run_reviewer`.
- **Prompt shape (`--mode`)**: `inline` embeds every input file under `<file-NONCE>` tags; `reference` emits a `## Files to Review` manifest of absolute paths only. `build_prompt` skips reading input-file bytes entirely in reference mode. Context files are inline-wrapped in both modes. Argv (`build_command`, `CLI_SPEC`) is mode-independent — reference is purely a prompt-shape change. Reference mode is a Phase-1 falsification test for the larger sandbox + bypass-perms work tracked in `BACKLOG.md`; hybrid mode was dropped permanently.

### Invariants to preserve

- **Prompt goes on stdin, never argv — except agy, which reads a file path.** Every stdin-capable CLI is invoked with the prompt written to `proc.stdin`, keeping prompts out of `/proc/PID/cmdline` (see commit `55d783b`). Don't move those prompts to argv. **agy is the documented exception:** it has no stdin input mode (`--print` requires the prompt as its argv value) and inline prompts embed file contents that would exceed `MAX_ARG_STRLEN` (128 KiB → `E2BIG`) on argv. So agy uses `"prompt_delivery": "argv_file"` in `CLI_SPEC`: the prompt is written to a file and agy is handed a tiny instruction naming that path (`AGY_FILE_INSTRUCTION`). Only the *path* — never the prompt contents — reaches the process table, so the invariant's intent holds. `build_command(..., prompt_path=…)` requires the path for argv_file CLIs; the instruction must sit immediately after `--print` (which consumes the next arg as its value) so it isn't swallowed by `--model`. Verified against agy 1.0.16/1.1.1 (2026-07-10 smoke).
- **Self-skip is opt-in** (`--skip-self`, default off). `detect_self()` reports the host via env vars: `CLAUDE_CODE_ENTRYPOINT` → `claude`, `CODEX_ENV` → `codex`, `OPENCODE` → `opencode`. `ANTIGRAVITY_AGENT=1` short-circuits detection to `"none"` (set by `agy` on child processes; gemini CLI deprecated, replaced by `agy`). Rationale: a fresh subprocess of the host CLI has independent context — running it as a reviewer is valid and adds signal. `--skip-self` honoured only for the auto-resolved set; explicit `--reviewers` always wins. Don't reintroduce a default skip without discussion (see chat 2026-05-03).
- **Dual failure classification**: a reviewer fails if rc ≠ 0 OR captured output < `FAILURE_MIN_BYTES` (50). Don't weaken either check — both have caught real breakage. Partial failures still produce `REVIEW.md`; failed reviewers get their own section with stderr tail (last 2000 chars) and up to 1000 chars of any partial output.
- **Injection posture**: all file content is wrapped in `<file>` tags with a preamble telling the model to treat that content as review data. Synthesis input wraps each review in `<review reviewer="…">`. `html.escape(..., quote=True)` is used on attribute values. This is defense-in-depth, not a sandbox.
- **agy is an agentic, uncontained reviewer.** Unlike the `claude` reviewer agent (restricted to `Read/Grep/Glob`, no Bash — spec §5.2), `agy --print` runs as an autonomous agent: to read its prompt file it uses tools, and observed runs also ran `pytest` and grepped the repo unprompted, auto-proceeding without `--dangerously-skip-permissions`. This makes agy's reviews richer but means agy can execute commands on the working tree during a review — an injection in adversarial review material could weaponise that. Acceptable for reviewing your own code; **do not point agy at untrusted code** until the bwrap/`--sandbox` containment in BACKLOG lands. `AgyAdapter.get_response_text` trims agy's step-narration preamble down to the first `## Summary` heading so it doesn't pollute REVIEW.md.
- **pykrete is a default-on reviewer** — it's in `ALL_REVIEWERS` alongside agy, not an opt-in addition. Running an uncontained, agentic reviewer (see below) by default is an accepted trade-off, same posture as agy.
- **Per-CLI `success_exit_codes`.** `CLI_SPEC[cli].get("success_exit_codes", (0,))` — most CLIs succeed only on exit 0; pykrete's is `(0, 3)` (3 == success via NanoGPT model downgrade). This widens which exit codes count as success but does NOT weaken the byte floor: `reviewer_ok` still requires `len(text) >= FAILURE_MIN_BYTES` regardless of which success code fired.
- **Config errors become recorded failures, never escape the fanout.** A missing `$PYKRETE_CONFIG` raises `ValueError` inside `build_command`; `run_reviewer` catches it and returns a failed `ReviewerResult` rather than letting the exception propagate. Critical because pykrete runs by default — an unconfigured pykrete must not crash the whole run, just its own section.
- **Downgrade (exit 3) ⇒ comparison-ineligible, and no bogus `final_model`.** `ReviewerResult.downgraded` is `True` whenever a run is `ok` with `rc != 0`; harvest rows set `comparison_eligible = not drift_blocks_eligibility and not downgraded`, so a downgraded pykrete run never counts toward the inline-vs-reference comparison stats. Because pykrete only reports a *family*, not the model NanoGPT actually routed to, `final_model` is recorded as `family:<name>` (`records_family_not_model` in `CLI_SPEC`) instead of fabricating a specific downgraded-model name.
- **pykrete is agentic/uncontained** (wraps the `pi` agent) — same posture as agy above: **do not point pykrete at untrusted code** until the bwrap/`--sandbox` containment in BACKLOG lands.
- **`--family`, not `--model`.** pykrete's `model_flag` is `--family`; `models: {pykrete: <family>}` in the YAML prompt schema names a NanoGPT family (e.g. `glm`), not a specific pinned model — pykrete resolves the actual model within that family itself.
- **Context files always inline.** Both `--mode inline` and `--mode reference` wrap context files in `<file-NONCE>` tags — they're framing material the model needs *before* any tool call, so they cannot be deferred to the manifest. The reference-mode preamble (`reference_preamble`) stacks *after* the nonce-tag preamble (`injection_preamble`); both apply because context still uses tags even when input files don't.
- **Exit codes**: `0` ≥1 reviewer succeeded, `1` all failed or none available, `2` argparse error.
- **Output paths never overwrite.** `resolve_output_path` auto-suffixes (`-2`, `-3`, …) when the target exists, regardless of whether the path was explicit (`--output`), suggested by the synthesizer/haiku, or timestamp-fallback. Explicit `--output` collision prints a `note: ... exists; writing to X-2.md` warning. Don't reintroduce silent overwrite — paired `--mode inline` vs `--mode reference` runs to the same `--output` will clobber findings (see paralife 2026-05-03 sidecar). If a user explicitly *wants* overwrite, that's a future `--force` flag, not the default.
- **Single-attempt reviewer runs.** 429 → fail clean. Quota-proximity probe deferred to v0.2.1 (see BACKLOG).
- **Timeout default is `None` (no timeout).** `--timeout` unset → `_run_reviewer_attempt` / `_run_synthesis_attempt` / `suggest_filename_haiku` skip the `wait_for` wrapper and await the underlying coroutine directly. Frontier models on big prompts routinely exceed any sensible default; users opt in to a kill-on-exceed deadline with `--timeout N`. Don't reintroduce a wall-clock default. Known issue: when `--timeout N` *is* set, observed slop on Node/Bun-wrapped CLIs (codex/gemini/opencode) ranges +3–9s past the deadline due to `kill_proc` post-SIGKILL teardown — tracked in BACKLOG goal 3.

### Synthesis caveat (documented in README)

When `--synthesizer` is also a reviewer, that model is double-weighted. The synthesizer call uses the CLI name directly regardless of the reviewer list, so it works whether or not the host was dropped via `--skip-self`. Don't "fix" double-weighting by auto-excluding the synthesizer from reviewers without discussion — the README explicitly calls this out as user choice.

## Dependency tracking

Gemini emitted cumulative (non-delta) assistant messages in some versions. `GeminiAdapter.feed_line` keys off `ev.get("delta")` — if a future gemini release drops that flag, it will double-count text. Comment at multi_review.py:351 flags this. Same caution applies to any adapter when upstream schemas change.

## Comparison-test methodology

Every run writes a metadata row to `runs/runs.jsonl` by default (opt out with `--no-harvest`). `multi_review.py --report` reads that JSONL and regenerates `EXPERIMENTS.md` — the inline-vs-reference comparison log + ordering rule + per-project narrative. Schema is flat JSONL keyed by `HARVEST_SCHEMA_VERSION`; bump that on field rename/removal (additions are safe). Per-project narrative depth lives in `runs/notes/<project>-<YYYY-MM-DD>.md` sidecars stitched in at report time. `EXPERIMENTS.md` is fully generated — never edit it by hand; edits are overwritten on next `--report`. The `project` key is derived via `--project-tag` (explicit override) → `git remote get-url origin` basename → `cwd.name` fallback (`derive_project`); paired runs from a worktree like `Guestflow-16.1/` and the main `Guestflow/` checkout share one bucket via origin, but pre-change rows keyed off `cwd.name` may differ — pass `--project-tag` when finer phase partitioning is wanted.

**Run-to-run variance is large.** Paired runs of the same prompt on the same codebase produce materially different findings, severities, and per-reviewer behaviour from one day to the next — same model, same `--mode`, different bugs surfaced. Two paired runs on Guestflow-16.1 (2026-04-29 vs 2026-04-30) both showed reference-mode beating inline, but for **different reasons each time** (cleaner synthesis vs +2 unique codex bugs); reviewer-level quirks shifted too (gemini fallback chain burned through on one run, ran clean on the next; opencode hallucinated a fix as present in one reference run but not another). **Do not draw conclusions from single runs.** Treat each row in `EXPERIMENTS.md` as one sample, not a trend. We need ≥5 paired runs across distinct codebases before any "mode X is better for reviewer Y" claim is load-bearing. When narrating sidecars, emphasise what the run *showed this time* over what it "proves".
