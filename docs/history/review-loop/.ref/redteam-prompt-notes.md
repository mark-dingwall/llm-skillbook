# liveness-redteam2.yaml — new ideas not already in the loop prompt

Source: `example-redteam-prompt.yaml` (copied from
`Pykrete/.multi-review/prompts/liveness-redteam2.yaml`), a second-pass
red-team prompt for a plan+spec review via multi-review.

Most of its machinery duplicates the current loop-prompt draft (severity
rubric with failing scenarios, CONFIRMED/PLAUSIBLE, refute-before-reporting,
do-not-pad, subject vs ground-truth file split, vacuous-test check). The
genuinely new, adoptable ideas:

1. **Fix manifest / directed re-review.** Rounds ≥2 currently hand reviewers
   a raw diff range. This prompt instead enumerates each applied fix with a
   per-fix verification task ("the `recovered` path retries the SAME
   candidate WITHOUT spending a resume attempt… check the backstop isn't
   off-by-one or bypassable"). Reframes round N+1 from "re-review the diff"
   to "audit whether each fix does what it claimed and what it might have
   broken" — the removed-behavior-auditor instinct applied to inter-round
   fixes. Nearly free to produce: triage already knows what each fix was
   for; emit the manifest alongside `{{ diff_range }}`.

2. **State-space enumeration directive.** For a designated complex area,
   don't just say "focus here" — order a cross-product trace ("every
   combination of {stopReason, sawAssistantOutput, idledOut, noncePresent,
   probe-result}") and state the expected branch order to check against.
   Optional add-on to the per-complex-area reviewer when the area is branchy
   logic.

3. **Concreteness bar for out-of-focus areas.** "Only raise these if you
   find something concrete" — a softer valve than the loop's out-of-diff
   rule (Critical + conclusive trace only). Keep the strict rule for the
   loop; this phrasing is a middle setting for round-1 sub-scoping if the
   strict rule ever feels too tight.

4. **Drift assumption made explicit.** multi-review has first-class drift
   handling (`if_drift`, a materiality classifier for subject changes
   mid-review). The loop assumes a frozen tree during a round — the skill
   should say so: don't edit while reviewers run; if you did, the round's
   diff scope is void.

5. **Open Questions as a first-class output section.** The evidence contract
   says drop-or-raise-as-open-question but gives it no home in the output
   format. Adding the section is a pressure valve: findings that fail the
   evidence bar get a legitimate channel instead of being padded into Minor.

Minor framing worth stealing:
- Verdict-first ordering (ship / ship-with-fixes / do-not-ship at the top,
  counts repeated in a closing Summary).
- "A finding you could not refute is stronger" — positive framing of the
  refutation clause.
