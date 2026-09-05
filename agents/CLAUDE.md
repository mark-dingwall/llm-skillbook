# Plugin agent mirror contract

The Claude plugin agent definition files in root `agents/` are regular files
deliberately kept byte-identical to their canonical component definitions.
Do not replace those definitions with symlinks: Claude plugin registration
skips symlinked agents.

Synchronize mirrors by copying from the canonical definitions, then run
`tests/test_plugin_agents.py`. A successful metadata validation alone is not
evidence that agent registration works; the mirror and regular-file checks are
part of the contract.
