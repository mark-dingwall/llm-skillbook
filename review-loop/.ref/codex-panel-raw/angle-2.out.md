material findings: 8

1. **Critical is undefined despite receiving convergence-breaking privileges**
   - In round ≥2, a reviewer can label an unrelated pre-existing bug “Critical” and thereby admit it into the active round or reopen a settled finding. The base template only lists overlapping examples—“bugs” are Critical while “poor error handling” and “missing features” are Important—and the addendum makes Important independently merge-blocking, leaving no distinct Critical threshold.
   - Sources: `loop-prompt-draft.md`, `requesting-code-review/code-reviewer.md`
   - Confidence: CONFIRMED — “Findings outside this diff are admissible only as Critical” (`loop-prompt-draft.md:36`), while the only base descriptions are “Critical (Must Fix) [Bugs, security issues, data loss risks, broken functionality]” and “Important (Should Fix) [Architecture problems, missing features, poor error handling, test gaps]” (`code-reviewer.md:87-91`).
   - Refutation: Checked the addendum, base template, requesting skill, and held-back additions for an impact, reachability, recoverability, or blast-radius boundary. None distinguishes Critical from an Important that already “would block the merge.”

2. **The addendum misclassifies traceable mechanisms with uncertain triggers as CONFIRMED**
   - A reviewer can trace a race-prone line but cannot establish whether production scheduling makes the race reachable. The addendum says traced findings are CONFIRMED and PLAUSIBLE is only for cases where tracing is infeasible; the source evidence ladder says exactly this case is PLAUSIBLE. Reviewers therefore receive contradictory confidence rules.
   - Sources: `loop-prompt-draft.md`, `code-review-analysis.md`
   - Confidence: CONFIRMED — “trace the finding in source wherever possible and mark it CONFIRMED. Only mark PLAUSIBLE … when tracing isn't feasible” (`loop-prompt-draft.md:20`) conflicts with “PLAUSIBLE — mechanism is real, trigger is uncertain (timing, env, config)” (`code-review-analysis.md:40-41`).
   - Refutation: Tried reading “trace the finding” as tracing the entire trigger-to-impact chain rather than locating the mechanism. The addendum never says that, and its “reasoned, not traced” parenthetical preserves the conflicting interpretation.

3. **“Would you block?” is a personal preference, not a reproducible severity test**
   - Missing retries in a payment path and in a disposable developer tool may have identical code shape but radically different severity. Unless deployment criticality, exposure, recovery, and risk tolerance happen to appear in the plan, reviewers cannot apply the boundary consistently; triage also cannot rebut a normative preference with “solid evidence.”
   - Sources: `loop-prompt-draft.md`, `requesting-code-review/code-reviewer.md`
   - Confidence: CONFIRMED — the sole boundary is “Important means you would block the merge over this finding alone” (`loop-prompt-draft.md:23`), while the base only says “Categorize issues by actual severity” (`code-reviewer.md:71`).
   - Refutation: Checked whether the shared scope block or template placeholders require operational context or a severity matrix. They pin scope, requirements, and conventions, but not likelihood, blast radius, recoverability, or release posture.

4. **The design exception legitimizes arbitrary hypothetical futures**
   - A reviewer can demand a plugin abstraction because a hypothetical future database migration would be harder without it, then mark that concern Important. Another reviewer can invent a different future change next round. The finding satisfies the literal contract even when the change is neither planned nor likely, feeding the exact non-convergence the loop is intended to prevent.
   - Sources: `loop-prompt-draft.md`, `receiving-code-review/SKILL.md`
   - Confidence: CONFIRMED — design findings need only “name a concrete future change the design makes harder” (`loop-prompt-draft.md:19`); no authority, probability, or disproportionate-cost requirement follows.
   - Refutation: Checked the receiving skill’s YAGNI guard and SETTLED machinery. Triage can reject each hypothetical after it is emitted, but neither mechanism prevents an unlimited sequence of novel hypotheticals from satisfying the reviewer contract.

5. **Confirmed absence findings have no valid evidence shape**
   - A reviewer exhaustively traces an authorization path and confirms that no guard exists. “Missing features” and “test gaps” are explicitly reviewable, but there is no truthful offending `file:line` or positive source quote. The reviewer must invent an anchor, weaken a confirmed omission to PLAUSIBLE, or drop it.
   - Sources: `requesting-code-review/code-reviewer.md`, `loop-prompt-draft.md`, `fable-method-notes.md`
   - Confidence: CONFIRMED — the base requires “File:line reference” for every issue (`code-reviewer.md:96-100`) while also naming “missing features” and “test gaps” (`code-reviewer.md:90-91`). The addendum equates CONFIRMED with source tracing (`loop-prompt-draft.md:20`).
   - Refutation: Checked for an `N/A`, nearest-anchor, section, exhaustive-search, or negative-evidence format. None exists. `fable-method-notes.md` recognizes the absence-detection difficulty but does not repair the reviewer output contract.

6. **The addendum drops the baseline’s concrete-cost path**
   - Three duplicated validation implementations may impose a present drift and maintenance cost without yet producing a wrong output or qualifying as architecture. The addendum orders the reviewer to drop it, even though the base asks about DRY and the analysis explicitly permits concrete cost as evidence.
   - Sources: `loop-prompt-draft.md`, `requesting-code-review/code-reviewer.md`, `code-review-analysis.md`
   - Confidence: CONFIRMED — “Neither => not an issue; drop it” follows only failure-scenario and design-future-change branches (`loop-prompt-draft.md:19`), whereas the baseline says cleanup findings state “concrete cost (duplication, waste, maintainability…) instead of a crash” (`code-review-analysis.md:51-55`).
   - Refutation: Considered treating every cleanup or convention concern as architecture. That evades the wording but replaces a measurable present cost with a speculative future change and conflicts with the base’s separate DRY/style categories.

7. **The absolute ban on call-sequence assertions rejects genuine interaction contracts**
   - For crash-safe persistence, “write data → fsync → rename” ordering is the observable safety contract. A focused test may need a fault-injecting fake or ordered-call assertion because executing real crashes is impractical. The addendum would classify that test as testing internal steps even though a plausible wrong ordering can lose data.
   - Sources: `loop-prompt-draft.md`, `requesting-code-review/code-reviewer.md`
   - Confidence: CONFIRMED — tests must assert boundary behavior, “not internal steps, call sequences” (`loop-prompt-draft.md:28`), while the base simultaneously asks whether integration and real behavior are tested (`code-reviewer.md:57-61`).
   - Refutation: Checked whether “boundary” could include a dependency protocol. The explicit prohibition on call sequences removes that interpretation and contains no exception for ordered external protocols.

8. **Recommendations provide an ungoverned escape from the evidence contract**
   - A reviewer unable to substantiate a refactor as an issue can place it under Recommendations without confidence, refutation, or failing scenario. If the orchestrator acts on it, the fix and resulting diff enter the loop without appearing in finding reconciliation or termination counts.
   - Sources: `requesting-code-review/code-reviewer.md`, `loop-prompt-draft.md`
   - Confidence: PLAUSIBLE — the base mandates a separate “Recommendations [Improvements for code quality, architecture, or process]” channel (`code-reviewer.md:102-103`), but the draft only defines triage and accounting for findings/backlog. The eventual orchestrator’s treatment of recommendations is not yet implemented, so the bypass outcome cannot be traced.
   - Refutation: Checked for instructions that Recommendations must satisfy the evidence contract, are informational only, or must never trigger fixes. None appears in the draft or base template.
