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
HEAD_KEYS = {"schema", "run_id", "status", "worktree", "branch", "base_identity", "stage", "next_action", "frozen", "review"}
REVIEW_KEYS = {"kind", "state", "round", "root_identity", "dispatch_id", "run_ref", "target_seal", "evidence_path", "reviewed_commit", "previous_open_finding_ids", "open_finding_ids"}


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


def _review_body(expectation: DispatchExpectation, findings: tuple[dict[str, object], ...] = ()) -> bytes:
    return (
        "## Summary\nNo findings.\n\n```review-record\n"
        + json.dumps({
            "request_id": expectation.request_id,
            "role": expectation.role,
            "charter_id": expectation.charter_id,
            "target_seal": expectation.target_seal,
            "round_input_seal": expectation.round_input_seal,
            "scope_locator_ids": list(expectation.scope_locator_ids),
            "source_findings": list(findings),
        })
        + "\n```\nREVIEW-STATUS: COMPLETE\n"
    ).encode()


def _candidate_identity(candidate: bytes) -> dict[str, object]:
    return {
        "kind": "candidate_sha256",
        "path": RELATIVE_CANDIDATE.as_posix(),
        "value": hashlib.sha256(candidate).hexdigest(),
    }


def _assert_v1_head(head: dict[str, object]) -> None:
    assert set(head) == HEAD_KEYS
    assert head["schema"] == "feature-forge/ledger/v1"
    assert isinstance(head["run_id"], str) and isinstance(head["worktree"], str)
    assert isinstance(head["branch"], str) and isinstance(head["base_identity"], str)
    assert head["status"] in {"active", "blocked"}
    assert set(head["stage"]) == {"id", "state"}
    assert head["stage"]["id"] == 5
    assert head["stage"]["state"] in {"pending", "active", "blocked", "complete", "invalidated"}
    assert isinstance(head["next_action"], str) and head["next_action"]
    assert set(head["frozen"]) == {"specification", "plan"}
    assert set(head["review"]) == REVIEW_KEYS


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
        if repository is None:
            _git(self.repository, "init", "-q")
            _git(self.repository, "config", "user.name", "Feature Forge fixture")
            _git(self.repository, "config", "user.email", "fixture@example.invalid")
            _git(self.repository, "add", RELATIVE_CANDIDATE.as_posix())
            _git(self.repository, "commit", "-qm", "candidate source")
            _git(self.repository, "checkout", "-qb", "feature/alpha")
        else:
            _git(self.repository, "add", RELATIVE_CANDIDATE.as_posix())
            _git(self.repository, "commit", "-qm", "correct candidate")
        self.source_commit = _git(self.repository, "rev-parse", "HEAD")
        # Capture once, before the disposable target exists.  All later reads
        # intentionally use source_identity to detect drift against this value.
        self.captured_candidate = self.source.read_bytes()
        self.captured_identity = _candidate_identity(self.captured_candidate)
        self.ground_truth = self.root / "frozen-authority.md"
        self.ground_truth.write_text("authoritative review constraints\n")
        self.target = self.root / "materialized-target"
        (self.target / RELATIVE_CANDIDATE).parent.mkdir(parents=True)
        (self.target / RELATIVE_CANDIDATE).write_bytes(self.captured_candidate)
        assert (self.target / RELATIVE_CANDIDATE).read_bytes() == self.captured_candidate
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.name", "Feature Forge fixture")
        _git(self.target, "config", "user.email", "fixture@example.invalid")
        _git(self.target, "add", "-A")
        _git(self.target, "commit", "-qm", "review transport")
        self.bootstrap_commit = _git(self.target, "rev-parse", "HEAD")
        self.run_root = self.root / "external-review-loop-run"
        self.controller = Controller(xdg_config_home=self.root / "xdg")
        self.events: list[str] = []
        self._write_head(self._head())

    @property
    def candidate_sha256(self) -> str:
        return hashlib.sha256(self.source.read_bytes()).hexdigest()

    @property
    def source_identity(self) -> dict[str, object]:
        return _candidate_identity(self.source.read_bytes())

    @property
    def ledger_path(self) -> Path:
        return self.repository / "docs/feature-forge/runs/2026-08-25-alpha/ledger.md"

    def _head(self) -> dict[str, object]:
        return {
            "schema": "feature-forge/ledger/v1", "run_id": "alpha", "status": "active",
            "worktree": str(self.repository.resolve()), "branch": "feature/alpha", "base_identity": self.source_commit,
            "stage": {"id": 5, "state": "active"}, "next_action": "begin specification review",
            "frozen": {"specification": None, "plan": None},
            "review": {
                "kind": None, "state": "not_started", "round": 0, "root_identity": None,
                "dispatch_id": None, "run_ref": None, "target_seal": None, "evidence_path": None,
                "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": [],
            },
        }

    def _load_head(self) -> dict[str, object]:
        text = self.ledger_path.read_text()
        match = re.match(r"\s*```json\n(.*?)\n```", text, re.DOTALL)
        assert match, "ledger must begin with a JSON head fence"
        return json.loads(match.group(1))

    def _write_head(self, head: dict[str, object]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text("```json\n" + json.dumps(head, sort_keys=True) + "\n```\n\nFixture ledger.\n")

    def persist_review_active(self, dispatch_id: str, run_state) -> dict[str, object]:
        path = self.receipt_path(dispatch_id)
        if path.exists():
            raise ValueError("receipt path is already allocated")
        head = self._load_head()
        head.update(status="active", stage={"id": 5, "state": "active"}, next_action="await or recover the active review")
        head["review"] = {
            "kind": "specification", "state": "review_active", "round": 0,
            "root_identity": self.captured_identity["value"], "dispatch_id": dispatch_id,
            "run_ref": str(run_state.run_root), "target_seal": run_state.governing_seal,
            "evidence_path": path.relative_to(self.repository).as_posix(), "reviewed_commit": None,
            "previous_open_finding_ids": [], "open_finding_ids": [],
        }
        self._write_head(head)
        return head

    def block_recovery(self) -> None:
        head = self._load_head()
        assert head["review"]["state"] == "review_active"
        head.update(status="blocked", stage={"id": 5, "state": "blocked"}, next_action="resolve the existing review receipt")
        self._write_head(head)

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

    def reviewer(self, *, fail: bool = False, findings: tuple[dict[str, object], ...] = ()):
        def dispatch(expectation: DispatchExpectation):
            self.events.append(expectation.role)
            if fail:
                raise ControllerError("synthetic reviewer unavailable")
            return _review_body(expectation, findings), ProcessCompletion(expectation.request_id, 0, True)

        return dispatch

    def triager(self, *, actionable: bool = False):
        def dispatch(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("triage")
            findings = []
            if actionable:
                for report_id, raw_findings in expectation.extra["raw_findings"].items():
                    for finding_id, (claim, severity, locators) in raw_findings.items():
                        findings.append({
                            "canonical_id": f"actionable-{report_id}-{finding_id}",
                            "sources": [{"report_id": report_id, "finding_id": finding_id,
                                         "claim": claim, "severity": severity, "locators": locators}],
                            "current_severity": severity, "factual": "CONFIRMED", "state": "OPEN",
                            "evidence_locators": list(locators),
                        })
            return _role_artifact(
                expectation.request_id, "triage", expectation.target_seal, None,
                {"report_ids": list(expectation.expected_ids), "findings": findings},
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
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", dispatch_id):
            raise ValueError("dispatch id is not filename-safe")
        return self.repository / "docs/feature-forge/runs/2026-08-25-alpha/reviews" / f"{dispatch_id}.json"

    def write_receipt(
        self,
        dispatch_id: str,
        run_state,
        result: str,
        actionable_ids: list[str],
        captured_identity: dict[str, object],
    ) -> Path:
        if result not in {"pass", "changes_required", "blocked"}:
            raise ValueError("invalid review result")
        if captured_identity != self.captured_identity or captured_identity != self.source_identity:
            raise ValueError("reviewed source identity drifted")
        path = self.receipt_path(dispatch_id)
        head = self._load_head()
        review = head["review"]
        if review["state"] != "review_active" or review["dispatch_id"] != dispatch_id:
            raise ValueError("receipt does not match the active review")
        if review["run_ref"] != str(run_state.run_root) or review["target_seal"] != run_state.governing_seal:
            raise ValueError("receipt is not bound to the controller return")
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

    def apply_result(self, result: str, actionable_ids: list[str]) -> None:
        head = self._load_head()
        head["review"]["state"] = result
        head["review"]["round"] = 1
        head["review"]["open_finding_ids"] = sorted(set(actionable_ids))
        if result == "pass":
            head.update(status="active", stage={"id": 5, "state": "complete"}, next_action="freeze the reviewed specification")
        elif result == "changes_required":
            head.update(status="active", stage={"id": 5, "state": "active"}, next_action="correct the specification and start a fresh review")
        else:
            head.update(status="blocked", stage={"id": 5, "state": "blocked"}, next_action="resolve the review blocker")
        self._write_head(head)

    def record_controller_return(self, dispatch_id: str, outcome, *, round1_error: ControllerError | None = None) -> Path:
        run_state, result, actionable_ids = _map_controller_return(outcome, round1_error=round1_error)
        receipt = self.write_receipt(dispatch_id, run_state, result, actionable_ids, self.captured_identity)
        self.apply_result(result, actionable_ids)
        return receipt


def _map_controller_return(outcome, *, round1_error: ControllerError | None = None):
    """Derive the Feature Forge state solely from public controller returns."""
    if round1_error is not None:
        return outcome.run_state, "blocked", []
    if hasattr(outcome, "review_may_start"):
        if outcome.run_state.stage != "STAGE0" or not outcome.review_may_start:
            return outcome.run_state, "blocked", []
        raise ValueError("reviewable Stage 0 has no terminal mapping")
    if outcome.stage != "TRIAGE":
        raise ValueError("unsupported controller return")
    rows = outcome.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
    actionable_ids = sorted(row["id"] for row in rows if row["state"] == "OPEN")
    return outcome, ("changes_required" if actionable_ids else "pass"), actionable_ids


def _map_clean_return(fixture: BoundaryFixture, dispatch_id: str):
    captured_identity = fixture.captured_identity
    run_state = fixture.controller.create_run(fixture.intent())
    assert run_state.run_root == fixture.run_root
    assert run_state.governing_seal
    assert run_state.snapshot["processor_state"]["preflight"]["invocation_intent"]["base"] == fixture.bootstrap_commit
    review_active = fixture.persist_review_active(dispatch_id, run_state)
    assert review_active["review"]["run_ref"] != str(fixture.target)
    assert not fixture.receipt_path(dispatch_id).exists()
    stage0 = fixture.stage0(run_state)
    assert stage0.run_state.stage == "STAGE0" and stage0.review_may_start
    round1 = fixture.controller.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.controller.run_triage(round1, triager=fixture.triager())
    assert triage.stage == "TRIAGE"
    assert triage.snapshot["processor_state"]["apply_ledger_decisions"]["rows"] == []
    assert fixture.source_identity == captured_identity
    assert fixture._load_head()["review"]["state"] == "review_active"
    receipt = fixture.record_controller_return(dispatch_id, triage)
    return triage, receipt, captured_identity


def _recover_receipt(fixture: BoundaryFixture, receipt: Path) -> None:
    """Recovery records a return only from one valid canonical Feature Forge receipt."""
    try:
        head = fixture._load_head()
        review = head["review"]
        if review["state"] != "review_active":
            raise ValueError("recovery requires an active review")
        canonical = fixture.receipt_path(str(review["dispatch_id"]))
        payload = json.loads(receipt.read_text())
        if (
            receipt.resolve() != canonical.resolve()
            or set(payload) != RECEIPT_KEYS
            or payload["schema"] != "feature-forge/review-receipt/v1"
            or payload["kind"] != review["kind"]
            or payload["dispatch_id"] != review["dispatch_id"]
            or payload["run_ref"] != review["run_ref"]
            or payload["target_seal"] != review["target_seal"]
            or payload["source_identity"] != fixture.captured_identity
            or payload["source_identity"] != fixture.source_identity
            or payload["result"] not in {"pass", "changes_required", "blocked"}
            or not isinstance(payload["actionable_finding_ids"], list)
            or not all(isinstance(item, str) and item for item in payload["actionable_finding_ids"])
            or payload["actionable_finding_ids"] != sorted(set(payload["actionable_finding_ids"]))
            or (payload["result"] == "pass" and payload["actionable_finding_ids"] != [])
            or (payload["result"] == "changes_required" and not payload["actionable_finding_ids"])
            or (payload["result"] == "blocked" and payload["actionable_finding_ids"] != [])
        ):
            raise ValueError("invalid receipt")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        fixture.block_recovery()
        return
    fixture.apply_result(payload["result"], payload["actionable_finding_ids"])


def test_review_loop_boundary_uses_fresh_receipts_stops_at_triage_and_preserves_identity(tmp_path):
    first = BoundaryFixture(tmp_path, b"candidate version one\n", "first")
    triage_one, receipt_one, identity_one = _map_clean_return(first, "spec-review-1")

    assert first.captured_identity == _candidate_identity(b"candidate version one\n")
    assert (first.target / RELATIVE_CANDIDATE).read_bytes() == first.captured_candidate
    receipt_data = json.loads(receipt_one.read_text())
    assert set(receipt_data) == RECEIPT_KEYS
    assert receipt_data == {
        "schema": "feature-forge/review-receipt/v1",
        "kind": "specification",
        "dispatch_id": "spec-review-1",
        "run_ref": str(first.run_root),
        "target_seal": triage_one.governing_seal,
        "source_identity": first.captured_identity,
        "result": "pass",
        "actionable_finding_ids": [],
    }
    assert first.run_root.is_relative_to(first.root)
    assert not first.run_root.is_relative_to(first.target)
    assert receipt_one.relative_to(first.repository).as_posix().startswith(
        "docs/feature-forge/runs/2026-08-25-alpha/reviews/"
    )
    assert receipt_one != first.run_root
    assert first._load_head()["status"] == "active"
    assert first._load_head()["stage"] == {"id": 5, "state": "complete"}
    assert first._load_head()["next_action"] == "freeze the reviewed specification"

    second = BoundaryFixture(
        tmp_path, b"candidate version two\n", "second", repository=first.repository,
    )
    triage_two, receipt_two, identity_two = _map_clean_return(second, "spec-review-2")
    assert second.run_root != first.run_root
    assert triage_two.governing_seal != triage_one.governing_seal
    assert receipt_two.parent == receipt_one.parent
    assert receipt_two != receipt_one and receipt_two.exists()
    with pytest.raises(ValueError, match="already allocated"):
        second.persist_review_active("spec-review-2", triage_two)

    stopped = BoundaryFixture(tmp_path, b"stopped\n", "stopped")
    stopped_run = stopped.controller.create_run(stopped.intent())
    stopped.persist_review_active("stop-1", stopped_run)
    stopped_stage0 = stopped.stage0(stopped_run, scout_fails=True)
    assert stopped_stage0.run_state.stage == "INDETERMINATE"
    assert stopped.events == ["scout", "scout"]
    stopped_receipt = stopped.record_controller_return("stop-1", stopped_stage0)
    assert json.loads(stopped_receipt.read_text())["result"] == stopped._load_head()["review"]["state"] == "blocked"
    assert stopped._load_head()["stage"] == {"id": 5, "state": "blocked"}

    failed_gate = BoundaryFixture(tmp_path, b"failed gate\n", "failed-gate")
    failed_gate_run = failed_gate.controller.create_run(failed_gate.intent())
    failed_gate.persist_review_active("gate-1", failed_gate_run)
    failed_stage0 = failed_gate.stage0(failed_gate_run, gate_fails=True)
    assert not failed_stage0.review_may_start
    assert failed_gate.events == ["scout", "gate:tests", "inventory-owner", "inventory-challenge"]
    failed_gate_receipt = failed_gate.record_controller_return("gate-1", failed_stage0)
    assert json.loads(failed_gate_receipt.read_text())["result"] == failed_gate._load_head()["review"]["state"] == "blocked"

    failed_round = BoundaryFixture(tmp_path, b"failed review\n", "failed-round")
    failed_round_run = failed_round.controller.create_run(failed_round.intent())
    failed_round.persist_review_active("round-1", failed_round_run)
    reviewable = failed_round.stage0(failed_round_run)
    with pytest.raises(ControllerError, match="synthetic reviewer unavailable"):
        failed_round.controller.run_round1(reviewable, dispatch_role=failed_round.reviewer(fail=True))
    assert "triage" not in failed_round.events
    failed_round_receipt = failed_round.record_controller_return("round-1", reviewable, round1_error=ControllerError("synthetic reviewer unavailable"))
    assert json.loads(failed_round_receipt.read_text())["result"] == failed_round._load_head()["review"]["state"] == "blocked"

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

    fixture.persist_review_active("recovery-1", run_state)
    stage0 = fixture.stage0(run_state)
    round1 = fixture.controller.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.controller.run_triage(round1, triager=fixture.triager())
    captured_identity = fixture.captured_identity
    receipt = fixture.write_receipt("recovery-1", triage, "pass", [], captured_identity)
    assert json.loads(receipt.read_text())["source_identity"] == fixture.captured_identity
    assert json.loads(receipt.read_text())["result"] == "pass"
    _recover_receipt(fixture, receipt)
    assert fixture._load_head()["review"]["state"] == "pass"
    assert fixture._load_head()["status"] == "active"
    assert fixture._load_head()["stage"] == {"id": 5, "state": "complete"}
    assert fixture._load_head()["next_action"] == "freeze the reviewed specification"

    recovery = BoundaryFixture(tmp_path, b"candidate\n", "recovery-block")
    recovery_run = recovery.controller.create_run(recovery.intent())
    recovery.persist_review_active("recovery-2", recovery_run)
    transcript = fixture.run_root / "transcript.md"
    transcript.write_text("review-loop status is not a Feature Forge receipt\n")
    _recover_receipt(recovery, transcript)
    blocked = recovery._load_head()
    assert blocked["status"] == "blocked" and blocked["stage"]["state"] == "blocked"
    assert blocked["review"]["state"] == "review_active"
    with pytest.raises(ValueError, match="filename-safe"):
        recovery.receipt_path("../transcript")

    malformed = BoundaryFixture(tmp_path, b"candidate\n", "recovery-malformed")
    malformed_run = malformed.controller.create_run(malformed.intent())
    malformed.persist_review_active("malformed-1", malformed_run)
    malformed_receipt = malformed.receipt_path("malformed-1")
    malformed_receipt.parent.mkdir(parents=True)
    malformed_receipt.write_text(json.dumps({
        "schema": "feature-forge/review-receipt/v1", "kind": "plan",
        "dispatch_id": "malformed-1", "run_ref": str(malformed_run.run_root),
        "target_seal": malformed_run.governing_seal, "source_identity": malformed.captured_identity,
        "result": "pass", "actionable_finding_ids": ["z", "a"],
    }))
    _recover_receipt(malformed, malformed_receipt)
    malformed_head = malformed._load_head()
    assert malformed_head["status"] == "blocked"
    assert malformed_head["review"]["state"] == "review_active"


def test_actionable_triage_maps_changes_required_with_sorted_ids(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "actionable")
    run_state = fixture.controller.create_run(fixture.intent())
    fixture.persist_review_active("actionable-1", run_state)
    stage0 = fixture.stage0(run_state)
    source_finding = ({"id": "raw-b", "claim": "needs a correction", "severity": "Important",
                       "locator_ids": [RELATIVE_CANDIDATE.as_posix()]},)
    round1 = fixture.controller.run_round1(stage0, dispatch_role=fixture.reviewer(findings=source_finding))
    triage = fixture.controller.run_triage(round1, triager=fixture.triager(actionable=True))
    actionable_ids = sorted(row["id"] for row in triage.snapshot["processor_state"]["apply_ledger_decisions"]["rows"])
    receipt = fixture.record_controller_return("actionable-1", triage)
    payload = json.loads(receipt.read_text())
    assert payload["result"] == fixture._load_head()["review"]["state"] == "changes_required"
    assert payload["actionable_finding_ids"] == actionable_ids
    assert fixture._load_head()["status"] == "active"
    assert fixture._load_head()["stage"] == {"id": 5, "state": "active"}
    assert fixture._load_head()["next_action"] == "correct the specification and start a fresh review"


def test_boundary_persists_review_active_before_stage0(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "durable-head")
    run_state = fixture.controller.create_run(fixture.intent())
    head = fixture.persist_review_active("durable-1", run_state)
    assert fixture.ledger_path.exists()
    assert head["review"] == fixture._load_head()["review"]
    _assert_v1_head(fixture._load_head())
    assert head["worktree"] == str(fixture.repository.resolve())
    assert head["branch"] == _git(fixture.repository, "branch", "--show-current") == "feature/alpha"
    assert head["base_identity"] == fixture.source_commit
    assert head["stage"] == {"id": 5, "state": "active"}
    assert head["status"] == "active"
    assert head["review"]["round"] == 0
    assert isinstance(head["review"]["root_identity"], str)
    assert head["review"]["kind"] == "specification"
    assert head["review"]["root_identity"] == fixture.captured_identity["value"]
    assert head["review"]["dispatch_id"] == "durable-1"
    assert head["review"]["run_ref"] == str(run_state.run_root)
    assert head["review"]["target_seal"] == run_state.governing_seal
    assert head["review"]["evidence_path"] == "docs/feature-forge/runs/2026-08-25-alpha/reviews/durable-1.json"
    fixture.stage0(run_state)
    assert fixture._load_head()["review"]["state"] == "review_active"
