"""Read and validate persisted reviewer artifacts for interactive aggregation."""
from __future__ import annotations

import json
import stat
from pathlib import Path

from multi_review.core.adapters import Usage
from multi_review.core.fanout import ReviewerResult
from multi_review.core.prompt import classify_review_ok


_USAGE_FIELDS = {"input_tokens", "output_tokens", "cached_tokens", "tool_calls"}


def failed_reviewer(cli: str, error: str, *, text: str = "", stderr_tail: str = "") -> ReviewerResult:
    return ReviewerResult(
        cli=cli, ok=False, text=text, stderr_tail=stderr_tail,
        usage=None, elapsed=0.0, error=error,
    )


def read_state_file(path: Path) -> tuple[object | None, str | None]:
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            return None, f"invalid reviewer state: not a regular file: {path}"
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "reviewer produced no state file"
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"invalid reviewer state: {exc}"


def read_review_body(path: Path) -> tuple[str, str | None]:
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            return "", f"review body is not a regular file: {path}"
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return "", None
    except (OSError, UnicodeError) as exc:
        return "", f"cannot read review body: {exc}"


def result_from_state(cli: str, state: object, review_text: str) -> ReviewerResult:
    """Turn one parsed state object and body into a qualified reviewer result."""
    if not isinstance(state, dict):
        return failed_reviewer(cli, "invalid reviewer state: expected an object", text=review_text)

    if state.get("cli") != cli:
        return failed_reviewer(cli, "invalid reviewer state: cli does not match artifact name", text=review_text)
    if type(state.get("ok")) is not bool:
        return failed_reviewer(cli, "invalid reviewer state: ok must be a boolean", text=review_text)
    if "body" in state and not isinstance(state["body"], str):
        return failed_reviewer(cli, "invalid reviewer state: body must be a string", text=review_text)

    duration = state.get("duration_seconds", 0.0)
    if duration is None:
        duration = 0.0
    if type(duration) not in (int, float) or duration < 0:
        return failed_reviewer(cli, "invalid reviewer state: duration_seconds must be non-negative", text=review_text)

    stderr_tail = state.get("stderr_tail", "")
    if not isinstance(stderr_tail, str):
        return failed_reviewer(cli, "invalid reviewer state: stderr_tail must be a string", text=review_text)
    final_model = state.get("final_model")
    if final_model is not None and not isinstance(final_model, str):
        return failed_reviewer(cli, "invalid reviewer state: final_model must be a string or null", text=review_text)
    error = state.get("error")
    if error is not None and not isinstance(error, str):
        return failed_reviewer(cli, "invalid reviewer state: error must be a string or null", text=review_text)

    usage_raw = state.get("usage")
    usage: Usage | None = None
    if usage_raw is not None:
        if (
            not isinstance(usage_raw, dict)
            or set(usage_raw) - _USAGE_FIELDS
            or any(type(value) is not int or value < 0 for value in usage_raw.values())
        ):
            return failed_reviewer(cli, "invalid reviewer state: usage must contain non-negative integers", text=review_text)
        usage = Usage(**usage_raw)

    ok, classification_error = classify_review_ok(state["ok"], review_text)
    return ReviewerResult(
        cli=cli,
        ok=ok,
        text=review_text,
        stderr_tail=stderr_tail,
        usage=usage,
        elapsed=float(duration),
        model_used=final_model,
        error=error or classification_error,
    )
