material findings: 7

1. **The fix author controls the only convergence verdict**
   - A costly Important finding can be downgraded or refuted using selectively favorable context, allowing the agent to preserve its own fix and declare convergence. This contaminates factual verification, severity, `INTENTIONAL`, and the final green verdict.
   - **Countermeasure: (b)** Structural separation: independent read-only fact and rigor adjudicators must approve every green-making disposition (`REFUTED`, `DOWNGRADED`, `INTENTIONAL`) and final convergence against an immutable pre-fix snapshot.
   - **Sources:** `loop-prompt-draft.md`, `receiving-code-review/SKILL.md`, `zeroshot-notes.md`, `fable-method-notes.md`.
   - **Confidence: CONFIRMED.** The termination rule expressly says “reviewer confidence labels don't decide this — **your post-triage status does**.” `fable-method-notes.md` separately says “the author's claims are not evidence for a finding's disposition.”
   - **Refutation:** Checked whether `/receiving-code-review` or the held additions require independent adjudication. They require careful checking and reconciliation, but the decisive judgment remains with the implementing agent.

2. **The later-round finding policy is internally contradictory**
   - A round-2 fix can introduce a new Important regression. `zeroshot-notes.md` would forbid it as a new finding, while the draft’s inter-round diff review should admit it. Strict application misses regressions; loose application restores the endless stream of novel “Important” findings.
   - **Countermeasure: (a)** Every later-round finding must emit `PROVENANCE: INCOMPLETE-FIX <prior-id> | FIX-REGRESSION <diff-line> | CRITICAL-ESCAPE <trace>`. Reject any other provenance mechanically.
   - **Sources:** `loop-prompt-draft.md`, `zeroshot-notes.md`, `redteam-prompt-notes.md`.
   - **Confidence: CONFIRMED.** The draft says rounds ≥2 “review only the diff since the previous round”; `zeroshot-notes.md` says “Round 1 is the ONLY round that may introduce findings.”
   - **Refutation:** Checked whether the fix manifest resolves admission of newly introduced defects. It directs re-review of fixes but does not reconcile them with the finding-set ratchet.

3. **`SETTLED` conflates a valid finding with a verified repair**
   - An Important finding is accepted, then fixed incompletely. Round 2 receives it as `SETTLED` and is told not to re-litigate it below Critical, suppressing precisely the directed fix audit the next round needs.
   - **Countermeasure: (b)** Use typed, append-only states: `OPEN_ACCEPTED → FIX_CLAIMED → FIX_VERIFIED`; only `REFUTED` and `FIX_VERIFIED` enter `SETTLED`. Missing fix verification is absence-detection, so a state-machine gate—not prose—must prevent convergence.
   - **Sources:** `loop-prompt-draft.md`, `redteam-prompt-notes.md`.
   - **Confidence: CONFIRMED.** The draft says “SETTLED — already **accepted or refuted; do not re-litigate**,” while `redteam-prompt-notes.md` requires round N+1 to “audit whether each fix does what it claimed.”
   - **Refutation:** Considered whether “accepted” implicitly meant “accepted and successfully fixed.” The draft updates `SETTLED` each round and defines no repair-verification transition, so that interpretation is unsupported.

4. **Unverified findings have contradictory carry-forward semantics**
   - When an Important finding needs unavailable credentials or environment access, a pressured agent can invoke the single-round rule that unverified candidates are dropped, then report zero surviving blockers. The held addition says not to drop it but does not define a disposition or termination effect.
   - **Countermeasure: (a)** Require `DISPOSITION: NEEDS_EVIDENCE | UNVERIFIABLE`, the missing evidence, and the next action for every such finding; deterministic rollup must treat unresolved Important-or-above entries as non-green.
   - **Sources:** `loop-prompt-draft.md`, `code-review-analysis.md`, `zeroshot-notes.md`, `fable-method-notes.md`.
   - **Confidence: CONFIRMED.** `code-review-analysis.md` says a no-verdict candidate “is dropped”; the held addition says it “is not silently dropped or assumed resolved.”
   - **Refutation:** Checked whether “unverified-never-carries-forward” defines fail-closed behavior. Its body rejects silent dropping, but neither it nor the draft says where the finding goes or whether it blocks convergence.

5. **A shared scope block can make every reviewer consistently wrong**
   - The agent can choose a baseline after part of its fix, omit staged or untracked files, or narrow the endpoint. Every reviewer then receives the identical—but laundered—scope, and reconciliation still balances.
   - **Countermeasure: (b)** Seal workspace manifests before edits and after fixes, including committed, staged, unstaged, and untracked material; derive the round diff mechanically from those manifests and invalidate the round if the tree changes while reviewers run.
   - **Sources:** `loop-prompt-draft.md`, `requesting-code-review/SKILL.md`, `redteam-prompt-notes.md`.
   - **Confidence: CONFIRMED.** The held addition only says to “pin diff command / changed files” once; the red-team note only freezes the tree “during a round.”
   - **Refutation:** Checked the SHA instructions and frozen-tree assumption. Neither validates who selected the endpoints nor accounts for dirty and untracked material.

6. **Reviewer under-dispatch is invisible to the proposed statistics**
   - Under budget pressure, the agent can classify no area as sufficiently complex, run only the holistic and adversarial reviewers, and truthfully report “reviewers run: 2.” Nothing records the specialist reviewers that should have existed.
   - **Countermeasure: (b)** Build a pre-dispatch risk/surface inventory and immutable reviewer roster, then require `planned = completed`; a separate gap check must inspect omitted lenses because missing-reviewer detection is an absence task.
   - **Sources:** `loop-prompt-draft.md`, `zeroshot-notes.md`, `fable-method-notes.md`.
   - **Confidence: CONFIRMED.** The draft requires “one per area of high complexity or likely footguns,” but its held statistic records only “reviewers run.”
   - **Refutation:** Checked whether risk-sized loops or mandatory surface flags suffice. They improve selection, but no source reconciles the planned roster against completed, non-failed reviewer runs.

7. **`INTENTIONAL` is unauthenticated retroactive amnesty**
   - A fix introduces a side effect; after a reviewer flags it, the author declares the behavior deliberate and adds it to `INTENTIONAL`. Future reviewers are then discouraged from challenging a decision that did not exist before the defect was found.
   - **Countermeasure: (a)** Require `INTENTIONAL <id> AUTHORITY: <pre-existing user/spec quote>` at designation time. Without independent authority predating the finding, it remains open or is handed to the user for a decision.
   - **Sources:** `loop-prompt-draft.md`, `fable-method-notes.md`, `receiving-code-review/SKILL.md`.
   - **Confidence: CONFIRMED.** The draft permits “deliberate decisions surfaced in triage” to enter `INTENTIONAL`; `fable-method-notes.md` says task framing and author claims are not authority.
   - **Refutation:** Checked whether prior-human-decision handling supplies this control. `/receiving-code-review` protects existing human decisions, but the draft does not require an authority link or prevent after-the-fact author decisions.
