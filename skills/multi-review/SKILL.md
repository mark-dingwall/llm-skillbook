---
name: multi-review
description: Fan out a code review across claude/agy/codex/opencode, aggregate into REVIEW.md, optionally synthesize. Supports inline + reference modes including automated paired-pass runs with drift detection.
---

# multi-review

Orchestrate a multi-model code review.

## Invocation forms

- `/multi-review` — interactive prompt build
- `/multi-review "text"` — interactive build with seed
- `/multi-review --use-defaults "text"` — autonomous build, no prompts
- `/multi-review --prompt-files A.yaml,B.yaml` — run one or more pre-written prompt files
- `/multi-review --resume-pair <pair-id>` — resume pass 2 of a paired run
- `/multi-review --report` — regenerate EXPERIMENTS.md from harvest log

## Procedure

### Step 1 — Parse args

Extract: prompt-files list (or build), resume-pair id, `--report`, `--use-defaults` seed, `--list-reviewers`.

If `--list-reviewers`: probe each known CLI via `shutil.which <cli>` + `<cli> --version`; print availability, detected default models, and the host backend (Task subagent for claude in v0.2). Exit. (Replaces v0.1's flag with a skill-local procedure per spec §5.1.)

**Resolve central path:** read `~/.claude/skills/multi-review/config.json` `central_path` field. Stash it as `CENTRAL_PATH` for use by later steps. Fail with a setup hint if config.json absent.

### Step 2 — Build prompts (if needed)

Determine prompt files:
- If `--prompt-files` given: use them as-is.
- If `--resume-pair`: skip build; read pending meta.
- If `--report`: skip build.
- Otherwise: dispatch `multi-review-build` Task subagent:
  - With seed text and (interactive | autonomous) mode flag.
  - Receive list of YAML paths.

Validate every YAML via Bash:
```
uv run python -m multi_review.cli.validate_prompt <path>
```
Abort batch if any invalid (print specific field error to user).

### Step 3 — Sweep expired pending pairs

Before any per-prompt work, remove stale pending-pair dirs left behind by paired
runs that were abandoned or denied at the Step 9/10 flush (a clean paired run
self-cleans in Step 11; only interrupted ones linger). There is no dedicated GC
CLI — sweep inline, dropping anything older than 7 days so an in-flight
`--resume-pair` is never clobbered:
```
[ -d <cwd>/.multi-review/pending ] && \
  find <cwd>/.multi-review/pending -mindepth 1 -maxdepth 1 -type d -mtime +7 \
    -exec rm -rf {} + || true
```

### Step 4 — Per prompt: determine pass order + drift posture

For each validated prompt file:

a. Generate `pass1_run_id` (`uv run python -c "from multi_review.core.paths import generate_run_id; print(generate_run_id())"`).

b. If `mode == both`:
   - Generate `pair_id` (same helper, `generate_pair_id`).
   - Determine pass-1 mode from EXPERIMENTS.md `next_recommended_order` — if absent or stale, default to reference first.
   - If `if_drift != ignore`: plan a snapshot before pass 1 fanout.

c. If `mode != both`: single pass.

d. If `mode == both`: generate `pass2_run_id` (same helper). For `mode != both`, `pass2_run_id` is unused.

**Path constants used by Steps 5–10** (resolved per active pass — substitute `pass1_run_id` during pass 1, `pass2_run_id` during pass 2):

- `SESSION_DIR = <cwd>/.multi-review/sessions/<run_id>`
- `REVIEWS_DIR = <SESSION_DIR>/reviews`

### Step 5 — Pass 1 fanout

Prepare prompt (uses `SESSION_DIR` for `pass1_run_id`):
```
uv run python -m multi_review.cli.prepare --prompt-file <yaml> --out-dir <SESSION_DIR> --mode-override <pass1_mode>
```

If snapshotting (per spec §9.1 — input files AND context files):
```
uv run python -m multi_review.cli.snapshot create \
  --snapshot-dir <cwd>/.multi-review/pending/<pair_id>/files \
  --file <file1> --file <file2> ... \
  --context-file <ctx1> --context-file <ctx2> ...
```

**Fanout sequencing — Task tool blocks the host turn (spec §6.2 step 3).** In a single assistant message:
1. **First**, dispatch every non-claude reviewer via Bash `run_in_background` invoking `spawn.py` (returns immediately with a task id per reviewer):
   ```
   uv run python -m multi_review.cli.spawn --cli <cli> --prompt-file <prompt_path> \
     --out-dir <REVIEWS_DIR> --model <models[cli]> --effort <model_effort[cli]>
   ```
   Omit `--model` / `--effort` entirely when `models[cli]` / `model_effort[cli]` is unset — `spawn.py` defaults both to `None`; never pass an empty `--model ""` (would hand agy a blank model string). agy/codex/opencode ship unset by default.
2. **Then**, in the SAME message, dispatch the claude reviewer via Task — this call blocks until the subagent returns: `Task(subagent_type="multi-review-reviewer", prompt=<reviewer_task.md filled>)`.

   The agent definition is read-only (`tools: Read, Grep, Glob` — no Write per spec §5.2). Claude Code's Task tool returns the agent's final assistant message as a string; the host CAPTURES that string and persists it. Record wall time around the Task call as `<claude_duration>`. Then in a Bash heredoc write the captured text to `<REVIEWS_DIR>/claude.txt` and invoke the host-side writer:
   ```
   uv run python -m multi_review.cli.write_task_result \
     --cli claude --out-dir <REVIEWS_DIR> \
     --text-file <REVIEWS_DIR>/claude.txt \
     --duration-seconds <claude_duration> \
     --task-mode review --model claude-opus-4-7
   ```
   This produces `<REVIEWS_DIR>/claude.md` + `<REVIEWS_DIR>/claude.state.json` matching the shape `spawn.py` would emit. The Step 7 aggregator's `## Summary` heading check (M13) still applies and will demote a Task-subagent return that lacks the heading.

### Join barrier

Wait until all reviewers have finished. The mechanism depends on how each
was dispatched:

- **`claude` reviewer** (Task tool, `multi-review-reviewer` subagent):
  `TaskGet <task_id>` returns its status; poll until `status == "complete"`.
  Read the final state via the state.json the reviewer writes (or via
  `TaskOutput` for the agent's return text — but state.json is authoritative).
- **External reviewers** (`agy`, `codex`, `opencode`, dispatched via
  `Bash run_in_background` running `multi_review.cli.spawn`):
  `BashOutput <bash_id>` returns the latest stdout/stderr lines + an `exited`
  flag. Poll until `exited: true` for every external bash_id.

Don't mix the two: `TaskGet` against a Bash background id will fail; vice
versa. Track the dispatch type for each reviewer when you launch them.

Total wall ≈ max(claude Task, max(other reviewers)).

If `claude` is not in `reviewers`, skip the Task dispatch and the `mr-write-task-result` invocation; the join barrier reduces to BashOutput polling on each external bash_id.

### Step 6 — Synthesis

If `synthesizer != none` and ≥2 reviewers succeeded (check `.state.json` `ok` fields):

First, build the synthesis prompt (both branches):
```
uv run python -m multi_review.cli.build_synth_input \
  --state-dir <REVIEWS_DIR> \
  --out-prompt-file <SESSION_DIR>/synth-prompt.md \
  --out-nonce-file <SESSION_DIR>/synth-nonce.txt
```

- If `synthesizer == "claude"`: dispatch `multi-review-synthesizer` via Task with the synthesizer prompt at `<SESSION_DIR>/synth-prompt.md` and nonce from `<SESSION_DIR>/synth-nonce.txt`. Record wall time as `<synth_duration>`. The agent is read-only (`tools: Read`); CAPTURE the Task return value as a string, write it to `<SESSION_DIR>/synth.txt` via a Bash heredoc, then invoke:
  ```
  uv run python -m multi_review.cli.write_task_result \
    --cli claude --out-dir <SESSION_DIR> \
    --text-file <SESSION_DIR>/synth.txt \
    --duration-seconds <synth_duration> \
    --task-mode synthesize --model claude-opus-4-7
  ```
  This produces `<SESSION_DIR>/synth.txt` (overwriting the captured-text scratch with itself) and `<SESSION_DIR>/synth.state.json`.
- Else:
  ```
  uv run python -m multi_review.cli.spawn \
    --cli <synthesizer> \
    --prompt-file <SESSION_DIR>/synth-prompt.md \
    --task-mode synthesize \
    --input-nonce $(cat <SESSION_DIR>/synth-nonce.txt) \
    --out-dir <SESSION_DIR>/synth/
  ```
  Then extract the synthesis body to the canonical location Step 7 expects:
  ```
  cp <SESSION_DIR>/synth/synth.txt <SESSION_DIR>/synth.txt
  ```
  (`spawn --task-mode synthesize` writes `<out-dir>/synth.txt`; this copy normalises the path so both branches converge at `<SESSION_DIR>/synth.txt`.)
- Read synthesis text from `<SESSION_DIR>/synth.txt` for Step 7's `--synthesis-text-file`.

### Step 7 — Aggregate

**Failure classifier — `## Summary` heading check.** Before aggregation, scan each `<REVIEWS_DIR>/<cli>.md` against the canonical regex `^#{1,3}\s+(summary|executive summary)\b` (case-insensitive — see `SUMMARY_HEADING_CONTRACT` and spec §5.2). Any reviewer whose output fails to match is demoted to `ok: false` and its body moved to `partial` in the state JSON. This catches long permission-refusal text, stalled subagents, and Task-subagent returns that lack an exit code. Applies to all reviewers (subprocess and Task-subagent alike).

**Output path branches by mode** (spec §4.2):

- **Single-pass** (`mode != both`): write to cwd root.
  ```
  uv run python -m multi_review.cli.aggregate \
    --reviews-dir <REVIEWS_DIR> --output <cwd>/REVIEW-<slug>.md \
    --mode <pass1_mode> --task <task> \
    --synthesis-text-file <synth_output> \
    --pair-id <pair_id_or_omit> --prompt-file <yaml_path>
  ```
- **Paired** (both passes; `mode == both`): write to the staged session dir; Step 10 promotes to cwd root with mode-suffixed names.
  ```
  uv run python -m multi_review.cli.aggregate \
    --reviews-dir <REVIEWS_DIR> --output <SESSION_DIR>/REVIEW.md \
    --mode <passN_mode> --task <task> \
    --synthesis-text-file <synth_output> \
    --pair-id <pair_id> --prompt-file <yaml_path>
  ```

Report the actual output path to the user. Auto-suffix (`-2`, `-3`, …) applies only to cwd-root paths (single-pass here, paired after Step 10 promotion); staged session-dir paths are unique per `run_id` so cannot collide.

### Step 8 — Build harvest row + (deferred) write

```bash
uv run python -m multi_review.cli.write_harvest_row \
  --state-dir <SESSION_DIR>/reviews/ \
  --out-review <REVIEW_PATH> \
  --prompt-file <PROMPT_FILE> \
  --run-id <RUN_ID> \
  --log <CENTRAL_PATH>/runs.jsonl \
  --mode <MODE> \
  --project <PROJECT> \
  --task <TASK> \
  --drift-status <DRIFT_STATUS>
```

### Step 9 — Pass 2 + flush harvest rows (paired only)

If `mode != both`: nothing to do here; skip to Step 10. **Tie-break:** when EXPERIMENTS counters tie at 0 (post-reset reality + every fresh codebase), default pass-1 mode is `reference` (spec §11.3).

If `mode == both`:

a. If `if_drift != ignore`:
   - `mr-snapshot diff --snapshot-dir <pending/<pair_id>/files> --file <each input file> --context-file <each context file>`
   - Branch on `status`:
     - `clean` → proceed.
     - `drifted` + `if_drift == abort` → harvest row marks `drift_status: drifted`, skip pass 2, continue.
     - `drifted` + `if_drift == ask` → AskUserQuestion(proceed | abort | investigate). On investigate: dispatch `multi-review-investigate` with the diff + pass-1 REVIEW.md → re-ask with verdict.

b. Run pass 2 fanout, synthesis, aggregate — same as Steps 5–7 with `mode_override` = pass 2 mode and `pair-id` flag passed through, **but resolve `SESSION_DIR` and `REVIEWS_DIR` against `pass2_run_id`** (not the pass-1 id). All prepare / fanout / aggregate invocations during pass 2 use `<cwd>/.multi-review/sessions/<pass2_run_id>` so pass-2 artifacts never collide with pass-1's.

c. Build pass 2 harvest row (pending).

d. Flush both pass rows so the Step 10 report sees current data:

   - Tell user: "Writing this pair's 2 harvest rows to `<CENTRAL_PATH>/runs.jsonl` requires write permission. Continue?" (Silent if the user installed the allowlist entry from `setup.py` per spec §4.3 step 5.)
   - On approval:
     ```
     uv run python -m multi_review.cli.harvest_row --flush-pending --log <CENTRAL_PATH>/runs.jsonl
     ```
   - On denial: rows stay pending; skip Step 10's report build for this pair and print the resume command. Step 12's batched flush still runs at batch end as a backstop.

### Step 10 — Post-paired report

`<CENTRAL_PATH>` was resolved in Step 1 from `~/.claude/skills/multi-review/config.json`. Use it instead of any hardcoded `~/kramtime/...` path.

**Promote staged REVIEW.md files to cwd root with mode suffixes** (spec §4.2, §6.2 step 4). The promotion MUST go through `resolve_output_path` to honour the no-overwrite invariant — a raw `mv` clobbers any existing `REVIEW-<slug>-<mode>.md` at the destination. Run once per pass:

```
uv run python -c "
import os, sys, pathlib
from multi_review.core.aggregate import resolve_output_path
src = pathlib.Path(sys.argv[1])
dst = resolve_output_path(pathlib.Path(sys.argv[2]))
os.replace(src, dst)
print(dst)
" <SESSION_DIR>/REVIEW.md <cwd>/REVIEW-<slug>-<pass-mode>.md
```

The printed line is the actual final path (may be auto-suffixed `-2`, `-3`, …). Substitute `SESSION_DIR` with the per-pass session dir (pass 1 uses `pass1_run_id`, pass 2 uses `pass2_run_id`). Example: pass 1 mode `reference`, slug `auth-review` → `<cwd>/REVIEW-auth-review-reference.md` (or `-2` etc. if a prior run left a file there). Report both final paths to the user.

Then build the long-form paired report. Filename is fixed by the builder as `<project>-<date>-<pair-id>.md` (spec §4.2 / §10.1):

```
uv run python -m multi_review.cli.report build-paired \
  --log <CENTRAL_PATH>/runs.jsonl \
  --pair-id <pair_id> --out-dir <CENTRAL_PATH>/reports \
  --project <project> --date <YYYY-MM-DD> \
  --headline-file <synth_pass2_output_pair_section> \
  --mode-divergence-file ... \
  --per-reviewer-notes-file ...
```

The mode_divergence / per_reviewer_notes blocks come from a final synthesis pass scoped to the pair: dispatch `multi-review-synthesizer` with both REVIEW.md files in `<pass-1>` and `<pass-2>` blocks. The synthesizer prompt template forbids load-bearing comparative claims at single-run level (spec §10.2).

### Step 11 — Cleanup

`mr-snapshot cleanup --snapshot-dir <pending/<pair_id>/files>`
Remove `.multi-review/pending/<pair_id>/`.

Step 10 promoted both staged `REVIEW.md` files out of `.multi-review/sessions/<run_id>/`, so the session directories now contain only ephemeral artifacts (per-reviewer state/.md, synthesis input/output, prepared prompt). Cleaning or pruning these directories will not lose user-visible output.

### Step 12 — Batch end: harvest flush + regen

Flush any still-pending harvest rows (spec §5.3). For paired runs Step 9 already flushed each pair eagerly, so this pass is a no-op when only paired prompts ran; it still matters for single-pass prompts in a batch, or paired pairs whose Step 9 flush the user denied.

- Tell user: "Writing N harvest rows to `<CENTRAL_PATH>/runs.jsonl` requires write permission. Continue?" (Silent if user installed the allowlist entry from `setup.py` per spec §4.3 step 5.)
- On approval:
  ```
  uv run python -m multi_review.cli.harvest_row --flush-pending --log <CENTRAL_PATH>/runs.jsonl
  ```
  The flag scans `<cwd>/.multi-review/pending-harvest/*.json`, appends each row, and deletes each pending file only after successful write.
- On denial: pending files stay in place (spec §12 error-table behaviour); print the resume command.

After harvest:
```
uv run python -m multi_review.cli.report regen \
  --log <CENTRAL_PATH>/runs.jsonl \
  --reports-dir <CENTRAL_PATH>/reports \
  --output <CENTRAL_PATH>/EXPERIMENTS.md
```

### Step 13 — Final summary

Print per-prompt: REVIEW.md path, reviewer pass/fail counts, comparison eligibility (paired only).

## Notes on `mode: both` + `if_drift: ignore`

When both conditions hold:
- **Skip** snapshot creation in step 5.
- **Skip** drift diff and investigate logic in step 9a entirely.
- Harvest row records `drift_status: unchecked` and pair-level `comparison_eligible: false`.

The investigate subagent is never dispatched in this configuration.

## Notes on `claude` not in reviewers

If the user's prompt file has `reviewers` without `claude`:
- The reviewer fanout in step 5 dispatches no Task subagent; all reviewers are subprocess.
- The synthesizer path in step 6 still uses `multi-review-synthesizer` Task IF `synthesizer == "claude"`. Otherwise subprocess synthesis via `mr-spawn`.

This is supported; print a one-line acknowledgement: "Note: claude reviewer omitted; synthesis still via Task subagent."
