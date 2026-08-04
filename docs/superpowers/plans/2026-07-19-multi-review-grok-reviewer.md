# Grok Reviewer (opt-in) Implementation Plan

> **Archival.** Historical record of the work as planned. Line references point at the pre-split `multi_review.py` and may not match current code. Current behaviour lives in `CLAUDE.md`, `README.md` and `skills/multi-review/SKILL.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `grok` (xAI Grok Build CLI) as a **sixth, opt-in** reviewer — valid everywhere a reviewer or synthesizer can be named, but never auto-selected.

**Architecture:** Grok is invoked headless as `grok --sandbox workspace --prompt-file /dev/stdin --output-format streaming-json`. The prompt arrives on the child's stdin pipe, which `/dev/stdin` resolves to — so the existing stdin delivery path in `fanout.py` works unchanged and no `argv_file` workaround is needed. A new `GrokAdapter` parses grok's JSONL event stream (`thought` / `text` / `end`). Opt-in is achieved by splitting the single `ALL_REVIEWERS` constant into a **known/valid** set (`ALL_REVIEWERS`, gains grok) and a **default** set (`DEFAULT_REVIEWERS`, does not).

**Tech Stack:** Python 3.11+, `uv`, pytest. No new dependencies.

**Revision note (rev 6, final):** round 5 (the agreed cap) found two MEDIUMs: resume re-read the *current* YAML rather than guaranteeing pass 1's configuration (added a SHA-256 integrity check), and the manual failure smoke asserted a bare `REVIEW.md` that no code path writes (`SKILL.md:191` writes `REVIEW-<slug>.md`). Both fixed.

**Revision note (rev 5):** round 4 found that rev 4's resume fix was itself broken two ways — copying the prompt YAML re-bases relative `files:` paths (`promptfile.py:99`), and the target directory does not exist under `if_drift: ignore` (`snapshot.py:28`). Replaced the copy with a pointer file validated in place, plus an explicit `mkdir -p` and `mode == both` guard.

**Revision note (rev 4):** round 3 found that rev 3's new resume instruction depended on a `pending/<pair_id>/` prompt artifact that **nothing in the repo writes** — a self-inflicted gap. Task 4 now persists it during pass 1 and hard-stops on resume if absent. Also: the synthesis *model* lookup was left unqualified, and the contract test claimed to pin more sites than it asserted; both corrected.

**Revision note (rev 3):** round 2 (2 reviewers, scoped to rev-2's own changes) surfaced 5 further verified findings, all folded in — the largest being that rev 2 **declared** `validate_prompt`'s `resolved` object authoritative but left every actual dispatch instruction in `SKILL.md` unqualified (`SKILL.md:103`, "dispatch every non-claude reviewer"), and left the `--resume-pair` path with no `resolved` object at all. Task 4 now pins both prose control-plane sites. Also corrected: the claim that these tests enforce the *live* path — `setup.py` copies rather than symlinks, so they guard the repo copy and the manual smoke must reinstall first.

**Revision note (rev 2):** rev 1 was reviewed by a 4-reviewer codex panel (holistic, adversarial, opt-in-split specialist, adapter/invocation specialist). 12 verified findings are folded in; the largest are (a) **no automated coverage of grok as a synthesizer**, and a test shim that emitted JSONL unconditionally so it could not have caught it; (b) **the telemetry entry could be omitted with the whole suite green**, because `harvest.py:123` silently defaults unknown reviewers to `"degraded"`; (c) **the live opt-in path is the builder agent's hardcoded default at `agents/multi-review-build.md:40`, not `resolve_reviewers`** — which has no executable caller outside tests — so the Python-side split alone does not enforce the user requirement; (d) the `PromptFile` dataclass default was changed but never exercised. Six findings were **refuted or narrowed on scope** — see "Review provenance" at the end.

## Global Constraints

- **Prompt goes on stdin, never argv.** grok satisfies this natively: only the literal string `/dev/stdin` reaches `/proc/PID/cmdline`, never prompt bytes. Do NOT switch grok to `-p <PROMPT>` or `argv_file` delivery — inline-mode prompts embed file contents and would exceed `MAX_ARG_STRLEN` (128 KiB → `E2BIG`).
- **Opt-in means opt-in, and the enforcement point is not only Python.** grok must be absent from every auto-selected set — `DEFAULT_REVIEWERS`, `PromptFile.reviewers`'s default, `fill_defaults`, **and the `multi-review-build` agent's autonomous `--use-defaults` list** — while present in every *valid choice* set (prompt-YAML `reviewers`, `synthesizer`, `spawn --cli`, `--list-reviewers` probe).
- **Dual failure classification unchanged.** A reviewer fails if rc ∉ its success set OR captured output < `FAILURE_MIN_BYTES` (50). grok gets no `success_exit_codes` override — it succeeds only on 0.
- **No `records_family_not_model` for grok.** grok reports real model IDs (`grok-4.5-build`); record models honestly, not `family:…`.
- **`--sandbox workspace` is a fenced-writes flag, not a security boundary.** Reads are unrestricted under it; writes are confined to cwd + tmp. grok keeps the same "agentic — do not point at untrusted code" warning as agy/pykrete.
- **Linux-only assumption:** `/dev/stdin` must exist. The repo already targets Linux/WSL; record the assumption, do not add a portability shim.
- **Do not touch `--effort` plumbing.** `spawn.py` accepts `--effort` and prints a no-op note for *all* CLIs. grok has `--reasoning-effort`, but wiring effort through `CLI_SPEC` is a cross-cutting change for a separate task — BACKLOG it.
- **Do not attempt the pre-existing fanout stdin-lifecycle fix in this plan.** It is real, cross-cutting, and out of scope — see "Refuted / deferred findings".
- Commit messages end with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Baseline test command: `uv run pytest tests/ -q`. Current suite: **186 passing**. Never leave it red.

## Verified Facts (probed against the installed CLI, 2026-07-19)

These were established empirically. Do not re-derive them; do not "fix" the plan to match a guess.

| Fact | Evidence |
|---|---|
| `grok --prompt-file /dev/stdin` reads the prompt from a pipe, runs single-turn, exits rc=0 | piped a prompt, got a clean response, rc=0 |
| `--output-format streaming-json` emits JSONL with types `thought`, `text`, `end` — **and nothing else** | counted event types over a tool-using run: `Counter({'thought': 40, 'text': 14, 'end': 1})` |
| **No tool-call events exist** in `streaming-json` or `json` output, even when tools ran (`num_turns: 2`) | same run; `tool_calls` telemetry is therefore unavailable |
| The `end` event carries complete token usage | `{"type":"end","stopReason":"EndTurn","usage":{"input_tokens":12941,"cache_read_input_tokens":5376,"output_tokens":31,"reasoning_tokens":25,"total_tokens":18348},"num_turns":1,"modelUsage":{"grok-4.5-build":{...}}}` |
| Default output format (`plain`, used by the synthesis path with `streaming=False`) is clean markdown — no narration, no ANSI | asked for a `## Summary` doc; stdout was exactly the document, stderr empty |
| `--sandbox workspace` resolves (built-in profile) and does **not** block reads outside cwd | with `--cwd /tmp/grokprobe`, grok read `~/kramtime/multi-review/README.md` and returned its first line |
| grok refuses to start rather than run unsandboxed when a *named* profile is missing | `--sandbox bogus-profile` → "refusing to start rather than run unsandboxed" |
| grok is agentic and auto-approves tools in headless mode (no `--always-approve` needed) | it ran a directory listing unprompted |

Additionally verified against the repo during review (rev 2):

| Fact | Evidence |
|---|---|
| `adapter.last_error` has **zero** consumers repo-wide | only its definition at `adapters.py:40` |
| `harvest.py:123` is `TELEMETRY_QUALITY.get(r.cli, "degraded")` — a missing entry is silent | source |
| `resolve_reviewers` has no executable caller outside tests; the skill fans out over the YAML's resolved `reviewers` | `rg` across `multi_review/`, `skills/`, `agents/` |
| `validate_prompt` already emits the fully-defaulted object as `{"ok": true, "resolved": {...}}` | `validate_prompt.py:19` |
| `resolve_reviewers` does not validate explicit names against any set | `reviewers.py:60-72` — it filters only on `available` |

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `multi_review/core/adapters.py` | modify | `GrokAdapter` + `ADAPTER_FOR` / `__all__` registration |
| `tests/fixtures/streams/grok/success.jsonl` | create | Captured real grok event stream for replay tests |
| `tests/unit/test_adapters.py` | modify | GrokAdapter unit tests |
| `multi_review/core/reviewers.py` | modify | `DEFAULT_REVIEWERS` split, `CLI_SPEC["grok"]`, `resolve_reviewers` base |
| `multi_review/core/promptfile.py` | modify | defaults from `DEFAULT_REVIEWERS`; valid set stays `ALL_REVIEWERS` |
| `tests/unit/test_reviewers.py` | modify | opt-in + argv-shape tests; strengthen the pykrete both-sets test |
| `tests/unit/test_promptfile.py` | modify | grok valid-but-not-default tests, dataclass default, negative valid-set tests |
| `multi_review/core/harvest.py` | modify | `TELEMETRY_QUALITY["grok"]` |
| `tests/unit/test_harvest.py` | modify | telemetry regression test |
| `tests/fixtures/bin/grok` | create | Discriminating fake grok binary (mode-branching) |
| `tests/integration/test_grok_spawn.py` | create | End-to-end spawn-CLI tests, review **and** synthesize |
| `tests/integration/test_skill_contract.py` | modify | Static guard on the builder agent's autonomous default |
| `README.md`, `CLAUDE.md`, `skills/multi-review/SKILL.md`, `agents/multi-review-build.md`, `BACKLOG.md`, `tests/manual/pykrete-smoke.md`, `tests/manual/skill-step5-join.md` | modify | Docs + invariants |
| `tests/manual/grok-smoke.md` | create | Live smoke procedure |

**Task order rationale:** Task 1 (adapter) comes before Task 2 (`CLI_SPEC`) deliberately. `spawn.py` calls `make_adapter(args.cli)`, which does `ADAPTER_FOR[cli]()` — adding `"grok"` to `ALL_REVIEWERS` (which is `spawn.py`'s `--cli` choices list) before the adapter exists would make `--cli grok` raise `KeyError`. Adapter first keeps every task independently green.

---

### Task 1: GrokAdapter

**Files:**
- Modify: `multi_review/core/adapters.py` (append class after `PykreteAdapter`, before the `ADAPTER_FOR` dict; then edit `ADAPTER_FOR` and `__all__`)
- Create: `tests/fixtures/streams/grok/success.jsonl`
- Test: `tests/unit/test_adapters.py`

**Interfaces:**
- Consumes: `ProgressAdapter`, `Usage` from `multi_review.core.adapters` (already in the file).
- Produces: `GrokAdapter` class; `ADAPTER_FOR["grok"] is GrokAdapter`. Instances expose `.text` (str), `.usage` (`Usage`), `.phase` (str), `.last_error` (str | None) — the base-class contract.

**Design notes for the implementer:**
- `thought` events are grok's reasoning narration. They are **not** part of the review body — do not append them to `text_parts`. They *are* a liveness signal, so they set `phase = "thinking"`. **The phase vocabulary for grok is `starting` → `thinking` → `running` → `done` / `error`.** (rev 1 said `thought` should set `"running"`; that contradicted its own code. `"thinking"` wins — it carries strictly more information for the dashboard, and a test now pins it.)
- The `end` event's `usage` is **absolute (cumulative for the whole run), not a delta**. Assign with `=`, do not accumulate with `+=`. (Contrast `OpenCodeAdapter`, which accumulates per-step deltas.)
- `cached_tokens` maps from `cache_read_input_tokens` — the key name differs from every other adapter.
- `tool_calls` stays 0: grok emits no tool events in either output format (see Verified Facts). Do not invent a heuristic (e.g. counting `num_turns`) to populate it — that would be a fabricated metric.
- **Guard types, not just JSON syntax.** `json.loads` happily returns `None`, `[]`, or `"banner"` for valid non-object JSON, and `ev.get(...)` then raises `AttributeError`, killing the drain task. A `text` event with `"data": null` would append `None` and make the inherited `"".join(self.text_parts)` raise later at `adapters.py:45`. Both are cheap to prevent; the plan claims defensiveness, so make the claim true.
- `last_error` is written for parity with the base-class contract, but **nothing in the repo reads it today** (verified). Do not build behaviour on it.

- [ ] **Step 1: Write the fixture**

Create `tests/fixtures/streams/grok/success.jsonl` with exactly this content (real captured events, trimmed):

```
{"type":"thought","data":"The"}
{"type":"thought","data":" user"}
{"type":"thought","data":" wants a review."}
{"type":"text","data":"## Summary\n"}
{"type":"text","data":"\nThe module is sound; two edge cases are unhandled.\n"}
{"type":"end","stopReason":"EndTurn","sessionId":"019f79a1-4f5f-7192-a991-9259d21f06d5","requestId":"775cb133-75ee-4375-850b-1c7da4015625","usage":{"input_tokens":12941,"cache_read_input_tokens":5376,"output_tokens":31,"reasoning_tokens":25,"total_tokens":18348},"num_turns":1,"total_cost_usd":0.0276808,"modelUsage":{"grok-4.5-build":{"inputTokens":12941,"outputTokens":31,"cacheReadInputTokens":5376,"modelCalls":1,"costUSD":0.0276808}}}
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/unit/test_adapters.py`:

```python
def test_grok_adapter_success_fixture():
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    _feed(a, FIX / "grok" / "success.jsonl")
    assert a.text.startswith("## Summary")
    assert "two edge cases are unhandled" in a.text


def test_grok_adapter_excludes_thought_narration():
    """thought events are reasoning narration, not review body."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    _feed(a, FIX / "grok" / "success.jsonl")
    assert "The user wants a review." not in a.text
    assert "wants" not in a.text


def test_grok_adapter_phase_transitions():
    """Pinned contract: starting -> thinking -> running -> done."""
    import json
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    assert a.phase == "starting"
    a.feed_line(json.dumps({"type": "thought", "data": "hm"}))
    assert a.phase == "thinking"
    a.feed_line(json.dumps({"type": "text", "data": "body"}))
    assert a.phase == "running"
    a.feed_line(json.dumps({"type": "end", "stopReason": "EndTurn", "usage": {}}))
    assert a.phase == "done"


def test_grok_adapter_end_event_usage_is_absolute():
    import json
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    end = {"type": "end", "stopReason": "EndTurn",
           "usage": {"input_tokens": 100, "cache_read_input_tokens": 10,
                     "output_tokens": 50, "reasoning_tokens": 5,
                     "total_tokens": 165}}
    a.feed_line(json.dumps(end))
    a.feed_line(json.dumps(end))          # a second end must not double-count
    assert a.usage.input_tokens == 100
    assert a.usage.output_tokens == 50
    assert a.usage.cached_tokens == 10    # from cache_read_input_tokens
    assert a.usage.tool_calls == 0        # grok emits no tool events


def test_grok_adapter_survives_malformed_and_non_object_lines():
    """Valid-but-non-object JSON must not raise: ev.get() on a list/str/None
    would AttributeError and kill the drain task mid-review."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    for bad in ('not json at all', 'null', '[]', '"banner"', '42'):
        a.feed_line(bad)
    a.feed_line('{"type":"text","data":"ok"}')
    assert a.text == "ok"


def test_grok_adapter_ignores_non_string_text_payload():
    """data: null must not enter text_parts — "".join() would raise later."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    a.feed_line('{"type":"text","data":null}')
    a.feed_line('{"type":"text","data":"real"}')
    assert a.text == "real"


def test_grok_adapter_ignores_non_dict_usage():
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    a.feed_line('{"type":"end","stopReason":"EndTurn","usage":"nope"}')
    assert a.usage.input_tokens == 0


def test_grok_adapter_coerces_bad_token_counters():
    """Usage declares ints. A drifted counter (null / string / object / bool /
    negative) must not reach <cli>.state.json or the harvest row as a non-int."""
    from multi_review.core.adapters import GrokAdapter
    a = GrokAdapter()
    a.feed_line('{"type":"end","stopReason":"EndTurn","usage":'
                '{"input_tokens":null,"output_tokens":"12",'
                '"cache_read_input_tokens":{"nested":1}}}')
    assert a.usage.input_tokens == 0
    assert a.usage.output_tokens == 0
    assert a.usage.cached_tokens == 0
    for v in a.usage.as_dict().values():
        assert isinstance(v, int) and not isinstance(v, bool)


def test_grok_registered():
    from multi_review.core.adapters import ADAPTER_FOR, GrokAdapter
    assert ADAPTER_FOR["grok"] is GrokAdapter
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_adapters.py -q -k grok`
Expected: FAIL — `ImportError: cannot import name 'GrokAdapter'` (9 errors).

- [ ] **Step 4: Write the implementation**

In `multi_review/core/adapters.py`, insert this class immediately after `PykreteAdapter` and before the `ADAPTER_FOR` dict:

```python
def _int0(v) -> int:
    """Token counters only. Non-int (null, str, dict from a drifted schema) -> 0.

    bool is excluded deliberately: it is an int subclass, and True would
    silently become a token count of 1.
    """
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0


class GrokAdapter(ProgressAdapter):
    """grok --output-format streaming-json.

    Event types (the complete set — verified against grok Build TUI 2026-07):
      {"type":"thought","data":str}  reasoning narration; liveness only, NOT body
      {"type":"text","data":str}     response body deltas
      {"type":"end", usage:{...}}    terminal; usage is ABSOLUTE, not a delta

    grok emits no tool-call events in any output format, so usage.tool_calls
    stays 0. Don't synthesise it from num_turns — that would be a made-up metric.

    Type guards are load-bearing, not decoration: json.loads returns None/list/
    str for valid non-object JSON, and ev.get() on those raises AttributeError
    inside the drain task, killing the review mid-stream.
    """

    def feed_line(self, line: str) -> None:
        super().feed_line(line)
        line = line.strip()
        if not line:
            return
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            return
        if not isinstance(ev, dict):
            return
        t = ev.get("type")
        if t == "thought":
            self.phase = "thinking"
        elif t == "text":
            self.phase = "running"
            data = ev.get("data")
            if isinstance(data, str):
                self.text_parts.append(data)
        elif t == "end":
            # Absolute totals for the whole run — assign, never accumulate.
            # Coerce per counter: Usage declares ints, and a drifted schema
            # (null, a string, a nested object) would otherwise flow straight
            # into <cli>.state.json and the harvest row as a non-int.
            u = ev.get("usage")
            if isinstance(u, dict):
                self.usage.input_tokens = _int0(u.get("input_tokens"))
                self.usage.output_tokens = _int0(u.get("output_tokens"))
                self.usage.cached_tokens = _int0(u.get("cache_read_input_tokens"))
            self.phase = "done"
            stop = ev.get("stopReason")
            if stop and stop != "EndTurn":
                self.last_error = f"stopReason={stop}"
        elif t == "error":
            self.phase = "error"
            self.last_error = str(ev.get("message") or ev.get("error") or "error")
```

Then register it. Change the `ADAPTER_FOR` dict:

```python
ADAPTER_FOR = {
    "claude": ClaudeAdapter,
    "agy": AgyAdapter,
    "codex": CodexAdapter,
    "opencode": OpenCodeAdapter,
    "pykrete": PykreteAdapter,
    "grok": GrokAdapter,
}
```

And add `"GrokAdapter",` to `__all__`, immediately after `"PykreteAdapter",`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_adapters.py -q`
Expected: PASS, all adapter tests green (9 new).

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: 195 passed.

- [ ] **Step 7: Commit**

```bash
git add multi_review/core/adapters.py tests/unit/test_adapters.py tests/fixtures/streams/grok/success.jsonl
git commit -m "$(cat <<'EOF'
feat(grok): GrokAdapter for streaming-json event stream

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Opt-in reviewer split + CLI_SPEC entry

**Files:**
- Modify: `multi_review/core/reviewers.py` (module docstring L4; `ALL_REVIEWERS` L20; `resolve_reviewers` L65; `CLI_SPEC` L100-146)
- Modify: `multi_review/core/promptfile.py` (import L8; `PromptFile.reviewers` L22; `_KNOWN_REVIEWERS` comment L33; `fill_defaults` L47)
- Test: `tests/unit/test_reviewers.py`, `tests/unit/test_promptfile.py`

**Interfaces:**
- Consumes: `GrokAdapter` registered in `ADAPTER_FOR` (Task 1).
- Produces:
  - `ALL_REVIEWERS: list[str]` — known/valid set, now `["claude", "agy", "codex", "opencode", "pykrete", "grok"]`.
  - `DEFAULT_REVIEWERS: list[str]` — auto-selected set, `["claude", "agy", "codex", "opencode", "pykrete"]` (no grok).
  - `CLI_SPEC["grok"]` with `base = ["grok", "--sandbox", "workspace", "--prompt-file", "/dev/stdin"]`, `stream_flags = ["--output-format", "streaming-json"]`, `model_flag = "--model"`, `stdin_sentinel = None`.
  - `build_command("grok", model, streaming=True)` → argv containing `/dev/stdin` and never the prompt text.

**Design notes for the implementer:**
- `ALL_REVIEWERS` keeps its name and its meaning as the *known/valid* set — every existing consumer that means "is this a real reviewer?" (`promptfile._KNOWN_REVIEWERS`, `spawn.py --cli choices`, `detect_available`) is already correct and must NOT be repointed at `DEFAULT_REVIEWERS`.
- Only three call sites become "default": `resolve_reviewers`'s non-explicit base, and `promptfile`'s two default sites (**the dataclass `default_factory` AND `fill_defaults`** — they are independent; changing only one leaves a hole that `fill_defaults`-based tests cannot see).
- `detect_available()` deliberately keeps scanning `ALL_REVIEWERS` — `--list-reviewers` should report grok's presence/absence even though grok is never auto-selected.
- **grok needs no `stdin_sentinel`.** `/dev/stdin` in `base` already routes the pipe. Adding `-` would pass a stray positional arg that grok would treat as a prompt.
- `--sandbox workspace` goes in `base` so it applies to both the streaming reviewer path and the non-streaming synthesis path.
- No `config_env`, no `success_exit_codes`, no `records_family_not_model` — grok needs none of the pykrete-specific machinery.
- **`resolve_reviewers` does not validate explicit names against any set** (verified: it filters only on `available`). So a test that passes `explicit=["grok"]` proves nothing about grok being *known* — it passes on today's code. The real proof of validity is the `validate()` test in `test_promptfile.py`. The `resolve_reviewers` explicit test is retained only as a regression guard on generic explicit-selection behaviour, and is labelled as such.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_reviewers.py`:

```python
def test_grok_is_known_but_not_default():
    from multi_review.core.reviewers import ALL_REVIEWERS, DEFAULT_REVIEWERS
    assert "grok" in ALL_REVIEWERS          # valid wherever a reviewer is named
    assert "grok" not in DEFAULT_REVIEWERS  # never auto-selected


def test_default_reviewers_is_exactly_the_five():
    from multi_review.core.reviewers import DEFAULT_REVIEWERS
    assert DEFAULT_REVIEWERS == ["claude", "agy", "codex", "opencode", "pykrete"]


def test_resolve_reviewers_never_auto_selects_grok():
    from multi_review.core.reviewers import resolve_reviewers
    chosen = resolve_reviewers(
        explicit=None, skip_self=False, self_cli="",
        available={"claude", "agy", "codex", "opencode", "pykrete", "grok"},
    )
    assert "grok" not in chosen
    assert "claude" in chosen


def test_resolve_reviewers_explicit_selection_still_passes_through():
    """Regression guard on generic explicit-selection behaviour only.

    NOT evidence that grok is a *known* reviewer: resolve_reviewers filters on
    `available` and never checks membership of any reviewer set, so this passes
    for any string. Grok's validity is proved by the validate() test in
    tests/unit/test_promptfile.py.
    """
    from multi_review.core.reviewers import resolve_reviewers
    chosen = resolve_reviewers(
        explicit=["grok"], skip_self=False, self_cli="",
        available={"claude", "grok"},
    )
    assert chosen == ["grok"]


def test_detect_available_probes_grok(monkeypatch):
    """--list-reviewers must report grok's availability even though it is opt-in."""
    import multi_review.core.reviewers as m
    monkeypatch.setattr(m.shutil, "which", lambda c: "/usr/bin/" + c)
    assert "grok" in m.detect_available()


def test_build_command_grok_argv_shape():
    from multi_review.core.reviewers import build_command
    cmd = build_command("grok", model=None, streaming=True)
    assert cmd[0] == "grok"
    # Prompt is delivered via the stdin pipe that /dev/stdin resolves to.
    assert cmd[cmd.index("--prompt-file") + 1] == "/dev/stdin"
    assert cmd[cmd.index("--sandbox") + 1] == "workspace"
    assert cmd[cmd.index("--output-format") + 1] == "streaming-json"
    assert "-" not in cmd            # no stdin sentinel; it would be a stray prompt arg


def test_build_command_grok_model_pin():
    from multi_review.core.reviewers import build_command
    cmd = build_command("grok", model="grok-4.5-build", streaming=True)
    assert cmd[cmd.index("--model") + 1] == "grok-4.5-build"


def test_build_command_grok_synthesis_drops_stream_flags():
    """streaming=False is the synthesis path: plain stdout, still stdin-delivered."""
    from multi_review.core.reviewers import build_command
    cmd = build_command("grok", model=None, streaming=False)
    assert "--output-format" not in cmd
    assert cmd[cmd.index("--prompt-file") + 1] == "/dev/stdin"


def test_grok_has_no_pykrete_machinery():
    from multi_review.core.reviewers import CLI_SPEC
    spec = CLI_SPEC["grok"]
    assert "success_exit_codes" not in spec      # succeeds only on 0
    assert "config_env" not in spec
    assert not spec.get("records_family_not_model")  # grok reports real model IDs
```

**Also modify the existing `test_pykrete_known_and_default`** (`tests/unit/test_reviewers.py:155`). Its name promises "and default" but its only set assertion is `ALL_REVIEWERS` membership — which after the split proves *known* and nothing else. Replace the assertion block:

```python
def test_pykrete_known_and_default():
    from multi_review.core.reviewers import ALL_REVIEWERS, DEFAULT_REVIEWERS, CLI_SPEC
    assert "pykrete" in ALL_REVIEWERS         # known/valid
    assert "pykrete" in DEFAULT_REVIEWERS     # AND default-on (post-split proof)
    assert CLI_SPEC["pykrete"]["success_exit_codes"] == (0, 3)
```

Append to `tests/unit/test_promptfile.py`:

```python
def test_dataclass_default_reviewers_excludes_grok():
    """Direct construction bypasses fill_defaults entirely. Without this test,
    leaving PromptFile.reviewers' default_factory on ALL_REVIEWERS would make
    grok auto-selected for every direct PromptFile(...) while every
    fill_defaults-based test still passed."""
    from multi_review.core.promptfile import PromptFile
    from multi_review.core.reviewers import DEFAULT_REVIEWERS
    pf = PromptFile(prompt_format_version=1, task="code", files=["a.py"])
    assert pf.reviewers == DEFAULT_REVIEWERS
    assert "grok" not in pf.reviewers


def test_grok_omitted_from_filled_defaults():
    from multi_review.core.promptfile import fill_defaults
    pf = fill_defaults({"prompt_format_version": 1, "task": "code",
                        "files": ["a.py"]})
    assert "grok" not in pf.reviewers


def test_grok_is_a_valid_explicit_reviewer_and_synthesizer(tmp_path):
    """fill_defaults does not enforce membership — validate does. Drive validate."""
    from multi_review.core.promptfile import fill_defaults, validate
    (tmp_path / "a.py").write_text("x = 1\n")
    pf = fill_defaults({"prompt_format_version": 1, "task": "code",
                        "files": ["a.py"], "reviewers": ["grok"],
                        "synthesizer": "grok"})
    validate(pf, base_dir=tmp_path)      # must not raise
    assert pf.reviewers == ["grok"]
    assert pf.synthesizer == "grok"


def test_unknown_reviewer_and_synthesizer_still_rejected(tmp_path):
    """Lock the valid set while it is being changed."""
    import pytest
    from multi_review.core.promptfile import fill_defaults, validate, ValidationError
    (tmp_path / "a.py").write_text("x = 1\n")
    bad_rev = fill_defaults({"prompt_format_version": 1, "task": "code",
                             "files": ["a.py"], "reviewers": ["grok3"]})
    with pytest.raises(ValidationError):
        validate(bad_rev, base_dir=tmp_path)
    bad_synth = fill_defaults({"prompt_format_version": 1, "task": "code",
                               "files": ["a.py"], "synthesizer": "grok3"})
    with pytest.raises(ValidationError):
        validate(bad_synth, base_dir=tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_reviewers.py tests/unit/test_promptfile.py -q -k "grok or pykrete or dataclass"`
Expected: FAIL — `ImportError: cannot import name 'DEFAULT_REVIEWERS'` / `KeyError: 'grok'`.

- [ ] **Step 3: Split the reviewer sets**

In `multi_review/core/reviewers.py`, replace line 20:

```python
ALL_REVIEWERS: list[str] = ["claude", "agy", "codex", "opencode", "pykrete"]
```

with:

```python
# Known/valid reviewers: everything nameable in a prompt YAML's `reviewers` or
# `synthesizer`, spawnable via `spawn --cli`, and probed by --list-reviewers.
ALL_REVIEWERS: list[str] = ["claude", "agy", "codex", "opencode", "pykrete", "grok"]

# Auto-selected reviewers: the set used when the user names none. grok is
# OPT-IN — valid everywhere above, never auto-selected. Adding a reviewer here
# makes it default-on (the pykrete posture); leaving it out makes it opt-in.
# NOTE: this constant is not the only default site. agents/multi-review-build.md
# hardcodes the same list for its autonomous --use-defaults selection; the two
# must stay in sync (guarded by tests/integration/test_skill_contract.py).
DEFAULT_REVIEWERS: list[str] = ["claude", "agy", "codex", "opencode", "pykrete"]
```

Then in `resolve_reviewers`, change the base (L65) from:

```python
    base = explicit if is_explicit else list(ALL_REVIEWERS)
```

to:

```python
    base = explicit if is_explicit else list(DEFAULT_REVIEWERS)
```

Leave `detect_available()` on `ALL_REVIEWERS` — availability probing covers opt-in reviewers too.

Update the module docstring's bullet at line 4 from `  - ALL_REVIEWERS list` to:

```
  - ALL_REVIEWERS (known/valid) + DEFAULT_REVIEWERS (auto-selected) lists
```

- [ ] **Step 4: Add the CLI_SPEC entry**

In `multi_review/core/reviewers.py`, add this entry to `CLI_SPEC` immediately after the `"pykrete"` entry:

```python
    "grok": {
        # --prompt-file /dev/stdin: grok has no `-` stdin sentinel, but reading
        # the prompt file from /dev/stdin resolves to the pipe fanout already
        # writes to. Only the literal "/dev/stdin" reaches /proc/PID/cmdline,
        # never prompt bytes — the stdin invariant holds without an argv_file
        # workaround. Assumes a Linux /dev/stdin (repo targets Linux/WSL).
        # --sandbox workspace: fences writes to cwd + tmp; reads stay open so
        # reference-mode manifests outside cwd still work. NOT a security
        # boundary — grok remains agentic/uncontained in posture.
        "base": ["grok", "--sandbox", "workspace", "--prompt-file", "/dev/stdin"],
        "stream_flags": ["--output-format", "streaming-json"],
        "model_flag": "--model",
        "default_args": [],
        "stdin_sentinel": None,   # /dev/stdin in base already routes the pipe
    },
```

No change to `build_command` is required: grok uses the generic path (default `stdin` delivery, no `config_env`).

- [ ] **Step 5: Point BOTH promptfile default sites at DEFAULT_REVIEWERS**

In `multi_review/core/promptfile.py`, change the import (L8) from:

```python
from multi_review.core.reviewers import ALL_REVIEWERS
```

to:

```python
from multi_review.core.reviewers import ALL_REVIEWERS, DEFAULT_REVIEWERS
```

Change the dataclass field (L22) from:

```python
    reviewers: list[str] = field(default_factory=lambda: list(ALL_REVIEWERS))
```

to:

```python
    reviewers: list[str] = field(default_factory=lambda: list(DEFAULT_REVIEWERS))
```

Change the `_KNOWN_REVIEWERS` comment (L33) to make the split explicit:

```python
_KNOWN_REVIEWERS = set(ALL_REVIEWERS)  # valid set (includes opt-in reviewers like grok)
```

Change `fill_defaults` (L47) from:

```python
    raw.setdefault("reviewers", list(ALL_REVIEWERS))
```

to:

```python
    raw.setdefault("reviewers", list(DEFAULT_REVIEWERS))
```

Leave `_VALID_SYNTHESIZERS` alone — it derives from `_KNOWN_REVIEWERS`, so grok becomes a valid synthesizer automatically.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_reviewers.py tests/unit/test_promptfile.py -q`
Expected: PASS. Note `test_fill_defaults_populates_missing` (`tests/unit/test_promptfile.py:30`) still asserts the 5-reviewer list and must stay green unchanged — that is the proof grok did not leak into defaults. If it fails, grok reached a default site; fix the source, not the assertion.

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: 208 passed.

- [ ] **Step 8: Commit**

```bash
git add multi_review/core/reviewers.py multi_review/core/promptfile.py tests/unit/test_reviewers.py tests/unit/test_promptfile.py
git commit -m "$(cat <<'EOF'
feat(grok): opt-in reviewer — split DEFAULT_REVIEWERS from ALL_REVIEWERS

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Telemetry classification + end-to-end spawn tests (review AND synthesize)

**Files:**
- Modify: `multi_review/core/harvest.py` (`TELEMETRY_QUALITY` L34-40)
- Modify: `tests/unit/test_harvest.py`
- Create: `tests/fixtures/bin/grok` (mode 100755)
- Create: `tests/integration/test_grok_spawn.py`

**Interfaces:**
- Consumes: `CLI_SPEC["grok"]` and `DEFAULT_REVIEWERS` (Task 2); `GrokAdapter` (Task 1).
- Produces: `TELEMETRY_QUALITY["grok"] == "known-issues"`; a fake `grok` binary honouring `GROK_ARGV_LOG`, `GROK_STDIN_LOG`, `FAKE_GROK_RC`, `FAKE_GROK_SHORT`, and **branching its output format on `--output-format`**.

**Design notes for the implementer:**
- `"known-issues"` is the honest label: grok's *token* telemetry is complete and reliable (better than agy/pykrete's `"degraded"`), but `tool_calls` is permanently 0 because grok emits no tool events. It is not `"reliable"` — that is reserved for codex, which reports everything. **Record in docs that grok's `tool_calls: 0` is an unavailable sentinel, not a measured zero** — the schema has no way to say "unknown", and a future analyst must not read it as "grok used no tools".
- **A missing `TELEMETRY_QUALITY` entry is silent.** `harvest.py:123` is `TELEMETRY_QUALITY.get(r.cli, "degraded")` — omit the grok entry and every harvest row quietly records the wrong quality while the entire suite stays green. A `python -c` spot-check during implementation does not prevent later regression; the pytest assertion does. This is why Step 1 has a test, not just an edit.
- **The shim must branch on `--output-format`.** The reviewer path passes `--output-format streaming-json` and expects JSONL; the synthesis path (`streaming=False`) passes no such flag and expects clean markdown, which `synthesis.py:105` takes as the synthesis body verbatim with no adapter involved. A shim that emits JSONL unconditionally would let a broken synthesis path pass — `run_synthesis` only checks rc and byte count, so the JSONL envelope itself would sail through as "successful synthesis".
- **The shim reads the path given to `--prompt-file`**, not bare fd 0. At the OS level `cat /dev/stdin` and `cat` are equivalent, so the data transport is faithful either way — but reading the *argument* is what ties the test to the invocation contract. It does not need to be a full argument parser: rejecting unknown flags or pinning exact token order would be brittle without catching more real bugs.

- [ ] **Step 1: Add the telemetry entry and its regression test**

In `multi_review/core/harvest.py`, add to the `TELEMETRY_QUALITY` dict after the `"pykrete"` line:

```python
    "grok": "known-issues",     # tokens complete/reliable; no tool-call events exist
```

Append to `tests/unit/test_harvest.py`:

```python
def test_grok_telemetry_known_issues():
    """Not "reliable" (tool_calls is permanently 0, an unavailable sentinel) and
    not "degraded" (token counts are complete). A missing entry would silently
    fall back to "degraded" via TELEMETRY_QUALITY.get(cli, "degraded")."""
    from multi_review.core.harvest import TELEMETRY_QUALITY
    assert TELEMETRY_QUALITY["grok"] == "known-issues"


def test_build_row_emits_grok_telemetry_quality():
    row = build_row(
        results=[_r("grok")], mode="inline", task="code", project="p",
        wall_seconds=2.0, reviewers_attempted=["grok"],
        synthesizer="claude", synthesis_ok=True,
        pair_id=None, prompt_file="prompts/auth.yaml",
        prompt_format_version=1, drift_status="clean",
        telemetry_notes=None,
    )
    assert row["usage_by_reviewer"]["grok"]["telemetry_quality"] == "known-issues"
```

- [ ] **Step 2: Run the telemetry tests**

Run: `uv run pytest tests/unit/test_harvest.py -q -k grok`
Expected: PASS (2 new). If you skipped the harvest.py edit they fail — which is the point.

- [ ] **Step 3: Write the mode-branching fake grok binary**

Create `tests/fixtures/bin/grok`:

```bash
#!/usr/bin/env bash
# Fake grok. Discriminating shim:
#   - echoes argv one token per line to $GROK_ARGV_LOG
#   - reads the prompt from the path given to --prompt-file (NOT bare fd 0), so
#     the test is tied to the invocation contract; copies it to $GROK_STDIN_LOG
#   - BRANCHES ON --output-format: streaming JSONL for the reviewer path, clean
#     markdown for the synthesis path (which build_command builds with
#     streaming=False and synthesis.py treats as the body verbatim)
#   - FAKE_GROK_RC (default 0) sets the exit code
#   - FAKE_GROK_SHORT=1 emits <50 bytes of body to drive the byte-floor case
set -u
prompt_file=""
streaming=0
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[i]}" in
    --prompt-file) prompt_file="${args[i+1]:-}" ;;
    --output-format) [ "${args[i+1]:-}" = "streaming-json" ] && streaming=1 ;;
  esac
done
[ -n "${GROK_ARGV_LOG:-}" ] && printf '%s\n' "$@" > "$GROK_ARGV_LOG"
if [ -z "$prompt_file" ]; then
  echo "fake grok: no --prompt-file given" >&2
  exit 64
fi
prompt=$(cat "$prompt_file")
[ -n "${GROK_STDIN_LOG:-}" ] && printf '%s' "$prompt" > "$GROK_STDIN_LOG"

if [ "${FAKE_GROK_SHORT:-0}" = "1" ]; then
  body='short'
else
  body='## Summary
Fake grok review body, well over fifty bytes of content here.'
fi

if [ "$streaming" = "1" ]; then
  printf '%s\n' '{"type":"thought","data":"Considering the diff."}'
  printf '{"type":"text","data":%s}\n' "$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
  printf '%s\n' '{"type":"end","stopReason":"EndTurn","usage":{"input_tokens":1200,"cache_read_input_tokens":300,"output_tokens":45,"reasoning_tokens":9,"total_tokens":1554},"num_turns":1,"modelUsage":{"grok-4.5-build":{"inputTokens":1200,"outputTokens":45}}}'
else
  printf '%s\n' "$body"
fi
exit "${FAKE_GROK_RC:-0}"
```

Make it executable:

```bash
chmod +x tests/fixtures/bin/grok
```

- [ ] **Step 4: Write the failing integration tests**

Create `tests/integration/test_grok_spawn.py`:

```python
# tests/integration/test_grok_spawn.py
"""Integration tests driving the real spawn CLI against a discriminating fake
grok binary (tests/fixtures/bin/grok). Exercises argparse, spawn.main, the
GrokAdapter's streaming-json parsing, the non-streaming synthesis path, exit-code
mapping, and <cli>.md/.state.json writing — none of which unit tests on
build_command or the adapter alone would catch if the argv shape, the stdin
wiring, or the review-vs-synthesis output contract drifted.
"""
import json
import os
import subprocess
from pathlib import Path

FIXTURE_BIN = Path(__file__).parent.parent / "fixtures" / "bin"


def _env(extra=None):
    env = {**os.environ, "PATH": f"{FIXTURE_BIN}:{os.environ['PATH']}"}
    if extra:
        env.update(extra)
    return env


def _spawn(tmp_path, prompt_text="review this code please", extra_args=(), env_extra=None):
    prompt = tmp_path / "p.txt"
    prompt.write_text(prompt_text)
    out_dir = tmp_path / "out"
    out_dir.mkdir(exist_ok=True)
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "grok", "--prompt-file", str(prompt),
         "--out-dir", str(out_dir), *extra_args],
        capture_output=True, text=True, env=_env(env_extra),
    )
    return r, out_dir, prompt


def test_review_success_parses_streaming_json(tmp_path):
    r, out_dir, _ = _spawn(tmp_path)
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    state = json.loads(Path(j["state_path"]).read_text())
    assert state["cli"] == "grok"
    assert state["ok"] is True
    assert state["downgraded"] is False
    assert state["final_model"] == "<default>"      # never a "family:" prefix
    assert state["usage"]["input_tokens"] == 1200   # from the end event
    assert state["usage"]["cached_tokens"] == 300
    assert state["usage"]["tool_calls"] == 0
    body = Path(j["review_path"]).read_text()
    assert body.startswith("## Summary")
    assert "Considering the diff." not in body      # thought narration excluded
    assert '"type"' not in body                     # JSONL envelope not leaked


def test_prompt_travels_on_stdin_not_argv(tmp_path):
    """Core invariant: prompt bytes must never reach /proc/PID/cmdline."""
    argv_log = tmp_path / "argv.log"
    stdin_log = tmp_path / "stdin.log"
    secret = "SENTINEL-PROMPT-BODY-must-not-appear-on-argv"
    r, _, _ = _spawn(
        tmp_path, prompt_text=secret,
        env_extra={"GROK_ARGV_LOG": str(argv_log), "GROK_STDIN_LOG": str(stdin_log)},
    )
    assert r.returncode == 0, r.stderr
    argv = argv_log.read_text().splitlines()
    assert secret not in argv_log.read_text()        # prompt not on argv
    assert argv[argv.index("--prompt-file") + 1] == "/dev/stdin"
    assert argv[argv.index("--sandbox") + 1] == "workspace"
    assert argv[argv.index("--output-format") + 1] == "streaming-json"
    assert stdin_log.read_text() == secret           # prompt did arrive on the pipe


def test_model_pin_forwarded_and_recorded(tmp_path):
    argv_log = tmp_path / "argv.log"
    r, out_dir, _ = _spawn(
        tmp_path, extra_args=("--model", "grok-4.5-build"),
        env_extra={"GROK_ARGV_LOG": str(argv_log)},
    )
    assert r.returncode == 0, r.stderr
    argv = argv_log.read_text().splitlines()
    assert argv[argv.index("--model") + 1] == "grok-4.5-build"
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["final_model"] == "grok-4.5-build"  # real model, not "family:..."


def test_synthesize_uses_plain_output_not_jsonl(tmp_path):
    """The synthesis path builds with streaming=False and takes stdout verbatim
    (synthesis.py:105) with no adapter. If the streaming flag leaked in, the
    JSONL envelope would become the synthesis body — and would still pass
    run_synthesis's rc+byte-count check, so only this assertion catches it."""
    argv_log = tmp_path / "argv.log"
    stdin_log = tmp_path / "stdin.log"
    review_body = tmp_path / "review_body.txt"
    review_body.write_text('<review-deadbeef reviewer="grok">\nLooks fine.\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "grok", "--task-mode", "synthesize",
         "--input-nonce", "deadbeef",
         "--prompt-file", str(review_body), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
        env=_env({"GROK_ARGV_LOG": str(argv_log), "GROK_STDIN_LOG": str(stdin_log)}),
    )
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    synth = Path(j["synth_path"]).read_text()
    assert synth.startswith("## Summary")
    assert '"type"' not in synth                    # NOT the JSONL envelope
    argv = argv_log.read_text().splitlines()
    assert "--output-format" not in argv            # non-streaming path
    assert argv[argv.index("--prompt-file") + 1] == "/dev/stdin"
    # Non-leak assertion must key off the PROMPT CONTENT, not the parent-side
    # filename: synthesis.py:62 assembles a fresh prompt containing the nonce
    # and the wrapped review bodies, so asserting the filename is absent would
    # still pass if that assembled prompt were placed on argv.
    assert "deadbeef" not in argv_log.read_text()   # prompt content not on argv
    assert "Looks fine." not in argv_log.read_text()
    assert "deadbeef" in stdin_log.read_text()      # the wrapped reviews arrived
    state = json.loads((out_dir / "synth.state.json").read_text())
    assert state["ok"] is True


def test_synthesize_model_pin_recorded_verbatim(tmp_path):
    """grok has no records_family_not_model, so the pinned model is recorded
    as-is — unlike pykrete, which must record "family:<x>"."""
    review_body = tmp_path / "review_body.txt"
    review_body.write_text('<review-deadbeef reviewer="grok">\nLooks fine.\n</review-deadbeef>\n')
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    r = subprocess.run(
        ["uv", "run", "python", "-m", "multi_review.cli.spawn",
         "--cli", "grok", "--task-mode", "synthesize",
         "--model", "grok-4.5-build", "--input-nonce", "deadbeef",
         "--prompt-file", str(review_body), "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=_env(),
    )
    assert r.returncode == 0, r.stderr
    state = json.loads((out_dir / "synth.state.json").read_text())
    assert state["final_model"] == "grok-4.5-build"
    assert not str(state["final_model"]).startswith("family:")


def test_nonzero_exit_is_a_recorded_failure(tmp_path):
    r, out_dir, _ = _spawn(tmp_path, env_extra={"FAKE_GROK_RC": "1"})
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["ok"] is False
    assert "exit 1" in state["error"]


def test_exit_3_is_not_success_for_grok(tmp_path):
    """pykrete's success_exit_codes widening must not leak to other CLIs."""
    r, out_dir, _ = _spawn(tmp_path, env_extra={"FAKE_GROK_RC": "3"})
    assert r.returncode == 1
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["ok"] is False


def test_short_output_fails_on_byte_floor(tmp_path):
    r, out_dir, _ = _spawn(tmp_path, env_extra={"FAKE_GROK_SHORT": "1"})
    assert r.returncode == 1
    state = json.loads((out_dir / "grok.state.json").read_text())
    assert state["ok"] is False
    assert "50" in state["error"]      # byte floor, not exit code
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_grok_spawn.py -q`
Expected: PASS, 8 tests.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: 218 passed.

- [ ] **Step 7: Commit**

```bash
git add multi_review/core/harvest.py tests/unit/test_harvest.py tests/fixtures/bin/grok tests/integration/test_grok_spawn.py
git commit -m "$(cat <<'EOF'
test(grok): spawn integration coverage (review + synthesize) + telemetry guard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Guard the opt-in control plane (builder default + skill dispatch binding)

**Files:**
- Modify: `agents/multi-review-build.md` (schema block L21-23; Modes section; Defaults list L40)
- Modify: `skills/multi-review/SKILL.md` (Step 2 resume branch L33; Step 2 validate step L39; Step 5 prompt-YAML persistence + fanout L104; claude-inclusion note L143; Step 6 synthesis L147/L157/L166; Step 9b pass-2 L235; closing rules L323/L325)
- Modify: `tests/integration/test_skill_contract.py`

**Interfaces:**
- Consumes: `DEFAULT_REVIEWERS`, `ALL_REVIEWERS` (Task 2).
- Produces: static contract tests that fail if (a) the builder agent's autonomous reviewer default drifts from `DEFAULT_REVIEWERS`, or (b) any of the skill's three reviewer-*selection* sites (fanout, synthesizer + model lookup, resume prompt path) stops binding to the validated resolved set. Also produces `pending/<pair_id>/prompt-source.txt`, written during pass 1, which makes the resume path's resolved object obtainable at all.

**Why this is its own task, not part of Task 5's docs sweep:** `resolve_reviewers` has **no executable caller outside tests** (verified). The live v0.2 path is: the `multi-review-build` agent authors a YAML with an *explicit* `reviewers` list → `fill_defaults` never supplies a default at all. So the user's requirement ("grok must not run unless specified") is enforced in practice by *prose* — in two places, both of which this task pins:

1. `agents/multi-review-build.md`'s autonomous default list, and
2. `skills/multi-review/SKILL.md`'s dispatch instructions, which currently say "dispatch every non-claude reviewer" (**L104**) with no statement of *which set* — an LLM orchestrator could legitimately satisfy that from `ALL_REVIEWERS` or the `--list-reviewers` probe, both of which will contain grok. Task 5 adds grok to the concrete external-reviewer enumeration at L133, which sharpens the ambiguity if L104 is left unqualified.

Every Python test in Tasks 1-3 can pass while either prose site silently defeats opt-in. The SKILL.md edits live here rather than in Task 5 so this task's tests are green on their own.

**Scope honesty:** these tests assert the **repository** copies. `setup.py` *copies* `skills/` and `agents/` into `~/.claude` (it symlinks only under `--dev`), so a stale install can still diverge from a green test. That is a deployment concern, not something a repo-reading test can observe — it is handled by the reinstall precondition in `tests/manual/grok-smoke.md`. Do not describe these tests as proving the *installed* builder is correct.

`test_skill_contract.py` already exists for exactly this class of doc-drift bug and states a "NO false positives" design constraint — honour it: parse explicitly-formatted lines, scoped to their section, rather than trying to understand prose.

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_skill_contract.py`:

```python
def _builder_defaults_section() -> str:
    """The `## Defaults` section only, up to the next heading.

    Scoping matters: an unscoped document-wide search could match a
    default-looking bullet elsewhere while the real autonomous default quietly
    gained grok.
    """
    text = (AGENTS_DIR / "multi-review-build.md").read_text()
    m = re.search(r"^## Defaults$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert m, "builder agent lost its `## Defaults` section"
    return m.group(1)


def test_builder_autonomous_default_matches_DEFAULT_REVIEWERS():
    """The builder agent's autonomous (--use-defaults) reviewer list is the
    SOURCE OF the live opt-in enforcement point: resolve_reviewers has no caller
    outside tests, and an explicit `reviewers` list in the authored YAML bypasses
    fill_defaults entirely. If someone adds grok to that prose list, opt-in is
    silently dead and every Python test still passes. This is the guard.

    Scope caveat: this asserts the REPO copy. `setup.py` copies agents into
    ~/.claude (symlinks only under --dev), so a stale install can still differ.
    That is a deployment concern, covered by the reinstall step in
    tests/manual/grok-smoke.md, not something this test can see.
    """
    from multi_review.core.reviewers import DEFAULT_REVIEWERS
    section = _builder_defaults_section()
    matches = re.findall(r"^- reviewers: \[([^\]]*)\]\s*$", section, re.MULTILINE)
    assert len(matches) == 1, (
        f"expected exactly one `- reviewers: [...]` default line, found {len(matches)}"
    )
    listed = [s.strip() for s in matches[0].split(",") if s.strip()]
    assert listed == DEFAULT_REVIEWERS, (
        f"builder autonomous default {listed} != DEFAULT_REVIEWERS {DEFAULT_REVIEWERS}"
    )


def test_builder_lists_grok_as_a_valid_synthesizer_choice():
    """grok must be nameable by the builder even though it is never a default.

    Tokenised, not a substring test: `"grok" in line` would also be satisfied by
    text like `grok-disabled`.
    """
    text = (AGENTS_DIR / "multi-review-build.md").read_text()
    m = re.search(r"^synthesizer: (.+)$", text, re.MULTILINE)
    assert m, "builder schema lost its synthesizer choice line"
    choices = {c.strip() for c in m.group(1).split("|")}
    assert "grok" in choices, f"grok missing from synthesizer choices {choices}"
    assert "none" in choices


def test_skill_dispatch_binds_to_resolved_reviewers():
    """The reviewer-selecting steps must name the validated set, not an
    unqualified `reviewers` that an LLM orchestrator could satisfy from the
    known/probed list — which contains opt-in grok.

    Pins the three sites that actually SELECT what runs. The remaining
    Task 4 edits (claude-inclusion note, pass-2 back-reference, closing rules)
    are consistency edits, not selection sites, and are deliberately not
    pinned — literal-string assertions on prose are a false-positive source,
    and this file's stated design constraint is NO false positives.
    """
    text = SKILL.read_text()
    # 1. Fanout: which reviewers get dispatched.
    assert "every non-claude reviewer in `resolved.reviewers`" in text, (
        "SKILL.md Step 5 fanout instruction lost its resolved-set qualifier"
    )
    # 2. Synthesis: which CLI runs the consensus pass, and with which model.
    assert "resolved.synthesizer" in text, (
        "SKILL.md Step 6 must select the synthesizer from the resolved object"
    )
    assert "resolved.models[resolved.synthesizer]" in text, (
        "SKILL.md Step 6 synthesis model lookup lost its resolved qualifier"
    )
    # 3. Resume: pass 2 must reuse pass 1's resolved set, not re-derive it.
    assert "pending/<pair_id>/prompt-source.txt" in text, (
        "SKILL.md resume path must read the prompt pointer pass 1 persisted"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_skill_contract.py -q -k "builder or dispatch"`
Expected: FAIL — the synthesizer line does not yet contain grok, and SKILL.md contains none of `resolved.reviewers` / `resolved.synthesizer` / `pending/<pair_id>/prompt-source.txt`. (`test_builder_autonomous_default_matches_DEFAULT_REVIEWERS` should already PASS, since the builder currently lists the correct five; that is a regression guard, green from day one by design — do not "fix" it into failing.)

- [ ] **Step 3: Update the builder agent**

In `agents/multi-review-build.md`:

Line 21 — add grok to the synthesizer *choices*:

```
synthesizer: claude | agy | codex | opencode | pykrete | grok | none
```

Line 22 — leave the reviewer example as the **default five** and label it, so nobody "helpfully" completes the list:

```
reviewers: [claude, agy, codex, opencode, pykrete]   # default set; grok is opt-in, add only on request
```

Line 23 — add grok to the configurable model keys:

```
models: { claude: ..., agy: ..., codex: ..., opencode: ..., pykrete: ..., grok: ... }
```

In the `## Defaults` section, leave `- reviewers: [claude, agy, codex, opencode, pykrete]` **exactly as-is** (the contract test parses this line), and add after the `models.pykrete` bullet:

```
- models.grok: (unset — grok picks its default model; set explicitly for reproducibility, e.g. `grok-4.5-build`)
```

Then add an explicit instruction to the `## Modes` section:

```markdown
**grok is opt-in.** It is a valid reviewer and synthesizer choice, but never
include it in the autonomous `--use-defaults` selection, and never add it to a
`reviewers` list unless the user asked for it by name. The default reviewer set
is exactly `claude, agy, codex, opencode, pykrete`.
```

- [ ] **Step 4: Bind SKILL.md dispatch to the resolved set**

`validate_prompt` already prints `{"ok": true, "resolved": {...}}` (`validate_prompt.py:19`) — the fully-defaulted `PromptFile`. The skill never says to use it, so every later reference to `reviewers` / `synthesizer` / `models` is unqualified. Fix each site:

**Step 2, validate step (L39)** — add after the validate invocation:

```markdown
Capture the `resolved` object from `validate_prompt`'s JSON output and treat it as the **sole** source of `reviewers`, `synthesizer`, `models`, `model_effort`, `mode`, and `if_drift` for the rest of the run. Never derive a run set from `ALL_REVIEWERS`, from the `--list-reviewers` probe, or from what happens to be installed — those include opt-in reviewers (currently `grok`) that must not run unless named. Below, `resolved.<field>` always means this object's field.
```

**Step 2, resume branch (L33) — and the pass-1 write that makes it possible.** Currently `If --resume-pair: skip build; read pending meta.` On resume no `resolved` object exists, leaving the sole-source rule undefined for the whole pass-2 run. **"Read pending meta" is undefined prose: nothing in the repo writes pair metadata or a prompt YAML into `pending/<pair_id>/`** — Step 5 creates only `pending/<pair_id>/files` (the drift snapshot, `SKILL.md:98`), and the builder's YAML lives in a `.tmp/` directory that may be gone by resume time. So the resume branch must first be given something to read.

In **Step 5**, alongside the snapshot creation, add:

```markdown
Persist the prompt location for resume. **Only when `resolved.mode == both`**
(single-pass runs never generate a `pair_id`):

    mkdir -p <cwd>/.multi-review/pending/<pair_id>
    printf '%s\n' "<absolute path of the prompt YAML>" \
      > <cwd>/.multi-review/pending/<pair_id>/prompt-source.txt
    sha256sum "<absolute path of the prompt YAML>" | cut -d' ' -f1 \
      > <cwd>/.multi-review/pending/<pair_id>/prompt-source.sha256

The explicit `mkdir -p` is required: `create_snapshot()` is otherwise the only
thing that creates `pending/<pair_id>/` (`snapshot.py:28`), and it is skipped
entirely under `if_drift: ignore` — so without this the write fails on exactly
the configuration that still needs to be resumable. Step 11 removes the whole
`pending/<pair_id>/` directory after pass 2, so this leaves no lasting artifact.
```

**Record the path, do not copy the YAML.** `load_promptfile` validates with `base_dir=path.parent.resolve()` (`promptfile.py:99`), so a prompt with relative `files: ["./src/foo.py"]` resolves against the YAML's own directory. Copying it into `pending/<pair_id>/` silently re-bases every relative path and can make a valid prompt fail validation on resume — a pointer keeps pass 2 resolving exactly as pass 1 did.

Then replace the Step 2 resume branch with:

```markdown
- If `--resume-pair`: skip build. Read `<cwd>/.multi-review/pending/<pair_id>/prompt-source.txt` (written by pass 1) to get the prompt YAML's absolute path, then run that path through `validate_prompt` to obtain the `resolved` object — validating the original in place so relative `files` / `context_files` resolve against the same base directory pass 1 used. Pass 2 must use the same resolved set as pass 1 — never re-derive reviewers from availability or from the probe list. Before validating, re-hash the YAML and compare against `prompt-source.sha256`; **if it differs, stop** — the prompt was edited between passes, so pass 2 would silently run a different reviewer set, synthesizer, or mode under pass 1's `pair_id` and the pair's comparison data would be meaningless. If the pointer file, the hash file, or the prompt YAML it names is absent, the pair is likewise unresumable: report which one is missing and stop, rather than guessing a reviewer set.
```

**Step 5, fanout (L104 — L103 is the heading)** — the phrase the contract test pins. Change:

> 1. **First**, dispatch every non-claude reviewer via Bash `run_in_background` …

to:

```markdown
1. **First**, dispatch every non-claude reviewer in `resolved.reviewers` via Bash `run_in_background` … Dispatch exactly that set — not every installed reviewer, not every reviewer in `ALL_REVIEWERS`.
```

and in the same block change `<MODEL_FLAG>` / `<EFFORT_FLAG>` to read `resolved.models[cli]` and `resolved.model_effort[cli]`.

**Claude inclusion (L143)** — `If claude is not in reviewers` → `If claude is not in resolved.reviewers`.

**Step 6, synthesis (L147, L157, L166)** — `synthesizer != none` → `resolved.synthesizer != none`; `synthesizer == "claude"` → `resolved.synthesizer == "claude"`; `--cli <synthesizer>` → `--cli <resolved.synthesizer>`. **L166 also carries the synthesis model lookup** — `<SYNTH_MODEL_FLAG>` = `--model <models[synthesizer]>` if `models[synthesizer]` is set — and it appears **twice on that line**. Both occurrences become `resolved.models[resolved.synthesizer]`. Missing this leaves the synthesizer's model pinned from an unqualified map, which is the same class of ambiguity as the fanout instruction.

**Step 9b, pass 2 (L235)** — after "same as Steps 5-7", add: `using the same resolved.reviewers / resolved.synthesizer as pass 1`.

**Closing rules (L323 and L325 — L321 is only the section heading)** — qualify the bare `reviewers` / `synthesizer` references as `resolved.reviewers` / `resolved.synthesizer`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_skill_contract.py -q`
Expected: PASS (3 new). Note this file also parses every documented CLI invocation in SKILL.md for flag validity — if a Step-4 edit mangled an invocation block, `test_skill_flags_exist` fails. That is the guard working.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: 221 passed.

- [ ] **Step 7: Commit**

```bash
git add agents/multi-review-build.md skills/multi-review/SKILL.md tests/integration/test_skill_contract.py
git commit -m "$(cat <<'EOF'
test(grok): pin opt-in control plane — builder default + resolved-set dispatch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Documentation, invariants, and manual smoke

**Files:**
- Modify: `README.md` (L5 subprocess list, L11-16 supported CLIs, L110 synthesizer enum, L114-119 reviewers sample, L122-126 models sample, L157 field table row, Limitations L198-204)
- Modify: `CLAUDE.md` (L52 adapter prose, L59 "Adding a new reviewer", L71 pykrete default-on invariant, Invariants section)
- Modify: `skills/multi-review/SKILL.md` (L3 description, L25 probe list, L111 default-model note, L133 external-reviewer list — the dispatch-binding sites were already done in Task 4)
- Modify: `tests/manual/pykrete-smoke.md` (L25, L72), `tests/manual/skill-step5-join.md` (L18)
- Modify: `BACKLOG.md`
- Create: `tests/manual/grok-smoke.md`

**No automated tests** (Task 4 already carries the executable doc guard). One commit. **Rewrite** the reviewer/synthesizer enumerations rather than appending to them, and mark grok's opt-in status everywhere it is listed — a bare `grok` added to a list reads as default-on.

**Classification rule for every list you touch:** decide whether the list means **valid** (gains grok), **default** (must NOT gain grok), or **a deliberate scenario subset** (leave alone — e.g. `tests/fixtures/prompts/valid.yaml:6`, `tests/unit/test_promptfile.py:14`, `tests/manual/single_pass.md:4`). Historical plan documents under `docs/superpowers/plans/` are archival records of what was true then — **do not rewrite them**.

- [ ] **Step 1: README**

- **L5** (subprocess-reviewer list): add grok — `Other reviewers (agy, codex, opencode, pykrete, grok) continue as subprocesses.`
- **L11-16** (supported CLIs): add `` `grok` (opt-in — see below) ``.
- **L110** (synthesizer enum comment): `claude | agy | codex | opencode | pykrete | grok | none`.
- **L114-119** (`reviewers` sample): keep the five active and add a commented opt-in line, e.g. `#  - grok        # opt-in: never auto-selected`.
- **L122-126** (`models` sample): add `grok: grok-4.5-build`.
- **L157** (field table, `reviewers` row): the Notes cell becomes `Subset of `claude \| agy \| codex \| opencode \| pykrete \| grok`. Default omits `grok` (opt-in).` **and the Default cell must change too** — it currently says "all detected", which (a) contradicts opt-in once `--list-reviewers` probes grok and (b) is already wrong, since `fill_defaults` uses a fixed list, not availability detection. Replace with: `claude, agy, codex, opencode, pykrete`.

Then add a `## Grok setup` section after `## Pykrete setup`:

```markdown
## Grok setup

`grok` is an **opt-in** reviewer — it is never auto-selected. Name it explicitly
in a prompt YAML's `reviewers` (or `synthesizer`) to use it:

```yaml
reviewers: [claude, codex, grok]
models:
  grok: grok-4.5-build     # optional; omit for grok's default
```

Install and authenticate the Grok Build CLI so `grok` is on `PATH`. Verify with
`/multi-review --list-reviewers` (grok is probed even though it is opt-in).

multi-review invokes it as
`grok --sandbox workspace --prompt-file /dev/stdin --output-format streaming-json`.
The prompt travels on stdin; `--sandbox workspace` fences writes to cwd + tmp
while leaving reads open, so reference-mode file manifests outside cwd still work.
```

Add to `## Limitations`:

```markdown
- **grok tool-call telemetry is unavailable, and `0` is a sentinel.** grok emits
  no tool-call events in any output format, so `tool_calls` is always `0` for the
  grok reviewer **even on runs where it demonstrably used tools**. Read it as
  "unknown", never as "grok used no tools" — the harvest schema has no way to
  express unavailability for a single field. Token counts are complete and
  reliable; harvest rows record `telemetry_quality: known-issues` to reflect the
  split. Filtering analyses to `telemetry_quality == "reliable"` therefore also
  excludes grok's good token data; filter per-field when that matters.
- **grok is an agentic, uncontained reviewer.** It auto-approves its own tool use
  in headless mode and can run commands on your working tree during a review.
  `--sandbox workspace` fences writes but is not a security boundary and does not
  restrict reads — **don't point grok at untrusted code** until sandbox
  containment lands (BACKLOG). Same posture as agy and pykrete.
```

- [ ] **Step 2: CLAUDE.md**

- **L52** (adapter prose): the structured-stream vs plain-text split must name grok as a structured-stream (JSONL) adapter alongside claude/codex/opencode.
- **L59** ("Adding a new reviewer"): rewrite to name both sets and the extra registration points:

```markdown
- **Adding a new reviewer**: add to `ALL_REVIEWERS` (known/valid), decide default-on vs opt-in by whether it also goes in `DEFAULT_REVIEWERS`, add a `CLI_SPEC` entry, write a `ProgressAdapter` subclass, register in `ADAPTER_FOR`, add a `TELEMETRY_QUALITY` entry (a missing one silently defaults to `degraded`), and — if it is default-on — add it to the builder agent's autonomous default list too.
```

- **L71** (pykrete default-on invariant): its stated *reason* becomes false after the split. Rewrite: pykrete is default-on because it is in **`DEFAULT_REVIEWERS`**, not merely because it is in `ALL_REVIEWERS` (grok is in `ALL_REVIEWERS` and is not default-on).

Add these invariants to the "Invariants to preserve" section:

```markdown
- **`ALL_REVIEWERS` is the known/valid set; `DEFAULT_REVIEWERS` is the auto-selected set.** Membership in the first makes a reviewer nameable (prompt-YAML `reviewers`/`synthesizer`, `spawn --cli`, `--list-reviewers` probing); membership in the second makes it default-on. `resolve_reviewers`'s non-explicit base and `promptfile`'s TWO default sites (the dataclass `default_factory` and `fill_defaults` — they are independent) are the ONLY consumers of `DEFAULT_REVIEWERS`; every other consumer means "is this a real reviewer?" and must stay on `ALL_REVIEWERS`. `detect_available()` deliberately probes `ALL_REVIEWERS` so `--list-reviewers` reports opt-in reviewers too.
- **The Python split is NOT the whole opt-in enforcement — two prose sites are load-bearing.** `resolve_reviewers` has no executable caller outside tests: the live path is the `multi-review-build` agent authoring an explicit `reviewers` list, which bypasses `fill_defaults` entirely. So opt-in actually rests on (1) the agent's autonomous `--use-defaults` list at `agents/multi-review-build.md`, and (2) `SKILL.md`'s dispatch instructions, which must name `resolved.reviewers` — an unqualified "dispatch every non-claude reviewer" can be satisfied from `ALL_REVIEWERS` or the `--list-reviewers` probe, both of which contain grok. Both are pinned by `tests/integration/test_skill_contract.py`. Don't edit either without updating the constant, and don't delete the tests.
- **Those contract tests assert the REPO copy, not the installed one.** `setup.py` *copies* `skills/` and `agents/` into `~/.claude` (symlink only under `--dev`), so a green suite does not prove the artifacts Claude Code actually loads are current. Re-run setup after changing either file, and treat any manual smoke of skill/agent behaviour as invalid until you have.
- **grok is opt-in** — in `ALL_REVIEWERS` but NOT `DEFAULT_REVIEWERS`. Unlike agy/pykrete it never runs unless explicitly named. Don't "helpfully" add it to a default set; that reverses a deliberate decision (2026-07-19).
- **grok's prompt reaches stdin via `--prompt-file /dev/stdin`, not a sentinel.** grok has no `-` stdin sentinel, so `CLI_SPEC["grok"]["base"]` names `/dev/stdin` as the prompt file and `stdin_sentinel` is `None`; the pipe `fanout.py` already writes to is what `/dev/stdin` resolves to. Only the literal string `/dev/stdin` reaches `/proc/PID/cmdline`, so the stdin invariant holds with no `argv_file` workaround. Don't add a `-` sentinel — grok would read it as a stray positional prompt. Assumes a Linux `/dev/stdin` (repo targets Linux/WSL).
- **grok's output format is mode-dependent, and the test shim must mirror that.** The reviewer path passes `--output-format streaming-json` (JSONL → `GrokAdapter`); the synthesis path builds with `streaming=False`, passes no format flag, and `synthesis.py` takes stdout verbatim as the synthesis body with no adapter involved. `run_synthesis` only checks rc and byte count, so a leaked streaming flag would silently make the JSONL envelope the "synthesis". `tests/fixtures/bin/grok` branches on `--output-format` precisely so that regression fails a test.
- **grok emits no tool-call events.** Verified against both `--output-format streaming-json` and `json`: the complete event vocabulary is `thought` / `text` / `end`, even on runs where tools demonstrably executed (`num_turns > 1`). `GrokAdapter` leaves `usage.tool_calls` at 0 and `TELEMETRY_QUALITY["grok"]` is `"known-issues"` (tokens reliable, tool calls absent). **That 0 is an unavailable sentinel, not a measured zero.** Don't synthesise `tool_calls` from `num_turns` — that fabricates a metric.
- **grok's `end` event usage is absolute, not a delta.** `GrokAdapter` assigns (`=`) rather than accumulates (`+=`), unlike `OpenCodeAdapter`'s per-step deltas. `cached_tokens` maps from `cache_read_input_tokens`, a key name unique to grok. The adapter also guards `isinstance(ev, dict)` and string payloads: valid-but-non-object JSON would otherwise raise `AttributeError` inside the drain task and kill the review mid-stream.
- **`--sandbox workspace` is fenced writes, not containment.** Reads are unrestricted under that profile (verified: sandboxed grok read a file outside its `--cwd`), so reference mode is unaffected. It puts grok level with codex's implicit `workspace-write` default rather than with agy/pykrete's no-profile posture — it is NOT a security boundary. **grok is agentic and uncontained: do not point it at untrusted code** until the bwrap work in BACKLOG lands. grok refuses to start rather than run unsandboxed if a named profile is missing, so a broken profile fails loudly.
```

- [ ] **Step 3: SKILL.md**

- **L3** (skill description): add grok to the fan-out list so the skill is discoverable for it — `claude/agy/codex/opencode/pykrete/grok`.
- **L25** (`--list-reviewers` probe): make the enumeration explicit and mark grok opt-in:

```markdown
If `--list-reviewers`: probe each of `claude, agy, codex, opencode, pykrete, grok` (i.e. `ALL_REVIEWERS`) via `shutil.which <cli>` + `<cli> --version`; print availability, detected default models, and the host backend (Task subagent for claude in v0.2). Mark `grok` as **opt-in** in the output — it is probed but never auto-selected (`DEFAULT_REVIEWERS` omits it). Exit.
```

- **L111** (default-model note): add grok to the list of externals that ship with no `--model` by default.
- **L133** (external-reviewer dispatch/join list): add grok — it is a subprocess reviewer like agy/codex/opencode/pykrete. Phrase it as *"whichever of these are in `resolved.reviewers`"*, not as a set to dispatch: this is a table of **how to poll** each dispatch type, and a bare enumeration containing grok sitting near the fanout instruction is exactly the ambiguity Task 4 closed.

> **Do not re-edit the sites Task 4 already bound** (Step 2 resume + validate, Step 5 prompt persistence + fanout, claude-inclusion, Step 6 synthesis, Step 9b, closing rules). The three *selection* sites among them — fanout, synthesizer + its model lookup, and the resume prompt path — are pinned by `test_skill_dispatch_binds_to_resolved_reviewers`, so changing that wording fails the suite. The others are unpinned consistency edits; leave them alone anyway.

- [ ] **Step 4: Stale manual-test docs**

- `tests/manual/pykrete-smoke.md:25` states the exact five-member `ALL_REVIEWERS` and **infers pykrete's default-on status from that membership** — false after the split. Rewrite to cite `DEFAULT_REVIEWERS` for the default claim and note `ALL_REVIEWERS` now also contains opt-in `grok`.
- `tests/manual/pykrete-smoke.md:72` repeats a five-CLI probe list — add grok.
- `tests/manual/skill-step5-join.md:18` lists external reviewers as `agy, codex, opencode` — it **already** omits pykrete. Add both pykrete and grok.

- [ ] **Step 5: BACKLOG**

Add a `## grok deferred cluster (2026-07-19)` section:

```markdown
### Thread `model_effort` through to `grok --reasoning-effort`

grok exposes `--reasoning-effort` (alias `--effort`), and the prompt YAML has a
`model_effort` map, but `spawn.py --effort` is a no-op for every CLI — it prints
a note and drops the value. Wiring effort through `CLI_SPEC`/`build_command` is
a cross-cutting change affecting claude/codex/grok together; do it once for all
of them rather than special-casing grok.

### Record grok's actual model from the `end` event

grok's `end` event carries `modelUsage: {"<model-id>": {...}}` naming the model
actually used. Harvest currently records `final_model` as `<default>` when no
model is pinned. Parsing that key would give a real model ID for unpinned runs —
useful because grok's default model changes upstream without notice. Deferred:
`GrokAdapter` would need to surface it and `ReviewerResult.model_used` would
need a per-CLI "adapter knows better than the caller" override path.

### Field-level telemetry availability

`TELEMETRY_QUALITY` is per-reviewer, so grok's reliable token counts are labelled
`known-issues` solely because `tool_calls` is unavailable — and README tells
analysts to filter on `telemetry_quality == "reliable"`, which discards good data.
A field-level shape (`tool_calls: null` + `tool_calls_quality: unavailable`) would
be more honest but needs a `HARVEST_SCHEMA_VERSION` bump and a migration, so it is
deferred rather than bundled into the grok work.

### `detect_self()` does not recognise grok

If multi-review is ever run from inside a grok session, `--skip-self` cannot drop
grok because `detect_self()` has no grok branch (no known env marker). Not an
issue today: v0.2's entry point is a Claude Code skill. Revisit if a grok-hosted
invocation path appears.
```

Also add a `## Reviewer stdin lifecycle (pre-existing, 2026-07-19)` section — see "Refuted / deferred findings" for the evidence:

```markdown
### `fanout.py` writes the whole prompt before starting the output drainers

`run_reviewer` writes and `drain()`s the entire prompt to the child's stdin
(`fanout.py:149`) BEFORE creating the stdout/stderr drain tasks, and the
`--timeout` wrapper only covers the later `gather()` (`fanout.py:180`).
Consequences: (a) a child that stops reading stdin blocks `drain()` forever —
even when `--timeout` is set, because the deadline has not started; (b) a child
that writes enough stdout while still reading a large prompt can deadlock, since
those pipes are not being drained yet; (c) the whole prompt is encoded and
buffered in memory.

Affects every stdin-delivery reviewer — codex, opencode, pykrete, grok — i.e.
three default-on reviewers today. NOT introduced by any one of them. `agy` is
exempt (argv_file delivery) and the synthesis path is exempt
(`proc.communicate()` handles all three streams concurrently inside `wait_for`,
`synthesis.py:87`).

Fix: start the stdin write and both drainers concurrently, and put the whole
exchange inside the timeout. Related: `BrokenPipeError`/`ConnectionResetError`
during the write are silently swallowed (`fanout.py:149-155`) and delivery
completeness is never recorded, so a child that reads only part of the prompt,
emits >50 bytes and exits 0 is classified as a success. Also `spawn.py`'s
`Path.read_text()` (L64, L112) raises `UnicodeDecodeError` outside the state-file
writer, so a non-UTF8 prompt file produces a traceback and no recorded failure —
low priority, since spawn's input is machine-generated by `prepare.py`.
```

- [ ] **Step 6: Manual smoke procedure**

Create `tests/manual/grok-smoke.md` covering, with explicit expected results.

**Precondition — reinstall first, or the smoke is worthless.** `setup.py` *copies* `skills/multi-review/` and `agents/*.md` into `~/.claude` (it symlinks only under `--dev`), so a checkout with this branch's edits does **not** change what Claude Code actually runs. Every case below exercises the installed copy. Begin the procedure with:

```bash
uv run python -m multi_review.cli.setup --source-repo $(pwd)     # or --dev to symlink
grep -c grok ~/.claude/agents/multi-review-build.md              # expect >= 1
grep -c 'resolved.reviewers' ~/.claude/skills/multi-review/SKILL.md  # expect >= 1
```

If those greps come back empty you are testing a stale install, and cases 1-3 will report false confidence about opt-in.

1. **Availability** — `/multi-review --list-reviewers` lists grok, marked opt-in.
2. **Opt-in holds (YAML path)** — run a prompt YAML with `reviewers` omitted; assert `REVIEW-*.md` has **no** grok section and the harvest row's `usage_by_reviewer` has no `grok` key.
3. **Opt-in holds (autonomous builder path)** — run `/multi-review --use-defaults "<seed>"`, then **read the generated YAML** at `.multi-review/prompts/.tmp/<id>.yaml` and assert its explicit `reviewers` list omits grok. This is a distinct path from case 2: the builder writes an explicit list, so `fill_defaults` never runs.
4. **Explicit selection** — run with `reviewers: [claude, grok]`; assert a grok section exists, opens with `## Summary`, and the harvest row records non-zero `input_tokens`/`output_tokens` with `tool_calls: 0` and `telemetry_quality: known-issues`.
5. **Reference mode with an out-of-cwd file** — run `mode: reference` with a `files:` entry outside the current directory; assert grok's review actually engages with that file's content (this is the check that `--sandbox workspace` has not broken reads).
6. **Synthesizer role** — run with `synthesizer: grok` and ≥2 successful reviewers; assert `synth.txt` is clean markdown with no JSONL envelope and no narration.
7. **Failure path** — temporarily rename the `grok` binary off `PATH`, run **single-pass** (`mode: reference`, not `both`) with `reviewers: [claude, grok]`; assert grok appears as a *failed section* with a `CLI not found` error and the run still produces its review file (exit 0, claude succeeded). **Assert the path the skill reports, which is `<cwd>/REVIEW-<slug>.md`** (`SKILL.md:191`) — not a bare `REVIEW.md`, which no code path writes, and possibly auto-suffixed `-2` if a prior run left a file there. Paired runs use mode-suffixed names instead, which is why this case pins single-pass.

Mark the file honestly at the top with whether it has been executed live and on what date. **Do not claim it passed if it has not been run.**

- [ ] **Step 7: Verify no enumeration was missed**

Run a scan that covers markdown across the whole repo except the archival plans:

```bash
rg -n 'claude.{0,3} agy.{0,3} codex|opencode.{0,3} pykrete|agy, codex, opencode' \
   README.md CLAUDE.md skills/ agents/ tests/manual/ | grep -v grok
```

Every hit must be classified as **valid** (needs grok), **default** (correctly excludes it), or **scenario subset** (leave alone). Expected remaining hits: only default-set and scenario-subset lines. `docs/superpowers/plans/` is excluded by design — those are archival.

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: 221 passed (docs-only task; the count must not move). Note `tests/integration/test_skill_contract.py` parses `agents/*.md`, so a malformed edit there fails the suite — that is the guard working.

- [ ] **Step 9: Commit**

```bash
git add README.md CLAUDE.md skills/multi-review/SKILL.md BACKLOG.md tests/manual/
git commit -m "$(cat <<'EOF'
docs(grok): opt-in reviewer setup, invariants, telemetry caveats

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage.** The request was "add support for Grok — opt-in, don't use if unspecified."
- *Support*: `CLI_SPEC` entry + adapter + telemetry + spawn integration covering **both** review and synthesize modes (Tasks 1-3). ✅
- *Opt-in*: `DEFAULT_REVIEWERS` split (Task 2), enforced in Python by `test_grok_is_known_but_not_default`, `test_default_reviewers_is_exactly_the_five`, `test_resolve_reviewers_never_auto_selects_grok`, `test_grok_omitted_from_filled_defaults`, `test_dataclass_default_reviewers_excludes_grok`, and the untouched `test_fill_defaults_populates_missing`; enforced on the two prose control-plane sites by Task 4's contract tests (builder autonomous default + `SKILL.md` dispatch binding to `resolved.reviewers`) — noting those guard the repo copy, with the installed copy covered by `grok-smoke.md`'s reinstall precondition; documented in README/CLAUDE/SKILL/builder (Task 5). ✅
- *Containment decision* (user chose `--sandbox workspace`): in `CLI_SPEC` base, asserted in `test_build_command_grok_argv_shape` and `test_prompt_travels_on_stdin_not_argv`, smoke-checked for read regressions in `grok-smoke.md` case 5. ✅

**Placeholder scan.** No TBD/TODO; every code step carries complete code; no "similar to Task N".

**Type consistency.** `GrokAdapter` (Task 1) is the exact name registered in `ADAPTER_FOR` and imported in Task 1's tests. `DEFAULT_REVIEWERS` (Task 2) is spelled identically in `reviewers.py`, `promptfile.py`, and all tests including Task 4's contract test. `TELEMETRY_QUALITY["grok"] == "known-issues"` matches the string asserted in Task 3 Step 1 and quoted in the README limitation. The shim's env-var names (`GROK_ARGV_LOG`, `GROK_STDIN_LOG`, `FAKE_GROK_RC`, `FAKE_GROK_SHORT`) match every use in `test_grok_spawn.py`.

**Non-vacuity, explicitly.** Each guard names the failure it would catch:
- stdin invariant — shim logs stdin *separately from argv*, so "prompt arrived nowhere" is distinguishable from "prompt arrived on stdin".
- opt-in — `fill_defaults` alone cannot prove validity (it does not enforce membership; `validate` does), so `test_grok_is_a_valid_explicit_reviewer_and_synthesizer` drives `validate`; and `test_dataclass_default_reviewers_excludes_grok` covers the default site `fill_defaults` tests cannot reach.
- synthesis — shim branches on `--output-format`, so a leaked streaming flag produces JSONL where markdown is asserted.
- telemetry — pytest assertion, because a missing dict entry is silent (`.get(cli, "degraded")`).
- live opt-in — contract test parses the builder's default line, because no Python test can see it.
- `test_resolve_reviewers_explicit_selection_still_passes_through` is explicitly labelled as **not** evidence of grok support, since it passes on today's code.

**Test-count arithmetic.** 186 baseline → **+9** (Task 1: adapter) = **195** → **+13** (Task 2: 9 in `test_reviewers.py` + 4 in `test_promptfile.py`; `test_pykrete_known_and_default` is modified in place, so it adds 0 and subtracts 0) = **208** → **+10** (Task 3: 8 integration + 2 harvest) = **218** → **+3** (Task 4: 2 builder + 1 skill-dispatch) = **221**. Task 5 adds none. If a step's expected count does not match, stop and find out why before proceeding.

---

## Review provenance

Rev 1 was reviewed by a 4-reviewer codex panel (`gpt-5.6-sol`, reasoning effort high): holistic breadth, adversarial, opt-in-split specialist, adapter/invocation specialist. All findings were checked against source before acceptance.

**Accepted and folded in (12):** grok-as-synthesizer had no automated coverage and the shim emitted JSONL unconditionally so it could not have caught it (Task 3); the `TELEMETRY_QUALITY` entry could be omitted with the suite green (Task 3); the builder agent's autonomous default is the live opt-in path and was untested (Task 4 — new); the `PromptFile` dataclass default was changed but never exercised (Task 2); `test_pykrete_known_and_default` stopped proving "default" after the split, as did `CLAUDE.md:71`'s stated reasoning (Tasks 2, 5); the skill never binds orchestration to `validate_prompt`'s `resolved` object (Task 5); README's "all detected" default cell contradicts opt-in (Task 5); the doc scan missed `README.md:5`, `SKILL.md:3`/`:111`, builder `models` keys, and two `tests/manual/` files (Task 5); the adapter guarded JSON syntax but not JSON *type* (Task 1); the `thought`-phase contract contradicted itself between prose and code (Task 1); `test_resolve_reviewers_honours_explicit_grok` was vacuous (Task 2); `tool_calls: 0` needed documenting as an unavailable sentinel (Tasks 3, 5).

**Round 2** (rev 2 → rev 3, monotonic: scoped to rev-2's own changes; 2 reviewers — delta-correctness, adversarial). 5 findings, all accepted, 2 with narrowed remedies:

- **`resolved.*` declared authoritative but never used at the dispatch sites** (HIGH). Confirmed: `SKILL.md:103` says "dispatch every non-claude reviewer" with no set qualifier, and Task 5 was adding grok to the concrete external-reviewer enumeration nearby — an LLM orchestrator could satisfy the instruction from `ALL_REVIEWERS` or the probe list. The resume branch (`SKILL.md:31`) had no `resolved` object at all. → Task 4 now binds all seven dispatch sites plus resume, pinned by a new contract test. **This moved SKILL.md work from Task 5 into Task 4** so Task 4's test is green within its own task.
- **Task 4 guards the repo template, not the installed builder** (HIGH). Confirmed: `setup.py:52-71` copies rather than symlinks unless `--dev`. Remedy narrowed: the reviewer wanted a pytest that installs into an isolated `HOME`; that duplicates `test_cli_setup.py` and tests copy mechanics rather than opt-in. Instead the claim is corrected everywhere ("source of the live path", not "live path"), and `grok-smoke.md` gains a hard reinstall precondition with greps, since every skill/agent smoke case is otherwise exercising a stale copy.
- **Task 4's regex could match a decoy default; synthesizer check was a substring** (MEDIUM). Confirmed. → scoped to the `## Defaults` section, uniqueness asserted, synthesizer choices tokenised on `|` (so `grok-disabled` no longer satisfies it).
- **Nested telemetry values unguarded** (MEDIUM). Confirmed: rev 2 checked `isinstance(usage, dict)` but then assigned arbitrary nested values into a `Usage` that declares ints — `{"input_tokens": null}` would reach `state.json` and the harvest row. → `_int0()` coercion per counter (excluding `bool`, an int subclass that would score `True` as 1 token) + a test.
- **Synthesis argv non-leak assertion checked a filename, not content** (Important). Confirmed: `review_body` is the parent-side filename; the child prompt is assembled fresh at `synthesis.py:62`, so the assertion would have passed even with the real prompt on argv. → assert the nonce and review body are absent from argv instead.

Round 2 also independently confirmed rev-2's corrected test arithmetic, that Task 4's regex cannot match the commented schema line, that `spawn --task-mode synthesize` emits exactly the keys the new test asserts, and that Task 2's tests compile against the real API.

**Round 3** (rev 3 → rev 4, monotonic: scoped to rev-3's own changes; 1 reviewer). 4 findings, all accepted:

- **The resume binding depended on an artifact nothing persists** (HIGH). Confirmed: rev 3 told resume to "re-validate the pair's stored prompt YAML", but "read pending meta" (`SKILL.md:33`) is undefined prose — pass 1 creates only `pending/<pair_id>/files` (the drift snapshot, `SKILL.md:98`), never the YAML, and the builder's `.tmp/` copy may be gone by resume time. A self-inflicted finding: rev 3 introduced the dependency without introducing the write. → Task 4 now has pass 1 persist a pointer at `pending/<pair_id>/prompt-source.txt` (removed with the rest of the pending dir at Step 11), resume reads it, and an absent file is an explicit hard stop rather than a re-derived reviewer set. **Round 4 then found the first version of this fix was itself wrong** — see below.
- **Synthesis model lookup left unqualified** (MEDIUM). Confirmed: `SKILL.md:166` carries `models[synthesizer]` **twice**, and rev 3's edit list named only `--cli <synthesizer>` on that line. → both occurrences become `resolved.models[resolved.synthesizer]`.
- **The contract test pinned one site while the plan claimed it pinned all of them** (MEDIUM). Confirmed overclaim. → the test now pins the three sites that actually *select* what runs (fanout, synthesizer + model lookup, resume prompt path); the remaining consistency edits are explicitly documented as unpinned, because literal-string assertions on prose are a false-positive source and `test_skill_contract.py`'s stated design constraint is no false positives.
- **Two line references off by one or two** (LOW). Confirmed: the fanout phrase is `SKILL.md:104` (103 is the heading) and the closing bare fields are L323/L325 (321 is the heading). → corrected.

Round 3 independently confirmed the rest of rev 3: the contract test's literal string matches the plan's SKILL.md wording character-for-character; `--cli <resolved.synthesizer>` does not break `test_skill_flags_exist` (the parser validates `--flag` tokens, not values, `test_skill_contract.py:98-115`); `_int0` is placed where `GrokAdapter` can resolve it; the arithmetic 186 → 195 → 208 → 218 → 221 is right; and moving the SKILL.md edits left Task 5 internally consistent.

**Round 4** (rev 4 → rev 5, monotonic; 1 reviewer). 3 findings, all accepted — and both HIGHs were defects in **rev 4's own fix**, not in the original design. That is the loop working: each round's remedy got its own adversarial pass.

- **Copying the prompt YAML into `pending/` silently re-bases every relative path** (HIGH). Confirmed: `load_promptfile` validates with `base_dir=path.parent.resolve()` (`promptfile.py:99`), and `_resolve_path` joins relative entries onto that base (`promptfile.py:56`); an integration test pins the behaviour (`test_cli_prepare.py:31`). So a prompt with `files: ["./src/foo.py"]` would resolve correctly in pass 1 and fail validation on resume. The reviewer proposed persisting a canonical fully-defaulted YAML with absolutised paths; **narrowed** — that asks an LLM orchestrator to perform a correctness-critical rewrite with no CLI to do it. → persist a *pointer* (`prompt-source.txt` holding the YAML's absolute path) and validate the original in place, which preserves pass-1 base-dir semantics exactly and needs no new machinery.
- **`if_drift: ignore` leaves no directory to write into** (HIGH). Confirmed: `create_snapshot()`'s `mkdir(parents=True)` (`snapshot.py:28`) is the only creator of `pending/<pair_id>/`, and that call is skipped entirely under `if_drift: ignore` (`SKILL.md:312`) — precisely the configuration that still needs to be resumable. → explicit `mkdir -p`, plus an explicit `resolved.mode == both` guard (single-pass runs never generate a `pair_id`, `SKILL.md:74`).
- **One stale `L103` reference** (LOW). → corrected to L104.

Round 4 also confirmed all four contract-test literals match the instructed SKILL.md wording character-for-character; that the new pending-dir file is swept and cleaned up correctly and does not perturb the snapshot diff (which operates only on the `/files` child); and the arithmetic (186 collected; 195 → 208 → 218 → 221, with Task 4 still adding exactly three test functions despite more assertions).

**Round 5** (rev 5 → rev 6, final round of the agreed 5-round cap; 1 reviewer). 2 findings, both accepted, both MEDIUM:

- **Resume validated the current YAML, not pass 1's** (MEDIUM). Confirmed: `load_promptfile` re-reads the file (`promptfile.py:94`), and the drift snapshot covers only input/context files (`SKILL.md:95`) — so a prompt YAML edited between passes could silently change reviewers, synthesizer, models, or mode under pass 1's `pair_id`, making the pair's comparison data meaningless. Narrow window for same-turn paired runs, but `--resume-pair` is exactly the delayed case. → pass 1 also writes `prompt-source.sha256`; resume re-hashes and hard-stops on mismatch.
- **Manual smoke asserted a filename no code path writes** (MEDIUM). Confirmed: single-pass aggregation writes `<cwd>/REVIEW-<slug>.md` (`SKILL.md:191`), paired runs use mode-suffixed names, and nothing emits a bare `REVIEW.md`. The failure-path case would have failed against a correct implementation. → case 7 now pins single-pass mode and asserts the reported `REVIEW-<slug>.md` path, noting possible `-2` auto-suffixing.

Round 5 also ran a whole-plan consistency pass and found **no** surviving stale references (no lingering `prompt.yaml`, no stale `L103`, no stale test counts, no tests referenced in the wrong task), confirmed the pointer literal matches character-for-character, confirmed nothing repo-managed deletes the original YAML between passes, and confirmed each task is independently green by dependency inspection.

**Loop terminated at the agreed 5-round cap.** Findings by round: 12 → 5 → 4 → 3 → 2, with severity falling from Critical/HIGH to MEDIUM. Rounds 3-5 were dominated by defects in the *previous round's fixes* rather than in the original design — the plan's substance converged around rev 3. Two MEDIUM items remain unreviewed by construction (the rev-6 changes themselves): the resume hash-check prose and the smoke filename fix, both localized and low-risk.

**Refuted / deferred findings (with reasons):**

- **"fanout stdin lifecycle can deadlock before the timeout" — rated Critical, verdict "REJECT — not implementation-ready".** The defect is **real and confirmed** against source (`fanout.py:149` writes and drains before `fanout.py:180` starts the drainers under `wait_for`). Rejected as a **blocker on scope**: it is pre-existing and cross-cutting, affecting every stdin-delivery reviewer — codex, opencode, pykrete — three of which are default-on today. grok neither introduces nor worsens it, and rewriting the fanout lifecycle is not part of "add an opt-in reviewer". Logged to BACKLOG with full evidence.
- **"partial/closed stdin writes can be reported as success"** — same code path, same disposition; folded into the same BACKLOG entry.
- **"`spawn.py` `read_text()` raises `UnicodeDecodeError` outside the state writer"** — real and pre-existing, but spawn's prompt file is machine-generated by `prepare.py`, not user-supplied bytes, so the path is not reachable in practice. Noted in the same BACKLOG entry at low priority.
- **"introduce `tool_calls: null` + `tool_calls_quality: unavailable`"** — correct diagnosis, disproportionate remedy: it requires a `HARVEST_SCHEMA_VERSION` bump plus a migration for what is currently a documentation problem. The documentation half is accepted (README limitation + CLAUDE.md invariant both state the sentinel explicitly); the schema half is BACKLOGged.
- **"the shim should reject unknown flags and pin exact token order"** — over-engineering. The shim now reads the `--prompt-file` value and branches on `--output-format`, which ties it to the invocation contract; a full argument parser would be brittle without catching additional real bugs. The unit tests in Task 2 already assert each flag's following token.
- **"`last_error` assignments are inert"** — factually correct (verified: zero consumers repo-wide). Kept anyway for parity with the base-class contract and sibling adapters; the plan no longer implies they drive behaviour.
