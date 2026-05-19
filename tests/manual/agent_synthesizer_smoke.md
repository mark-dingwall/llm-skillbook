# multi-review-synthesizer smoke

1. Run `mr-spawn` against two CLIs in inline mode against `multi_review.py` (small file).
2. Build synth input via `build_synthesis_input` (REPL or short Python).
3. Dispatch via Task: `Task(subagent_type="multi-review-synthesizer", prompt=...)`.
4. Verify output has Consensus Summary, Agreed Strengths, Agreed Concerns, Divergent Views, filename suggestion in <filename> tags.
