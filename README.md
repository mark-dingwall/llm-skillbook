# llm-skillbook

llm-skillbook packages code-review, feature-delivery, and team-orchestration
workflows for Claude Code and OpenAI Codex. Choose the smallest workflow that matches the job:

| Workflow | Use it for |
|---|---|
| [feature-forge](feature-forge/README.md) | Carrying a bounded, nontrivial Git work unit from specification through reviewed acceptance |
| [multi-review](multi-review/README.md) | Collecting parallel reviews from configured AI tools and assembling one report |
| [review-loop](review-loop/README.md) | Running a fail-closed, ledger-backed review process through an external host/controller |
| [review-team](review-team/README.md) | Getting a high-confidence, read-only review from independent workers |
| [work-team](work-team/README.md) | Delivering a task through a planned, audited team of fresh subagents with a verifiable result |

Each component README explains its operating boundary and the useful next
action. Start there before invoking a workflow.

## Install

### Use this checkout

Codex discovers the skills when it is running in this repository. Open the
checkout in Codex and invoke the workflow by name, for example
`$review-team`.

For Claude Code, add this checkout as a local plugin marketplace, then install
the plugin. Replace the example path with this repository's absolute path:

```text
/plugin marketplace add /absolute/path/to/llm-skillbook
/plugin install llm-skillbook@llm-skillbook
```

Then open the chosen component README and invoke its named workflow; for
example, use `/multi-review` for the interactive multi-review flow.

### Install user-scoped copies

Python can install one workflow or all workflows for Claude Code, Codex, or
both:

```bash
python3 install.py all --target both
python3 install.py review-team --target codex
```

Add `--dev` to link the workflow directory back to this checkout for
edit-in-place development. Skill-directory installs refuse to replace a
destination the installer did not create unless you pass `--force`. Claude
installs also copy agent files by name, and those individual files do not have
that ownership guard; inspect same-named files in the destination before
installing. Installing `work-team` for Claude also adds its exact-agent return
capture hook to `~/.claude/settings.json`; unrelated settings and hooks are
preserved, and a malformed or conflicting hook configuration is rejected
without installing the skill.

## Prerequisites and safety

- `multi-review` and `review-loop` require `uv`. Their component READMEs
  describe the supported entry points and current host/controller boundaries.
- Feature Forge also needs Git isolation, `review-loop`, a configured reviewer
  runner, and its participating Superpowers skills.
- Review tools may send source and prompts to external AI providers. Some
  configured reviewers can execute commands or read beyond the nominated
  files. Treat reviewed content and model output as untrusted, and provide
  external containment when the component's safety boundary requires it.
- Installation changes user-scoped tool directories. Prefer the in-repository
  mode while evaluating the workflows. Resolve skill-directory and Claude
  agent-file collisions before installing, and use `--force` only for a skill
  destination you intentionally want to replace.
