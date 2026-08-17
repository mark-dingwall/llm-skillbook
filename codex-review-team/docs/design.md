# Codex Review Team Repository Design

**Date:** 2026-08-10
**Status:** Approved

## Purpose

Develop and maintain the `review-team` skill, portable to Codex and Claude
Code, inside the existing `llm-skillbook` Git repository. The repository is
the durable source for the skill package, design and implementation
documents, evaluation evidence, and change history. Codex's personal skills
directory contains only an installed copy used at runtime.

The component's behavioral design is the authority for review-team behavior.
This repository design changes ownership and deployment mechanics only. It does not reopen the
workflow topology, effort budgets, role boundaries, verification rules, failure
policy, or report contract.

## Root Terminology

Use these terms consistently:

- **Repository root:** the existing `llm-skillbook` Git checkout. It owns the
  single `.git` directory, branches, worktrees, and commits.
- **Component root:** the `codex-review-team` directory within that repository.
  It contains everything maintained for this skill.
- **Package root:** the component's `skill` directory. It contains only files
  that form the installable Codex skill.
- **Installed root:** the `review-team` directory in Codex's personal skills
  directory. It is derived from the package root and is never edited directly.

The component is not a nested Git repository. All Git operations apply to the
repository as a whole, even when a commit touches only this component.

## Component Layout

```text
codex-review-team/
├── skill/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   └── references/
│       ├── finder-angles.md
│       ├── verifier.md
│       └── report-contract.md
├── docs/
│   ├── design.md
│   └── implementation-plan.md
└── evals/
    ├── scenarios.md
    ├── baseline-results.md
    ├── green-results.md
    ├── refactor-results.md
    └── checksum evidence
```

The package root stays limited to the five runtime files required by the frozen
design. Project documentation and evaluation artifacts live beside the package,
not inside it.

## Source and Installation Flow

The package root is the sole writable source of truth:

1. Author or refine package files in the repository.
2. Run structural validation against the package root.
3. Commit a coherent repository state.
4. Explicitly install the package into Codex's personal skills directory.
5. Compare the installed tree recursively with the committed package.
6. Run behavioral tests through the installed `$review-team` skill.

If behavioral evidence requires a refinement, edit the repository package,
validate and commit it, reinstall it, confirm equality, and rerun the affected
tests. Never patch the installed copy and synchronize backward.

Installation must fail closed when an unrelated installed directory already
occupies the destination. The implementation plan must inspect that destination
before its first write and define a recoverable replacement procedure for later
installs of the package created by this component.

## Git Workflow

Implementation runs on an isolated branch or worktree of the repository. The
main controller executes the plan inline so the harness's collaboration slots
remain available for the nested Scope, Finder, Verifier, Sweep, and Synthesis
workers used by behavioral tests.

Commits should capture reviewable outcomes rather than individual mechanical
steps. Expected boundaries are:

1. behavioral design and implementation-plan migration;
2. RED scenarios and baseline evidence;
3. initial skill package;
4. static validation and first installation;
5. GREEN evidence;
6. evidence-driven refinements and final deployment evidence, when needed.

Checksum files remain useful as reproducibility and installation-integrity
evidence. Git commits replace their earlier role as a substitute for version
history.

## Validation

The revised implementation plan must preserve the frozen behavioral validation
campaign while changing its paths and boundaries:

- structural validation targets the repository package;
- behavioral validation invokes the installed copy;
- source and installed trees must match before each behavioral campaign;
- the reviewed target repository remains read-only;
- RED, GREEN, and REFACTOR outputs are committed under the component's
  evaluation directory;
- final evidence identifies both the source commit and installed-package
  checksums.

The deployment is complete only when the repository package validates, the
installed copy matches it, behavioral gates pass, and the relevant evidence is
committed.

## Non-Goals

- Building a generic installer or package manager for every skill in the
  repository.
- Making this skill portable to agent harnesses beyond Codex and Claude Code.
- Importing or replacing Claude Code's built-in review-team implementation.
- Creating a nested repository for the component.
- Maintaining two editable copies of the skill.
- Reopening frozen review-team behavior solely because its files moved.
