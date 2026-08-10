# PR #1 Review Follow-up Implementation Plan

> **Completed historical plan.** All listed fixes landed in `e30d621` and were
> included in PR #1, merged at `6e48d3f`. Retain this record for rationale; do
> not re-execute its tasks.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five confirmed headless-driver review findings without adding abstractions for the five unsupported or low-value cleanup suggestions.

**Architecture:** Keep signal and CLI-boundary handling in the repository-root driver. Preserve the shared fanout, synthesis, and prompt-file designs where investigation showed either an existing safety mechanism or no current defect.

**Tech Stack:** Python 3.11+, asyncio, pytest, pathlib, POSIX signals where available.

## Global Constraints

- Preserve `main(argv) -> int` and the one-shot CLI's non-zero cancellation contract.
- Do not weaken atomic output-directory claiming or report publication.
- Add no new dependencies or generic runtime type-checking framework.

---

### Task 1: Contain SIGINT during startup and fanout

**Files:**
- Modify: `multi_review.py`
- Test: `tests/unit/test_multi_review_driver.py`

**Interfaces:**
- Consumes: `_run_driver(argv, restore_signal_handlers)` and `claim_output_dir_with_sigterm_mask(out_dir, claim_ref)`.
- Produces: exit code `1`, no traceback, and claim cleanup when SIGINT interrupts startup or `asyncio.run()`.

- [x] **Step 1: Write failing SIGINT regression tests**

Add one test that delivers SIGINT after `.multi-review.claim` is touched but before the claim helper returns, and one test that makes `asyncio.run()` raise `KeyboardInterrupt`. Assert return code `1` and absence of the claim marker.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `UV_CACHE_DIR=/tmp/multi-review-uv-cache uv run pytest tests/unit/test_multi_review_driver.py -k 'sigint and (claim or fanout)' -q`

Expected: SIGINT escapes as `KeyboardInterrupt` and/or strands the claim on the current implementation.

- [x] **Step 3: Implement the minimal signal fix**

Block both `SIGTERM` and `SIGINT` during the atomic claim assignment, and catch `KeyboardInterrupt` at the same driver boundary that converts async cancellation to exit code `1`.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command and expect all selected tests to pass.

### Task 2: Keep post-validation failures inside the CLI boundary

**Files:**
- Modify: `multi_review.py`
- Test: `tests/unit/test_multi_review_driver.py`

**Interfaces:**
- Consumes: `_resolve_path(path, base) -> Path`, which may raise `ValidationError`.
- Produces: CLI validation exit code `2` with an `error:` diagnostic.

- [x] **Step 1: Write a failing TOCTOU regression test**

Monkeypatch the driver's `_resolve_path` so the load-time call succeeds and a build-time call raises `ValidationError("path changed")`; assert code `2` and no exception escape.

- [x] **Step 2: Run the test and verify RED**

Run: `UV_CACHE_DIR=/tmp/multi-review-uv-cache uv run pytest tests/unit/test_multi_review_driver.py -k resolve_path -q`

Expected: `ValidationError` escapes.

- [x] **Step 3: Implement the minimal exception boundary**

Catch `ValidationError` around path resolution/prompt construction, print `error: <diagnostic>` to stderr, and return `2`.

- [x] **Step 4: Run the test and verify GREEN**

Run the Step 2 command and expect the regression test to pass.

### Task 3: Improve claim and classification diagnostics

**Files:**
- Modify: `multi_review.py`
- Test: `tests/unit/test_multi_review_driver.py`

**Interfaces:**
- Consumes: `.multi-review.claim`, `classify_review_ok(raw_ok, text)`.
- Produces: an `already claimed` stale-marker diagnostic and exactly one rendered classification note.

- [x] **Step 1: Write failing diagnostic regression tests**

Add a stale-claim test that asserts stderr contains `already claimed`, and extend the classified-failure test to assert `no ## Summary heading in review body` appears exactly once in `REVIEW.md`.

- [x] **Step 2: Run the tests and verify RED**

Run: `UV_CACHE_DIR=/tmp/multi-review-uv-cache uv run pytest tests/unit/test_multi_review_driver.py -k 'claimed or classified' -q`

Expected: the stale marker reports `must be empty`, and the classification note appears twice.

- [x] **Step 3: Implement minimal diagnostic fixes**

Check the claim marker before the generic non-empty check, and retain classification notes in `ReviewerResult.error` without copying them into `stderr_tail`.

- [x] **Step 4: Run focused verification and attempt full verification**

Run: `UV_CACHE_DIR=/tmp/multi-review-uv-cache uv run pytest tests/unit/test_multi_review_driver.py -q`

Then run: `UV_CACHE_DIR=/tmp/multi-review-uv-cache uv run pytest tests/ -q`

Expected: both commands exit `0` with no failures.

Execution note: fresh Python 3.11 runs passed all 134 tests in the affected
driver, fanout, synthesis, prompt-file, and aggregation modules. The monolithic
suite was attempted but blocked in this sandbox's nested CLI-spawn tests; the
same focused spawn tests passed when isolated.
