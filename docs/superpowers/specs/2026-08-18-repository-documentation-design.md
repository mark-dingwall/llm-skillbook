# Repository Documentation Design

**Date:** 2026-08-18  
**Status:** Approved for implementation

## Purpose

Give humans and coding agents a durable entry point at the repository root and
in every tracked top-level directory. Human documentation should explain what a
component is and what to do next. Agent documentation should preserve the
technical contracts needed to change it safely without duplicating facts that
the working tree can answer directly.

## Scope

The documentation contract covers the repository root and every tracked
top-level directory. At the time of this design those directories are
`.agents`, `.claude-plugin`, `agents`, `docs`, `feature-forge`, `multi-review`,
`review-loop`, `review-team`, and `tests`.

`.git` and ignored or generated directories such as `.codex`, `.pytest_cache`,
`__pycache__`, virtual environments, and package metadata are outside the
contract. The verification test derives covered directories from tracked Git
paths, so a future tracked top-level directory joins the contract without a
manually maintained inventory.

## Audience and Outcomes

Each `README.md` serves a person arriving without repository history. After
reading it, that person should know what the directory is for, when it matters,
and the next useful action or authoritative document.

Each `CLAUDE.md` serves an LLM or contributor preparing to change files in that
scope. After reading it, they should know the durable authority boundaries,
safety invariants, maintenance workflow, and appropriate verification. It is
not an inventory of the current tree.

Each `AGENTS.md` is a relative symlink to the `CLAUDE.md` beside it. The shared
content must therefore be harness-neutral even though the canonical filename is
`CLAUDE.md`.

## Document Shape

### Human overview

Directory READMEs use only the sections needed from this sequence:

1. A one-paragraph purpose and intended use.
2. The primary action, invocation, or maintenance entry point.
3. Essential prerequisites or safety constraints.
4. Links to authoritative details instead of copied implementation prose.

They omit source-tree inventories, dated history, internal state schemas, and
provider- or environment-specific observations.

### Agent guidance

Directory CLAUDE files use only the sections needed from this sequence:

1. Scope and source-of-truth boundaries.
2. Durable behavioral and safety invariants.
3. Change workflow, including cross-component synchronization rules.
4. Verification commands and what failures mean.
5. Capability limits that materially affect safe changes.

They omit exact file inventories, line references, commit IDs, dated model or
tool versions, historical test totals, local checkout observations, and facts
that can be obtained cheaply from source, manifests, or test discovery.
Commands are retained when they are stable contributor interfaces rather than
observations about one machine.

### Root documents

Root documents are written only after the directory documents pass their
cold-read. The root README summarizes the package, supported use cases,
installation, and links to the component READMEs. The root CLAUDE file
synthesizes repository-wide authority, packaging, synchronization, testing,
documentation, and safety rules; component-specific detail remains local.

## Evidence and Synthesis Workflow

Every included top-level directory receives an independent read-only
exploration before prose is drafted. Explorers identify the human action,
durable technical contracts, verification entry points, stale claims, and
brittle facts to exclude. The main agent validates returned claims against the
working tree before using them.

Directory documents are then drafted in place, cold-read as if by a new reader,
and cut until every section serves its named outcome. Only after all directory
documents are complete may they become inputs to the root documents.

## Staleness Policy

Operational documentation must not prescribe removed commands or paths,
overstate implemented behavior, or describe environment observations as
project contracts. This pass corrects the stale operational claims found during
exploration, including multi-review execution and containment wording, Claude
development-install behavior, obsolete manual-smoke paths, and review-loop's
current capability boundary.

Historical plans, evaluations, transcripts, and evidence remain unchanged when
their old paths or dated facts are part of the record. Active entry points must
label those artifacts historical or non-authoritative so readers do not mistake
them for current instructions. A repository-wide search checks known obsolete
operational terms after drafting; each hit is either corrected or demonstrated
to be intentionally historical.

## Symlinks and Distribution

At root and in each covered directory, `AGENTS.md` must be a relative symlink
whose literal target is `CLAUDE.md`. It must not be a copied file.

Repository-maintainer documentation is not part of copied skill payloads.
`install.py` therefore excludes `AGENTS.md` alongside `CLAUDE.md`; otherwise
`shutil.copy2` would follow the symlink and silently ship a regular duplicate.
This exclusion does not affect repository-local Codex discovery or development
installs, which resolve the canonical skill directories directly.

The rule does not apply to Claude plugin subagent definitions under the root
`agents` directory. Those must remain real files and byte-match their canonical
multi-review counterparts because plugin discovery does not register symlinked
agent definitions.

## Verification

A repository test derives tracked top-level directories from Git and verifies:

- the root and every covered directory contain `README.md` and `CLAUDE.md`;
- every corresponding `AGENTS.md` is a symlink with literal target
  `CLAUDE.md` and resolves to an existing file;
- copied installs exclude both maintainer guidance filenames;
- existing packaging and plugin-agent contracts continue to pass.

The final verification also runs Markdown-link and stale-reference checks,
component tests relevant to edited operational docs, the root packaging suite,
plugin validation, and `git diff --check`. Historical artifacts are excluded
from claims about current behavior but not from link-integrity checks where
their links are intended to remain navigable.

## Acceptance Criteria

The work is complete when:

1. Root and every tracked top-level directory have the required README and
   CLAUDE files plus an exact `AGENTS.md -> CLAUDE.md` symlink.
2. Every README is a succinct human overview with an actionable next step.
3. Every CLAUDE file contains durable, harness-neutral technical guidance and
   no tree inventory or dated environment facts.
4. Directory documents were synthesized from independent exploration, and root
   documents were synthesized afterward from the completed directory docs.
5. Discovered stale operational claims are corrected; retained dated material
   is clearly historical or non-authoritative.
6. Installed payload behavior remains unchanged apart from explicitly
   excluding the new maintainer symlinks.
7. Automated contract checks, relevant existing tests, plugin validation,
   stale-reference review, link review, and whitespace validation all pass.
