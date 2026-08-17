"""Run preflight: sealing, ground truth, profile selection, persisted intent.

Resolves invocation intent into a persisted run before any semantic
dispatch (design Sec. 4, "Preflight and Stage 0"). No reviewer, evidence
scout, or FIX agent is dispatched here.
"""
from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Sequence

from .artifacts import CanonicalStore, EvidenceArtifact, canonical_bytes
from .evidence import (
    EvidenceDiscoveryIndeterminate,
    EvidencePlan,
    Gate,
    GateProposal,
    GateResult,
)
from .evidence import discover_evidence as _discover_evidence
from .profiles import InvocationIntent, ProfileError, ReviewProfile, RolePins, load_profile
from .prompts import (
    DispatchExpectation,
    ProcessCompletion,
    RoleExpectation,
    RoleValidationError,
    UnusableReview,
    ValidatedReview,
    ValidatedRoleArtifact,
    validate_review_report,
)
from .seals import GitPolicy, SealEntry, TargetSeal, check_run_root_disjoint, seal_inputs, seal_target


class PreflightError(Exception):
    """The invocation cannot be resolved into a run; the target is rejected."""


class ProfileConfirmationRequired(Exception):
    """An explicit profile is missing or malformed; the caller must decide.

    Never fall back to tier defaults silently: the caller must confirm via
    ``confirm_tier_defaults`` before ``create_run`` proceeds without it.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


STAGES = (
    "PREFLIGHT",
    "STAGE0",
    "REVIEW",
    "TRIAGE",
    "FIX",
    "CLOSE",
    "COMPLETE",
    "INDETERMINATE",
    "CANCELLED_BEFORE_REVIEW",
)


@dataclass(frozen=True)
class RunState:
    """The controller's view of one run: its persisted canonical snapshot
    plus the current lifecycle stage (design: "Controller stages become
    persisted enums").

    ``stage``/``reason`` are a deterministic projection of ``snapshot``'s
    ``processor_state`` keys wherever that is possible (so they always agree
    with what is durably on disk after a restart) -- see
    ``Controller._derive_stage``. The two stages that are NOT derivable from
    "which operation has run" -- ``CANCELLED_BEFORE_REVIEW`` and an
    INDETERMINATE stop while awaiting automatic-max confirmation -- are
    carried only on this in-memory ``RunState`` returned by the stopping
    call; a full crash-durable record of *why* a run stopped mid-Stage-0
    would need either a new state.py operation (the compact kernel is a
    fixed AST boundary this task must not touch) or a new artifacts.py
    surface (out of this task's file scope). Disclosed as a carry-forward,
    not silently faked.
    """

    run_root: Path
    governing_seal: str
    snapshot: dict[str, object]
    stage: str = "PREFLIGHT"
    reason: str | None = None


def _detect_git_policy(target: Path, intent: InvocationIntent) -> GitPolicy:
    result = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise PreflightError(f"target is not a Git working tree: {target}")
    toplevel = Path(result.stdout.strip()).resolve()
    return GitPolicy(
        enabled=True,
        base=intent.base,
        head=intent.head,
        include_untracked=True,
        include_index=True,
        git_dir_outside_target=(toplevel != target),
    )


def _check_exclusions(exclusions: tuple[str, ...]) -> None:
    for excl in exclusions:
        if not isinstance(excl, str) or not excl or excl.startswith("/") or ".." in Path(excl).parts:
            raise PreflightError(f"exclusion escapes the sealed target: {excl!r}")


def _role_to_dict(pins: RolePins) -> dict[str, object]:
    return {
        "capability": pins.capability,
        "model": pins.model,
        "fallback_capability": pins.fallback_capability,
        "fallback_model": pins.fallback_model,
        "multi_review_models": dict(pins.multi_review_models),
    }


def _profile_to_dict(profile: ReviewProfile) -> dict[str, object]:
    return {
        "version": profile.version,
        "max_time_seconds": profile.max_time_seconds,
        "holistic": _role_to_dict(profile.holistic),
        "adversarial": _role_to_dict(profile.adversarial),
        "specialists": _role_to_dict(profile.specialists),
    }


def _seal_entry_to_dict(entry: SealEntry) -> dict[str, object]:
    return {"path": entry.path, "kind": entry.kind, "mode": entry.mode, "digest": entry.content_digest}


def _target_seal_to_dict(seal: TargetSeal) -> dict[str, object]:
    return {
        "schema_version": seal.schema_version,
        "root": seal.root,
        "tree_digest": seal.tree_digest,
        "git_dir_outside_target": seal.git_dir_outside_target,
        "git_base_commit": seal.git_base_commit,
        "git_head_commit": seal.git_head_commit,
        "git_index_digest": seal.git_index_digest,
        "digest": seal.digest,
    }


class ControllerError(Exception):
    """Stage 0/round orchestration cannot proceed; callers fail closed."""


class ConfirmationExpired(Exception):
    """The persisted deadline expired while awaiting confirmation.

    A ``confirm`` callable passed to ``run_stage0`` should raise this
    instead of returning when the run's absolute expiry has passed while a
    human was being asked to confirm an automatically-derived ``max`` tier
    (design: "If the persisted deadline expires while awaiting confirmation,
    expiry takes precedence: mark the stage INDETERMINATE").
    """


def _new_id() -> str:
    return uuid.uuid4().hex


def _issue(
    store: CanonicalStore,
    *,
    operation: str,
    projection: dict[str, object],
    evidence: Sequence[EvidenceArtifact],
) -> dict[str, object]:
    return store.issue_transition(operation=operation, evidence=tuple(evidence), projection=projection)


def _artifact(artifact_id: str, kind: str, target_seal: str, body: object) -> EvidenceArtifact:
    raw = body if isinstance(body, bytes) else canonical_bytes(body)
    return EvidenceArtifact(artifact_id=artifact_id, kind=kind, schema_version=1, target_seal=target_seal, raw_bytes=raw)


def _dispatch_gates(
    plan: EvidencePlan,
    seal: str,
    gate_dispatch: Callable[[Gate], GateResult],
    new_id: Callable[[], str],
) -> tuple[list[GateResult], list[dict[str, object]], list["EvidenceArtifact"]]:
    """Execute every applicable gate in ``plan`` and shape its compact record.

    Shared by ``run_stage0`` (first execution) and ``rerun_gates`` (design:
    "After any accepted FIX delta ... run every safe applicable required
    gate plus the safe supporting gates ... on the verified post-FIX seal")
    so the two call sites cannot drift on how a gate becomes a ``gates``
    record or an evidence artifact.
    """
    gate_results: list[GateResult] = []
    gate_dicts: list[dict[str, object]] = []
    gate_evidence: list[EvidenceArtifact] = []
    for gate in plan.gates:
        if gate.applicability == "not_applicable":
            gate_dicts.append({
                "id": gate.id, "target_seal": seal, "applicability": "not_applicable",
                "classification": gate.classification, "status": "NOT_RUN", "artifact_id": None,
            })
            continue
        result = gate_dispatch(gate)
        gate_results.append(result)
        artifact_id = new_id()
        gate_evidence.append(_artifact(artifact_id, "gate-result", seal, {
            "gate_id": result.gate_id, "argv": list(result.argv), "exit_status": result.exit_status,
            "stdout_excerpt": result.stdout_excerpt, "stderr_excerpt": result.stderr_excerpt,
            "rationale": result.rationale, "provenance": result.provenance,
        }))
        gate_dicts.append({
            "id": gate.id, "target_seal": seal, "applicability": "applicable",
            "classification": gate.classification, "status": result.status, "artifact_id": artifact_id,
        })
    return gate_results, gate_dicts, gate_evidence


def _dispatch_with_retry(dispatch: Callable[[], ValidatedRoleArtifact], *, on_exhausted: str) -> ValidatedRoleArtifact:
    """Call ``dispatch`` once; on malformed output (design: "retried once"),
    call it exactly one more time. A second malformed result is fail-closed.
    """
    try:
        return dispatch()
    except RoleValidationError:
        try:
            return dispatch()
        except RoleValidationError as exc:
            raise ControllerError(on_exhausted) from exc


def _aggregate_adjudication(projection: object, green_ids: Sequence[str]) -> tuple[str, list[str]]:
    """Fold the per-row adjudication verdicts into one kernel status + decided IDs.

    Precedence (design's atomic-bounce / undecided-subset-retry): any UNDECIDED
    row blocks the whole batch (retry); otherwise any BOUNCE reverts the whole
    batch atomically; otherwise UPHOLD. ``decided_ids`` is the undecided subset
    for a retry (informational to the kernel) and the full green set otherwise.
    """
    if not isinstance(projection, list):
        raise ControllerError("adjudication projection must be a per-row decision list")
    statuses = {}
    for item in projection:
        if not isinstance(item, dict) or "id" not in item or "status" not in item:
            raise ControllerError("adjudication decision is malformed")
        statuses[item["id"]] = item["status"]
    if set(statuses) != set(green_ids):
        raise ControllerError("adjudication must decide exactly the pending green set")
    values = list(statuses.values())
    if "UNDECIDED" in values:
        return "UNDECIDED", [i for i in green_ids if statuses[i] == "UNDECIDED"]
    if "BOUNCE" in values:
        return "BOUNCE", list(green_ids)
    return "UPHOLD", list(green_ids)


@dataclass(frozen=True)
class InventoryArea:
    id: str
    charter: str
    surfaces: tuple[str, ...]
    consequence: str
    generalist_miss: bool
    owning_file_ids: tuple[str, ...]


@dataclass(frozen=True)
class Stage0Outcome:
    run_state: RunState
    gate_results: tuple[GateResult, ...]
    evidence_gaps: tuple[str, ...]
    areas: tuple[InventoryArea, ...]
    priority_order: tuple[str, ...]
    tier: str
    # Mirrors reconcile_gates' own compact rollup (state._gates:
    # "review_may_start": not any("failed" in reason for reason in blocks)).
    # Defaults to the fail-closed value: every early-abort Stage0Outcome
    # (INDETERMINATE / CANCELLED_BEFORE_REVIEW) stops before gates are ever
    # reconciled, so "may review start" is unknown, not true.
    review_may_start: bool = False
    blocking_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateRerunOutcome:
    run_state: RunState
    gate_results: tuple[GateResult, ...]
    evidence_gaps: tuple[str, ...]
    review_may_start: bool
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class RawReport:
    report_id: str
    role: str
    review: ValidatedReview


@dataclass(frozen=True)
class Round1Outcome:
    run_state: RunState
    roster: tuple[dict[str, object], ...]
    raw_reports: tuple[RawReport, ...]


@dataclass(frozen=True)
class FixOutcome:
    run_state: RunState
    transition: object  # fix.FixTransition
    gate_rerun: GateRerunOutcome
    disposable_copy: Path


@dataclass(frozen=True)
class AdjudicationOutcome:
    run_state: RunState
    status: str
    attempts: int
    settled: bool


@dataclass(frozen=True)
class PromotionRecord:
    """The result of ``promote_post_fix_baseline``: which ledger ids' verified
    FIX delta was actually written back to the authoritative target, and the
    seal ``close()`` must find there afterward. Pure in-memory record -- the
    run's single fixed ``governing_seal`` carries no new canonical field for
    it (single-round promotion, not multi-baseline advancement).
    """
    covered_ids: tuple[str, ...]
    after_seal: str


class Controller:
    def __init__(self, xdg_config_home: Path | None = None) -> None:
        self._xdg_config_home = xdg_config_home

    def create_run(
        self,
        intent: InvocationIntent,
        *,
        confirm_tier_defaults: Callable[[str], bool] | None = None,
    ) -> RunState:
        if intent.run_root is None:
            raise PreflightError("invocation intent has no run root")
        target = Path(intent.target).resolve()
        run_root = Path(intent.run_root).resolve()
        if not target.is_dir():
            raise PreflightError(f"target is not a directory: {target}")

        # Reject any run-root/target overlap before creating any artifact.
        check_run_root_disjoint(target, run_root)
        _check_exclusions(intent.exclusions)

        git_policy = _detect_git_policy(target, intent)
        target_seal = seal_target(target, git_policy)

        ground_truth_seal = seal_inputs(list(intent.ground_truth), target_seal.digest)

        profile: ReviewProfile | None = None
        if intent.review_profile is not None:
            try:
                profile = load_profile(intent.review_profile, self._xdg_config_home)
            except ProfileError as exc:
                if confirm_tier_defaults is None or not confirm_tier_defaults(str(exc)):
                    raise ProfileConfirmationRequired(str(exc)) from exc
                profile = None

        effective_max_time = intent.max_time_seconds
        if effective_max_time is None and profile is not None:
            effective_max_time = profile.max_time_seconds
        start_time = datetime.now(timezone.utc)
        absolute_expiry = (
            (start_time + timedelta(seconds=effective_max_time)).isoformat()
            if effective_max_time is not None
            else None
        )

        preflight = {
            "invocation_intent": {
                "target": str(intent.target),
                "base": intent.base,
                "head": intent.head,
                "exclusions": list(intent.exclusions),
                "review_profile": intent.review_profile,
                "max_time_seconds": intent.max_time_seconds,
                "no_confirm": intent.no_confirm,
                "ground_truth": [str(p) for p in intent.ground_truth],
            },
            "resolved_target": str(target),
            "resolved_base": target_seal.git_base_commit,
            "resolved_head": target_seal.git_head_commit,
            "resolved_exclusions": list(intent.exclusions),
            "run_root": str(run_root),
            "ground_truth": [_seal_entry_to_dict(e) for e in ground_truth_seal.entries],
            "target_seal": _target_seal_to_dict(target_seal),
            "delta_policy": {
                "enabled": git_policy.enabled,
                "base": git_policy.base,
                "head": git_policy.head,
                "include_untracked": git_policy.include_untracked,
                "include_index": git_policy.include_index,
                "git_dir_outside_target": git_policy.git_dir_outside_target,
            },
            "selected_profile": _profile_to_dict(profile) if profile is not None else None,
            "start_time": start_time.isoformat(),
            "absolute_expiry": absolute_expiry,
        }

        store = CanonicalStore(run_root)
        store.initialize(target_seal.digest, {"preflight": preflight})
        snapshot = store.load()
        return RunState(run_root=run_root, governing_seal=target_seal.digest, snapshot=snapshot)

    # --- Stage 0: evidence discovery + gate execution + inventory + rating ---

    def run_stage0(
        self,
        run_state: RunState,
        *,
        operator_gates: Sequence[GateProposal] = (),
        repository_gates: Sequence[GateProposal] = (),
        scout: Callable[[], ValidatedRoleArtifact],
        gate_dispatch: Callable[[Gate], GateResult],
        inventory_owner: Callable[[RoleExpectation], ValidatedRoleArtifact],
        inventory_challenger: Callable[[RoleExpectation], ValidatedRoleArtifact],
        inventory_revision: Callable[[RoleExpectation], ValidatedRoleArtifact] | None = None,
        explicit_tier: str | None,
        no_confirm: bool = False,
        raters: tuple[Callable[[], ValidatedRoleArtifact], Callable[[], ValidatedRoleArtifact]] | None = None,
        confirm: Callable[[str], bool] | None = None,
        new_id: Callable[[], str] = _new_id,
    ) -> Stage0Outcome:
        """Scout + every applicable baseline gate, then inventory owner and
        challenger, then -- only for automatic effort -- two raters (brief
        interfaces: exactly this order). Malformed retries and a
        confirmation decline/expiry stop before any reviewer is scheduled.
        """
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)

        def _indeterminate(reason: str) -> Stage0Outcome:
            return Stage0Outcome(
                run_state=RunState(run_state.run_root, run_state.governing_seal, run_state.snapshot, "INDETERMINATE", reason),
                gate_results=(), evidence_gaps=(), areas=(), priority_order=(), tier="",
            )

        try:
            captured: dict[str, ValidatedRoleArtifact] = {}

            def _tracking_scout() -> ValidatedRoleArtifact:
                result = scout()
                captured["scout"] = result
                return result

            plan = _discover_evidence(operator_gates, repository_gates, _tracking_scout)
            scout_artifact = captured["scout"]

            gate_results, gate_dicts, gates_only_evidence = _dispatch_gates(plan, seal, gate_dispatch, new_id)
            gate_evidence: list[EvidenceArtifact] = [
                _artifact(new_id(), "evidence-scout", seal, scout_artifact.artifact)
            ] + gates_only_evidence

            owner_expectation = RoleExpectation(
                request_id=new_id(), role_id="inventory-owner", target_seal=seal,
                round_input_seal=None, expected_ids=(),
            )
            owner_result = _dispatch_with_retry(
                lambda: inventory_owner(owner_expectation), on_exhausted="inventory owner output was malformed twice"
            )
            inventory_evidence = [_artifact(new_id(), "inventory-owner", seal, owner_result.artifact)]

            challenge_expectation = RoleExpectation(
                request_id=new_id(), role_id="inventory-challenge", target_seal=seal,
                round_input_seal=None, expected_ids=(),
            )
            challenge_result = _dispatch_with_retry(
                lambda: inventory_challenger(challenge_expectation),
                on_exhausted="inventory challenger output was malformed twice",
            )
            inventory_evidence.append(_artifact(new_id(), "inventory-challenge", seal, challenge_result.artifact))

            final_owner = owner_result
            if challenge_result.artifact["verdict"] == "CHALLENGE":
                if inventory_revision is None:
                    raise ControllerError("inventory was challenged but no revision dispatcher was supplied")
                challenge_ids = tuple(c["id"] for c in challenge_result.artifact["challenges"])
                revision_expectation = RoleExpectation(
                    request_id=new_id(), role_id="inventory-revision", target_seal=seal,
                    round_input_seal=None, expected_ids=challenge_ids,
                )
                final_owner = _dispatch_with_retry(
                    lambda: inventory_revision(revision_expectation),
                    on_exhausted="inventory revision output was malformed twice",
                )
                inventory_evidence.append(_artifact(new_id(), "inventory-revision", seal, final_owner.artifact))

            ratings_projection: list[object] = []
            rating_evidence: list[EvidenceArtifact] = []
            if explicit_tier is None:
                if raters is None or len(raters) != 2:
                    raise ControllerError("automatic tier requires exactly two rating samples")
                for rater in raters:
                    rating_result = _dispatch_with_retry(rater, on_exhausted="rating output was malformed twice")
                    ratings_projection.append(rating_result.projection)
                    rating_evidence.append(_artifact(new_id(), "rating", seal, rating_result.artifact))
        except (EvidenceDiscoveryIndeterminate, ControllerError) as exc:
            return _indeterminate(str(exc))

        if explicit_tier is not None:
            tier_projection = {"explicit_tier": explicit_tier, "no_confirm": no_confirm, "ratings": []}
            tier_evidence = [_artifact(new_id(), "tier-selection", seal, {"explicit_tier": explicit_tier})]
        else:
            tier_projection = {"explicit_tier": None, "no_confirm": no_confirm, "ratings": ratings_projection}
            tier_evidence = rating_evidence

        updated = _issue(store, operation="derive_policy", projection=tier_projection, evidence=tier_evidence)
        policy = updated["processor_state"]["derive_policy"]
        tier = policy["tier"]

        if policy["confirmation_required"]:
            if confirm is None:
                return Stage0Outcome(
                    run_state=RunState(
                        run_state.run_root, run_state.governing_seal, updated,
                        "CANCELLED_BEFORE_REVIEW", "automatic max tier requires confirmation but none was supplied",
                    ),
                    gate_results=(), evidence_gaps=(), areas=(), priority_order=(), tier=tier,
                )
            try:
                confirmed = confirm("automatically derived tier is 'max'; confirm reviewer dispatch?")
            except ConfirmationExpired as exc:
                return Stage0Outcome(
                    run_state=RunState(run_state.run_root, run_state.governing_seal, updated, "INDETERMINATE", str(exc)),
                    gate_results=(), evidence_gaps=(), areas=(), priority_order=(), tier=tier,
                )
            if not confirmed:
                return Stage0Outcome(
                    run_state=RunState(
                        run_state.run_root, run_state.governing_seal, updated,
                        "CANCELLED_BEFORE_REVIEW", "operator declined automatic max-tier confirmation",
                    ),
                    gate_results=(), evidence_gaps=(), areas=(), priority_order=(), tier=tier,
                )

        gates_projection = {"target_seal": seal, "gates": gate_dicts}
        updated = _issue(store, operation="reconcile_gates", projection=gates_projection, evidence=gate_evidence)
        reconciled = updated["processor_state"]["reconcile_gates"]
        kernel_gaps = reconciled["evidence_gaps"]
        evidence_gaps = tuple(dict.fromkeys(list(plan.evidence_gaps) + list(kernel_gaps)))
        review_may_start = reconciled["review_may_start"]
        blocking_reasons = tuple(reconciled["blocking_reasons"])

        inventory_projection = {**final_owner.projection, "prior_areas": [], "mappings": [], "invalidators": {}}
        updated = _issue(store, operation="refresh_inventory", projection=inventory_projection, evidence=inventory_evidence)
        refreshed = updated["processor_state"]["refresh_inventory"]
        active_areas = refreshed["active_areas"]
        priority_order = tuple(refreshed["priority_order"])

        rich_by_id = {a["id"]: a for a in final_owner.artifact["areas"]}
        areas = tuple(
            InventoryArea(
                id=a["id"],
                charter=rich_by_id[a["id"]]["charter"],
                surfaces=tuple(rich_by_id[a["id"]]["surfaces"]),
                consequence=a["consequence"],
                generalist_miss=a["generalist_miss"],
                owning_file_ids=tuple(a["owning_file_ids"]),
            )
            for a in active_areas
        )

        return Stage0Outcome(
            run_state=RunState(run_state.run_root, run_state.governing_seal, updated, "STAGE0", None),
            gate_results=tuple(gate_results),
            evidence_gaps=evidence_gaps,
            areas=areas,
            priority_order=priority_order,
            tier=tier,
            review_may_start=review_may_start,
            blocking_reasons=blocking_reasons,
        )

    def rerun_gates(
        self,
        run_state: RunState,
        plan: EvidencePlan,
        *,
        gate_dispatch: Callable[[Gate], GateResult],
        new_id: Callable[[], str] = _new_id,
    ) -> GateRerunOutcome:
        """Re-execute every applicable gate in ``plan`` and reconcile again.

        Design: "After any accepted FIX delta, refresh applicability and run
        every safe applicable required gate plus the safe supporting gates
        selected for the changed behavior on the verified post-FIX seal."
        This task does not implement FIX itself (carried to a later task,
        per task-6-report.md); it supplies only the re-execution mechanism
        FIX will call once a verified post-FIX seal exists. ``plan`` is the
        caller's already-refreshed evidence plan (its own applicability
        refresh, e.g. via ``discover_evidence`` again, is that later task's
        job). Reissuing ``reconcile_gates`` is safe to call any number of
        times -- each call simply replaces the compact gates record for the
        current ``run_state.governing_seal``.
        """
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        gate_results, gate_dicts, gate_evidence = _dispatch_gates(plan, seal, gate_dispatch, new_id)
        gates_projection = {"target_seal": seal, "gates": gate_dicts}
        updated = _issue(store, operation="reconcile_gates", projection=gates_projection, evidence=gate_evidence)
        reconciled = updated["processor_state"]["reconcile_gates"]
        evidence_gaps = tuple(dict.fromkeys(list(plan.evidence_gaps) + list(reconciled["evidence_gaps"])))
        return GateRerunOutcome(
            run_state=RunState(run_state.run_root, run_state.governing_seal, updated, run_state.stage, run_state.reason),
            gate_results=tuple(gate_results),
            evidence_gaps=evidence_gaps,
            review_may_start=reconciled["review_may_start"],
            blocking_reasons=tuple(reconciled["blocking_reasons"]),
        )

    def _close_blocked_stage0(self, stage0: Stage0Outcome, new_id: Callable[[], str]) -> RunState:
        """Compute a NOT_CONVERGED terminal verdict for a run that Stage 0
        itself blocked (design: "Any executed applicable gate that does not
        produce its expected passing signal stops NOT CONVERGED"). Round 1
        never dispatches, so `round1_triage_complete` /
        `scheduled_reports_usable` / `raw_reports_reconciled` are honestly
        `False` and no `final_challenge` was ever attempted; the kernel's own
        `gates_not_ready` conjunct (from `reconcile_gates`' real
        `blocking_reasons`) is what actually drives NOT_CONVERGED here --
        those other unmet conjuncts just make the failure impossible to
        misread as anything else.
        """
        run_state = stage0.run_state
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        processor = run_state.snapshot["processor_state"]
        policy = processor["derive_policy"]
        active_areas = processor["refresh_inventory"]["active_areas"]
        gates = processor["reconcile_gates"]
        lifecycle = {
            "confirmation": "not_required" if not policy["confirmation_required"] else "confirmed",
            "deadline_expired": False,
            "round1_triage_complete": False,
            "scheduled_reports_usable": False,
            "raw_reports_reconciled": False,
            "any_indeterminate": False,
            "expected_final_seal": seal,
            "actual_final_seal": seal,
        }
        final_challenge = {
            "state": "BLOCKED_BEFORE_REVIEW", "fresh": False, "target_seal": seal,
            "source_finding_ids": [], "artifact_id": "no-final-challenge-blocked-by-gates",
            "retry_required": False,
        }
        projection = {
            "lifecycle": lifecycle, "ledger": [], "gates": gates,
            "areas": active_areas, "final_challenge": final_challenge,
        }
        evidence = [_artifact(new_id(), "close-computation", seal, {
            "lifecycle": lifecycle, "blocked_before_review": True,
            "blocking_reasons": list(stage0.blocking_reasons),
        })]
        updated = _issue(store, operation="compute_terminal", projection=projection, evidence=evidence)
        reason = "blocked before review: " + "; ".join(stage0.blocking_reasons)
        return RunState(run_state.run_root, run_state.governing_seal, updated, "COMPLETE", reason)

    # --- Round 1: freeze roster, dispatch holistic/adversarial/specialists ---

    def run_round1(
        self,
        stage0: Stage0Outcome,
        *,
        dispatch_role: Callable[[DispatchExpectation], tuple[bytes, ProcessCompletion]],
        capacity: int | None = None,
        multi_review_dispatch: "Callable[[DispatchExpectation], object] | None" = None,
        new_id: Callable[[], str] = _new_id,
    ) -> Round1Outcome:
        """`multi_review_dispatch`, when supplied, replaces `dispatch_role`
        for the ``"holistic"`` roster entry only: it is called with the same
        `DispatchExpectation` and must return a
        `multi_review.MultiReviewResult` (Task 11 -- the caller-contained
        fixed-pair multi-review slot). On a validated aggregate, its two
        qualified reports become two ``RawReport``s for this one roster
        entry (both role ``"holistic"``, same expectation, distinct
        preallocated report ids) -- ``run_triage`` already aggregates across
        however many raw reports Round 1 produced, so no further change is
        needed there. On a structured ordinary-fallback reason, this falls
        through to the unchanged `dispatch_role` path below (no multi-review
        retry). `multi_review.MultiReviewIndeterminate` is never caught here
        -- target/round-input seal drift propagates straight out, exactly
        like every other uncaught `ControllerError` this function already
        raises (design: "target/input seal drift is INDETERMINATE, never
        fallback").
        """
        from .execution import default_capacity

        if stage0.run_state.stage != "STAGE0":
            raise ControllerError(f"run_round1 requires a STAGE0 outcome, got stage={stage0.run_state.stage!r}")
        if not stage0.review_may_start:
            # A failed applicable gate -- required OR supporting -- means no
            # reviewer is ever dispatched; the kernel's own gates rollup
            # already carries this as review_may_start=False.
            blocked_state = self._close_blocked_stage0(stage0, new_id)
            return Round1Outcome(run_state=blocked_state, roster=(), raw_reports=())

        run_state = stage0.run_state
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        areas_by_id = {a.id: a for a in stage0.areas}
        active_areas = run_state.snapshot["processor_state"]["refresh_inventory"]["active_areas"]

        roster_projection = {
            "tier": stage0.tier,
            "areas": active_areas,
            "priority_order": list(stage0.priority_order),
            "capacity": capacity or default_capacity(),
        }
        updated = _issue(
            store, operation="plan_roster", projection=roster_projection,
            evidence=[_artifact(new_id(), "roster-plan", seal, {"tier": stage0.tier})],
        )
        roster = tuple(updated["processor_state"]["plan_roster"]["roster"])

        raw_reports: list[RawReport] = []
        for entry in roster:
            role = entry["role"]
            area_id = entry.get("area_id")
            charter_id = area_id if role == "specialist" else role
            if role == "specialist":
                scope_locator_ids = tuple(areas_by_id[area_id].owning_file_ids)
            else:
                # Round 1 dispatches against the whole sealed target (design
                # Sec. 4: "Round 1 reviews the full sealed target"); this MVP
                # does not model per-file locator IDs for a whole-target
                # scope, so a single fixed sentinel stands for "everything".
                scope_locator_ids = ("target-root",)
            request_id = new_id()
            expectation = DispatchExpectation(
                request_id=request_id, role=role, charter_id=charter_id, target_seal=seal,
                round_input_seal=None, scope_locator_ids=scope_locator_ids,
            )
            if role == "holistic" and multi_review_dispatch is not None:
                mr_result = multi_review_dispatch(expectation)
                if mr_result.reports is not None:
                    for qualified in mr_result.reports:
                        raw_reports.append(
                            RawReport(report_id=qualified.report_id, role=role, review=qualified.review)
                        )
                    continue
                # structured ordinary-fallback reason: dispatch exactly the
                # same single-reviewer path every other role already uses,
                # for this same expectation -- no multi-review retry.
            body, process = dispatch_role(expectation)
            outcome = validate_review_report(body, expectation, process)
            if isinstance(outcome, UnusableReview) or not outcome.usable:
                raise ControllerError(f"round 1 role {role!r} produced no usable report")
            raw_reports.append(RawReport(report_id=request_id, role=role, review=outcome))

        return Round1Outcome(
            run_state=RunState(run_state.run_root, run_state.governing_seal, updated, "REVIEW", None),
            roster=roster,
            raw_reports=tuple(raw_reports),
        )

    # --- TRIAGE: strict-JSON triage of every usable raw report ---

    def run_triage(
        self,
        round1: Round1Outcome,
        *,
        triager: Callable[[RoleExpectation], ValidatedRoleArtifact],
        new_id: Callable[[], str] = _new_id,
    ) -> RunState:
        run_state = round1.run_state
        # run_triage only ever INITIALIZES the ledger (round 1). Round-N
        # triage-RECONCILE onto prior canonical rows -- and everything that
        # rides on it (reopened settlements, coverage invalidation, successor
        # STALE, Critical restaffing, oscillation, round caps) -- depends on
        # multi-baseline seal advancement and is deferred to Task 9. Fail closed
        # LOUDLY rather than letting a second call reinitialize or silently skip.
        if "apply_ledger_decisions" in run_state.snapshot["processor_state"]:
            raise ControllerError(
                "round-N triage-reconcile onto prior canonical rows is deferred to Task 9 "
                "(needs post-FIX baseline seal advancement); refusing to reinitialize the ledger"
            )
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        usable_ids = tuple(r.report_id for r in round1.raw_reports)
        raw_findings = {
            r.report_id: {
                f.finding_id: (f.claim, f.severity, list(f.locator_ids)) for f in r.review.record.source_findings
            }
            for r in round1.raw_reports
        }
        expectation = RoleExpectation(
            request_id=new_id(), role_id="triage", target_seal=seal, round_input_seal=None,
            expected_ids=usable_ids, extra={"raw_findings": raw_findings},
        )
        result = _dispatch_with_retry(lambda: triager(expectation), on_exhausted="triage output was malformed twice")
        rows = result.projection["rows"]

        initial_rows: list[dict[str, object]] = []
        decisions: list[dict[str, object]] = []
        for row in rows:
            if row["state"] != "OPEN":
                raise ControllerError(
                    f"triage row {row['id']!r} proposes {row['state']} on first appearance; "
                    "not supported by this task's scope"
                )
            initial_rows.append({**row, "proof_artifact_ids": [], "manifest_artifact_id": None})
            decisions.append({
                "id": row["id"], "state": "OPEN", "proof_artifact_ids": [], "manifest_artifact_id": None,
            })

        ledger_projection = {
            "target_seal": seal, "initial_rows": initial_rows, "decisions": decisions,
            "manifests": [], "adjudication": None,
        }
        raw_evidence = [_artifact(r.report_id, "raw-report", seal, r.review.body) for r in round1.raw_reports]
        evidence = raw_evidence + [_artifact(new_id(), "triage-result", seal, result.artifact)]
        updated = _issue(store, operation="apply_ledger_decisions", projection=ledger_projection, evidence=evidence)
        return RunState(run_state.run_root, run_state.governing_seal, updated, "TRIAGE", None)

    # --- FIX: the sole authorized mutation window -----------------------

    def run_fix(
        self,
        run_state: RunState,
        *,
        target_root: Path,
        fix_implementer: Callable[[Path, RoleExpectation], ValidatedRoleArtifact],
        evidence_plan: EvidencePlan,
        post_fix_gate_dispatch: Callable[[Path], Callable[[Gate], GateResult]],
        new_id: Callable[[], str] = _new_id,
    ) -> "FixOutcome":
        """Materialize a disposable copy, dispatch the sole non-delegating FIX
        implementer against it, validate the candidate delta before recording
        ``FIX_APPLIED``, then rerun the required/supporting gates on the verified
        post-FIX copy.

        The implementer is faked in tests: a callable that writes the fix into
        the disposable copy and returns a validated ``fix`` role artifact. The
        real backend would build ``fix.build_fix_call`` + ``execution.Executor``;
        that provider dispatch is out of this task's tested scope.
        """
        from .evidence import make_disposable_copy
        from .fix import FixController
        from .seals import GitPolicy, seal_target

        seal = run_state.governing_seal
        rows = run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
        open_rows = [r for r in rows if r["state"] == "OPEN"]
        if not open_rows:
            raise ControllerError("run_fix requires at least one OPEN ledger row")

        work = Path(run_state.run_root) / "fix" / new_id()
        copy_root = work / "copy"
        make_disposable_copy(seal_target(Path(target_root), GitPolicy(enabled=False)), copy_root)
        before = seal_target(copy_root, GitPolicy(enabled=False))

        expectation = RoleExpectation(
            request_id=new_id(), role_id="fix", target_seal=seal, round_input_seal=None,
            expected_ids=tuple(r["id"] for r in open_rows),
        )
        manifest = fix_implementer(copy_root, expectation)
        after = seal_target(copy_root, GitPolicy(enabled=False))

        fixctl = FixController(run_state, work, new_id=new_id)
        request = fixctl.prepare(open_rows, seal, evidence_plan)
        validated = fixctl.validate_candidate(request, before, after, manifest, copy_root=copy_root)
        transition = fixctl.apply(validated)

        gate_rerun = self.rerun_gates(
            transition.run_state, evidence_plan, gate_dispatch=post_fix_gate_dispatch(copy_root), new_id=new_id,
        )
        return FixOutcome(
            run_state=gate_rerun.run_state, transition=transition,
            gate_rerun=gate_rerun, disposable_copy=copy_root,
        )

    # --- adjudication: strict two-call settlement of green decisions ----

    def run_adjudication(
        self,
        run_state: RunState,
        settlements: Sequence[dict[str, object]],
        *,
        adjudicator: Callable[[RoleExpectation], ValidatedRoleArtifact],
        authority_kinds: dict[str, str] | None = None,
        proof_evidence: Sequence[EvidenceArtifact] = (),
        new_id: Callable[[], str] = _new_id,
    ) -> "AdjudicationOutcome":
        """Settle a batch of green (FIX_VERIFIED / REFUTED / INTENTIONAL) decisions.

        The adjudication role returns a per-row UPHOLD/BOUNCE/UNDECIDED verdict;
        this controller (Task-1/2 deferred the grouping decision here) aggregates
        it into the kernel's single-status ``apply_ledger_decisions`` adjudication:
        any UNDECIDED retries the whole set once (attempt two consumes the
        canonical retry state); otherwise any BOUNCE atomically reverts every
        green decision; otherwise UPHOLD settles them with the positive
        seal-bound adjudication proof. An empty settlement set makes no call.
        """
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        kinds = authority_kinds or {}
        rows = {r["id"]: r for r in run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]}
        by_id = {s["id"]: s for s in settlements}
        green_states = {"FIX_VERIFIED", "REFUTED", "INTENTIONAL"}

        if not settlements:
            raise ControllerError("run_adjudication requires at least one green settlement")
        if len(by_id) != len(settlements):
            raise ControllerError("settlements must decide each row at most once")
        if set(by_id) != set(rows):
            raise ControllerError("this task adjudicates the full pending ledger in one batch (round-N is Task 9)")
        for row in rows.values():
            if row["state"] not in {"OPEN", "FIX_APPLIED"}:
                raise ControllerError(
                    f"row {row['id']!r} is already terminal ({row['state']}); re-adjudication is Task 9"
                )
        for ident, s in by_id.items():
            if s["state"] not in green_states:
                raise ControllerError(f"settlement {ident!r} proposes non-green state {s['state']!r}")

        green_ids = [r_id for r_id in rows if r_id in by_id]
        manifests: list[dict[str, object]] = []
        decisions: list[dict[str, object]] = []
        for ident in rows:
            s = by_id[ident]
            manifest = s.get("manifest_artifact_id")
            decisions.append({
                "id": ident, "state": s["state"],
                "proof_artifact_ids": list(s.get("proof_artifact_ids", [])),
                "manifest_artifact_id": manifest,
            })
            if manifest is not None:
                manifests.append({"id": manifest, "finding_id": ident})

        expectation = RoleExpectation(
            request_id=new_id(), role_id="adjudication", target_seal=seal, round_input_seal=None,
            expected_ids=tuple(green_ids), extra={"adjudication_kinds": kinds},
        )
        result = _dispatch_with_retry(
            lambda: adjudicator(expectation), on_exhausted="adjudication output was malformed twice"
        )
        status, decided_ids = _aggregate_adjudication(result.projection, green_ids)

        # The green settlements' own proof (post-FIX re-review + gate reruns) is
        # registered once, in the first settling transition; a retry reuses those
        # already-canonical proof IDs by reference. "A passing gate or manifest
        # alone is never fix verification" -- the caller supplies both.
        attempt = 1
        state = run_state
        pending_proof = tuple(proof_evidence)
        while True:
            proof_id = new_id()
            proof = None if status in {"UNDECIDED", "FAILED"} else proof_id
            adjudication = {
                "attempt": attempt, "status": status,
                "decided_ids": decided_ids, "proof_artifact_id": proof,
            }
            projection = {
                "target_seal": seal, "decisions": decisions,
                "manifests": manifests, "adjudication": adjudication,
            }
            evidence = tuple(pending_proof) + (_artifact(proof_id, "adjudication-result", seal, result.artifact),)
            pending_proof = ()
            updated = _issue(store, operation="apply_ledger_decisions", projection=projection, evidence=evidence)
            state = RunState(run_state.run_root, run_state.governing_seal, updated, run_state.stage, None)
            if attempt == 1 and status in {"UNDECIDED", "FAILED"}:
                attempt = 2
                retry_expectation = RoleExpectation(
                    request_id=new_id(), role_id="adjudication", target_seal=seal, round_input_seal=None,
                    expected_ids=tuple(green_ids), extra={"adjudication_kinds": kinds},
                )
                result = _dispatch_with_retry(
                    lambda: adjudicator(retry_expectation), on_exhausted="adjudication retry was malformed twice"
                )
                status, decided_ids = _aggregate_adjudication(result.projection, green_ids)
                continue
            break

        final_rows = state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
        settled = all(r["state"] in green_states for r in final_rows)
        return AdjudicationOutcome(
            run_state=RunState(state.run_root, state.governing_seal, state.snapshot, "TRIAGE", None),
            status=status, attempts=attempt, settled=settled,
        )

    # --- promotion: write a verified single-round FIX back to the real target ---

    def promote_post_fix_baseline(
        self,
        run_state: RunState,
        validated: "ValidatedFix",
        target_root: Path,
        *,
        new_id: Callable[[], str] = _new_id,
    ) -> "PromotionRecord":
        """Replay ``validated``'s already-verified FIX delta from its disposable
        copy onto the REAL, authoritative target -- single-round promotion only
        (the run's fixed ``governing_seal`` is never advanced to a new baseline;
        that is multi-round seal advancement, still deferred and loudly
        fail-closed via ``run_triage``/``run_adjudication``'s guards).

        Pure I/O + verification, fail-closed on any drift: the real target must
        reseal to exactly ``validated.before_seal`` before anything is written
        (FIX only ever touched the disposable copy, so the target should be
        unchanged) -- then ``FixController.write_back`` replays the delta --
        then the target must reseal to exactly ``validated.after_seal`` (an
        incomplete or wrong replay, or a mid-write-back crash that leaves the
        tree half-written, must never be silently accepted as a promoted fix).
        Returns the promotion record naming which ledger ids this write-back
        covers, for ``close()`` to check honestly.
        """
        from .fix import FixController
        from .seals import GitPolicy, seal_target

        target_root = Path(target_root)
        pre = seal_target(target_root, GitPolicy(enabled=False))
        if pre.digest != validated.before_seal:
            raise ControllerError(
                "promotion aborted: the authoritative target has drifted since FIX ran "
                f"(expected pre-FIX seal {validated.before_seal!r}, found {pre.digest!r})"
            )
        fixctl = FixController(run_state, Path(run_state.run_root) / "promote", new_id=new_id)
        fixctl.write_back(validated, target_root)
        post = seal_target(target_root, GitPolicy(enabled=False))
        if post.digest != validated.after_seal:
            raise ControllerError(
                "promotion aborted: write-back did not reproduce the verified post-FIX seal "
                f"(expected {validated.after_seal!r}, found {post.digest!r}); the target may now "
                "be partially written -- inspect it before retrying"
            )
        return PromotionRecord(covered_ids=validated.bound_ids, after_seal=validated.after_seal)

    # --- explicit fail-closed tripwire for the still-deferred Task-9 work ----
    #
    # MutationResult persistence needs a new canonical home in artifacts.py/
    # state.py (both frozen boundaries here). It exists as a loud fail-closed
    # stub -- never a silent no-op -- so a real run stops with a clear
    # diagnostic instead of quietly skipping the deferred work before a later
    # task lands (team-lead ruling: "fail closed on any of these").

    def record_mutation_result(self, *_args, **_kwargs) -> "RunState":
        """DEFERRED to Task 9: give ``evidence.MutationResult`` a durable
        canonical home + a path to final-readiness/report. state.py was frozen in
        Task 7 (carry-forward (c)); there is no kernel op to persist it here.
        """
        raise ControllerError(
            "MutationResult has no durable canonical home yet (state.py frozen "
            "since Task 7); persisting it is deferred to Task 9"
        )

    # --- final-readiness challenge and CLOSE ---

    def run_final_challenge(
        self,
        run_state: RunState,
        *,
        final_challenger: Callable[[], ValidatedRoleArtifact],
        new_id: Callable[[], str] = _new_id,
    ) -> RunState:
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        result = _dispatch_with_retry(final_challenger, on_exhausted="final-readiness challenge was malformed twice")
        if result.artifact["verdict"] == "BLOCK":
            raise ControllerError(
                "final-readiness BLOCK handling (supplemental TRIAGE) is not implemented in this task's scope"
            )
        artifact_id = new_id()
        attempt = {"status": "UPHOLD", "target_seal": seal, "source_finding_ids": [], "artifact_id": artifact_id}
        projection = {"current_seal": seal, "attempts": [attempt]}
        evidence = [_artifact(artifact_id, "final-challenge", seal, result.artifact)]
        updated = _issue(store, operation="record_final_challenge", projection=projection, evidence=evidence)
        return RunState(run_state.run_root, run_state.governing_seal, updated, "CLOSE", None)

    def close(
        self, run_state: RunState, *, promotion: "PromotionRecord | None" = None, new_id: Callable[[], str] = _new_id,
    ) -> RunState:
        """Compute the terminal verdict, with a genuine (never vacuous) seal
        comparison for both the promoted and no-FIX paths.

        ``expected_final_seal`` is always ``governing_seal``: the compact
        ``reconcile_gates`` records were logged against it (state.py's own
        gates-recompute enforces this, unconditionally), so it cannot be
        swapped for a post-FIX seal without corrupting that recompute. The
        genuineness instead comes from what decides whether ``actual_final_seal``
        is ALLOWED to echo it: a FRESH reseal of the real target, taken right
        now, independently verified against the honest reference for this run
        -- ``promotion.after_seal`` (what write-back actually proved it wrote)
        for a genuinely-promoted run, or the anchor policy's own seal for an
        untouched one. Only when that fresh reseal matches does
        ``actual_final_seal`` get to equal ``expected_final_seal``; any drift
        -- pre-existing, mid-run, or after promotion -- surfaces as a real
        mismatch, so a false merge-ready is impossible.

        A FIX_VERIFIED row not covered by ``promotion`` was verified only
        against a disposable copy; the authoritative target was never written
        for it, so it still forces NOT_CONVERGED via ``any_indeterminate``,
        independent of the seal check above (a partially-promoted batch must
        not slip through on the seal match alone).
        """
        from .seals import GitPolicy, seal_target

        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        processor = run_state.snapshot["processor_state"]
        policy = processor["derive_policy"]
        ledger_rows = processor["apply_ledger_decisions"]["rows"]
        active_areas = processor["refresh_inventory"]["active_areas"]
        gates = processor["reconcile_gates"]
        final_challenge = processor["record_final_challenge"]
        target_root = Path(processor["preflight"]["resolved_target"])

        fix_verified_ids = {r["id"] for r in ledger_rows if r["state"] == "FIX_VERIFIED"}
        promoted_ids = set(promotion.covered_ids) if promotion is not None else set()
        if not promoted_ids <= fix_verified_ids:
            raise ControllerError(
                "promotion record covers ledger ids that were never FIX_VERIFIED "
                f"({sorted(promoted_ids - fix_verified_ids)}); refusing to close"
            )
        copy_only_fixes = sorted(fix_verified_ids - promoted_ids)

        if promotion is not None:
            fresh = seal_target(target_root, GitPolicy(enabled=False))
            seal_verified = fresh.digest == promotion.after_seal
        else:
            delta_policy = processor["preflight"]["delta_policy"]
            anchor_policy = GitPolicy(
                enabled=delta_policy["enabled"], base=delta_policy["base"], head=delta_policy["head"],
                include_untracked=delta_policy["include_untracked"], include_index=delta_policy["include_index"],
                git_dir_outside_target=delta_policy["git_dir_outside_target"],
            )
            fresh = seal_target(target_root, anchor_policy)
            seal_verified = fresh.digest == seal
        actual_final_seal = seal if seal_verified else fresh.digest

        reason = None
        if copy_only_fixes:
            reason = (
                "authoritative target not repaired: disposable-copy fix not promoted "
                f"to the sealed target (rows {copy_only_fixes})"
            )
        elif not seal_verified:
            reason = f"authoritative target drifted from its verified seal (found {fresh.digest!r})"

        lifecycle = {
            "confirmation": "not_required" if not policy["confirmation_required"] else "confirmed",
            "deadline_expired": False,
            "round1_triage_complete": True,
            "scheduled_reports_usable": True,
            "raw_reports_reconciled": True,
            "any_indeterminate": bool(copy_only_fixes),
            "expected_final_seal": seal,
            "actual_final_seal": actual_final_seal,
        }
        projection = {
            "lifecycle": lifecycle, "ledger": ledger_rows, "gates": gates,
            "areas": active_areas, "final_challenge": final_challenge,
        }
        evidence = [_artifact(new_id(), "close-computation", seal, {
            "lifecycle": lifecycle, "unpromoted_fix_rows": copy_only_fixes,
            "promoted_ids": sorted(promoted_ids),
        })]
        updated = _issue(store, operation="compute_terminal", projection=projection, evidence=evidence)
        stage = "INDETERMINATE" if copy_only_fixes else "COMPLETE"
        return RunState(run_state.run_root, run_state.governing_seal, updated, stage, reason)
