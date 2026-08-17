from dataclasses import asdict, dataclass
from typing import Callable

from .artifacts import ArtifactMismatch, ProjectionAuthority, TransitionEnvelope


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


Operation = Callable[[dict[str, object]], dict[str, object]]


class InputValidation(Exception):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        super().__init__("invalid operation input")
        self.issues = issues


def _failure(*issues: ValidationIssue) -> dict[str, object]:
    ordered = sorted(issues, key=lambda issue: (issue.path, issue.code))
    return {
        "schema_version": 1,
        "ok": False,
        "errors": [asdict(issue) for issue in ordered],
    }


def invalid_json_response(message: str) -> dict[str, object]:
    return _failure(ValidationIssue("$", "invalid_json", message))


def _exact_fields(
    value: dict[str, object], path: str, expected: set[str], issues: list[ValidationIssue]
) -> None:
    for key in expected - value.keys():
        issues.append(ValidationIssue(f"{path}.{key}", "missing", "field is required"))
    for key in value.keys() - expected:
        issues.append(ValidationIssue(f"{path}.{key}", "unknown", "field is not allowed"))


def _fields(
    value: dict[str, object],
    path: str,
    required: set[str],
    optional: set[str],
    issues: list[ValidationIssue],
) -> None:
    for key in required - value.keys():
        issues.append(ValidationIssue(f"{path}.{key}", "missing", "field is required"))
    for key in value.keys() - required - optional:
        issues.append(ValidationIssue(f"{path}.{key}", "unknown", "field is not allowed"))


def _strings(value: object, path: str, issues: list[ValidationIssue]) -> list[str]:
    if not isinstance(value, list):
        issues.append(ValidationIssue(path, "type", "value must be an array"))
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(
                ValidationIssue(f"{path}[{index}]", "value", "item must be a non-empty string")
            )
        elif item in result:
            issues.append(ValidationIssue(f"{path}[{index}]", "duplicate", "item is duplicated"))
        else:
            result.append(item)
    return result


def _nonempty_string(value: object, path: str, issues: list[ValidationIssue]) -> str:
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue(path, "value", "value must be a non-empty string"))
        return ""
    return value


def _union(*groups: list[str]) -> list[str]:
    result: list[str] = []
    for group in groups:
        for item in group:
            if item not in result:
                result.append(item)
    return result


TIERS = ("low", "med", "high", "max")
POLICIES: dict[str, dict[str, object]] = {
    "low": {
        "round_cap": 2,
        "normal_capability": "mid-tier",
        "specialist_threshold": "Critical",
        "multi_review_rounds": [],
    },
    "med": {
        "round_cap": 3,
        "normal_capability": "mid-tier",
        "specialist_threshold": "Important",
        "multi_review_rounds": [],
    },
    "high": {
        "round_cap": 5,
        "normal_capability": "one-above-mid",
        "specialist_threshold": "Important",
        "multi_review_rounds": [1],
    },
    "max": {
        "round_cap": 5,
        "normal_capability": "most-capable",
        "specialist_threshold": "every",
        "multi_review_rounds": [1, 2],
    },
}


def _validate_gestalt(value: object, path: str, issues: list[ValidationIssue]) -> bool:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "gestalt must be an object"))
        return False
    _exact_fields(value, path, {"decision", "factors"}, issues)
    if value.get("decision") != "+1":
        issues.append(ValidationIssue(f"{path}.decision", "value", "decision must be +1"))
    factors = value.get("factors")
    factors_valid = isinstance(factors, list) and len(factors) >= 3
    if not factors_valid:
        issues.append(
            ValidationIssue(f"{path}.factors", "value", "at least three factors are required")
        )
        return False
    for index, factor in enumerate(factors):
        factor_path = f"{path}.factors[{index}]"
        if not isinstance(factor, dict):
            issues.append(ValidationIssue(factor_path, "type", "factor must be an object"))
            factors_valid = False
            continue
        _exact_fields(factor, factor_path, {"factor", "evidence"}, issues)
        for key in ("factor", "evidence"):
            text = factor.get(key)
            if not isinstance(text, str) or not text.strip():
                issues.append(
                    ValidationIssue(f"{factor_path}.{key}", "value", f"{key} must be non-empty")
                )
                factors_valid = False
    return factors_valid and value.get("decision") == "+1"


def _derive_policy(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(payload, "$.input", {"explicit_tier", "no_confirm", "raters"}, issues)
    explicit = payload.get("explicit_tier")
    no_confirm = payload.get("no_confirm")
    raters = payload.get("raters")
    if explicit is not None and explicit not in TIERS:
        issues.append(
            ValidationIssue("$.input.explicit_tier", "value", "tier must be low, med, high, or max")
        )
    if type(no_confirm) is not bool:
        issues.append(
            ValidationIssue("$.input.no_confirm", "type", "no_confirm must be a boolean")
        )
    if not isinstance(raters, list):
        issues.append(ValidationIssue("$.input.raters", "type", "raters must be an array"))
        raters = []

    if explicit in TIERS:
        if raters:
            issues.append(
                ValidationIssue(
                    "$.input.raters", "forbidden", "explicit tier requests must not include raters"
                )
            )
        if issues:
            raise InputValidation(issues)
        tier = str(explicit)
        return {
            "tier": tier,
            "source": "explicit",
            "confirmation_required": False,
            **_policy_values(tier),
        }

    if len(raters) != 2:
        issues.append(
            ValidationIssue("$.input.raters", "count", "automatic selection requires two raters")
        )
    merged_complexity = 0
    merged_risk = 0
    gestalt = False
    for index, sample in enumerate(raters):
        path = f"$.input.raters[{index}]"
        if not isinstance(sample, dict):
            issues.append(ValidationIssue(path, "type", "rater must be an object"))
            continue
        allowed = {"complexity", "risk", "gestalt"}
        required = {"complexity", "risk"}
        for key in sample.keys() - allowed:
            issues.append(ValidationIssue(f"{path}.{key}", "unknown", "field is not allowed"))
        for key in required - sample.keys():
            issues.append(ValidationIssue(f"{path}.{key}", "missing", "field is required"))
        for key in ("complexity", "risk"):
            value = sample.get(key)
            if value not in TIERS:
                issues.append(
                    ValidationIssue(f"{path}.{key}", "value", f"{key} must be a valid tier")
                )
            else:
                if key == "complexity":
                    merged_complexity = max(merged_complexity, TIERS.index(str(value)))
                else:
                    merged_risk = max(merged_risk, TIERS.index(str(value)))
        if "gestalt" in sample:
            gestalt = _validate_gestalt(sample["gestalt"], f"{path}.gestalt", issues) or gestalt

    if issues:
        raise InputValidation(issues)
    tier_index = max(merged_complexity, merged_risk)
    if merged_complexity >= TIERS.index("high") and merged_risk >= TIERS.index("high"):
        tier_index += 1
    if gestalt:
        tier_index += 1
    tier = TIERS[min(tier_index, len(TIERS) - 1)]
    return {
        "tier": tier,
        "source": "automatic",
        "confirmation_required": tier == "max" and not no_confirm,
        **_policy_values(tier),
    }


def _policy_values(tier: str) -> dict[str, object]:
    values = dict(POLICIES[tier])
    values["multi_review_rounds"] = list(values["multi_review_rounds"])
    return values


def _derive_compact_policy(projection: dict[str, object]) -> dict[str, object]:
    """Derive policy from the issued two-axis rating projection only."""
    issues: list[ValidationIssue] = []
    _exact_fields(projection, "$.projection", {"explicit_tier", "no_confirm", "ratings"}, issues)
    explicit = projection.get("explicit_tier")
    no_confirm = projection.get("no_confirm")
    ratings = projection.get("ratings")
    if explicit is not None and explicit not in TIERS:
        issues.append(ValidationIssue("$.projection.explicit_tier", "value", "tier is invalid"))
    if type(no_confirm) is not bool:
        issues.append(ValidationIssue("$.projection.no_confirm", "type", "must be boolean"))
    if not isinstance(ratings, list):
        issues.append(ValidationIssue("$.projection.ratings", "type", "must be an array"))
        ratings = []
    if explicit in TIERS:
        if ratings:
            issues.append(ValidationIssue("$.projection.ratings", "forbidden", "explicit tier has no ratings"))
        if issues:
            raise InputValidation(issues)
        return {"tier": explicit, "source": "explicit", "confirmation_required": False, **_policy_values(explicit)}
    if len(ratings) != 2:
        issues.append(ValidationIssue("$.projection.ratings", "count", "automatic selection needs two ratings"))
    axes = {"complexity": 0, "risk": 0}
    gestalt = False
    for index, rating in enumerate(ratings):
        path = f"$.projection.ratings[{index}]"
        if not isinstance(rating, dict):
            issues.append(ValidationIssue(path, "type", "rating must be an object"))
            continue
        _exact_fields(rating, path, {"complexity", "risk", "gestalt_step"}, issues)
        for axis in axes:
            value = rating.get(axis)
            if value not in TIERS:
                issues.append(ValidationIssue(f"{path}.{axis}", "value", "axis is invalid"))
            else:
                axes[axis] = max(axes[axis], TIERS.index(str(value)))
        if type(rating.get("gestalt_step")) is not bool:
            issues.append(ValidationIssue(f"{path}.gestalt_step", "type", "must be boolean"))
        else:
            gestalt = gestalt or bool(rating["gestalt_step"])
    if issues:
        raise InputValidation(issues)
    tier_index = max(axes.values())
    if axes["complexity"] >= TIERS.index("high") and axes["risk"] >= TIERS.index("high"):
        tier_index += 1
    if gestalt:
        tier_index += 1
    tier = TIERS[min(tier_index, len(TIERS) - 1)]
    return {"tier": tier, "source": "automatic", "confirmation_required": tier == "max" and not no_confirm, **_policy_values(tier)}


CONSEQUENCES = ("Minor", "Important", "Critical")
INVALIDATOR_KEYS = {
    "surface_changed",
    "dependency_changed",
    "contract_changed",
    "finding_reopened",
    "identity_changed",
    "new_depth_evidence",
}
AREA_FIELDS = {
    "id",
    "aliases",
    "consequence",
    "consequence_evidence",
    "generalist_miss",
    "surfaces",
    "surface_files",
    "charter",
}


def _validate_coverage(
    value: object, path: str, issues: list[ValidationIssue]
) -> dict[str, object]:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "coverage must be an object"))
        return {"status": "STALE"}
    status = value.get("status")
    if status == "STALE":
        _exact_fields(value, path, {"status"}, issues)
        return {"status": "STALE"}
    if status != "CURRENT":
        issues.append(ValidationIssue(f"{path}.status", "value", "status must be CURRENT or STALE"))
        return {"status": "STALE"}
    _exact_fields(
        value,
        path,
        {"status", "report_id", "seal", "owning_files", "reviewed_files"},
        issues,
    )
    report_id = _nonempty_string(value.get("report_id"), f"{path}.report_id", issues)
    seal = _nonempty_string(value.get("seal"), f"{path}.seal", issues)
    owning = _strings(value.get("owning_files"), f"{path}.owning_files", issues)
    reviewed = _strings(value.get("reviewed_files"), f"{path}.reviewed_files", issues)
    if not set(owning).issubset(reviewed):
        issues.append(
            ValidationIssue(
                f"{path}.reviewed_files", "coverage", "reviewed files must include every owning file"
            )
        )
    return {
        "status": "CURRENT",
        "report_id": report_id,
        "seal": seal,
        "owning_files": owning,
        "reviewed_files": reviewed,
    }


def _validate_area(
    value: object, path: str, issues: list[ValidationIssue], require_coverage: bool
) -> dict[str, object] | None:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "area must be an object"))
        return None
    expected = AREA_FIELDS | ({"coverage"} if require_coverage else set())
    _exact_fields(value, path, expected, issues)
    area_id = _nonempty_string(value.get("id"), f"{path}.id", issues)
    consequence = value.get("consequence")
    if consequence not in CONSEQUENCES:
        issues.append(
            ValidationIssue(f"{path}.consequence", "value", "consequence is invalid")
        )
        consequence = "Minor"
    normalized: dict[str, object] = {
        "id": area_id,
        "aliases": _strings(value.get("aliases"), f"{path}.aliases", issues),
        "consequence": consequence,
        "consequence_evidence": _strings(
            value.get("consequence_evidence"), f"{path}.consequence_evidence", issues
        ),
        "generalist_miss": _strings(
            value.get("generalist_miss"), f"{path}.generalist_miss", issues
        ),
        "surfaces": _strings(value.get("surfaces"), f"{path}.surfaces", issues),
        "surface_files": _strings(
            value.get("surface_files"), f"{path}.surface_files", issues
        ),
        "charter": _nonempty_string(value.get("charter"), f"{path}.charter", issues),
    }
    if not normalized["surfaces"]:
        issues.append(ValidationIssue(f"{path}.surfaces", "empty", "at least one surface is required"))
    if not normalized["surface_files"]:
        issues.append(
            ValidationIssue(f"{path}.surface_files", "empty", "at least one owning file is required")
        )
    if require_coverage:
        normalized["coverage"] = _validate_coverage(value.get("coverage"), f"{path}.coverage", issues)
        proof = normalized["coverage"]
        if proof["status"] == "CURRENT" and set(proof["owning_files"]) != set(
            normalized["surface_files"]
        ):
            issues.append(
                ValidationIssue(
                    f"{path}.coverage.owning_files",
                    "coverage",
                    "coverage owning files must equal the canonical surface files",
                )
            )
    return normalized


def _validate_area_list(
    value: object, path: str, issues: list[ValidationIssue], require_coverage: bool
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        issues.append(ValidationIssue(path, "type", "areas must be an array"))
        return []
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        item = _validate_area(raw, f"{path}[{index}]", issues, require_coverage)
        if item is None:
            continue
        area_id = str(item["id"])
        if area_id in seen:
            issues.append(ValidationIssue(f"{path}[{index}].id", "duplicate", "area ID is duplicated"))
        seen.add(area_id)
        result.append(item)
    return result


def _validate_priority(
    value: object, active_ids: set[str], path: str, issues: list[ValidationIssue]
) -> list[str]:
    priority = _strings(value, path, issues)
    if set(priority) != active_ids or len(priority) != len(active_ids):
        issues.append(
            ValidationIssue(path, "bijection", "priority order must name every active ID exactly once")
        )
    return priority


def _refresh_inventory(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(
        payload,
        "$.input",
        {
            "prior_areas",
            "current_areas",
            "mappings",
            "priority_order",
            "invalidators",
        },
        issues,
    )
    prior = _validate_area_list(payload.get("prior_areas"), "$.input.prior_areas", issues, True)
    current = _validate_area_list(
        payload.get("current_areas"), "$.input.current_areas", issues, False
    )
    prior_by_id = {str(item["id"]): item for item in prior}
    current_by_id = {str(item["id"]): item for item in current}
    active_ids = set(current_by_id)
    priority = _validate_priority(
        payload.get("priority_order"), active_ids, "$.input.priority_order", issues
    )

    raw_mappings = payload.get("mappings")
    if not isinstance(raw_mappings, list):
        issues.append(ValidationIssue("$.input.mappings", "type", "mappings must be an array"))
        raw_mappings = []
    mapped_prior: set[str] = set()
    lineages: dict[str, list[dict[str, object]]] = {area_id: [] for area_id in active_ids}
    successor_targets: set[str] = set()
    retired: list[dict[str, object]] = []
    for index, raw in enumerate(raw_mappings):
        path = f"$.input.mappings[{index}]"
        if not isinstance(raw, dict):
            issues.append(ValidationIssue(path, "type", "mapping must be an object"))
            continue
        resolution = raw.get("resolution")
        expected = (
            {"prior_id", "resolution", "retirement_reason"}
            if resolution == "retired"
            else {"prior_id", "resolution", "active_id"}
        )
        _exact_fields(raw, path, expected, issues)
        prior_id = _nonempty_string(raw.get("prior_id"), f"{path}.prior_id", issues)
        if prior_id not in prior_by_id:
            issues.append(ValidationIssue(f"{path}.prior_id", "unknown", "prior ID is unknown"))
            continue
        if prior_id in mapped_prior:
            issues.append(ValidationIssue(f"{path}.prior_id", "duplicate", "prior ID is mapped twice"))
        mapped_prior.add(prior_id)
        if resolution == "retired":
            reason = _nonempty_string(
                raw.get("retirement_reason"), f"{path}.retirement_reason", issues
            )
            if "\n" in reason or "\r" in reason:
                issues.append(
                    ValidationIssue(
                        f"{path}.retirement_reason", "multiline", "reason must be one line"
                    )
                )
            retired.append({**prior_by_id[prior_id], "retirement_reason": reason})
        elif resolution in {"continuing", "successor"}:
            active_id = _nonempty_string(raw.get("active_id"), f"{path}.active_id", issues)
            if active_id not in active_ids:
                issues.append(ValidationIssue(f"{path}.active_id", "unknown", "active ID is unknown"))
                continue
            if resolution == "continuing" and active_id != prior_id:
                issues.append(
                    ValidationIssue(path, "identity", "continuing mapping must preserve its ID")
                )
            if resolution == "successor":
                successor_targets.add(active_id)
            lineages[active_id].append(prior_by_id[prior_id])
        else:
            issues.append(
                ValidationIssue(f"{path}.resolution", "value", "resolution is invalid")
            )
    if mapped_prior != set(prior_by_id):
        issues.append(
            ValidationIssue("$.input.mappings", "coverage", "every prior ID must be mapped once")
        )

    raw_invalidators = payload.get("invalidators")
    if not isinstance(raw_invalidators, dict):
        issues.append(
            ValidationIssue("$.input.invalidators", "type", "invalidators must be an object")
        )
        raw_invalidators = {}
    invalidators: dict[str, dict[str, bool]] = {}
    for area_id, raw in raw_invalidators.items():
        path = f"$.input.invalidators.{area_id}"
        if area_id not in active_ids:
            issues.append(ValidationIssue(path, "unknown", "invalidator area is unknown"))
            continue
        if not isinstance(raw, dict):
            issues.append(ValidationIssue(path, "type", "invalidators must be an object"))
            continue
        _exact_fields(raw, path, INVALIDATOR_KEYS, issues)
        flags: dict[str, bool] = {}
        for key in INVALIDATOR_KEYS:
            flag = raw.get(key)
            if type(flag) is not bool:
                issues.append(ValidationIssue(f"{path}.{key}", "type", "flag must be boolean"))
                flag = False
            flags[key] = bool(flag)
        invalidators[str(area_id)] = flags

    for area_id, ancestors in lineages.items():
        if ancestors and area_id not in invalidators:
            issues.append(
                ValidationIssue(
                    f"$.input.invalidators.{area_id}",
                    "missing",
                    "every continuing or successor area requires explicit invalidator flags",
                )
            )

    if issues:
        raise InputValidation(issues)

    active: list[dict[str, object]] = []
    for area_id in priority:
        proposed = current_by_id[area_id]
        ancestors = lineages[area_id]
        consequence = max(
            [str(proposed["consequence"])] + [str(item["consequence"]) for item in ancestors],
            key=CONSEQUENCES.index,
        )
        merged: dict[str, object] = {
            "id": area_id,
            "aliases": _union(
                *[list(item["aliases"]) for item in ancestors], list(proposed["aliases"])
            ),
            "consequence": consequence,
            "consequence_evidence": _union(
                *[list(item["consequence_evidence"]) for item in ancestors],
                list(proposed["consequence_evidence"]),
            ),
            "generalist_miss": _union(
                *[list(item["generalist_miss"]) for item in ancestors],
                list(proposed["generalist_miss"]),
            ),
            "surfaces": _union(
                *[list(item["surfaces"]) for item in ancestors], list(proposed["surfaces"])
            ),
            "surface_files": _union(
                *[list(item["surface_files"]) for item in ancestors],
                list(proposed["surface_files"]),
            ),
            "charter": proposed["charter"],
        }
        retained = None
        if len(ancestors) == 1 and area_id not in successor_targets:
            retained = ancestors[0].get("coverage")
        flags = invalidators.get(area_id, {})
        if retained and retained.get("status") == "CURRENT" and not any(flags.values()):
            merged["coverage"] = retained
        else:
            merged["coverage"] = {"status": "STALE"}
        active.append(merged)
    if issues:
        raise InputValidation(issues)
    return {"active_areas": active, "retired_areas": retired, "priority_order": priority}


def _record_specialist_coverage(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(
        payload,
        "$.input",
        {"areas", "coverage_events", "target_seal", "scheduled_area_ids"},
        issues,
    )
    target_seal = _nonempty_string(
        payload.get("target_seal"), "$.input.target_seal", issues
    )
    areas = _validate_area_list(payload.get("areas"), "$.input.areas", issues, True)
    by_id = {str(area["id"]): area for area in areas}
    scheduled = _strings(
        payload.get("scheduled_area_ids"), "$.input.scheduled_area_ids", issues
    )
    for index, area_id in enumerate(scheduled):
        if area_id not in by_id:
            issues.append(
                ValidationIssue(
                    f"$.input.scheduled_area_ids[{index}]", "unknown", "scheduled area is unknown"
                )
            )
    raw_events = payload.get("coverage_events")
    if not isinstance(raw_events, list) or not raw_events:
        issues.append(
            ValidationIssue(
                "$.input.coverage_events", "count", "at least one completed report is required"
            )
        )
        raw_events = []
    updates: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(raw_events):
        path = f"$.input.coverage_events[{index}]"
        if not isinstance(raw, dict):
            issues.append(ValidationIssue(path, "type", "coverage event must be an object"))
            continue
        _exact_fields(
            raw,
            path,
            {"area_id", "report_id", "seal", "owning_files", "reviewed_files", "usable"},
            issues,
        )
        area_id = _nonempty_string(raw.get("area_id"), f"{path}.area_id", issues)
        if area_id not in by_id:
            issues.append(ValidationIssue(f"{path}.area_id", "unknown", "area ID is unknown"))
        if area_id not in scheduled:
            issues.append(
                ValidationIssue(f"{path}.area_id", "unscheduled", "coverage requires a scheduled specialist")
            )
        if area_id in updates:
            issues.append(ValidationIssue(f"{path}.area_id", "duplicate", "coverage event is duplicated"))
        if raw.get("usable") is not True:
            issues.append(
                ValidationIssue(f"{path}.usable", "value", "only completed usable reports may update coverage")
            )
        proof = _validate_coverage(
            {
                "status": "CURRENT",
                "report_id": raw.get("report_id"),
                "seal": raw.get("seal"),
                "owning_files": raw.get("owning_files"),
                "reviewed_files": raw.get("reviewed_files"),
            },
            path,
            issues,
        )
        if proof["seal"] != target_seal:
            issues.append(
                ValidationIssue(f"{path}.seal", "seal", "coverage report is bound to another target seal")
            )
        if area_id in by_id and set(proof["owning_files"]) != set(by_id[area_id]["surface_files"]):
            issues.append(
                ValidationIssue(
                    f"{path}.owning_files",
                    "coverage",
                    "coverage owning files must equal the canonical active-lineage surface files",
                )
            )
        updates[area_id] = proof
    if issues:
        raise InputValidation(issues)
    return {
        "areas": [
            {**area, "coverage": updates.get(str(area["id"]), area["coverage"])}
            for area in areas
        ]
    }


def _plan_roster(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(payload, "$.input", {"tier", "areas", "priority_order", "capacity"}, issues)
    tier = payload.get("tier")
    if tier not in TIERS:
        issues.append(ValidationIssue("$.input.tier", "value", "tier is invalid"))
    areas = _validate_area_list(payload.get("areas"), "$.input.areas", issues, True)
    by_id = {str(item["id"]): item for item in areas}
    priority = _validate_priority(
        payload.get("priority_order"), set(by_id), "$.input.priority_order", issues
    )
    capacity = payload.get("capacity")
    if type(capacity) is not int or capacity < 2:
        issues.append(
            ValidationIssue("$.input.capacity", "value", "capacity must reserve one controller slot")
        )
    if issues:
        raise InputValidation(issues)

    threshold = POLICIES[str(tier)]["specialist_threshold"]
    eligible: list[dict[str, object]] = []
    for area_id in priority:
        item = by_id[area_id]
        qualifies = tier == "max" or (
            bool(item["generalist_miss"])
            and CONSEQUENCES.index(str(item["consequence"]))
            >= CONSEQUENCES.index(str(threshold))
        )
        if qualifies and (
            item["consequence"] == "Critical" or item["coverage"]["status"] != "CURRENT"
        ):
            eligible.append(item)
    eligible.sort(key=lambda item: item["coverage"]["status"] == "CURRENT")
    roster: list[dict[str, object]] = [{"role": "holistic"}, {"role": "adversarial"}]
    roster.extend(
        {
            "role": "specialist",
            "area_id": item["id"],
            "charter": item["charter"],
            "primary_surface": item["surfaces"][0],
        }
        for item in eligible
    )
    wave_size = int(capacity) - 1
    waves = [roster[index : index + wave_size] for index in range(0, len(roster), wave_size)]
    return {"roster": roster, "waves": waves}


GATE_FIELDS = {
    "id",
    "target_seal",
    "applicability",
    "applicability_reason",
    "timing",
    "classification",
    "status",
    "command",
    "result",
    "reason",
}


def _reconcile_gates(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(payload, "$.input", {"target_seal", "gates"}, issues)
    target_seal = _nonempty_string(
        payload.get("target_seal"), "$.input.target_seal", issues
    )
    raw_gates = payload.get("gates")
    if not isinstance(raw_gates, list):
        issues.append(ValidationIssue("$.input.gates", "type", "gates must be an array"))
        raw_gates = []
    normalized: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_gates):
        path = f"$.input.gates[{index}]"
        if not isinstance(raw, dict):
            issues.append(ValidationIssue(path, "type", "gate must be an object"))
            continue
        _exact_fields(raw, path, GATE_FIELDS, issues)
        gate_id = _nonempty_string(raw.get("id"), f"{path}.id", issues)
        if gate_id in seen:
            issues.append(ValidationIssue(f"{path}.id", "duplicate", "gate ID is duplicated"))
        seen.add(gate_id)
        seal = _nonempty_string(raw.get("target_seal"), f"{path}.target_seal", issues)
        if seal != target_seal:
            issues.append(
                ValidationIssue(f"{path}.target_seal", "seal", "gate is bound to another seal")
            )
        applicability = raw.get("applicability")
        if applicability not in {"applicable", "not_applicable"}:
            issues.append(
                ValidationIssue(f"{path}.applicability", "value", "applicability is invalid")
            )
        _nonempty_string(
            raw.get("applicability_reason"), f"{path}.applicability_reason", issues
        )
        if raw.get("timing") not in {"baseline", "post_fix"}:
            issues.append(ValidationIssue(f"{path}.timing", "value", "timing is invalid"))
        if raw.get("classification") not in {"required", "supporting"}:
            issues.append(
                ValidationIssue(f"{path}.classification", "value", "classification is invalid")
            )
        status = raw.get("status")
        if status not in {"PASSED", "FAILED", "NOT_RUN"}:
            issues.append(ValidationIssue(f"{path}.status", "value", "status is invalid"))
        command = raw.get("command")
        result = raw.get("result")
        reason = raw.get("reason")
        if applicability == "not_applicable":
            if status != "NOT_RUN":
                issues.append(
                    ValidationIssue(
                        f"{path}.status", "state", "non-applicable gates cannot be executed"
                    )
                )
            if command is not None:
                issues.append(
                    ValidationIssue(f"{path}.command", "state", "non-applicable command must be null")
                )
            if result is not None:
                issues.append(
                    ValidationIssue(f"{path}.result", "state", "non-applicable result must be null")
                )
            _nonempty_string(reason, f"{path}.reason", issues)
        elif status in {"PASSED", "FAILED"}:
            _nonempty_string(command, f"{path}.command", issues)
            _nonempty_string(result, f"{path}.result", issues)
            if reason is not None:
                issues.append(
                    ValidationIssue(f"{path}.reason", "state", "executed gate reason must be null")
                )
        elif status == "NOT_RUN":
            _nonempty_string(command, f"{path}.command", issues)
            if result is not None:
                issues.append(
                    ValidationIssue(f"{path}.result", "state", "unrun gate result must be null")
                )
            _nonempty_string(reason, f"{path}.reason", issues)
        normalized.append(dict(raw))

    if issues:
        raise InputValidation(issues)
    gaps: list[str] = []
    blockers: list[str] = []
    if not normalized:
        gaps.append("no applicable evidence gates discovered")
    for item in normalized:
        gate_id = str(item["id"])
        if item["applicability"] == "not_applicable":
            gaps.append(f"gate {gate_id} not applicable: {item['reason']}")
        elif item["status"] == "NOT_RUN":
            gaps.append(f"gate {gate_id} not run: {item['reason']}")
        if item["applicability"] == "applicable" and item["status"] == "FAILED":
            blockers.append(f"gate {gate_id} failed")
        elif item["classification"] == "required" and item["status"] != "PASSED":
            blockers.append(f"required gate {gate_id} did not pass")
    executed_failure = any(
        item["applicability"] == "applicable" and item["status"] == "FAILED"
        for item in normalized
    )
    return {
        "gates": normalized,
        "evidence_gaps": gaps,
        "blocking_reasons": blockers,
        "review_may_start": not executed_failure,
        "merge_readiness_eligible": not blockers,
    }


SEVERITIES = ("Minor", "Important", "Critical")
FACTUAL_STATES = {"CONFIRMED", "PLAUSIBLE", "UNVERIFIABLE"}
LEDGER_STATES = {"OPEN", "FIX_APPLIED", "FIX_VERIFIED", "REFUTED", "INTENTIONAL"}
RAW_FIELDS = {"report_id", "finding_id", "claim", "severity", "source_locators"}
DECISION_FIELDS = {
    "id",
    "source_refs",
    "current_severity",
    "factual",
    "proposed_state",
    "evidence",
    "authority",
    "authority_proof",
    "manifest_id",
    "fix_evidence",
}
ROW_FIELDS = {
    "id",
    "reported_severity",
    "current_severity",
    "claim",
    "source_locators",
    "source_findings",
    "factual",
    "state",
    "evidence",
    "history",
    "manifest_id",
    "fix_evidence",
    "authority",
    "authority_proof",
}

AUTHORITY_PROOF_FIELDS = {"locator", "identity", "proposition", "linkage"}


def _authority_proof(
    value: object, path: str, issues: list[ValidationIssue]
) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "authority proof must be an object or null"))
        return None
    _exact_fields(value, path, AUTHORITY_PROOF_FIELDS, issues)
    return {
        key: _nonempty_string(value.get(key), f"{path}.{key}", issues)
        for key in sorted(AUTHORITY_PROOF_FIELDS)
    }


def _raw_finding(value: object, path: str, issues: list[ValidationIssue]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "raw finding must be an object"))
        return None
    _exact_fields(value, path, RAW_FIELDS, issues)
    report_id = _nonempty_string(value.get("report_id"), f"{path}.report_id", issues)
    finding_id = _nonempty_string(value.get("finding_id"), f"{path}.finding_id", issues)
    claim = _nonempty_string(value.get("claim"), f"{path}.claim", issues)
    severity = value.get("severity")
    if severity not in SEVERITIES:
        issues.append(ValidationIssue(f"{path}.severity", "value", "severity is invalid"))
        severity = "Minor"
    locators = _strings(value.get("source_locators"), f"{path}.source_locators", issues)
    if not locators:
        issues.append(
            ValidationIssue(f"{path}.source_locators", "empty", "source locators are required")
        )
    return {
        "report_id": report_id,
        "finding_id": finding_id,
        "claim": claim,
        "severity": severity,
        "source_locators": locators,
    }


def _row_evidence(
    value: object, path: str, finding_id: str, issues: list[ValidationIssue]
) -> list[object]:
    if not isinstance(value, list):
        issues.append(ValidationIssue(path, "type", "evidence must be an array"))
        return []
    result: list[object] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if isinstance(item, str) and item.strip():
            result.append(item)
        elif isinstance(item, dict):
            if item.get("kind") == "adjudication":
                _exact_fields(
                    item,
                    item_path,
                    {"kind", "seal", "fact", "linkage", "authority_identity"},
                    issues,
                )
                _adjudication_proof(item, item_path, issues, canonical=True)
            else:
                _exact_fields(item, item_path, {"finding_id", "quote", "round", "time"}, issues)
                if item.get("finding_id") != finding_id:
                    issues.append(
                        ValidationIssue(
                            f"{item_path}.finding_id", "binding", "acceptance must bind this row"
                        )
                    )
                _nonempty_string(item.get("quote"), f"{item_path}.quote", issues)
                _nonempty_string(item.get("time"), f"{item_path}.time", issues)
                if type(item.get("round")) is not int or item.get("round", 0) < 1:
                    issues.append(
                        ValidationIssue(f"{item_path}.round", "value", "round must be positive")
                    )
            result.append(dict(item))
        else:
            issues.append(
                ValidationIssue(item_path, "value", "evidence must be text or an acceptance record")
            )
    return result


def _adjudication_proof(
    value: object,
    path: str,
    issues: list[ValidationIssue],
    *,
    canonical: bool = False,
) -> dict[str, object] | None:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "adjudication evidence must be an object"))
        return None
    expected = {"seal", "fact", "linkage", "authority_identity"}
    if canonical:
        expected.add("kind")
        if value.get("kind") != "adjudication":
            issues.append(ValidationIssue(f"{path}.kind", "value", "kind must be adjudication"))
    _exact_fields(value, path, expected, issues)
    for key in ("seal", "fact", "linkage"):
        _nonempty_string(value.get(key), f"{path}.{key}", issues)
    identity = value.get("authority_identity")
    if identity is not None:
        _nonempty_string(identity, f"{path}.authority_identity", issues)
    return dict(value)


def _fix_evidence(
    value: object, path: str, issues: list[ValidationIssue]
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        issues.append(ValidationIssue(path, "type", "fix evidence must be an array"))
        return []
    result: list[dict[str, str]] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            issues.append(ValidationIssue(item_path, "type", "fix evidence must be an object"))
            continue
        _exact_fields(item, item_path, {"seal", "locator", "result"}, issues)
        result.append(
            {
                key: _nonempty_string(item.get(key), f"{item_path}.{key}", issues)
                for key in ("seal", "locator", "result")
            }
        )
    return result


def _ref(raw: dict[str, object]) -> str:
    return f"{raw['report_id']}:{raw['finding_id']}"


def _ledger_row(value: object, path: str, issues: list[ValidationIssue]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "ledger row must be an object"))
        return None
    _exact_fields(value, path, ROW_FIELDS, issues)
    item = dict(value)
    _nonempty_string(item.get("id"), f"{path}.id", issues)
    for key in ("reported_severity", "current_severity"):
        if item.get(key) not in SEVERITIES:
            issues.append(ValidationIssue(f"{path}.{key}", "value", "severity is invalid"))
    if item.get("factual") not in FACTUAL_STATES:
        issues.append(ValidationIssue(f"{path}.factual", "value", "factual state is invalid"))
    if item.get("state") not in LEDGER_STATES:
        issues.append(ValidationIssue(f"{path}.state", "value", "ledger state is invalid"))
    _nonempty_string(item.get("claim"), f"{path}.claim", issues)
    _strings(item.get("source_locators"), f"{path}.source_locators", issues)
    item["evidence"] = _row_evidence(
        item.get("evidence"), f"{path}.evidence", str(item.get("id", "")), issues
    )
    adjudication_proofs = [
        entry
        for entry in item["evidence"]
        if isinstance(entry, dict) and entry.get("kind") == "adjudication"
    ]
    item["fix_evidence"] = _fix_evidence(
        item.get("fix_evidence"), f"{path}.fix_evidence", issues
    )
    authority = item.get("authority")
    if authority not in {"none", "file", "user"}:
        issues.append(ValidationIssue(f"{path}.authority", "value", "authority is invalid"))
    item["authority_proof"] = _authority_proof(
        item.get("authority_proof"), f"{path}.authority_proof", issues
    )
    state = item.get("state")
    manifest_id = item.get("manifest_id")
    has_manifest = isinstance(manifest_id, str) and bool(manifest_id.strip())
    if state == "FIX_APPLIED" and not has_manifest:
        issues.append(ValidationIssue(f"{path}.manifest_id", "state", "FIX_APPLIED requires a manifest"))
    if state == "FIX_VERIFIED" and (
        not has_manifest or not item["fix_evidence"]
    ):
        issues.append(
            ValidationIssue(
                f"{path}.fix_evidence", "state", "FIX_VERIFIED requires a manifest and fix evidence"
            )
        )
    if state == "INTENTIONAL":
        if authority not in {"file", "user"}:
            issues.append(
                ValidationIssue(f"{path}.authority", "authority", "INTENTIONAL requires file or user authority")
            )
        if authority == "file" and item["authority_proof"] is None:
            issues.append(
                ValidationIssue(f"{path}.authority_proof", "authority", "file authority requires sealed linkage proof")
            )
        if authority == "file" and item["authority_proof"] is not None and not any(
            proof.get("authority_identity") == item["authority_proof"]["identity"]
            for proof in adjudication_proofs
        ):
            issues.append(
                ValidationIssue(
                    f"{path}.evidence",
                    "adjudication",
                    "file-authorized settlement requires retained matching adjudication proof",
                )
            )
        if authority == "user" and not any(
            isinstance(entry, dict)
            and entry.get("kind") is None
            and entry.get("finding_id") == item.get("id")
            for entry in item["evidence"]
        ):
            issues.append(
                ValidationIssue(f"{path}.evidence", "authority", "user authority requires a bound acceptance record")
            )
    elif authority != "none" or item["authority_proof"] is not None:
        issues.append(
            ValidationIssue(f"{path}.authority", "state", "authority applies only to INTENTIONAL rows")
        )
    if state == "REFUTED" and not adjudication_proofs:
        issues.append(
            ValidationIssue(
                f"{path}.evidence", "adjudication", "REFUTED requires retained adjudication proof"
            )
        )
    if (
        item.get("reported_severity") in SEVERITIES
        and item.get("current_severity") in SEVERITIES
        and SEVERITIES.index(str(item["current_severity"]))
        < SEVERITIES.index(str(item["reported_severity"]))
        and not adjudication_proofs
    ):
        issues.append(
            ValidationIssue(
                f"{path}.evidence", "adjudication", "severity downgrade requires retained adjudication proof"
            )
        )
    if not isinstance(item.get("history"), list):
        issues.append(ValidationIssue(f"{path}.history", "type", "history must be an array"))
    stored_raw = item.get("source_findings")
    if not isinstance(stored_raw, list):
        issues.append(
            ValidationIssue(f"{path}.source_findings", "type", "source findings must be an array")
        )
        item["source_findings"] = []
    else:
        normalized: list[dict[str, object]] = []
        for index, raw in enumerate(stored_raw):
            parsed = _raw_finding(raw, f"{path}.source_findings[{index}]", issues)
            if parsed:
                normalized.append(parsed)
        item["source_findings"] = normalized
    return item


def _bounce(base: dict[str, object], proposed: dict[str, object]) -> dict[str, object]:
    restored = dict(base)
    restored["history"] = list(base["history"]) + [
        {"rejected_state": proposed["state"], "reason": "adjudication bounce"}
    ]
    return restored


def _apply_ledger_decisions(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(
        payload,
        "$.input",
        {
            "rows",
            "raw_findings",
            "decisions",
            "manifests",
            "user_acceptances",
            "adjudication",
            "target_seal",
        },
        issues,
    )
    target_seal = _nonempty_string(
        payload.get("target_seal"), "$.input.target_seal", issues
    )
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list):
        issues.append(ValidationIssue("$.input.rows", "type", "rows must be an array"))
        raw_rows = []
    rows: list[dict[str, object]] = []
    rows_by_id: dict[str, dict[str, object]] = {}
    for index, value in enumerate(raw_rows):
        parsed = _ledger_row(value, f"$.input.rows[{index}]", issues)
        if not parsed:
            continue
        row_id = str(parsed["id"])
        if row_id in rows_by_id:
            issues.append(ValidationIssue(f"$.input.rows[{index}].id", "duplicate", "row ID is duplicated"))
        rows_by_id[row_id] = parsed
        rows.append(parsed)

    raw_values = payload.get("raw_findings")
    if not isinstance(raw_values, list):
        issues.append(
            ValidationIssue("$.input.raw_findings", "type", "raw findings must be an array")
        )
        raw_values = []
    findings: list[dict[str, object]] = []
    findings_by_ref: dict[str, dict[str, object]] = {}
    for index, value in enumerate(raw_values):
        parsed = _raw_finding(value, f"$.input.raw_findings[{index}]", issues)
        if not parsed:
            continue
        source_ref = _ref(parsed)
        if source_ref in findings_by_ref:
            issues.append(
                ValidationIssue(
                    f"$.input.raw_findings[{index}]", "duplicate", "raw finding is duplicated"
                )
            )
        findings_by_ref[source_ref] = parsed
        findings.append(parsed)

    for row_index, existing in enumerate(rows):
        for stored_index, stored in enumerate(existing["source_findings"]):
            source_ref = _ref(stored)
            if source_ref in findings_by_ref and findings_by_ref[source_ref] != stored:
                issues.append(
                    ValidationIssue(
                        f"$.input.rows[{row_index}].source_findings[{stored_index}]",
                        "premise",
                        "stored raw premise does not match the sealed raw finding",
                    )
                )

    manifests_value = payload.get("manifests")
    if not isinstance(manifests_value, list):
        issues.append(ValidationIssue("$.input.manifests", "type", "manifests must be an array"))
        manifests_value = []
    manifests: dict[str, str] = {}
    for index, value in enumerate(manifests_value):
        path = f"$.input.manifests[{index}]"
        if not isinstance(value, dict):
            issues.append(ValidationIssue(path, "type", "manifest must be an object"))
            continue
        _exact_fields(value, path, {"id", "finding_id"}, issues)
        manifest_id = _nonempty_string(value.get("id"), f"{path}.id", issues)
        finding_id = _nonempty_string(value.get("finding_id"), f"{path}.finding_id", issues)
        if manifest_id in manifests:
            issues.append(ValidationIssue(f"{path}.id", "duplicate", "manifest ID is duplicated"))
        manifests[manifest_id] = finding_id

    acceptance_value = payload.get("user_acceptances")
    if not isinstance(acceptance_value, list):
        issues.append(
            ValidationIssue("$.input.user_acceptances", "type", "acceptances must be an array")
        )
        acceptance_value = []
    acceptances: dict[str, dict[str, object]] = {}
    for index, value in enumerate(acceptance_value):
        path = f"$.input.user_acceptances[{index}]"
        if not isinstance(value, dict):
            issues.append(ValidationIssue(path, "type", "acceptance must be an object"))
            continue
        _exact_fields(value, path, {"finding_id", "quote", "round", "time"}, issues)
        finding_id = _nonempty_string(value.get("finding_id"), f"{path}.finding_id", issues)
        _nonempty_string(value.get("quote"), f"{path}.quote", issues)
        _nonempty_string(value.get("time"), f"{path}.time", issues)
        if type(value.get("round")) is not int or int(value.get("round", 0)) < 1:
            issues.append(ValidationIssue(f"{path}.round", "value", "round must be positive"))
        if finding_id in acceptances:
            issues.append(
                ValidationIssue(f"{path}.finding_id", "duplicate", "acceptance is duplicated")
            )
        acceptances[finding_id] = dict(value)

    decisions_value = payload.get("decisions")
    if not isinstance(decisions_value, list):
        issues.append(ValidationIssue("$.input.decisions", "type", "decisions must be an array"))
        decisions_value = []
    decisions: list[dict[str, object]] = []
    decision_ids: set[str] = set()
    mapped_refs: list[str] = []
    for index, value in enumerate(decisions_value):
        path = f"$.input.decisions[{index}]"
        if not isinstance(value, dict):
            issues.append(ValidationIssue(path, "type", "decision must be an object"))
            continue
        _exact_fields(value, path, DECISION_FIELDS, issues)
        item = dict(value)
        finding_id = _nonempty_string(item.get("id"), f"{path}.id", issues)
        if finding_id in decision_ids:
            issues.append(ValidationIssue(f"{path}.id", "duplicate", "decision ID is duplicated"))
        decision_ids.add(finding_id)
        refs = _strings(item.get("source_refs"), f"{path}.source_refs", issues)
        mapped_refs.extend(refs)
        for source_ref in refs:
            if source_ref not in findings_by_ref:
                issues.append(
                    ValidationIssue(f"{path}.source_refs", "unknown", "source reference is unknown")
                )
        if item.get("current_severity") not in SEVERITIES:
            issues.append(
                ValidationIssue(f"{path}.current_severity", "value", "severity is invalid")
            )
        if item.get("factual") not in FACTUAL_STATES:
            issues.append(ValidationIssue(f"{path}.factual", "value", "factual state is invalid"))
        if item.get("proposed_state") not in LEDGER_STATES:
            issues.append(ValidationIssue(f"{path}.proposed_state", "value", "state is invalid"))
        if item.get("authority") not in {"none", "file", "user"}:
            issues.append(ValidationIssue(f"{path}.authority", "value", "authority is invalid"))
        item["authority_proof"] = _authority_proof(
            item.get("authority_proof"), f"{path}.authority_proof", issues
        )
        item["evidence"] = _strings(item.get("evidence"), f"{path}.evidence", issues)
        item["fix_evidence"] = _fix_evidence(
            item.get("fix_evidence"), f"{path}.fix_evidence", issues
        )
        if item.get("factual") == "UNVERIFIABLE" and item.get("proposed_state") in {
            "FIX_VERIFIED",
            "REFUTED",
            "INTENTIONAL",
        }:
            issues.append(
                ValidationIssue(f"{path}.proposed_state", "settlement", "UNVERIFIABLE cannot settle")
            )
        decisions.append(item)
    if sorted(mapped_refs) != sorted(findings_by_ref) or len(mapped_refs) != len(set(mapped_refs)):
        issues.append(
            ValidationIssue(
                "$.input.decisions", "reconciliation", "every raw finding must map exactly once"
            )
        )

    if issues:
        raise InputValidation(issues)

    base_by_id = {key: dict(value) for key, value in rows_by_id.items()}
    proposed_by_id = {key: dict(value) for key, value in rows_by_id.items()}
    ordered_ids = [str(item["id"]) for item in rows]
    pending: list[str] = []
    for item in decisions:
        finding_id = str(item["id"])
        sources = [findings_by_ref[source_ref] for source_ref in item["source_refs"]]
        existing = rows_by_id.get(finding_id)
        if existing is None:
            if finding_id not in ordered_ids:
                ordered_ids.append(finding_id)
            reported = max((str(source["severity"]) for source in sources), key=SEVERITIES.index)
            base = {
                "id": finding_id,
                "reported_severity": reported,
                "current_severity": reported,
                "claim": sources[0]["claim"],
                "source_locators": _union(*[list(source["source_locators"]) for source in sources]),
                "source_findings": sources,
                "factual": item["factual"],
                "state": "OPEN",
                "evidence": list(item["evidence"]),
                "history": [],
                "manifest_id": None,
                "fix_evidence": [],
                "authority": "none",
                "authority_proof": None,
            }
        else:
            base = dict(existing)
            combined_sources = list(existing["source_findings"])
            known_refs = {_ref(source) for source in combined_sources}
            combined_sources.extend(source for source in sources if _ref(source) not in known_refs)
            base["source_findings"] = combined_sources
            base["source_locators"] = _union(
                list(existing["source_locators"]),
                *[list(source["source_locators"]) for source in sources],
            )
            base["reported_severity"] = max(
                [str(existing["reported_severity"])] + [str(source["severity"]) for source in sources],
                key=SEVERITIES.index,
            )
        base_by_id[finding_id] = base
        proposed = dict(base)
        proposed_state = str(item["proposed_state"])
        previous_state = str(base["state"])
        settled_states = {"FIX_VERIFIED", "REFUTED", "INTENTIONAL"}
        if (
            previous_state in settled_states
            and proposed_state in settled_states
            and proposed_state != previous_state
        ):
            issues.append(
                ValidationIssue(
                    f"$.input.decisions.{finding_id}.proposed_state",
                    "transition",
                    "a settled row must reopen before changing settlement",
                )
            )
        if proposed_state == "FIX_APPLIED":
            manifest_id = item.get("manifest_id")
            if previous_state != "OPEN" or not isinstance(manifest_id, str) or manifests.get(
                manifest_id
            ) != finding_id:
                issues.append(
                    ValidationIssue(
                        f"$.input.decisions.{finding_id}.manifest_id",
                        "transition",
                        "FIX_APPLIED requires a matching manifest from OPEN",
                    )
                )
        if proposed_state == "FIX_VERIFIED":
            manifest_id = item.get("manifest_id")
            if (
                previous_state != "FIX_APPLIED"
                or manifest_id != base.get("manifest_id")
                or manifests.get(str(manifest_id)) != finding_id
                or not item["fix_evidence"]
                or any(proof["seal"] != target_seal for proof in item["fix_evidence"])
            ):
                issues.append(
                    ValidationIssue(
                        f"$.input.decisions.{finding_id}.fix_evidence",
                        "transition",
                        "FIX_VERIFIED requires matching manifest and current-seal fix evidence",
                    )
                )
        if previous_state in {"FIX_VERIFIED", "REFUTED", "INTENTIONAL"} and proposed_state == "OPEN":
            proposed["history"] = list(base["history"]) + [
                {"rejected_state": previous_state, "reason": "basis invalidated"}
            ]
        proposed.update(
            {
                "current_severity": item["current_severity"],
                "factual": item["factual"],
                "state": proposed_state,
                "evidence": list(item["evidence"]),
                "manifest_id": item.get("manifest_id"),
                "fix_evidence": list(item["fix_evidence"]),
                "authority": item["authority"],
                "authority_proof": item["authority_proof"],
            }
        )
        direct_user = (
            proposed_state == "INTENTIONAL"
            and item["authority"] == "user"
            and finding_id in acceptances
        )
        if proposed_state == "INTENTIONAL" and item["authority"] == "user" and not direct_user:
            issues.append(
                ValidationIssue(
                    f"$.input.decisions.{finding_id}.authority",
                    "authority",
                    "user authority requires a ledger-bound acceptance",
                )
            )
        if proposed_state == "INTENTIONAL" and item["authority"] == "file" and item["authority_proof"] is None:
            issues.append(
                ValidationIssue(
                    f"$.input.decisions.{finding_id}.authority_proof",
                    "authority",
                    "file authority requires exact sealed locator, identity, proposition, and linkage",
                )
            )
        if proposed_state == "INTENTIONAL" and item["authority"] == "none":
            issues.append(
                ValidationIssue(
                    f"$.input.decisions.{finding_id}.authority",
                    "authority",
                    "INTENTIONAL requires file or user authority",
                )
            )
        if proposed_state != "INTENTIONAL" and (
            item["authority"] != "none" or item["authority_proof"] is not None
        ):
            issues.append(
                ValidationIssue(
                    f"$.input.decisions.{finding_id}.authority",
                    "state",
                    "authority applies only to INTENTIONAL decisions",
                )
            )
        if direct_user:
            proposed["evidence"] = list(proposed["evidence"]) + [acceptances[finding_id]]
        green = proposed_state in {"REFUTED", "INTENTIONAL"} and not direct_user
        downgraded = (
            SEVERITIES.index(str(proposed["reported_severity"])) >= SEVERITIES.index("Important")
            and SEVERITIES.index(str(proposed["current_severity"]))
            < SEVERITIES.index(str(proposed["reported_severity"]))
        )
        if green or downgraded:
            pending.append(finding_id)
        proposed_by_id[finding_id] = proposed

    if issues:
        raise InputValidation(issues)

    operative = dict(proposed_by_id)
    next_attempt: dict[str, object] | None = None
    adjudication_value = payload.get("adjudication")
    pending_set = set(pending)
    if pending and adjudication_value is None:
        for finding_id in pending:
            operative[finding_id] = base_by_id[finding_id]
        next_attempt = {
            "original_expected_ids": pending,
            "attempt_number": 1,
            "retry_mode": "full",
            "settled_decisions": [],
            "pending_ids": pending,
        }
    elif pending:
        if not isinstance(adjudication_value, dict):
            raise InputValidation(
                [ValidationIssue("$.input.adjudication", "type", "adjudication must be an object")]
            )
        path = "$.input.adjudication"
        _exact_fields(
            adjudication_value,
            path,
            {
                "original_expected_ids",
                "attempt_number",
                "retry_mode",
                "settled_decisions",
                "pending_ids",
                "outcome",
            },
            issues,
        )
        original = _strings(
            adjudication_value.get("original_expected_ids"), f"{path}.original_expected_ids", issues
        )
        pending_ids = _strings(adjudication_value.get("pending_ids"), f"{path}.pending_ids", issues)
        attempt_number = adjudication_value.get("attempt_number")
        mode = adjudication_value.get("retry_mode")
        if attempt_number not in {1, 2}:
            issues.append(ValidationIssue(f"{path}.attempt_number", "value", "attempt must be 1 or 2"))
        if mode not in {"full", "undecided_subset"}:
            issues.append(ValidationIssue(f"{path}.retry_mode", "value", "retry mode is invalid"))

        def parse_adjudication_decisions(value: object, decision_path: str) -> list[dict[str, object]]:
            if not isinstance(value, list):
                issues.append(ValidationIssue(decision_path, "type", "decisions must be an array"))
                return []
            parsed: list[dict[str, object]] = []
            seen_ids: set[str] = set()
            for index, raw_decision in enumerate(value):
                item_path = f"{decision_path}[{index}]"
                if not isinstance(raw_decision, dict):
                    issues.append(ValidationIssue(item_path, "type", "decision must be an object"))
                    continue
                _exact_fields(raw_decision, item_path, {"id", "decision", "evidence"}, issues)
                item_id = _nonempty_string(raw_decision.get("id"), f"{item_path}.id", issues)
                if item_id in seen_ids:
                    issues.append(ValidationIssue(f"{item_path}.id", "duplicate", "ID is duplicated"))
                seen_ids.add(item_id)
                if raw_decision.get("decision") not in {"UPHOLD", "BOUNCE", "UNDECIDED"}:
                    issues.append(ValidationIssue(f"{item_path}.decision", "value", "decision is invalid"))
                proof = _adjudication_proof(
                    raw_decision.get("evidence"), f"{item_path}.evidence", issues
                )
                if proof is not None and proof.get("seal") != target_seal:
                    issues.append(
                        ValidationIssue(
                            f"{item_path}.evidence.seal",
                            "seal",
                            "adjudication evidence is bound to another target seal",
                        )
                    )
                parsed_item = dict(raw_decision)
                parsed_item["evidence"] = proof
                parsed.append(parsed_item)
            return parsed

        settled = parse_adjudication_decisions(
            adjudication_value.get("settled_decisions"), f"{path}.settled_decisions"
        )
        if any(item["decision"] == "UNDECIDED" for item in settled):
            issues.append(
                ValidationIssue(f"{path}.settled_decisions", "state", "settled decisions cannot be undecided")
            )
        settled_ids = {str(item["id"]) for item in settled}
        if set(original) != pending_set:
            issues.append(
                ValidationIssue(f"{path}.original_expected_ids", "set", "expected IDs do not match")
            )
        if settled_ids & set(pending_ids) or settled_ids | set(pending_ids) != set(original):
            issues.append(
                ValidationIssue(path, "partition", "settled and pending IDs must partition original IDs")
            )
        if attempt_number == 1 and (mode != "full" or settled or set(pending_ids) != set(original)):
            issues.append(ValidationIssue(path, "attempt", "first attempt must cover the full set"))
        if attempt_number == 2 and mode == "full" and (settled or set(pending_ids) != set(original)):
            issues.append(ValidationIssue(path, "attempt", "full retry must cover the full set"))
        outcome_value = adjudication_value.get("outcome")
        if not isinstance(outcome_value, dict):
            issues.append(ValidationIssue(f"{path}.outcome", "type", "outcome must be an object"))
            outcome_value = {"status": "failed", "decisions": []}
        _exact_fields(outcome_value, f"{path}.outcome", {"status", "decisions"}, issues)
        status = outcome_value.get("status")
        if status not in {"clean", "failed"}:
            issues.append(ValidationIssue(f"{path}.outcome.status", "value", "status is invalid"))
        call_decisions = parse_adjudication_decisions(
            outcome_value.get("decisions"), f"{path}.outcome.decisions"
        )
        if status == "failed" and call_decisions:
            issues.append(
                ValidationIssue(f"{path}.outcome.decisions", "state", "failed output is discarded")
            )
        if status == "clean" and {str(item["id"]) for item in call_decisions} != set(pending_ids):
            issues.append(
                ValidationIssue(f"{path}.outcome.decisions", "set", "clean call must decide every pending ID")
            )
        for item in settled + call_decisions:
            finding_id = str(item["id"])
            proposed = proposed_by_id.get(finding_id)
            proof = item.get("evidence")
            if item.get("decision") != "UPHOLD" or not proposed or not isinstance(proof, dict):
                continue
            authority_identity = proof.get("authority_identity")
            if proposed["state"] == "INTENTIONAL" and proposed["authority"] == "file":
                expected_identity = proposed["authority_proof"]["identity"]
                if authority_identity != expected_identity:
                    issues.append(
                        ValidationIssue(
                            f"{path}.outcome.decisions",
                            "authority",
                            "file-authority uphold must repeat the exact authority identity",
                        )
                    )
            elif authority_identity is not None:
                issues.append(
                    ValidationIssue(
                        f"{path}.outcome.decisions",
                        "authority",
                        "non-file disposition cannot claim an authority identity",
                    )
                )
        if issues:
            raise InputValidation(issues)

        def uphold(finding_id: str, decision: dict[str, object]) -> dict[str, object]:
            accepted = dict(proposed_by_id[finding_id])
            proof = {"kind": "adjudication", **dict(decision["evidence"])}
            accepted["evidence"] = list(accepted["evidence"]) + [proof]
            return accepted

        for finding_id in pending:
            operative[finding_id] = base_by_id[finding_id]
        for item in settled:
            finding_id = str(item["id"])
            operative[finding_id] = (
                uphold(finding_id, item)
                if item["decision"] == "UPHOLD"
                else _bounce(base_by_id[finding_id], proposed_by_id[finding_id])
            )
        if status == "failed":
            if attempt_number == 1:
                next_attempt = {
                    "original_expected_ids": original,
                    "attempt_number": 2,
                    "retry_mode": "full",
                    "settled_decisions": [],
                    "pending_ids": original,
                }
            else:
                for finding_id in pending_ids:
                    operative[finding_id] = _bounce(
                        base_by_id[finding_id], proposed_by_id[finding_id]
                    )
        else:
            undecided: list[str] = []
            first_settled = list(settled)
            for item in call_decisions:
                finding_id = str(item["id"])
                if item["decision"] == "UPHOLD":
                    operative[finding_id] = uphold(finding_id, item)
                    first_settled.append(item)
                elif item["decision"] == "BOUNCE":
                    operative[finding_id] = _bounce(
                        base_by_id[finding_id], proposed_by_id[finding_id]
                    )
                    first_settled.append(item)
                elif attempt_number == 1:
                    undecided.append(finding_id)
                else:
                    operative[finding_id] = _bounce(
                        base_by_id[finding_id], proposed_by_id[finding_id]
                    )
            if attempt_number == 1 and undecided:
                next_attempt = {
                    "original_expected_ids": original,
                    "attempt_number": 2,
                    "retry_mode": "undecided_subset",
                    "settled_decisions": first_settled,
                    "pending_ids": undecided,
                }
    elif adjudication_value is not None:
        raise InputValidation(
            [ValidationIssue("$.input.adjudication", "unexpected", "no adjudication is pending")]
        )

    final_rows = [operative[finding_id] for finding_id in ordered_ids]
    return {
        "rows": final_rows,
        "rejected_dispositions": [
            history
            for item in final_rows
            for history in item["history"]
            if isinstance(history, dict) and "rejected_state" in history
        ],
        "pending_fix_ids": [
            str(item["id"]) for item in final_rows if item["state"] in {"OPEN", "FIX_APPLIED"}
        ],
        "round_indeterminate": False,
        "next_adjudication": next_attempt,
    }


CHALLENGE_ATTEMPT_FIELDS = {
    "status",
    "target_seal",
    "material",
    "reason",
    "source_finding_ids",
    "failure_kind",
}
CHALLENGE_RESULT_FIELDS = {
    "state",
    "fresh",
    "target_seal",
    "source_finding_ids",
    "procedural_block",
    "reason",
    "retry_required",
}


def _record_final_challenge(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(payload, "$.input", {"current_seal", "attempts"}, issues)
    current_seal = _nonempty_string(
        payload.get("current_seal"), "$.input.current_seal", issues
    )
    raw_attempts = payload.get("attempts")
    if not isinstance(raw_attempts, list) or not 1 <= len(raw_attempts) <= 2:
        issues.append(
            ValidationIssue("$.input.attempts", "count", "one or two attempts are required")
        )
        raw_attempts = []
    attempts: list[dict[str, object]] = []
    for index, raw in enumerate(raw_attempts):
        path = f"$.input.attempts[{index}]"
        if not isinstance(raw, dict):
            issues.append(ValidationIssue(path, "type", "attempt must be an object"))
            continue
        _exact_fields(raw, path, CHALLENGE_ATTEMPT_FIELDS, issues)
        item = dict(raw)
        status = item.get("status")
        if status not in {"UPHOLD", "BLOCK", "FAILED"}:
            issues.append(ValidationIssue(f"{path}.status", "value", "status is invalid"))
        _nonempty_string(item.get("target_seal"), f"{path}.target_seal", issues)
        if type(item.get("material")) is not bool:
            issues.append(ValidationIssue(f"{path}.material", "type", "material must be boolean"))
        item["source_finding_ids"] = _strings(
            item.get("source_finding_ids"), f"{path}.source_finding_ids", issues
        )
        if status == "UPHOLD":
            if item.get("material") or item.get("reason") is not None or item.get("failure_kind") is not None:
                issues.append(ValidationIssue(path, "state", "UPHOLD cannot carry block or failure state"))
        elif status == "BLOCK":
            if item.get("material") is not True:
                issues.append(ValidationIssue(f"{path}.material", "value", "BLOCK must be material"))
            _nonempty_string(item.get("reason"), f"{path}.reason", issues)
            if item.get("failure_kind") is not None:
                issues.append(ValidationIssue(f"{path}.failure_kind", "state", "BLOCK is not a call failure"))
        elif status == "FAILED":
            if item.get("material") or item["source_finding_ids"]:
                issues.append(ValidationIssue(path, "state", "failed calls have no operative decision"))
            _nonempty_string(item.get("reason"), f"{path}.reason", issues)
            if item.get("failure_kind") not in {"failed", "malformed"}:
                issues.append(
                    ValidationIssue(f"{path}.failure_kind", "value", "failure kind is invalid")
                )
        attempts.append(item)
    if len(attempts) == 2 and attempts[0].get("status") != "FAILED":
        issues.append(
            ValidationIssue("$.input.attempts[1]", "unexpected", "retry follows only a failed call")
        )
    if issues:
        raise InputValidation(issues)

    last = attempts[-1]
    source_ids = list(last["source_finding_ids"])
    base = {
        "fresh": True,
        "target_seal": last["target_seal"],
        "source_finding_ids": source_ids,
        "procedural_block": False,
        "reason": last["reason"],
        "retry_required": False,
    }
    if any(item["target_seal"] != current_seal for item in attempts):
        return {"state": "STALE", **base, "fresh": False}
    if last["status"] == "FAILED":
        if len(attempts) == 1:
            return {"state": "RETRY_REQUIRED", **base, "retry_required": True}
        return {"state": "INDETERMINATE", **base}
    if source_ids:
        return {"state": "NEEDS_TRIAGE", **base}
    if last["status"] == "BLOCK":
        return {"state": "BLOCKED", **base, "procedural_block": True}
    return {"state": "UPHELD", **base, "reason": None}


LIFECYCLE_FIELDS = {
    "confirmation",
    "deadline_expired",
    "round1_triage_complete",
    "scheduled_reports_usable",
    "raw_reports_reconciled",
    "any_indeterminate",
    "expected_final_seal",
    "actual_final_seal",
}
GATE_RESULT_FIELDS = {
    "gates",
    "evidence_gaps",
    "blocking_reasons",
    "review_may_start",
    "merge_readiness_eligible",
}


def _validate_challenge_result(
    challenge: dict[str, object], path: str, issues: list[ValidationIssue]
) -> None:
    state = challenge.get("state")
    fresh = challenge.get("fresh")
    sources = challenge.get("source_finding_ids")
    procedural = challenge.get("procedural_block")
    reason = challenge.get("reason")
    retry = challenge.get("retry_required")
    invalid = False
    if state == "UPHELD":
        invalid = not fresh or bool(sources) or bool(procedural) or reason is not None or bool(retry)
    elif state == "BLOCKED":
        invalid = not fresh or bool(sources) or procedural is not True or not isinstance(reason, str) or bool(retry)
    elif state == "NEEDS_TRIAGE":
        invalid = not fresh or not bool(sources) or bool(procedural) or bool(retry)
    elif state == "RETRY_REQUIRED":
        invalid = not fresh or bool(sources) or bool(procedural) or not isinstance(reason, str) or retry is not True
    elif state == "INDETERMINATE":
        invalid = not fresh or bool(sources) or bool(procedural) or not isinstance(reason, str) or bool(retry)
    elif state == "STALE":
        invalid = fresh is not False or bool(retry)
    if invalid:
        issues.append(
            ValidationIssue(path, "state", "challenge fields are inconsistent with its state")
        )


def _compute_terminal(payload: dict[str, object]) -> dict[str, object]:
    issues: list[ValidationIssue] = []
    _exact_fields(
        payload, "$.input", {"lifecycle", "ledger", "gates", "areas", "final_challenge"}, issues
    )
    lifecycle = payload.get("lifecycle")
    if not isinstance(lifecycle, dict):
        issues.append(ValidationIssue("$.input.lifecycle", "type", "lifecycle must be an object"))
        lifecycle = {}
    _exact_fields(lifecycle, "$.input.lifecycle", LIFECYCLE_FIELDS, issues)
    if lifecycle.get("confirmation") not in {"not_required", "accepted", "declined", "awaiting"}:
        issues.append(
            ValidationIssue("$.input.lifecycle.confirmation", "value", "confirmation is invalid")
        )
    for key in (
        "deadline_expired",
        "round1_triage_complete",
        "scheduled_reports_usable",
        "raw_reports_reconciled",
        "any_indeterminate",
    ):
        if type(lifecycle.get(key)) is not bool:
            issues.append(ValidationIssue(f"$.input.lifecycle.{key}", "type", "field must be boolean"))
    expected_seal = _nonempty_string(
        lifecycle.get("expected_final_seal"), "$.input.lifecycle.expected_final_seal", issues
    )
    actual_seal = _nonempty_string(
        lifecycle.get("actual_final_seal"), "$.input.lifecycle.actual_final_seal", issues
    )

    raw_ledger = payload.get("ledger")
    if not isinstance(raw_ledger, list):
        issues.append(ValidationIssue("$.input.ledger", "type", "ledger must be an array"))
        raw_ledger = []
    ledger: list[dict[str, object]] = []
    ledger_ids: set[str] = set()
    for index, raw in enumerate(raw_ledger):
        parsed = _ledger_row(raw, f"$.input.ledger[{index}]", issues)
        if parsed:
            row_id = str(parsed["id"])
            if row_id in ledger_ids:
                issues.append(ValidationIssue(f"$.input.ledger[{index}].id", "duplicate", "row ID is duplicated"))
            ledger_ids.add(row_id)
            ledger.append(parsed)

    gates = payload.get("gates")
    if not isinstance(gates, dict):
        issues.append(ValidationIssue("$.input.gates", "type", "gates must be an object"))
        gates = {}
    _exact_fields(gates, "$.input.gates", GATE_RESULT_FIELDS, issues)
    if not isinstance(gates.get("gates"), list):
        issues.append(ValidationIssue("$.input.gates.gates", "type", "gates must be an array"))
    evidence_gaps = _strings(
        gates.get("evidence_gaps"), "$.input.gates.evidence_gaps", issues
    )
    gate_blockers = _strings(
        gates.get("blocking_reasons"), "$.input.gates.blocking_reasons", issues
    )
    for key in ("review_may_start", "merge_readiness_eligible"):
        if type(gates.get(key)) is not bool:
            issues.append(ValidationIssue(f"$.input.gates.{key}", "type", "field must be boolean"))

    areas = _validate_area_list(payload.get("areas"), "$.input.areas", issues, True)
    challenge = payload.get("final_challenge")
    if not isinstance(challenge, dict):
        issues.append(
            ValidationIssue("$.input.final_challenge", "type", "challenge must be an object")
        )
        challenge = {}
    _exact_fields(challenge, "$.input.final_challenge", CHALLENGE_RESULT_FIELDS, issues)
    if challenge.get("state") not in {
        "UPHELD",
        "BLOCKED",
        "NEEDS_TRIAGE",
        "RETRY_REQUIRED",
        "INDETERMINATE",
        "STALE",
    }:
        issues.append(ValidationIssue("$.input.final_challenge.state", "value", "state is invalid"))
    for key in ("fresh", "procedural_block", "retry_required"):
        if type(challenge.get(key)) is not bool:
            issues.append(
                ValidationIssue(f"$.input.final_challenge.{key}", "type", "field must be boolean")
            )
    _nonempty_string(
        challenge.get("target_seal"), "$.input.final_challenge.target_seal", issues
    )
    _strings(
        challenge.get("source_finding_ids"),
        "$.input.final_challenge.source_finding_ids",
        issues,
    )
    if challenge.get("reason") is not None:
        _nonempty_string(challenge.get("reason"), "$.input.final_challenge.reason", issues)
    _validate_challenge_result(challenge, "$.input.final_challenge", issues)
    if issues:
        raise InputValidation(issues)

    derived_gates = _reconcile_gates(
        {"target_seal": actual_seal, "gates": gates["gates"]}
    )
    if gates != derived_gates:
        raise InputValidation(
            [
                ValidationIssue(
                    "$.input.gates",
                    "consistency",
                    "gate rollup must equal the deterministic result derived from its records",
                )
            ]
        )
    evidence_gaps = list(derived_gates["evidence_gaps"])
    gate_blockers = list(derived_gates["blocking_reasons"])

    limitations = list(evidence_gaps)
    limitations.extend(
        f"open Minor row {row['id']}"
        for row in ledger
        if row["current_severity"] == "Minor" and row["state"] in {"OPEN", "FIX_APPLIED"}
    )
    if lifecycle["confirmation"] == "declined" and not lifecycle["deadline_expired"]:
        return {
            "lifecycle_outcome": "CANCELLED_BEFORE_REVIEW",
            "terminal_verdict": None,
            "merge_ready": None,
            "qualified_claim_eligible": False,
            "failed_conditions": [],
            "limitations": limitations,
        }

    convergence_failures: list[str] = []
    if lifecycle["deadline_expired"]:
        convergence_failures.append("deadline expired")
    if lifecycle["confirmation"] not in {"not_required", "accepted"}:
        convergence_failures.append("required confirmation was not accepted")
    if not lifecycle["round1_triage_complete"]:
        convergence_failures.append("Round 1 did not complete through TRIAGE")
    if not lifecycle["scheduled_reports_usable"]:
        convergence_failures.append("not every scheduled report was usable")
    if not lifecycle["raw_reports_reconciled"]:
        convergence_failures.append("raw reports were not fully reconciled")
    if lifecycle["any_indeterminate"]:
        convergence_failures.append("a lifecycle stage is INDETERMINATE")
    if expected_seal != actual_seal:
        convergence_failures.append("final target seal does not match")
    for row in ledger:
        if (
            SEVERITIES.index(str(row["current_severity"])) >= SEVERITIES.index("Important")
            and row["state"] in {"OPEN", "FIX_APPLIED"}
        ):
            convergence_failures.append(f"Important+ row {row['id']} remains {row['state']}")

    converged = not convergence_failures
    readiness_failures = list(convergence_failures)
    challenge_upheld = (
        challenge["state"] == "UPHELD"
        and challenge["fresh"]
        and challenge["target_seal"] == actual_seal
    )
    if not challenge_upheld:
        detail = f": {challenge['reason']}" if challenge.get("reason") else ""
        readiness_failures.append(f"final challenge did not uphold the final seal{detail}")
    if not derived_gates["merge_readiness_eligible"]:
        readiness_failures.extend(gate_blockers or ["evidence gate conditions were not satisfied"])
    for row in ledger:
        if (
            SEVERITIES.index(str(row["current_severity"])) >= SEVERITIES.index("Important")
            and row["state"] not in {"FIX_VERIFIED", "REFUTED", "INTENTIONAL"}
        ):
            reason = f"Important+ row {row['id']} is not settled"
            if reason not in readiness_failures:
                readiness_failures.append(reason)
    for area in areas:
        if (
            CONSEQUENCES.index(str(area["consequence"])) >= CONSEQUENCES.index("Important")
            and area["generalist_miss"]
            and area["coverage"]["status"] != "CURRENT"
        ):
            readiness_failures.append(f"specialist coverage blocker for area {area['id']}")

    merge_ready = converged and not readiness_failures
    return {
        "lifecycle_outcome": "CONVERGED" if converged else "NOT_CONVERGED",
        "terminal_verdict": "CONVERGED" if converged else "NOT_CONVERGED",
        "merge_ready": merge_ready,
        "qualified_claim_eligible": merge_ready,
        "failed_conditions": readiness_failures,
        "limitations": limitations,
    }


OPERATIONS: dict[str, Operation] = {
    "derive_policy": _derive_policy,
    "refresh_inventory": _refresh_inventory,
    "record_specialist_coverage": _record_specialist_coverage,
    "plan_roster": _plan_roster,
    "reconcile_gates": _reconcile_gates,
    "apply_ledger_decisions": _apply_ledger_decisions,
    "record_final_challenge": _record_final_challenge,
    "compute_terminal": _compute_terminal,
}


def apply(
    envelope: TransitionEnvelope,
    snapshot: dict[str, object],
    authority: ProjectionAuthority,
) -> dict[str, object]:
    """Apply one issued compact projection to an in-memory canonical snapshot.

    The controller creates the authority from the persisted snapshot.  This
    function deliberately accepts no caller-authored registry fragments.
    """
    if not isinstance(authority, ProjectionAuthority):
        raise ArtifactMismatch("state transitions require canonical projection authority")
    authority.validate(envelope, snapshot)
    operation = OPERATIONS.get(envelope.operation)
    if operation is None:
        raise ArtifactMismatch("unknown issued transition operation")
    projection = envelope.projection
    try:
        result = _derive_compact_policy(projection) if envelope.operation == "derive_policy" else operation(projection)
    except InputValidation as exc:
        raise ArtifactMismatch("issued projection is invalid for its operation") from exc
    updated = dict(snapshot)
    processor_state = dict(snapshot.get("processor_state", {}))
    processor_state[envelope.operation] = result
    updated["processor_state"] = processor_state
    return updated


def process_test_fixture(request: object) -> dict[str, object]:
    """Legacy test adapter for processor unit fixtures only.

    Production transitions enter through :func:`apply`, with authority created
    by the controller from persisted canonical state.  This adapter is kept
    deliberately out of the package exports and CLI's normal invocation.
    """
    if not isinstance(request, dict):
        return _failure(ValidationIssue("$", "type", "request must be an object"))

    issues: list[ValidationIssue] = []
    expected = {"schema_version", "operation", "input"}
    for key in expected - request.keys():
        issues.append(ValidationIssue(f"$.{key}", "missing", "field is required"))
    for key in request.keys() - expected:
        issues.append(ValidationIssue(f"$.{key}", "unknown", "field is not allowed"))

    version = request.get("schema_version")
    if "schema_version" in request and (type(version) is not int or version != 1):
        issues.append(
            ValidationIssue("$.schema_version", "unsupported", "schema_version must be 1")
        )

    operation = request.get("operation")
    if "operation" in request:
        if not isinstance(operation, str):
            issues.append(ValidationIssue("$.operation", "type", "operation must be a string"))
        elif operation not in OPERATIONS:
            issues.append(ValidationIssue("$.operation", "unknown", "operation is not supported"))

    payload = request.get("input")
    if "input" in request and not isinstance(payload, dict):
        issues.append(ValidationIssue("$.input", "type", "input must be an object"))

    if issues:
        return _failure(*issues)

    assert isinstance(operation, str)
    assert isinstance(payload, dict)
    try:
        result = OPERATIONS[operation](payload)
    except InputValidation as exc:
        return _failure(*exc.issues)
    return {"schema_version": 1, "ok": True, "result": result}
