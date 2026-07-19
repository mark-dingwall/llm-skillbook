# drift detection (mode: both, if_drift: ask, background)

1. Build prompt with mode: both, delay: 60, delay_type: background, if_drift: ask.
2. Run pass 1.
3. Verify `<cwd>/.multi-review/pending/<pair-id>/prompt-source.txt` and `prompt-source.sha256` both exist.
4. While background timer running, edit one reviewed file (add a TODO comment).
5. `/multi-review --resume-pair <pair-id>`.
6. Verify AskUserQuestion appears with proceed/abort/investigate.
7. Choose investigate. Verify `multi-review-investigate` subagent dispatched and returns verdict.
8. AskUserQuestion proceed/accept-pass-1-as-final/restart appears. Choose proceed.
9. Pass 2 runs. Paired report shows drift_status: drifted, comparison_eligible: false at pair level.
10. Separately: repeat from step 1, but instead of step 4, edit the prompt YAML itself before `--resume-pair`. Verify resume hard-stops citing a hash mismatch — no AskUserQuestion, no pass 2.
