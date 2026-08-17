# Codex discovery contract

`.agents` provides repository-local discovery aliases for Codex. The aliases
are relative and zero-copy: they expose canonical skill roots without creating
another editable source tree.

Edit the canonical skill root, not an alias. Any move or rename must update the
installer and plugin metadata together, then run the packaging and discovery
checks. Keep maintainer guidance at the repository or directory entry points;
it must not leak into copied skill payloads.

From the repository root, run:

```bash
python3 -m pytest tests/test_install.py tests/test_plugin_agents.py \
  'tests/test_documentation.py::test_documentation_entrypoints[.agents]' -q
```

A failure means the install payload or fail-closed boundary regressed, the
required plugin-agent copies drifted, or this directory's entry points and
exact `AGENTS.md -> CLAUDE.md` link are invalid.
