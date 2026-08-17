"""Trivial fixture target for the ordinary clean tracer (Task 6, Step 2).

Deliberately tiny: the tracer's point is proving the controller's
orchestration and the real gate-execution path, not exercising a real
codebase. The one baseline gate below exits 0 unconditionally.
"""


def greet(name: str) -> str:
    return f"hello, {name}"
