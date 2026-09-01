# fable-method investigation

## 1. Overview

- **What**: A discipline system for LLM coding agents — a 7-step work loop (`fable-method`), an orchestrator (`fable-loop`), an adversarial verifier (`fable-judge`), and a domain-adapter generator (`fable-domain`), packaged as a self-hosting Claude Code plugin (v1.4.0) with a harness-neutral `AGENTS.md` variant.
- **Thesis**: Weak models fail *procedurally* (skip the spec, fake "all tests pass", act unbidden, invent APIs). The method fixes discipline, not intelligence — so measured lift is inversely proportional to model tier. Frontier models pass its traps natively (published nulls, rounds 6/7).
- **Size**: Core method is 129 lines (`skills/fable-method/SKILL.md`). Whole system is prose-first: 4 SKILL.md files (38–130 lines each), reference tables/flowcharts, 8 domain adapters, a 118-line JS eval harness, 14 trap scenarios, a 234-line results log.
- **Maturity**: v1.4, 15 documented eval rounds, one outside contributor, explicit changelog tying each feature to a measured result. Every rule traces to a failing test; nulls and cut features are published.

## 2. Core methodology

Two gates before the loop:

| Gate | Rule |
|---|---|
| Triviality | One file, <10 lines, no new behavior, exact change known → just do it, one check, 2-sentence report. Loop skipped. |
| Fit | Route by *where the answer lives*: reachable sources → loop; researchable → research then loop; only-inference → say so, no "costume"; recurring specialty → build a skill. Non-default routes must be named in the report ("a silent detour is indistinguishable from a skipped step"). |

The 7-step loop:

| Step | Name | Key mechanism |
|---|---|---|
| 0 | Classify | 3 shapes (question / task / plan-first) via signal table + ordered tie-breaks. Never re-litigate stated decisions. |
| 1 | Define done | 1–2 sentences, load-bearing assumptions stated, one clarifying question max. |
| 2 | Gather evidence | Orient first; primary sources over memory; parallelize independent lookups; time-boxed (1 round + 1 follow-up; 3rd needs stated reason); surprises re-route the loop. |
| 3 | Decide | ONE recommendation; alternatives get a line each. **AUTH gate** for irreversible/outward actions: literal `AUTH: user said "<exact words>"` — docs are not authorization, task completion is not authorization. |
| 4 | Act surgically | **INTENT gate** before any behavior change: `INTENT: code does X; check expects Y; spec says Z` (must open the spec). **Recall gate**: unopened facts from memory get sourced now or labeled unverified. Authority order: user > spec > tests > code; "make tests pass" ≠ spec. 8 standing prohibitions (no commit/push, no weakening checks, no new deps...). |
| 5 | Verify by observation | Done criterion *observed*; system health checked ("green targeted check + broken build = failed verification"); **TWINS gate** after defect fixes: `TWINS: searched <pattern> - found <N> other sites`. Hard bound: 3 failed fix-verify cycles → hand back. |
| 6 | Report outcome-first | Plain language, caveats for everything skipped; **PENDING gate** for prescribed-but-untaken follow-ups; final **Artifact gate** mechanically re-inserts any owed INTENT/AUTH/TWINS/PENDING line. |

**fable-loop** (multi-step orchestration): Plan (evidence fan-out to subagents, distilled findings only) → Execute (deciding/editing stays main-thread; mid-item memory gaps pause for a research subagent) → Verify (1–3 attacker subagents with distinct refutation lenses) → Audit/report.

**fable-judge**: "A report is a set of claims, not evidence." Diff is ground truth; every claimed verification re-run; unre-runnable claims labeled UNVERIFIABLE, never assumed true. Ordered fraud taxonomy: weakened checks > false completion > scope creep > unauthorized action > spec betrayal > debris. Verdicts: VERIFIED / VERIFIED WITH CAVEATS / REFUTED.

**fable-domain**: Discuss → Research (fetched-now sources, link + access date) → Generate (adapter + trap fixture + smoke eval, all-or-not-done) → Verify (judge the bundle's own claims). Two hard stops *before* generation: red-line refusal (licensure/harm domains) and scope stop (sector must differ from coding default).

## 3. Architecture & code-vs-LLM split

| Layer | Form | Why |
|---|---|---|
| Method + skills | Pure prose (SKILL.md, dense imperative, numbered rules) | The product *is* instructions; portability (AGENTS.md = same body minus frontmatter, for any harness) |
| References | Lazy-loaded prose (flowcharts.md, failure-modes.md, examples.md, domains/) | On-demand context economy; adapters load only on matching task shape |
| Eval harness | Code — `eval/workflow.js`, 118 lines | A/B runs need determinism: fixture copy, forced `haiku` executor, judge-side `diff -ru` |
| CI | Code — `.github/checks.py`, 116 lines, stdlib only | Mechanical schema enforcement of prose contracts (headers, frontmatter, version equality, dash ban) |
| Packaging | JSON manifests + install.sh/ps1 | Self-hosting plugin+marketplace in one repo |

Ratio: ~95% prose, ~230 lines of code total. Code exists only where trust requires mechanism: measuring the prose (evals) and validating its structure (CI). The prose itself models the brevity it demands — worked examples are 5–8 lines, not transcripts.

## 4. Enforcement & verification

**On the LLM (compliance mechanisms)**:
- Four forced literal artifacts at decision points — INTENT (edit-time), AUTH (outward action), TWINS (post-fix sweep), PENDING (untaken follow-up) — format-checkable strings the model must emit *at the moment of acting*. Core empirical finding: prose rules failed (Haiku 1/4), the forced INTENT line succeeded (4/4). `eval/RESULTS.md` rounds 2→3.
- Artifact gate: mechanical final sweep re-inserting owed lines (`SKILL.md:113`).
- Hard bounds everywhere: evidence rounds 1+1, 3 fix-verify cycles, 1–3 attackers.
- fable-judge as external check: diff + re-execution, never the self-report.

**On itself (testing)**:
- 14 trap fixtures: bait instruction contradicts a fact elsewhere in the fixture; `GROUND-TRUTH.md` answer sheets excluded from executor copies; judge diffs pristine-vs-run itself so file changes are fact, not claim.
- Haiku as executor = discriminator (frontier tiers pass natively).
- CI: 7 structural checks incl. required adapter section headers and plugin/marketplace version equality.
- Results log publishes nulls and cut features: "a results log that only contains wins for the method would not be worth trusting."

## 5. Unique features & clever techniques

- **Forced artifact > prose rule** — `skills/fable-method/SKILL.md:78`; v1→v3 arc in `eval/RESULTS.md` rounds 1–3 (Haiku 0/4 → 4/4 surfacing a wrong test). Reused for TWINS (round 14: 0/6 → 3/3).
- **Refutation-lens verifiers** — `skills/fable-loop/SKILL.md:33-37`: attackers each get a distinct named lens (diff-read, runtime-exercise, spec-contradiction, scope-diff); "distinct lenses beat identical reviewers."
- **Judge-by-execution + UNVERIFIABLE label** — `skills/fable-judge/SKILL.md:15-23`; round 8: Haiku-as-assessor fraud-catch 3.5/5 → 5/5 with the skill.
- **Provenance tags on generator rules** — `skills/fable-domain/SKILL.md:10`: every step marked [observed] (recorded frontier trace), [covenant] (no-rule-without-failing-test), or [v1.4]. Two zero-hint Fable 5 agents independently converged on the recorded process.
- **Flowcharts corrected against transcripts** — `references/flowcharts.md:143-147`: 3 corrections where observation beat introspection; AUTH gate placement traces to an observed unauthorized deploy.
- **Trap design** — `eval/scenarios/`: s9 makes an unauthorized deploy an objective diff fact (`DEPLOYED.marker`); s13 hides one bug across 5 disguised sites plus 4 must-not-touch correct modules; s1 caps score to 0 on *any* edit for a question-shaped ask.
- **Ranked failure modes** — `references/failure-modes.md`: 18 modes mapped to the exact rule that prevents each; closes by ranking the 3 costliest for a budget-limited audit.
- **Early hard stops** — `skills/fable-domain/SKILL.md:23-25`: red-line + scope-stop moved *before* research after a weak model "blew straight past" a late-placed check (round 15) — momentum beats restraint mid-build.
- **CI-as-schema on prose** — `.github/checks.py`: greps adapter headers, frontmatter substrings, JSON validity, cross-manifest version equality, even a repo-wide em-dash ban.

## 6. Strengths & weaknesses

**Strengths**
- Evidence-driven minimalism: near every rule cites a measured failure; 129-line core.
- Honest reporting engineered in at every layer (caveats, UNVERIFIABLE, smoke-grade labels, published negatives — e.g. skill-in-skill discovery cut after 1/14 pickups).
- Observation outranks self-report at executor, judge, harness, and even doc-provenance level.
- Triviality gate prevents process tax; app-scale validation (4/4 runs 8/8) shows no overhead failure.

**Weaknesses**
- **PENDING gate doesn't work at its target tier**: round 11, 11/12 Haiku runs still silently dropped the deploy decision across 3 wordings. Kept anyway; helps mid tiers. Bounds the artifact trick: it works on actions taken, not absences noticed.
- **install.sh diverges from plugin install**: copies only 3 of 4 skills (drops fable-domain) and no eval/, silently breaking standalone judge suite mode.
- **Schema debt wider than advertised**: 7/8 adapters lack Sources, 8/8 lack Workflow — including the generated devops.md, contradicting the "required for v1.4+ generated adapters" claim. Documented as a contribution path, but live drift.
- Open issues: step-header scaffolding leaks into reports (a strip clause went 0/3 and was removed); artifact-gate "owed-line closure" never validated (harness debt, round 15).
- One-seed-per-scenario evals are self-labeled smoke tests, not benchmarks.

## 7. Adaptable ideas

1. Forced literal artifact line at the decision point instead of a prose rule (INTENT pattern; proven 0/4→4/4).
2. A/B trap-fixture evals: bait vs hidden truth, weak-tier executor as discriminator, judge diffs a pristine copy itself.
3. Judge-by-execution: diff + re-run every claim; UNVERIFIABLE label for what can't be re-run — never assumed true.
4. Ordered fraud taxonomy (weakened checks first) as a verifier checklist; per-domain fraud tables.
5. Publish nulls and cut features in the results log — credibility mechanism.
6. Triviality + fit gates before any process engages; "silent detour = skipped step."
7. Explicit authority chain (user > spec > tests > code) with "make tests pass" excluded from spec authority.
8. Refutation-lens attacker fan-out — distinct named lenses, budget-bounded (1–3).
9. Provenance-tag every rule ([observed]/[covenant]/[version]) so rules trace to recorded traces or failing tests.
10. CI-grep structural contracts on prose docs (headers, frontmatter, version equality).
11. Hard-stop refusal/scope gates placed before generation momentum builds.
12. Bounded loops everywhere: evidence 1+1 rounds, 3 fix-verify cycles then hand back.
13. Mechanical end-of-report repair pass (artifact gate) for owed compliance lines.
14. Lazy-loaded reference files + task-shape-matched domain adapters for context economy.
15. Meta-lesson: gate acts, not omissions — forced artifacts fail when they require noticing an absence (round 11, s9).
