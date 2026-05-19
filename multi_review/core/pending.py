from __future__ import annotations
import os
import shutil
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal

import yaml

PENDING_TTL_DAYS = 7

Status = Literal["awaiting-pass-2", "resuming", "complete", "aborted"]

@dataclass
class PendingPair:
    pair_id: str
    pass1_run_id: str
    pass2_run_id: str | None
    modes: dict[str, str]
    prompt_file: str | None
    status: Status
    delay_type: Literal["foreground", "background"]
    notification_task_id: str | None
    created_iso: str
    git_head: str | None
    git_dirty: bool
    if_drift: Literal["ignore", "abort", "ask"]

def _pair_dir(pending_root: Path, pair_id: str) -> Path:
    return pending_root / pair_id

def write_meta(pending_root: Path, meta: PendingPair) -> None:
    d = _pair_dir(pending_root, meta.pair_id)
    d.mkdir(parents=True, exist_ok=True)
    target = d / "meta.yaml"
    fd, tmp = tempfile.mkstemp(prefix="meta-", suffix=".yaml", dir=str(d))
    try:
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(asdict(meta), f, sort_keys=False)
        os.replace(tmp, target)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise

def read_meta(pending_root: Path, pair_id: str) -> PendingPair:
    target = _pair_dir(pending_root, pair_id) / "meta.yaml"
    data = yaml.safe_load(target.read_text())
    return PendingPair(**data)

def transition_status(pending_root: Path, pair_id: str, *, expected: Status, new: Status) -> bool:
    lock = _pair_dir(pending_root, pair_id) / ".status.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        meta = read_meta(pending_root, pair_id)
        if meta.status != expected:
            return False
        meta.status = new
        write_meta(pending_root, meta)
        return True
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)

def list_pending(pending_root: Path) -> list[PendingPair]:
    if not pending_root.exists():
        return []
    out = []
    for child in sorted(pending_root.iterdir()):
        meta_path = child / "meta.yaml"
        if meta_path.exists():
            out.append(read_meta(pending_root, child.name))
    return out

def sweep_expired(pending_root: Path, *, ttl_days: int = PENDING_TTL_DAYS) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    swept = []
    for meta in list_pending(pending_root):
        created = datetime.fromisoformat(meta.created_iso.replace("Z", "+00:00"))
        if created < cutoff:
            shutil.rmtree(_pair_dir(pending_root, meta.pair_id), ignore_errors=True)
            swept.append(meta.pair_id)
    return swept
