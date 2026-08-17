# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Fans out one review prompt to multiple AI CLIs in parallel (`claude`, `agy`, `codex`, `opencode`, `pykrete`, `grok`), aggregates responses into `REVIEW.md`, and optionally runs a consensus-synthesis pass.

The project supports two entry points: the **Claude Code skill** `/multi-review`, whose
multi-step procedure lives in `SKILL.md`, and the root
`multi_review.py` headless single-pass driver for contained callers: invoke
`uv run <absolute-repo-path>/multi_review.py --prompt-file <yaml> --out-dir <dir> [--timeout <sec>]`.

Packaged via `pyproject.toml` (`multi_review/core` + `multi_review/cli`). Console scripts (`mr-spawn`, …) are declared there but **are not installed in this checkout** — invoke modules as `uv run python -m multi_review.cli.<name>`.

## Commands

```bash
# Install/refresh the skill + agents (repo-level installer)
python3 ../install.py multi-review --target both        # --dev to symlink

# Test suite
uv run pytest tests/ -q

# Validate a prompt YAML without running a review
uv run python -m multi_review.cli.validate_prompt prompt.yaml

```

`ruff` and `mypy` are configured in `pyproject.toml` but not wired into any target — don't assume a tool is installed without checking.

## Tooling gotchas

- `codex exec` always tries reading extra prompt from stdin after startup — if stdin stays open (not piped/closed), it hangs forever.
- `agy --print <prompt>` swallows whatever argv token comes immediately after `--print` as its prompt value — even if that token is itself a flag. `agy --print --model X "prompt"` silently discards `"prompt"` and answers as if asked about `--model` instead. Put flags before `--print`, or after the prompt string — never between. Confirmed live 2026-08-03 against agy 1.1.10; `build_command` already orders agy's argv correctly (see the agy invariant below) — this note is for anyone invoking `agy` by hand outside the tool.
- `agy --print` (headless) auto-denies any permission-gated tool call, always — there's no human to prompt. Pass `--dangerously-skip-permissions` when invoking it by hand, or it silently produces no output with a denial message on stderr. multi_review's own agy invocation already does this (see the agy invariant below).

## Testing discipline

When fixing a bug or shipping a behavioural change in an untested area, write the test as part of the fix. The pytest suite under `tests/{unit,integration}/` is the baseline (`uv run pytest tests/ -q`); every bugfix is an opportunity to backfill the test that would have caught it. Do not ship a fix to a regressed path without leaving an executable check behind. Applies to: adapter JSONL parsing, prompt assembly, aggregation. Skill-level interactive flows that genuinely can't be automated → document a manual smoke step under `tests/manual/*.md` instead.

**`uv run pytest` resolves to the system pytest**, and `pytest_asyncio` is not importable there — hence the pre-existing `PytestConfigWarning: Unknown config option: asyncio_mode` on every run. Harmless today because zero `async def` tests exist, but it silently disarms `asyncio_mode = "auto"` (pyproject.toml) the day someone writes one — an `async def test_...` would just be collected as a coroutine object and reported as a pass without ever running its body. Don't rely on the warning being noticed; if you add an async test, verify it actually executed (e.g. a deliberate `assert False` inside it) before trusting a green run.

## Manual-smoke note

Skill-level interactive flows bypass the test suite. When you hit a bug in
SKILL.md procedure (a step doesn't fan out right, a Task subagent loses context, an
AskUserQuestion sequence misbehaves), add or update the corresponding `tests/manual/*.md`
procedure as part of the fix — and where the bug surface is automatable (parsing),
backfill a pytest test under
`tests/{unit,integration}/`. Skill bugs are exactly the category that "manual only" excuses
get used to skip — don't.

## Architecture

### Data flow

SKILL.md steps drive this; the module names below are where each step's work happens.

1. `validate_prompt` parses the prompt YAML into a `resolved` object — reviewer set, synthesizer, and models. That object is the sole source of who runs; never re-derive from `ALL_REVIEWERS` or a `--list-reviewers` probe.
2. `prepare` calls `build_prompt`: the nonce-tag injection preamble + tool-read reference preamble + task template (or `custom_prompt`) + inline context + an absolute-path input manifest. Context files are wrapped in `<file-NONCE path="…">…</file-NONCE>`; input-file bytes are never read into the prompt.
3. Fanout: the `claude` reviewer runs as a Task subagent (`multi-review-reviewer`), captured via `write_task_result`. Every other reviewer is a background `spawn` subprocess whose stdout feeds a per-CLI `ProgressAdapter` (`claude`/`codex`/`opencode`/`grok` parse JSONL; `agy`/`pykrete` are plain text).
4. `build_synth_input` wraps each successful review in `<review reviewer="…">`; the synthesizer (Task subagent or `spawn`) returns a Consensus Summary body.
5. `aggregate` emits YAML frontmatter + one section per reviewer + Consensus Summary.

### Key abstractions

- **`CLI_SPEC` table** (`multi_review/core/reviewers.py`): single source of truth for each CLI's invocation — `base` args, streaming flags, `--model` flag name, and optional `stdin_sentinel` (the `-` arg some CLIs need to read prompt from stdin). `build_command` composes argv from this; both `run_reviewer` (streaming) and `run_synthesis` (non-streaming) consume it.
- **Adding a new reviewer**: add to `ALL_REVIEWERS` (known/valid), decide default-on vs opt-in by whether it also goes in `DEFAULT_REVIEWERS`, add a `CLI_SPEC` entry, write a `ProgressAdapter` subclass, register in `ADAPTER_FOR`, and — if it is default-on — add it to the builder agent's autonomous default list too.
- **`ProgressAdapter` subclasses** (one per CLI): parse that CLI's JSON event stream into a `Usage` dataclass + accumulated text. Each CLI has different telemetry fidelity. Keep the adapter defensive: upstream event schemas drift.
- **`ReviewerState` / `ReviewerResult`**: mutable state the dashboard watches vs. final result returned from `run_reviewer`.
- **Prompt shape is unconditional.** `build_prompt` emits every input file in a `## Files to Review` manifest of absolute paths and never reads input-file bytes. Context files are inline-wrapped under `<file-NONCE>` tags. The nonce-tag injection preamble and tool-read reference preamble always apply because they protect distinct delivery channels.

### Invariants to preserve

- **Prompt goes on stdin, never argv — except agy, which reads a file path.** Every stdin-capable CLI is invoked with the prompt written to `proc.stdin`, keeping prompts out of `/proc/PID/cmdline` (see commit `55d783b`). Don't move those prompts to argv. **agy is the documented exception:** it has no stdin input mode (`--print` requires the prompt as its argv value), and prompts can embed context-file contents that would exceed `MAX_ARG_STRLEN` (128 KiB → `E2BIG`) on argv. So agy uses `"prompt_delivery": "argv_file"` in `CLI_SPEC`: the prompt is written to a file and agy is handed a tiny instruction naming that path (`AGY_FILE_INSTRUCTION`). Only the *path* — never the prompt contents — reaches the process table, so the invariant's intent holds. `build_command(..., prompt_path=…)` requires the path for argv_file CLIs; the instruction must sit immediately after `--print` (which consumes the next arg as its value) so it isn't swallowed by `--model`. Verified against agy 1.0.16/1.1.1 (2026-07-10 smoke).
- **Self-skip is opt-in** (`--skip-self`, default off). `detect_self()` reports the host via env vars: `CLAUDE_CODE_ENTRYPOINT` → `claude`, `CODEX_ENV` → `codex`, `OPENCODE` → `opencode`. `ANTIGRAVITY_AGENT=1` short-circuits detection to `"none"` (set by `agy` on child processes; gemini CLI deprecated, replaced by `agy`). Rationale: a fresh subprocess of the host CLI has independent context — running it as a reviewer is valid and adds signal. `--skip-self` honoured only for the auto-resolved set; explicit `--reviewers` always wins. Don't reintroduce a default skip without discussion (see chat 2026-05-03).
- **Dual failure classification**: a reviewer fails if rc ≠ 0 OR captured output < `FAILURE_MIN_BYTES` (50). Don't weaken either check — both have caught real breakage. Partial failures still produce `REVIEW.md`; failed reviewers get their own section with stderr tail (last 2000 chars) and up to 1000 chars of any partial output.
- **Injection posture**: inline context content is wrapped in `<file-NONCE>` tags with a preamble telling the model to treat it as review data. Input files are manifested; contents returned by file-reading tools are still review data, not instructions. Synthesis input wraps each review in `<review reviewer="…">`. `html.escape(..., quote=True)` is used on inline-context attribute values. This is defense-in-depth, not a sandbox.
- **agy is an agentic, uncontained reviewer, and now runs with `--dangerously-skip-permissions` unconditionally.** Unlike the `claude` reviewer agent (restricted to `Read/Grep/Glob`, no Bash — spec §5.2), `agy --print` runs as an autonomous agent: to read its prompt file it uses tools. An earlier observation (pre-2026-08-03) noted agy running `pytest` and grepping the repo unprompted without this flag — that was stale. Verified live 2026-08-03 against agy 1.1.10: in `--print` (headless) mode, agy auto-denies ANY tool needing a permission it can't interactively prompt for, deterministically — even a trivial file read fails every time without `--dangerously-skip-permissions`, since headless mode has no human to approve it. Since agy's real invocation must read at minimum its own prompt file, **every agy review failed this way until the flag was added** (`CLI_SPEC["agy"]["bypass_perms_flag"]`, appended in `build_command` right after the prompt instruction — never between `--print` and the prompt, which silently swallows whatever token lands there instead of the real prompt; confirmed live for this exact flag, not just the pre-existing `--model` case). This makes agy's reviews richer but means agy can now unconditionally execute commands on the working tree during a review — an injection in adversarial review material could weaponise that, more directly than before. Acceptable for reviewing your own code; **do not point agy at untrusted code** until the bwrap/`--sandbox` containment in BACKLOG lands, at which point revisit gating `bypass_perms_flag` on real containment being active for that invocation instead of unconditional. `AgyAdapter.get_response_text` trims agy's step-narration preamble down to the first `## Summary` heading so it doesn't pollute REVIEW.md.
- **`claude -p` through the headless driver is uncontained too.** The skill's `claude` reviewer runs
  as a Task subagent restricted to `Read`/`Grep`/`Glob` (spec §5.2). `multi_review.py`
  (the headless driver) dispatches it as `claude -p` through the same in-process fanout as every
  other reviewer, with its full default toolset — a fifth uncontained, agentic reviewer, same posture
  as agy/pykrete/grok. **Do not point the driver at untrusted code** until the bwrap/`--sandbox`
  containment in BACKLOG lands.
- **pykrete is a default-on reviewer** — it's in `DEFAULT_REVIEWERS` alongside agy, not merely in `ALL_REVIEWERS` (grok is in `ALL_REVIEWERS` too and is NOT default-on — see the opt-in split below). Running an uncontained, agentic reviewer (see below) by default is an accepted trade-off, same posture as agy.
- **Per-CLI `success_exit_codes`.** `CLI_SPEC[cli].get("success_exit_codes", (0,))` — most CLIs succeed only on exit 0; pykrete's is `(0, 3)` (3 == success via NanoGPT model downgrade). This widens which exit codes count as success but does NOT weaken the byte floor: `reviewer_ok` still requires `len(text) >= FAILURE_MIN_BYTES` regardless of which success code fired.
- **Config errors become recorded failures, never escape the fanout.** A missing `$PYKRETE_CONFIG` raises `ValueError` inside `build_command`; `run_reviewer` catches it and returns a failed `ReviewerResult` rather than letting the exception propagate. Critical because pykrete runs by default — an unconfigured pykrete must not crash the whole run, just its own section.
- **Downgrade (exit 3).** Fanout treats pykrete exit 3 as success and sets `ReviewerResult.downgraded`; `spawn` serializes that informational field into state JSON. Because pykrete only reports a *family*, not the model NanoGPT actually routed to, the family-prefixed `final_model` remains (`records_family_not_model` in `CLI_SPEC`) instead of fabricating a specific model name. `aggregate` does not read `.downgraded`; the deleted comparison-eligibility logic must stay deleted.
- **pykrete is agentic/uncontained** (wraps the `pi` agent) — same posture as agy above: **do not point pykrete at untrusted code** until the bwrap/`--sandbox` containment in BACKLOG lands.
- **`task` reaches pykrete as `--task`.** pykrete's lead model comes from `[defaults.<task>].<family>`; without the flag it always resolves `general`. `CLI_SPEC["pykrete"]["task_flag"]` plus SKILL.md Step 5's unconditional `<TASK_FLAG>` carry it. Task names go verbatim except `generic`, aliased to pykrete's own `general` via `task_aliases` — same concept, and users write `[defaults.general]`. pykrete's task vocabulary is open (any `[defaults.*]` key); unknown tasks warn on stderr and fall back, never touching stdout. Synthesis never passes `--task` (`build_command(streaming=False)` leaves `task=None`).
- **`--family`, not `--model`.** pykrete's `model_flag` is `--family`; `models: {pykrete: <family>}` in the YAML prompt schema names a NanoGPT family (e.g. `glm`), not a specific pinned model — pykrete resolves the actual model within that family itself.
- **Context files always inline.** Context files are wrapped in `<file-NONCE>` tags because they're framing material the model needs *before* any tool call, so they cannot be deferred to the manifest. The tool-read preamble (`reference_preamble`) stacks *after* the nonce-tag preamble (`injection_preamble`); both apply because input and context use distinct delivery channels.
- **Two summary-sentinel regexes, one per job — never re-merge them.** `SUMMARY_PRESENT_RE` (unanchored) is the *gate* used by `classify_review_ok`; `SUMMARY_HEADING_RE` (anchored, `MULTILINE` `^`) is the *trim* used by `AgyAdapter.get_response_text` and `write_task_result`. Opposite risk profiles: the gate returns a boolean, so a false accept only renders a visibly-junk section; the trim slices `text[m.start():]`, so a false match silently destroys real analysis (e.g. latching onto the `## Summary` headings quoted inside `prompt.py`'s own `TEMPLATES`). They were one constant until 2026-07-31; the anchored form asserted more than the output contract can deliver — every observed violation (agy narration, claude Task narration, grok's newline-less glue) had the heading **present but not at a line start**, and a false demotion renders the review as a failure section. Guide reviewers on presence, gate on presence; only trim on position.
- **The gate runs after synthesis, so it saves no tokens.** `classify_review_ok` is called only by `aggregate` (SKILL.md Step 7). `build_synthesis_input` (Step 6) filters on the raw `state.json` `ok` (rc + `FAILURE_MIN_BYTES`), so a demoted review has *already* reached the synthesizer. Reviewer narration is therefore handled by instruction, not code — a one-line "ignore narration" rule that must exist in BOTH `synthesis_prompt` (subprocess synthesizers) and `agents/multi-review-synthesizer.md` (the claude synthesizer, which never reads `synthesis_prompt`). Pinned by `test_both_synthesis_paths_carry_the_narration_rule`.
- **Exit codes**: `0` ≥1 reviewer succeeded, `1` all failed or none available, `2` argparse error.
- **Output paths never overwrite by default.** `resolve_output_path` auto-suffixes (`-2`, `-3`, …) when the target exists. `mr-aggregate --force` is the explicit overwrite escape hatch; do not use it in the skill's normal workflow. Don't reintroduce silent overwrite.
- **Single-attempt reviewer runs.** 429 → fail clean. A quota-proximity probe remains deferred (see BACKLOG).
- **Timeout default is `None` (no timeout).** `--timeout` unset → `run_reviewer` / `_run_synthesis_attempt` / `suggest_filename_haiku` await without imposing a deadline. Frontier models on big prompts routinely exceed any sensible default; users opt in to a kill-on-exceed deadline with `--timeout N`. Don't reintroduce a wall-clock default. Explicit timeouts include `kill_proc` teardown after the deadline. Historical 2026-05-01 evidence measured +3–9s total elapsed slop on codex, opencode, and the now-removed Gemini reviewer; treat that evidence as closed until reproduced with the current implementation and supported reviewer set.
- **`ALL_REVIEWERS` is the known/valid set; `DEFAULT_REVIEWERS` is the auto-selected set.** Membership in the first makes a reviewer nameable (prompt-YAML `reviewers`/`synthesizer`, `spawn --cli`, `--list-reviewers` probing); membership in the second makes it default-on. `resolve_reviewers`'s non-explicit base and `promptfile`'s TWO default sites (the dataclass `default_factory` and `fill_defaults` — they are independent) are the ONLY consumers of `DEFAULT_REVIEWERS`; every other consumer means "is this a real reviewer?" and must stay on `ALL_REVIEWERS`. `detect_available()` deliberately probes `ALL_REVIEWERS` so `--list-reviewers` reports opt-in reviewers too.
- **The Python split is NOT the whole opt-in enforcement — two prose sites are load-bearing.** `resolve_reviewers` has no executable caller outside tests: the live path is the `multi-review-build` agent authoring an explicit `reviewers` list, which bypasses `fill_defaults` entirely. So opt-in actually rests on (1) the agent's autonomous `--use-defaults` list at `agents/multi-review-build.md`, and (2) `SKILL.md`'s dispatch instructions, which must name `resolved.reviewers` — an unqualified "dispatch every non-claude reviewer" can be satisfied from `ALL_REVIEWERS` or the `--list-reviewers` probe, both of which contain grok. Both are pinned by `tests/integration/test_skill_contract.py`. Don't edit either without updating the constant, and don't delete the tests.
- **No test may write into the live checkout.** Any test that stages an install must copy under `tmp_path`, never the real tree. A session-scoped autouse fixture in `tests/conftest.py` snapshots the obsolete config path, restores it, and fails the run on any mutation — ordering-independent by design; don't demote it to a per-test assertion.
- **Those contract tests assert the REPO copy, not the installed one.** `../install.py` *copies* the skill into `~/.claude`/`~/.agents/skills` (symlink only under `--dev`), so a green suite does not prove the artifacts Claude Code/Codex actually load are current. Re-install after changing either file, and treat any manual smoke of skill/agent behaviour as invalid until you have.
- **grok is opt-in** — in `ALL_REVIEWERS` but NOT `DEFAULT_REVIEWERS`. Unlike agy/pykrete it never runs unless explicitly named. Don't "helpfully" add it to a default set; that reverses a deliberate decision (2026-07-19).
- **grok's prompt reaches stdin via `--prompt-file /dev/stdin`, not a sentinel.** grok has no `-` stdin sentinel, so `CLI_SPEC["grok"]["base"]` names `/dev/stdin` as the prompt file and `stdin_sentinel` is `None`; the pipe `fanout.py` already writes to is what `/dev/stdin` resolves to. Only the literal string `/dev/stdin` reaches `/proc/PID/cmdline`, so the stdin invariant holds with no `argv_file` workaround. Don't add a `-` sentinel — grok would read it as a stray positional prompt. Assumes a Linux `/dev/stdin` (repo targets Linux/WSL).
- **grok's output format is mode-dependent, and the test shim must mirror that.** The reviewer path passes `--output-format streaming-json` (JSONL → `GrokAdapter`); the synthesis path builds with `streaming=False`, passes no format flag, and `synthesis.py` takes stdout verbatim as the synthesis body with no adapter involved. `run_synthesis` only checks rc and byte count, so a leaked streaming flag would silently make the JSONL envelope the "synthesis". `tests/fixtures/bin/grok` branches on `--output-format` precisely so that regression fails a test.
- **grok's clean `stopReason` has two spellings — compare normalised, never exact.** `EndTurn` (fixture `tests/fixtures/streams/grok/success.jsonl`, older build) and `end_turn` (grok 0.2.117, 2026-08-03). `GrokAdapter` normalises (`str(stop).replace("_","").lower() != "endturn"`) because `fanout.py` computes `ok = base_ok and not adapter.last_error` — an exact match against one spelling silently recorded **every successful grok review** as a failure, truncating a complete review into `partial` and rendering a false failure section. Any *other* stopReason still surfaces verbatim: a refusal/abort appears there and nowhere else (grok exits 0 either way), so don't loosen further. The adapter's consumed-type list is a snapshot, not a contract — 0.2.117 also emits `available_commands` and a standalone `usage` event, both inert because unrecognised types hit no branch. Don't rewrite `feed_line` as an exhaustive match.
- **grok emits no tool-call events.** Verified against both `--output-format streaming-json` and `json`: the complete *observed* event vocabulary is `thought` / `text` / `end` (an `error` branch exists defensively for an event type never seen in probing), even on runs where tools demonstrably executed (`num_turns > 1`). `GrokAdapter` leaves `usage.tool_calls` at 0. **That 0 is an unavailable sentinel, not a measured zero.** Don't synthesise `tool_calls` from `num_turns` — that fabricates a metric.
- **grok's `end` event usage is absolute, not a delta.** `GrokAdapter` assigns (`=`) rather than accumulates (`+=`), unlike `OpenCodeAdapter`'s per-step deltas. `cached_tokens` maps from `cache_read_input_tokens`, a key name unique to grok. The adapter also guards `isinstance(ev, dict)` and string payloads: valid-but-non-object JSON would otherwise raise `AttributeError` inside the drain task and kill the review mid-stream.
- **`--sandbox workspace` is fenced writes, not containment.** Reads are unrestricted under that profile (verified: sandboxed grok read a file outside its `--cwd`), so manifested files outside cwd remain readable. It puts grok level with codex's implicit `workspace-write` default rather than with agy/pykrete's no-profile posture — it is NOT a security boundary. **grok is agentic and uncontained: do not point it at untrusted code** until the bwrap work in BACKLOG lands. grok refuses to start rather than run unsandboxed if a named profile is missing, so a broken profile fails loudly.

### Synthesis caveat (documented in README)

When `--synthesizer` is also a reviewer, that model is double-weighted. The synthesizer call uses the CLI name directly regardless of the reviewer list, so it works whether or not the host was dropped via `--skip-self`. Don't "fix" double-weighting by auto-excluding the synthesizer from reviewers without discussion — the README explicitly calls this out as user choice.

## Adapter schema drift

Upstream event schemas change without notice, and an adapter that silently mis-parses produces a plausible-looking wrong review. Two live examples are pinned in the invariants above: grok's `stopReason` spelling flip (`EndTurn` → `end_turn`) and its absolute-vs-delta usage accounting. Keep every adapter defensive — unrecognised event types must hit no branch — and re-check `tests/fixtures/streams/` against a real run after any CLI upgrade.

(The deleted `GeminiAdapter` carried the original version of this warning: it keyed text accumulation off `ev.get("delta")` and would have double-counted if that flag ever vanished.)
