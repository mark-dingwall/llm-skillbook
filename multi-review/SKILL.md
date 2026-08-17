---
name: multi-review
description: Fan out a code review across claude/agy/codex/opencode/pykrete/grok, aggregate into REVIEW.md, and optionally synthesize.
---

# multi-review

Orchestrate a multi-model code review.

## Invocation forms

- `/multi-review` — interactive prompt build
- `/multi-review "text"` — interactive build with seed
- `/multi-review --use-defaults "text"` — autonomous build, no prompts
- `/multi-review --prompt-files A.yaml,B.yaml` — run one or more pre-written prompt files

## Procedure

**Running Python:** `$SKILL_DIR` below means this skill's own directory (the
absolute path of the folder containing this `SKILL.md`) — substitute it literally
in each command. `$SKILL_DIR/scripts/py` runs the skill's Python with its shipped
project + lockfile, so commands work from any working directory (do not rely on a
shell variable persisting between commands).

### Step 1 — Parse args

Extract: prompt-files list (or build), `--use-defaults` seed, `--list-reviewers`.

If `--list-reviewers`: probe each of `claude, agy, codex, opencode, pykrete, grok` (i.e. `ALL_REVIEWERS`) via `shutil.which <cli>` + `<cli> --version`; print availability, detected default models, and the host backend (Task subagent for claude). Mark `grok` as **opt-in** in the output — it is probed but never auto-selected (`DEFAULT_REVIEWERS` omits it). Exit.

### Step 2 — Build prompts (if needed)

Determine prompt files:
- If `--prompt-files` given: use them as-is.
- Otherwise: dispatch `multi-review-build` Task subagent:
  - With seed text and (interactive | autonomous) mode flag.
  - Receive list of YAML paths.

Validate every YAML via Bash:
```
"$SKILL_DIR/scripts/py" -m multi_review.cli.validate_prompt <path>
```
Abort batch if any invalid (print specific field error to user).

Capture the `resolved` object from `validate_prompt`'s JSON output and treat it as the **sole** source of `reviewers`, `synthesizer`, `models`, and `task` for the rest of the run. Never derive a run set from `ALL_REVIEWERS`, from the `--list-reviewers` probe, or from what happens to be installed — those include opt-in reviewers (currently `grok`) that must not run unless named. Below, `resolved.<field>` always means this object's field.

### Step 4 — Generate run id

For each validated prompt file:

a. Generate `run_id` (`"$SKILL_DIR/scripts/py" -c "from multi_review.core.paths import generate_run_id; print(generate_run_id())"`).

**Path constants used by the remaining steps:**

- `SESSION_DIR = <cwd>/.multi-review/sessions/<run_id>`
- `REVIEWS_DIR = <SESSION_DIR>/reviews`

### Step 5 — Fanout

Prepare prompt:
```
"$SKILL_DIR/scripts/py" -m multi_review.cli.prepare --prompt-file <yaml> --out-dir <SESSION_DIR>
```

**Fanout sequencing — Task tool blocks the host turn (spec §6.2 step 3).** In a single assistant message:
1. **First**, dispatch every non-claude reviewer in `resolved.reviewers` via Bash `run_in_background` invoking `spawn.py` (returns immediately with a task id per reviewer). Dispatch exactly that set — not every installed reviewer, not every reviewer in `ALL_REVIEWERS`. Build argv by appending each optional flag ONLY when its value is set — `<MODEL_FLAG>` below is a conditional token, not a literal:
   - `<MODEL_FLAG>`  = `--model <resolved.models[cli]>`         if `resolved.models[cli]` is set, else **nothing** (no token at all)
   - `<TASK_FLAG>`   = `--task <resolved.task>`                 **always** (the prompt's task; `task` is required in every validated prompt YAML, and `build_command` drops it for CLIs with no `task_flag`)
   ```
   "$SKILL_DIR/scripts/py" -m multi_review.cli.spawn --cli <cli> --prompt-file <prompt_path> \
     --out-dir <REVIEWS_DIR> <MODEL_FLAG> <TASK_FLAG>
   ```
   An unset value emits NO token — never `--model ""` (a blank string would hand agy an empty model). `spawn.py` defaults both to `None`; agy/codex/opencode/pykrete/grok ship unset by default, so their command is just the base argv with neither flag.
2. **Then**, in the SAME message, dispatch the claude reviewer via Task — this call blocks until the subagent returns: `Task(subagent_type="multi-review-reviewer", prompt=<reviewer_task.md filled>)`.

   The agent definition is read-only (`tools: Read, Grep, Glob` — no Write per spec §5.2). Claude Code's Task tool returns the agent's final assistant message as a string; the host CAPTURES that string and persists it. Record wall time around the Task call as `<claude_duration>`. Then in a Bash heredoc write the captured text to `<REVIEWS_DIR>/claude.txt` and invoke the host-side writer:
   ```
   "$SKILL_DIR/scripts/py" -m multi_review.cli.write_task_result \
     --cli claude --out-dir <REVIEWS_DIR> \
     --text-file <REVIEWS_DIR>/claude.txt \
     --duration-seconds <claude_duration> \
     --task-mode review --model opus
   ```
   This produces `<REVIEWS_DIR>/claude.md` + `<REVIEWS_DIR>/claude.state.json` matching the shape `spawn.py` would emit. The Step 7 aggregator's `## Summary` heading check (M13) still applies and will demote a Task-subagent return that lacks the heading.

### Join barrier

Wait until all reviewers have finished. The mechanism depends on how each
was dispatched:

- **`claude` reviewer** (Task tool, `multi-review-reviewer` subagent): the
  Task call in Step 5 already returned synchronously, and the host immediately
  persisted that return value. Do not issue a follow-up polling call; use
  `<REVIEWS_DIR>/claude.state.json` as the authoritative state.
- **External reviewers** (whichever of `agy`, `codex`, `opencode`, `pykrete`,
  `grok` are in `resolved.reviewers`, dispatched via `Bash run_in_background`
  running `multi_review.cli.spawn`):
  `BashOutput <bash_id>` returns the latest stdout/stderr lines + an `exited`
  flag. Poll until `exited: true` for every external bash_id.

Use `BashOutput` only with external-reviewer Bash background ids. The Claude
review has no outstanding task id at this point because its synchronous return
was already captured in Step 5.

Total wall ≈ max(claude Task, max(other reviewers)).

If `claude` is not in `resolved.reviewers`, skip the Task dispatch and the `write_task_result` invocation; the join barrier reduces to BashOutput polling on each external bash_id.

### Step 6 — Synthesis

If `resolved.synthesizer != none` and ≥2 reviewers succeeded (check `.state.json` `ok` fields):

First, build the synthesis prompt (both branches):
```
"$SKILL_DIR/scripts/py" -m multi_review.cli.build_synth_input \
  --state-dir <REVIEWS_DIR> \
  --out-prompt-file <SESSION_DIR>/synth-prompt.md \
  --out-nonce-file <SESSION_DIR>/synth-nonce.txt
```

- If `resolved.synthesizer == "claude"`: dispatch `multi-review-synthesizer` via Task with the synthesizer prompt at `<SESSION_DIR>/synth-prompt.md` and nonce from `<SESSION_DIR>/synth-nonce.txt`. Record wall time as `<synth_duration>`. The agent is read-only (`tools: Read`); CAPTURE the Task return value as a string, write it to `<SESSION_DIR>/synth.txt` via a Bash heredoc, then invoke:
  ```
  "$SKILL_DIR/scripts/py" -m multi_review.cli.write_task_result \
    --cli claude --out-dir <SESSION_DIR> \
    --text-file <SESSION_DIR>/synth.txt \
    --duration-seconds <synth_duration> \
    --task-mode synthesize --model opus
  ```
  This produces `<SESSION_DIR>/synth.txt` (overwriting the captured-text scratch with itself) and `<SESSION_DIR>/synth.state.json`.
- Else: build argv with `<SYNTH_MODEL_FLAG>` = `--model <resolved.models[resolved.synthesizer]>` if `resolved.models[resolved.synthesizer]` is set, else **nothing** (no token at all) — conditional token, same construction as Step 5's `<MODEL_FLAG>`:
  ```
  "$SKILL_DIR/scripts/py" -m multi_review.cli.spawn \
    --cli <resolved.synthesizer> \
    --prompt-file <SESSION_DIR>/synth-prompt.md \
    --task-mode synthesize \
    --input-nonce $(cat <SESSION_DIR>/synth-nonce.txt) \
    --out-dir <SESSION_DIR>/synth/ <SYNTH_MODEL_FLAG>
  ```
  Then extract the synthesis body to the canonical location Step 7 expects:
  ```
  cp <SESSION_DIR>/synth/synth.txt <SESSION_DIR>/synth.txt
  ```
  (`spawn --task-mode synthesize` writes `<out-dir>/synth.txt`; this copy normalises the path so both branches converge at `<SESSION_DIR>/synth.txt`.)
- Read synthesis text from `<SESSION_DIR>/synth.txt` for Step 7's `--synthesis-text-file`.

### Step 7 — Aggregate

**Failure classifier — `## Summary` heading check.** Before aggregation, scan each `<REVIEWS_DIR>/<cli>.md` for a `Summary` or `Executive Summary` heading (case-insensitive; it may be preceded by narration). Any reviewer whose output fails this presence check is rendered as an effective failure; the raw state JSON remains unchanged. This catches long permission-refusal text, stalled subagents, and Task-subagent returns that lack an exit code. Applies to all reviewers (subprocess and Task-subagent alike).

Write to the cwd root:
```
"$SKILL_DIR/scripts/py" -m multi_review.cli.aggregate \
  --reviews-dir <REVIEWS_DIR> --output <cwd>/REVIEW-<slug>.md \
  --task <task> \
  --synthesis-text-file <synth_output> --prompt-file <yaml_path>
```

Report the actual output path to the user. Auto-suffix (`-2`, `-3`, …) applies to cwd-root paths.

(Steps 3, 8–12 removed in v0.3.0.)

### Step 13 — Final summary

Print per-prompt: REVIEW.md path, reviewer pass/fail counts.

## Notes on `claude` not in reviewers

If the user's prompt file has `resolved.reviewers` without `claude`:
- The reviewer fanout in step 5 dispatches no Task subagent; all reviewers are subprocess.
- The synthesizer path in step 6 still uses `multi-review-synthesizer` Task IF `resolved.synthesizer == "claude"`. Otherwise subprocess synthesis via `multi_review.cli.spawn`.

This is supported; print a one-line acknowledgement: "Note: claude reviewer omitted; synthesis still via Task subagent."
