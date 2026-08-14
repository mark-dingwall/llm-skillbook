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
- automatic effort-tier derivation, per-round re-inventory, quiet decay, and
  `specialist-covered-ever` state;
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
   ledger and inventory state, maintains decay fields, and computes terminal
   rollups. It never reads or interprets the review target.
2. **Canonical prompt renderer.** Renders a declared template and explicit
   fragments from a JSON context. It is the sole production and fixture path
   for reviewer prompts.
3. **Multi-review adapter.** Converts one canonical holistic request into the
   repo-local multi-review driver's v2 prompt file, invokes it under the chosen
   containment policy, validates its report, and returns either a usable
   holistic report or a structured fallback reason.

These are separate units, not one mixed script and not a plugin framework. Each
has a narrow interface and independent tests. They may share small data types
or validation utilities only when doing so removes real duplication without
coupling their lifecycles.

Focused prompt resources contain the detailed charters for initial rating,
re-inventory, adjudication, holistic review, adversarial review, and specialist
review. The rating, re-inventory, and adjudication agents read their own prompt
resources from fixed skill-relative paths. The controller carries only the
path, task-local input, and required output contract.

## 4. Review flow and effort tiers

### Preflight and Stage 0

Resolve invocation intent before dispatch: optional tier, profile, maximum
time, containment bypass, and confirmation override. Validate an explicitly
selected profile before any agent runs. Then run the existing quality gate,
seal the target, and inventory the sealed scope.

When the operator supplies a tier, respect it and do not derive a competing
tier. Run only the semantic inventory needed to name risk areas and build the
roster.

When no tier is supplied, dispatch two independent raters, preferring different
vendors where available. Two samples of one model are acceptable when the host
offers no real vendor diversity, but the report must not describe them as
independent model families. Each rater returns strict JSON containing its
inventory, complexity rating (`C`), risk rating (`R`), evidence, and any
declared gestalt factors. Both axes use the `low < med < high < max` ladder.
Ratings and semantic identity come from the raters.

The state processor merges already-decided values mechanically: take the
maximum `C` across raters, take the maximum `R` across raters, then take the
maximum of those two merged axes as the base tier. Record divergence when two
ratings on the same axis differ by at least two ladder positions. If both
merged axes are at least `high`, step up once. Then, if any rater supplied a
valid `GESTALT: +1` decision with at least three individually evidenced
factors, step up once more regardless of how many raters supplied one. Cap the
result at `max`.

The rater makes the semantic gestalt decision. The processor validates its
declared structure and applies the arithmetic; it never decides whether
factors form a gestalt, invents a factor, or applies the gestalt step more than
once.

Malformed rater output is discarded and retried once. Do not repair JSON,
infer omitted fields, or partially accept it. Fewer than two valid independent
ratings after retries makes Stage 0 indeterminate and stops before review
dispatch.

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
selected cap. Thus `max` makes every named area eligible but still staffs at
most five specialists. When eligible areas exceed the cap, the inventory agent
ranks them by consequence and evidenced need for depth; semantic ties are
resolved by the agent, not by a filename or alphabetical heuristic. The state
processor validates the supplied ranking and applies the cap. Every omitted
area records `Not staffed`, the cap/threshold/decay reason, and its remaining
coverage state.

Round 1 reviews the full sealed target. Later rounds review the fix diff, fix
manifest, relevant ledger state, and refreshed risk inventory. A `max` round-2
multi-review uses this focused later-round scope; it does not repeat a full
target review unless the operator explicitly requests it or the fixes expose a
materially new surface.

### Inventory, specialist eligibility, and decay

Every inventory area carries a stable semantic ID, aliases, `CONSEQUENCE`,
attributed consequence evidence, evidenced `GENERALIST-MISS` or an explicit
absence, normalized `SURFACE` locators, mapping status,
`specialist-covered-ever`, and `quiet` count. The LLM decides area equivalence,
dependency relevance, consequence, and whether specialist depth is needed.
The state processor accepts only resolved semantic decisions and owns the
coverage fields.

Each later-round refresh uses two attributed rater outputs at the run tier's
normal reviewer capability. Apply the same strict JSON, retry-once, and
two-valid-output floor as initial rating. Fewer than two valid refreshes makes
the round INDETERMINATE and stops before roster dispatch; do not reuse a stale
inventory or merge one rater with itself.

`CONSEQUENCE` uses `Minor < Important < Critical`. Across raters and rounds,
retain the highest consequence ever stated, every attributed consequence and
`GENERALIST-MISS` evidence line, and the union of evidenced surface locators.
A rater omission or weaker restatement cannot lower historical consequence or
erase a coverage gap.

Before applying the specialist cap, an area is staffed when:

```text
(tier == max OR (GENERALIST-MISS exists AND consequence meets threshold))
AND (consequence == Critical OR specialist-covered-ever == no OR quiet < 2)
```

The first line is eligibility; the second is decay. Critical areas never decay,
and decay cannot prevent an area's first specialist coverage. A cap-omitted
eligible area remains named and records its coverage gap.

On entry to a later round, reset effective `quiet` to zero before roster
selection when the fix diff touches an area's surface, a changed dependency or
contract feeds the area, or one of its ledger rows reopens. At round end update
the two processor-owned fields independently:

- Set `specialist-covered-ever: yes` when a specialist completed a valid report;
  otherwise preserve its prior value.
- Set `quiet: 0` after a new finding, reopened row, or entry touch. Otherwise,
  increment quiet when a specialist completed a valid report. If the specialist
  was not rostered, was NOT RUN, or produced no valid report after retries,
  preserve the prior quiet value.

A new area starts `specialist-covered-ever: no, quiet: 0`. A round-1 specialist
that completes silently produces `yes, quiet: 1`; two consecutive completed,
silent, untouched rounds therefore reach `quiet: 2` and decay before the next
roster. Decayed areas remain in the inventory and under holistic coverage so a
later touch can re-staff them immediately.

Ambiguous semantic mappings are never guessed and cannot inherit trusted
coverage or decay. Suppress decay for every implicated record; an unresolved
Important+ mapping is a merge-readiness blocker. Rating and refresh outputs
that attempt to author `specialist-covered-ever` or `quiet` are malformed,
because those fields belong to the state processor.

At CLOSE, an Important+ area with evidenced `GENERALIST-MISS` that never
received valid specialist coverage is a merge-readiness blocker, as is an
Important+ area with no coverage. An area that received valid specialist
coverage before later decaying is disclosed as decayed-after-coverage but is
not a blocker solely because it decayed.

### Adjudication

After triage and before any green-making disposition becomes operative,
dispatch one read-only adjudicator pass for all pending reprieves in that
round: rows proposed as REFUTED, file-authorized INTENTIONAL rows, and rows
whose current severity is below any reviewer-stated Important+ severity,
including rows ingested already downgraded. The adjudicator receives the
pending rows, sealed scope inventory, and ground-truth inventory, then reads
the sources independently and searches for evidence that contradicts the
triager's disposition.

User-confirmed risk acceptance during the current loop remains the direct
authority exception: record the quoted confirmation without pretending it is
file-adjudicable. Every other pending reprieve is tier-invariant and cannot
become operative without adjudication.

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
state. A second failed/malformed call bounces its entire attempted set; rows
still undecided after the subset retry also bounce. Never make a third call.

## 5. Prompts and report contracts

The renderer accepts JSON context plus a known template identifier. Templates
contain only declared `{{name}}` substitutions. Conditional material is
selected by the caller as explicit fragments such as round-one,
later-round, holistic, adversarial, or specialist. Templates do not contain a
general control language, and bracketed prose is never interpreted as a menu.

The renderer fails on:

- missing declared values;
- unknown values supplied by the caller;
- unknown template or fragment names; or
- any unresolved substitution token in the output.

The rendered bytes are the production prompt and the test fixture input. The
renderer preserves the existing prompt boundary: subject material is data,
reviewers are read-only against the seal, and reviewers report rather than fix.

The canonical holistic prompt requires each raw reviewer response to use
`## Summary` as its first major heading. This applies to an ordinary holistic
review and to every successful raw reviewer section produced by multi-review.
It does not require the aggregate `REVIEW.md` itself to begin with that heading;
the aggregate begins with metadata and wraps the raw sections. The heading is
useful to both ordinary agents and the multi-review driver, whose classifier
treats it as a structural sentinel. The canonical prompt must work unchanged
in both paths; do not add a multi-review-only LLM instruction fragment.

Prompt bodies never travel in process arguments. The adapter passes only paths
and short scalar options to the multi-review driver. The driver writes its
prompt file and delivers prompts through stdin for supported clients; clients
without stdin receive only a short instruction naming the prompt file. This
preserves the existing E2BIG protection. Generated prompt files and driver YAML
are transient and retained only while the run is active.

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

Each multi-review driver call receives a fresh, empty, atomically claimable
output directory. Scope it by round and attempt, for example:

```text
<run>/rounds/<round>/multi-review/<attempt>/
```

Never reuse the run root or a prior round/attempt directory as the driver's
`--out-dir`. Retries use a new attempt directory. After an active call ends,
retain evidence-bearing report content under the run directory and discard
only the transient prompt/YAML transport files according to the artifact rule
below.

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

- run identity, subject/base/head, exclusions, deployment context, and seal;
- requested tier/profile/deadline/overrides and their resolution;
- automatic ratings and evidence when rating ran;
- selected tier and tier source;
- named inventory areas, semantic IDs/aliases, consequence,
  `specialist-covered-ever`, and quiet count;
- round roster, requested capability, resolved reviewer/model, completion,
  duration, and degraded/fallback reason;
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
    reviewers: [claude, codex, opencode]
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
supplies one for that invocation; a per-run value overrides the profile.
Reviewer calls still retain their normal per-call timeouts. Unknown keys,
unknown versions, wrong types, and unsupported capability labels are errors.
If a `multi_review` block supplies `reviewers`, it must contain at least two
distinct reviewer IDs supported by the local driver.

Resolve the selected reviewer list, including inherited driver defaults,
before validating `models`. Every model key must name a supported reviewer in
that resolved selected list, and every model value must be a non-empty string.
A pin for an unselected reviewer is invalid configuration. A selected reviewer
that is unavailable at runtime follows degraded/fallback handling instead.

Profiles may choose known multi-review participants, pin their tool-specific
models, set normal-role capability labels or model pins, and set a maximum
time. They may not set the tier, alter round caps or staffing thresholds, add
arbitrary commands, enable synthesis, or weaken containment, the two-report
minimum, sealing, ledger transitions, or terminal rules. There is no
inheritance, include, stacking, or per-area specialist override in version 1.

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
be honored, stop and report it. Multi-review participant availability follows
the adapter's existing degraded/fallback contract instead. A profile that
selects an unavailable participant remains structurally valid; record that
participant's failure, use the run when at least two selected reports remain
valid, and otherwise fall back to the normal holistic reviewer. A participant-
specific model pin that makes that participant fail is handled the same way.

An operator may still directly instruct the orchestrator to use a particular
CLI for a one-off review. That is explicit invocation intent, not a reason to
add arbitrary command execution to profile files.

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

The prompt file sets `prompt_format_version: 2`, uses the canonical prompt as
`custom_prompt`, and sets `synthesizer: none`. Synthesis is disabled, not merely
non-authoritative. If a human later wants an overview, the orchestrating LLM
can summarize the retained evidence on request.

The driver exit code is necessary but insufficient because the current driver
returns success when any classified report succeeds. The adapter independently
validates `REVIEW.md` and accepts it only when at least two distinct raw
reviewer reports are structurally valid and recorded as successful. Partial
failure with at least two valid reports is usable and marked degraded; name the
failed reviewers in canonical state and the human report.

The aggregate `REVIEW.md` is passed whole to ordinary holistic triage as one
opaque report. Triage does not understand multi-review vendors, roster
selection, or aggregation internals. Retained raw reports remain the evidence,
but there is no second merge/dedup/synthesis implementation inside
review-loop.

Bubblewrap is required by default. The adapter mounts the sealed review target
read-only, provides only the writable state needed by the driver and reviewer
clients, preserves required network access, and verifies the target seal after
the call. Exact mount and environment recipes belong in the implementation
plan and adapter tests, not in `SKILL.md`.

An explicit `--yolo`-style containment bypass is optional for MVP: include it
only if it remains a small branch at the adapter boundary. If implemented, it
bypasses Bubblewrap only, is recorded prominently, and does not bypass the
two-report minimum, report validation, seal check, timeout, degraded status,
or fallback disclosure.

The adapter requests ordinary holistic fallback and records the reason when
the seal still matches and:

- the driver is missing or cannot start;
- Bubblewrap is missing or unusable and no explicit containment bypass applies;
- the driver exits unsuccessfully or produces malformed/inconsistent output;
- fewer than two distinct valid raw reports remain;
- the adapter cannot enforce its deadline or validation contract.

A target-seal mismatch is not a reviewer availability failure and never takes
the fallback branch. It voids every report produced for that round, marks the
round INDETERMINATE, and makes the current loop NOT CONVERGED. Do not dispatch
an ordinary reviewer against the changed tree under the old seal; continuing
requires a new loop with a fresh seal.

Fallback is automatic because it adds only the final branch to an adapter that
already owns invocation and validation. The fallback reviewer uses the
selected tier's normal holistic capability or explicit profile override. The
adversarial and specialist roster is unchanged. A fallback failure follows the
ordinary reviewer retry and indeterminate-round rules; it is never interpreted
as a clean review.

## 9. Testing and MVP acceptance

### Deterministic tests

Give each helper ordinary unit and contract tests.

The state processor tests tier lookups, strict schemas, rating combination,
divergence and one-time gestalt step-up, consequence monotonicity, complete
quiet-decay transitions, state-field ownership, `GENERALIST-MISS` eligibility,
cap application, ambiguous mappings, `specialist-covered-ever`, adjudication
bounce/restoration, valid and invalid ledger transitions, and terminal
rollups.

The renderer tests exact declared substitutions, explicit fragment selection,
missing/unknown/unresolved failures, preservation of the reviewer safety
boundary, the `## Summary` contract, and byte-equivalent use for ordinary and
multi-review holistic dispatch.

The adapter tests with controlled fake processes and reports: normal success,
partial degraded success, fewer than two reports, duplicate reviewer IDs,
malformed frontmatter/sections, driver failure, missing Bubblewrap, deadlines,
ordinary fallback, and containment-bypass semantics if implemented. Separate
tests prove that every round/attempt gets a fresh empty output directory and
that seal drift voids the round without fallback. It also asserts that prompt
bodies never appear in process arguments.

Profile tests cover name and explicit-path resolution, version and unknown-key
rejection, sparse overlays, ordinary/fallback holistic inheritance, minimum
distinct reviewers, inherited-reviewer resolution before model-map validation,
non-empty model values, unsupported/unselected pins, missing profiles, and
non-overridable safety fields.

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
  fail closed under malformed, failed, or undecided results;
- normal and multi-review holistic paths use the same canonical prompt;
- high/max multi-review timing and ordinary fallback match this design;
- every multi-review call uses a fresh round/attempt output directory, while
  seal drift voids the round instead of falling back;
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
review-state processor against representative rating, tier, inventory-decay,
adjudication-bounce, and terminal-rollup JSON. Measure its interface and the
skill prose it can replace. This is an evidence gate, not permission to begin
the rest of the redesign opportunistically.

After the prototype is reviewed, use its observed interface to write the clean
replacement implementation plan for the renderer, prompt resources, adapter,
profiles, controller rewrite, migration of focused fixtures, documentation,
and final forward test. Replace the old plan rather than maintaining two active
plans; Git remains the archive.

The implementation must preserve these previously verified boundaries even if
their old machinery is removed:

- the entire reviewer safety preamble belongs inside the canonical rendered
  prompt;
- unresolved placeholders or conditional menus never reach a reviewer;
- rating guidance has a dedicated self-read prompt home;
- the rating fixture exercises real tier/inventory decisions rather than mere
  schema conformance;
- read-only adjudication retains its two-call fail-closed state machine; and
- quiet decay and `specialist-covered-ever` survive the simplification.

Create `DESIGNING_PROFILES.md` alongside the implemented profile support. It is
an operator-facing schema and recipe guide, not always-loaded controller
content. Do not ship tracked selectable profiles in the repository.

Deferred work remains deferred until real usage supplies evidence: integration
with `codex-review-team`, synthesis, arbitrary provider commands, profile
composition, per-area model maps, automatic provider capability benchmarking,
expanded observability artifacts, and broader platform portability.
