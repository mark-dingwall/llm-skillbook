# multi-review

Fan out a code review across multiple AI models in parallel, aggregate results into a `REVIEW.md`, and optionally run a consensus-synthesis pass. It supports an interactive Claude Code skill and a contained headless CLI.

**Two supported entry points.** Use `/multi-review` inside Claude Code for the interactive workflow, or `multi_review.py --prompt-file … --out-dir …` for a contained headless single pass. The skill runs `claude` as a Task subagent; the headless driver runs it through `claude -p`. The proposed `claude -p` billing change that originally motivated this split is deferred indefinitely, so choose the entry point that fits the caller rather than a presumed billing distinction.

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

Setup copies `skills/multi-review/` and `agents/*.md` into `~/.claude/`.

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
while leaving reads open, so file manifests outside cwd still work.
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
| `/multi-review --list-reviewers` | Probe each CLI via `shutil.which` + `<cli> --version`, print availability and detected models |

## Prompt YAML schema

Reviews are driven by YAML prompt files. The `multi-review-build` subagent authors these interactively; you can also write them by hand and pass them with `--prompt-files`.

```yaml
prompt_format_version: 2

# Task preset. One of: code | plan | security | generic | custom
task: code

# Files to review (required)
files:
  - src/auth.ts
  - src/session.ts

# Extra context — always inlined (optional)
context_files:
  - docs/threat-model.md

# Free-form prompt override. Required when task == custom; when supplied for
# any task, it replaces that task's built-in template.
custom_prompt: |
  Focus on dependency ordering and rollback paths

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

```

### Field reference

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `prompt_format_version` | int | — | Required. Currently `2`. |
| `task` | enum | — | Required. `code \| plan \| security \| generic \| custom`. |
| `files` | list[path] | — | Required. Paths must exist at validation time. Relative paths resolve against the **prompt YAML's own directory**, not cwd. |
| `context_files` | list[path] | `[]` | Always inlined. |
| `custom_prompt` | string | — | Required when `task == custom`. |
| `synthesizer` | enum | `claude` | Which CLI runs the consensus pass. `none` disables it. |
| `reviewers` | list[enum] | claude, agy, codex, opencode, pykrete | Subset of `claude \| agy \| codex \| opencode \| pykrete \| grok`. Default omits `grok` (opt-in). |
| `models` | map | CLI defaults | Primary model per reviewer. Setting this pins the reviewer (see below). |

Validate a YAML file without running a review:

```bash
uv run python -m multi_review.cli.validate_prompt prompt.yaml
```

## Model pinning

Setting `models.X: <model>` pins reviewer X to that model. This matches v0.1 `--model X=Y` behaviour. Reviewers run single-attempt; 429/capacity errors → fail clean.

> Fallback chain (gemini capacity recovery) scrapped 2026-06-19. See BACKLOG v0.2.1 quota-proximity probe for the planned replacement.

## Limitations

- **agy is an agentic, uncontained reviewer.** `agy --print` runs as an autonomous agent and reads its prompt from a file (agy has no stdin input mode). Headless agy auto-denies every permission-gated tool call, including reading that prompt file, so multi-review passes `--dangerously-skip-permissions` unconditionally — without it, no agy review produces output at all. The cost is that agy can run arbitrary commands on your working tree during a review: **don't point agy at untrusted code** until sandbox containment lands (BACKLOG). Its step-narration preamble is trimmed to the first `## Summary` heading before aggregation.
- **The v0.1 positional standalone CLI remains removed.** `./multi_review.py file.ts` is not a
  supported interface. The root script path now hosts a supported headless single-pass contract for
  contained callers: run `uv run <absolute-repo-path>/multi_review.py --prompt-file <yaml> --out-dir
  <dir> [--timeout <sec>]` inside `bwrap --unshare-pid --die-with-parent`, and send termination
  signals to the `bwrap` wrapper. This is required for full-tree shutdown because Codex/OpenCode may
  run engines below their direct shim. This supported driver is for contained callers; it does not
  replace the `/multi-review` skill.
- **No timeouts in v0.2.** The prompt YAML has no timeout field. Subprocess reviewers accept `--timeout N` when `spawn` is invoked by hand, but the skill never passes it; Claude Code's `Task` tool exposes no timeout knob at all, so the claude reviewer could not honour one anyway. Tracked in BACKLOG.
- **grok is an agentic, uncontained reviewer.** It auto-approves its own tool use
  in headless mode and can run commands on your working tree during a review.
  `--sandbox workspace` fences writes but is not a security boundary and does not
  restrict reads — **don't point grok at untrusted code** until sandbox
  containment lands (BACKLOG). Same posture as agy and pykrete.

## Testing discipline

See `CLAUDE.md` — every bugfix in an untested path backfills the test that would have caught it. Skill-level interactive flows that genuinely cannot be automated → document a manual smoke step in `tests/manual/` instead.

## License

MIT. See `LICENSE`.
