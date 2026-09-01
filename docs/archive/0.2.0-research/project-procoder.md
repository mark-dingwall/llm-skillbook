# Procoder investigation

## 1. Overview

- **What**: `~/tools/procoder` — a single Go binary + thin prompt layer that imposes an engineering process on AI coding agents (Claude, Copilot, Codex, Qoder). Not a linter wrapper: a chain of *refusing controllers* that judge "done" so the agent can't.
- **Thesis** (docs/quality-chain.md): "An AI coding agent is a confident narrator of its own progress... 'done' degrades into 'I stopped'." Fix: move the verdict out of the agent into a binary that refuses.
- **Positioning** (docs/influences.md): claims to replace superpowers + ponytail outright, and serena for indexed languages. Self-assessment; treat as positioning, not fact.
- **Size/maturity**: 34 command files (14–97 lines each), 10 quality domains, ~12-host portability layer, regression tests pinning its own past bugs. Docs show at least one shipped-bug postmortem (golangci one-issue-per-line hid funlen findings until v0.32.6) — actively dogfooded, though the dogfooding leg of this investigation returned nothing usable (see §6 caveat).

## 2. Core methodology

Chain: `idea → spec → [spec check] → plan → [plan check] → story/task → [close controller] → [gate] → merged → lessons → (feeds back into gate)`. Each bracket is a controller that can refuse.

| Stage | Controller refuses on |
|---|---|
| Spec (`procoder spec check`) | Missing/empty sections (In/Out of scope, Constraints, Interfaces, Data, Edge cases, Failure modes), unresolved `OPEN:` questions, untestable criteria |
| Plan (`procoder plan check`) | Placeholders ("TBD", "handle edge cases", "similar to Task N"), tasks with no files |
| Backlog | Epic seeded from spec records a **fingerprint of acceptance criteria** to flag later drift; closes cascade upward; `sprint open` refuses while last retro is empty |
| Close (`todo close` / story close) | Any unchecked criterion, no evidence, gate not clean; under `[test] policy="block"` suite must be green — "unverifiable and failing are the same answer" |
| Gate (`procoder check`) | Any blocking finding; **unchecked counts as failing**. Same collector backs local gate, `procoder git`, CI |
| Docs obligation | Public-surface change with no doc change refused unless `docs: none — <reason>` in commit |
| Lessons | Escaped finding must name the layer that missed it, adapt it same-PR, record it; `procoder lessons` exits 1 on unadapted entries ("recorded is not learned") |

Philosophy: **refusal, not advice** — "Advice gets rationalised under pressure... A named, blocking gap gets fixed because there is no other way forward." Documented cost: when the controller is wrong, fix what's named or edit `.procoder/` deliberately — "never soften the wording until the controller stops objecting."

## 3. Architecture & code-vs-LLM split

**Split rule: prose carries judgment, binary carries verification.**

| Layer | Content | Example |
|---|---|---|
| Go binary (`internal/`) | All mechanical checks: format, lint, secrets, section completeness, mirror drift, gate | `spec.checkOne` parses section *bodies*, not just headings |
| `commands/*.md` (34 files) | 3-line launcher boilerplate + judgment procedure. Length scales with judgment complexity (doctor.md 14 → merge.md 97), not command surface | tdd.md, debug.md, spec.md |
| `AGENTS.md` / `SKILL.md` | Contract stated once: "The binary computes; you act." Same body; SKILL.md adds frontmatter (normalize+stripFrontmatter makes them equal — not byte-identical files) | |
| `internal/principles/principles.go` | Full principles text injected at SessionStart; AGENTS.md carries the 12-line summary | |
| `.procoder/` (per repo) | Repo-owned overrides + committed Markdown state (lessons, answers, baseline) — human-reviewable, no opaque store | |

**Three contracts** (docs/architecture.md):
1. **P-CONTROL** — tools compute and hand over; nothing writes user code behind the agent's back. "An agent that gets silently overridden routes around its harness." Only exception: Procoder's own state files. Serena's symbol-*editing* tools explicitly refused on this line ("a rename you never saw is a change nobody reviewed"). `index rename` prints a diff, writes nothing.
2. **Unchecked is never clean** — missing/failed/timed-out tool = NOT checked, counted as failing. "If a Procoder report says clean, the check ran."
3. **D-OVERRIDE** — `.procoder/` files beat built-ins *wholesale* (no partial patching; principles.go:171). "Procoder imposes process, not opinions."

Hooks (`hooks/claude-hooks.json`): SessionStart → principles+status injection ("state AFTER principles — the last thing read is the thing acted on"); PostToolUse on Write|Edit → same-turn format/lint/secrets/doc-drift pass (sub-second target, 60s cap); PreToolUse on Bash → gate; Stop/PreCompact → `hook stop`. One binary, no daemon; multi-host JSON envelopes per `host.Detect()`.

## 4. Enforcement & verification

**Making the LLM comply:**
- Exit-code refusal at every chain stage; controllers accumulate *all* gaps, not first-fail (close.go:70-136).
- Three-valued verdicts everywhere: Clean / Unformatted / **Unchecked** (format.go:25-39); gate fails on `unformatted>0 || unchecked>0` (gate.go:106-113). Spec/plan use exit 0/1/**2** (unreadable ≠ gaps).
- Same-turn feedback: PostToolUse hook fires the same logic as the commit-time gate per edit — mistake surfaced at the moment it's made.
- One gate: hook, `procoder check`, `procoder git`, CI all call the same `Collect`. "A green local gate that fails CI is defined as a bug."
- Non-delegation rule repeated verbatim in AGENTS.md, SKILL.md, principles.go: judgment-only question → "STOP and put it to the user... an invented answer is indistinguishable from a decision."
- AI-attribution lines in commits *block* ("the work is the author's").

**Testing itself:**
- Regression tests pin past failures with the story at the fix site: `TestUncheckedFailsTheGateLikeUnformatted` (gate_test.go:56 — v1 printed findings and exited 0); spec.go:282 comment records two real specs with `- [O-1]` questions passing COMPLETE because only the `OPEN:` marker was checked.
- Checkers carry known-good/known-bad fixtures: "a checker that cannot catch its planted bad fixture is not trusted."
- Refusal-path tests, both-direction pins, mirror-drift tests.

## 5. Unique features & clever techniques

| Technique | Where |
|---|---|
| Unchecked-fails-gate, pinned by regression test | `internal/gate/gate.go:106-113`, `gate_test.go:56` |
| Section-*content* checks: "a heading is not an answer"; body parsed, comments stripped | `internal/spec/spec.go:259-340`, `internal/plan/plan.go:132-191` |
| Mirrors-and-drift: one master AGENTS.md, 12 byte-pinned host copies + 7 version-pinned manifests; drift blocks. Adoption gate: missing copies only nagged once ≥1 exists | `internal/portability/portability.go` |
| Forbidden-path check: `hooks/hooks.json` *existing* is the bug (Gemini auto-loads it incompatibly) | portability.go |
| Acceptance-criteria fingerprint on epic seed → detects spec drift after the fact | docs/quality-chain.md:85-87 |
| Backward-looking gate on forward action: next `sprint open` blocked by prior sprint's empty Retro | `internal/backlog/sprint.go:127-138` |
| Carry-needs-a-reason: `sprint carry` refuses without a why | sprint.go:208-248 |
| Test-design triad: name-the-break ("what production change fails this test — is it a bug?"), mirror-assertion ban, mental mutation check as pre-done gate | `commands/tdd.md:29-48` |
| Three-strikes-means-architecture: 3 failed fixes → stop, name the failing pattern, discuss refactor before fix #4; plus thrash red-flag list | `commands/debug.md:44-48` |
| One-way spec ratchet: spike→bounded→architectural can only escalate mid-task | `commands/spec.md:36-40` |
| Fail-towards-removal sanitiser: load-bearing step ordering (code blocks → secrets → paths → identities); unclosed fence = code-until-EOF + `incomplete` flag | `internal/copilot/sanitise.go` |
| Session-start injection: principles (constant) before status (today's); version check on a goroutine with timeout, stderr-only, silent on failure — "the one place where silence is right" | `internal/principles/principles.go:183-256` |
| `debt:` markers must name ceiling + revisit trigger; triggerless markers flagged as rot | `procoder debt` |
| UNLEARNED enforcement: lessons ledger entries without an adaptation exit 1 | `procoder lessons` |

## 6. Strengths & weaknesses

**Strengths**
- Closes the silent-skip hole completely — the single most load-bearing idea.
- P-CONTROL preserves agent trust and review-in-one-place; the refusal of serena's write tools shows the line is principled, not incidental.
- One gate, three firing points (edit-time hook, CLI, CI) — no local/CI divergence by definition.
- Prose stays thin because verification lives in code; command length tracks judgment, not features.
- Learns from its own escapes and pins them as tests with the story attached.

**Weaknesses**
- Heavy Go investment; several checks are Go-only (bench, licenses, complexity Go/Python only) — depth is uneven across the 10 domains.
- Refusal's cost is real and self-acknowledged: a wrong controller blocks work; escape hatch is editing `.procoder/`, which needs discipline.
- Doc drift observed even here: docs say 10 mirror hosts, code has 12; "33 commands" is now 34; "byte-identical" AGENTS/SKILL claim only true post-normalization.
- influences.md's "replaces all three" is unfalsifiable marketing tone.
- **Caveat**: the dogfooding explorer returned nothing; `.procoder/` self-use is unverified — docs claims about it stand uncorroborated.

## 7. Adaptable ideas

Raw candidates for another skill project:

1. Three-valued verdicts; unchecked = failing (`gate.go:106`).
2. Refusing controllers with exit codes instead of advisory prose.
3. Thin prose / thick binary split; prompt length scales with judgment.
4. Check section content, not markers — "a heading is not an answer" (`spec.go:259-340`).
5. One master file + byte-pinned mirrors; drift blocks the gate (`portability.go`).
6. Wholesale repo override of defaults (D-OVERRIDE, `principles.go:171`).
7. Same-turn PostToolUse feedback wired to the same collector as the commit gate.
8. Lessons ledger with UNLEARNED enforcement — adapt the layer that missed it, same PR.
9. Test-design triad: name-the-break, mirror-assertion ban, mutation check (`tdd.md:29-48`).
10. Pin past failures as regression tests with the story in a comment (`gate_test.go:56`, `spec.go:282`).
11. Three-strikes-means-architecture stop rule (`debug.md:44-48`).
12. One-way ceremony ratchet — complexity can upgrade mid-task, never downgrade (`spec.md:36-40`).
13. Backward-looking gates on forward actions (retro blocks next sprint open).
14. Acceptance-criteria fingerprints to detect post-hoc spec drift.
15. Fail-towards-removal ordering for redaction pipelines; unclosed-fence = strip-to-EOF (`sanitise.go`).
16. Adoption-gated nagging: report missing mirrors only after first adoption.
17. Session-start injection ordering: constants first, live state last.
18. Non-delegation rule duplicated verbatim wherever load-bearing ("an invented answer is indistinguishable from a decision").
19. Distinct exit code for "unreadable" vs "has gaps" (0/1/2).
20. Refuse work-hiding shortcuts: carries need reasons, AI-attribution lines block.
