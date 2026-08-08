# PR #1 Review Fixes Design

## Goal

Resolve the five independently verified findings from the high-effort review of PR #1, then perform a second review scoped only to the resulting fix diff.

## Approach

Use focused boundary fixes instead of introducing a new lifecycle abstraction. The affected code is signal- and cancellation-sensitive; keeping each correction local makes its behavior and regression coverage easier to audit.

## Changes

### Path validation

Both command-line prompt-file resolution and YAML `files`/`context_files` resolution must translate `RuntimeError` from `Path.resolve()`—including symlink loops on supported Python 3.11—into the driver's existing clean invalid-input path. Invalid paths must print a concise error without a traceback and return exit code 2.

### Artifact encoding

Every prompt and review artifact written by the affected paths must specify UTF-8 explicitly. Valid Unicode input and reviewer output must not depend on the process locale.

### Cancellation and publication

Fan-out cancellation must be idempotent: only the first SIGTERM requests cancellation of the active task, allowing cleanup and process reaping to complete if another SIGTERM arrives.

Before synchronous report rendering begins, both SIGTERM and SIGINT must be handed to a synchronous cleanup handler. A signal during rendering or immediately after replacement must remove staged and final report files and terminate with exit code 1. A signal already queued before the handoff must still cancel before publication.

### Synthesis deadline

The configured synthesis timeout must cover both subprocess creation and communication. The implementation should mirror the single-deadline approach already used by reviewer fan-out so time spent launching reduces the remaining communication budget.

## Testing

Add regression tests before production changes and observe each fail for the intended reason:

- prompt-file and YAML input-path symlink loops;
- Unicode prompt and report writes under a forced non-UTF default encoding;
- SIGINT during report rendering and after publication;
- repeated SIGTERM while cancellation cleanup is in progress;
- synthesis subprocess creation that blocks beyond the configured timeout.

Run the focused changed-area suite after each red-green cycle, followed by the broader deterministic suite. The final multi-agent review must compare the fix branch against `262250c5b1f700ee56d0429470c5181037fb62d8` and must not re-review the original PR diff.

## Non-goals

- Refactoring process management into a new shared abstraction.
- Changing non-positive timeout semantics.
- Working around the independently verified CPython 3.14 `asyncio` subprocess lost-wakeup race that already exists in the base revision.
- Modifying the existing dirty `review-loop-compatibility` worktree.
