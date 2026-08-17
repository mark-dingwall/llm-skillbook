# multi-review-synthesizer smoke

Run this procedure from the repository root.

1. Run two CLIs against a small file (for example,
   `multi-review/multi_review/core/paths.py`):
   ```bash
   uv run --project multi-review python -m multi_review.cli.spawn --cli <cli> \
     --prompt-file <prepared prompt> --out-dir /tmp/synth-smoke/reviews
   ```
2. Build the synthesis input:
   ```bash
   uv run --project multi-review python -m multi_review.cli.build_synth_input \
     --state-dir /tmp/synth-smoke/reviews \
     --out-prompt-file /tmp/synth-smoke/synth-prompt.md \
     --out-nonce-file /tmp/synth-smoke/synth-nonce.txt
   ```
3. Dispatch via Task using `multi-review/templates/synthesizer_task.md`:
   `Task(subagent_type="multi-review-synthesizer", prompt=<filled template>)`.
4. Verify the output has Headline, Agreed Strengths, Agreed Concerns, and
   Divergent Views — and no `## Consensus Summary` heading (the host adds it).
