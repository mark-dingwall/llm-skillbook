material findings: 7

1. **Accepted is incorrectly treated as resolved**

   An Important missing-auth finding is accepted in round 1, but the fixer applies an incomplete patch. Round 2 receives the finding as `SETTLED`, cannot re-examine the original failure, finds nothing new, and terminates green. Accepted findings need an `OPEN → FIX_ATTEMPTED → FIX_VERIFIED` lifecycle; only the last state is settled.

   Sources: `loop-prompt-draft.md`, `redteam-prompt-notes.md`.

   Confidence: CONFIRMED — `loop-prompt-draft.md:37` says, “SETTLED — already accepted or refuted; do not re-litigate,” and line 46 again places accepted findings in `SETTLED`. This directly conflicts with the directed fix audit in `redteam-prompt-notes.md:12-20`.

   Refutation: I checked whether the fix manifest implicitly reopens accepted findings. It directs reviewers to audit fixes but does not override the explicit prohibition on re-litigating accepted findings.

2. **Later-round admissibility must be causal, not location-based or “no new findings”**

   A fix changes a callee’s return contract; an unchanged caller now mishandles it. The resulting Important defect is located outside the diff, so the draft backlogs it. Zeroshot’s proposed “no new findings after round 1” would suppress it entirely. The coherent rule is: later rounds may admit findings that are unresolved descendants of earlier findings or causally introduced/exposed by the fix diff, even when the cited failure line is unchanged. Only unrelated pre-existing defects go to backlog.

   Sources: `loop-prompt-draft.md`, `zeroshot-notes.md`, `code-review-analysis.md`, `code-review-prompts.md`.

   Confidence: CONFIRMED — `loop-prompt-draft.md:36` restricts non-Critical findings outside the diff, while `zeroshot-notes.md:43-47` freezes the finding set. Yet `code-review-prompts.md:90-93` explicitly requires checking unchanged callers for new preconditions, return shapes, exceptions, and ordering dependencies.

   Refutation: I checked whether enclosing-function scope or the Critical exception covered this. Neither admits an Important regression located in an unchanged caller.

3. **The ledger cannot represent unresolved findings or execute round-5 failure semantics**

   A production-only race cannot be verified locally. The design says it cannot be dropped, but reconciliation has no `NEEDS_EVIDENCE`, `UNVERIFIABLE`, or `OPEN` bucket. It must therefore be misclassified, backlogged into a non-blocking channel, or leave reconciliation impossible. Likewise, if round 5 finds an Important defect and applies a fix, no sixth review exists to verify it. Termination must roll up the entire open ledger—not merely the current round’s yield—and round 5 must end FAIL with a hand-back unless every blocker was already verified closed.

   Sources: `loop-prompt-draft.md`, `zeroshot-notes.md`, `fable-method-notes.md`.

   Confidence: CONFIRMED — `loop-prompt-draft.md:56-59` says an unverified finding is not dropped, but defines `surfaced = accepted + refuted + backlogged`. Meanwhile `zeroshot-notes.md:55-61` requires unresolved-at-cap to fail, and `fable-method-notes.md:89-92` requires a non-convergence hand-back. The executable draft only says “Cap 5.”

   Refutation: I checked whether “unverified never carries forward” meant triage must retry until a verdict exists. No retry or unavailable-evidence terminal rule is specified, and `UNVERIFIABLE` cases may be inherently undecidable in the harness.

4. **The fixer/triager can self-authorize termination through downgrade or `INTENTIONAL`**

   A fixer weakens a test, then characterizes the lost behavior as intentional or downgrades the resulting defect to Minor. Because “your post-triage status” controls termination, the same orchestration process can erase the blocker. Require an auditable, independently checked rigor verdict for every disposition crossing the Important boundary; `INTENTIONAL` must cite controlling authority or explicit human risk acceptance, not the author’s claim.

   Sources: `loop-prompt-draft.md`, `zeroshot-notes.md`, `fable-method-notes.md`, `receiving-code-review/SKILL.md`.

   Confidence: PLAUSIBLE — the draft does not explicitly identify whether fixer and triager are separate actors, so self-dealing cannot be conclusively traced. It does, however, give post-triage status sole termination authority without an independent veto.

   Refutation: I checked the “solid evidence” requirement and `/receiving-code-review` skepticism. They encourage rigor but do not require recorded evidence, authority tracing, or independent review of a downgrade.

5. **Semantic recurrence can be suppressed as settled relitigation**

   Round 1 fixes boundary failure A by changing `>=` to `>`. Round 2 discovers failure B and “fixes” it by restoring `>=`, resurrecting A. Because A is already settled and only a conclusively Critical finding may reopen it, an Important regression can be suppressed. Previously observed failure scenarios must reactivate when they become reachable again. Repeated A→B→A transitions should trigger an early non-convergence hand-back rather than consume rounds or appear green.

   Sources: `loop-prompt-draft.md`, `redteam-prompt-notes.md`.

   Confidence: PLAUSIBLE — this state transition is permitted by the written rules, but there is no implementation yet in which to reproduce it.

   Refutation: I checked the Critical reopening exception and fix manifest. The exception excludes Important recurrence; the manifest audits the latest fix but defines no semantic cycle detection or reactivation rule.

6. **The reviewed snapshot is not proven to equal the final subject**

   A fixer adds an untracked source file, or edits the tree after reviewers finish but before the final report. SHA-based ranges omit the untracked file, while the frozen-tree rule only invalidates drift during a round. The loop can therefore declare green over a state different from what will ship. Each round needs immutable before/after subject snapshots that include tracked, untracked, and non-Git material, plus a final equality check against the last reviewed snapshot.

   Sources: `requesting-code-review/code-reviewer.md`, `code-review-prompts.md`, `redteam-prompt-notes.md`, `loop-prompt-draft.md`.

   Confidence: PLAUSIBLE — snapshot construction is not yet specified, so the exact evasion depends on implementation. The supplied template uses only `BASE_SHA..HEAD_SHA`; the working-tree fallback covers tracked changes but not untracked files.

   Refutation: I checked both the working-tree fallback and frozen-tree assumption. Neither binds the post-review final tree to the reviewed state or inventories untracked files.

7. **The backlog is an unbounded reviewer-controlled denial-of-service channel**

   A reviewer emits hundreds of out-of-diff Minor candidates. If triage verifies them, review cost explodes; if it does not, unverified claims enter the required full final report. Either path can exhaust context or obscure the real blockers without increasing the round count. Give each reviewer and the aggregate backlog fixed candidate caps, require ranking and stable IDs, and place overflow in a durable appendix rather than the live loop context.

   Sources: `loop-prompt-draft.md`, `code-review-analysis.md`.

   Confidence: PLAUSIBLE — the resulting resource exhaustion depends on runtime limits, but the draft supplies no backlog bound and requires that the final report include it “in full.”

   Refutation: I checked the anti-padding instruction and the caps described in `code-review-analysis.md:77-79`. Those caps are not adopted into the draft and do not explicitly govern backlog candidates.
