# Run plan contract

`plan.json` is the run. It is written before any dispatch, validated with
`wt-validate <skill>/references/schemas/plan.schema.json plan.json`, edited by
humans between runs, and cited by `result.json`.

## Fields

```json
{
  "run": "2026-09-01T02-todo-cli",
  "task": "<task text verbatim>",
  "phases": [
    {
      "id": "spec",
      "workers": [{
        "id": "spec-writer", "role": "writer",
        "goal": "Write SPEC.md: commands, storage schema, exact outputs, exit codes. Done when every command has a Given/When/Then.",
        "inputs": ["<task text>"], "owns": ["SPEC.md"],
        "verify": "test -s SPEC.md",
        "returns": "schemas/status.schema.json"
      }]
    },
    {
      "id": "tests",
      "workers": [{
        "id": "test-writer", "role": "writer",
        "goal": "Black-box pytest suite derived from SPEC.md only. Done when the suite collects and fails for missing implementation.",
        "inputs": ["SPEC.md"], "owns": ["test_todo.py"],
        "verify": "python3 -m pytest -q --collect-only test_todo.py",
        "returns": "schemas/status.schema.json"
      }]
    },
    {
      "id": "impl",
      "loop": {"review": "reviewer", "fix": "fixer", "max_rounds": 2},
      "workers": [{
        "id": "implementer", "role": "implementer",
        "goal": "Make test_todo.py pass with minimal code. Done when pytest is green.",
        "inputs": ["SPEC.md", "test_todo.py"], "owns": ["todo.py"],
        "verify": "python3 -m pytest -q test_todo.py",
        "returns": "schemas/status.schema.json"
      }]
    }
  ]
}
```

- `owns` — every path the worker may create or edit. Within one phase, `owns`
  sets must be disjoint; the controller checks this before dispatch.
- `verify` — a command the worker runs and pastes into `verify_output`, and the
  controller reruns on ingest.
- `returns` — the schema `wt-validate` applies to the worker's final message.
- `group` — optional label; workers sharing a group run concurrently, groups
  run in order. Omit when the whole phase is one group.
- `loop` — review→fix rounds for the phase. `review` and `fix` name roles from
  [packets.md](packets.md); they are always separate fresh workers.

## Fan-out predicate

Workers may run concurrently only when all hold:

1. Their `owns` sets are disjoint.
2. Each has its own `verify` command that can pass without the others.
3. None consumes an artefact another is producing in the same phase.

Otherwise put them in successive phases. Tests that read a spec follow the
spec phase; implementation follows tests; review follows implementation.

## Sizing

Split by verification boundary: one worker per independently runnable check
(one test file, one build target, one review group). If a goal needs two
checks, it is two workers. Do not size by a number; when telemetry from a
previous run shows one worker dominating (`wt-telemetry`), split that worker's
goal along its verification boundaries.

## Requirements no test can observe

Visual styling, animation, tone, "feels right". These must not be left to a
prose reminder in an implementer's packet. Add a verification worker whose
oracle is one of:

- **Rendering assertion**: a browser-level test (e.g. Playwright:
  computed style, `getAnimations()`, reduced-motion emulation, screenshot
  diff). Ask the user once, in Frame, before adding such a dependency.
- **Rubric judge**: a fresh worker given the rendered output (screenshot or
  DOM dump) and a written rubric, returning `schemas/review.schema.json`.
  The rubric lists observable criteria; the verdict is data, not prose.

Its findings enter the same review→fix loop as everything else.

## Numbers

`max_rounds`, retry counts, and wave sizes are failure detectors: when hit,
they produce residuals. They are not design rules and must not be quoted as
such in reports.
