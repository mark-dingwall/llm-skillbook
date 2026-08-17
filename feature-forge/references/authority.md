# Feature Forge authority and scope-control contract

This reference defines who may decide, what belongs to a work unit, and how a
candidate is made decision-complete. Canonical paths, durable states, and the
fixed change and invalidation graph are owned by the
[workflow contract](workflow.md); use that contract without redefining them
here.

## Mode authority and materiality

| Mode | Alias | Without pause | Pause/block |
| --- | --- | --- | --- |
| interactive | none | editorial corrections | every nontrivial assumption/material decision and UAT |
| supervised | default | minor local reversible decisions; execution mode | goals/non-goals, observable behavior, acceptance, compatibility, scope, public/cross-task contracts, security/data posture, major architecture |
| unattended | full | recorded in-scope decisions and minimum coherence repairs | missing authority, unsafe/irreversible action, unavailable dependency, fundamental intent change, irresolvable contradiction |

**Material** means a decision that changes intent, goals or non-goals,
observable behavior, acceptance, compatibility, scope, a public or cross-task
contract, security or data posture, or major architecture. **Minor** means a
local, reversible decision whose effects remain inside an already-authorized
implementation and do not alter a material item. **In scope** means necessary
to meet the durable intent brief and canonical specification's authorized goals
and requirements, without introducing a new request or expanding a declared
non-goal. When classification is uncertain, classify upward: minor becomes
material, and the more restrictive authority rule applies.

Record every material authority in the canonical specification as either
`user` or `agent:<mode>`. A durable intent brief is required before delegated
authority can be exercised. The record identifies the decision, its rationale,
authority, affected requirements or scenarios, and any acceptance consequence.

## Decision-tree hardening

Harden a work unit by following this terminating loop:

```text
model design tree -> resolve discoverable facts -> compute prerequisite-ready
frontier -> ask whole numbered frontier with recommendations -> integrate into
the one spec -> recompute until frontier and Open questions are empty
```

The design tree represents every decision needed to make the work unit
coherent. Resolve facts that can be discovered from the repository, existing
contracts, or dependable evidence before asking. The prerequisite-ready
frontier contains every remaining decision whose prerequisites are settled;
ask it as one numbered set and include a recommendation for each item.
Integrate each outcome into the same canonical specification, including
authority and rationale, then recompute. Do not maintain competing specs.

When an authority request says **“no more questions,” “fewer questions,”
“implement now,”** or an equivalent acceleration phrase, use the actual current
specification and context to assemble the entire remaining decision frontier.
For each actual decision, record a recommended resolution or default, its
assumptions, and its acceptance and scope consequences; omit or reopen none.
Calling the aggregate a “recommended” or “complete” packet is not a substitute
for explicitly recording those resolution/default, assumption, and
acceptance/scope consequences for every decision. A packet missing any of them
remains incomplete in Harden.

Interactive or supervised mode presents that complete record once for
whole-packet approval or rejection; approval authorizes the recorded defaults.
Unattended mode records the decisions and standing `agent:unattended` authority,
then continues. If current context does not identify the decisions needed to
populate the record, remain in Harden and recover them; do not invent decisions
or implement. Missing authority or an irresolvable contradiction blocks; the
process terminates only when both the frontier and `Open questions` are empty.

## Work-unit specification contract

Each work unit has one canonical specification, with exactly these sections:

1. Intent and authority
2. Goals and non-goals
3. Observable requirements and scenarios
4. Architecture/components/data flow
5. Interfaces/contracts/invariants
6. Domain language
7. Decisions and rationale
8. Assumptions and delegated decisions
9. Error handling
10. Test strategy
11. Open questions

Every normative feature requirement has a stable `REQ-NNN` identifier and one
observable `SHALL` or `MUST` statement. Important success, edge, and error
cases have stable `SCN-NNN` identifiers and use `GIVEN/WHEN/THEN`. Requirements
and scenarios provide the acceptance vocabulary: each one identifies its
acceptance classification, method, expected evidence, and — for UAT — the four
required UAT fields defined below.

The specification includes the durable intent brief, identifies every material
decision's `user` or `agent:<mode>` authority, and records assumptions and
delegated decisions. It classifies every requirement's acceptance as
`automated`, `UAT`, or `not_applicable`; a `not_applicable` classification must
explain why no acceptance action applies. It also records the four required
UAT fields for each UAT-classified requirement. The Candidate gate requires
the `Open questions` section to be present and empty.

## Candidate, freeze, and change control

A candidate is a single hardened, coherent, bounded, and testable canonical
specification: its decision frontier and `Open questions` are empty, delegated
assumptions and authority are recorded, acceptance is classified, and the
applicable approval exists. It becomes frozen only through the workflow
contract's specification-freeze process and recorded identity.

Before changing a candidate, classify proposed behavior that is not needed by
an approved requirement or blocking defect as a **new request**. Explicitly
defer or reject that discretionary behavior outside the current work unit while
preserving every approved requirement and invariant. Deferral or rejection does
not open an approval frontier, create a pause, or disturb candidate
reviewability: an unchanged candidate remains reviewable. Only an explicit,
authorized expansion of the work unit reopens scope and change control; then
classify the expansion under this contract and apply the workflow contract. A
new request remains deferred unless the user explicitly authorizes that
expansion; no delegated `agent:<mode>` authority may authorize it itself.
Machinery beyond this contract — process, artifacts, or checks — is added only
when a named requirement, invariant, existing project convention, or
deterministic evidence gate requires it.

Classify a proposed delta before changing a frozen artifact. An **editorial**
delta corrects wording, formatting, or equivalent clarity while behavior and
contracts are provably unchanged. It requires scoped delta re-review, then
uses the workflow-owned editorial transition and identity recording rules.
Reviewer doubt classifies it upward as a specification or plan defect.
Everything else is a non-editorial correction and follows the fixed
invalidation graph in the [workflow contract](workflow.md#fixed-change-and-invalidation-graph).
Do not restate or alter that graph here.

## Acceptance contract

For every requirement and applicable scenario, record one current acceptance
row with method, state, authority, evidence, and any fallback. Methods are
`automated`, `UAT`, or `not_applicable`; states are `pending`, `approved`,
`rejected`, `infeasible`, or `waived`.

`automated` uses reproducible deterministic evidence. `not_applicable` needs
its documented rationale. `approved` requires current evidence. `rejected`
returns through root-cause classification and the workflow-owned invalidation
graph. `infeasible` records why the method cannot currently run and blocks
required behavior until a user supplies a working method or an explicit
waiver decision resolves it. `waived` records the material authority and
rationale; it is never an implicit approval.

### UAT contract

This is the sole definition of the UAT acceptance contract; nothing here
redefines a workflow-owned stage, state, or checkpoint. Every UAT-classified
requirement's specification entry declares all four fields before Harden can
terminate:

```text
named participant; observable exercise; unattended automated substitute;
evidence criterion that the substitute must satisfy
```

A record missing any of the four fields is not a complete UAT classification.
The **evidence criterion** is the one observable result that both the
participant's judgment and the unattended substitute are tested against — the
supervised and unattended records differ in who or what produces the
evidence, never in the criterion itself.

**Interactive/supervised record (authority `user`).** Names the participant,
the exercise that participant actually performed, its approval or rejection,
the authority (`user`), and the evidence establishing the criterion was met.
It records only what that participant actually did in this run; it neither
invents a human outcome that did not occur nor denies one the run's own
supplied facts state did occur.

**Unattended record (authority `agent:unattended`).** Unattended mode never
performs, infers, or claims human participation. It runs the requirement's
declared unattended automated substitute and evaluates the result against the
same declared evidence criterion — never a weaker one. When the substitute
satisfies the criterion, the record states the automated evidence obtained
and that human UAT was **waived**: state `waived`, standing authority
`agent:unattended`. It never records `approved`, `user`, or any named human
(for example, Sam) as the authority for that outcome — waiving is the only
disposition unattended acceptance may record for a human-classified UAT. If
the requirement declares no adequate unattended automated substitute, or the
declared substitute cannot test the evidence criterion, unattended mode does
not weaken or silently pass acceptance: it records `infeasible` and blocks
until a user supplies a working method or an explicit waiver.

Only user authority waives a UAT outside this unattended substitution path.
`infeasible` blocks required behavior absent a user method or waiver
decision; `rejected` returns through root-cause classification per the
acceptance contract above.

## Acceptance checklist

- [ ] The applicable mode is `interactive` (`none`), `supervised` (`default`), or `unattended` (`full`), and every pause/block rule is obeyed.
- [ ] Material, minor, and in-scope decisions are classified; uncertainty was classified upward.
- [ ] Every material authority is recorded as `user` or `agent:<mode>` against the durable intent brief.
- [ ] The hardening design tree resolved discoverable facts, recomputed its prerequisite-ready frontier, and terminated with both frontier and `Open questions` empty.
- [ ] The canonical specification contains all eleven required sections, including `Intent and authority` and an empty `Open questions` section.
- [ ] Every normative requirement uses `REQ-NNN` with one observable `SHALL` or `MUST`; important scenarios use `SCN-NNN` and `GIVEN/WHEN/THEN`.
- [ ] The candidate and freeze gates are satisfied; every delta has an editorial/non-editorial classification and the workflow-owned invalidation graph is applied.
- [ ] Every acceptance row has an `automated`, `UAT`, or `not_applicable` method and is `pending`, `approved`, `rejected`, `infeasible`, or `waived`.
- [ ] Each UAT declares all four required fields (participant, observable exercise, unattended automated substitute, evidence criterion); unattended work blocks where no adequate substitute exists, and every unattended UAT record is `waived`/`agent:unattended`, never a claimed human approval.
