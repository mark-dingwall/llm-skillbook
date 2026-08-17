"""Test-only canonical binding fixtures.

Production code must never import this module.
"""

from __future__ import annotations

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
    from review_loop.artifacts import ArtifactRef, TransitionEnvelope

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
    snapshot = {
        "schema_version": 1,
        "governing_seal": target_seal,
        "artifact_registry": {
            "artifacts": {
                ref.artifact_id: {
                    "kind": ref.kind,
                    "schema_version": ref.schema_version,
                    "target_seal": ref.target_seal,
                    "digest": ref.digest,
                }
                for ref in refs
            },
            "bindings": [
                {
                    "operation": operation,
                    "source_ids": list(source_ids),
                    "projection_digest": _digest(projection),
                }
            ],
        },
        "processor_state": {},
    }
    return snapshot, refs[0] if len(refs) == 1 else refs, TransitionEnvelope(
        operation=operation,
        artifact_refs=refs,
        projection=projection,
        expected_governing_seal=target_seal,
    )


def apply_bound(operation: str, projection: dict[str, object], *, source_ids: tuple[str, ...] = ("artifact-1",)) -> dict[str, object]:
    from review_loop.artifacts import ProjectionAuthority
    from review_loop.state import apply
    snapshot, _, envelope = bound_transition_fixture(kind="projection", schema_version=1, target_seal="seal-1", operation=operation, source_ids=source_ids, raw_bytes=b"{}", projection=projection)
    return apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))["processor_state"][operation]
