# fable-method — review-relevant mechanisms worth adapting

Source: `~/tools/fable-method/` — a plugin of four skills (fable-method:
7-step think/act/verify loop; fable-loop: same loop with parallel evidence +
adversarial verifier subagents; fable-judge: adversarial verification of
"finished" work; fable-domain: adapter generation). Distinctive stance:
specify *what to do, in what order, with thresholds* so a weak model can
follow it literally; every rule is backed by an eval round (~15 rounds /
260 runs) where its absence produced a measured failure; nulls published.

Closest analog to our loop: `skills/fable-judge/SKILL.md`. Ready checklist:
`skills/fable-method/references/failure-modes.md` (18 modes). Methodology:
`eval/README.md`, `eval/RESULTS.md`, `eval/scenarios/*/GROUND-TRUTH.md`.

## Skill-content ideas

1. **Forced-artifact-at-the-decision-point + its boundary.** The empirical
   core: a rule stated as prose transferred ~0/4; the same rule as a
   mandatory verbatim output line (`INTENT: code does X / check expects Y /
   spec says Z`) went 4/4. Boundary (measured, s9): forced artifacts work
   when attached to an action in hand (annotate the edit/finding), and FAIL
   when they require noticing an absence (a `PENDING:` line for a follow-up
   not taken stayed 0/4). Design consequence: per-finding attestations
   should annotate the thing in hand (`TRACE: <file:line> observed <X>`);
   absence-detection (gap sweeps, "did they forget Y") is the class weak
   agents skip even when forced — assign it to a higher-effort verifier.

2. **Changed test = guilty until its justification traces to a spec.**
   (fable-judge step 4) Default disposition for fix diffs that touch tests
   (loosened assertion, changed expected value, skip, widened tolerance,
   real call → mock): presume fraud until traced to spec. The highest-value
   hunt in a re-review diff: "did they make the test agree with the bug?"

3. **Explicit authority order.** `explicit user statement > spec/README/
   docstring > tests > current code behavior`. Deterministic tie-break for
   "code and test disagree — which is the defect?"

4. **Task-framing is not authority.** "Fix the code so tests pass" does not
   promote tests above spec; the instruction that framed the work is not
   evidence the change is correct. Review analog: the PR description's /
   author's claims are not evidence for a finding's disposition.

5. **Judge by diff + execution, never by the report.** "A report is a set of
   claims, not evidence; nothing is believed that was not observed." Ground
   truth for triage = the diff and executed output; both the reviewer's
   finding text and the author's fix-claim are claims to prove or refute.

6. **Claims-table verdict + two-directional calibration guard.** Verdict on
   line 1, then (claim | what was observed) table, then frauds, then
   recommended action. Scale VERIFIED / VERIFIED-WITH-CAVEATS / REFUTED
   with a symmetric warning: "never soften a refutation to be polite, and
   never inflate a caveat into a refutation to look rigorous." Most prompts
   only guard one direction.

7. **UNVERIFIABLE as a first-class disposition.** A finding that can't be
   checked in this harness (credentials, env, human eyes) is labeled
   UNVERIFIABLE and never assumed true OR resolved — prevents "couldn't
   reproduce" defaulting to "not a bug". (Pairs with zeroshot's
   NEEDS_EVIDENCE ≠ REJECT.)

8. **Fraud catalogue to run against the FIX diff.** Named families, ordered
   by observed frequency: weakened checks; false completion ("should work
   now" over a broken transcript); scope creep (drive-by refactors,
   reformat, new deps — anything touched beyond the files the findings
   named); unauthorized outward action; spec betrayal; debris (scratch
   files, debug prints, orphaned imports). A re-review checklist aimed at
   *the fix*, complementing the inter-round diff scope ratchet. Debris and
   scope-creep are cheap objective checks.

9. **Distinct refutation lenses; weight effort toward refuters.** 1-3
   verifiers each told to REFUTE from a distinct lens: "prove the diff
   wrong/incomplete"; "find a runtime input that breaks it"; "find a
   spec/doc contradiction"; "diff the change set against declared scope and
   prove something outside it changed." When choosing where to spend
   reasoning effort, attackers get more than evidence-gatherers.

10. **Verifier is a gate, not a second implementation.** "Minutes, not
    hours; judging changes nothing (read and run only); if verification
    needs an environment you lack, hand that back rather than guessing."
    Stops triage ballooning into re-authoring and muddying loop state.

11. **Twin check, as finder angle AND fix-verification requirement.** After
    a defect is found/fixed, search the whole project for the same wrong
    construct; emit `TWINS: searched <pattern> — found <N> sites` (measured
    0/6 → 3/3 once forced). Re-review must confirm the author swept
    siblings, not just the cited line. The forced line names a re-runnable
    search, making a fabricated "all clear" convictable.

12. **Hand-back payload on non-convergence.** Terminating at the cap must
    deliver state, not a stop: surviving findings + fix attempts made + why
    they didn't resolve + current hypothesis. (Pairs with zeroshot's
    unresolved-at-cap == FAIL.)

13. **"Costume rigor" warning.** Verification theater — the shape of
    thoroughness with no search behind it — is *worst when a rule prompted
    "be rigorous"*. Countermeasure: every claim must name a re-runnable
    observation; an assertion that isn't one is treated as theater. Caution
    against "be thorough" phrasing in reviewer prompts.

## Eval methodology (for testing OUR skill — feeds the writing-skills RED phase)

14. **Trap fixture + hidden answer sheet.** Small single-decision fixtures
    where the plausible action is wrong; `GROUND-TRUTH.md` never shown to
    the agent under test (distinct filename because some fixtures' READMEs
    are themselves bait). For a review skill: bait a plausible-but-wrong
    finding or triage disposition, objectively detectable.

15. **Objective violation = a diff fact.** Every trap's failure is a
    gradeable artifact (marker file written, specific test value enshrined,
    wrong field unchanged) — never a rater's opinion.

16. **Scoring caps = disposition ladder with partial credit.** e.g. missed
    the bug → 0; found but mishandled disposition → 1; found + correct
    disposition → 2. Maps directly onto grading reviewer/triage behavior.

17. **Control-vs-treatment A/B on a deliberately mid-tier executor; publish
    nulls.** Capable models ceiling out; lift is only visible at weak tiers
    / at traps. Blind judge holds ground truth + trap definition, scores on
    fixed axes. "A results log that only contains wins would not be worth
    trusting."

18. **Fixture hygiene: don't pre-solve.** When the task prompt named the
    source files, every condition hit ceiling — naming the planted bug's
    location erases the measurement. Preserve evidence-discovery difficulty.

19. **Observation beats introspection.** Protocols drafted from
    introspection were corrected by traces of a strong agent actually doing
    the task; no rule ships without a failing test that demanded it.
    (Same covenant as superpowers:writing-skills.)

## Skipped as irrelevant

fable-domain's adapter-generation machinery; install/marketplace plumbing.
Two crumbs: per-domain fraud tables + minimum-evidence-sets (if reviewing
non-code artifacts); and the round-14 result that skill-in-skill
auto-discovery does not transfer to weak models (1/14) — don't design the
skill to rely on a reviewer auto-invoking sub-skills.
