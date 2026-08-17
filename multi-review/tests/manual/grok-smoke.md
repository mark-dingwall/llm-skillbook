# grok reviewer manual smoke

**Status:** updated for v0.3 on 2026-08-11. This CLI makes live, paid network
calls; re-run the procedure to refresh the live evidence.

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
- `GrokAdapter` leaves `usage.tool_calls` at `0` because grok emits no tool-call
  events in any output format. That value is unavailable rather than a measured
  zero (see `multi_review/core/adapters.py`).
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
  in posture, as this smoke's source observation records.
- Opt-in enforcement rests on two prose sites, not just the Python split:
  `agents/multi-review-build.md`'s autonomous `--use-defaults` reviewer list,
  and `SKILL.md`'s dispatch instructions binding to `resolved.reviewers`. Both
  are pinned by `tests/integration/test_skill_contract.py` — but that test
  asserts the **repo** copy of those files, not what's installed in
  `~/.claude`. See the precondition below.

## Precondition — reinstall first, or the smoke is worthless

The repository installer copies canonical agent definitions into `~/.claude`.
`--dev` symlinks the skill directory, but it still copies the agents, so a
checkout with changed canonical agents does **not** change what Claude Code
actually runs until it is reinstalled. Every case below exercises the installed
copy. From the repository root, begin the procedure with:

```bash
python3 install.py multi-review --target claude                  # add --dev to symlink the skill
grep -c grok ~/.claude/agents/multi-review-build.md              # expect >= 1
grep -c 'resolved.reviewers' ~/.claude/skills/multi-review/SKILL.md  # expect >= 1
```

If those greps come back empty you are testing a stale install, and cases 1-3
will report false confidence about opt-in.

For every remaining case, work from the component root so the prompt examples
and paths below resolve as written:

```bash
cd multi-review
```

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
prompt_format_version: 2
task: code
files:
  - multi_review/core/paths.py
synthesizer: none
```

Run it via `/multi-review --prompt-files <yaml>`. Confirm `REVIEW-*.md` has
**no** grok section.

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
prompt_format_version: 2
task: code
files:
  - multi_review/core/paths.py
synthesizer: none
reviewers:
  - claude
  - grok
```

Run it. Confirm:
- A grok section exists in `REVIEW-*.md`, opening with a `## Summary` heading.
- The review text references `project_state_dir` or `run_dir` (symbols defined
  only in `multi_review/core/paths.py`) — a `## Summary` heading alone does not
  prove the prompt arrived; grok could read an empty prompt, review nothing,
  and still return a superficially successful response.

### 5 — Reference-only input with an out-of-cwd file

Build a v0.3 prompt YAML with a `files:` entry outside the current working
directory (e.g. a file under `/tmp` or a sibling repo).
Confirm grok's review actually engages with that file's content — this is
the check that `--sandbox workspace` has not broken reads (it fences writes
only; the historical source observation above records that reads are not
restricted under that profile).

### 6 — Synthesizer role

```yaml
prompt_format_version: 2
task: code
files:
  - multi_review/core/paths.py
  - multi_review/core/reviewers.py
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

Run a single pass with `reviewers: [claude, grok]`, applying the `PATH`/`uv`
substitution above to whichever step spawns the grok subprocess. Confirm:
- grok appears as a *failed section* with a `CLI not found` error.
- The run still produces its review file (exit 0, claude succeeded).
- The path the skill reports is `<cwd>/REVIEW-<slug>.md` (SKILL.md Step 7) —
  not a bare `REVIEW.md`, which no code path writes, and possibly
  auto-suffixed `-2` if a prior run left a file there.

## Pass criteria

- [ ] 1: `--list-reviewers` shows grok available and marked opt-in.
- [ ] 2: omitted `reviewers` in a v0.3 YAML never includes grok in the review
      file.
- [ ] 3: `--use-defaults` autonomous builder's authored YAML omits grok from
      its explicit `reviewers` list.
- [ ] 4: explicit `reviewers: [claude, grok]` produces a grok `## Summary`
      section whose review text proves it read the selected file.
- [ ] 5: an out-of-cwd input file is readable and its content is reviewed.
- [ ] 6: `synthesizer: grok` produces clean markdown synthesis, no JSONL
      envelope, no narration.
- [ ] 7: `grok` off `PATH` produces a failed-reviewer section rather than a
      run crash; the reported path is `<cwd>/REVIEW-<slug>.md`.

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
  invocation, contrary to this smoke's source-observation section.
