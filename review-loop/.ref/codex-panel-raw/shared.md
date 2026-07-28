You are one of five parallel reviewers examining the design sources for a planned Claude Code skill called "review-loop". Work strictly from your assigned angle (given at the end).

GOAL: The skill will orchestrate a multi-round code-review loop: dispatch several external reviewer agents against a subject -> verify and triage their findings against the actual sources -> apply fixes -> re-review scoped to the inter-round diff -> terminate when no blocking (Important-or-above) findings survive triage, capped at 5 rounds. Known hard problem this design exists to solve: earlier versions ran a dozen rounds without converging because fresh reviewers kept generating new "Important" findings.

SOURCES — read them; all under .ref/ in the current working directory:
- loop-prompt-draft.md — the current working prompt the skill will grow from, plus six held-back orchestration additions. The primary design artifact.
- code-review-analysis.md — 15 principles distilled from Claude Code's built-in /code-review (find/verify asymmetry, evidence bars for confirm AND refute, mechanism-angles, gap sweep, fail-closed verification). Raw companions if needed: code-review-prompts.md, code-review-workflow.js.
- requesting-code-review/ and receiving-code-review/ — the superpowers skills the loop invokes (SKILL.md in each; requesting- also has code-reviewer.md, the reviewer prompt template the draft's addendum extends).
- redteam-prompt-notes.md (+ example-redteam-prompt.yaml) — ideas from a hand-written second-pass red-team prompt: fix manifest for directed re-review, state-space enumeration directives, concreteness bar, frozen-tree assumption, Open Questions section.
- zeroshot-notes.md — 13 mechanisms from the zeroshot review pipeline: split verifier charters (fact vs rigor), DOWNGRADE over REJECT, NEEDS_EVIDENCE vs REJECT, monotonic finding-set ratchet, compile-only synthesizer, unresolved-at-cap==FAIL, fail-closed on verifier crash, pre-review quality gate, risk-sized loops, scoped specialist validators.
- fable-method-notes.md — 13 mechanisms + eval methodology from fable-method: forced verbatim artifacts at decision points (and the measured boundary: they fail for absence-detection), changed-test-guilty-until-spec-traced, authority order, judge-by-diff-and-execution, two-directional calibration guard, UNVERIFIABLE disposition, fix-diff fraud catalogue, twin check, hand-back payload on non-convergence, costume-rigor warning, trap-fixture testing methodology.

TASK: From your angle only, surface findings NOT already covered by the sources: gaps, contradictions between sources, failure modes, concrete design risks, or concrete improvements. Do NOT restate what a source already says — the sources are the baseline, not findings. When a finding builds on or contradicts a source, name the file.

OUTPUT (markdown, to stdout):
Line 1: verdict — "material findings: N" or "no material findings".
Then numbered findings, most important first, max 8. Each needs:
- **Title**
- The concrete failing scenario (specific situation -> wrong outcome) or, for an improvement, what it concretely buys.
- Source file(s) it touches.
- Confidence: CONFIRMED (traced in the source text — quote the line) or PLAUSIBLE (reasoned — say why you could not trace it).
- Refutation: you attempted to refute it first; state what you checked.
Do not pad. A short list of real findings beats a long list. "No material findings" is a valid and useful verdict.

YOUR ANGLE:
