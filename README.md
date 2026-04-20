# multi-review

Run the same review prompt through multiple AI CLIs in parallel, then aggregate their
output into a single `REVIEW.md` (with an optional consensus-synthesis pass).

Different models catch different blind spots. A prompt, plan, or piece of code that
survives independent review from 2–3 AI CLIs is more robust than one that only
passes a single pair of eyes.

Single-file Python script. Run via `uv`. No packaging, no install step.

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) — handles the `rich` dependency automatically via PEP 723 inline metadata.
- One or more of the supported AI CLIs on `PATH`:
  - [`claude`](https://github.com/anthropics/claude-code)
  - [`gemini`](https://github.com/google-gemini/gemini-cli)
  - [`codex`](https://github.com/openai/codex)
  - [`opencode`](https://opencode.ai) _(optional — no JSON stream, progress tracked as byte count only)_

## Install

```bash
git clone https://github.com/mark-dingwall/multi-review ~/tools/multi-review
ln -s ~/tools/multi-review/multi_review.py ~/.local/bin/multi-review
```

Or run it directly:

```bash
~/tools/multi-review/multi_review.py --list-reviewers
```

The script's shebang (`#!/usr/bin/env -S uv run --script`) lets `uv` resolve dependencies on first run.

## Quickstart

```bash
# Review one file with the default "generic" prompt
multi-review src/auth.ts

# Code-focused review across multiple files
multi-review --task code src/auth.ts src/session.ts

# Security audit with extra context
multi-review --task security --context docs/threat-model.md api/handlers/*.py

# Review a plan document with a custom prompt
multi-review --prompt "Focus on dependency ordering and rollback paths" plan.md

# Skip the consensus synthesis pass
multi-review --task code --no-synthesize file.py

# Use a different synthesizer
multi-review --task plan --synthesizer gemini PLAN.md

# Per-reviewer model override
multi-review --model claude=claude-opus-4-7 --model codex=gpt-5 file.py
```

## How it works

1. Builds one prompt (task preset or custom) and wraps the reviewed files in `<file>` tags with a prompt-injection defense preamble.
2. Launches all available reviewer CLIs in parallel via `asyncio`.
3. Streams each CLI's JSONL event output through a per-CLI `ProgressAdapter` that tracks token counts, tool calls, and elapsed time — all rendered in a live `rich` dashboard.
4. Captures each CLI's response and writes `REVIEW.md` with YAML frontmatter (reviewers, usage, models) + one Markdown section per reviewer.
5. If ≥2 reviewers succeeded and `--synthesize` is on (default), pipes the aggregated `REVIEW.md` through the synthesizer CLI to fill a "Consensus Summary" section (Agreed Strengths / Agreed Concerns / Divergent Views).

## Self-skip

When running inside an AI CLI that is also a reviewer, that CLI is automatically
excluded so the review stays independent. Detection is env-var-based:

| Env var                  | Detected host | Reviewer skipped |
| ------------------------ | ------------- | ---------------- |
| `CLAUDE_CODE_ENTRYPOINT` | Claude Code   | `claude`         |
| `GEMINI_CLI`             | Gemini CLI    | `gemini`         |
| `CODEX_ENV`              | Codex CLI     | `codex`          |
| `ANTIGRAVITY_AGENT=1`    | Antigravity   | _(none)_         |

Override with `--reviewers claude,gemini,codex` if you want to force a specific set.

Check detection:

```bash
multi-review --list-reviewers
```

## Progress signals per reviewer

Each CLI exposes different telemetry during a run. The dashboard shows what's available:

| Reviewer   | In/out tokens | Tool calls | Bytes read | Phase label |
| ---------- | ------------- | ---------- | ---------- | ----------- |
| `claude`   | live (per-message)           | yes  | yes | yes (`running`, `tool:<name>`, `done`) |
| `gemini`   | final-only (in `result`)     | final-only | yes | coarse (`running`, `done`) |
| `codex`    | final-only (in `turn.completed`) | yes  | yes | yes (`running`, `tool:<name>`, `done`) |
| `opencode` | —                            | —    | yes | minimal (`running`, `done`) — no JSON stream |

`opencode` has no structured event stream, so its dashboard column is the raw byte count of stdout.

## Consensus synthesis (and the double-weighting caveat)

By default, once all reviewers have responded, the aggregated `REVIEW.md` is piped
through `--synthesizer` (default: `claude`) with a fixed synthesis prompt instructing
it to treat all reviews as peer input.

**Caveat:** when the synthesizer is also a reviewer, that model's view is effectively
double-weighted (once as reviewer, once as synthesizer). For the most independent
consensus, pick a synthesizer that is _not_ in the reviewer set, e.g.:

```bash
multi-review --task code --synthesizer claude src/*.py   # if self-skip removed claude as reviewer
multi-review --task code --reviewers gemini,codex --synthesizer claude src/*.py
```

Synthesis is skipped automatically when fewer than 2 reviewers succeed; the Consensus
section will read `Consensus: n/a (insufficient reviewers)`.

Disable it entirely with `--no-synthesize`.

## Prompt-injection defense

Every file passed to `multi-review` is wrapped in `<file path="...">...</file>`
tags, and the prompt opens with an explicit instruction that content inside those
tags is review data, not instructions. This does not remove the risk of injection
— it only raises the floor. Don't use `multi-review` to review attacker-controlled
input without additional sandboxing.

## Exit codes

- `0` — at least one reviewer succeeded and wrote a review.
- `1` — all reviewers failed, or no reviewers were available after filtering.
- `2` — argument error.

A response is classified as a failure when the CLI exits non-zero OR when the
captured response is under 50 bytes.

Partial failures still produce a `REVIEW.md`; failed reviewers get their own
section with an `error:` line and a tail of their captured stderr.

## CLI surface

```
multi-review [file ...]
  --task {code,plan,design,security,generic}  (default: generic)
  --prompt TEXT            # custom prompt, overrides --task
  --prompt-file PATH       # read custom prompt from file
  --context PATH           # extra context (repeatable)
  --reviewers csv          # explicit reviewer list
  --output PATH            # default: ./REVIEW.md
  --timeout SEC            # default: 600 per reviewer
  --no-synthesize          # disable consensus pass
  --synthesizer CLI        # default: claude
  --model cli=model-id     # per-reviewer model override (repeatable)
  --dry-run                # print assembled prompt, exit
  --list-reviewers         # show detected CLIs + self-detection
  --version
  -h, --help
```

## Not in v0.1

- Retries / exponential backoff.
- `coderabbit`, `qwen`, `cursor` adapters (happy to add — open an issue).
- `--output-format json`.
- Cost budgets / `--max-budget`.
- Automated tests (one manual smoke test only).

## License

MIT. See `LICENSE`.
