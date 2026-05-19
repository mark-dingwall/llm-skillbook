# multi-review-reviewer smoke

1. From inside Claude Code TUI in this repo, dispatch via Task:
   ```
   Task(subagent_type="multi-review-reviewer", prompt=<contents of tests/fixtures/prompts/valid.yaml after running mr-prepare>)
   ```
2. Expect a structured response with `## Summary`, `## Critical`, `## Concerns`, `## Style / Maintainability`, `## Strengths` sections.
3. Verify the subagent did not call any write tools.
4. Verify file:line citations present.
