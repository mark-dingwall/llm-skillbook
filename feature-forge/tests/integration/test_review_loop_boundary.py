"""Repository-only qualification of Feature Forge's read-only review boundary.

The live review-loop Controller owns sealing and state transitions.  This
fixture supplies only validated synthetic roles, so it exercises the public
controller contract without a provider or Bubblewrap execution.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("review_loop")

from review_loop.controller import Controller, ControllerError
from review_loop.evidence import GateResult
from review_loop.execution import CallRequest, CodexHostPaths, build_codex_call
from review_loop.prompts import (
    DispatchExpectation,
    ProcessCompletion,
    RoleExpectation,
    RoleValidationError,
    ValidatedRoleArtifact,
    validate_role_json,
)
from review_loop.profiles import InvocationIntent
from review_loop.seals import GitPolicy, seal_target


RELATIVE_CANDIDATE = Path("docs/feature-forge/runs/2026-08-25-alpha/specification.md")
RECEIPT_KEYS = {
    "schema", "kind", "dispatch_id", "run_ref", "target_seal",
    "source_identity", "result", "actionable_finding_ids",
}


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, text=True, capture_output=True,
    ).stdout.strip()


def _role_artifact(
    request_id: str,
    role_id: str,
    target_seal: str,
    round_input_seal: str | None,
    payload: dict[str, object],
    *,
    expected_ids: tuple[str, ...] = (),
    extra: dict[str, object] | None = None,
) -> ValidatedRoleArtifact:
    body = json.dumps({
        "request_id": request_id,
        "role_id": role_id,
        "target_seal": target_seal,
        "round_input_seal": round_input_seal,
        "payload": payload,
    }).encode()
    return validate_role_json(
        role_id,
        body,
        RoleExpectation(
            request_id=request_id,
            role_id=role_id,
            target_seal=target_seal,
            round_input_seal=round_input_seal,
            expected_ids=expected_ids,
            extra=extra or {},
        ),
    )


def _review_body(expectation: DispatchExpectation) -> bytes:
    return (
        "## Summary\nNo findings.\n\n```review-record\n"
        + json.dumps({
            "request_id": expectation.request_id,
            "role": expectation.role,
            "charter_id": expectation.charter_id,
            "target_seal": expectation.target_seal,
            "round_input_seal": expectation.round_input_seal,
            "scope_locator_ids": list(expectation.scope_locator_ids),
            "source_findings": [],
        })
        + "\n```\nREVIEW-STATUS: COMPLETE\n"
    ).encode()


class BoundaryFixture:
    """A disposable subject plus minimal validated controller dispatchers."""

    def __init__(
        self, tmp_path: Path, candidate: bytes, name: str, *, repository: Path | None = None,
    ) -> None:
        self.root = tmp_path / name
        self.root.mkdir()
        self.repository = repository or self.root / "feature-forge-repository"
        self.source = self.repository / RELATIVE_CANDIDATE
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_bytes(candidate)
        self.ground_truth = self.root / "frozen-authority.md"
        self.ground_truth.write_text("authoritative review constraints\n")
        self.target = self.root / "materialized-target"
        (self.target / RELATIVE_CANDIDATE).parent.mkdir(parents=True)
        (self.target / RELATIVE_CANDIDATE).write_bytes(candidate)
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.name", "Feature Forge fixture")
        _git(self.target, "config", "user.email", "fixture@example.invalid")
        _git(self.target, "add", "-A")
        _git(self.target, "commit", "-qm", "review transport")
        self.bootstrap_commit = _git(self.target, "rev-parse", "HEAD")
        self.run_root = self.root / "external-review-loop-run"
        self.controller = Controller(xdg_config_home=self.root / "xdg")
        self.events: list[str] = []

    @property
    def candidate_sha256(self) -> str:
        return hashlib.sha256(self.source.read_bytes()).hexdigest()

    @property
    def source_identity(self) -> dict[str, object]:
        return {
            "kind": "candidate_sha256",
            "path": RELATIVE_CANDIDATE.as_posix(),
            "value": self.candidate_sha256,
        }

    def intent(self) -> InvocationIntent:
        return InvocationIntent(
            target=self.target,
            base=self.bootstrap_commit,
            head=None,
            exclusions=(),
            review_profile=None,
            max_time_seconds=None,
            no_confirm=False,
            ground_truth=(self.ground_truth,),
            run_root=self.run_root,
        )

    def scout(self, *, fail: bool = False):
        seal = seal_target(self.target, GitPolicy(enabled=True, base="HEAD", include_untracked=True)).digest

        def dispatch() -> ValidatedRoleArtifact:
            self.events.append("scout")
            if fail:
                raise RoleValidationError("synthetic stop")
            return _role_artifact("scout", "evidence", seal, None, {
                "gates": [{
                    "id": "tests", "argv": ["python3", "-c", "pass"],
                    "applicability": "applicable", "classification": "required",
                    "rationale": "minimal deterministic gate",
                }],
                "evidence_gaps": [],
            })

        return dispatch

    def gate_dispatch(self, *, failed: bool = False):
        def dispatch(gate):
            self.events.append(f"gate:{gate.id}")
            return GateResult(
                gate_id=gate.id, argv=gate.argv, classification=gate.classification,
                applicability=gate.applicability, provenance=gate.provenance,
                rationale=gate.rationale,
                target_seal=seal_target(
                    self.target, GitPolicy(enabled=True, base="HEAD", include_untracked=True),
                ).digest,
                status="FAILED" if failed else "PASSED",
                exit_status=1 if failed else 0,
                stdout_excerpt="", stderr_excerpt="",
            )

        return dispatch

    def inventory_owner(self):
        def dispatch(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("inventory-owner")
            return _role_artifact(expectation.request_id, "inventory-owner", expectation.target_seal, None, {
                "areas": [{
                    "id": "candidate", "aliases": [], "consequence": "Minor",
                    "generalist_miss": True, "generalist_miss_evidence": "small subject",
                    "surfaces": [RELATIVE_CANDIDATE.as_posix()],
                    "owning_file_ids": [RELATIVE_CANDIDATE.as_posix()],
                    "charter": "Review the candidate subject.",
                }],
                "priority_order": ["candidate"], "mappings": [],
            })

        return dispatch

    def inventory_challenger(self):
        def dispatch(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("inventory-challenge")
            return _role_artifact(
                expectation.request_id, "inventory-challenge", expectation.target_seal, None,
                {"verdict": "UPHOLD"},
            )

        return dispatch

    def reviewer(self, *, fail: bool = False):
        def dispatch(expectation: DispatchExpectation):
            self.events.append(expectation.role)
            if fail:
                raise ControllerError("synthetic reviewer unavailable")
            return _review_body(expectation), ProcessCompletion(expectation.request_id, 0, True)

        return dispatch

    def triager(self):
        def dispatch(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("triage")
            return _role_artifact(
                expectation.request_id, "triage", expectation.target_seal, None,
                {"report_ids": list(expectation.expected_ids), "findings": []},
                expected_ids=expectation.expected_ids,
                extra=expectation.extra,
            )

        return dispatch

    def stage0(self, run_state, *, scout_fails: bool = False, gate_fails: bool = False):
        return self.controller.run_stage0(
            run_state,
            scout=self.scout(fail=scout_fails),
            gate_dispatch=self.gate_dispatch(failed=gate_fails),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="low",
        )

    def receipt_path(self, dispatch_id: str) -> Path:
        assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", dispatch_id)
        return self.repository / "docs/feature-forge/runs/2026-08-25-alpha/reviews" / f"{dispatch_id}.json"

    def write_receipt(
        self,
        dispatch_id: str,
        run_state,
        result: str,
        actionable_ids: list[str],
        captured_identity: dict[str, object],
    ) -> Path:
        if captured_identity != self.source_identity:
            raise ValueError("reviewed source identity drifted")
        path = self.receipt_path(dispatch_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "feature-forge/review-receipt/v1",
            "kind": "specification",
            "dispatch_id": dispatch_id,
            "run_ref": str(run_state.run_root),
            "target_seal": run_state.governing_seal,
            "source_identity": captured_identity,
            "result": result,
            "actionable_finding_ids": sorted(set(actionable_ids)),
        }
        with path.open("x") as handle:
            json.dump(payload, handle, sort_keys=True)
        return path


def _map_clean_return(fixture: BoundaryFixture, dispatch_id: str):
    captured_identity = fixture.source_identity
    run_state = fixture.controller.create_run(fixture.intent())
    assert run_state.run_root == fixture.run_root
    assert run_state.governing_seal
    assert run_state.snapshot["processor_state"]["preflight"]["invocation_intent"]["base"] == fixture.bootstrap_commit
    review_active = {
        "kind": "specification",
        "state": "review_active",
        "dispatch_id": dispatch_id,
        "run_ref": str(run_state.run_root),
        "target_seal": run_state.governing_seal,
        "evidence_path": fixture.receipt_path(dispatch_id).relative_to(fixture.repository).as_posix(),
        "source_identity": captured_identity,
    }
    assert review_active["run_ref"] != str(fixture.target)
    assert not fixture.receipt_path(dispatch_id).exists()
    stage0 = fixture.stage0(run_state)
    assert stage0.run_state.stage == "STAGE0" and stage0.review_may_start
    round1 = fixture.controller.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.controller.run_triage(round1, triager=fixture.triager())
    assert triage.stage == "TRIAGE"
    assert triage.snapshot["processor_state"]["apply_ledger_decisions"]["rows"] == []
    assert fixture.source_identity == captured_identity
    receipt = fixture.write_receipt(dispatch_id, triage, "pass", [], captured_identity)
    return triage, receipt, captured_identity


def _recover_mapped_result(fixture: BoundaryFixture, receipt: Path) -> str:
    """Recovery accepts only a persisted Feature Forge receipt bound to current bytes."""
    payload = json.loads(receipt.read_text())
    if set(payload) != RECEIPT_KEYS or payload["source_identity"] != fixture.source_identity:
        raise ValueError("reviewed source identity drifted or receipt is invalid")
    return str(payload["result"])


def test_review_loop_boundary_uses_fresh_receipts_stops_at_triage_and_preserves_identity(tmp_path):
    first = BoundaryFixture(tmp_path, b"candidate version one\n", "first")
    triage_one, receipt_one, identity_one = _map_clean_return(first, "spec-review-1")

    assert (first.target / RELATIVE_CANDIDATE).read_bytes() == first.source.read_bytes()
    receipt_data = json.loads(receipt_one.read_text())
    assert set(receipt_data) == RECEIPT_KEYS
    assert receipt_data == {
        "schema": "feature-forge/review-receipt/v1",
        "kind": "specification",
        "dispatch_id": "spec-review-1",
        "run_ref": str(first.run_root),
        "target_seal": triage_one.governing_seal,
        "source_identity": first.source_identity,
        "result": "pass",
        "actionable_finding_ids": [],
    }
    assert first.run_root.is_relative_to(first.root)
    assert not first.run_root.is_relative_to(first.target)
    assert receipt_one.relative_to(first.repository).as_posix().startswith(
        "docs/feature-forge/runs/2026-08-25-alpha/reviews/"
    )
    assert receipt_one != first.run_root

    second = BoundaryFixture(
        tmp_path, b"candidate version two\n", "second", repository=first.repository,
    )
    triage_two, receipt_two, identity_two = _map_clean_return(second, "spec-review-2")
    assert second.run_root != first.run_root
    assert triage_two.governing_seal != triage_one.governing_seal
    assert receipt_two.parent == receipt_one.parent
    assert receipt_two != receipt_one and receipt_two.exists()
    with pytest.raises(FileExistsError):
        second.write_receipt("spec-review-2", triage_two, "pass", [], identity_two)

    stopped = BoundaryFixture(tmp_path, b"stopped\n", "stopped")
    stopped_stage0 = stopped.stage0(stopped.controller.create_run(stopped.intent()), scout_fails=True)
    assert stopped_stage0.run_state.stage == "INDETERMINATE"
    assert stopped.events == ["scout", "scout"]

    failed_gate = BoundaryFixture(tmp_path, b"failed gate\n", "failed-gate")
    failed_stage0 = failed_gate.stage0(
        failed_gate.controller.create_run(failed_gate.intent()), gate_fails=True,
    )
    assert not failed_stage0.review_may_start
    assert failed_gate.events == ["scout", "gate:tests", "inventory-owner", "inventory-challenge"]

    failed_round = BoundaryFixture(tmp_path, b"failed review\n", "failed-round")
    reviewable = failed_round.stage0(failed_round.controller.create_run(failed_round.intent()))
    with pytest.raises(ControllerError, match="synthetic reviewer unavailable"):
        failed_round.controller.run_round1(reviewable, dispatch_role=failed_round.reviewer(fail=True))
    assert "triage" not in failed_round.events

    first.source.write_bytes(b"changed after return\n")
    with pytest.raises(ValueError, match="identity drifted"):
        first.write_receipt("drifted", triage_one, "pass", [], identity_one)


def test_boundary_containment_and_recovery_use_only_bound_evidence(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "containment")
    run_state = fixture.controller.create_run(fixture.intent())
    target_seal = seal_target(fixture.target, GitPolicy(enabled=True, base=fixture.bootstrap_commit, include_untracked=True))
    host = CodexHostPaths(
        bwrap=Path("/bin/false"), node=Path("/bin/false"),
        codex_package_root=fixture.root / "runtime", codex_entry=fixture.root / "runtime/codex.js",
        auth_file=fixture.root / "auth.json", resolv_conf=Path("/etc/resolv.conf"),
        nsswitch_conf=Path("/etc/nsswitch.conf"), ca_certificates=Path("/etc/ssl/certs/ca-certificates.crt"),
    )
    _, _, mapping = build_codex_call(CallRequest(
        call_id="containment", role="holistic", target_root=fixture.target,
        target_entries=target_seal.entries, input_paths=(fixture.ground_truth,),
        run_root=fixture.run_root, prompt="repository-only mapping check",
    ), host, fixture.root / "mapping-call")
    assert fixture.target / RELATIVE_CANDIDATE in mapping.target_ro
    assert all(path.is_relative_to(fixture.target) for path in mapping.target_ro)
    assert mapping.inputs_ro == (fixture.ground_truth,)
    assert fixture.repository not in mapping.target_ro + mapping.inputs_ro
    assert fixture.run_root not in mapping.target_ro + mapping.inputs_ro

    stage0 = fixture.stage0(run_state)
    round1 = fixture.controller.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.controller.run_triage(round1, triager=fixture.triager())
    captured_identity = fixture.source_identity
    receipt = fixture.write_receipt("recovery-1", triage, "pass", [], captured_identity)
    assert json.loads(receipt.read_text())["source_identity"] == fixture.source_identity
    assert json.loads(receipt.read_text())["result"] == "pass"
    assert _recover_mapped_result(fixture, receipt) == "pass"
    transcript = fixture.run_root / "transcript.md"
    transcript.write_text("review-loop status is not a Feature Forge receipt\n")
    with pytest.raises(json.JSONDecodeError):
        _recover_mapped_result(fixture, transcript)
    with pytest.raises(FileNotFoundError):
        _recover_mapped_result(fixture, fixture.receipt_path("missing"))
    fixture.source.write_bytes(b"identity drift\n")
    with pytest.raises(ValueError, match="identity drifted"):
        _recover_mapped_result(fixture, receipt)
