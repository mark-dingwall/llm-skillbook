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
  - [`opencode`](https://opencode.ai) _(optional — uses `--format json` event stream; token usage best-effort, depends on upstream schema)_

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
multi-review --model claude=claude-opus-4-7 --model codex=gpt-5.5 file.py
```

## How it works

1. Builds one prompt (task preset or custom) and wraps the reviewed files in nonce-tagged `<file-NONCE>` tags with a prompt-injection defense preamble.
2. Launches all available reviewer CLIs in parallel via `asyncio`.
3. Streams each CLI's JSONL event output through a per-CLI `ProgressAdapter` that tracks token counts, tool calls, and elapsed time — all rendered in a live `rich` dashboard.
4. Captures each CLI's response and writes `REVIEW.md` with YAML frontmatter (reviewers, usage, models) + one Markdown section per reviewer.
5. If ≥2 reviewers succeeded and `--synthesize` is on (default), pipes the aggregated `REVIEW.md` through the synthesizer CLI to fill a "Consensus Summary" section (Agreed Strengths / Agreed Concerns / Divergent Views).

## Self-skip (opt-in)

When `multi-review` is launched **from inside an AI CLI** (e.g. you're using Claude
Code and you run `multi-review` in its terminal), that CLI is the "host". By default
the host is still included as a reviewer — the spawned subprocess has its own
context window with no prior reasoning carried over, so it remains a useful
independent voice. Pass `--skip-self` to drop the host from the auto-resolved
reviewer set.

When launched from a plain shell, no host is detected and `--skip-self` is a no-op.

Detection is env-var-based — host is whichever of these the parent CLI sets:

| Env var                  | Detected host | Reviewer dropped under `--skip-self` |
| ------------------------ | ------------- | ------------------------------------- |
| `CLAUDE_CODE_ENTRYPOINT` | Claude Code   | `claude`                              |
| `GEMINI_CLI`             | Gemini CLI    | `gemini`                              |
| `CODEX_ENV`              | Codex CLI     | `codex`                               |
| `OPENCODE`               | opencode      | `opencode`                            |
| `ANTIGRAVITY_AGENT=1`    | Antigravity   | _(none — host detection skipped)_     |

`--skip-self` only affects the auto-resolved reviewer list. An explicit
`--reviewers claude,gemini` runs exactly that set even with `--skip-self`.

Check detection:

```bash
multi-review --list-reviewers              # shows host + effective set
multi-review --list-reviewers --skip-self  # preview the dropped set
```

## Progress signals per reviewer

Each CLI exposes different telemetry during a run. The dashboard shows what's available:

| Reviewer   | In/out tokens | Tool calls | Bytes read | Phase label |
| ---------- | ------------- | ---------- | ---------- | ----------- |
| `claude`   | live (per-message)           | yes  | yes | yes (`running`, `tool:<name>`, `done`) |
| `gemini`   | final-only (in `result`)     | final-only | yes | coarse (`running`, `done`) |
| `codex`    | final-only (in `turn.completed`) | yes  | yes | yes (`running`, `tool:<name>`, `done`) |
| `opencode` | best-effort (in `step_finish`) | yes | yes | yes (`running`, `tool:<name>`, `done`, `error:<name>`) |

`opencode` now emits a structured event stream via `--format json`. Token counts are best-effort: they appear if the CLI surfaces them in `step_finish`, otherwise `0`. Bytes read is still tracked for all reviewers.

## Consensus synthesis (and the double-weighting caveat)

By default, once all reviewers have responded, the aggregated `REVIEW.md` is piped
through `--synthesizer` (default: `claude`) with a fixed synthesis prompt instructing
it to treat all reviews as peer input.

**Caveat:** when the synthesizer is also a reviewer, that model's view is effectively
double-weighted (once as reviewer, once as synthesizer). For the most independent
consensus, pick a synthesizer that is _not_ in the reviewer set, e.g.:

```bash
multi-review --task code --skip-self --synthesizer claude src/*.py   # claude only as synthesizer
multi-review --task code --reviewers gemini,codex --synthesizer claude src/*.py
```

Synthesis is skipped automatically when fewer than 2 reviewers succeed; the Consensus
section will read `Consensus: n/a (insufficient reviewers)`.

Disable it entirely with `--no-synthesize`.

## Prompt-injection defense

Every file passed to `multi-review` is wrapped in
`<file-NONCE path="...">...</file-NONCE>` tags using a fresh 8-hex per-run nonce
(synthesis input wraps each review in `<review-NONCE reviewer="...">` the same way),
and the prompt opens with an explicit instruction that content inside those tags is
review data, not instructions. The nonce prevents a reviewed file from forging the
closing tag and breaking out of the data block. This does not remove the risk of
injection — it only raises the floor. Don't use `multi-review` to review
attacker-controlled input without additional sandboxing.

## Capacity-aware fallback (gemini)

Gemini's frontier models hit `429 MODEL_CAPACITY_EXHAUSTED` opaquely. Every
gemini run is **capacity-resilient by default**: a 3-deep model chain is
walked on capacity-class stderr matches (regex over `RESOURCE_EXHAUSTED`,
`MODEL_CAPACITY_EXHAUSTED`, `Quota exceeded`, `429`, `UNAVAILABLE`,
`model is overloaded`), stopping at the first success.

Default chain (top-to-bottom precedence):

```
gemini-3.1-pro-preview
gemini-3-flash-preview
gemini-2.5-pro
```

Knobs:

- `--no-fallback` — disable fallback entirely (single attempt only).
- `--fallback-model gemini=A,B,C` — override the chain.
- `--model gemini=X` — **pins** to X and **disables fallback** for gemini.
  Use `--fallback-model` if you want both an override and a chain.

Real failures (auth, network, prompt-too-large) do **not** burn the chain —
only capacity-class matches trigger the next hop. Mid-stream 429s that
already produced ≥50 bytes of usable output are kept as-is (no retry).

Surfacing:

- The dashboard shows a **Model** column. When fallback fires you get an
  `*N` marker (N = attempts).
- `REVIEW.md` frontmatter gains a `fallbacks:` block when ≥2 hops were
  walked, naming `attempts` and the `used` model. Synthesis pass tracked
  the same way under `fallbacks.synthesis`.
- A `[yellow]Fallback fired …[/yellow]` console line per reviewer (and for
  synthesis) prints the stderr tail — capture these for tuning the regex.

Cost note: a stuck-capacity gemini can spend up to 6× the prompt cost on a
single review. Fallback firing is visible (dashboard + frontmatter +
console line) so the cost stays attributable, but watch for it on large
prompts. Use `--no-fallback` if you'd rather fail fast.

Other CLIs (claude, codex, opencode) have no fallback today — their
capacity patterns and chains are unset.

## Inline vs reference mode

By default (`--mode inline`), every input file's contents are embedded into the
prompt inside `<file-NONCE>` tags. Front-loading 100k+ tokens of source can
dilute model attention and surface fewer findings than a same-prompt interactive
run where the model reads files iteratively as it reasons.

`--mode reference` instead emits a manifest of absolute paths and instructs the
model to read each file via its own file-reading tools. Context files (`--context`)
are still inline-wrapped regardless of mode — they're framing material the model
needs before any tool call.

```bash
multi-review --mode reference --task code src/auth.ts src/session.ts
```

When to prefer reference:

- Large file sets where front-loaded context dilutes attention.
- Reviewer CLIs whose models have strong file-reading / search discipline.

Caveats:

- The reviewer CLI must have its file-read tool enabled. Permission prompts
  mid-stream are still possible (Phase 2 of this work will add an opt-in
  `--bypass-perms` + bwrap sandbox combo to suppress prompts safely).
- Models with poor read-as-you-reason habits may underperform inline. If a
  reviewer comes back light on findings, swap modes and compare.

## Thorough mode (optional)

For high-stakes reviews — design contracts, ship/no-ship decisions,
cross-checking an internal review verdict — consider running multi-review
**twice** against the same inputs, once with `--mode inline` and once with
`--mode reference`. Early evidence suggests the two prompt shapes elicit
different reviewer behaviour: some reviewers tool-read deeper in reference
mode, others surface findings only when content is inlined. The two runs
together cover signal a single mode misses.

Cost: ~2× wall time, more model quota burned, more bytes on the wire for
inline. Worth it for important reviews; overkill for small drive-by passes.

If you're a coding agent invoked with "build a prompt for multi-review at
/path/to/it", **relay this option to your user** — many will pick it for
important reviews if asked.

Each run automatically writes a metadata row to `runs/runs.jsonl`
(opt out with `--no-harvest`). Run `multi_review.py --report` to regenerate
`EXPERIMENTS.md` from the accumulated data; that file recommends which
order to run in next to keep the dataset balanced.

(Diversity-of-findings claim is currently n=4 runs across two projects —
early signal, not robust. See `EXPERIMENTS.md` for raw comparison data.)

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
  --task                   {code,plan,design,security,generic}  (default: generic)
  --prompt TEXT            # custom prompt, overrides --task
  --prompt-file PATH       # read custom prompt from file
  --context PATH           # extra context (repeatable)
  --reviewers csv          # explicit reviewer list
  --output PATH            # default: ./REVIEW.md; auto-suffixes -2/-3/... if target exists
  --timeout SEC            # default: no timeout (run to completion or Ctrl+C)
  --no-synthesize          # disable consensus pass
  --synthesizer CLI        # default: claude
  --model cli=model-id     # per-reviewer model override; pins + disables fallback.
  --fallback-model cli=A,B,C  # override the built-in fallback chain (repeatable)
  --no-fallback            # disable capacity-aware fallback (gemini default chain)
  --mode {inline,reference} # inline: file contents embedded (default).
                            # reference: manifest of absolute paths only.
  --allow-missing          # warn-and-skip missing input/context files (default: error)
  --dry-run                # print assembled prompt, exit
  --list-reviewers         # show detected CLIs + self-detection
  --no-harvest             # skip writing per-run metadata row to runs/runs.jsonl
  --project-tag NAME       # partition harvest rows by phase or arbitrary label
                           # (default: git origin basename, fallback cwd basename)
  --report                 # regenerate EXPERIMENTS.md from runs/runs.jsonl, exit
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
