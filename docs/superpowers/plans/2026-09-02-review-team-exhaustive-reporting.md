# Exhaustive Review-Team Reporting Implementation Plan

> **Execution bootstrap:** Before invoking an execution skill or creating its
> workspace, set the controller working directory to
> `/home/mark/kramtime/llm-skillbook/.worktrees/review-team-refinements` and
> verify that it is the `review-team-refinements` linked worktree. Do not run
> SDD setup from the primary checkout and do not create another worktree.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `review-team` report every independently verified surviving finding while keeping its upstream candidate ceilings and favoring terse, evidence-complete issue prose.

**Architecture:** Keep Scope, Finder, verification, replacement, Sweep, and candidate ceilings unchanged. Replace the final numeric report cap with the closed policy `allVerifiedSurvivors`: Synthesis may order and conservatively merge findings only when their normalized issue semantics match, the controller must deterministically backfill every unmentioned survivor with a total accepted-before-backfilled same-bucket order, and fallback must emit every exact-deduplicated survivor. Apply concise-language guidance where report text originates—in Finder summaries and failure scenarios, Verifier evidence, and final assembly—without weakening evidence requirements.

**Tech Stack:** Markdown skill contracts, Python 3, pytest, Git.

**Spec:** In-chat bounded design approved 2026-09-02; its complete normative requirements are reproduced in Global Constraints because this bounded change has no separate specification file.

**Status:** Reviewed and ready for implementation; four-round review loop complete with no open Critical or Important findings, with the documentation handoff added before this plan was committed.

## Global Constraints

- Remove only the final report cap. Preserve the existing `high` and `xhigh` Finder, Cleanup, Sweep, replacement, and all-record ceilings exactly.
- Account for every independently verified `CONFIRMED` or `PLAUSIBLE` survivor exactly once: as a primary finding, as a member of an explicit same-root-cause merge, or as a retained identity in a fallback exact-duplicate group. Surface every distinct verified issue and every distinct verifier-evidence item.
- Keep Synthesis optional and non-authoritative. Invalid, missing, failed, or unusable Synthesis output must not drop a distinct verified issue or distinct verifier evidence. Admit a same-root-cause merge only when every member also has the same category and verdict and byte-identical normalized `summary` and `failure_scenario` after trimming and collapsing internal whitespace; otherwise keep the members as separate primaries.
- Keep correctness before cleanup and `CONFIRMED` before `PLAUSIBLE`. Within each category/verdict bucket, emit accepted primaries in Synthesis severity order followed by backfilled primaries in base order; preserve the existing deterministic base order for fallback.
- Keep refuted details hidden unless requested at invocation, and preserve the exact no-survivor outcome.
- Declare `reportPolicy: allVerifiedSurvivors` before dispatch and in final stats. Keep numeric candidate limits inside `ceilings`; do not represent unlimited reporting as a numeric sentinel.
- Favor terse prose: one-line imperative titles and, when the evidence remains complete, one sentence each for the failure scenario or cleanup cost and verifier evidence. Never shorten text by dropping the trigger, consequence, cited guard, invariant, rule, or concrete cost required by the applicable evidence ladder.
- Treat `review-team/docs/` and `review-team/evals/` as historical provenance. Do not rewrite their frozen caps or recorded results as though past evaluations exercised the new behavior.
- Update `review-team/README.md` with the user-facing exhaustive-reporting and terse-prose behavior. Update `review-team/CLAUDE.md` with the durable maintainer contract and focused verification route.
- Preserve `review-team/AGENTS.md` and root `AGENTS.md` as exact relative symlinks whose literal target is `CLAUDE.md`; verify them rather than replacing or editing them.
- Keep root `README.md` and `CLAUDE.md` unchanged unless implementation reveals a genuinely repository-wide rule. The Review Team component owns these reporting invariants.
- Do not install into a user-scoped skills directory, update plugin caches, publish, push, or open a pull request as part of this plan.
- Preserve unrelated work and stage only the explicit paths named by each commit step.
- Run every controller and worker filesystem or Git operation in `/home/mark/kramtime/llm-skillbook/.worktrees/review-team-refinements`. Do not implement from the primary checkout or create another worktree.

## Execution Preflight

Before creating the SDD workspace or dispatching Task 1, set the working directory for every controller command to `/home/mark/kramtime/llm-skillbook/.worktrees/review-team-refinements` and run:

```bash
git rev-parse --show-toplevel
git branch --show-current
git status --short --branch
```

Expected: the top level is `/home/mark/kramtime/llm-skillbook/.worktrees/review-team-refinements`, the branch is `review-team-refinements`, and the worktree is clean. If any path appears, preserve it and record it in the SDD ledger before dispatch; never stage it through this plan unless a later task explicitly owns it.

---

### Task 1: Pin the exhaustive-reporting contract

**Files:**
- Create: `review-team/tests/test_reporting_contract.py`
- Modify: `review-team/SKILL.md:35-62`
- Modify: `review-team/references/report-contract.md:19-38,245-254,361-468`
- Modify: `review-team/references/finder-angles.md:169-176`
- Modify: `review-team/references/verifier.md:47-53`

**Interfaces:**
- Consumes: ordered, independently verified survivor records and the existing numeric candidate-ceiling table.
- Produces: `reportPolicy: allVerifiedSurvivors`, exhaustive Synthesis backfill, exhaustive deterministic fallback, and final stats with numeric candidate ceilings only.

- [ ] **Step 1: Add the failing structural contract test**

Create `review-team/tests/test_reporting_contract.py`:

```python
"""Static contract checks for exhaustive Review Team reporting."""

from pathlib import Path


COMPONENT = Path(__file__).resolve().parents[1]
SKILL = (COMPONENT / "SKILL.md").read_text()
REPORT = (COMPONENT / "references" / "report-contract.md").read_text()
FINDER = (COMPONENT / "references" / "finder-angles.md").read_text()
VERIFIER = (COMPONENT / "references" / "verifier.md").read_text()


def test_every_verified_survivor_is_reported() -> None:
    live_reporting_contract = "\n".join((SKILL, REPORT, FINDER, VERIFIER))

    assert "reportPolicy: allVerifiedSurvivors" in REPORT
    assert "Backfill every unmentioned survivor in base order." in REPORT
    assert "Emit every remaining representative in survivor order." in REPORT
    assert "Every survivor `candidateId` must be accounted for exactly once" in REPORT
    assert "`reported` is the number of rendered primary findings" in REPORT
    assert "exact partition of all fallback survivor IDs" in REPORT
    assert "Retain every distinct verifier-evidence item" in REPORT
    assert "Render every distinct verifier-evidence item from a semantic merge" in REPORT
    assert "Assemble the complete report deterministically." in SKILL

    for obsolete in (
        "report cap and output",
        "Report cap",
        "report capacity remains",
        "take the report cap",
        "reportCap",
        "the report cap",
        "final cap",
        "while capacity remains",
    ):
        assert obsolete not in live_reporting_contract


def test_numeric_candidate_ceilings_are_preserved() -> None:
    assert (
        "| `high` | A-C, `3 × 6` | `1 × 30` | 48 | 0 | 48 | 48 | 96 |"
        in REPORT
    )
    assert (
        "| `xhigh` | A-E, `5 × 8` | `1 × 40` | 80 | 8 | 88 | 88 | 176 |"
        in REPORT
    )


def test_higher_priority_backfilled_survivor_precedes_accepted_lower_priority_finding() -> None:
    assert (
        "After backfill, order the complete set of accepted and backfilled primary findings\n"
        "together: correctness before Cleanup and `CONFIRMED` before `PLAUSIBLE`."
        in REPORT
    )


def test_semantic_merges_require_identical_normalized_issue_semantics() -> None:
    assert (
        "Admit a semantic merge only when the supplied summaries and verifier evidence\n"
        "make the same root cause explicit and every member has the same category and\n"
        "verdict."
        in REPORT
    )
    assert (
        "Require the normalized `summary` and `failure_scenario` values to be\n"
        "byte-identical across all members."
        in REPORT
    )
    assert "Normalize each field by trimming it and\ncollapsing internal whitespace" in REPORT
    assert "Otherwise keep the records as\nseparate primary findings." in REPORT
    assert "Preserve every affected location." in REPORT


def test_same_bucket_accepted_primaries_precede_backfilled_primaries() -> None:
    assert (
        "Within each category and verdict bucket, emit accepted primaries in Synthesis\n"
        "severity order followed by backfilled primaries in base order."
        in REPORT
    )
```

- [ ] **Step 2: Run the new test and confirm the RED state**

Run:

```bash
python3 -m pytest review-team/tests/test_reporting_contract.py -q
```

Expected: `test_every_verified_survivor_is_reported` and the three Synthesis ordering/merge tests fail because the live files still contain the numeric report-cap contract and lack the exhaustive compatibility and tie rules. `test_numeric_candidate_ceilings_are_preserved` passes because it pins the candidate values that must survive this change.

- [ ] **Step 3: Remove the cap from the live entry point**

In `review-team/SKILL.md`, keep the phase topology and replace the capped assembly instruction with:

```markdown
6. Send only verified `CONFIRMED` and `PLAUSIBLE` survivors to optional
   Synthesis. Assemble the complete report deterministically.
```

Do not copy numeric role ceilings into `SKILL.md`; `report-contract.md` remains their one live source of truth.

- [ ] **Step 4: Replace the report cap with an exhaustive policy**

In `review-team/references/report-contract.md`:

1. Change the state-machine terminus from `report cap and output` to `complete report output`.
2. Remove the `Report cap` column and its `10`/`15` values while preserving these exact rows:

```markdown
| Level | Correctness finders | Cleanup | Initial max | Sweep max | Finder-output max | Replacement max | All-record max |
|---|---:|---:|---:|---:|---:|---:|---:|
| `high` | A-C, `3 × 6` | `1 × 30` | 48 | 0 | 48 | 48 | 96 |
| `xhigh` | A-E, `5 × 8` | `1 × 40` | 80 | 8 | 88 | 88 | 176 |
```

3. Immediately after the table, add:

```markdown
The closed report policy is `allVerifiedSurvivors`. It is not a numeric
ceiling. Account for every independently verified `CONFIRMED` or `PLAUSIBLE`
survivor exactly once: as a primary finding, as a member of an explicit
same-root-cause merge, or as a retained identity in a fallback exact-duplicate
group. Surface every distinct verified issue and verifier-evidence item.
```

4. In Synthesis, replace both capacity-conditional backfill rules—including the earlier “while capacity remains” sentence and the later “report capacity remains” sentence—with unconditional accounting. Require every survivor to be claimed by a valid primary or merge identity, or deterministically backfilled. Use this exact controller rule:

```markdown
Backfill every unmentioned survivor in base order. Preserve verifier
refinements and never promote an unverified replacement. After backfill, require
every dispatched survivor identity to appear exactly once across primary and
merge positions; otherwise discard Synthesis and use deterministic fallback.
```

After global correctness-before-Cleanup and `CONFIRMED`-before-`PLAUSIBLE`
precedence, define the complete same-bucket tie rule:

```markdown
Within each category and verdict bucket, emit accepted primaries in Synthesis
severity order followed by backfilled primaries in base order.
```

5. Replace report-slot language with finding identity. Admit a semantic merge only when the records have an explicit shared root cause, the same category and verdict, and byte-identical normalized `summary` and `failure_scenario` after trimming each field and collapsing internal whitespace. Otherwise keep them as separate primary findings. A valid merge emits one primary carrying every affected location; distinct root causes remain distinct findings. Add these compatibility and evidence rules:

```markdown
Admit a semantic merge only when the supplied summaries and verifier evidence
make the same root cause explicit and every member has the same category and
verdict. Require the normalized `summary` and `failure_scenario` values to be
byte-identical across all members. Normalize each field by trimming it and
collapsing internal whitespace before comparing. Otherwise keep the records as
separate primary findings.
```

```markdown
Render every distinct verifier-evidence item from a semantic merge with its
affected location. Collapse only byte-identical evidence; terse presentation
must not erase evidence that supports a different merged survivor.
```
6. In deterministic fallback, retain exact-claim deduplication and ordering. Treat each representative plus its retained exact-duplicate IDs as one controller-owned identity group. Require those groups to form an exact partition of all fallback survivor IDs. Retain every distinct verifier-evidence item and collapse only byte-identical evidence before rendering. Then state:

```markdown
Emit every remaining representative in survivor order. Label the report as
deterministic fallback because Synthesis was skipped, failed, or unusable.
```

7. After the Synthesis and fallback rules, add the shared postcondition:

```markdown
Every survivor `candidateId` must be accounted for exactly once by a rendered
primary, a valid semantic merge, or a fallback exact-duplicate group. Preserve
every distinct verifier-evidence item attached to an accounted survivor. The
fallback groups must form an exact partition of all fallback survivor IDs.
`reported` is the number of rendered primary findings after valid semantic
merges or fallback exact deduplication; it is not the survivor count.
```

8. Put `reportPolicy` beside `level` in the final stats schema and remove `reportCap` from `ceilings`:

```text
level
reportPolicy: allVerifiedSurvivors
completedFinders
candidates
verifierAgents
confirmed
plausible
refuted
refinements
independentlyVerifiedReplacements
reported
excludedGitlinks[]
ceilings: {
  initial
  sweep
  finderOutput
  replacement
  allRecords
}
```

9. Require the controller to emit the closed report policy together with the numeric ceilings before dispatch and in final stats.

- [ ] **Step 5: Remove obsolete final-cap guidance from Finders and Verifiers**

In `review-team/references/finder-angles.md`, replace the conditional final-cap sentence with:

```markdown
Correctness survivors precede Cleanup survivors in base and final ordering.
```

In `review-team/references/verifier.md`, change the input-exclusion sentence so it ends:

```markdown
Do not send Finder identity, Finder confidence, hidden reasoning, other
locations, session history, expected verdicts, or final presentation policy.
```

Verifiers still judge evidence independently and do not need to know whether or how the controller formats all survivors.

- [ ] **Step 6: Run the focused contract test**

Run:

```bash
python3 -m pytest review-team/tests/test_reporting_contract.py -q
```

Expected: 5 tests pass. Inspect a failure rather than weakening an assertion or changing any preserved numeric ceiling.

- [ ] **Step 7: Review and commit the exhaustive-reporting contract**

Run:

```bash
git status --short
git add review-team/SKILL.md review-team/references/report-contract.md review-team/references/finder-angles.md review-team/references/verifier.md review-team/tests/test_reporting_contract.py
git diff --cached -- review-team/SKILL.md review-team/references/report-contract.md review-team/references/finder-angles.md review-team/references/verifier.md review-team/tests/test_reporting_contract.py
git diff --cached --check -- review-team/SKILL.md review-team/references/report-contract.md review-team/references/finder-angles.md review-team/references/verifier.md review-team/tests/test_reporting_contract.py
git commit -m "feat(review-team): report every verified finding"
```

Expected: the cached diff includes the complete new test plus only the four live contract files, no unrelated path is staged, the commit succeeds, and the worktree returns to clean.

### Task 2: Make finding prose terse at its sources

**Files:**
- Modify: `review-team/tests/test_reporting_contract.py`
- Modify: `review-team/references/finder-angles.md:65-91`
- Modify: `review-team/references/verifier.md:179-206`
- Modify: `review-team/references/report-contract.md:426-440`

**Interfaces:**
- Consumes: Finder `summary` and `failure_scenario` strings plus Verifier `evidence` strings.
- Produces: terse report-ready fields that retain the trigger, consequence, and evidence required by the applicable verdict ladder.

- [ ] **Step 1: Extend the contract test with terse-language requirements**

Append to `review-team/tests/test_reporting_contract.py`:

```python
def test_report_fields_favor_terse_evidence_complete_language() -> None:
    assert "Keep `summary` to one terse sentence." in FINDER
    assert "Keep `failure_scenario` to one terse sentence" in FINDER
    assert "Keep `evidence` to one terse sentence when that sentence" in VERIFIER
    assert "Apply the same terse-field rules to refinements and replacements." in VERIFIER
    assert "Do not repeat the same mechanism across fields." in REPORT
    assert "Never omit evidence required by the applicable verdict ladder." in REPORT
```

- [ ] **Step 2: Run the focused test and confirm the new RED state**

Run:

```bash
python3 -m pytest review-team/tests/test_reporting_contract.py::test_report_fields_favor_terse_evidence_complete_language -q
```

Expected: FAIL because the approved terse-language rules are not yet present.

- [ ] **Step 3: Tighten Finder output without lowering its evidence bar**

After the candidate shape in `review-team/references/finder-angles.md`, add:

```markdown
Keep `summary` to one terse sentence. Keep `failure_scenario` to one terse
sentence when that sentence can still name the observable wrong output, crash,
data loss, security effect, wasted work, or concrete maintenance cost. Use a
second sentence only when it is necessary to preserve the trigger or
consequence.
```

Retain the existing maximum-not-quota, anti-padding, and evidence-backed-empty-output rules unchanged.

- [ ] **Step 4: Tighten Verifier evidence without weakening adjudication**

After the output shape in `review-team/references/verifier.md`, add:

```markdown
Keep `evidence` to one terse sentence when that sentence can still cite the
relevant code, guard, invariant, rule, or concrete cost and satisfy the selected
verdict ladder. Use additional sentences only for evidence necessary to the
verdict or a supported refinement. Apply the same terse-field rules to
refinements and replacements: their `summary` is one terse sentence, and their
`failure_scenario` is one terse sentence unless a second is necessary to
preserve the trigger or consequence.
```

Do not change either verdict ladder, identity validation, whole-group completeness, or replacement rules.

- [ ] **Step 5: Tighten final rendering guidance**

After the finding shape in `review-team/references/report-contract.md`, add:

```markdown
Favor terse language. Keep the imperative title on one line and keep the
failure scenario or cleanup cost and verifier evidence to one sentence each
when their required meaning remains complete. Do not repeat the same mechanism
across fields. Never omit evidence required by the applicable verdict ladder.
```

- [ ] **Step 6: Run the complete component contract test**

Run:

```bash
python3 -m pytest review-team/tests/test_reporting_contract.py -q
```

Expected: 6 tests pass.

- [ ] **Step 7: Review and commit the terse-output contract**

Run:

```bash
git status --short
git add review-team/references/finder-angles.md review-team/references/verifier.md review-team/references/report-contract.md review-team/tests/test_reporting_contract.py
git diff --cached -- review-team/references/finder-angles.md review-team/references/verifier.md review-team/references/report-contract.md review-team/tests/test_reporting_contract.py
git diff --cached --check -- review-team/references/finder-angles.md review-team/references/verifier.md review-team/references/report-contract.md review-team/tests/test_reporting_contract.py
git commit -m "docs(review-team): favor terse finding prose"
```

Expected: only the four named paths are staged and committed.

### Task 3: Update component entry points, route verification, and complete the repository handoff

**Files:**
- Modify: `review-team/README.md`
- Modify: `review-team/CLAUDE.md:72-96`
- Verify only: `review-team/AGENTS.md` (must remain `AGENTS.md -> CLAUDE.md`)
- Verify only: root `README.md`, `CLAUDE.md`, and `AGENTS.md` (no content change expected; `AGENTS.md -> CLAUDE.md`)

**Interfaces:**
- Consumes: the new component-owned reporting contract and existing documentation-entrypoint gate.
- Produces: a concise human explanation, durable maintainer rules and verification commands, preserved entrypoint symlinks, plus evidence that the live skill, packaging suite, links, and whitespace are sound.

- [ ] **Step 1: Update the component README**

In `review-team/README.md`, extend the short explanation of what a result means to state that every independently verified `CONFIRMED` or `PLAUSIBLE` survivor is surfaced, either directly or through an explicit same-root-cause merge. State that final reporting is exhaustive rather than numerically limited, while effort-level candidate ceilings still bound discovery. Add that reports favor terse prose without omitting the trigger, consequence, or verifier evidence. Keep this as a concise human entry point; do not copy the full runtime algorithm or numeric ceiling table into it.

- [ ] **Step 2: Update the component maintainer contract and verification route**

In the Synthesis and reporting section of `review-team/CLAUDE.md`, add the durable component rule:

```markdown
Final reporting is exhaustive and has no numeric output limit. Account for
every independently verified `CONFIRMED` or `PLAUSIBLE` survivor through a
rendered primary, a valid same-root-cause merge, or a fallback exact-duplicate
group. Preserve every distinct verifier-evidence item and favor terse,
evidence-complete fields.
```

Replace the statement that Review Team has no separate suite with:

````markdown
Review Team is instruction-only. Its focused static contract pins reporting
behavior, while the documentation parameters verify entry points and links:

```bash
python3 -m pytest \
  review-team/tests/test_reporting_contract.py \
  'tests/test_documentation.py::test_documentation_entrypoints[review-team]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[review-team]' -q
```
````

Keep this guidance at the component boundary; do not add Review Team behavioral claims to the root maintainer contract.

- [ ] **Step 3: Verify documentation ownership and entrypoint symlinks**

Run:

```bash
test -L AGENTS.md
test "$(readlink AGENTS.md)" = CLAUDE.md
test -L review-team/AGENTS.md
test "$(readlink review-team/AGENTS.md)" = CLAUDE.md
git ls-files -s AGENTS.md review-team/AGENTS.md
git diff --exit-code -- README.md CLAUDE.md AGENTS.md review-team/AGENTS.md
```

Expected: both `AGENTS.md` paths are tracked with mode `120000` and literal target `CLAUDE.md`; the root entry points and component symlink have no diff. Do not stage either symlink or any root Markdown file.

- [ ] **Step 4: Run the focused component gate**

Run:

```bash
python3 -m pytest \
  review-team/tests/test_reporting_contract.py \
  'tests/test_documentation.py::test_documentation_entrypoints[review-team]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[review-team]' -q
```

Expected: 8 tests pass.

- [ ] **Step 5: Audit live versus historical cap references**

Run:

```bash
rg -n "reportCap|Report cap|report cap|final cap|capacity remains|cap the report" \
  review-team/SKILL.md review-team/references review-team/README.md review-team/CLAUDE.md
```

Expected: no matches in live runtime or maintainer contracts. Do not use matches under `review-team/docs/` or `review-team/evals/` as a reason to rewrite historical records.

- [ ] **Step 6: Run cross-cutting verification from the repository root**

Run:

```bash
python3 -m pytest tests -q
python3 -m pytest review-team/tests/test_reporting_contract.py -q
git diff --check
git status --short
```

Expected: both pytest commands pass, `git diff --check` exits zero, and status lists only the intended `review-team/README.md` and `review-team/CLAUDE.md` changes remaining after Tasks 1 and 2.

- [ ] **Step 7: Review and commit the component entry points**

Run:

```bash
git add review-team/README.md review-team/CLAUDE.md
git diff --cached -- review-team/README.md review-team/CLAUDE.md
git diff --cached --check -- review-team/README.md review-team/CLAUDE.md
git commit -m "docs(review-team): describe exhaustive reporting"
git status --short --branch
```

Expected: the explicit diff matches this plan, the commit succeeds, and the feature worktree is clean on branch `review-team-refinements`.

- [ ] **Step 8: Perform the completion audit**

Confirm each requirement against authoritative current state:

1. `review-team/references/report-contract.md` contains no final numeric cap and declares `allVerifiedSurvivors`.
2. Synthesis accounts for every survivor or falls back. A semantic merge requires an explicit shared root cause, the same category and verdict, and byte-identical normalized `summary` and `failure_scenario` after trimming and collapsing internal whitespace; otherwise the records remain separate primaries. Every valid merge retains all affected locations and distinct verifier evidence.
3. After global correctness-before-Cleanup and `CONFIRMED`-before-`PLAUSIBLE` precedence, accepted primaries precede backfilled primaries within each category/verdict bucket; accepted primaries retain Synthesis severity order and backfilled primaries retain base order.
4. Fallback exact-duplicate groups partition all survivor IDs, retain distinct evidence, and emit every remaining representative.
5. `high` retains `48/0/48/48/96` and `xhigh` retains `80/8/88/88/176` in `initial/sweep/finderOutput/replacement/allRecords` order.
6. Finder, Verifier, and report contracts favor terse language without removing their evidence ladders.
7. Refutation visibility, no-survivor wording, survivor base ordering, read-only behavior, and failure policy remain unchanged.
8. Historical design and evaluation records remain unmodified.
9. `review-team/README.md` describes exhaustive, terse reporting and `review-team/CLAUDE.md` owns its maintainer invariant and verification route.
10. Root `README.md` and `CLAUDE.md` remain unchanged; root and Review Team `AGENTS.md` remain exact `CLAUDE.md` symlinks.
11. The five Task 1 contract checks, six complete reporting-contract checks, focused component gate, root test suite, and `git diff --check` have fresh passing output.
12. No user-scoped installation or remote state was changed.

Do not claim completion if any item lacks direct evidence.
