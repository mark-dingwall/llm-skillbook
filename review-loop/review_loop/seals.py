"""Target/input sealing, git identity binding, and deterministic deltas.

Establishes the Stage 0 target-baseline identity and the call-input
identities bound to it.  Filesystem/git integration lives here; state.py
must never import this module.
"""
from __future__ import annotations

import os
import stat
import struct
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .artifacts import bytes_digest, canonical_bytes, digest

SCHEMA_VERSION = 1


class SealError(Exception):
    """A target, input, or delta could not be sealed; callers fail closed."""


@dataclass(frozen=True)
class GitPolicy:
    enabled: bool
    base: str | None = None
    head: str | None = None  # None means the current working tree
    include_untracked: bool = False
    include_index: bool = True
    git_dir_outside_target: bool = True


@dataclass(frozen=True)
class SealEntry:
    path: str  # POSIX-style, relative to the sealed root
    kind: str  # "file" | "dir"
    mode: int  # permission bits (mode & 0o7777)
    content_digest: str | None  # sha256 hex for files; None for dirs


@dataclass(frozen=True)
class TargetSeal:
    schema_version: int
    root: str
    tree_digest: str
    entries: tuple[SealEntry, ...]
    git_dir_outside_target: bool | None
    git_base_commit: str | None
    git_head_commit: str | None
    git_index_digest: str | None
    digest: str  # binds tree_digest and git identity together


@dataclass(frozen=True)
class InputSeal:
    target_seal: str
    digest: str
    entries: tuple[SealEntry, ...]


@dataclass(frozen=True)
class DeltaEntry:
    path: str
    change: str  # "added" | "removed" | "changed"
    before_type: str | None
    after_type: str | None
    content_changed: bool
    mode_changed: bool


@dataclass(frozen=True)
class DeltaArtifact:
    output_path: Path
    digest: str
    before_seal: str
    after_seal: str
    entries: tuple[DeltaEntry, ...]
    git_index_changed: bool


def _read_all(fd: int) -> bytes:
    chunks = []
    while True:
        chunk = os.read(fd, 1 << 20)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _admit(dir_fd: int, name: str) -> tuple[str, int, str | None, int]:
    """Descriptor-relative admission check for one directory entry.

    Rejects symlinks/FIFOs/sockets/devices/unreadable entries and any entry
    whose type or identity differs between the lstat used for enumeration
    and the descriptor actually opened, closing the race a caller could use
    to swap a regular file for a symlink between the two.
    """
    try:
        lst = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except OSError as exc:
        raise SealError(f"unreadable entry: {name}") from exc
    mode = lst.st_mode
    if stat.S_ISLNK(mode):
        raise SealError(f"symlink rejected: {name}")
    if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise SealError(f"unsupported entry type rejected: {name}")
    flags = os.O_RDONLY | os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=dir_fd)
    except OSError as exc:
        raise SealError(f"unreadable entry: {name}") from exc
    try:
        fst = os.fstat(fd)
        if (
            (fst.st_dev, fst.st_ino) != (lst.st_dev, lst.st_ino)
            or stat.S_ISREG(lst.st_mode) != stat.S_ISREG(fst.st_mode)
            or stat.S_ISDIR(lst.st_mode) != stat.S_ISDIR(fst.st_mode)
        ):
            raise SealError(f"type or identity changed during enumeration: {name}")
        if stat.S_ISREG(fst.st_mode):
            content_digest = bytes_digest(_read_all(fd))
            return "file", fst.st_mode & 0o7777, content_digest, fd
        return "dir", fst.st_mode & 0o7777, None, fd
    except Exception:
        os.close(fd)
        raise


def _open_root(root: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(str(root), flags)
    except OSError as exc:
        raise SealError(f"cannot open target root: {root}") from exc


def _walk(dir_fd: int, prefix: str, out: list[SealEntry], root_exclude: frozenset[str] = frozenset()) -> None:
    with os.scandir(dir_fd) as it:
        names = sorted(entry.name for entry in it)
    if not prefix:
        names = [name for name in names if name not in root_exclude]
    for name in names:
        rel = name if not prefix else f"{prefix}/{name}"
        kind, mode, content_digest, fd = _admit(dir_fd, name)
        try:
            out.append(SealEntry(rel, kind, mode, content_digest))
            if kind == "dir":
                _walk(fd, rel, out)
        finally:
            os.close(fd)


def _encode_entries(entries: Sequence[SealEntry]) -> bytes:
    """NUL-safe length-prefixed canonical framing (no shell word splitting)."""
    parts = []
    for entry in entries:
        path_bytes = entry.path.encode("utf-8")
        digest_bytes = bytes.fromhex(entry.content_digest) if entry.content_digest else b""
        parts.append(struct.pack(">B", 0 if entry.kind == "file" else 1))
        parts.append(struct.pack(">I", len(path_bytes)))
        parts.append(path_bytes)
        parts.append(struct.pack(">H", entry.mode))
        parts.append(struct.pack(">B", len(digest_bytes)))
        parts.append(digest_bytes)
    return b"".join(parts)


def _resolve_ref(root: Path, ref: str | None) -> str:
    if not ref or not ref.strip():
        raise SealError("git delta contract has an absent ref")
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", ref],
        capture_output=True,
        text=True,
    )
    stderr = result.stderr or ""
    if "ambiguous" in stderr.lower():
        raise SealError(f"git ref is ambiguous: {ref}")
    if result.returncode != 0:
        raise SealError(f"git ref is absent or invalid: {ref}")
    resolved = result.stdout.strip()
    if not resolved:
        raise SealError(f"git ref is absent or invalid: {ref}")
    return resolved


def _git_index_digest(root: Path, git_policy: GitPolicy) -> str | None:
    if not git_policy.include_index:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-s", "-z"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise SealError("cannot read git index")
    payload = result.stdout
    if git_policy.include_untracked:
        others = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
            capture_output=True,
        )
        if others.returncode != 0:
            raise SealError("cannot enumerate untracked files")
        payload += b"\x00UNTRACKED\x00" + others.stdout
    return bytes_digest(payload)


def seal_target(root: Path, git_policy: GitPolicy) -> TargetSeal:
    root = Path(root)
    if not root.is_dir():
        raise SealError(f"target root is not a directory: {root}")
    root_fd = _open_root(root)
    entries: list[SealEntry] = []
    try:
        # .git metadata is never a target-tree input; its identity is bound
        # separately below as the git index digest.
        _walk(root_fd, "", entries, root_exclude=frozenset({".git"}))
    finally:
        os.close(root_fd)
    entries = tuple(sorted(entries, key=lambda e: e.path))
    tree_digest = bytes_digest(_encode_entries(entries))

    git_base_commit = git_head_commit = git_index_digest = None
    git_dir_outside_target = None
    if git_policy.enabled:
        git_dir_outside_target = git_policy.git_dir_outside_target
        git_base_commit = _resolve_ref(root, git_policy.base)
        git_head_commit = _resolve_ref(root, git_policy.head) if git_policy.head else None
        git_index_digest = _git_index_digest(root, git_policy)

    binding = {
        "schema_version": SCHEMA_VERSION,
        "tree_digest": tree_digest,
        "git_base_commit": git_base_commit,
        "git_head_commit": git_head_commit,
        "git_index_digest": git_index_digest,
    }
    return TargetSeal(
        schema_version=SCHEMA_VERSION,
        root=str(root),
        tree_digest=tree_digest,
        entries=entries,
        git_dir_outside_target=git_dir_outside_target,
        git_base_commit=git_base_commit,
        git_head_commit=git_head_commit,
        git_index_digest=git_index_digest,
        digest=digest(binding),
    )


def seal_inputs(paths: Sequence[Path], target_seal: str) -> InputSeal:
    if not target_seal:
        raise SealError("input seal requires a target seal")
    entries: list[SealEntry] = []
    for raw in paths:
        p = Path(raw)
        try:
            parent_fd = os.open(str(p.parent), os.O_RDONLY | os.O_DIRECTORY)
        except OSError as exc:
            raise SealError(f"cannot open parent of input: {p}") from exc
        try:
            kind, mode, content_digest, fd = _admit(parent_fd, p.name)
        finally:
            os.close(parent_fd)
        try:
            if kind != "file":
                raise SealError(f"input must be a regular file: {p}")
            entries.append(SealEntry(str(p), kind, mode, content_digest))
        finally:
            os.close(fd)
    if len({e.path for e in entries}) != len(entries):
        raise SealError("duplicate input path")
    entries = tuple(sorted(entries, key=lambda e: e.path))
    payload_digest = bytes_digest(_encode_entries(entries))
    return InputSeal(
        target_seal=target_seal,
        digest=digest({"target_seal": target_seal, "payload_digest": payload_digest}),
        entries=entries,
    )


def _atomic_write(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with open(tmp, "xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    dir_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def materialize_delta(before: TargetSeal, after: TargetSeal, output: Path) -> DeltaArtifact:
    before_by = {e.path: e for e in before.entries}
    after_by = {e.path: e for e in after.entries}
    entries: list[DeltaEntry] = []
    for path in sorted(set(before_by) | set(after_by)):
        b = before_by.get(path)
        a = after_by.get(path)
        if b is None:
            entries.append(DeltaEntry(path, "added", None, a.kind, True, True))
        elif a is None:
            entries.append(DeltaEntry(path, "removed", b.kind, None, True, True))
        elif b.kind != a.kind or b.content_digest != a.content_digest or b.mode != a.mode:
            entries.append(
                DeltaEntry(
                    path,
                    "changed",
                    b.kind,
                    a.kind,
                    content_changed=(b.kind != a.kind or b.content_digest != a.content_digest),
                    mode_changed=(b.mode != a.mode),
                )
            )
    git_index_changed = before.git_index_digest != after.git_index_digest
    payload = {
        "schema_version": SCHEMA_VERSION,
        "before_seal": before.digest,
        "after_seal": after.digest,
        "entries": [
            {
                "path": e.path,
                "change": e.change,
                "before_type": e.before_type,
                "after_type": e.after_type,
                "content_changed": e.content_changed,
                "mode_changed": e.mode_changed,
            }
            for e in entries
        ],
        "git_index_changed": git_index_changed,
    }
    output = Path(output)
    data = canonical_bytes(payload)
    _atomic_write(output, data)
    return DeltaArtifact(
        output_path=output,
        digest=bytes_digest(data),
        before_seal=before.digest,
        after_seal=after.digest,
        entries=tuple(entries),
        git_index_changed=git_index_changed,
    )


def check_run_root_disjoint(target_root: Path, run_root: Path) -> None:
    target_root = Path(target_root).resolve()
    run_root = Path(run_root).resolve()
    if (
        target_root == run_root
        or run_root.is_relative_to(target_root)
        or target_root.is_relative_to(run_root)
    ):
        raise SealError("run root overlaps the sealed target")
