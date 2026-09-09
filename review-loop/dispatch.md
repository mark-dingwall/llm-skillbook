# Dispatch mechanics

Operational how-to only. Policy (what must be true before something is
green, what stops a run, what confirmation means) lives in `SKILL.md`; this
file owns only the execution mappings and CLI mechanics described below.

## Ordinary review execution

`review_loop/execution.py`'s `Executor` is the sole tested ordinary MVP
backend: a fixed, empirically-tested Bubblewrap mapping with a fresh
non-reusable process-tree identity and deadline-bound termination with
parent-death cleanup. The trusted Codex CLI process receives a fixed provider
auth file and network access as runtime prerequisites. `--sandbox read-only`
governs model-generated shell commands. For review data, the mapping exposes
the target (or a disposable copy), the exact review-data inputs named in the
call's input seal, and a fresh report/scratch channel. The outer mapping alone
does not make provider credentials secret from a compromised CLI process.
This contract makes no claim whether model-generated shell commands can or
cannot read the credential. If a requested reviewer CLI has no tested mapping
here, it cannot be dispatched; do not improvise an uncontained subprocess
call.

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

## Running the Python (`$SKILL_DIR/scripts/py`)

`$SKILL_DIR` is this skill's own directory (absolute path of the folder holding
`SKILL.md`) — substitute it literally. Run every `review_loop` Python — the
`__main__.py` CLI below and any `Controller`-driving library snippet — through
`$SKILL_DIR/scripts/py` (e.g. `"$SKILL_DIR/scripts/py" -m review_loop status
--run-root <path>`). The launcher resolves the skill's shipped project +
lockfile, so imports and deps work from any caller working directory. (The
in-repo test suite calls `python3 -m review_loop` directly — that path is
test-only and unaffected.)

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
    report as `STAGE0` on recovery — a disclosed recovery limitation, not a
    caller-repairable condition.
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
- **Multi-review took ordinary fallback**: first confirm the host resolved all
  prerequisites and safely constructed the adapter. Missing setup
  prerequisites or unsafe construction fail closed before fallback is
  available. After construction, a structured adapter result for a rechecked
  unavailable runtime, driver or participant, or failed aggregate validation
  takes the ordinary path once. A seal-mismatch `INDETERMINATE` is never a
  fallback path; see `SKILL.md`.
- **The `multi-review` smoke harness reports a `REPO_ROOT` failure**: in a
  nested checkout, confirm that `tests/manual/headless-driver-smoke.sh`
  resolves the component root rather than the enclosing Git root, and check
  whether `multi-review/` has its own `.git` in the test environment.
