# Repository Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give humans and coding agents durable, non-stale entry points at the repository root and in every tracked top-level directory.

**Architecture:** Each tracked top-level directory is documented from independent exploration before the repository root is synthesized. Human READMEs stay short and actionable; harness-neutral CLAUDE files hold durable contributor contracts and are exposed through exact `AGENTS.md -> CLAUDE.md` symlinks. Automated checks derive the directory scope from Git, while a final operational-doc audit distinguishes current instructions from intentionally historical evidence.

**Tech Stack:** Markdown, relative symbolic links, Python 3, pytest, Git, Claude Code plugin validation.

## Global Constraints

- Cover the repository root and every directory represented by a tracked top-level Git path; exclude `.git` and ignored/generated directories.
- Write directory documents before using them to synthesize root documents.
- Every `README.md` must tell a fresh human what the scope is for and what useful action to take next.
- Every `CLAUDE.md` must be harness-neutral and preserve only durable authority, safety, workflow, verification, and material capability-boundary guidance.
- Do not put source-tree inventories, line references, commit IDs, dated model/tool versions, historical test totals, or local-machine observations in CLAUDE files.
- Every root or directory `AGENTS.md` must be a relative symlink whose literal target is `CLAUDE.md`.
- Preserve historical artifacts when their dated content is evidence; correct current operational instructions and label historical material non-authoritative from active entry points.
- Keep repository-maintainer `README.md`, `CLAUDE.md`, and `AGENTS.md` files out of copied skill payloads.
- Root Claude plugin agent definitions remain real files that byte-match their canonical multi-review counterparts; they are never replaced by symlinks.

---

### Task 1: Pin the documentation and installer contracts

**Files:**
- Create: `tests/test_documentation.py`
- Modify: `tests/test_install.py`
- Modify: `install.py`

**Interfaces:**
- Consumes: tracked paths reported by `git ls-files`; installer `EXCLUDE_TOP` policy.
- Produces: one parametrized structural contract for root/top-level docs and an explicit copied-payload exclusion for `AGENTS.md`.

- [ ] **Step 1: Add the failing documentation contract**

Create `tests/test_documentation.py` with this behavior:

```python
"""Repository documentation entry-point contract."""

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def tracked_top_level_directories() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    names = {
        raw.decode().split("/", 1)[0]
        for raw in result.stdout.split(b"\0")
        if raw and b"/" in raw
    }
    return [Path(name) for name in sorted(names)]


SCOPES = [Path("."), *tracked_top_level_directories()]
LOCAL_LINK = re.compile(
    r"\[[^]]+\]\((?!https?://|mailto:|#)([^)#\s]+)(?:#[^)]*)?\)"
)


@pytest.mark.parametrize(
    "scope",
    SCOPES,
    ids=lambda scope: "root" if scope == Path(".") else str(scope),
)
def test_documentation_entrypoints(scope: Path) -> None:
    directory = REPO / scope
    assert (directory / "README.md").is_file()
    assert (directory / "CLAUDE.md").is_file()

    agents = directory / "AGENTS.md"
    assert agents.is_symlink()
    assert os.readlink(agents) == "CLAUDE.md"
    assert agents.resolve(strict=True) == (directory / "CLAUDE.md").resolve()


@pytest.mark.parametrize(
    "scope",
    SCOPES,
    ids=lambda scope: "root" if scope == Path(".") else str(scope),
)
def test_entrypoint_local_markdown_links_resolve(scope: Path) -> None:
    directory = REPO / scope
    for name in ("README.md", "CLAUDE.md"):
        document = directory / name
        if not document.exists():
            continue
        for relative in LOCAL_LINK.findall(document.read_text()):
            target = (document.parent / relative).resolve()
            assert target.exists(), f"broken link in {document}: {relative}"
```

- [ ] **Step 2: Run the new contract and record the expected RED state**

Run: `python3 -m pytest tests/test_documentation.py -q`

Expected: every undocumented scope fails on a missing README, CLAUDE file, or symlink. The failure list must include root and the newly tracked `docs` directory.

- [ ] **Step 3: Pin `AGENTS.md` as maintainer-only installer content**

Add `"AGENTS.md"` to `install.py`'s `EXCLUDE_TOP`. In `test_codex_payload_ships_runtime_excludes_dev`, include `AGENTS.md` in the `drop` tuple. Add this assertion so the policy cannot pass merely because a source file happens to be absent:

```python
def test_maintainer_guidance_is_excluded_by_name():
    assert {"README.md", "CLAUDE.md", "AGENTS.md"} <= install.EXCLUDE_TOP
```

- [ ] **Step 4: Verify the installer contract**

Run: `python3 -m pytest tests/test_install.py -q`

Expected: all installer tests pass. The documentation contract remains red until directory and root entry points are created.

- [ ] **Step 5: Commit the contract change**

```bash
git add install.py tests/test_install.py tests/test_documentation.py
git commit -m "test: pin repository documentation contract"
```

### Task 2: Explore and document repository planning records

**Files:**
- Create: `docs/README.md`
- Create: `docs/CLAUDE.md`
- Create symlink: `docs/AGENTS.md -> CLAUDE.md`

**Interfaces:**
- Consumes: the repository documentation design and plan, plus an independent read-only explorer report for `docs`.
- Produces: a human index for current planning records and durable rules distinguishing current specifications/plans from component-owned historical evidence.

- [ ] **Step 1: Dispatch a read-only explorer for `docs`**

Ask one fresh explorer to identify its human purpose, authority boundaries, lifecycle rules, stale-risk factors, and appropriate verification. It must not edit files and must return exact evidence consulted.

- [ ] **Step 2: Write the local human overview**

Create a short README that says this directory holds repository-wide current design and implementation-planning records, points readers to the active specification and plan, and explains that component-specific designs remain with their components.

- [ ] **Step 3: Write durable agent guidance**

Create a CLAUDE file covering current-versus-historical authority, spec/plan naming and review gates, the rule against treating plans as runtime truth, and link/placeholder verification. Do not enumerate every plan or repeat task content.

- [ ] **Step 4: Add and verify the symlink**

Run:

```bash
ln -s CLAUDE.md docs/AGENTS.md
python3 -m pytest 'tests/test_documentation.py::test_documentation_entrypoints[docs]' -q
```

Expected: the `docs` parameter passes.

- [ ] **Step 5: Commit the planning-doc entry points**

```bash
git add docs/README.md docs/CLAUDE.md docs/AGENTS.md
git commit -m "docs: explain repository planning records"
```

### Task 3: Document packaging and test-support directories

**Files:**
- Create: `.agents/README.md`, `.agents/CLAUDE.md`, `.agents/AGENTS.md`
- Create: `.claude-plugin/README.md`, `.claude-plugin/CLAUDE.md`, `.claude-plugin/AGENTS.md`
- Create: `agents/README.md`, `agents/CLAUDE.md`, `agents/AGENTS.md`
- Create: `tests/README.md`, `tests/CLAUDE.md`, `tests/AGENTS.md`

**Interfaces:**
- Consumes: completed explorer reports for `.agents`, `.claude-plugin`, `agents`, and `tests`; installer and plugin-agent contract tests.
- Produces: local packaging/discovery/test guidance without duplicating the current skill or agent inventory.

- [ ] **Step 1: Write four succinct READMEs**

Cover these outcomes:

- `.agents`: Codex repository-local discovery aliases; edit canonical skill roots rather than these links.
- `.claude-plugin`: Claude marketplace/plugin metadata; root README owns installation guidance.
- `agents`: real-file Claude plugin agent mirrors; canonical definitions live with multi-review.
- `tests`: packaging and plugin-registration regression tests; point maintainers to the full root-suite command.

- [ ] **Step 2: Write four durable CLAUDE files**

Preserve these contracts:

- discovery links are relative, zero-copy aliases and move in sync with installer/plugin metadata;
- manifest dots resolve from repository root, plugin names stay aligned, and plugin validation alone does not prove agent registration;
- root agent mirrors must be byte-identical regular files, with synchronization verified by `tests/test_plugin_agents.py`;
- root tests use isolated temporary homes, sample rather than exhaustively prove payload boundaries, and failures identify packaging rather than component behavior.

Do not copy exact skill names, agent names, manifest versions, or test counts into CLAUDE prose.

- [ ] **Step 3: Create exact local symlinks**

```bash
ln -s CLAUDE.md .agents/AGENTS.md
ln -s CLAUDE.md .claude-plugin/AGENTS.md
ln -s CLAUDE.md agents/AGENTS.md
ln -s CLAUDE.md tests/AGENTS.md
```

- [ ] **Step 4: Verify the four scopes and packaging behavior**

Run:

```bash
python3 -m pytest \
  'tests/test_documentation.py::test_documentation_entrypoints[.agents]' \
  'tests/test_documentation.py::test_documentation_entrypoints[.claude-plugin]' \
  'tests/test_documentation.py::test_documentation_entrypoints[agents]' \
  'tests/test_documentation.py::test_documentation_entrypoints[tests]' \
  tests/test_install.py tests/test_plugin_agents.py -q
claude plugin validate . --strict
```

Expected: every selected test passes and strict plugin validation succeeds.

- [ ] **Step 5: Commit packaging documentation**

```bash
git add .agents .claude-plugin agents tests
git commit -m "docs: explain packaging and test surfaces"
```

### Task 4: Document Feature Forge

**Files:**
- Modify: `feature-forge/README.md`
- Create: `feature-forge/CLAUDE.md`
- Create symlink: `feature-forge/AGENTS.md -> CLAUDE.md`

**Interfaces:**
- Consumes: the Feature Forge explorer report and live `SKILL.md`/owner references.
- Produces: a human invocation/prerequisite overview and a durable controller-maintenance contract.

- [ ] **Step 1: Rewrite the README around user action**

Explain when a bounded Git work unit warrants Feature Forge, how to invoke it, the human decisions it may request, and that it depends on review-loop plus participating Superpowers skills. Link to live owner references; identify dated design/review material as lineage, not current execution authority.

- [ ] **Step 2: Write the CLAUDE contract**

Retain sole-controller/ledger authority, source-of-truth ownership among live references, frozen spec/plan identity, no-unrelated-work handling, authority/UAT truthfulness, worker packet boundaries, review-loop verdict mapping, and exactly-once Finish recovery. Describe state semantics, not the current file layout or dated qualification evidence.

- [ ] **Step 3: Add the symlink and verify the scope**

```bash
ln -s CLAUDE.md feature-forge/AGENTS.md
python3 -m pytest 'tests/test_documentation.py::test_documentation_entrypoints[feature-forge]' -q
```

Expected: the Feature Forge parameter passes.

- [ ] **Step 4: Commit Feature Forge documentation**

```bash
git add feature-forge/README.md feature-forge/CLAUDE.md feature-forge/AGENTS.md
git commit -m "docs: separate Feature Forge user and agent guidance"
```

### Task 5: Rewrite multi-review documentation and current smoke instructions

**Files:**
- Modify: `multi-review/README.md`
- Modify: `multi-review/CLAUDE.md`
- Create symlink: `multi-review/AGENTS.md -> CLAUDE.md`
- Modify: `multi-review/tests/manual/grok-smoke.md`
- Modify: `multi-review/tests/manual/agent_reviewer_smoke.md`
- Modify: `multi-review/tests/manual/agent_synthesizer_smoke.md`

**Interfaces:**
- Consumes: multi-review explorer report, live Python contracts, `SKILL.md`, canonical agents, and contract tests.
- Produces: accurate separation between interactive Claude orchestration and caller-contained headless execution, plus current manual-smoke paths.

- [ ] **Step 1: Replace the README with a succinct user contract**

Distinguish `/multi-review` from the headless driver; call the latter caller-contained rather than contained by itself. Explain partial-failure reporting, minimal prompt usage, installation, and untrusted-code warning. Remove billing history, dated model examples, exact provider argv/event details, removed-v0.1 narrative, and blanket artifact-name claims.

- [ ] **Step 2: Replace brittle CLAUDE observations with durable invariants**

Keep execution-path ownership, reviewer-known versus reviewer-default semantics, prompt-delivery security, result/summary gates, synthesis narration parity, output atomicity, canonical-agent mirroring, tests-before-agent install, and the fact that Claude `--dev` still copies subagent files. Remove environment-specific pytest/console-script claims, dated CLI observations, event catalogs, chat/commit references, and source inventories.

- [ ] **Step 3: Correct active manual-smoke instructions**

- Replace the removed setup module in the Grok precondition with `python3 install.py multi-review --target claude` run from repository root, and state that `--dev` still requires reinstall after canonical agent changes.
- Replace `skills/multi-review/templates/reviewer_task.md` with `multi-review/templates/reviewer_task.md`.
- Replace `skills/multi-review/templates/synthesizer_task.md` with `multi-review/templates/synthesizer_task.md`.
- Keep live-paid-network and historical-observation labels where they are materially part of the smoke procedure.

- [ ] **Step 4: Add the symlink and run focused verification**

```bash
ln -s CLAUDE.md multi-review/AGENTS.md
python3 -m pytest 'tests/test_documentation.py::test_documentation_entrypoints[multi-review]' -q
uv run --project multi-review --extra dev pytest multi-review/tests -q
python3 -m pytest tests/test_plugin_agents.py -q
```

Expected: the documentation parameter, component suite, and mirror contract pass.

- [ ] **Step 5: Commit multi-review documentation**

```bash
git add multi-review/README.md multi-review/CLAUDE.md multi-review/AGENTS.md multi-review/tests/manual
git commit -m "docs: refresh multi-review guidance"
```

### Task 6: Rewrite review-loop documentation at its implemented boundary

**Files:**
- Modify: `review-loop/README.md`
- Create: `review-loop/CLAUDE.md`
- Create symlink: `review-loop/AGENTS.md -> CLAUDE.md`
- Modify: `review-loop/docs/history/README.md`

**Interfaces:**
- Consumes: review-loop explorer report, live controller/kernel behavior, shipped `SKILL.md`/dispatch guidance, and acceptance evidence.
- Produces: an honest current capability overview and a durable deterministic-controller contract.

- [ ] **Step 1: Rewrite the README around the actual operator boundary**

Explain the fail-closed ledger model and qualified verdict, but state clearly that production CLI commands manage runs/status/reports while role-driving stages still require a host/controller caller. Describe the currently wired single-round FIX boundary and opt-in multi-review limitation without source inventories or dated acceptance totals.

- [ ] **Step 2: Write the CLAUDE contract**

Keep deterministic-code versus semantic-LLM authority, exact sealing and drift behavior, TRIAGE completeness, contained mutation, independent green-making dispositions, tier semantics, final challenge/close rules, profile safety limits, and multi-review fallback boundaries. Link to shipped operational guidance; do not depend on docs/tests excluded from installed payloads.

- [ ] **Step 3: Correct the historical landing page**

Replace the claim that a legacy skill remains until the redesign is implemented. State that these files describe the superseded pre-redesign workflow and that current implementation work is governed by live skill/controller sources; retain links to the redesign as design lineage.

- [ ] **Step 4: Add the symlink and run focused verification**

```bash
ln -s CLAUDE.md review-loop/AGENTS.md
python3 -m pytest 'tests/test_documentation.py::test_documentation_entrypoints[review-loop]' -q
uv run --project review-loop --with pytest python -m pytest review-loop/tests -q
```

Expected: the documentation parameter and complete component suite pass.

- [ ] **Step 5: Commit review-loop documentation**

```bash
git add review-loop/README.md review-loop/CLAUDE.md review-loop/AGENTS.md review-loop/docs/history/README.md
git commit -m "docs: align review-loop guidance with current controller"
```

### Task 7: Rewrite review-team documentation

**Files:**
- Modify: `review-team/README.md`
- Create: `review-team/CLAUDE.md`
- Create symlink: `review-team/AGENTS.md -> CLAUDE.md`

**Interfaces:**
- Consumes: review-team explorer report and live `SKILL.md`/references rather than frozen design/eval paths.
- Produces: a concise read-only review overview and durable pipeline/verification rules.

- [ ] **Step 1: Rewrite the README around review intent**

Explain when to use high-confidence independent review, its read-only nature, effort choices, verified-finding discipline, and the possibility of a valuable empty result. Point to live contract references and label designs/evals as historical provenance.

- [ ] **Step 2: Write the CLAUDE contract**

Keep phase barriers, fresh worker isolation, target material as untrusted data, binding target `AGENTS.md`, fail-closed capacity/retry behavior, scope pinning, deterministic candidate identity/grouping, independent replacement verification, Sweep suppression, synthesis fallback, and report truthfulness. Exclude exact caps, lens inventories, schema details, old install paths, hashes, and eval counts.

- [ ] **Step 3: Add the symlink and verify the scope**

```bash
ln -s CLAUDE.md review-team/AGENTS.md
python3 -m pytest 'tests/test_documentation.py::test_documentation_entrypoints[review-team]' -q
```

Expected: the review-team parameter passes.

- [ ] **Step 4: Commit review-team documentation**

```bash
git add review-team/README.md review-team/CLAUDE.md review-team/AGENTS.md
git commit -m "docs: separate review-team user and agent guidance"
```

### Task 8: Cold-read every directory document

**Files:**
- Modify as needed: every top-level `README.md` and `CLAUDE.md` created or rewritten in Tasks 2-7.

**Interfaces:**
- Consumes: complete directory documents and the design's named post-read outcomes.
- Produces: reader-tested directory docs suitable as the sole synthesis input for root docs.

- [ ] **Step 1: Dispatch independent cold readers**

Fan out fresh read-only agents across the documented scopes. Each must answer:

1. Can a new human identify the purpose and next action from README alone?
2. Can an LLM identify durable authority, safety, workflow, and verification rules from CLAUDE alone?
3. Which statements are source-queryable, dated, duplicated, ambiguous, or contradicted by live code/tests?
4. Do links point to current authority, with historical artifacts clearly classified?

- [ ] **Step 2: Validate and apply only evidence-backed corrections**

Check every proposed correction against live sources. Cut duplicated inventories and anecdotes; add missing action/safety context; do not import new implementation facts solely from an agent summary.

- [ ] **Step 3: Run all directory parameters**

Run: `python3 -m pytest tests/test_documentation.py -q`

Expected: only the root parameter may still fail; every tracked directory parameter passes.

- [ ] **Step 4: Commit cold-read refinements**

```bash
git add .agents .claude-plugin agents docs feature-forge multi-review review-loop review-team tests
git commit -m "docs: refine directory guidance after cold read"
```

### Task 9: Synthesize repository-root documentation last

**Files:**
- Modify: `README.md`
- Create: `CLAUDE.md`
- Create symlink: `AGENTS.md -> CLAUDE.md`

**Interfaces:**
- Consumes: only completed/cold-read top-level READMEs and CLAUDE files, plus root installer/plugin entry points for verification.
- Produces: the repository-wide human overview and harness-neutral contributor contract.

- [ ] **Step 1: Rewrite the root human overview**

Summarize the skillbook's purpose, link to each user-facing component README, explain in-repo and copied installation, identify essential prerequisites and major safety boundaries, and provide the next action for Claude Code and Codex users. Keep packaging internals in root CLAUDE, not README.

- [ ] **Step 2: Write the root CLAUDE contract**

Synthesize repository-wide authority and documentation policy, canonical-skill versus discovery/mirror boundaries, plugin and installer synchronization, explicit-path Git safety, verification routing, maintainer-doc exclusion, and the rule that component CLAUDE files own component-specific invariants. Avoid a directory tree or copied component details.

- [ ] **Step 3: Add the root symlink and run the full structural contract**

```bash
ln -s CLAUDE.md AGENTS.md
python3 -m pytest tests/test_documentation.py -q
```

Expected: every root and directory parameter passes.

- [ ] **Step 4: Dispatch one fresh root cold reader**

Ask it to navigate from root README to a suitable skill and from root CLAUDE to the correct component maintenance guidance without using conversation history. Apply only source-validated gaps or cuts.

- [ ] **Step 5: Commit root documentation**

```bash
git add README.md CLAUDE.md AGENTS.md
git commit -m "docs: add repository human and agent entry points"
```

### Task 10: Audit stale operational documentation and verify acceptance

**Files:**
- Modify only source-validated stale operational documents found by the audit.

**Interfaces:**
- Consumes: all completed documentation, the design acceptance criteria, live sources/tests, and known stale terms from exploration.
- Produces: an evidence-backed final audit with current instructions corrected and historical evidence intentionally classified.

- [ ] **Step 1: Search for known obsolete operational references**

Run focused searches for removed setup modules, legacy nested skill paths, claims that headless multi-review supplies its own containment, outdated review-loop implementation status, and active references to unavailable installed docs. Classify every hit as current operational guidance or historical evidence before editing.

Example command:

```bash
rg -n 'multi_review\.cli\.setup|skills/multi-review|setup\.py|legacy skill.*until|contained headless|tests/ACCEPTANCE\.md' \
  --glob '*.md' --glob '!**/docs/superpowers/**' --glob '!**/evals/**'
```

- [ ] **Step 2: Check Markdown links in current entry points**

Run the durable entry-point link contract:

```bash
python3 -m pytest tests/test_documentation.py -k local_markdown_links -q
```

Expected: every local Markdown target in root and top-level READMEs/CLAUDE files exists. Check historical landing pages separately; do not rewrite frozen evidence merely to make old prose current.

- [ ] **Step 3: Run complete verification**

```bash
python3 -m pytest tests -q
uv run --project multi-review --extra dev pytest multi-review/tests -q
uv run --project review-loop --with pytest python -m pytest review-loop/tests -q
claude plugin validate . --strict
git diff --check
git status --short
```

Expected: all test suites and plugin validation pass; `git diff --check` is silent; status contains only intentional documentation/audit changes not yet committed.

- [ ] **Step 4: Audit the specification requirement by requirement**

Verify each acceptance criterion against current files, symlink metadata, test output, cold-reader reports, stale-search classifications, and the fact that root docs were authored after directory docs. Treat missing or indirect evidence as incomplete and return to the owning task.

- [ ] **Step 5: Commit final audit corrections**

```bash
git add README.md CLAUDE.md AGENTS.md .agents .claude-plugin agents docs feature-forge multi-review review-loop review-team tests install.py
git commit -m "docs: complete repository documentation audit"
```
