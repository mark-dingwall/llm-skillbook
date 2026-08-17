"""Strict version-1 review profiles and tier-default policy resolution.

Profiles are optional local YAML sparse overlays on tier defaults (design
Sec. 7).  They may only pin capability/model for the fixed normal roles and
the fixed claude/codex multi-review pair, and set a run deadline; they can
never touch tier, round caps, staffing thresholds, participants, or
synthesis.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CAPABILITIES = ("mid-tier", "one-above-mid", "most-capable")
MULTI_REVIEW_PARTICIPANTS = ("claude", "codex")
SUPPORTED_VERSION = 1


class ProfileError(Exception):
    """A selected profile is missing or malformed; callers never fall back silently."""


# --- strict YAML: reject duplicate mapping keys at every nesting level ---


class _StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.Node, deep: bool = False) -> dict:
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, f"expected a mapping node, but found {node.id}", node.start_mark
        )
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _load_yaml_strict(text: str, path: Path) -> object:
    try:
        return yaml.load(text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise ProfileError(f"profile is not valid YAML: {path}: {exc}") from exc


# --- schema validation ---


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProfileError(message)


def _object(value: object, path: str, keys: set[str]) -> dict:
    _require(isinstance(value, dict), f"{path} must be a mapping")
    assert isinstance(value, dict)
    unknown = set(value) - keys
    _require(not unknown, f"{path} has unknown fields: {sorted(unknown)}")
    return value


def _capability(value: object, path: str) -> str:
    _require(isinstance(value, str) and value in CAPABILITIES, f"{path} is not a supported capability")
    assert isinstance(value, str)
    return value


def _model(value: object, path: str) -> str:
    _require(isinstance(value, str) and bool(value), f"{path} must be a non-empty string")
    assert isinstance(value, str)
    return value


@dataclass(frozen=True)
class RolePins:
    capability: str | None = None
    model: str | None = None
    fallback_capability: str | None = None
    fallback_model: str | None = None
    multi_review_models: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewProfile:
    version: int
    max_time_seconds: int | None
    holistic: RolePins
    adversarial: RolePins
    specialists: RolePins


def _multi_review(value: object, path: str) -> dict[str, str]:
    data = _object(value, path, {"models"})
    models = data.get("models", {})
    _require(isinstance(models, dict), f"{path}.models must be a mapping")
    assert isinstance(models, dict)
    unknown = set(models) - set(MULTI_REVIEW_PARTICIPANTS)
    _require(not unknown, f"{path}.models may only pin {MULTI_REVIEW_PARTICIPANTS}")
    _require(
        set(models) == set(MULTI_REVIEW_PARTICIPANTS),
        f"{path}.models must pin the full non-empty {MULTI_REVIEW_PARTICIPANTS} pair",
    )
    out: dict[str, str] = {}
    for key, raw in models.items():
        out[key] = _model(raw, f"{path}.models.{key}")
    return out


def _holistic(value: object) -> RolePins:
    data = _object(value, "holistic", {"capability", "model", "fallback_capability", "fallback_model", "multi_review"})
    capability = _capability(data["capability"], "holistic.capability") if "capability" in data else None
    model = _model(data["model"], "holistic.model") if "model" in data else None
    fallback_capability = (
        _capability(data["fallback_capability"], "holistic.fallback_capability")
        if "fallback_capability" in data
        else capability
    )
    fallback_model = (
        _model(data["fallback_model"], "holistic.fallback_model")
        if "fallback_model" in data
        else model
    )
    multi_review_models = _multi_review(data["multi_review"], "holistic.multi_review") if "multi_review" in data else {}
    return RolePins(capability, model, fallback_capability, fallback_model, multi_review_models)


def _normal_role(value: object, path: str) -> RolePins:
    data = _object(value, path, {"capability", "model"})
    capability = _capability(data["capability"], f"{path}.capability") if "capability" in data else None
    model = _model(data["model"], f"{path}.model") if "model" in data else None
    return RolePins(capability, model, None, None, {})


def _parse_profile(raw: object, path: Path) -> ReviewProfile:
    data = _object(raw, "profile", {"version", "max_time_seconds", "holistic", "adversarial", "specialists"})
    _require(
        type(data.get("version")) is int and data.get("version") == SUPPORTED_VERSION,
        f"profile version must be {SUPPORTED_VERSION}: {path}",
    )
    max_time = data.get("max_time_seconds")
    if max_time is not None:
        _require(
            type(max_time) is int and max_time > 0,
            "max_time_seconds must be a positive integer",
        )
    holistic = _holistic(data["holistic"]) if "holistic" in data else RolePins()
    adversarial = _normal_role(data["adversarial"], "adversarial") if "adversarial" in data else RolePins()
    specialists = _normal_role(data["specialists"], "specialists") if "specialists" in data else RolePins()
    return ReviewProfile(SUPPORTED_VERSION, max_time, holistic, adversarial, specialists)


# --- selector resolution: bare name (XDG) or explicit path ---


def _is_bare_name(selector: str) -> bool:
    return "/" not in selector and "\\" not in selector


def _resolve_bare_name(selector: str, xdg_config_home: Path | None) -> Path:
    _require(selector not in ("", ".", ".."), f"profile name is not a safe basename: {selector!r}")
    base = xdg_config_home if xdg_config_home is not None else Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    profiles_dir = (Path(base) / "review-loop" / "profiles").resolve()
    resolved = (profiles_dir / f"{selector}.yaml").resolve()
    _require(
        resolved == profiles_dir / f"{selector}.yaml" and resolved.parent == profiles_dir,
        f"profile name escapes the profiles directory: {selector!r}",
    )
    return resolved


def load_profile(selector: str, xdg_config_home: Path | None) -> ReviewProfile:
    _require(isinstance(selector, str) and bool(selector), "profile selector must be a non-empty string")
    path = _resolve_bare_name(selector, xdg_config_home) if _is_bare_name(selector) else Path(selector)
    try:
        text = path.read_text()
    except OSError as exc:
        raise ProfileError(f"profile not found: {path}") from exc
    raw = _load_yaml_strict(text, path)
    return _parse_profile(raw, path)


# --- policy resolution: profile overlay on tier defaults ---


@dataclass(frozen=True)
class InvocationIntent:
    target: Path
    base: str | None
    head: str | None
    exclusions: tuple[str, ...]
    review_profile: str | None
    max_time_seconds: int | None
    no_confirm: bool
    ground_truth: tuple[Path, ...]
    run_root: Path | None = None
    # Operator-supplied tier intent (design Sec. 4: "Resolve invocation
    # intent before dispatch: optional tier, profile, maximum time in
    # seconds, and confirmation override"). None means automatic
    # derivation; preflight only records this intent, it never derives a
    # tier -- that still requires Stage 0's rating dispatch.
    tier: str | None = None


@dataclass(frozen=True)
class RunPolicy:
    tier: str
    max_time_seconds: int | None
    holistic_capability: str | None
    holistic_model: str | None
    holistic_fallback_capability: str | None
    holistic_fallback_model: str | None
    holistic_multi_review_models: dict[str, str]
    adversarial_capability: str | None
    adversarial_model: str | None
    specialists_capability: str | None
    specialists_model: str | None


def resolve_policy(invocation: InvocationIntent, profile: ReviewProfile | None, derived_tier: str) -> RunPolicy:
    holistic = profile.holistic if profile else RolePins()
    adversarial = profile.adversarial if profile else RolePins()
    specialists = profile.specialists if profile else RolePins()
    max_time_seconds = invocation.max_time_seconds
    if max_time_seconds is None and profile is not None:
        max_time_seconds = profile.max_time_seconds
    return RunPolicy(
        tier=derived_tier,
        max_time_seconds=max_time_seconds,
        holistic_capability=holistic.capability,
        holistic_model=holistic.model,
        holistic_fallback_capability=holistic.fallback_capability,
        holistic_fallback_model=holistic.fallback_model,
        holistic_multi_review_models=dict(holistic.multi_review_models),
        adversarial_capability=adversarial.capability,
        adversarial_model=adversarial.model,
        specialists_capability=specialists.capability,
        specialists_model=specialists.model,
    )
