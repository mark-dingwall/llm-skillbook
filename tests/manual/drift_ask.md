# drift detection (mode: both, if_drift: ask, background)

1. Build prompt with mode: both, delay: 60, delay_type: background, if_drift: ask.
2. Run pass 1.
3. While background timer running, edit one reviewed file (add a TODO comment).
4. `/multi-review --resume-pair <pair-id>`.
5. Verify AskUserQuestion appears with proceed/abort/investigate.
6. Choose investigate. Verify `multi-review-investigate` subagent dispatched and returns verdict.
7. AskUserQuestion proceed/accept-pass-1-as-final/restart appears. Choose proceed.
8. Pass 2 runs. Paired report shows drift_status: drifted, comparison_eligible: false at pair level.
