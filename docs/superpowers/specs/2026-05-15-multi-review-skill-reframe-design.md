# multi-review v0.2 — skill reframe design

**Date:** 2026-05-15
**Status:** brainstorm complete, awaiting plan
**Driver:** Anthropic's June 15 2026 billing change moves `claude -p` and Agent SDK usage off interactive Pro/Max plan limits onto separate Agent SDK credit pools. For multi_review's per-PR review workflow this is a ~10x effective cost increase, and the existing CLI is the workflow squarely targeted by the change.

## 1. Background

`multi_review.py` (v0.1) is a 1966-line single-file Python script that fans out one review prompt to multiple AI CLIs in parallel (claude, gemini, codex, opencode), aggregates outputs into `REVIEW.md`, and optionally runs a synthesis pass. The claude reviewer is spawned via `claude -p` subprocess — which from June 15 2026 will draw from the new Agent SDK credit pool ($20/mo on Pro, $200/mo on Max-20x), not the interactive subscription limits. Empirically this gives a Pro user ~10–40 opus review runs/month before drain.

Sonnet at the same effort is materially weaker than opus per the user's own A/B testing (`Opus 4.7 xhigh|high ≥ GPT 5.5 high > Deepseek 4 Pro ≥ Gemini 3.1 Pro`), so dropping claude to sonnet isn't a viable mitigation. Dropping claude from the reviewer pool entirely loses the strongest signal.

Storybloq (Storybloq/storybloq) demonstrates a viable pattern: a Claude Code skill that returns prompts to the host session, which then dispatches subagents via the native `Task` tool. Subagents spawned via `Task` from an interactive session draw from interactive subscription billing, not the Agent SDK pool. This is the architectural seam we exploit.

## 2. Goals

1. Move the claude reviewer from `claude -p` subprocess invocation to host-dispatched `Task` subagent so it stays on interactive subscription billing.
2. Preserve cross-model peer review: gemini, codex, opencode (deepseek-via-openrouter) continue as subprocess invocations.
3. Bundle the inline-vs-reference comparison methodology into the call lifecycle: snapshot, drift detection, paired-run reports, harvest, EXPERIMENTS.md regeneration — all automated.
4. Promote review prompts to first-class artefacts (YAML files) for reusability and configurability.
5. Quality-priority: opus `xhigh` for reviewer, opus `high` for synthesizer. Token cost secondary to review quality.
6. Cleanly migrate ~9 historical sidecars from ad-hoc markdown to structured format C without polluting the inline-vs-reference signal with noisy data.

## 3. Non-goals

- Multi-runtime support (Codex, Gemini, OpenCode hosts). Claude Code only for v0.2. The architecture doesn't preclude future ports.
- MCP server. The work distributes cleanly across helper CLIs invoked from a skill via Bash, with no in-process state requirements.
- User-facing CLI. The skill is the sole entry surface; existing automation use cases (CI, git hooks) are exactly the workflows being repriced and are explicitly out of scope.
- Daemon mode, git-hook integration. These cross the "automation that looks like API-bypass" line and risk ToS exposure.
- DeepSeek/Qwen/Kimi as first-class reviewers. DeepSeek is already accessed via opencode→OpenRouter; the others are below the frontier-quality bar.

## 4. Architecture

### 4.1 Package layout

```
<multi-review-repo>/
├── multi_review/
│   ├── core/                       # importable library
│   │   ├── prompt.py               # assembly (inline/reference modes, nonce tags); exports SUMMARY_HEADING_CONTRACT canonical string
│   │   ├── reviewers.py            # CLI_SPEC, adapter logic; defines ClaudeTaskAdapter (v0.2: build_subagent_prompt(spec) → str + parse_subagent_result(text, metadata) → ReviewerResult). SKILL.md owns Task dispatch; this seam is payload/parse only. Subprocess- and direct-API alternative claude paths are deferred (§14) — they own dispatch, so they slot into the broader reviewer registry, not this adapter.
│   │   ├── fanout.py               # subprocess spawn + JSONL stream parse
│   │   ├── harvest.py              # JSONL row append + telemetry quality flags
│   │   ├── snapshot.py             # snapshot dir mgmt + diff
│   │   ├── report.py               # EXPERIMENTS.md regeneration
│   │   └── pending.py              # pending-pair record read/write
│   └── cli/                        # skill-internal helper CLIs
│       ├── prepare.py
│       ├── spawn.py
│       ├── aggregate.py
│       ├── cooldown_notify.py
│       ├── harvest_row.py
│       ├── snapshot.py
│       ├── report.py
│       ├── validate_prompt.py
│       ├── migrate_sidecars.py
│       ├── pending.py
│       └── setup.py
├── skills/multi-review/
│   ├── SKILL.md
│   └── templates/                  # template content blocks for subagent prompts
├── agents/
│   ├── multi-review-reviewer.md       # opus, effort: xhigh
│   ├── multi-review-synthesizer.md    # opus, effort: high
│   ├── multi-review-build.md          # sonnet, effort: high
│   └── multi-review-investigate.md    # sonnet, effort: high
├── tests/
│   ├── fixtures/streams/<cli>/     # captured JSONL fixtures
│   ├── unit/
│   ├── integration/
│   └── manual/                     # documented smoke procedures
├── docs/superpowers/specs/
├── runs/                           # central harvest + reports + notes (dev-checkout path; resolved location may differ — see §4.2)
│   ├── runs.jsonl
│   ├── reports/                    # format-C paired-run reports
│   └── notes/
│       └── legacy/                 # pre-schema-stabilisation sidecars
├── BACKLOG.md
├── EXPERIMENTS.md                  # generated; do not edit by hand
└── README.md
```

### 4.2 State directories

- `<cwd>/` (cwd root)
  - `REVIEW-<slug>.md` — final aggregated review output for single-pass runs, auto-suffixed on collision. Lives at cwd root (not under `.multi-review/`) for visibility. **Not gitignored by default**; user opts in to commit or extends `.gitignore` per project. **Paired runs**: pass-1 REVIEW.md is staged under `.multi-review/sessions/<pass-1-run-id>/REVIEW.md` during pass 2 fanout to kill pass-1-leakage as a hidden-drift channel into pass 2's reference-mode tool reads. On pair completion **both** outputs land at cwd root as `REVIEW-<slug>-<mode>.md` (e.g. `REVIEW-auth-review-reference.md` and `REVIEW-auth-review-inline.md`); auto-suffix on collision applies per file. Single-pass runs continue to emit `REVIEW-<slug>.md` with no mode suffix.
- `<cwd>/.multi-review/` (per-project, gitignored on first use)
  - `prompts/<name>.yaml` — persistent user-authored prompt files.
  - `prompts/.tmp/<id>.yaml` — ephemeral build-prompt drafts.
  - `pending/<pair-id>/meta.yaml` — pending-pair metadata.
  - `pending/<pair-id>/.status.lock` — ephemeral O_EXCL sentinel for atomic state transitions (see §8.6); present only during a transition.
  - `pending/<pair-id>/files/` — snapshot copies (only when `mode: both` AND `if_drift != ignore`).
  - `sessions/<run-id>/` — per-run working dir (per-reviewer outputs, prompt-as-sent, state files; pass-1 staged REVIEW.md during paired runs). Renamed from `runs/` to disambiguate from the central `runs/` namespace.
  - `pending-harvest/<run-id>.json` — fallback for harvest rows when central log write is denied.
- **Central state location** (resolved at setup time, requires session perm to write)
  - Resolution order: (1) if running from a multi-review dev checkout, use `<repo>/runs/`; (2) else `$XDG_DATA_HOME/multi-review/` (Linux default `~/.local/share/multi-review/`); (3) macOS default `~/Library/Application Support/multi-review/`. Recorded in `~/.claude/skills/multi-review/config.json` at setup; SKILL.md reads from there. No hardcoded `~/kramtime/...` path.
  - Contents at resolved path:
    - `runs.jsonl` — append-only harvest log.
    - `reports/<project>-<date>-<pair-id>.md` — auto-generated paired-run reports (format C).
    - `notes/<topic>.md` — hand-written cumulative narrative notes.
    - `notes/legacy/<original-name>.md` — pre-schema-stabilisation sidecars; excluded from EXPERIMENTS.md auto-stitching.

### 4.3 Install model

One-time: `python -m multi_review.cli.setup` (or `uv run python -m multi_review.cli.setup`). `--dev` mode symlinks `skills/` and `agents/` into `~/.claude/` instead of copying — removes the "re-run setup after every edit" pain when iterating on the skill itself.

Actions, all idempotent:
1. Copy (or symlink, `--dev`) `skills/multi-review/` → `~/.claude/skills/multi-review/`. The build-agent template embeds a `## Summary` heading contract clause regenerated from the canonical `SUMMARY_HEADING_CONTRACT` constant in `multi_review.core.prompt` (single source of truth — agent `.md` and `prepare.py` both pull from this constant; setup regenerates agent `.md` from template at install time so the two never drift).
2. Copy (or symlink, `--dev`) `agents/*.md` → `~/.claude/agents/`.
3. Symlink `multi_review.cli.*` entry points into `~/.local/bin/` (or rely on `uv run` paths from SKILL.md, whichever proves cleaner at implementation time).
4. Resolve central state path per §4.2 resolution order; write to `~/.claude/skills/multi-review/config.json`. Create `<resolved>/reports/` and `<resolved>/notes/legacy/` if absent.
5. **Permission allowlist hint.** Print a copy-pastable snippet showing the `~/.claude/settings.local.json` entry that allowlists the resolved `runs.jsonl` path (so the user isn't perm-prompted on every harvest row write). Optionally offer to write it directly. If declined, document: per-run perm prompts are the cost of opting out.
6. If historical sidecars detected, prompt to run `multi_review.cli.migrate_sidecars`.

## 5. Components

### 5.1 SKILL.md (skills/multi-review/SKILL.md)

Procedural markdown auto-loaded on `/multi-review` invocation. Pure instructions to the main Claude session — no helper logic embedded. Roughly 200 lines, structured as numbered procedure + decision graph.

Responsibilities:
1. Parse args (`/multi-review`, `/multi-review "text"`, `/multi-review --use-defaults "text"`, `/multi-review --prompt-files A.yaml,B.yaml`, `/multi-review --resume-pair <id>`, `/multi-review --report`, `/multi-review --list-reviewers`, etc.).
2. Dispatch `multi-review-build` Task subagent for prompt construction when needed.
3. For each validated prompt file: orchestrate snapshot (conditional), reviewer fanout (parallel Task + Bash), aggregation, harvest, optional cooldown, optional pass 2, optional Investigate flow, paired-report generation, EXPERIMENTS.md regen.
4. Handle perm prompts for central log writes.
5. Surface final summary to user (paths to outputs, fail/pass counts, fallback events).
6. **`--list-reviewers` diagnostic**: SKILL.md procedure that probes each known CLI via `shutil.which` + `<cli> --version`, prints availability + detected default models, and prints the host-detected backend (Task subagent for claude in v0.2). Replaces v0.1's `--list-reviewers` flag with a skill-local procedure.

### 5.2 Custom agents

| Agent | Model | Effort | Tools | Role |
|-------|-------|--------|-------|------|
| `multi-review-reviewer` | claude-opus-4-7 | xhigh | Read, Grep, Glob | Code review with adversarial scrutiny |
| `multi-review-synthesizer` | claude-opus-4-7 | high | Read | Read N reviews → Consensus Summary (Agreed Strengths, Agreed Concerns, Divergent Views) |
| `multi-review-build` | claude-sonnet-4-6 | high | Read, Write (scoped), AskUserQuestion, Glob | Author/validate YAML prompt files; interactive or autonomous from freeform seed. Write scoped by convention to `<cwd>/.multi-review/prompts/.tmp/<id>.yaml` (ephemeral) or `<cwd>/.multi-review/prompts/<name>.yaml` (persistent). The build-agent prompt instructs the agent to write only YAMLs under those paths; structural validation by `validate_prompt.py` (A3) catches malformed output upstream. |
| `multi-review-investigate` | claude-sonnet-4-6 | high | Read | Drift materiality classification: which pass-1 findings still apply after edits |

Effort levels pinned in agent definition frontmatter (definition-time, per `https://code.claude.com/docs/en/sub-agents.md`). No per-invocation override needed.

Dropped `Bash` from the `multi-review-reviewer` toolset: untrusted file contents flow through the reviewer prompt, and subagent tool grants are not per-operation — coupling `Bash` with `Read` in the same agent creates a local-code-execution risk if a review subject contains adversarial content. Read-only static analysis (Grep/Glob/Read) is sufficient for the v0.2 reviewer remit.

**Reviewer prompt contract — `## Summary` heading required.** Every reviewer agent prompt (both the `multi-review-reviewer` Task subagent and the subprocess-CLI reviewer system prompts emitted by `prepare.py`) must instruct the model to emit a `## Summary` section. This is a structural success sentinel: see §12 — output missing the heading is classified as failed (catches long permission-refusal text and Task-subagent failures that lack a non-zero exit code).

**Single source of truth.** The contract clause lives as a canonical Python string constant `SUMMARY_HEADING_CONTRACT` in `multi_review.core.prompt`. `prepare.py` imports it directly for subprocess reviewer prompts. The `multi-review-reviewer.md` agent definition embeds the same string at install time — `setup.py` regenerates the agent `.md` from a template that interpolates the constant. Editing the contract means editing the constant; the two materialisations stay in sync by construction. The matching regex used by the failure classifier (§12) is `^#{1,3}\s+(summary|executive summary)\b` case-insensitive — relaxed from a strict `## Summary` literal so subagents that emit `# Summary`, `### Summary`, or `## Executive Summary` still pass. Single-signal classifier is accepted internal-tool risk.

**Task-subagent reviewer telemetry: controlled degradation.** Claude Code's `Task` tool returns a structured result containing the subagent's final text plus optional metadata, but does not surface token-level usage in the form `spawn.py`'s JSONL adapters produce. For the claude reviewer (only), harvest records `telemetry_quality: degraded`, sets `input_tokens` / `output_tokens` / `cached_tokens` to `null`, captures `tool_calls` only if available from Task metadata, and records `wall_seconds` from skill-side timing. CLAUDE.md already flags claude inline telemetry as unreliable; this is a controlled degradation, not a new regression. Subprocess reviewers (gemini/codex/opencode) retain full JSONL-derived telemetry.

### 5.3 Helper CLIs (multi_review/cli/)

Each is a thin argparse wrapper around `multi_review.core/`. Invoked by SKILL.md via Bash. Read inputs from files/args; write outputs to files or stdout JSON.

- **`prepare.py`** — assemble prompt from YAML, write to tmp file.
- **`spawn.py`** — run one external CLI, stream JSONL through per-CLI adapter, write final review + state JSON.
- **`aggregate.py`** — build REVIEW.md from per-reviewer outputs + optional synthesis.
- **`harvest_row.py`** — append one JSONL row to central log (triggers session perm prompt). Also accepts `--flush-pending` to drain accumulated `<cwd>/.multi-review/pending-harvest/<run-id>.json` fallbacks into the central log (used after the user grants the allowlist mid-session, or as a periodic cleanup step).
- **`snapshot.py`** — subcommands create/diff/cleanup.
- **`report.py`** — regenerate EXPERIMENTS.md from central log + reports.
- **`validate_prompt.py`** — validate YAML against schema, fill defaults.
- **`migrate_sidecars.py`** — one-shot historical migration.
- **`pending.py`** — pending-pair state-machine: subcommands `init` / `read` / `transition` / `gc`. Transitions are atomic via an `O_EXCL` sentinel file (`.status.lock`) and `os.rename` (see §8.6). Invoked from §6.2 step 3, §8.3, §8.4, §8.5.
- **`cooldown_notify.py`** — fired by the background `sleep` script (§8.2). Reads pending meta via `pending.py read` (plain read, no lock needed); exits silently if status ≠ `awaiting-pass-2`; else dispatches platform notification (`notify-send` / `osascript` / `wsl-notify-send`). Status-gated so manual `--resume-pair` before the timer fires suppresses the late notification.
- **`setup.py`** — install/upgrade.

### 5.4 Prompt file format (YAML)

```yaml
prompt_format_version: 1
task: code                            # code | plan | security | generic | custom
files: ["src/auth.ts", "src/session.ts"]
context_files: ["docs/threat-model.md"]
custom_prompt: |                      # only when task == custom
  Focus on dependency ordering and rollback paths
mode: reference                       # inline | reference | both
synthesizer: claude                   # claude | gemini | codex | opencode | none
reviewers: ["claude", "gemini", "codex", "opencode"]
models:                               # primary model per reviewer
  claude: claude-opus-4-7
  gemini: gemini-3.1-pro
  codex: gpt-5
  opencode: openrouter/deepseek/deepseek-v4-pro
model_effort:                         # optional; silently ignored where unsupported
  codex: high
  # claude effort pinned in agent definition (xhigh)
fallback_models:                      # ordered chain on capacity failure; absent key = pin (no fallback)
  gemini: ["gemini-3.1-flash", "gemini-2.5-pro"]
delay: 1800                           # cooldown seconds (mode: both only)
delay_type: background                # foreground | background
if_drift: ignore                      # ignore | abort | ask (mode: both only). Default `ignore` for MVP — matches `core/promptfile.py:26`. Set `ask` (or `abort`) explicitly for paired runs that feed comparison stats (§7.1): under `ignore`, the harvest row records `drift_status: unchecked` and pair-level `comparison_eligible: false`. Default chosen as `ignore` because most ad-hoc paired runs are not load-bearing comparison data, and the `ask` flow demands a snapshot every time which is a foot-cannon for first-time users (decision recorded 2026-05-19).
output_dir: null                      # default: <cwd>/.multi-review/sessions/<auto-slug>/
save_as: null                         # promote ephemeral to persistent if set
harvest: true
```

**`fallback_models` default = pin.** An explicit chain is opt-in; v0.2 ships a built-in default `fallback_models.gemini: ["gemini-3.1-flash", "gemini-2.5-pro"]` applied only when the user provides no `models.gemini` override (i.e. defaults-on-defaults). To opt back into the default chain after pinning, omit the explicit-pin block entirely.

| `models.gemini`     | `fallback_models.gemini`  | Behavior                                                   |
|---------------------|---------------------------|------------------------------------------------------------|
| absent              | absent                    | default primary + built-in default chain                   |
| `X`                 | absent / `null` / `[]`    | pin to `X`, no fallback                                    |
| `X`                 | `[A, B]`                  | primary `X`, chain `[A, B]` on capacity-class failures     |

Same shape applies to every reviewer; only gemini ships a non-empty built-in default chain in v0.2.

**Server-side YAML validation (`validate_prompt.py`).** Cheap structural checks so a malformed prompt can't burn ~thousands of tokens × 4 reviewers downstream:
- Type and required-field checks: `task`, `files`, `mode`, `reviewers`, `synthesizer` present and well-typed.
- Enum validation: `task`, `mode`, `synthesizer`, every entry in `reviewers`, `delay_type`, `if_drift` against the closed value sets.
- `delay`: positive integer ≤ 86400 (24h sanity bound).
- `files` and `context_files`: every listed path must exist on disk.
- `models.<cli>` keys: must be members of the known-reviewer set.

The §8.2 background `sleep <delay> && python -m multi_review.cli.cooldown_notify --pair-id <id>` shell composition is safe because (a) `delay` is int-validated above, and (b) `pair_id` originates from `paths.generate_pair_id()` internally, not user-supplied YAML. Trust boundary is build-agent output validated by these structural checks; heavy regex enforcement is unnecessary at single-user scale.

**Snapshot consequence of context files.** Since `context_files` are inline-wrapped under `<file-NONCE>` tags in both `mode: inline` and `mode: reference` (they're framing material the model must see *before* any tool call), they are also included in the snapshot/diff set for paired runs (`if_drift != ignore`) — see §9.1. This kills a hidden-drift hole where context files (e.g. threat-model docs) could change between pass 1 and pass 2 unnoticed.

## 6. Data flow

### 6.1 Single-pass run

1. SKILL.md reads prompt YAML, validates via `validate_prompt.py`.
2. `prepare.py` writes assembled prompt to `<cwd>/.multi-review/sessions/<run-id>/prompt.txt`.
3. **Parallel fanout — explicit sequencing.** Task tool blocks the host turn until the subagent returns, so "fan out everything at once" requires care. The Claude Code mechanics this sequencing depends on (Task blocking + concurrent background Bash interleaving, `TaskGet` semantics) are gated by the §14 preflight procedure (`tests/manual/preflight-v0.2.md`, plan Task 0) — a preflight block-fail invalidates this step's design.
   1. **First**, in one Claude message, dispatch every non-claude reviewer via Bash `run_in_background` invoking `spawn.py` (returns immediately with a `task_id` per reviewer).
   2. **Then**, in the same message, dispatch the claude reviewer via the Task tool (this call blocks until the subagent returns).
   3. **Join barrier**: step 4 only begins once both (a) the Task call returns AND (b) every backgrounded `spawn.py` task reports completion (polled via `TaskGet`/`TaskOutput`). Total wall ≈ max(Task-claude, max(other reviewers)) — same parallelism as v0.1's asyncio fanout for the common case where claude is the slowest leg.
4. Per-reviewer outputs land in `<run-id>/reviews/<cli>.md`; state JSON in `<run-id>/state/<cli>.json`. (Pass-1 of a paired run: per §4.2, the final `REVIEW.md` is staged under `<run-id>/REVIEW.md` and only promoted to cwd root after the pair completes.)
5. If synthesizer != none AND ≥2 reviewers succeeded: dispatch synthesis (Task subagent if claude, else `spawn.py --task synthesize` subprocess).
6. `aggregate.py` writes final `<cwd>/REVIEW-<slug>.md` (auto-suffixed on collision; cwd root, not under `.multi-review/`, per §4.2). Pass 1 of a paired run instead stages to `.multi-review/sessions/<pass-1-run-id>/REVIEW.md`; both halves are then promoted to cwd-root mode-suffixed names (`REVIEW-<slug>-<mode>.md`) on pair completion (§6.2 step 4).
7. Request perm for central log write. `harvest_row.py` appends one JSONL row. **Perm-prompt fatigue mitigation**: setup.py (§4.3 step 5) prints a copy-pastable `~/.claude/settings.local.json` allowlist entry for the resolved `runs.jsonl` path. With the allowlist in place, this step is silent; without it, every run prompts. Documented trade-off — declining the allowlist means accepting per-run perm prompts.
8. `report.py` regenerates `EXPERIMENTS.md`.
9. Summary to user.

### 6.2 Paired-pass run (`mode: both`)

Pass order chosen from EXPERIMENTS.md ordering rule (`next_recommended_order`).

1. **Pass 1**: single-pass flow with the chosen mode. **Snapshot** (`snapshot.py create`) of input files + context files **only if `if_drift != ignore`** (context files in the snapshot set per §5.4 / §9.1). Pending meta records modes, timestamps, git ref, `notification_task_id` if cooldown.
2. **Pass-2 trigger** — branches on whether pass 1 burned the gemini fallback chain:
   - **Clean path** (no gemini fallback in pass 1): pass 2 fires **immediately in the same turn** after pass 1's join barrier resolves. No cooldown, no `awaiting-pass-2` state, no background task. `next_recommended_order` (§11.3) defaults to `reference` first when counters tie at zero.
   - **Fallback fired AND `delay_type: foreground`**: skill waits visibly in the same turn with countdown; pending meta still flips to `awaiting-pass-2` for the duration so the O_EXCL transition discipline in §8.6 applies to any concurrent `--resume-pair`.
   - **Fallback fired AND `delay_type: background`**: schedule background notification, pending meta `awaiting-pass-2`, skill exits cleanly with resume command. Pass 2 fires on `--resume-pair` or auto-fire after the user wakes the skill.
3. **Pass 2** (executes per the branch above):
   - Atomic transition via `pending.py transition --to resuming` (O_EXCL sentinel per §8.6). If current status is not `awaiting-pass-2`, helper refuses with `already resuming` / `already complete` / `expired` and pass 2 aborts. (Clean-path same-turn pass 2 skips this since meta never entered `awaiting-pass-2`.)
   - TaskStop the notification task if still alive.
   - If `if_drift != ignore`: run `snapshot.py diff`. Branch on result:
     - clean → proceed.
     - drifted + `abort` → emit warning, skip pass 2, mark pair aborted, continue to next prompt.
     - drifted + `ask` → AskUserQuestion proceed/abort/investigate. Investigate → `multi-review-investigate` Task subagent with diff + pass-1 REVIEW.md → verdict prose → AskUserQuestion again. **If the user chooses `proceed` after drift was detected, harvest sets `comparison_eligible: false` for that pair** regardless of fallback state — user explicitly accepted contamination, and we don't claim a clean comparison on top of accepted contamination. `proceed` is still a valid choice; it just disqualifies the pair from the inline-vs-reference signal.
   - If `if_drift == ignore`: no snapshot, no diff, proceed directly. Harvest will mark `drift_status: unchecked` and `comparison_eligible: false`.
   - Run pass 2 fanout.
4. **Post-paired**: in one rename step, promote both halves to cwd root with mode-suffixed names — pass-1 staged `.multi-review/sessions/<pass-1-run-id>/REVIEW.md` → `<cwd>/REVIEW-<slug>-<pass-1-mode>.md`, and the pass-2 final REVIEW → `<cwd>/REVIEW-<slug>-<pass-2-mode>.md` (per §4.2; auto-suffix on collision applies per file). `report.py --build-paired-report --pair-id` writes structured report to `<resolved central path>/reports/<project>-<date>-<pair-id>.md` (format C). `snapshot.py cleanup` removes pending dir. `report.py --regen` updates EXPERIMENTS.md.

### 6.3 Multi-prompt batch

Sequential. Per-prompt failures don't abort the batch. Batch-end: single perm prompt for harvest writes (batched), single EXPERIMENTS.md regen.

**`delay_type: background` is overridden to `foreground` inside a batch.** Background cooldown means "skill exits, user resumes later via `--resume-pair`" — that semantics is incompatible with "skill stays alive to run the next prompt in the batch". `validate_prompt.py` silently rewrites `delay_type: background → foreground` when the prompt is loaded as part of a batch (single-prompt invocations keep background semantics). The skill stays alive through each pair's cooldown then advances to the next prompt. **No batch-id, no orphan-queue state file, no `--resume-batch` flag** — keeps the state surface flat. Overnight-queue use case (the reason batch exists) is unaffected: the user wants the whole batch to run start-to-finish unattended, and foreground cooldown inside a batch matches that. Documented in §5.4 schema notes for `delay_type`.

### 6.4 Build flow

`/multi-review` or `/multi-review "text"` → SKILL.md dispatches `multi-review-build` Task subagent:
- Freeform text passed as seed (empty for bare invocation).
- Interactive (default): AskUserQuestion loop ending in "build another?".
- Autonomous (`--use-defaults`): subagent does shallow Glob/Read scan of cwd, infers defaults, writes YAML without asking.
- Ephemeral YAMLs land in `<cwd>/.multi-review/prompts/.tmp/<id>.yaml`.

SKILL.md continues with single/paired flow per generated file.

## 7. Comparison eligibility and telemetry

### 7.1 Eligibility (for inline-vs-reference comparison stats)

**Scope:** v0.2 ships only the **mechanical eligibility flags** below — they are a *necessary but not sufficient* gate. The downstream aggregation contract (which metric? what `n` threshold before a claim is load-bearing? how to normalise across reviewers and codebases?) is **out of scope for v0.2** and tracked as a deferred item in §14. Until then, cumulative comparative claims continue to live in hand-authored `runs/notes/<topic>.md` per CLAUDE.md's ≥5-paired-run rule. v0.2 does not claim its filter alone produces a comparison signal; it claims the filter cleanly excludes runs that *cannot* contribute.

- **Row-level** (each run): based **only on multi_review-measured fields** — `wall_seconds` non-null, `reviewers_succeeded ≥ 2`. CLI-reported usage telemetry is **never** an eligibility gate. (Prior-run quota cascade is captured downstream by the per-reviewer fallback rule below; no separate confound flag needed.)
- **Per-reviewer** (within a row): `comparison_eligible: false` for any reviewer that ran on a non-default fallback model (`fallback_hops > 0`).
- **Pair-level** (derived at report time): for paired comparison stats, a pair is `<reviewer>_comparable` only if **both** halves have that reviewer marked `comparison_eligible: true`. This catches the model-mismatch case (gemini-3.1-pro inline vs gemini-flash-lite reference is incomparable; the model difference dwarfs the mode difference).
- **`if_drift: ignore` pairs**: `comparison_eligible: false` at the pair level regardless of fallback state. User opted out of drift detection; we can't claim clean comparison.
- **`if_drift: ask` with proceed-after-drift**: `comparison_eligible: false` at the pair level. User explicitly accepted contamination (§6.2 step 3). Same reasoning as `ignore`.

### 7.2 Telemetry quality

Per-reviewer block in harvest:

```json
"usage_by_reviewer": {
  "gemini": {
    "input_tokens": 12345,
    "output_tokens": 6789,
    "tool_calls": 22,
    "telemetry_quality": "reliable",   // reliable | known-issues | degraded
    "comparison_eligible": true,
    "fallback_hops": 0,
    "final_model": "gemini-3.1-pro"
  },
  "claude": {
    "input_tokens": null,              // null for Task-subagent reviewers (no JSONL pipeline)
    "output_tokens": null,             // null for Task-subagent reviewers
    "cached_tokens": null,             // null for Task-subagent reviewers
    "tool_calls": 12,                  // captured from Task metadata when available, else null
    "telemetry_quality": "degraded",
    "comparison_eligible": true,
    "fallback_hops": 0,
    "final_model": "claude-opus-4-7"
  }
}
```

`telemetry_quality` is set by the adapter based on its current knowledge of upstream CLI reporting fidelity. Forward-only: when a CLI fixes their telemetry, the adapter bumps its declared quality and new rows reflect it; old rows keep their original flag. Comparisons that want token-level data filter on `telemetry_quality == "reliable"`.

### 7.3 Telemetry notes

Free-form `telemetry_notes` field per row for human-flagged anomalies (e.g., "claude reported 0 output_tokens but the review is non-empty"). Captured at run time; queryable later.

## 8. Cooldown

### 8.1 Trigger and purpose

Gemini fallback fired in pass 1 → cooldown for pass 2. Other reviewers don't have fallback chains today, so cooldown is gemini-specific in v0.2.

**Purpose:** Pass-1 gemini fallback indicates quota was hit, which makes it likely an immediate pass 2 would also fall back. Cooldown improves the odds that **pass 2 lands on the primary model so pass 2 produces a useful review** — *not* because waiting changes pass 1's eligibility. Pass 1's `<reviewer>_comparable: false` for gemini is already locked in once fallback fired; no amount of delay rescues it (the pair-level comparison eligibility on that reviewer is already lost, per §7.1). A pre-flight quota-proximity probe (avoid burning fallback in pass 1 in the first place) is the cleaner intervention and is deferred to §14.

### 8.2 Behaviour by `delay_type`

- **`background`** (default): spawn Bash `run_in_background` with:
  ```
  sleep <delay> && \
    python -m multi_review.cli.cooldown_notify --pair-id <id>
  ```
  `cooldown_notify` reads pending meta via `pending.py`, **exits silently if status ≠ `awaiting-pass-2`** (manual resume already happened), else fires platform notification. Skill exits cleanly. Print resume command. Pending meta records `notification_task_id`. The status guard is the load-bearing piece — a bare `sleep && notify-send` would fire spurious notifications after manual resume.
- **`foreground`**: skill waits visibly with countdown. Ctrl+C aborts pair.

### 8.3 Resume

`/multi-review --resume-pair <id>` (manual; works whether timer fired or not):

1. Atomic transition via `pending.py transition --to resuming` (O_EXCL sentinel, see §8.6). Helper refuses if current status ≠ `awaiting-pass-2`.
2. TaskStop the notification task if alive.
3. Run drift check (if applicable).
4. Continue pass 2.

### 8.4 Early resume + late notification

If user resumes manually before timer fires:
- Step 1's atomic transition flips status to `resuming` first. When the bg `sleep` finally wakes, `cooldown_notify` reads status, sees `≠ awaiting-pass-2`, and exits silently — no spurious notification.
- Step 2 kills the bg task as belt-and-braces.

### 8.5 Expired pairs

GC: pending dirs older than `PENDING_TTL_DAYS` (hardcoded 7 in v0.2; future config) are swept on next skill invocation via `pending.py gc`. `--resume-pair` against expired pair: warn, refuse by default, `--force` override. GC runs at skill start, not at end-of-run, so a long-running batch can't sweep a pair it's actively using.

### 8.6 Concurrency — pending-meta atomic transitions

Pending-meta state transitions (`init` → `awaiting-pass-2` → `resuming` → `complete` / `aborted`) are race-prone: two concurrent `--resume-pair <id>` invocations could both observe `awaiting-pass-2` on plain reads and both proceed.

**Property:** one transition wins; concurrent callers see a structured `already resuming` / `already complete` / `expired` error.

**Implementation (in `pending.py`):** an `O_EXCL` sentinel file (`.status.lock`) inside the pending dir provides mutual exclusion. `os.open(..., O_CREAT | O_EXCL | O_WRONLY)` succeeds for exactly one caller; losers receive `FileExistsError` and return `False` (no block-and-retry). The winner reads `meta.yaml`, validates the transition is legal, writes the new meta via `os.rename` (atomic on POSIX), and removes the sentinel.

`cooldown_notify` reads status with a plain read. If a manual resume has already flipped the status, `cooldown_notify` sees `≠ awaiting-pass-2` and exits silently on its next status check — same end behaviour, no lock needed for the read path.

All call sites — §6.2 step 3, §8.3, §8.4, §8.5 — go through `pending.py` subcommands. No ad-hoc meta writes elsewhere.

## 9. Drift handling

### 9.1 Detection

Snapshot at pass 1 → diff at pass 2.

**Snapshot set = input files + context files.** Both `files:` and `context_files:` from the prompt YAML are included unconditionally. Context files are inline-wrapped under `<file-NONCE>` tags in both modes (§5.4), so their content materially shapes the review even when not in `files:`; drift in a context file (threat-model doc, ADR, etc.) between pass 1 and pass 2 would otherwise leak as hidden divergence.

```
mode == both AND if_drift in {abort, ask}:
  snapshot at pass 1, diff at pass 2, full machinery
  snapshot covers: prompt.files + prompt.context_files

mode == both AND if_drift == ignore:
  no snapshot, no diff, no investigate subagent ever called
  pair flagged drift_status: "unchecked", comparison_eligible: false

mode != both:
  snapshot/drift never relevant
```

### 9.2 `if_drift: ask` Investigate flow

1. AskUserQuestion: proceed | abort | investigate.
2. **investigate**: Task `multi-review-investigate` subagent receives diff + pass-1 REVIEW.md. Subagent classifies each diff: cosmetic, addressing pass-1 finding X, or unrelated material change. Returns verdict prose: "Pass 1 review still applies / partially applies / does not apply; findings A,B addressed; finding C still stands; new concern in `session.ts:42` not covered."
3. AskUserQuestion again with verdict in context: proceed (with current files) | accept-pass-1-as-final | restart.

### 9.3 Limitations

- Hash check would be redundant given snapshot is the source of truth. Removed from design.
- Drift detection covers explicitly-submitted files only. Files the pass-1 reviewer happened to investigate via tools (reference mode) but didn't list as inputs are not tracked. Documented limitation; not addressed in v0.2.

## 10. Sidecar format C

### 10.1 Structure

`runs/reports/<project>-<date>-<pair-id>.md`:

```markdown
---
report_format_version: 1
project: paralife
date: 2026-05-05
pair_id: pair-20260505-0345-9f3a
runs: [run-20260505-0345, run-20260505-0512]
pair_type: paired                     # single | paired | multi
modes: { run-20260505-0345: reference, run-20260505-0512: inline }
reviewers_run: [claude, gemini, codex, opencode]
gemini_comparable: true               # derived from both halves
codex_comparable: true
claude_comparable: true
opencode_comparable: true
synthesizer: claude
fallback_events: []
confound: false
comparison_eligible: true
---

## Headline

(auto-drafted by post-run synthesis; human-editable)

## Mode-divergence observations

(auto-drafted: descriptive notes on what diverged between modes this run — findings unique to one mode, reviewer-ranking flips, anomalies. **Strictly descriptive. No "mode X is better" verdicts.**)

## Per-reviewer notes

(auto-drafted: per-reviewer behaviour, telemetry observations, anomalies)

## Open questions

(seeded blank for human use; cross-cutting observations belong in runs/notes/<topic>.md)
```

### 10.2 Auto-drafting

After paired run completes, SKILL.md invokes a post-run synthesis pass that reads both REVIEW.md outputs + per-reviewer state and produces three sections:

- **Headline** — descriptive one-paragraph summary of what happened this run (counts, fail/pass, fallback events).
- **Mode-divergence observations** — strictly descriptive notes: which findings appeared in one mode and not the other, where reviewer rankings flipped, anomalies (e.g. one reviewer hallucinated a fix as present). No evaluative claims about which mode is "better".
- **Per-reviewer notes** — per-reviewer behavioural and telemetry observations.

Same `multi-review-synthesizer` agent reused. The synthesis prompt **explicitly forbids load-bearing comparative claims** ("mode X outperformed mode Y", "reference is better for reviewer Z") at the single-run level. CLAUDE.md sets the bar at ≥5 paired runs across distinct codebases before such claims become load-bearing; the post-run report is n=1 by construction.

Open questions section left blank for user.

User reviews and commits. **Cumulative cross-pair comparative claims live in `runs/notes/<topic>.md`** — hand-authored prose, referencing reports by `pair_id`, written only after the ≥5-paired-run threshold is met for that codebase / reviewer / mode axis.

## 11. Migration

### 11.1 Historical sidecars → format C

`multi_review.cli.migrate_sidecars`, one-shot, **purely interactive** (no `--auto-apply`). **Sidecars are not 1:1 with pairs** — paralife-2026-04-29 covers 9 rows / multiple pairs + standalone runs; paralife-2026-05-03 has 2 same-day pairs; a naïve project+date key collides. Migration is row-driven, not sidecar-driven.

**Working with limited data.** `runs/runs.jsonl` has ~34 rows and the v1 schema has no `run_id`, no `pair_id`, no prompt-content hash. Row-grouping has to lean on the fields that *do* exist: `project`, `mode`, `started_at`, `finished_at`, `prompt_bytes`, and an identical-input-file-set test derived from `argv` (30 of 34 rows have `argv` populated; rows without `argv` cannot be paired and are surfaced for the user to classify manually). Given the small `n`, dropping `--auto-apply` entirely is cheaper than building robust auto-classification — the user clicks through ~34 rows once.

Step-by-step:

1. **Row-group first.** Tool reads `runs/runs.jsonl` and groups rows into **candidate pairs** by (`project`, identical input-file set from `argv`, mode-flip inline↔reference, both rows within a time window). **Window: `max(60 min, configured delay + 10 min slack)`** — the previous 30-minute default equalled the default cooldown and produced off-by-one drops of legitimate pairs. Pairs that hit the window boundary always surface for user confirmation rather than silently dropping. The row run-id (synthesised at migration time from `started_at` + `cwd`) is the primary key, not project+date.
2. **Sidecar matching is interactive.** For each `runs/notes/*.md`, tool shows: "this sidecar mentions dates X / projects Y; the row-grouper found these candidate pairs: …". User picks per-sidecar:
   - assign sidecar to pair P (single-pair narrative)
   - split sidecar across pairs P1 + P2 (multi-pair narrative — tool prompts for split criterion)
   - mark sidecar as legacy (moves to `<central-path>/notes/legacy/<original-name>.md`, untouched)
3. **Per-pair report emission.** For each candidate pair:
   - If all rows have full v1 telemetry (`prompt_bytes`, `output_bytes`, `usage` populated) → write format-C report at `<central-path>/reports/<project>-<date>-<pair-id>.md`. Prose from matched sidecars stitched under standard headings verbatim where it fits.
   - Else → classify pair as `legacy/incomplete-telemetry`, skip report emission, surface in summary.
4. **Row-rewrite scope is narrow.** Migration writes `pair_id` back onto every legacy row that the user confirmed as part of a pair (the *only* legacy-row rewrite). Unmatched rows keep `pair_id: null`. This is the bridge that lets `report.py` link harvest rows to migrated reports — without it, format-C reports would orphan from the harvest log. The rewrite is in-place on `runs.jsonl`; a `.bak` copy is taken first.

**Expected outcome.** Counts depend on user grouping decisions; the tool surfaces final counts (candidate pairs, reports emitted, legacy sidecars, incomplete-telemetry pairs) at the end of dry-run for the user to sanity-check before applying. No fixed "~7 / ~2" estimate — the JSONL doesn't support that level of pre-commitment.

### 11.2 Harvest schema bump

`HARVEST_SCHEMA_VERSION: 1 → 2`. **Mostly additive, with one rename**:
- v1's flat `usage` dict is renamed to `usage_by_reviewer` and restructured as a per-CLI nested object. `usage` is retained in v2 as a **read-only alias** (deprecated; consumers should migrate to `usage_by_reviewer`) emitted alongside `usage_by_reviewer` for one release cycle. Removing `usage` entirely is a v3 task. This keeps the migration honest: it's not "additive only" — it's "alias-preserving rename".

New fields (all **nullable**; legacy v1 rows backfill to `null`):
- `pair_id: string | null` — populated by §11.1 row-rewrite on matched legacy pairs; `null` on unmatched rows. Eligibility filter (§7.1) treats `null` pair_id as ineligible — pre-stabilisation rows stay out of comparison stats by design.
- `prompt_file: string | null`
- `prompt_format_version: int | null`
- `usage_by_reviewer.<cli>.telemetry_quality: string | null`
- `usage_by_reviewer.<cli>.comparison_eligible: bool | null`
- `usage_by_reviewer.<cli>.fallback_hops: int | null`
- `usage_by_reviewer.<cli>.final_model: string | null`
- `drift_status: string | null`
- `telemetry_notes: string | null`

**Nullability discipline.** Every v2-new field is explicitly nullable in the schema. Legacy v1 rows materialise `null` for all of them. §11.3's eligibility filter rejects rows where any of `comparison_eligible`, `fallback_hops`, or `final_model` is null for the relevant reviewer, which means **legacy rows cannot leak into trust counters** — they're cleanly excluded, not silently treated as `true` / `0` / `unknown`. This is intentional: pre-stabilisation rows simply don't contribute to the comparison signal.

**Claude reviewer null tokens are not a v2 migration artefact**, they are a structural property of Task-subagent telemetry (§5.2). `usage_by_reviewer.claude.input_tokens` / `output_tokens` / `cached_tokens` are nullable in v2 for the same reason they will be nullable in v3+. Consumers reading these fields must handle null; comparisons that need claude token data filter on `telemetry_quality == "reliable"` and will return zero rows until a future "telemetry reliable" path lands.

### 11.3 EXPERIMENTS.md regen post-migration

1. Backfill harvest schema.
2. Regenerate EXPERIMENTS.md from upgraded harvest + format-C reports.
3. New section: "Pre-schema-stabilisation narrative (excluded from comparison)" linking to `<central-path>/notes/legacy/*.md`.
4. `sessions_reference_first` / `sessions_inline_first` counters recomputed from `comparison_eligible: true` rows only. **Counters will reset to ~0 by design** — the eligibility filter strips most v0.1-era rows. This is intended: pre-stabilisation rows can't honestly contribute to the comparison. The EXPERIMENTS.md ordering rule re-stabilises after the first few new paired runs land under v0.2 and start accumulating eligible rows.
5. **`next_recommended_order` tie-break**: when both counters are 0 (post-reset reality, and every fresh codebase) or otherwise equal, the ordering rule returns `reference`. Stated explicitly to remove ambiguity at the cold-start boundary. Same rule applies at §6.2 step 2 for clean-path pair-2 dispatch.

### 11.4 CLI → skill breaking changes

`./multi_review.py file.ts` no longer works. The v0.1 entry script kept temporarily with a deprecation banner that prints upgrade instructions and exits 1. Removed entirely in v0.3.

All v0.1 CLI flags map to YAML prompt-file fields. README rewrites significantly.

**Pin-without-fallback semantics** — v0.2 preserves v0.1 least-surprise: setting `models.X: Y` pins X to Y with no fallback (matches v0.1 `--model X=Y` behaviour). Opting into a fallback chain is explicit (`fallback_models.X: [...]`). Absent `fallback_models.X` and `fallback_models.X: []` are equivalent. This is a **revised** §5.4 design — earlier drafts proposed inverting the default to "absent = use built-in chain", which would have silently changed v0.1 pin behaviour. Built-in defaults (e.g. the gemini fallback chain) apply only when the user has not supplied a `models.X` override.

### 11.5 Project-level `.multi-review/` gitignore

First skill invocation in a project:
1. Detect cwd `.gitignore`. Create if absent.
2. Append `.multi-review/` if not present. Idempotent.
3. `--no-gitignore` flag suppresses.

## 12. Error handling

| Failure | Behaviour |
|---------|-----------|
| Reviewer rc!=0 OR output < 50 bytes (subprocess reviewers only) | Failed section in REVIEW.md with stderr tail + partial output. Other reviewers unaffected. |
| Reviewer output missing `## Summary` heading (regex `^#{1,3}\s+(summary\|executive summary)\b`, case-insensitive) | Classify as failed; capture full output under `partial` field for inspection. Structural sentinel catches long permission-refusal text (which clears the 50-byte / rc=0 bar) and Task-subagent failures that have no exit code. **Applies to all reviewers** — subprocess (gemini/codex/opencode) and Task subagent (claude) alike — so the failure classifier is mode-independent. Reviewer prompt contract in §5.2 mandates the heading. Heading-depth and `Executive Summary` synonym are allowed to reduce false negatives. |
| Capacity fallback chain exhausted | Reviewer marked failed. Final attempt's stderr captured. Pair-level `<reviewer>_comparable: false`. |
| **Claude Task subagent fails** (no rc dimension applies) | Three failure conditions, any one of which classifies the reviewer as failed: (a) the Task tool itself raises (subagent crash, context overflow, dispatcher error); (b) returned text fails the `## Summary` regex; (c) returned text is < 50 bytes. Output bytes is still a useful sentinel even without rc — catches empty-string returns from a stalled subagent. Actionable error if context overflow. |
| <2 reviewers succeeded | Synthesis auto-skipped. REVIEW.md ships with available sections + reason note. |
| Synthesizer fails | REVIEW.md ships without consensus. Run still success if ≥2 reviewers passed. |
| Snapshot perm denied | Halt pass 1 before fanout. No partial state. Actionable error. |
| Harvest write perm denied | Row written to `<cwd>/.multi-review/pending-harvest/<run-id>.json`. EXPERIMENTS.md not regenerated. Later flush via `--flush-pending-harvest`. |
| Background sleep killed externally | No auto-recovery. Pending meta survives. User runs `--resume-pair` manually. |
| Resume against unknown/expired pair | Error lists known pending pair IDs OR refuses with `--force` override for expired. |
| Prompt YAML invalid | `validate_prompt.py` returns specific field errors. SKILL.md offers fill-via-build or abort. |
| Working tree dirty at snapshot | Snapshot captures current content. `git_dirty: true`, `git_head: <sha>` recorded. No special handling. |
| Skill invoked from non-Claude-Code host | Error message: requires Claude Code TUI for Task subagent dispatch. Suggest removing claude from reviewers or running from inside Claude Code. |

Batch-level failure isolation: one prompt failure doesn't abort the batch. Final summary lists per-prompt status. Exit code: `0` ≥1 prompt produced ≥1 successful reviewer, `1` all failed.

## 13. Testing

### 13.1 Layers

| Layer | Coverage | Mechanism |
|-------|----------|-----------|
| Core library (`multi_review/core/`) | 80%+ line | pytest unit tests against in-memory fixtures |
| Helper CLIs (`multi_review/cli/`) | 70%+ line | pytest integration: subprocess invocation, golden output comparison |
| Adapter JSONL parsing | 100% on parse logic | Replay captured JSONL fixtures per CLI per scenario (success, capacity-failure, auth-failure, empty, tool-burst) |
| Skill + agents | Manual smoke | Documented procedures in `tests/manual/<scenario>.md` |

### 13.2 CI scope

- Push: pytest unit + integration; ruff lint; mypy strict on `core/`.
- Release prep: manual smoke checklist (self-review, build, drift, migration, cooldown).
- Adapter fixtures re-captured during release prep to catch upstream schema drift.

### 13.3 Pre-existing gap

v0.1 has zero automated tests. v0.2 introduces a substantial uplift but takes a pragmatic approach: ship with core + adapter coverage (highest-value), backfill integration coverage as bugs surface. CLAUDE.md "Testing discipline" section codifies the rule: bugfixes in untested code carry their test.

## 14. Out of scope (deferred)

- **Preflight gate (required before implementation).** v0.2 implementation is blocked behind manual verification of four Claude Code mechanics — Task-subagent billing pool, Task-blocking + concurrent background Bash interleaving, `TaskStop` / `TaskGet` semantics, background Bash persistence across skill exit. Procedures and recorded verdicts live in `tests/manual/preflight-v0.2.md` (see plan Task 0). Until preflight passes, no code lands; a block-fail returns to brainstorming. Listed here for visibility, but it is **not** deferrable — it is the hard gate on the entire reframe.
- **Alternative claude backends** (subprocess `claude -p` revival, direct Anthropic API adapter). v0.2 ships the `ClaudeTaskAdapter` seam (§4.1: defined in `core/reviewers.py`; payload/parse only — SKILL.md owns Task dispatch). Alternative backends *own* dispatch (they shell out via `asyncio.subprocess` or hit the Anthropic SDK directly), so they don't slot into `ClaudeTaskAdapter`; they slot into the broader reviewer registry alongside the subprocess CLIs. Adding them is a config-shaped extension of the existing subprocess path, not a rewrite of the Task adapter. Anthropic flipping Task-subagent billing is judged low-probability (would cripple their own agent ecosystem); these alternatives remain belt-and-braces. *(Paired review C1 — Task adapter built; alternative backend impls remain deferred.)*
- **Aggregation contract for inline-vs-reference comparison** (metric, n-threshold, normalisation). v0.2 ships only mechanical eligibility flags (§7.1); cumulative claims continue to live in hand-authored `runs/notes/<topic>.md` per CLAUDE.md ≥5-paired-run rule. Building a defensible aggregator is its own milestone.
- **Task-subagent timeout regression.** v0.1 supported `--timeout N` for subprocess reviewers. Claude Code's `Task` tool exposes no equivalent `Task --timeout` knob, so the claude reviewer in v0.2 has no opt-in deadline. Documented regression from v0.1; revisit if Claude Code exposes a per-Task timeout.
- **Sandboxing of reference-mode Read tool surface.** Reference mode lets the reviewer Read arbitrary paths under the prompt's manifest. Real injection risk if a review subject contains adversarial content telling the reviewer to read elsewhere. Single-user internal tool reviewing user's own code; trust posture documented in spec. Path-allowlisting at the agent-tool level is the right long-term fix; out of scope at v0.2 scope.
- **Tool-call log tracking for hidden drift.** Reference-mode reviewers can Read files at tool-call time that aren't in the prompt manifest; those reads aren't snapshotted. §9 covers prompt files (input + context); untracked-tool-read drift remains a §9.3 documented limitation. Tracking would require capturing each Read call's path+content hash at fanout time — heavy infra, deferred. The §6.2 pass-1 REVIEW.md staging fix (§4.2) covers the highest-priority leakage channel cheaply.
- **Native Windows support.** POSIX-only via `os.open(O_EXCL)`. Native Windows untested; run from WSL.
- Multi-runtime support (Codex/Gemini/OpenCode as host).
- Per-invocation effort override on Task subagents (not documented; would unlock a `--effort` flag).
- Pre-flight gemini quota probe (avoid burning fallback in the first place).
- Spread-across-days limiter (`--max-runs-per-day N`).
- Snapshot-based strict pass 2 (pass 2 reviews snapshot content rather than live files; preserves comparison when drift detected). Methodologically cleaner than the current abort/ask default, but not a v0.2 goal.
- Sidecar restructure beyond format C (full option B split into mechanical + narrative file types).
- Synthesizer model A/B (opus-high vs sonnet-high). Tracked in BACKLOG.md.
- Full SKILL.md → CLI state-machine extraction. *(Paired review C4. §8.6 covers the one real race — pending-meta transitions — via `pending.py` + lockfile. Broader extraction is scope creep at v0.2 scale.)*
- Single `multi-review-cli` binary with subcommands (vs the current 9 helper CLIs). *(Paired review C6. Keep 9 for unit-test isolation; subprocess cold-start cost is acceptable at this tool's scale.)*
- Live `rich` 6Hz dashboard parity with v0.1. *(Paired review C6. Lost in the skill model since Bash `run_in_background` doesn't stream to the host turn. Replacement: per-reviewer Bash output streamed via `run_in_background` + skill-side status-poll text updates. No interactive dashboard in v0.2.)*
- cwd-mismatch guard for reference mode (already in BACKLOG.md; carries over to v0.2 release notes). *(Paired review C7.)*
- Within-mode variance baseline (statistical rigour on run-to-run noise within a single mode). *(Paired review extended C12. Not a v0.2 goal; CLAUDE.md's "≥5 paired runs before claims" rule is the working substitute.)*
- `model_effort.claude` silent-ignore vs hard-reject. *(Paired review CN5. Validator warns-but-accepts is sufficient; full reject is YAGNI given claude effort is pinned in agent definition.)*

## 15. Open implementation details

- Exact `effort` flag name for codex CLI (`--reasoning-effort` vs `--thinking-budget` vs other) — verify at implementation time against current `codex --help`.
- Whether `effort: max` is supported on opus and how it differs from `xhigh` — verify with test invocation.
- Whether `claude_code_subagent_effort` env var override exists (parallel to `CLAUDE_CODE_SUBAGENT_MODEL`) — documented uncertain.
- Best mechanism for `~/.local/bin/` symlinks vs `uv run` paths in SKILL.md Bash invocations.
- Notification mechanism cross-platform: `notify-send` (Linux), `osascript` (macOS), `wsl-notify-send` or PowerShell (Windows/WSL). Detect at setup.

## 16. Glossary

- **Pair / paired run**: a single review subject reviewed twice (once inline, once reference) for comparison.
- **Cooldown**: pause between pass 1 and pass 2 of a paired run to let gemini quota recover, so **pass 2 lands on the primary model and produces a useful review**. Does **not** retroactively rescue pass-1 comparison eligibility — once pass 1 fell back, that reviewer's pair-level `<reviewer>_comparable` is already false (§7.1, §8.1).
- **Drift**: file content changes between pass 1 and pass 2 of a paired run.
- **Comparison eligible**: a run or reviewer whose data validly contributes to inline-vs-reference statistics.
- **Telemetry quality**: per-reviewer self-declared accuracy of upstream CLI's reported usage metrics.
- **Format C**: structured YAML frontmatter + free-form body sidecar format (vs A: ad-hoc markdown, B: split mechanical + narrative).
- **Reference mode**: prompt shape where files are listed as paths in a manifest; reviewer reads them via its own tools. Contrasts with **inline mode** (file contents embedded in prompt).
