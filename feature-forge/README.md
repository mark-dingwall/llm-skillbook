# feature-forge

Sole outer controller for delivering a bounded feature from specification
through planning, independent review, and acceptance — one canonical run,
advancing only the ledger's next permitted action.

- **Contract:** [`SKILL.md`](SKILL.md); owner references in [`references/`](references/).
- **Invoke:** Claude Code — the `feature-forge` skill; Codex — `$feature-forge`.

## Prerequisites (not standalone)
Depends on other installed skills: **`review-loop`** and `superpowers:*`
(`brainstorming`, `writing-plans`, `subagent-driven-development`,
`executing-plans`, `finishing-a-development-branch`). Install those too; without
them the run fails fast at dispatch. Instruction-only otherwise (no runtime deps).

## Install
See the [repo README](../README.md#install) — in-repo (Codex `.agents/skills/`,
Claude plugin) or `python3 ../install.py feature-forge --target both`.
