# Headless single-pass driver — design

**Status:** revised after round-1 and round-2 multi-reviewer review (see Review history below),
pending implementation plan
**Requested by:** the `review-loop` skill (`~/kramtime/claude-skills/review-loop`), via handoff doc
**Repo state at design time:** branch `worktree-review-loop-compatibility`, 237 tests green — **6
commits behind `main`**, missing the agy `bypass_perms_flag` fix (`main:multi_review/core/reviewers.py:141,201-202`).
Every agy review fails on this branch as-is. **Rebase onto `main` before implementation begins.**

## Problem

`review-loop` needs to run multi-review's fanout under `bwrap` containment (a sealed worktree,
per-CLI writable scratch, agentic reviewers like `agy`/`pykrete` that write to disk unprompted).
Containment requires **one process to wrap** — child processes inherit the sandbox namespace.
Critically, the wrapped process's **working directory is the sealed tree under review**, not this
repo, and that tree may or may not contain its own `pyproject.toml` — both cases matter below.

The v0.2 skill can't be wrapped: it's ~13 steps of in-context LLM procedure, and its `claude`
reviewer runs as a Task subagent, not a subprocess — no namespace the caller sets up can contain
that. `multi_review.py` today is a 28-line deprecation stub that prints a banner and exits 1.

## Goal

Revive `multi_review.py` at the repo root as a headless, single-pass, no-LLM-in-the-loop driver:

```
uv run <absolute-path-to-repo>/multi_review.py --prompt-file <yaml> --out-dir <dir> [--timeout <sec>]
```

The caller invokes by **absolute path** to this repo's `multi_review.py`, cwd unconstrained (the
sealed tree under review). No `--project` flag, no other change to the caller's invocation. See
Architecture for why this now actually holds — round-2 review found the round-1 draft's claim about
*why* it holds was wrong, even though the conclusion (works from a foreign cwd) needed to be made
true by restoring a PEP 723 header, not just asserted.

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
- persisting per-reviewer `.md`/`.state.json` artifacts to disk. The driver holds intermediate
  results as plain Python objects, not files. **Correction from round-2 review:** this does *not*
  mean `REVIEW.md` carries every reviewer's full body regardless of outcome — `write_review_md`
  truncates failed/demoted reviewers' text to 1000 chars (`core/aggregate.py:141`), same as it
  always has for every caller, including the skill. This driver doesn't change that truncation or
  provide a separate on-disk copy to recover the untruncated text from. Accepted: matches existing
  behavior everywhere else `write_review_md` is used; not a regression this driver introduces.

## Architecture

Single file, `multi_review.py` at repo root. Pure orchestration calling directly into
already-tested `multi_review.core.*` functions — **not** through the `multi_review.cli.*`
subprocess-shaped wrappers (`prepare.py`, `spawn.py`, `aggregate.py`, `build_synth_input.py`).
Estimated 180-230 lines.

**Keeps a PEP 723 `# /// script` header**, declaring this repo's own runtime dependencies:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.7", "pyyaml>=6.0"]
# ///
```

This reverses the round-1 draft, which removed the header on the reasoning that `sys.path[0]` (the
script's own directory) already makes `import multi_review` resolve correctly regardless of caller
cwd — true, and unaffected either way by the header. What that reasoning missed, and round-2 review
live-reproduced: `sys.path[0]` only explains how the *local* `multi_review` package resolves. It says
nothing about *third-party* dependencies (`PyYAML`, `rich`) — those come from whichever Python
environment `uv run` builds, and `uv`'s **project discovery for that environment runs from the
invoking cwd**, not the script's location. From a foreign cwd with no `pyproject.toml` of its own,
`uv run <path>/multi_review.py` builds an environment with no declared dependencies at all;
`import yaml` inside `load_promptfile` fails immediately. Worse, from a foreign cwd that *does* have
its own `pyproject.toml` (plausible for the sealed tree under review, if it's itself a Python
project), `uv` adopts *that* project — still without `PyYAML`, and it writes `.venv/`/`uv.lock` into
the tree under review, which is exactly what `bwrap` containment exists to prevent.

A PEP 723 header sidesteps project discovery entirely — `uv run` builds an isolated, dependency-only
environment for the script itself, unaffected by cwd. Verified live (round-2 review) from a plain
foreign directory with no `pyproject.toml`: without the header, `import yaml` fails; with it, it
succeeds. `sys.path[0]` still makes the local `multi_review` package importable regardless — the two
mechanisms are independent and both needed.

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

**Why not `core.fanout.run_all_reviewers()`, which already does exactly this?** It exists
(`fanout.py:251-304`) and already wraps `run_reviewer` in a `gather` with its own cancellation
handling. It's not used here because it calls `run_reviewer` without `prompt_path`
(`fanout.py:267-274`) — fine for CLIs using `stdin` delivery, but agy's `argv_file` delivery mode
requires the on-disk prompt path and `build_command` raises `ValueError` without it
(`reviewers.py:184-185`). Since agy is default-on, using `run_all_reviewers` as-is would fail agy on
every run, recorded as an ordinary agy failure with no obvious cause. The driver hand-rolls a
comparably small `gather` instead, passing `prompt_path` explicitly, and borrows
`run_all_reviewers`'s cancellation-handling shape (see "Shutdown" below) rather than its exact code.

The driver still needs *some* visible progress signal for its caller (`review-loop` has no
dashboard to watch) — see "Progress output" in the Flow section below.

### Flow

1. Parse `--prompt-file`, `--out-dir`, `--timeout` (argparse; `--timeout` is `type=int,
   default=None` — matching the repo-wide "no default timeout" invariant; its own usage errors
   exit 2 as standard).
2. `--out-dir`: if it exists, it must be an empty directory, else print error and exit 2. If it
   doesn't exist, create it with `mkdir(parents=True)`. (Round-1 finding: a reused out-dir lets
   `aggregate`'s auto-suffix silently write `REVIEW-2.md` while a stale `REVIEW.md` from a prior
   round remains — and the driver's own "does REVIEW.md exist" sanity check would pass on that
   stale file. Owning a guaranteed-fresh directory removes the whole failure class instead of
   adding overwrite-detection logic. Round-2 review caught that the round-1 text required freshness
   but never actually created the directory for the normal, common case where it doesn't exist yet
   — fixed here. `review-loop`, which runs rounds, is responsible for giving each round its own
   directory — the same guarantee `SKILL.md`'s per-`run_id` `SESSION_DIR` already provides today.)
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
   Write the result to `<out-dir>/prompt.txt` (the directory is guaranteed to exist per step 2).
   `build_prompt` can raise `SystemExit` on an unreadable file (`core/prompt.py:335-336,352`) —
   catch it, print the message, exit 1 (unrecoverable; no reviewer has been dispatched yet).
6. Fanout. For each `cli` in the deduped reviewer list, wrap `run_reviewer` in a small coroutine
   that also reports progress:

   ```python
   async def _run_and_report(cli: str) -> ReviewerResult:
       result = await run_reviewer(
           cli, prompt_text,
           model=pf.models.get(cli), timeout=timeout,
           state=ReviewerState(cli=cli, adapter=make_adapter(cli)),
           prompt_path=out_dir / "prompt.txt",
       )
       print(f"[multi_review] {cli}: {'ok' if result.ok else 'failed'} "
             f"({result.elapsed:.1f}s) [raw]", file=sys.stderr, flush=True)
       return result
   ```

   `model=None` when `pf.models` has no entry for that CLI is correct as a call — but round-2 review
   found the round-1 draft's rationale wrong: `build_command` does **not** treat `model=None` as "no
   flag" universally. For CLIs with a configured `default_args` (e.g. `claude` → `["--model", "opus",
   "--effort", "xhigh"]`, `reviewers.py:202-205`), `None` falls through to that default rather than
   omitting the flag — same behavior `spawn.py` already has today, not a regression, just corrected
   here so the spec doesn't claim something false. `pf.model_effort` is **not forwarded** —
   `run_reviewer` takes no effort parameter, matching `spawn.py`'s own `--effort` being a documented
   no-op today (`spawn.py:11-12,58-62`).

   Run all the wrapped coroutines concurrently: `raw = await asyncio.gather(*(_run_and_report(cli)
   for cli in reviewers), return_exceptions=True)`. `run_reviewer` is already defensive for ordinary
   exceptions — a `build_command` `ValueError` (e.g. missing `$PYKRETE_CONFIG`) is caught internally
   and returns a failed `ReviewerResult` (`fanout.py:114-119`) — but it deliberately **re-raises**
   `asyncio.CancelledError` after cleaning up its child process (`fanout.py:200-202`), and
   `return_exceptions=True` collects `BaseException`s too, not just `Exception`s. **Check with `if
   not isinstance(item, ReviewerResult)`, not `if isinstance(item, Exception)`** — round-2 review
   found the latter misses a `CancelledError` (a `BaseException`, not an `Exception`), which would
   otherwise fall through to the "treat it as a real result" branch and crash on `.ok`/`.cli` at step
   7, defeating the exact protection this line exists to provide. For anything that isn't a
   `ReviewerResult`, synthesize `ReviewerResult(cli=cli, ok=False, text="", stderr_tail=f"driver:
   reviewer crashed: {item!r}", usage=Usage(), elapsed=0.0, error=str(item))` in its place, using
   `zip(reviewers, raw)` to recover which `cli` each position belongs to (`gather` preserves input
   order). Call the resulting list `raw_results` — every element guaranteed to be a `ReviewerResult`
   — and use that name, not "the original fanout results" or similar, in every step below that reads
   it. (Round-2 review found the round-1 draft's prose-only references to "the raw list" ambiguous
   enough that reading it as the pre-substitution `gather` return — which can contain bare
   exceptions — would crash `build_synthesis_input`'s `r.ok` access in step 8.)
7. Classify. For each result in `raw_results`, compute `ok, note = classify_review_ok(result.ok,
   result.text)` — the same `## Summary`-heading-aware classifier `aggregate.py` applies, imported
   directly from `core.prompt`. Build `classified_results` via `dataclasses.replace(r, ok=ok,
   error=(note or r.error), stderr_tail=(f"{r.stderr_tail}\n{note}" if note else r.stderr_tail))` —
   **`dataclasses.replace`, not in-place mutation** (`ReviewerResult` is a plain, non-frozen
   dataclass; round-2 review flagged that "build a new list" is satisfiable by a literal in-place
   `r.ok = ok` loop, which would corrupt `raw_results` out from under step 8, since Python passes
   objects by reference and both names would point at the same mutated objects). Setting `error=note`
   on demotion (not just appending to `stderr_tail`) is also a round-2 correction: `write_review_md`
   renders its primary per-reviewer status line from `result.error`, defaulting to the string
   `"unknown error"` when `None` (`core/aggregate.py:121,128`) — `stderr_tail` alone only shows up in
   a later fenced block, so without this, exactly the case this spec's own headline test exercises
   (raw-ok, Summary heading missing) renders as an uninformative `failed — unknown error`.

   **`classified_results` — not `raw_results` — is the single source of truth for both the exit
   code (step 10) and what `write_review_md` renders as `reviewers_succeeded`/`reviewers_failed`.**
   Round-1 review found the original design's exit code used *raw* `ok` (rc + byte-floor only,
   pre-Summary-heading-check) while `REVIEW.md`'s own frontmatter used the classified value — so the
   driver could exit 0 while every single reviewer section in the file it just wrote was marked
   failed. Computing both from the same classified list removes that gap by construction.
8. Synthesis gate. Separately from step 7's `classified_results`, count reviewers with **raw**
   `result.ok == True` among `raw_results` (not `classified_results` — this is the deliberate
   divergence explained below). If `pf.synthesizer != "none"` and that raw count is `>= 2`: call
   `build_synthesis_input(raw_results)` (from `core.synthesis`, operates on `r.ok` — i.e. still raw,
   matching `SKILL.md` Step 6's own gate, which also reads raw `state.json` `ok` before any
   Summary-heading check) → `(body, nonce)`. Then, **wrapped in `try/except Exception`**:

   ```python
   try:
       ok, text, err, suggested, attempts = await run_synthesis(
           pf.synthesizer, body, nonce,
           model=pf.models.get(pf.synthesizer), timeout=timeout,
       )
   except Exception as exc:
       ok, text = False, ""
       print(f"[multi_review] synthesis ({pf.synthesizer}): crashed: {exc}",
             file=sys.stderr, flush=True)
   ```

   **This `try/except` is required, not optional — round-2 review found, and two independent
   reviewers confirmed by reading `synthesis.py`, that `run_synthesis` can genuinely raise.**
   `_run_synthesis_attempt`'s `tempfile.NamedTemporaryFile(...)` call executes *before* its own
   `try:` block (`synthesis.py:66-72`); an `OSError` there (e.g. an unwritable `/tmp` under
   `bwrap --tmpfs /tmp`, which fires specifically when the synthesizer uses `argv_file` delivery —
   i.e. `agy`) propagates straight out. Without this wrapper, that exception would escape step 8
   entirely, so step 9 never runs and **no `REVIEW.md` is written at all** — discarding every
   already-collected reviewer result at the last, most expensive possible moment. This is a
   correction to the round-1 draft's error table, which incorrectly claimed synthesis failure could
   only ever produce `ok=False` cleanly.

   If `ok`: `synthesis_text = text`. Otherwise (including the crashed-and-caught case):
   `synthesis_text = None` — treated as absent, same as `synthesizer == "none"` or the `<2` case.
   Print one progress line regardless: `f"[multi_review] synthesis ({pf.synthesizer}): {'ok' if ok
   else 'failed'}"`.

   The raw-vs-classified split itself is deliberate, not a bug: the synthesis gate answers "is there
   enough raw material to synthesize from" (matching the skill's own semantics), while the exit code
   and `REVIEW.md` contents answer "did the round actually produce anything the caller can trust".
   Round-1 review confirmed conflating the two was the bug; round-2 review probed the resulting edge
   case explicitly — two reviewers both raw-`ok` (gate fires, synthesis runs) but both later
   demoted to classified-`ok=False` (Summary heading missing) — and confirmed the artifact this
   produces is self-consistent-enough to ship as-is: `REVIEW.md` would show `reviewers_succeeded: []`
   with a Consensus Summary section present, the driver still correctly exits `1` (classified count
   is 0), and `review-loop` discards the round per its own contract on any exit ≠ 0. The Consensus
   Summary section in that specific file is informational-only dead weight, not a correctness bug —
   not worth suppressing given the exit code is what the caller actually acts on.
9. `write_review_md(path=<out-dir>/REVIEW.md, results=classified_results, synthesis_text=synthesis_text,
   mode=pf.mode, task=pf.task, reviewers_attempted=<deduped reviewer list from step 4>,
   models=pf.models, synthesizer=(pf.synthesizer if synthesis_text else None),
   synthesized_at=(<UTC ISO timestamp, `time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())`> if
   synthesis_text else None), prompt_file=str(prompt_file))` — called directly from `core.aggregate`,
   no `resolve_output_path` indirection needed (step 2 already guaranteed `<out-dir>` is fresh, so no
   collision is possible; the auto-suffix behavior that indirection exists for cannot trigger here).
   Round-2 review found the round-1 draft dropped `models=`/`synthesizer=`/`synthesized_at=` without
   comment — `write_review_md` only emits the synthesizer frontmatter block when **both**
   `synthesizer` and `synthesized_at` are given (`core/aggregate.py:109-111`), so omitting them
   silently drops attribution for who produced the Consensus Summary; pass them.

   **Correction to the round-1 draft's claim about this call's failure-free-ness:** `write_review_md`
   *always* renders a `## Consensus Summary` heading, even when `synthesis_text` is `None` — the
   fallback body text is `_Consensus synthesis skipped (run without --no-synthesize to populate)._`
   (`core/aggregate.py:147-159`), which references a `--no-synthesize` flag this driver has no
   equivalent of. That's a pre-existing wart in `write_review_md` itself, not something the driver
   introduces or can cleanly suppress without a core change — out of scope here, just documented so
   nobody mistakes the phrase for something the driver is supposed to control.
10. Exit `0` if the classified-`ok` count from step 7 is `>= 1`, else `1`.

### Entry point contract

The driver exposes `def main(argv: list[str] | None = None) -> int`, same pattern every
`multi_review/cli/*.py` module already uses, with `if __name__ == "__main__": sys.exit(main())` at
the bottom. Round-2 review found the round-1 draft never stated this, leaving the driver's own
callable surface — needed for both `uv run multi_review.py ...` and for tests calling `main([...])`
directly — entirely to inference.

### Shutdown

`asyncio.run()`'s default `Ctrl-C`/`SIGINT` handling cancels the running task tree, which
`run_reviewer` already handles cleanly — cancellation triggers its own `kill_proc` on the child
before re-raising (`fanout.py:188-214`). **`SIGTERM` does not go through the same path** — it has
default disposition (immediate process termination) unless the driver installs a handler, so no
Python cleanup code runs and every in-flight reviewer subprocess is orphaned. Round-2 review verified
this live: 0 of 3 reviewer children survived a `SIGINT` to the driver, 3 of 3 survived a `SIGTERM`.
This matters specifically for this driver's deployment — the orphans are uncontained, agentic CLIs
(`agy`/`pykrete`/`claude -p`) that keep running with `--dangerously-skip-permissions` against the
sealed tree after `review-loop` believes the round is over.

Two complementary mitigations, both cheap, both should land:

- **Driver-side:** `loop.add_signal_handler(signal.SIGTERM, main_task.cancel)` at startup, routing
  `SIGTERM` into the same cancellation path `SIGINT` already uses for free.
- **Caller-side contract:** round-2 review verified that under `bwrap --unshare-pid
  --die-with-parent`, killing the `bwrap` process itself (not the driver) tore down all child
  reviewer processes cleanly, regardless of the driver's own signal handling. `review-loop` should
  use that flag combination and signal the wrapper, not attempt to reach into the driver's process
  tree directly.

### Directory layout under `--out-dir`

```
<out-dir>/
  prompt.txt   # from build_prompt, step 5
  REVIEW.md    # from write_review_md, step 9
```

No `reviews/` or `synth/` subdirectories — there are no per-reviewer files to hold, since fanout
and synthesis results are passed as in-memory objects directly into `write_review_md`.

## Error handling

| Failure | Where | Driver behavior |
|---|---|---|
| Bad `--prompt-file`/`--out-dir`/`--timeout` argv | argparse | exit 2 (argparse default) |
| `--out-dir` exists and is non-empty | step 2 | print error, exit 2 |
| `--out-dir` doesn't exist | step 2 | created via `mkdir(parents=True)` |
| Unreadable/missing YAML file | `path.read_text()` inside `load_promptfile` | `OSError` caught, exit 2 |
| Malformed YAML syntax | `yaml.safe_load` inside `load_promptfile` | `yaml.YAMLError` caught, exit 2 |
| Unknown/mistyped YAML field | `PromptFile(**raw)` inside `fill_defaults` | `TypeError` caught, exit 2 |
| Schema violation (bad enum, missing file, etc.) | `validate()` | `ValidationError` caught, exit 2 |
| `mode: both` | step 3 | exit 2 |
| Unreadable input/context file | `build_prompt` (step 5) | `SystemExit` caught, exit 1 — no reviewer dispatched |
| One reviewer's subprocess fails, times out, or crashes | `run_reviewer` (step 6) | that result's `ok=False`; others unaffected; never aborts the run |
| A `CancelledError`/other non-`ReviewerResult` item from `gather` | step 6 | synthesized failed `ReviewerResult` for that CLI (via `not isinstance(item, ReviewerResult)`); others unaffected |
| `run_synthesis` raises | step 8 | caught, `synthesis_text=None`, run continues to step 9 |
| Synthesis fails or `pf.synthesizer == "none"` or `<2` raw successes | step 8 | `synthesis_text=None`; `REVIEW.md`'s Consensus Summary section renders `write_review_md`'s own existing fallback text |
| `SIGTERM` to the driver during fanout | Shutdown | mitigated by a driver-side handler + caller-side `bwrap --unshare-pid --die-with-parent` contract (see Shutdown) |
| `write_review_md` itself fails (e.g. disk full, read-only mount) | `core.aggregate.write_review_md` (step 9) | `OSError`/`SystemExit` propagates uncaught — this is the one failure mode with no fallback, since it's the write of the driver's entire output; exit code is whatever the interpreter gives an uncaught exception (1). Round-2 review noted this is indistinguishable from "every reviewer failed" from the caller's point of view (both exit 1) — accepted, not fixed here; `review-loop` treats any non-zero exit the same way regardless. |

"Partial failures still produce `REVIEW.md`" holds for every row except the last (nothing else can
prevent the write) — same invariant the rest of the codebase already holds.

## Testing

New `tests/unit/test_multi_review_driver.py`. Monkeypatch `run_reviewer` and `run_synthesis` (both
plain `async def` functions imported into the driver module) to return canned `ReviewerResult` /
synthesis tuples. `build_prompt`, `classify_review_ok`, `build_synthesis_input`, and
`write_review_md` run for real against `tmp_path`, since they're pure fast functions already covered
by existing unit tests and mocking them here would just test the mocks.

**Import mechanism.** `multi_review.py` (the driver script) and `multi_review/` (the package
directory, with its own `__init__.py`) share a stem. Round-2 review verified live
(`importlib.util.find_spec('multi_review').origin`) that a plain `import multi_review` inside a test
resolves to the *package*, never the driver script — Python's `FileFinder` prefers packages over
same-named modules, and this repo's `tests/conftest.py` only prepends the repo root to `sys.path`,
which doesn't change that resolution. Load the driver explicitly instead:

```python
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "mr_driver", Path(__file__).resolve().parents[2] / "multi_review.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
```

then `monkeypatch.setattr(driver, "run_reviewer", ...)` and call `driver.main([...])`, asserting the
returned `int` (argparse's own usage errors are the one case that raises `SystemExit` instead —
`pytest.raises(SystemExit)` only for that case). This does not affect the driver's own runtime
imports (`import multi_review.core.fanout` from inside the script) — those resolve correctly via
`sys.path[0]` being the script's own directory regardless of this test-only package/module name
collision.

Cases:

- dedup: `reviewers: [codex, codex, agy]` dispatches exactly 2 `run_reviewer` calls (codex, agy)
- every `run_reviewer` call receives `prompt_path == out_dir / "prompt.txt"` — round-2 review noted
  this is invisible to a suite that doesn't assert it, while silently breaking agy on every real run
  if ever dropped (agy's `argv_file` delivery requires it)
- conditional `model=` forwarding: present when `pf.models[cli]` is set, `None` when absent (a
  direct kwarg assertion on the mocked call args, no argv construction involved)
- `--timeout` is forwarded to every `run_reviewer` and `run_synthesis` call; omitted `--timeout`
  reaches both as `None`, not some other default
- a `CancelledError` (not just a generic `Exception`) instance appearing among `gather`'s results is
  treated as a failed reviewer via the `not isinstance(item, ReviewerResult)` check, not crashed on
  — regression test for the round-2-found `isinstance(item, Exception)` bug
- exit code is driven by the **classified** (post-`classify_review_ok`) success count, not raw
  `ok` — construct a case where raw `ok=True` but the review text lacks a `## Summary` heading, and
  assert exit 1 with that reviewer in `reviewers_failed` and its `error` field set to the
  classifier's `note` (not left `None`)
- an exception raised inside a mocked `run_reviewer` call doesn't affect other reviewers' results
  and produces a synthesized failed `ReviewerResult` for that CLI, present (not vanished) in
  `reviewers_failed`
- synthesis gate: 1 raw success → `run_synthesis` not called; 2 raw successes → called
- synthesis gate uses **raw** `ok` (`raw_results`), exit code uses **classified** `ok`
  (`classified_results`) — a case where these two counts disagree (e.g. 2 raw successes but only 1
  classified) confirms synthesis still fires while the exit code still reflects the classified count
- `run_synthesis` raising (not just returning `ok=False`) → caught, `synthesis_text=None`, run
  continues, `REVIEW.md` still written, exit code unaffected by the synthesis outcome
- `mode: both` → exit 2, `run_reviewer` never called
- `--out-dir` doesn't exist → created, run proceeds
- `--out-dir` already exists and is non-empty → exit 2, `run_reviewer` never called
- malformed YAML / unknown top-level key → exit 2, not an uncaught traceback
- `build_prompt` raising (unreadable file) → exit 1, `run_reviewer` never called

## Manual smoke (before `review-loop` commits to this shape)

The test suite mocks all CLI dispatch, so a green suite says nothing about real subprocess or
sandboxed behavior.

1. `claude -p` running correctly under `bwrap --clearenv` with `~/.claude` bound writable.
2. Whether headless `claude -p` auto-denies permission-gated tool calls the way `agy --print` does
   (see the Goal section's posture-change note) — if so, reference mode systematically fails for
   `claude` through this driver and needs its own fix, not just a caveat.
3. WSL2: `--ro-bind /mnt/wsl` required in the `bwrap` invocation, or DNS breaks inside the sandbox —
   noted in the original handoff, repeated here since it's easy to lose.
4. **Invocation-contract smoke (round-2 addition):** `uv run <repo>/multi_review.py` from a foreign
   cwd with no `pyproject.toml`, and separately from a foreign cwd that has its own `pyproject.toml`
   — both must succeed and must not write `.venv/`/`uv.lock` into that foreign tree. This is the
   scenario the PEP 723 header fix targets; it was verified live during review but deserves a formal
   smoke pass against the actual implementation, not just the design.
5. **Shutdown smoke (round-2 addition):** send `SIGTERM` to the driver mid-fanout with the
   driver-side handler in place, confirm no orphaned reviewer subprocesses; separately, confirm
   killing a `bwrap --unshare-pid --die-with-parent` wrapper around the driver tears down all
   children even without the handler.

## Open question carried from the handoff (resolved here)

Driver location: `multi_review.py` at repo root, not a new `mr-run` console script. The caller
(`review-loop`) already expects to point `bwrap` at this path; a console script would require the
caller to update its config for no benefit, since either way it's one string.

## Review history

- **Round 1** (4 reviewers: codex holistic breadth, adversarial, async/subprocess-dispatch focus,
  writing-plans-compatibility focus): surfaced the subprocess-dispatch cwd blocker (live-reproduced
  independently by 2 reviewers), the exit-code/`reviewers_failed` mismatch, the stale-`REVIEW.md`
  on out-dir reuse, the missing-`--input-nonce` synthesis bug, the vanishing-reviewer-on-crash gap,
  and the vacuous test-mock design. Addressed by moving fanout in-process, unifying the
  exit-code/`reviewers_failed` source of truth, requiring a fresh `--out-dir`, and wiring the
  synthesis call's real arguments.
- **Round 2** (same 4-reviewer panel, re-reviewing the round-1 revision): confirmed all round-1
  fixes landed as intended, then found a *new* foundational blocker in the in-process design's own
  invocation contract — `uv run`'s dependency resolution (not the local-package-import mechanism
  round 1 checked) still breaks from a foreign cwd, live-reproduced — plus: `--out-dir` was declared
  fresh-required but never actually created; `run_synthesis` can raise and silently discard every
  collected reviewer result if unwrapped; `SIGTERM` orphans reviewer subprocesses (live-verified);
  the crash-isolation fix from round 1 had its own bug (`isinstance(x, Exception)` misses
  `CancelledError`); progress-line timing was described in a way `asyncio.gather` can't actually
  produce; the test suite couldn't import the driver module due to a package/module name collision;
  and several smaller correctness/precision issues in the error table and `write_review_md` call.
  All addressed above. No cap-3 round 3 has been run as of this revision — see note below.

## Follow-up items noted, not part of this design

- `BACKLOG.md:1154` and `README.md:166,186` both claim `output_dir` overriding is wired. It isn't —
  nothing reads `PromptFile.output_dir`. Worth a correction pass, unrelated to this driver.
