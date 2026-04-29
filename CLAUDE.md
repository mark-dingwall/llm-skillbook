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

# Force explicit reviewer set (bypasses self-skip / availability filter)
./multi_review.py --reviewers gemini,codex file.py

# Per-reviewer model override
./multi_review.py --model claude=claude-opus-4-7 --model codex=gpt-5 file.py
```

No `make`, `lint`, or `test` targets exist. Manual smoke test only. Linting/typing is not wired up — don't assume a tool is available without checking.

## Architecture

### Data flow

1. `parse_args` → `detect_self` + `resolve_reviewers` filter the reviewer list (self-skip by env var, availability by `shutil.which`).
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
- **Self-skip via env vars** (`detect_self`): `CLAUDE_CODE_ENTRYPOINT` → skip `claude`, `GEMINI_CLI` → skip `gemini`, `CODEX_ENV` → skip `codex`, `OPENCODE` → skip `opencode`. `ANTIGRAVITY_AGENT=1` short-circuits to "none". Override with `--reviewers`.
- **Dual failure classification**: a reviewer fails if rc ≠ 0 OR captured output < `FAILURE_MIN_BYTES` (50). Don't weaken either check — both have caught real breakage. Partial failures still produce `REVIEW.md`; failed reviewers get their own section with stderr tail (last 2000 chars) and up to 1000 chars of any partial output.
- **Injection posture**: all file content is wrapped in `<file>` tags with a preamble telling the model to treat that content as review data. Synthesis input wraps each review in `<review reviewer="…">`. `html.escape(..., quote=True)` is used on attribute values. This is defense-in-depth, not a sandbox.
- **Context files always inline.** Both `--mode inline` and `--mode reference` wrap context files in `<file-NONCE>` tags — they're framing material the model needs *before* any tool call, so they cannot be deferred to the manifest. The reference-mode preamble (`reference_preamble`) stacks *after* the nonce-tag preamble (`injection_preamble`); both apply because context still uses tags even when input files don't.
- **Exit codes**: `0` ≥1 reviewer succeeded, `1` all failed or none available, `2` argparse error.

### Synthesis caveat (documented in README)

When `--synthesizer` is also a reviewer, that model is double-weighted. `async_main` handles the "synthesizer was self-skipped as reviewer" case implicitly because the synthesizer call uses the CLI name directly regardless of the reviewer list. Don't "fix" this by auto-excluding the synthesizer from reviewers without discussion — the README explicitly calls this out as user choice.

## Dependency tracking

Gemini emitted cumulative (non-delta) assistant messages in some versions. `GeminiAdapter.feed_line` keys off `ev.get("delta")` — if a future gemini release drops that flag, it will double-count text. Comment at multi_review.py:351 flags this. Same caution applies to any adapter when upstream schemas change.
