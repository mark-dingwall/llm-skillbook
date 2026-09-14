# Autoprompt-skill investigation

## 1. Overview

Multi-agent orchestration skill (`~/tools/autoprompt-skill`) that turns a single `/autoprompt <mission>` into a gated, evidence-driven build/debug pipeline run by ~25 typed subagent personas across a 5-level hierarchy (L0 conductor → L4 terminal leaves).

**Thesis:** LLMs cannot be trusted to grade their own work, so independence, distrust-by-default, and cryptographic provenance are engineered into every step — as prose contracts *and* mechanical guards.

| Dimension | Value |
|---|---|
| Personas | 25 (contract JSON, tiers R1-R5) |
| Frameworks | 18 seeded + on-the-fly generation |
| Providers | 6 (claude, codex, opencode, kilo, vscode, prime) — generated from one canon |
| Core doctrine | 4 files: SKILL.md, GATES.md, MODES.md, PLAYBOOKS.md (~730 lines) |
| Harness code | `autoprompt-gate.js`, `autoprompt-ledger-check.js`, `supervisor.sh`, `phase-budget.js` |
| Maturity | Mature: CI on 4 OS/Node combos, 24+ test suites, benchmark doc, self-disclosed evidence gaps |

Benchmark claim: Terminal-Bench 2.1, OpenCode 60/89 → +Autoprompt 73/89 (+14.6pt). **Caveat:** treatment arm's per-task map "not retained" — headline not reconstructable; baseline has full verdicts.

## 2. Core methodology

Gate ladder G1–G8 + GOAL-CHECK, each gate cast to a fixed persona:

| Gate | Persona | Job | Default |
|---|---|---|---|
| G1 PLAN | ap-planner | Conditional (debug, design fork, PLAN-CONFLICT) | — |
| G2 PLAN REVIEW | ap-reviewer | PASS/SMASH + numbered reasons | — |
| G3 FRESH VERIFY | ap-fresh-verifier | Fresh context, mission-vs-plan | REJECT |
| G3.5 DEPTH-LOCK | ap-depth-prober | Root-cause proof, every debug feature | FAIL |
| G4 IMPLEMENT | ap-implementer | Strict TDD 6-step, ≥95% coverage | — |
| G5 IMPL REVIEW | ap-reviewer | Claims ↔ file:line evidence | — |
| G6 VERIFY | ap-verifier | Real runs, verbatim output, regression check | — |
| G7 SIGN-OFF | ap-juror(s) | Fresh jurors, unanimous (T3) | — |
| G8 SCRIBE | ap-scribe | Records only, never edits code | — |
| GOAL-CHECK | ap-goal-checker | Re-derives asks from prompt ledger | NOT-DONE |

**Flow:** L0 conductor → chooser (one AskUserQuestion if attended) → L1 scope coordinator → per-feature framework selection (closed first-match tree, 14 leaves; MISS → generator) → L2 managers → gate ladder per tier.

**Tiers T0–T3** scale rigor (T0: G4→{G5,G6}→GOAL-CHECK; T3 adds conditional G1, unanimous juror panel, convergence sweep). Tier escalates on OUT-OF-SCOPE/redo-budget spend; **never de-escalates**.

**Key loops:** G2∧G3 jointly freeze plans; G3.5 depth-miss → back to G1; G6 FAILED → back to G4; all negatives loop *up*, never sideways. DONE requires zero live subagents, zero open findings, real end-to-end exercise.

**Resume:** explicit-only; reads only GATELOG.md tail frontier row; workers fetch their own slices; debug resume always re-runs G3.5.

## 3. Architecture & code-vs-LLM split

**Prose (doctrine):** `agents/contracts/` is canon — persona .md files (identical 6-section template), 18 framework files, selector tree in `frameworks/README.md` (declared SINGLE SOURCE OF TRUTH; the former `framework-selector.js` was deliberately removed). Judgment lives here: what counts as done, what a depth-miss is, review criteria.

**Code (harness):**
- `autoprompt-gate.js` — topology enforcement: `assertExecLevel` throws RULE-68 TypeError if L0–L2 touches an execution gate; unregistered personas unspawnable; `sealDoneProvenance` single DONE funnel; JSON Schemas requiring sha256/bytes/nonce on missionPointer and every publication.
- `autoprompt-ledger-check.js` — standalone read-only auditor: reconciles every PASS row against spawn + on-disk artifact; mechanical self-review detector (F5-18).
- `supervisor.sh` — OS-level relaunch loop with nonce-verified DONE sentinels, monotonic frontier counter, poison-restart escalation.
- `phase-budget.js` — pure wall-clock budget module with exit-code verdicts.
- `scripts/generate-provider-contracts.cjs` + `runtime-payload.cjs` — one contract JSON → 6 provider trees + sha256 manifests; `--check` drift-diff fails CI before tests run.

**Why the split:** invariants that can be mechanized are enforced twice — doctrine states them, code throws on violation. What can't be mechanized (plan quality, root-cause depth) gets adversarial fresh-context personas with defaults set to reject.

**Caveat:** the gate/ledger harness ships **only for the Claude provider**. The other 5 providers run on prose + supervisor alone — a materially weaker enforcement story.

## 4. Enforcement & verification

**Making the LLM comply:**
- **Default-negative gates:** G3 default-REJECT, G3.5 default-FAIL, GOAL-CHECK default-NOT-DONE; "verdict prose never overrides structured negative evidence."
- **Blind concurrency:** G2‖G3 and G5‖G6 "share no verdict channel" — explicit "Do not read G3's verdict" clauses (GATES.md L82/111/156).
- **Self-review ban, mechanized:** ledger-checker flags any single transcript containing both a production Edit/Write and a real test-runner invocation as P0 — behavioral signature, not prose claim.
- **Cryptographic pinning:** mission pointer = path+sha256+bytes+nonce, verified by every recipient (`INVALID-BRIEF` on mismatch); artifacts, receipts, and installed payloads re-hashed rather than believed.
- **Provenance reconcile:** every claimed PASS must match a recorded persona spawn (correct persona) + existing artifact; fabricated attestation = P0.
- **Fail-closed everywhere:** half-written artifacts = absent; garbage config → default, "never disables the guard"; unmatched task shapes never land on a silent default framework.

**Testing itself:**
- `npm test` chains generator `--check` + manifest `--check` (drift = failure) before node:test suites; CI matrix Node 20/22/24 ubuntu + Node 24 windows; CRLF-normalized hashing keeps pins platform-independent.
- Install pipeline: `verifySource` re-hashes repo tree pre-install; `verifyPayload` fails on missing, altered, **or unexpectedly added** files.
- Lifecycle suites round-trip install→verify→prune and assert tamper detection (appending bytes to GATES.md throws).

## 5. Unique features & clever techniques

| Technique | Where |
|---|---|
| Sealed-hypothesis depth-lock: prober derives D1–D3 blind; proposed fix layer revealed *last*, only for comparison; PASS iff layer==D3 ∧ repro RED unpatched | `agents/contracts/personas/ap-depth-prober.md:20`, `frameworks/backend-fix.md` |
| Names real-world traps verbatim: "the pylint-7080 / xarray-6992 trap", "the astropy miss" — checklists exist to catch specific observed failures | `frameworks/backend-fix.md` |
| Blind concurrent reviewers with no verdict channel | `agents/claude/GATES.md:82,111,156` |
| Mechanical self-review signature (edit + test-run in one transcript = P0) | `autoprompt-ledger-check.js:1510-1528` |
| Single DONE funnel (`sealDoneProvenance`) — no self-reported DONE escapes reconciliation | `agents/claude/workflow/autoprompt-gate.js:1209` |
| On-MISS framework generator: 3-axis classify → gate composition → default-FAIL validation → one remint → escalate; deliberately no promotion registry (regenerate deterministically) | `frameworks/generation.md` |
| Poison-restart supervisor: monotonic frontier counter separates FINISHED / HEALTHY-LONG / TRULY-STUCK; stale DONE sentinels quarantined (renamed), never deleted, with livelock-avoiding reclaim | `supervisor.sh:570-607,1241-1266` |
| Honest-surface invariant: budget breach seals on real landed evidence, "never manufactures coverage" | `phase-budget.js:15-17` |
| One contract → 6 provider trees, drift as CI failure; Prime target even code-gens a Python dispatcher re-implementing the sha256/nonce/depth scheme | `scripts/generate-provider-contracts.cjs` |
| Prose retires its own code: selector JS removed, "never defer routing to it" | `frameworks/README.md:103` |
| Compact pointer briefs: role/boundary/acceptance + hash pointer, never pasted transcripts; resume reads only ledger tail | `SKILL.md` §6, §10 |

## 6. Strengths & weaknesses

**Strengths**
- Independence is engineered three ways (fixed casting, blind concurrency, transcript signature) — hardest-to-fake anti-self-review design seen in this survey.
- Dual-layer enforcement: nearly every doctrine invariant has a matching thrown error / exit code / CI diff.
- Provenance chain is end-to-end cryptographic: mission → briefs → artifacts → install payloads.
- Honest failure posture: fail-closed defaults, escalate-never-fake budget seals, regressions-are-signal rule.
- Single-source generation keeps 6 provider trees provably in sync.

**Weaknesses**
- Mechanical harness is Claude-only; 5/6 providers get prose + supervisor — the "mechanical" story is oversold for them.
- Headline benchmark (82.02%) not reconstructable; only baseline has per-task evidence (self-disclosed).
- Heavy: ~730 lines of doctrine + large harness; token/latency cost of blind duplicate reviews and fresh-context verifiers is significant.
- Kilo provider is string-substituted OpenCode output — fragile derivation.
- Complexity risks drift between prose and code layers despite the CI gates (the ledger-checker's rule registry is mostly unimplemented placeholders).

## 7. Adaptable ideas

- Blind concurrent review: two reviewers, no verdict channel, join after both report; negative loops upward.
- Hash-pinned mission pointer (path+sha256+bytes+nonce) verified by every subagent; mismatch = refuse, never reconstruct.
- Default-negative gates: verifier/goal-checker start at REJECT/NOT-DONE, flipped only by evidence; prose never overrides negative structured evidence.
- Mechanical self-review detection from transcript signatures (production edit + test run in one context).
- Sealed-hypothesis root-cause probe: derive independently, compare to proposal last.
- Encode past real failures as named traps in checklists ("the astropy miss").
- Single DONE funnel reconciling claims against spawn log + on-disk artifacts.
- Resume-from-frontier: read only ledger tail; workers fetch own slices (context minimalism).
- One canonical contract → generated per-target renderings with `--check` drift-diff wired into CI before tests.
- Fail-closed framework generator for unmatched task shapes (classify → compose → validate default-FAIL → one remint → escalate); no silent default path.
- Supervisor poison-restart guard: monotonic progress counter distinguishes healthy-long from stuck; quarantine (rename) stale completion sentinels, never delete.
- Honest-surface budget seal: timeout closes on genuinely landed evidence, never synthesizes coverage.
- Tier ratchet: rigor escalates on scope surprises, never de-escalates.
- Install integrity: verify source pre-install, fail on missing/altered/*added* files at destination.
- Persona files from one 6-section template — uniform corpus, only role body varies.
