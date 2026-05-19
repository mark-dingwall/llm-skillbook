# multi_review/core/paths.py
from __future__ import annotations
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path


def project_state_dir(cwd: Path) -> Path:
    return cwd / ".multi-review"


def run_dir(cwd: Path, run_id: str) -> Path:
    return project_state_dir(cwd) / "sessions" / run_id


def pending_pair_dir(cwd: Path, pair_id: str) -> Path:
    return project_state_dir(cwd) / "pending" / pair_id


def _dev_checkout_runs() -> Path | None:
    """If invoked from a multi-review dev checkout, return <repo>/runs."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "multi_review" / "core" / "paths.py").exists() and (parent / "runs").exists():
            return parent / "runs"
    return None


def central_runs_dir() -> Path:
    """Resolution order per spec §4.2:
    1. ~/.claude/skills/multi-review/config.json `central_path`.
    2. Dev checkout `<repo>/runs/`.
    3. $XDG_DATA_HOME/multi-review/ (Linux).
    4. ~/Library/Application Support/multi-review/ (macOS).
    5. ~/.local/share/multi-review/ (Linux fallback).
    """
    home = Path(os.path.expanduser("~"))
    cfg = home / ".claude" / "skills" / "multi-review" / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text())
            if data.get("central_path"):
                return Path(data["central_path"])
        except (json.JSONDecodeError, OSError):
            pass
    dev = _dev_checkout_runs()
    if dev is not None:
        return dev
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "multi-review"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "multi-review"
    return home / ".local" / "share" / "multi-review"


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


def _short_token() -> str:
    return secrets.token_hex(2)


def generate_run_id() -> str:
    return f"run-{_timestamp_slug()}-{_short_token()}"


def generate_pair_id() -> str:
    return f"pair-{_timestamp_slug()}-{_short_token()}"


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
