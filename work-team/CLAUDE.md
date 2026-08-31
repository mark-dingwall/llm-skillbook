# work-team controller guidance

The live [skill contract](SKILL.md) and its references are the operational
authority. Read the owning reference immediately before planning, dispatching,
or reporting; do not recreate rules from memory. [Design](docs/) and
[evaluation](evals/) records are provenance.

## Boundary

The controller plans, dispatches, validates, loops, verifies, and reports. It
never writes a deliverable, applies a fix, or issues a review verdict. A
worker's failure becomes a retry with the same packet, a re-plan into smaller
packets, or a residual — never controller work.

## Run artefacts

`.work-team/` run directories are gitignored by default; the controller adds
the ignore entry during Frame. Committing run artefacts requires an explicit
user override.

## Harness neutrality

Prose must not depend on one harness. Name the subagent primitive generically
and give both concrete forms only where a command differs (Agent tool;
`spawn_agent` with `fork_turns: "none"`). Scripts are Python 3 standard
library only.

## Verification

Instruction-only skill; scripts have no separate suite here. After changing
entry points or links, run from the repository root:

```bash
python3 -m pytest \
  'tests/test_documentation.py::test_documentation_entrypoints[work-team]' \
  'tests/test_documentation.py::test_entrypoint_local_markdown_links_resolve[work-team]' -q
```

Behavioral changes to SKILL.md or references require a scenario run per
`evals/run-eval.sh` on both harnesses before merge; record results in `evals/`.
Install the skill under test as a filtered copy (`install.py` without `--dev`,
mirrored to `~/.codex/skills`); a symlink exposes `evals/oracle.md` to the
evaluated agent and invalidates the run. Audit each transcript for reads of
`evals/` before scoring.
