# grok reviewer manual smoke

**Status:** procedure authored 2026-07-19. **All 7 cases executed live
2026-08-03** against grok 0.2.117 (a422116) — all pass. Case 5 (first run)
found a blocker that failed every grok review (see Results); cases 1-4 and 7
(run after the fix) found no further issues. This CLI makes live, paid
network calls; every pass criterion below is now evidenced.

grok is the opt-in sixth reviewer: valid everywhere a reviewer or synthesizer
can be named, but never auto-selected (`ALL_REVIEWERS` contains it,
`DEFAULT_REVIEWERS` does not). Unlike pykrete/agy it needs no external config
to run — the risk here is the opposite one: proving it stays off when not
named.

## Facts this procedure relies on (verified against source, 2026-07-19)

From `multi_review/core/reviewers.py`:
- `ALL_REVIEWERS = ["claude", "agy", "codex", "opencode", "pykrete", "grok"]`;
  `DEFAULT_REVIEWERS = ["claude", "agy", "codex", "opencode", "pykrete"]` —
  grok is in the first, not the second.
- `CLI_SPEC["grok"]["base"] = ["grok", "--sandbox", "workspace", "--prompt-file", "/dev/stdin"]`,
  `stream_flags = ["--output-format", "streaming-json"]`, `model_flag = "--model"`,
  `stdin_sentinel = None` (the prompt reaches grok via `/dev/stdin`, not a `-` sentinel).
- No `success_exit_codes` override for grok (defaults to `(0,)`), no
  `records_family_not_model`, no `config_env` — grok has no config-file
  precondition to fail clean on.
- `TELEMETRY_QUALITY["grok"] = "known-issues"` (`multi_review/core/harvest.py`)
  — tokens reliable, `tool_calls` always `0` and unavailable (grok emits no
  tool-call events in any output format; see `GrokAdapter` docstring in
  `multi_review/core/adapters.py`).
- `GrokAdapter.feed_line` consumes `thought` / `text` / `end` (plus a
  defensive `error` branch for a type never seen in probing); `end` usage is
  absolute (assigned, not accumulated). grok emits more types than these —
  0.2.117 also sends `available_commands` and a standalone `usage` event — but
  unrecognised types hit no branch and are inert. **The event schema drifts:**
  the clean `stopReason` has shipped as both `EndTurn` and `end_turn`, and the
  exact-match against one spelling was the case-5 blocker. Treat every literal
  here as a snapshot, not a contract.
- `--sandbox workspace` fences writes to cwd + tmp; it does **not** restrict
  reads and is **not** a security boundary — grok remains agentic/uncontained
  in posture, same as agy and pykrete (CLAUDE.md invariants).
- Opt-in enforcement rests on two prose sites, not just the Python split:
  `agents/multi-review-build.md`'s autonomous `--use-defaults` reviewer list,
  and `SKILL.md`'s dispatch instructions binding to `resolved.reviewers`. Both
  are pinned by `tests/integration/test_skill_contract.py` — but that test
  asserts the **repo** copy of those files, not what's installed in
  `~/.claude`. See the precondition below.

## Precondition — reinstall first, or the smoke is worthless

`setup.py` *copies* `skills/multi-review/` and `agents/*.md` into `~/.claude`
(it symlinks only under `--dev`), so a checkout with this branch's edits does
**not** change what Claude Code actually runs. Every case below exercises the
installed copy. Begin the procedure with:

```bash
uv run python -m multi_review.cli.setup --source-repo $(pwd)     # or --dev to symlink
grep -c grok ~/.claude/agents/multi-review-build.md              # expect >= 1
grep -c 'resolved.reviewers' ~/.claude/skills/multi-review/SKILL.md  # expect >= 1
```

If those greps come back empty you are testing a stale install, and cases 1-3
will report false confidence about opt-in.

## Procedure

### 1 — Availability

```
/multi-review --list-reviewers
```

Confirm the printed table includes a `grok` row marked available (assuming
`grok` is on `PATH` and authenticated), and marked **opt-in** in the output
(SKILL.md Step 1 probes `ALL_REVIEWERS`, including grok, but grok is never
auto-selected).

### 2 — Opt-in holds (YAML path)

Build a prompt YAML with `reviewers` omitted entirely (so `fill_defaults`
populates `DEFAULT_REVIEWERS`):

```yaml
prompt_format_version: 1
task: code
files:
  - multi_review/core/paths.py
mode: reference
synthesizer: none
```

Run it via `/multi-review --prompt-files <yaml>`. Confirm:
- `REVIEW-*.md` has **no** grok section.
- The harvest row's `usage_by_reviewer` has no `grok` key.

### 3 — Opt-in holds (autonomous builder path)

```
/multi-review --use-defaults "review paths.py for correctness"
```

Before the run proceeds (or from the retained `.multi-review/prompts/.tmp/`
directory), **read the generated YAML** at
`.multi-review/prompts/.tmp/<id>.yaml` and assert its explicit `reviewers`
list omits grok. This is a distinct path from case 2: the builder writes an
explicit list, so `fill_defaults` never runs — this is the live path that
`test_builder_autonomous_default_matches_DEFAULT_REVIEWERS` guards on the repo
copy, and this case is what proves the *installed* copy behaves the same way.

### 4 — Explicit selection

```yaml
prompt_format_version: 1
task: code
files:
  - multi_review/core/paths.py
mode: reference
synthesizer: none
reviewers:
  - claude
  - grok
```

Run it. Confirm:
- A grok section exists in `REVIEW-*.md`, opening with a `## Summary` heading.
- The harvest row records non-zero `input_tokens`/`output_tokens` for grok,
  with `tool_calls: 0` and `telemetry_quality: "known-issues"`.
- The review text references `project_state_dir` or `central_runs_dir` (symbols
  defined only in `multi_review/core/paths.py`) — a `## Summary` heading and
  non-zero tokens alone don't prove the prompt arrived; grok re-opens fd 0 via
  `/dev/stdin`, and the plausible live failure is grok reading an empty prompt,
  reviewing nothing, and still exiting 0 with >50 bytes (a recorded success
  with a content-free review).

### 5 — Reference mode with an out-of-cwd file

Build a prompt YAML with `mode: reference` and a `files:` entry outside the
current working directory (e.g. a file under `/tmp` or a sibling repo).
Confirm grok's review actually engages with that file's content — this is
the check that `--sandbox workspace` has not broken reads (it fences writes
only; reads are unrestricted under that profile per the CLAUDE.md invariant).

### 6 — Synthesizer role

```yaml
prompt_format_version: 1
task: code
files:
  - multi_review/core/paths.py
  - multi_review/core/reviewers.py
mode: reference
synthesizer: grok
reviewers:
  - claude
  - codex
```

Run it (with ≥2 reviewers succeeding). Confirm `synth.txt` is clean markdown
with no JSONL envelope and no step-narration — the synthesis path builds with
`streaming=False`, passes no `--output-format` flag, and takes grok's stdout
verbatim as the synthesis body with no adapter involved.

### 7 — Failure path

Do **not** rename or move the `grok` binary — a rename-then-restore via
`which` is self-defeating (once renamed, `which grok` resolves to nothing,
so the restore command has no destination and leaves the binary disabled).
Instead, hide grok from `PATH` only for this one invocation by filtering out
any directory that contains a `grok` executable, and invoke `uv` by its
absolute path so command lookup itself isn't affected by the filtered PATH:

```bash
UV_BIN=$(command -v uv)
CLEAN_PATH=$(python3 -c "
import os
dirs = [d for d in os.environ['PATH'].split(':') if d and not os.path.isfile(os.path.join(d, 'grok'))]
print(':'.join(dirs))
")
PATH="$CLEAN_PATH" "$UV_BIN" run python -m multi_review.cli.spawn --cli grok ...
```

Nothing is renamed, so there is nothing to restore afterward — the real
`PATH`/binary are untouched outside this one command's environment. (`claude`
in `reviewers: [claude, grok]` runs via the Task tool, not a subprocess, so
excluding whole PATH directories here doesn't affect it.)

Run **single-pass** (`mode: reference`, not `both`) with
`reviewers: [claude, grok]`, applying the `PATH`/`uv` substitution above to
whichever step spawns the grok subprocess. Confirm:
- grok appears as a *failed section* with a `CLI not found` error.
- The run still produces its review file (exit 0, claude succeeded).
- The path the skill reports is `<cwd>/REVIEW-<slug>.md` (SKILL.md Step 7) —
  not a bare `REVIEW.md`, which no code path writes, and possibly
  auto-suffixed `-2` if a prior run left a file there. Paired runs use
  mode-suffixed names instead, which is why this case pins single-pass.

## Pass criteria

- [x] 1: `--list-reviewers` shows grok available and marked opt-in.
      PASS 2026-08-03: `detect_available()` returns grok alongside the other
      five; grok is absent from `DEFAULT_REVIEWERS` so it renders opt-in.
- [x] 2: omitted `reviewers` in a YAML never includes grok (review file or
      harvest row). PASS 2026-08-03: `fill_defaults` resolved to
      `[claude, agy, codex, opencode, pykrete]`; live fanout's REVIEW.md has
      no grok section and `usage_by_reviewer` has no `grok` key.
- [x] 3: `--use-defaults` autonomous builder's authored YAML omits grok from
      its explicit `reviewers` list. PASS 2026-08-03: builder wrote
      `reviewers: [claude, agy, codex, opencode, pykrete]`.
- [x] 4: explicit `reviewers: [claude, grok]` produces a grok `## Summary`
      section; harvest row shows non-zero tokens, `tool_calls: 0`,
      `telemetry_quality: "known-issues"`. PASS 2026-08-03: 99 899 in / 3 290
      out tokens, `tool_calls: 0`, `telemetry_quality: "known-issues"`; review
      body cites `project_state_dir`/`central_runs_dir` (paths.py-only
      symbols), proving the prompt arrived.
- [x] 5: reference mode with an out-of-cwd file — grok's review engages with
      that file's real content (reads not blocked by the sandbox profile).
      PASS 2026-08-03, after fixing the stopReason blocker (see Results).
- [x] 6: `synthesizer: grok` produces clean markdown synthesis, no JSONL
      envelope, no narration. PASS 2026-08-03.
- [x] 7: `grok` off `PATH` → recorded failed-reviewer section, not a run
      crash; reported path is `<cwd>/REVIEW-<slug>.md` (single-pass).
      PASS 2026-08-03: `error: "CLI not found: [Errno 2] No such file or
      directory: 'grok'"`, claude succeeded, output written to
      `<cwd>/REVIEW-case7-offpath.md`.

## Failure modes to watch for

- grok not actually opt-in on the **installed** copy despite the repo/test
  suite being green — this is exactly what the reinstall precondition and
  cases 2/3 exist to catch. A stale `~/.claude` install is the most likely
  way this smoke reports false confidence.
- `## Summary` heading missing from real grok output — would demote a
  genuinely successful review to a failure section (SKILL.md Step 7's
  classifier).
- grok's `--sandbox workspace` behaving differently than documented (e.g.
  refusing a read outside cwd, or failing to fence a write) — this file's
  case 5 is the first live chance to see it against the real binary instead
  of the fixture shim at `tests/fixtures/bin/grok`.
- Synthesis producing a JSONL envelope instead of clean markdown — would mean
  the `--output-format` flag leaked into the non-streaming synthesis
  invocation (see CLAUDE.md invariant on grok's mode-dependent output format).

## Results

### 2026-08-03 — cases 5 and 6 executed live (grok 0.2.117, `a422116`)

Cases 1-4 and 7 remain unrun as of this section (executed later the same day —
see the follow-up section below).

**Case 5 — reference mode, out-of-cwd file: PASS (after fixing a blocker).**
Reviewed `~/kramtime/claude-skills/review-loop/.ref/code-review-workflow.js`
from a cwd of the multi-review checkout. grok's review names `canonFile`,
`verifyGroups`, `LEVEL_PARAMS` and `Object.create(null)` — symbols that exist
only in that file — so `--sandbox workspace` does **not** restrict reads, as
the CLAUDE.md invariant claims. 31 209 in / 4 543 out tokens, `tool_calls: 0`,
`telemetry_quality: "known-issues"`, 95 s.

**Case 6 — `synthesizer: grok`: PASS.** Reviewers claude + codex both ok;
grok synthesized in 27 s. `synth.txt` is 2 664 bytes of clean markdown, zero
lines matching `^{"type"` (no JSONL envelope leak), no step narration, and it
correctly omits the host-supplied `## Consensus Summary` heading. The
`FILENAME:` line was parsed and stripped as designed —
`suggested_filename: "REVIEW-core-paths-reviewers.md"`. `usage: null` on the
synthesis state is expected: that path builds with `streaming=False` and runs
no adapter.

#### Bug 1 (blocker, fixed) — `stopReason` schema drift failed every grok review

Case 5's first run recorded `ok: false` with `error: "stopReason=end_turn"`
despite producing a complete 7.9 KB review. `GrokAdapter` compared
`stop != "EndTurn"`, but grok 0.2.117 emits `end_turn` (confirmed by direct
probe: `stopReason":"end_turn"`, rc 0, on a trivial prompt). Since
`fanout.py:226` computes `ok = base_ok and not adapter.last_error`, **every
successful grok review was being recorded as a failure** with its body
truncated into `partial` — and a false failure written to `runs.jsonl`. The
`EndTurn` spelling in `tests/fixtures/streams/grok/success.jsonl` is a real
capture from an older build, so both spellings have now been observed.

Fixed by normalising the comparison (`str(stop).replace("_","").lower() !=
"endturn"`); any other stopReason still surfaces verbatim, since a refusal or
abort shows up there and nowhere else (grok exits 0 either way). Pinned by
`test_grok_adapter_accepts_every_observed_clean_stop_reason` and
`test_grok_adapter_still_flags_genuine_abort_stop_reasons`. The fixture shim's
default was moved to `end_turn` to track current reality. Re-ran case 5 against
the real binary: `ok: true`, `error: null`.

The probe also surfaced two event types the adapter docstring called a complete
set: `available_commands` (startup banner) and a standalone `usage` event.
Both are inert — unrecognised types hit no branch — but the docstring's
"complete OBSERVED set" claim was stale and has been corrected.

#### Live confirmation of the 2026-07-31 gate split

Both grok runs opened with narration glued straight onto the heading with no
newline (`"I'll review the referenced file carefully…## Summary"`). Verified
directly: `classify_review_ok` returns `(True, None)` while the anchored
`SUMMARY_HEADING_RE` does **not** match. Under the pre-split single anchored
regex this real, complete, correct review would have been demoted to a
1000-char failure section. Third independent observation of the
heading-present-but-not-at-line-start shape.

#### Bug 2 (fixed) — pytest silently redirected the real harvest path

Not grok-specific; hit while satisfying this file's own reinstall
precondition. `~/.claude/skills/multi-review/config.json` contained
`/tmp/pytest-of-mark/pytest-3/test_setup_dev_mode_symlinks0/xdg/multi-review`,
so `central_runs_dir()` — which reads that file before any other resolution
step — pointed every real run's harvest at a deleted tmpdir.

Cause: `test_setup_dev_mode_symlinks` ran `setup --dev --source-repo <the live
checkout>`. `--dev` symlinks `$HOME/.claude/skills/multi-review` at
`--source-repo`, so setup's `config.json` write follows the symlink into the
real tree; monkeypatching `HOME` does not redirect it. Reproduced by running
that single test in isolation and diffing the file. Suite stayed green
throughout — nothing asserts the checkout is unmodified.

Fixed by staging a copy of `skills/` + `agents/` under `tmp_path` and pointing
`--source-repo` there. Guarded by a session-scoped autouse fixture in
`tests/conftest.py` that snapshots the file, restores it, and fails the run if
any test mutates it — ordering-independent, so it catches a reintroduction
from any test, not just this one.

#### Bug 3 (fixed) — SKILL.md Step 8 never recorded the synthesizer

Case 6's harvest row came out `synthesizer: null, synthesis_ok: false` even
though grok's synthesis succeeded and is present in the REVIEW.md.
`write_harvest_row` accepts `--synthesizer` / `--synthesis-ok`, but SKILL.md
Step 8's documented invocation listed neither — so every skill-driven run
mislabels its synthesis. Nothing errors; the columns are just silently wrong,
the same failure shape as the never-populated `comparison_eligible` key. Step 8
now passes both conditionally; pinned by
`test_skill_harvest_invocation_records_the_synthesizer`. Case 6's row was
corrected in place.

#### Procedure gaps found in this document

- Cases 4 and 6's YAML snippets use paths relative to the repo root, but
  `promptfile.py:99` resolves relative `files:` against **the YAML's own
  directory**. A YAML staged outside the repo fails validation with
  `files: path does not exist on disk`. Use absolute paths, or keep the YAML
  in the repo root.
- The reinstall precondition should also check
  `~/.claude/skills/multi-review/config.json` for a `/tmp/pytest-of-*` path —
  bug 2 above makes that a recurring hazard on any dev box that runs the suite.

### 2026-08-03 (later) — cases 1-4 and 7 executed live (grok 0.2.117, `a422116`)

Ran with the stopReason fix from Bug 1 already in place. All five pass, no
further bugs found.

**Case 1 — availability: PASS.** `detect_available()` (probes `ALL_REVIEWERS`)
returned grok alongside claude/agy/codex/opencode/pykrete; grok's absence from
`DEFAULT_REVIEWERS` marks it opt-in in the rendered table.

**Case 2 — opt-in via omitted `reviewers`: PASS.** `validate_prompt` on a YAML
with `reviewers` omitted resolved `[claude, agy, codex, opencode, pykrete]` via
`fill_defaults` — no grok. Ran the full fanout live: the resulting REVIEW.md
has no grok section and the harvest row's `usage_by_reviewer` has no `grok`
key, as expected. Two of the other four reviewers didn't fully succeed, but
neither is grok-related: pykrete failed clean on missing `$PYKRETE_CONFIG` as
designed, and agy failed on a `command` tool auto-denied under a
headless-permission gate. The agy failure is unrelated to this smoke's
subject but noted for the record — observed once here, cause not confirmed.
CLAUDE.md's agy invariant says it normally auto-proceeds without
`--dangerously-skip-permissions`, so a permission block is somewhat
surprising; may be a local sandbox quirk, may be worth its own investigation.

**Case 3 — opt-in via autonomous builder: PASS.** `multi-review-build` in
`--use-defaults` mode wrote `reviewers: [claude, agy, codex, opencode,
pykrete]` — matches `DEFAULT_REVIEWERS`, omits grok, on the installed copy
(not just the repo copy the unit tests pin).

**Case 4 — explicit `[claude, grok]` selection: PASS.** grok section present
with a `## Summary` heading (narration glued directly onto the heading again,
no newline — third-plus observation of the same shape the gate/trim split
handles). Harvest row: 99 899 in / 3 290 out tokens, `tool_calls: 0`,
`telemetry_quality: "known-issues"`. Review body cites `project_state_dir` and
`central_runs_dir` — symbols defined only in `paths.py` — proving the prompt
(not an empty stdin) reached the model.

**Case 7 — grok off PATH: PASS.** Spawned grok with `PATH` filtered to drop
the directory containing the `grok` binary (per the procedure's
rename-avoidance approach). Recorded `error: "CLI not found: [Errno 2] No
such file or directory: 'grok'"`, `ok: false`. claude still succeeded; the
aggregated file landed at `<cwd>/REVIEW-case7-offpath.md` (not a bare
`REVIEW.md`), matching SKILL.md Step 7's single-pass output-path contract.

No code changes this round — all five cases behaved exactly as documented
once Bug 1 (case 5/6 round) was fixed.
