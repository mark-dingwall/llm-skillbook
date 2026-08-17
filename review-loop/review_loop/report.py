"""Generate the human-facing Markdown report from canonical state.

Pure formatting over ``RunState.snapshot["processor_state"]`` -- the exact
compact records the controller already persisted via ``state.py``'s kernel.
This module never re-derives a verdict; it only renders what the kernel and
controller already decided (design Sec. 6: "one human-readable Markdown
ledger/report").
"""
from __future__ import annotations

from .controller import RunState

_MISSING = object()


def _get(processor: dict, key: str, default=_MISSING):
    value = processor.get(key, default)
    if value is _MISSING:
        return None
    return value


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- (none)\n"
    return "".join(f"- {item}\n" for item in items)


def generate_report(run_state: RunState) -> str:
    processor = run_state.snapshot.get("processor_state", {})
    lines: list[str] = []
    lines.append("# Review Loop Report")
    lines.append("")
    lines.append(f"- Stage: `{run_state.stage}`")
    if run_state.reason:
        lines.append(f"- Reason: {run_state.reason}")
    lines.append(f"- Governing seal: `{run_state.governing_seal}`")
    lines.append("")

    policy = _get(processor, "derive_policy")
    lines.append("## Selected policy")
    if policy is None:
        lines.append("Not yet derived.")
    else:
        lines.append(f"- Tier: `{policy['tier']}` (source: {policy['source']})")
        lines.append(f"- Round cap: {policy['round_cap']}")
        lines.append(f"- Normal reviewer capability: {policy['normal_capability']}")
        lines.append(f"- Specialist threshold: {policy['specialist_threshold']}")
        confirmation = "required" if policy["confirmation_required"] else "not required"
        lines.append(f"- Confirmation: {confirmation}")
    lines.append("")

    lines.append("## Confirmation path")
    if run_state.stage == "CANCELLED_BEFORE_REVIEW":
        lines.append(f"Cancelled before review: {run_state.reason}")
    elif policy is not None and policy["confirmation_required"]:
        lines.append("Automatic `max` tier confirmed before reviewer dispatch.")
    else:
        lines.append("No confirmation was required.")
    lines.append("")

    roster = _get(processor, "plan_roster")
    lines.append("## Staffing")
    if roster is None:
        lines.append("No roster planned.")
    else:
        planned = roster["roster"]
        entries = [
            (r["role"] if r["role"] != "specialist" else f"specialist ({r['area_id']})")
            for r in planned
        ]
        lines.append(f"- Planned: {len(planned)} role(s) across {len(roster['waves'])} wave(s)")
        lines.append(_bullet_list(entries).rstrip())
    lines.append("")

    lines.append("## Seals")
    lines.append(f"- Governing/target-baseline seal: `{run_state.governing_seal}`")
    terminal = _get(processor, "compute_terminal")
    if terminal is not None:
        # Controller.close() now performs a genuine fresh re-seal of the
        # authoritative target at CLOSE and compares it against the expected
        # identity (the verified post-FIX seal for a promoted run, or the
        # governing/anchor seal for an untouched run) -- a mismatch fails the
        # "seal" terminal conjunct below (Task 9 Slice 2). Git-index/commit-
        # drift detection beyond that byte-identity comparison remains
        # deferred; see tests/ACCEPTANCE.md.
        seal_drift = "seal" in terminal["failed_conditions"]
        lines.append(
            "- CLOSE recomputed a fresh seal of the authoritative target and "
            "compared it against the expected identity (the verified post-FIX "
            "seal for a promoted run, the governing/anchor seal otherwise): "
            + ("mismatch detected (NOT CONVERGED)." if seal_drift else "matched.")
        )
    lines.append("")

    gates = _get(processor, "reconcile_gates")
    lines.append("## Gate plan and results")
    if gates is None:
        lines.append("No gates reconciled.")
    else:
        for gate in gates["gates"]:
            lines.append(
                f"- `{gate['id']}` ({gate['classification']}, {gate['applicability']}): {gate['status']}"
            )
        if not gates["gates"]:
            lines.append("- (no gates discovered)")
    lines.append("")

    lines.append("## Evidence gaps")
    gaps = list(gates["evidence_gaps"]) if gates is not None else []
    lines.append(_bullet_list(gaps).rstrip())
    lines.append("")

    lines.append("## Mutation evidence")
    lines.append("Mutation testing was not run for this MVP round; no mutation-adequacy evidence to report.")
    lines.append("")

    lines.append("## Degraded behavior")
    lines.append("None recorded.")
    lines.append("")

    ledger = _get(processor, "apply_ledger_decisions")
    lines.append("## Ledger")
    if ledger is None:
        lines.append("No ledger rows.")
    else:
        rows = ledger["rows"]
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["state"]] = counts.get(row["state"], 0) + 1
        lines.append(f"- Total rows: {len(rows)}")
        for state, count in sorted(counts.items()):
            lines.append(f"- {state}: {count}")
    lines.append("")

    lines.append("## Residual limitations")
    lines.append(
        "Adjudication and single-round FIX (including post-FIX promotion to the "
        "authoritative target) are implemented and wired. Deferred: multi-round "
        "TRIAGE-reconcile onto prior canonical rows, inventory refresh across "
        "rounds, and round-N coverage/restaffing -- all require governing-seal "
        "advancement beyond this MVP's single-round scope; see tests/ACCEPTANCE.md."
    )
    lines.append("")

    lines.append("## Convergence and merge-readiness")
    if terminal is None:
        lines.append("CLOSE has not run; convergence unknown.")
    else:
        lines.append(f"- Terminal verdict: `{terminal['terminal_verdict']}`")
        lines.append(f"- Merge-ready: {terminal['merge_ready']}")
        if terminal["failed_conditions"]:
            lines.append("- Failed conjuncts:")
            for condition in terminal["failed_conditions"]:
                lines.append(f"  - {condition}")
        else:
            lines.append("- No failed conjuncts.")
    lines.append("")

    return "\n".join(lines) + "\n"
