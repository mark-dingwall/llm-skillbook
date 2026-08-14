# Review Loop Redesign

**Status:** Draft of approved design; pending written-spec review

**Date:** 2026-08-14

## 1. Purpose and authority

This design defines the lean replacement for the unfinished review-loop tier
and roster plan. It is written for an implementer who has the repository but
none of the design conversation. After reading it, that implementer should be
able to plan the bounded prototype described in section 10 without reopening
settled product decisions.

Where this document conflicts with `PLAN-2026-07-28.md` or the recovered
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
run the existing quality gate and seal the target.

Dispatch one semantic inventory agent. It owns the canonical area IDs, aliases,
mapping decisions, consequence and `GENERALIST-MISS` evidence, surface
locators, and total specialist-priority order. Malformed output is discarded
and retried once; a second failure makes Stage 0 INDETERMINATE and the loop NOT
CONVERGED. When the operator supplies a tier, respect it and do not dispatch
rating agents merely to derive a competing tier.

When no tier is supplied, also dispatch two independent rating samples,
preferring different vendors where available. Two samples of one model are
acceptable when the host offers no real vendor diversity, but the report must
not describe them as independent model families. Each rater returns strict JSON
containing its complexity rating (`C`), risk rating (`R`), evidence, and any
declared gestalt factors. Both axes use the `low < med < high < max` ladder.
The inventory agent owns semantic identity; rating agents do not emit a
competing inventory.

The controller checks the current seal immediately before every target-accessing
process is launched and after each such process completes: inventory and rating
agents, ordinary holistic/adversarial/specialist reviewers, adjudicators, and
the multi-review driver. If members run concurrently, a post-completion mismatch
cancels the outstanding members. A mismatch voids all output from the affected
round or Stage 0, makes the loop NOT CONVERGED, and never takes a fallback
branch. The multi-review adapter performs these checks for its driver call; the
controller performs them for ordinary dispatch.

`FIX` is the sole authorized mutation window. Immediately before it, record the
current seal; immediately after it, regenerate the seal and verify that every
changed path is declared by the fix manifest and remains within the authorized
target. That post-FIX seal becomes the next round's baseline. The MVP assumes
the single user does not run a concurrent writer during this controller-owned
window; if exclusive mutation cannot be assured, stop NOT CONVERGED rather than
absorbing unexplained drift. Canonical state retains the Stage 0 seal and every
round baseline, not one run-wide seal.

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
and makes the loop NOT CONVERGED. The same-model allowance above applies to
these two samples in every round where rating is required.

An automatically derived `low`, `med`, or `high` tier proceeds without an
extra prompt. An automatically derived `max` tier pauses once before reviewer
dispatch unless the operator explicitly requested no confirmation. If the
operator declines or does not confirm, stop cleanly and retain the completed
inventory/rating state. An explicitly requested `max` tier already expresses
authority and does not prompt again. Hosts may expose the override as
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

Round 1 reviews the full sealed target. Later rounds review the changed target
files plus exact regular files containing the fix diff, fix manifest, relevant
ledger state, and refreshed risk inventory. Those generated inputs are sealed
as part of that round's input set. A `max` round-2 multi-review uses this
focused scope; it repeats a full target review only when the operator explicitly
requests one.

### Inventory and specialist selection

Every inventory area carries a stable semantic ID, aliases, `CONSEQUENCE`,
attributed consequence evidence, evidenced `GENERALIST-MISS` or an explicit
absence, normalized `SURFACE` locators, and its place in the total specialist
priority order. The inventory agent decides area equivalence, dependency
relevance, consequence, and whether specialist depth is needed.
The state processor accepts only resolved semantic decisions; it never infers
an area identity from a path or a prior state record.

Each later-round refresh uses the one inventory agent at the run tier's normal
reviewer capability. Its strict JSON must contain the full inventory schema and
map every previously named area to one resolved continuing ID, an explicit
replacement/new ID, or `RETIRED`. It also receives whether each area has a valid
prior specialist report and refreshes the total priority order accordingly. An
absent or ambiguous mapping, malformed JSON, missing field, or partial inventory
makes the whole output malformed and consumes its one retry. A second failure
makes the started round INDETERMINATE and the loop NOT CONVERGED; stop before
roster dispatch, record no roster or coverage update, and count it as an
attempted round. Never reuse a stale inventory.

`CONSEQUENCE` uses `Minor < Important < Critical`. Across inventory refreshes,
retain the highest consequence ever stated, every attributed consequence and
`GENERALIST-MISS` evidence line, and the union of evidenced surface locators.
An inventory omission or weaker restatement cannot lower historical consequence
or erase a coverage gap.

Before applying the specialist cap, an area is eligible when:

```text
tier == max OR (GENERALIST-MISS exists AND consequence meets threshold)
```

All current eligible areas are reconsidered every dispatched round. This MVP
does not implement quiet decay or numeric coverage counters; it records only
whether each area has a valid specialist report and the report's roster link.
A cap-omitted eligible area remains named and is prioritized ahead of already
covered areas next round. At CLOSE, an Important+ area with evidenced
`GENERALIST-MISS` and no valid specialist report for that area is a
merge-readiness blocker. If the tier threshold made that area ineligible, the
run may still be CONVERGED but is not merge-ready; the hand-back recommends a
new run at a tier that can staff it. Holistic mention alone is not specialist
coverage.

### Adjudication

After triage and before any green-making disposition becomes operative, collect
all pending reprieves in that round: rows proposed as REFUTED, file-authorized
INTENTIONAL rows, and rows whose current severity is below any reviewer-stated
Important+ severity, including rows ingested already downgraded. If the set is
non-empty, dispatch one read-only adjudicator pass. If it is empty, skip the
call. The adjudicator receives the pending rows, sealed scope inventory, and
ground-truth inventory, then reads the sources independently and searches for
evidence that contradicts the triager's disposition.

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
`UNDECIDED` decision and one evidence locator for every expected ledger ID.
Missing, unknown, or duplicate IDs; duplicate result blocks; a mismatched
expected-ID set; invalid decisions; or missing evidence makes the whole call
malformed. `UPHOLD` keeps the proposed disposition, `BOUNCE` restores the row,
and `UNDECIDED` is eligible only for the subset retry described next.

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
response to lead its review with a `## Summary` section and to end with exactly one
`REVIEW-STATUS: COMPLETE` line. A reviewer that cannot review the scope must
instead emit `REVIEW-STATUS: UNABLE` with a brief reason; it is not a usable
report. Step narration or a preamble may precede the heading. The shared
ordinary-report validator uses the established unanchored presence check for
`Summary` or `Executive Summary`, not a positional heading check, and requires
exactly one final `COMPLETE` status. Inventory, rating, and adjudication use
their strict-JSON validators instead. This prevents a structurally plausible
refusal from counting as a completed report. One shared fixture corpus exercises
the ordinary validator and the driver's opt-in classifier so their two
codebase-local implementations cannot drift silently.

The aggregate `REVIEW.md` itself need not begin with that heading; it begins
with metadata and wraps raw reports. The canonical holistic prompt works
unchanged in both paths; do not add a multi-review-only LLM instruction
fragment.

Prompt bodies never travel in process arguments. The adapter writes the driver
YAML to a transient per-round transport path outside the still-empty output
directory and passes only its path and short scalar options to the multi-review
driver. The driver writes its per-client prompt-body file under its output
directory and delivers prompts through stdin for supported clients; clients
without stdin receive only a short instruction naming that file. This preserves
the existing E2BIG protection.

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

- run identity, subject/base/head, exclusions, deployment context, Stage 0
  seal, and each round's input seal;
- requested tier/profile/deadline/overrides and their resolution;
- automatic ratings and evidence when rating ran;
- selected tier and tier source;
- named inventory areas, semantic IDs/aliases, consequence, semantic mapping
  decisions, and any valid specialist-report linkage;
- round roster including specialist area IDs, requested capability, resolved
  reviewer/model, completion, duration, and degraded/fallback reason;
- canonical ledger rows, provenance, dispositions, and fix manifests;
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
mapping of writable client state mounts for those two clients and the fresh
multi-review output directory. A profile cannot add a participant or mount:
adding another client is deferred until a containment mapping and adapter test
exist for it.

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
value is always positive integer seconds. Reviewer calls still retain their
normal per-call timeouts. Unknown keys, unknown versions, wrong types,
non-positive deadlines, and unsupported capability labels are errors.
`multi_review.models` may name only `claude` and `codex`, and each value must
be a non-empty string.

A model pin for any reviewer outside the fixed pair is invalid configuration. A
selected reviewer that is unavailable at runtime follows fallback handling.

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
pin: an unavailable or rejected pin makes that participant failed; the adapter
must not retry it without the pin or run it at a default model. With the fixed
two-reviewer MVP pair, that causes ordinary holistic fallback and a prominent
record of the failed pinned participant.

An operator may still directly instruct the orchestrator to use a particular
CLI for one ordinary, non-multi-review review. That one-off instruction must
use the controller's normal containment when a tested mapping exists. If none
exists, require explicit confirmation of uncontained execution and record that
bypass prominently; otherwise stop because the requested CLI cannot be honored.
This is not a reason to add arbitrary commands to profiles or override the
contained multi-review pair.

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
round seal, `reviewers: [claude, codex]`, any configured `models` entries, the
canonical prompt as `custom_prompt`, `synthesizer: none`, and the driver's
review-loop opt-in `require_complete_status: true`. Extend the v2 schema with
that optional boolean, defaulting to false, so other tasks and custom-prompt
callers retain the driver's current Summary-only behavior. The v2 validator
strictly requires only `prompt_format_version`, `task`, and `files`; the adapter
still writes every field above explicitly so reviewer and synthesizer defaults
cannot widen the call. An older driver rejects the unknown opt-in field and
therefore takes ordinary fallback rather than accepting refusals. Synthesis is
disabled, not merely non-authoritative.

The driver exit code is necessary but insufficient because the current driver
returns success when any classified report succeeds. The adapter independently
validates the driver's machine-readable result in `REVIEW.md` and accepts it
only when both fixed, distinct reviewers are recorded as successful. When the
opt-in above is true, extend the driver's existing per-report classifier with
the same unanchored Summary-presence and final completed-status contract before
it writes its existing frontmatter lists; do not add a sidecar report. The
adapter reads only the leading YAML frontmatter: the
document must begin with `---`, end that frontmatter at the first subsequent
line equal to `---`, and parse to the expected unique, disjoint success/failure
lists. It never splits the Markdown body on `---` or independently parses
reviewer sections. Thus a Markdown rule, embedded YAML, or diff in a raw report
cannot change the count. Any failed participant or malformed frontmatter takes
the ordinary holistic fallback; the run is marked degraded and names the
failure.

The aggregate `REVIEW.md` is passed whole to ordinary holistic triage as one
opaque report. Triage does not understand multi-review vendors, roster
selection, or aggregation internals. Retained raw reports remain the evidence,
but there is no second merge/dedup/synthesis implementation inside
review-loop.

Bubblewrap is required. The adapter mounts the sealed review target read-only,
bind-mounts only that round's fresh multi-review output directory at the same
absolute path as writable state, read-only binds the driver YAML and exact
later-round input artifacts from the run directory, and adds the explicit
client-state mounts for `claude` and `codex`. Canonical state, the ledger, prior
rounds, and the rest of the run root are not mounted writable. These binds are
required even below `$HOME`: the containment recipe
tmpfs-mounts `$HOME`, so host paths otherwise do not exist in the sandbox. The
adapter preserves required network access and performs the seal checks around
the call. Exact mount and environment recipes belong in the implementation plan
and adapter tests, not in `SKILL.md`. There is no multi-review containment bypass
in the MVP.

The adapter requests ordinary holistic fallback and records the reason when
the seal still matches and:

- the driver is missing or cannot start;
- Bubblewrap is missing or unusable;
- the driver exits unsuccessfully or produces malformed/inconsistent output;
- either fixed participant lacks a valid completed report;
- the adapter cannot enforce its deadline or validation contract.

A target-seal mismatch is not a reviewer availability failure and never takes
the fallback branch. It voids every report produced for that round or Stage 0,
marks that stage INDETERMINATE, and makes the current loop NOT CONVERGED. Do not
dispatch against a changed tree under an old seal. Only the controller-owned
FIX transition may establish the next round's seal within the same loop.

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

When the run-level deadline expires, stop launching work and terminate the
active call or batch using its normal deadline mechanism. Recheck the seal,
retain completed raw evidence as non-operative, mark the current stage or round
INDETERMINATE, and return NOT CONVERGED. Deadline expiry never becomes a clean
or partially completed round.

## 9. Testing and MVP acceptance

### Deterministic tests

Give each helper ordinary unit and contract tests.

The state processor tests tier lookups, strict schemas, rating combination,
one-time gestalt step-up, consequence monotonicity, single-owner re-inventory
mappings, malformed/ambiguous-map retries, `GENERALIST-MISS` eligibility,
uncovered-first priority filtering and cap application, area-linked specialist
coverage, both second-call adjudication paths, ledger-ID-bound user acceptance,
valid and invalid ledger transitions, pre- and post-roster INDETERMINATE
accounting, per-round seals, deadline expiry, and terminal rollups.

The prompt/report helper tests exact declared substitutions, explicit fragment
selection, template-token failures without rescanning substituted data,
preservation of the safety boundary for every target-accessing role, the
unanchored `Summary` and completed-status classifier for all ordinary review
roles, strict-JSON role validation, and byte-equivalent use for ordinary and
multi-review holistic dispatch.

The adapter tests with controlled fake processes and reports: normal success,
the opt-in completed-status classifier without changing other driver tasks,
rejection of the opt-in by an older driver, missing completed reports,
unexpected/duplicate reviewer IDs, malformed frontmatter, body delimiters that
resemble frontmatter fences, driver failure, missing Bubblewrap, deadlines, and
ordinary fallback. Separate tests prove that every scheduled call gets one
fresh empty output directory, only that directory is writable inside the
`$HOME` tmpfs recipe, exact later-round inputs are readable, canonical state and
prior rounds are not writable, no multi-review retry occurs, and pre/post seal
drift from every review path voids the stage without fallback. It also asserts
that prompt bodies never appear in process arguments.

Profile tests cover name and explicit-path resolution, version and unknown-key
rejection, sparse overlays, positive-integer deadlines, ordinary/fallback
holistic inheritance, minimum fixed-pair configuration, non-empty model values,
unsupported pins, honored or failed participant pins without default-model
substitution, missing profiles, and non-overridable safety fields.

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
- pending green-making dispositions receive tier-invariant adjudication and
  fail closed under malformed, failed, or undecided results, while an empty set
  dispatches no adjudicator;
- normal and multi-review holistic paths use the same canonical prompt;
- every scheduled high/max multi-review slot follows the tier table and its
  resolved fallback profile;
- every multi-review call uses one fresh round output directory, while
  its output directory remains writable under containment and seal drift from
  any review path voids the round instead of falling back;
- profiles can refine dispatch but cannot alter safety or convergence;
- state survives host/session restarts outside the sealed target;
- the final Markdown report explains selected policy, actual execution,
  degraded/fallback behavior, ledger state, and both verdicts; and
- `SKILL.md` is reviewed after implementation for missed behavior and needless
  residue, with effectiveness taking precedence over an arbitrary size target.

## 10. Migration and implementation sequence

Do not patch D7 in isolation or execute the old 3,678-line plan. This design
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
