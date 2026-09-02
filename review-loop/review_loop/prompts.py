"""Canonical prompt renderer and strict role/report validators.

Templates and fragments are fixed, skill-relative resources containing only
declared ``{name}`` substitutions.  This module is the sole production and
fixture path for every dispatched prompt and the sole ordinary report/role
classifier; the state kernel (state.py) never parses semantic JSON and never
touches the filesystem -- that boundary lives here instead.
"""
from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .state import CONSEQUENCES, INVALIDATORS, REQUIRED_GATE_IDS, TIERS

RESOURCES = Path(__file__).parent / "resources"

TEMPLATES = {"review": "review.md"}
FRAGMENTS = {
    "safety": "safety.md",
    "round-one": "round-one.md",
    "later-round": "later-round.md",
    "holistic": "holistic.md",
    "adversarial": "adversarial.md",
    "specialist": "specialist.md",
}

_LEDGER_STATES = {"OPEN", "FIX_APPLIED", "FIX_VERIFIED", "REFUTED", "INTENTIONAL"}
_SEVERITIES = {"Minor", "Important", "Critical"}
_FACTUAL = {"CONFIRMED", "PLAUSIBLE", "UNVERIFIABLE"}


class RenderError(Exception):
    """Prompt rendering rejected malformed or mismatched substitution input."""


class RoleValidationError(Exception):
    """A dispatched role/report output was rejected as malformed."""

    def __init__(self, *issues: str) -> None:
        super().__init__("; ".join(issues) or "invalid role output")
        self.issues = list(issues)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RoleValidationError(message)


def _object(value: object, keys: set[str], where: str) -> dict[str, object]:
    _require(isinstance(value, dict), f"{where} must be an object")
    assert isinstance(value, dict)
    _require(set(value) == keys, f"{where} has unknown or missing fields")
    return value


def _text(value: object, where: str) -> str:
    _require(isinstance(value, str) and bool(value), f"{where} must be a non-empty string")
    assert isinstance(value, str)
    return value


def _unique_ids(value: object, where: str) -> list[str]:
    _require(
        isinstance(value, list) and all(isinstance(v, str) and v for v in value),
        f"{where} must contain non-empty IDs",
    )
    assert isinstance(value, list)
    _require(len(set(value)) == len(value), f"{where} IDs must be unique")
    return list(value)


# --- Renderer ------------------------------------------------------------

_FORMATTER = string.Formatter()


def _declared_names(text: str, where: str) -> set[str]:
    names: set[str] = set()
    try:
        fields = list(_FORMATTER.parse(text))
    except ValueError as exc:
        raise RenderError(f"{where} has an unresolved substitution token") from exc
    for _, field_name, format_spec, conversion in fields:
        if field_name is None:
            continue
        if (
            not field_name
            or not field_name.isidentifier()
            or format_spec
            or conversion is not None
        ):
            raise RenderError(f"{where} has an invalid substitution token: {field_name!r}")
        names.add(field_name)
    return names


def _load_resource(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RenderError(f"resource is unreadable: {path}") from exc


def render_prompt(
    template_id: str, fragment_ids: tuple[str, ...], context: Mapping[str, str]
) -> bytes:
    if template_id not in TEMPLATES:
        raise RenderError(f"unknown template: {template_id!r}")
    for fragment_id in fragment_ids:
        if fragment_id not in FRAGMENTS:
            raise RenderError(f"unknown fragment: {fragment_id!r}")
    if not isinstance(context, Mapping) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in context.items()
    ):
        raise RenderError("context must be a mapping of str to str")

    sources = [RESOURCES / TEMPLATES[template_id]] + [
        RESOURCES / FRAGMENTS[fragment_id] for fragment_id in fragment_ids
    ]
    texts = [_load_resource(path) for path in sources]

    declared: set[str] = set()
    for path, text in zip(sources, texts):
        declared |= _declared_names(text, str(path))

    supplied = set(context)
    missing = declared - supplied
    if missing:
        raise RenderError(f"missing declared values: {sorted(missing)}")
    unknown = supplied - declared
    if unknown:
        raise RenderError(f"unknown supplied values: {sorted(unknown)}")

    # str.format() performs exactly one substitution pass: it does not
    # rescan the text produced by substituting a value, so a value
    # containing literal "{{...}}" is never reinterpreted as syntax.
    rendered = "".join(text.format(**context) for text in texts)
    return rendered.encode("utf-8")


# --- Review-report classifier ---------------------------------------------


@dataclass(frozen=True)
class DispatchExpectation:
    request_id: str
    role: str
    charter_id: str
    target_seal: str
    round_input_seal: str | None
    scope_locator_ids: tuple[str, ...]
    model: str | None = None
    exclusions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessCompletion:
    request_id: str
    exit_status: int
    process_tree_terminated: bool


@dataclass(frozen=True)
class SourceFinding:
    finding_id: str
    claim: str
    severity: str
    locator_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReviewRecord:
    request_id: str
    role: str
    charter_id: str
    target_seal: str
    round_input_seal: str | None
    scope_locator_ids: tuple[str, ...]
    source_findings: tuple[SourceFinding, ...]


@dataclass(frozen=True)
class ValidatedReview:
    body: bytes
    record: ReviewRecord
    terminal_status: str
    usable: bool


@dataclass(frozen=True)
class UnusableReview:
    body: bytes
    reason: str


_TERMINAL_LINES = {
    "REVIEW-STATUS: COMPLETE": "COMPLETE",
    "REVIEW-STATUS: UNABLE": "UNABLE",
}
_FENCE_RE = re.compile(r"```review-record\r?\n(.*?)\r?\n```", re.DOTALL)
_RECORD_KEYS = {
    "request_id",
    "role",
    "charter_id",
    "target_seal",
    "round_input_seal",
    "scope_locator_ids",
    "source_findings",
}
_FINDING_KEYS = {"id", "claim", "severity", "locator_ids"}


def _parse_source_findings(raw: object) -> tuple[SourceFinding, ...] | None:
    if not isinstance(raw, list):
        return None
    findings: list[SourceFinding] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) != _FINDING_KEYS:
            return None
        fid, claim, severity, locators = (
            item["id"],
            item["claim"],
            item["severity"],
            item["locator_ids"],
        )
        if not isinstance(fid, str) or not fid or fid in seen:
            return None
        if not isinstance(claim, str) or not claim or severity not in _SEVERITIES:
            return None
        if (
            not isinstance(locators, list)
            or not locators
            or not all(isinstance(x, str) and x for x in locators)
        ):
            return None
        seen.add(fid)
        findings.append(SourceFinding(fid, claim, severity, tuple(locators)))
    return tuple(findings)


def validate_review_report(
    body: bytes, dispatch: DispatchExpectation, process: ProcessCompletion
) -> ValidatedReview | UnusableReview:
    if not isinstance(dispatch, DispatchExpectation) or not isinstance(
        process, ProcessCompletion
    ):
        raise TypeError("dispatch and process must be typed expectations")

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return UnusableReview(body, "report is not valid UTF-8")

    fences = _FENCE_RE.findall(text)
    if len(fences) != 1:
        return UnusableReview(body, "report must contain exactly one fenced review-record")

    try:
        raw = json.loads(fences[0])
    except json.JSONDecodeError:
        return UnusableReview(body, "review-record is not valid JSON")

    if not isinstance(raw, dict) or set(raw) != _RECORD_KEYS:
        return UnusableReview(body, "review-record has unknown or missing fields")

    def _id(value: object) -> bool:
        return isinstance(value, str) and bool(value)

    if not (
        _id(raw["request_id"])
        and _id(raw["role"])
        and _id(raw["charter_id"])
        and _id(raw["target_seal"])
    ):
        return UnusableReview(body, "review-record has invalid identity fields")
    if raw["round_input_seal"] is not None and not _id(raw["round_input_seal"]):
        return UnusableReview(body, "review-record round_input_seal must be null or non-empty")

    scope = raw["scope_locator_ids"]
    if (
        not isinstance(scope, list)
        or not all(_id(s) for s in scope)
        or len(set(scope)) != len(scope)
    ):
        return UnusableReview(body, "review-record scope_locator_ids must be unique non-empty IDs")

    findings = _parse_source_findings(raw["source_findings"])
    if findings is None:
        return UnusableReview(body, "review-record source_findings is malformed")

    record = ReviewRecord(
        request_id=raw["request_id"],
        role=raw["role"],
        charter_id=raw["charter_id"],
        target_seal=raw["target_seal"],
        round_input_seal=raw["round_input_seal"],
        scope_locator_ids=tuple(scope),
        source_findings=findings,
    )
    expected = (
        dispatch.request_id,
        dispatch.role,
        dispatch.charter_id,
        dispatch.target_seal,
        dispatch.round_input_seal,
        dispatch.scope_locator_ids,
    )
    actual = (
        record.request_id,
        record.role,
        record.charter_id,
        record.target_seal,
        record.round_input_seal,
        record.scope_locator_ids,
    )
    if actual != expected:
        return UnusableReview(body, "review-record does not match dispatch expectation")

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines or lines[-1] not in _TERMINAL_LINES:
        return UnusableReview(body, "report is missing its exact terminal status line")
    terminal = _TERMINAL_LINES[lines[-1]]

    usable = (
        terminal == "COMPLETE"
        and process.request_id == dispatch.request_id
        and process.exit_status == 0
        and process.process_tree_terminated is True
    )
    return ValidatedReview(body=body, record=record, terminal_status=terminal, usable=usable)


# --- Strict role-JSON validators -------------------------------------------


@dataclass(frozen=True)
class RoleExpectation:
    request_id: str
    role_id: str
    target_seal: str
    round_input_seal: str | None = None
    expected_ids: tuple[str, ...] = ()
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidatedRoleArtifact:
    role_id: str
    body: bytes
    artifact: Mapping[str, object]
    projection: object


_ENVELOPE_KEYS = {"request_id", "role_id", "target_seal", "round_input_seal", "payload"}


def _envelope(body: bytes, role_id: str, expectation: RoleExpectation) -> object:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RoleValidationError("role output is not valid UTF-8") from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RoleValidationError("role output is not valid JSON") from exc
    envelope = _object(raw, _ENVELOPE_KEYS, "role envelope")
    _require(
        envelope["request_id"] == expectation.request_id
        and envelope["role_id"] == role_id
        and envelope["role_id"] == expectation.role_id
        and envelope["target_seal"] == expectation.target_seal
        and envelope["round_input_seal"] == expectation.round_input_seal,
        "role envelope does not match dispatch expectation",
    )
    return envelope["payload"]


def _area_schema(value: object, where: str) -> dict[str, object]:
    item = _object(
        value,
        {
            "id",
            "aliases",
            "consequence",
            "generalist_miss",
            "generalist_miss_evidence",
            "surfaces",
            "owning_file_ids",
            "charter",
        },
        where,
    )
    ident = _text(item["id"], f"{where}.id")
    _require(
        isinstance(item["aliases"], list) and all(isinstance(a, str) and a for a in item["aliases"]),
        f"{where}.aliases must be a list of non-empty strings",
    )
    _require(item["consequence"] in CONSEQUENCES, f"{where}.consequence is invalid")
    _require(type(item["generalist_miss"]) is bool, f"{where}.generalist_miss must be boolean")
    if item["generalist_miss"]:
        _text(item["generalist_miss_evidence"], f"{where}.generalist_miss_evidence")
    else:
        _require(
            item["generalist_miss_evidence"] is None,
            f"{where}.generalist_miss_evidence must be null when GENERALIST-MISS is absent",
        )
    _require(
        isinstance(item["surfaces"], list)
        and bool(item["surfaces"])
        and all(isinstance(s, str) and s for s in item["surfaces"]),
        f"{where}.surfaces must be a non-empty list of non-empty strings",
    )
    files = _unique_ids(item["owning_file_ids"], f"{where}.owning_file_ids")
    charter = _text(item["charter"], f"{where}.charter")
    return {
        "id": ident,
        "aliases": list(item["aliases"]),
        "consequence": item["consequence"],
        "generalist_miss": item["generalist_miss"],
        "generalist_miss_evidence": item["generalist_miss_evidence"],
        "surfaces": list(item["surfaces"]),
        "owning_file_ids": files,
        "charter": charter,
    }


def _areas_and_priority(payload: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, dict], list[str]]:
    raw_areas = payload["areas"]
    _require(isinstance(raw_areas, list), "areas must be an array")
    assert isinstance(raw_areas, list)
    areas = [_area_schema(v, f"areas[{i}]") for i, v in enumerate(raw_areas)]
    by_id = {a["id"]: a for a in areas}
    _require(len(by_id) == len(areas), "area IDs must be unique")
    priority = _unique_ids(payload["priority_order"], "priority_order")
    _require(set(priority) == set(by_id), "priority_order must be a bijection with areas")
    return areas, by_id, priority


def _validate_evidence(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    data = _object(payload, {"gates", "evidence_gaps"}, "payload")
    _require(isinstance(data["gates"], list), "payload.gates must be an array")
    required = set(REQUIRED_GATE_IDS)
    gates: list[dict[str, object]] = []
    seen: set[str] = set()
    for i, raw in enumerate(data["gates"]):
        where = f"payload.gates[{i}]"
        gate = _object(
            raw, {"id", "argv", "applicability", "classification", "rationale"}, where
        )
        ident = _text(gate["id"], f"{where}.id")
        _require(ident not in seen, f"{where}.id must be unique")
        seen.add(ident)
        _require(
            isinstance(gate["argv"], list)
            and bool(gate["argv"])
            and all(isinstance(a, str) and a for a in gate["argv"]),
            f"{where}.argv must be a non-empty list of non-empty strings",
        )
        _require(
            gate["applicability"] in {"applicable", "not_applicable"},
            f"{where}.applicability is invalid",
        )
        _require(
            gate["classification"] in {"required", "supporting"},
            f"{where}.classification is invalid",
        )
        _require(
            (ident in required) == (gate["classification"] == "required"),
            f"{where}.classification disagrees with fixed gate policy",
        )
        _text(gate["rationale"], f"{where}.rationale")
        gates.append(dict(gate))
    _require(
        isinstance(data["evidence_gaps"], list)
        and all(isinstance(g, str) and g for g in data["evidence_gaps"]),
        "payload.evidence_gaps must be a list of non-empty strings",
    )
    artifact = {"gates": gates, "evidence_gaps": list(data["evidence_gaps"])}
    projection = {
        "gates": [
            {
                "id": g["id"],
                "target_seal": expectation.target_seal,
                "applicability": g["applicability"],
                "classification": g["classification"],
                "status": "NOT_RUN",
                "artifact_id": None,
            }
            for g in gates
        ],
        "evidence_gaps": list(data["evidence_gaps"]),
    }
    return artifact, projection


def _validate_inventory_owner(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    is_refresh = bool(expectation.expected_ids)
    keys = {"areas", "priority_order", "mappings"}
    data = _object(payload, keys, "payload")
    areas, by_id, priority = _areas_and_priority(data)

    _require(isinstance(data["mappings"], list), "payload.mappings must be an array")
    if not is_refresh:
        _require(not data["mappings"], "payload.mappings must be empty for an initial inventory")
        artifact = {"areas": areas, "priority_order": priority, "mappings": []}
        projection = {
            "current_areas": [
                {
                    "id": a["id"],
                    "consequence": a["consequence"],
                    "generalist_miss": a["generalist_miss"],
                    "owning_file_ids": a["owning_file_ids"],
                }
                for a in areas
            ],
            "priority_order": priority,
        }
        return artifact, projection

    mapped: set[str] = set()
    mappings: list[dict[str, object]] = []
    invalidators: dict[str, dict[str, bool]] = {}
    for i, raw in enumerate(data["mappings"]):
        where = f"payload.mappings[{i}]"
        m = _object(
            raw,
            {"prior_id", "resolution", "active_id", "retirement_reason", "invalidators"},
            where,
        )
        prior_id = _text(m["prior_id"], f"{where}.prior_id")
        _require(prior_id in expectation.expected_ids, f"{where}.prior_id is not a known prior area")
        _require(prior_id not in mapped, f"{where}.prior_id is mapped more than once")
        mapped.add(prior_id)
        resolution = m["resolution"]
        _require(
            resolution in {"continuing", "successor", "retired"},
            f"{where}.resolution is invalid",
        )
        if resolution == "retired":
            _require(m["active_id"] is None, f"{where}.active_id must be null when retired")
            reason = _text(m["retirement_reason"], f"{where}.retirement_reason")
            _require("\n" not in reason, f"{where}.retirement_reason must be single-line")
            _require(m["invalidators"] is None, f"{where}.invalidators must be null when retired")
        else:
            active_id = m["active_id"]
            _require(
                isinstance(active_id, str) and active_id in by_id,
                f"{where}.active_id must name a current area",
            )
            if resolution == "continuing":
                _require(active_id == prior_id, f"{where}.active_id must equal prior_id when continuing")
            _require(
                m["retirement_reason"] is None,
                f"{where}.retirement_reason must be null unless retired",
            )
            flags = _object(m["invalidators"], INVALIDATORS, f"{where}.invalidators")
            _require(
                all(type(v) is bool for v in flags.values()),
                f"{where}.invalidators must be boolean",
            )
            if active_id in invalidators:
                _require(
                    invalidators[active_id] == flags,
                    f"{where}.invalidators disagrees with an earlier mapping onto the same area",
                )
            else:
                invalidators[active_id] = dict(flags)
        mappings.append(dict(m))
    _require(mapped == set(expectation.expected_ids), "payload.mappings must map every prior area exactly once")

    artifact = {"areas": areas, "priority_order": priority, "mappings": mappings}
    projection = {
        "current_areas": [
            {
                "id": a["id"],
                "consequence": a["consequence"],
                "generalist_miss": a["generalist_miss"],
                "owning_file_ids": a["owning_file_ids"],
            }
            for a in areas
        ],
        "priority_order": priority,
        "mappings": [
            {"prior_id": m["prior_id"], "resolution": m["resolution"], "active_id": m["active_id"]}
            for m in mappings
        ],
        "invalidators": invalidators,
    }
    return artifact, projection


def _validate_inventory_challenge(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    if not isinstance(payload, dict):
        raise RoleValidationError("payload must be an object")
    verdict = payload.get("verdict")
    if verdict == "UPHOLD":
        _object(payload, {"verdict"}, "payload")
        return {"verdict": "UPHOLD", "challenges": []}, {"verdict": "UPHOLD", "challenge_ids": []}
    _require(verdict == "CHALLENGE", "payload.verdict must be UPHOLD or CHALLENGE")
    data = _object(payload, {"verdict", "challenges"}, "payload")
    _require(
        isinstance(data["challenges"], list) and bool(data["challenges"]),
        "payload.challenges must be non-empty when CHALLENGE",
    )
    categories = {"omission", "unsupported_claim", "fragmentation", "unusable_charter"}
    challenges: list[dict[str, object]] = []
    seen: set[str] = set()
    for i, raw in enumerate(data["challenges"]):
        where = f"payload.challenges[{i}]"
        item = _object(raw, {"id", "category", "statement", "evidence"}, where)
        ident = _text(item["id"], f"{where}.id")
        _require(ident not in seen, f"{where}.id must be unique")
        seen.add(ident)
        _require(item["category"] in categories, f"{where}.category is invalid")
        _text(item["statement"], f"{where}.statement")
        _text(item["evidence"], f"{where}.evidence")
        challenges.append(dict(item))
    artifact = {"verdict": "CHALLENGE", "challenges": challenges}
    projection = {"verdict": "CHALLENGE", "challenge_ids": [c["id"] for c in challenges]}
    return artifact, projection


def _validate_inventory_revision(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    data = _object(payload, {"areas", "priority_order", "resolutions"}, "payload")
    areas, by_id, priority = _areas_and_priority(data)
    _require(isinstance(data["resolutions"], list), "payload.resolutions must be an array")
    resolved: set[str] = set()
    resolutions: list[dict[str, object]] = []
    for i, raw in enumerate(data["resolutions"]):
        where = f"payload.resolutions[{i}]"
        item = _object(raw, {"challenge_id", "resolution"}, where)
        cid = _text(item["challenge_id"], f"{where}.challenge_id")
        _require(cid in expectation.expected_ids, f"{where}.challenge_id is not a known challenge")
        _require(cid not in resolved, f"{where}.challenge_id is resolved more than once")
        resolved.add(cid)
        _text(item["resolution"], f"{where}.resolution")
        resolutions.append(dict(item))
    _require(
        resolved == set(expectation.expected_ids),
        "payload.resolutions must resolve every challenge exactly once",
    )
    artifact = {"areas": areas, "priority_order": priority, "resolutions": resolutions}
    projection = {
        "current_areas": [
            {
                "id": a["id"],
                "consequence": a["consequence"],
                "generalist_miss": a["generalist_miss"],
                "owning_file_ids": a["owning_file_ids"],
            }
            for a in areas
        ],
        "priority_order": priority,
    }
    return artifact, projection


def _validate_rating(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    data = _object(payload, {"complexity", "risk", "evidence", "gestalt"}, "payload")
    _require(data["complexity"] in TIERS, "payload.complexity is invalid")
    _require(data["risk"] in TIERS, "payload.risk is invalid")
    _require(isinstance(data["evidence"], list) and bool(data["evidence"]), "payload.evidence must be non-empty")
    axes_seen: set[str] = set()
    evidence: list[dict[str, object]] = []
    for i, raw in enumerate(data["evidence"]):
        where = f"payload.evidence[{i}]"
        item = _object(raw, {"axis", "statement"}, where)
        _require(item["axis"] in {"complexity", "risk"}, f"{where}.axis is invalid")
        _text(item["statement"], f"{where}.statement")
        axes_seen.add(item["axis"])
        evidence.append(dict(item))
    _require({"complexity", "risk"} <= axes_seen, "payload.evidence must cover both axes")
    gestalt = data["gestalt"]
    gestalt_step = False
    factors: list[str] = []
    if gestalt is not None:
        g = _object(gestalt, {"factors"}, "payload.gestalt")
        _require(
            isinstance(g["factors"], list) and all(isinstance(f, str) and f for f in g["factors"]),
            "payload.gestalt.factors must be non-empty strings",
        )
        _require(len(g["factors"]) >= 3, "payload.gestalt.factors requires at least three factors")
        _require(len(set(g["factors"])) == len(g["factors"]), "payload.gestalt.factors must be distinct")
        factors = list(g["factors"])
        gestalt_step = True
    artifact = {
        "complexity": data["complexity"],
        "risk": data["risk"],
        "evidence": evidence,
        "gestalt_factors": factors,
    }
    projection = {"complexity": data["complexity"], "risk": data["risk"], "gestalt_step": gestalt_step}
    return artifact, projection


def _validate_triage(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    data = _object(payload, {"report_ids", "findings"}, "payload")
    report_ids = _unique_ids(data["report_ids"], "payload.report_ids")
    _require(
        set(report_ids) == set(expectation.expected_ids) and len(report_ids) == len(expectation.expected_ids),
        "payload.report_ids must match the exact usable raw-report set",
    )
    raw_findings = expectation.extra.get("raw_findings", {})
    _require(isinstance(raw_findings, dict), "expectation is missing registered raw-report premises")

    findings: list[dict[str, object]] = []
    canonical_seen: set[str] = set()
    source_seen: set[tuple[str, str]] = set()
    _require(isinstance(data["findings"], list), "payload.findings must be an array")
    for i, raw in enumerate(data["findings"]):
        where = f"payload.findings[{i}]"
        item = _object(
            raw,
            {"canonical_id", "sources", "current_severity", "factual", "state", "evidence_locators"},
            where,
        )
        cid = _text(item["canonical_id"], f"{where}.canonical_id")
        _require(cid not in canonical_seen, f"{where}.canonical_id must be unique")
        canonical_seen.add(cid)
        _require(
            isinstance(item["sources"], list) and bool(item["sources"]),
            f"{where}.sources must be non-empty",
        )
        sources: list[dict[str, object]] = []
        for j, raw_source in enumerate(item["sources"]):
            swhere = f"{where}.sources[{j}]"
            source = _object(raw_source, {"report_id", "finding_id", "claim", "severity", "locators"}, swhere)
            report_id = _text(source["report_id"], f"{swhere}.report_id")
            finding_id = _text(source["finding_id"], f"{swhere}.finding_id")
            key = (report_id, finding_id)
            _require(report_id in expectation.expected_ids, f"{swhere}.report_id is not a usable report")
            premise_reports = raw_findings.get(report_id, {})
            premise = premise_reports.get(finding_id) if isinstance(premise_reports, dict) else None
            _require(premise is not None, f"{swhere} does not match a registered raw finding")
            claim, severity, locators = premise
            _require(source["claim"] == claim, f"{swhere}.claim must match the raw premise exactly")
            _require(source["severity"] == severity, f"{swhere}.severity must match the raw premise exactly")
            _require(
                set(source["locators"]) == set(locators) and isinstance(source["locators"], list),
                f"{swhere}.locators must match the raw premise exactly",
            )
            _require(key not in source_seen, f"{swhere} maps a source finding more than once")
            source_seen.add(key)
            sources.append(dict(source))
        _require(item["current_severity"] in CONSEQUENCES, f"{where}.current_severity is invalid")
        _require(item["factual"] in _FACTUAL, f"{where}.factual is invalid")
        _require(item["state"] in _LEDGER_STATES, f"{where}.state is invalid")
        if item["factual"] == "UNVERIFIABLE":
            _require(item["state"] == "OPEN", f"{where} UNVERIFIABLE cannot settle a row")
        _require(
            isinstance(item["evidence_locators"], list)
            and all(isinstance(x, str) and x for x in item["evidence_locators"]),
            f"{where}.evidence_locators must be a list of non-empty strings",
        )
        reported_severity = max(
            (s["severity"] for s in sources), key=CONSEQUENCES.index
        )
        findings.append(
            {
                "id": cid,
                "sources": sources,
                "source_ids": [f"{s['report_id']}:{s['finding_id']}" for s in sources],
                "reported_severity": reported_severity,
                "current_severity": item["current_severity"],
                "factual": item["factual"],
                "state": item["state"],
                "evidence_locators": list(item["evidence_locators"]),
                "target_seal": expectation.target_seal,
            }
        )

    expected_pairs = {
        (rid, fid)
        for rid in expectation.expected_ids
        for fid in (raw_findings.get(rid) or {})
    }
    _require(source_seen == expected_pairs, "payload.findings must cover every raw finding exactly once")

    artifact = {"report_ids": report_ids, "findings": findings}
    projection = {
        "rows": [
            {
                "id": f["id"],
                "source_ids": f["source_ids"],
                "reported_severity": f["reported_severity"],
                "current_severity": f["current_severity"],
                "factual": f["factual"],
                "state": f["state"],
                "target_seal": f["target_seal"],
            }
            for f in findings
        ]
    }
    return artifact, projection


def _validate_adjudication(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    data = _object(payload, {"decisions"}, "payload")
    _require(isinstance(data["decisions"], list), "payload.decisions must be an array")
    kinds = expectation.extra.get("adjudication_kinds", {})
    _require(isinstance(kinds, dict), "expectation is missing adjudication authority kinds")

    seen: set[str] = set()
    decisions: list[dict[str, object]] = []
    for i, raw in enumerate(data["decisions"]):
        where = f"payload.decisions[{i}]"
        item = _object(
            raw, {"id", "decision", "evidence_locator", "fact_linkage", "authority_identity"}, where
        )
        ident = _text(item["id"], f"{where}.id")
        _require(ident in expectation.expected_ids, f"{where}.id is not a pending row")
        _require(ident not in seen, f"{where}.id decided more than once")
        seen.add(ident)
        _require(
            item["decision"] in {"UPHOLD", "BOUNCE", "UNDECIDED"},
            f"{where}.decision is invalid",
        )
        _text(item["evidence_locator"], f"{where}.evidence_locator")
        if item["decision"] == "UPHOLD":
            _text(item["fact_linkage"], f"{where}.fact_linkage")
            if kinds.get(ident) == "file_authorized":
                _text(item["authority_identity"], f"{where}.authority_identity")
            else:
                _require(
                    item["authority_identity"] is None,
                    f"{where}.authority_identity must be null unless file-authorized",
                )
        else:
            _require(
                item["fact_linkage"] is None,
                f"{where}.fact_linkage must be null unless UPHOLD",
            )
            _require(
                item["authority_identity"] is None,
                f"{where}.authority_identity must be null unless UPHOLD",
            )
        decisions.append(dict(item))
    _require(seen == set(expectation.expected_ids), "payload.decisions must cover every pending row exactly once")

    artifact = {"decisions": decisions}
    projection = [
        {
            "id": d["id"],
            "status": d["decision"],
            "evidence_locator": d["evidence_locator"],
            "fact_linkage": d["fact_linkage"],
            "authority_identity": d["authority_identity"],
        }
        for d in decisions
    ]
    return artifact, projection


def _validate_fix(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    data = _object(
        payload, {"changes", "test_trace", "external_actions_attempted", "external_actions_note"}, "payload"
    )
    _require(isinstance(data["changes"], list), "payload.changes must be an array")
    changes: list[dict[str, object]] = []
    paths_seen: set[str] = set()
    bound_ids: set[str] = set()
    for i, raw in enumerate(data["changes"]):
        where = f"payload.changes[{i}]"
        item = _object(
            raw, {"path", "description", "ledger_ids", "twin_search_pattern", "twin_search_count"}, where
        )
        path = _text(item["path"], f"{where}.path")
        _require(path not in paths_seen, f"{where}.path is bound more than once")
        paths_seen.add(path)
        _text(item["description"], f"{where}.description")
        ledger_ids = _unique_ids(item["ledger_ids"], f"{where}.ledger_ids")
        _require(bool(ledger_ids), f"{where}.ledger_ids must be non-empty")
        _require(
            set(ledger_ids) <= set(expectation.expected_ids),
            f"{where}.ledger_ids must be authorized OPEN rows",
        )
        _text(item["twin_search_pattern"], f"{where}.twin_search_pattern")
        _require(
            type(item["twin_search_count"]) is int and item["twin_search_count"] >= 0,
            f"{where}.twin_search_count must be a non-negative integer",
        )
        bound_ids |= set(ledger_ids)
        changes.append(dict(item))
    if changes:
        _require(bool(bound_ids), "payload.changes must bind at least one authorized ledger ID")

    _require(isinstance(data["test_trace"], list), "payload.test_trace must be an array")
    trace: list[dict[str, object]] = []
    for i, raw in enumerate(data["test_trace"]):
        where = f"payload.test_trace[{i}]"
        item = _object(raw, {"test_path", "spec_ids"}, where)
        test_path = _text(item["test_path"], f"{where}.test_path")
        _require(test_path in paths_seen, f"{where}.test_path must be one of the changed paths")
        _unique_ids(item["spec_ids"], f"{where}.spec_ids")
        trace.append(dict(item))

    attempted = data["external_actions_attempted"]
    _require(type(attempted) is bool, "payload.external_actions_attempted must be boolean")
    if attempted:
        _text(data["external_actions_note"], "payload.external_actions_note")
    else:
        _require(
            data["external_actions_note"] is None,
            "payload.external_actions_note must be null when nothing was attempted",
        )

    artifact = {
        "changes": changes,
        "test_trace": trace,
        "external_actions_attempted": attempted,
        "external_actions_note": data["external_actions_note"],
    }
    projection = {
        "bound_ledger_ids": sorted(bound_ids),
        "external_actions_attempted": attempted,
    }
    return artifact, projection


def _validate_final_readiness(payload: object, expectation: RoleExpectation) -> tuple[dict, dict]:
    if not isinstance(payload, dict):
        raise RoleValidationError("payload must be an object")
    verdict = payload.get("verdict")
    if verdict == "UPHOLD":
        _object(payload, {"verdict"}, "payload")
        return {"verdict": "UPHOLD", "source_findings": ()}, {"verdict": "UPHOLD", "source_findings": []}
    _require(verdict == "BLOCK", "payload.verdict must be UPHOLD or BLOCK")
    data = _object(payload, {"verdict", "evidence", "procedural_blocker", "source_findings"}, "payload")
    _text(data["evidence"], "payload.evidence")
    if data["procedural_blocker"] is not None:
        _text(data["procedural_blocker"], "payload.procedural_blocker")
    findings = _parse_source_findings(data["source_findings"])
    _require(findings is not None, "payload.source_findings is malformed")
    assert findings is not None
    artifact = {
        "verdict": "BLOCK",
        "evidence": data["evidence"],
        "procedural_blocker": data["procedural_blocker"],
        "source_findings": findings,
    }
    projection = {
        "verdict": "BLOCK",
        "source_findings": [
            {"id": f.finding_id, "claim": f.claim, "severity": f.severity, "locator_ids": list(f.locator_ids)}
            for f in findings
        ],
    }
    return artifact, projection


_ROLE_VALIDATORS = {
    "evidence": _validate_evidence,
    "inventory-owner": _validate_inventory_owner,
    "inventory-challenge": _validate_inventory_challenge,
    "inventory-revision": _validate_inventory_revision,
    "rating": _validate_rating,
    "triage": _validate_triage,
    "adjudication": _validate_adjudication,
    "fix": _validate_fix,
    "final-readiness": _validate_final_readiness,
}


def validate_role_json(role_id: str, body: bytes, expectation: RoleExpectation) -> ValidatedRoleArtifact:
    if role_id not in _ROLE_VALIDATORS:
        raise RoleValidationError(f"unknown role: {role_id!r}")
    if not isinstance(expectation, RoleExpectation):
        raise TypeError("expectation must be a RoleExpectation")
    payload = _envelope(body, role_id, expectation)
    artifact, projection = _ROLE_VALIDATORS[role_id](payload, expectation)
    return ValidatedRoleArtifact(role_id=role_id, body=body, artifact=artifact, projection=projection)
