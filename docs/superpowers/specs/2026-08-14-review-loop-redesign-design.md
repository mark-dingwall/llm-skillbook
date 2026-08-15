# Review Loop Redesign

**Status:** Reviewed design; ready for bounded prototype planning

**Date:** 2026-08-14

## 1. Purpose and authority

This design defines the lean replacement for the unfinished review-loop tier
and roster plan. It is written for an implementer who has the repository but
none of the design conversation. After reading it, that implementer should be
able to plan the bounded prototype described in section 10 without reopening
settled product decisions.

Where this document conflicts with the [archived tier-and-roster
plan](../../history/review-loop/PLAN-2026-07-28.md) or the recovered
`SIMPLIFY-DEF.md`, this document governs new work. Those documents are
historical inputs, not implementation authority.

The redesign preserves the loop's purpose and safety model while making its
cost proportional to risk and its prompt footprint smaller. It retains:

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
provider benchmarking, an event log, command transcripts, copied inputs, or a
portable non-GNU sealing implementation.

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

### Prefer explicit, unsurprising control

Operator-supplied intent wins. Never silently ignore a tier, profile, model
pin, reviewer selection, deadline, or confirmation override. Never silently
replace an invalid profile with defaults. Record the selected policy and what
actually ran.

## 3. Architecture

The skill is a thin controller over focused prompt resources and three focused
helpers:

1. **Review-state processor.** Consumes validated JSON and produces validated
   JSON. It applies tier lookups, combines already-assigned values, advances
   ledger and inventory state, and computes terminal rollups. It never reads
   or interprets the review target.
2. **Canonical prompt/report contract.** Renders a declared template and
   explicit fragments from a JSON context, and validates raw Markdown review
   reports. It is the sole production and fixture path for every dispatched
   LLM prompt and the sole ordinary-dispatch report classifier.
3. **Multi-review adapter.** Converts one canonical holistic request into the
   repo-local multi-review driver's v2 prompt file, invokes it under the required
   containment policy, validates its report, and returns either a usable
   holistic report or a structured fallback reason.

These are separate units, not one mixed script and not a plugin framework. Each
has a narrow interface and independent tests. They may share small data types
or validation utilities only when doing so removes real duplication without
coupling their lifecycles.

Focused prompt resources contain the detailed charters for inventory, rating,
adjudication, holistic review, adversarial review, and specialist review. Every
role reads a prompt rendered from those fixed skill-relative resources. The
controller carries only the resource identifier, task-local input, and required
output contract.

## 4. Review flow and effort tiers

### Preflight and Stage 0

Resolve invocation intent before dispatch: optional tier, profile, maximum time
in seconds, and confirmation override. A supplied maximum must be a positive
integer. Validate an explicitly selected profile before any agent runs. Then
resolve the full proposed run root and reject it when it equals, contains, or
is contained by the sealed target; do this before creating any artifact. Run the
existing quality gate and seal the target. The sealer accepts only directories
and readable regular files: a symlink, FIFO, socket, device, unreadable entry,
or an entry whose type or identity changes during enumeration fails preflight.
This establishes the Stage 0 **target-baseline seal**, which covers the whole
target tree.

At Stage 0, resolve the operator-designated ground-truth sources into one
ordered canonical inventory of exact regular-file locators and immutable file
identities. Persist that inventory in canonical state before any triage can
refer to it. An out-of-tree ground-truth source is included in every applicable
round-input seal; a missing or changed source fails closed rather than being
rediscovered or reconstructed from a digest after restart.

Dispatch one semantic inventory agent at `most-capable`. It owns the canonical
area IDs, aliases, mapping decisions, consequence and `GENERALIST-MISS`
evidence, surface locators, and total specialist-priority order. Malformed
output is discarded and retried once; a second failure makes Stage 0
INDETERMINATE and the loop NOT CONVERGED. When the operator supplies a tier,
respect it and do not dispatch rating agents merely to derive a competing tier.

When no tier is supplied, also dispatch two `most-capable` rating samples,
preferring different vendors where available. Two samples of one model are
acceptable when the host offers no real vendor diversity, but the report must
not describe them as independent model families. Each rater returns strict JSON
containing its complexity rating (`C`), risk rating (`R`), evidence, and any
declared gestalt factors. Both axes use the `low < med < high < max` ladder.
The inventory agent owns semantic identity; rating agents do not emit a
competing inventory.

The controller checks the applicable expected seals immediately before every
target-accessing process is launched and after each such process completes:
inventory and rating agents, ordinary holistic/adversarial/specialist
reviewers, triagers, adjudicators, and the multi-review driver. The **target-baseline
seal** always means the last accepted whole-target identity. After immutable
out-of-tree inputs for a round exist, a separate **round-input seal** references
that target baseline and hashes those exact generated inputs; it does not
replace or redefine the target baseline. A process must match every seal for
the inputs it can read. If members run concurrently, a post-completion mismatch
cancels the outstanding members. A mismatch voids all output from the affected
round or Stage 0, makes the loop NOT CONVERGED, and never takes a fallback
branch. The multi-review adapter performs these checks for its driver call; the
controller performs them for ordinary dispatch.

Every ordinary target-accessing role, including TRIAGE, uses a tested host
execution mapping that enforces read-only access to its sealed target and
round-input scope. The mapping exposes no writable canonical state, peer
artifacts, or prior-round artifacts, and permits writes only to that call's
fresh controller-owned report channel and disposable scratch. The controller
records the call outcome and atomically publishes the validated report only
after the call exits, so a peer cannot replace it. The prompt's read-only
instruction is not authorization. If the selected CLI has no tested mapping,
the controller does not dispatch it; there is no uncontained ordinary review
bypass. Seal checks remain necessary detection and fail-closed evidence
handling, not a substitute for read-only execution and not rollback machinery.

`FIX` is the sole authorized mutation window. In this MVP it is an explicit
controller-to-single-operator hand-off, not an LLM role or a generic command
executor. Before entering it, the controller binds the window to exact current
`OPEN` ledger IDs. The operator supplies a fix manifest that associates every
declared changed target path with one or more of those IDs; a manifest cannot
itself alter ledger state. Immediately before the hand-off, recompute the whole
target identity and compare it with the last verified target-baseline seal. A
mismatch stops NOT CONVERGED; never record the mismatching identity as a new
baseline. Only after that comparison succeeds may the controller record the
verified pre-FIX identity and record `FIX_STARTED` before entering `FIX`.
Immediately afterward, regenerate the whole-target identity and verify its delta
from that pre-FIX identity: every changed path must be declared by the fix
manifest and remain within the authorized target. Run the quality gate, then
recompute the identity once more; the gate must pass and that identity must
equal the verified post-FIX identity before it becomes the next round's
target-baseline seal. After that equality succeeds, atomically transition every
and only currently `OPEN` ledger row with a manifest-bound, verified changed
target path to `FIX_APPLIED`, recording its manifest and target-baseline linkage.
Rows without that verified linkage remain `OPEN`. A failed post-FIX gate or
changed post-gate identity stops NOT CONVERGED before another reviewer runs. A
missing or malformed manifest, a
changed path without an authorized ledger-ID association, or an operator who
declines to fix prevents a successful FIX transition; the ledger remains
operative for CLOSE. If the operator declines before mutating, recompute the
target identity, require it to equal the verified pre-FIX identity, record no
`FIX_APPLIED` transition, and restore the bound rows to `OPEN`; it establishes
no new baseline. If the host or session interrupts
after `FIX_STARTED` and before this post-FIX verification succeeds, record the
round INDETERMINATE and return NOT CONVERGED. A restarted controller may retain
the evidence for its hand-back but must not resume that run or establish a new
baseline; start a new run instead. From the Stage 0 target-baseline seal until
the run cancels or reaches CLOSE, the single-user MVP assumes no concurrent
writer other than this controller-authorized FIX hand-off. If the operator
cannot assure that exclusivity before a target-accessing dispatch or during
FIX, stop NOT CONVERGED rather than accepting an ABA-style restored seal.
Canonical state retains the Stage 0 target baseline, each verified pre-FIX
identity, each round's target baseline, and each round-input seal rather than
one overloaded run-wide seal.

Immediately before CLOSE computes either terminal verdict, recompute the whole
target identity and compare it with the last accepted target-baseline seal. A
mismatch is NOT CONVERGED; it cannot produce a verdict for bytes that no
reviewer saw.

The state processor merges already-decided values mechanically: take the
maximum `C` across raters, take the maximum `R` across raters, then take the
maximum of those two merged axes as the base tier. If both merged axes are at
least `high`, step up once. Then, if any rater supplied a valid `GESTALT: +1`
decision with at least three individually evidenced factors, step up once more
regardless of how many raters supplied one. Cap the result at `max`.

The rater makes the semantic gestalt decision. The processor validates its
declared structure and applies the arithmetic; it never decides whether
factors form a gestalt, invents a factor, or applies the gestalt step more than
once.

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

| Tier | Specialist threshold | Specialist cap | Round cap | Normal reviewer capability | Multi-review timing |
|---|---|---:|---:|---|---|
| `low` | Critical only | 2 | 2 | mid-tier | never |
| `med` | Important+ | 3 | 3 | mid-tier | never |
| `high` | Important+ | 5 | 5 | one-above-mid | round 1 |
| `max` | every named area eligible | 5 | 5 | most-capable | rounds 1 and 2 |

The round cap is a ceiling, not a quota. Close as soon as the invariant ledger
conditions are satisfied.

The capability column governs ordinary review roles, including ordinary
holistic fallback; it does not configure multi-review participants.
Multi-review uses each fixed CLI's tested tool default unless the profile
supplies an explicit model pin. Do not add a new fan-out capability abstraction
for the MVP.

Every round retains holistic and adversarial review. Multi-review replaces
only the holistic slot; it never replaces adversarial or specialist review.
Specialists are selected from the named inventory under the tier threshold and
cap. The threshold decides eligibility; it does not override the independently
selected cap. The processor filters the inventory agent's validated total
priority order to eligible IDs and applies the cap; there is no separate
ranking call. The agent orders never-covered eligible areas before areas with a
valid prior specialist report, then ranks semantically by consequence and
evidenced need for depth. Every specialist roster entry carries its area ID.
Every omitted area records `Not staffed`, the cap or threshold reason, and
whether a valid specialist report for that area exists in prior round state.

Round 1 reviews the full sealed target. Later-round holistic and adversarial
reviewers receive the changed target files plus exact regular files containing
the fix diff, fix manifest, relevant ledger state, and refreshed risk
inventory. A staffed specialist additionally receives the sealed regular target
files resolved from that area's current `SURFACE` locators, including unchanged
files needed to inspect the chartered area. A qualified non-file locator must
resolve to its owning target file before dispatch. Missing, escaping, or
ambiguous locator resolution makes the started round INDETERMINATE before
reviewer dispatch; it never counts as coverage. Those generated inputs are
sealed as part of the round's input set. A `max` round-2 multi-review uses the
focused holistic scope; it repeats a full target review only when the operator
explicitly requests one.

### Inventory and specialist selection

Every inventory area carries a stable semantic ID, aliases, `CONSEQUENCE`,
attributed consequence evidence, evidenced `GENERALIST-MISS` or an explicit
absence, normalized `SURFACE` locators, and its place in the total specialist
priority order. The inventory agent decides area equivalence, dependency
relevance, consequence, and whether specialist depth is needed.
The state processor accepts only resolved semantic decisions; it never infers
an area identity from a path or a prior state record.

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
hide one. It also receives whether each area has a valid prior specialist report
and refreshes the total priority order accordingly. An absent or ambiguous
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
cap-omitted area, a rename, move, or merge (which uses a continuing or successor
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

Before applying the specialist cap, an area is eligible when:

```text
tier == max OR (GENERALIST-MISS exists AND consequence meets threshold)
```

All current non-retired eligible areas are reconsidered every dispatched round.
This MVP does not implement quiet decay or numeric coverage counters; it records
only whether each area has a valid specialist report and the report's roster
link. A cap-omitted eligible area remains named and is prioritized ahead of
already covered areas next round. At CLOSE, a current non-retired Important+
area with evidenced `GENERALIST-MISS` and no valid specialist report for that
area is a merge-readiness blocker. A valid retired area is neither eligible for
staffing nor a merge-readiness coverage blocker. If the tier threshold made an
active area ineligible, the run may still be CONVERGED but is not merge-ready;
the hand-back recommends a new run at a tier that can staff it. If the cap still
leaves active gaps at `max`, the hand-back names them and recommends narrowing or
splitting the review target; the controller does not invent a higher tier,
exceed the cap, or loop without bound. Holistic mention alone is not specialist
coverage.

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
record and requires its reported severity and required source locators to be
preserved exactly in triage provenance; TRIAGE may add separate current evidence
but cannot weaken, replace, or omit that raw premise. Every listed finding
record has a canonical ID, aliases and source report and finding IDs, source
locators, reported and current severity,
`CONFIRMED`/`PLAUSIBLE`/`UNVERIFIABLE` factual status, proposed ledger state,
provenance, and evidence locators. The controller rejects unknown, missing, or
duplicate report and finding IDs, report IDs not matching the usable raw-report
set, any reported-severity or required-source-locator mismatch, invalid
state/factual combinations, missing source or evidence locators, and any result
whose applicable seal differs. It derives "reviewer-stated Important+" only
from that immutable raw inventory. It retries one malformed or failed triage
call once. A second failure makes the round INDETERMINATE and NOT CONVERGED
without FIX or coverage update.

The ledger has exactly five states: `OPEN`, `FIX_APPLIED`, `FIX_VERIFIED`,
`REFUTED`, and `INTENTIONAL`. New findings and any finding reactivated by new
conclusive evidence enter `OPEN`. `OPEN -> FIX_APPLIED` requires a fix-manifest
entry bound to that exact ledger ID. A later triage result may return
`FIX_APPLIED -> OPEN` when the failure remains or its evidence is inconclusive.
`FIX_APPLIED -> FIX_VERIFIED` requires that result to cite both the manifest
entry and sealed current-target evidence that the original failure no longer
occurs. An empty report, reviewer silence, a passing quality gate, or the
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
quality gate passed for the final sealed target, every Important+ row is
`FIX_VERIFIED`, `REFUTED`, or an explicitly recorded `INTENTIONAL` exception,
and no current non-retired Important+ specialist-coverage blocker remains.
Open Minor rows are reported but do not by themselves prevent either verdict.

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
`UNDECIDED` decision and one evidence locator for every expected ledger ID. An
`UPHOLD` repeats the exact authority identity and a positive proposition-to-row
linkage that supports the reprieve; it is invalid when that linkage merely says
no contradiction was found. Missing, unknown, or duplicate IDs; duplicate
result blocks; a mismatched expected-ID set; invalid decisions; or missing
evidence makes the whole call malformed. `UPHOLD` keeps the proposed
disposition, `BOUNCE` restores the row, and `UNDECIDED` is eligible only for the
subset retry described next.

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
later-round, inventory, rating, adjudication, holistic, adversarial, or
specialist. Templates do not contain a general control language, and bracketed
prose is never interpreted as a menu.

Before substitution, the helper fails on:

- missing declared values;
- unknown values supplied by the caller;
- unknown template or fragment names; or
- undeclared or unresolved substitution tokens in the selected template or
  fragments.

Substituted values are opaque data; literal `{{...}}` text inside subject
material is never rescanned as template syntax. The rendered bytes are the
production prompt and the test fixture input. Every target-accessing LLM prompt
preserves the existing boundary: subject material is labelled data, the role is
read-only against the seal, and the role reports rather than fixes.

Every holistic, adversarial, and specialist prompt asks each raw reviewer
response to lead its review with a `## Summary` section, include exactly one
fenced strict-JSON `review-record`, and make its last non-blank line exactly one
terminal record: `REVIEW-STATUS: COMPLETE`, or `REVIEW-STATUS: UNABLE` when it
could not review the scope. The record contains the controller-issued
`request_id`, role, charter identifier, target-baseline seal, `round_input_seal`
(null only in Stage 0), the exact dispatched scope-locator IDs, and a
`source_findings` array. It has no other fields. Every source finding has a
unique ID, `Minor`/`Important`/`Critical` severity, and one or more source
locators; an explicit empty array means no findings. The record is the
source-finding universe: narrative observations without an entry are not a
reported finding and cannot affect the ledger. `UNABLE` may be explained briefly
in the preceding body and is not a usable report. Step narration or a preamble
may precede the heading. A usable report also requires the controller to have
recorded successful completion of that exact dispatched `request_id` and a
unique controller-assigned raw `report_id`; the validator must match every
record field to its dispatch. The established
unanchored presence check for `Summary` or `Executive Summary` remains a
compatibility/display check, not sufficient completion evidence. Earlier
status-looking text is body data, so quoted source material cannot create or
invalidate completion. The terminal line must match exactly; trailing prose or
an absent/unknown status is invalid. Inventory, rating, and adjudication use
their strict-JSON validators instead. The review-loop multi-review opt-in
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
launching each client it writes and byte-compares that client's prompt-body file
against the payload, then delivers only those bytes. It adds no injection or
reference preamble, title, context body, file manifest, delimiter, or trailing
newline. The required `files` list still validates sealed scope and controls
what the contained clients can read; it is not rendered into the prompt body.
A mismatch is a driver validation failure. Existing non-review-loop tasks and
custom-prompt callers retain the current wrapped behavior unless they opt in.

Prompt bodies never travel in process arguments. The adapter writes the driver
YAML to a transient per-round transport path outside the still-empty output
directory and passes only its path and short scalar options to the multi-review
driver. The driver writes any per-client prompt-body file to that client's
read-only input view, separate from its private aggregation directory, and
delivers prompts through stdin for supported clients; clients without stdin
receive only a short instruction naming that file. This preserves the existing
E2BIG protection without granting a client access to driver-owned artifacts.

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

At minimum, canonical state records:

- run identity, subject/base/head, exclusions, deployment context, the Stage 0
  start and resolved absolute deadline when one exists, the Stage 0 target
  baseline, every verified pre-FIX identity and subsequent target baseline, and
  each round-input seal;
- lifecycle status, including `CANCELLED_BEFORE_REVIEW` and its reason when
  applicable;
- requested tier/profile/deadline/overrides and their resolution;
- automatic ratings and evidence when rating ran;
- selected tier and tier source;
- the ordered round-one ground-truth inventory with exact locators and immutable
  identities;
- named inventory areas, semantic IDs/aliases, consequence, semantic mapping
  decisions including every `retirement_reason`, current active status, priority
  order, and any valid specialist-report linkage;
- round roster including specialist area IDs, requested capability, resolved
  reviewer, requested capability or model argument, dispatch outcome,
  completion, duration, and degraded/fallback reason;
- immutable per-dispatch validation tuples: `request_id`, controller-assigned
  raw `report_id`, role, charter identifier, expected target/round-input seals,
  exact scope-locator IDs, and completion outcome;
- canonical ledger rows, raw-report mappings, provenance, dispositions,
  fix-verification evidence, and fix manifests;
- pending adjudication sets, call outcomes, final decisions, and atomic
  bounce/restoration results; and
- convergence, merge-readiness, and the exact failed terminal conjunct when a
  run does not converge.

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

A bare name resolves only to:

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
a non-empty `files` list of exact regular input paths covered by the current
round-input seal, `reviewers: [claude, codex]`, any configured `models` entries,
the canonical prompt as `custom_prompt`, `verbatim_custom_prompt: true`,
`synthesizer: none`, the driver's review-loop opt-in
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

The driver exit code is necessary but insufficient because the current driver
returns success when any classified report succeeds. The adapter independently
validates the driver's machine-readable result in `REVIEW.md` and accepts it
only when both fixed, distinct reviewers are recorded as successful. When the
opt-in above is true, the driver validates each participant's complete terminal
line and exactly one strict `review-record` against the non-prompt expectation
before accepting it. For each accepted fixed slot, the driver selects that
slot's controller-preallocated raw `report_id` and writes, in the existing leading
YAML frontmatter, a participant-qualified record containing that ID, the shared
`request_id`, and the validated `source_findings` inventory. It writes no
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

The aggregate `REVIEW.md` is retained whole as evidence. From its validated
frontmatter, the adapter mechanically presents TRIAGE one opaque usable-report
envelope with a controller-assigned aggregate `report_id` and the exact union of
participant-qualified source finding IDs, severities, and locators. TRIAGE does
not understand multi-review vendors, roster selection, or aggregation internals
and does not parse the body. The envelope is one report: its source-report ID is
the aggregate ID and each source-finding ID is the pair of participant raw
`report_id` and that participant's source-finding ID. This is provenance
preservation rather than a second merge, deduplication, or synthesis
implementation inside review-loop.

Bubblewrap is required. The adapter gives the driver a private aggregation and
staging directory and read-only binds the driver YAML plus only the exact sealed
regular inputs for that call. In Round 1, those target inputs are the full
sealed target regular-file set; in a later focused round they are only the
declared changed/surface target files and exact run artifacts. The driver's YAML
`files` list names the same sealed call-input set, so it both validates and
limits what contained clients can read. The repo-local driver checkout, interpreter or
managed environment, CLI executables, libraries, and required package/cache
content are also available read-only so the tested command can actually start
under containment.

No live host client-state directory, including `~/.claude` or `~/.codex`, is
writable in the sandbox. Each fixed client gets its own fresh scratch home/state
directory for that driver call, discarded after evidence has been retained. Each
client starts in its own child Bubblewrap/mount-namespace view, constructed by
the driver from the adapter's exact call-input mapping. That view omits the
private aggregation/staging directory—including `.REVIEW.md.tmp`, final
`REVIEW.md`, and any driver-only transport staging. The driver captures client
output, terminates/reaps the client's process group before aggregation, and
alone publishes the final report. Bind only the minimum exact
credential/configuration files needed to authenticate as read-only;
client-generated caches, session files, and other mutable state are written to
scratch.

Any host settings file that can define executable hooks remains read-only and
is not copied into mutable scratch. Scratch is never reused or promoted back to
host state. Canonical state, the ledger, prior rounds, and the rest of the run
root are not mounted writable. These explicit binds are
required even below `$HOME`: the containment recipe tmpfs-mounts `$HOME`, so
host paths otherwise do not exist in the sandbox. The adapter preserves
required network access and performs the seal checks around the call. Exact
mount and environment recipes belong in the implementation plan and adapter
tests, not in `SKILL.md`. There is no multi-review containment bypass in the
MVP.

The adapter requests ordinary holistic fallback and records the reason when
the seal still matches and:

- the driver is missing or cannot start;
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

The state processor tests tier lookups, strict schemas, rating combination,
one-time gestalt step-up, consequence monotonicity, single-owner re-inventory
mappings including bijective IDs and priority order, malformed/ambiguous-map
retries, `RETIRED` definitions and missing, blank, or multiline
`retirement_reason` rejection, `GENERALIST-MISS` eligibility, uncovered-first
priority filtering and cap application, area-linked specialist coverage and
later-round surface resolution, both second-call adjudication paths,
ledger-ID-bound user acceptance, strict-JSON TRIAGE report/retry behavior,
exact source-finding reconciliation, positive reprieve-proof validation, valid
and invalid ledger transitions including `FIX_APPLIED -> OPEN` and adjudicated
settlements, proof-linked `FIX_VERIFIED` transitions, pre- and post-roster
INDETERMINATE accounting, compare-before-record FIX entry, atomic verified
`OPEN -> FIX_APPLIED`, manifest ledger-ID/path validation, post-FIX quality-gate
failure, interrupted-FIX restart refusal, declined automatic-max cancellation,
expiry during confirmation and after TRIAGE before CLOSE, distinct target-baseline
and round-input seals, final-CLOSE seal drift, durable round-one ground truth,
persisted-deadline recovery, and both terminal rollups.

The prompt/report helper tests exact declared substitutions, explicit fragment
selection, template-token failures without rescanning substituted data,
preservation of the safety boundary for every target-accessing role, the
display-only unanchored `Summary` check, strict `review-record` validation for
all ordinary review roles, quoted status-looking source lines followed by one
terminal status, mismatched dispatch/seal/scope records, source-finding ID
uniqueness, immutable source severity/locator provenance, strict-JSON role
validation, and byte-equivalent use for ordinary and multi-review holistic
dispatch.

The adapter tests with controlled fake processes and reports: normal success,
the opt-in strict review-record classifier without changing other driver tasks,
rejection of either opt-in by an older driver, byte-equivalent verbatim custom
prompt transport, prompt-body mismatch failure, missing completed reports,
unexpected/duplicate reviewer IDs, malformed frontmatter, body delimiters that
resemble frontmatter fences, missing/malformed/mismatched participant review
records, participant-qualified frontmatter provenance, duplicate/swapped
fixed-slot raw IDs, driver failure, missing Bubblewrap, deadlines, recognized
zero-exit pin-downgrade signals, and ordinary fallback. Separate
tests prove that every scheduled call gets one fresh empty driver-private output
directory; the driver, interpreter/environment, fixed CLIs, and required
read-only package content can start inside the `$HOME` tmpfs recipe; exact
later-round inputs are readable; and an unlisted target file is unreadable.
Clients may write only their fresh scratch, while the driver alone can write or
publish prompt transport and aggregate artifacts. Fake clients and descendants
attempting to alter prompt transport, `.REVIEW.md.tmp`, or `REVIEW.md` must fail
and lead to fallback. Live host client state, canonical state, and prior rounds
remain non-writable; scratch cannot persist hooks or other state to the host.
Tests also prove that no multi-review retry occurs, expiry is checked before
fallback and CLOSE, pre/post seal drift from every review path voids the stage
without fallback, and prompt bodies never appear in process arguments. Controller
tests also prove that an ordinary role cannot write a peer report or canonical
state.

Profile tests cover name and explicit-path resolution, version and unknown-key
rejection, sparse overlays, positive-integer deadlines, ordinary/fallback
holistic inheritance, minimum fixed-pair configuration, non-empty model values,
duplicate YAML mapping keys at every depth, permitted normal-role pins versus
fixed-pair-only `multi_review.models` pins, exact pinned-model command
construction without default-model arguments, documented rejection/downgrade
signals and rejected pins causing participant failure, no substitute for an
explicit normal-role pin, missing profiles, and non-overridable safety fields.
Controller tests also reject a resolved run root that overlaps the sealed target
and an ordinary CLI with no tested containment mapping.

### LLM behavior tests

Use targeted RED/GREEN pressure scenarios only where a pre-change baseline
demonstrates a real behavior failure. Preserve the production prompt boundary
and keep ground truth outside the dispatched prompt. Retain focused coverage
for rating quality, semantic area identity/re-inventory, and reviewer behavior
whose efficacy depends on prose. Preserve the focused existing adjudication
fixture for independent disposition checking and its malformed/crashed-call
behavior. Do not recreate dual-model requirements, large manifests, input-hash
bureaucracy, or fixtures for wording-only edits.

### Acceptance criteria

The MVP is acceptable when:

- explicit and automatic tier paths produce the specified roster and round
  policy without changing completion semantics;
- auto-derived `max` is the only automatic tier that pauses;
- all three helpers fail closed at their declared boundaries;
- every ordinary target-accessing role has sealed read-only inputs and an
  isolated write surface, and special target entries, run-root overlap,
  concurrent writer uncertainty, interrupted FIX, post-FIX gate failure, and
  final seal drift fail closed;
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
- every multi-review call uses one fresh round output directory, while
  only the driver may write its private aggregation artifacts, disposable client
  scratch remains writable under containment, live host client state remains
  non-writable, and seal drift from any review path voids the round instead of
  falling back;
- profiles can refine dispatch but cannot alter safety or convergence;
- state survives host/session restarts outside the sealed target without
  rebasing a deadline, including the immutable round-one ground-truth inventory
  and audited retirement mappings;
- the final Markdown report explains selected policy, actual execution,
  degraded/fallback behavior, ledger state, and both verdicts; and
- `SKILL.md` is reviewed after implementation for missed behavior and needless
  residue, with effectiveness taking precedence over an arbitrary size target.

## 10. Migration and implementation sequence

Do not implement isolated tasks from the old 3,678-line plan. This design
absorbs the recovered simplification draft, the later verification amendments,
the repo-local multi-review v0.3 interface, and the subsequent Q&A decisions.

The next plan covers one bounded prototype first: implement and unit-test the
review-state processor against representative rating, tier, inventory mapping,
adjudication-bounce, and terminal-rollup JSON. Measure its interface and the
skill prose it can replace. This is an evidence gate, not permission to begin
the rest of the redesign opportunistically.

After the prototype is reviewed, use its observed interface to write the clean
replacement implementation plan for the prompt/report helper, prompt resources,
adapter, profiles, controller rewrite, migration of focused fixtures,
documentation, and final forward test. Replace the old plan rather than
maintaining two active plans; Git remains the archive.

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
with `codex-review-team`, synthesis, arbitrary provider commands, profile
composition, per-area model maps, automatic provider capability benchmarking,
expanded observability artifacts, and broader platform portability.
