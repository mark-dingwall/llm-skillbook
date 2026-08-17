# multi-review-reviewer smoke

1. Prepare a prompt from a fixture:
   ```bash
   uv run python -m multi_review.cli.prepare \
     --prompt-file tests/fixtures/prompts/valid.yaml --out-dir /tmp/reviewer-smoke
   ```
2. From inside the Claude Code TUI in this repo, dispatch via Task using
   `multi-review/templates/reviewer_task.md` with `<PROMPT_PATH>` set to the
   prepared prompt: `Task(subagent_type="multi-review-reviewer", prompt=<filled template>)`.
3. Expect a structured response with `## Summary`, `## Critical`, `## Concerns`, `## Style / Maintainability`, `## Strengths` sections.
4. Verify the subagent called no write tools.
5. Verify file:line citations are present.
