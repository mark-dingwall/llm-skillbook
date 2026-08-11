# multi_review/core/paths.py
from __future__ import annotations
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


def project_state_dir(cwd: Path) -> Path:
    return cwd / ".multi-review"


def run_dir(cwd: Path, run_id: str) -> Path:
    return project_state_dir(cwd) / "sessions" / run_id


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


def _short_token() -> str:
    return secrets.token_hex(2)


def generate_run_id() -> str:
    return f"run-{_timestamp_slug()}-{_short_token()}"


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
