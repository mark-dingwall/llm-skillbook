"""Test-only canonical binding fixtures.

Production code must never import this module.
"""

from __future__ import annotations

import copy
import hashlib
import json


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def bound_transition_fixture(
    *,
    kind: str,
    schema_version: int,
    target_seal: str,
    operation: str,
    source_ids: tuple[str, ...],
    raw_bytes: bytes,
    projection: dict[str, object],
):
    """Return matching canonical snapshot, reference, and transition envelope."""
    snapshot = {
        "schema_version": 1,
        "governing_seal": target_seal,
        "artifact_registry": {
            "artifacts": {},
            "bindings": [],
        },
        "processor_state": {},
    }
    return bound_transition_on_snapshot(
        snapshot,
        kind=kind,
        schema_version=schema_version,
        target_seal=target_seal,
        operation=operation,
        source_ids=source_ids,
        raw_bytes=raw_bytes,
        projection=projection,
    )


def bound_transition_on_snapshot(
    snapshot: dict[str, object],
    *,
    kind: str,
    schema_version: int,
    target_seal: str,
    operation: str,
    source_ids: tuple[str, ...],
    raw_bytes: bytes,
    projection: dict[str, object],
):
    """Bind a new transition to a copy of an existing canonical snapshot."""
    from review_loop.artifacts import ArtifactRef, TransitionEnvelope

    issued = copy.deepcopy(snapshot)
    if issued.get("governing_seal") != target_seal:
        raise ValueError("fixture target seal must match the canonical snapshot")
    registry = issued["artifact_registry"]
    assert isinstance(registry, dict)
    artifacts = registry["artifacts"]
    bindings = registry["bindings"]
    assert isinstance(artifacts, dict)
    assert isinstance(bindings, list)
    refs = tuple(
        ArtifactRef(
            artifact_id=artifact_id,
            kind=kind,
            schema_version=schema_version,
            target_seal=target_seal,
            digest=hashlib.sha256(raw_bytes + artifact_id.encode("utf-8")).hexdigest(),
        )
        for artifact_id in source_ids
    )
    for ref in refs:
        if ref.artifact_id in artifacts:
            raise ValueError("fixture artifact IDs must be unique")
        artifacts[ref.artifact_id] = {
            "kind": ref.kind,
            "schema_version": ref.schema_version,
            "target_seal": ref.target_seal,
            "digest": ref.digest,
        }
    bindings.append(
        {
            "operation": operation,
            "source_ids": list(source_ids),
            "projection_digest": _digest(projection),
        }
    )
    envelope = TransitionEnvelope(
        operation=operation,
        artifact_refs=refs,
        projection=projection,
        expected_governing_seal=target_seal,
    )
    return issued, refs[0] if len(refs) == 1 else refs, envelope


def apply_bound(operation: str, projection: dict[str, object], *, source_ids: tuple[str, ...] = ("artifact-1",)) -> dict[str, object]:
    from review_loop.artifacts import ProjectionAuthority
    from review_loop.state import apply
    snapshot, _, envelope = bound_transition_fixture(kind="projection", schema_version=1, target_seal="seal-1", operation=operation, source_ids=source_ids, raw_bytes=b"{}", projection=projection)
    return apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))["processor_state"][operation]
