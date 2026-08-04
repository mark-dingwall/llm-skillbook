# multi-review v0.2 Bundle B Implementation Plan

> **Archival.** Historical record of the work as planned. Line references point at the pre-split `multi_review.py` and may not match current code. Current behaviour lives in `CLAUDE.md`, `README.md` and `skills/multi-review/SKILL.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the orchestration-layer fixes surfaced by the 2026-05-27 dogfood review, swap the deprecated `gemini` CLI for `agy` (Google Antigravity), scrap the fallback/cooldown subsystem, and land the SHOULD-tier robustness fixes — so the v0.2 live smokes (Tasks 35/36/37) can run.

**Architecture:** Five phases delivered in dependency order. Phase 1 deletes the fallback + cooldown + pending subsystem (largest LOC delta, single coherent commit cluster). Phase 2 swaps `gemini` → `agy` (new adapter, new fixtures, new CLI_SPEC entry, drop GeminiAdapter). Phase 3 wires the dead `build_row` path via a new `mr-write-harvest-row` CLI. Phase 4 fixes the synthesis contract (double `## Consensus Summary`, leaked `<filename>` block, missing `mr-build-synth-input`). Phase 5 lands SHOULD-tier fixes (paired-report overwrite, snapshot context-only crash, opencode fixture, frontmatter parity, etc.).

**Tech Stack:** Python 3.11+, asyncio, rich, pytest. Skills layer (Claude Code subagents via Task tool for `claude` reviewer; external CLIs via Bash `run_in_background` subprocess). `agy` CLI ≥1.0.9 as `gemini` replacement.

## Global Constraints (verbatim from CLAUDE.md)

- Prompt goes on stdin, never argv.
- Self-skip is opt-in (`--skip-self`, default off).
- Dual failure classification: `rc ≠ 0` OR captured output `< FAILURE_MIN_BYTES (50)`.
- Output paths never overwrite — `resolve_output_path` auto-suffixes (`-2`, `-3`, …).
- Timeout default is `None` (no `wait_for` wrapper unless `--timeout N` set).
- Context files always inline — both `--mode inline` and `--mode reference` wrap context in `<file-NONCE>` tags.
- `SUMMARY_HEADING_CONTRACT` sentinel must remain in `agents/multi-review-reviewer.md`; `setup.py` interpolates it.
- Schema v2 `usage` alias deprecated, retained until v3.
- NEVER skip hooks (`--no-verify`).
- No comments unless WHY non-obvious.
- No defensive code for hypotheticals.
- Don't commit unless the user (implementer subagents authorized per task) explicitly asks.

---

## Phase 1 — Scrap fallback + cooldown + pending subsystem

**Rationale (user decision, 2026-06-19):** Fallback to weaker models is "review theatre" — cognitively complex review work needs frontier models. Falling back to flash-lite produces noise the user has to manually discount. If we hit 429, fail clean and let the user retry. Deletes the entire cooldown / pending-pair / O_EXCL transition state machine that exists only to manage cross-pass fallback recovery.

### Task B1: Delete pending-pair + cooldown subsystem

**Files:**
- Delete: `multi_review/core/pending.py`
- Delete: `multi_review/cli/pending.py`
- Delete: `multi_review/cli/cooldown_notify.py`
- Delete: `tests/unit/test_pending.py` (if present)
- Delete: `tests/integration/test_cli_pending.py` (if present)
- Delete: `tests/integration/test_cli_cooldown_notify.py` (if present)
- Delete: `tests/manual/cooldown_resume.md` (if present)
- Modify: `multi_review/cli/__init__.py` (drop any `pending` / `cooldown_notify` re-exports)
- Modify: `multi_review/core/paths.py:20` — delete `pending_pair_dir(cwd, pair_id)` helper (orphaned by Task B1).
- Modify: `pyproject.toml` entry-points / console-scripts table — drop `mr-pending`, `mr-cooldown-notify` entries if registered
- Modify: `setup.py` — drop any pending/cooldown wiring

**Interfaces:**
- Consumes: none
- Produces: SKILL.md no longer has Steps 9/10 cooldown orchestration (deleted in Task B6).

- [ ] **Step 1: Inventory references**

```bash
grep -rn --include="*.py" --include="*.md" -E "pending|cooldown_notify|PendingPair|awaiting-pass-2|notification_task_id" multi_review/ tests/ skills/ agents/ docs/
```
Capture full reference list — every hit must be eliminated by end of Phase 1.

- [ ] **Step 2: Delete the modules + tests**

```bash
git rm multi_review/core/pending.py multi_review/cli/pending.py multi_review/cli/cooldown_notify.py
git rm -f tests/unit/test_pending.py tests/integration/test_cli_pending.py tests/integration/test_cli_cooldown_notify.py tests/manual/cooldown_resume.md 2>/dev/null || true
```

- [ ] **Step 3: Run tests — expect import errors elsewhere**

```bash
uv run pytest tests/ -q 2>&1 | head -40
```
Expected: ImportError or collection errors in any file that imported `multi_review.core.pending` or `multi_review.cli.pending`. Note the failing modules — they'll be cleaned in Tasks B2-B6.

- [ ] **Step 4: Commit the deletion stub**

```bash
git add -A
git commit -m "chore: delete pending-pair + cooldown subsystem (Bundle B Phase 1)

User decision 2026-06-19: scrap fallback entirely. Cooldown exists only to
recover gemini quota for pass 2, and the recovery path (fall back to weaker
model) produces low-signal reviews ('review theatre'). Pending-pair state
machine has no other consumer."
```

### Task B2: Strip fallback chain from `core/reviewers.py`

**Files:**
- Modify: `multi_review/core/reviewers.py:7,87-109,128`

**Interfaces:**
- Consumes: none
- Produces: `CLI_SPEC[cli]` entries no longer carry `fallback_chain` key. `build_command` no longer reads it. `resolve_chain` and `CAPACITY_PATTERNS` are gone — callers in `cli/spawn.py`, `core/fanout.py` must be updated in Tasks B3/B4.

- [ ] **Step 1: Write/update failing tests**

Add to `tests/unit/test_reviewers.py`:
```python
def test_cli_spec_has_no_fallback_chain_key():
    from multi_review.core.reviewers import CLI_SPEC
    for cli, spec in CLI_SPEC.items():
        assert "fallback_chain" not in spec, f"{cli} still has fallback_chain"

def test_no_capacity_patterns_export():
    import multi_review.core.reviewers as r
    assert not hasattr(r, "CAPACITY_PATTERNS")
    assert not hasattr(r, "GEMINI_FALLBACK_CHAIN")
    assert not hasattr(r, "resolve_chain")

def test_build_command_no_chain_branch():
    from multi_review.core.reviewers import build_command
    cmd = build_command("claude", model=None, streaming=True)
    assert "--model" in cmd
    assert "opus" in cmd
```

Delete any existing `test_resolve_chain*` / `test_fallback_chain*` / `test_capacity_pattern*` tests in `tests/unit/test_reviewers.py`.

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/unit/test_reviewers.py -q
```
Expected: test_cli_spec_has_no_fallback_chain_key fails (key still present); test_no_capacity_patterns_export fails (symbols still exported).

- [ ] **Step 3: Strip the code**

In `multi_review/core/reviewers.py`:
- Delete module-docstring line 7 mentioning `GEMINI_FALLBACK_CHAIN, CAPACITY_PATTERNS`.
- Delete `GEMINI_FALLBACK_CHAIN` (lines ~87-97) and `CAPACITY_PATTERNS` (lines ~99-105).
- Delete the `fallback_chain` key from every `CLI_SPEC` entry (claude, codex, opencode — gemini entry being deleted entirely in Task B7).
- Replace the `else: chain = spec.get("fallback_chain") or []; if chain: ...` branch in `build_command` (lines ~155-160) with a straight `else: cmd += spec.get("default_args", [])`.
- Delete `resolve_chain` function entirely.
- Remove `re` import if it becomes unused.

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_reviewers.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add multi_review/core/reviewers.py tests/unit/test_reviewers.py
git commit -m "refactor(reviewers): strip fallback_chain/CAPACITY_PATTERNS/resolve_chain

Part of Bundle B fallback scrap. CLI_SPEC entries no longer carry fallback_chain;
build_command's chain-default branch collapses to default_args."
```

### Task B3: Strip fallback from `core/fanout.py`

**Files:**
- Modify: `multi_review/core/fanout.py:18-24,280-339`
- Modify: `tests/unit/test_fanout.py` (drop fallback-related tests)
- Modify: `tests/integration/test_fanout_*.py` (drop capacity-pattern fixtures)

**Interfaces:**
- Consumes: `CLI_SPEC` (now without `fallback_chain`), `make_adapter`, `build_command`.
- Produces: `run_reviewer(cli, prompt, *, model, out_dir, timeout, state_callback)` — one model, one attempt, no chain. Returns `ReviewerResult` with `fallback_attempts=[]` field dropped (Task B5 removes the field from the dataclass).

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_fanout.py`:
```python
def test_run_reviewer_no_chain_walk(tmp_path, monkeypatch):
    """A 429-style stderr from the first model produces a failed result — no second attempt."""
    # use existing subprocess monkey-patch helper if one exists; otherwise spawn echo with rc=1
    from multi_review.core.fanout import run_reviewer
    import asyncio
    # arrange a fake CLI that prints capacity-style stderr then exits 1
    # ... (use existing fixture pattern in test_fanout.py)
    result = asyncio.run(run_reviewer("claude", "x", model="opus", out_dir=tmp_path, timeout=None))
    assert result.ok is False
    assert getattr(result, "fallback_hops", 0) == 0
```

Delete `test_*fallback*`, `test_*capacity*`, `test_*chain*` tests in `tests/unit/test_fanout.py` and `tests/integration/test_fanout_*.py`.

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/unit/test_fanout.py -q
```
Expected: ImportError on `CAPACITY_PATTERNS` (still imported at module top); fallback tests fail.

- [ ] **Step 3: Strip the code**

In `multi_review/core/fanout.py`:
- Remove `CAPACITY_PATTERNS` from the `from multi_review.core.reviewers import (...)` block.
- Delete `_is_capacity_failure` function.
- Delete the chain-walk loop in `run_reviewer` (lines ~270-310): collapse to a single `_run_reviewer_attempt` call.
- Delete `fallback_attempts` / `fallback_hops` accumulation.
- Drop the `state.adapter = make_adapter(cli)` fresh-adapter-per-hop reassignment.
- The state-callback emissions for `phase="fallback"` go away.

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_fanout.py tests/integration/test_fanout_*.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add multi_review/core/fanout.py tests/unit/test_fanout.py tests/integration/
git commit -m "refactor(fanout): collapse chain walk to single attempt

run_reviewer no longer walks GEMINI_FALLBACK_CHAIN on 429. _is_capacity_failure
deleted. ReviewerResult.fallback_attempts field removed."
```

### Task B4: Strip fallback flags from `cli/spawn.py`

**Files:**
- Modify: `multi_review/cli/spawn.py:24,33-95,140-165`
- Modify: `tests/integration/test_cli_spawn.py`

**Interfaces:**
- Consumes: simplified `run_reviewer` (no chain).
- Produces: `spawn` CLI no longer accepts `--fallback-chain` or `--no-fallback`. `--model X` still works as a pin; no model passed → CLI uses its default.

- [ ] **Step 1: Update failing tests**

```python
def test_spawn_no_fallback_flags(tmp_path):
    from multi_review.cli.spawn import main
    rc = main(["--cli", "claude", "--prompt-file", "/nonexistent",
               "--out-dir", str(tmp_path), "--fallback-chain", "a,b,c"])
    # argparse error: unrecognized arg
    assert rc == 2

def test_spawn_no_no_fallback_flag(tmp_path):
    from multi_review.cli.spawn import main
    rc = main(["--cli", "claude", "--prompt-file", "/nonexistent",
               "--out-dir", str(tmp_path), "--no-fallback"])
    assert rc == 2
```

Delete any `test_spawn_walks_fallback*` / `test_spawn_capacity*` tests.

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/integration/test_cli_spawn.py -q
```
Expected: new no-flag tests fail (flags still exist).

- [ ] **Step 3: Strip the code**

In `multi_review/cli/spawn.py`:
- Remove `CAPACITY_PATTERNS, resolve_chain` from imports.
- Delete `--fallback-chain` argparse line.
- Delete the `fallback_disabled` / `override_chain` resolution block.
- Replace `chain = resolve_chain(...)` with `chain = None` (let downstream pick default), and update `run_reviewer` call to pass `model=args.model` only.
- Delete `capacity_pattern = CAPACITY_PATTERNS.get(args.cli)` and any references.
- Drop the `_run_synthesize` synthesis-chain handling similarly (mirror simplification).

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/integration/test_cli_spawn.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add multi_review/cli/spawn.py tests/integration/test_cli_spawn.py
git commit -m "refactor(spawn): drop --fallback-chain/--no-fallback flags

Pinned model (--model X) still works; absent --model = CLI default."
```

### Task B5: Strip fallback fields from state + harvest + report

**Files:**
- Modify: `multi_review/core/fanout.py` (`ReviewerResult` dataclass — drop `fallback_attempts`, `fallback_hops`)
- Modify: `multi_review/cli/aggregate.py` (drop `fallbacks:` frontmatter emission)
- Modify: `multi_review/core/harvest.py` (drop `fallback_hops` per-reviewer field, drop `fallback_attempts` top-level)
- Modify: `multi_review/core/report.py` (drop `gem_fb` references, drop `fallbacks:` EXPERIMENTS column)
- Modify: `multi_review/cli/write_task_result.py` (drop `fallback_attempts` / `fallback_hops` writes)
- Modify: `tests/unit/test_harvest.py`, `tests/unit/test_report.py`, `tests/unit/test_aggregate.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: state.json + harvest row no longer carry `fallback_attempts` / `fallback_hops` / `fallbacks` keys. Schema v2 still v2 — these fields removed are additive-rollback (consumers tolerated absence). EXPERIMENTS.md regen omits the fallbacks column.

- [ ] **Step 1: Update failing tests**

```python
def test_harvest_row_no_fallback_fields(tmp_path):
    from multi_review.core.harvest import build_row
    # ... construct minimal inputs
    row = build_row(...)
    assert "fallback_attempts" not in row
    for ubr in row["usage_by_reviewer"].values():
        assert "fallback_hops" not in ubr

def test_aggregate_no_fallbacks_frontmatter(tmp_path):
    # generate REVIEW.md from a state.json that does NOT have fallback_attempts
    # assert frontmatter has no `fallbacks:` line
    ...
```

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/unit/test_harvest.py tests/unit/test_aggregate.py tests/unit/test_report.py -q
```

- [ ] **Step 3: Strip the fields**

- `core/fanout.py`: remove `fallback_attempts: list = field(default_factory=list)` and `fallback_hops: int = 0` from `ReviewerResult`.
- `cli/aggregate.py`: drop the `if results.get("fallbacks"): ...` frontmatter block.
- `core/harvest.py`: drop `fallback_hops` from `usage_by_reviewer[*]`; drop `fallback_attempts` from top-level row.
- `core/report.py`: line 148 `gem_fb` and any other `fallback_*` accesses → delete. Drop the EXPERIMENTS table column.
- `cli/write_task_result.py`: remove `fallback_attempts`, `fallback_hops` from the written JSON.

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/ -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: drop fallback_attempts/fallback_hops/fallbacks fields

State, harvest row, REVIEW.md frontmatter, and EXPERIMENTS table no longer
carry fallback telemetry. Schema v2 stays v2 (field removal is rollback-safe
for existing v2 consumers — they tolerated absence)."
```

### Task B6: Collapse per-reviewer eligibility + drop SKILL Steps 9/10

**Files:**
- Modify: `multi_review/core/report.py:40,351` (`_is_pair_eligible`, `_compute_pair_eligible`)
- Modify: `skills/multi-review/SKILL.md` (delete Steps 9 + 10; renumber)
- Modify: `agents/multi-review-build.md` (delete `fallback_models:` defaults; delete `delay`, `delay_type` fields; delete `notify` field — only `if_drift` remains relevant for paired runs)

**Interfaces:**
- Consumes: harvest rows no longer carrying `fallback_hops`.
- Produces: pair-level `comparison_eligible = not drift_blocks` (collapsed from `fallback_hops==0 AND not drift_blocks`).

- [ ] **Step 1: Update failing tests**

```python
def test_pair_eligible_collapses_to_drift_only(tmp_path):
    """comparison_eligible should be True for a clean pair with no drift,
    regardless of whether fallback_hops is absent or 0."""
    from multi_review.core.report import _compute_pair_eligible
    # construct a row WITHOUT fallback_hops
    assert _compute_pair_eligible(row_pass1, row_pass2) is True
```

- [ ] **Step 2: Run tests — expect baseline pass (verify behaviour pre-change)**

- [ ] **Step 3: Code changes**

- `core/report.py`:
  - `_is_pair_eligible` (line ~40): drop the `fallback_hops == 0` clause. Keep `comparison_eligible` default-True read.
  - `_compute_pair_eligible` (line ~351): drop the `fallback_hops` check.

- `skills/multi-review/SKILL.md`:
  - Delete the cooldown-trigger step (current Step 9: "if any reviewer had fallback_hops > 0 spawn background sleep + cooldown_notify").
  - Delete the resume-pair step (current Step 10).
  - Renumber Steps 11-13 to 9-11.
  - Update any `pending write` / `pending transition` invocations to a no-op (just delete).

- `agents/multi-review-build.md`:
  - Delete the entire `fallback_models:` defaults section.
  - Delete `delay:`, `delay_type:`, `notify:` lines from the prompt-file template; keep `mode:`, `if_drift:`.

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/ -q
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(report,skill,build): collapse eligibility to drift-only

Pair-level comparison_eligible = (not drift_blocks). SKILL.md cooldown
Steps 9/10 deleted. Build agent's prompt-file template no longer emits
fallback_models/delay/delay_type/notify keys."
```

### Task B7: Update spec + README + CLAUDE.md

**Files:**
- Modify: `docs/superpowers/specs/2026-05-15-multi-review-skill-reframe-design.md` — strike fallback/cooldown/pending sections (§7.1 per-reviewer rule, §8 entire cooldown chapter, §6.2 pass-2-branch fallback paths, §4.2 pending/ tree entries, §5.3 pending.py / cooldown_notify.py CLI entries)
- Modify: `README.md` — drop "Capacity-aware fallback (gemini)" section, drop fallback claims in reviewer-fidelity table
- Modify: `CLAUDE.md` — remove the "Capacity-aware fallback" bullet; add a one-line note "Fallback subsystem scrapped 2026-06-19 — see BACKLOG #X for v0.2.1 quota-proximity probe consideration"
- Modify: `BACKLOG.md` — add v0.2.1 note for "model-config feature" (TOML + edit command) and "quota-proximity probe" as deferred work; archive the fallback-related goals as DROPPED

**Interfaces:** docs only — no code consumers.

- [ ] **Step 1: Update spec** — open the file, delete or strike-through:
  - §4.2: `pending/<pair-id>/` directory description (lines ~88-92).
  - §5.3: `pending.py` and `cooldown_notify.py` bullets (lines ~160-161).
  - §6.2 step 2: pass-2-branch fallback enumeration → simplify to "pass 2 fires immediately after pass 1's join barrier resolves".
  - §7.1: drop per-reviewer fallback rule; collapse pair-level to drift-only.
  - §8 entirely: delete cooldown chapter.
  - §5.4 schema notes for `delay_type` / `delay`: delete.
  - §10.1 `fallbacks` frontmatter column: delete.
- [ ] **Step 2: Update README** — search `grep -n "fallback\|cooldown" README.md` and delete each block.
- [ ] **Step 3: Update CLAUDE.md** — replace the "Capacity-aware fallback (gemini)" bullet with "Single-attempt reviewer runs. 429 → fail clean. Quota-proximity probe deferred to v0.2.1 (see BACKLOG)."
- [ ] **Step 4: Update BACKLOG.md** — add `v0.2.1` cluster: model-config feature + telemetry recovery via `--log-file` + quota-proximity probe.
- [ ] **Step 5: Commit**

```bash
git add docs/ README.md CLAUDE.md BACKLOG.md
git commit -m "docs: scrap fallback/cooldown from spec + README + CLAUDE.md

Fallback subsystem deleted (Bundle B Phase 1). Spec §7.1 per-reviewer rule
collapses to drift-only; §8 cooldown chapter removed; §4.2 pending/ tree
entries removed; §5.3 pending.py / cooldown_notify.py CLI entries removed.
v0.2.1 quota-proximity probe + model-config feature noted in BACKLOG."
```

### Task B8: Sweep — confirm no fallback references remain

- [ ] **Step 1: Final inventory**

```bash
grep -rn --include="*.py" --include="*.md" --include="*.json" -E "fallback_chain|fallback_hops|fallback_attempts|GEMINI_FALLBACK|CAPACITY_PATTERNS|pending-pair|cooldown_notify|PendingPair|awaiting-pass-2" multi_review/ tests/ skills/ agents/ docs/ README.md CLAUDE.md BACKLOG.md
```
Expected: zero hits except (a) historical-context paragraphs in CLAUDE.md / BACKLOG ("Fallback subsystem scrapped 2026-06-19 …") and (b) commit message references in `git log`.

- [ ] **Step 2: Full test run**

```bash
uv run pytest tests/ -q
```
Expected: all green.

- [ ] **Step 3: No commit needed unless sweep found stragglers** — if any, commit as `chore: sweep residual fallback refs`.

---

## Phase 2 — `gemini` → `agy` swap

**Rationale:** Google has officially deprecated the `gemini` CLI in favour of `agy` (Antigravity CLI). `agy --print` returns plain text (no JSONL event stream), so the existing `GeminiAdapter` event-parser is obsolete. New plain-text `AgyAdapter` buffers stdout as the full review body. Telemetry loss (no token usage) is accepted until v0.2.1 (`--log-file` probe BACKLOGGED).

### Task B9: Add `agy` to CLI_SPEC + ALL_REVIEWERS; drop `gemini`

**Files:**
- Modify: `multi_review/core/reviewers.py:22,112-149`
- Modify: `tests/unit/test_reviewers.py`

**Interfaces:**
- Consumes: none.
- Produces: `ALL_REVIEWERS = ["claude", "agy", "codex", "opencode"]`. `CLI_SPEC["agy"]` entry with the shape below. No `CLI_SPEC["gemini"]` key.

- [ ] **Step 1: Write failing tests**

```python
def test_all_reviewers_contains_agy_not_gemini():
    from multi_review.core.reviewers import ALL_REVIEWERS
    assert "agy" in ALL_REVIEWERS
    assert "gemini" not in ALL_REVIEWERS

def test_cli_spec_agy_shape():
    from multi_review.core.reviewers import CLI_SPEC
    s = CLI_SPEC["agy"]
    assert s["base"] == ["agy", "--print"]
    assert s["model_flag"] == "--model"
    assert s["stdin_sentinel"] is None
    assert s["stream_flags"] == []          # agy has no event-stream flag
    assert s["default_args"] == []          # unpinned — let agy pick its own default

def test_cli_spec_no_gemini_entry():
    from multi_review.core.reviewers import CLI_SPEC
    assert "gemini" not in CLI_SPEC

def test_build_command_agy_with_default():
    """agy unpinned by default — let agy pick. Pinned --model still works."""
    from multi_review.core.reviewers import build_command
    cmd = build_command("agy", model=None, streaming=True)
    assert cmd == ["agy", "--print"]   # no --model flag

def test_build_command_agy_pinned():
    from multi_review.core.reviewers import build_command
    cmd = build_command("agy", model="Gemini 3.1 Pro (High)", streaming=True)
    assert "--model" in cmd
    assert "Gemini 3.1 Pro (High)" in cmd
```

- [ ] **Step 2: Run tests — expect failures**

- [ ] **Step 3: Code changes**

In `multi_review/core/reviewers.py`:
```python
ALL_REVIEWERS: list[str] = ["claude", "agy", "codex", "opencode"]
```
Replace the `"gemini"` block in `CLI_SPEC` with:
```python
"agy": {
    "base": ["agy", "--print"],
    "stream_flags": [],
    "model_flag": "--model",
    # default_args=[] — let agy pick its default model. v0.2.1 model-config
    # feature will read user-specified model from TOML. Verified working
    # values for explicit pinning: "Gemini 3.1 Pro (High)" (default-ish),
    # "Gemini 3.5 Flash (Low|Medium|High)" (cheaper variants).
    "default_args": [],
    "stdin_sentinel": None,
},
```

In `build_command`: ensure the `if streaming: cmd += spec["stream_flags"]` branch tolerates an empty `stream_flags` list (it already does — list concat with empty is fine). No further changes needed.

- [ ] **Step 4: Run tests to verify pass**

- [ ] **Step 5: Commit**

```bash
git add multi_review/core/reviewers.py tests/unit/test_reviewers.py
git commit -m "feat(reviewers): swap gemini → agy in CLI_SPEC

agy CLI 1.0.9+ replaces deprecated gemini CLI. agy --print returns plain text
(no JSONL event stream), so stream_flags is empty. default_args=[] — unpinned;
agy picks its own default. v0.2.1 model-config feature will let users specify.
ALL_REVIEWERS = [claude, agy, codex, opencode]."
```

### Task B10: Add `AgyAdapter`; delete `GeminiAdapter`

**Files:**
- Modify: `multi_review/core/adapters.py:110-141, 218-237`
- Modify: `tests/unit/test_adapters.py`
- Add: `tests/fixtures/streams/agy/success.txt` (plain text — single review body, ≥50 bytes)
- Delete: `tests/fixtures/streams/gemini/` (entire directory)

**Interfaces:**
- Consumes: `ProgressAdapter` ABC.
- Produces: `AgyAdapter` with `feed_line` that appends every non-empty line to `text_parts`, leaves `usage` all-zero, sets `phase = "running"` on first line and `phase = "done"` only when caller signals EOF (since plain text has no terminal event). `ADAPTER_FOR = {"claude": ..., "agy": AgyAdapter, "codex": ..., "opencode": ...}`.

- [ ] **Step 1: Write failing tests**

```python
def test_agy_adapter_buffers_plain_text():
    from multi_review.core.adapters import AgyAdapter
    a = AgyAdapter()
    a.feed_line("Hi, Gemini here.")
    a.feed_line("Second line.")
    assert "".join(a.text_parts) == "Hi, Gemini here.\nSecond line.\n" or \
           "".join(a.text_parts) == "Hi, Gemini here.Second line." or \
           "Gemini here" in "".join(a.text_parts)
    assert a.usage.input_tokens == 0
    assert a.usage.output_tokens == 0
    assert a.phase in ("running", "done")

def test_agy_fixture_round_trip():
    from multi_review.core.adapters import AgyAdapter
    a = AgyAdapter()
    fixture = Path("tests/fixtures/streams/agy/success.txt").read_text()
    for line in fixture.splitlines():
        a.feed_line(line)
    body = "".join(a.text_parts)
    assert len(body) >= 50

def test_no_gemini_adapter_export():
    import multi_review.core.adapters as m
    assert not hasattr(m, "GeminiAdapter")
    assert "gemini" not in m.ADAPTER_FOR
    assert m.ADAPTER_FOR["agy"] is m.AgyAdapter
```

- [ ] **Step 2: Run tests — expect failures**

- [ ] **Step 3: Implement `AgyAdapter`**

In `multi_review/core/adapters.py`:
```python
class AgyAdapter(ProgressAdapter):
    """Plain-text buffer for agy --print (no event stream).

    agy does not expose a JSONL --output-format. The whole stdout is the
    review body. Token telemetry is not available via --print; usage stays
    zero. v0.2.1 may probe --log-file for recoverable counters (BACKLOG).
    """
    def feed_line(self, line: str) -> None:
        super().feed_line(line)
        if not line:
            return
        if self.phase == "starting":
            self.phase = "running"
        self.text_parts.append(line + "\n")
```

Delete the `GeminiAdapter` class entirely.

Update `ADAPTER_FOR`:
```python
ADAPTER_FOR = {
    "claude": ClaudeAdapter,
    "agy": AgyAdapter,
    "codex": CodexAdapter,
    "opencode": OpenCodeAdapter,
}
```

Update `__all__` — replace `"GeminiAdapter"` with `"AgyAdapter"`.

- [ ] **Step 4: Add fixture**

```bash
mkdir -p tests/fixtures/streams/agy
git rm -rf tests/fixtures/streams/gemini
```

Write `tests/fixtures/streams/agy/success.txt`:
```
# Review

The auth middleware in `src/auth.py:42` uses `<` instead of `<=` for token
expiry. This causes a 1-second race window where the token is treated as
expired but still accepted on retry.

## Recommendation

Use `<=` and add a leeway constant `LEEWAY_SECONDS = 1`.

## Severity

Medium — race exists but window is tiny.
```
(Body ≥ 50 bytes so dual-failure check passes.)

- [ ] **Step 5: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_adapters.py -q
```

- [ ] **Step 6: Commit**

```bash
git add multi_review/core/adapters.py tests/unit/test_adapters.py tests/fixtures/streams/
git commit -m "feat(adapters): replace GeminiAdapter with AgyAdapter (plain text)

agy --print returns plain text; AgyAdapter buffers all non-empty lines into
text_parts, leaves Usage at zero. GeminiAdapter and tests/fixtures/streams/gemini/
deleted. Telemetry recovery via agy --log-file deferred to v0.2.1."
```

### Task B11: Self-detection — drop `GEMINI_CLI`, keep `ANTIGRAVITY_AGENT`

**Files:**
- Modify: `multi_review/core/reviewers.py` (`detect_self` function)
- Modify: `tests/unit/test_reviewers.py`

**Interfaces:**
- Consumes: none.
- Produces: `detect_self()` reads `CLAUDE_CODE_ENTRYPOINT`, `CODEX_ENV`, `OPENCODE` env vars. `ANTIGRAVITY_AGENT` short-circuits to `"none"` (agy spawning a subprocess of multi-review). `GEMINI_CLI` env var no longer recognised.

- [ ] **Step 1: Write failing tests**

```python
def test_detect_self_no_gemini_branch(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
    monkeypatch.delenv("CODEX_ENV", raising=False)
    monkeypatch.delenv("OPENCODE", raising=False)
    monkeypatch.delenv("ANTIGRAVITY_AGENT", raising=False)
    monkeypatch.setenv("GEMINI_CLI", "1")
    from multi_review.core.reviewers import detect_self
    assert detect_self() == "none"  # GEMINI_CLI no longer recognised

def test_detect_self_antigravity_still_shortcircuits(monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_AGENT", "1")
    from multi_review.core.reviewers import detect_self
    assert detect_self() == "none"
```

- [ ] **Step 2: Run tests — expect failures** on the no-gemini-branch test.

- [ ] **Step 3: Code changes**

Delete the `GEMINI_CLI` env-var branch in `detect_self()`. Keep `ANTIGRAVITY_AGENT` short-circuit branch.

- [ ] **Step 4: Run tests to verify pass**

- [ ] **Step 5: Commit**

```bash
git add multi_review/core/reviewers.py tests/unit/test_reviewers.py
git commit -m "fix(reviewers): drop GEMINI_CLI env-var branch from detect_self

gemini CLI deprecated. ANTIGRAVITY_AGENT=1 short-circuit retained (set by
agy on child processes; verified 2026-06-19)."
```

### Task B12: Update build agent + SKILL.md + agents/reviewer.md for agy

**Files:**
- Modify: `agents/multi-review-build.md` (model defaults, reviewer enumeration prose, read-permission scope note)
- Modify: `agents/multi-review-reviewer.md` (if it enumerates reviewers anywhere)
- Modify: `skills/multi-review/SKILL.md` (any literal `gemini` references)

**Interfaces:** build agent now emits `agy` as a valid reviewer name; emits no `models.gemini` / no `models.agy` keys by default (model unpin — Task B15).

- [ ] **Step 1: Inventory `gemini` mentions**

```bash
grep -n "gemini" agents/*.md skills/multi-review/SKILL.md
```

- [ ] **Step 2: Replace `gemini` with `agy` in every reviewer-list and prompt-file template hit.** Keep one historical-context paragraph in the build agent that explains the swap rationale and the read-permission caveat:

> **agy permission posture.** `agy --print` defaults often refuse reads outside the current working directory. When you prepare a prompt that targets files outside cwd, scope the review to cwd OR copy the target tree to cwd / a `/tmp/<scratch>/` directory first (omit `node_modules`, `.git`, `dist`, `build`, `.venv`, `__pycache__`, vendor dirs). Don't pass `--dangerously-skip-permissions` blindly — read-only reviews don't need it.

- [ ] **Step 3: Commit**

```bash
git add agents/ skills/multi-review/SKILL.md
git commit -m "docs(agents,skill): swap gemini → agy in agent prompts

Build agent prompt-file template uses agy. SKILL.md reviewer enumeration
updated. Build agent gains a permission-posture note explaining agy refuses
out-of-cwd reads by default."
```

### Task B13: Smoke-test `agy` integration end-to-end (manual)

**Files:**
- Add: `tests/manual/agy-smoke.md`

**Rationale:** No automated end-to-end test exists for the new CLI — verify the actual `agy` binary works in our subprocess + adapter combo.

- [ ] **Step 1: Write the manual procedure**

```markdown
# agy reviewer manual smoke

## Setup
- `agy --version` ≥ 1.0.9
- `which agy` resolves to `~/.local/bin/agy` or wherever it's installed

## Procedure
1. From this repo root:
   ```bash
   uv run python -m multi_review.cli.spawn --cli agy --prompt-file <(echo "Review this file:
   $(cat README.md | head -50)
   Are there any bugs?") --out-dir /tmp/agy-smoke --timeout 120
   ```
2. Wait for completion.
3. Check `/tmp/agy-smoke/REVIEW.md` exists, ≥50 bytes, plain prose review.
4. Check `/tmp/agy-smoke/state.json` — `ok: true`, `usage.input_tokens` and friends all 0 (expected — agy --print has no telemetry).
5. With `--model` override:
   ```bash
   uv run python -m multi_review.cli.spawn --cli agy --model "Gemini 3.5 Flash (Low)" ...
   ```
   Confirm faster + smaller output.

## Pass criteria
- rc 0
- REVIEW.md plausible
- state.json valid JSON with `ok: true`
- No crashes from empty stream_flags

## Failure modes seen
- agy refusing to read `/proc/...` etc. — use real cwd files.
- `--print-timeout 5m0s` default; our default `--timeout None` overrides.
```

- [ ] **Step 2: Commit**

```bash
git add tests/manual/agy-smoke.md
git commit -m "docs(tests): manual smoke for agy reviewer integration"
```

---

## Phase 3 — Harvest wiring (`build_row` was dead code)

**Rationale:** `core/harvest.build_row` has zero callers in `cli/`. SKILL Step 8 currently hand-builds a row JSON, which means the schema-v2 `comparison_eligible` chain has been unreachable and the field-set diverged. New `mr-write-harvest-row` CLI bridges the gap, called once at end of each pass.

### Task B14: New `cli/write_harvest_row.py` — wire `build_row`

**Files:**
- Create: `multi_review/cli/write_harvest_row.py`
- Modify: `multi_review/core/harvest.py` (add missing fields + guard `usage=None`)
- Modify: `skills/multi-review/SKILL.md` (replace hand-built row with CLI call)
- Add: `tests/integration/test_cli_write_harvest_row.py`
- Modify: `tests/unit/test_harvest.py`
- Modify: `pyproject.toml` (register `mr-write-harvest-row` console script)

**Interfaces:**
- Consumes: state JSON files (one per reviewer, written by `cli/spawn.py` or `cli/write_task_result.py`), `--prompt-file`, `--out-review` (REVIEW.md path), `--run-id`, `--log` (central harvest JSONL path).
- Produces: appends one row to `--log` (or to `<cwd>/.multi-review/pending-harvest/<run-id>.json` if central log write denied). Row schema:

```python
{
    "schema_version": 2,
    "run_id": str,
    "started_at": str,         # ISO8601 from earliest state.json
    "finished_at": str,        # ISO8601 from latest state.json
    "wall_seconds": float,
    "cwd": str,
    "project": str,            # from --project-tag or git origin or cwd.name
    "task": str,               # from prompt-file frontmatter or --task
    "mode": str,               # "inline" | "reference" (from --mode)
    "argv": list[str],         # SKILL-level argv captured by caller
    "prompt_bytes": int,       # len of prompt-file
    "output_bytes": int,       # len of out-review
    "reviewers_attempted": list[str],
    "reviewers_succeeded": list[str],
    "reviewers_failed": list[str],
    "synthesizer": str | None,
    "synthesis_ok": bool,
    "pair_id": str | None,
    "prompt_file": str,
    "prompt_format_version": int,
    "drift_status": str,       # "clean" | "drifted" | "unchecked" | "skipped"
    "telemetry_notes": list[str],
    "usage_by_reviewer": dict,  # {cli: {input_tokens, output_tokens, ..., comparison_eligible}}
    "usage": dict,              # v1 alias (deprecated, retained until v3)
}
```

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_harvest.py`:
```python
def test_build_row_includes_new_fields():
    from multi_review.core.harvest import build_row
    row = build_row(
        run_id="r1", started_at="2026-06-19T10:00:00Z",
        finished_at="2026-06-19T10:01:30Z", cwd="/tmp/proj",
        project="proj", task="code", mode="inline",
        argv=["spawn", "--cli", "claude"],
        prompt_bytes=1234, output_bytes=5678,
        reviewer_results=[...], synthesizer=None, synthesis_ok=False,
        pair_id=None, prompt_file="...", prompt_format_version=1,
        drift_status="clean", telemetry_notes=[],
    )
    assert row["started_at"] == "2026-06-19T10:00:00Z"
    assert row["cwd"] == "/tmp/proj"
    assert row["argv"] == ["spawn", "--cli", "claude"]
    assert row["prompt_bytes"] == 1234
    assert row["output_bytes"] == 5678

def test_build_row_guards_usage_none():
    """build_row must not crash when a ReviewerResult.usage is None."""
    from multi_review.core.harvest import build_row
    rr_no_usage = make_reviewer_result(cli="claude", ok=True, usage=None)
    row = build_row(..., reviewer_results=[rr_no_usage], ...)
    assert row["usage_by_reviewer"]["claude"]["input_tokens"] == 0
```

Add `tests/integration/test_cli_write_harvest_row.py`:
```python
def test_write_harvest_row_appends_to_log(tmp_path):
    log = tmp_path / "runs.jsonl"
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    (state_dir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "usage": {...}, ...
    }))
    review = tmp_path / "REVIEW.md"
    review.write_text("# Review\n...")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Review this.")
    rc = main([
        "--state-dir", str(state_dir),
        "--out-review", str(review),
        "--prompt-file", str(prompt),
        "--run-id", "r1",
        "--log", str(log),
        "--mode", "inline",
        "--project", "test",
        "--task", "code",
    ])
    assert rc == 0
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["run_id"] == "r1"

def test_write_harvest_row_falls_back_to_pending_on_perm_denied(tmp_path):
    # Make --log path unwritable
    ...
    rc = main([..., "--log", "/proc/1/no-write"])
    assert rc == 0  # graceful fallback
    pending = tmp_path / ".multi-review/pending-harvest"
    assert len(list(pending.glob("*.json"))) == 1
```

- [ ] **Step 2: Run tests — expect failures**

- [ ] **Step 3: Update `core/harvest.build_row`**

Add fields: `started_at`, `finished_at`, `cwd`, `argv`, `prompt_bytes`, `output_bytes`.

Guard usage:
```python
def _usage_dict(r) -> dict:
    u = getattr(r, "usage", None)
    if u is None:
        return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0,
                "tool_calls": 0, "comparison_eligible": True}
    d = u.as_dict()
    d["comparison_eligible"] = True   # default; SKILL drift step may override
    return d
```

- [ ] **Step 4: Implement `cli/write_harvest_row.py`**

```python
"""mr-write-harvest-row — read state.json files + REVIEW.md + prompt-file,
build a v2 harvest row, append to --log (or fall back to pending-harvest)."""
import argparse, json, sys
from pathlib import Path
from multi_review.core.harvest import build_row
from multi_review.core.paths import state_dir_root

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--out-review", type=Path, required=True)
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--mode", choices=["inline", "reference"], required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--pair-id", default=None)
    p.add_argument("--drift-status", default="clean")
    args = p.parse_args(argv)

    states = []
    for sf in sorted(args.state_dir.glob("*.state.json")):
        try:
            states.append(json.loads(sf.read_text()))
        except Exception as e:
            print(f"warning: skipping malformed {sf}: {e}", file=sys.stderr)

    row = build_row(
        run_id=args.run_id,
        states=states,
        out_review=args.out_review,
        prompt_file=args.prompt_file,
        mode=args.mode,
        project=args.project,
        task=args.task,
        pair_id=args.pair_id,
        drift_status=args.drift_status,
    )

    try:
        with args.log.open("a") as f:
            f.write(json.dumps(row) + "\n")
        return 0
    except (PermissionError, OSError) as e:
        pending = Path.cwd() / ".multi-review/pending-harvest"
        pending.mkdir(parents=True, exist_ok=True)
        (pending / f"{args.run_id}.json").write_text(json.dumps(row))
        print(f"note: central log unwritable ({e}); buffered to {pending}", file=sys.stderr)
        return 0
```

- [ ] **Step 5: Update SKILL.md Step 8**

Replace the hand-built row JSON block with:
```bash
uv run python -m multi_review.cli.write_harvest_row \
  --state-dir <run_dir>/states/ \
  --out-review <REVIEW_PATH> \
  --prompt-file <PROMPT_FILE> \
  --run-id <RUN_ID> \
  --log <CENTRAL_PATH>/runs.jsonl \
  --mode <MODE> \
  --project <PROJECT> \
  --task <TASK> \
  --drift-status <DRIFT_STATUS>
```

- [ ] **Step 6: Register console script**

In `pyproject.toml`:
```toml
[project.scripts]
mr-write-harvest-row = "multi_review.cli.write_harvest_row:main"
```

- [ ] **Step 7: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_harvest.py tests/integration/test_cli_write_harvest_row.py -q
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(harvest): mr-write-harvest-row CLI wires dead build_row path

build_row gains started_at/finished_at/cwd/argv/prompt_bytes/output_bytes,
guards usage=None. SKILL Step 8 replaces hand-built row JSON with this CLI.
Schema v2 chain (per-reviewer comparison_eligible) now reachable end-to-end."
```

---

## Phase 4 — Synthesis contract fixes

**Rationale:** Synthesizer agent currently outputs `## Consensus Summary` + `### Headline` + trailing `### Filename suggestion\n<filename>...</filename>`. `cli/write_task_result.py:45,65` writes that verbatim. `core/aggregate.py:162-165` then prepends its own `## Consensus Summary`. Result: every REVIEW.md ships with a doubled heading and a leaked `<filename>` block. Also: no `cli/build_synth_input` exists — non-claude synthesis branch in SKILL Step 6 is unrunnable.

### Task B15: Synth output contract — parse filename + prevent doubled heading

**Files:**
- Modify: `agents/multi-review-synthesizer.md` — synth agent now outputs body only (no `## Consensus Summary` heading) and a separate `<filename>` line that the host-side tooling parses out.
- Modify: `multi_review/cli/write_task_result.py:45,65` — parse trailing `<filename>...</filename>` block, write filename + body separately to state.json (or to a sidecar `suggested_filename.txt`).
- Modify: `multi_review/core/aggregate.py:65-70,162-165` — never demote a `## Summary` heading and never prepend its own `## Consensus Summary` if the body already contains one; emit the heading exactly once.

**Interfaces:**
- Consumes: synth-agent verbatim text.
- Produces: state.json carries `body` (filename-stripped) and `suggested_filename` (parsed). aggregate.py emits `## Consensus Summary\n\n<body>` once.

- [ ] **Step 1: Write failing tests**

```python
def test_write_task_result_parses_filename(tmp_path):
    text = "Some headline.\n\nBody text.\n\n### Filename suggestion\n<filename>auth-review.md</filename>\n"
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    rc = write_task_result.main([
        "--cli", "claude", "--state-dir", str(state_dir),
        "--text-file", str(tmp_path / "raw.txt"),
        "--task-mode", "synthesize",
    ])
    state = json.loads((state_dir / "claude.state.json").read_text())
    assert state["body"] == "Some headline.\n\nBody text.\n"
    assert state["suggested_filename"] == "auth-review.md"

def test_aggregate_no_double_consensus_heading(tmp_path):
    # Set up synth body without leading heading
    body = "Both reviewers flagged the auth race.\n\nFix: use <=.\n"
    out = run_aggregate(body=body)
    headings = [l for l in out.splitlines() if l.strip() == "## Consensus Summary"]
    assert len(headings) == 1
```

- [ ] **Step 2: Run tests — expect failures**

- [ ] **Step 3: Update synth agent prompt** (`agents/multi-review-synthesizer.md`):
  - Output structure: body only (plain prose, optional inner `### Headline`).
  - Append a single trailing line: `<filename>suggested-name.md</filename>` (no `### Filename suggestion` heading).
  - Explicit: "Do NOT emit a `## Consensus Summary` heading — the host wraps your output with the section heading."

- [ ] **Step 4: Update `cli/write_task_result.py`**:

```python
FILENAME_TAG_RE = re.compile(r"<filename>(.+?)</filename>\s*$", re.DOTALL)

def _split_filename(text: str) -> tuple[str, str | None]:
    m = FILENAME_TAG_RE.search(text)
    if not m:
        return text, None
    body = text[:m.start()].rstrip()
    return body, m.group(1).strip()
```

For `--task-mode synthesize`: extract filename, write `body` (not raw text) and `suggested_filename` separately.

- [ ] **Step 5: Update `core/aggregate.py`**:

Around lines 162-165 — change "prepend `## Consensus Summary\n`" to:
```python
if not body.lstrip().startswith("## Consensus Summary"):
    body = "## Consensus Summary\n\n" + body.lstrip()
```
And remove the line-65 heading demotion (the in-memory regex demotion is no longer needed since synth agent doesn't emit `## Summary`).

- [ ] **Step 6: Run tests to verify pass**

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "fix(synth): single Consensus Summary heading + parse filename tag

Synth agent emits body + trailing <filename>...</filename> tag only.
write_task_result splits filename out and stores it in state.json.
aggregate adds the heading once if absent. Fixes the doubled heading +
leaked <filename> tag that has fired on every paired run."
```

### Task B16: New `cli/build_synth_input.py` — wire `build_synthesis_input`

**Files:**
- Create: `multi_review/cli/build_synth_input.py`
- Modify: `multi_review/core/synthesis.py` (fix the swapped `(body, nonce)` return — line 49: code returns `nonce, body`, docstring says `body, nonce`)
- Modify: `skills/multi-review/SKILL.md` Step 6 (call this CLI before non-claude synthesis branch)
- Add: `tests/integration/test_cli_build_synth_input.py`
- Modify: `pyproject.toml` — register `mr-build-synth-input` console script

**Interfaces:**
- Consumes: `--state-dir` (reviewer state.json files), `--out-prompt-file` (where to write synth prompt), optional `--out-nonce-file`.
- Produces: writes synth prompt to `--out-prompt-file`, prints `nonce` to stdout (or writes to `--out-nonce-file`). Synth prompt format: synth preamble + per-reviewer `<review reviewer="…" nonce="NONCE">…</review>` blocks (matches existing `build_synthesis_input` shape).

- [ ] **Step 1: Write failing tests**

```python
def test_build_synth_input_writes_prompt_and_nonce(tmp_path):
    state_dir = tmp_path / "states"
    state_dir.mkdir()
    (state_dir / "claude.state.json").write_text(json.dumps({
        "cli": "claude", "ok": True, "body": "claude's review", ...
    }))
    (state_dir / "codex.state.json").write_text(json.dumps({
        "cli": "codex", "ok": True, "body": "codex's review", ...
    }))
    out_prompt = tmp_path / "synth-prompt.md"
    out_nonce = tmp_path / "nonce.txt"
    rc = main(["--state-dir", str(state_dir),
               "--out-prompt-file", str(out_prompt),
               "--out-nonce-file", str(out_nonce)])
    assert rc == 0
    nonce = out_nonce.read_text().strip()
    prompt = out_prompt.read_text()
    assert f'nonce="{nonce}"' in prompt or nonce in prompt
    assert "claude's review" in prompt
    assert "codex's review" in prompt
```

- [ ] **Step 2: Run tests — expect failures**

- [ ] **Step 3: Fix the swapped tuple in `core/synthesis.py`**

```python
def build_synthesis_input(results, ...) -> tuple[str, str]:
    """Returns (body, nonce)."""
    ...
    return body, nonce      # was: return nonce, "\n".join(parts)
```

Update docstring + callers (search for any callers that destructured `(nonce, body)` — fix them).

- [ ] **Step 4: Implement `cli/build_synth_input.py`**

```python
"""mr-build-synth-input — read reviewer state.json files, emit synth prompt + nonce."""
import argparse, json, sys
from pathlib import Path
from multi_review.core.synthesis import build_synthesis_input

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--out-prompt-file", type=Path, required=True)
    p.add_argument("--out-nonce-file", type=Path, default=None)
    args = p.parse_args(argv)

    results = []
    for sf in sorted(args.state_dir.glob("*.state.json")):
        try:
            results.append(json.loads(sf.read_text()))
        except Exception as e:
            print(f"warning: skipping malformed {sf}: {e}", file=sys.stderr)

    body, nonce = build_synthesis_input(results)
    args.out_prompt_file.write_text(body)
    if args.out_nonce_file:
        args.out_nonce_file.write_text(nonce)
    else:
        print(nonce)
    return 0
```

- [ ] **Step 5: Update SKILL.md Step 6**

Both branches (claude-synth via Task tool, external-synth via Bash subprocess):
```bash
uv run python -m multi_review.cli.build_synth_input \
  --state-dir <run_dir>/states \
  --out-prompt-file <run_dir>/synth-prompt.md \
  --out-nonce-file <run_dir>/synth-nonce.txt
```
For the external branch, then:
```bash
uv run python -m multi_review.cli.spawn --cli <synthesizer> \
  --prompt-file <run_dir>/synth-prompt.md \
  --task-mode synthesize \
  --input-nonce $(cat <run_dir>/synth-nonce.txt) \
  --out-dir <run_dir>/synth/
```

- [ ] **Step 6: Register console script**

In `pyproject.toml`:
```toml
mr-build-synth-input = "multi_review.cli.build_synth_input:main"
```

- [ ] **Step 7: Run tests to verify pass**

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(synth): mr-build-synth-input CLI + fix (body,nonce) tuple order

core.synthesis.build_synthesis_input now returns (body, nonce) as documented
— previously returned (nonce, body), which broke every external-synth call.
New CLI emits the prompt + nonce to disk for the SKILL Step 6 non-claude
branch."
```

---

## Phase 5 — SHOULD-tier robustness fixes

### Task B17: SKILL join-barrier prose — `BashOutput` vs `TaskGet`

**Files:**
- Modify: `skills/multi-review/SKILL.md` (locate the join-barrier paragraph by content: it currently reads "(b) every backgrounded spawn.py task reports completion (poll via TaskGet/TaskOutput)". The step number may have shifted after B6 deleted cooldown steps — locate by content, not by number.)
- Add: `tests/manual/skill-step5-join.md` (filename retained for ledger continuity even if SKILL step number differs).

**Rationale:** Current prose says "poll via TaskGet/TaskOutput" for "every backgrounded spawn.py task" — but external reviewers are launched via `Bash run_in_background`, so the right poll mechanism is `BashOutput`. Only the `claude` reviewer (launched via the Task tool as a `multi-review-reviewer` subagent) uses `TaskGet`/`TaskOutput`.

- [ ] **Step 1: Rewrite the join-barrier section** (find the step that begins "Wait until all reviewers have finished" or similar — its number may have shifted after B6):

```markdown
### Join barrier

Wait until all reviewers have finished. The mechanism depends on how each
was dispatched:

- **`claude` reviewer** (Task tool, `multi-review-reviewer` subagent):
  `TaskGet <task_id>` returns its status; poll until `status == "complete"`.
  Read the final state via the state.json the reviewer writes (or via
  `TaskOutput` for the agent's return text — but state.json is authoritative).
- **External reviewers** (`agy`, `codex`, `opencode`, dispatched via
  `Bash run_in_background` running `multi_review.cli.spawn`):
  `BashOutput <bash_id>` returns the latest stdout/stderr lines + an `exited`
  flag. Poll until `exited: true` for every external bash_id.

Don't mix the two: `TaskGet` against a Bash background id will fail; vice
versa. Track the dispatch type for each reviewer when you launch them.
```

- [ ] **Step 2: Add manual smoke** to `tests/manual/skill-step5-join.md` describing the expected polling pattern + the failure mode if the wrong tool is called.

- [ ] **Step 3: Commit**

```bash
git add skills/multi-review/SKILL.md tests/manual/
git commit -m "fix(skill): Step 5 join barrier prose — BashOutput for external, TaskGet for claude

Reviewer dispatch is mixed: claude → Task subagent → TaskGet; external CLIs
→ Bash run_in_background → BashOutput. Polling with the wrong tool fails
silently or with an unhelpful error."
```

### Task B18: Interim model unpin for codex + opencode

**Files:**
- Modify: `multi_review/core/reviewers.py` (`CLI_SPEC["codex"]` and `CLI_SPEC["opencode"]` `default_args`)
- Modify: `agents/multi-review-build.md` (default prompt-file template — omit `models.codex`, `models.opencode`; keep `models.claude: claude-opus-4-7`)

**Rationale:** Model IDs churn weekly (codex `gpt-5.5` → ?; opencode openrouter IDs change without notice). v0.2.1 will introduce a model-config feature (TOML + edit command). Until then, unpin external CLIs so a stale ID doesn't break smokes the day before tagging. agy was unpinned from creation in B9.

- [ ] **Step 1: CLI_SPEC `default_args` edits**
  - `codex`: drop `["--model", "gpt-5.5", ...]` → keep the `-c model_reasoning_effort="high"` config arg, drop `--model`. Result: `default_args = ["-c", 'model_reasoning_effort="high"']`.
  - `opencode`: drop `["--model", "openrouter/deepseek/deepseek-v4-pro"]` → `default_args = []`.
  - `claude`: keep `["--model", "opus", "--effort", "xhigh"]` — Claude reviewer launches via Task subagent which inherits frontmatter pin; this default_args path is only the fallback synth-via-spawn route, but `opus` family alias is stable.
  - `agy`: already `default_args = []` from B9 — no change.

- [ ] **Step 2: Update `cli/spawn.py`**

In `build_command` indirectly (through `CLI_SPEC` edits) — no functional code change needed in `spawn.py` itself. Verify: if `--model` not passed AND CLI_SPEC `default_args` is empty, `build_command` skips the `--model` flag.

```bash
uv run python -m multi_review.cli.spawn --cli agy --prompt-file /tmp/p --out-dir /tmp/o --dry-run-cmd 2>&1
# Expected: ['agy', '--print']
```

(If `--dry-run-cmd` flag doesn't exist, add a tiny one that prints the resolved argv and exits 0 — or invoke `build_command` from a one-liner.)

- [ ] **Step 3: Update build agent template**

`agents/multi-review-build.md`:
```yaml
models:
  claude: claude-opus-4-7
  # agy, codex, opencode: omit to use CLI default; set explicitly only if a
  # specific model is required (e.g. for reproducibility in EXPERIMENTS).
```

- [ ] **Step 4: Tests**

```python
def test_build_command_agy_no_default_model():
    from multi_review.core.reviewers import build_command
    cmd = build_command("agy", model=None, streaming=False)
    assert cmd == ["agy", "--print"]   # no --model

def test_build_command_agy_pinned_still_works():
    cmd = build_command("agy", model="Gemini 3.5 Flash (High)", streaming=False)
    assert "--model" in cmd
    assert "Gemini 3.5 Flash (High)" in cmd
```

- [ ] **Step 5: Run tests + commit**

```bash
git add -A
git commit -m "refactor: unpin external CLI models until v0.2.1 model-config lands

agy/codex/opencode default_args no longer pin a specific model; the CLI's
own default is used. --model X explicit pin still works. Claude reviewer
stays pinned to claude-opus-4-7 (via Task subagent frontmatter, which is
the actual reviewer-launch path)."
```

### Task B19: `cli/report.py` + `cli/migrate_sidecars.py` — auto-suffix on paired output

**Files:**
- Modify: `multi_review/cli/report.py:37`
- Modify: `multi_review/cli/migrate_sidecars.py:91`
- Modify: `tests/integration/test_cli_report.py`

**Rationale:** Both call `build_paired_report` and write to `args.out_dir / f"{project}-{date}-{pair_id}.md"` — but never call `resolve_output_path`. Silent overwrite. The REVIEW.md promotion path (SKILL Step 11) does use `resolve_output_path`, so this is a missed call site.

- [ ] **Step 1: Failing test**

```python
def test_report_auto_suffixes_on_collision(tmp_path):
    out = tmp_path / "proj-2026-06-19-pair-1.md"
    out.write_text("existing")
    rc = main(["--out-dir", str(tmp_path), "--project", "proj",
               "--date", "2026-06-19", "--pair-id", "pair-1", ...])
    assert rc == 0
    assert out.read_text() == "existing"   # untouched
    assert (tmp_path / "proj-2026-06-19-pair-1-2.md").exists()
```

- [ ] **Step 2: Apply `resolve_output_path` to the computed path before calling `build_paired_report`**

- [ ] **Step 3: Mirror change in `cli/migrate_sidecars.py:91`**

- [ ] **Step 4: Run tests + commit**

```bash
git add -A
git commit -m "fix(report): auto-suffix paired-report path on collision

cli/report and cli/migrate_sidecars now call resolve_output_path before
writing — matches the REVIEW.md promotion path (SKILL Step 11)."
```

### Task B20: `cli/snapshot.py` — `--file` not required for diff

**Files:**
- Modify: `multi_review/cli/snapshot.py:14`
- Modify: `tests/integration/test_cli_snapshot.py`

**Rationale:** `--file` is `required=True` on both create AND diff subparsers. For context-only prompts (zero input files but with `<file-NONCE>`-wrapped context), `create` is invoked with no files, which currently crashes argparse.

- [ ] **Step 1: Failing test**

```python
def test_snapshot_create_no_files(tmp_path):
    rc = snapshot.main(["create", "--snapshot-dir", str(tmp_path)])
    assert rc == 0
    # context-only prompt should produce an empty snapshot directory
```

- [ ] **Step 2: Make `--file` `required=False, default=[]` on the create subparser** (diff already tolerates).

- [ ] **Step 3: Run tests + commit**

```bash
git add -A
git commit -m "fix(snapshot): --file optional on create for context-only prompts"
```

### Task B21: `core/report.py` `_read` exists() guard

**Files:**
- Modify: `multi_review/core/report.py` (`_read` helper)
- Modify: `tests/unit/test_report.py`

**Rationale:** `_read(p)` returns `p.read_text() if p else None` — no `.exists()` guard, so a stale state path raises FileNotFoundError.

- [ ] **Step 1: Failing test**

```python
def test_read_handles_missing_path(tmp_path):
    from multi_review.core.report import _read
    assert _read(tmp_path / "absent") is None
```

- [ ] **Step 2: Add guard**

```python
def _read(p):
    if not p or not p.exists():
        return None
    return p.read_text()
```

- [ ] **Step 3: Run tests + commit**

```bash
git add -A
git commit -m "fix(report): _read returns None for missing path (not FileNotFoundError)"
```

### Task B22: Drift snapshot includes context files; opencode `part.tokens`; frontmatter parity

**Files:**
- Modify: `multi_review/core/snapshot.py` (`diff_snapshot` — accept added/un-snapshotted files as "added")
- Modify: `multi_review/core/adapters.py` (`OpenCodeAdapter.feed_line` — read `part.tokens` alongside the existing `part.usage`/`ev.usage` paths)
- Modify: `tests/fixtures/streams/opencode/success.jsonl` (fixture already has `part.tokens`; adapter must consume it)
- Modify: `multi_review/cli/aggregate.py` (frontmatter parity with build agent prompt-file template — emit `models:`, `mode:`, `if_drift:` consistent with prompt-file)
- Modify: tests accordingly

- [ ] **Step 1: Failing tests** for each:

```python
def test_diff_snapshot_detects_added(tmp_path):
    # snapshot created with files=[a.py]; b.py exists at diff time
    diff = diff_snapshot(...)
    assert "b.py" in diff.added_files

def test_opencode_adapter_reads_part_tokens():
    a = OpenCodeAdapter()
    a.feed_line(json.dumps({"part": {"tokens": {"input": 100, "output": 50}}, ...}))
    assert a.usage.input_tokens == 100
    assert a.usage.output_tokens == 50
```

- [ ] **Step 2: Implement each fix.** Keep scope tight — each is ≤ 10 lines.

- [ ] **Step 3: Run tests + one combined commit**

```bash
git add -A
git commit -m "fix(snapshot,opencode,aggregate): SHOULD-tier robustness

- diff_snapshot detects added/un-snapshotted files (was: only deletions)
- OpenCodeAdapter reads part.tokens (matches fixture; existing code looked
  only at part.usage/ev.usage)
- aggregate frontmatter emits models/mode/if_drift consistently with the
  build-agent prompt-file template (parity for downstream tooling)"
```

### Task B23: Drift diff includes context files (D1)

**Files:**
- Modify: `multi_review/core/promptfile.py` or wherever `--mode reference` resolves the snapshot set, to include context files alongside input files.
- Modify: `tests/unit/test_promptfile.py` or `tests/unit/test_snapshot.py`

**Rationale:** Context files participate in the prompt; drift detection currently snapshots input files only. If a context file changes between pass 1 and pass 2 of a paired run, drift is undetected and the comparison row is silently contaminated.

- [ ] **Step 1: Failing test** asserting that context-file mtime change shows up in `diff_snapshot.modified_files` for both modes.

- [ ] **Step 2: Implement** — extend the snapshot file set to include context files (the prompt loader knows which paths are inputs vs context; thread the context paths into `snapshot.create_snapshot(...)`).

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "fix(snapshot): include context files in drift detection set

Context files participate in the prompt; a change between pass 1 and pass
2 of a paired run contaminates the comparison row. Snapshot now captures
context paths alongside input paths."
```

### Task B24: NICE-tier sweep (opportunistic — may be deferred to BACKLOG)

Each is 1-2 line touchups. Skip any that involve real design work — move those to BACKLOG instead.

- C8/C9/C10: minor synth-contract polish (BACKLOG if not trivial)
- D2: snapshot edge cases (BACKLOG if not trivial)
- D4: adapter usage-accumulate vs assign comment-only clarification
- E2/E5/E6: SKILL prose polish
- A8a/A8b/A7/A5: harvest field clarifications

Time-box: 30 min. Anything that takes longer → BACKLOG.

- [ ] **Step 1: Time-boxed sweep**
- [ ] **Step 2: Single commit** for whatever lands:

```bash
git commit -m "chore: NICE-tier polish (Bundle B opportunistic)"
```

---

## Final verification

After all phases:

```bash
uv run pytest tests/ -q
```
Expected: all green.

```bash
grep -rn --include="*.py" -E "fallback_chain|fallback_hops|GEMINI_FALLBACK|CAPACITY_PATTERNS|PendingPair" multi_review/ tests/
```
Expected: zero hits in code.

```bash
grep -rn --include="*.md" "gemini" multi_review/ skills/ agents/
```
Expected: only historical-context paragraphs in agent prompts; no live invocation refs.

```bash
# Manual: smoke agy adapter end-to-end
# Manual: smoke synth contract (run a paired pass, inspect REVIEW.md has single ## Consensus Summary, no <filename> leak)
# Manual: smoke harvest row (after one full single-pass run, inspect runs.jsonl has all new fields)
```

After verification passes → ready for Tasks 35/36/37 (live smokes + tag v0.2.0).

---

## Out of scope (BACKLOG)

- v0.2.1 model-config feature (TOML + `mr-config edit` command + two-channel injection)
- v0.2.1 agy telemetry recovery via `--log-file`
- v0.2.1 quota-proximity probe (avoid burning quota in the first place)
- v0.3 schema-v2 `usage` alias removal (still retained until then)

## Risk + mitigation

| Risk | Mitigation |
|---|---|
| agy `--print` behaviour differs across versions | Pin to 1.0.9+ in the manual smoke; document in CLAUDE.md |
| Phase 1 deletion breaks something the dogfood review missed | Phase 1 ends with full `pytest` green AND `grep` sweep — both gate Phase 2 |
| Synth-contract change ripples to existing REVIEW.md sidecars in the wild | Sidecars are user-visible artifacts in the working dir; we don't auto-migrate. Document in CHANGELOG |
| Model unpin destabilises smokes | Acceptable — Tasks 35/36/37 explicitly verify the unpinned default each runs cleanly |
