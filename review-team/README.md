# review-team

Read-only, high-confidence multi-agent code review: Scope → independent Finders
→ grouped Verifiers → optional Sweep → constrained Synthesis. Unverified
candidates never become findings; an empty result is complete and valuable.

- **Contract:** [`SKILL.md`](SKILL.md); details in [`references/`](references/).
- **Invoke:** Claude Code — the `review-team` skill; Codex — `$review-team`
  (e.g. "Use $review-team at high effort to review the current branch").
- Accepts effort `high` | `xhigh` | `max`.

Instruction-only — no runtime dependencies; the closest to standalone of the
four skills. [`evals/`](evals/) holds frozen RED/GREEN evidence and transcripts;
paths inside them are historical and intentionally not rewritten.

## Install
See the [repo README](../README.md#install) — in-repo (Codex `.agents/skills/`,
Claude plugin) or `python3 ../install.py review-team --target both`.
