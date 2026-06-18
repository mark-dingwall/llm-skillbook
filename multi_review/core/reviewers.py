"""multi_review.core.reviewers — reviewer detection, CLI_SPEC, command builder.

Single source of truth for:
  - ALL_REVIEWERS list
  - detect_self / detect_available / resolve_reviewers
  - CLI_SPEC table (invocation recipes)
  - build_command, make_adapter
"""
from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# -------- Reviewer list --------

ALL_REVIEWERS: list[str] = ["claude", "agy", "codex", "opencode"]

# -------- CLI detection + self-skip --------

def detect_self() -> str:
    if os.environ.get("ANTIGRAVITY_AGENT") == "1":
        return "none"
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    if os.environ.get("GEMINI_CLI"):
        return "gemini"
    if os.environ.get("CODEX_ENV"):
        return "codex"
    # opencode sets OPENCODE=1 in the child env of every shell/agent invocation.
    if os.environ.get("OPENCODE"):
        return "opencode"
    return ""


def detect_available() -> list[str]:
    return [c for c in ALL_REVIEWERS if shutil.which(c)]


def resolve_reviewers(
    *,
    explicit: list[str] | None,
    skip_self: bool,
    self_cli: str,
    available: set[str],
) -> list[str]:
    """Return the ordered list of reviewers to run.

    Parameters
    ----------
    explicit:
        Non-None means the user passed --reviewers; self-skip is ignored for
        explicit lists (invariant: explicit --reviewers always wins).
    skip_self:
        Drop the host CLI from the auto-resolved set (opt-in; default False).
    self_cli:
        The host CLI name as returned by detect_self().
    available:
        Set of CLIs that are currently available on PATH. Callers should pass
        ``set(detect_available())`` — kept separate so the function is pure /
        testable without touching the filesystem.
    """
    is_explicit = explicit is not None
    base = explicit if is_explicit else list(ALL_REVIEWERS)
    out = []
    for cli in base:
        # Self-skip is opt-in via --skip-self. Default behaviour: a fresh subprocess
        # of the host CLI has independent context and is a valid reviewer.
        # Explicit --reviewers always honoured (skip_self ignored when explicit).
        if skip_self and not is_explicit and cli == self_cli and self_cli not in ("", "none"):
            continue
        if cli not in available:
            continue
        if cli not in out:
            out.append(cli)
    return out


# -------- Invocation commands --------

# Per-CLI invocation recipe. "base" + optional stream_flags + optional
# --model/-m override (or default_args when no override) + optional stdin
# sentinel. Prompt is always written to the child's stdin (see run_reviewer)
# so it never appears in /proc/PID/cmdline.
CLI_SPEC: dict[str, dict] = {
    "claude": {
        "base": ["claude", "-p"],
        "stream_flags": ["--output-format", "stream-json",
                         "--include-partial-messages", "--verbose"],
        "model_flag": "--model",
        "default_args": ["--model", "opus", "--effort", "xhigh"],
        "stdin_sentinel": None,
    },
    "agy": {
        "base": ["agy", "--print"],
        "stream_flags": [],
        "model_flag": "--model",
        # default_args=[] — let agy pick its default model. v0.2.1 model-config
        # feature will read user-specified model from TOML. Verified working
        # values for explicit pinning: "Gemini 3.1 Pro (High)" (default-ish),
        # "Gemini 3.5 Flash (Low|Medium|High)" (cheaper variants).
        "default_args": [],
        "stdin_sentinel": None,
    },
    "codex": {
        "base": ["codex", "exec", "--skip-git-repo-check"],
        "stream_flags": ["--json"],
        "model_flag": "--model",
        "default_args": ["--model", "gpt-5.5",
                         "-c", 'model_reasoning_effort="high"'],
        "stdin_sentinel": "-",
    },
    "opencode": {
        "base": ["opencode", "run"],
        "stream_flags": ["--format", "json"],
        "model_flag": "--model",
        "default_args": ["--model", "openrouter/deepseek/deepseek-v4-pro"],
        "stdin_sentinel": "-",
    },
}


def build_command(cli: str, model: str | None, *, streaming: bool) -> list[str]:
    try:
        spec = CLI_SPEC[cli]
    except KeyError:
        raise ValueError(f"Unknown CLI: {cli}")
    cmd = list(spec["base"])
    if streaming:
        cmd += spec["stream_flags"]
    if model:
        cmd += [spec["model_flag"], model]
    else:
        cmd += spec.get("default_args", [])
    if spec["stdin_sentinel"]:
        cmd.append(spec["stdin_sentinel"])
    return cmd


def make_adapter(cli: str):
    from multi_review.core.adapters import ADAPTER_FOR, ProgressAdapter  # noqa: F401
    return ADAPTER_FOR[cli]()
