"""review-loop CLI entry point.

Two invocation surfaces, deliberately unequal in trust:

- Production subcommands (`create-run`, `status`, `report`) drive only
  `Controller`'s deterministic, non-role-validated operations: preflight
  (sealing plus profile/deadline/tier *intent* capture -- never tier
  *derivation*), durable-state recovery, and final-report generation. Each
  accepts controller-owned invocation intent only; none accepts a
  caller-supplied canonical snapshot, artifact registry, or projection, and
  each rejects an unrecognized request field outright (design Sec. 3: "does
  not expose a free-form operator CLI that can supply both a projection and
  a fabricated registry").
- `--test-fixture` is the pre-existing, still test-only pure-processor
  adapter (`review_loop.state.apply` against a caller-supplied snapshot +
  envelope). A caller-authored snapshot/registry IS the authority on that
  one path, by design, exclusively for fixture testing (see
  `tests/unit/test_state_cli.py`, `tests/contract/`); production never
  reaches it.

Stage 0 dispatch (evidence scout / inventory / rating), Round 1 review
dispatch, TRIAGE, FIX, adjudication, and the final-readiness challenge all
require a real role-output validator (`review_loop.prompts`) to run over
raw dispatched text *before* any projection becomes canonical -- that is
code, not JSON-describable data, so those stages are driven by a host
importing `review_loop.controller.Controller` directly and supplying real
dispatch callables (see SKILL.md and dispatch.md), never by this entry
point. Building that host driver is out of this module's scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

from .artifacts import ArtifactRef, CanonicalStore, ProjectionAuthority, TransitionEnvelope
from .controller import Controller, PreflightError, ProfileConfirmationRequired, RunState
from .profiles import InvocationIntent
from .report import generate_report
from .seals import SealError
from .state import apply

TIERS = ("low", "med", "high", "max")

# Keys a create-run request may name. Anything else -- most importantly a
# caller-supplied "snapshot", "envelope", "artifact_registry", or
# "projection" -- is rejected outright: production never treats caller JSON
# as canonical state or projection authority.
_CREATE_RUN_KEYS = {
    "target", "base", "head", "exclusions", "review_profile",
    "max_time_seconds", "no_confirm", "ground_truth", "tier", "run_root",
}

# Furthest-advanced processor_state operation key present names the
# durably-recoverable stage, mirroring `RunState.stage`'s own values
# (`controller.py` sets exactly these strings). `CANCELLED_BEFORE_REVIEW`
# and an awaiting-confirmation `INDETERMINATE` are documented in
# `RunState`'s own docstring as in-memory-only outcomes of a stopped
# `run_stage0` call with no durable marker yet (carried forward, not
# fixed here) -- a purely disk-derived view cannot distinguish either from
# a plain mid-Stage-0 crash, so both report as "STAGE0" here; see
# tests/ACCEPTANCE.md. A third, narrower gap: `Controller.close()` also
# returns an in-memory `stage="INDETERMINATE"` when a FIX_VERIFIED row's
# delta was verified only against a disposable copy and never promoted to
# the authoritative target (`copy_only_fixes` non-empty) -- but it still
# WRITES `compute_terminal`, so `_derive_stage` on disk reports "COMPLETE"
# for that run, same as any other closed run. This is not a false-green:
# the authoritative `merge_ready=False` and `failed_conditions` containing
# `"indeterminate"` are still correctly persisted and surfaced by `status`/
# `report` via `compute_terminal` itself -- only the coarse *stage* label
# collapses two different "COMPLETE" causes into one string. Disclosed,
# not a derivation change.
_STAGE_ORDER = (
    ("compute_terminal", "COMPLETE"),
    ("record_final_challenge", "CLOSE"),
    ("apply_ledger_decisions", "TRIAGE"),
    ("plan_roster", "REVIEW"),
    ("derive_policy", "STAGE0"),
    ("reconcile_gates", "STAGE0"),
    ("refresh_inventory", "STAGE0"),
)


def _error(code: str, message: str) -> dict:
    return {"schema_version": 1, "ok": False, "errors": [{"path": "$", "code": code, "message": message}]}


def _emit(payload: dict) -> int:
    json.dump(payload, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0 if payload.get("ok") else 2


def _default_run_root(target: Path) -> Path:
    """``$XDG_STATE_HOME/review-loop/runs/<project-id>/<run-id>/`` (design
    Sec. 6). No implementation of this path existed before this CLI;
    project-id is a stable digest of the resolved target path, run-id a
    fresh UUID -- collision-resistant and filesystem-safe, per the design's
    own requirement, but this exact encoding is this module's choice, not
    a shared contract other code depends on.
    """
    state_home = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    project_id = hashlib.sha256(str(target.resolve()).encode("utf-8")).hexdigest()[:16]
    run_id = uuid.uuid4().hex
    return state_home / "review-loop" / "runs" / project_id / run_id


def _derive_stage(processor_state: dict) -> str:
    for key, stage in _STAGE_ORDER:
        if key in processor_state:
            return stage
    return "PREFLIGHT" if "preflight" in processor_state else "UNKNOWN"


def _load_run(run_root: Path) -> dict | None:
    try:
        return CanonicalStore(run_root).load()
    except FileNotFoundError:
        return None


def _read_request(args) -> dict:
    if getattr(args, "json", None) is not None:
        text = args.json
    else:
        text = sys.stdin.read()
    if not text.strip():
        return {}
    return json.loads(text)


def _cmd_create_run(args) -> int:
    try:
        request = _read_request(args)
    except json.JSONDecodeError as exc:
        return _emit(_error("invalid_json", str(exc)))
    if not isinstance(request, dict):
        return _emit(_error("invalid_request", "request must be a JSON object"))

    # "host calls" invocation style: explicit flags set/override request
    # fields so a host need not construct JSON by hand.
    for flag_name, key in (
        ("target", "target"), ("base", "base"), ("head", "head"),
        ("review_profile", "review_profile"), ("max_time_seconds", "max_time_seconds"),
        ("tier", "tier"), ("run_root", "run_root"),
    ):
        value = getattr(args, flag_name, None)
        if value is not None:
            request[key] = value
    if getattr(args, "exclude", None):
        request["exclusions"] = list(args.exclude)
    if getattr(args, "ground_truth", None):
        request["ground_truth"] = list(args.ground_truth)
    if getattr(args, "no_confirm", False):
        request["no_confirm"] = True

    unknown = set(request) - _CREATE_RUN_KEYS
    if unknown:
        return _emit(_error("unknown_field", f"unsupported request field(s): {sorted(unknown)}"))
    if not isinstance(request.get("target"), str) or not request["target"]:
        return _emit(_error("missing_field", "target is required"))

    tier = request.get("tier")
    if tier is not None and tier not in TIERS:
        return _emit(_error("invalid_tier", f"tier must be one of {TIERS} or omitted for automatic derivation"))
    max_time = request.get("max_time_seconds")
    if max_time is not None and (type(max_time) is not int or max_time <= 0):
        return _emit(_error("invalid_max_time_seconds", "max_time_seconds must be a positive integer"))
    no_confirm = request.get("no_confirm", False)
    if not isinstance(no_confirm, bool):
        return _emit(_error("invalid_no_confirm", "no_confirm must be a boolean"))
    exclusions = request.get("exclusions", [])
    ground_truth = request.get("ground_truth", [])
    if not isinstance(exclusions, list) or not all(isinstance(e, str) for e in exclusions):
        return _emit(_error("invalid_exclusions", "exclusions must be a list of strings"))
    if not isinstance(ground_truth, list) or not all(isinstance(g, str) for g in ground_truth):
        return _emit(_error("invalid_ground_truth", "ground_truth must be a list of strings"))
    for key in ("base", "head", "review_profile"):
        if request.get(key) is not None and not isinstance(request[key], str):
            return _emit(_error(f"invalid_{key}", f"{key} must be a string or omitted"))

    target = Path(request["target"])
    run_root = Path(request["run_root"]) if request.get("run_root") else _default_run_root(target)

    intent = InvocationIntent(
        target=target,
        base=request.get("base"),
        head=request.get("head"),
        exclusions=tuple(exclusions),
        review_profile=request.get("review_profile"),
        max_time_seconds=max_time,
        no_confirm=no_confirm,
        ground_truth=tuple(Path(g) for g in ground_truth),
        run_root=run_root,
        tier=tier,
    )
    controller = Controller()
    try:
        # Never interactive: a non-interactive production caller that names
        # an invalid/missing profile stops closed instead of silently
        # falling back to tier defaults (design Sec. 4/7: "never silently
        # fall back").
        state = controller.create_run(intent, confirm_tier_defaults=None)
    except ProfileConfirmationRequired as exc:
        return _emit(_error("profile_confirmation_required", exc.reason))
    except (PreflightError, SealError) as exc:
        return _emit(_error("preflight_rejected", str(exc)))

    preflight = state.snapshot["processor_state"]["preflight"]
    return _emit({
        "schema_version": 1, "ok": True,
        "run_root": str(state.run_root),
        "governing_seal": state.governing_seal,
        "stage": state.stage,
        "resolved": {
            "tier": preflight["invocation_intent"]["tier"],
            "no_confirm": preflight["invocation_intent"]["no_confirm"],
            "review_profile": preflight["invocation_intent"]["review_profile"],
            "selected_profile": preflight["selected_profile"],
            "absolute_expiry": preflight["absolute_expiry"],
        },
    })


def _cmd_status(args) -> int:
    run_root = Path(args.run_root)
    snapshot = _load_run(run_root)
    if snapshot is None:
        return _emit(_error("no_such_run", f"no run state at {run_root}"))
    processor = snapshot["processor_state"]
    payload = {
        "schema_version": 1, "ok": True,
        "run_root": str(run_root), "governing_seal": snapshot["governing_seal"],
        "stage": _derive_stage(processor),
    }
    if "compute_terminal" in processor:
        terminal = processor["compute_terminal"]
        payload["terminal"] = {
            "terminal_verdict": terminal["terminal_verdict"],
            "merge_ready": terminal["merge_ready"],
            "failed_conditions": terminal["failed_conditions"],
        }
    return _emit(payload)


def _cmd_report(args) -> int:
    run_root = Path(args.run_root)
    snapshot = _load_run(run_root)
    if snapshot is None:
        return _emit(_error("no_such_run", f"no run state at {run_root}"))
    processor = snapshot["processor_state"]
    run_state = RunState(
        run_root=run_root, governing_seal=snapshot["governing_seal"],
        snapshot=snapshot, stage=_derive_stage(processor), reason=None,
    )
    report_path = run_root / "REPORT.md"
    report_path.write_text(generate_report(run_state))
    return _emit({"schema_version": 1, "ok": True, "report_path": str(report_path)})


def _legacy_test_fixture() -> int:
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        return _emit(_error("invalid_json", str(exc)))
    try:
        snapshot = request["snapshot"]
        raw = request["envelope"]
        envelope = TransitionEnvelope(
            raw["operation"],
            tuple(ArtifactRef(**ref) for ref in raw["artifact_refs"]),
            raw["projection"], raw["expected_governing_seal"],
        )
        result = apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))
    except (KeyError, TypeError, ValueError) as exc:
        return _emit(_error("invalid_fixture", str(exc)))
    except Exception as exc:
        return _emit(_error("rejected", str(exc)))
    return _emit({"schema_version": 1, "ok": True, "result": result})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="review-loop")
    sub = parser.add_subparsers(dest="command")

    create = sub.add_parser("create-run", help="preflight: seal the target, resolve profile/deadline/tier intent")
    create.add_argument("--json", default=None, help="full request as a JSON string (default: read JSON from stdin)")
    create.add_argument("--target", default=None)
    create.add_argument("--base", default=None)
    create.add_argument("--head", default=None)
    create.add_argument("--exclude", action="append", default=[])
    create.add_argument("--review-profile", dest="review_profile", default=None)
    create.add_argument("--max-time-seconds", dest="max_time_seconds", type=int, default=None)
    create.add_argument("--no-confirm", action="store_true")
    create.add_argument("--ground-truth", action="append", default=[])
    create.add_argument("--tier", default=None, choices=TIERS)
    create.add_argument("--run-root", dest="run_root", default=None)
    create.set_defaults(func=_cmd_create_run)

    status = sub.add_parser("status", help="recover the durable stage of a persisted run")
    status.add_argument("--run-root", dest="run_root", required=True)
    status.set_defaults(func=_cmd_status)

    report = sub.add_parser("report", help="write the final Markdown report and print its path")
    report.add_argument("--run-root", dest="run_root", required=True)
    report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)

    if argv == ["--test-fixture"]:
        return _legacy_test_fixture()

    parser = _build_parser()
    if not argv:
        parser.print_usage(sys.stderr)
        return 2
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_usage(sys.stderr)
        return 2
    try:
        return args.func(args)
    except json.JSONDecodeError as exc:
        return _emit(_error("invalid_json", str(exc)))


if __name__ == "__main__":
    raise SystemExit(main())
