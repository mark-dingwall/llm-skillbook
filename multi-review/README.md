# multi-review

multi-review collects parallel reviews from configured AI CLIs and assembles a
single report. Use it when an important change benefits from independent
perspectives, not as a substitute for accountable human review.

## Choose an entry point

Use `/multi-review` inside Claude Code for the interactive workflow. It can
help author a prompt file, dispatch Claude Code subagents, and coordinate the
review steps.

Use the headless driver when another tool or controller owns the workflow:

```bash
uv run --project multi-review multi-review/multi_review.py \
  --prompt-file path/to/review.yaml \
  --out-dir path/to/review-run
```

The driver performs one fan-out and report assembly pass. It is
*caller-contained*: it does not create a security boundary itself. A caller
that needs sandboxing, lifecycle control, or cleanup must provide those
properties around the command.

The interactive skill and headless driver have different report locations and
naming conventions. Read the result path reported by the entry point you ran
instead of assuming a shared filename.

## Install

From the repository root, install for Claude Code, Codex, or both:

```bash
python3 install.py multi-review --target both
```

Add `--dev` to link the skill directory for edit-in-place development. Claude
Code subagent definitions are still copied, so reinstall after changing a
canonical agent definition.

## Write a prompt file

The interactive workflow can create a prompt file. For headless use, start
with the smallest useful YAML:

```yaml
prompt_format_version: 2
task: code
files:
  - src/example.py
reviewers: [claude, codex]
synthesizer: none
```

Paths in `files` and `context_files` are resolved relative to the prompt file.
Omit `models` to use each CLI's default, or set a YAML model entry to pin a
headless/external route. That YAML does not override the Claude Code Task
subagents used by the interactive workflow; those use their agent definitions.

Known reviewers are not necessarily defaults. In particular, opt-in reviewers
must be named explicitly in the prompt rather than added to an automatic set.
Validate a prompt before spending review capacity:

```bash
uv run --project multi-review python -m multi_review.cli.validate_prompt \
  path/to/review.yaml
```

## Read results carefully

One failed or unavailable reviewer does not discard the reviews that completed:
the final report records both successful and failed slots. Synthesis is only
attempted when enough reviewer output is available, and a synthesis failure is
reported without hiding the underlying reviews.

A consensus summary is an interpretation of those reviewer outputs, not an
independent review or an extra vote. Do not double-weight it when deciding what
to investigate or fix.

## Safety boundary

Review prompts can direct tools toward code and context that may be untrusted.
Some configured reviewers are agentic and can execute commands or read beyond
the intended review subject. Do not run them against untrusted code without an
appropriate external containment boundary, and treat model output as
untrusted review input rather than instructions to follow automatically.

For the interactive procedure and maintainer invariants, see
[SKILL.md](SKILL.md) and [CLAUDE.md](CLAUDE.md). Historical design and smoke
evidence under `docs/` and `tests/manual/` are not a replacement for the
current entry-point contracts.
