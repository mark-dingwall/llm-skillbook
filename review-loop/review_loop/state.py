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
REQUIRED_GATE_IDS = ("tests",)
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


def _canonical_required_gate_ids(processor_state: dict[str, object]) -> list[str]:
    policy = processor_state.get("derive_policy")
    _require(
        isinstance(policy, dict),
        "canonical.derive_policy",
        "gate policy is missing",
    )
    assert isinstance(policy, dict)
    required_gate_ids = policy.get("required_gate_ids")
    _require(
        required_gate_ids == list(REQUIRED_GATE_IDS),
        "canonical.derive_policy.required_gate_ids",
        "fixed gate policy is malformed",
    )
    assert isinstance(required_gate_ids, list)
    return list(required_gate_ids)


def _policy(tier: str, source: str, confirmation: bool) -> dict[str, object]:
    rounds, capability, threshold, multi = POLICIES[tier]
    return {
        "tier": tier,
        "source": source,
        "confirmation_required": confirmation,
        "round_cap": rounds,
        "normal_capability": capability,
        "specialist_threshold": threshold,
        "multi_review_rounds": list(multi),
        "required_gate_ids": list(REQUIRED_GATE_IDS),
    }


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
        item = dict(current_by[ident]); ancestors = lineage[ident]; flags = data["invalidators"].get(ident)
        if ancestors:
            _require(isinstance(flags, dict) and set(flags) == INVALIDATORS and all(type(v) is bool for v in flags.values()), f"projection.invalidators.{ident}", "requires boolean invalidators")
        else:
            _require(flags is None, f"projection.invalidators.{ident}", "new area has no invalidator record")
            flags = {}
        retained = ancestors[0]["coverage"] if len(ancestors) == 1 and ident not in successors else None
        item["consequence"] = max([item["consequence"]] + [a["consequence"] for a in ancestors], key=CONSEQUENCES.index)
        item["generalist_miss"] = bool(item["generalist_miss"]) or any(bool(a["generalist_miss"]) for a in ancestors)
        item["owning_file_ids"] = list(dict.fromkeys([file for area in ancestors + [item] for file in area["owning_file_ids"]]))
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


def _gates(p: dict[str, object], required_gate_ids: list[str]) -> dict[str, object]:
    data = _object(p, "projection", {"target_seal", "gates"})
    _require(isinstance(data["gates"], list), "projection.gates", "must be array")
    required = set(
        _ids(required_gate_ids, "canonical.derive_policy.required_gate_ids")
    )
    blocks: list[str] = []
    gaps: list[str] = []
    seen: set[object] = set()
    for i, raw in enumerate(data["gates"]):
        path = f"projection.gates[{i}]"
        gate = _object(
            raw,
            path,
            {
                "id",
                "target_seal",
                "applicability",
                "classification",
                "status",
                "artifact_id",
            },
        )
        _require(gate["target_seal"] == data["target_seal"], path, "stale gate")
        _require(
            gate["id"] not in seen
            and gate["applicability"] in {"applicable", "not_applicable"}
            and gate["classification"] in {"required", "supporting"}
            and gate["status"] in {"PASSED", "FAILED", "NOT_RUN"},
            path,
            "invalid gate",
        )
        seen.add(gate["id"])
        _require(
            (gate["id"] in required) == (gate["classification"] == "required"),
            f"{path}.classification",
            "classification disagrees with fixed gate policy",
        )
        _require(
            not (
                gate["applicability"] == "not_applicable"
                and gate["status"] != "NOT_RUN"
            ),
            path,
            "non-applicable gate cannot execute",
        )
        if gate["applicability"] == "applicable" and gate["status"] == "FAILED":
            blocks.append(f"gate {gate['id']} failed")
        if (
            gate["classification"] == "required"
            and gate["applicability"] == "applicable"
            and gate["status"] != "PASSED"
        ):
            blocks.append(f"required gate {gate['id']} did not pass")
        if gate["status"] == "NOT_RUN":
            gaps.append(f"gate {gate['id']} not run")
    missing = required - seen
    if missing:
        blocks.extend(f"required gate {ident} missing" for ident in sorted(missing))
    if not data["gates"]:
        gaps.append("no applicable evidence gates discovered")
    return {
        "gates": data["gates"],
        "required_gate_ids": list(required_gate_ids),
        "blocking_reasons": blocks,
        "evidence_gaps": gaps,
        "review_may_start": not any("failed" in reason for reason in blocks),
        "merge_readiness_eligible": not blocks,
    }


def _ledger(p: dict[str, object], prior_state: object) -> dict[str, object]:
    data=_object(p,"projection",{"prior_rows","decisions","manifests","target_seal","adjudication"})
    _require(isinstance(data["prior_rows"],list) and isinstance(data["decisions"],list) and isinstance(data["manifests"],list),"projection","ledger lists required")
    prior_attempt = None
    if prior_state is not None:
        _require(
            isinstance(prior_state, dict),
            "canonical.apply_ledger_decisions",
            "must be an object",
        )
        assert isinstance(prior_state, dict)
        prior_attempt = prior_state.get("next_adjudication")
        if prior_attempt is not None:
            prior_attempt = _object(
                prior_attempt,
                "canonical.apply_ledger_decisions.next_adjudication",
                {"attempt", "pending_ids"},
            )
            _require(
                prior_attempt["attempt"] == 2,
                "canonical.apply_ledger_decisions.next_adjudication.attempt",
                "must schedule attempt two",
            )
            pending = _ids(
                prior_attempt["pending_ids"],
                "canonical.apply_ledger_decisions.next_adjudication.pending_ids",
            )
            _require(
                bool(pending),
                "canonical.apply_ledger_decisions.next_adjudication.pending_ids",
                "must not be empty",
            )
            prior_attempt = {"attempt": 2, "pending_ids": pending}
    prior={}
    for i, raw in enumerate(data["prior_rows"]):
        row=_object(raw,f"projection.prior_rows[{i}]",{"id","source_ids","reported_severity","current_severity","factual","state","proof_artifact_ids","manifest_artifact_id","target_seal"})
        _require(row["target_seal"]==data["target_seal"] and row["id"] not in prior, f"projection.prior_rows[{i}]", "invalid prior row")
        prior[row["id"]]=row
    manifest_map={}
    for i, raw in enumerate(data["manifests"]):
        manifest=_object(raw,f"projection.manifests[{i}]",{"id","finding_id"})
        _require(isinstance(manifest["id"],str) and manifest["id"] and manifest["id"] not in manifest_map and manifest["finding_id"] in prior,f"projection.manifests[{i}]","invalid manifest")
        manifest_map[manifest["id"]]=manifest["finding_id"]
    proposed={}; green=[]
    for i, raw in enumerate(data["decisions"]):
        item=_object(raw,f"projection.decisions[{i}]",{"id","state","proof_artifact_ids","manifest_artifact_id"}); ident=item["id"]; old=prior.get(ident)
        _require(old is not None and ident not in proposed and item["state"] in {"OPEN","FIX_APPLIED","FIX_VERIFIED","REFUTED","INTENTIONAL"},f"projection.decisions[{i}]","unknown or invalid decision")
        before, after=old["state"],item["state"]
        legal={"OPEN":{"OPEN","FIX_APPLIED","REFUTED","INTENTIONAL"},"FIX_APPLIED":{"OPEN","FIX_APPLIED","FIX_VERIFIED"},"FIX_VERIFIED":{"OPEN","FIX_VERIFIED"},"REFUTED":{"OPEN","REFUTED"},"INTENTIONAL":{"OPEN","INTENTIONAL"}}
        _require(after in legal[before],f"projection.decisions[{i}].state","illegal ledger transition")
        manifest=item["manifest_artifact_id"]
        if after == "FIX_APPLIED": _require(manifest_map.get(manifest)==ident,f"projection.decisions[{i}].manifest_artifact_id","manifest must be linked to finding")
        if after == "FIX_VERIFIED": _require(manifest_map.get(manifest)==ident and manifest==old.get("manifest_artifact_id"),f"projection.decisions[{i}].manifest_artifact_id","must retain linked applied manifest")
        if after in {"FIX_VERIFIED","REFUTED","INTENTIONAL"}: _require(bool(_ids(item["proof_artifact_ids"],f"projection.decisions[{i}].proof_artifact_ids")),f"projection.decisions[{i}]","settlement needs proof")
        merged=dict(old); merged.update({"state":after,"proof_artifact_ids":item["proof_artifact_ids"],"manifest_artifact_id":manifest}); proposed[ident]=merged
        if after in {"FIX_VERIFIED","REFUTED","INTENTIONAL"}: green.append(ident)
    _require(set(proposed)==set(prior),"projection.decisions","must decide every existing row")
    adjudication=data["adjudication"]
    if green:
        _require(isinstance(adjudication,dict),"projection.adjudication","green decisions require adjudication")
        a=_object(adjudication,"projection.adjudication",{"attempt","status","decided_ids","proof_artifact_id"}); _require(a["attempt"] in {1,2} and a["status"] in {"UPHOLD","BOUNCE","UNDECIDED","FAILED"},"projection.adjudication","invalid attempt")
        ids=set(_ids(a["decided_ids"],"projection.adjudication.decided_ids")); _require(ids <= set(green),"projection.adjudication.decided_ids","unknown decision")
        _require(a["status"] in {"FAILED","UNDECIDED"} or isinstance(a["proof_artifact_id"],str) and a["proof_artifact_id"],"projection.adjudication.proof_artifact_id","settled outcome needs proof")
        if a["status"]=="UPHOLD": _require(ids==set(green),"projection.adjudication","uphold needs all decisions")
        if a["attempt"] == 1: _require(prior_attempt is None,"canonical.apply_ledger_decisions.next_adjudication","first attempt cannot replay state")
        else:
            expected={"attempt":2,"pending_ids":green}
            _require(prior_attempt==expected,"canonical.apply_ledger_decisions.next_adjudication","attempt two must consume prior retry state")
        if a["status"] in {"FAILED","UNDECIDED"} and a["attempt"]==1: return {"rows":list(prior.values()),"pending_fix_ids":[r["id"] for r in prior.values() if r["state"] in {"OPEN","FIX_APPLIED"}],"round_indeterminate":False,"next_adjudication":{"attempt":2,"pending_ids":green}}
        if a["status"] in {"FAILED","UNDECIDED"}: proposed={ident:prior[ident] for ident in prior}
        if a["status"]=="BOUNCE": proposed={ident:(prior[ident] if ident in ids else value) for ident,value in proposed.items()}
    else: _require(adjudication is None and prior_attempt is None,"projection.adjudication","no adjudication pending")
    rows=list(proposed.values()); return {"rows":rows,"pending_fix_ids":[r["id"] for r in rows if r["state"] in {"OPEN","FIX_APPLIED"}],"round_indeterminate":False,"next_adjudication":None}


def _challenge(p: dict[str, object]) -> dict[str, object]:
    data=_object(p,"projection",{"current_seal","attempts"}); _require(isinstance(data["attempts"],list) and 1<=len(data["attempts"])<=2,"projection.attempts","one or two attempts")
    attempts=[]
    for i,raw in enumerate(data["attempts"]):
        a=_object(raw,f"projection.attempts[{i}]",{"status","target_seal","source_finding_ids","artifact_id"}); _require(a["status"] in {"UPHOLD","BLOCK","FAILED"},f"projection.attempts[{i}]","invalid status"); attempts.append(a)
    _require(len(attempts)==1 or attempts[0]["status"]=="FAILED","projection.attempts","only failed call retries")
    last=attempts[-1]; sources=_ids(last["source_finding_ids"],"projection.source_finding_ids")
    if any(a["target_seal"]!=data["current_seal"] for a in attempts): state="STALE"; fresh=False
    elif last["status"]=="FAILED": state="RETRY_REQUIRED" if len(attempts)==1 else "INDETERMINATE"; fresh=True
    elif sources: state="NEEDS_TRIAGE"; fresh=True
    else: state="UPHELD" if last["status"]=="UPHOLD" else "BLOCKED"; fresh=True
    return {"state":state,"fresh":fresh,"target_seal":last["target_seal"],"source_finding_ids":sources,"artifact_id":last["artifact_id"],"retry_required":state=="RETRY_REQUIRED"}


def _terminal(p: dict[str, object], required_gate_ids: list[str]) -> dict[str, object]:
    data=_object(p,"projection",{"lifecycle","ledger","gates","areas","final_challenge"})
    lifecycle=_object(data["lifecycle"],"projection.lifecycle",{"confirmation","deadline_expired","round1_triage_complete","scheduled_reports_usable","raw_reports_reconciled","any_indeterminate","expected_final_seal","actual_final_seal"})
    _require(isinstance(data["ledger"],list) and isinstance(data["areas"],list),"projection","malformed terminal projection")
    gate=_object(data["gates"],"projection.gates",{"gates","blocking_reasons","evidence_gaps","review_may_start","merge_readiness_eligible","required_gate_ids"})
    _require(gate["required_gate_ids"]==required_gate_ids,"projection.gates.required_gate_ids","must match canonical gate policy")
    challenge=_object(data["final_challenge"],"projection.final_challenge",{"state","fresh","target_seal","source_finding_ids","artifact_id","retry_required"})
    failed=[]
    if lifecycle["confirmation"] not in {"not_required","confirmed"}: failed.append("confirmation")
    if lifecycle["deadline_expired"]: failed.append("deadline")
    for key in ("round1_triage_complete","scheduled_reports_usable","raw_reports_reconciled"):
        if lifecycle[key] is not True: failed.append(key)
    if lifecycle["any_indeterminate"]: failed.append("indeterminate")
    if lifecycle["expected_final_seal"] != lifecycle["actual_final_seal"]: failed.append("seal")
    if challenge["state"] != "UPHELD" or challenge["fresh"] is not True or challenge["target_seal"] != lifecycle["actual_final_seal"] or challenge["source_finding_ids"] or challenge["retry_required"] or not isinstance(challenge["artifact_id"],str) or not challenge["artifact_id"]: failed.append("final_challenge")
    # Gate rollup must match compact records rather than trusting a caller flag.
    recomputed=_gates({"target_seal":lifecycle["expected_final_seal"],"gates":gate["gates"]},required_gate_ids)
    if any(gate[key] != recomputed[key] for key in ("blocking_reasons","evidence_gaps","review_may_start","merge_readiness_eligible")): failed.append("gates")
    if not gate["merge_readiness_eligible"] or gate["blocking_reasons"]: failed.append("gates_not_ready")
    for i,row in enumerate(data["ledger"]):
        _require(isinstance(row,dict),f"projection.ledger[{i}]","invalid row")
        state=row.get("state"); severity=row.get("current_severity")
        proofs=row.get("proof_artifact_ids")
        if state in {"FIX_VERIFIED","REFUTED","INTENTIONAL"} and (not isinstance(proofs,list) or not proofs or any(not isinstance(proof,str) or not proof for proof in proofs)): failed.append(f"proof:{row.get('id')}")
        if severity in {"Important","Critical"} and state not in {"FIX_VERIFIED","REFUTED","INTENTIONAL"}: failed.append(f"open:{row.get('id')}")
    for raw in data["areas"]:
        area=_area(raw,"projection.areas",True)
        if area["generalist_miss"] and CONSEQUENCES.index(area["consequence"])>=CONSEQUENCES.index("Important") and area["coverage"]["status"]!="CURRENT": failed.append(f"coverage:{area['id']}")
    ready=not failed
    return {"lifecycle_outcome":"CONVERGED" if ready else "NOT_CONVERGED","terminal_verdict":"CONVERGED" if ready else "NOT_CONVERGED","merge_ready":ready,"qualified_claim_eligible":ready,"failed_conditions":failed}


OPERATIONS = {"derive_policy":_derive,"refresh_inventory":_refresh,"record_specialist_coverage":_coverage,"plan_roster":_roster,"record_final_challenge":_challenge}


def apply(envelope: TransitionEnvelope, snapshot: dict[str, object], authority: ProjectionAuthority) -> dict[str, object]:
    if not isinstance(authority, ProjectionAuthority):
        raise ArtifactMismatch("state transitions require canonical projection authority")
    authority.validate(envelope, snapshot)
    processor_state = snapshot.get("processor_state")
    if not isinstance(processor_state, dict):
        raise ArtifactMismatch("canonical processor state is malformed")
    operation = OPERATIONS.get(envelope.operation)
    try:
        if envelope.operation == "apply_ledger_decisions":
            result = _ledger(
                envelope.projection,
                processor_state.get("apply_ledger_decisions"),
            )
        elif envelope.operation == "reconcile_gates":
            result = _gates(
                envelope.projection,
                _canonical_required_gate_ids(processor_state),
            )
        elif envelope.operation == "compute_terminal":
            result = _terminal(
                envelope.projection,
                _canonical_required_gate_ids(processor_state),
            )
        elif operation is not None:
            result = operation(envelope.projection)
        else:
            raise ArtifactMismatch("unknown issued transition operation")
    except InputValidation as exc:
        raise ArtifactMismatch("issued compact projection is invalid") from exc
    updated = dict(snapshot)
    processor = dict(processor_state)
    processor[envelope.operation] = result
    updated["processor_state"] = processor
    return updated
