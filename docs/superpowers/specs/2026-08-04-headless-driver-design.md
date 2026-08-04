# Headless single-pass driver — design

**Status:** revised after round-1 multi-reviewer review (see Review History below), pending
implementation plan
**Requested by:** the `review-loop` skill (`~/kramtime/claude-skills/review-loop`), via handoff doc
**Repo state at design time:** branch `worktree-review-loop-compatibility`, 237 tests green — **6
commits behind `main`**, missing the agy `bypass_perms_flag` fix (`main:multi_review/core/reviewers.py:141,201-202`).
Every agy review fails on this branch as-is. **Rebase onto `main` before implementation begins.**

## Problem

`review-loop` needs to run multi-review's fanout under `bwrap` containment (a sealed worktree,
per-CLI writable scratch, agentic reviewers like `agy`/`pykrete` that write to disk unprompted).
Containment requires **one process to wrap** — child processes inherit the sandbox namespace.
Critically, the wrapped process's **working directory is the sealed tree under review**, not this
repo — that constraint shapes several decisions below.

The v0.2 skill can't be wrapped: it's ~13 steps of in-context LLM procedure, and its `claude`
reviewer runs as a Task subagent, not a subprocess — no namespace the caller sets up can contain
that. `multi_review.py` today is a 28-line deprecation stub that prints a banner and exits 1.

## Goal

Revive `multi_review.py` at the repo root as a headless, single-pass, no-LLM-in-the-loop driver:

```
uv run <absolute-path-to-repo>/multi_review.py --prompt-file <yaml> --out-dir <dir> [--timeout <sec>]
```

The caller invokes by **absolute path** to this repo's `multi_review.py`. This is not a new
constraint the caller has to accommodate — it's already how `uv run <script>.py` resolves: uv
discovers the project by walking up from the *script's own location*, not the invoking shell's
cwd (confirmed live: importing `multi_review` from the driver script succeeds regardless of
caller cwd). The caller's cwd is expected to be the sealed tree under review, not this repo.

- exit `0` = usable result: **≥1 reviewer's REVIEW.md section is not in `reviewers_failed`** —
  i.e. the same success definition `aggregate` applies to what actually lands in the file (see
  Exit code below; round-1 review found the naive "≥1 raw CLI exit success" definition can disagree
  with `reviewers_failed` and is not what "usable" should mean).
- writes `<out-dir>/REVIEW.md`
- `REVIEW.md` frontmatter carries `reviewers_failed` (via `core.aggregate.write_review_md`,
  unchanged)
- everything else (which CLIs ran, adapter quirks, dispatch mechanics) stays behind the interface

The `claude` reviewer runs through the same in-process fan-out as every other reviewer — `claude
-p` billing reverted to subscription, so the Task-subagent workaround that motivated the v0.2 split
no longer has a reason to exist for this path. `core/reviewers.py` already wires `"claude": {"base":
["claude", "-p"], ...}` and `ClaudeAdapter`. No core changes needed.

**Posture change worth stating plainly:** the skill's `claude` reviewer runs as a Task subagent
restricted to `Read`/`Grep`/`Glob` (spec §5.2). Through this driver, `claude -p` gets its full
default toolset — it becomes a fifth uncontained, agentic reviewer, same posture as `agy`/`pykrete`.
Add it to CLAUDE.md's "do not point at untrusted code" list alongside them. Whether headless
`claude -p` also auto-denies permission-gated tool calls the way `agy --print` does (CLAUDE.md's
documented agy behavior) is **unverified** — fold into the manual smoke below rather than assuming
either way, since if it does, reference mode would fail systematically for `claude` through this
driver.

## Non-goals

Explicitly out of scope — these are what make the skill a skill, and `review-loop` doesn't need
them:

- pending-pair GC, pass-order/drift posture, harvest rows + batch flush, paired pass 2, drift
  report, promotion, cleanup, summary steps
- `mode: both` — driver takes `inline` or `reference` only, same restriction `prepare.py` already
  enforces
- any change to the skill's own Task-dispatch branches (they stay; the driver is a second, parallel
  entry point, not a replacement)
- persisting per-reviewer `.md`/`.state.json` artifacts to disk — `REVIEW.md` already carries every
  reviewer's full body (see Architecture); the driver holds intermediate results as plain Python
  objects, not files, and doesn't need to write them out to do its job

## Architecture

Single file, `multi_review.py` at repo root. Plain module — no PEP 723 `# /// script` header (the
current tombstone has one; remove it, don't just omit it from a rewrite). Pure orchestration
calling directly into already-tested `multi_review.core.*` functions — **not** through the
`multi_review.cli.*` subprocess-shaped wrappers (`prepare.py`, `spawn.py`, `aggregate.py`,
`build_synth_input.py`). Estimated 150-200 lines.

### Why not shell out to `spawn.py` (reversed from the initial design)

The first draft of this spec dispatched one `spawn.py` subprocess per reviewer via
`asyncio.create_subprocess_exec(sys.executable, "-m", "multi_review.cli.spawn", ...)`. Round-1
review live-reproduced, independently, twice, that this breaks whenever the driver's cwd isn't the
multi-review repo root: `python -m` resolves module lookup against cwd, `multi_review` is not
`pip install`-ed into the venv (no `[build-system]` in `pyproject.toml`), and the caller's cwd is
*always* the sealed tree under review, never this repo. Every reviewer would fail with
`ModuleNotFoundError` on every real invocation — the one deployment this driver exists for.

That subprocess layer also turned out to be the root cause of two more round-1 Critical findings:
a reviewer whose `spawn.py` process died before writing its state file vanished from `REVIEW.md`
entirely (nothing files-based could reconstruct it), and the spec's own testing strategy (mock
`create_subprocess_exec`) couldn't produce the files later steps needed to read, making the tests
it described vacuous.

Fix: call `multi_review.core.fanout.run_reviewer()` — already `async`, already used by `spawn.py`
internally, already returns a plain `ReviewerResult` — directly, via `asyncio.gather`, in the
driver's own process. No subprocess, no cwd dependency, no file round-trip that a crashed task
could leave half-written. The *actual* reviewer CLIs (`agy`, `codex`, `claude`, …) remain real
subprocesses, same as always — `run_reviewer` spawns them itself. Only the orchestration layer
between "the driver" and "one call per reviewer" changes.

The driver still needs *some* visible progress signal for its caller (`review-loop` has no
dashboard to watch) — see "Progress output" below for the rudimentary stderr line this adds back.

### Flow

1. Parse `--prompt-file`, `--out-dir`, `--timeout` (argparse; its own usage errors exit 2 as
   standard).
2. `--out-dir` must not exist, or must exist and be empty. Otherwise: print error, exit 2. (Round-1
   finding: a reused out-dir lets `aggregate`'s auto-suffix silently write `REVIEW-2.md` while a
   stale `REVIEW.md` from a prior round remains — and the driver's own "does REVIEW.md exist" sanity
   check would pass on that stale file. Owning a guaranteed-fresh directory removes the whole
   failure class instead of adding overwrite-detection logic. `review-loop`, which runs rounds, is
   responsible for giving each round its own directory — the same guarantee `SKILL.md`'s
   per-`run_id` `SESSION_DIR` already provides today.)
3. `load_promptfile(prompt_file)`. Wrap in `try/except (ValidationError, yaml.YAMLError, TypeError,
   OSError)` — round-1 review confirmed live that malformed YAML raises `yaml.YAMLError` and an
   unknown/misspelled top-level key raises `TypeError` from `PromptFile(**raw)`, neither of which is
   `ValidationError`; both must be caught here rather than crashing uncaught. Any of these: print
   the exception message to stderr, exit 2. If `pf.mode == "both"`: print error, exit 2 (checked
   here explicitly rather than relying on `prepare.py`'s copy of this check, since that module is no
   longer called).
4. Deduplicate `pf.reviewers` preserving order (`list(dict.fromkeys(pf.reviewers))`).
   `promptfile.validate()` checks membership in `ALL_REVIEWERS` but not uniqueness — round-1 review
   confirmed `reviewers: [codex, codex]` passes validation today. Without dedup, two concurrent
   `run_reviewer` calls for the same CLI would be indistinguishable in the results list and would
   double-count toward the synthesis gate.
5. Build the prompt: normalize `pf.files`/`pf.context_files` against the prompt file's own
   directory (same rule `prepare.py`'s `_norm` helper already applies) and call
   `multi_review.core.prompt.build_prompt(task=pf.task, files=…, context_files=…,
   custom_prompt=pf.custom_prompt, mode=pf.mode, nonce=<fresh secrets.token_hex(4)>)` directly.
   Write the result to `<out-dir>/prompt.txt`. `build_prompt` can raise `SystemExit` on an unreadable
   file (`core/prompt.py:335-336,352`) — catch it, print the message, exit 1 (unrecoverable; no
   reviewer has been dispatched yet).
6. Fanout: for each `cli` in the deduped reviewer list, build a task:
   `run_reviewer(cli, prompt_text, model=pf.models.get(cli), timeout=timeout, state=ReviewerState(cli=cli,
   adapter=make_adapter(cli)), prompt_path=<out-dir>/prompt.txt)`. `model=None` when
   `pf.models` has no entry for that CLI — `run_reviewer`/`build_command` already treat `None` as
   "no flag", so no conditional-token construction is needed at this layer (that construction lived
   in `spawn.py`'s argv building, which no longer applies). `pf.model_effort` is **not forwarded** —
   `run_reviewer` takes no effort parameter, matching `spawn.py`'s own `--effort` being a documented
   no-op today (`spawn.py:11-12,58-62`); note this rather than silently dropping a field the prompt
   schema still accepts.

   Run all tasks concurrently via `asyncio.gather(..., return_exceptions=True)`. `run_reviewer` is
   already defensive (a `build_command` `ValueError`, e.g. missing `$PYKRETE_CONFIG`, is caught
   internally and returns a failed `ReviewerResult`, never raises) — `return_exceptions=True` is a
   second line of defense so that if a *genuinely* unexpected exception still escapes one task, it
   can't take down `gather` and silently drop every other reviewer's results. Any task result that
   is an `Exception` instead of a `ReviewerResult`: synthesize `ReviewerResult(cli=cli, ok=False,
   text="", stderr_tail=f"driver: reviewer crashed: {exc}", usage=Usage(), elapsed=0.0,
   error=str(exc))` in its place. This is what closes round-1's "reviewer vanishes from
   `reviewers_failed` if its process dies early" finding — there is no file to fail to write
   anymore, only a Python object that's either the real result or an explicit stand-in for one.

   **Progress output:** after each task completes, print one line to stderr:
   `f"[multi_review] {cli}: {'ok' if result.ok else 'failed'} ({result.elapsed:.1f}s)"`. Rudimentary
   — no dashboard, no rich.Live — but gives `review-loop` visibility into what's happening without
   parsing driver stdout, which stays reserved for nothing in particular (the driver prints no
   machine-readable summary to stdout; its contract is the exit code plus `<out-dir>/REVIEW.md`).
7. For each result, compute `ok, note = classify_review_ok(result.ok, result.text)` — the same
   `## Summary`-heading-aware classifier `aggregate.py` applies, imported directly from
   `core.prompt`. Build a new list of `ReviewerResult`s with `ok` replaced by this classified value
   (append `note` to `stderr_tail` when present, same as `cli/aggregate.py` does). **This
   classified list — not the raw fanout results — is the single source of truth for both the exit
   code (step 10) and what `write_review_md` renders as `reviewers_succeeded`/`reviewers_failed`.**
   Round-1 review found the original design's exit code used *raw* `ok` (rc + byte-floor only,
   pre-Summary-heading-check) while `REVIEW.md`'s own frontmatter used the classified value — so the
   driver could exit 0 while every single reviewer section in the file it just wrote was marked
   failed. Computing both from the same classified list removes that gap by construction.
8. Synthesis gate: separately from step 7's classified list, count reviewers with **raw** `result.ok
   == True` (pre-classification) among the original fanout results. If `pf.synthesizer != "none"`
   and that raw count is `>= 2`: call `build_synthesis_input(fanout_results)` (from
   `core.synthesis`, operates on `r.ok` — i.e. still raw, matching `SKILL.md` Step 6's own gate,
   which also reads raw `state.json` `ok` before any Summary-heading check) → `(body, nonce)`. Then
   `await run_synthesis(pf.synthesizer, body, nonce, model=pf.models.get(pf.synthesizer),
   timeout=timeout)` → `(ok, text, err, suggested, attempts)`. Print a progress line
   (`f"[multi_review] synthesis ({pf.synthesizer}): {'ok' if ok else 'failed'}"`). If `ok`:
   `synthesis_text = text`; otherwise `synthesis_text = None` (treated as absent — same as
   `synthesizer == "none"` or the `<2` case).

   This is a deliberate, and now explicit, divergence: the synthesis *gate* uses the raw definition
   (matching the skill), the exit code and `REVIEW.md` contents use the classified definition. They
   answer different questions — "is there enough raw material to synthesize from" vs. "did the
   round actually produce anything the caller can trust" — and round-1 review confirmed conflating
   them was the bug, not the two-definitions design itself.
9. `write_review_md(path=<out-dir>/REVIEW.md, results=<classified list from step 7>,
   synthesis_text=synthesis_text, mode=pf.mode, task=pf.task, reviewers_attempted=<deduped reviewer
   list from step 4>, prompt_file=str(prompt_file))` — called directly from `core.aggregate`, no
   `resolve_output_path` indirection needed (step 2 already guaranteed `<out-dir>` is fresh, so no
   collision is possible; the auto-suffix behavior that indirection exists for cannot trigger here).
10. Exit `0` if the classified-`ok` count from step 7 is `>= 1`, else `1`.

### Directory layout under `--out-dir`

```
<out-dir>/
  prompt.txt   # from build_prompt, step 5
  REVIEW.md    # from write_review_md, step 9
```

No `reviews/` or `synth/` subdirectories — there are no per-reviewer files to hold, since fanout
and synthesis results are passed as in-memory objects directly into `write_review_md`.

## Error handling

Precise table, replacing the round-1 draft's incomplete one (round-1 review found several of its
claims — "config errors always raise `ValidationError`", "`aggregate.main()` always returns 0" —
factually wrong against the real exception surface):

| Failure | Where | Driver behavior |
|---|---|---|
| Bad `--prompt-file`/`--out-dir`/`--timeout` argv | argparse | exit 2 (argparse default) |
| `--out-dir` exists and is non-empty | step 2 | print error, exit 2 |
| Unreadable/missing YAML file | `path.read_text()` inside `load_promptfile` | `OSError` caught, exit 2 |
| Malformed YAML syntax | `yaml.safe_load` inside `load_promptfile` | `yaml.YAMLError` caught, exit 2 |
| Unknown/mistyped YAML field | `PromptFile(**raw)` inside `fill_defaults` | `TypeError` caught, exit 2 |
| Schema violation (bad enum, missing file, etc.) | `validate()` | `ValidationError` caught, exit 2 |
| `mode: both` | step 3 | exit 2 |
| Unreadable input/context file | `build_prompt` (step 5) | `SystemExit` caught, exit 1 — no reviewer dispatched |
| One reviewer's subprocess fails, times out, or crashes | `run_reviewer` (step 6) | that result's `ok=False`; others unaffected; never aborts the run |
| An exception somehow escapes `run_reviewer` anyway | `asyncio.gather(return_exceptions=True)` (step 6) | synthesized failed `ReviewerResult` for that CLI; others unaffected |
| Synthesis fails or `pf.synthesizer == "none"` or `<2` raw successes | step 8 | `synthesis_text=None`; `REVIEW.md` written without a Consensus Summary |
| `write_review_md` itself fails (e.g. disk full, read-only mount) | `core.aggregate.write_review_md` (step 9) | `OSError`/`SystemExit` propagates uncaught — this is the one failure mode with no fallback, since it's the write of the driver's entire output; exit code is whatever the interpreter gives an uncaught exception (1) |

"Partial failures still produce `REVIEW.md`" holds for every row except the last (nothing else can
prevent the write) — same invariant the rest of the codebase already holds.

## Testing

New `tests/unit/test_multi_review_driver.py` (unit-level, not integration — the round-1 draft's
integration test with a mocked subprocess layer is no longer applicable; there is no subprocess
layer for the driver's own orchestration to mock). Monkeypatch `run_reviewer` and `run_synthesis`
(both plain `async def` functions imported into the driver module) to return canned `ReviewerResult`
/ synthesis tuples — this is a standard unit-test mock, not the file-producing-side-effect problem
round-1 review found in the subprocess-mock design. `build_prompt`, `classify_review_ok`,
`build_synthesis_input`, and `write_review_md` run for real against `tmp_path`, since they're pure
fast functions already covered by existing unit tests and mocking them here would just test the
mocks.

Cases:

- dedup: `reviewers: [codex, codex, agy]` dispatches exactly 2 `run_reviewer` calls (codex, agy)
- conditional `model=` forwarding: present when `pf.models[cli]` is set, `None` when absent (no
  argv construction anymore — this is a direct kwarg, so the case reduces to a simple assertion on
  the call args)
- exit code is driven by the **classified** (post-`classify_review_ok`) success count, not raw
  `ok` — construct a case where raw `ok=True` but the review text lacks a `## Summary` heading, and
  assert exit 1 with that reviewer in `reviewers_failed`
- an exception raised inside a mocked `run_reviewer` call doesn't affect other reviewers' results
  and produces a synthesized failed `ReviewerResult` for that CLI, present (not vanished) in
  `reviewers_failed`
- synthesis gate: 1 raw success → `run_synthesis` not called; 2 raw successes → called
- synthesis gate uses **raw** `ok`, exit code uses **classified** `ok` — a case where these two
  counts disagree (e.g. 2 raw successes but only 1 classified) confirms synthesis still fires while
  the exit code still reflects the classified count
- synthesis failure (`ok=False` from `run_synthesis`) → `REVIEW.md` written without a synthesis
  section, exit code unaffected by the synthesis outcome
- `mode: both` → exit 2, `run_reviewer` never called
- `--out-dir` already exists and is non-empty → exit 2, `run_reviewer` never called
- malformed YAML / unknown top-level key → exit 2, not an uncaught traceback
- `build_prompt` raising (unreadable file) → exit 1, `run_reviewer` never called
- `--timeout` value is forwarded to every `run_reviewer` and `run_synthesis` call

## Manual smoke (before `review-loop` commits to this shape)

The test suite mocks all CLI dispatch, so a green suite says nothing about real subprocess
behavior. Two items, both already noted as needed, one item added by round-1 review:

1. `claude -p` running correctly under `bwrap --clearenv` with `~/.claude` bound writable.
2. Whether headless `claude -p` auto-denies permission-gated tool calls the way `agy --print` does
   (see the Goal section's posture-change note) — if so, reference mode systematically fails for
   `claude` through this driver and needs its own fix, not just a caveat.
3. WSL2: `--ro-bind /mnt/wsl` required in the `bwrap` invocation, or DNS breaks inside the sandbox —
   noted in the original handoff, repeated here since it's easy to lose.

## Open question carried from the handoff (resolved here)

Driver location: `multi_review.py` at repo root, not a new `mr-run` console script. The caller
(`review-loop`) already expects to point `bwrap` at this path; a console script would require the
caller to update its config for no benefit, since either way it's one string.

## Review history

- **Round 1** (4 reviewers: codex holistic breadth, adversarial, async/subprocess-dispatch focus,
  writing-plans-compatibility focus): surfaced the subprocess-dispatch cwd blocker (live-reproduced
  independently by 2 reviewers), the exit-code/`reviewers_failed` mismatch, the stale-`REVIEW.md`
  on out-dir reuse, the missing-`--input-nonce` synthesis bug, the vanishing-reviewer-on-crash gap,
  and the vacuous test-mock design. All addressed above by moving fanout in-process (eliminates the
  cwd blocker, the vanishing-reviewer gap, and the vacuous-mock problem as a side effect of the same
  change), unifying the exit-code/`reviewers_failed` source of truth, requiring a fresh `--out-dir`,
  and wiring the synthesis call's real argument list (moot as argv now that it's a direct call, but
  the equivalent gap — forgetting to pass `nonce` — is called out explicitly in step 8).

## Follow-up items noted, not part of this design

- `BACKLOG.md:1154` and `README.md:166,186` both claim `output_dir` overriding is wired. It isn't —
  nothing reads `PromptFile.output_dir`. Worth a correction pass, unrelated to this driver.
