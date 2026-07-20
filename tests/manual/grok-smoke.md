# grok reviewer manual smoke

**Status:** procedure authored 2026-07-19; not yet executed live. This
environment has the real `grok` CLI installed but it makes live, paid network
calls — nothing below has been exercised end to end. Do not treat any
pass/fail claim in this file as evidence until the "Results" section at the
bottom is filled in from a real run.

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
- `GrokAdapter.feed_line` handles the complete *observed* event set —
  `thought` / `text` / `end` (plus a defensive `error` branch for a type
  never seen in probing); `end` usage is absolute (assigned, not accumulated).
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

Temporarily rename the `grok` binary off `PATH` (e.g.
`mv $(which grok) $(which grok).disabled`). Run **single-pass**
(`mode: reference`, not `both`) with `reviewers: [claude, grok]`. Confirm:
- grok appears as a *failed section* with a `CLI not found` error.
- The run still produces its review file (exit 0, claude succeeded).
- The path the skill reports is `<cwd>/REVIEW-<slug>.md` (SKILL.md Step 7) —
  not a bare `REVIEW.md`, which no code path writes, and possibly
  auto-suffixed `-2` if a prior run left a file there. Paired runs use
  mode-suffixed names instead, which is why this case pins single-pass.

Restore the `grok` binary afterward (`mv $(which grok).disabled $(which grok)`,
adjusting the path as needed).

## Pass criteria

- [ ] 1: `--list-reviewers` shows grok available and marked opt-in.
- [ ] 2: omitted `reviewers` in a YAML never includes grok (review file or
      harvest row).
- [ ] 3: `--use-defaults` autonomous builder's authored YAML omits grok from
      its explicit `reviewers` list.
- [ ] 4: explicit `reviewers: [claude, grok]` produces a grok `## Summary`
      section; harvest row shows non-zero tokens, `tool_calls: 0`,
      `telemetry_quality: "known-issues"`.
- [ ] 5: reference mode with an out-of-cwd file — grok's review engages with
      that file's real content (reads not blocked by the sandbox profile).
- [ ] 6: `synthesizer: grok` produces clean markdown synthesis, no JSONL
      envelope, no narration.
- [ ] 7: `grok` off `PATH` → recorded failed-reviewer section, not a run
      crash; reported path is `<cwd>/REVIEW-<slug>.md` (single-pass).

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

Not yet run. Fill in per scenario (1-7) once executed against the real `grok`
CLI: date, pass/fail, and any bug found — including whether it needs a fix +
backfilled pytest test per CLAUDE.md's testing-discipline note, or is
genuinely un-automatable and stays here.
