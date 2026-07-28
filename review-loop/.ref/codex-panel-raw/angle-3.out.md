material findings: 8

1. **`SETTLED` suppresses verification of incomplete fixes**

   **Failing scenario:** Round 1 accepts Important finding F1. The applied fix handles only one trigger. Round 2 receives F1 under `SETTLED` and obeys “do not re-litigate,” so the still-broken behavior is suppressed unless promoted to Critical. The loop can terminate incorrectly.

   **Sources:** `loop-prompt-draft.md`, `redteam-prompt-notes.md`.

   **Confidence: CONFIRMED.** The draft says, “`SETTLED — already accepted or refuted; do not re-litigate`” (line 37) and later, “update SETTLED with findings accepted or refuted” (line 46). Acceptance is therefore conflated with verified resolution.

   **Refutation:** I checked whether the proposed fix manifest overrides `SETTLED`. `redteam-prompt-notes.md` proposes directed fix verification, but no precedence rule permits reopening the original finding. Use lifecycle states such as `ACCEPTED_OPEN → FIX_APPLIED → FIX_VERIFIED`; only `REFUTED` and `FIX_VERIFIED` belong in `SETTLED`.

2. **The monotonic finding-set ratchet forbids reporting new fix regressions**

   **Failing scenario:** Fixing F1 introduces an unrelated authorization bypass in the inter-round diff. The diff-scoped reviewer finds it, but zeroshot’s proposed rule allows later rounds only to refine or withdraw existing findings. Treating the bypass as a refinement corrupts identity; rejecting it misses a blocker.

   **Sources:** `zeroshot-notes.md`, `loop-prompt-draft.md`, `fable-method-notes.md`.

   **Confidence: CONFIRMED.** `zeroshot-notes.md` says, “Round 1 is the ONLY round that may introduce findings” (lines 43–47), while `fable-method-notes.md` explicitly requires hunting fix-diff scope creep, new dependencies, debris, and spec betrayal (lines 61–68).

   **Refutation:** I checked whether every fix regression could inherit the repaired finding’s identity. Unrelated regressions and drive-by changes have different root causes. The ratchet needs a narrow exception: later rounds may create findings only for defects introduced or exposed by the inter-round diff.

3. **Reconciliation has neither exclusive buckets nor a defined counting unit**

   **Failing scenario:** Three reviewers report one defect. Triage confirms it, downgrades it from Important to Minor, and backlogs it because it is out of scope. Is `surfaced` three raw reports or one canonical finding? Is the right side one accepted, one backlogged, both, or neither? Every interpretation either breaks the equation or double-counts.

   **Sources:** `loop-prompt-draft.md`, `code-review-analysis.md`, `zeroshot-notes.md`, `fable-method-notes.md`.

   **Confidence: CONFIRMED.** The draft requires “`surfaced = accepted + refuted + backlogged`” and also “Merge same-root-cause findings by reference” (lines 58–60). The other sources add `DOWNGRADE`, `NEEDS_EVIDENCE`, and `UNVERIFIABLE`, which are not mutually exclusive with acceptance or backlog.

   **Refutation:** I checked whether these could all be terminal dispositions. They operate on different axes: factual status, severity, scope/action, and lifecycle. Use separate fields and equations, such as `raw reports = canonical findings + duplicate aliases` and `canonical findings = resolved + unresolved`.

4. **Backlogging an Important finding contradicts the severity contract**

   **Failing scenario:** In round 2, a reviewer conclusively finds an out-of-diff Important defect. Triage backlogs it, and the loop terminates because backlog never triggers another round—even though Important is defined as independently merge-blocking.

   **Sources:** `loop-prompt-draft.md`.

   **Confidence: CONFIRMED.** Line 23 says Important means “you would block the merge over this finding alone.” Lines 44–46 send verified out-of-diff non-Critical findings—including Important—to backlog and declare that backlogged items never trigger another round.

   **Refutation:** I checked the Critical exception and final backlog report. Neither reconciles a known merge-blocker with a passing terminal result. Either backlog severity must be capped at Minor, or convergence and merge-readiness must be separate verdicts.

5. **Unresolved triage states have no executable termination semantics**

   **Failing scenario:** A reviewer supplies a traced Important finding, but the triager disputes it without conclusive counterproof; alternatively, credentials are required to verify it, or triage never returns a verdict. The draft can neither reconcile the finding nor determine whether it blocks termination.

   **Sources:** `loop-prompt-draft.md`, `zeroshot-notes.md`, `fable-method-notes.md`.

   **Confidence: CONFIRMED.** The draft says PLAUSIBLE findings are promoted or refuted (line 44), while its held-back rule merely says no-verdict findings are “not silently dropped or assumed resolved” (lines 56–57). The companion sources require `NEEDS_EVIDENCE`, `UNVERIFIABLE`, fail-closed crashes, and unresolved-at-cap failure.

   **Refutation:** I checked whether “survive verification” implicitly covers these states. It cannot reliably do so because they did not complete verification. Define `UNTRIAGED`, `VERIFICATION_ERROR`, `NEEDS_EVIDENCE`, `UNVERIFIABLE`, and `CONTESTED` as explicit unresolved states; potential Important-or-above findings must block success until resolved or knowingly handed back at cap.

6. **No stable finding identity or lineage exists across rounds**

   **Failing scenario:** Reviewer A reports a faulty invariant at one line; reviewer B reports its downstream manifestation elsewhere. After a fix shifts both lines, round 2 returns stronger evidence in different wording. The orchestrator can merge distinct defects, reopen a settled duplicate, or suppress a legitimate refinement.

   **Sources:** `loop-prompt-draft.md`, `code-review-analysis.md`, `code-review-workflow.js`.

   **Confidence: PLAUSIBLE.** This is an absence: exhaustive keyword inspection found no global ID assignment, alias, parent, or supersession schema. The single-round workflow uses temporary local indices and strips them from its final findings; those indices cannot satisfy the draft’s cross-round “by reference” rule.

   **Refutation:** I checked whether file/line or normalized prose could serve as identity. Lines move, paraphrases vary, and same-root findings may span locations. Assign immutable canonical IDs at ingestion, retain every reviewer report as an alias, and record `refines`, `duplicates`, `supersedes`, fix-attempt, and location-history edges.

7. **The round state is not durable or atomically recoverable**

   **Failing scenario:** Triage accepts two findings, refutes one, applies one fix, then crashes. On restart, temporary reviewer outputs may be gone, the prior frozen tree may no longer be reconstructable from an edited worktree, and it is unclear which verdicts or fix links committed. Re-running reviewers can generate a different set and restart non-convergence.

   **Sources:** `loop-prompt-draft.md`, `redteam-prompt-notes.md`, `zeroshot-notes.md`.

   **Confidence: PLAUSIBLE.** I could not trace any persistence format, checkpoint boundary, resume algorithm, or atomic phase marker in the draft. Zeroshot’s durable message ledger is described only as an external mechanism, not integrated into this design.

   **Refutation:** I checked whether `SETTLED`, `INTENTIONAL`, backlog, and diff ranges collectively reconstruct state. They omit raw outputs, canonical IDs, pending verdicts, fix-to-finding links, verification evidence, and exact before/after tree identities. Persist an append-only ledger before mutations and checkpoint each phase with immutable tree OIDs.

8. **`INTENTIONAL` decisions never expire when their premises change**

   **Failing scenario:** Round 1 records missing validation as intentional because an upstream invariant guarantees the input. A later fix weakens that invariant. Reviewers continue receiving the unconditional `INTENTIONAL` entry and suppress the now-real defect.

   **Sources:** `loop-prompt-draft.md`.

   **Confidence: PLAUSIBLE.** The draft defines `INTENTIONAL` as “deliberate decisions, not defects” (line 38) and continually updates it (line 46), but provides no authority, assumptions, dependency anchors, challenge rule, or invalidation condition.

   **Refutation:** I checked whether the diff-scope rule or Critical escape hatch protects against stale intent. The Critical exception applies only to `SETTLED`, not `INTENTIONAL`, and an Important regression would remain suppressed. Intent records need rationale, authority, dependent assumptions/locations, and mandatory revalidation when those dependencies change.
