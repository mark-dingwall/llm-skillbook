# Claude plugin hook contract

Plugin hooks live in `hooks.json` and call scripts owned by their canonical
component. Keep matchers limited to the component-specific event identity;
handlers must return successfully without side effects for unrelated or
inactive runs.

Run `claude plugin validate . --strict`, the owning component tests, and
`python3 -m pytest tests/test_plugin_agents.py -q` after changing hook
registration.
