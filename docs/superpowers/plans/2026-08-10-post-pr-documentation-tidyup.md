# Post-PR Documentation Tidy-up Implementation Plan

> **Completed historical plan (2026-08-10).** Implemented in the post-PR cleanup commit following `6e48d3f`; retained to explain the archive and documentation decisions.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the post-PR documentation accurate, mark the comparison subsystem as deprecated without changing its runtime behaviour, and place private historical artifacts out of the repository root.

**Architecture:** The active README, Claude Code skill, agents, manual smoke procedures, and rendered experiment log remain the sources of current user guidance. Historical plans and ignored run artifacts remain available for forensics but are explicitly marked archival. The comparison subsystem stays implemented in this change; its deprecation is documentary only until the follow-up compatibility/removal work.

**Tech Stack:** Markdown, Python 3.11, pytest, git.

## Global Constraints

- Keep both `/multi-review` and `multi_review.py --prompt-file ... --out-dir ...` documented and supported.
- Do not change prompt-schema or runtime behaviour in this tidy-up.
- Mark `mode: both`, drift comparison, harvest, persisted telemetry, `runs/`, experiments, sidecars, and paired reports as deprecated; do not claim `inline` or `reference` is superior.
- Keep private or client-specific artifacts ignored and out of the repository root.
- Every code-backed documentation claim must be verified by pytest or the relevant CLI help.

---

### Task 1: Correct active documentation and declare the comparison subsystem deprecated

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `skills/multi-review/SKILL.md`
- Modify: `agents/multi-review-build.md`
- Modify: `agents/multi-review-synthesizer.md`
- Modify: `tests/manual/agy-smoke.md`
- Modify: `tests/manual/headless-driver-smoke.md`
- Modify: `tests/manual/pykrete-smoke.md`
- Modify: `tests/manual/single_pass.md`
- Modify: `tests/manual/skill-step5-join.md`
- Modify: `tests/fixtures/streams/README.md`
- Test: `tests/integration/test_skill_contract.py`

**Interfaces:**
- Consumes: current prompt defaults in `multi_review/core/promptfile.py` and documented CLI flags in `multi_review/cli/*.py`.
- Produces: current guidance for the interactive skill and headless driver, with no stale promises about no-op fields or deferred harvest writes.

- [x] **Step 1: Add contract assertions for the corrected documentation terminology**

Extend `tests/integration/test_skill_contract.py` with narrow assertions that the active skill documents the comparison subsystem as deprecated and does not instruct a `TaskGet` join for the synchronous Claude Task result.

- [x] **Step 2: Run the new contract test and confirm it fails before documentation is changed**

Run: `uv run pytest tests/integration/test_skill_contract.py -q`

Expected: FAIL because the active skill has no comparison-deprecation notice and still contains the obsolete Claude `TaskGet` branch.

- [x] **Step 3: Update current guidance from current code**

Make these precise corrections:

- Describe the headless driver as a supported single-pass entry point and state that the anticipated `claude -p` billing change is deferred indefinitely.
- Set the documented `if_drift` default to `ignore`.
- State that `harvest` is currently always written by the skill despite the YAML field, and that a real opt-out is planned for follow-up work.
- Mark the comparison subsystem deprecated and discourage new `mode: both` experiments without labelling either single prompt delivery mode as deprecated.
- Remove or clearly mark `output_dir`, `save_as`, and `model_effort` as accepted-but-not-implemented pending their schema cleanup.
- Correct the summary gate, Claude task join, filename, and smoke-output assertions to match current code.
- Update the fixture guide to use `multi_review/core/reviewers.py` and remove obsolete Gemini recapture instructions.

- [x] **Step 4: Run active documentation contract tests**

Run: `uv run pytest tests/integration/test_skill_contract.py -q`

Expected: PASS.

### Task 2: Render experiment logs as deprecated historical material

**Files:**
- Modify: `multi_review/core/report.py`
- Modify: `tests/unit/test_report.py`

**Interfaces:**
- Consumes: `render_experiments_markdown(log_path, reports_dir)`.
- Produces: generated experiment Markdown that names the real `report regen` command, describes the output as local historical/deprecated data, and makes no nonexistent `--no-harvest` promise.

- [x] **Step 1: Add a failing renderer test for legacy copy**

Add a test that calls `render_experiments_markdown()` and asserts that the output identifies the comparison log as deprecated historical data, names `multi_review.cli.report regen`, and contains neither `multi_review.py --report` nor `--no-harvest`.

- [x] **Step 2: Run the renderer test and confirm it fails**

Run: `uv run pytest tests/unit/test_report.py -q`

Expected: FAIL because the current renderer emits both obsolete command strings.

- [x] **Step 3: Update the renderer and ordering copy**

Replace the generated header and methodology with wording that accurately describes the report command and local-only historical data. State that the ordering field is legacy/deprecated, and correct its tie rule to `reference-first`.

- [x] **Step 4: Run report tests**

Run: `uv run pytest tests/unit/test_report.py -q`

Expected: PASS.

### Task 3: Label historical design records and archive ignored artifacts

**Files:**
- Modify: `docs/superpowers/specs/2026-05-15-multi-review-skill-reframe-design.md`
- Modify: `docs/superpowers/specs/2026-08-04-headless-driver-design.md`
- Modify: `docs/superpowers/plans/2026-08-04-headless-driver.md`
- Modify: `docs/superpowers/plans/2026-08-08-headless-driver-remediation.md`
- Modify: `docs/superpowers/plans/2026-08-09-pr1-review-followup.md`
- Move: `REVIEW-*.md` to `runs/archive/reviews/`
- Move: `EXPERIMENTS.md` to `runs/archive/experiments/`
- Move: existing `runs/{reports,notes,prompts,runs.jsonl,runs.jsonl.bak,EXPERIMENTS.md}` to `runs/archive/`
- Create: `runs/README.md` (ignored local archive guide)

**Interfaces:**
- Consumes: current implementation status at merge commit `6e48d3f` and the existing ignored local artifacts.
- Produces: historical documents that cannot be mistaken for active execution instructions, plus a clean repository root with client-specific run material under one local archive hierarchy.

- [x] **Step 1: Add explicit historical status markers**

Add concise banners naming completed or superseded status, the successor record where applicable, and the implementing commit for the PR follow-up plan. Preserve original content as historical evidence.

- [x] **Step 2: Move ignored artifacts without deleting them**

Create `runs/archive/{reviews,experiments,reports,notes,prompts,data}`. Move the root `REVIEW-*.md` files, root `EXPERIMENTS.md`, and existing ignored run outputs into the corresponding archive directories. Do not move `runs/.gitkeep` or `skills/multi-review/config.json`.

- [x] **Step 3: Add an ignored local archive guide**

Create `runs/README.md` explaining that all contents are local, ignored historical/private material; that the comparison subsystem is deprecated; and that no archived record is current operating guidance.

- [x] **Step 4: Verify artifact layout and tracked files**

Run: `test ! -e EXPERIMENTS.md && ! find . -maxdepth 1 -name 'REVIEW-*.md' -print -quit | grep -q . && test -f runs/README.md && find runs/archive -type f | wc -l`

Expected: no root experiment/review artifacts, local guide present, and archived artifacts present.

### Task 4: Full verification and delivery

**Files:**
- Verify: all modified files and generated local experiment log

**Interfaces:**
- Consumes: completed Tasks 1–3.
- Produces: a tested post-PR cleanup commit pushed to `origin/main` and a tag recommendation tied to the actual release commit history.

- [x] **Step 1: Regenerate the local historical experiment log**

Run: `uv run python -m multi_review.cli.report regen --log runs/archive/data/runs.jsonl --reports-dir runs/archive/reports --output runs/archive/experiments/EXPERIMENTS.md`

Expected: JSON output with `"ok": true` and the archive experiment path.

- [x] **Step 2: Run focused and full tests**

Run: `uv run pytest tests/unit/test_report.py tests/integration/test_skill_contract.py -q && uv run pytest tests/ -q`

Expected: all tests pass.

- [x] **Step 3: Inspect documentation and repository status**

Run: `git diff --check && git status --short && rg -n 'multi_review\.py --report|--no-harvest|post-June 15 2026' README.md CLAUDE.md skills agents multi_review/core/report.py`

Expected: no whitespace errors or obsolete active-doc claims; only intentional historical occurrences, if any.

- [x] **Step 4: Commit and push the cleanup**

Run: `git add README.md CLAUDE.md BACKLOG.md agents docs multi_review/core/report.py skills tests && git commit -m "docs: tidy post-PR guidance and archive comparison artifacts" && git push origin main`

Expected: one commit on `main` pushed to `origin/main`; ignored archive artifacts remain untracked by design.

Completed as `d085404` (`docs: tidy post-PR guidance and archive comparison artifacts`), pushed to `origin/main`.
