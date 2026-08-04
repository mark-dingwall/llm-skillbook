# multi-review

Fan out a code review across multiple AI models in parallel, aggregate results into a `REVIEW.md`, and optionally run a consensus-synthesis pass. Supports inline and reference prompt modes, automated paired runs with drift detection, and harvest-based comparison tracking.

**v0.2 is a Claude Code skill, not a standalone CLI.** The entry point is `/multi-review` inside a Claude Code session. The `claude` reviewer runs as a Task subagent on interactive subscription billing rather than `claude -p` subprocess (which draws from the Agent SDK credit pool post-June 15 2026). Other reviewers (agy, codex, opencode, pykrete, grok) continue as subprocesses.

## Requirements

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- Claude Code (TUI) — required for Task subagent dispatch
- One or more of the supported reviewer CLIs on `PATH`:
  - [`claude`](https://github.com/anthropics/claude-code)
  - `agy`
  - [`codex`](https://github.com/openai/codex)
  - [`opencode`](https://opencode.ai)
  - `pykrete`
  - `grok` (opt-in — see below)

## Install

Run setup once from the cloned repository:

```bash
uv run python -m multi_review.cli.setup --source-repo $(pwd)
```

Setup copies `skills/multi-review/` and `agents/*.md` into `~/.claude/`, resolves the central state path (see §4.2 of spec), and writes `~/.claude/skills/multi-review/config.json`.

To avoid a per-run permission prompt for harvest row writes, pass `--write-allowlist` to have setup insert the resolved `runs.jsonl` path into `~/.claude/settings.local.json`:

```bash
uv run python -m multi_review.cli.setup --source-repo $(pwd) --write-allowlist
```

Without `--write-allowlist`, a Bash permission prompt fires once per run. The allowlist entry is the only write that setup makes to your Claude settings.

For iterating on the skill itself, `--dev` symlinks instead of copying so edits take effect without re-running setup:

```bash
uv run python -m multi_review.cli.setup --source-repo $(pwd) --dev
```

## Pykrete setup

`pykrete` is a **default-on** reviewer (like `agy`) — it runs in every auto-resolved reviewer set without opting in. It routes reviews through NanoGPT via the `pi` agent. Until configured, it shows up as a failed section in `REVIEW.md`.

```bash
npm link pykrete
export NANOGPT_API_KEY=...
```

Then create a `pykrete.toml` (NanoGPT config) and point `PYKRETE_CONFIG` at it:

```bash
export PYKRETE_CONFIG=/path/to/pykrete.toml
```

`models: {pykrete: <family>}` in a prompt YAML names a NanoGPT **family** (e.g. `glm`), not a specific model — pykrete resolves the actual model within that family itself.

The prompt's `task` is forwarded as pykrete's `--task`, and pykrete picks that family's lead model from `[defaults.<task>].<family>` (falling back to `[defaults.general]`). So put the model you want for reviews under `[defaults.code]` — or whichever task you actually run. multi-review's `generic` task maps to pykrete's own `general`; every other task name goes through verbatim, and a task with no `[defaults.*]` table just warns on stderr and falls back.

Without `NANOGPT_API_KEY` and `PYKRETE_CONFIG` set, pykrete fails clean (recorded failure with the config error as the reason) — it does not abort the rest of the fanout.

## Grok setup

`grok` is an **opt-in** reviewer — it is never auto-selected. Name it explicitly
in a prompt YAML's `reviewers` (or `synthesizer`) to use it:

```yaml
reviewers: [claude, codex, grok]
models:
  grok: grok-4.5-build     # optional; omit for grok's default
```

Install and authenticate the Grok Build CLI so `grok` is on `PATH`. Verify with
`/multi-review --list-reviewers` (grok is probed even though it is opt-in).

multi-review invokes it as
`grok --sandbox workspace --prompt-file /dev/stdin --output-format streaming-json`.
The prompt travels on stdin; `--sandbox workspace` fences writes to cwd + tmp
while leaving reads open, so reference-mode file manifests outside cwd still work.
The synthesis path runs the same binary without `--output-format` — plain-text
output taken verbatim, not the streaming-json envelope — so don't assume the
flag is unconditional.

## Usage

Invoke from inside a Claude Code session:

```
/multi-review
```

### Invocation forms

| Form | Behaviour |
|------|-----------|
| `/multi-review` | Interactive prompt build — `multi-review-build` subagent asks questions, authors a YAML prompt file, then runs it |
| `/multi-review "seed text"` | Interactive build with seed — subagent skips discovery questions, starts from your seed |
| `/multi-review --use-defaults "seed text"` | Autonomous build — subagent does a shallow cwd scan, infers defaults, writes YAML without prompting |
| `/multi-review --prompt-files A.yaml,B.yaml` | Run one or more pre-written prompt files directly (skips build subagent) |
| `/multi-review --resume-pair <pair-id>` | Resume pass 2 of a paired run |
| `/multi-review --report` | Regenerate `EXPERIMENTS.md` from harvest log, then exit |
| `/multi-review --list-reviewers` | Probe each CLI via `shutil.which` + `<cli> --version`, print availability and detected models |

## Prompt YAML schema

Reviews are driven by YAML prompt files. The `multi-review-build` subagent authors these interactively; you can also write them by hand and pass them with `--prompt-files`.

```yaml
prompt_format_version: 1

# Task preset. One of: code | plan | security | generic | custom
task: code

# Files to review (required)
files:
  - src/auth.ts
  - src/session.ts

# Extra context — always inlined regardless of mode (optional)
context_files:
  - docs/threat-model.md

# Free-form prompt override. Only used when task == custom
custom_prompt: |
  Focus on dependency ordering and rollback paths

# Prompt shape. One of: inline | reference | both
# inline  — file contents embedded in <file-NONCE> tags
# reference — manifest of absolute paths; reviewer reads via its own tools
# both — run once in each mode (paired run for comparison)
mode: reference

# Synthesis pass. One of: claude | agy | codex | opencode | pykrete | grok | none
synthesizer: claude

# Reviewer set
reviewers:
  - claude
  - agy
  - codex
  - opencode
  - pykrete
#  - grok        # opt-in: never auto-selected

# Primary model per reviewer (optional — omit for defaults)
models:
  claude: claude-opus-4-7
  codex: gpt-5
  opencode: openrouter/deepseek/deepseek-v4-pro
  pykrete: glm      # names a NanoGPT *family*, not a specific model
  grok: grok-4.5-build

# Effort hint per reviewer — silently ignored where unsupported
# claude effort is pinned in the agent definition (xhigh); this field
# is ignored for claude
model_effort:
  codex: high

# Drift policy between passes (mode: both only)
# ignore — no snapshot, no diff; pair flagged comparison_eligible: false
# abort  — abort pass 2 on any drift
# ask    — AskUserQuestion: proceed | abort | investigate
if_drift: ask

# Optional overrides
output_dir: null    # default: <cwd>/.multi-review/sessions/<auto-slug>/
save_as: null       # promote ephemeral YAML to persistent name if set
harvest: true       # write harvest row to central runs.jsonl
```

### Field reference

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `prompt_format_version` | int | — | Required. Currently `1`. |
| `task` | enum | — | Required. `code \| plan \| security \| generic \| custom`. |
| `files` | list[path] | — | Required. Paths must exist at validation time. Relative paths resolve against the **prompt YAML's own directory**, not cwd. |
| `context_files` | list[path] | `[]` | Always inlined (both modes). Also snapshotted for drift detection. |
| `custom_prompt` | string | — | Required when `task == custom`. |
| `mode` | enum | — | Required. `inline \| reference \| both`. |
| `synthesizer` | enum | `claude` | Which CLI runs the consensus pass. `none` disables it. |
| `reviewers` | list[enum] | claude, agy, codex, opencode, pykrete | Subset of `claude \| agy \| codex \| opencode \| pykrete \| grok`. Default omits `grok` (opt-in). |
| `models` | map | CLI defaults | Primary model per reviewer. Setting this pins the reviewer (see below). |
| `model_effort` | map | `{}` | Effort hint per reviewer. Silently ignored where unsupported. |
| `if_drift` | enum | `ask` | `ignore \| abort \| ask`. `ask` keeps the pair comparison-eligible unless the user chooses to proceed after drift. |
| `output_dir` | path\|null | auto | Override staging directory for session files. |
| `save_as` | string\|null | null | Name to promote the ephemeral YAML to a persistent prompt file. |
| `harvest` | bool | `true` | Write a harvest row to `runs.jsonl`. |

Validate a YAML file without running a review:

```bash
uv run python -m multi_review.cli.validate_prompt prompt.yaml
```

## Model pinning

Setting `models.X: <model>` pins reviewer X to that model. This matches v0.1 `--model X=Y` behaviour. Reviewers run single-attempt; 429/capacity errors → fail clean.

> Fallback chain (gemini capacity recovery) scrapped 2026-06-19. See BACKLOG v0.2.1 quota-proximity probe for the planned replacement.

## Paired runs and drift

`mode: both` runs the same prompt twice — once inline, once reference — for inline-vs-reference comparison. Pass 2 fires immediately after pass 1's join barrier resolves in the same turn.

**Pass order** is read from `EXPERIMENTS.md`'s `next_recommended_order` field. When counters tie (including every fresh codebase), the default is `reference` first.

**Drift detection** (`if_drift: ask` default) snapshots `files` and `context_files` before pass 1 and diffs them before pass 2. On drift, the skill asks whether to proceed, abort, or investigate (dispatches `multi-review-investigate` subagent to classify each changed file against pass-1 findings).

Manual smoke procedures:
- `tests/manual/paired_pass.md` — full paired-run procedure
- `tests/manual/drift_ask.md` — drift-ask flow

## Comparison eligibility

A paired run contributes to `sessions_reference_first` / `sessions_inline_first` counters in `EXPERIMENTS.md` only when:

- **Per-reviewer**: default model used AND reviewer finished `ok`
- **Pair-level**: both passes satisfy the per-reviewer check for every reviewer; `if_drift` was not `ignore`; and the user did not choose "proceed" after drift was detected

Runs that fail any check are harvested (so the data is preserved) but are excluded from comparison stats. Legacy v1 rows with null eligibility fields are excluded by design.

## Limitations

- **Drift detection covers explicitly-submitted files only.** Files the pass-1 reviewer happened to read via tools (reference mode) but are not listed in `files` or `context_files` are not tracked. Untracked-tool-read drift is a documented v0.2 gap.
- **agy is an agentic, uncontained reviewer.** `agy --print` runs as an autonomous agent and reads its prompt from a file (agy has no stdin input mode). Headless agy auto-denies every permission-gated tool call, including reading that prompt file, so multi-review passes `--dangerously-skip-permissions` unconditionally — without it, no agy review produces output at all. The cost is that agy can run arbitrary commands on your working tree during a review: **don't point agy at untrusted code** until sandbox containment lands (BACKLOG). Its step-narration preamble is trimmed to the first `## Summary` heading before aggregation.
- **v0.1 standalone CLI removed.** `./multi_review.py file.ts` prints a deprecation banner and exits 1. The v0.1 entry script will be removed entirely in v0.3.
- **No timeouts in v0.2.** The prompt YAML has no timeout field. Subprocess reviewers accept `--timeout N` when `spawn` is invoked by hand, but the skill never passes it; Claude Code's `Task` tool exposes no timeout knob at all, so the claude reviewer could not honour one anyway. Tracked in BACKLOG.
- **claude token telemetry is null.** Task subagents do not surface JSONL-level usage; `input_tokens` / `output_tokens` / `cached_tokens` for the claude reviewer are `null` in all harvest rows. Comparisons needing claude token data should filter on `telemetry_quality == "reliable"` (will return zero rows until a future path adds reliable telemetry).
- **grok tool-call telemetry is unavailable, and `0` is a sentinel.** grok emits
  no tool-call events in any output format, so `tool_calls` is always `0` for the
  grok reviewer **even on runs where it demonstrably used tools**. Read it as
  "unknown", never as "grok used no tools" — the harvest schema has no way to
  express unavailability for a single field. Token counts are complete and
  reliable; harvest rows record `telemetry_quality: known-issues` to reflect the
  split. Filtering analyses to `telemetry_quality == "reliable"` therefore also
  excludes grok's good token data; filter per-field when that matters.
- **grok is an agentic, uncontained reviewer.** It auto-approves its own tool use
  in headless mode and can run commands on your working tree during a review.
  `--sandbox workspace` fences writes but is not a security boundary and does not
  restrict reads — **don't point grok at untrusted code** until sandbox
  containment lands (BACKLOG). Same posture as agy and pykrete.

## Testing discipline

See `CLAUDE.md` — every bugfix in an untested path backfills the test that would have caught it. Skill-level interactive flows that genuinely cannot be automated → document a manual smoke step in `tests/manual/` instead.

## Migrating from v0.1

Two helper CLIs handle the migration:

- **`mr-migrate-harvest`** (`multi_review.cli.migrate_harvest`) — backfills v1 harvest rows to schema v2 (`usage` → `usage_by_reviewer`, new nullable fields). Interactive, row-by-row; groups candidate pairs by project + input-file set + mode-flip + time window. Takes a `.bak` copy of `runs.jsonl` before any rewrite.

- **`mr-migrate-sidecars`** (`multi_review.cli.migrate_sidecars`) — interactive sidecar reorganisation. Maps existing `runs/notes/*.md` sidecars to candidate pairs or marks them legacy. Emits format-C reports to the resolved central `reports/` directory.

```bash
uv run python -m multi_review.cli.migrate_harvest
uv run python -m multi_review.cli.migrate_sidecars
```

Both are one-shot and idempotent if re-run. Run harvest migration first, then sidecar migration.

## License

MIT. See `LICENSE`.
