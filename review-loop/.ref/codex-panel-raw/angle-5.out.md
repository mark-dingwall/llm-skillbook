material findings: 8

1. **The viable v1 is a six-stage ledgered loop; adopting the full mechanism catalogue would make the skill unfollowable**
   - Concrete risk: an executor juggling split verifiers, unanimity, numerous finder angles, multiple disposition vocabularies, fraud catalogues, twin checks, gap sweeps, forced artifacts, classifiers, reconciliation, and reporting can omit the load-bearing transition—such as leaving a verified blocker out of the next round—while still producing the appearance of rigor.
   - Minimal core: `quality/scope gate → bounded round-1 review → deterministic finding ledger and triage → fix/test → diff-plus-fix-manifest re-review → pass or unresolved hand-back`.
   - Load-bearing: immutable scope; evidence-bearing findings; stable finding IDs; independent triage; explicit remediation states; diff-scoped directed re-review; backlog; deterministic reconciliation; fail-closed cap.
   - Nice-to-have, activated by risk: one specialist lens, state-space enumeration, changed-test scrutiny, twin search, authority ordering, and one gap sweep.
   - CUT from v1: split fact/rigor agents, unanimous multi-verifier approval, junior/senior classifier escalation, exhaustive angle fan-out, repeated gap sweeps, mandatory Strengths/Recommendations, and forced artifacts beyond one reproducible observation per finding. Also cut the monotonic finding-set rule and global “stop on any unclear item,” for reasons below.
   - Sources: all design sources, especially `zeroshot-notes.md`, `fable-method-notes.md`, and `code-review-analysis.md`.
   - Confidence: **PLAUSIBLE** — the combined skill has not been evaluated, so prompt-compliance failure cannot be traced directly. `fable-method-notes.md` supplies component-level evidence that prose rules often fail, but no source tests the accumulated design.
   - Refutation: I removed mechanisms already marked optional or non-transferable and checked whether the remainder formed disjoint responsibilities. It still contains redundant verification agents, verdict systems, and review-expansion mechanisms around a much smaller convergence kernel.

2. **“SETTLED” conflates finding validity with fix completion**
   - Scenario: round 1 accepts an Important finding; the attempted fix handles only one trigger. Round 2 is simultaneously told not to re-litigate the accepted finding and to audit the applied fix, so a reviewer may suppress the still-open defect and incorrectly pass.
   - Replace `SETTLED` with two independent dimensions: claim disposition (`CONFIRMED | REFUTED | UNVERIFIABLE`) and remediation state (`OPEN | FIX_APPLIED | RESOLVED | BACKLOG | INTENTIONAL`). Only `RESOLVED`, `REFUTED`, and `INTENTIONAL` suppress review; `FIX_APPLIED` creates a mandatory verification task.
   - Sources: `loop-prompt-draft.md`, `redteam-prompt-notes.md`.
   - Confidence: **CONFIRMED** — `loop-prompt-draft.md:37` says, “SETTLED — already accepted or refuted; do not re-litigate,” while `redteam-prompt-notes.md:16-18` says later rounds must “audit whether each fix does what it claimed and what it might have broken.”
   - Refutation: I checked whether “accepted” could mean “accepted as resolved.” Line 46 says SETTLED is updated with findings “accepted or refuted” during triage, before the subsequent fix has been re-reviewed, so that interpretation does not resolve the conflict.

3. **The monotonic finding-set ratchet would hide fix-introduced regressions**
   - Scenario: fixing a validation defect introduces an authorization bypass at a newly touched line. Because it has no round-1 finding ID, a strict “later rounds may only refine or withdraw” rule forbids reporting it—the opposite of directed fix re-review.
   - CUT this ratchet. Keep monotonicity only for historical decisions: unchanged old findings cannot be re-litigated, but genuinely new defects inside the inter-round diff remain admissible and receive new IDs linked to the inducing fix.
   - Sources: `zeroshot-notes.md`, `redteam-prompt-notes.md`, `loop-prompt-draft.md`.
   - Confidence: **CONFIRMED** — `zeroshot-notes.md:43-46` says round 1 is “the ONLY round that may introduce findings”; `redteam-prompt-notes.md:16-18` requires checking “what [each fix] might have broken.”
   - Refutation: I considered treating every regression as a refinement of the original finding. That loses distinct root cause, severity, location, and remediation history, and cannot represent unrelated scope-creep defects in the fix diff.

4. **“Fail closed” has incompatible meanings, leaving reviewer-CLI failure able to produce green**
   - Scenario: the adversarial reviewer times out, refuses, or emits unparsable prose. It surfaces no candidate; the terminal rule sees no surviving Important finding and passes—even though a mandatory review role never ran successfully.
   - Give pipeline health a separate state from finding disposition. Each call needs a deadline, captured exit status, output-schema validation, and one bounded retry. Invalid output is never treated as an empty review. A round cannot advance until required breadth/adversarial roles succeed; exhaustion yields `INDETERMINATE`, with diagnostics and a human retry/degrade decision.
   - Sources: `loop-prompt-draft.md`, `code-review-analysis.md`, `zeroshot-notes.md`.
   - Confidence: **CONFIRMED** — the sources prescribe three different outcomes: `code-review-analysis.md:109-111` says no-verdict candidates are “dropped”; `loop-prompt-draft.md:56-57` says no-verdict findings are not silently dropped; `zeroshot-notes.md:63-66` says a verifier crash is “not cleared.”
   - Refutation: I checked whether these rules cleanly addressed different stages. They do not cover a finder that returns no valid candidate envelope, and the draft has no health/quorum condition separate from finding counts.

5. **The inherited “always review” policy lacks a boundary for invoking the full loop**
   - Scenario: a generated-file refresh or one-line mechanical rename triggers up to five multi-agent rounds because the invoked skill says never skip simple work. Cost rises without materially improving assurance, encouraging users to bypass the skill entirely.
   - Define three entry outcomes: stop immediately for empty scope or failed deterministic quality gates; use a single bounded review for low-risk mechanical changes; use the loop for explicit requests or security/auth, concurrency, persistence/migrations, public contracts, cross-cutting behavior, and materially large changes.
   - Sources: `requesting-code-review/SKILL.md`, `zeroshot-notes.md`, `code-review-analysis.md`.
   - Confidence: **CONFIRMED** — `requesting-code-review/SKILL.md:92-95` says, “Never… Skip review because ‘it’s simple’,” while `zeroshot-notes.md:73-77` says risk classification should size the loop.
   - Refutation: I checked whether risk-sized reviewer counts implicitly permit zero rounds or a single pass. The described tiers all instantiate a review workflow; none defines when the multi-round skill itself is inappropriate.

6. **Five rounds do not bound cost because reviewer count per round is unbounded**
   - Scenario: six “high complexity” areas produce eight reviewers per round; five rounds mean 40 high-reasoning CLI calls before retries, triage, tests, or synthesis. A repository-scale change can exhaust context, money, or wall time without reaching the round cap.
   - Add a preflight budget: configurable maximum reviewers, external calls, wall time, and—where observable—tokens/cost. A sensible default is at most four reviewers in round 1 and two directed fix reviewers thereafter. Exceeding a budget should hand back current state and ask whether to continue, narrow scope, or degrade.
   - Sources: `loop-prompt-draft.md`, `code-review-analysis.md`, `zeroshot-notes.md`.
   - Confidence: **PLAUSIBLE** — the sources contain candidate/report caps, risk sizing, and empirical agent counts, but no absolute call, time, or spend ceiling. Exact token accounting may also be unavailable from the reviewer CLI.
   - Refutation: I checked whether the five-round cap or per-finder finding caps bound execution cost. Neither bounds `one per area of high complexity`, retries, or long-running calls.

7. **Wholesale use of `receiving-code-review` imports a global human stop into an otherwise autonomous loop**
   - Scenario: one unclear Minor suggestion causes “STOP—do not implement anything,” preventing an independently confirmed Critical fix and forcing unnecessary human intervention.
   - Override that rule per finding: uncertain non-blockers go to Open Questions/backlog; other verified fixes continue. Show a concise status after every round, but pause only for ambiguous blocking intent, conflict with user authority, destructive/public-contract decisions, budget exhaustion, or the same blocker surviving two fix attempts. Thus a human can intervene before round 5 without becoming a mandatory hop every round.
   - Sources: `loop-prompt-draft.md`, `receiving-code-review/SKILL.md`.
   - Confidence: **CONFIRMED** — `loop-prompt-draft.md:44` says receiving-code-review “governs verification and pushback”; `receiving-code-review/SKILL.md:43-45` says, “IF any item is unclear: STOP… ASK.”
   - Refutation: I checked the external-reviewer-specific branch for a narrower rule. It still asks the human whenever verification is difficult and supplies no per-finding continuation policy.

8. **“Non-code: adapt” is incompatible with mandatory inter-round git diffs**
   - Scenario: the subject is an uncommitted document outside Git, a generated report, binary artifact, API response, or remote configuration. Round 1 can review it, but round 2 has no trustworthy `diff_range`; silently falling back to full review recreates the fresh-finding non-convergence problem.
   - Require a subject adapter that produces a frozen snapshot ID and canonical inter-round delta. Text can use normalized patches; structured data can use semantic diffs; opaque artifacts need domain extraction plus hashes. If no trustworthy delta exists, permit only one review round or require explicit before/after revisions.
   - Sources: `loop-prompt-draft.md`, `code-review-analysis.md`, `redteam-prompt-notes.md`.
   - Confidence: **CONFIRMED** — `loop-prompt-draft.md:13` says, “Non-code subject: adapt,” but lines 34-36 require a `diff_range`; `code-review-analysis.md:126` says every phase is diff-anchored.
   - Refutation: I checked whether `files`/`context_files` or the frozen-tree rule supplies revision identity. They identify material and prevent drift but do not produce an inter-round delta for non-Git or opaque subjects.
