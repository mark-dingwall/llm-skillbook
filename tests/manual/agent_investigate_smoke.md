# multi-review-investigate smoke

1. Run a paired-run pass 1 manually (mode: inline, then mock-edit a file under review).
2. Diff via `uv run python -m multi_review.cli.snapshot diff --snapshot-dir <pending/<pair-id>/files> --file <each reviewed file>`.
3. Dispatch: `Task(subagent_type="multi-review-investigate", prompt="<diff>\n<REVIEW.md content>")`.
4. Verify output has Verdict, Per-hunk classification, Recommendation, Rationale sections.
