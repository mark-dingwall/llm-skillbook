# multi_review/core/promptfile.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import yaml

from multi_review.core.reviewers import ALL_REVIEWERS, DEFAULT_REVIEWERS

class ValidationError(Exception):
    pass

@dataclass
class PromptFile:
    prompt_format_version: int
    task: Literal["code", "plan", "security", "generic", "custom"]
    files: list[str]
    context_files: list[str] = field(default_factory=list)
    custom_prompt: str | None = None
    synthesizer: str = "claude"
    reviewers: list[str] = field(default_factory=lambda: list(DEFAULT_REVIEWERS))
    models: dict[str, str] = field(default_factory=dict)

_VALID_TASKS = {"code", "plan", "security", "generic", "custom"}
_KNOWN_REVIEWERS = set(ALL_REVIEWERS)  # valid set (includes opt-in reviewers like grok)
_VALID_SYNTHESIZERS = _KNOWN_REVIEWERS | {"none"}

_REQUIRED_FIELDS = {"prompt_format_version", "task", "files"}
_REMOVED_KEYS = ("mode", "model_effort", "if_drift", "output_dir", "save_as", "harvest")

def fill_defaults(raw: dict) -> PromptFile:
    found = [key for key in _REMOVED_KEYS if key in raw]
    if found:
        raise ValidationError(
            "prompt YAML key(s) removed in v0.3.0, delete before retrying: "
            + ", ".join(found)
        )
    raw = dict(raw)
    for f in _REQUIRED_FIELDS:
        if f not in raw:
            raise ValidationError(f"missing required field: {f!r}")
    raw.setdefault("context_files", [])
    raw.setdefault("custom_prompt", None)
    raw.setdefault("synthesizer", "claude")
    raw.setdefault("reviewers", list(DEFAULT_REVIEWERS))
    raw.setdefault("models", {})
    try:
        return PromptFile(**raw)
    except TypeError as exc:
        raise ValidationError(str(exc)) from exc

def _resolve_path(p: str, base: Path | None) -> Path:
    try:
        if "\0" in p:
            raise ValueError("embedded null byte")
        pp = Path(p)
        if pp.is_absolute() or base is None:
            return pp
        return (base / pp).resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValidationError(f"invalid path {p!r}: {exc}") from exc

def validate(pf: PromptFile, base_dir: Path | None = None) -> None:
    # Required-field + type + enum checks (cheap; catches malformed prompts upstream
    # of fanout so we never burn ~thousands of tokens × N reviewers on garbage).
    if type(pf.prompt_format_version) is not int:
        raise ValidationError("prompt_format_version must be an integer")
    if not isinstance(pf.task, str):
        raise ValidationError("task must be a string")
    if not isinstance(pf.synthesizer, str):
        raise ValidationError("synthesizer must be a string")
    for field_name in ("files", "context_files", "reviewers"):
        value = getattr(pf, field_name)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValidationError(f"{field_name} must be a list of strings")
    for field_name in ("models",):
        value = getattr(pf, field_name)
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in value.items()
        ):
            raise ValidationError(f"{field_name} must be a mapping of strings to strings")
    for field_name in ("custom_prompt",):
        value = getattr(pf, field_name)
        if value is not None and not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string or null")
    if pf.prompt_format_version == 1:
        raise ValidationError(
            "prompt_format_version: 1 is no longer supported — v0.3 removed inline delivery "
            "and 6 deprecated fields (mode, if_drift, harvest, output_dir, save_as, model_effort). "
            "Set prompt_format_version: 2."
        )
    if pf.prompt_format_version != 2:
        raise ValidationError(f"unknown prompt_format_version: {pf.prompt_format_version}")
    if pf.task not in _VALID_TASKS:
        raise ValidationError(f"task must be one of {_VALID_TASKS}, got {pf.task!r}")
    if pf.synthesizer not in _VALID_SYNTHESIZERS:
        raise ValidationError(f"synthesizer must be one of {_VALID_SYNTHESIZERS}, got {pf.synthesizer!r}")
    if not pf.files:
        raise ValidationError("files: must list at least one path")
    if pf.task == "custom" and not pf.custom_prompt:
        raise ValidationError("task=custom requires custom_prompt body")
    if not pf.reviewers:
        raise ValidationError("reviewers: must not be empty")
    for r in pf.reviewers:
        if r not in _KNOWN_REVIEWERS:
            raise ValidationError(f"reviewers contains unknown CLI {r!r}; known: {_KNOWN_REVIEWERS}")
    for cli in pf.models:
        if cli not in _KNOWN_REVIEWERS:
            raise ValidationError(f"models.{cli!r} is not a known reviewer; known: {_KNOWN_REVIEWERS}")
    for p in pf.files:
        if not _resolve_path(p, base_dir).exists():
            raise ValidationError(f"files: path does not exist on disk: {p}")
    for p in pf.context_files:
        if not _resolve_path(p, base_dir).exists():
            raise ValidationError(f"context_files: path does not exist on disk: {p}")

def load_promptfile(path: Path) -> PromptFile:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ValidationError(f"{path}: prompt file is not valid UTF-8: {exc}") from exc
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValidationError(f"{path}: top-level must be a mapping")
    pf = fill_defaults(raw)
    validate(pf, base_dir=path.parent.resolve())
    return pf
