# feature-forge: Proposed Enhancements

**Executive summary.** Four sibling projects (fable-method, autoprompt-skill, procoder, zeroshot) were mined for mechanisms transferable to feature-forge's instruction-only controller. The strongest signals converge on fail-closed structured evidence, bounded review rounds with escalation, and cheap deterministic gates before expensive review dispatch — all implementable without touching feature-forge's invariants. Proposals rated poor are retained as documented dead ends, mostly for violating the review-loop adapter boundary or instruction-only packaging. A final cross-check against the prior five-project report added 8 proposals and one verified prerequisite: the review-loop adapter interface gap (see last section).

---

## fable-method

| Title | Fit | Impact |
|---|---|---|
| Forced literal gate lines at transitions | excellent | high |
| No-weakened-checks rule + authority chain in packets | excellent | high |
| CI-as-schema tests on prose contracts | excellent | medium |
| Trap-fixture eval suite | good | high |
| UNVERIFIABLE evidence label | good | medium |
| Ordered fraud taxonomy in review criterion | good | medium |
| Bounded review/fix cycles with escalation | good | medium |
| Triviality decline at preflight | good | low |
| Refutation-lens reviewer fan-out | poor | low |
| Provenance tags on contract rules | poor | low |

**Forced literal gate lines at transitions**
Source: INTENT/AUTH/TWINS forced-artifact pattern — `/home/mark/tools/fable-method/skills/fable-method/SKILL.md`, `eval/RESULTS.md` rounds 2-3 (prose rules 1/4, literal lines 4/4).
- Format-checkable one-liners emitted before acting: `IDENTITY: <spec@blob> <plan@blob> match`, `SEAL: <hash> unchanged`, `FINISH: <finish_id> phase=<p>`.
- Required verbatim in ledger transition-log evidence column.
- Resume treats a missing owed line as a missing return — recover, don't infer.
Fit: **excellent** — strengthens ledger discipline at moment of action, zero new state; the one empirically proven fable-method mechanism.

**No-weakened-checks rule and authority chain in worker packets**
Source: authority order user > spec > tests > code; fraud taxonomy ranks weakened checks first — `/home/mark/tools/fable-method/skills/fable-method/SKILL.md` step 4, fable-judge.
- Packet contract: never weaken/delete/skip a check to make it pass — failing check routes via invalidation graph.
- One-line authority order in every packet.
- Final verification diffs for deleted/loosened assertions since plan freeze.
Fit: **excellent** — closes a real gap; packets forbid spec/plan edits but say nothing about test-gaming, the top measured fraud mode.

**Trap-fixture eval suite for controller discipline**
Source: A/B trap fixtures, excluded answer sheets, judge diffs pristine copy — `/home/mark/tools/fable-method/eval/`.
- Repo-level mini repos: mid-run ledger + a bait (second finish invocation, drifted blob, stash-tempting dirty path).
- Ground truth excluded from executor copy; judge diffs pristine-vs-run.
- Results (incl. nulls) in repo log; nothing wired into installed operation.
Fit: **good** — feature-forge has zero behavioral tests today; real build effort, but fixtures stay out of the payload.

**UNVERIFIABLE evidence label**
Source: fable-judge "a report is a set of claims, not evidence" — `/home/mark/tools/fable-method/skills/fable-judge/SKILL.md:15-23`.
- `unverifiable` evidence-quality tag (not a state) on acceptance/verification rows.
- Unreproducible evidence cannot support `approved`; routes to infeasible/blocked.
Fit: **good** — matches evidence-before-assertion posture; small prose delta.

**Ordered fraud taxonomy in the implementation-review completion criterion**
Source: fable-judge ranked checklist: weakened checks > false completion > scope creep > unauthorized action > spec betrayal > debris.
- Embed ranking in implementation-review charter via subject framing/completion criterion — never a roster parameter.
- Controller uses same ranking when classifying findings into the invalidation graph.
Fit: **good** — rides the existing convey-focus mechanism; must stay framing-only.

**Bounded review/fix cycles with escalation**
Source: hard bounds everywhere — 3 failed fix-verify cycles then hand back (`SKILL.md` step 5).
- Round counter per review in ledger Reviews table.
- After N `changes_required` rounds without pass → `blocked` + escalation-to-user action.
- Invalidation-graph re-entry resets counter with recorded reason.
Fit: **good** — compatible with sole-next-action; prevents unbounded churn.

**CI-as-schema tests on the prose contracts**
Source: `checks.py` greps prose for headers/vocabulary/version equality — `/home/mark/tools/fable-method/.github/checks.py`.
- Repo pytest asserting cross-file consistency: Finish phase list, state enums, 8 checkpoint categories, template field names vs workflow.md.
- Pure stdlib; existing pytest gate; never shipped in payload.
Fit: **excellent** — three references + two templates share hand-maintained enums with no drift check today.

**Triviality decline at preflight**
Source: triviality gate skips the loop, skip named in report (`SKILL.md` gates).
- Stage 1: trivially bounded work → recommend declining full run (ask if supervised; proceed if unattended).
- Red flag: a silent skip is indistinguishable from a skipped stage — record the decline.
Fit: **good** — cheap recorded exit from process tax.

**Refutation-lens reviewer fan-out**
Source: named adversarial lenses per attacker subagent — `/home/mark/tools/fable-method/skills/fable-loop/SKILL.md:33-37`.
- Would inject lenses into review rounds — but review-loop self-derives its roster; injecting violates the boundary or builds a parallel mechanism.
Fit: **poor** — belongs upstream in review-loop, not feature-forge.

**Provenance tags on contract rules**
Source: rules tagged [observed]/[covenant]/[version] — `/home/mark/tools/fable-method/skills/fable-domain/SKILL.md:10`.
- No eval trail to back tags → theatre; adds bulk; viable only after trap fixtures exist.
Fit: **poor** — untestable decoration today.

---

## autoprompt-skill

| Title | Fit | Impact |
|---|---|---|
| Default-negative verdict posture at evidence gates | excellent | high |
| Recipient-side frozen-identity verification in packets | excellent | medium |
| Goal-check: re-derive asks before acceptance | good | high |
| Read-only ledger auditor script | good | high |
| Fail-closed partial records; quarantine, never delete | good | medium |
| Named-trap registry cited by review charters | moderate | medium |
| Honest-surface budget seal for unattended runs | moderate | low |
| Blind concurrent reviewers, no verdict channel | poor | medium |
| Tiered gate ladder (T0-T3) | poor | low |

**Default-negative verdict posture at evidence gates**
Source: gates default REJECT/FAIL/NOT-DONE; prose never overrides structured negative evidence — `~/tools/autoprompt-skill` agents/claude/GATES.md.
- Stages 11-12 rows start `pending`, flip only on recorded structured evidence; absence of evidence is a fail.
- Red flag: narrative success never overrides a missing/negative ledger field.
- Ambiguous/unparseable review-loop return maps to `blocked`, never `pass`.
Fit: **excellent** — pure instruction hardening of gates FF already owns.

**Goal-check: re-derive asks from the intent brief before acceptance**
Source: GOAL-CHECK persona re-derives asks from the ledger, default NOT-DONE.
- Stage 12 entry: re-read intent brief, list asks independently, map each to a REQ/SCN or recorded deferral.
- Unmapped ask = acceptance defect via existing invalidation graph.
- Mapping recorded as Stage 12 exit evidence.
Fit: **good** — FF traces REQ→evidence but never re-checks REQs against original intent.

**Read-only ledger auditor script**
Source: `autoprompt-ledger-check.js` standalone read-only auditor.
- Script in assets/ parsing ledger.md: exactly-one-next-action, status vocab, complete/pass rows have transition rows + evidence, frozen identities vs `git cat-file`, checkpoint commits exist.
- Run at resume and before Stage 14 claim; failure blocks, never advances state.
- Output is evidence only; ledger stays sole authority.
Fit: **good** — mechanizes checks prose already mandates; small script earns its place.

**Recipient-side frozen-identity verification in dispatch packets**
Source: hash-pinned mission pointer verified by every recipient; mismatch = refuse (INVALID-BRIEF).
- Packets carry frozen spec/plan `<path>@<blob>` pins; worker recomputes before any edit.
- Mismatch → worker returns `blocked` with observed identity; never re-derives authority.
- Same pin rule for review-loop dispatches (seal restated, reconciled on return).
Fit: **excellent** — closes the gap that only the controller verifies identities; one field, one rule.

**Fail-closed partial records; quarantine, never delete**
Source: half-written artifacts treated as absent; stale sentinels renamed, never deleted (supervisor.sh).
- Transition/Finish-journal row missing any required field = absent — recover from prior complete row.
- Ambiguous run-dir state inventoried or renamed aside with evidence, never deleted.
- Partial category-8 receipt never counts as its phase.
Fit: **good** — crisp fail-closed criterion for existing recovery rules.

**Named-trap registry cited by review charters**
Source: frameworks name observed failures verbatim ("the pylint-7080 trap").
- Short reference listing traps from past FF runs ("checkbox drift", "invented UAT"); charters cite stage-relevant traps; append-only.
Fit: **moderate** — good memory mechanism, but list starts empty and FF adds machinery only on named requirements.

**Honest-surface budget seal for unattended runs**
Source: phase-budget.js — budget breach seals on genuinely landed evidence, never manufactures coverage.
- Optional per-run budget recorded at preflight; breach → `blocked` + inventory of landed evidence; never synthesized acceptance.
Fit: **moderate** — wall-clock enforcement is weak without a harness; value is the never-fake-on-timeout rule.

**Blind concurrent reviewers with no verdict channel**
Source: G2‖G3, G5‖G6 concurrent gates, no shared verdict channel (GATES.md:82,111,156).
- Would require FF to run parallel review rounds and join — review-loop owns reviewer independence internally.
Fit: **poor** — violates the adapter boundary; right home is review-loop.

**Tiered gate ladder (T0-T3) to scale rigor per work unit**
Source: MODES.md tiers skip/add gates by risk; escalate only upward.
- Skipping stages breaks the fixed fourteen-stage workflow and resume/recovery uniformity; FF already has upward-classification.
Fit: **poor** — conflicts with fixed stage set; escalation half is a near-duplicate.

---

## procoder

| Title | Fit | Impact |
|---|---|---|
| Deterministic candidate/plan content gate | excellent | high |
| Test-design triad in review + packets | excellent | high |
| Unchecked-counts-as-failing verification vocabulary | good | medium |
| Three-strikes upward reclassification on thrash | good | medium |
| Run escapes ledger with adaptation enforcement | good | medium |
| Backward-looking Preflight gate on abandoned runs | good | low |
| Resume read-order: contracts before live state | good | low |
| Refusing-binary gate replacing prose controllers | poor | high |
| Same-turn hook enforcement | poor | medium |
| Non-delegation rule duplicated verbatim | poor | low |

**Deterministic candidate/plan content gate**
Source: controllers parse section bodies, refuse placeholders — `/home/mark/tools/procoder` internal/spec/spec.go:259-340, internal/plan/plan.go:132-191.
- Checker script in assets/, run at Stage 4 and Stage 7 exit: non-empty section bodies, Open questions present+empty, no placeholder tokens, plan tasks name owned paths.
- Distinct outcomes (unreadable / has-gaps / clean); accumulate all gaps.
- Gap blocks before review-loop dispatch — cheaper than burning a review round; known-bad fixtures prove detection.
Fit: **excellent** — hardens an existing LLM-judged gate with zero new workflow state.

**Unchecked-counts-as-failing verification vocabulary**
Source: three-valued verdicts (clean/failed/unchecked), unchecked fails — internal/gate/gate.go:106-113.
- Stage 11 + ledger: every declared check records ran + result; not-run/timeout/unavailable = `unchecked` = failing, never omitted.
- Extends to acceptance rows and the final-report table.
Fit: **good** — closes the declared-check-silently-vanishes hole.

**Test-design triad in implementation review and worker packets**
Source: name-the-break, mirror-assertion ban, mental mutation check — commands/tdd.md:29-48.
- Charter: per new test, "what production change fails this, and is that a bug?"; mirror assertions are findings.
- Packet: verification evidence shows test failing pre-fix or names the break guarded.
Fit: **excellent** — zero new machinery; directly attacks vacuous-test theatre.

**Three-strikes upward reclassification on review thrash**
Source: three failed fixes force naming the pattern before attempt #4 — commands/debug.md:44-48.
- After 3 `changes_required` rounds sharing a root cause → reclassify upward through invalidation graph, not round 4.
- Thrash evidence + reclassification authority in transition row; complements oscillation→blocked.
Fit: **good** — uses the existing graph as escalation target; no invariant change.

**Run escapes ledger with adaptation enforcement**
Source: escaped findings must name the layer that missed them, adapted same-PR — "recorded is not learned".
- Final-report section: every post-gate defect names the missing stage/charter + adaptation (or recorded deferral).
- Unattributed escape blocks Stage 13 Report; optional advisory cross-run lessons file at Preflight.
Fit: **good** — per-run attribution fits Stage 13; keep cross-run half advisory.

**Backward-looking Preflight gate on abandoned runs**
Source: forward action blocked by prior unfinished obligations — internal/backlog/sprint.go:127-138.
- Stage 1: enumerate nonterminal runs; new run starts only after user acknowledgment (or recorded standing authority unattended); recorded as exit evidence.
Fit: **good** — generalizes existing read-only collision inspection.

**Resume read-order: contracts before live state**
Source: principles injected before status — "the last thing read is the thing acted on" (internal/principles/principles.go:183-256).
- SKILL.md start-or-resume: references first, then ledger/artifacts — next action is last thing read.
Fit: **good** — pure ordering tweak exploiting recency effects.

**Refusing-binary gate replacing prose controllers**
Source: thin prose / thick binary split — docs/quality-chain.md, internal/gate.
- Would move gates/seals/Finish validation into a CLI — breaks instruction-only packaging, creates a second workflow authority.
Fit: **poor** — competes with the ledger.

**Same-turn hook enforcement wired to the gate**
Source: PostToolUse hooks fire the collector on every edit — hooks/claude-hooks.json.
- Harness-specific, outside the skill, acts between ledger transitions.
Fit: **poor** — an enforcement channel the ledger does not own.

**Non-delegation rule duplicated verbatim at every load-bearing site**
Source: same rule word-for-word in AGENTS.md/SKILL.md/principles.go.
- Conflicts with FF's single-owner documentation contract; duplication = drift risk.
Fit: **poor** — direct contract conflict.

---

## zeroshot

| Title | Fit | Impact |
|---|---|---|
| Structured evidence-or-reject schema | excellent | high |
| Freshness-gated evidence (postdates reviewed commit) | excellent | high |
| Bounded correction loops with round caps | good | medium |
| Pre-review readiness gate | good | medium |
| Two-persona worker packets (correction variant) | good | medium |
| Instant-reject tripwire lists | good | medium |
| Inline declarable proof gates in intent brief | good | medium |
| Contrastive BAD/GOOD requirement examples | good | low |
| Deny-hook enforcement of git-safety prose | moderate | medium |
| Hash-sealed self-verifying footers | poor | low |
| Behavioral simulation of the workflow | poor | low |

**Structured evidence-or-reject schema for verification and acceptance rows**
Source: validator results require command+exitCode+output; narrow CANNOT_VALIDATE — `/home/mark/tools/zeroshot/src/agents/`.
- Micro-schema in authority.md: `command | exit code | output excerpt | UTC time` per row; prose without it is not evidence.
- Columns added to ledger + final-report templates; narrow tool-unavailable escape, never "probably fine".
- Charters instruct reviewers to reject rows lacking the schema.
Fit: **excellent** — hardens existing Stage 11-12 evidence fields; pure instruction/template change.

**Freshness-gated evidence: proofs must postdate the reviewed implementation commit**
Source: git-pusher rejects PASS evidence older than last IMPLEMENTATION_READY — src/agents/git-pusher-template.js:150-200.
- Evidence carries timestamp + commit ref no older than the reviewed commit.
- Stage 13 refuses checkpoint 7 on stale acceptance evidence; routes via invalidation as "evidence stale".
- `commit@time` in evidence column lets resume re-check mechanically.
Fit: **excellent** — seals cover content identity but not recency; same fail-closed style.

**Bounded correction loops with explicit round caps**
Source: everything bounded — worker maxIterations 5, validator maxRetries 3 (cluster-templates/full-workflow.json).
- Per-review-stage round budget; exceeding maps to `blocked` with named oscillation blocker.
- Round count in ledger; cap invalidation re-entries per root cause the same way.
Fit: **good** — termination guarantee the current unbounded cycle lacks.

**Pre-review readiness gate: cheap self-check before review-loop dispatch**
Source: quick-validation must pass before heavy-validation loads (meta-coordinator).
- Fixed checklist before `review_active` at Stages 5/8/10: sections present, Open questions empty, tests run locally, no TODO in diff, seal computable.
- Fail returns to owning stage without spending a review round; recorded as dispatch-gate evidence.
Fit: **good** — saves review rounds without touching the adapter boundary.

**Two-persona worker packets: distinct re-dispatch packet after changes_required**
Source: prompt.initial vs prompt.subsequent + self-verification question gate.
- Correction-packet variant: verbatim surviving findings, prior commit, no re-litigating passed scope.
- Worker answers a short self-verification gate before returning (command re-run post-fix, evidence cites new commit).
Fit: **good** — fits the packet-completeness contract; persona is packet content, not authority.

**Instant-reject tripwire lists in review charters and acceptance**
Source: instant-reject lists — TODO/placeholder, "will add tests later", lazy-debugging flags.
- Fixed tripwire list, single-sourced, cited by all three charters; any hit → changes_required/rejected, never pass-with-note.
Fit: **good** — cheap prose mechanizing judgment reviewers already owe.

**Inline declarable proof gates in the intent brief (cmdproof analog)**
Source: fenced command-proofs block parsed into gates all agents see — src/command-proofs.ts.
- User declares mandatory verification commands; Harden copies them into the spec as named gates.
- Each becomes an acceptance row Stage 11/12 must satisfy; frozen with the spec so gates can't be dropped.
Fit: **good** — direct durable user lever riding existing REQ/acceptance rails.

**Contrastive BAD/GOOD examples for requirement measurability**
Source: planner schema with contrastive examples (❌"Dark mode works" ✅"Toggle → contrast >4.5:1").
- 2-3 BAD/GOOD pairs in authority.md keyed to SHALL/GIVEN-WHEN-THEN; candidate gate + charter check against the GOOD pattern.
Fit: **good** — near-zero cost compliance boost.

**Deny-hook mechanical enforcement of git-safety prose**
Source: PreToolUse hooks block stash/reset --hard/push -f/clean -f, env-gated — cluster-hooks/.
- Optional env-gated hook denying already-forbidden git commands during an active run; prose stays authoritative.
Fit: **moderate** — strains instruction-only packaging; harness-specific; activation scoping is fiddly.

**Hash-sealed self-verifying ledger/report footers**
Source: exports seal SHA-256 + complete flag into footer — cli/export-stream.ts:98-118.
- Git checkpoints already content-hash both files; second seal = competing integrity mechanism.
Fit: **poor** — contradicts the mutable-ledger invariant.

**Behavioral simulation / cycle detection of the workflow itself**
Source: static schema check + seeded simulation, DFS cycle detection — src/template-validation/.
- Workflow is prose executed by an LLM, not data executed by an engine; nothing mechanical to simulate. Thin vocabulary repo test survives, marginal.
Fit: **poor** — workflows-as-data prerequisite absent.

---

## Cross-project convergence (strongest signals first)

1. **Fail-closed structured evidence — 4/4 projects.** autoprompt (default-negative posture), zeroshot (evidence-or-reject schema), procoder (unchecked = failing), fable-method (UNVERIFIABLE label). Same thesis everywhere: absence or unreproducibility of evidence is a fail; prose never overrides a missing field.
2. **Bounded review rounds with escalation — 3/4.** fable-method (N rounds → blocked), procoder (three-strikes → upward reclassification), zeroshot (round caps → oscillation blocker). Current FF contract permits unbounded churn.
3. **Fraud/tripwire lists in review charters — 3/4.** fable-method (ranked fraud taxonomy), zeroshot (instant-reject tripwires), autoprompt (named-trap registry). Convey via subject framing/completion criterion to respect the adapter boundary.
4. **Cheap deterministic checks before expensive steps — 3/4.** procoder (content gate script), zeroshot (pre-review readiness checklist), autoprompt (ledger auditor script). Small read-only scripts producing evidence only, ledger stays sole authority.
5. **Identity/freshness verified beyond the controller — 2/4.** autoprompt (recipient-side pin verification), zeroshot (evidence must postdate reviewed commit). Both close gaps where seals exist but only one party checks them.
6. **Anti-test-gaming rules in packets/review — 2/4.** fable-method (no-weakened-checks + authority chain), procoder (test-design triad). Attacks the top measured fraud mode.

**Convergent rejections** (independent agreement on what *not* to do): restructuring review-loop's roster/parallelism (fable-method fan-out, autoprompt blind reviewers — both poor: adapter boundary); harness hooks as enforcement (procoder poor, zeroshot moderate: harness-specific, outside ledger authority).

---

## Cross-check against ~/feature-forge-report.md (2026-08-22)

The prior five-project comparative report was cross-checked against this one. Corroborations: its P0 shortlist independently converges on our top signals (validator scripts, unchecked-is-failing, spec/plan readiness lint, trap fixtures, triviality admission hint, fail-closed evidence). Gaps it surfaces that this report missed are added below.

**Gap 0 — review-loop compatibility (prerequisite, verified live).** feature-forge's adapter contract claims it conveys review focus via "subject set, deployment context, completion criterion" — but review-loop's live `InvocationIntent` (`review-loop/review_loop/profiles.py:204`) accepts none of those fields, rejects non-directory targets (`controller.py:360`), and round-N triage/reconciliation is deferred fail-closed (`controller.py:792-1055`). Verified in this session.
- Affects proposals that ride the "convey via charter/subject framing" mechanism: fraud taxonomy (fable-method), tripwire lists (zeroshot), test-design triad charter half (procoder), named-trap registry (autoprompt). All remain valid but are **contingent on first defining a real adapter mapping**.
- Added proposal: **Review-loop adapter capability contract** — specify the actual mapping (exact-file candidate materialization into a directory subject, ground_truth split, criterion via profile or documented workaround), version it, and add one happy-path + one incompatible-capability fixture. Fit: **excellent**, impact high. This is the prior report's P0 #1 and its "immediate risk".

**Gaps 1-7 — proposals added from the prior report** (fit ratings ours):

1. **Dispatch identity + recover-before-redispatch** — one canonical `dispatch_id` (adapter+stage+frozen IDs+seal+task IDs) echoed in a closed return envelope; on resume, observe/recover that dispatch before any redispatch. Extends our recipient-side pin verification. Fit: **excellent**, impact high.
2. **Closed adapter outcome set** — standardize returns to `completed | changes_required | blocked | refusal | malformed | timeout | crash`; only the controller maps outcomes to transitions; unknown/partial = `malformed`, never success. Extends our evidence-or-reject schema. Fit: **excellent**, impact medium.
3. **Defect-work depth/twin evidence** (fable intent/twin gates + autoprompt depth-lock, defect-classified work only) — intent-source tuple, reproducible red baseline, deepest evidenced cause, scoped twin-search receipt; surprises return to controller, never silently rewrite frozen authority. Fit: **good**, impact medium.
4. **Pinned-root pre-effect revalidation** (zeroshot copy-containment) — bind execution/Finish receipts to canonical worktree root+branch+commit; recheck immediately before each filesystem/Git effect. Fit: **good**, impact medium.
5. **Overlap/integration classification** (autoprompt lanes, narrow slice) — before execution-mode choice, classify each writable boundary disjoint / intentionally-shared-inline / explicit integration task; unclassified overlap blocks the subagent branch. Fit: **good**, impact medium.
6. **Early evidence-capability receipt** — after plan review, prove declared verification/acceptance runners, credentials, and environments exist; missing required capability blocks before implementation, not at Stage 11. Fit: **good**, impact medium.
7. **Verbatim authority excerpt bound to `finish_id`** (fable AUTH line as evidence, not authority) — Stage 14 stores the exact user-authorization quote structurally bound to action + target + `finish_id`. Fit: **good**, impact low.

**Adjacent (from prior report, out of scope here):** the skillbook has no LICENSE file — clarify before anyone copies/redistributes prose from the compared MIT/Apache projects, and before publishing feature-forge itself.
