# zeroshot — review-pipeline mechanisms worth adapting

Source: `~/kramtime/zeroshot/` cluster templates. The four `code-review-*`
templates (bell/book/candle/conductor) are thin routers; the substance is in
`cluster-templates/base-templates/code-review-workflow.json` (37KB) plus the
conductor, with `docs-review-workflow.json` adding one idea. Key files:
- `cluster-templates/base-templates/code-review-workflow.json`
- `cluster-templates/code-review-conductor.json`
- `cluster-templates/base-templates/docs-review-workflow.json`
- `lib/quality-detection.js`, `scripts/quality-gate-runner.js`

## Pipeline shape (context)

Conductor classifies the change on ChangeScope (PATCH/MODULE/CROSS_CUTTING)
× RiskDomain (GENERAL/SENSITIVE) plus surface flags (security/test/API) →
picks a tier (bell: 1 validator, 3 iters; book: 2, 4; candle: 2, 5). The
workflow runs one analyst (fans out per-perspective finder subagents) +
1-2 validators + a compile-only synthesizer + a completion detector, over a
SQLite message bus. Validators verdict every finding per round; any
rejection re-wakes the analyst; terminate on unanimous approval or cap.

## New mechanisms (numbered refs are lines in code-review-workflow.json)

1. **Split verifier roles: fact-checker vs rigor-checker.** (:333, :441)
   validator-evidence verifies only factual claims (file/line exists, code
   does what's claimed, no resolving context missed) and is forbidden from
   judging severity. validator-rigor assumes quotes are accurate and judges
   only severity calibration + whether impact follows. Decomposes "precision
   gate" into disjoint charters: "is this real?" never conflated with "does
   this matter?" Both must clear.

2. **DOWNGRADE verdict with suggestedSeverity, preferred over REJECT.**
   (:310, :428) A real-but-overstated finding is kept and re-ranked, not
   discarded ("REJECT only if egregious — LOW marked CRITICAL"). Triage
   analogue: inflated findings drop below the block line but survive as
   non-blocking, rather than being thrown out.

3. **NEEDS_EVIDENCE distinct from REJECT.** (:310) "Cannot locate the
   referenced file/line" routes to substantiate-or-withdraw; "code
   contradicts the claim" routes to refuted. Different verdicts, different
   remediation.

4. **Monotonic finding-set ratchet.** (:204-205) Round 1 is the ONLY round
   that may introduce findings ("wide net"); every later round may only
   refine (stronger evidence) or withdraw contested ones; accepted findings
   are frozen. Distinct from (and complementary to) the diff-scope ratchet —
   this ratchets the finding SET, guaranteeing convergence by construction.
   Strong candidate to adopt.

5. **Synthesizer as pure compiler.** (:597) Terminal report is compiled from
   the message ledger only — "Do NOT re-analyze code" — tracing each
   finding's refine/withdraw chain. No fresh judgment leaks in at summary
   time. (Rhymes with /code-review's synthesis-by-index.)

6. **Deterministic verdict rollup where unresolved-at-cap == FAIL.** (:597)
   First-match precedence: confirmed CRITICAL or ANY still-contested finding
   → NOT_READY; confirmed HIGH → SIGNIFICANT_ISSUES; etc. The loop cannot
   "time out to green" — hitting the round cap with unresolved blocking
   findings is a blocking outcome. Directly applicable to our cap-5 rule:
   cap exhaustion with surviving Important+ must be reported as unresolved,
   never a silent pass.

7. **Fail-closed on verifier crash.** (:379, :487) A validator's onError
   publishes approved:false — a crashed verification counts as rejection,
   never as skipped. Analogue: a reviewer/triage pass that fails to complete
   is "not cleared", not "no findings".

8. **Pre-review quality gate.** (:672-701, quality-gate-runner.js) Lint/
   typecheck/tests run BEFORE any LLM review; failure kills the cluster.
   Don't spend expensive review on code that doesn't build. Command
   auto-detection per ecosystem in lib/quality-detection.js.

9. **Risk classification sizes the loop; flags mandate lenses.**
   (conductor) Scope×risk picks verifier count/iteration cap/model tier;
   independently, surface flags force specific perspectives ("security
   surface → MUST spawn Security Reviewer"). Size the loop to detected
   risk; force-enable lenses on sensitive surfaces.

10. **Classifier escape hatch.** (:204) Perspectives the classifier turned
    off are carried as "(INACTIVE): activate only if you discover relevant
    changes the classifier missed." Upstream routing never hard-suppresses
    a reviewer who finds the routing was wrong.

11. **Junior→senior escalation, decision-forcing, safe-default bias.**
    (conductor :51, :135) Cheap classifier may say UNCERTAIN → escalates to
    a senior pass forbidden from punting, with explicit bias ("Unsure →
    SENSITIVE; missing a security review is worse than an unnecessary one")
    and a safe-tier fallback if both fail.

12. **Unanimous approval across heterogeneous verifiers as the pass gate.**
    (:243, :628) Advance only when EVERY validator approves the round; one
    REJECT/NEEDS_EVIDENCE re-triggers. With #1: facts AND rigor must both
    hold — consensus across disjoint mandates, not majority vote.

13. **Category-scoped specialist validators that auto-ACCEPT out of scope.**
    (docs-review-workflow.json) A specialist (testability, traceability)
    verdicts only findings in its category and auto-approves the rest.
    Lets you add a domain lens (concurrency, crypto) with veto power only
    inside its domain, without diluting attention or blocking unrelated
    findings.

## Framings worth stealing near-verbatim

- Severity anchored to review-evasion: "CRITICAL: silent runtime bug that
  passes review unnoticed" — top tier tied to "would slip past a reviewer",
  sharper than generic impact. (:204, :441)
- Recall/precision split stated TO THE FINDER: "false positives > missed
  issues (validators will filter)". (:204)
- Verifier calibration guard: "Accept REASONABLE evidence. Do not demand
  certainty. REFINED findings: evaluate NEW evidence fairly. No new
  objections to previously-accepted findings" — blocks re-litigation from
  the verifier side, complementing the SETTLED list. (:441)
