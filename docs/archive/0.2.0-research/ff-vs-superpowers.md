# Feature Forge vs Superpowers — comparative review

**Executive summary.** Superpowers is empirically hardened enforcement: short fenced laws, numbered gates, Excuse→Reality tables, and scripts for every deterministic step, all iterated against observed agent failures. Feature Forge is a rigorous formal contract: a fourteen-stage state machine with strong invariants, but expressed almost entirely as dense prose the LLM must remember, self-execute, and self-attest — deterministic checks included. The highest-value moves are shipping a small `ff-check.py` for the mechanical gates (rule A), and reshaping the load-bearing prose into fenced laws, numbered steps, and recognition tables (rule B).

Golden rules: **A** = code for deterministic work; **B** = LLM tasks single, measurable, bounded, minimum prose.

---

## Adopt now (ranked)

**1. Ship `ff-check.py` — code for every deterministic gate** — impact: high — rule A
- Superpowers: `subagent-driven-development/scripts/` (`sdd-workspace`, `task-brief`, `review-package`) — scripts derive paths, extract text, package diffs; they fail loudly and never enter controller context.
- FF gap: slug validation (`references/workflow.md:20-23`), frozen `<path>@<git-blob-id>` recomputation at 8+ gates (`workflow.md:44-47` + Stages 6-11), post-review seal comparison (`workflow.md:93-96`), preflight collision inventory (`workflow.md:170`), and both copy-time checklists (`assets/ledger-template.md:118-124`, `final-report-template.md:104-113`) are all prose the LLM executes from memory and self-attests.
- Proposal: one script, subcommands `paths`/`preflight` (validated slug → all canonical paths, collision inventory, lowest unused suffix), `identities` (recompute blob IDs, MATCH/DRIFT), `seal-diff` (reuse review-loop's seal format — never a parallel manifest — allowlist = ledger path + review evidence ref), `lint-ledger`/`lint-report` (mechanical fields, enum vocab, next-action arity, no blob ID on mutable records; unattended mode → empty Human-UAT branch, no `user`/named-human authority), and non-committing `checkpoint-check` (canonical message, no-delta, nothing foreign staged). Script never writes the ledger; interpreting failures stays LLM work. Stage prose shrinks to "run the command; nonzero → read-only reconciliation." Note: `workflow.md:15-16` has no slot for a numeric suffix — resolve by suffixing the slug so it propagates to all paths, and amend `workflow.md:20-23`. Scripts are installed payload under `feature-forge/scripts/` with tests.

**2. SessionStart hook: active-run pointer** — impact: high — rule A
- Superpowers: `hooks/session-start` injects the meta-skill as unmissable context every session.
- FF gap: resume correctness depends entirely on the model choosing to re-read the ledger (`SKILL.md:14-22`); after compaction nothing detects an active nonterminal run.
- Proposal: hook globs `docs/feature-forge/runs/*/ledger.md`; if not `complete`, inject only the ledger path + "active run exists; read it and every artifact it names; do not start a new run." No parsed state. Register under SessionStart (`startup|clear|compact`); document that install.py/Codex users lack this backstop and pair with an `ff-check.py runs` subcommand the controller runs at Start-or-resume.

**3. One Iron Law in a fence** — impact: high — rule B
- Superpowers: `verification-before-completion/SKILL.md:16-18` — one fenced law + one-line consequence per skill.
- FF gap: `SKILL.md:8-12` core invariant is descriptive prose; the load-bearing rule is the third clause of the second sentence.
- Proposal: replace the section with a three-line fence — `ONE CANONICAL RUN.` / `FEATURE FORGE IS THE OUTER CONTROLLER FROM PREFLIGHT THROUGH FINISH.` / `THE LEDGER NAMES ONE NEXT ACTION. DO ONLY THAT.` — plus consequence line; two "no exceptions" bullets (no dispatch without persisted ledger; no `finish-authority` before persisted `finish_id`/`ready`) as pointers, not restatements.

**4. Red flags → stop-list + Excuse→Reality table** — impact: high — rule B
- Superpowers: `verification-before-completion/SKILL.md:50-72` — one condition per bullet, then a Thought|Reality table; recognition tables are the measured-effective phrasing.
- FF gap: `SKILL.md:59-64` packs seven stop-conditions into one 30-word clause; real harvested rationalizations are buried as prose in `authority.md:50-58, 177-184`, `final-report-template.md:38-42`, `CLAUDE.md:64-69`.
- Proposal: one bullet per condition + closing "reconcile read-only, then recover; do not infer state"; keep the finish-ordering prohibition as its own bright line; ~8 first-person trigger thoughts and an Excuse→Reality table seeded only from the four harvested clauses, Reality column citing the owning reference. Sources stay intact.

**5. State the Finish contract once; gate the heavy reference** — impact: high — rule B
- Superpowers: `writing-skills/SKILL.md:233-241, 256-259` — cross-reference, never restate; progressive disclosure on observable predicates.
- FF gap: the Stage 13/14 contract is prose-restated in `SKILL.md:40-50`, `CLAUDE.md:108-128`, and canonically in `workflow.md:279-388`; all three can drift. `SKILL.md:20` also force-loads all 6,669 words of references before any dispatch.
- Proposal: SKILL.md keeps only the fenced phase line + two bright lines (persist-before-claim; exactly-once) + "see workflow.md"; CLAUDE.md's Finish section becomes a one-line pointer. Split `workflow.md:279-388` into `references/finish-protocol.md` gated on "ledger records a finish_id or any Finish phase"; keep workflow.md and authority.md mandatory, gate adapters-and-reviews.md on first adapter dispatch.

**6. Numbered actions and numbered gates** — impact: high — rule B
- Superpowers: `verification-before-completion/SKILL.md:23-36` — 5-step gate closed by "skip any step = lying"; per-phase checkbox lists in writing-skills.
- FF gap: Stage 1's owned action is one ~190-word sentence chaining ~10 actions (`workflow.md:170`); the three highest-risk gates (pre-dispatch persist, Stage 11 final verification, Stage 14 pre-claim capability) are narrated paragraphs (`workflow.md:69-70, 247-253, 297-308`).
- Proposal: split any stage owning ≥5 obligations (Stage 1; optionally 13) into a numbered one-verb-per-line list; rewrite the three gates as 4-5 ordered steps naming the exact command/artifact (`ff-check.py seal-diff`, `identities`, capability receipt path), closed with "skip a step = fabricating the gate." Net word count goes down. Name both copy-time checklists as Stage 1 / Stage 13 exit evidence: "an unticked box blocks the transition."

**7. Review-round termination rule** — impact: high — rule B
- Superpowers: `subagent-driven-development/SKILL.md:354-429` — 5-round cap, escalation ladder, mandatory adjudication at cap.
- FF gap: `changes_required` loops are open-ended (`workflow.md:204, 228, 244`); oscillation reaches `blocked` only if review-loop itself reports it — the controller has no rule.
- Proposal: record round number in the Reviews table; add one round invariant — a round whose surviving actionable findings are not a strict reduction of the prior round's is oscillation, mapped to `blocked` under the existing NOT-CONVERGED row with the findings named. No new escalation machinery.

---

## Adopt later (ranked)

**8. Pressure-test scenarios + symptom-first description** — impact: high — rule B
- Superpowers: `writing-skills/testing-skills-with-subagents.md` — test skills on subagents under pressure, harvest rationalizations verbatim, close each loophole; descriptions carry "about to violate" symptoms.
- FF gap: zero behavioral verification (`CLAUDE.md:132-140`); rules were written from design reasoning. `SKILL.md:3` triggers on a subjective "warrants" judgement and omits resume — the highest-risk entry path.
- Proposal: after the now-batch lands, run ~6 with-skill forced-choice scenarios at the invariant gates (inadequate UAT substitute; "just merge it"; blob-identity drift; crash at `menu_pending`; "implement now"; dirty base at Option 1), record rationalizations verbatim in `feature-forge/tests/scenarios/`, feed them into item 4's table; gate edits to SKILL.md and owner references on re-running affected scenarios. Rewrite the description resume-first with observable symptoms, then re-test it.

**9. Ledger schema tightening** — impact: medium — rule A
- Superpowers: SDD records `commits <base7>..<head7>` per task (multi-commit tasks are normal); every ledger line is fixed-shape and grep-able.
- FF gap: implementation table records one `commit` per task (`workflow.md:39`, `ledger-template.md:44`), leaving the review/resume range undefined; two ledger fields mandate "plain language" where the same sentence names a fixed enum (`ledger-template.md:62-63, 76-77`).
- Proposal: column becomes `commits (base..head)` (BASE via `git rev-parse HEAD` before dispatch — never `HEAD~1`); convert both fields to enums, registering the vocabularies in workflow.md's states section first so the template doesn't invent vocab. Both feed `lint-ledger`.

**10. `ff-finish-gate` precondition checker** — impact: high — rule A
- Superpowers: SDD's compaction-survivable fixed-shape state markers make resume mechanical.
- FF gap: the six-phase exactly-once Finish journal — the one irreversible step — is guarded by ~110 lines of prose (`workflow.md:279-388`); legal-transition and receipt-presence checks are deterministic.
- Proposal: `ff-finish-gate LEDGER TARGET_PHASE` asserts the edge is legal, required receipts non-empty, `finish_id` unchanged; prints ALLOW/DENY + missing fields. Strictly a precondition checker, never an authorizer (CLAUDE.md forbids a parallel state machine); ALLOW is necessary not sufficient; exactly-once still rests on the durable journal. Don't script the terminal receipt (its location is judgment).

**11. Worker-packet contract fixes** — impact: high — rule B
- Superpowers: `writing-plans/SKILL.md:84-97` — every plan task carries Files + exact interface signatures because the implementer sees only its own task; handoffs travel as script-produced files, not pasted prose (`subagent-driven-development/SKILL.md:230-271`).
- FF gap: the packet demands fields (`adapters-and-reviews.md:133-138`) the frozen plan is never required to contain, so the controller authors them at dispatch — the "inventing cross-task authority" the packet forbids; and `adapters-and-reviews.md:143-145` bans materializing packets, forcing controller transcription of blob-sealed frozen text.
- Proposal: name writing-plans' per-task structure in plan-return's retained method and make it Plan review's mechanical completion criterion; add "every packet field is copied from the frozen plan, never authored at dispatch — a missing field is a plan defect routed through the invalidation graph." Clarify the prohibition means no competing *canonical* artifact: run-scoped git-ignored scratch files are permitted transport; frozen task text reaches workers by deterministic extraction. Also reframe the packet as covering the dispatched scope (one *or more* same-shape tasks), with one ledger row per task regardless.

**12. Prose micro-pass bundle** — impact: medium — rule B
- Superpowers: ✅/❌ pairs (`verification-before-completion/SKILL.md:76-104`); positive recipes beat composition prohibitions (measured, `writing-skills/SKILL.md:459-470`); fixed-field material goes in tables; exceptions become conditionals on observable predicates.
- FF gap + proposal, four small edits: (a) `authority.md:172-184` — keep the four-field fence, replace ~150 words with one rule line + three ✅/❌ rows; delete "(for example, Sam)". (b) Flip two composition prohibitions to recipes: `ledger-template.md:123` and `final-report-template.md:112` → "each cell holds an ID, status term, path, commit, evidence reference, or one-sentence rationale — never restated spec/plan/review text." (c) `adapters-and-reviews.md:12-113` — hoist the shared block rule once, tabulate the four uniform adapter fields, keep boundaries as prose. (d) Two nuance-clause fixes only: move the atomicity disclaimer (`workflow.md:283-285`) to a note under the phase fence; rewrite `adapters-and-reviews.md:82-83` as "If the ambiguity is non-material and in scope: the wrapped skill rules on it and continues." Plus one line in SKILL.md Outer control: after every adapter return, state both native verdicts, the mapped result, and the re-read sole next action before proceeding.

---

## Not worth adopting

- **RED-baseline skill testing (run scenarios without the skill)** — the skill exists; only with-skill gate behavior matters now.
- **Five Iron Laws** — one law covers it; the rest are downstream and would dilute the fence.
- **Per-action pre-announcements** — redundant with the mandated fourteen-stage native projection; keep only the post-return verdict statement.
- **Mechanical em-dash/nuance-clause purge** — would strip legitimate appositives and anti-rationalization counters; fix the two real sites only.
- **Committing checkpoint script** — auto-commit removes the controller's staged-diff inspection; check-only variant adopted instead.
- **New seal manifest format (`ff-seal` à la review-package)** — a second digest format forks the ledger's seal semantics; reuse review-loop's own seal.
- **Ledger-recorded packet path + content hash** — frozen blob identity plus the recorded commit range already make dispatches auditable.
- **File-level reference gating table (3 rows)** — authority.md is needed at too many stages to gate; only adapters-and-reviews.md and the Finish protocol gate cleanly.
- **Escalation ladder (fresh worker, higher model tier) at round caps** — new machinery outside FF's vocabulary; the strict-reduction oscillation rule terminates loops without it.
- **Batched-dispatch permission structure** — batching selection belongs to the wrapped skill's retained method; the packet reframing in item 11 suffices.
