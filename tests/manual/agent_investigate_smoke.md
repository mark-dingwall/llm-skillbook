# multi-review-investigate smoke

1. Run a paired-run pass 1 manually (mode: inline, then mock-edit a file under review).
2. Diff via `mr-snapshot diff`.
3. Dispatch: `Task(subagent_type="multi-review-investigate", prompt="<diff>\n<REVIEW.md content>")`.
4. Verify output has Verdict, Per-hunk classification, Recommendation, Rationale sections.
