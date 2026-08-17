# Dispatch mechanics

Operational how-to only. Policy (what must be true before something is
green, what stops a run, what confirmation means) lives in `SKILL.md` and
the governing design; this file never restates it.

## Ordinary review execution

`review_loop/execution.py`'s `Executor` is the sole tested ordinary MVP
backend: the Codex CLI under a fixed, empirically-tested Bubblewrap mapping
(`--sandbox read-only`, no host credentials, no network, a fresh non-reusable
process-tree identity, deadline-bound termination with parent-death cleanup).
It exposes the target (or a disposable copy), the exact review-data inputs
named in the call's input seal, and a fresh report/scratch channel — nothing
else. If a requested reviewer CLI has no tested mapping here, it cannot be
dispatched; do not improvise an uncontained subprocess call.

`FIX` uses a *separate* write-enabled mapping (`review_loop/fix.py`,
`build_fix_call`): auth and network stay on (the implementer may need them),
but the disposable copy is the only writable target surface, and dependency/
lockfile/tooling-path writes are rejected before the candidate delta is ever
accepted. Never reuse the ordinary read-only mapping for FIX or vice versa —
they enforce opposite guarantees.

Gate execution (`review_loop/evidence.py`) uses a third, narrower mapping:
no credentials, no network, either the sealed target directly (only for a
tested non-mutating command) or a disposable copy for anything that may
write ordinary test/build output.

## Multi-review containment

`review_loop/multi_review.py`'s `MultiReviewAdapter` launches the repo-local
multi-review headless driver inside `bwrap --unshare-pid --die-with-parent`,
reusing multi-review's tested Bubblewrap recipe reduced to the fixed
Claude+Codex pair. See `SKILL.md`'s "Multi-review" section for the opt-in
decision and its disclosed residual limitations — this file only names the
mechanism. Real Bubblewrap containment tests live in
`review-loop/tests/integration/test_multi_review_containment.py` and
`multi-review/tests/unit/test_headless_driver_smoke_harness.py`.

## The `__main__.py` CLI

Two invocation surfaces, deliberately unequal in trust — see the module's
own docstring for the full rationale:

- **Production**, JSON on stdin or equivalent flags, no caller-supplied
  canonical snapshot/registry/projection ever accepted:
  - `create-run` — preflight only. Request keys: `target` (required),
    `base`, `head`, `exclusions` (list), `review_profile`, `max_time_seconds`
    (positive int), `no_confirm` (bool), `ground_truth` (list of paths),
    `tier` (`low`/`med`/`high`/`max`, operator intent — recorded, not
    derived), `run_root` (defaults to
    `$XDG_STATE_HOME/review-loop/runs/<project-id>/<run-id>/`). Any other
    key is rejected outright. An invalid or missing explicitly-named
    profile stops closed (`profile_confirmation_required`) — this
    non-interactive path never asks and never falls back to tier defaults
    silently.
  - `status --run-root <path>` — recovers the furthest-advanced durable
    stage from persisted `processor_state` keys. `CANCELLED_BEFORE_REVIEW`
    and an awaiting-confirmation `INDETERMINATE` have no durable marker yet
    (see `RunState`'s docstring in `controller.py`) and both currently
    report as `STAGE0` on recovery — a disclosed limitation, not a bug fix
    owed to this task (`tests/ACCEPTANCE.md`).
  - `report --run-root <path>` — writes `<run_root>/REPORT.md` via
    `report.generate_report` and prints its path.
- **Test-only**: `python3 -m review_loop --test-fixture`, JSON `{"snapshot":
  ..., "envelope": ...}` on stdin, calling `state.apply` directly against
  the caller-supplied snapshot. This is the pure-processor fixture adapter
  used by `tests/unit/test_state_cli.py` and the `tests/contract/` suite; it
  is exactly as narrow as it was before this task and production code never
  reaches it.

Stage 0 through CLOSE — everything that needs a real role-output validator
in the loop before a projection becomes canonical — has no CLI surface. Call
`Controller`'s methods directly as a library, per `SKILL.md`'s "Dispatching
a role" section.

## Troubleshooting

- **`ArtifactMismatch` from `state.apply`/`CanonicalStore`**: a projection,
  artifact reference, or expected seal did not match the canonical registry
  exactly. This is the fail-closed authority boundary working as intended —
  never work around it by hand-constructing a passing envelope; find why the
  upstream evidence or seal actually diverged.
- **A round comes back `INDETERMINATE` with no reviewer dispatched**: check
  `reconcile_gates`' `blocking_reasons` first — a failed applicable gate
  (required *or* supporting) stops the round before any reviewer runs
  (`Controller._close_blocked_stage0`).
- **Multi-review took ordinary fallback**: expected whenever the driver,
  Bubblewrap, or either fixed participant is unavailable, or the driver's
  strict aggregate validation failed — this is automatic, not a fault to
  chase, unless the log instead shows a seal-mismatch `INDETERMINATE` (which
  is never a fallback path; see `SKILL.md`).
- **The pre-existing `multi-review` smoke-harness `REPO_ROOT` failure**:
  fixed in this task (`tests/manual/headless-driver-smoke.sh` was deriving
  `repo_root` from `git rev-parse --show-toplevel`, which resolves to an
  *enclosing* repository when `multi-review/` is nested in a monorepo/
  worktree rather than being its own Git repo). If it reappears, check
  whether `multi-review/` again lacks its own `.git` in the environment
  running the suite.
