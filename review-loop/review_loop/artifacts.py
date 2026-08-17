"""Canonical review-state storage and projection authority.

The controller owns this module.  The state kernel only receives a compact
projection plus an authority derived from the already persisted snapshot.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path


class ArtifactMismatch(Exception):
    """An attempted state transition is not issued by canonical state."""


@dataclass(frozen=True)
class ProjectionBinding:
    operation: str
    source_ids: tuple[str, ...]
    projection_digest: str


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    kind: str
    schema_version: int
    target_seal: str
    digest: str


@dataclass(frozen=True)
class TransitionEnvelope:
    operation: str
    artifact_refs: tuple[ArtifactRef, ...]
    projection: dict[str, object]
    expected_governing_seal: str


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ProjectionAuthority:
    """Read-only view of bindings from one canonical-state snapshot."""

    def __init__(self, snapshot: dict[str, object]) -> None:
        self._snapshot = snapshot

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, object]) -> "ProjectionAuthority":
        cls._registry(snapshot)  # fail at the boundary, not after a transition
        return cls(snapshot)

    @staticmethod
    def _registry(snapshot: dict[str, object]) -> dict[str, object]:
        if not isinstance(snapshot, dict):
            raise ArtifactMismatch("canonical snapshot must be an object")
        if not isinstance(snapshot.get("governing_seal"), str) or not snapshot["governing_seal"]:
            raise ArtifactMismatch("canonical snapshot has no governing seal")
        registry = snapshot.get("artifact_registry")
        if not isinstance(registry, dict):
            raise ArtifactMismatch("canonical snapshot has no artifact registry")
        if not isinstance(registry.get("artifacts"), dict) or not isinstance(
            registry.get("bindings"), list
        ):
            raise ArtifactMismatch("canonical artifact registry is malformed")
        return registry

    def validate(self, envelope: TransitionEnvelope, snapshot: dict[str, object] | None = None) -> None:
        if not isinstance(envelope, TransitionEnvelope):
            raise ArtifactMismatch("transition must use a TransitionEnvelope")
        if snapshot is not None and canonical_bytes(snapshot) != canonical_bytes(self._snapshot):
            raise ArtifactMismatch("authority is not derived from the supplied canonical snapshot")
        registry = self._registry(self._snapshot)
        if envelope.expected_governing_seal != self._snapshot["governing_seal"]:
            raise ArtifactMismatch("transition governing seal is stale")
        source_ids = tuple(ref.artifact_id for ref in envelope.artifact_refs)
        if not source_ids or len(set(source_ids)) != len(source_ids):
            raise ArtifactMismatch("transition source IDs must be non-empty and unique")
        artifacts = registry["artifacts"]
        assert isinstance(artifacts, dict)
        for ref in envelope.artifact_refs:
            if not isinstance(ref, ArtifactRef):
                raise ArtifactMismatch("transition artifact reference is malformed")
            entry = artifacts.get(ref.artifact_id)
            expected = {
                "kind": ref.kind,
                "schema_version": ref.schema_version,
                "target_seal": ref.target_seal,
                "digest": ref.digest,
            }
            if entry != expected:
                raise ArtifactMismatch(f"artifact reference {ref.artifact_id!r} is not canonical")
            if ref.target_seal != self._snapshot["governing_seal"]:
                raise ArtifactMismatch("artifact reference is bound to a stale seal")
        expected_binding = {
            "operation": envelope.operation,
            "source_ids": list(source_ids),
            "projection_digest": digest(envelope.projection),
        }
        if expected_binding not in registry["bindings"]:
            raise ArtifactMismatch("projection does not match a canonical binding")


class CanonicalStore:
    """Controller-private atomic store; metadata lives inside review-state.json."""

    def __init__(self, run_root: Path) -> None:
        self._run_root = run_root
        self._state_path = run_root / "review-state.json"
        self._evidence_path = run_root / "evidence"

    def initialize(self, governing_seal: str, processor_state: dict[str, object] | None = None) -> None:
        if not governing_seal:
            raise ValueError("governing_seal is required")
        if self._state_path.exists():
            raise FileExistsError(self._state_path)
        self._run_root.mkdir(parents=True, exist_ok=True)
        self._evidence_path.mkdir(exist_ok=True)
        self._replace({
            "schema_version": 1,
            "governing_seal": governing_seal,
            "artifact_registry": {"artifacts": {}, "bindings": []},
            "processor_state": processor_state or {},
        })

    def load(self) -> dict[str, object]:
        with self._state_path.open("rb") as handle:
            snapshot = json.loads(handle.read().decode("utf-8"))
        ProjectionAuthority.from_snapshot(snapshot)
        return snapshot

    def issue_transition(
        self,
        *,
        operation: str,
        artifact_id: str,
        kind: str,
        schema_version: int,
        target_seal: str,
        raw_bytes: bytes,
        projection: dict[str, object],
        processor_state: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Persist allowed evidence then atomically bind it with its projection.

        An interruption before the state replacement leaves an unbound evidence
        file.  Loading state never discovers it, so it is non-operative.
        """
        snapshot = self.load()
        if target_seal != snapshot["governing_seal"]:
            raise ArtifactMismatch("cannot issue evidence for a stale seal")
        if not artifact_id or "/" in artifact_id or "\\" in artifact_id:
            raise ValueError("artifact_id must be a simple non-empty ID")
        if not kind or type(schema_version) is not int or schema_version < 1:
            raise ValueError("kind and positive schema_version are required")
        evidence_path = self._evidence_path / artifact_id
        if evidence_path.exists():
            raise FileExistsError(evidence_path)
        self._write_file(evidence_path, raw_bytes)
        registry = snapshot["artifact_registry"]
        assert isinstance(registry, dict)
        artifacts = dict(registry["artifacts"])
        if artifact_id in artifacts:
            raise ArtifactMismatch("artifact ID already exists")
        artifacts[artifact_id] = {
            "kind": kind,
            "schema_version": schema_version,
            "target_seal": target_seal,
            "digest": bytes_digest(raw_bytes),
        }
        bindings = list(registry["bindings"])
        bindings.append({
            "operation": operation,
            "source_ids": [artifact_id],
            "projection_digest": digest(projection),
        })
        updated = dict(snapshot)
        updated["artifact_registry"] = {"artifacts": artifacts, "bindings": bindings}
        if processor_state is None:
            # Import lazily to keep the pure state kernel independent of this
            # controller-owned storage module.
            from .state import apply

            envelope = TransitionEnvelope(
                operation=operation,
                artifact_refs=(
                    ArtifactRef(
                        artifact_id=artifact_id,
                        kind=kind,
                        schema_version=schema_version,
                        target_seal=target_seal,
                        digest=bytes_digest(raw_bytes),
                    ),
                ),
                projection=projection,
                expected_governing_seal=target_seal,
            )
            updated = apply(envelope, updated, ProjectionAuthority.from_snapshot(updated))
        else:
            updated["processor_state"] = processor_state
        self._replace(updated)
        return updated

    def apply_transition(self, envelope: TransitionEnvelope) -> dict[str, object]:
        """Atomically persist a transition already bound in canonical state."""
        from .state import apply

        snapshot = self.load()
        updated = apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))
        self._replace(updated)
        return updated

    def _replace(self, snapshot: dict[str, object]) -> None:
        temporary = self._state_path.with_name(f".{self._state_path.name}.tmp")
        self._write_file(temporary, canonical_bytes(snapshot))
        os.replace(temporary, self._state_path)
        directory_fd = os.open(self._run_root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    @staticmethod
    def _write_file(path: Path, data: bytes) -> None:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
