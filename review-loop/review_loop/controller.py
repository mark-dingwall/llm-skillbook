"""Run preflight: sealing, ground truth, profile selection, persisted intent.

Resolves invocation intent into a persisted run before any semantic
dispatch (design Sec. 4, "Preflight and Stage 0"). No reviewer, evidence
scout, or FIX agent is dispatched here.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .artifacts import CanonicalStore
from .profiles import InvocationIntent, ProfileError, ReviewProfile, RolePins, load_profile
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


@dataclass(frozen=True)
class RunState:
    run_root: Path
    governing_seal: str
    snapshot: dict[str, object]


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
