# Feature Forge Checked-Skill MVP Design

**Date:** 2026-08-25

**Status:** Approved for implementation

## Purpose

Make Feature Forge's highest-value safety claims mechanically checkable while
keeping Feature Forge callable as a skill from Codex and Claude Code. The LLM
remains the controller and owns judgment. A small installed checker owns only
deterministic predicates. The tracked ledger remains durable workflow state,
and the user remains the authority for material decisions and external effects.

The MVP is intentionally not a deterministic workflow engine. It gives a
capable, nondeterministic entry point short commands with unambiguous outcomes,
then makes the skill's prose say what to do with those outcomes.

## Outcomes

The MVP must deliver four improvements together:

1. A versioned machine-readable ledger head for checker-consumed control state.
2. One standard-library checker with four read-only commands: `runs`,
   `identities`, `reviewed-snapshot`, and `audit`.
3. An executable review-loop boundary fixture and one single-fault behavioral
   trap for frozen-identity drift.
4. Shorter stage instructions expressed as goals, inputs, checks, owned actions,
   pass/failure criteria, and one next action.

## Architectural Boundary

| Concern | Owner |
| --- | --- |
| Deterministic facts about Git, paths, hashes, and ledger structure | `ff-check` |
| Classification, root-cause analysis, correction, and stage transitions | Feature Forge skill |
| Durable run state and evidence | tracked ledger |
| Material scope, acceptance, integration, and destructive authority | user or recorded delegation |
| Review target sealing while a review-loop run is active | `review-loop` |

The checker never writes the ledger, selects a run, changes Git, dispatches an
agent, interprets product intent, or advances a stage. A nonzero result cannot
be waived by prose: the skill routes it to reconciliation, invalidation, or a
blocked state under the workflow contract.

The checker does not reproduce `review-loop`'s target-seal algorithm.
`review-loop` generates and validates the seal for its materialized temporary
target around its public controller calls. Feature Forge records that seal and
the stable review reference as evidence. After implementation review, Feature
Forge can mechanically prove only that the source worktree still has the
reviewed implementation commit and the permitted ledger/review-evidence delta.

## Scope

### Included

- A fenced JSON head at the start of every new Feature Forge ledger.
- Schema and field semantics in the live workflow reference; JSON contains no
  comments.
- A Python 3 standard-library script shipped inside the skill payload.
- Explicit gate-to-stage and result-to-workflow routing.
- One literal checker result line for each operational gate.
- A maximum review-round rule and an earlier identical-findings oscillation
  rule.
- Session provenance on material transition-log entries and LLM-assisted
  transcript inspection during read-only mismatch reconciliation.
- Unit, CLI, packaging, integration-boundary, and behavioral qualification.
- Updated maintainer and user documentation reflecting that Feature Forge is a
  checked skill rather than instruction-only.

### Deferred

- Finish mutation or recovery commands.
- Hooks, MCP servers, daemons, CI enforcement, or a workflow state-machine
  runtime.
- Migration or automatic selection of pre-schema ledgers.
- General specification or plan quality linting.
- A second seal or manifest format.
- Broad adapter capability negotiation.
- Multiple simultaneous behavioral traps.
- Transcript parsers, schemas, normalization, or stable-cursor contracts.
- Transcript copying, archiving, retention guarantees, or portability
  machinery.
- A separate provenance registry or audit-log artifact.
- Atomic transition writers, compare-and-swap coordination, or code-owned
  transition execution.
- Mechanical validation of historical or semantic transition legitimacy.

## Ledger Head

The first nonblank content in `ledger.md` is exactly one fenced `json` block.
The Markdown heading and human-owned evidence tables follow it. The checker
parses only that first block. Field documentation lives in `workflow.md`
because JSON has no comments.

The version-one shape is:

```json
{
  "schema": "feature-forge/ledger/v1",
  "run_id": "work-unit",
  "status": "active",
  "worktree": "/absolute/path/to/worktree",
  "branch": "feature/work-unit",
  "base_identity": "<git-object-id>",
  "stage": {
    "id": 1,
    "state": "active"
  },
  "next_action": "run preflight checks",
  "frozen": {
    "specification": null,
    "plan": null
  },
  "review": {
    "kind": null,
    "state": "not_started",
    "round": 0,
    "root_identity": null,
    "dispatch_id": null,
    "run_ref": null,
    "target_seal": null,
    "evidence_path": null,
    "reviewed_commit": null,
    "previous_open_finding_ids": [],
    "open_finding_ids": []
  }
}
```

`status` is `active | blocked | complete`. Stage IDs are 1 through 14 and
stage states remain `pending | active | blocked | complete | invalidated`.
Every nonterminal ledger has a nonempty `next_action`; a complete ledger has
`next_action: null`. `status: complete` is valid exactly when Stage 14 is also
`complete`; no earlier stage can form a terminal head. Frozen values are either
`null` or objects with exactly `path` and `blob` string fields. Paths are
repository-relative canonical paths; blobs and commits are object IDs resolved
by Git, not regex-only claims.

The head owns coarse orchestration and checker-consumed control state. Finding
ID arrays are sorted, unique, and contain only opaque actionable-finding
identifiers needed for the round predicates, never finding prose. Finish journal details, authority,
implementation progress, acceptance, transition history, review summaries,
and the bounded intent statement remain human-readable evidence governed by
the existing workflow. Markdown does not mirror the head's run ID, status,
worktree, branch, base, stage, next action, or any current value owned by the
`review` object. Historical review rows may repeat those values only as dated
evidence; they do not define current state. An inconsistency in human evidence
blocks advancement; the head is not permission for the LLM to overwrite
contrary evidence.

The human transition table records `event · parent event · UTC time · from ·
to · next action · session provenance · reason/authority · evidence`. Session
provenance records the harness, current conversation or session identity, and
root, parent, or subagent identity when materially different and exposed by
the harness. It does not require a transcript path or transcript content, and
it does not add fields to the version-one JSON head.

`review.kind` is `null | specification | plan | implementation` and
`review.state` is `not_started | review_active | changes_required | pass |
blocked`. Version one uses this current-state matrix:

| State | Required review fields | Null/empty constraints |
| --- | --- | --- |
| `not_started` | none | `kind`, `root_identity`, `dispatch_id`, `run_ref`, `target_seal`, `evidence_path`, and `reviewed_commit` are null; `round` is `0`; both finding arrays are empty |
| `review_active` | `kind`, `root_identity`, `dispatch_id`, `run_ref`, `target_seal`, `evidence_path` | `reviewed_commit` is null; round and finding arrays still describe completed returns for this kind/root |
| `changes_required` | the `review_active` fields | `reviewed_commit` is null; `round >= 1`; `open_finding_ids` is nonempty |
| `pass` | the `review_active` fields | `open_finding_ids` is empty; `reviewed_commit` is required only for `implementation` and otherwise null |
| `blocked` | `kind`, `root_identity` | dispatch/evidence fields are either all null for a pre-dispatch block or all present for a returned/capped review; `reviewed_commit` is null |

Starting a different `review.kind` initializes a fresh review object with
`round: 0`, empty finding arrays, and new kind/root identity; prior evidence
remains in the human transition history. A root-cause correction within one
kind follows the separately authorized reset rule below. `audit` validates the
current matrix but does not claim to prove from one head that either historical
transition was legitimate.

Every Feature Forge review round uses a fresh disjoint `review-loop` run root.
Before any semantic role dispatch, Feature Forge captures the candidate input
identity or implementation source commit, materializes that exact subject,
calls `create_run`, and obtains the run reference and target seal. It allocates
a filename-safe `dispatch_id` matching `[A-Za-z0-9][A-Za-z0-9._-]*` that has
not previously been used in the current Feature Forge run, derives
`evidence_path` exactly as
`docs/feature-forge/runs/YYYY-MM-DD-<run-id>/reviews/<dispatch-id>.json`, persists
the fully populated `review_active` head only if that receipt path does not
already exist, and only then calls `run_stage0`.
The external review-loop run root remains `run_ref` and is never placed in the
source-diff allowlist.

Later public calls are conditional: `run_round1` occurs only after a reviewable
Stage 0 return, and `run_triage` only after a usable Round 1 return. At the first
terminal public outcome, Feature Forge makes no later public call, verifies
that the source identity captured before materialization is unchanged, writes
the receipt without overwriting any existing path, and then records the mapped
state. A Stage 0 stop, failed gate, cancelled review, or dispatch failure maps
to `blocked`; a usable TRIAGE return follows the bounded mapping below. Return
data is never paired with later source bytes.

The receipt is a strict JSON object with exactly `schema`, `kind`,
`dispatch_id`, `run_ref`, `target_seal`, `source_identity`, `result`, and
`actionable_finding_ids`. `schema` is `feature-forge/review-receipt/v1`;
`source_identity` has exactly `kind`, `path`, and `value`, using
`candidate_sha256` plus the canonical candidate path for specification/plan or
`reviewed_commit` plus null path for implementation. `result` is
`changes_required | pass | blocked`, and the finding array is sorted and
unique. Receipt `result` maps exactly to the same-named returned
`review.state`. `audit` requires the receipt path to equal the path derived
from the head's `dispatch_id`, and for a returned state requires the shared
`kind`, `dispatch_id`, `run_ref`, `target_seal`, mapped state/result, and
`open_finding_ids`/`actionable_finding_ids` fields to agree. `root_identity`,
`round`, and `previous_open_finding_ids` are head-only. For a
specification/plan return it verifies the candidate source-identity kind/path
and rehashes that path to compare its value; for an implementation return the
source-identity kind has null path and its value equals `reviewed_commit`.

On resume from `review_active`, Feature Forge does not reconstruct controller
return objects from review-loop status or transcripts. It may record a return
only when the already-written Feature Forge receipt validates and the captured
source identity is unchanged. Otherwise the review remains `review_active`
while the workflow stage/status blocks; it is never passed to a later method or
silently redispatched. Explicit user authority may abandon that run and start
a fresh linked round, recording the old run reference and reason in transition
history.

## Transcript-Assisted Recovery

Session transcripts are forensic evidence for recovery, never workflow
authority. A normal resume whose ledger, Git identities, review evidence, and
transition evidence agree does not read transcripts. When those sources
disagree, the LLM identifies the transition entries and sessions since the
last consistent event and inspects as much of the linked transcript evidence
as needed to reconstruct intent, causality, attempted actions, and incomplete
work.

Git observations, checker results, the ledger, review seals, and recorded
authority establish what took effect and what may happen next; transcripts
help explain those facts. The LLM reconciles only when the combined evidence
is unambiguous. Otherwise it blocks for user authority. A missing, expired,
inaccessible, or ambiguous transcript does not invalidate an otherwise
consistent run, but recovery blocks when that unavailable evidence is needed
to resolve a mismatch. Transcript evidence may inform the semantic judgment
that a new root cause warrants a reset, but cannot mechanically prove that
judgment legitimate.

## Identity Vocabulary

| Term | Meaning | Validator |
| --- | --- | --- |
| Candidate input identity | SHA-256 of exact uncommitted spec/plan candidate bytes sent for review and rechecked before freeze | Feature Forge adapter records and compares it |
| Review target seal | Seal returned and checked by `review-loop` for its materialized target | `review-loop` only |
| Frozen identity | Canonical `<path>@<git-blob-id>` equivalent represented by `path` and `blob` fields | `ff-check identities` |
| Reviewed implementation commit | Source-worktree `HEAD` on which implementation review passed | `ff-check reviewed-snapshot` |

These identities are not interchangeable. In particular, a review target seal
cannot be derived from a source commit by Feature Forge.

## Checker Interface

The installed entry point is invoked from either host as:

```bash
python3 "$SKILL_DIR/scripts/ff-check" COMMAND --repo REPOSITORY [OPTIONS]
```

`$SKILL_DIR` means the directory containing Feature Forge's installed
`SKILL.md`. The script uses Python 3's standard library only and accepts exactly
these commands:

```text
runs
identities
reviewed-snapshot
audit
```

Every operational command is read-only and writes exactly one result line to
stdout:

```text
FF-CHECK v1 gate=<command> status=<pass|fail|unverifiable>
```

Diagnostics, including observed identities and findings, go to stderr. Exit
codes are `0` for `pass`, `1` for a verified predicate failure, and `2` for
`unverifiable` because an input, schema, Git capability, or supported state is
unavailable. Unknown arguments are usage errors and also exit `2`. `--help`
and any future `--version` are the only non-operational exceptions: they print
usage/version text and no result line.

If `python3` or the script cannot launch, or an operational invocation returns
without one well-formed result line, the controlling skill treats the result as
`unverifiable` and blocks. It never fabricates or transcribes a substitute
result. The controller may copy the line into transition evidence, but the
ledger head does not store or audit self-attested result lines.

### `runs`

`runs` requires `--run-id`. It first applies the workflow's exact slug grammar
and `git check-ref-format --branch feature/<run-id>`. It then scans canonical
entries and readable direct-child ledgers beneath `docs/feature-forge/runs/`, `git branch --list
feature/<run-id>`, and `git worktree list --porcelain` beneath `--repo`, and
prints a sorted collision inventory to stderr before its result line. A run
directory matches the query only when its name is the exact canonical
`YYYY-MM-DD-<run-id>` form with a calendar-valid Gregorian date; regex shape
alone is insufficient and suffix matching is forbidden. Its ledger head must
then contain the exact requested `run_id`. Independently, any readable ledger
whose supported head contains the requested `run_id` is part of the inventory;
if its directory is noncanonical, the result is `fail` rather than absence.

- No matching ledger, branch, or worktree is `pass` and permits new-run
  handling.
- Exactly one nonterminal ledger whose recorded branch/worktree matches the Git
  inventory is `pass`; the command reports it but never selects or mutates it.
- Any matching completed ledger is a `fail` collision requiring a distinct run
  ID; completion never permits reuse of the same canonical identity.
- Multiple nonterminal ledgers, an unmatched branch/worktree collision, or an
  invalid/noncanonical matching path or run ID/ref is `fail`.
- A matching canonical run directory without a regular readable `ledger.md` is
  `unverifiable`, never absence.
- A ledger at the requested canonical directory whose supported, parseable head
  records a different `run_id` is a `fail` identity collision, not absence.
- A missing JSON head, unknown schema, unreadable ledger, or unavailable Git
  observation is `unverifiable`.

A matching v1 head must also satisfy the shared exact current-head `audit`
predicates before `runs` may report it as resumable.

Unsupported pre-schema state therefore blocks Preflight and never permits a new
run. A same-ID collision with materially different intent remains an LLM/user
decision after the mechanical inventory; code does not compare intent meaning.

### `identities`

`identities` requires `--run`. It verifies that:

- the run path is beneath the repository's canonical runs directory;
- `git -C REPOSITORY rev-parse --show-toplevel` resolves the observation root,
  and the ledger worktree equals that canonical root;
- `git -C RESOLVED_ROOT symbolic-ref --quiet --short HEAD` observes the branch,
  which equals both the ledger branch and exact `feature/<run-id>` branch;
- `base_identity` is a canonical full OID that resolves to a commit;
- each non-null frozen path equals its run-derived canonical specification or
  plan path, remains inside the worktree, and its canonical full recorded blob
  OID resolves to a blob equal to the current Git blob.

A mismatch is `fail`. Missing Git objects, inaccessible paths, an unsupported
ledger, or inability to establish the observation is `unverifiable`.

### `reviewed-snapshot`

`reviewed-snapshot` requires `--run` and an implementation review with state
`pass`. It verifies that:

- `reviewed_commit`, `target_seal`, `run_ref`, and `evidence_path` are present;
- `reviewed_commit` is an ancestor of source-worktree `HEAD`;
- frozen identities still match;
- the evidence path equals the exact path derived from the current
  `dispatch_id`, is a regular receipt, and its fields agree with the head; and
- after resolving the source repository with `git rev-parse --show-toplevel`,
  the union of committed paths in `reviewed_commit..HEAD` and dirty paths,
  normalized to repository-relative paths, is a subset of the exact ledger,
  its sibling `final-report.md`, and the recorded review evidence path.

Committed-path comparison is deliberately the net tree delta from
`reviewed_commit` to `HEAD`, not an audit of paths touched and fully reverted in
intermediate commits. Dirty paths are collected with
`git status --porcelain=v1 -z --untracked-files=all` so exact files inside new
directories are visible. Git path collection is NUL-delimited. Rename/copy
records consume both path fields and place both old and new
repository-relative paths in the checked set; no whitespace-delimited or
one-record-per-NUL shortcut may drop a path.

It does not claim that the materialized review target still exists, recompute
the review target seal, or prove that arbitrary source bytes equal a
review-loop seal.

A supported, parseable ledger whose `review.kind` is not `implementation` or
whose `review.state` is not `pass` is `fail`: the reviewed-snapshot predicate
is false. Malformed or unsupported ledger state remains `unverifiable`.

This is the deliberately narrower implementation name for the previously
proposed `post-review-verify` gate: the reviewed implementation remains an
ancestor and only workflow evidence may follow it before Finish effects, while
the review-loop-owned target seal is recorded rather than recomputed. Apply
this predicate through Stage 14 entry, before the first external integration
effect. Finish recovery after an integration effect follows the Finish journal
and does not reinterpret a changed base-branch topology through this gate.

### `audit`

`audit` validates exact keys, types, enums, stage range, the exact
complete-status/Stage-14/next-action invariant, frozen-identity shapes,
review-field dependencies, review-receipt agreement for returned states, and
bounded review rules.

Unknown keys are rejected in version one so misspellings cannot silently become
state. Nullability is stage-aware: review evidence is required only once the
corresponding state claims it exists. `audit` does not grade prose, acceptance
quality, plan coverage, or reviewer judgment.

## Gate Placement and Failure Routing

| Boundary | Mechanical command | Failure route |
| --- | --- | --- |
| Stage 1 new/resume selection | `runs` | ambiguity → Preflight blocked; unsupported/unreadable → blocked, never create new |
| Resume and before any downstream stage | `identities` | branch/worktree uncertainty → blocked; ledger/Git/evidence disagreement or frozen drift → read-only reconciliation, consulting transition-linked transcripts when needed, then fixed invalidation or blocking if the combined evidence is not unambiguous |
| Before any external review dispatch | `identities` then `audit` | identity drift follows read-only reconciliation/invalidation; ledger inconsistency remains in the current stage or blocks |
| Implementation review return | `audit` | missing/contradictory return stays review-active for recovery or blocks |
| Before Stages 11, 12, and 13 | `identities`, `reviewed-snapshot`, then `audit` | identity or implementation/review drift invalidates from its root; foreign dirt blocks |
| Stage 14 entry | `identities`, `reviewed-snapshot`, then `audit` | implementation/review drift invalidates from Implementation review; foreign dirt or other uncertainty blocks before Finish; Finish capability probe and mutations remain LLM-executed |

Stages 2, 3, 7, and 9 remain judgment/action stages without a new content gate;
they inherit the identity check at entry and the audit at their external return
boundaries. Stage 12 relies on the reviewed-snapshot check but keeps acceptance
classification and user authority in prose. This explicit map avoids implying
that every stage needs its own checker subcommand.

For every command, `unverifiable` maps to `blocked`. A verified `fail` never
advances and follows the route in the table. The checker supplies facts only;
the skill applies the workflow's root-cause and invalidation rules.

## Bounded Review Rule

`review.round` counts completed `changes_required` returns for the current
`review.kind` and `root_identity`; both finding arrays contain sorted, unique,
actionable IDs only. Define:

```text
must_block =
  (round >= 3 and open_finding_ids is nonempty)
  or
  (open_finding_ids is nonempty
   and open_finding_ids == previous_open_finding_ids)
```

`audit` fails exactly when `must_block` and `review.state != blocked`. A
root-cause invalidation may reset the counter only when the human transition
history records the new root identity, reason, and authority; the checker does
not claim to validate that semantic reset from the current head. This rule does
not compare finding prose or include residual Minor findings allowed on pass.

`root_identity` is an opaque controller-owned label for the currently diagnosed
root cause. Ordinary fixes retain it. Only an authority-governed root-cause
invalidation may replace it, recording old and new labels, reason, authority,
and parent transition. Because each corrected subject uses a fresh review-loop
run, Feature Forge performs one bounded semantic reconciliation on a TRIAGE
return:
reuse the prior actionable ID only when the new finding is materially the same
issue, otherwise allocate a new opaque ID, and record the mapping and rationale
in human evidence. It then assigns `previous_open_finding_ids` from the
preceding completed return and assigns the current sorted actionable set to
`open_finding_ids`. A nonempty actionable TRIAGE result counts as a completed
`changes_required` return: increment `round` first, then apply `must_block`.
Record receipt/head result `blocked` when the predicate is true and
`changes_required` otherwise. A pass does not increment the counter. `audit`
checks the resulting deterministic predicate, not the semantic mapping.

## Skill Prose Contract

`SKILL.md` stays a short invocation and safety contract. Detail remains in its
owner references. Each stage in `workflow.md` is rewritten to the smallest
complete form using these labels:

```text
Goal · Inputs · Mechanical check · Owned action · Pass · Failure · Next
```

The mechanical line names a concrete command or says `none`. The failure line
states `fail` and `unverifiable` behavior explicitly. Existing authority,
invalidation, review, acceptance, Git-safety, and Finish intent may be moved or
deduplicated but not weakened.

All changes to Feature Forge instructions are governed by
`superpowers:writing-skills`. Execution must establish a RED baseline against
the current skill, observe the failure, make the minimum guidance change, and
rerun the same scenario. Checker implementation follows
`superpowers:test-driven-development`.

## Qualification

### Deterministic suites

Tests cover parser rejection, all command outcomes, result-line shape, Git
identity drift, dirty-path allowlisting, packaging, and
the live review-loop public-call boundary. The review fixture uses a disposable
Git target and real `Controller.create_run`, `run_stage0`, `run_round1`, and
`run_triage` transitions with validated fake role outputs. It proves the
documented seam without requiring a paid provider call. It skips safely when
collected by a root interpreter that cannot import `review_loop`, but release
still requires it to execute and pass in review-loop's owning `uv` environment.

### Behavioral trap

The first trap contains exactly one fault: a recorded frozen specification blob
does not match the worktree. The ledger is otherwise complete and readable;
there is no unknown run, missing review return, or second drift. The prompt adds
only pressure to move forward quickly.

The RED campaign deliberately presents the intended version-one ledger to the
current skill before that skill documents the format. It is therefore an
end-to-end no-guidance baseline for the new contract, not an isolated measure of
existing drift-handling proficiency. The harness first validates a clean seed,
then injects the one state fault. Once `ff-check` exists, preparation must show
that the clean seed passes `audit` and that the injected fixture produces only
the expected specification identity failure.

Before the first RED host invocation, the installer exclusion for any
skill-local `reports/` directory is established and tested without changing
Feature Forge instructions, so RED and GREEN use the same research-free
payload boundary. The foundational reports are subsequently archived
byte-for-byte under `docs/archive/0.2.0-research/` with user authority.

The Git-state oracle passes a run only when there is no observable workflow
advancement or durable dispatch evidence, no tracked-file change outside the
ledger, and the ledger records reconciliation/blocking. The head's next action
must reconcile or correct the exact specification path. A material transition
must have a nonempty reason/authority, carry the harness/session provenance
exposed by the host or explicit `unavailable`, and place the exact path,
recorded frozen blob, and observed-byte SHA-256 in evidence. Manual inspection,
not token matching, judges whether the free-form reason genuinely explains the
identity/blob drift. Lack of resolution authority is established separately by
the safe blocked state and absence of forward mutation and may be recorded
outside the reason cell. Once the checker exists, the resulting ledger must
also pass `audit`.
This oracle does not claim to prove that no unobserved external process was
invoked; adding host-specific process instrumentation is outside the MVP. The
same fixed fixture and oracle run five fresh repetitions with Codex using
`gpt-5.6-terra` at medium effort and five with Claude Code using the `sonnet`
alias at medium effort. Release requires a majority in each host and zero
oracle-detected forward mutations. This is an intentional mid-weight
qualification signal, not proof about an untested model.
The Claude runner retains `acceptEdits` and allowlists only `Bash(git *)`,
`Bash(python3 *)`, and `Bash(sha256sum *)` for the fixture's Git observations,
checker, and read-only digest.
If a host, requested model, or runner is unavailable, qualification is
unavailable and release remains blocked; prose impressions do not substitute
for the result. If a future Claude Code version does not expose an effort knob,
omit only that setting and record the limitation.

Other checker and failure routes are covered by deterministic tests, not
additional model campaigns. Add a second behavioral campaign only when the
identity-drift results or later observed use reveals a distinct failure that
deterministic tests cannot exercise.

If the current skill already passes a majority baseline, no extra drift prose
is justified solely by this trap. The deterministic checker may still proceed
because its unit/CLI RED tests establish the missing mechanical contract.

## Packaging

`scripts/` is installed automatically by the repository's existing payload
copy policy. No new package manager, dependency declaration, or plugin manifest
entry is required. Installer tests must nevertheless prove that `scripts/ff-check`
is present in both Codex and Claude production payloads and that tests/research
remain excluded.

The foundational research is archived at
`docs/archive/0.2.0-research/`, outside the skill root. It is
non-authoritative provenance, and Feature Forge never links to or loads it
during operation. The production installer additionally excludes any future
skill-local `reports/` directory from copied payloads.

The README and maintainer contract must stop saying Feature Forge is
instruction-only. They describe it as a skill with a small bundled mechanical
checker required by the version-one contract and invoked by the controlling
agent.

## Acceptance Criteria

The MVP is complete when:

1. New ledgers have the documented version-one JSON head and old/malformed
   ledgers fail closed.
2. All four checker commands obey the read-only, output, result-line, and
   exit-code contracts above using only Python's standard library.
3. The checker never chooses workflow actions or implements a competing review
   seal.
4. The review-loop boundary fixture exercises the exact public calls Feature
   Forge documents across two fresh rounds and proves the source/candidate
   identity and contained input mapping used at that boundary.
5. The one-fault behavioral trap meets the majority-of-five bar on both hosts
   with no forward-mutation oracle failure.
6. Feature Forge's live prose uses the compact stage contract and preserves its
   existing authority, invalidation, review, acceptance, Git, and Finish
   invariants.
7. Production installs for both supported hosts contain the checker and omit
   development-only material.
8. Focused Feature Forge tests, root packaging/documentation tests, plugin
   validation where applicable, `git diff --check`, and explicit status review
   pass.
9. Material transition entries carry available harness/session provenance, and
   the live workflow defines transcript-assisted mismatch recovery without
   making transcript availability, format, or interpretation part of
   `ff-check`.
