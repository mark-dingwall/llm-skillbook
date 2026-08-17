# `.claude-plugin`

This directory contains the Claude marketplace and plugin metadata for this
repository. Use it when validating the local plugin or changing its metadata.

For installation and user-facing setup, start with the repository root
README. Validate metadata from the repository root with
`claude plugin validate . --strict`. When agent layout or metadata changes,
also run `python3 -m pytest tests/test_plugin_agents.py -q`.
