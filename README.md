# llm-skillbook

Four code-review / feature-delivery skills packaged for **Claude Code** and
**OpenAI Codex** from one layout.

| Skill | Does | Standalone? |
|---|---|---|
| [`feature-forge`](feature-forge/) | Spec → plan → reviewed acceptance for a bounded feature | No — needs `review-loop` + `superpowers:*` skills |
| [`multi-review`](multi-review/) | Fan out a review across many models, aggregate + synthesize | Code-backed (needs `uv`); Claude-oriented (see below) |
| [`review-loop`](review-loop/) | Converging multi-round adversarial review, mechanical green verdict | Code-backed (needs `uv`) |
| [`review-team`](review-team/) | High-confidence read-only multi-agent review | Yes (instruction-only) |

Each skill dir holds `SKILL.md` (+ `agents/openai.yaml` for Codex UI metadata,
`references/`, `assets/`, and a Python package where code-backed).

## Install

### In-repo — zero install
- **Codex:** run Codex in this repo; it auto-discovers the four skills via
  `.agents/skills/`. Invoke with `$feature-forge` (etc.).
- **Claude Code:** add the repo as a plugin marketplace, then install the plugin:
  ```
  /plugin marketplace add /home/mark/kramtime/llm-skillbook
  /plugin install llm-skillbook@llm-skillbook
  ```

### User-scoped — copy out of the repo
```
python3 install.py all --target both      # or a single skill; --target claude|codex
python3 install.py all --target both --dev # symlink instead of copy (edit-in-place)
```
Installs to `~/.claude/skills/` (+ subagents to `~/.claude/agents/`) and
`~/.agents/skills/`. Refuses to overwrite a directory it did not create
(`--force` to override).

## Prerequisites
- **`uv`** for `multi-review` and `review-loop` (their `scripts/py` launcher runs
  `uv run --project <skill> --locked`, so they work from any working directory).
- **`feature-forge`** is not standalone: it invokes `review-loop` and several
  `superpowers:*` skills — install those too, or it fails fast at dispatch.
- **`multi-review`** interactive orchestration uses Claude Code Task subagents; in
  Codex use its headless driver (`uv run <skill>/multi_review.py --prompt-file …`).
  Its `openai.yaml` disables implicit Codex invocation for that reason.
