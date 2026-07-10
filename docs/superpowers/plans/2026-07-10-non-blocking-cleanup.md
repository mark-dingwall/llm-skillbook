# Non-Blocking Cleanup (M9 + test-theatre) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove a stale hardcoded open-question from generated EXPERIMENTS.md, and harden six vacuous test assertions the audit found so they actually guard the behaviour they name.

**Architecture:** Two independent tasks. Task 1 is product-code TDD (a real RED test drives removing an obsolete string from `render_experiments_markdown`). Task 2 is test-only hardening: each fix tightens a weak assert, then a *mutation check* (temporarily break the asserted value, watch the test fail, revert) stands in for "watch it fail" — proving the strengthened assert is non-vacuous.

**Tech Stack:** Python, pytest, `uv run pytest`.

## Global Constraints

- Branch: `v0.2-impl`. Do NOT create branches, push, amend, or use `--no-verify`. Commit per task.
- End every commit message with: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Baseline suite: `uv run pytest tests/ -q` — currently **159 passing**. It must stay green (count grows only if a task adds a test).
- Touch only what each task requires. Match existing style. Minimum code.
- Preserve project invariants (prompt-on-stdin, `<file-NONCE>` wrapping, context-always-inline, timeout default None, output paths never overwrite). None of these tasks should affect them.

---

### Task 1: M9 — drop the obsolete gemini open-question from EXPERIMENTS.md

The `## Open questions` block in `render_experiments_markdown` is hardcoded and written into every regenerated EXPERIMENTS.md. Its first bullet asks about the `gemini-quota-cascade` — a subsystem deleted in Bundle B (gemini→agy, fallback removal). The other two bullets (diversity-of-findings <100KB; `--mode auto`) are still live and stay.

**Files:**
- Modify: `multi_review/core/report.py:193-200`
- Test: `tests/unit/test_report.py` (add one test; sibling of the existing `test_experiments_table_has_no_fallback_column` at line 172, which is the exact pattern to copy)

**Interfaces:**
- Consumes: `render_experiments_markdown(*, log_path: Path, reports_dir: Path) -> str` (existing, unchanged signature).
- Produces: nothing new; behaviour change only (generated markdown no longer mentions gemini).

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_report.py` (it already imports `render_experiments_markdown` at the top):

```python
def test_open_questions_has_no_removed_subsystems(tmp_path):
    # An empty log still emits the static "## Open questions" block; it must
    # not reference subsystems deleted in Bundle B (gemini / quota-cascade).
    log = tmp_path / "runs.jsonl"
    log.write_text("")
    md = render_experiments_markdown(log_path=log, reports_dir=tmp_path / "reports")
    lowered = md.lower()
    assert "gemini" not in lowered
    assert "quota-cascade" not in lowered
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_report.py::test_open_questions_has_no_removed_subsystems -v`
Expected: FAIL — the current string contains `gemini-quota-cascade`.

- [ ] **Step 3: Remove the obsolete bullet**

In `multi_review/core/report.py`, the current block (lines ~193-200) is:

```python
    parts.append("## Open questions\n")
    parts.append(
        "- Is the gemini-quota-cascade real or perceived? Need a session "
        "where inline runs first against fresh quota.\n"
        "- Does the diversity-of-findings benefit hold for prompts under "
        "100KB? Both Guestflow data points are large reviews.\n"
        "- Should `--mode auto` exist (run both for prompts ≥ N bytes)? "
        "Backlog candidate.\n"
    )
```

Delete only the first bullet (the two `gemini-quota-cascade` lines), keeping the other two:

```python
    parts.append("## Open questions\n")
    parts.append(
        "- Does the diversity-of-findings benefit hold for prompts under "
        "100KB? Both Guestflow data points are large reviews.\n"
        "- Should `--mode auto` exist (run both for prompts ≥ N bytes)? "
        "Backlog candidate.\n"
    )
```

- [ ] **Step 4: Run to verify it passes + no regressions**

Run: `uv run pytest tests/unit/test_report.py -q`
Expected: PASS (new test green, existing report tests still green).

- [ ] **Step 5: Commit**

```bash
git add multi_review/core/report.py tests/unit/test_report.py
git commit -m "fix(report): drop obsolete gemini open-question from EXPERIMENTS.md

The static Open-questions block referenced the gemini-quota-cascade, a
subsystem deleted in Bundle B; it shipped into every regenerated report.
Remove that bullet (keep the two still-live questions) and guard with a
test that generated markdown names no removed subsystem.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: M10 — harden six vacuous test assertions

Six tests pass through weak/tautological asserts (over-broad `or`, an always-true disjunct, a size-only check, and one test whose escape hatch masked a *doubly-broken* setup). Each fix tightens the assert to pin the behaviour the test name claims. **For every fix, run the mutation check** described in its step — that is how we "watch it fail" for a test-only change; a strengthened assert that can't be made to fail is still theatre.

**Files:**
- Modify: `tests/integration/test_cli_build_synth_input.py:123` (F1)
- Modify: `tests/unit/test_adapters.py:43-45` and `:58` (F2, F3)
- Modify: `tests/unit/test_paths.py:25-31` (F4)
- Modify: `tests/unit/test_snapshot.py:13` (F5)
- Modify: `tests/integration/test_cli_spawn.py:34` (F6)

**Interfaces:** none — test-only changes. No product code is touched in this task.

- [ ] **Step 1: F1 — delete vacuous disjunct in build_synth_input tuple-order test**

In `tests/integration/test_cli_build_synth_input.py`, the test already unpacks `body, nonce = build_synthesis_input([r])` and asserts `"review text" in body` and `len(nonce) == 8` — those two already fail if the tuple order swaps. Line 123 is unfalsifiable filler (`build_synthesis_input` always emits `review-{nonce}` into the body, so the right disjunct is always true). Delete line 123 entirely:

```python
    assert nonce not in body or f"review-{nonce}" in body  # nonce appears as tag name in body
```

Mutation check: after deleting, temporarily swap the return in `multi_review/core/synthesis.py:48` to `return nonce, "\n".join(parts)` and run
`uv run pytest tests/integration/test_cli_build_synth_input.py::test_build_synth_input_tuple_order_body_nonce -q`
— it must FAIL (proving the surviving asserts guard order). Revert the synthesis.py swap.

- [ ] **Step 2: F2 — exact-equality assert for agy plain-text buffering**

In `tests/unit/test_adapters.py::test_agy_adapter_buffers_plain_text`, replace the 3-way OR (lines 43-45) and de-gemini the sample text (this is an agy test; the `Gemini here` sample is a stale leftover):

```python
    a.feed_line("Hi from agy.")
    a.feed_line("Second line.")
    assert "".join(a.text_parts) == "Hi from agy.\nSecond line.\n"
```

(Keep the existing `usage.input_tokens == 0` / `output_tokens == 0` / `phase in (...)` asserts below — they pin the no-telemetry contract and are valid.)

Mutation check: temporarily change `AgyAdapter.feed_line` in `multi_review/core/adapters.py` to append `line` (no `+ "\n"`) and run
`uv run pytest tests/unit/test_adapters.py::test_agy_adapter_buffers_plain_text -q`
— it must FAIL. Revert.

- [ ] **Step 3: F3 — assert fixture content survives the round-trip**

In `tests/unit/test_adapters.py::test_agy_fixture_round_trip`, replace the size-only assert (line 58) with checks that distinctive fixture lines survive:

```python
    assert "The auth middleware in `src/auth.py:42`" in body
    assert "LEEWAY_SECONDS = 1" in body
```

Mutation check: temporarily make `AgyAdapter.feed_line` early-return without appending, run the test — it must FAIL. Revert.

- [ ] **Step 4: F4 — actually exercise the XDG fallback (was doubly-broken)**

`tests/unit/test_paths.py::test_central_runs_dir_falls_back_to_xdg` never tested XDG fallback: dev-checkout detection short-circuited (the test forgot to set `MULTI_REVIEW_NO_DEV_CHECKOUT=1`, which `paths._dev_checkout_runs` documents for exactly this), so `central_runs_dir()` returned `<repo>/runs` and the `or p.parent.exists()` escape hatch made it pass anyway. The intended first disjunct was also wrong: the real return is `xdg/multi-review` directly, not its parent. Replace lines 25-31:

```python
def test_central_runs_dir_falls_back_to_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("HOME_RUNS_OVERRIDE", raising=False)
    # Suppress dev-checkout detection so XDG resolution actually wins.
    monkeypatch.setenv("MULTI_REVIEW_NO_DEV_CHECKOUT", "1")
    # No config.json under the fake HOME, so resolution falls through to XDG.
    p = central_runs_dir()
    assert p == tmp_path / "xdg" / "multi-review"
```

Verify it PASSES (confirmed manually: with the env set, `central_runs_dir()` returns `<XDG_DATA_HOME>/multi-review`).
Mutation check: temporarily change the XDG branch in `multi_review/core/paths.py:60` to `return Path(xdg) / "wrong"`, run the test — it must FAIL. Revert.

- [ ] **Step 5: F5 — assert snapshot copied content, not just presence**

In `tests/unit/test_snapshot.py::test_create_snapshot_copies_files`, replace the weak `or rglob` line (13):

```python
    assert snapped.exists()
    assert snapped.read_text() == "v1\n"
```

Mutation check: temporarily make `create_snapshot` in `multi_review/core/snapshot.py` write empty content (e.g. `target.write_text("")` instead of copying), run the test — it must FAIL. Revert.

- [ ] **Step 6: F6 — assert spawn success is True, not just a bool**

In `tests/integration/test_cli_spawn.py::test_spawn_writes_review_and_state`, the fixture is a successful claude stream fed through an `exit 0` fake CLI, so `ok` must be `True`. Replace line 34:

```python
    assert state["ok"] is True
```

Mutation check: temporarily change the fake CLI's `exit 0` to `exit 1` in the test setup (line 13), run the test — the `ok is True` assert must FAIL. Revert.

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: PASS — **160 passing** (159 baseline + Task 1's new test; Task 2 adds no tests, only strengthens existing ones).

- [ ] **Step 8: Commit**

```bash
git add tests/
git commit -m "test: harden six vacuous assertions found by test-theatre audit

Tighten weak/tautological asserts so each guards the behaviour it names:
delete an unfalsifiable disjunct (synth tuple-order), exact-match agy
buffering, assert fixture content survives the round-trip, actually
exercise the XDG fallback (was masked by a dev-checkout short-circuit and
an escape-hatch or), assert snapshot content is copied, and pin spawn
success to True. Each verified non-vacuous by a mutation check.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Follow-ups (inline, not plan tasks)

Per the agreed scope these are handled as small inline edits outside this plan, not as TDD tasks:

- **M8 (output-path TOCTOU):** dropped as YAGNI (unreachable in this single-user tool's sequential SKILL flow). Record a one-line note in `BACKLOG.md`.
- **SKILL Step 8 (pass-2 harvest framing):** prose clarification that a paired pass-2 needs its own `write_harvest_row` invocation. Doc-only; I5's `test_skill_contract.py` already guards the flags.

## Self-Review

- **Spec coverage:** M9 → Task 1. All six audit findings (F1-F6) → Task 2 steps 1-6. M8/Step-8 → Follow-ups (by agreement). Complete.
- **Placeholder scan:** every step has exact file:line, exact before/after code, and a concrete mutation check with the exact file to perturb. No TBDs.
- **Type consistency:** no new types/signatures introduced; `render_experiments_markdown` used with its existing signature.
