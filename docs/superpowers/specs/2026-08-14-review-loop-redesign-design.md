# Review Loop Redesign

**Status:** Approved for replacement implementation planning

**Date:** 2026-08-14

## 1. Purpose and authority

This design defines the lean replacement for the unfinished review-loop tier
and roster plan. It is written for an implementer who has the repository but
none of the design conversation. After reading it, that implementer should be
able to plan the bounded prototype described in section 10 without reopening
settled product decisions.

The operator points review-loop at completed code or technical documentation
and may leave it unattended. Subject to the selected effort, deadline, and
explicit safety boundaries, the loop discovers an appropriate review plan,
collects evidence, fixes accepted findings, and returns the strongest honest
verdict it can support for the resulting local artifact.

Where this document conflicts with the [archived tier-and-roster
plan](../../history/review-loop/PLAN-2026-07-28.md) or the recovered
`SIMPLIFY-DEF.md`, this document governs new work. Those documents are
historical inputs, not implementation authority.

The redesign preserves the loop's purpose and assurance model while making its
cost proportional to risk and its prompt footprint smaller. Its North Star is:

> No known material defect, after the artifact has survived risk-proportionate
> independent challenge and all applicable deterministic evidence gates.

This is a qualified operational claim, not proof that an artifact is safe or
correct. The final report must state what was challenged, what deterministic
evidence ran, what could not run, and which residual limitations moderate the
claim. The redesign retains:

- the `GATE -> REVIEW -> TRIAGE -> FIX -> CLOSE` loop;
- whole-tree sealing and out-of-tree artifacts;
- holistic and adversarial review as the base roster;
- consequence-gated specialist staffing;
- automatic effort-tier derivation and per-round re-inventory;
- read-only adjudication of green-making triage dispositions;
- ledger-based convergence and separate merge-readiness; and
- fail-closed treatment of missing reviewers, malformed judgments, ambiguous
  state, and seal drift.

This is an MVP. It does not add review-team integration, synthesis, arbitrary
reviewer commands in profiles, profile inheritance, a general workflow engine,
provider benchmarking, an event log, command transcripts, durable copied input
trees, a portable non-GNU sealing implementation, or multi-review's planned
general-purpose `--sandbox {auto,bwrap,none}` facility. Numeric specialist or
finding caps, an `xhigh` tier, and direct integration into every phase of an
external planning or implementation workflow are explicit non-goals, not
deferred extensions.

## 2. Governing principles

### Use the right execution substrate

LLMs own semantic work over arbitrary code and documents: identifying risk
areas, assigning ratings, deciding whether two areas or findings are
equivalent, tracing dependencies, and judging evidence. Deterministic code owns
strict schemas, fixed lookups, already-decided value combinations, state
transitions, and rejection of malformed or ambiguous input.

Code must not imitate semantic judgment. An LLM must not manually reproduce a
fixed state machine.

### Minimize context without weakening behavior

There is no line-count gate for `SKILL.md`. Keep only the controller workflow,
non-obvious invariants, loading instructions, schemas needed at the boundary,
and terminal conditions in always-loaded context. Put role-specific guidance
in focused files that the dispatched role reads itself. Put repeatable fragile
mechanics in scripts.

Use standard-library facilities when they are adequate. This is a preference,
not a dependency ban: use a mature, small dependency when it materially
improves correctness or avoids home-grown functionality, such as parsing YAML.
Do not add a framework merely to connect three helpers.

### Keep completion semantics tier-invariant

The tier changes effort spent: specialist threshold, round cap, reviewer
capability, and whether the holistic slot fans out. It never changes what
counts as settled, whether adjudication is required, what converged means, or
what merge-ready means. Lower tiers may find less because they spend less; they
may not declare success under a weaker ledger rule.

The tier controls search depth, not truth. Applicable deterministic evidence,
settlement requirements, required-role completeness, adjudication, and the
meaning of the final verdict do not weaken at lower tiers. A deliberately
lower tier may therefore return an honest evidence-limited or NOT CONVERGED
result.

### Add redundancy where one semantic miss can doom the run

Use N+1 challenge at consequential semantic gates: automatic effort rating,
scope and roster calibration, green-making dispositions, and final readiness.
The additional role independently inspects primary artifacts or sealed evidence;
it does not reason from another agent's summary or create a second canonical
ledger. Deterministic mechanics such as schema validation, batching, sealing,
and state transitions need tests and fail-closed behavior rather than duplicate
LLM opinions.

### Prefer explicit, unsurprising control

Operator-supplied intent wins. Never silently ignore a tier, profile, model
pin, reviewer selection, deadline, or confirmation override. Never silently
replace an invalid profile with defaults. Record the selected policy and what
actually ran.

Avoid surprising material expenditure. An automatically derived `max` tier
requires confirmation before reviewer dispatch unless the operator explicitly
selected `max` or explicitly disabled confirmation. Explicit no-confirmation
changes prompting behavior only; it does not authorize dependency installation,
deployment, commits, or other external state changes.

## 3. Architecture

The skill is a thin controller over focused prompt resources and three focused
helpers:

1. **Review-state processor.** Consumes compact validated projections plus
   immutable artifact references and produces validated JSON. It applies tier
   lookups, combines already-assigned values, advances ledger and inventory
   state, and computes terminal rollups. It validates state-machine invariants,
   not a second copy of every rich report/artifact schema, and never reads or
   interprets the review target.
2. **Canonical prompt/report contract.** Renders a declared template and
   explicit fragments from a JSON context, and validates raw Markdown review
   reports. It is the sole production and fixture path for every dispatched
   LLM prompt and the sole ordinary-dispatch report classifier.
3. **Multi-review adapter.** A late, isolated MVP integration that converts one
   canonical holistic request into the repo-local multi-review driver's
   supported v2 headless request, invokes that driver inside caller-provided
   Bubblewrap containment, validates its report, and returns either a usable
   holistic report or a structured fallback reason. It reuses multi-review's
   tested embedding and shutdown contract; it does not implement a generalized
   sandbox selector or duplicate multi-review's fan-out machinery.

These are separate units, not one mixed script and not a plugin framework. Each
has a narrow interface and independent tests. They may share small data types
or validation utilities only when doing so removes real duplication without
coupling their lifecycles.

The processor boundary is deliberately narrower than the canonical artifacts.
Each specialized boundary validates its rich object: the prompt/report contract
owns agent outputs, the evidence runner owns gate execution records, and the
controller owns direct operator records plus FIX manifests. The controller is
the sole artifact-registry owner. Only after the applicable validator succeeds
does it durably store the object and mint an opaque artifact ID bound in
canonical state to artifact kind, schema version, governing seal, and content
digest. The same atomic issuance records a projection binding: operation,
ordered source artifact IDs, every state-affecting projected field, and the
byte-stable projection digest. It then supplies only that registered compact
projection. The processor requires an exact match against the canonical
projection binding and rejects absent IDs, changed values, or any kind,
schema-version, seal, source-set, or digest mismatch; a caller-supplied
non-empty string—or a genuine artifact ID paired with altered summary
values—is not proof. In particular:

- rating projections contain the two validated axes, a validated one-bit
  gestalt step-up decision, and the rating artifact reference, not factor prose;
- area projections contain stable ID, consequence, whether evidenced
  `GENERALIST-MISS` exists, resolved owning-file IDs, coverage proof reference,
  mappings, invalidators, and priority—not aliases, narrative evidence,
  charters, or display locators;
- gate projections contain gate ID, target seal, applicability,
  required/supporting classification, and pass/fail/not-run state plus the gate
  artifact reference—not commands, captured output, or explanatory prose;
- ledger projections contain immutable row/source IDs, severities, factual and
  lifecycle states, manifest/proof references, authority identity/linkage where
  applicable, and the governing seal—not raw claims, report prose, or quotes;
  the full canonical artifact retains those details for audit;
- final-challenge projections contain the sealed operative outcome and source
  finding IDs or blocker reference, not the complete attempt report.

This is not permission to trust caller-authored summary booleans. The processor
still derives eligibility, blockers, transitions, retry/bounce state, and both
terminal verdicts from exact enums and references, rejects contradictory
projections, and fails closed when a required proof reference or seal is absent.
Cross-helper fixtures must show that invented IDs, wrong-kind references, stale
seals, and digest mismatches never become operative state.
The production processor is invoked only by the controller against the
controller's persisted canonical registry snapshot; it does not expose a
free-form operator CLI that can supply both a projection and a fabricated
registry. Its atomic boundary is `validate rich object -> persist bytes and
artifact binding -> persist exact projection binding -> apply transition`.
Test-only JSON adapters may
exercise the pure processor, but production never treats their input as an
issued artifact.

Focused prompt resources contain the detailed charters for evidence discovery,
inventory, inventory challenge, rating, adjudication, holistic review,
adversarial review, specialist review, bounded FIX, and final-readiness
challenge. Every role reads a prompt rendered from those fixed skill-relative
resources. The controller carries only the resource identifier, task-local
input, and required output contract. Semantic roles never delegate.

## 4. Review flow and effort tiers

### Preflight and Stage 0

Resolve invocation intent before dispatch: optional tier, profile, maximum time
in seconds, and confirmation override. A supplied maximum must be a positive
integer. Validate an explicitly selected profile before any agent runs. Then
resolve the full proposed run root and reject it when it equals, contains, or
is contained by the sealed target; do this before creating any artifact.
Preflight also resolves the subject, base, head, exclusions, and one
deterministic **delta contract** for later rounds. It records whether Git
metadata sits outside the target, the bound
index/working/untracked policy, and the one non-mutating mechanism that can
render the exact changed-path set and canonical-record delta between any
verified pre-FIX and post-FIX identity. That delta records every changed entry,
including add/delete/type/mode/content-digest changes and every bound index
change; a textual content patch is only its regular-file rendering. The
mechanism must materialize the canonical-record delta as one controller-owned,
versioned, byte-stable regular file outside the target; it may additionally
materialize a regular-file content patch. Those files are sealed round inputs,
never a copied input tree. An absent or ambiguous base, repository-state policy,
two-state reconstruction, or an unmaterializable delta format rejects the target
before Stage 0; this MVP does not add a snapshot or non-Git delta fallback.

Before spending on semantic review, compute a provisional whole-target identity
with the sealer and dispatch one fast, read-only **evidence scout** at
`mid-tier`. It inspects
the actual target, operator instructions, repository guidance, build metadata,
and stated review intent. Operator-supplied gates take precedence, followed by
explicit repository-declared gates; the scout fills gaps rather than replacing
either. Its strict result lists each proposed gate's stable ID, exact invocation,
provenance, applicability, intended execution phases, prerequisites, expected
signal, safety assessment, and any important behavior for which no applicable
deterministic gate exists. A malformed result receives one retry; a second
failure makes Stage 0 INDETERMINATE. An empty valid gate list is an evidence gap,
not a passing gate and not by itself a failed run.

Execution phase is scheduling metadata, never terminal evidence. Each actual
gate execution produces an individual record bound to the target seal on which
it ran. If no target mutation occurs, a required baseline pass is already bound
to the final seal. After any accepted FIX delta, refresh applicability and run
every safe applicable required gate plus the safe supporting gates selected for
the changed behavior on the verified post-FIX seal. CLOSE derives readiness
only from execution records for the actual final seal; a pass on any earlier
seal is stale and cannot satisfy a required gate.

The result also classifies each gate as `required` only when operator or
repository authority makes it mandatory; all other useful gates are
`supporting`. The controller validates the proposed execution plan before
running it. For terminal purposes a gate is applicable only when it is relevant,
safe, and runnable with prerequisites already present; a relevant check blocked
by missing tooling remains a disclosed evidence opportunity, not a silently
passing gate. Never install dependencies, initialize tooling, alter manifests
or lockfiles, deploy, commit, use production credentials, or allow an
uncontrolled external write in
order to obtain gate evidence. A gate that may write ordinary test/build output
runs against a disposable exact copy or equivalent tested containment bound to
the provisional identity; the copy is transient execution substrate, not a
durable review artifact. A gate may run against the authoritative target only
when its tested invocation is non-mutating.

Every gate command uses a tested execution mapping exposing only its exact
sealed target or disposable copy, declared read-only runtime inputs, and fresh
scratch. It supplies no host credentials, denies network access and writes
outside the copy/scratch, and terminates the complete process tree on deadline.
If this mapping or another equivalently tested containment is unavailable,
record `NOT_RUN` and the reason. Any executed applicable gate that does not
produce its expected passing signal stops NOT CONVERGED; `supporting` never
means that a known failure is advisory. After baseline gates, recompute the
authoritative target identity and require equality with the provisional identity
before promoting it to the Stage 0 target-baseline seal. Record exact commands,
target identity, exit status, and bounded output for every attempted gate.

Evidence is artifact-sensitive. For code, applicable gates may include tests,
lint, type checks, builds, schema checks, or executable examples. For technical
documents, use existing mechanical checks such as link, schema, reference, and
example validation, plus existing behavioral fixtures when the document is
instructional. Do not invent a nominal test merely to claim coverage. Semantic
correctness and completeness of prose are established primarily through the
independent review roster. RED/GREEN pressure scenarios are required when
developing review-loop's own skill or role prompts, where the document directly
controls agent behavior; they are not a universal per-target document gate.

The sealer accepts only directories and readable regular files: a symlink,
FIFO, socket, device, unreadable entry, or an entry whose type or identity
changes during enumeration fails preflight. Its versioned canonical byte record
contains a sorted, unambiguously framed relative-path entry for every admitted
directory and regular file, each entry's type and relevant mode, and a content
digest for every regular file. For a Git target it also binds the whole index
identity named by the delta contract; Git metadata itself is not a target-tree
input. Stable open/stat checks must prove that the enumerated entries remained
the recorded type and identity while the record was made. This establishes the
Stage 0 **target-baseline seal**, which covers the whole target tree; every
comparison is an exact comparison of this canonical record, not merely a
comparison of file contents.

At Stage 0, resolve the operator-designated ground-truth sources into one
ordered canonical inventory of exact regular-file locators and immutable file
identities. Persist that inventory in canonical state before any triage can
refer to it. An out-of-tree ground-truth source is included in every applicable
call-input seal; a missing or changed source fails closed rather than being
rediscovered or reconstructed from a digest after restart.

Dispatch one semantic inventory agent at `most-capable`. It owns the canonical
area IDs, aliases, mapping decisions, consequence and `GENERALIST-MISS`
evidence, surface locators, and total specialist-priority order. Malformed
output is discarded and retried once; a second failure makes Stage 0
INDETERMINATE and the loop NOT CONVERGED. When the operator supplies a tier,
respect it and do not dispatch rating agents merely to derive a competing tier.

After each valid initial inventory proposal, dispatch one independent, read-only scope
challenger at the same capability required for that inventory call
(`most-capable` at Stage 0 and the run tier's normal capability on refresh). It
receives the target and proposal, not the inventory agent's hidden reasoning,
and checks for omitted material areas,
unsupported consequence or `GENERALIST-MISS` claims, redundant fragmentation,
and charters that cannot be answered independently from primary artifacts. It
returns either `UPHOLD` or individually evidenced challenges; it never emits a
competing inventory. A challenged inventory receives one owner revision that
must resolve every challenge in a complete replacement inventory or preserve a
rejection with primary evidence. Persist the proposal, challenges, and
resolutions for the final-readiness check. Malformed challenger or revision
output receives one retry at its owning boundary; a second failure makes the
stage INDETERMINATE. This bounded proposer/challenger exchange does not iterate
to consensus: do not challenge the owner revision again in the same inventory
stage. Its preserved challenges and resolutions remain inputs to final readiness.

When no tier is supplied, also dispatch two `most-capable` rating samples,
preferring different vendors where available. Two samples of one model are
acceptable when the host offers no real vendor diversity, but the report must
not describe them as independent model families. Each rater returns strict JSON
containing its complexity rating (`C`), risk rating (`R`), evidence, and any
declared gestalt factors. Both axes use the `low < med < high < max` ladder.
The inventory agent owns semantic identity; rating agents do not emit a
competing inventory.

The evidence scout uses the provisional identity until the Stage 0 baseline is
promoted; every later call uses the applicable accepted target baseline. The
controller checks the applicable expected seals immediately before every
target-accessing process is launched and after each such process completes:
evidence scouts, inventory agents and challengers, rating agents, ordinary
holistic/adversarial/specialist reviewers, triagers, adjudicators,
final-readiness challengers, and the multi-review driver. FIX uses the separate
mutation-window checks below. The **target-baseline
seal** always means the last accepted whole-target identity. A round may have
multiple immutable **round-input seals**, one per input-producing stage. In a
later round, first make an inventory-refresh-input seal for a controller-made,
read-only projection of the prior mappings and coverage, plus the verified
delta and manifest. Its completed inventory then feeds a separate
reviewer-input seal. A TRIAGE-input seal covers the published raw reports it
reads, and an adjudication-input seal covers its pending triage result and
authority inputs. Stage 0 inventory and rating calls use the target baseline
plus a Stage-0 static-input seal for their exact operator inputs; their report
field remains `round_input_seal: null` because it is not a round. Each
call-input seal references the applicable target baseline and hashes its exact
regular inputs; no later stage extends, replaces, or reuses an earlier seal. A
process must match every seal for the inputs it can read. If members run
concurrently, a post-completion mismatch cancels the outstanding members. A
mismatch voids all output from the affected round or Stage 0, makes the loop
NOT CONVERGED, and never takes a fallback branch. The multi-review adapter
performs these checks for its driver call; the controller performs them for
ordinary dispatch.

Every non-FIX target-accessing call, including ordinary roles, TRIAGE, and the
multi-review adapter's driver call, uses a tested host execution mapping that
enforces read-only access through three disjoint mount classes: (1) its exact
per-call target-path scope, whose paths must match the target-baseline record or
the evidence scout's provisional record;
(2) the exact review-data inputs named in its call-input seal; and (3) the
tested, non-review-data runtime/credential allowlist needed to start that call.
Only the preflight evidence scout, Stage 0 inventory/challenge/rating calls, a
round-1 full review, and the final-readiness challenge have the whole target tree
as their target-path scope. Later evidence and inventory refreshes and focused
reviews receive only their declared changed or `SURFACE` target files; any
target bytes TRIAGE or an adjudicator needs must likewise be in its exact
dispatched scope. The runtime
allowlist is read-only and may contain only the driver or CLI executable,
interpreter/libraries, and exact required authentication/configuration files; it
cannot contain target data, review artifacts, canonical state, peer artifacts,
or prior-round artifacts. The mapping exposes no writable canonical state, peer
artifact, or prior-round artifact, and permits writes only to that call's fresh
controller-owned report channel and disposable scratch. Before target access,
the mapping establishes a fresh,
non-reusable process-tree or containment identity with parent-death cleanup. The
controller persists that identity and its tested termination handle in the
immutable `CALL_STARTED` dispatch tuple. A report becomes operative only after
the mapping has terminated and reaped the whole call process tree, the controller
has recorded that termination proof, validated the result and post-call seals,
and atomically published the report and completion tuple. On recovery or deadline
expiry, a `CALL_STARTED` tuple without that completion is never harvested,
resumed, or retried: use its persisted handle to terminate/reap any surviving
process tree. If the controller cannot prove that outcome, it retains any output
only as non-operative evidence, marks its Stage 0 or round INDETERMINATE, and
launches no replacement or fallback. Recovery may continue only from a fully
published phase boundary after the deadline and seals are rechecked. The prompt's
read-only instruction is not authorization. If the selected CLI has no tested
mapping, the controller does not dispatch it; there is no uncontained bypass.
Seal checks remain necessary detection and fail-closed evidence handling, not a
substitute for read-only execution and not rollback machinery.

`FIX` is the sole authorized mutation window. Invoking review-loop authorizes
one controller-dispatched implementation agent to make bounded local changes
needed to resolve current `OPEN` ledger rows. It is not a generic command
executor and it may not delegate. Before entering FIX, the controller binds the
window to the exact current `OPEN` IDs and supplies their immutable claims,
current evidence, authoritative sources, permitted target root, and required
manifest contract. The implementer may change only the review target; it may
not install dependencies, alter dependency manifests or lockfiles merely to
obtain tooling, commit, stage, deploy, contact external systems, use production
credentials, or perform unrelated cleanup. Direct user risk acceptance remains
outside the implementer's authority.

The implementer may invoke only controller-approved local validation commands
from the evidence plan when the FIX mapping can contain their effects. Those
results are diagnostic; the controller independently reruns applicable gates
after validating the delta.

The FIX execution mapping is the sole tested writable mapping. It exposes the
sealed target and controller-supplied FIX inputs, no canonical state or peer
artifact, and a fresh report/manifest channel. Agent tool/process actions receive
no host credentials, no network, and no write path outside the authorized target
or disposable copy and scratch; the host may retain only the tested provider
control channel and minimum read-only authentication needed to run the agent.
The mapping terminates and reaps the whole process tree on deadline. If the host
cannot enforce that separation, automated FIX is unavailable and the run stops
NOT CONVERGED rather than relying on prompt compliance.

Prefer a disposable writable copy or equivalent containment from which the
controller can validate a candidate delta before applying it to the
authoritative target. A tested direct single-writer target mapping may be used
with the same controls, pre/post identities, and process handling; the final
report must disclose that interruption may require operator recovery. There is
no uncontained writable fallback and no rollback claim.

The implementation agent returns a strict fix manifest associating every
declared changed target path with one or more bound ledger IDs and explaining
the change. FIX never stages, commits, or otherwise mutates the bound Git index;
any index delta during the mutation window is unauthorized. A manifest cannot
itself alter ledger state. Immediately before dispatch or candidate-delta
application, recompute the whole target identity and compare it with the last
verified target-baseline seal. A mismatch stops NOT CONVERGED; never record the
mismatching identity as a new baseline. Only after equality may the controller
record the verified pre-FIX identity and `FIX_STARTED`.

After FIX, use the delta contract to render and retain the exact
canonical-record delta, changed-path set, and any regular-file content patch,
then regenerate the whole-target identity and verify its delta from the pre-FIX
identity. Every changed target path or bound index entry must be manifest-bound
to one or more authorized IDs and remain within the target. A missing or
malformed manifest, unauthorized path, an undeclared change made only to enable
review tooling, external-state attempt, or delta-contract failure stops NOT
CONVERGED and promotes no ledger row. In a disposable-copy implementation,
reject the candidate before applying
it. In a direct-write implementation, retain the detected delta for explicit
operator recovery and make no claim that the target was restored.

Refresh the evidence plan against the actual verified delta. Run every safe
applicable required gate on the verified post-FIX seal and add safe supporting
gates for changed behavior.
A gate that may write uses the same disposable-copy rule as preflight. After
the gates, recompute the authoritative identity once more; every required gate
must have run and passed, every other executed applicable gate must have passed,
and the identity must equal the verified post-FIX identity before it
becomes the next round's target-baseline seal. Only then may the controller seal
the retained delta as the next round's input and atomically transition every
and only currently `OPEN` row with a manifest-bound verified change to
`FIX_APPLIED`. Rows without that linkage remain `OPEN`. A passing gate or
manifest alone is never fix verification.

When relevant tests pass and an already installed, configured mutation tool can
run safely and within the remaining deadline, run it against the changed or
risk-bearing code. Never install or initialize mutation tooling. If tooling is
absent, the controller may instead ask for a small number of high-value manual
mutations in a disposable copy: the unmutated targeted test must pass and each
non-equivalent mutant must make it fail. Do not weaken a test or disable a
fixture to manufacture failure. Mutation evidence supports test adequacy; it is
not a universal score threshold or by itself a terminal verdict. When relevant
mutation testing was unavailable, retain one concise follow-up note for the
final report rather than prompting during the run.

Apply the same opportunistic mutation policy after the initial passing baseline
when relevant, even if the loop never enters FIX. After FIX, scope it to changed
or risk-bearing behavior and tests. Mutation-tool absence never triggers an
installation or confirmation prompt.

If the host or session interrupts after `FIX_STARTED` and before post-FIX
verification succeeds, record the round INDETERMINATE and return NOT CONVERGED.
A restarted controller may retain evidence for hand-back but must not resume
that run or establish a new baseline; start a new run instead. From the Stage 0
target-baseline seal until cancellation or CLOSE, the single-user MVP assumes no
concurrent writer other than the controller-authorized FIX agent or deterministic
candidate-delta application. If exclusivity cannot be assured, stop NOT
CONVERGED rather than accepting an ABA-style restored seal. Canonical state
retains the Stage 0 target baseline, each verified pre-FIX identity, each
round's target baseline, and each round-input seal rather than one overloaded
run-wide seal.

Immediately before a positive CLOSE, recompute the whole target identity and
compare it with the last accepted target-baseline seal. A mismatch is NOT
CONVERGED; it cannot produce a verdict for bytes that no reviewer saw.

When deterministic state first qualifies for merge-readiness, dispatch one
independent final-readiness challenger at `most-capable` against the final
sealed target, ground truth, complete roster and scope-challenge history,
ledger, fix manifests, gate plan/results, mutation evidence, and disclosed
gaps. It tests whether the artifact still contradicts authority, a material
claim lacks evidence, a test was weakened, required work was omitted, or a
known material defect remains. It returns `UPHOLD` or `BLOCK` plus exact
evidence and may include ordinary source findings under the canonical report
contract. `BLOCK` requires a material target defect or material evidence/process
failure; a Minor observation is reported without independently blocking. The
role cannot create readiness, weaken a deterministic prerequisite, or settle a
ledger row.

Publish any final-challenger source findings as one required raw report and run
one sealed supplemental TRIAGE pass under the ordinary provenance and ledger
rules. A resulting Important+ `OPEN` row continues to FIX when round and
deadline policy allow; the next review is a new round. Otherwise the run is NOT
CONVERGED. A procedural `BLOCK` without a target finding names the failed
readiness condition and prevents merge-readiness. A malformed or failed
challenge receives one retry; a second failure makes CLOSE INDETERMINATE. After
any subsequent target change, the prior result is stale and a fresh final
challenge is required. `UPHOLD` is supporting independent evidence only: the
state processor still computes the terminal verdict mechanically.

The prompt/report contract validates the rater's evidence and any declared
gestalt factors, then emits a compact rating projection. The state processor
merges already-decided values mechanically: take the
maximum `C` across raters, take the maximum `R` across raters, then take the
maximum of those two merged axes as the base tier. If both merged axes are at
least `high`, step up once. Then, if any rater supplied a valid `GESTALT: +1`
decision whose report contract established at least three individually
evidenced factors, step up once more regardless of how many raters supplied
one. Cap the result at `max`.

The rater makes the semantic gestalt decision. The report contract validates
the factor structure and preserves the prose in the rating artifact. The
processor accepts only the resulting validated step-up bit and artifact
reference; it never decides whether factors form a gestalt, invents a factor,
or applies the gestalt step more than once.

Malformed rater output is discarded and retried once. Do not repair JSON,
infer omitted fields, or partially accept it. Fewer than two valid rating
samples after retries makes Stage 0 INDETERMINATE, stops before review dispatch,
and makes the loop NOT CONVERGED.

An automatically derived `low`, `med`, or `high` tier proceeds without an
extra prompt. An automatically derived `max` tier pauses once before reviewer
dispatch unless the operator explicitly requested no confirmation. If the
operator declines or does not confirm, persist `CANCELLED_BEFORE_REVIEW`, retain
the completed inventory/rating state, and stop without entering CLOSE or
emitting a CONVERGED or merge-ready verdict. If the persisted deadline expires
while awaiting confirmation, expiry takes precedence: mark the stage
INDETERMINATE and return NOT CONVERGED rather than recording cancellation. An
explicitly requested `max` tier already expresses authority and does not prompt again. Hosts may expose the override as
`--no-confirm`; clear prose such as “run without confirmation” is equivalent.
No custom argument parser is required.

### Tier table

| Tier | Intended use | Specialist eligibility | Round cap | Normal reviewer capability | Multi-review timing |
|---|---|---|---:|---|---|
| `low` | small, bounded, low-consequence target | Critical with `GENERALIST-MISS` | 2 | mid-tier | never |
| `med` | ordinary default review | Important+ with `GENERALIST-MISS` | 3 | mid-tier | never |
| `high` | complex, sensitive, or uncertain work | Important+ with `GENERALIST-MISS` | 5 | one-above-mid | round 1 |
| `max` | exhaustive treatment where omissions are particularly costly | every materially distinct named area | 5 | most-capable | rounds 1 and 2 |

The round cap is a ceiling, not a quota. Close as soon as the invariant ledger
conditions are satisfied.

The capability column governs ordinary review roles, including ordinary
holistic fallback; it does not configure multi-review participants.
Multi-review uses each fixed CLI's tested native tool default unless the
profile supplies an explicit model pin. When `use_cli_defaults: true`, every
unpinned fixed participant receives only its base, delivery, and streaming
arguments: no `CLI_SPEC.default_args`, inferred model, or inferred effort. An
explicit `models[participant]` entry is the exact-pin path. Absent or false
retains the generic driver's current behavior for non-review-loop callers. Do
not add a new fan-out capability abstraction for the MVP.

Every round retains holistic and adversarial review. Multi-review replaces
only the holistic slot; it never replaces adversarial or specialist review.
Specialists are selected from the named inventory under the tier threshold and
coverage rule below. There is no numeric specialist cap. The processor filters
the inventory agent's validated total priority order to the complete scheduled
set; there is no separate ranking call and priority cannot remove a role. The
order exists only for capacity-safe batching and deadline handling. Every
specialist roster entry carries its area ID, distinct failure-mode charter, and
primary surface. The controller freezes the complete round roster before
dispatch, reserves its own active slot, uses the host-advertised concurrency
limit when available, and dispatches excess roles in waves. If no numeric limit
is exposed, use a conservative tested concurrency. Never skip a scheduled role
to fit capacity. Deadline expiry or a required role that remains unusable after
its allowed retry makes the round INDETERMINATE and NOT CONVERGED.

Round 1 reviews the full sealed target. Later-round holistic and adversarial
reviewers receive the changed target files plus exact regular files containing
the canonical-record delta, its regular-file content patch when one exists, the
fix manifest, relevant ledger state, and refreshed risk inventory. A staffed
specialist additionally receives the sealed regular target files resolved from
that area's current `SURFACE` locators, including unchanged files needed to
inspect the chartered area. A qualified non-file locator must resolve to its
owning target file before dispatch. Missing, escaping, or ambiguous locator
resolution makes the started round INDETERMINATE before reviewer dispatch; it
never counts as coverage. Those generated inputs are sealed as part of the
round's input set. A `max` round-2 multi-review uses the focused holistic scope;
it repeats a full target review only when the operator explicitly requests one.

### Inventory and specialist selection

Every inventory area carries a stable semantic ID, aliases, `CONSEQUENCE`,
attributed consequence evidence, evidenced `GENERALIST-MISS` or an explicit
absence, normalized `SURFACE` locators, and its place in the total specialist
priority order. Each area is a materially distinct concern with a specialist
charter that can be answered from primary artifacts; overlapping concerns that
require the same evidence and continuous reasoning belong in one area. The
inventory agent decides area equivalence, dependency and contract relevance,
consequence, and whether specialist depth is needed.
The prompt/report contract validates and preserves the inventory's aliases,
charters, narrative evidence, and locators. The state processor accepts only a
compact projection of its resolved semantic decisions; it never infers an area
identity from a path or a prior state record. The controller joins scheduled
area IDs back to their canonical charters and primary surfaces when rendering
review prompts.

`GENERALIST-MISS` is a prospective, evidenced explanation of why the holistic
charter alone is likely to miss or under-examine a material failure mode in the
named area. It does not claim that a generalist has already run or actually
missed a finding. This lets the Stage 0 inventory justify round-1 specialist
depth without manufacturing review history.

Each later-round refresh uses the one inventory agent at the run tier's normal
reviewer capability. Its strict JSON must contain the full inventory schema and
map every previously named area exactly once to one resolved continuing ID, an
explicit listed successor ID, or `RETIRED`. Every non-retired mapping target
must be a current active ID. Active IDs are unique, and the total specialist
priority order is bijective with them: it names every active ID exactly once and
no other ID. The inventory agent may name genuinely new active areas, but it
must not use a duplicate, omission, or ambiguous replacement chain to create or
hide one. It also receives each area's `CURRENT`/`STALE` specialist coverage and
refreshes the total priority order for batching accordingly. An absent or ambiguous
mapping, duplicate or missing ID, invalid priority order, malformed JSON,
missing field, or partial inventory makes the whole output malformed and
consumes its one retry. A second failure makes the started round INDETERMINATE
and the loop NOT CONVERGED; stop before roster dispatch, record no roster or
coverage update, and count it as an attempted round. Never reuse a stale
inventory.

`RETIRED` is an explicit semantic mapping from a previously named area to no
active, separate material concern in the latest sealed target. It may apply
when the risk-bearing surface was removed or neutralized, or when the prior area
was not a distinct material concern. It must not represent an unstaffed or
ineligible area, a rename, move, or merge (which uses a continuing or successor
ID), target-scope drift, or an individual ledger finding's disposition. Every
`RETIRED` mapping contains a non-blank, single-line `retirement_reason`. The
reason is retained in canonical state and the final report solely for post-run
independent audit; it has no dispatch, triage, adjudication, or terminal effect
beyond identifying the mapping as retired.

`CONSEQUENCE` uses `Minor < Important < Critical`. Across inventory refreshes,
retain the highest consequence ever stated, every attributed consequence and
`GENERALIST-MISS` evidence line, and the union of evidenced surface locators for
every active lineage. An inventory omission or weaker restatement cannot lower
historical consequence or erase a coverage gap. A valid explicit `RETIRED`
mapping is the sole exception: it preserves that evidence as historical audit
data but ends the active lineage and its staffing obligation.

An area is eligible when:

```text
tier == max OR (GENERALIST-MISS exists AND consequence meets threshold)
```

For each eligible active area, canonical state records specialist coverage as
`CURRENT` or `STALE`; it has no quiet counter. Staff the area when it is Critical
or its coverage is not CURRENT. Thus eligible Critical areas receive specialist
challenge in every dispatched round, while a non-Critical area retains a valid
review until evidence invalidates it. Passing or silent rounds alone never
change coverage.

Coverage becomes CURRENT only from a completed usable specialist report whose
sealed scope contains every current active-lineage `SURFACE` owning file. It
becomes STALE before roster selection when a verified delta changes a relevant
surface, dependency, or contract; a linked finding reopens; semantic identity
changes or a successor is created; or the refreshed inventory supplies material
new evidence that specialist depth is needed. The inventory agent makes
dependency, contract, identity, and new-evidence judgments explicitly; the
processor validates and applies them but never infers them from paths. A
continuing ID may retain CURRENT coverage only when none of those invalidators
holds. Every successor and newly eligible area starts STALE. Holistic mention
alone is not specialist coverage.

Inventory refresh and specialist completion are two different transitions.
`refresh_inventory` runs before roster selection and only maps identities,
applies invalidators, retains eligible prior coverage, and makes every new or
successor area STALE. After a scheduled specialist report is usable and its
findings have passed through TRIAGE, `record_specialist_coverage` may move that
active area to CURRENT before CLOSE. Its compact projection must name the
scheduled area ID, current target seal, exact resolved owning-file ID set, and
immutable specialist-report/scope proof reference, plus the accepted sealed
TRIAGE artifact that contains that exact raw specialist report ID. Apply the
coverage update atomically with accepted TRIAGE state: if that TRIAGE result
reopens a finding linked to the area, reopen invalidation wins and coverage
remains or becomes STALE. A report omitted from TRIAGE, a report from another
seal, an unscheduled area, or a scope that omits or adds an owning file is
rejected.

At CLOSE, a current non-retired Important+ area with evidenced
`GENERALIST-MISS` and no CURRENT specialist report is a merge-readiness blocker.
A valid retired area is neither eligible for staffing nor a blocker. If an
operator-selected lower tier makes such an active area ineligible, the run may
still be CONVERGED but is not merge-ready; the hand-back recommends a new run at
a sufficient tier. At `max`, every materially distinct named area is eligible
and every required uncovered role is scheduled; the controller does not invent
a higher tier or omit work to satisfy an arbitrary count.

### TRIAGE and ledger

After every required report for a round is usable, dispatch one read-only
triager against the applicable seals and its exact sealed raw-report and
current-evidence scope. It converts the raw reports into one strict-JSON triage
result before any FIX, roster-coverage update, or terminal decision. The result
contains an exact `report_ids` set and a record for every report, including an
explicit empty finding list. It maps each raw report's exact `source_findings`
inventory to canonical ledger IDs; multiple source findings may map to one
canonical ID, but none may be omitted, duplicated, or mapped outside that
inventory. The controller reconstructs each source finding from the sealed raw
record and requires its reported claim, severity, and required source locators
to be preserved exactly in triage provenance; TRIAGE may add separate current
evidence but cannot weaken, replace, or omit that raw premise. Every listed
finding record has a canonical ID, aliases and source report and finding IDs,
source claim and locators, reported and current severity,
`CONFIRMED`/`PLAUSIBLE`/`UNVERIFIABLE` factual status, proposed ledger state,
provenance, and evidence locators. The controller rejects unknown, missing, or
duplicate report and finding IDs, report IDs not matching the usable raw-report
set, any reported-severity or required-source-locator mismatch, invalid
state/factual combinations, missing source or evidence locators, and any result
whose applicable seal differs. It derives "reviewer-stated Important+" only
from that immutable raw inventory. It retries one malformed or failed triage
call once. A second failure makes the round INDETERMINATE and NOT CONVERGED
without FIX or coverage update.

After those checks, the controller projects only immutable row/source IDs,
reported and current severity, factual/proposed state, governing seal, and the
required manifest, proof, acceptance, or authority references into the state
processor. Claims, prose evidence, aliases, and locators remain in the sealed
triage and canonical audit artifacts and are not revalidated as a second rich
schema by the processor.

The ledger has exactly five states: `OPEN`, `FIX_APPLIED`, `FIX_VERIFIED`,
`REFUTED`, and `INTENTIONAL`. New findings and any finding reactivated by new
conclusive evidence enter `OPEN`. `OPEN -> FIX_APPLIED` requires a fix-manifest
entry bound to that exact ledger ID. A later triage result may return
`FIX_APPLIED -> OPEN` when the failure remains or its evidence is inconclusive.
`FIX_APPLIED -> FIX_VERIFIED` requires that result to cite both the manifest
entry and sealed current-target evidence that the original failure no longer
occurs. The processor projection carries a structured fix-proof reference with
the current target seal and rejects missing, empty, or stale-seal proof. An
empty report, reviewer silence, passing evidence gates, or the
manifest's existence alone is not fix verification. `OPEN` or `FIX_APPLIED`
may become `REFUTED` or file-authorized `INTENTIONAL` only after the
adjudication rule below; ledger-ID-bound direct user risk acceptance may instead
create the recorded `INTENTIONAL` exception. A later report or changed authority
that invalidates a `FIX_VERIFIED`, `REFUTED`, or `INTENTIONAL` basis returns the
row to `OPEN` and preserves the rejected basis as history. `UNVERIFIABLE` cannot
settle a row. There is no generic accepted, deferred, or closed state.

CLOSE computes two total verdicts from the canonical ledger and final lifecycle
state. Immediately before CLOSE, recheck the persisted absolute expiry and final
target seal. Expiry marks the current lifecycle INDETERMINATE and returns NOT
CONVERGED; it takes precedence over either terminal verdict. CLOSE is reachable
only after any required automatic-max confirmation was accepted and Round 1
completed through TRIAGE. The loop is CONVERGED only when
every scheduled role in every completed round supplied a usable report, every
usable raw report maps to the ledger, no stage is INDETERMINATE, the final target
seal matches, and no Important+ row is `OPEN` or `FIX_APPLIED`. Otherwise it is
NOT CONVERGED and the hand-back names the failed conjunct. The target is
merge-ready only when it is CONVERGED, the
final-readiness challenger upheld the same final seal, every required evidence
gate ran and passed for that seal, every other executed applicable gate passed,
every Important+ row is
`FIX_VERIFIED`, `REFUTED`, or an explicitly recorded `INTENTIONAL` exception,
and no current non-retired Important+ specialist-coverage blocker remains.
This merge-ready verdict is the operational “no known material defect” claim;
it is always accompanied by the evidence and limitation disclosure from section
1. Open Minor rows and unavailable supporting gates are reported but do not by
themselves prevent either verdict. A material evidence gap identified by the
final challenger does prevent merge-readiness.

### Adjudication

After triage and before any green-making disposition becomes operative, collect
all pending reprieves in that round: rows proposed as REFUTED, file-authorized
INTENTIONAL rows, and rows whose current severity is below any reviewer-stated
Important+ severity, including rows ingested already downgraded. Every
file-authorized pending reprieve carries a proof record: one exact sealed
ground-truth locator and identity, the authority proposition it relies on, and
a concise explanation of why that proposition supports this ledger ID and
disposition. A locator's mere existence or the absence of contrary text is not
proof. If the set is non-empty, dispatch one read-only adjudicator pass. If it
is empty, skip the call. The adjudicator receives the pending rows, the sealed
scope's exact file list and exclusions, and the inventory of authoritative
ground-truth sources pinned at round 1. Ground truth consists of specs, decision
records, or other operator-designated authority used to check the target rather
than material being reviewed as the target; out-of-tree ground-truth files are
included in the applicable seal. The adjudicator reads those sources
independently and looks for positive support or a contradiction of the triager's
proposed disposition.

User-confirmed risk acceptance during the current loop remains the direct
authority exception. Bind it to exact ledger IDs and record the user's quoted
message plus round and time; do not pretend it is file-adjudicable. A quote with
no unambiguous ledger-ID binding is not operative. Every other pending reprieve
is tier-invariant and cannot become operative without adjudication.

Use `most-capable` for adjudication by default because a mistaken reprieve can
directly create a green verdict. If the host cannot select capability, use its
default and disclose that control was unavailable under the same host-fallback
rule as other roles.

The adjudicator returns strict JSON with exactly one `UPHOLD`, `BOUNCE`, or
`UNDECIDED` decision and one evidence locator for every expected ledger ID. The
prompt/report contract validates and retains that full output, then gives the
state processor a compact per-row projection bound to the adjudication-input
seal and immutable adjudication artifact reference. An
`UPHOLD` of a file-authorized `INTENTIONAL` repeats the exact authority identity
and a positive proposition-to-row linkage that supports that reprieve. An
`UPHOLD` of a `REFUTED` row or severity downgrade instead requires positive
sealed target or ground-truth evidence and a fact-to-row linkage. Neither form
is valid when it merely says no contradiction was found. Missing, unknown, or
duplicate IDs; duplicate result blocks; a mismatched expected-ID set; invalid
decisions; or missing evidence makes the whole call malformed. `UPHOLD` keeps
the proposed disposition, `BOUNCE` restores the row, and `UNDECIDED` is eligible
only for the subset retry described next.

The projection must retain enough positive proof to prevent green-making from a
bare decision: the evidence seal, proof reference, and fact-to-row linkage, plus
the exact authority identity/linkage for file-authorized intent. The processor
checks those fields against the pending row and governing seal and preserves
their references on the canonical row. It does not parse the adjudicator's prose
or duplicate the full report schema.

Adjudication has at most two calls. If the first call crashes or is malformed,
discard every decision from it and retry the full set once. If a clean first
call leaves rows undecided, retain its final decisions and retry only the
undecided IDs once. A bounced row is restored atomically to its pre-disposition
state. On the second call, a failure or malformed result bounces its entire
attempted set, and every clean `UNDECIDED` result also bounces. Never make a
third call.

## 5. Prompts and report contracts

The prompt/report helper accepts JSON context plus a known template identifier.
Templates contain only declared `{{name}}` substitutions. Conditional material
is selected by the caller as explicit fragments such as round-one,
later-round, evidence discovery, inventory, inventory challenge, rating,
adjudication, holistic, adversarial, specialist, FIX, or final readiness.
Templates do not contain a general control language, and bracketed prose is
never interpreted as a menu.

Before substitution, the helper fails on:

- missing declared values;
- unknown values supplied by the caller;
- unknown template or fragment names; or
- undeclared or unresolved substitution tokens in the selected template or
  fragments.

Substituted values are opaque data; literal `{{...}}` text inside subject
material is never rescanned as template syntax. The rendered bytes are the
production prompt and the test fixture input. Every non-FIX target-accessing LLM
prompt preserves the existing boundary: subject material is labelled data, the
role is read-only against the seal, and the role reports rather than fixes. The
FIX prompt preserves the same untrusted-subject boundary but carries the sole
explicit, ledger-bound writable authorization described in section 4.

Every holistic, adversarial, and specialist prompt asks each raw reviewer
response to lead its review with a `## Summary` section, include exactly one
fenced strict-JSON `review-record`, and make its last non-blank line exactly one
terminal record: `REVIEW-STATUS: COMPLETE`, or `REVIEW-STATUS: UNABLE` when it
could not review the scope. The record contains the controller-issued
`request_id`, role, charter identifier, target-baseline seal, `round_input_seal`
(null only in Stage 0), the exact dispatched scope-locator IDs, and a
`source_findings` array. It has no other fields. Every source finding has a
unique ID, a non-blank concise `claim`, `Minor`/`Important`/`Critical` severity,
and one or more source locators; an explicit empty array means no findings. The
claim is the immutable semantic premise TRIAGE maps to a ledger row. The record
is the source-finding universe: narrative observations without an entry are not
a reported finding and cannot affect the ledger. `UNABLE` may be explained
briefly in the preceding body and is not a usable report. Step narration or a
preamble may precede the heading. A usable report also requires the controller
to have recorded successful completion of that exact dispatched `request_id` and
a unique controller-assigned raw `report_id`; the validator must match every
record field to its dispatch. The established
unanchored presence check for `Summary` or `Executive Summary` remains a
compatibility/display check, not sufficient completion evidence. Earlier
status-looking text is body data, so quoted source material cannot create or
invalidate completion. The terminal line must match exactly; trailing prose or
an absent/unknown status is invalid. Evidence discovery, inventory, inventory
challenge, rating, adjudication, FIX-manifest, and final-readiness roles use
their declared strict validators instead. The review-loop multi-review opt-in
applies the same record contract to each raw participant report: both receive
the same canonical `request_id`, while the controller preallocates their
distinct raw `report_id`s and the driver validates/echoes them outside the
verbatim prompt. One shared
fixture corpus exercises the ordinary validator and the driver's opt-in
classifier so their two codebase-local implementations cannot drift silently.

The aggregate `REVIEW.md` itself need not begin with that heading; it begins
with metadata and wraps raw reports. The canonical holistic prompt works
unchanged in both paths; do not add a multi-review-only LLM instruction
fragment.

The driver's v2 schema adds optional `verbatim_custom_prompt`, defaulting to
false. It is valid only with `task: custom` and a non-empty `custom_prompt`.
When true, the driver treats `custom_prompt` as an exact byte payload: before
launching the fixed clients it writes and byte-compares its prompt transport
against the payload, then delivers only those in-memory bytes over stdin. It
adds no injection or
reference preamble, title, context body, file manifest, delimiter, or trailing
newline. The required `files` list still validates sealed scope and controls
what the contained clients can read; it is not rendered into the prompt body.
A mismatch before launch or after fan-out is a driver validation failure.
Existing non-review-loop tasks and custom-prompt callers retain the current
wrapped behavior unless they opt in.

Prompt bodies never travel in process arguments. The adapter writes the driver
YAML to a transient per-round transport path outside the still-empty output
directory and passes only its path and short scalar options to the multi-review
driver. The fixed Claude/Codex clients both receive prompt bytes through stdin.
This preserves the existing E2BIG protection. Under interim whole-call
containment, the on-disk transport is visible in the shared namespace, so its
pre/post byte check is required and the final report discloses that it was not a
driver-private mount.

## 6. State and artifacts

Canonical state is JSON. Human-facing state is generated Markdown. Store every
run outside the sealed target under:

```text
$XDG_STATE_HOME/review-loop/runs/<project-id>/<run-id>/
```

When `XDG_STATE_HOME` is unset, use
`~/.local/state/review-loop/runs/<project-id>/<run-id>/`.

Retain the run directory by default and identify it in the final hand-back.
Project and run identifiers must be stable, filesystem-safe, and collision
resistant; their exact encoding is an implementation detail covered by unit
tests.

Each scheduled multi-review call receives one fresh, empty, atomically claimable
output directory, for example:

```text
<run>/rounds/<round>/multi-review/
```

Never use the run root or a prior round directory as the driver's `--out-dir`.
The adapter never retries a multi-review call. After the call ends, retain
evidence-bearing report content under the run directory and discard only the
transient prompt/YAML transport files according to the artifact rule below.

The MVP durable artifacts are:

- `review-state.json`, the canonical machine state;
- one human-readable Markdown ledger/report; and
- raw reviewer reports that were actually used as review evidence.

For multi-review, the aggregate `REVIEW.md` already preserves the successful
raw reviewer sections and is sufficient evidence; do not duplicate those
sections into additional files merely to satisfy this list. Ordinary reviewer
reports remain separate raw files.

Do not add an event log, command transcript, copied input tree, profile
snapshot, generated-prompt archive, or artifact hash manifest without evidence
from real use that it is needed. The target seal itself remains required and
is represented in canonical state rather than as a new family of artifacts.
The minimal artifact/projection registry inside `review-state.json` is the
narrow exception required to authenticate state transitions; it is part of the
canonical machine state, not a separate hash-manifest artifact or event log.

At minimum, canonical state records:

- run identity, subject/base/head, exclusions, deployment context, the Stage 0
  start and resolved absolute deadline when one exists, the Stage 0 target
  baseline, every verified pre-FIX identity and subsequent target baseline, and
  each call-input seal;
- lifecycle status, including `CANCELLED_BEFORE_REVIEW` and its reason when
  applicable;
- requested tier/profile/deadline/overrides and their resolution;
- automatic ratings and evidence when rating ran;
- selected tier and tier source;
- evidence-scout proposals, authoritative gate provenance, exact validated
  invocations, `required`/`supporting` classification, timing, safety decision,
  target identity, result, and explicit evidence gaps;
- the ordered round-one ground-truth inventory with exact locators and immutable
  identities;
- named inventory areas, semantic IDs/aliases, consequence, semantic mapping
  decisions including every `retirement_reason`, current active status, priority
  order, `CURRENT`/`STALE` coverage with its reason and specialist-report
  linkage, plus each inventory proposal, independent challenge, and owner
  resolution;
- round roster including specialist area IDs, requested capability, resolved
  reviewer, requested capability or model argument, dispatch outcome,
  completion, batch/wave, duration, and degraded/fallback reason;
- immutable per-dispatch validation tuples: `request_id`, controller-assigned
  raw `report_id`, role, charter identifier, expected target/call-input seals,
  exact scope-locator IDs, `CALL_STARTED`/completion outcome, recoverable
  containment/process identity and termination proof, and any non-operative
  recovery outcome;
- canonical ledger rows, raw-report mappings, provenance, dispositions,
  fix-verification evidence, FIX process/mapping outcome, fix manifests,
  verified deltas, post-fix gate results, and bounded mutation evidence;
- pending adjudication sets, call outcomes, final decisions, and atomic
  bounce/restoration results; and
- final-readiness challenge inputs, outcomes, findings or blockers; convergence,
  merge-readiness; and the exact failed terminal conjunct when a run does not
  converge.

The processor owns atomic state transitions and rejects unknown states,
impossible transitions, malformed enums, unresolved semantic mappings, and
ambiguous inputs. It does not invent missing semantic data.

## 7. Profiles and capability resolution

Profiles are optional local YAML files. The invocation-level concept is
`review_profile`; hosts may present it as `profile: <name>`, `--profile
<name>`, or equivalent prose. This is operator intent for the skill to
interpret, not a reason to build a custom argument parser.

The no-profile MVP path uses the adapter-owned explicit multi-review list
`[claude, codex]`; it must write that list into the driver YAML and must never
inherit the driver's five-reviewer default. The adapter owns a small, tested
mapping of exact read-only credentials/configuration and fresh per-call mutable
client scratch for those two clients, plus the fresh multi-review output
directory. It never mounts a live host client-state directory writable. A
profile cannot add a participant or mount: adding another client is deferred
until a containment mapping and adapter test exist for it.

A bare name is a separator-free safe basename (not `.` or `..`) whose resolved
path remains beneath the configured profiles directory. It resolves only to:

```text
$XDG_CONFIG_HOME/review-loop/profiles/<name>.yaml
```

When `XDG_CONFIG_HOME` is unset, use
`~/.config/review-loop/profiles/<name>.yaml`.

Project-local or other profiles require an explicit path. There is no profile
auto-discovery. Profiles are environment-specific and are not committed as
selectable repository presets. The repository may document examples and
recipes.

Version 1 is a strict sparse overlay on tier defaults:

```yaml
version: 1
max_time_seconds: 1800

holistic:
  capability: mid-tier
  model: local-model-id
  fallback_capability: mid-tier
  fallback_model: local-model-id
  multi_review:
    models:
      claude: provider-model-id
      codex: provider-model-id

adversarial:
  capability: mid-tier
  model: local-model-id

specialists:
  capability: mid-tier
  model: local-model-id
```

Every field is optional except `version`. Named fields replace the relevant
tier default; omitted fields inherit it. `holistic.capability` and
`holistic.model` control ordinary holistic dispatch, including low/med rounds
and later high/max rounds that do not fan out. Fallback inherits those values
unless the fallback-specific fields override them.

An absent `max_time_seconds` means no run-level deadline unless the operator
supplies one for that invocation; a per-run value overrides the profile. The
value is always positive integer seconds. At Stage 0 entry, persist the resolved
absolute expiry before dispatch; recovery uses that original expiry and never
rebases the deadline. Reviewer calls still retain their normal per-call timeouts.
Unknown keys, unknown versions, wrong types,
non-positive deadlines, and unsupported capability labels are errors.
`multi_review.models` may name only `claude` and `codex`, and each value must
be a non-empty string. Profile and driver YAML loaders reject duplicate mapping
keys at every nesting level before applying defaults or semantic validation;
last-key-wins parsing is invalid configuration.

A model pin in `multi_review.models` for a reviewer outside the fixed pair is
invalid configuration. Normal-role `holistic`, `adversarial`, and `specialists`
model pins shown in this schema are allowed. An unpinned ordinary role may use
its normal one retry and otherwise makes the round INDETERMINATE. An explicit
normal-role pin is never substituted: a retry, if appropriate, uses the exact
same pin; a rejected or unavailable pin makes the required role unusable and
therefore makes the round INDETERMINATE. Ordinary holistic fallback is reserved
for a failed fixed-pair multi-review slot.

Profiles may pin tool-specific models for the fixed multi-review pair, set
normal-role capability labels or model pins, and set a maximum time. They may
not set the tier, alter round caps or staffing thresholds, add arbitrary
commands, choose participants, enable synthesis, or weaken containment, the
two-report minimum, sealing, ledger transitions, or terminal rules. There is
no inheritance, include, stacking, or per-area specialist override in version
1.

Missing or malformed explicitly selected profiles stop before dispatch and
ask whether to proceed with tier defaults. They never silently fall back.
Errors point to the installed `DESIGNING_PROFILES.md`, which documents the
schema, safe limits, examples, and migration guidance.

Capability labels are contextual policy, not hardcoded model names or an
automatic benchmark. Resolve `mid-tier`, `one-above-mid`, and `most-capable`
against the current host's supported controls and record the actual result. If
the host cannot select capability, proceed with its default and record
`capability control unavailable`.

Do not silently substitute for an explicit normal-role model pin: if it cannot
be honored, stop and report it. The same rule applies to a multi-review model
pin. For the MVP, “honored” means the adapter passed the exact configured model
argument, omitted the CLI's default-model arguments, and the CLI did not reject
or emit the tested mapping's documented downgrade signal for that request. Each
tested CLI mapping defines the rejection/downgrade signals it recognizes and
records the raw indication; absence of an indication is not provider-side model
attestation. An unavailable, rejected, or reported-downgraded pin makes that
participant failed; the adapter must not retry it without the pin or run it at
a default model. With the fixed two-reviewer MVP pair, that causes ordinary
holistic fallback and a prominent record of the requested pin and failed
participant.

An operator may still directly instruct the orchestrator to use a particular
CLI for one ordinary, non-multi-review review. That one-off instruction must
use the controller's tested read-only mapping. If none exists, stop because the
requested CLI cannot be honored; explicit confirmation does not authorize an
uncontained ordinary review. This is not a reason to add arbitrary commands to
profiles or override the contained multi-review pair.

## 8. Multi-review boundary and failure handling

This integration is scheduled after the ordinary controller path and its
deterministic boundaries work end to end, but it remains part of MVP
acceptance. Multi-review already exposes a supported headless v2 driver contract
for contained callers and has exercised caller-supplied Bubblewrap mount and
process-tree shutdown recipes across the fixed reviewer CLIs. Review-loop owns
only its concrete call mapping, containment wrapper, validation, and fallback;
it does not add multi-review's separately planned generalized sandbox CLI.
For this MVP, that supported whole-call caller containment is an accepted
interim boundary. Multi-review's prioritized Phase 2 will move the boundary to
one native Bubblewrap namespace per reviewer subprocess; adopting that stronger
profile is follow-up hardening, not a prerequisite for the ordinary path or this
MVP's multi-review slot.

The adapter treats multi-review as a black box with one request and one report:

```text
canonical holistic prompt
    -> adapter
    -> bwrap + repo-local multi_review.py
    -> REVIEW.md
    -> adapter validation
    -> ordinary holistic triage
```

The adapter-written driver YAML sets `prompt_format_version: 2`, `task: custom`,
a non-empty `files` list that is exactly the union of the per-call regular
target-path scope validated against the target-baseline seal and the regular
client-visible review-data inputs covered by the current reviewer-input seal,
`reviewers: [claude, codex]`, any configured `models` entries, the canonical prompt as
`custom_prompt`, `verbatim_custom_prompt: true`,
`use_cli_defaults: true`, `synthesizer: none`, the driver's review-loop opt-in
`require_complete_status: true`, and a `review_record_expectation` object. That
object carries the exact non-prompt `request_id`, role, charter identifier,
target-baseline seal, round-input seal, scope-locator IDs, and controller-
preallocated distinct raw `report_id`s keyed to `claude` and `codex`. The shared
fields are what each model-authored participant record must match; the fixed-slot
ID mapping remains controller/driver metadata and is never expected in that
record. Extend the v2 schema with those optional
review-loop fields, each defaulting to false or absent, so other tasks and
custom-prompt callers retain their current behavior. The v2 validator strictly requires only
`prompt_format_version`, `task`, and `files`; the adapter still writes every
field above explicitly so reviewer and synthesizer defaults cannot widen the
call. An older driver rejects an unknown review-loop opt-in field and therefore
takes ordinary fallback rather than accepting refusals or wrapped prompt
transport.
Synthesis is disabled, not merely non-authoritative.

The controller-owned driver YAML is a driver-only regular input, never a
client-visible `files` entry. After writing it, the adapter creates a separate
immutable driver-configuration call-input seal over its exact bytes and records
that seal and digest in the dispatch tuple. The driver must match both that seal
and the reviewer-input seal; the adapter byte-verifies the YAML against the
persisted configuration seal immediately before dispatch and after the driver
exits. A mismatch voids the stage as any other input-seal mismatch; it is not a
fallback condition.

The driver exit code is necessary but insufficient because the current driver
returns success when any classified report succeeds. The adapter independently
validates the driver's machine-readable result in `REVIEW.md` and accepts it
only when both fixed, distinct reviewers are recorded as successful. When the
opt-in above is true, the driver validates each participant's complete terminal
line and exactly one strict `review-record` against the non-prompt expectation
before accepting it. For each accepted fixed slot, the driver selects that
slot's controller-preallocated raw `report_id` and writes, in the existing leading
YAML frontmatter, a participant-qualified record containing that ID, the shared
`request_id`, and the validated `source_findings` inventory, including every
immutable claim. It writes no
participant record for a malformed or incomplete body. The adapter reads only
that leading YAML frontmatter: the document must begin with `---`, end that
frontmatter at the first subsequent line equal to `---`, and parse to expected
unique, disjoint success/failure lists and exactly the two validated participant
records. The successful fixed slots `{claude, codex}`, their preallocated raw
IDs, the participant records, and durable dispatch tuples must be the same
bijection; otherwise the result is malformed. It never splits the Markdown body
on `---` or independently parses reviewer sections. Thus a Markdown rule,
embedded YAML, or diff in a raw report cannot change the count or source
inventory. Any failed participant, missing/malformed record, or malformed
frontmatter takes the ordinary holistic fallback; the run is marked degraded and
names the failure.

The driver safely serializes every model-authored claim and other frontmatter
value; it never hand-interpolates such data into YAML. Before publishing, and
again before the adapter accepts it, the leading frontmatter must pass a
duplicate-key-rejecting typed parse and round-trip to the expected fixed-slot
record. A multiline, YAML-shaped, or `---`-looking claim is data, never a
frontmatter delimiter or participant field.

The aggregate `REVIEW.md` is retained whole as evidence. From its validated
frontmatter, the adapter mechanically presents TRIAGE one opaque usable-report
envelope with a controller-assigned aggregate `report_id` and the exact union of
participant-qualified source finding IDs, claims, severities, and locators.
TRIAGE does
not understand multi-review vendors, roster selection, or aggregation internals
and does not parse the body. The envelope is one report: its source-report ID is
the aggregate ID and each source-finding ID is the pair of participant raw
`report_id` and that participant's source-finding ID. This is provenance
preservation rather than a second merge, deduplication, or synthesis
implementation inside review-loop.

Bubblewrap is required. Following multi-review's supported caller contract, the
adapter launches the headless driver inside a `bwrap --unshare-pid
--die-with-parent` wrapper and sends termination signals to that wrapper. It
starts from multi-review's tested containment recipe, reducing it to the exact
fixed-pair runtime and inputs below; any necessary divergence must be justified
by an adapter test. The adapter gives the whole call one fresh aggregation,
transport, home/state, and scratch mapping; read-only binds the driver YAML plus
exactly that `files` union; and exposes no live host client-state directory
writable. In Round 1, its target-path component is the full sealed target
regular-file set; in a later focused round it is only the declared
changed/surface target files, while its review-data component is the exact run
artifacts. The two components retain their separate baseline and call-input-seal
validation even though the driver's `files` list unites them. The separately
sealed driver YAML is driver transport rather than a client-visible `files`
entry, although the current whole-call namespace does not make it inaccessible
to a hostile reviewer process. Before dispatch, resolve the tested
driver runtime closure. Its checkout, interpreter or managed environment, CLI
executables, libraries, and required package/cache content must all lie outside
the sealed target; none may be obtained from a target-path scope or a review-data
input. A closure that intersects the target makes multi-review unavailable and
takes the ordinary fallback—this MVP neither copies nor stages a driver runtime.
The resolved runtime closure is otherwise available read-only so the tested
command can actually start under containment.

No live host client-state directory, including `~/.claude` or `~/.codex`, is
writable in the sandbox. The fixed clients receive fresh scratch home/state
directories for that driver call, discarded after evidence has been retained.
Bind only the minimum exact credential/configuration files needed to
authenticate as read-only; client-generated caches, session files, and other
mutable state are written to scratch. The driver captures participant streams
in memory, waits for and reaps the reviewer subprocesses, and only then writes
and atomically publishes the aggregate. The output directory is fresh and
claimed before dispatch, and the adapter rejects any malformed, inconsistent,
special, or non-regular final artifact.

The interim whole-call namespace means reviewer subprocesses can see the
driver's transport and writable aggregation/scratch mounts and can interfere
with sibling processes. The post-fan-out publication order and strict aggregate
validation reduce false-evidence risk, but this is not the same boundary as
driver-private output. Treat attempted interference or unexpected output state
as call failure and ordinary fallback, and disclose this residual limitation in
every run that uses multi-review. When multi-review's prioritized per-reviewer
subprocess profile lands, adopt it to make driver transport/output, peer
artifacts, and live host state inaccessible at the mount boundary; do not
reimplement that generalized native facility inside review-loop.

Any host settings file that can define executable hooks remains read-only and
is not copied into mutable scratch. Scratch is never reused or promoted back to
host state. Canonical state, the ledger, prior rounds, and the rest of the run
root are not mounted writable. These explicit binds are required even below
`$HOME`: the containment recipe uses a fresh home, so host paths otherwise do
not exist in the sandbox. The adapter preserves
required network access and performs the seal checks around the call. Exact
mount and environment recipes belong in the implementation plan and adapter
tests, not in `SKILL.md`. There is no multi-review containment bypass in the
MVP. This containment protects filesystem integrity and write isolation, not
confidentiality: because the clients retain network access, a compromised client
can exfiltrate any mounted input or credential to an arbitrary endpoint. Use
only targets and credentials acceptable for provider and residual network
exposure; egress controls remain deferred work.

The adapter requests ordinary holistic fallback and records the reason when
the seal still matches and:

- the driver is missing or cannot start;
- its required driver runtime closure intersects the sealed target;
- Bubblewrap is missing or unusable;
- the driver exits unsuccessfully or produces malformed/inconsistent output;
- either fixed participant lacks a valid completed report;
- the adapter cannot enforce its deadline or validation contract.

An applicable seal mismatch is not a reviewer availability failure and never
takes the fallback branch. It voids every report produced for that round or
Stage 0, marks that stage INDETERMINATE, and makes the current loop NOT
CONVERGED. Do not dispatch against a changed tree or changed generated input
under an old seal. Only the controller-owned FIX transition may establish the
next round's target-baseline seal within the same loop.

Before choosing or launching fallback, check the run deadline and every
applicable seal again. Expiry stops NOT CONVERGED; it never launches fallback.
The adapter invokes multi-review once for a scheduled holistic slot; it never
retries the expensive fan-out. Fallback is automatic because it adds only the
final branch to an adapter that already owns invocation and validation. The
fallback reviewer uses `holistic.fallback_capability` and `fallback_model` when
set; otherwise it inherits the resolved ordinary `holistic.capability` and
`model`. The adversarial and specialist roster is unchanged. Each ordinary
reviewer has at most one retry. If any required ordinary report, including
fallback, is still unusable, retain sibling raw reports only as non-operative
evidence, perform no triage, fix, or coverage update for that round, mark it
INDETERMINATE, stop the loop, and return NOT CONVERGED.

The run-level deadline is elapsed wall-clock time from the persisted Stage 0
start; waiting for the automatic-`max` confirmation counts. Recovery checks the
persisted absolute expiry before every lifecycle action, including cancellation
and CLOSE, and never restarts its clock.
When it expires, stop launching work and terminate the active call or batch
using its normal deadline mechanism. Recheck every applicable seal, retain
completed raw evidence as non-operative, mark the current stage or round
INDETERMINATE, and return NOT CONVERGED. Deadline expiry never becomes a clean
or partially completed round.

## 9. Testing and MVP acceptance

### Deterministic tests

Give each helper ordinary unit and contract tests.

The state processor tests its compact projection schemas, tier lookups, rating
combination,
one-time gestalt step-up, consequence monotonicity, single-owner re-inventory
mappings including bijective IDs and priority order, malformed/ambiguous-map
retries, coverage invalidation after a changed `SURFACE` file, continuing-ID
retention, and mandatory successor uncoverage, `RETIRED` definitions and missing, blank, or multiline
`retirement_reason` rejection, `GENERALIST-MISS` eligibility, uncovered-first
priority ordering without roster omission, complete capacity-safe wave
scheduling, `CURRENT`/`STALE` coverage under every declared invalidator,
eligible-Critical restaffing, area-linked specialist coverage and later-round
surface resolution, post-TRIAGE coverage rejection when the specialist report
is omitted or a linked finding reopened, source-backed `REFUTED` upholds and both
second-call adjudication paths,
ledger-ID-bound user acceptance, strict-JSON TRIAGE report/retry behavior,
exact source-finding reconciliation, positive reprieve-proof validation, valid
and invalid ledger transitions including `FIX_APPLIED -> OPEN` and adjudicated
settlements, proof-linked `FIX_VERIFIED` transitions, pre- and post-roster
INDETERMINATE accounting, compare-before-record FIX entry, atomic verified
`OPEN -> FIX_APPLIED`, manifest ledger-ID/path validation, unauthorized FIX
paths and actions, post-FIX evidence-gate failure, interrupted-FIX restart
refusal, a `CALL_STARTED` recovery with a
recoverable process/containment handle that makes the incomplete stage
non-operative and INDETERMINATE, declined automatic-max cancellation, expiry
during confirmation and after TRIAGE before CLOSE, distinct target-baseline and
immutable per-stage call-input seals (including Stage-0 static,
inventory-refresh, raw-report TRIAGE, and triage-result adjudication inputs),
post-FIX baseline acceptance before its delta is sealed, canonical-record delta
coverage for mode-only,
empty-directory, and index-only changes, final-CLOSE seal drift, durable
round-one ground truth, persisted-deadline recovery, required versus supporting
gate effects, rejection of earlier-seal gate passes at final readiness, stale
final-readiness results after mutation, final-challenge
findings returning through TRIAGE, and both terminal rollups. Rich rating,
inventory, review, gate, adjudication, FIX, and final-challenge report schemas
belong to prompt/report or controller contract tests; do not duplicate them in
state-processor tests. Cross-helper contract fixtures prove that each validated
artifact projects the exact state fields and immutable references expected by
the processor.

Evidence-gate controller tests cover precedence of operator and repository
authority over scout suggestions, valid empty discovery as an evidence gap,
malformed discovery retry, unsafe and mutating-command rejection, disposable
copy binding, read-only target binding, scratch-only writes, absent host
credentials, denied network access, process-tree termination, exact
baseline/post-fix command and result recording, authoritative target drift,
document-specific mechanical and behavioral gates, unavailable supporting
gates, executed gate failures, and required gates that cannot support
merge-readiness.
Mutation tests cover safe use of existing configured tooling, no installation
or initialization path, bounded manual mutations in a disposable copy,
unmutated-baseline failure, equivalent and surviving mutants, and the concise
missing-tooling report note.

FIX controller tests prove that invocation authorizes exactly one non-delegating
implementation role, only FIX receives a writable mapping, manifest-bound
changes can advance eligible rows, unrelated and tooling-only changes cannot,
target/copy/scratch write boundaries and network/credential denial are enforced
independently of prompt compliance, an uncontained or externally acting
implementation path is rejected, and a failed or interrupted direct-write path
discloses recovery without claiming rollback. Inventory-challenge tests cover
upheld proposals, omissions,
redundant fragmentation, evidenced owner rejection, bounded revision, and
malformed-call failure. Final-readiness tests prove that `UPHOLD` cannot bypass
deterministic prerequisites, procedural blockers prevent merge-readiness,
source findings enter ordinary TRIAGE, and a changed target requires a fresh
challenge.

The prompt/report helper tests exact declared substitutions, explicit fragment
selection, template-token failures without rescanning substituted data,
preservation of the read-only safety boundary for every non-FIX target-accessing
role and the exact ledger-bound writable boundary for FIX, the
display-only unanchored `Summary` check, strict `review-record` validation for
all ordinary review roles, quoted status-looking source lines followed by one
terminal status, mismatched dispatch/seal/scope records, source-finding ID
uniqueness, distinct same-locator/same-severity claims, immutable source
claim/severity/locator provenance, strict-JSON role validation, and
byte-equivalent use for ordinary and multi-review holistic
dispatch.

The adapter tests with controlled fake processes and reports: normal success,
the opt-in strict review-record classifier without changing other driver tasks,
rejection of either opt-in by an older driver, byte-equivalent verbatim custom
prompt transport, exact unpinned Claude and Codex native-CLI argv rather than
generic driver defaults, prompt-body mismatch failure, missing completed reports,
unexpected/duplicate reviewer IDs, malformed frontmatter, body delimiters that
resemble frontmatter fences, missing/malformed/mismatched participant review
records, participant-qualified frontmatter provenance, duplicate/swapped
fixed-slot raw IDs, hostile multiline/YAML-shaped/delimiter-looking claims and
duplicate frontmatter keys, driver failure, missing Bubblewrap, deadlines, recognized
zero-exit pin-downgrade signals, driver-YAML byte drift before or after dispatch,
and ordinary fallback. Separate
tests prove that every scheduled call gets one fresh empty claimed output
directory; the driver, interpreter/environment, fixed CLIs, and required
read-only package content can start inside the `$HOME` tmpfs recipe; exact
later-round target and review-data inputs are readable only through the exact
`files` union; the runtime/credential allowlist contains no review data; a
target-contained driver runtime takes ordinary fallback; and an unlisted target
file is unreadable.
Clients may write only the fresh whole-call output/scratch surfaces; live host
client state, the target, canonical state, and prior rounds remain non-writable,
and scratch cannot persist hooks or other state to the host. Fake clients that
precreate, replace, link, or corrupt prompt transport, `.REVIEW.md.tmp`, or
`REVIEW.md` must make publication or adapter validation fail and take ordinary
fallback, never create usable evidence. A contract test records that current
whole-call containment does not hide those paths and therefore keeps the
residual-limitation disclosure operative until native per-reviewer containment
is adopted.
Tests also prove that no multi-review retry occurs, expiry and recovery terminate
the whole call tree before fallback or an INDETERMINATE result, pre/post seal
drift from every review path voids the stage without fallback, and prompt bodies
never appear in process arguments. Controller tests also prove that an ordinary
role cannot write a peer report or canonical state.

Profile tests cover name and explicit-path resolution, version and unknown-key
rejection, sparse overlays, positive-integer deadlines, ordinary/fallback
holistic inheritance, minimum fixed-pair configuration, non-empty model values,
duplicate YAML mapping keys at every depth, separator/traversal rejection for
bare profile names, permitted normal-role pins versus
fixed-pair-only `multi_review.models` pins, exact pinned-model command
construction without default-model arguments, documented rejection/downgrade
signals and rejected pins causing participant failure, no substitute for an
explicit normal-role pin, missing profiles, and non-overridable safety fields.
Controller tests also reject a resolved run root that overlaps the sealed target,
a target without one deterministic delta contract, and an ordinary CLI with no
tested containment mapping.

### LLM behavior tests

Use targeted RED/GREEN pressure scenarios only where a pre-change baseline
demonstrates a real behavior failure. Preserve the production prompt boundary
and keep ground truth outside the dispatched prompt. Retain focused coverage
for rating quality, semantic area identity/re-inventory, evidence-gate
selection, inventory challenge, bounded FIX behavior, final-readiness challenge,
and reviewer behavior whose efficacy depends on prose. Controls exercise the
current guidance before it changes; retain exact observed failures,
rationalizations, useful null results, and fresh-context variance. Add the
minimum role guidance that closes a demonstrated failure, then probe that
boundary rather than adding speculative prose. Preserve the focused existing
adjudication fixture for independent disposition checking and its
malformed/crashed-call behavior. Use behavioral document tests directly for
review-loop's own instructional skill and prompts, not as a mandatory gate for
arbitrary prose targets. Do not recreate dual-model requirements, large
manifests, input-hash bureaucracy, or fixtures for wording-only edits.

### Acceptance criteria

The MVP is acceptable when:

- explicit and automatic tier paths produce the specified roster and round
  policy without changing completion semantics;
- auto-derived `max` is the only automatic tier that pauses, while explicit
  `max` and explicit no-confirmation proceed without that prompt;
- one canonical inventory survives independent scope challenge, every
  specialist required by the Critical/coverage rule is scheduled without a
  numeric cap, and concurrency waves never omit a required role;
- specialist coverage changes only through the declared `CURRENT`/`STALE`
  events, with eligible Critical areas staffed every dispatched round;
- all three helpers fail closed at their declared boundaries;
- evidence discovery records applicable code/document gates and gaps, executes
  only safe validated commands in the declared contained mapping, never
  installs tooling, and distinguishes required gates from supporting evidence;
- every non-FIX target-accessing role has sealed read-only inputs and an
  isolated write surface, and special target entries, run-root overlap, a
  missing deterministic delta contract, concurrent writer uncertainty,
  interrupted FIX, post-FIX gate failure, and final seal drift fail closed;
- the sole FIX role is ledger-bound and contained, every target change is
  manifest- and delta-validated, unrelated or external actions cannot advance
  state, and passing gates alone never verify a fix;
- existing safe mutation tooling or bounded manual mutation contributes
  supporting evidence without installation, score thresholds, or false
  terminal authority;
- every usable review report is reconciled through validated TRIAGE into the
  canonical ledger from its exact source-finding inventory, and only
  evidence-linked ledger transitions affect the two terminal verdicts;
- pending green-making dispositions receive tier-invariant adjudication and
  fail closed under malformed, failed, or undecided results, while an empty set
  dispatches no adjudicator;
- normal and multi-review holistic paths use the same canonical prompt;
- multi-review's verbatim custom-prompt opt-in delivers the exact canonical
  bytes or falls back without launching a wrapped prompt;
- every scheduled high/max multi-review slot uses the fixed CLI pair at tested
  tool defaults or exact explicit pins and uses its resolved fallback profile;
- every multi-review call uses one fresh round output directory and disposable
  whole-call home/scratch, live host client state remains non-writable,
  malformed or interfered-with output cannot become usable evidence, the
  interim shared-namespace limitation is disclosed, and seal drift from any
  review path voids the round instead of falling back;
- profiles can refine dispatch but cannot alter safety or convergence;
- state survives host/session restarts outside the sealed target without
  rebasing a deadline, including the immutable round-one ground-truth inventory
  and audited retirement mappings;
- a fresh independent final-readiness challenge can only uphold or block the
  mechanically eligible verdict, routes new findings through TRIAGE, and becomes
  stale after any target change;
- the final Markdown report explains selected policy, planned and completed
  staffing, gate commands/results, mutation evidence or its one-line follow-up,
  degraded/fallback behavior, evidence gaps, ledger state, and both verdicts;
- merge-ready means the qualified operational “no known material defect” claim
  from section 1 and never an assertion of proof; and
- `SKILL.md` is reviewed after implementation for missed behavior and needless
  residue, with effectiveness taking precedence over an arbitrary size target.

## 10. Migration and implementation sequence

Do not implement isolated tasks from the old 3,678-line plan. This design
absorbs the recovered simplification draft, the later verification amendments,
the repo-local multi-review v0.3 interface, and the subsequent Q&A decisions.

The bounded prototype has now been implemented, tested, and independently
reviewed. It demonstrated that deterministic policy is valuable, found and
closed several fail-open proof-binding paths, and showed that duplicating rich
artifact schemas produces an over-broad 2,000-line state boundary. It is an
evidence artifact, not the unchanged implementation foundation.

Use its observed interface and review findings to write the clean
replacement implementation plan for the prompt/report helper, prompt resources,
profiles, evidence discovery and execution, bounded FIX mapping, controller
rewrite, migration of focused fixtures, documentation, the late isolated
multi-review adapter, and final forward test. The ordinary path must work end to
end before the adapter is introduced, while adapter acceptance remains required
for MVP completion. The plan keeps the deterministic policy kernel,
`record_specialist_coverage`, structured seal-bound proof references, and
terminal recomputation, but replaces rich processor inputs with the compact
validated projections defined in section 3. Replace the old plan rather than
maintaining two active plans; Git remains the archive.

Before changing `SKILL.md` or any behavior-bearing role prompt, apply the
writing-skills RED/GREEN discipline: demonstrate the current behavior failure
with a focused fresh-context control, make the minimum guidance change, and
rerun the scenario. Ordinary code follows deterministic test-first development.
Independent review gates the amended design, the replacement plan, each
meaningful implementation slice, and final acceptance.

The implementation must preserve these previously verified boundaries even if
their old machinery is removed:

- the entire reviewer safety preamble belongs inside the canonical rendered
  prompt;
- unresolved placeholders or conditional menus never reach a reviewer;
- rating guidance has a dedicated self-read prompt home;
- the inventory and rating fixtures exercise real semantic and tier decisions
  rather than mere schema conformance;
- read-only adjudication retains its two-call fail-closed state machine; and
- each selected reviewer must produce a completed, usable report rather than a
  structurally plausible refusal.

Create `DESIGNING_PROFILES.md` alongside the implemented profile support. It is
an operator-facing schema and recipe guide, not always-loaded controller
content. Do not ship tracked selectable profiles in the repository.

Deferred work remains deferred until real usage supplies evidence: integration
with `review-team`, synthesis, arbitrary provider commands, profile
composition, per-area model maps, automatic provider capability benchmarking,
expanded observability artifacts, and broader platform portability.
