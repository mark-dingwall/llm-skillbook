"""Pure compact state kernel.

Rich reports are validated and retained by the controller.  This module sees
only their canonical references and the fixed, state-affecting projections.
"""
from __future__ import annotations

from dataclasses import dataclass

from .artifacts import ArtifactMismatch, ProjectionAuthority, TransitionEnvelope

TIERS = ("low", "med", "high", "max")
CONSEQUENCES = ("Minor", "Important", "Critical")
POLICIES = {
    "low": (2, "mid-tier", "Critical", []),
    "med": (3, "mid-tier", "Important", []),
    "high": (5, "one-above-mid", "Important", [1]),
    "max": (5, "most-capable", "every", [1, 2]),
}
INVALIDATORS = {"surface_changed", "dependency_changed", "contract_changed", "finding_reopened", "identity_changed", "new_depth_evidence"}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


class InputValidation(Exception):
    def __init__(self, *issues: ValidationIssue) -> None:
        self.issues = list(issues)


def _require(condition: bool, path: str, message: str) -> None:
    if not condition:
        raise InputValidation(ValidationIssue(path, "value", message))


def _object(value: object, path: str, keys: set[str]) -> dict[str, object]:
    _require(isinstance(value, dict), path, "must be an object")
    assert isinstance(value, dict)
    _require(set(value) == keys, path, "has missing or unknown fields")
    return value


def _ids(value: object, path: str) -> list[str]:
    _require(isinstance(value, list) and all(isinstance(item, str) and item for item in value), path, "must contain non-empty IDs")
    assert isinstance(value, list)
    _require(len(set(value)) == len(value), path, "IDs must be unique")
    return list(value)


def _policy(tier: str, source: str, confirmation: bool) -> dict[str, object]:
    rounds, capability, threshold, multi = POLICIES[tier]
    return {"tier": tier, "source": source, "confirmation_required": confirmation, "round_cap": rounds, "normal_capability": capability, "specialist_threshold": threshold, "multi_review_rounds": multi}


def _derive(projection: dict[str, object]) -> dict[str, object]:
    data = _object(projection, "projection", {"explicit_tier", "no_confirm", "ratings"})
    explicit, no_confirm, ratings = data["explicit_tier"], data["no_confirm"], data["ratings"]
    _require(type(no_confirm) is bool, "projection.no_confirm", "must be boolean")
    _require(isinstance(ratings, list), "projection.ratings", "must be an array")
    assert isinstance(ratings, list)
    if explicit is not None:
        _require(explicit in TIERS and not ratings, "projection", "explicit tier is invalid or has ratings")
        return _policy(str(explicit), "explicit", False)
    _require(len(ratings) == 2, "projection.ratings", "automatic policy requires two ratings")
    axes = {"complexity": 0, "risk": 0}; gestalt = False
    for index, rating in enumerate(ratings):
        item = _object(rating, f"projection.ratings[{index}]", {"complexity", "risk", "gestalt_step"})
        for axis in axes:
            _require(item[axis] in TIERS, f"projection.ratings[{index}].{axis}", "tier is invalid")
            axes[axis] = max(axes[axis], TIERS.index(str(item[axis])))
        _require(type(item["gestalt_step"]) is bool, f"projection.ratings[{index}].gestalt_step", "must be boolean")
        gestalt = gestalt or bool(item["gestalt_step"])
    rank = max(axes.values()) + (axes["complexity"] >= 2 and axes["risk"] >= 2) + gestalt
    tier = TIERS[min(int(rank), 3)]
    return _policy(tier, "automatic", tier == "max" and not no_confirm)


def _area(value: object, path: str, coverage: bool) -> dict[str, object]:
    keys = {"id", "consequence", "generalist_miss", "owning_file_ids"} | ({"coverage"} if coverage else set())
    item = _object(value, path, keys)
    _require(isinstance(item["id"], str) and item["id"], f"{path}.id", "must be an ID")
    _require(item["consequence"] in CONSEQUENCES and type(item["generalist_miss"]) is bool, path, "has invalid consequence or miss")
    files = _ids(item["owning_file_ids"], f"{path}.owning_file_ids")
    out = {"id": item["id"], "consequence": item["consequence"], "generalist_miss": item["generalist_miss"], "owning_file_ids": files}
    if coverage:
        proof = _object(item["coverage"], f"{path}.coverage", {"status", "report_artifact_id", "seal", "owning_file_ids"})
        _require(proof["status"] in {"STALE", "CURRENT"}, f"{path}.coverage.status", "invalid status")
        if proof["status"] == "STALE":
            _require(proof["report_artifact_id"] is None and proof["seal"] is None and proof["owning_file_ids"] == [], f"{path}.coverage", "stale coverage carries no proof")
        else:
            _require(isinstance(proof["report_artifact_id"], str) and proof["report_artifact_id"], f"{path}.coverage.report_artifact_id", "missing proof ref")
            _require(isinstance(proof["seal"], str) and proof["seal"], f"{path}.coverage.seal", "missing seal")
            _require(set(_ids(proof["owning_file_ids"], f"{path}.coverage.owning_file_ids")) == set(files), f"{path}.coverage.owning_file_ids", "must match area files")
        out["coverage"] = proof
    return out


def _refresh(p: dict[str, object]) -> dict[str, object]:
    data = _object(p, "projection", {"prior_areas", "current_areas", "mappings", "priority_order", "invalidators"})
    prior = [_area(v, f"projection.prior_areas[{i}]", True) for i, v in enumerate(data["prior_areas"] if isinstance(data["prior_areas"], list) else [])]
    current = [_area(v, f"projection.current_areas[{i}]", False) for i, v in enumerate(data["current_areas"] if isinstance(data["current_areas"], list) else [])]
    prior_by = {str(a["id"]): a for a in prior}; current_by = {str(a["id"]): a for a in current}
    _require(len(prior_by) == len(prior) and len(current_by) == len(current), "projection", "area IDs must be unique")
    priority = _ids(data["priority_order"], "projection.priority_order")
    _require(set(priority) == set(current_by), "projection.priority_order", "must be a bijection")
    _require(isinstance(data["mappings"], list) and isinstance(data["invalidators"], dict), "projection", "mappings and invalidators are malformed")
    lineage: dict[str, list[dict[str, object]]] = {key: [] for key in current_by}; mapped: set[str] = set(); successors: set[str] = set(); retired: list[str] = []
    for i, raw in enumerate(data["mappings"]):
        m = _object(raw, f"projection.mappings[{i}]", {"prior_id", "resolution", "active_id"})
        old, resolution, new = m["prior_id"], m["resolution"], m["active_id"]
        _require(old in prior_by and old not in mapped and resolution in {"continuing", "successor", "retired"}, f"projection.mappings[{i}]", "invalid mapping")
        mapped.add(str(old))
        if resolution == "retired": _require(new is None, f"projection.mappings[{i}].active_id", "retired maps to no active ID"); retired.append(str(old)); continue
        _require(new in current_by and (resolution != "continuing" or new == old), f"projection.mappings[{i}]", "invalid active mapping")
        lineage[str(new)].append(prior_by[str(old)]); successors |= {str(new)} if resolution == "successor" else set()
    _require(mapped == set(prior_by), "projection.mappings", "must map every prior ID")
    active = []
    for ident in priority:
        item = dict(current_by[ident]); flags = data["invalidators"].get(ident, {})
        _require(isinstance(flags, dict) and set(flags) == INVALIDATORS and all(type(v) is bool for v in flags.values()), f"projection.invalidators.{ident}", "requires boolean invalidators")
        ancestors = lineage[ident]; retained = ancestors[0]["coverage"] if len(ancestors) == 1 and ident not in successors else None
        item["consequence"] = max([item["consequence"]] + [a["consequence"] for a in ancestors], key=CONSEQUENCES.index)
        item["coverage"] = retained if retained and retained["status"] == "CURRENT" and not any(flags.values()) else {"status": "STALE", "report_artifact_id": None, "seal": None, "owning_file_ids": []}
        active.append(item)
    return {"active_areas": active, "retired_area_ids": retired, "priority_order": priority}


def _coverage(p: dict[str, object]) -> dict[str, object]:
    data = _object(p, "projection", {"areas", "coverage", "target_seal", "scheduled_area_ids"})
    _require(isinstance(data["target_seal"], str) and data["target_seal"], "projection.target_seal", "missing seal")
    areas = [_area(v, f"projection.areas[{i}]", True) for i, v in enumerate(data["areas"] if isinstance(data["areas"], list) else [])]; by = {a["id"]: a for a in areas}
    scheduled = set(_ids(data["scheduled_area_ids"], "projection.scheduled_area_ids")); _require(scheduled <= set(by), "projection.scheduled_area_ids", "unknown area")
    _require(isinstance(data["coverage"], list), "projection.coverage", "must be an array")
    for i, raw in enumerate(data["coverage"]):
        event = _object(raw, f"projection.coverage[{i}]", {"area_id", "report_artifact_id", "seal", "owning_file_ids", "usable"})
        ident = event["area_id"]; _require(ident in scheduled and event["usable"] is True and event["seal"] == data["target_seal"], f"projection.coverage[{i}]", "invalid coverage event")
        _require(set(_ids(event["owning_file_ids"], f"projection.coverage[{i}].owning_file_ids")) == set(by[ident]["owning_file_ids"]), f"projection.coverage[{i}]", "files do not match")
        by[ident]["coverage"] = {"status": "CURRENT", "report_artifact_id": event["report_artifact_id"], "seal": event["seal"], "owning_file_ids": event["owning_file_ids"]}
    return {"areas": areas}


def _roster(p: dict[str, object]) -> dict[str, object]:
    data = _object(p, "projection", {"tier", "areas", "priority_order", "capacity"}); _require(data["tier"] in TIERS and type(data["capacity"]) is int and data["capacity"] >= 2, "projection", "invalid tier or capacity")
    areas = [_area(v, f"projection.areas[{i}]", True) for i,v in enumerate(data["areas"] if isinstance(data["areas"],list) else [])]; by = {a["id"]:a for a in areas}; priority = _ids(data["priority_order"], "projection.priority_order"); _require(set(priority)==set(by), "projection.priority_order", "must be a bijection")
    threshold = POLICIES[data["tier"]][2]; eligible = [by[i] for i in priority if (data["tier"] == "max" or (by[i]["generalist_miss"] and CONSEQUENCES.index(by[i]["consequence"]) >= CONSEQUENCES.index(threshold))) and (by[i]["consequence"] == "Critical" or by[i]["coverage"]["status"] != "CURRENT")]
    eligible.sort(key=lambda a: a["coverage"]["status"] == "CURRENT"); roster = [{"role":"holistic"},{"role":"adversarial"}] + [{"role":"specialist","area_id":a["id"]} for a in eligible]; width = data["capacity"]-1
    return {"roster": roster, "waves": [roster[i:i+width] for i in range(0,len(roster),width)]}


def _gates(p: dict[str, object]) -> dict[str, object]:
    data = _object(p,"projection",{"target_seal","gates"}); _require(isinstance(data["gates"],list),"projection.gates","must be array"); blocks=[]; gaps=[]
    for i, raw in enumerate(data["gates"]):
        gate=_object(raw,f"projection.gates[{i}]",{"id","target_seal","applicability","classification","status","artifact_id"}); _require(gate["target_seal"]==data["target_seal"],f"projection.gates[{i}]","stale gate")
        if gate["applicability"] == "applicable" and gate["status"] == "FAILED": blocks.append(f"gate {gate['id']} failed")
        if gate["classification"] == "required" and gate["applicability"] == "applicable" and gate["status"] != "PASSED": blocks.append(f"required gate {gate['id']} did not pass")
        if gate["status"] == "NOT_RUN": gaps.append(f"gate {gate['id']} not run")
    return {"gates":data["gates"],"blocking_reasons":blocks,"evidence_gaps":gaps,"review_may_start":not any("failed" in b for b in blocks),"merge_readiness_eligible":not blocks}


def _ledger(p: dict[str, object]) -> dict[str, object]:
    data=_object(p,"projection",{"rows","target_seal"}); _require(isinstance(data["rows"],list),"projection.rows","must be array"); rows=[]
    for i, raw in enumerate(data["rows"]):
        row=_object(raw,f"projection.rows[{i}]",{"id","source_ids","reported_severity","current_severity","factual","state","proof_artifact_ids","manifest_artifact_id","target_seal"}); _require(row["target_seal"]==data["target_seal"] and row["state"] in {"OPEN","FIX_APPLIED","FIX_VERIFIED","REFUTED","INTENTIONAL"},f"projection.rows[{i}]","invalid row"); _ids(row["source_ids"],f"projection.rows[{i}].source_ids")
        if row["state"] in {"FIX_VERIFIED","REFUTED","INTENTIONAL"}: _require(bool(row["proof_artifact_ids"]),f"projection.rows[{i}].proof_artifact_ids","settlement needs proof")
        rows.append(row)
    return {"rows":rows,"pending_fix_ids":[r["id"] for r in rows if r["state"] in {"OPEN","FIX_APPLIED"}],"round_indeterminate":False,"next_adjudication":None}


def _challenge(p: dict[str, object]) -> dict[str, object]:
    data=_object(p,"projection",{"current_seal","status","target_seal","source_finding_ids","artifact_id"}); _require(data["target_seal"]==data["current_seal"],"projection.target_seal","stale challenge"); sources=_ids(data["source_finding_ids"],"projection.source_finding_ids")
    state = "NEEDS_TRIAGE" if sources else {"UPHOLD":"UPHELD","BLOCK":"BLOCKED","FAILED":"INDETERMINATE"}.get(data["status"]); _require(state is not None,"projection.status","invalid")
    return {"state":state,"fresh":True,"target_seal":data["target_seal"],"source_finding_ids":sources,"artifact_id":data["artifact_id"]}


def _terminal(p: dict[str, object]) -> dict[str, object]:
    data=_object(p,"projection",{"lifecycle","ledger","gates","areas","final_challenge"}); _require(isinstance(data["lifecycle"],dict) and isinstance(data["ledger"],list) and isinstance(data["areas"],list),"projection","malformed terminal projection")
    settled=all(row.get("state") in {"FIX_VERIFIED","REFUTED","INTENTIONAL"} for row in data["ledger"]); covered=all(a.get("coverage",{}).get("status")=="CURRENT" or not a.get("generalist_miss") for a in data["areas"]); ready=settled and covered and not data["gates"].get("blocking_reasons") and data["final_challenge"].get("state")=="UPHELD" and not data["lifecycle"].get("any_indeterminate")
    return {"lifecycle_outcome":"CONVERGED" if ready else "NOT_CONVERGED","terminal_verdict":"CONVERGED" if ready else "NOT_CONVERGED","merge_ready":ready,"qualified_claim_eligible":ready,"failed_conditions":[] if ready else ["terminal conjunct failed"]}


OPERATIONS = {"derive_policy":_derive,"refresh_inventory":_refresh,"record_specialist_coverage":_coverage,"plan_roster":_roster,"reconcile_gates":_gates,"apply_ledger_decisions":_ledger,"record_final_challenge":_challenge,"compute_terminal":_terminal}


def apply(envelope: TransitionEnvelope, snapshot: dict[str, object], authority: ProjectionAuthority) -> dict[str, object]:
    if not isinstance(authority, ProjectionAuthority): raise ArtifactMismatch("state transitions require canonical projection authority")
    authority.validate(envelope, snapshot)
    operation=OPERATIONS.get(envelope.operation)
    if operation is None: raise ArtifactMismatch("unknown issued transition operation")
    try: result=operation(envelope.projection)
    except InputValidation as exc: raise ArtifactMismatch("issued compact projection is invalid") from exc
    updated=dict(snapshot); processor=dict(snapshot.get("processor_state",{})); processor[envelope.operation]=result; updated["processor_state"]=processor
    return updated
