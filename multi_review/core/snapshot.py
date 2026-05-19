# multi_review/core/snapshot.py
from __future__ import annotations
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass
class SnapshotDiff:
    status: Literal["clean", "drifted"]
    changed_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    unified_diffs: dict[str, str] = field(default_factory=dict)

def _snap_path(snapshot_dir: Path, source: Path) -> Path:
    rel = source.resolve().as_posix().lstrip("/")
    return snapshot_dir / rel

def create_snapshot(
    files: list[Path],
    snapshot_dir: Path,
    context_files: list[Path] | None = None,
) -> None:
    """Snapshot input files + context files (per spec §9.1)."""
    if context_files is None:
        context_files = []
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for f in [*files, *context_files]:
        target = _snap_path(snapshot_dir, f)
        target.parent.mkdir(parents=True, exist_ok=True)
        if f.exists():
            shutil.copy2(f, target)

def diff_snapshot(
    files: list[Path],
    snapshot_dir: Path,
    context_files: list[Path] | None = None,
) -> SnapshotDiff:
    import difflib
    if context_files is None:
        context_files = []
    diff = SnapshotDiff(status="clean")
    for f in [*files, *context_files]:
        target = _snap_path(snapshot_dir, f)
        if not target.exists():
            continue
        if not f.exists():
            diff.deleted_files.append(str(f.resolve()))
            diff.status = "drifted"
            continue
        old = target.read_text(errors="replace").splitlines(keepends=True)
        new = f.read_text(errors="replace").splitlines(keepends=True)
        if old != new:
            diff.changed_files.append(str(f.resolve()))
            diff.unified_diffs[str(f.resolve())] = "".join(
                difflib.unified_diff(old, new,
                                     fromfile=f"snapshot/{f.name}",
                                     tofile=f"current/{f.name}")
            )
            diff.status = "drifted"
    return diff

def cleanup_snapshot(snapshot_dir: Path) -> None:
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
