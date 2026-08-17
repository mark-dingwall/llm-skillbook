# Plan: unify 4 skills for dual-platform (Claude Code + Codex) install

## Goal
Every top-level skill dir installs cleanly into **both** Claude Code and OpenAI
Codex, from one unified layout, with a repo-that-is-also-a-plugin/marketplace
for CC plus a plain-copy fallback, and dev docs distributed into their owning
skill.

## Skills
`feature-forge` (model layout), `multi-review` (Python + CC agents),
`review-loop` (Python), `review-team` (nested under `skill/`).

## Unified layout (per skill dir, feature-forge shape)
```
<skill>/
  SKILL.md                 # required — both platforms (name + description)
  agents/openai.yaml       # recommended (repo policy) — Codex UI metadata; NOT required by Codex
  agents/*.md              # Claude subagents — only multi-review
  references/  assets/     # optional
  dispatch.md templates/   # skill-referenced runtime files (review-loop, multi-review) — MUST ship
  <python_pkg>/  pyproject.toml  uv.lock  scripts/  # code-backed — ship all (deps + lockfile + launcher)
  tests/  docs/  README.md  PLAN.md BACKLOG.md  __pycache__ .sdd-history evals/  # dev-only, excluded
```
**Payload = denylist, not allowlist** (fixes review F2): ship everything in the skill dir
EXCEPT the dev-only set above. Then run a validator: every path SKILL.md (transitively)
references must exist in the payload. Ship `pyproject.toml` **and `uv.lock`** → launcher uses
`--locked` for reproducible resolution (fixes review F1; keeps installed pkg from being rewritten).

## Phase 1 — Normalize layout
1. **review-team**: `git mv review-team/skill/* review-team/` ; remove empty `skill/`.
2. **multi-review**: `git mv multi-review/skills/multi-review/{SKILL.md,templates} multi-review/` ; remove `skills/`. Reconcile `templates/` vs `references/` naming (keep `templates/`, it's referenced by SKILL.md).
3. **multi-review**: add `agents/openai.yaml`.
4. **review-loop**: add `agents/openai.yaml`. (SKILL.md already top-level.)
5. **feature-forge**: already conformant — no move.

## Phase 2 — multi-review render quirk → build-time
6. Add `multi_review/cli/render_agents.py`: writes `agents/multi-review-reviewer.md`
   from template + `SUMMARY_HEADING_CONTRACT`. Commit the rendered output.
7. Add drift test: committed `.md` == freshly rendered. (single-source preserved)
8. Strip install-time substitution from `setup.py` (superseded by shared installer).

## Phase 2c — Fix Python invocation from foreign cwd (review F1 + follow-up)
Code-backed SKILL.md commands use bare `uv run python -m <pkg>...` — from a user's
target-repo cwd, uv resolves *their* project, not the skill, so the package/deps aren't found.
**Codex exposes no skill-root env var** → don't rely on one. Use a bundled launcher:
- Add `scripts/<skill>` launcher (multi-review, review-loop). It derives its own root:
  `root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"` — correct for copy, symlink, and plugin.
  Then forwards: `exec uv run --project "$root" --locked python "$@"`.
- Rewrite SKILL.md code lines from `uv run python -m X ...` → `"$skill_dir/scripts/<skill>" -m X ...`,
  where the agent substitutes `$skill_dir` = the absolute skill path it loaded SKILL.md from.
  `${CLAUDE_PLUGIN_ROOT}` is an optional Claude shortcut only, not the portable contract.
- Test each code-backed command from an unrelated working directory (copy AND symlink install).

## Phase 3 — Codex `agents/openai.yaml` for all four
9. Ensure each has `interface: {display_name, short_description, default_prompt: "Use $<name> ..."}`.
   feature-forge + review-team already have; add for multi-review, review-loop.
9b. **multi-review Codex scope (review F3):** openai.yaml makes it *discoverable*, not fully executable —
   its interactive path needs Claude Task/agents. Set multi-review's `default_prompt` to the **headless
   shell** entry (`uv run <SKILL_ROOT>/multi_review.py --prompt-file … --out-dir …`) and document in its
   SKILL.md/README that interactive orchestration is Claude-only. No Codex adapters built (per your steer).

## Codex distribution scope (review F5)
Codex support is **local install only**: repo-scoped `.agents/skills/` (Phase 4a) + user-scoped
`$HOME/.agents/skills/` (Phase 5). A Codex `.codex-plugin/` package for directory distribution is
**deferred** — the two local routes already satisfy "install as a skill." Note in root README.

## Phase 4a — Codex self-exposure (repo-scoped, committed)
Codex scans `$REPO_ROOT/.agents/skills/` and **follows symlinks**. Expose the
top-level skill dirs with committed symlinks (zero-copy, mirrors CC `skills:["."]`):
- `.agents/skills/feature-forge -> ../../feature-forge` (× all 4)
This makes anyone running Codex in-repo pick the skills up automatically.
(The pre-existing empty `.agents/` root dir is exactly this location — intended, not stale.)

## Phase 4 — Plugin + marketplace (CC)
10. `/.claude-plugin/plugin.json` (doc-confirmed: `skills:["."]` scans root for `<skill>/SKILL.md`,
    tolerates non-skill siblings; `agents` = explicit `.md` file paths, not dirs → openai.yaml ignored):
    ```json
    { "name": "llm-skillbook", "description": "...", "version": "0.1.0",
      "skills": ["."],
      "agents": ["./multi-review/agents/multi-review-build.md",
                 "./multi-review/agents/multi-review-reviewer.md",
                 "./multi-review/agents/multi-review-synthesizer.md"] }
    ```
11. `/.claude-plugin/marketplace.json`: one plugin, `source: "."`, `owner.name`.
12. Validate: `claude plugin validate --strict` + `/skill-doctor`.

## Phase 5 — Shared installer (copy fallback + Codex)
13. `/install.py` (repo-level), interface:
    `install.py <skill|all> --target claude|codex|both [--dev]`
    - copies **payload only** (excludes dev-only set above)
    - Claude: `<skill>/` → `~/.claude/skills/<name>/`; `agents/*.md` → `~/.claude/agents/`
    - Codex: `<skill>/` → `$HOME/.agents/skills/<name>/`  (NOT ~/.codex/skills — that's stale)
    - fail-closed if destination is a foreign (non-skillbook) dir (per review-team design)
    - `--dev` symlinks for local iteration
    - post-copy source/install equality check
14. Skills table drives it (name, has_python, has_cc_agents).

## Phase 6 — Docs distribution
Every root `docs/` file maps cleanly to feature-forge or review-loop (verified).
15. `docs/feature-forge/**` + `docs/superpowers/**/*feature-forge*` → `feature-forge/docs/`.
16. `docs/history/review-loop/**` → `review-loop/docs/history/`.
17. `docs/superpowers/**/*review-loop*` → `review-loop/docs/`.
18. Remove empty root `docs/`.
19. Fix repo-internal links (e.g. `review-loop/README.md:55` `../docs/history/...` → `docs/history/...`).
    **Do NOT** rewrite feature-forge's runtime output paths (`docs/superpowers/specs/...`,
    `docs/feature-forge/runs/...`) — those are template strings for the *target* repo, not links here.

## Phase 7 — Docs/READMEs
20. Add `feature-forge/README.md`, `review-team/README.md` (what it is + install both platforms).
21. Update `multi-review/README.md`, `review-loop/README.md` install sections for new layout + Codex.
21b. Fix stale `~/.codex/skills/...` paths in `review-team/docs/*` → `.agents/skills/` (repo) or `$HOME/.agents/skills/` (user).
21c. **Per-skill Prerequisites section (review F4):** each README states its deps + a fail-fast note.
    - feature-forge: requires `review-loop` + `superpowers:*` (brainstorming, writing-plans,
      subagent-driven-development, executing-plans, finishing-a-development-branch). NOT standalone.
    - multi-review, review-loop: `uv` + reviewer CLIs; code-backed.
    - review-team: closest to standalone (instruction-only, generic Task subagents).
    No auto-install of deps (YAGNI) — document + fail-fast only.
22. Add root `README.md`: index of 4 skills + install paths (CC plugin/marketplace + copy; Codex local).

## Phase 8 — Verify (review F7, F8)
23. Run each skill's existing test suite (multi-review, review-loop) — ensure moves didn't break imports/paths.
24. `claude plugin validate --strict` + `/skill-doctor` clean.
25. **Matrix, all four × {copy, symlink}, from an unrelated cwd** (temp `$HOME`):
    - Codex install path = `$HOME/.agents/skills/<name>` (NOT ~/.codex/skills).
    - assert: discovery (skill appears), explicit invocation resolves, every SKILL.md-referenced
      path exists, Python deps resolve, one harmless command per code-backed skill runs.

## Open risks / adjacent
- **Portability is per-skill, not "installs anywhere" (corrected per review F4):**
  - review-team — closest to standalone (instruction-only, generic subagents).
  - feature-forge — instruction-only BUT depends on review-loop + `superpowers:*` skills; not standalone.
  - multi-review, review-loop — code-backed; need `uv`+deps; best repo-scoped. Document deps + fail-fast.
- Plugin cache copies whole repo (tests/docs bloat) — functional, not fixing now.
- Empty root `.codex/` dir — purpose unclear (config.toml home? not needed for skills). Leave; ask user.
  `.agents/` is now used (Phase 4a).
- Codex user-scoped copy of a code-backed skill ships its Python pkg; confirm `uv` on target.
