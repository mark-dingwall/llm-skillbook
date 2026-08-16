# Feature Forge

**Status:** Frozen specification baseline

**Date:** 2026-08-17

## 1. Purpose and authority

Feature Forge is a Git-only skill for delivering a bounded feature, migration,
refactor, or comparable work unit whose ambiguity, risk, or cross-component
scope warrants explicit specification, independent review, planning,
implementation, and acceptance.

This document is written for a skill author who has the repository but none of
the design conversation. After reading it, that author should be able to test
and implement the MVP without reopening settled product decisions.

It preserves the Superpowers specification-to-plan-to-code artifact formats and
delegates to existing skills where their contracts fit. It adds specification
hardening, controlled scope freezes, stage-specific review, durable
coarse-grained workflow state, explicit acceptance, and delayed branch
finishing.

The MVP does not build a workflow engine. A frontier LLM owns orchestration and
semantic judgment. Harness-native task tools provide the live task view. A
tracked Markdown ledger provides durable stage and evidence state. Git provides
artifact identity and recovery checkpoints.

## 2. Goals and non-goals

### Goals

- Turn an initially ambiguous work unit into one reviewed, testable, frozen
  specification.
- Produce a reviewed implementation plan that is faithful to the frozen
  specification and safe for context-isolated workers.
- Execute the plan using the best available Superpowers execution skill.
- Prevent discretionary scope growth after initial user decisions are complete.
- Preserve decisions, assumptions, approvals, review outcomes, baselines, and
  acceptance evidence across context compaction or a new session.
- Delay branch completion until implementation review, verification, and
  acceptance are complete.
- Keep the ordinary user experience to one skill invocation plus questions that
  genuinely require the user's authority.

### Non-goals

- A general workflow DSL, daemon, scheduler, database, event-sourced engine, or
  programmatic agent runner.
- A Node, Python, YAML-parser, or third-party runtime dependency.
- OpenSpec CLI integration, change directories, synchronization, or archival.
- Non-Git repositories.
- Replacing the participating Superpowers skills or `review-loop`.
- Automatically deploying, publishing, merging, or performing destructive or
  externally consequential operations beyond existing user and platform
  authority.
- Maintaining separate ADR and glossary files solely for Feature Forge.

## 3. Invocation and discovery

The skill name is `feature-forge`.

The MVP deliverable contains `SKILL.md`, concise workflow/reference material,
and reusable ledger and final-report templates. It contains no runtime script.

Its trigger must describe only when to use it, not summarize its workflow. The
intended trigger is a bounded feature or comparable multi-step work unit whose
size, ambiguity, risk, or cross-component coordination warrants specification,
planning, independent review, and acceptance. Trivial mechanical edits remain
outside the skill.

The invocation may include an automation mode:

```text
Use feature-forge to add organization-level SSO. Automation: supervised.
```

When the user omits the mode, `supervised` is the default.

## 4. Execution architecture

Feature Forge is the sole outer controller. It creates or updates the harness's
native task list with the workflow stages, permits only one active stage, and
rehydrates that list from the run ledger when resuming.

When native tasks are available, use them as a best-effort display of the
fourteen stages in Section 10, with at most one active item. Providers may use
their own status vocabulary and may summarize blocked or invalidated state in
annotations. When native tasks are absent, the workflow is unchanged. Native
task state never enforces or advances independently of the durable ledger.

The controller delegates semantic work as follows:

- `superpowers:brainstorming` creates the initial design/specification.
- A Feature Forge-native hardening interview applies the design-tree and
  frontier-round method derived from `grilling`.
- `review-loop` challenges the specification, plan, and implementation under
  three different charters.
- `superpowers:writing-plans` creates the implementation plan.
- `superpowers:subagent-driven-development` is preferred for implementation;
  `superpowers:executing-plans` is the inline fallback.
- `superpowers:finishing-a-development-branch` runs only after final review,
  verification, acceptance, and reporting.

Feature Forge must not invoke `executing-plans` as its outer workflow engine.
That skill has no parent/child plan stack or return-before-finish contract and
would recursively invoke itself when selected for implementation.

### Sub-skill return boundaries

Feature Forge explicitly regains control at these boundaries:

1. Brainstorming returns after the written specification and its self-review;
   it does not invoke `writing-plans`.
2. Writing Plans returns after plan creation and self-review; it does not offer
   or begin execution.
3. The selected execution skill returns after all implementation tasks and
   their local verification; it does not invoke branch finishing.
4. Branch finishing is invoked exactly once, by Feature Forge, at the terminal
   stage.

These are caller-owned adapter boundaries, not requests to alter the installed
subskills. Feature Forge supplies four named adapter contracts:

- `brainstorm-return`: in interactive/supervised mode, perform the complete
  brainstorming method and its user approval gates, then return the approved
  specification instead of invoking Writing Plans. In unattended mode, replace
  only those synchronous approval gates with a recorded `agent:unattended`
  intent/design decision and independent self-review under the invocation's
  standing authority; retain the rest of the method and return boundary;
- `plan-return`: perform the complete Writing Plans method, including its
  required header and self-review, then return the plan instead of offering or
  beginning execution; and
- `execute-return`: perform the selected execution skill's complete task and
  local-review method, then return the implementation result instead of
  invoking branch finishing or deleting caller-owned progress state; and
- `finish-authority`: in interactive/supervised mode, perform the complete
  branch-finishing method including its integration menu. In unattended mode,
  retain its verification and environment checks but replace the synchronous
  menu with the invocation's pre-authorized outcome, defaulting to its
  non-destructive Keep option; never infer push, merge, deploy, publish, or
  cleanup authority.

Each adapter replaces only the deviations explicitly enumerated in its named
contract. If the harness cannot enforce that contract, Feature Forge blocks
before invocation rather than allowing a duplicate or premature transition.
The package documents the exact adapter prompts as part of the MVP.

## 5. Canonical artifacts

The canonical specification and plan retain the existing Superpowers paths:

```text
docs/superpowers/specs/YYYY-MM-DD-<work-unit>-design.md
docs/superpowers/plans/YYYY-MM-DD-<work-unit>.md
```

Feature Forge owns a separate tracked namespace:

```text
docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/
├── ledger.md
└── final-report.md
```

`<work-unit>` is one deterministic slug used in all paths, the run identifier,
and `feature/<work-unit>` branch: lowercase ASCII letters and digits separated
by single hyphens, beginning and ending alphanumeric. Reject separators,
traversal segments, whitespace, leading dashes, and invalid Git-ref content
rather than sanitizing ambiguously.

The ledger is the durable source of coarse workflow state. Harness-native
tasks are a disposable projection. The specification is the semantic source of
requirements and decisions. The plan is the source of implementation tasks.
The ledger links to those documents; it does not duplicate their prose.

`review-loop` artifacts must remain outside the target tree sealed at dispatch,
as required by that skill. Feature Forge calls it with the exact subject,
ground-truth artifacts, stage charter, and completion criterion. It preserves
both native verdicts, the stable report reference, and the content seal, then
maps the return as follows:

| Native result | Feature Forge gate |
|---|---|
| `CONVERGED` and merge-ready | `pass` |
| Actionable open findings with a viable fix path | `changes_required` |
| `INDETERMINATE`, not converged without a viable fix, missing authority, or unavailable reviewer capability | `blocked` |
| `CONVERGED` but not merge-ready | `blocked` with the named blocker |

Feature Forge records the mapped result after the loop returns. It sets
`review_active` before dispatch and does not mutate the target or ledger while
the loop is active.

## 6. Specification contract

The specification is one canonical document so `writing-plans` and context-
isolated workers receive one complete authority source. It uses the ordinary
Superpowers design layout, enhanced by EARS-like and OpenSpec-inspired content
discipline.

It contains:

1. Intent and authority
2. Goals and non-goals
3. Observable requirements and scenarios
4. Architecture, components, and data flow
5. Interfaces, contracts, and invariants
6. Domain language
7. Decisions and rationale
8. Assumptions and delegated decisions
9. Error handling
10. Test strategy
11. Open questions

The acceptance portion classifies each requirement's acceptance method as
`automated`, `UAT`, or `not_applicable`. A UAT entry names the participant and
observable exercise plus an unattended automated substitute and its evidence
criterion. If no adequate substitute exists, unattended mode blocks rather
than weakening acceptance. `not_applicable` includes a rationale. Run-time UAT
state is `pending`, `approved`, `rejected`, `infeasible`, or `waived`, with
authority and evidence. `rejected` returns to defect classification;
`infeasible` blocks unless the user waives or changes the method. Only the user
can waive otherwise-applicable UAT; unattended mode records the invocation's
standing automation authority as the waiver and never as human approval.

Each normative feature requirement in a work-unit specification has a stable
`REQ-NNN` identifier, expresses one observable behavior with one `SHALL` or
`MUST`, and includes concrete GIVEN/WHEN/THEN scenarios for important success,
edge, and error cases. The specification keeps behavior separate from
implementation mechanics. This rule describes specifications produced by
Feature Forge; Sections 3–15 of this design are the Feature Forge workflow
contract, with core conformance risks summarized in Section 16.

Material decisions and assumptions record their authority as `user` or
`agent:<automation-mode>`. Ordinary answers are integrated into the appropriate
requirement or design section rather than preserved as conversational history.
`Open questions` must be empty before specification review begins.

The specification's Intent and authority section is the durable intent brief.
It records the user's requested outcome, constraints, exclusions, automation
authority, and any linked external authority needed to review faithfulness
after conversational context is lost.

## 7. Specification hardening

The hardening interview preserves the core `grilling` algorithm rather than
inventing an unrelated questioning method:

1. Model unresolved decisions as a design tree.
2. Treat a decision's settled prerequisites as the condition for joining the
   current frontier.
3. Resolve discoverable facts instead of asking the user. Use deterministic
   tools for direct facts and delegate only broad or ambiguous investigation.
4. Ask the whole frontier in one numbered round. Give a recommended answer for
   every question.
5. Incorporate each settled answer into the specification immediately.
6. Recompute the tree after every round because answers may add, remove, or
   reshape downstream branches.
7. Continue until the frontier is empty and no material decision remains
   silently assumed.

If the user asks for no more questions, fewer questions, immediate
implementation, or equivalent acceleration, the controller consolidates the
remaining frontier into explicit assumptions and decisions. In interactive or
supervised mode it presents that record for one approval before continuing. In
unattended mode it records the resolutions and continues without pausing.

## 8. Automation authority

Feature Forge supports three modes:

### Interactive (`none` alias)

Pause for nontrivial assumptions, meaningful decisions, material review
changes, execution-mode selection, and user acceptance.

### Supervised (`default` alias and default mode)

Make and record minor assumptions, correct non-semantic defects, make
non-material adjustments needed to express already-approved requirements
coherently, and choose the execution mode. Pause for changes to goals,
non-goals, observable behavior, acceptance criteria, compatibility, scope, or
material architecture. Follow the specification's acceptance classification;
pause when it declares UAT.

### Unattended (`full` alias)

Make and record in-scope product and technical decisions, including
defect-driven scope corrections necessary to honor the work unit's intent.
Choose the execution mode and perform automated acceptance without synchronous
UAT. Still stop for missing authority, unavailable credentials or systems,
unsafe or irreversible operations, fundamental intent changes, or genuinely
irresolvable contradictions.

At Finish, execute a pre-authorized integration outcome when the invocation
names one. Otherwise choose the non-destructive “keep the branch/worktree”
outcome and report it; unattended authority alone never implies merge, push,
deployment, publication, or cleanup permission.

Automation controls who may settle a decision. It never weakens specification,
review, verification, acceptance-evidence, or completion gates and never
overrides platform safety or permission requirements.

A decision is **material** when it changes a goal or non-goal, observable
behavior, acceptance criterion, compatibility promise, public or cross-task
interface/invariant, security or data posture, scope, or major architecture. A
decision is **minor** only when it is local, reversible, and preserves all of
those properties. A change is **in scope** only when an approved requirement
needs it or it is the minimum correction for a blocking defect. When uncertain,
classify upward and apply the stricter authority rule.

## 9. Scope and change control

After hardening finishes, the document becomes a **specification candidate**:
initial user decision-making is complete. Until review passes, changes must be
driven by a defect, contradiction, ambiguity, infeasibility, missing
requirement, or inability to test—not discretionary improvement.

Editorial and non-semantic corrections are automatic. Material changes follow
the selected automation policy. Scope expansion is permitted only when needed
to resolve a blocking defect and must remain the minimum change that honors the
work unit's intent.

After specification review passes, its committed content identity becomes the
**frozen specification baseline**. Planning and implementation must not change
it. A later-discovered specification defect creates an explicit change request
and returns to the minimum necessary specification stage. After amendment, the
affected specification and downstream artifacts are reviewed and re-frozen.

Change classification is recorded as one of: `editorial`, `plan-only defect`,
`implementation defect`, `specification defect`, or `new request`. Every change
invalidates the content identity and applicable review evidence for the changed
artifact; editorial corrections need only a scoped delta review and do not
require user approval. Other changes invalidate dependent artifacts as their
contracts require. A new request is deferred unless the user explicitly
expands the work unit.

An editorial amendment enters `invalidated`, receives a scoped delta review,
is committed, and replaces the frozen blob identity in the ledger before any
downstream gate resumes. Its prior identity remains in transition history.
Because behavior and contracts are unchanged, dependent artifacts retain their
evidence; any reviewer doubt about that premise reclassifies the change as a
specification or plan defect.

For non-editorial corrections the invalidation graph is fixed:

- specification defect invalidates plan, implementation, implementation
  review, verification, acceptance, and report;
- plan-only defect invalidates affected implementation tasks and all later
  implementation review, verification, acceptance, and report;
- implementation defect invalidates implementation review, verification,
  acceptance, and report; and
- acceptance defect is classified back to specification, plan, or
  implementation at its root cause and follows that path.

The run resumes at the earliest invalidated node. No later evidence survives
unless its inputs and contract are provably unchanged by the allowed editorial
transition above.

After plan review passes, the committed plan identity becomes the **frozen plan
baseline**. Progress tracking uses native tasks or an execution ledger; it must
not mutate the frozen plan's checkbox syntax.

Additional machinery is allowed only when a named requirement, invariant,
existing project convention, or deterministic evidence gate requires it.

## 10. Workflow and gates

Feature Forge executes these stages in order:

1. **Preflight:** confirm Git repository, inspect current state, select
   automation mode, establish reviewer-runner availability, establish or verify
   an isolated worktree, create the run ledger, and project stages into native
   tasks. `review-loop` must validate the user-authorized runner configuration
   required by its own contract; Feature Forge does not substitute a generic
   subagent mechanism. Interactive/supervised mode asks at preflight if no
   runner is configured; unattended mode blocks if none is pre-authorized.
   Reuse an existing non-primary feature worktree only when its branch and
   changes belong to this work unit; otherwise create
   `feature/<work-unit>` in a new worktree before writing.
   Detect an existing same-date slug before creating artifacts: resume it only
   when its intent and identities match. Otherwise supervised/interactive mode
   asks resume-versus-new; unattended mode chooses the lowest unused numeric
   suffix only when the intents are clearly distinct, and blocks if ambiguous.
   Before creating or reusing `feature/<work-unit>`, inspect every same-slug
   branch and worktree regardless of date and verify its intent, base, and run
   identity. Explicitly resume a match; otherwise apply the same unique-suffix
   or blocking rule to both slug and branch.
2. **Brainstorm:** use `superpowers:brainstorming` to explore, compare
   approaches, obtain design approval, and write the initial specification.
3. **Harden:** run the grilling-derived decision-tree interview and update the
   specification.
4. **Candidate gate:** require an empty frontier and `Open questions` section;
   record delegated assumptions and the applicable approval.
5. **Specification review:** invoke `review-loop` with the specification
   charter.
6. **Specification freeze:** commit the reviewed specification and record its
   Git content identity.
7. **Plan:** use `superpowers:writing-plans` against the frozen specification.
   Add a Feature Forge execution note immediately after its required header:
   plan checkboxes are frozen authority, progress lives in the run ledger, and
   workers must not edit the plan to mark completion.
8. **Plan review:** invoke `review-loop` with the plan charter; then commit and
   record the frozen plan identity.
9. **Implement:** choose subagent-driven or inline execution, preferring
   subagent-driven when two or more plan tasks can be owned independently with
   their contracts already fixed. Use inline execution when work is tightly
   coupled through shared mutable state or delegation is unavailable. Return
   before branch finish in either mode.
10. **Implementation review:** invoke `review-loop` with the implementation
    charter and resolve findings. Any fix invalidates that review result; rerun
    review over the changed tree until the final tree receives `PASS`. A fix
    that exposes a spec or plan defect enters change control and invalidates the
    affected downstream baselines.
11. **Final verification:** run fresh risk-proportionate deterministic checks
    over the completed tree.
12. **Acceptance:** execute the specification's per-requirement acceptance
    classification, which is the sole authority at this gate. During spec
    authoring, UI, CLI, and externally consumed API behavior are strong signals
    to classify as UAT; purely internal behavior normally uses automated
    acceptance. Unattended mode records automated evidence and any standing UAT
    waiver.
13. **Report:** write the final requirement-to-evidence and acceptance report;
    complete the ledger.
14. **Finish:** invoke `superpowers:finishing-a-development-branch` exactly
    once and execute the user's selected integration outcome.

A stage advances only when its artifact and evidence gate are complete. A
blocked, contradictory, or materially ambiguous stage remains active or
returns through explicit change control; it is never marked complete to keep
the workflow moving.

## 11. Review charters

### Specification review

Subject: the specification candidate.

Ground truth: captured user intent, existing repository behavior and
constraints, and explicitly referenced authorities.

The review determines whether the specification is faithful, coherent,
bounded, observable, testable, internally consistent, and complete for its
declared intent. Automatically resolvable findings may be fixed within the
candidate scope. Material direction or scope decisions follow automation
authority.

### Plan review

Subject: the implementation plan.

Ground truth: the exact frozen specification and repository state.

The review evaluates requirement-to-task coverage, architectural and systemic
correctness, decomposition and dependency order, cross-task contract
coherence, and execution/verification adequacy. It reviews code blocks only
where they establish or violate interfaces, signatures, invariants, test
intent, dependencies, or architecture. RED/GREEN implementation is responsible
for ordinary code correctness.

### Implementation review

Subject: the complete implementation diff, tests, and affected documentation.

Ground truth: the exact frozen specification and reviewed plan.

The review determines whether requirements are implemented, scenarios are
covered, invariants hold, no material regression or security/performance defect
is known, and no extra scope or machinery was introduced. The loop's own
convergence and merge-readiness verdicts remain distinct.

Final verification always runs against the exact implementation snapshot that
received the last implementation-review `pass`, after all review fixes. The
only permitted post-pass tree changes before verification are the controller's
ledger transition and review-evidence reference; a seal diff must prove that no
implementation or other path changed. The plan is re-reviewed only when a fix
changes or contradicts its task decomposition, dependencies, or cross-task
contracts; specification changes follow full change control.

## 12. Traceability and acceptance

Every implementation-plan task names the requirement and scenario identifiers
it implements. The final report maps:

```text
requirement/scenario -> plan task -> test or evidence -> UAT result
```

Each row includes an evidence command or artifact reference, outcome, and date.
Missing, stale, or non-reproducible evidence is not a pass. The final report
also records the reviewed tree identity, final verification commands/results,
open defects, acceptance method, human approver when applicable, and an
explicit branch-finishing readiness verdict.

For requirements classified as UAT, the user exercises the named behavior and
approval or rejection is recorded. Unattended mode runs the declared automated
substitute and records: "Automated acceptance evidence completed; human
UAT/sign-off was waived." It must not claim user acceptance.

UAT-discovered defects return to implementation and review. Acceptance is not
complete while any required behavior lacks evidence or any material defect is
open.

## 13. Ledger and resumption

The ledger uses the supplied template and records only coarse orchestration
state:

- work-unit identifier and status;
- automation mode;
- current stage and next permitted action;
- worktree and branch identity;
- canonical specification and plan paths and frozen Git identities;
- review state and outcome summaries;
- user approvals and delegated-authority records;
- execution mode and an implementation-progress table containing only plan
  task ID, status, commit ID, and evidence reference;
- final verification and acceptance status; and
- blockers or change requests.

It does not duplicate requirement or task prose, test commands, review
findings, or decisions already owned by canonical artifacts. During
implementation the progress table is authoritative for task completion; native
tasks project it, and a resume cross-checks its commit and evidence references
against Git before continuing.

Stage status is one of `pending`, `active`, `blocked`, `complete`, or
`invalidated`; review state is one of `not_started`, `review_active`, `pass`,
`changes_required`, or `blocked`. The ledger always names exactly one next
permitted action, except when status is terminal. `review_active` permits only
awaiting or recovering that review; it never permits beginning the next stage.

The template includes a transition log with event ID, UTC time, from/to state,
next permitted action, reason/authority, and evidence reference. Persist the
complete ledger update before every external dispatch and immediately after
every return. The prescribed Git checkpoints commit accumulated ledger state;
ordinary transitions do not create extra commits. If a return was not recorded,
resume recovers the referenced dispatch before it considers re-dispatch.

On resume, the controller reads the ledger and exact canonical artifacts,
checks that recorded frozen identities still match, reconstructs native tasks,
and continues from the single permitted action. Conversation memory and a
surviving native task list never override the ledger. A mismatch, rejected
approval, new change request, missing review return, or dirty path first enters
read-only reconciliation. Unresolved material drift becomes `blocked`; an
authorized correction invalidates the affected stage and dependent stages,
then resumes at the earliest invalidated gate.

Frozen identity means the Git blob object ID for each canonical file, recorded
as `<path>@<blob-id>`. Review identity is the exact content seal returned by
`review-loop`; final verification records the reviewed implementation commit
and verifies that no implementation path changed after that seal. The
controller recomputes and compares applicable identities before every
downstream gate and on resume.

The implementation subject begins review and final verification as clean,
committed content. Each review round is read-only against its whole-tree seal.
Review-loop fixes occur only between rounds; the changed tree is re-sealed and
independently reviewed in the next round. `pass` requires a final round over the
post-fix snapshot. Accepted implementation fixes are committed before the next
outer gate.

The ledger is controller state, not part of the implementation subject. It is
expected to change from `review_active` to the returned result after the loop
closes. Before verification, compare the current whole tree to the returned
seal and accept only the exact run-ledger path plus its recorded evidence
reference as post-pass differences; inspect those differences and separately
confirm the implementation commit and every other sealed path are unchanged.
The final report and completed ledger are committed after verification and
acceptance, restoring a clean tree before Finish. Any other untracked or
unstaged content blocks advancement.

## 14. Git and commit boundaries

Read-only exploration may happen in the current checkout. Before the first
tracked Feature Forge artifact is written, use `superpowers:using-git-worktrees`
to establish or verify isolation. Preserve unrelated user changes and never
start implementation on `main` or `master` without explicit authority.

Preflight inventories every dirty path. Reuse a dirty feature worktree only
when each change is attributable to this work unit and its state can be
reconciled; otherwise create a separate worktree or block. Stage commits by
explicit path, inspect the staged diff, and never capture, stash, reset, or
discard unrelated changes.

Create these checkpoints when the corresponding tree differs:

1. `docs: draft <feature> specification` after brainstorming.
2. `docs: freeze reviewed <feature> specification` after hardening and
   specification review.
3. `docs: draft <feature> implementation plan` after writing the plan.
4. `docs: freeze reviewed <feature> implementation plan` after plan review.
5. Implementation commits owned by each reviewed plan task and the selected
   execution skill.
6. `fix: address final <feature> review findings` when final review changes the
   implementation.
7. `docs: record <feature> acceptance` for the final report, UAT or waiver,
   verification summary, traceability, and completed ledger.

Do not create empty commits, commit during an active review round, amend or
squash automatically, combine unrelated user changes, or mutate frozen
artifacts for progress tracking. The worktree must be clean before branch
finishing begins.

## 15. Dependencies and deferred escalation

The MVP requires Git, the named skills, a frontier-capable agent, and a harness
that can read and write repository files. Native plan/todo support is used when
available and replaced by the ledger checklist when absent.

No custom Feature Forge validation program is included. Structural validation
uses the repeatable validator supplied by `skill-creator`; behavior validation
uses the pressure scenarios and artifact-template checks recorded outside the
installed skill. Skill pressure tests must first show that prompt guidance plus
the ledger fails the same mechanical invariant in at least three independent
pressure runs.
Only then may a later change add the smallest deterministic validator needed to
prevent the observed failure. Python or Node selection belongs to that later
evidence-driven change, not this MVP.

## 16. Normative requirements and scenarios

### REQ-001: Canonical authority

Feature Forge SHALL maintain one canonical specification and one canonical
implementation plan for a work unit.

#### Scenario: Worker receives complete authority

- GIVEN a frozen specification and reviewed plan
- WHEN a context-isolated worker receives a plan task
- THEN the task identifies its applicable requirements, interfaces, invariants,
  and verification without requiring the worker to invent cross-task contracts

### REQ-002: Controlled stage advancement

Feature Forge SHALL advance a workflow stage only when its declared artifact
and evidence gate is complete.

#### Scenario: Review is incomplete

- GIVEN a stage whose review has an open material finding
- WHEN the controller evaluates the next action
- THEN the stage remains active or enters explicit change control
- AND no downstream stage is marked in progress

### REQ-003: Scope protection

After the specification becomes a candidate, Feature Forge SHALL reject
discretionary scope or machinery expansion.

#### Scenario: Reviewer suggests an attractive extra feature

- GIVEN a coherent specification candidate
- WHEN a reviewer proposes useful behavior that is not needed to resolve a
  defect or fulfill an approved requirement
- THEN the proposal is recorded as outside the MVP
- AND the candidate is not expanded

### REQ-004: Automation without weaker assurance

Feature Forge SHALL apply the same artifact, review, verification, and evidence
gates in every automation mode.

#### Scenario: Unattended overnight run

- GIVEN unattended authority
- WHEN a material in-scope decision arises
- THEN the agent records and resolves the decision without pausing
- AND all ordinary assurance gates still run
- AND external safety or permission requirements remain binding

### REQ-005: Durable resumption

Feature Forge SHALL reconstruct the single permitted next action from the run
ledger and canonical artifacts after session loss.

#### Scenario: Native task list is lost

- GIVEN a frozen specification, a reviewed plan, and an active implementation
  recorded in the ledger
- WHEN a fresh session resumes without the original native task list
- THEN it verifies frozen identities
- AND rebuilds tasks from the plan and execution progress
- AND does not repeat completed specification or planning stages

### REQ-006: Delayed branch finishing

Feature Forge SHALL invoke branch finishing only after implementation review,
fresh verification, acceptance evidence, and final reporting are complete.

#### Scenario: Execution skill reaches its normal terminal handoff

- GIVEN all implementation-plan tasks have passed their local checks
- WHEN the selected execution skill would normally finish the branch
- THEN it returns control to Feature Forge
- AND Feature Forge completes the remaining assurance stages first

### REQ-007: Immutable reviewed baselines

Feature Forge SHALL detect and reject unapproved drift from a frozen
specification or plan.

#### Scenario: Plan changes during implementation

- GIVEN a recorded frozen plan identity
- WHEN the controller resumes after a plan-file edit
- THEN it does not continue implementation under the old review evidence
- AND routes the change through classification, review, and re-freezing

### REQ-008: Acceptance truthfulness

Feature Forge SHALL distinguish human acceptance from automated acceptance.

#### Scenario: Human UAT is waived

- GIVEN unattended mode and a user-visible result
- WHEN automated acceptance passes without synchronous user participation
- THEN the final report records the evidence and waiver
- AND does not claim human sign-off

### REQ-009: Canonical artifact contract

Feature Forge SHALL use only the canonical specification, plan, run ledger, and
final-report paths for outer-workflow authority.

#### Scenario: Agent considers extra process documents

- GIVEN the canonical artifacts can represent the work unit
- WHEN an agent considers a separate charter, decision log, state file, or
  acceptance document
- THEN it records the information in the owning canonical artifact
- AND does not add the extra document

### REQ-010: Review integrity

Feature Forge SHALL advance from a review only when `review-loop` returns a
passing result and content seal for the exact target under the applicable
charter.

#### Scenario: A review is already active

- GIVEN the ledger records `review_active`
- WHEN another controller resumes the run
- THEN its only permitted action is to await or recover that review
- AND it does not mutate the target, ledger, or downstream stage

### REQ-011: Isolated and auditable Git work

Feature Forge SHALL establish an isolated feature worktree before the first
tracked artifact write and create only the declared checkpoint commits from
explicitly staged in-scope paths.

#### Scenario: Primary checkout contains user changes

- GIVEN unrelated changes exist in the primary checkout
- WHEN Feature Forge starts a new work unit
- THEN it leaves those changes untouched
- AND performs tracked work in a separate feature worktree

### REQ-012: Complete outer pipeline

Feature Forge SHALL retain outer control from preflight through exactly one
terminal invocation of branch finishing.

#### Scenario: Inner skill offers its normal handoff

- GIVEN brainstorming, writing-plans, or an execution skill reaches its normal
  terminal handoff
- WHEN downstream Feature Forge gates remain
- THEN Feature Forge intercepts the handoff and resumes at the next outer stage
- AND branch finishing remains pending until review, verification, acceptance,
  and reporting are complete

## 17. Skill-development verification

Feature Forge is a discipline-enforcing skill and must be developed with
`superpowers:writing-skills` RED-GREEN-REFACTOR:

1. Run realistic combined-pressure scenarios without Feature Forge.
2. Preserve exact failures and rationalizations.
3. Write only the minimum guidance and templates needed to correct those
   observed failures.
4. Re-run the scenarios with the skill.
5. Close demonstrated loopholes and re-test until behavior is stable.

The campaign must cover at least premature implementation, scope expansion,
plan-review distraction by speculative code, nested execution/early branch
finishing, unattended authority, resumption after task-state loss, and unsafe
work on a dirty primary checkout.

Structural validation, a cold-reader test, an independent final review, and
fresh verification are required before installation or publication.
