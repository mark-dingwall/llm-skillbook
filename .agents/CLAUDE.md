# Codex discovery contract

`.agents` provides repository-local discovery aliases for Codex. The aliases
are relative and zero-copy: they expose canonical skill roots without creating
another editable source tree.

Edit the canonical skill root, not an alias. Any move or rename must update the
installer and plugin metadata together, then run the packaging and discovery
checks. Keep maintainer guidance at the repository or directory entry points;
it must not leak into copied skill payloads.
