# drift detection (mode: both, if_drift: ask)

Pass 2 normally fires in the same turn as pass 1, so drift can only occur on a
resumed pair. This procedure interrupts between passes to create that window.

1. Build a prompt with `mode: both`, `if_drift: ask`.
2. Run pass 1, then interrupt the session before pass 2 starts.
3. Verify `<cwd>/.multi-review/pending/<pair-id>/` holds `prompt-source.txt`, `prompt-source.sha256`, and a `files/` snapshot.
4. Edit one reviewed file (add a TODO comment).
5. `/multi-review --resume-pair <pair-id>`.
6. Verify AskUserQuestion offers proceed / abort / investigate.
7. Choose investigate. Verify `multi-review-investigate` is dispatched and returns a verdict.
8. Verify the follow-up AskUserQuestion offers proceed / accept-pass-1-as-final / restart. Choose proceed.
9. Verify pass 2 runs and the paired report records `drift_status: drifted`, `comparison_eligible: false` at pair level.
10. Repeat from step 1, but at step 4 edit the prompt YAML instead of a reviewed file. Verify the resume hard-stops on the hash mismatch — no AskUserQuestion, no pass 2.
