# `tests`

This directory holds packaging and plugin-registration regression tests. They
check repository entry points, installer payload boundaries, and Claude agent
mirrors; they are not component-behavior tests for the skills themselves.

Run the full root test suite with `python3 -m pytest -q` after packaging or
documentation changes. Use the focused tests while iterating, then run the
full suite before handoff.
