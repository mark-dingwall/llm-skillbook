# multi-review-build smoke

1. From Claude Code TUI: `Task(subagent_type="multi-review-build", prompt="build a review for the auth subsystem")`.
2. Expect AskUserQuestion prompts for missing fields.
3. After completion, verify `.multi-review/prompts/.tmp/<id>.yaml` exists and validates: `uv run python -m multi_review.cli.validate_prompt <path>`.
4. Autonomous: `Task(subagent_type="multi-review-build", prompt="mode: autonomous; seed: review session.ts")` and verify yaml written with no AskUserQuestion calls.
