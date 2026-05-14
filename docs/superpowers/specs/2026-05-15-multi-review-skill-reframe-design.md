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
~/kramtime/multi-review/
├── multi_review/
│   ├── core/                       # importable library
│   │   ├── prompt.py               # assembly (inline/reference modes, nonce tags)
│   │   ├── reviewers.py            # CLI_SPEC, adapter logic
│   │   ├── fanout.py               # subprocess spawn + JSONL stream parse
│   │   ├── harvest.py              # JSONL row append + telemetry quality flags
│   │   ├── snapshot.py             # snapshot dir mgmt + diff
│   │   ├── report.py               # EXPERIMENTS.md regeneration
│   │   └── pending.py              # pending-pair record read/write
│   └── cli/                        # skill-internal helper CLIs
│       ├── prepare.py
│       ├── spawn.py
│       ├── aggregate.py
│       ├── harvest_row.py
│       ├── snapshot.py
│       ├── report.py
│       ├── validate_prompt.py
│       ├── migrate_sidecars.py
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
├── runs/                           # central harvest + reports + notes
│   ├── runs.jsonl
│   ├── reports/                    # format-C paired-run reports
│   └── notes/
│       └── legacy/                 # pre-schema-stabilisation sidecars
├── BACKLOG.md
├── EXPERIMENTS.md                  # generated; do not edit by hand
└── README.md
```

### 4.2 State directories

- `<cwd>/.multi-review/` (per-project, gitignored on first use)
  - `prompts/<name>.yaml` — persistent user-authored prompt files.
  - `prompts/.tmp/<id>.yaml` — ephemeral build-prompt drafts.
  - `pending/<pair-id>/meta.yaml` — pending-pair metadata.
  - `pending/<pair-id>/files/` — snapshot copies (only when `mode: both` AND `if_drift != ignore`).
  - `runs/<run-id>/` — per-run working dir (per-reviewer outputs, prompt-as-sent, state files).
  - `pending-harvest/<run-id>.json` — fallback for harvest rows when central log write is denied.
  - `REVIEW-*.md` — final outputs at cwd root for visibility.
- `~/kramtime/multi-review/runs/` (central, requires session perm to write)
  - `runs.jsonl` — append-only harvest log.
  - `reports/<pair-id>.md` — auto-generated paired-run reports (format C).
  - `notes/<topic>.md` — hand-written cumulative narrative notes.
  - `notes/legacy/<original-name>.md` — pre-schema-stabilisation sidecars; excluded from EXPERIMENTS.md auto-stitching.

### 4.3 Install model

One-time: `python -m multi_review.cli.setup` (or `uv run python -m multi_review.cli.setup`).

Actions, all idempotent:
1. Copy `skills/multi-review/` → `~/.claude/skills/multi-review/`.
2. Copy `agents/*.md` → `~/.claude/agents/`.
3. Symlink `multi_review.cli.*` entry points into `~/.local/bin/` (or rely on `uv run` paths from SKILL.md, whichever proves cleaner at implementation time).
4. Create `~/kramtime/multi-review/runs/reports/` and `runs/notes/legacy/` if absent.
5. If historical sidecars detected, prompt to run `multi_review.cli.migrate_sidecars`.

## 5. Components

### 5.1 SKILL.md (skills/multi-review/SKILL.md)

Procedural markdown auto-loaded on `/multi-review` invocation. Pure instructions to the main Claude session — no helper logic embedded. Roughly 200 lines, structured as numbered procedure + decision graph.

Responsibilities:
1. Parse args (`/multi-review`, `/multi-review "text"`, `/multi-review --use-defaults "text"`, `/multi-review --prompt-files A.yaml,B.yaml`, `/multi-review --resume-pair <id>`, `/multi-review --report`, etc.).
2. Dispatch `multi-review-build` Task subagent for prompt construction when needed.
3. For each validated prompt file: orchestrate snapshot (conditional), reviewer fanout (parallel Task + Bash), aggregation, harvest, optional cooldown, optional pass 2, optional Investigate flow, paired-report generation, EXPERIMENTS.md regen.
4. Handle perm prompts for central log writes.
5. Surface final summary to user (paths to outputs, fail/pass counts, fallback events).

### 5.2 Custom agents

| Agent | Model | Effort | Tools | Role |
|-------|-------|--------|-------|------|
| `multi-review-reviewer` | claude-opus-4-7 | xhigh | Read, Grep, Glob, Bash (read-only) | Code review with adversarial scrutiny |
| `multi-review-synthesizer` | claude-opus-4-7 | high | Read | Read N reviews → Consensus Summary (Agreed Strengths, Agreed Concerns, Divergent Views) |
| `multi-review-build` | claude-sonnet-4-6 | high | Read, Write, AskUserQuestion, Glob | Author/validate YAML prompt files; interactive or autonomous from freeform seed |
| `multi-review-investigate` | claude-sonnet-4-6 | high | Read | Drift materiality classification: which pass-1 findings still apply after edits |

Effort levels pinned in agent definition frontmatter (definition-time, per `https://code.claude.com/docs/en/sub-agents.md`). No per-invocation override needed.

### 5.3 Helper CLIs (multi_review/cli/)

Each is a thin argparse wrapper around `multi_review.core/`. Invoked by SKILL.md via Bash. Read inputs from files/args; write outputs to files or stdout JSON.

- **`prepare.py`** — assemble prompt from YAML, write to tmp file.
- **`spawn.py`** — run one external CLI, stream JSONL through per-CLI adapter, write final review + state JSON.
- **`aggregate.py`** — build REVIEW.md from per-reviewer outputs + optional synthesis.
- **`harvest_row.py`** — append one JSONL row to central log (triggers session perm prompt).
- **`snapshot.py`** — subcommands create/diff/cleanup.
- **`report.py`** — regenerate EXPERIMENTS.md from central log + reports.
- **`validate_prompt.py`** — validate YAML against schema, fill defaults.
- **`migrate_sidecars.py`** — one-shot historical migration.
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
fallback_models:                      # ordered chain on capacity failure; [] = pin
  gemini: ["gemini-3.1-flash", "gemini-2.5-pro"]
delay: 1800                           # cooldown seconds (mode: both only)
delay_type: background                # foreground | background
if_drift: ignore                      # ignore | abort | ask (mode: both only)
output_dir: null                      # default: <cwd>/.multi-review/runs/<auto-slug>/
save_as: null                         # promote ephemeral to persistent if set
harvest: true
```

Pinning a model with no fallback: set `models.gemini: X` and `fallback_models.gemini: []`. Setting `models.gemini` alone does **not** disable fallback (v0.2 behaviour; differs from v0.1 CLI `--model` semantics).

## 6. Data flow

### 6.1 Single-pass run

1. SKILL.md reads prompt YAML, validates via `validate_prompt.py`.
2. `prepare.py` writes assembled prompt to `<cwd>/.multi-review/runs/<run-id>/prompt.txt`.
3. **Parallel fanout in one Claude message**: Task subagent for claude reviewer (if claude in `reviewers`) + Bash `run_in_background` for each non-claude reviewer via `spawn.py`.
4. Per-reviewer outputs land in `<run-id>/reviews/<cli>.md`; state JSON in `<run-id>/state/<cli>.json`.
5. If synthesizer != none AND ≥2 reviewers succeeded: dispatch synthesis (Task subagent if claude, else `spawn.py --task synthesize` subprocess).
6. `aggregate.py` writes final `<cwd>/.multi-review/REVIEW-<slug>.md` (auto-suffixed on collision).
7. Request perm for central log write. `harvest_row.py` appends one JSONL row.
8. `report.py` regenerates `EXPERIMENTS.md`.
9. Summary to user.

### 6.2 Paired-pass run (`mode: both`)

Pass order chosen from EXPERIMENTS.md ordering rule (`next_recommended_order`).

1. **Pass 1**: single-pass flow with the chosen mode. **Snapshot** (`snapshot.py create`) of input + context files **only if `if_drift != ignore`**. Pending meta records modes, timestamps, git ref, `notification_task_id` if cooldown.
2. **Cooldown check**: if pass 1 gemini fell back, schedule pass 2 with configured `delay`. `delay_type: background` spawns notification task; foreground waits visibly. Either way, pending meta status is `awaiting-pass-2`.
3. **Pass 2** (via `--resume-pair` or auto-fire after foreground wait):
   - If pending meta status != `awaiting-pass-2`: refuse (already resumed).
   - Atomically set status to `resuming`.
   - TaskStop the notification task if still alive.
   - If `if_drift != ignore`: run `snapshot.py diff`. Branch on result:
     - clean → proceed.
     - drifted + `abort` → emit warning, skip pass 2, mark pair aborted, continue to next prompt.
     - drifted + `ask` → AskUserQuestion proceed/abort/investigate. Investigate → `multi-review-investigate` Task subagent with diff + pass-1 REVIEW.md → verdict prose → AskUserQuestion again.
   - If `if_drift == ignore`: no snapshot, no diff, proceed directly. Harvest will mark `drift_status: unchecked` and `comparison_eligible: false`.
   - Run pass 2 fanout.
4. **Post-paired**: `report.py --build-paired-report --pair-id` writes structured report to `~/kramtime/multi-review/runs/reports/<pair-id>.md` (format C). `snapshot.py cleanup` removes pending dir. `report.py --regen` updates EXPERIMENTS.md.

### 6.3 Multi-prompt batch

Sequential. Per-prompt failures don't abort the batch. Batch-end: single perm prompt for harvest writes (batched), single EXPERIMENTS.md regen.

If any prompt has `delay_type: background` and pass 1 fell back, batch pauses after that prompt's pass 1; remaining prompts queue in pending state.

### 6.4 Build flow

`/multi-review` or `/multi-review "text"` → SKILL.md dispatches `multi-review-build` Task subagent:
- Freeform text passed as seed (empty for bare invocation).
- Interactive (default): AskUserQuestion loop ending in "build another?".
- Autonomous (`--use-defaults`): subagent does shallow Glob/Read scan of cwd, infers defaults, writes YAML without asking.
- Ephemeral YAMLs land in `<cwd>/.multi-review/prompts/.tmp/<id>.yaml`.

SKILL.md continues with single/paired flow per generated file.

## 7. Comparison eligibility and telemetry

### 7.1 Eligibility (for inline-vs-reference comparison stats)

- **Row-level** (each run): based **only on multi_review-measured fields** — `wall_seconds` non-null, `reviewers_succeeded ≥ 2`. CLI-reported usage telemetry is **never** an eligibility gate. (Prior-run quota cascade is captured downstream by the per-reviewer fallback rule below; no separate confound flag needed.)
- **Per-reviewer** (within a row): `comparison_eligible: false` for any reviewer that ran on a non-default fallback model (`fallback_hops > 0`).
- **Pair-level** (derived at report time): for paired comparison stats, a pair is `<reviewer>_comparable` only if **both** halves have that reviewer marked `comparison_eligible: true`. This catches the model-mismatch case (gemini-3.1-pro inline vs gemini-flash-lite reference is incomparable; the model difference dwarfs the mode difference).
- **`if_drift: ignore` pairs**: `comparison_eligible: false` at the pair level regardless of fallback state. User opted out of drift detection; we can't claim clean comparison.

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
  }
}
```

`telemetry_quality` is set by the adapter based on its current knowledge of upstream CLI reporting fidelity. Forward-only: when a CLI fixes their telemetry, the adapter bumps its declared quality and new rows reflect it; old rows keep their original flag. Comparisons that want token-level data filter on `telemetry_quality == "reliable"`.

### 7.3 Telemetry notes

Free-form `telemetry_notes` field per row for human-flagged anomalies (e.g., "claude reported 0 output_tokens but the review is non-empty"). Captured at run time; queryable later.

## 8. Cooldown

### 8.1 Trigger

Gemini fallback fired in pass 1 → cooldown for pass 2. Other reviewers don't have fallback chains today, so cooldown is gemini-specific in v0.2.

### 8.2 Behaviour by `delay_type`

- **`background`** (default): spawn Bash `run_in_background` with `sleep <delay> && notify-send 'multi-review pass 2 ready: <pair-id>'`. Skill exits cleanly. Print resume command. Pending meta records `notification_task_id`.
- **`foreground`**: skill waits visibly with countdown. Ctrl+C aborts pair.

### 8.3 Resume

`/multi-review --resume-pair <id>` (manual; works whether timer fired or not):

1. Read pending meta. Refuse if `status != awaiting-pass-2`.
2. Atomically set `status: resuming`.
3. TaskStop the notification task if alive.
4. Run drift check (if applicable).
5. Continue pass 2.

### 8.4 Early resume + late notification

If user resumes manually before timer fires:
- Step 2 prevents double-fire (the bg script's own status check on wakeup sees `status != awaiting-pass-2` and exits silently).
- Step 3 kills the bg task as belt-and-braces.

### 8.5 Expired pairs

GC: pending dirs older than `PENDING_TTL_DAYS` (hardcoded 7 in v0.2; future config) are swept on next skill invocation. `--resume-pair` against expired pair: warn, refuse by default, `--force` override. GC runs at skill start, not at end-of-run, so a long-running batch can't sweep a pair it's actively using.

## 9. Drift handling

### 9.1 Detection

Snapshot at pass 1 → diff at pass 2.

```
mode == both AND if_drift in {abort, ask}:
  snapshot at pass 1, diff at pass 2, full machinery

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

## Mode comparison

(auto-drafted table: verdict per reviewer per mode, mode-unique findings)

## Per-reviewer notes

(auto-drafted: per-reviewer behaviour, telemetry observations, anomalies)

## Open questions

(seeded blank for human use; cross-cutting observations belong in runs/notes/<topic>.md)
```

### 10.2 Auto-drafting

After paired run completes, SKILL.md invokes a post-run synthesis pass that reads both REVIEW.md outputs + per-reviewer state and produces the Headline + Mode comparison + Per-reviewer notes sections. Same `multi-review-synthesizer` agent reused. Open questions section left blank for user.

User reviews and commits. Cumulative narrative observations (cross-cutting patterns across multiple paired runs) go to `runs/notes/<topic>.md` as hand-written prose, referencing reports by `pair_id`.

## 11. Migration

### 11.1 Historical sidecars → format C

`multi_review.cli.migrate_sidecars`, one-shot, interactive by default:

1. For each `runs/notes/*.md`: cross-reference with `runs/runs.jsonl` by project + date.
2. **Clean paired** (one inline + one reference, full telemetry, no quota-burn confound): write `runs/reports/<project>-<date>-<pair-id>.md` in format C. Body content reorganised under standard headings; prose preserved verbatim where it fits.
3. **Multi-run / backfilled / exploratory**: move to `runs/notes/legacy/<original-name>.md`. Untouched. Excluded from EXPERIMENTS.md auto-stitching.

Per-file dry-run prompts for confirm/skip/manual-edit. `--auto-apply` skips prompts.

Expected outcome (counted from EXPERIMENTS.md): ~7 clean paired reports, ~2 legacy files.

### 11.2 Harvest schema bump

`HARVEST_SCHEMA_VERSION: 1 → 2`. Additive only. New fields:
- `pair_id: string | null`
- `prompt_file: string | null`
- `prompt_format_version: int`
- `usage_by_reviewer.<cli>.telemetry_quality`
- `usage_by_reviewer.<cli>.comparison_eligible`
- `usage_by_reviewer.<cli>.fallback_hops`
- `usage_by_reviewer.<cli>.final_model`
- `drift_status`
- `telemetry_notes`

Existing rows backfilled with null/default during migration. No row rewriting beyond null-fill.

### 11.3 EXPERIMENTS.md regen post-migration

1. Backfill harvest schema.
2. Regenerate EXPERIMENTS.md from upgraded harvest + format-C reports.
3. New section: "Pre-schema-stabilisation narrative (excluded from comparison)" linking to `runs/notes/legacy/*.md`.
4. `sessions_reference_first` / `sessions_inline_first` counters recomputed from `comparison_eligible: true` rows only.

### 11.4 CLI → skill breaking changes

`./multi_review.py file.ts` no longer works. The v0.1 entry script kept temporarily with a deprecation banner that prints upgrade instructions and exits 1. Removed entirely in v0.3.

All v0.1 CLI flags map to YAML prompt-file fields. README rewrites significantly.

`--model X=Y` v0.1 implicitly disabled fallback. v0.2 decouples: set `models.X: Y` and `fallback_models.X: []` to pin without fallback. Documented breaking change.

### 11.5 Project-level `.multi-review/` gitignore

First skill invocation in a project:
1. Detect cwd `.gitignore`. Create if absent.
2. Append `.multi-review/` if not present. Idempotent.
3. `--no-gitignore` flag suppresses.

## 12. Error handling

| Failure | Behaviour |
|---------|-----------|
| Reviewer rc!=0 OR output < 50 bytes | Failed section in REVIEW.md with stderr tail + partial output. Other reviewers unaffected. |
| Capacity fallback chain exhausted | Reviewer marked failed. Final attempt's stderr captured. Pair-level `<reviewer>_comparable: false`. |
| Claude Task subagent fails | Treated as reviewer failure. Actionable error if context overflow. |
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

- BYO-API-key escape hatch (direct Anthropic API adapter). Useful as a fallback if Anthropic later restricts the interactive-subagent pattern. Not needed today; the skill+Task pattern works under current policy.
- Multi-runtime support (Codex/Gemini/OpenCode as host).
- Per-invocation effort override on Task subagents (not documented; would unlock a `--effort` flag).
- Pre-flight gemini quota probe (avoid burning fallback in the first place).
- Spread-across-days limiter (`--max-runs-per-day N`).
- Snapshot-based strict pass 2 (pass 2 reviews snapshot content rather than live files; preserves comparison when drift detected).
- Sidecar restructure beyond format C (full option B split into mechanical + narrative file types).
- Synthesizer model A/B (opus-high vs sonnet-high). Tracked in BACKLOG.md.

## 15. Open implementation details

- Exact `effort` flag name for codex CLI (`--reasoning-effort` vs `--thinking-budget` vs other) — verify at implementation time against current `codex --help`.
- Whether `effort: max` is supported on opus and how it differs from `xhigh` — verify with test invocation.
- Whether `claude_code_subagent_effort` env var override exists (parallel to `CLAUDE_CODE_SUBAGENT_MODEL`) — documented uncertain.
- Best mechanism for `~/.local/bin/` symlinks vs `uv run` paths in SKILL.md Bash invocations.
- Notification mechanism cross-platform: `notify-send` (Linux), `osascript` (macOS), `wsl-notify-send` or PowerShell (Windows/WSL). Detect at setup.

## 16. Glossary

- **Pair / paired run**: a single review subject reviewed twice (once inline, once reference) for comparison.
- **Cooldown**: deliberate pause between paired-run passes to let gemini quota recover, preventing fallback in pass 2.
- **Drift**: file content changes between pass 1 and pass 2 of a paired run.
- **Comparison eligible**: a run or reviewer whose data validly contributes to inline-vs-reference statistics.
- **Telemetry quality**: per-reviewer self-declared accuracy of upstream CLI's reported usage metrics.
- **Format C**: structured YAML frontmatter + free-form body sidecar format (vs A: ad-hoc markdown, B: split mechanical + narrative).
- **Reference mode**: prompt shape where files are listed as paths in a manifest; reviewer reads them via its own tools. Contrasts with **inline mode** (file contents embedded in prompt).
