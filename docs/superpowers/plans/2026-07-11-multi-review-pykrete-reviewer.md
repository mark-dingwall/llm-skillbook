# Pykrete Reviewer Implementation Plan (rev 5)

> **Archival.** Historical record of the work as planned. Line references point at the pre-split `multi_review.py` and may not match current code. Current behaviour lives in `CLAUDE.md`, `README.md` and `skills/multi-review/SKILL.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `pykrete` as a **default-on** multi-review reviewer (like agy) so reviews can run on NanoGPT models.

**Architecture:** Pykrete is a Node CLI (`pykrete [--task T] [--family F] [--config P] -`) that wraps the `pi` agent against NanoGPT with a failover state machine. It reads the prompt on **stdin** (`-` sentinel), emits **plain text** on stdout, and uses exit code **3 for success-via-downgrade**. It slots in as a subprocess reviewer like `agy`/`codex`/`opencode`.

**Tech Stack:** Python 3.11+, stdlib `asyncio` subprocess, `pytest`. No new dependencies.

**Revision note (rev 2):** rev 1 was reviewed by a 4-reviewer codex panel. Verified findings folded in: (A) a `ValueError` on missing config would escape the fanout `gather` and abort every reviewer — fixed by catching construction errors in the runners; (B) adding pykrete to `ALL_REVIEWERS` made it a silent, uncontained default — fixed by a separate `DEFAULT_REVIEWERS`; (C) integration tests must drive the real `spawn` CLI; (D) exit-3 downgrades must not be recorded as a clean, comparison-eligible run with a family masquerading as the model. See "Review provenance" at the end.

**Revision note (rev 3):** rev 2 was reviewed by a 2-reviewer Round-2 panel (changes-only). Root cause of all findings: new `ReviewerResult` fields must be threaded through the **spawn → `state.json` → {harvest, aggregate}** persistence boundary, not just the in-memory object. Fixes: (R2-1 HIGH) serialize `downgraded` in `spawn.py` and read it in `write_harvest_row._state_to_result` so eligibility actually sees it; (R2-2) `resolve_reviewers` implicit base → `DEFAULT_REVIEWERS`; (R2-3) serialize `error` in `spawn.py` and reconstruct it in both loaders so the missing-config diagnosis survives into REVIEW.md; (R2-4) fix Task-1 test to the real promptfile API (`fill_defaults`/`validate`) and make the fake pykrete shim discriminate (argv echo + short-output mode).

**Revision note (rev 5): pykrete is now DEFAULT-ON, not opt-in** (user decision, 2026-07-19, overriding review finding B). Consequences: the `DEFAULT_REVIEWERS` split (rev 2) is **removed** — pykrete lives in `ALL_REVIEWERS`, which is both the known/valid set and the default set (promptfile already derives defaults from it, so no promptfile *source* change; only its test expectation grows to 5). The `resolve_reviewers` base reverts to `ALL_REVIEWERS`. **Task 3 (config errors don't escape the fanout) is now CRITICAL, not defensive:** every run includes pykrete, so an unconfigured/uninstalled pykrete must fail as a *recorded reviewer* (config error → Task 3; not-installed → existing `FileNotFoundError` handling at `fanout.py:117`), never crash the run. Accepted trade-off: until `NANOGPT_API_KEY` + `PYKRETE_CONFIG` are set, every run shows a failed pykrete section. Uncontained-default posture is now identical to agy's (documented, accepted).

## Global Constraints

- **Default-on, like agy.** pykrete joins `ALL_REVIEWERS` (known/valid + default). Rationale: user decision — same uncontained-default posture already accepted for agy. Safety net: it must fail cleanly when unconfigured/uninstalled (Task 3), never crash the run.
- **Partial-failure invariant is sacred** (`CLAUDE.md:68`): a broken/misconfigured pykrete must become a *recorded failed reviewer*, never a traceback that aborts the run or an empty "success" report.
- **Minimum code.** Match existing style in `multi_review/core/`. No speculative abstraction.
- **Baseline:** `uv run pytest tests/ -q` (168 passing on `main`). Every task ends green.
- **Pykrete interface facts** (established, do not re-litigate): stdin `-`; plain-text stdout; exit `{0=success, 3=downgrade-success, 1=error, 2=config, 4=all-unavailable}`; selection via `--family`/`--task` (NOT `--model <id>`); needs `NANOGPT_API_KEY` in env + `pykrete.toml` via `--config`; wraps the agentic `pi`.

---

### Task 1: ALL_REVIEWERS + CLI_SPEC entry + build_command plumbing

**Files:**
- Modify: `multi_review/core/reviewers.py` (`ALL_REVIEWERS` L20; `CLI_SPEC` L101-136; `build_command` L156)
- Test: `tests/unit/test_reviewers.py`, `tests/unit/test_promptfile.py`

pykrete is **default-on** (like agy). It joins `ALL_REVIEWERS`, which is BOTH the known/valid set (validation via `_KNOWN_REVIEWERS`) AND the prompt-file default set — `promptfile.py`'s `PromptFile.reviewers` default and `fill_defaults` already derive from `ALL_REVIEWERS`, so **no promptfile source change** is needed (only its existing default-set test expectation grows to 5). `resolve_reviewers` base stays `ALL_REVIEWERS` (unchanged).

**Interfaces:**
- Produces: `ALL_REVIEWERS` includes pykrete (validation + defaults). `CLI_SPEC["pykrete"]` with `success_exit_codes`, `config_env`, `model_flag="--family"`, `records_family_not_model=True`. `build_command("pykrete", …)` injects `--config <PYKRETE_CONFIG>` and `--family <model>`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_reviewers.py
def test_pykrete_known_and_default():
    from multi_review.core.reviewers import ALL_REVIEWERS, CLI_SPEC
    assert "pykrete" in ALL_REVIEWERS            # known/valid AND default-on
    assert CLI_SPEC["pykrete"]["success_exit_codes"] == (0, 3)

def test_build_command_pykrete_family_and_config(monkeypatch):
    from multi_review.core.reviewers import build_command
    monkeypatch.setenv("PYKRETE_CONFIG", "/etc/pykrete.toml")
    cmd = build_command("pykrete", model="glm", streaming=True)
    assert cmd[0] == "pykrete"
    assert cmd[cmd.index("--config") + 1] == "/etc/pykrete.toml"
    assert cmd[cmd.index("--family") + 1] == "glm"    # family, not --model
    assert "--model" not in cmd
    assert cmd[-1] == "-"                               # stdin sentinel last
    assert "--output-format" not in cmd                # plain text

def test_build_command_pykrete_config_kept_without_family(monkeypatch):
    from multi_review.core.reviewers import build_command
    monkeypatch.setenv("PYKRETE_CONFIG", "/etc/pykrete.toml")
    cmd = build_command("pykrete", model=None, streaming=True)
    assert "--config" in cmd            # NOT dropped when no family override
    assert "--family" not in cmd
    assert cmd[-1] == "-"

def test_build_command_pykrete_requires_config(monkeypatch):
    import pytest
    from multi_review.core.reviewers import build_command
    monkeypatch.delenv("PYKRETE_CONFIG", raising=False)
    with pytest.raises(ValueError, match="PYKRETE_CONFIG"):
        build_command("pykrete", model=None, streaming=True)
```

```python
# tests/unit/test_promptfile.py
# pykrete is DEFAULT-ON. UPDATE the existing test_fill_defaults_populates_missing
# (L30) assertion to include pykrete:
#     assert pf.reviewers == ["claude", "agy", "codex", "opencode", "pykrete"]
# Then ADD this non-vacuous validity check. Real API: fill_defaults(raw) -> PromptFile;
# validate(pf, base_dir). Required fields: prompt_format_version, task, files
# (promptfile.py:36 _REQUIRED_FIELDS). Membership is enforced by validate(), NOT
# fill_defaults (which passes any string through) — so validate must be called (R3-1).
def test_pykrete_valid_and_defaulted(tmp_path):
    from multi_review.core.promptfile import fill_defaults, validate
    f = tmp_path / "x.py"; f.write_text("")
    base = {"prompt_format_version": 1, "task": "code", "files": [str(f)]}
    pf = fill_defaults({**base, "reviewers": ["pykrete"], "synthesizer": "pykrete",
                        "models": {"pykrete": "glm"}})
    validate(pf, tmp_path)                               # must NOT raise: pykrete is a KNOWN/valid choice
    assert pf.reviewers == ["pykrete"]
    pf2 = fill_defaults(base)                            # omit reviewers -> defaults
    validate(pf2, tmp_path)
    assert "pykrete" in pf2.reviewers                    # default-on
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_reviewers.py tests/unit/test_promptfile.py -q -k "pykrete or default"`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# reviewers.py — pykrete joins the known + default set (default-on, like agy)
ALL_REVIEWERS: list[str] = ["claude", "agy", "codex", "opencode", "pykrete"]
```
(No `DEFAULT_REVIEWERS`, no `resolve_reviewers` change, no `promptfile.py` source change — defaults already derive from `ALL_REVIEWERS`.)

```python
# reviewers.py — CLI_SPEC entry (after "opencode")
    "pykrete": {
        "base": ["pykrete"],
        "stream_flags": [],
        "model_flag": "--family",          # YAML models:{pykrete:<family>} names a NanoGPT family
        "default_args": [],
        "stdin_sentinel": "-",
        "success_exit_codes": (0, 3),      # 3 == success via model downgrade
        "config_env": "PYKRETE_CONFIG",    # path to pykrete.toml (NanoGPT config)
        "records_family_not_model": True,  # model_used is a family, not the actual model (Task 5)
    },
```

```python
# reviewers.py — build_command, insert after `cmd = list(spec["base"])` on the generic path (L156)
    cmd = list(spec["base"])
    if spec.get("config_env"):
        cfg = os.environ.get(spec["config_env"])
        if not cfg:
            raise ValueError(
                f"{cli} requires ${spec['config_env']} to point at a pykrete.toml "
                f"(NanoGPT config). See README 'Pykrete setup'."
            )
        cmd += ["--config", cfg]
    if streaming:
        cmd += spec["stream_flags"]
    # ... unchanged (model/default_args either-or, then stdin_sentinel) ...
```
`build_command` may still `raise` — Task 3 makes the runners catch it so it never escapes.

No `promptfile.py` or `resolve_reviewers` change: both already derive from `ALL_REVIEWERS`, so adding pykrete there makes it default-on automatically. Only the existing `test_fill_defaults_populates_missing` assertion in `tests/unit/test_promptfile.py` must grow to the 5-reviewer list (see Step 1).

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/unit -q` (existing `test_fill_defaults_populates_missing` still green — defaults unchanged).
- [ ] **Step 5: Commit** — `feat(pykrete): known-vs-default reviewer split, CLI_SPEC, build_command plumbing`

---

### Task 2: Per-CLI success exit codes + downgrade flag

**Files:**
- Modify: `multi_review/core/fanout.py` (`reviewer_ok` helper; classifier L205; error branch L211-213; `ReviewerResult` — add `downgraded: bool`; `model_used` for family CLIs L218)
- Modify: `multi_review/core/synthesis.py` (classifier L108)
- Test: `tests/unit/test_fanout.py`

**Interfaces:**
- Produces: `reviewer_ok(cli, rc, text) -> bool` (reads `CLI_SPEC[cli].get("success_exit_codes",(0,))` + `FAILURE_MIN_BYTES`). `ReviewerResult.downgraded` (True iff `rc` is a *non-zero* success code). For `records_family_not_model` CLIs, `model_used` is recorded as `f"family:{model}"` (or `None`), never a bare model id. Consumed by Task 3 (runners), Task 5 (harvest), Task 6 (integration).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_fanout.py
def test_reviewer_ok_pykrete_accepts_downgrade_exit3():
    from multi_review.core.fanout import reviewer_ok
    body = "x" * 100
    assert reviewer_ok("pykrete", 3, body) is True
    assert reviewer_ok("pykrete", 0, body) is True
    assert reviewer_ok("pykrete", 1, body) is False
    assert reviewer_ok("pykrete", 4, body) is False
    assert reviewer_ok("pykrete", 0, "tiny") is False   # byte floor preserved
    assert reviewer_ok("codex", 3, body) is False        # default (0,) unchanged
    assert reviewer_ok("codex", 0, body) is True
```

- [ ] **Step 2: Run to verify it fails** — `uv run pytest tests/unit/test_fanout.py -q`.

- [ ] **Step 3: Implement**

```python
# fanout.py — helper
def reviewer_ok(cli: str, rc: "int | None", text: str) -> bool:
    """Success iff rc is in the CLI's success set AND output >= FAILURE_MIN_BYTES.
    Most CLIs succeed only on 0; pykrete also succeeds on 3 (model downgrade)."""
    return rc in CLI_SPEC[cli].get("success_exit_codes", (0,)) \
        and len(text.encode()) >= FAILURE_MIN_BYTES
```

```python
# fanout.py — classifier (replace L205 + error branch L210-214)
    success_codes = CLI_SPEC[cli].get("success_exit_codes", (0,))
    ok = reviewer_ok(cli, rc, text)
    downgraded = ok and rc != 0            # rc is a non-zero success code
    state.status = "done" if ok else "failed"
    ...
    err = None
    if not ok:
        err = f"exit {rc}" if rc not in success_codes else f"empty output (<{FAILURE_MIN_BYTES} bytes)"
```

```python
# fanout.py — ReviewerResult return (L215-219): honest model + downgrade flag
    if CLI_SPEC[cli].get("records_family_not_model"):
        recorded_model = f"family:{model}" if model is not None else None
    else:
        recorded_model = model if model is not None else "<default>"
    return ReviewerResult(cli, ok, text, stderr_tail, adapter.usage,
                          state.elapsed, error=err, model_used=recorded_model,
                          downgraded=downgraded)
```
Add `downgraded: bool = False` to the `ReviewerResult` dataclass.

```python
# synthesis.py — replace L108 (add reviewer_ok to the existing `from ...fanout import` at L23)
    ok = reviewer_ok(cli, proc.returncode, text)
```

- [ ] **Step 4: Run to verify pass + no regression** — `uv run pytest tests/ -q`.
- [ ] **Step 5: Commit** — `feat(pykrete): success_exit_codes {0,3}; record downgrade + honest model`

---

### Task 3: Config/construction errors become recorded failures (never escape) — [fixes finding A]

**Files:**
- Modify: `multi_review/core/fanout.py` (wrap `build_command` at L102 in `run_reviewer`)
- Modify: `multi_review/core/synthesis.py` (add `except ValueError` around `build_command` at L73 in `_run_synthesis_attempt`)
- Test: `tests/unit/test_fanout.py`

**Interfaces:**
- Consumes: nothing new. Produces: a missing/invalid `PYKRETE_CONFIG` yields a *failed `ReviewerResult`* (reviewer) / *failed tuple* (synthesis), so `spawn.py` still writes `<cli>.state.json` and the aggregator records a failed reviewer section. No exception reaches `asyncio.gather`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_fanout.py
import asyncio
def test_run_reviewer_missing_config_is_failed_not_raised(monkeypatch):
    monkeypatch.delenv("PYKRETE_CONFIG", raising=False)
    from multi_review.core.fanout import run_reviewer, ReviewerState
    from multi_review.core.reviewers import make_adapter
    state = ReviewerState(cli="pykrete", adapter=make_adapter("pykrete"))
    r = asyncio.run(run_reviewer("pykrete", "p", model=None, timeout=None, state=state))
    assert r.ok is False
    assert "PYKRETE_CONFIG" in (r.error or "")   # recorded, not raised
```

- [ ] **Step 2: Run to verify it fails** (currently the `ValueError` propagates out of `run_reviewer`) — `uv run pytest tests/unit/test_fanout.py -q -k missing_config`.

- [ ] **Step 3: Implement**

```python
# fanout.py — run_reviewer, replace the bare `cmd = build_command(...)` at L102
    state.status = "starting"
    state.started_at = time.time()
    try:
        cmd = build_command(cli, model, streaming=True, prompt_path=prompt_path)
    except ValueError as e:
        state.status = "error"; state.finished_at = time.time()
        if state_callback is not None:
            state_callback(cli, state)
        return ReviewerResult(cli, False, "", "", Usage(), state.elapsed, error=str(e))
```
(Keep the existing `state_callback` after; ensure timestamps set before the early return.)

```python
# synthesis.py — _run_synthesis_attempt: add except around build_command (outer try at L72)
    try:
        cmd = build_command(cli, model, streaming=False, prompt_path=tmp_path)
    except ValueError as e:
        return False, "", str(e), None
    # (existing nested try/except for create_subprocess_exec continues unchanged)
```

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/ -q`.
- [ ] **Step 5: Commit** — `fix(pykrete): config errors become recorded failures, never escape fanout`

---

### Task 4: PykreteAdapter (plain-text, no trim)

**Files:** Modify `multi_review/core/adapters.py` (class after `OpenCodeAdapter` L214; `ADAPTER_FOR` L216; `__all__`). Test `tests/unit/test_adapters.py`.

**Interfaces:** `PykreteAdapter(ProgressAdapter)` accumulates raw stdout into `text_parts`; `get_response_text()` returns joined+stripped body **without** AgyAdapter's `## Summary` trim; usage stays zero. Registered `ADAPTER_FOR["pykrete"]`.

- [ ] **Step 1: Failing tests**

```python
# tests/unit/test_adapters.py
def test_pykrete_adapter_accumulates_plaintext():
    from multi_review.core.adapters import PykreteAdapter
    a = PykreteAdapter(); a.feed_line("## Summary"); a.feed_line("Fine.")
    assert a.text == "## Summary\nFine."
    assert a.usage.input_tokens == 0

def test_pykrete_adapter_does_not_trim_preamble():
    from multi_review.core.adapters import PykreteAdapter
    a = PykreteAdapter(); a.feed_line("Intro before heading."); a.feed_line("## Summary")
    assert a.text.startswith("Intro before heading.")

def test_pykrete_registered():
    from multi_review.core.adapters import ADAPTER_FOR, PykreteAdapter
    assert ADAPTER_FOR["pykrete"] is PykreteAdapter
```

- [ ] **Step 2: Verify fail** — `uv run pytest tests/unit/test_adapters.py -q -k pykrete`.
- [ ] **Step 3: Implement**

```python
# adapters.py — after OpenCodeAdapter
class PykreteAdapter(ProgressAdapter):
    """Plain-text buffer for pykrete (wraps pi; no JSONL stream). Whole stdout is
    the review body; no telemetry (usage stays zero). Unlike AgyAdapter there is
    no agentic step-narration preamble to trim — return the body verbatim."""
    def feed_line(self, line: str) -> None:
        super().feed_line(line)
        if not line:
            return
        if self.phase == "starting":
            self.phase = "running"
        self.text_parts.append(line.rstrip("\n") + "\n")
```
Register in `ADAPTER_FOR` and add `"PykreteAdapter"` to `__all__`.

- [ ] **Step 4: Verify pass** — `uv run pytest tests/unit/test_adapters.py -q`.
- [ ] **Step 5: Commit** — `feat(pykrete): PykreteAdapter (plain-text, no preamble trim)`

---

### Task 5: Persistence boundary — telemetry, honest model, downgrade ineligibility, error diagnosis — [fixes finding D + R2-1 + R2-3]

**Root cause (R2):** the new `ReviewerResult` fields (`downgraded`, `error`) and the honest `model_used` are only useful if they survive `spawn.py` → `state.json` → the two loaders. Both loaders reconstruct a `ReviewerResult` from state: `write_harvest_row._state_to_result` (`write_harvest_row.py:17`, feeds eligibility) and `cli/aggregate.py`'s state loader (feeds the REVIEW.md failed-section renderer at `core/aggregate.py:128`, `r.error or 'unknown error'`).

**Files:**
- Modify: `multi_review/core/harvest.py` (`TELEMETRY_QUALITY` L34; `build_row` eligibility ~L116-125)
- Modify: `multi_review/cli/spawn.py` (state dict L91-98 — add `downgraded` + `error`)
- Modify: `multi_review/cli/write_harvest_row.py` (`_state_to_result` L17-38 — read `downgraded` + `error`)
- Modify: `multi_review/cli/aggregate.py` (state loader — read `error` so the failed section shows the diagnosis)
- Test: `tests/unit/test_harvest.py`, and an integration assertion via `write_harvest_row.main` (Task 6)

**Interfaces:** `TELEMETRY_QUALITY["pykrete"]="degraded"`. `spawn.py` state JSON gains `"downgraded": result.downgraded` and `"error": result.error`. `_state_to_result` sets `downgraded=bool(state.get("downgraded", False))` and `error=state.get("error")`. `build_row`: `comparison_eligible = <existing drift condition> and not r.downgraded`. `final_model` is already `family:…`/`None` from Task 2.

- [ ] **Step 1: Failing test**

```python
# tests/unit/test_harvest.py
def test_pykrete_telemetry_degraded():
    from multi_review.core.harvest import TELEMETRY_QUALITY
    assert TELEMETRY_QUALITY["pykrete"] == "degraded"

def test_downgraded_state_yields_ineligible_row(tmp_path):
    # Drive the REAL CLI boundary: write a state.json with downgraded=true + clean
    # drift, run write_harvest_row.main, assert the row's comparison_eligible is False.
    # (mirror the existing write_harvest_row integration setup in tests/)
    ...
```

- [ ] **Step 2: Verify fail** — `uv run pytest tests/unit/test_harvest.py -q -k "pykrete or downgrad"`.
- [ ] **Step 3: Implement**
  - `harvest.py`: add `"pykrete": "degraded"` to `TELEMETRY_QUALITY`; in `build_row`, AND the existing per-reviewer eligibility with `not r.downgraded`.
  - `spawn.py` state dict: add `"downgraded": result.downgraded` and `"error": result.error`.
  - `write_harvest_row.py` `_state_to_result`: add `downgraded=bool(state.get("downgraded", False))` and `error=state.get("error")` to the reconstructed `ReviewerResult`.
  - `cli/aggregate.py` state loader: add `error=state.get("error")` so the failed section renders the real diagnosis (e.g. missing `PYKRETE_CONFIG`) instead of `unknown error`.
- [ ] **Step 4: Verify pass** — `uv run pytest tests/ -q`.
- [ ] **Step 5: Commit** — `feat(pykrete): thread downgraded/error through state.json; degraded telemetry + ineligible downgrades`

---

### Task 6: Integration — drive the real spawn CLI (review, synth, missing-config) — [fixes finding C]

**Files:**
- Test: `tests/integration/test_pykrete_spawn.py` (new) — model on `tests/integration/test_cli_spawn.py`
- Fixture: `tests/fixtures/bin/pykrete` (new, executable shim)

**Interfaces:** Invoke `python -m multi_review.cli.spawn` in a subprocess (NOT `run_reviewer` directly) so argparse choices, `spawn.main`, exit mapping, and `<cli>.md`/`.state.json` writing are all exercised.

- [ ] **Step 1: Fake binary**

```bash
# tests/fixtures/bin/pykrete
#!/usr/bin/env bash
# Fake pykrete. Discriminating shim (R2-4):
#   - echoes its argv to $PYKRETE_ARGV_LOG (so tests can assert --family forwarding)
#   - FAKE_PYKRETE_RC (default 3) sets the exit code
#   - FAKE_PYKRETE_SHORT=1 emits <50 bytes to drive the byte-floor case
[ -n "$PYKRETE_ARGV_LOG" ] && printf '%s\n' "$*" > "$PYKRETE_ARGV_LOG"
cat >/dev/null
if [ "${FAKE_PYKRETE_SHORT:-0}" = "1" ]; then
  printf 'short\n'
else
  printf '## Summary\nFake pykrete review body, well over fifty bytes of content here.\n'
fi
exit "${FAKE_PYKRETE_RC:-3}"
```
`chmod +x`.

- [ ] **Step 2: Failing tests** — invoke the spawn module as a subprocess with `PATH` prepended by the fixture bin and `PYKRETE_CONFIG` set to a temp toml:
  1. **review, exit 3** → wrapper exit 0; `pykrete.state.json` `ok is True` AND `downgraded is True`; `pykrete.md` contains `## Summary`.
  2. **synthesis, exit 3, with `--model glm`** → `--task-mode synthesize --cli pykrete --model glm`; `synth.state.json` `ok is True`; assert `$PYKRETE_ARGV_LOG` contains `--family glm` (proves Task 7 / model_flag translation — a non-discriminating shim would pass regardless).
  3. **missing config** → unset `PYKRETE_CONFIG`; wrapper still exits cleanly and writes `pykrete.state.json` with `ok is False` and `state["error"]` containing `PYKRETE_CONFIG` (NO traceback). Proves R2-3 (error survives into state).
  4. **short output, exit 3** (`FAKE_PYKRETE_SHORT=1`) → `ok is False`, `state["error"]` mentions the byte floor, not `exit 3`.

- [ ] **Step 3: Run** — `uv run pytest tests/integration/test_pykrete_spawn.py -q`. Passes once Tasks 1-5 are in. (Match `ReviewerState`/spawn arg shapes to the real source.)
- [ ] **Step 4: Commit** — `test(pykrete): spawn-CLI integration — exit-3 review/synth + missing-config failure`

---

### Task 7: Synthesizer family forwarding — [fixes finding C2]

**Files:** Modify `skills/multi-review/SKILL.md` (Step 6 external-synthesizer `spawn` command ~L166).

**Interfaces:** The non-claude synthesis dispatch appends `--model <models[synthesizer]>` when set (conditional token, same pattern as the reviewer fanout at SKILL Step 5), so `models:{pykrete:glm}` selects `--family glm` for synthesis too. Without it, pykrete synthesis silently uses the toml default family.

- [ ] **Step 1:** Add the conditional `<MODEL_FLAG>` token to Step 6's `mr-spawn --task-mode synthesize` command, mirroring Step 5's reviewer construction (emit nothing when unset). Note it in the covering synthesis integration test (Task 6 case 2 — pass `--model glm`, assert argv/behaviour).
- [ ] **Step 2: Commit** — `fix(pykrete): forward synthesizer model/family in SKILL Step 6`

---

### Task 8: Documentation

**Files:** `README.md`, `CLAUDE.md`, `skills/multi-review/SKILL.md`, `agents/multi-review-build.md`, `BACKLOG.md`, plus stale in-source comments (`fanout.py:26`, `prompt.py:41` docstring, `spawn.py` `--model` help).

**No tests.** One commit. Rewrite (do not append to) the reviewer/synthesizer/model enumerations.

- [ ] **Step 1: README** — reviewer/synthesizer/model lists become `claude, agy, codex, opencode, pykrete`; **remove the retired `gemini`** from the sample (it currently fails validation); add **Pykrete setup**: `npm link` pykrete; export `NANOGPT_API_KEY`; create `pykrete.toml` + point `PYKRETE_CONFIG` at it; note `models:{pykrete:<family>}` names a NanoGPT *family*; note pykrete is **default-on** (like agy) and shows a failed section until `NANOGPT_API_KEY` + `PYKRETE_CONFIG` are configured.
- [ ] **Step 2: CLAUDE.md** — add invariants: (1) **pykrete is a default-on reviewer** in `ALL_REVIEWERS` (like agy) — uncontained-default posture accepted; (2) **per-CLI `success_exit_codes`** ({0,3}; does not weaken the byte floor); (3) **config errors become recorded failures**, never escape the fanout (critical: pykrete runs by default); (4) **downgrade (exit 3) ⇒ comparison-ineligible + no bogus `final_model`**; (5) **pykrete is agentic/uncontained** (wraps pi) — do not point at untrusted code; (6) **family, not model**. Also **fix the false claim** that every subprocess emits JSONL (already false for agy; also false for pykrete) — distinguish structured-stream vs plain-text adapters.
- [ ] **Step 3: SKILL.md + agents/multi-review-build.md** — add pykrete to the valid reviewer/synthesizer *choice* lists and make the `--list-reviewers` probe list explicit. Because pykrete is **default-on**, it belongs in the default reviewer set wherever enumerated (consistent with `ALL_REVIEWERS` / `fill_defaults`); the `multi-review-build` agent's autonomous `--use-defaults` selection should include pykrete alongside the other four.
- [ ] **Step 4: Stale comments** — update `fanout.py:26` and `prompt.py:41` docstring wording from "rc == 0 and byte floor" to "exit code in the CLI's success set and output ≥ `FAILURE_MIN_BYTES`"; fix `spawn.py` `--model` help (it says "specific model"; for pykrete it is a family).
- [ ] **Step 5: BACKLOG** — defer: `--task` threading from the prompt task; capture pykrete's actual selected model (needs upstream reporting) to replace `family:…`; JSONL passthrough adapter if Pykrete adds `--format json`.
- [ ] **Step 6: Commit** — `docs(pykrete): default-on reviewer setup, invariants, drop retired gemini, fix adapter prose`

---

### Task 9: Live smoke + manual procedure

**Files:** Create `tests/manual/pykrete-smoke.md`.

- [ ] **Step 1:** Procedure: `npm link` pykrete; export `NANOGPT_API_KEY`; write `pykrete.toml` (`default_family` + `[families]` + `[defaults.code]`); set `PYKRETE_CONFIG`; confirm the skill Step-1 probe lists pykrete available; run a single-pass review with an **explicit** `reviewers: [pykrete]` against a small file; confirm `REVIEW.md` has a **Pykrete** `## Summary` section; force a downgrade (bad lead model first in the family list) and confirm the review still lands **and** the harvest row is `comparison_eligible=false`; run once with `PYKRETE_CONFIG` unset and confirm pykrete is a *recorded failed reviewer*, not a crash.
- [ ] **Step 2:** Run once for real; record outcome + any bug in the doc.
- [ ] **Step 3: Commit** — `test(pykrete): manual live-smoke procedure`

---

## Self-Review notes

- **Finding A (config escapes fanout):** Task 3 catches construction errors in both runners → recorded failure, state written, `gather` never sees an exception. Task 6 case 3 proves it via the real spawn CLI.
- **Finding B (silent uncontained default):** user chose **default-on** (rev 5) — pykrete stays in `ALL_REVIEWERS`; the `test_fill_defaults_populates_missing` assertion grows to 5. The safety net that makes default-on acceptable is Task 3 (unconfigured/uninstalled pykrete fails as a recorded reviewer, never crashes the run).
- **Finding C (test not E2E / synth untested):** Task 6 drives `python -m multi_review.cli.spawn` for review + synth + missing-config; Task 7 + Task 6 case 2 cover synthesizer family forwarding.
- **Finding D (comparison contamination):** Task 2 records `downgraded` + honest `family:…`/`None`; Task 5 marks downgraded rows ineligible.
- **No `detect_self` branch:** pykrete is never the host CLI — intentionally omitted.
- **Deferred (BACKLOG):** `--task` threading; actual-model capture; JSONL passthrough.

## Execution Handoff

1. **Subagent-Driven (recommended)** — fresh subagent per task, spec + code-quality review between tasks.
2. **Inline Execution** — batch in this session with checkpoints.

## Review provenance

- **Round 1** (rev 1 → rev 2): 4-reviewer codex panel (holistic, adversarial, classifier deep-dive, build_command deep-dive; gpt-5.6-sol, high effort). 2 HIGH + 4 MEDIUM + 2 LOW, all verified against source, none refuted.
- **Round 2** (rev 2 → rev 3): 2-reviewer changes-only panel (adversarial, holistic). 1 HIGH (R2-1: `downgraded` lost at the state→harvest boundary) + 3 MEDIUM, all verified against source, none refuted. Convergent theme: thread new fields through `state.json`.
- **Round 3** (rev 3 → rev 4): 1-reviewer changes-only convergence check (ran the real suite: 67 passed; live-introspected the promptfile API). 1 MEDIUM (R3-1: Task-1 test was vacuous — `fill_defaults` accepts any string; must call `validate`), verified, fixed in rev 4. Everything else confirmed correct and complete (incl. the third state-loader `build_synth_input.py`, which needs no new keys).
- **Round 4** (rev 4, narrow): confirmed the R3-1 test fix is non-vacuous (`validate`'s valid set derives from `ALL_REVIEWERS` at `promptfile.py:33`). Verdict: **CONVERGED — no new significant findings.**

**Loop converged at Round 4** (finding trend 8 → 4 → 1 → 0; cap was 5). Every finding across all rounds was verified against source before acceptance; none were refuted; no reviewer-stated severity was challenged. Plan is review-complete and ready to execute.
