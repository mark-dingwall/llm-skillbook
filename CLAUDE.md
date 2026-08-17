# Repository maintainer contract

## Authority and documentation

This file owns repository-wide maintenance rules. The nearest top-level
`CLAUDE.md` owns component-specific authority, safety, workflow, and
verification rules; read it before changing that scope. Do not copy component
invariants into this file. A component's live `SKILL.md`, owner references,
runtime code, manifests, and tests retain the authority assigned by that
component contract.

`README.md` files are short human entry points: they identify purpose, the
operating boundary, and a useful next action. `CLAUDE.md` files are
harness-neutral maintainer contracts. Every repository root or tracked
top-level scope exposes that same contract through an `AGENTS.md` relative
symlink whose literal target is `CLAUDE.md`.

Plans, designs, reviews, evaluations, transcripts, and other dated records may
be valuable evidence, but they do not prove current runtime or installation
behavior. Follow the authority policy in [the planning-record contract](docs/CLAUDE.md)
and validate operational claims against live sources and fresh verification.
Do not add directory trees, source inventories, line references, commit IDs,
dated tool observations, or historical test totals to maintainer entry points.

## Canonical sources, discovery, and mirrors

The top-level skill directories are canonical. Repository-local discovery
links are zero-copy aliases into those roots; edit the canonical skill, not a
discovery alias. A skill move or rename must keep its canonical location,
discovery link, installer selection, and plugin references synchronized.
Follow [the discovery contract](.agents/CLAUDE.md) for those changes.

Plugin-root agent definitions are a deliberate exception to the symlink
policy. They are real-file mirrors of canonical definitions owned by their
component and must remain byte-identical; never replace them with symlinks.
Follow [the agent-mirror contract](agents/CLAUDE.md) before changing or copying
an agent.

Repository and component `README.md`, `CLAUDE.md`, and `AGENTS.md` files are
maintainer guidance. Keep those filenames out of copied skill payloads, and do
not make installed operation depend on repository-only documentation or tests.

## Plugin and installer synchronization

Interpret plugin manifest roots from the repository checkout and keep plugin
names aligned across the marketplace and plugin metadata. Strict metadata
validation does not prove agent registration; pair it with the mirror checks
required by [the plugin metadata contract](.claude-plugin/CLAUDE.md).

Keep skill-directory destinations fail-closed. A normal install may update a
skill destination created by this installer, but replacing a foreign skill
destination requires explicit force authority. Claude agent definitions are
copied separately by name and do not have that ownership guard; inspect the
resolved agent destinations and obtain overwrite authority before installing.
Development installs link skill directories but still copy Claude agents, so
canonical agent changes require mirror verification and reinstallation.
Verify repository sources before updating any user-scoped installation.

## Git safety

Resolve the repository root and inspect current status before writing. Preserve
unrelated work: do not modify, stage, stash, reset, discard, amend, or combine
changes outside the requested scope. Stage and commit only explicit paths;
never use blanket additions such as `git add .` or `git add -A`. Recheck the
explicit diff and symlink metadata before any commit.

## Verification routing

Run checks from the repository root and use the narrowest owning gate while
iterating:

- Documentation entry points, exact `AGENTS.md` links, and local Markdown links:
  `python3 -m pytest tests/test_documentation.py -q`.
- Installer safety and copied-payload boundaries: `python3 -m pytest
  tests/test_install.py -q`.
- Plugin agent identity and regular-file requirements: `python3 -m pytest
  tests/test_plugin_agents.py -q`.
- Plugin metadata: `claude plugin validate . --strict`, paired with the plugin
  agent checks when agent layout or registration may be affected.
- Component behavior: use the focused and full commands in that component's
  `CLAUDE.md`; root packaging tests do not establish component correctness.

For a cross-cutting handoff, run the affected component suites, the root suite
with `python3 -m pytest tests -q`, plugin validation when applicable,
`git diff --check`, and an explicit status review. Interpret each failure at
the owning boundary rather than treating one green suite as evidence for
another.
