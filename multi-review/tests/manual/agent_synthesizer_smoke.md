# multi-review-synthesizer smoke

1. Run two CLIs against a small file (e.g. `multi_review/core/paths.py`):
   ```bash
   uv run python -m multi_review.cli.spawn --cli <cli> \
     --prompt-file <prepared prompt> --out-dir /tmp/synth-smoke/reviews
   ```
2. Build the synthesis input:
   ```bash
   uv run python -m multi_review.cli.build_synth_input \
     --state-dir /tmp/synth-smoke/reviews \
     --out-prompt-file /tmp/synth-smoke/synth-prompt.md \
     --out-nonce-file /tmp/synth-smoke/synth-nonce.txt
   ```
3. Dispatch via Task using `skills/multi-review/templates/synthesizer_task.md`:
   `Task(subagent_type="multi-review-synthesizer", prompt=<filled template>)`.
4. Verify the output has Headline, Agreed Strengths, Agreed Concerns, Divergent Views, and a trailing `<filename>` suggestion — and no `## Consensus Summary` heading (the host adds it).
