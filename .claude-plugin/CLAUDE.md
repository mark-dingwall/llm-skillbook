# Claude plugin metadata contract

The manifest dots resolve from the repository root, so plugin metadata must be
interpreted from this checkout rather than from a copied subdirectory. Keep
the plugin names aligned across marketplace and plugin metadata.

Strict plugin validation checks metadata shape, but it does not prove that
Claude registered every agent or hook. Pair validation with the plugin-agent
contract tests whenever agent or hook layout changes. Keep installation
guidance in the root README.

Run both gates from the repository root:

```bash
claude plugin validate . --strict
python3 -m pytest tests/test_plugin_agents.py -q
```

A validation failure means the plugin metadata is invalid. A contract-test
failure means a plugin-root agent is missing, differs from its canonical
definition, or is a symlink instead of the required real file.
