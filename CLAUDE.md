# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project shape

Single-file Python tool (`multi_review.py`, ~950 LOC). PEP 723 inline metadata declares `python>=3.11` and `rich>=13.7`; the shebang `#!/usr/bin/env -S uv run --script` lets `uv` resolve deps on first run. No package, no `pyproject.toml`, no test suite, no lint config. The script is the product.

## Common commands

```bash
# Run directly (uv resolves rich on first invocation)
./multi_review.py --list-reviewers
./multi_review.py --dry-run --task code path/to/file.py
./multi_review.py --task security --context docs/threat-model.md api/*.py

# Smoke test without calling any CLI
./multi_review.py --dry-run --task generic README.md
```

There are no `make`, `pytest`, `ruff`, or CI configs. The README explicitly lists "automated tests (one manual smoke test only)" under *Not in v0.1*. Do not invent a test harness unless asked.

## Architecture

Four concerns, all in `multi_review.py`:

1. **Reviewer resolution** — `detect_self()` reads env vars (`CLAUDE_CODE_ENTRYPOINT`, `GEMINI_CLI`, `CODEX_ENV`, `ANTIGRAVITY_AGENT`) to identify the host CLI and self-exclude it from the reviewer set. `detect_available()` checks `PATH`. `resolve_reviewers()` intersects requested ∩ available ∩ not-self.

2. **Prompt assembly** — `build_prompt()` emits an `INJECTION_PREAMBLE` then a task template from `TEMPLATES` (or a `--prompt` / `--prompt-file` override), then wraps every context and input file in `<file path="…">…</file>` tags. The preamble tells the model those tags are data, not instructions — this is the only injection defense.

3. **Per-CLI streaming adapters** — one `ProgressAdapter` subclass per reviewer parses that CLI's JSONL stdout into a shared `Usage` struct + accumulated response text:
   - `ClaudeAdapter`: `stream_event` / `assistant` / `result` envelopes. Prefers fully-assembled `assistant.message.content` over stream deltas to avoid dupes.
   - `GeminiAdapter`: coarse `message` / `result` events; usage only arrives in final `result`.
   - `CodexAdapter`: `item.completed` for `agent_message` (last wins) and `tool_call`; `turn.completed` for usage.
   - `OpenCodeAdapter`: no JSON stream — captures raw stdout as text, tracks bytes only. Its `label_cols = "bytes"` signals the dashboard to show bytes instead of tokens.
   Adapters are registered in `ADAPTER_FOR`. Each CLI's command line is built in `build_command()` / `build_synthesis_command()` — streaming vs non-streaming invocations use different flags.

4. **Orchestration** — `run_all_reviewers()` launches all reviewers via `asyncio.create_subprocess_exec` concurrently; a `rich.Live` table rebuilds from `ReviewerState` objects on each tick. A reviewer is classified `ok` iff `returncode == 0` AND `len(text.encode()) >= FAILURE_MIN_BYTES` (50). After all reviewers return, if `≥2` succeeded and `--synthesize` is on, `run_synthesis()` pipes the assembled `REVIEW.md` back through `--synthesizer` (default `claude`) with `SYNTHESIS_PROMPT` to fill the Consensus section.

## Output contract

`write_review_md()` produces YAML frontmatter (`task`, `reviewers_succeeded`, `reviewers_failed`, `reviewed_at`, `files`, `models`, per-reviewer `usage`, and synthesis metadata when populated) followed by one `## <Cli> Review` section per reviewer and a final `## Consensus Summary`. Failed reviewers get a `(FAILED)` heading with error, elapsed, stderr tail (last 2000 chars), and up to 1000 chars of any partial output. Exit codes: `0` = ≥1 reviewer succeeded, `1` = all failed or no reviewers resolved, `2` = argparse error.

## Conventions worth preserving

- **Self-skip is the default** and must stay on unless `--reviewers` is explicit. This is what keeps the peer review independent.
- **Synthesizer double-weighting caveat** (README §Consensus synthesis): when the synthesizer is also a reviewer, its view is double-counted. Preserve this property and the warning if you refactor synthesis.
- **Per-reviewer model override** uses `--model cli=model-id` (repeatable) — `parse_model_overrides()` validates the CLI name is in `ALL_REVIEWERS`.
- **Adding a new reviewer** = add to `ALL_REVIEWERS`, write a `ProgressAdapter` subclass, register in `ADAPTER_FOR`, and extend both `build_command()` and `build_synthesis_command()`. The README *Not in v0.1* list names `coderabbit`, `qwen`, `cursor` as open candidates.
- **Failure classification is dual** (exit code OR too-small output). Don't weaken either check — both have caught real breakage.
- **Progress telemetry differs per CLI** (see README table). The dashboard's `label_cols` / `bytes_seen` distinction exists because opencode has no event stream.
