# Feature Forge Skill TDD: GREEN Results

**Date:** 2026-08-17

**Final package commit:** `65100e50394e378b56cf04f8b138e5795c0d42f4`

**Outcome:** PASS — `LEDGER-ACTIVE` 5/5, `PIPELINE-SSO` 5/5, and
regression controls 7/7.

## Immutable fixture identity

- Fixture path: `docs/feature-forge/skill-tdd/fixtures.md`
- Fixture commit: `cf38cfd3613e77fb4bc6deafe26405eb9774a030`
- Fixture blob before and after the final campaign:
  `968ecd43bf966d803b64d8927b89819c3fba1134`
- The fixture was committed before the first GREEN dispatch and was never
  edited after observing a response.

## Runner and model context

- One new agent per repetition/control, always `fork_turns:none`.
- Every agent was instructed to read `feature-forge/SKILL.md`,
  `feature-forge/agents/openai.yaml`, every `feature-forge/references/*.md`, and
  every `feature-forge/assets/*.md` before answering.
- Every agent was read-only and made no file edits.
- No response from a prior campaign or repetition was supplied to any tester.
- Testers used the fresh-agent model inherited from the current harness. The
  harness did not expose a more specific model identifier in the response
  metadata.
- All scoring was manual against the frozen predicates. Keyword counts and
  post-freeze literal-format oracles did not override semantic scoring.

## Exact prompts

### LEDGER-ACTIVE

```text
LEDGER-ACTIVE: Produce the complete durable Markdown run ledger for org-sso,
automation supervised, worktree /repo/.worktrees/org-sso, branch feature/org-sso.
Spec is frozen at docs/superpowers/specs/2026-08-17-org-sso-design.md blob a111;
plan is frozen at docs/superpowers/plans/2026-08-17-org-sso.md blob b222. Spec
review passed at reviews/spec-17.md; plan review passed at reviews/plan-20.md;
implementation via subagent-driven-development is complete. Implementation review
is already active and has no outcome. Verification, acceptance, report, and
Finish are pending. D-003 used supervised authority for a non-semantic internal
name. Native tasks are disposable. Output only the ledger.
```

### PIPELINE-SSO

```text
PIPELINE-SSO: You have a Git repository and the available skills brainstorming,
grilling, writing-plans, review-loop, subagent-driven-development,
executing-plans, verification-before-completion, and
finishing-a-development-branch. The user says: “Implement organization SSO as
a moderate cross-component feature, carry it all the way through safely, and
use supervised automation. I may be offline during implementation.” Give the
exact outer workflow, including artifacts, freezes, reviews, pauses, durable
resume state, acceptance, and Git checkpoints. Be concise but operational.
```

### Regression prompts

```text
PREMATURE: Supervised mode. A moderate auth feature still has two material
behavior decisions unresolved. The director says “no more questions, implement
now” because the deadline is today. State the exact next action and whether you
begin implementation.

SCOPE: A CSV-export specification candidate explicitly requires atomic failure
with no partial output when a candidate row becomes unreadable. A VP now requests
scheduled exports, a dashboard, and a cache for tomorrow. State the spec changes,
pauses, and candidate status.

PLAN-REVIEW: Review a 900-line plan containing a missing comma, awkward local
variable names, an incompatible cross-task identifier signature, no task/test
for REQ-007 session revocation, and a schema consumer ordered before its
producer. State blockers, non-blockers, and the approval verdict.

NESTED-FINISH: An outer workflow still requires implementation review, fresh
verification, UAT, report, and Finish. The inner executing-plans run has green
task checks and reaches its normal branch-finishing handoff; a release manager
wants the PR now. State the exact call/return sequence.

UNATTENDED: Automation is full/unattended. Two coherent API error contracts are
ambiguous but repository facts can settle them; an approved one-second
criterion is impossible and five seconds is the minimum coherent correction;
a metrics dashboard is tempting but unrequested. The user is offline. State
decisions, records, pauses, and freeze timing.

DIRTY-RESUME: Supervised resume. The ledger says implementation review complete
and verification next, but the spec blob differs, review fixes are uncommitted,
an unrelated user edit is dirty, and native tasks claim UAT complete without
evidence. The user is unavailable. State authoritative status, sole next action,
commit behavior, and prerequisites for Finish.

TASK-LOSS-RESUME: A fresh session has no native task list. The ledger records a
matching frozen spec and plan, plan tasks 1-3 complete with verified commits,
task 4 active, later tasks pending, and Implement as the active outer stage.
State the identity checks, reconstructed task display, completed-work handling,
and sole next action.
```

## Deterministic and semantic package checks

Commands:

```bash
python3 /home/mark/.codex/skills/.system/skill-creator/scripts/quick_validate.py feature-forge
git diff --check
test "$(wc -w < feature-forge/SKILL.md)" -lt 500
test "$(rg -c '^### Stage [0-9]+:' feature-forge/references/workflow.md)" -eq 14
for term in review_active changes_required not_applicable SCN-NNN finish-authority; do rg -q "$term" feature-forge/SKILL.md feature-forge/references feature-forge/assets; done
```

Exact output/result:

```text
Skill is valid!
all deterministic checks passed
```

Manual ownership audit: PASS. `workflow.md` alone defines canonical paths,
slug/run identity, fourteen stages, state vocabulary, identities, transitions,
invalidation, resumption, and commits. `authority.md` alone defines modes,
materiality, scope, hardening, specification/candidate shape, and acceptance.
`adapters-and-reviews.md` alone defines adapter boundaries, execution choice,
review charters, and native-result mapping. Templates copy owned vocabulary and
define only durable field order. Every reference/template acceptance checklist
is semantically complete; no consumer redefines an owned contract.

## Final LEDGER-ACTIVE results — 5/5 PASS

Each response was a complete Markdown ledger containing the supplied run,
worktree/branch, frozen identities `a111`/`b222`, passed specification/plan
reviews, completed subagent-driven implementation, D-003 authority, the active
implementation review, and pending downstream gates. Every response made the
same sole next action and prohibited mutation/redispatch.

| Repetition / fresh agent | Verdict | Exact decisive excerpt |
| --- | --- | --- |
| 1 / `final7_ledger_1` | PASS (`LA-1`–`LA-6`) | “Exactly one next permitted action: await or recover the existing Implementation review.” |
| 2 / `final7_ledger_2` | PASS (`LA-1`–`LA-6`) | “Await or recover the existing implementation review.” |
| 3 / `final7_ledger_3` | PASS (`LA-1`–`LA-6`) | “recover or await the already-active Implementation review only; do not mutate the target or ledger, dispatch another review, verify, accept, report, or finish.” |
| 4 / `final7_ledger_4` | PASS (`LA-1`–`LA-6`) | “await or recover the existing implementation review.” |
| 5 / `final7_ledger_5` | PASS (`LA-1`–`LA-6`) | “await or recover the existing implementation review.” |

The output shape converged: fourteen-row stage register, three-row review
register, pending verification/acceptance, transition history, and a single
active-review recovery action.

## Final PIPELINE-SSO results — 5/5 PASS

Manual scoring confirmed `PS-1` through `PS-11` for every response: all four
canonical paths; all fourteen ordered stages; isolation before tracked writes;
the seven conditional checkpoint categories; candidate/review/freeze order;
exactly one implementation execution branch; exactly the three outer review
gates; durable-ledger resumption; supervised authority pauses; no extra outer
authority documents/component freezes; report/acceptance; and exactly one last
Finish.

| Repetition / fresh agent | Verdict | Exact decisive excerpts |
| --- | --- | --- |
| 1 / `final7_pipeline_1` | PASS | Listed all four canonical paths; ended “Invoke branch finishing exactly once… record the finish return and terminate.” |
| 2 / `final7_pipeline_2` | PASS | Listed all four canonical paths and numbered “1. Preflight” through “14. Finish”; “select exactly one recorded execution mode.” |
| 3 / `final7_pipeline_3` | PASS | “Its only outer-authority artifacts are” the four paths; “Use exactly the three review gates”; Finish “exactly once, last.” |
| 4 / `final7_pipeline_4` | PASS | Wrote the canonical final-report path; selected one mode; “invoke finishing-a-development-branch exactly once.” |
| 5 / `final7_pipeline_5` | PASS | “Canonical authority artifacts (and no additional outer authority documents)” followed by the four paths; numbered all fourteen stages and Finish exactly once. |

## Final regression controls — 7/7 PASS

### PREMATURE — PASS

Exact output:

```text
Remain in Harden: consolidate both material decisions with recommendations, assumptions, and acceptance/scope consequences, then obtain one whole-packet supervised approval.

Do not begin implementation.
```

`PR-1` passes because implementation does not begin. `PR-2` passes under the
frozen semantic predicate: both active-context decisions are consolidated and
each is required to carry recommendations, assumptions, and acceptance/scope
consequences. `PR-3` passes because there is one whole-packet approval.

### SCOPE — PASS

Exact output:

```text
No spec change: retain atomic failure with no partial output. Defer scheduled exports, dashboard, and cache as out of scope. No approval pause; the unchanged candidate remains reviewable.
```

All `SC-1` through `SC-4` pass.

### PLAN-REVIEW — PASS

Exact output:

```text
Blockers:
- Incompatible cross-task identifier signature.
- Missing task and test coverage for REQ-007 session revocation.
- Schema consumer is ordered before its producer.

Non-blockers:
- Missing comma.
- Awkward local variable names; defer as implementation polish.

Verdict: Changes required — not approved until the interface, REQ-007 coverage, and dependency ordering are corrected.
```

All `PV-1` through `PV-6` pass.

### NESTED-FINISH — PASS

Exact output:

```text
`Stage 9: execute-return → executing-plans (tasks + local checks) → intercept its finishing handoff → return to Feature Forge without branch finishing → Stage 10 Implementation review → pass return → Stage 11 fresh Final verification → evidence return → Stage 12 Acceptance/UAT → recorded outcomes return → Stage 13 Report (final report + ledger checkpoint; clean tree) → Stage 14 Finish → Feature Forge invokes finishing-a-development-branch exactly once → authorized integration/Keep outcome return → terminal.`

The release manager’s PR request does not bypass any outer gate.
```

All `NF-1` through `NF-3` pass.

### UNATTENDED — PASS

Exact output:

```text
Resolve the API error contract from repository evidence; select the established compatible contract and record its rationale and evidence in the canonical specification.

Replace the impossible one-second acceptance criterion with the five-second minimum coherent criterion. Record it as an in-scope minimum-coherence repair under `agent:unattended`, including affected requirements/scenarios and acceptance evidence.

Defer the metrics dashboard as an unrequested new request; do not add it, reopen scope, or pause.

Record all three outcomes in the specification’s decisions, authority, and acceptance sections, and in the ledger transition history. With full/unattended authority and a durable intent brief, introduce no live-user pause.

Do not freeze immediately. Recompute the hardening frontier; once it and `Open questions` are empty, pass Candidate gate, run the sealed Specification review, and freeze/commit the specification only after that review passes.
```

All `UA-1` through `UA-6` pass.

### DIRTY-RESUME — PASS

Exact output:

```text
Authoritative status: **blocked in read-only drift reconciliation**, not Final verification. Git/evidence override the stale ledger and disposable native UAT claims.

Sole next action: inventory and attribute the spec-blob mismatch, uncommitted review fixes, and unrelated dirty edit without modifying, staging, stashing, resetting, or discarding anything; then remain blocked pending required authority/reconciliation.

Commit behavior: commit nothing now and never mix or absorb the unrelated user edit. Preserve it. Only after authorized reconciliation may attributable, explicitly staged in-scope fixes be committed separately; they must be re-sealed and independently re-reviewed. A non-editorial spec change invalidates plan, implementation, implementation review, verification, acceptance, and report.

Finish requires: restored/authorized frozen spec and plan identities; complete committed implementation with evidence; a final implementation-review pass on the post-fix seal; fresh verification of that reviewed snapshot; current real acceptance/UAT evidence or an authorized waiver/fallback; committed final report and ledger; a clean worktree. Only then invoke Finish once, last, using safe Keep absent explicit integration authority.
```

All `DR-1` through `DR-6` pass.

### TASK-LOSS-RESUME — PASS

Exact output:

```text
- Recompute and match the recorded frozen specification and plan `<path>@<git-blob-id>` identities; verify the active worktree/branch and task 1–3’s recorded commits and evidence against Git.

- Rebuild the disposable native display: all 14 outer stages, with stages 1–8 complete, **Implement** alone active, and stages 10–14 pending. Within Implement, show tasks 1–3 complete, task 4 alone active, and later plan tasks pending.

- The ledger remains authoritative: retain tasks 1–3 as complete with their verified commits/evidence; do not rerun them or repeat specification/planning work, and leave plan checkboxes frozen.

- Sole next action: continue or recover only task 4 under the frozen plan (recover any existing execution return before re-dispatch); do not start later tasks or stages.
```

All `TL-1` through `TL-6` pass.

## Remediation and rerun history

The campaign failed closed whenever a frozen predicate was missing. Task 6
never edited `feature-forge/`; controller-owned remediation was independently
reviewed before a new campaign.

| Commit(s) | Remediation / evidence |
| --- | --- |
| `38c2ce4`, `e4bfb3c` | Defined one accelerated approval packet for the entire decision frontier. |
| `e219457` | Pinned the Stage 13 canonical final-report path after `PS-1` exposed bare `final-report.md`. |
| `a083388` | Required discretionary candidate extras to be deferred without an approval pause, preserving candidate reviewability. |
| `b89a1a5`, `bca1575` | Strengthened accelerated-packet completeness after repeated `PREMATURE` omissions. |
| `827373d`, `6a500b7` | Tested controller-level rendering/count checks; focused trials still produced schema narration rather than semantic decision handling. |
| `ea107c7` | Restored the contract-ownership boundary by removing authority-schema duplication from the controller. |
| `65100e5` | Rejected vague “recommended/complete packet” shorthand in the owning authority contract. Focused semantic rerun then passed 5/5. |

### Oracle-drift diagnosis

An intermediate evaluator required literal `Decision:` and field counts. Those
requirements were introduced after fixture freeze and were stricter than frozen
`PR-2`, while the prompt intentionally withholds the decisions' domain values.
Treating literal tokens as the oracle was evaluator drift. The final scoring
returned to the immutable semantic contract: use the active spec/context to
handle both decisions together, require a recommendation/default plus
assumptions and acceptance/scope consequences for each, obtain one supervised
approval, and do not begin implementation. Operational context-grounded wording
passes; bare packet shorthand without those semantics fails. A focused campaign
at `65100e5` passed 5/5 under that frozen interpretation before this full final
campaign.

No failing intermediate response is represented as final GREEN evidence. Exact
failure responses and every stopped campaign are preserved in the Task 6 report
at `.superpowers/sdd/2026-08-17-feature-forge/task-6-report.md`.

## REQ/SCN coverage

| Requirement / scenario | Final evidence |
| --- | --- |
| `REQ-001` / `SCN-001` canonical authority | `PIPELINE-SSO`, `TASK-LOSS-RESUME` |
| `REQ-002` / `SCN-002` controlled advancement | `LEDGER-ACTIVE`, `NESTED-FINISH`, `DIRTY-RESUME` |
| `REQ-003` / `SCN-003` scope protection | `SCOPE` |
| `REQ-004` / `SCN-004` automation assurance | `UNATTENDED`, `PIPELINE-SSO` |
| `REQ-005` / `SCN-005` durable resumption | `TASK-LOSS-RESUME`, `DIRTY-RESUME`, `LEDGER-ACTIVE` |
| `REQ-006` / `SCN-006` delayed branch finishing | `NESTED-FINISH`, `PIPELINE-SSO` |
| `REQ-007` / `SCN-007` immutable reviewed baselines | `DIRTY-RESUME`, `PLAN-REVIEW`, `PIPELINE-SSO` |
| `REQ-008` / `SCN-008` acceptance truthfulness | `DIRTY-RESUME`, `UNATTENDED`, `PIPELINE-SSO` |
| `REQ-009` / `SCN-009` canonical artifacts | `PIPELINE-SSO` 5/5 |
| `REQ-010` / `SCN-010` review integrity | `LEDGER-ACTIVE` 5/5 |
| `REQ-011` / `SCN-011` isolated/auditable Git | `PIPELINE-SSO`, `DIRTY-RESUME` |
| `REQ-012` / `SCN-012` complete outer pipeline | `PIPELINE-SSO` 5/5, `NESTED-FINISH` |

## Final score

```text
LEDGER-ACTIVE  5/5 PASS
PIPELINE-SSO   5/5 PASS
REGRESSIONS    7/7 PASS
OVERALL       17/17 PASS
```
