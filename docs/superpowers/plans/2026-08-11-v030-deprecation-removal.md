# v0.3.0 Deprecation Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the deprecated paired-comparison workflow outright. Delivery becomes reference-only (no `mode` switch). The skill drops to single-pass. Harvest/snapshot/sidecar/report code is deleted; historical repo artefacts move to a gitignored `.archive/`. A removed-option guard rejects legacy prompt-YAML keys with exit 2.

**Architecture:** `multi_review/core/{prompt,promptfile}.py` lose the mode branch and six schema fields; every direct caller (`aggregate.py`, `cli/aggregate.py`, `cli/prepare.py`, `multi_review.py`) follows in the same task. `skills/multi-review/SKILL.md` and `agents/*.md` drop to validate→prepare→fanout→synthesis→aggregate, keeping existing step numbers (gaps where steps are deleted) so the two load-bearing hardcoded-step-number tests in `test_skill_contract.py` need no renumbering. The harvest/snapshot/sidecar/report modules and their CLIs are deleted once nothing documents them. `runs/` (gitignored, already containing a prior archive pass) moves to `.archive/`; the central-path/config.json machinery that only served harvest is retired with it.

**Tech Stack:** Python 3.11, pytest, PyYAML, bash (headless-driver-smoke.sh), git.

## Global Constraints

- **Baseline:** `uv run pytest tests/ -q` → **368 passed, 1 warning** (pre-existing harmless `asyncio_mode` warning — zero `async def` tests exist). Suite must be green at the end of every task below.
- Reference-only delivery: input files always emit a `## Files to Review` manifest of absolute paths; context files always stay inline `<file-NONCE>` wrapped; both preambles (`injection_preamble` + now-unconditional `reference_preamble`) always apply.
- Removed prompt-YAML keys (`mode`, `if_drift`, `output_dir`, `save_as`, `model_effort`, `harvest`) exit 2 with a one-line stderr/JSON message naming the key. No silent ignoring, no back-compat shim.
- Delete deprecated source + tests outright. Move material deprecated **repo artefacts** (the local `runs/` records and explanatory README) into gitignored `.archive/`; only empty directory scaffolding and placeholder `.gitkeep` files may be deleted.
- Never touch user data outside the repo (`~/.claude/skills/multi-review/config.json`, any central `runs.jsonl`/`EXPERIMENTS.md`) — only the code that writes them goes away.
- Touch only what the task requires; match existing style; every deletion below names its file explicitly.
- **Doc-before-code ordering is deliberate, not stylistic:** `test_skill_contract.py::test_skill_flags_exist`/`test_skill_modules_resolve` dynamically check that every flag/module SKILL.md documents still exists in code. Removing a flag/module from code while SKILL.md still names it fails the suite immediately. So SKILL.md/agents edits (Task 1) land *before* the Python flag/module removals they anticipate (Tasks 2–3) — safe because deleting a doc's *reference* to a still-existing flag never fails that test, only the reverse does.

## Open Decisions

| # | Decision | Recommendation | Lands in |
|---|---|---|---|
| 1 | Bump `prompt_format_version` 1→2? | **Yes.** The six-key reject only catches YAMLs that *set* a removed key. A minimal historical YAML that only ever set `task`/`files` (relying on the old `mode: inline` default) has none of the six keys present and would otherwise silently start getting reference-only delivery with zero warning — exactly the silent-ignoring D3 forbids. | Task 3 |
| 2 | REVIEW.md frontmatter: drop `mode:`/`if_drift:`/`pair_id:` lines entirely, or hardcode `mode: reference` for continuity? | **Drop entirely.** Nothing outside the deleted sidecar/report modules ever parsed these fields. | Task 3 |
| 3 | Central-path subsystem (`paths.central_runs_dir`/`_dev_checkout_runs`/`generate_pair_id`, `setup.py`'s central-dir/config.json/allowlist scaffolding) — retire, or leave as dead scaffolding? | **Retire.** Once Task 1 removes SKILL.md's only `CENTRAL_PATH` consumers, nothing reads it. Leaving it re-litters an untracked `runs/` on every fresh clone with no gitignore rule left to hide it. Also retires the now-vestigial `tests/conftest.py` guard fixture's docstring + the matching CLAUDE.md invariant bullet, both of which describe a write that no longer happens. | Task 4 |
| 4 | `docs/superpowers/plans/*.md` + `specs/*.md` (harvest/pairing-heavy historical design docs) — archive into `.archive/`, or leave tracked? | **Leave tracked.** They already carry their own "Archival — historical record" banners (same convention as this file). `.archive/` is gitignored; moving tracked docs there would silently stop shipping real project history on the next clone — a bigger action than anything D4 named. | No task touches them |
| 5 | `spawn.py --effort` flag — delete as dead collateral (its only backing field, `model_effort`, is removed), or leave as an inert no-op? | **Delete.** Nothing will ever set it once SKILL.md drops `<EFFORT_FLAG>` and the YAML schema drops `model_effort`. | Task 3 |
| 6 | `tests/manual/{pykrete,grok}-smoke.md` — dated, already-PASSED historical records containing now-rejected `mode:`/harvest fixture text — edit, or leave as-is? | **Leave as-is**, same convention as `preflight-v0.2.md`. A "superseded, don't replay literally" banner is optional polish, not required. | No task touches them |
| 7 | Migrate pre-v0.3 `.multi-review/pending/<pair_id>/` or `pending-harvest/` state? | **No automatic migration.** These are transient, project-local remnants of the workflow being removed, not repo artefacts or a supported data format. The current checkout has an empty `pending/` and no `pending-harvest/`; v0.3 must not scan or mutate other repositories to find more. Finish any paused pair before upgrading, or preserve its directory manually if it has personal historical value. | No implementation task |

---

### Task 1: Strip the skill to single-pass (D2)

**Files:**
- Modify: `skills/multi-review/SKILL.md`
- Modify: `agents/multi-review-build.md`
- Modify: `agents/multi-review-reviewer.md`
- Modify: `agents/multi-review-synthesizer.md`
- Modify: `CLAUDE.md` (top `### Deprecated comparison workflow` section — delete)
- Modify: `README.md` (opening deprecated-workflow blockquote; `## Deprecated paired runs and drift` section; `## Deprecated comparison eligibility` section — delete all three)
- Delete: `agents/multi-review-investigate.md`
- Delete: `tests/manual/agent_investigate_smoke.md`
- Delete: `tests/manual/drift_ask.md`
- Delete: `tests/manual/paired_pass.md`
- Modify: `tests/manual/agent_synthesizer_smoke.md` (drop "inline mode" phrase from Step 1)
- Modify: `tests/manual/single_pass.md` (drop `mode: inline` parenthetical; delete the entire harvest verification tail, including the `runs.jsonl` permission-prompt/allowlist bullet and the report-regeneration step — none survives v0.3)
- Modify: `tests/manual/headless-driver-smoke.md` (Section 2: drop the "a `mode: reference` run" framing — low priority wording only)
- Test: `tests/integration/test_skill_contract.py`

**Interfaces:**
- Consumes: `DEFAULT_REVIEWERS`/`ALL_REVIEWERS` (`multi_review/core/reviewers.py`, untouched this task).
- Produces: a single-pass-only `SKILL.md` referencing only `validate_prompt`, `prepare`, `spawn`, `aggregate`, `write_task_result`, `build_synth_input`.

**Design note — no step renumbering.** Delete Steps 3, 8, 9, 10, 11, 12 in place, leaving numbering gaps; do **not** renumber survivors. `test_skill_dispatch_binds_to_resolved_reviewers` hardcodes `_skill_step_section(5)` (fanout) and `_skill_step_section(6)` (synthesis) — keeping those steps at their existing numbers means zero test churn there. Step 13 (Final summary) may keep its number too (nothing hardcodes it) — a `7 → 13` jump in the doc is fine; add one parenthetical at the end of Step 7 noting steps 3/8–12 were removed in v0.3.0.

- [ ] **Step 1: Add a failing "no deprecated content" contract test**

  In `tests/integration/test_skill_contract.py`:
  - Add `test_skill_has_no_deprecated_workflow_content` asserting none of `{"mode: both", "write_harvest_row", "snapshot create", "if_drift: ask", "pending/<pair_id>", "build-paired", "harvested", "comparison eligibility", "TaskGet", "## Comparison workflow deprecation"}` appear anywhere in `SKILL.md`.
  - Delete `test_skill_harvest_invocation_records_the_synthesizer` outright — its `skill.split("write_harvest_row", 1)[1]` would `IndexError` once Step 8's text is gone, not fail cleanly.
  - In `test_skill_dispatch_binds_to_resolved_reviewers`, delete the three resume-pointer assertions (`prompt-source.txt` in Step 2 and Step 5, `prompt-source.sha256` in Step 5). Keep the fanout/synthesis `resolved.reviewers`/`resolved.synthesizer` binding assertions verbatim — CLAUDE.md-pinned opt-in-enforcement invariant, do not touch.
  - In `test_skill_marks_comparison_workflow_deprecated_and_joins_claude_synchronously`, delete the `## Comparison workflow deprecation`/`mode: both` assertions; rename the function to `test_skill_never_polls_a_claude_task` and keep only the `"TaskGet" not in skill` assertion (a real, still-true invariant independent of the deleted section).

- [ ] **Step 2: Run and confirm RED**

  Run: `uv run pytest tests/integration/test_skill_contract.py -q`

  Expected: FAIL — `test_skill_has_no_deprecated_workflow_content` fails (SKILL.md still contains `write_harvest_row`, `mode: both`, etc.).

- [ ] **Step 3: Rewrite SKILL.md, agents, and delete dead docs**

  `skills/multi-review/SKILL.md`:
  - Frontmatter `description`: drop "The legacy paired comparison workflow remains for compatibility but is deprecated."
  - `## Invocation forms`: drop `--resume-pair` and `--report` lines.
  - Step 1: drop the `--resume-pair`/`--report` extract items and the whole "Resolve central path… CENTRAL_PATH" paragraph.
  - Step 2: drop the `--resume-pair` skip-build branch and the `--report` skip-build branch. In the `resolved` sole-source-of-truth sentence, drop `model_effort`, `mode`, `if_drift` from the field list; keep `reviewers`/`synthesizer`/`models` and **add `task`** (not in that sentence today — a real addition, not a no-op keep).
  - Delete Step 3 (pending-pair sweep) wholesale.
  - Step 4: keep only pass-1 `run_id` generation + the `SESSION_DIR`/`REVIEWS_DIR` path constants; delete the pair_id/drift-posture/pass2 sub-bullets (b, c, d). Retitle "Step 4 — Generate run id".
  - Step 5: drop `--mode-override <pass1_mode>` from the `prepare` invocation (becomes flagless on that axis); delete the snapshot-create block; delete the "Persist the prompt location for resume" block (mkdir + `prompt-source.txt`/`.sha256` + its explanatory paragraph); delete the `<EFFORT_FLAG>` construction and its use in the spawn invocation, keeping only `<MODEL_FLAG>` + `<TASK_FLAG>`. Keep the spawn dispatch loop and the claude Task dispatch + `write_task_result` call verbatim.
  - Join barrier: unchanged.
  - Step 6 (Synthesis): unchanged.
  - Step 7 (Aggregate): collapse "Output path branches by mode" to one unconditional `<cwd>/REVIEW-<slug>.md` path; drop `--mode <pass1_mode>` and `--pair-id <pair_id_or_omit>` from the `aggregate` invocation. Keep the `## Summary` heading classifier behavior, but rewrite "rendered and harvested as an effective failure" to "rendered as an effective failure" because Step 8 no longer exists. Append the one-line "(Steps 3, 8–12 removed in v0.3.0.)" note here.
  - Delete Steps 8, 9, 10, 11, 12 wholesale (harvest row, pass-2+drift, post-paired report, cleanup, batch harvest/regen).
  - Step 13 (Final summary): delete the entire `, comparison eligibility (paired only)` fragment — not merely the parenthetical — so the instruction becomes exactly `Print per-prompt: REVIEW.md path, reviewer pass/fail counts.` No comparison-eligibility value has a surviving computation path.
  - Delete `## Comparison workflow deprecation` section wholesale.
  - Delete `## Notes on mode: both + if_drift: ignore` section wholesale.
  - Keep `## Notes on claude not in reviewers` verbatim.

  `agents/multi-review-build.md`:
  - Frontmatter `description`: drop "mode" from the field list and drop "The paired comparison workflow is deprecated."
  - Schema fenced block: delete the `mode:`, `model_effort:`, `if_drift:`, `output_dir:`, `save_as:`, `harvest:` lines, but leave `prompt_format_version: 1` unchanged until Task 3 changes the validator and template together. Keep `reviewers:`/`synthesizer:` lines byte-identical (pinned by `test_builder_schema_reviewers_line_matches_DEFAULT_REVIEWERS` / `test_builder_lists_grok_as_a_valid_synthesizer_choice`).
  - `## Modes`: delete the "Comparison warning: do not author `mode: both`…" bullet.
  - `## Defaults`: delete the `mode:`, `if_drift:`, `model_effort:` lines. Keep `task`/`reviewers`/`synthesizer`/`models.*` lines byte-identical (pinned by `test_builder_autonomous_default_matches_DEFAULT_REVIEWERS` / `test_builder_autonomous_default_synthesizer_is_claude`).

  `agents/multi-review-reviewer.md`: rewrite the frontmatter `description`, `## Tools` section, and both stale `## Inputs` branches: bullet 1 ("An injection preamble naming a `<file-NONCE…>` wrapper format (inline mode) or a `## Files to Review` manifest… (reference mode)") and bullet 4 ("Either inline file contents or a path manifest"). This is no longer an inline-vs-reference choice: context files arrive inline under `<file-NONCE>`, input files arrive as a manifest the reviewer must read via Read/Grep/Glob, every run.

  `agents/multi-review-synthesizer.md`: delete the trailing "When invoked for a deprecated paired-run report build…" block (`### Mode-divergence observations`).

  Delete: `agents/multi-review-investigate.md`, `tests/manual/agent_investigate_smoke.md`, `tests/manual/drift_ask.md`, `tests/manual/paired_pass.md`.

  `CLAUDE.md`: delete the top `### Deprecated comparison workflow` paragraph — v0.3.0 is the promised follow-up. In the preceding project overview, trim the headless driver's "does not implement pairing/drift/harvest/promotion/cleanup" contrast; those are no longer features of either entry point.

  `README.md`: delete the opening `> **Deprecated comparison workflow.**` blockquote, `## Deprecated paired runs and drift`, and `## Deprecated comparison eligibility` sections, and the invocation-table rows for `/multi-review --resume-pair <pair-id>` and `/multi-review --report`.

- [ ] **Step 4: Run and confirm GREEN**

  Run: `uv run pytest tests/integration/test_skill_contract.py -q` → PASS.

  Run: `uv run pytest tests/ -q` → expect **368 passed** (one test deleted, one added; net unchanged).

---

### Task 2: Delete harvest/snapshot/sidecar/report clusters (D4 code)

**Files:**
- Delete: `multi_review/core/harvest.py`, `multi_review/core/snapshot.py`, `multi_review/core/sidecar.py`, `multi_review/core/report.py`
- Delete: `multi_review/cli/write_harvest_row.py`, `multi_review/cli/harvest_row.py`, `multi_review/cli/migrate_harvest.py`, `multi_review/cli/migrate_sidecars.py`, `multi_review/cli/report.py`, `multi_review/cli/snapshot.py`
- Delete: `tests/unit/test_harvest.py`, `tests/unit/test_snapshot.py`, `tests/unit/test_sidecar.py`, `tests/unit/test_report.py`
- Delete: `tests/integration/test_cli_harvest_row.py`, `tests/integration/test_cli_write_harvest_row.py`, `tests/integration/test_cli_migrate_harvest.py`, `tests/integration/test_cli_migrate_sidecars.py`, `tests/integration/test_cli_snapshot.py`, `tests/integration/test_cli_report.py`
- Modify: `pyproject.toml` (remove `[project.scripts]` lines: `mr-harvest-row`, `mr-snapshot`, `mr-report`, `mr-migrate-sidecars`, `mr-migrate-harvest`, `mr-write-harvest-row`)
- Modify: `multi_review/core/adapters.py` (reword the grok usage-coercion comment so it ends at `<cli>.state.json`; there is no harvest row after this task)
- Modify: `README.md` (delete `## Deprecated v0.1 migration helpers` section)
- Modify: `CLAUDE.md` — opening packaging paragraph: replace the deleted `mr-snapshot` console-script example with a surviving script such as `mr-spawn`. `## Commands`: delete the `report regen` block. `## Testing discipline`: drop `harvest schema`, `snapshot/drift detection`, `sidecar grouping`, `report rendering` from the "Applies to" list, and remove the later "sidecar classification, harvest fields" examples. `## Architecture > Data flow`: rewrite step 5 to end after aggregate output; delete the `write_harvest_row` clause. `## Key abstractions > Adding a new reviewer`: delete the "add a `TELEMETRY_QUALITY` entry" checklist item (its only home, `core/harvest.py`, is gone; nothing else reads it). `## Invariants to preserve`: rewrite the "Downgrade (exit 3)" bullet to retain only the live behavior: fanout treats pykrete exit 3 as success and sets `ReviewerResult.downgraded`, spawn serializes that informational field into state JSON, and the family-prefixed `final_model` remains; aggregate does not read `.downgraded`, and the deleted comparison-eligibility logic must disappear. In "Two summary-sentinel regexes", replace the `runs.jsonl` consequence with the surviving consequence (a false demotion renders the review as a failure section). In "The gate runs after synthesis", change "SKILL.md Steps 7/8" → "SKILL.md Step 7" and drop the "and `write_harvest_row`" clause. In "grok's clean stopReason", delete the `runs.jsonl` consequence while retaining the live false-failure behavior. In "grok emits no tool-call events", retain the still-valid `usage.tool_calls == 0` unavailable-sentinel guidance but delete the `TELEMETRY_QUALITY["grok"]` clause. Delete the closing `## Deprecated comparison-test methodology` section.

**Interfaces:**
- Consumes: nothing outside itself — SKILL.md/agents no longer reference any of these modules after Task 1.
- Produces: `ModuleNotFoundError` for every deleted `multi_review.core.*`/`multi_review.cli.*` name.

- [ ] **Step 1: Confirm nothing outside the deletion set imports these modules**

  Run: `grep -rn "core\.harvest\|core\.snapshot\|core\.sidecar\|core\.report\b\|cli\.harvest_row\|cli\.write_harvest_row\|cli\.migrate_harvest\|cli\.migrate_sidecars\|cli\.report\b\|cli\.snapshot\b" multi_review/ tests/ skills/ agents/`

  Expected: every hit is inside a file on the deletion list above (Task 1 already removed the SKILL.md/agents references). Known false positive: `tests/manual/headless-driver-smoke.sh` matches `cli\.snapshot\b` via the unrelated shell variable name `$cli.snapshot.before` — not a module reference, not on the deletion list, ignore it.

- [ ] **Step 2: Delete**

  `git rm` the 10 source files + 10 test files above. Edit `pyproject.toml`, `multi_review/core/adapters.py`, `README.md`, and `CLAUDE.md` per the bullets above. Note: `core/sidecar.py` and `core/report.py` must be removed in the same commit — `report.py`'s `from multi_review.core.sidecar import CandidatePair` is a function-body-local import, so `import multi_review.core.report` alone still succeeds with `sidecar.py` gone; only the `pair_id=None` branch would `ImportError` at call time if split across commits.

- [ ] **Step 3: Run and confirm GREEN**

  Run: `uv run pytest tests/ -q` → expect **368 − 63 = 305 passed** (63 = summed test-function count across the 10 deleted test files).

  Run: `grep -rn "core\.harvest\|core\.snapshot\|core\.sidecar\|core\.report\b\|cli\.harvest_row\|cli\.write_harvest_row\|cli\.migrate_harvest\|cli\.migrate_sidecars\|cli\.report\b\|cli\.snapshot\b" multi_review/ tests/ skills/ agents/` → no hits.

---

### Task 3: Reference-only delivery + six-key schema removal (D1 + D3)

**Files:**
- Modify: `multi_review/core/prompt.py`, `multi_review/core/promptfile.py`, `multi_review/core/aggregate.py`
- Modify: `multi_review/cli/aggregate.py`, `multi_review/cli/prepare.py`, `multi_review/cli/spawn.py`
- Modify: `multi_review.py`
- Modify: `agents/multi-review-build.md` (`prompt_format_version: 1` → `2`, in lockstep with validator acceptance)
- Test: `tests/unit/test_prompt.py`, `tests/unit/test_promptfile.py`, `tests/unit/test_aggregate.py`, `tests/unit/test_multi_review_driver.py`
- Test: `tests/integration/test_cli_prepare.py`, `tests/integration/test_cli_aggregate.py`, `tests/integration/test_cli_validate_prompt.py`, `tests/integration/test_skill_contract.py` (new pin test only, see Step 1)
- Modify fixtures: `tests/fixtures/prompts/valid.yaml`, `tests/fixtures/prompts/missing_files.yaml`, `tests/fixtures/prompts/custom_task_missing_body.yaml`, `tests/fixtures/prompts/defaults.yaml`
- Modify: `tests/manual/fixtures/headless-driver-smoke/reference.yaml`, `tests/manual/fixtures/headless-driver-smoke/shutdown.yaml`, `tests/manual/fixtures/headless-driver-smoke/subject.py`
- Delete: `tests/manual/fixtures/headless-driver-smoke/inline.yaml`
- Modify: `tests/manual/headless-driver-smoke.sh`
- Modify: `tests/manual/headless-driver-smoke.md` (live procedure/case numbering and current-acceptance wording; retain the explicitly historical five-case output verbatim)
- Modify: `README.md` (Prompt YAML schema example + field reference table; `## Limitations`)
- Modify: `CLAUDE.md` ("Prompt shape (--mode)" bullet, "Injection posture" bullet, "Context files always inline" bullet, grok `--sandbox workspace` bullet, "Architecture > Data flow" steps 1–2, "Output paths never overwrite" bullet)

**Interfaces:**
- Consumes: `PromptFile` dataclass / `fill_defaults` / `validate` (`promptfile.py`).
- Produces: `build_prompt()` with no `mode` parameter — always inlines `context_files`, always manifests `files`; `ValidationError` naming any removed key present in a raw YAML dict.

- [ ] **Step 1: Write/adjust failing tests**

  `tests/unit/test_promptfile.py`:
  - Add `test_promptfile_rejects_removed_key`, parametrized over falsy values for all six removed keys — `("mode", "")`, `("if_drift", "")`, `("harvest", False)`, `("output_dir", None)`, `("save_as", None)`, `("model_effort", {})`. For each, `fill_defaults({...minimal valid..., key: value})` raises `ValidationError` whose message contains the key name and `v0.3.0`. Falsy cases pin presence (`key in raw`) rather than truthiness semantics.
  - Add `test_promptfile_reports_all_removed_keys_present_at_once` (2+ removed keys in one dict → message names all of them).
  - Add `test_omitting_removed_keys_still_validates` (a dict with none of the six keys constructs fine — the omission-is-fine regression guard).
  - Add `test_prompt_format_version_1_rejected_even_with_no_removed_keys`: a minimal `task`/`files`-only YAML declaring `prompt_format_version: 1` raises `ValidationError` with a message distinct from the removed-key one.
  - Strip the eight now-invalid rows (`mode`, `if_drift`, `output_dir`, `save_as`, `harvest` — one row each — plus three `model_effort` rows) from `test_malformed_field_types_raise_validation_error`.
  - Drop `.mode`/`.if_drift` assertions from `test_load_valid_roundtrip` / `test_fill_defaults_populates_missing`.
  - **File-wide sweep, required:** this file predates the bump — `grep -n prompt_format_version tests/unit/test_promptfile.py` returns ~20 hits across ~15 test functions today, nearly all still `1`. Bump every one to `2` and delete every `mode: inline`/`"mode": "inline"` literal, in every test in this file **except** the four new tests above (which deliberately exercise the version/removed-key rejection paths). Leftover `1`s fail with the new version-rejection message instead of testing what each test intends — a wrong-message failure, not a clean red.

  `tests/fixtures/prompts/defaults.yaml`: bump `prompt_format_version` 1→2 (no removed keys to strip) — read by `test_validate_defaults_reviewers_and_synthesizer_are_not_poisoned` in `test_cli_validate_prompt.py`, which asserts `returncode == 0`; unlisted here it would flip that unrelated, currently-green test to a version-rejection failure.

  `tests/unit/test_prompt.py`:
  - Rewrite `test_build_prompt_inline_wraps_files` → `test_build_prompt_context_files_always_inline` (assert body-embedding on `context_files`, not `files`).
  - Drop the `mode=` kwarg from `test_build_prompt_reference_omits_contents`, `test_build_prompt_reference_includes_both_preambles`, `test_build_prompt_custom_task_uses_custom_prompt`.
  - Rewrite `test_build_prompt_explicit_nonce_regenerated_on_collision` to seed the collision string into a `context_files` body (only context bodies are ever inlined now).
  - Add `test_build_prompt_is_reference_only`: no `mode` kwarg accepted (`TypeError` if passed); a single call never embeds an input file's bytes, always inlines context bodies.

  `tests/unit/test_aggregate.py`:
  - Drop `mode=`/`if_drift=`/`pair_id=` kwargs from all call sites.
  - Delete `test_write_review_md_includes_mode_in_frontmatter` and the `if_drift` assertion inside the frontmatter-parity test.
  - Add `test_write_review_md_frontmatter_has_no_mode_or_if_drift_keys`.

  `tests/unit/test_multi_review_driver.py`:
  - Replace `test_mode_both_exits_2` with `test_removed_key_in_promptfile_exits_2`, parametrized over the six keys: write a promptfile containing the key, `_run_driver(...)` returns 2, stderr names the key.
  - Rewrite `test_prompt_txt_contains_the_input_file_body` → `test_prompt_txt_manifests_input_file_not_body`: assert the absolute path to `target.py` appears in `prompt.txt`; assert `"return 1"` (its body) does not.
  - Drop `mode = "inline"` from the `Prompt` fake stub (~line 662).
  - Bump `prompt_format_version: 1` → `2` in all four embedded-YAML literals: `BASE_YAML` (L38 — feeds most of this file's 62 tests via `_write_promptfile`), the nul-path literal in `test_nul_path_prompt_file_exits_2_without_traceback` (L159), `THREE_YAML` (L367), `SYNTH_YAML` (L474).

  `tests/integration/test_cli_prepare.py`: drop `--mode-override` from all subprocess calls and `mode: inline` from fixture YAML strings; bump the three embedded `prompt_format_version: 1` literals (L12, L40, L73) to `2`; change assertions from inline-body/`path=` to manifest-path-only. Add a removed-key subprocess test (`mode:` key present → rc 2, one JSON line, `ok:false` naming the key) — this doubles as the regression test for `cli/prepare.py`'s exception-handling fix below.

  `tests/integration/test_cli_aggregate.py`: drop `--mode` from all 5 invocations; drop/adjust the mode-in-frontmatter assertion.

  `tests/integration/test_cli_validate_prompt.py`: add one removed-key subprocess test (rc 2, JSON `ok:false` naming the key + `v0.3.0`).

  `tests/integration/test_skill_contract.py`: add `test_builder_schema_prompt_format_version_is_current` — extract the schema block's `prompt_format_version:` value (via `_builder_schema_block()`), assert it is `2`, and assert `fill_defaults`/`validate` accept a minimal YAML declaring it with no version-related `ValidationError`. Before implementation this fails on the still-correct Task 1 template value of `1`; after implementation it pins the template and validator change together (same intent as `test_builder_schema_reviewers_line_matches_DEFAULT_REVIEWERS`).

- [ ] **Step 2: Run and confirm RED**

  Run: `uv run pytest tests/unit/test_prompt.py tests/unit/test_promptfile.py tests/unit/test_aggregate.py tests/unit/test_multi_review_driver.py tests/integration/test_cli_prepare.py tests/integration/test_cli_aggregate.py tests/integration/test_cli_validate_prompt.py -q`

  Expected: FAIL — `build_prompt` still takes/needs `mode`, `PromptFile` still has the six fields, `--mode-override`/`--mode` are still required/present, and the builder template still declares prompt format 1.

- [ ] **Step 3: Implement**

  `multi_review/core/promptfile.py`: delete the six dataclass fields (`mode`, `model_effort`, `if_drift`, `output_dir`, `save_as`, `harvest`) — `Literal` import stays (still used by `task`). Delete `_VALID_MODES`/`_VALID_IF_DRIFT`. Add `_REMOVED_KEYS = ("mode", "model_effort", "if_drift", "output_dir", "save_as", "harvest")` and, as the first statement in `fill_defaults` (before the `_REQUIRED_FIELDS` loop): collect any of `_REMOVED_KEYS` present in `raw` and raise `ValidationError(f"prompt YAML key(s) removed in v0.3.0, delete before retrying: {', '.join(found)}")`. Delete the six `raw.setdefault(...)` calls. Delete the corresponding seven `validate()` checks (mode/if_drift isinstance-str, `model_effort` out of the `("models","model_effort")` loop, `output_dir`/`save_as` out of the `("custom_prompt","output_dir","save_as")` loop, `harvest` bool check, mode-enum check, if_drift-enum check). Bump `pf.prompt_format_version != 1` → `!= 2`, with a distinct message when the file declares `1`: `"prompt_format_version: 1 is no longer supported — v0.3 removed inline delivery and 6 deprecated fields (mode, if_drift, harvest, output_dir, save_as, model_effort). Set prompt_format_version: 2."`

  `agents/multi-review-build.md`: now bump the schema template's `prompt_format_version: 1` → `2`. This lands in the same task as validator support, so every task boundary remains operational rather than relying only on the tests to stay green.

  `multi_review/core/prompt.py`: delete the `mode` param and the `Literal` import (its only use in this module). Collapse `bodies` from `(kind, f, body)` 3-tuples to `(f, body)` 2-tuples, reading only `context_files`. `files` are always `.resolve(strict=True)`'d into `manifest_paths`, never read. Make `reference_preamble()` unconditional (delete the `if mode == "reference":` guard — keep `injection_preamble`/`reference_preamble` as two separate calls, do not merge them, they describe two distinct delivery channels). Delete the `if mode == "inline": ... else: ...` input-section split; only the manifest branch survives, unindented. Update the module docstring (line 1) and the `SUMMARY_HEADING_RE`/`SUMMARY_PRESENT_RE` comment block to drop `write_harvest_row` mentions — name only `aggregate.py`.

  `multi_review/core/aggregate.py`: drop `mode` (required) and `if_drift`/`pair_id` (optional) params from `write_review_md`, plus their frontmatter lines. Update the docstring's "forward-compat" language (only `prompt_file` remains forward-compat now).

  `multi_review/cli/aggregate.py`: drop `--mode`, `--if-drift`, `--pair-id` args and their call-site kwargs; reword the `classify_review_ok` comment to drop its stray "identical to write_harvest_row" clause (that module is gone as of Task 2).

  `multi_review/cli/prepare.py`: drop `--mode-override`, the `mode = args.mode_override or pf.mode` resolution + `mode == "both"` guard, `mode=` kwarg to `build_prompt`, `"mode"` key in the printed JSON. Wrap `pf = load_promptfile(args.prompt_file)` in `try/except ValidationError as e: print(json.dumps({"ok": False, "error": str(e)})); return 2` — this is a pre-existing bug fix (today a `ValidationError` here is unhandled: raw traceback on stderr, exit 1, not 2) load-bearing for D3's "every caller reaches exit 2" claim.

  `multi_review.py`: drop `mode=pf.mode` at both call sites (`build_prompt`, `write_review_md`). Delete the `if pf.mode == "both": print(...); return 2` guard outright — `load_promptfile()` (already earlier in `_run_driver`) now exits 2 for any removed-key or version-1 YAML via the existing `except (ValidationError, yaml.YAMLError, OSError)` handler; no repositioning needed.

  `multi_review/cli/spawn.py`: delete the `--effort` argparse arg, its no-op stderr print, and the docstring paragraph about it (dead once `model_effort`/`<EFFORT_FLAG>` are gone — see Open Decision 5).

  Fixtures: bump `prompt_format_version` 1→2 and strip `mode`/`if_drift`/`harvest` in `tests/fixtures/prompts/{valid,missing_files,custom_task_missing_body,defaults}.yaml` (`defaults.yaml` has no removed keys — version-only bump; the other three must not trip the removed-key/version check before reaching the check they isolate). Same version bump for `tests/manual/fixtures/headless-driver-smoke/{reference,shutdown}.yaml`. Delete `inline.yaml`. Drop `INLINE_MARKER` from `subject.py` (`REFERENCE_MARKER` stays). Verification: by Step 4, `grep -rn 'prompt_format_version: 1' tests/` hits should only remain inside `test_promptfile.py`'s and `test_multi_review_driver.py`'s deliberate version-1-rejection tests — everywhere else must read `2`.

  `tests/manual/headless-driver-smoke.sh`: rewrite `run_self_check`'s embedded Python heredoc to drop `root / "inline.yaml"` from `required`, the `inline = load_promptfile(...)` call, and the `.mode` assertions (L126-135), plus the `mode=` kwarg to `build_prompt`. In the two literal `prompt_format_version: 1` / `mode: inline` prompt blocks (`--workload-path-check` L687-690, `write_shutdown_prompt()` L918-921), bump the version to `2` and delete the `mode:` line. Collapse case1+case2 (the inline-vs-reference comparison) into one reference-only case; renumber case3→case2, case4→case3 (switching its foreign-cwd fixture from `inline.yaml` to `reference.yaml`), case5→case4.

  `tests/manual/headless-driver-smoke.md`: mirror the executable harness's current four-case structure: merge live Sections 1–2 into one reference-only sandbox/tool-read case, then renumber WSL2 DNS→2, foreign cwd→3, shutdown→4. Update the live outcome-record instructions and final binding-acceptance wording to expect `case1`–`case4`/`cases=4`. Preserve the dated 2026-08-07 five-case results and literal output block verbatim as explicitly historical evidence; add one sentence that those old labels are not the current harness contract.

  `README.md`: drop `mode`/`model_effort`/`if_drift`/`output_dir`/`save_as`/`harvest` from the schema example and field reference table; bump the example's `prompt_format_version` to 2. Rewrite the `context_files` example comment and field-reference row to say only that context is always inlined; delete the obsolete "regardless of mode"/"both modes" and snapshot-for-drift wording. `## Limitations`: delete the drift-detection bullet; trim the v0.1-positional-CLI bullet's now-vacuous "deprecated pairing/drift/harvest/promotion/cleanup" clause; delete the "Persisted telemetry is deprecated" bullet.

  `CLAUDE.md`: replace the "Prompt shape (--mode)" bullet with an unconditional description (input always manifest, context always inline, both preambles always apply). Rewrite "Injection posture" so it no longer claims all file content is tag-wrapped: only inline context content uses `<file-NONCE>` tags; input files are manifested and their tool-read contents are still review data, not instructions. Reword "Context files always inline" to drop the "both `--mode inline` and `--mode reference`" framing. Reword the grok `--sandbox workspace` bullet's "reference mode is unaffected" clause (no more contrast partner). In "Architecture > Data flow", remove `mode` from `resolved` in step 1 and rewrite step 2 to describe unconditional manifest+inline behavior. Drop "paired legacy runs can otherwise clobber findings" from "Output paths never overwrite by default".

- [ ] **Step 4: Run and confirm GREEN**

  Run: `uv run pytest tests/unit/test_prompt.py tests/unit/test_promptfile.py tests/unit/test_aggregate.py tests/unit/test_multi_review_driver.py tests/integration/test_cli_prepare.py tests/integration/test_cli_aggregate.py tests/integration/test_cli_validate_prompt.py -q` → PASS.

  Run: `uv run pytest tests/unit/test_headless_driver_smoke_harness.py -q` → PASS (`self_check_validates_fixtures`, `self_check_does_not_use_ambient_python3`, `self_check_honors_uv_bin_without_ambient_uv`, `plain_workload_resolves_every_reviewer_from_overrides_with_restricted_path` were the four at risk from the schema change).

  Run: `uv run pytest tests/ -q` → expect **305 + net new tests** (record the actual number; new removed-key/version-gate parametrized cases add roughly a dozen).

---

### Task 4: Archive `runs/` and retire the central-path subsystem (D4 artefacts + Open Decision 3)

**Files:**
- Create: `.archive/comparison-workflow/` (verbatim move of `runs/archive/`)
- Move/modify: `runs/README.md` → `.archive/README.md`
- Delete: `runs/.gitkeep`, `runs/notes/.gitkeep`, and the emptied `runs/{reports,prompts,notes}` dirs
- Modify: `.gitignore` (remove the `runs/*`/`!runs/.gitkeep` block + its comment, the `EXPERIMENTS.md` line, and the obsolete checkout-local `config.json` ignore; add `.archive/`)
- Modify: `multi_review/core/paths.py` (delete `central_runs_dir`, `_dev_checkout_runs`, `generate_pair_id`; keep `project_state_dir`, `run_dir`, `generate_run_id`, `slugify`)
- Modify: `multi_review/cli/setup.py` (drop central-dir creation, config.json write, `--write-allowlist` argparse arg + allowlist print/write — skill+agent install only)
- Modify: `README.md` (`## Install`: delete the central-path-resolution sentence and the whole `--write-allowlist` paragraph+snippet)
- Modify: `tests/conftest.py` (reword the now-vestigial guard fixture's docstring), `CLAUDE.md` (reword the matching "No test may write into the live checkout" invariant bullet) — both describe a `config.json` write that no longer exists after this task
- Test: `tests/unit/test_paths.py`, `tests/integration/test_cli_setup.py`

**Interfaces:**
- Consumes: nothing — Task 1 already removed SKILL.md's only `CENTRAL_PATH` consumers.
- Produces: `mr-setup` that installs skill+agents only; no config.json, no central dir.

- [ ] **Step 1: Write/adjust failing tests**

  `tests/integration/test_cli_setup.py`: rewrite `test_setup_installs_skill_and_writes_config` → `test_setup_installs_skill_and_agents_only`, asserting skill+agents copied and `assert not (skill_dst / "config.json").exists()` (fails today — file exists). Delete `test_setup_heals_stale_config` outright (its premise, healing a stale `central_path` field, no longer exists). In the two surviving setup tests, remove the `XDG_DATA_HOME`/`MULTI_REVIEW_NO_DEV_CHECKOUT` monkeypatches and subprocess-environment entries; their sole consumer is the central-path code deleted in this task. Reword `test_setup_dev_mode_symlinks`'s inline comment to drop the now-dead `central_runs_dir()`/config-write explanation; keep only why a staged source copy is useful to this symlink test.

  `tests/unit/test_paths.py`: delete `test_generate_pair_id_format` and the three `central_runs_dir` tests (`honours_config`, `falls_back_to_xdg`, `ignore_config_skips_config`). Update the module-level import to retain only `project_state_dir`, `run_dir`, `generate_run_id`, and `slugify`; otherwise test collection fails as soon as the deleted names disappear from `paths.py`.

- [ ] **Step 2: Run and confirm RED**

  Run: `uv run pytest tests/integration/test_cli_setup.py -q` → FAIL (`config.json` still gets written).

- [ ] **Step 3: Implement**

  `multi_review/core/paths.py`: delete `central_runs_dir`, `_dev_checkout_runs`, `generate_pair_id`.

  `multi_review/cli/setup.py`: remove step 1 (central-dir creation), step 4 (config.json write), step 5 (`--write-allowlist` arg + allowlist print/write). `_copy_tree` gains an `exclude: set[str] = frozenset()` param that skips matching child names; the skill-install call passes `exclude={"config.json"}` so a stray dev-checkout `config.json` under `skills/multi-review/` (or a real one left by a pre-0.3.0 install) is never copied over a fresh destination. Surviving `main()` does: resolve `home`, install skill (copy/symlink), install agents (copy/symlink + reviewer-template render), print a JSON summary with `skill`/`agents` paths only.

  This checkout currently has a stray `./skills/multi-review/config.json` (gitignored, untracked, dev leftover from a pre-0.3.0 `mr-setup` run against this repo). `rm -f ./skills/multi-review/config.json` — tolerate it already being absent when this plan is executed. This is explicitly the checkout-relative file, not the protected user-data path `~/.claude/skills/multi-review/config.json` named in Global Constraints. The `exclude` param above stops it recurring, but any existing checkout file must go or `--dev` mode's symlink (which symlinks the whole `skills/multi-review` dir, bypassing `_copy_tree` entirely) would still expose it at `skill_dst`.

  `tests/conftest.py` / `CLAUDE.md`: nothing writes `config.json` anymore — reword the `_no_test_may_mutate_the_live_checkout_config` fixture's docstring and CLAUDE.md's matching invariant bullet to say so. Keep the fixture itself (harmless precaution against a future regression).

  Archive: `mkdir -p .archive && mv runs/archive .archive/comparison-workflow` (whole subtree — `git ls-files runs/` shows only `runs/.gitkeep` is tracked, so this is a plain filesystem move, no git-history operation). Move `runs/README.md` to `.archive/README.md`, then update it in place with a one-line purpose ("local-only historical record, not shipped, not read by any code"), what `comparison-workflow/` is (pre-v0.3 inline-vs-reference comparison telemetry/reports/notes) and why it's kept (historical reference only — do not use to choose inline vs reference, delivery is reference-only now regardless), plus one line noting the whole directory is gitignored. This preserves the material explanatory artefact instead of deleting and recreating it.

  `git rm runs/.gitkeep`; remove the ignored placeholder `runs/notes/.gitkeep`, then `rmdir runs/reports runs/prompts runs/notes runs`. These directories are confirmed empty scaffolding, not historical records; do not use recursive deletion here. Edit `.gitignore`: remove the `runs/*`/`!runs/.gitkeep` block and its comment, remove the `EXPERIMENTS.md` line, remove the obsolete `skills/multi-review/config.json` ignore line/comment, and add `.archive/`. The test guard still makes any future recreation of that checkout-local config visible.

  `README.md`: trim `## Install` to skill+agent install only.

- [ ] **Step 4: Run and confirm GREEN**

  Run: `uv run pytest tests/unit/test_paths.py tests/integration/test_cli_setup.py -q` → PASS.

  Run: `uv run pytest tests/ -q` → expect prior count **− 5** (4 deleted `test_paths.py` cases + 1 deleted `test_setup_heals_stale_config`).

  Run: `find .archive -maxdepth 3 | sort` and `git status --ignored .archive` → everything under `.archive` shows `Ignored`, nothing new-tracked. Run: `test ! -d runs && echo ok`.

---

### Task 5: Version bump, final documentation sweep, full verification

**Files:**
- Modify: `multi_review/__init__.py` (`__version__ = "0.3.0"`)
- Modify: `pyproject.toml` (`[project].version = "0.3.0"`)
- Modify: `uv.lock` (regenerate so the local `multi-review` package entry matches)
- Modify: `tests/unit/test_smoke.py`
- Modify: `README.md` (remaining scan)
- Modify: `BACKLOG.md` (re-tag closed-by-removal items)
- Modify: `CLAUDE.md` (final grep sweep for stray references)
- Modify: `.gitignore`, `multi_review/core/adapters.py`, `tests/` (final grep sweep only; earlier tasks should already have made the semantic edits, but fix any genuine residue while preserving deliberate rejection cases and designated historical records)

**Interfaces:**
- Consumes: Tasks 1–4 complete.
- Produces: a fully green, internally consistent v0.3.0 tree.

- [ ] **Step 1: Version bump (test-first)**

  Edit `tests/unit/test_smoke.py`: `assert multi_review.__version__ == "0.3.0"`.

  Run: `uv run pytest tests/unit/test_smoke.py -q` → FAIL (still `"0.2.0"`).

  Edit `multi_review/__init__.py`. Run again → PASS.

  Edit `pyproject.toml`: `[project].version = "0.3.0"` (was `"0.2.0a0"` — already drifted from `__init__.py`'s `"0.2.0"` pre-bump; this closes both gaps at once). Run `uv lock` to regenerate `uv.lock`'s local `multi-review` package entry (currently `version = "0.2.0"` at line 163) — package isn't installed in this checkout (`uv run python -c "import importlib.metadata; importlib.metadata.version('multi-review')"` raises `PackageNotFoundError` today, confirmed), so there's no installed-metadata check to run; verify instead with `grep -A1 'name = "multi-review"' uv.lock` showing `version = "0.3.0"`.

- [ ] **Step 2: Repo-wide staleness grep**

  Run: `rg -n "mode: (inline|reference|both)|model_effort|if_drift|output_dir:|save_as:|harvest|snapshot|sidecar|write_harvest_row|EXPERIMENTS\\.md|runs\\.jsonl|config\\.json|report regen|central_path|central_runs_dir|generate_pair_id|MULTI_REVIEW_NO_DEV_CHECKOUT|XDG_DATA_HOME|comparison_eligible|drift_blocks_eligibility|pending-harvest|resume-pair|pair_id|paired[- ]run|pairing" README.md CLAUDE.md BACKLOG.md skills/ agents/ multi_review/ tests/ .gitignore`

  Fix genuine staleness; do not mechanically replace generic uses such as an upstream event-schema "snapshot" or a schema that "drifts". Expected test hits must be inspected rather than blindly removed: keep deliberate removed-key/version-rejection cases, the retained `config.json` regression guard, `XDG_DATA_HOME` in the headless sandbox harness (real environment isolation, unrelated to central-path resolution), and `tests/manual/{pykrete,grok}-smoke.md` (Open Decision 6). In `BACKLOG.md`, already-labelled FIXED/DROPPED passages may retain historical implementation names when their status is unambiguous; open guidance must not point at deleted code. Also leave intentional historical mentions alone in `docs/superpowers/plans/*.md` (pre-dated, self-marked archival), including this plan file itself.

- [ ] **Step 3: BACKLOG.md re-tag**

  Re-tag (don't delete) as closed-by-removal: "Thread `model_effort` through to grok `--reasoning-effort`", "Field-level telemetry availability", "agy telemetry recovery", "pass-2 harvest framing gap", "SKILL Step 10b paired-report synthesis underspecified", the comparison-counter sub-bullet under "Minor paired-smoke observations", the `final_model`-in-harvest sub-bullet, "harvest write atomicity", "snapshot diff false-positives on EOL/encoding", "M12 — snapshot diff skips new files", the paired-run methodology under "Synthesizer effort/model tuning", and "review-loop integration"'s `model_effort` no-op note. Reword still-live model-reporting items (grok actual model, pykrete actual selected model) around state/aggregate output rather than harvest rows; likewise retain any still-useful adapter work while deleting telemetry-quality/harvest-only motivation. Reword "Reference mode + bwrap sandbox…" Phase 1 description from "shipped a `--mode` flag" to "shipped reference-only delivery" — Phase 2 (bwrap containment) is now more urgent since reference delivery is unconditional for every run, not opt-in; note that explicitly. Mark the old central-path FIXED/closed writeups as superseded by v0.3 removal so they cannot be mistaken for current implementation guidance, while retaining their history.

- [ ] **Step 4: Full verification**

  Run: `uv run pytest tests/ -q` → all green, record final count.

  Run: `git diff --check && git status --short` → no whitespace errors, review the diff for anything unintended.

  Run: `rg -n '^mr-(harvest-row|snapshot|report|migrate-sidecars|migrate-harvest|write-harvest-row)\\s*=' pyproject.toml` → no output (exit 1), directly confirming all six deleted `[project.scripts]` entries are absent.

  Run: `uv run python -m multi_review.cli.harvest_row` (and one per other deleted CLI: `snapshot`, `report`, `migrate_harvest`, `migrate_sidecars`, `write_harvest_row`) → `ModuleNotFoundError` in each case, independently confirming the source modules are gone.
