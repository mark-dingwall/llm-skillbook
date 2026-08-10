# Headless Driver Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the headless driver's timeout, output publication, synthesis-status, and shutdown-evidence defects found in PR #1 review round 1.

**Architecture:** Keep `multi_review.py` as a thin orchestrator. Extend the existing fan-out and review writer APIs only with optional state, protecting compatibility for the v0.2 skill callers. Use atomic filesystem claims/publication and hermetic tests; the manual harness remains the real six-CLI evidence gate.

**Tech Stack:** Python 3.11 asyncio/pytest, Bash, Bubblewrap.

## Global Constraints

- Preserve existing prompt-delivery and classified-review success invariants.
- The driver remains internal/single-user, but must not inherit unrelated credentials in its smoke harness.
- Every behavior change starts with a focused failing pytest test.
- The full suite remains `uv run pytest tests/ -q`.

---

### Task 1: Cover reviewer stdin timeouts and synthesis failure reporting

**Files:**
- Modify: `tests/unit/test_fanout.py`
- Modify: `tests/unit/test_multi_review_driver.py`
- Modify: `multi_review/core/fanout.py`
- Modify: `multi_review/core/aggregate.py`
- Modify: `multi_review.py`

- [ ] **Step 1: Write failing tests**

Add a fake subprocess whose `stdin.drain()` never completes and assert `run_reviewer(..., timeout=0.01)` returns `ok=False`, `error == "timeout after 0.01s"`, and invokes `kill_proc`. Add a two-successful-reviewer test whose configured synthesis returns `(False, "", "synthesis timeout after 1s", ...)`, asserting `REVIEW.md` says the synthesis failed and includes that diagnostic rather than claiming it was skipped.

- [ ] **Step 2: Run the focused tests and observe their expected failures**

Run `uv run pytest tests/unit/test_fanout.py tests/unit/test_multi_review_driver.py -q`.

- [ ] **Step 3: Implement the minimum behavior**

Wrap prompt delivery and stream/process waiting in the same `asyncio.wait_for` deadline. Carry optional `synthesis_error` through `write_review_md`; when present, emit an explicit failed Consensus Summary diagnostic.

- [ ] **Step 4: Re-run the focused tests**

Run `uv run pytest tests/unit/test_fanout.py tests/unit/test_multi_review_driver.py -q`.

### Task 2: Make output ownership and SIGTERM publication safe

**Files:**
- Modify: `tests/unit/test_multi_review_driver.py`
- Modify: `multi_review.py`

- [ ] **Step 1: Write failing tests**

Test that a pre-existing exclusive output claim rejects a second driver before fan-out. Add a subprocess-style driver regression using a PATH-injected sleeping fake `claude`: signal the real driver while it is running, then assert exit `1`, no published `REVIEW.md`, and no live direct child.

- [ ] **Step 2: Run the driver test module and observe expected failures**

Run `uv run pytest tests/unit/test_multi_review_driver.py -q`.

- [ ] **Step 3: Implement the minimum behavior**

Atomically create an output claim file before writing `prompt.txt`; release it only after terminal cleanup. Render `REVIEW.md` to a staged path, yield once to process pending cancellation, then atomically publish it. A cancelled run removes staged output and returns `1`.

- [ ] **Step 4: Re-run the driver tests**

Run `uv run pytest tests/unit/test_multi_review_driver.py -q`.

### Task 3: Harden manual shutdown evidence and document the containment contract

**Files:**
- Modify: `tests/unit/test_headless_driver_smoke_harness.py`
- Modify: `tests/manual/headless-driver-smoke.sh`
- Modify: `tests/manual/headless-driver-smoke.md`
- Modify: `README.md`

- [ ] **Step 1: Write failing harness/documentation tests**

Add a helper-mode test proving plain shutdown uses a cleared environment with only its explicit allowlist. Add a fake late descendant/process-group test that fails if the post-signal scan observes a live process absent from the initial snapshot. Assert README names `bwrap --unshare-pid --die-with-parent` as required for full-tree shutdown.

- [ ] **Step 2: Run the harness tests and observe expected failures**

Run `uv run pytest tests/unit/test_headless_driver_smoke_harness.py -q`.

- [ ] **Step 3: Implement the minimum hardening**

Use `env -i` for plain cases and explicitly allow required runtime variables. Rescan the relevant process group after shutdown before claiming PASS, preserving the intentional plain Codex/OpenCode survivor reporting. State the internal driver’s required containment and signal target in README/manual documentation.

- [ ] **Step 4: Re-run focused harness tests**

Run `uv run pytest tests/unit/test_headless_driver_smoke_harness.py -q`.

### Task 4: Verify and re-review the remediation diff

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run the complete suite**

Run `uv run pytest tests/ -q` and record the pass/fail count and known warning.

- [ ] **Step 2: Run static/manual-safe checks**

Run `bash -n tests/manual/headless-driver-smoke.sh`, `tests/manual/headless-driver-smoke.sh --check`, and `git diff --check`.

- [ ] **Step 3: Re-review only the remediation diff**

Use independent holistic, adversarial, async/process, and shell-focused reviewers against `HEAD` plus the uncommitted remediation diff. Verify each report against source before deciding whether another remediation round is required.
