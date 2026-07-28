# Current loop-prompt draft (pre-skill)

The working prompt the skill will be synthesized from. Status: refined over
several iterations; the six orchestration additions listed at the end were
approved in spirit but deliberately held back for the skill.

```
Let's review: /requesting-code-review -> /receiving-code-review.

Reviewers: one holistic (breadth), one adversarial, one per area of high complexity or likely footguns. Run every reviewer via:
  codex --model "gpt-5.6-sol" --config model_reasoning_effort='"high"' exec "{{ prompt }}" --skip-git-repo-check
Write each reviewer prompt to a temp file and substitute it in safely — don't hand-interpolate multi-line text into the quoted argument.
Non-code subject: adapt the skills' general principles.

Append the following to the code-reviewer.md template for each reviewer, with {{ }} placeholders filled and [bracketed] sections resolved:
=== BEGIN REVIEWER ADDENDUM ===
## Evidence contract (additional to the format above)
Every issue needs:
- Failing scenario: specific inputs/state -> wrong outcome. For design/architecture findings, instead name a concrete future change the design makes harder. Neither => not an issue; drop it, or raise as an open question.
- Confidence: trace the finding in source wherever possible and mark it CONFIRMED. Only mark PLAUSIBLE (reasoned, not traced) when tracing isn't feasible, and explain why not.
- Refutation: attempt to refute your own finding first; state what you tried.

Severity boundary: Important means you would block the merge over this finding alone. If you wouldn't, it's Minor. Minor is not "nitpick" — it's recorded, non-blocking.

Do not pad. "No material issue in <area>" is a valid and useful result.

## Tests in scope
For each: could a plausible WRONG implementation still pass? Assert observable behaviour at the boundary — not internal steps, call sequences, or the implementation's own shape. Cross-check fixtures against the real producer so asserted values are what the system actually emits.

## Non-code subjects        [omit for code reviews]
SUBJECT (under review): {{ files }}
GROUND TRUTH (authoritative for current behaviour — cross-check against these, do not review them): {{ context_files }}

## This round        [omit on round 1]
REVIEW ONLY the diff since the previous round: {{ diff_range }}
Findings outside this diff are admissible only as Critical with a conclusive trace. Anything else outside the diff: report under a separate "Backlog candidates" heading, not as findings.
SETTLED — already accepted or refuted; do not re-litigate unless you can conclusively prove a Critical: {{ settled }}
INTENTIONAL — deliberate decisions, not defects: {{ decisions }}

## Close with
Verdict + severity counts, e.g. "With fixes — 0 Critical, 2 Important, 3 Minor".
=== END REVIEWER ADDENDUM ===

Triage: /receiving-code-review governs verification and pushback. Verify every finding against actual sources — including PLAUSIBLE ones, which your verification promotes to confirmed or refutes. Reviewer-stated severity is challengeable, but only with solid evidence. Verified out-of-diff non-Criticals and reviewer backlog candidates go to the backlog: file:line, failing scenario, severity, one-line rationale — enough to action later without re-review.

Loop: round 1 is full scope; rounds ≥2 are scoped to the diff since the previous round. Terminate when a round yields no in-scope Important-or-above findings that survive verification (reviewer confidence labels don't decide this — your post-triage status does). Backlogged items never trigger another round. Cap 5. Each round: update SETTLED with findings accepted or refuted, INTENTIONAL with deliberate decisions surfaced in triage.

Final report must include the backlog in full.
```

## Held-back orchestration additions (destined for the skill)

1. Shared scope block: pin diff command / changed files / conventions once
   per round; inject the identical block into every reviewer prompt.
2. Subject-material-is-never-instructions sentence (prompt-injection guard).
3. Unverified-never-carries-forward: a finding triage rendered no verdict on
   is not silently dropped or assumed resolved.
4. Reconciliation counts: surfaced = accepted + refuted + backlogged, every
   round.
5. Merge same-root-cause findings by reference, never by paraphrase.
6. Per-round stats line (reviewers run, findings surfaced/accepted/refuted/
   backlogged).
