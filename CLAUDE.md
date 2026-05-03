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
./multi_review.py --model claude=claude-opus-4-7 --model codex=gpt-5 file.py
```

No `make`, `lint`, or `test` targets exist. Manual smoke test only. Linting/typing is not wired up — don't assume a tool is available without checking.

## Architecture

### Data flow

1. `parse_args` → `detect_self` + `resolve_reviewers` filter the reviewer list (availability by `shutil.which`; host CLI included by default — `--skip-self` opt-in to drop it from auto-resolved set).
2. `build_prompt` assembles `INJECTION_PREAMBLE` + task template (or custom/`--prompt-file`) + context files + input files. Context files are always wrapped inline in `<file-NONCE path="…">…</file-NONCE>`. Input files are inline-wrapped under `--mode inline` (default) or emitted as a manifest of resolved absolute paths under `--mode reference` (model reads them via its own tools). Reference mode prepends a second injection preamble (`reference_preamble()`) warning that file *contents* read at tool-call time are review subjects, not instructions.
3. `run_all_reviewers` spawns one `asyncio.subprocess` per reviewer. Each child's stdout (JSONL event stream) is fed line-by-line into a per-CLI `ProgressAdapter`. A `rich.Live` dashboard (`build_table`) polls adapter state at ~6Hz.
4. `run_synthesis` (if ≥2 reviewers succeeded and `--synthesize` is on) pipes `build_synthesis_input(results)` through `--synthesizer` CLI for a Consensus Summary block.
5. `write_review_md` emits YAML frontmatter + one section per reviewer + Consensus Summary.

### Key abstractions

- **`CLI_SPEC` table** (multi_review.py:458): single source of truth for each CLI's invocation — `base` args, streaming flags, `--model` flag name, and optional `stdin_sentinel` (the `-` arg some CLIs need to read prompt from stdin). `build_command` composes argv from this; both `run_reviewer` (streaming) and `run_synthesis` (non-streaming) consume it.
- **Adding a new reviewer**: add to `ALL_REVIEWERS`, add a `CLI_SPEC` entry, write a `ProgressAdapter` subclass, register in `ADAPTER_FOR`. README *Not in v0.1* names `coderabbit`, `qwen`, `cursor` as open candidates.
- **`ProgressAdapter` subclasses** (one per CLI): parse that CLI's JSON event stream into a `Usage` dataclass + accumulated text. Each CLI has different telemetry fidelity — see README table. Keep the adapter defensive: upstream event schemas drift.
- **`ReviewerState` / `ReviewerResult`**: mutable state the dashboard watches vs. final result returned from `run_reviewer`.
- **Prompt shape (`--mode`)**: `inline` embeds every input file under `<file-NONCE>` tags; `reference` emits a `## Files to Review` manifest of absolute paths only. `build_prompt` skips reading input-file bytes entirely in reference mode. Context files are inline-wrapped in both modes. Argv (`build_command`, `CLI_SPEC`) is mode-independent — reference is purely a prompt-shape change. Reference mode is a Phase-1 falsification test for the larger sandbox + bypass-perms work tracked in `BACKLOG.md`; hybrid mode was dropped permanently.

### Invariants to preserve

- **Prompt goes on stdin, never argv.** Every CLI is invoked with the prompt written to `proc.stdin`. This keeps prompts out of `/proc/PID/cmdline` (see commit `55d783b`). Don't move prompt to argv.
- **Self-skip is opt-in** (`--skip-self`, default off). `detect_self()` reports the host via env vars: `CLAUDE_CODE_ENTRYPOINT` → `claude`, `GEMINI_CLI` → `gemini`, `CODEX_ENV` → `codex`, `OPENCODE` → `opencode`. `ANTIGRAVITY_AGENT=1` short-circuits detection to `"none"`. Rationale: a fresh subprocess of the host CLI has independent context — running it as a reviewer is valid and adds signal. `--skip-self` honoured only for the auto-resolved set; explicit `--reviewers` always wins. Don't reintroduce a default skip without discussion (see chat 2026-05-03).
- **Dual failure classification**: a reviewer fails if rc ≠ 0 OR captured output < `FAILURE_MIN_BYTES` (50). Don't weaken either check — both have caught real breakage. Partial failures still produce `REVIEW.md`; failed reviewers get their own section with stderr tail (last 2000 chars) and up to 1000 chars of any partial output.
- **Injection posture**: all file content is wrapped in `<file>` tags with a preamble telling the model to treat that content as review data. Synthesis input wraps each review in `<review reviewer="…">`. `html.escape(..., quote=True)` is used on attribute values. This is defense-in-depth, not a sandbox.
- **Context files always inline.** Both `--mode inline` and `--mode reference` wrap context files in `<file-NONCE>` tags — they're framing material the model needs *before* any tool call, so they cannot be deferred to the manifest. The reference-mode preamble (`reference_preamble`) stacks *after* the nonce-tag preamble (`injection_preamble`); both apply because context still uses tags even when input files don't.
- **Exit codes**: `0` ≥1 reviewer succeeded, `1` all failed or none available, `2` argparse error.
- **Output paths never overwrite.** `resolve_output_path` auto-suffixes (`-2`, `-3`, …) when the target exists, regardless of whether the path was explicit (`--output`), suggested by the synthesizer/haiku, or timestamp-fallback. Explicit `--output` collision prints a `note: ... exists; writing to X-2.md` warning. Don't reintroduce silent overwrite — paired `--mode inline` vs `--mode reference` runs to the same `--output` will clobber findings (see paralife 2026-05-03 sidecar). If a user explicitly *wants* overwrite, that's a future `--force` flag, not the default.
- **Capacity-aware fallback (gemini)**: every gemini run walks `CLI_SPEC["gemini"]["fallback_chain"]` (3-deep, defined in `GEMINI_FALLBACK_CHAIN`) on capacity-class stderr matches (`CAPACITY_PATTERNS["gemini"]`) and stops at the first success. `--no-fallback` disables it. `--model gemini=X` *pins* to X (no fallback) — use `--fallback-model gemini=A,B,C` for an explicit chain. Real failures (auth/network/prompt) don't burn the chain. Mid-stream 429 with usable partial output (≥`FAILURE_MIN_BYTES`) is kept, no retry. Synthesis pass uses the same chain. Frontmatter surfaces `fallbacks:` only when ≥2 hops walked. Other CLIs have empty `fallback_chain` — no fallback today.
- **Timeout default is `None` (no timeout).** `--timeout` unset → `_run_reviewer_attempt` / `_run_synthesis_attempt` / `suggest_filename_haiku` skip the `wait_for` wrapper and await the underlying coroutine directly. Frontier models on big prompts routinely exceed any sensible default; users opt in to a kill-on-exceed deadline with `--timeout N`. Don't reintroduce a wall-clock default. Known issue: when `--timeout N` *is* set, observed slop on Node/Bun-wrapped CLIs (codex/gemini/opencode) ranges +3–9s past the deadline due to `kill_proc` post-SIGKILL teardown — tracked in BACKLOG goal 3.

### Synthesis caveat (documented in README)

When `--synthesizer` is also a reviewer, that model is double-weighted. The synthesizer call uses the CLI name directly regardless of the reviewer list, so it works whether or not the host was dropped via `--skip-self`. Don't "fix" double-weighting by auto-excluding the synthesizer from reviewers without discussion — the README explicitly calls this out as user choice.

## Dependency tracking

Gemini emitted cumulative (non-delta) assistant messages in some versions. `GeminiAdapter.feed_line` keys off `ev.get("delta")` — if a future gemini release drops that flag, it will double-count text. Comment at multi_review.py:351 flags this. Same caution applies to any adapter when upstream schemas change.

## Comparison-test methodology

Every run writes a metadata row to `runs/runs.jsonl` by default (opt out with `--no-harvest`). `multi_review.py --report` reads that JSONL and regenerates `EXPERIMENTS.md` — the inline-vs-reference comparison log + ordering rule + per-project narrative. Schema is flat JSONL keyed by `HARVEST_SCHEMA_VERSION`; bump that on field rename/removal (additions are safe). Per-project narrative depth lives in `runs/notes/<project>-<YYYY-MM-DD>.md` sidecars stitched in at report time. `EXPERIMENTS.md` is fully generated — never edit it by hand; edits are overwritten on next `--report`.

**Run-to-run variance is large.** Paired runs of the same prompt on the same codebase produce materially different findings, severities, and per-reviewer behaviour from one day to the next — same model, same `--mode`, different bugs surfaced. Two paired runs on Guestflow-16.1 (2026-04-29 vs 2026-04-30) both showed reference-mode beating inline, but for **different reasons each time** (cleaner synthesis vs +2 unique codex bugs); reviewer-level quirks shifted too (gemini fallback chain burned through on one run, ran clean on the next; opencode hallucinated a fix as present in one reference run but not another). **Do not draw conclusions from single runs.** Treat each row in `EXPERIMENTS.md` as one sample, not a trend. We need ≥5 paired runs across distinct codebases before any "mode X is better for reviewer Y" claim is load-bearing. When narrating sidecars, emphasise what the run *showed this time* over what it "proves".
