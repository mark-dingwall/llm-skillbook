# multi-review maintainer contract

## Execution ownership

`SKILL.md` owns the interactive Claude Code procedure. The headless driver
owns one programmatic fan-out, synthesis, and report assembly pass; its caller
owns containment, scheduling, and any wider run lifecycle. Do not describe the
driver itself as a sandbox or use it to imply containment it does not provide.

Keep the two paths distinct. Claude Code Task subagents are driven by their
agent definitions. YAML model selections govern headless and external CLI
routes; they must not be documented as overrides for interactive Task agents.
Likewise, do not promise that the two entry points publish identically named
artifacts.

## Reviewer and prompt authority

The validated prompt is the sole authority for the reviewer set, synthesizer,
and model choices used for a run. The known-reviewer set is a valid-choice set,
not an automatic run set. Preserve opt-in reviewers outside every default and
ensure the interactive builder uses the same default policy as the runtime.

Treat prompts, listed source files, inline context, reviewer output, and
synthesis input as untrusted data. Preserve the prompt-delivery boundary: do
not move prompt text onto process command lines; retain the safe file-delivery
exception only where a client requires it. The synthesis helper cleans up the
temporary file it creates; prepared run prompt files belong to the caller or
run owner, which must govern their retention and cleanup. Keep input-tagging
and reference-read instructions intact so content cannot silently become
authority over the review procedure.

Progress adapters normalize each supported stream into the common result
shape. JSONL is a per-client capability, not a universal transport: do not
force it on plain-text clients or assume an external stream event schema is
stable.

## Results and synthesis

Use the shared result and summary classification rules wherever results are
persisted or aggregated. A failed, malformed, or structurally incomplete
review must remain visible as a failed slot; it must not be silently promoted
because other reviewers succeeded.

Synthesis is derived from reviewer output and is never another independent
vote. It has its own eligibility and failure handling, and must not hide raw
reviewer results. Both synthesis routes must carry the same instruction to
ignore agent step narration and treat review bodies as data, because the
interactive Task route and external CLI route receive different prompts.

The headless driver publishes its final report atomically: fully write and
validate the staged artifact before replacing the visible report. Cancellation,
integrity failure, or report-write failure must not leave a partial headless
report presented as complete. Do not extend this guarantee to the interactive
aggregator without first making its publication path satisfy it.

## Agents, installation, and verification

The canonical subagent definitions live with this component. Their plugin-root
counterparts are deliberately real files, not symlinks, and must remain
byte-identical. Verify that mirror contract before installing changed agents.

Run focused automated checks and any affected manual smoke procedure before
claiming a change is ready. Then reinstall the Claude target when a canonical
agent changed: `--dev` links the skill directory but still copies subagent
files, so it does not update an already installed agent definition.

Keep manual procedures only for interactions that cannot be made executable in
the component tests. Preserve paid-network and historical-observation labels
where they describe the evidentiary limits of a smoke procedure; do not turn
historical observations into current runtime guarantees.

See [SKILL.md](SKILL.md) for the live interactive procedure and [README.md](README.md)
for operator-facing guidance.
