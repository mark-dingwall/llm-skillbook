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
from pathlib import Path, PurePosixPath

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


def normalize_exclusions(exclusions: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for excluded in exclusions:
        if not isinstance(excluded, str) or not excluded:
            raise SealError(f"unsafe target exclusion: {excluded!r}")
        path = PurePosixPath(excluded)
        canonical = path.as_posix()
        if path.is_absolute() or ".." in path.parts or canonical == ".":
            raise SealError(f"unsafe target exclusion: {excluded!r}")
        if canonical not in normalized:
            normalized.append(canonical)
    return tuple(normalized)


def _is_excluded(path: str, exclusions: frozenset[str]) -> bool:
    return any(path == excluded or path.startswith(f"{excluded}/") for excluded in exclusions)


def _walk(
    dir_fd: int,
    prefix: str,
    out: list[SealEntry],
    root_exclude: frozenset[str] = frozenset(),
    exclusions: frozenset[str] = frozenset(),
) -> None:
    try:
        with os.scandir(dir_fd) as it:
            names = sorted(entry.name for entry in it)
    except OSError as exc:
        raise SealError(f"cannot list directory: {prefix or '.'}") from exc
    if not prefix:
        names = [name for name in names if name not in root_exclude]
    for name in names:
        rel = name if not prefix else f"{prefix}/{name}"
        if _is_excluded(rel, exclusions):
            continue
        kind, mode, content_digest, fd = _admit(dir_fd, name)
        try:
            out.append(SealEntry(rel, kind, mode, content_digest))
            if kind == "dir":
                _walk(fd, rel, out, exclusions=exclusions)
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


def _content_seal_digest(entries: Sequence[SealEntry]) -> str:
    tree_digest = bytes_digest(_encode_entries(tuple(sorted(entries, key=lambda entry: entry.path))))
    return digest({
        "schema_version": SCHEMA_VERSION,
        "tree_digest": tree_digest,
        "git_base_commit": None,
        "git_head_commit": None,
        "git_index_digest": None,
    })


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


def _git_index_digest(root: Path, git_policy: GitPolicy, exclusions: frozenset[str]) -> str | None:
    if not git_policy.include_index:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-s", "-z"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise SealError("cannot read git index")
    records = result.stdout.split(b"\0")
    payload = b"\0".join(
        record for record in records if record and not _is_excluded(
            record.split(b"\t", 1)[-1].decode("utf-8", "surrogateescape"), exclusions
        )
    )
    if payload:
        payload += b"\0"
    if git_policy.include_untracked:
        others = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
            capture_output=True,
        )
        if others.returncode != 0:
            raise SealError("cannot enumerate untracked files")
        other_records = others.stdout.split(b"\0")
        filtered = b"\0".join(
            record for record in other_records if record and not _is_excluded(
                record.decode("utf-8", "surrogateescape"), exclusions
            )
        )
        payload += b"\x00UNTRACKED\x00" + filtered + (b"\0" if filtered else b"")
    return bytes_digest(payload)


def seal_target(root: Path, git_policy: GitPolicy, *, exclusions: Sequence[str] = ()) -> TargetSeal:
    root = Path(root)
    if not root.is_dir():
        raise SealError(f"target root is not a directory: {root}")
    normalized_exclusions = frozenset(normalize_exclusions(exclusions))
    root_fd = _open_root(root)
    entries: list[SealEntry] = []
    try:
        # .git metadata is never a target-tree input; its identity is bound
        # separately below as the git index digest.
        _walk(
            root_fd, "", entries, root_exclude=frozenset({".git"}),
            exclusions=normalized_exclusions,
        )
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
        git_index_digest = _git_index_digest(root, git_policy, normalized_exclusions)

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
        flags = os.O_RDONLY | os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            parent_fd = os.open(str(p.parent), flags)
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


def _split_relpath(path: str) -> tuple[str, ...]:
    """Split a delta-entry path into safe components, or fail closed.

    Rejects anything that could escape a descriptor-relative walk: absolute
    paths, NUL bytes, and any ``.``/``..``/empty component (which also
    catches a leading/trailing/doubled ``/``).
    """
    if not path or path.startswith("/") or "\x00" in path:
        raise SealError(f"unsafe write-back path rejected: {path!r}")
    parts = tuple(path.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        raise SealError(f"unsafe write-back path rejected: {path!r}")
    return parts


def _walk_parent_dir(root_fd: int, parts: Sequence[str], *, create: bool) -> int:
    """Descend descriptor-relative through ``parts[:-1]``, rejecting symlinks.

    Every intermediate component is opened ``O_DIRECTORY | O_NOFOLLOW``: a
    symlink (or any non-directory) at any level makes the open fail, closing
    the race a caller could use to redirect a write outside the tree via a
    swapped-in symlink component. Returns an fd for the parent directory of
    ``parts[-1]``; the caller closes it.
    """
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            try:
                next_fd = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise SealError(f"missing write-back parent directory: {part!r}")
                try:
                    os.mkdir(part, 0o777, dir_fd=fd)
                except FileExistsError:
                    pass
                next_fd = os.open(part, flags, dir_fd=fd)
            except OSError as exc:
                raise SealError(f"cannot descend into write-back path component: {part!r}") from exc
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def _write_back_file(dest_parent_fd: int, name: str, data: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, 0o666, dir_fd=dest_parent_fd)
    except OSError as exc:
        raise SealError(f"cannot write target entry: {name!r}") from exc
    try:
        # os.write can short-write; loop until the buffer is fully drained
        # rather than trust a single call to have written everything.
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            view = view[n:]
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_back_dir(dest_parent_fd: int, name: str, mode: int) -> None:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        os.mkdir(name, mode, dir_fd=dest_parent_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise SealError(f"cannot create target directory: {name!r}") from exc
    try:
        fd = os.open(name, flags, dir_fd=dest_parent_fd)
    except OSError as exc:
        raise SealError(f"cannot verify target directory: {name!r}") from exc
    try:
        os.fchmod(fd, mode)
    finally:
        os.close(fd)


def _remove_leaf(dest_parent_fd: int, name: str, before_type: str) -> None:
    try:
        st = os.stat(name, dir_fd=dest_parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise SealError(f"cannot stat write-back removal target: {name!r}") from exc
    if stat.S_ISLNK(st.st_mode):
        raise SealError(f"refusing to remove a symlink at write-back boundary: {name!r}")
    if before_type == "file":
        if not stat.S_ISREG(st.st_mode):
            raise SealError(f"expected a regular file to remove: {name!r}")
        try:
            os.unlink(name, dir_fd=dest_parent_fd)
        except OSError as exc:
            raise SealError(f"cannot remove write-back target: {name!r}") from exc
    elif before_type == "dir":
        if not stat.S_ISDIR(st.st_mode):
            raise SealError(f"expected a directory to remove: {name!r}")
        try:
            os.rmdir(name, dir_fd=dest_parent_fd)
        except OSError as exc:
            raise SealError(f"cannot remove write-back target directory: {name!r}") from exc
    else:
        raise SealError(f"unsupported removed entry type: {before_type!r}")


def apply_delta_to_target(
    delta: DeltaArtifact,
    source_root: Path,
    dest_root: Path,
    *,
    expected_entries: Sequence[SealEntry] | None = None,
    expected_seal: str | None = None,
) -> None:
    """Replay an already-verified delta from a disposable-copy source onto
    the real target. Sibling of ``materialize_delta`` at the opposite end:
    that function reads two sealed trees and proves what changed; this one
    writes those changes onto the real, non-disposable target.

    This is the first primitive in the module that writes outside a
    disposable copy -- highest blast radius. The delta was already validated
    upstream (``FixController.validate_candidate``), but every path is
    re-validated here, at the write boundary, via descriptor-relative
    ``O_NOFOLLOW`` opens: nothing here trusts that the delta is safe just
    because it was checked earlier.

    Added/changed FILE entries are copied ``source_root/path ->
    dest_root/path`` (parents created on demand); added/changed DIR entries
    are created (mode brought to parity with source, covering a directory
    whose mode alone changed); ``removed`` entries are then applied in
    REVERSE sorted-path order so a file is unlinked before the directory it
    was the last occupant of is rmdir'd.
    """
    for label, root in (("source", source_root), ("destination", dest_root)):
        if not Path(root).is_dir():
            raise SealError(f"write-back {label} is not a directory: {root}")

    if (expected_entries is None) != (expected_seal is None):
        raise SealError("verified source entries and seal must be supplied together")
    expected_by_path = None
    if expected_entries is not None and expected_seal is not None:
        expected_by_path = {entry.path: entry for entry in expected_entries}
        if len(expected_by_path) != len(expected_entries):
            raise SealError("verified source entries contain duplicate paths")
        if _content_seal_digest(expected_entries) != expected_seal:
            raise SealError("verified source entries do not match the post-FIX seal")

    src_fd = _open_root(Path(source_root))
    try:
        captured: dict[str, tuple[str, int, bytes | None]] = {}
        for entry in sorted(delta.entries, key=lambda e: e.path):
            if entry.change not in ("added", "changed"):
                continue
            parts = _split_relpath(entry.path)

            src_parent_fd = _walk_parent_dir(src_fd, parts, create=False)
            try:
                kind, mode, _digest, sfd = _admit(src_parent_fd, parts[-1])
            finally:
                os.close(src_parent_fd)
            try:
                if kind != entry.after_type:
                    raise SealError(
                        f"source entry type does not match the delta for {entry.path!r}: "
                        f"expected {entry.after_type!r}, found {kind!r}"
                    )
                data = None
                if kind == "file":
                    os.lseek(sfd, 0, os.SEEK_SET)
                    data = _read_all(sfd)
                if expected_by_path is not None:
                    expected = expected_by_path.get(entry.path)
                    captured_digest = bytes_digest(data) if data is not None else None
                    if expected is None or (
                        expected.kind != kind
                        or expected.mode != mode
                        or expected.content_digest != captured_digest
                    ):
                        raise SealError(
                            f"source entry drifted from the verified post-FIX seal: {entry.path!r}"
                        )
                captured[entry.path] = (kind, mode, data)
            finally:
                os.close(sfd)
    finally:
        os.close(src_fd)

    dest_fd = _open_root(Path(dest_root))
    try:
        for entry in sorted(delta.entries, key=lambda e: e.path):
            if entry.change not in ("added", "changed"):
                continue
            parts = _split_relpath(entry.path)
            kind, mode, data = captured[entry.path]
            dest_parent_fd = _walk_parent_dir(dest_fd, parts, create=True)
            try:
                if kind == "file":
                    assert data is not None
                    _write_back_file(dest_parent_fd, parts[-1], data, mode)
                else:
                    _write_back_dir(dest_parent_fd, parts[-1], mode)
            finally:
                os.close(dest_parent_fd)

        removed = sorted((e for e in delta.entries if e.change == "removed"), key=lambda e: e.path, reverse=True)
        for entry in removed:
            parts = _split_relpath(entry.path)
            dest_parent_fd = _walk_parent_dir(dest_fd, parts, create=False)
            try:
                _remove_leaf(dest_parent_fd, parts[-1], entry.before_type)
            finally:
                os.close(dest_parent_fd)
    finally:
        os.close(dest_fd)


def check_run_root_disjoint(target_root: Path, run_root: Path) -> None:
    target_root = Path(target_root).resolve()
    run_root = Path(run_root).resolve()
    if (
        target_root == run_root
        or run_root.is_relative_to(target_root)
        or target_root.is_relative_to(run_root)
    ):
        raise SealError("run root overlaps the sealed target")
