# Headless single-pass driver — design

**Status:** approved, pending implementation plan
**Requested by:** the `review-loop` skill (`~/kramtime/claude-skills/review-loop`), via handoff doc
**Repo state at design time:** main, `0.2.0a0`, 240 tests green

## Problem

`review-loop` needs to run multi-review's fanout under `bwrap` containment (a sealed worktree,
per-CLI writable scratch, agentic reviewers like `agy`/`pykrete` that write to disk unprompted).
Containment requires **one process to wrap** — child processes inherit the sandbox namespace.

The v0.2 skill can't be wrapped: it's ~13 steps of in-context LLM procedure, and its `claude`
reviewer runs as a Task subagent, not a subprocess — no namespace the caller sets up can contain
that. `multi_review.py` today is a 28-line deprecation stub that prints a banner and exits 1.

## Goal

Revive `multi_review.py` at the repo root as a headless, single-pass, no-LLM-in-the-loop driver:

```
uv run multi_review.py --prompt-file <yaml> --out-dir <dir> [--timeout <sec>]
```

- exit `0` = usable result (≥1 reviewer succeeded); non-zero = round failed
- writes `<out-dir>/REVIEW.md`
- `REVIEW.md` frontmatter carries `reviewers_failed` (already emitted by `aggregate`, unchanged)
- everything else (which CLIs ran, adapter quirks, dispatch mechanics) stays behind the interface

The `claude` reviewer runs as an ordinary `spawn.py` subprocess like every other reviewer —
`claude -p` billing reverted to subscription, so the Task-subagent workaround that motivated the
v0.2 split no longer has a reason to exist for this path. `core/reviewers.py` already wires
`"claude": {"base": ["claude", "-p"], ...}` and `ClaudeAdapter`; `spawn.py` has zero special-casing
for it. No core changes needed.

## Non-goals

Explicitly out of scope — these are what make the skill a skill, and `review-loop` doesn't need
them:

- pending-pair GC, pass-order/drift posture, harvest rows + batch flush, paired pass 2, drift
  report, promotion, cleanup, summary steps
- `mode: both` — driver takes `inline` or `reference` only, same restriction `prepare.py` already
  enforces
- any change to the skill's own Task-dispatch branches (they stay; the driver is a second, parallel
  entry point, not a replacement)

## Architecture

Single file, `multi_review.py` at repo root. Plain module — no PEP 723 `# /// script` header.
Confirmed live: `uv run multi_review.py` (or `uv run python -m ...`) from the project root already
resolves the local `multi_review` package with no extra config, so the script-isolation trick buys
nothing and would instead cut it off from the project env. Pure orchestration: no new core logic,
only calls into already-tested `multi_review.cli.*` / `multi_review.core.*` pieces. Estimated
120-180 lines.

### Flow

1. `load_promptfile(prompt_file)`. If `pf.mode == "both"`: print error, exit 2 — fail fast instead
   of letting `prepare.py` reject it later with a less specific message.
2. Call `prepare.main([...])` **in-process** (synchronous, single fast filesystem op) → writes
   `<out-dir>/prompt.txt`.
3. Fanout: for each `cli` in `pf.reviewers`, build argv for `spawn.py --cli <cli> --prompt-file
   <out-dir>/prompt.txt --out-dir <out-dir>/reviews/`, appending `--model`/`--effort` **only when**
   `pf.models[cli]` / `pf.model_effort[cli]` is set (never an empty-string token — same rule
   `SKILL.md` Step 5 already documents). Run all of them concurrently via `asyncio.gather` over
   `asyncio.create_subprocess_exec(sys.executable, "-m", "multi_review.cli.spawn", *argv)`, one OS
   subprocess per reviewer. `--timeout`, if the driver received one, is forwarded verbatim to every
   spawn call (spawn.py already owns per-call timeout enforcement; the driver adds no wall-clock
   logic of its own).
4. After all spawns complete, read each `<out-dir>/reviews/<cli>.state.json` and count reviewers
   with `ok == true`. This is the **raw** `spawn.py` success flag (rc + `FAILURE_MIN_BYTES` floor),
   not `aggregate.py`'s post-hoc `## Summary`-heading demotion — same source `SKILL.md` Step 6 uses
   for its own synthesis gate, so the driver stays consistent with the skill's semantics rather than
   inventing a second definition of "succeeded".
5. If `pf.synthesizer != "none"` and that count is `>= 2`: call `build_synth_input.main([...
   --out-prompt-file ... --out-nonce-file ...])` in-process (writes directly to files, so no
   stdout-JSON parsing needed), then one more `spawn.py --task-mode synthesize` subprocess call,
   with the same conditional `--model` construction against `pf.models[pf.synthesizer]`.
   Fewer than 2 successes, or `synthesizer == "none"`: skip synthesis entirely, no
   `--synthesis-text-file` passed to aggregate.
6. Call `aggregate.main([--reviews-dir <out-dir>/reviews --output <out-dir>/REVIEW.md --mode
   <pf.mode> --task <pf.task> [--synthesis-text-file ...] --prompt-file <prompt_file>])` in-process.
7. Exit `0` if the raw-`ok` count from step 4 is `>= 1`, else `1`.

### Directory layout under `--out-dir`

Mirrors the shape `SKILL.md`'s `SESSION_DIR` already uses, so nothing new to learn:

```
<out-dir>/
  prompt.txt            # from prepare
  reviews/
    <cli>.md
    <cli>.state.json
  synth/
    synth.txt            # only if synthesis ran
    synth.state.json
  REVIEW.md              # from aggregate
```

## Error handling

- `prepare` fails (e.g. `build_prompt` raises) → unrecoverable, exit 1, fanout never attempted.
- A single `spawn.py` subprocess crashes or emits unparseable stdout → log a warning to stderr,
  record that reviewer as failed, continue with the rest. Never aborts the whole run — same
  "partial failures still produce `REVIEW.md`" invariant the rest of the codebase already holds.
- Synthesis spawn fails → treated as absent; `aggregate` runs without `--synthesis-text-file`
  (already an optional flag on that CLI).
- `aggregate.main()` itself always returns 0 by contract (write errors raise `SystemExit`
  internally) — the driver doesn't second-guess it beyond confirming `REVIEW.md` exists afterward.
- Config errors (bad YAML, unknown reviewer/model, missing input files) surface as
  `promptfile.ValidationError` from `load_promptfile` — caught, printed to stderr, exit 2 (same
  convention as the `mode: both` rejection).

## Testing

New `tests/integration/test_multi_review_driver.py`. Only the `spawn.py` subprocess layer is
mocked (patch `asyncio.create_subprocess_exec` to return a fake process with canned stdout/rc) —
`prepare`, `build_synth_input`, and `aggregate` run for real against `tmp_path`, since they're pure
fast filesystem/string operations already covered elsewhere and mocking them would just test the
mocks.

Cases:

- conditional `--model`/`--effort` argv construction (present when set, absent — not empty-string —
  when unset)
- synthesis gate: 1 raw success → synthesis skipped; 2 raw successes → synthesis invoked
- exit code: 0 on ≥1 raw success, 1 on 0 successes
- `mode: both` rejected immediately, exit 2, no subprocess spawned
- malformed spawn stdout → that reviewer marked failed, run continues, `REVIEW.md` still written

## Open question carried from the handoff (resolved here)

Driver location: `multi_review.py` at repo root, not a new `mr-run` console script. The caller
(`review-loop`) already expects to point `bwrap` at this path; a console script would require the
caller to update its config for no benefit, since either way it's one string.

## Follow-up items noted, not part of this design

- `BACKLOG.md:1154`'s claim that `output_dir` overriding is wired is wrong — nothing reads
  `PromptFile.output_dir`. Worth a correction pass, unrelated to this driver.
- One live manual smoke of `claude -p` under `bwrap --clearenv` with `~/.claude` bound writable is
  still needed before `review-loop` commits to this shape — the test suite mocks all CLI dispatch,
  so 240 green says nothing about real sandboxed subprocess behavior. Tracked as a manual smoke
  step, not part of this implementation.
