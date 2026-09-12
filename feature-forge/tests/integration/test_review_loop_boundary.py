"""Repository-only qualification of Feature Forge's read-only review boundary.

The live review-loop Controller owns sealing and state transitions.  This
fixture supplies only validated synthetic roles, so it exercises the public
controller contract without a provider or Bubblewrap execution.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import runpy
import shlex
import copy
import stat
import subprocess
import sys
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


RELATIVE_CANDIDATE = Path("docs/superpowers/specs/2026-08-25-alpha-design.md")
FF_CHECK = Path(__file__).resolve().parents[2] / "scripts" / "ff-check"
RECEIPT_KEYS = {
    "schema", "kind", "dispatch_id", "run_ref", "target_seal",
    "source_identity", "result", "actionable_finding_ids",
    "feature_forge_charter_id", "completion_criterion", "raw_report_ids",
    "triage_artifact_id", "triage_finding_ids", "stable_id_mapping",
}
FF_API = runpy.run_path(str(FF_CHECK))
ADAPTER_REFERENCE = FF_CHECK.parent.parent / "references/adapters-and-reviews.md"
ADAPTER_API = {}
_environment_recipe = re.search(
    r"```python\n(# Feature Forge synchronous Review Loop environment\n.*?)\n```",
    ADAPTER_REFERENCE.read_text(), re.DOTALL,
)
assert _environment_recipe is not None
exec(compile(_environment_recipe[1], str(ADAPTER_REFERENCE), "exec"), ADAPTER_API)
trusted_review_loop_environment = ADAPTER_API["trusted_review_loop_environment"]
CRITERION = "same grounded discrepancy against the same requirement, correctness condition, repository contract, or verification result, with no material change in the required correction"
COMPLETION = "No grounded discrepancies remain against the specification review charter."
HEAD_KEYS = {"schema", "run_id", "mode", "status", "worktree", "branch", "base_identity", "stage", "next_action", "frozen", "review"}
REVIEW_KEYS = {"kind", "state", "round", "root_identity", "dispatch_id", "run_ref", "target_seal", "evidence_path", "reviewed_commit", "previous_open_finding_ids", "open_finding_ids"}


def _materialize_committed_implementation(fixture, reviewed_commit, base, *, relevant_links=()):
    """Exercise the skill-owned transport recipe using the checker's Git policy."""
    repo = fixture.repository
    raw = FF_API["git_bytes"](repo, "ls-tree", "-r", "-z", reviewed_commit)
    assert raw is not None
    entries = [record.split(b"\t", 1) for record in raw.split(b"\0") if record]
    error = FF_API["transformation_gate"](repo, b"".join(path + b"\0" for _, path in entries))
    if error:
        raise ValueError(error)
    changed_raw = FF_API["git_bytes"](
        repo, "diff-tree", "-r", "--no-commit-id", "--name-status", "-z",
        "--no-renames", base, reviewed_commit,
    )
    changed = FF_API["parse_name_status_z"](changed_raw)
    base_entries = FF_API["git_bytes"](repo, "ls-tree", "-r", "-z", base)
    for record in base_entries.split(b"\0"):
        if record.startswith(b"120000 ") and record.split(b"\t", 1)[1].decode("utf-8") in changed:
            raise ValueError("symlink=review-relevant")
    links = []
    regular = []
    for metadata, raw_path in entries:
        mode, kind, oid = metadata.split(b" ")
        path = raw_path.decode("utf-8")
        if mode == b"160000":
            raise ValueError("gitlinks=unsupported")
        assert kind == b"blob"
        blob = FF_API["git_bytes"](repo, "cat-file", "blob", oid.decode("ascii"))
        assert blob is not None
        if mode == b"120000":
            if path in changed or path in relevant_links:
                raise ValueError("symlink=review-relevant")
            links.append({"path": path, "mode": "120000", "target": os.fsdecode(blob)})
        else:
            assert mode in {b"100644", b"100755"}
            regular.append((path, blob, 0o755 if mode == b"100755" else 0o644))
    target = fixture.root / "committed-target"
    target.mkdir()
    for path, blob, mode in regular:
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(blob)
        destination.chmod(mode)
    manifest = fixture.root / "symlink-manifest.json"
    manifest.write_text(json.dumps(links, sort_keys=True))
    assert FF_API["git"](target, "init", "-q") is not None
    assert FF_API["git"](target, "config", "user.name", "Feature Forge fixture") is not None
    assert FF_API["git"](target, "config", "user.email", "fixture@example.invalid") is not None
    error = FF_API["transformation_gate"](
        target, b"".join(path.encode("utf-8") + b"\0" for path, _, _ in regular),
    )
    if error:
        raise ValueError(error)
    assert FF_API["git"](target, "-c", "core.autocrlf=false", "add", "--", *(path for path, _, _ in regular)) is not None
    expected_index = {
        metadata.split(b" ")[0] + b" " + metadata.split(b" ")[2] + b" 0\t" + path
        for metadata, path in entries if metadata.startswith((b"100644 ", b"100755 "))
    }
    staged = FF_API["git_bytes"](target, "ls-files", "--stage", "-z")
    if staged is None or set(filter(None, staged.split(b"\0"))) != expected_index:
        raise ValueError("bootstrap=staged-mismatch")
    assert FF_API["git"](target, "commit", "-qm", "canonical review transport") is not None
    fixture.target = target
    fixture.bootstrap_commit = FF_API["git"](target, "rev-parse", "HEAD")
    return manifest


@pytest.mark.parametrize("entry", ["changed-link", "relevant-link", "removed-link", "gitlink", "filter"])
def test_implementation_materialization_blocks_unsupported_subject_before_creation(tmp_path, entry):
    fixture = BoundaryFixture(tmp_path, b"specification\n", f"unsupported-{entry}")
    repo = fixture.repository
    marker = fixture.root / "filter-ran"
    link = repo / "link"
    link.symlink_to("README.md")
    _git(repo, "add", "--", "link")
    _git(repo, "commit", "-qm", "existing link")
    base = _git(repo, "rev-parse", "HEAD")
    relevant = ()
    if entry == "changed-link":
        link.unlink()
        link.symlink_to("missing")
        _git(repo, "add", "--", "link")
        _git(repo, "commit", "-qm", "changed link")
    elif entry == "removed-link":
        _git(repo, "rm", "--", "link")
        _git(repo, "commit", "-qm", "removed link")
    elif entry == "relevant-link":
        relevant = ("link",)
    elif entry == "gitlink":
        _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{base},module")
        _git(repo, "commit", "-qm", "unsupported gitlink")
    else:
        attributes = Path(_git(repo, "rev-parse", "--git-path", "info/attributes"))
        attributes.write_text("README.md filter=unset\n")
        _git(repo, "config", "filter.unset.clean", f': > "{marker}"; exit 1')
    with pytest.raises(ValueError, match="unsupported|review-relevant"):
        _materialize_committed_implementation(
            fixture, _git(repo, "rev-parse", "HEAD"), base, relevant_links=relevant,
        )
    assert not (fixture.root / "committed-target").exists()
    assert not marker.exists()


@pytest.mark.parametrize("attribute", ["text", "filter=bootstrap"])
def test_bootstrap_rechecks_effective_attributes_before_staging(tmp_path, monkeypatch, attribute):
    fixture = BoundaryFixture(tmp_path, b"specification\n", "bootstrap-attributes")
    repo = fixture.repository
    (repo / "app.txt").write_bytes(b"canonical\r\nbytes\r\n")
    (repo / ".gitattributes").write_text(f"app.txt {attribute}\n")
    info = Path(_git(repo, "rev-parse", "--git-path", "info/attributes"))
    info.write_text("app.txt !text !filter\n")
    _git(repo, "add", "--", "app.txt", ".gitattributes")
    _git(repo, "commit", "-qm", "source attribute override")
    marker = fixture.root / "filter-ran"
    configuration = fixture.root / "global-config"
    _git(repo, "config", "--file", str(configuration), "filter.bootstrap.clean", f'touch "{marker}"; cat')
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(configuration))
    assert FF_API["transformation_gate"](repo, b"app.txt\0.gitattributes\0") is None
    observed_error = None
    try:
        commit = _git(repo, "rev-parse", "HEAD")
        _materialize_committed_implementation(fixture, commit, commit)
    except ValueError as error:
        observed_error = str(error)
    assert not marker.exists(), "bootstrap ran a filter after losing source info/attributes"
    assert observed_error == "transformations=unsupported"
    target = fixture.root / "committed-target"
    assert FF_API["git_bytes"](target, "ls-files", "--stage", "-z") == b""


@pytest.mark.parametrize("drift", ["blob", "mode"])
def test_bootstrap_rejects_staged_identity_drift_before_commit(tmp_path, monkeypatch, drift):
    fixture = BoundaryFixture(tmp_path, b"specification\n", "bootstrap-staged-drift")
    repo = fixture.repository
    (repo / "app.py").write_bytes(b"implementation\n")
    (repo / "app.py").chmod(0o755)
    _git(repo, "add", "--", "app.py")
    _git(repo, "commit", "-qm", "executable implementation")
    commit = _git(repo, "rev-parse", "HEAD")
    oid = _git(repo, "rev-parse", "HEAD:README.md" if drift == "blob" else "HEAD:app.py")
    mode = "100755" if drift == "blob" else "100644"
    target = fixture.root / "committed-target"
    real_run = subprocess.run

    def mutate_staged_index(command, **kwargs):
        observed = real_run(command, **kwargs)
        if str(target) in command and "add" in command and observed.returncode == 0:
            mutation, environment = FF_API["git_process"](
                target, "update-index", "--cacheinfo", f"{mode},{oid},app.py",
            )
            real_run(mutation, env=environment, check=True, capture_output=True)
        return observed

    monkeypatch.setattr(subprocess, "run", mutate_staged_index)
    with pytest.raises(ValueError, match="bootstrap=staged-mismatch"):
        _materialize_committed_implementation(fixture, commit, commit)
    assert FF_API["git"](target, "rev-parse", "--verify", "HEAD") is None


def test_first_implementation_pass_enters_stage_14_at_atomic_checkpoint_7(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"specification\n", "implementation-checkpoint")
    repo = fixture.repository
    plan = Path("docs/superpowers/plans/2026-08-25-alpha.md")
    (repo / plan).parent.mkdir(parents=True, exist_ok=True)
    (repo / plan).write_bytes(b"plan\n")
    source = repo / "app.py"
    source.write_bytes(b"\x00\xffexact\r\n")
    source.chmod(0o755)
    (repo / "unchanged-link").symlink_to("app.py\n")
    _git(repo, "add", "--", plan.as_posix(), "app.py", "unchanged-link")
    _git(repo, "commit", "-qm", "frozen authorities and existing implementation")
    base = _git(repo, "rev-parse", "HEAD")
    source.write_bytes(b"\x00\xffreviewed\r\n")
    _git(repo, "add", "--", "app.py")
    _git(repo, "commit", "-qm", "complete implementation")
    reviewed_commit = _git(repo, "rev-parse", "HEAD")
    exclude = Path(_git(repo, "rev-parse", "--git-path", "info/exclude"))
    exclude.write_text("ignored.cache\n")
    (repo / "ignored.cache").write_bytes(b"excluded from review")
    # The transport reads the committed object even when these checkout bytes drift.
    source.write_bytes(b"unreviewed checkout bytes")
    manifest = _materialize_committed_implementation(fixture, reviewed_commit, base)
    assert (fixture.target / "app.py").read_bytes() == b"\x00\xffreviewed\r\n"
    assert (fixture.target / "app.py").stat().st_mode & stat.S_IXUSR
    assert not (fixture.target / "ignored.cache").exists()
    assert not (fixture.target / "unchanged-link").exists()
    assert not (fixture.target / fixture.ledger_path.relative_to(repo)).exists()
    assert json.loads(manifest.read_text()) == [
        {"path": "unchanged-link", "mode": "120000", "target": "app.py\n"},
    ]
    source.write_bytes(b"\x00\xffreviewed\r\n")
    frozen = {
        name: {"path": path.as_posix(), "blob": _git(repo, "rev-parse", f"HEAD:{path}")}
        for name, path in (("specification", RELATIVE_CANDIDATE), ("plan", plan))
    }
    authorities = []
    for name, item in frozen.items():
        authority = fixture.root / f"{name}-authority.md"
        authority.write_bytes(FF_API["git_bytes"](repo, "cat-file", "blob", item["blob"]))
        authorities.append(authority)
    intent = fixture.intent()
    intent = type(intent)(**{**intent.__dict__, "ground_truth": (*authorities, manifest)})
    run_state = fixture.create_run(intent)
    data = fixture._head()
    data.update(stage={"id": 10, "state": "active"}, frozen=frozen,
                next_action="await or recover the active review")
    dispatch = "implementation-1"
    receipt_path = fixture.receipt_path(dispatch)
    data["review"].update(
        kind="implementation", state="review_active", root_identity=reviewed_commit,
        dispatch_id=dispatch, run_ref=str(run_state.run_root), target_seal=run_state.governing_seal,
        evidence_path=receipt_path.relative_to(repo).as_posix(),
    )
    fixture._write_head(data)
    progress = f"| Task 1 | complete | {reviewed_commit} | deterministic fixture checks passed | |"
    fixture.ledger_path.write_text(fixture.ledger_path.read_text().replace("|  |  |  |  |  |", progress))
    before_review = fixture.ledger_path.read_bytes()
    stage0 = fixture.stage0(run_state)
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.run_triage(round1, triager=fixture.triager())
    assert fixture.ledger_path.read_bytes() == before_review
    run_state, result, ids = _map_controller_return(triage)
    report_ids, artifact_id, triage_ids = _triage_evidence(round1, run_state)
    assert result == "pass" and ids == triage_ids == []
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps({
        "schema": "feature-forge/review-receipt/v1", "kind": "implementation",
        "dispatch_id": dispatch, "run_ref": str(run_state.run_root),
        "target_seal": run_state.governing_seal,
        "source_identity": {"kind": "reviewed_commit", "path": None, "value": reviewed_commit},
        "result": "pass", "actionable_finding_ids": [],
        "feature_forge_charter_id": "feature-forge/implementation-review/v1",
        "completion_criterion": "No grounded discrepancies remain.",
        "raw_report_ids": report_ids, "triage_artifact_id": artifact_id,
        "triage_finding_ids": [], "stable_id_mapping": [],
    }))
    data["review"].update(state="pass", reviewed_commit=reviewed_commit)
    data.update(stage={"id": 14, "state": "active"}, next_action="claim alpha-finish")
    fixture._write_head(data)
    fixture.ledger_path.write_text(
        fixture.ledger_path.read_text().replace("|  |  |  |  |  |", progress)
        + "\n## Finish journal\n\nfinish_id alpha-finish; phase ready; outcome pending.\n"
    )
    report = fixture.ledger_path.with_name("final-report.md")
    report.write_text("Verification and acceptance passed. Finish outcome pending.\n")
    _git(repo, "add", "--", *(path.relative_to(repo).as_posix() for path in (receipt_path, fixture.ledger_path, report)))
    _git(repo, "commit", "-qm", "checkpoint 7: acceptance and Finish ready")
    checkpoint = _git(repo, "rev-parse", "HEAD")
    assert _git(repo, "rev-parse", "HEAD^") == reviewed_commit
    assert _git(repo, "status", "--porcelain") == ""
    for gate in ("identities", "reviewed-snapshot", "audit"):
        observed = subprocess.run(
            [sys.executable, str(FF_CHECK), gate, "--repo", str(repo), "--run", str(report.parent)],
            capture_output=True, text=True,
        )
        assert observed.returncode == 0, observed.stderr
        assert _git(repo, "rev-parse", "HEAD") == checkpoint
        assert _git(repo, "status", "--porcelain") == ""


def test_same_kind_redispatch_retains_root_round_and_finding_history(tmp_path):
    first = BoundaryFixture(tmp_path, b"candidate v1\n", "history-first")
    first.begin_review("history-1")
    head = first._load_head()
    head["review"].update(state="changes_required", round=2,
                         previous_open_finding_ids=["FF-older"], open_finding_ids=["FF-prior"])
    head.update(stage={"id": 4, "state": "active"})
    first._write_head(head)
    second = BoundaryFixture(tmp_path, b"candidate v2\n", "history-second", repository=first.repository)
    second.begin_review("history-2")
    current = second._load_head()["review"]
    assert current["root_identity"] == head["review"]["root_identity"]
    assert current["round"] == 2
    assert current["previous_open_finding_ids"] == ["FF-older"]
    assert current["open_finding_ids"] == ["FF-prior"]
    assert current["dispatch_id"] == "history-2"
    assert current["run_ref"] != head["review"]["run_ref"]


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


def _exact_candidate_bytes(root: Path, path: Path) -> bytes:
    relative = path.absolute().relative_to(root.absolute())
    current = root
    if not stat.S_ISDIR(current.lstat().st_mode):
        raise ValueError("candidate root is unavailable")
    for index, part in enumerate(relative.parts):
        current /= part
        mode = current.lstat().st_mode
        if index == len(relative.parts) - 1:
            if not stat.S_ISREG(mode):
                raise ValueError("candidate is not an exact regular file")
        elif not stat.S_ISDIR(mode):
            raise ValueError("candidate ancestor is not a real directory")
    return path.read_bytes()


def _absent_entry_under_real_directories(root: Path, path: Path) -> bool:
    relative = path.absolute().relative_to(root.absolute())
    current = root
    if not stat.S_ISDIR(current.lstat().st_mode):
        return False
    for index, part in enumerate(relative.parts):
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return True
        if index == len(relative.parts) - 1:
            return False
        if not stat.S_ISDIR(mode):
            return False
    return False


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


def _assert_production_audit_passes(fixture: "BoundaryFixture") -> None:
    checked = subprocess.run(
        [sys.executable, str(FF_CHECK), "audit", "--repo", str(fixture.repository),
         "--run", str(fixture.ledger_path.parent)],
        text=True, capture_output=True, check=False,
    )
    assert checked.returncode == 0, checked.stderr
    assert checked.stdout == "FF-CHECK v1 gate=audit status=pass\n"


class BoundaryFixture:
    """A disposable subject plus minimal validated controller dispatchers."""

    def __init__(
        self, tmp_path: Path, candidate: bytes, name: str, *, repository: Path | None = None,
    ) -> None:
        self.root = tmp_path / name
        self.root.mkdir()
        self.reservations: list[dict[str, object]] = []
        if repository is None:
            primary = self.root / "feature-forge-primary"
            primary.mkdir()
            _git(primary, "init", "-q")
            _git(primary, "config", "user.name", "Feature Forge fixture")
            _git(primary, "config", "user.email", "fixture@example.invalid")
            (primary / "README.md").write_text("fixture\n")
            _git(primary, "add", "README.md")
            _git(primary, "commit", "-qm", "seed")
            _git(primary, "branch", "-M", "main")
            self.repository = self.root / "feature-forge-repository"
            _git(primary, "worktree", "add", "-qb", "feature/alpha", str(self.repository), "HEAD")
        else:
            self.repository = repository
        self.source = self.repository / RELATIVE_CANDIDATE
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_bytes(candidate)
        if repository is None:
            _git(self.repository, "add", RELATIVE_CANDIDATE.as_posix())
            _git(self.repository, "commit", "-qm", "candidate source")
        else:
            _git(self.repository, "add", RELATIVE_CANDIDATE.as_posix())
            _git(self.repository, "commit", "-qm", "correct candidate")
        self.source_commit = _git(self.repository, "rev-parse", "HEAD")
        # Capture once, before the disposable target exists.  All later reads
        # intentionally use source_identity to detect drift against this value.
        self.captured_candidate = _exact_candidate_bytes(self.repository, self.source)
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
        self.round1_outcome = None
        self.mapper = None
        self.triage_id_overrides = []
        self.mapping_decisions = []
        self.prior_receipt = None
        if self.ledger_path.exists():
            previous_review = self._load_head()["review"]
            if previous_review["evidence_path"]:
                receipt_path = self.repository / previous_review["evidence_path"]
                if receipt_path.is_file():
                    self.prior_receipt, error = FF_API["strict_receipt"](receipt_path)
                    assert error is None
        else:
            self._write_head(self._head())

    @property
    def candidate_sha256(self) -> str:
        return hashlib.sha256(_exact_candidate_bytes(self.repository, self.source)).hexdigest()

    @property
    def source_identity(self) -> dict[str, object]:
        return _candidate_identity(_exact_candidate_bytes(self.repository, self.source))

    @property
    def ledger_path(self) -> Path:
        return self.repository / "docs/feature-forge/runs/2026-08-25-alpha/ledger.md"

    def _head(self) -> dict[str, object]:
        return {
            "schema": "feature-forge/ledger/v1", "run_id": "alpha", "mode": "supervised", "status": "active",
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

    def _write_head(
        self, head: dict[str, object], reservations: list[dict[str, object]] | None = None,
    ) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        persisted = (
            self._load_reservations() if reservations is None and self.ledger_path.exists()
            else reservations or []
        )
        reservations = "".join(
            "RESERVATION " + json.dumps(item, sort_keys=True) + "\n"
            for item in persisted
        )
        history = [line for line in self.ledger_path.read_text().splitlines()
                   if line.startswith("MAPPING ")] if self.ledger_path.exists() else []
        if self.mapping_decisions:
            history.append("MAPPING " + json.dumps(self.mapping_decisions, sort_keys=True))
            self.mapping_decisions = []
        self.ledger_path.write_text(
            "```json\n" + json.dumps(head, sort_keys=True) + "\n```\n\nFixture ledger.\n" + reservations + "\n".join(history) + "\n\n## Implementation progress\n\n| plan task | status | commit | evidence | notes |\n| --- | --- | --- | --- | --- |\n|  |  |  |  |  |\n"
        )

    def _load_reservations(self) -> list[dict[str, object]]:
        reservations = []
        for line in self.ledger_path.read_text().splitlines():
            if line.startswith("RESERVATION "):
                item = json.loads(line.removeprefix("RESERVATION "))
                if not isinstance(item, dict):
                    raise ValueError("invalid review reservation")
                reservations.append(item)
        return reservations

    def reserve_review(self, dispatch_id: str) -> dict[str, object]:
        path = self.receipt_path(dispatch_id)
        reservations = self._load_reservations()
        if path.exists() or path.is_symlink():
            raise ValueError("receipt path is already allocated")
        if not _absent_entry_under_real_directories(self.repository, path):
            raise ValueError("receipt path is unavailable")
        if any(
            item["dispatch_id"] == dispatch_id for item in reservations
        ):
            raise ValueError("receipt path is already allocated")
        reservation = {
            "dispatch_id": dispatch_id,
            "run_ref": str(self.run_root),
            "evidence_path": path.relative_to(self.repository).as_posix(),
            "source_identity": self.captured_identity,
        }
        reservations.append(reservation)
        self.reservations = reservations
        head = self._load_head()
        head.update(status="blocked", stage={"id": 5, "state": "blocked"}, next_action="create-or-recover")
        retained = head["review"] if head["review"]["kind"] == "specification" else None
        head["review"] = {
            "kind": "specification", "state": "blocked", "round": 0,
            "root_identity": self.captured_identity["value"], "dispatch_id": None,
            "run_ref": None, "target_seal": None, "evidence_path": None,
            "reviewed_commit": None, "previous_open_finding_ids": [], "open_finding_ids": [],
        }
        if retained is not None:
            for key in ("root_identity", "round", "previous_open_finding_ids", "open_finding_ids"):
                head["review"][key] = retained[key]
        self._write_head(head, reservations)
        return reservation

    def begin_review(self, dispatch_id: str):
        self.reserve_review(dispatch_id)
        run_state = self.create_or_recover_review(dispatch_id)
        assert run_state is not None
        return run_state

    def create_or_recover_review(self, dispatch_id: str):
        reservation = next(
            (item for item in self._load_reservations() if item["dispatch_id"] == dispatch_id),
            None,
        )
        if reservation is None:
            raise ValueError("review has no durable reservation")
        if Path(str(reservation["run_ref"])).exists():
            head = self._load_head()
            head["next_action"] = "resolve existing external review run root"
            self._write_head(head)
            return None
        run_state = self.create_run(self.intent())
        self.persist_review_active(dispatch_id, run_state)
        return run_state

    def persist_review_active(self, dispatch_id: str, run_state) -> dict[str, object]:
        path = self.receipt_path(dispatch_id)
        if path.exists() or path.is_symlink():
            raise ValueError("receipt path is already allocated")
        if not _absent_entry_under_real_directories(self.repository, path):
            raise ValueError("receipt path is unavailable")
        reservation = next((
            item for item in self._load_reservations()
            if item["dispatch_id"] == dispatch_id
        ), None)
        if reservation is None or reservation["run_ref"] != str(run_state.run_root):
            raise ValueError("review has no matching durable reservation")
        head = self._load_head()
        head.update(status="active", stage={"id": 5, "state": "active"}, next_action="await or recover the active review")
        retained = head["review"]
        head["review"] = {
            "kind": "specification", "state": "review_active", "round": 0,
            "root_identity": self.captured_identity["value"], "dispatch_id": dispatch_id,
            "run_ref": str(run_state.run_root), "target_seal": run_state.governing_seal,
            "evidence_path": path.relative_to(self.repository).as_posix(), "reviewed_commit": None,
            "previous_open_finding_ids": [], "open_finding_ids": [],
        }
        for key in ("root_identity", "round", "previous_open_finding_ids", "open_finding_ids"):
            head["review"][key] = retained[key]
        self.reservations = [
            item for item in self._load_reservations()
            if item["dispatch_id"] != dispatch_id
        ]
        self._write_head(head, [])
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

    def create_run(self, intent):
        with trusted_review_loop_environment(FF_API["git_process"], self.target):
            return self.controller.create_run(intent)

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

    def run_round1(self, stage0, **kwargs):
        with trusted_review_loop_environment(FF_API["git_process"], self.target):
            self.round1_outcome = self.controller.run_round1(stage0, **kwargs)
        return self.round1_outcome

    def run_triage(self, round1, **kwargs):
        with trusted_review_loop_environment(FF_API["git_process"], self.target):
            return self.controller.run_triage(round1, **kwargs)

    def triager(self, *, actionable: bool = False):
        def dispatch(expectation: RoleExpectation) -> ValidatedRoleArtifact:
            self.events.append("triage")
            findings = []
            if actionable:
                for report_id, raw_findings in expectation.extra["raw_findings"].items():
                    for finding_id, (claim, severity, locators) in raw_findings.items():
                        findings.append({
                            "canonical_id": self.triage_id_overrides[len(findings)] if self.triage_id_overrides else f"actionable-{report_id}-{finding_id}",
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
        with trusted_review_loop_environment(FF_API["git_process"], self.target):
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
        evidence: dict[str, object] | None = None,
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
        if not _absent_entry_under_real_directories(self.repository, path):
            raise ValueError("receipt path is unavailable")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not _absent_entry_under_real_directories(self.repository, path):
            raise ValueError("receipt path is unavailable")
        if evidence is None:
            _, expected_result, expected_ids, evidence = self.return_evidence(dispatch_id, run_state)
            if (result, actionable_ids) != (expected_result, expected_ids):
                raise ValueError("receipt result is inconsistent with the controller return")
        payload = {
            **evidence,
            "schema": "feature-forge/review-receipt/v1",
            "kind": "specification",
            "dispatch_id": dispatch_id,
            "run_ref": str(run_state.run_root),
            "target_seal": run_state.governing_seal,
            "source_identity": captured_identity,
            "result": result,
            "actionable_finding_ids": sorted(set(actionable_ids)),
        }
        projected = copy.deepcopy(review)
        if actionable_ids:
            projected["previous_open_finding_ids"] = review["open_finding_ids"]
            projected["open_finding_ids"] = actionable_ids
            projected["round"] += 1
        elif result == "pass":
            projected["open_finding_ids"] = []
        if not FF_API["receipt_result_invariant"](payload, projected):
            raise ValueError("receipt result is inconsistent with the round state")
        with path.open("x") as handle:
            json.dump(payload, handle, sort_keys=True)
        return path

    def apply_result(self, result: str, actionable_ids: list[str]) -> None:
        head = self._load_head()
        projected = copy.deepcopy(head["review"])
        projected["state"] = result
        if actionable_ids:
            projected["previous_open_finding_ids"] = projected["open_finding_ids"]
            projected["open_finding_ids"] = sorted(set(actionable_ids))
            projected["round"] += 1
        elif result == "pass":
            projected["open_finding_ids"] = []
        self.apply_projected_review(projected)

    def apply_projected_review(self, projected: dict[str, object]) -> None:
        head = self._load_head()
        head["review"] = projected
        result = projected["state"]
        if result == "pass":
            head.update(status="active", stage={"id": 5, "state": "complete"}, next_action="freeze the reviewed specification")
        elif result == "changes_required":
            head.update(status="active", stage={"id": 3, "state": "active"}, next_action="correct the specification")
        else:
            head.update(status="blocked", stage={"id": 5, "state": "blocked"}, next_action="resolve the review blocker")
        self._write_head(head)

    def return_evidence(self, dispatch_id, outcome, *, round1_error=None):
        run_state, result, triage_ids = _map_controller_return(outcome, round1_error=round1_error)
        evidence = {
            "feature_forge_charter_id": "feature-forge/specification-review/v1",
            "completion_criterion": COMPLETION,
            "raw_report_ids": sorted(report.report_id for report in self.round1_outcome.raw_reports)
                              if self.round1_outcome else [],
            "triage_artifact_id": None, "triage_finding_ids": [], "stable_id_mapping": [],
        }
        if result == "blocked":
            return run_state, result, [], evidence
        report_ids, artifact_id, checked_ids = _triage_evidence(self.round1_outcome, run_state)
        artifact = _bound_triage(run_state.run_root, artifact_id, run_state.snapshot)
        assert checked_ids == triage_ids
        prior_findings = []
        if self.prior_receipt and self.prior_receipt["triage_artifact_id"] is not None:
            prior = self.prior_receipt
            previous_artifact = _bound_triage(Path(prior["run_ref"]), prior["triage_artifact_id"])
            assert sorted(previous_artifact["report_ids"]) == prior["raw_report_ids"]
            previous_mapping = {row["triage_finding_id"]: row["feature_forge_finding_id"]
                                for row in prior["stable_id_mapping"]}
            assert sorted(previous_mapping) == prior["triage_finding_ids"]
            assert sorted(f["id"] for f in previous_artifact["findings"]) == prior["triage_finding_ids"]
            prior_findings = [{"feature_forge_finding_id": previous_mapping[f["id"]], "triage_finding": f}
                              for f in previous_artifact["findings"]]
        assert sorted(row["feature_forge_finding_id"] for row in prior_findings) == self._load_head()["review"]["open_finding_ids"]
        semantic_input = {"prior_findings": prior_findings, "current_findings": artifact["findings"],
                          "materially_same_criterion": CRITERION}
        answer = self.mapper(semantic_input) if self.mapper else {
            "decisions": [{"triage_finding_id": f["id"], "decision": "new", "rationale": None}
                          for f in artifact["findings"]]}
        if not isinstance(answer, dict) or set(answer) != {"decisions"}:
            raise ValueError("invalid mapper return")
        mapped = FF_API["apply_stable_id_decisions"]({"dispatch_id": dispatch_id, **semantic_input, **answer})
        if (set(mapped) != {"schema", "status", "stable_id_mapping", "error"}
                or mapped["schema"] != "feature-forge/stable-id-map/v1"
                or mapped["status"] != "pass" or mapped["error"] is not None):
            raise ValueError("invalid mapper return")
        self.mapping_decisions = answer["decisions"]
        evidence.update(raw_report_ids=report_ids, triage_artifact_id=artifact_id,
                        triage_finding_ids=triage_ids, stable_id_mapping=mapped["stable_id_mapping"])
        ids = sorted(row["feature_forge_finding_id"] for row in mapped["stable_id_mapping"])
        review = self._load_head()["review"]
        if FF_API["review_must_block"](review["round"] + 1, review["open_finding_ids"], ids):
            result = "blocked"
        return run_state, result, ids, evidence

    def record_controller_return(self, dispatch_id: str, outcome, *, round1_error: ControllerError | None = None) -> Path:
        run_state, result, ids, evidence = self.return_evidence(dispatch_id, outcome, round1_error=round1_error)
        receipt = self.write_receipt(dispatch_id, run_state, result, ids, self.captured_identity, evidence)
        self.apply_result(result, ids)
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
    actionable_ids = sorted(
        row["id"] for row in rows
    )
    return outcome, ("changes_required" if actionable_ids else "pass"), actionable_ids


def _bound_triage(run_root, artifact_id, snapshot=None):
    snapshot = snapshot or json.loads((run_root / "review-state.json").read_text())
    registry = snapshot["artifact_registry"]
    metadata = registry["artifacts"][artifact_id]
    assert metadata["kind"] == "triage-result"
    assert metadata["target_seal"] == snapshot["governing_seal"]
    assert any(binding["operation"] == "apply_ledger_decisions" and artifact_id in binding["source_ids"]
               for binding in registry["bindings"])
    assert Path(artifact_id).name == artifact_id
    raw = (run_root / "evidence" / artifact_id).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == metadata["digest"]
    artifact = json.loads(raw)
    assert all(finding["target_seal"] == snapshot["governing_seal"] for finding in artifact["findings"])
    return artifact


def _triage_evidence(round1, outcome):
    assert round1 is not None
    triage_ids = sorted(row["id"] for row in outcome.snapshot["processor_state"]["apply_ledger_decisions"]["rows"])
    report_ids = sorted(report.report_id for report in round1.raw_reports)
    triage_artifacts = [artifact_id for artifact_id, item in outcome.snapshot["artifact_registry"]["artifacts"].items()
                        if item["kind"] == "triage-result"]
    assert len(triage_artifacts) == 1
    artifact_id = triage_artifacts[0]
    artifact = _bound_triage(outcome.run_root, artifact_id, outcome.snapshot)
    assert sorted(artifact["report_ids"]) == report_ids
    assert sorted(f["id"] for f in artifact["findings"]) == triage_ids
    return report_ids, artifact_id, triage_ids


def _nonempty_triage(fixture, run_state, severity="Important"):
    stage0 = fixture.stage0(run_state)
    source = ({"id": "raw-source", "claim": "REQ-007 has no acceptance check", "severity": severity,
               "locator_ids": [RELATIVE_CANDIDATE.as_posix()]},)
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer(findings=source))
    return fixture.run_triage(round1, triager=fixture.triager(actionable=True))


def _nonempty_receipt(fixture, dispatch, run_state):
    outcome = _nonempty_triage(fixture, run_state)
    run_state, result, ids, evidence = fixture.return_evidence(dispatch, outcome)
    return fixture.write_receipt(dispatch, run_state, result, ids, fixture.captured_identity, evidence)


@pytest.mark.parametrize("defect", ["missing", "unknown-prior", "rationale", "reuse-twice", "extra-output"])
def test_mapping_judgment_errors_block_before_receipt_creation(tmp_path, defect):
    first = BoundaryFixture(tmp_path, b"candidate v1\\n", "mapper-prior")
    previous = first.begin_review("mapper-prior")
    _recover_receipt(first, _nonempty_receipt(first, "mapper-prior", previous))
    fixture = BoundaryFixture(tmp_path, b"candidate v2\\n", "mapper-current", repository=first.repository)
    current = fixture.begin_review("mapper-current")
    outcome = _nonempty_triage(fixture, current)
    def mapper(packet):
        assert set(packet) == {"prior_findings", "current_findings", "materially_same_criterion"}
        assert packet["materially_same_criterion"] == CRITERION
        assert all(row["sources"][0]["claim"] == "REQ-007 has no acceptance check" for row in packet["current_findings"])
        assert all("sources" in row["triage_finding"] for row in packet["prior_findings"])
        decisions = [{"triage_finding_id": f["id"], "decision": p["feature_forge_finding_id"], "rationale": "same discrepancy"}
                     for f, p in zip(packet["current_findings"], packet["prior_findings"])]
        assert len(decisions) >= 2
        if defect == "missing":
            decisions.pop()
        elif defect == "unknown-prior":
            decisions[0]["decision"] = "FF-unknown"
        elif defect == "rationale":
            decisions[0]["rationale"] = None
        elif defect == "reuse-twice":
            decisions[1]["decision"] = decisions[0]["decision"]
        else:
            return {"decisions": decisions, "extra": True}
        return {"decisions": decisions}
    fixture.mapper = mapper
    before = fixture.ledger_path.read_bytes()
    with pytest.raises(ValueError, match="invalid mapper return"):
        fixture.record_controller_return("mapper-current", outcome)
    assert not fixture.receipt_path("mapper-current").exists()
    assert fixture.ledger_path.read_bytes() == before


@pytest.mark.parametrize("defect", ["digest", "binding", "report-inventory", "finding-inventory"])
def test_controller_evidence_checks_reject_inconsistent_triage(tmp_path, defect):
    fixture = BoundaryFixture(tmp_path, b"candidate\\n", "evidence")
    run_state = fixture.begin_review("evidence-1")
    outcome = _nonempty_triage(fixture, run_state)
    registry = outcome.snapshot["artifact_registry"]
    artifact_id = next(key for key, value in registry["artifacts"].items() if value["kind"] == "triage-result")
    if defect == "digest":
        (outcome.run_root / "evidence" / artifact_id).write_text("{}")
    elif defect == "binding":
        registry["bindings"] = [b for b in registry["bindings"] if b["operation"] != "apply_ledger_decisions"]
    elif defect == "report-inventory":
        fixture.round1_outcome = type("IncompleteRound1", (), {"raw_reports": ()})()
    else:
        outcome.snapshot["processor_state"]["apply_ledger_decisions"]["rows"] = []
    with pytest.raises(AssertionError):
        fixture.record_controller_return("evidence-1", outcome)
    assert not fixture.receipt_path("evidence-1").exists()


def test_pretriage_block_retains_usable_zero_finding_report_inventory(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\\n", "partial-reports")
    run_state = fixture.begin_review("partial-1")
    stage0 = fixture.stage0(run_state)
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer())
    receipt = fixture.record_controller_return("partial-1", stage0, round1_error=ControllerError("triage unavailable"))
    payload = json.loads(receipt.read_text())
    assert payload["result"] == "blocked" and payload["triage_artifact_id"] is None
    assert payload["raw_report_ids"] == sorted(report.report_id for report in round1.raw_reports)
    assert payload["raw_report_ids"] and payload["triage_finding_ids"] == []
    _assert_production_audit_passes(fixture)


def test_same_kind_pretriage_block_retains_round_and_both_finding_histories(tmp_path):
    first = BoundaryFixture(tmp_path, b"candidate v1\n", "pretriage-first")
    first_run = first.begin_review("pretriage-1")
    _recover_receipt(first, _nonempty_receipt(first, "pretriage-1", first_run))
    before = copy.deepcopy(first._load_head()["review"])
    assert before["state"] == "changes_required"

    second = BoundaryFixture(
        tmp_path, b"candidate v2\n", "pretriage-second", repository=first.repository,
    )
    second_run = second.begin_review("pretriage-2")
    stage0 = second.stage0(second_run)
    receipt = second.record_controller_return(
        "pretriage-2", stage0,
        round1_error=ControllerError("reviewer failed before Round1Outcome returned"),
    )
    payload = json.loads(receipt.read_text())
    after = second._load_head()["review"]

    assert payload["result"] == "blocked"
    assert payload["triage_artifact_id"] is None
    assert payload["triage_finding_ids"] == []
    assert payload["stable_id_mapping"] == []
    assert payload["actionable_finding_ids"] == []
    assert payload["raw_report_ids"] == []
    assert after["round"] == before["round"]
    assert after["previous_open_finding_ids"] == before["previous_open_finding_ids"]
    assert after["open_finding_ids"] == before["open_finding_ids"]
    _assert_production_audit_passes(second)


def _map_clean_return(fixture: BoundaryFixture, dispatch_id: str):
    captured_identity = fixture.captured_identity
    run_state = fixture.begin_review(dispatch_id)
    assert run_state.run_root == fixture.run_root
    assert run_state.governing_seal
    assert run_state.snapshot["processor_state"]["preflight"]["invocation_intent"]["base"] == fixture.bootstrap_commit
    review_active = fixture._load_head()
    assert review_active["review"]["run_ref"] != str(fixture.target)
    assert not fixture.receipt_path(dispatch_id).exists()
    stage0 = fixture.stage0(run_state)
    assert stage0.run_state.stage == "STAGE0" and stage0.review_may_start
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.run_triage(round1, triager=fixture.triager())
    assert triage.stage == "TRIAGE"
    assert triage.snapshot["processor_state"]["apply_ledger_decisions"]["rows"] == []
    assert fixture.source_identity == captured_identity
    assert fixture._load_head()["review"]["state"] == "review_active"
    receipt = fixture.record_controller_return(dispatch_id, triage)
    return triage, receipt, captured_identity


@pytest.mark.parametrize("operation", ["create_run", "run_stage0", "run_round1", "run_triage"])
@pytest.mark.parametrize("hostile", ["routing", "fsmonitor"])
def test_controller_handoff_preserves_target_identity_and_blocks_programs(
    tmp_path, monkeypatch, operation, hostile,
):
    """Every public handoff must seal the intended target without ambient Git effects."""
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "trusted-handoff")
    expected = seal_target(
        fixture.target,
        GitPolicy(enabled=True, base=fixture.bootstrap_commit, include_untracked=True),
    ).digest
    if operation != "create_run":
        run_state = fixture.begin_review("trusted-1")
    if operation in {"run_round1", "run_triage"}:
        stage0 = fixture.stage0(run_state)
    if operation == "run_triage":
        round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer())

    marker = fixture.root / "fsmonitor-ran"
    program = fixture.root / "fsmonitor"
    program.write_text(f"#!/bin/sh\n: > {shlex.quote(str(marker))}\nexit 0\n")
    program.chmod(0o755)
    _git(fixture.target, "config", "core.fsmonitor", str(program))
    if hostile == "routing":
        foreign = fixture.root / "foreign"
        _git(fixture.root, "clone", "-q", "--no-hardlinks", str(fixture.target), str(foreign))
        _git(foreign, "config", "user.name", "Foreign")
        _git(foreign, "config", "user.email", "foreign@example.invalid")
        (foreign / "foreign.txt").write_text("foreign identity\n")
        _git(foreign, "add", "foreign.txt")
        _git(foreign, "commit", "-qm", "foreign head")
        for key, value in {
            "GIT_DIR": str(foreign / ".git"), "GIT_WORK_TREE": str(foreign),
            "GIT_COMMON_DIR": str(foreign / ".git"),
            "GIT_INDEX_FILE": str(foreign / ".git/index"),
            "GIT_OBJECT_DIRECTORY": str(foreign / ".git/objects"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(foreign / ".git/objects"),
        }.items():
            monkeypatch.setenv(key, value)
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", f"'core.fsmonitor={program}'")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(program))
    monkeypatch.setenv("GIT_CONFIG_KEY_37", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_37", str(fixture.root))
    original_environment = dict(os.environ)

    if operation == "create_run":
        outcome = fixture.begin_review("trusted-1")
    elif operation == "run_stage0":
        outcome = fixture.stage0(run_state).run_state
    elif operation == "run_round1":
        outcome = fixture.run_round1(stage0, dispatch_role=fixture.reviewer()).run_state
    else:
        outcome = fixture.run_triage(round1, triager=fixture.triager())
    assert outcome.stage == {
        "create_run": "PREFLIGHT", "run_stage0": "STAGE0",
        "run_round1": "REVIEW", "run_triage": "TRIAGE",
    }[operation]
    assert outcome.governing_seal == expected
    assert not marker.exists(), "Review Loop Git executed the configured fsmonitor"
    assert dict(os.environ) == original_environment


def test_controller_handoff_restores_environment_after_real_reseal_failure(tmp_path, monkeypatch):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "failed-handoff")
    run_state = fixture.begin_review("failure-1")
    (fixture.target / RELATIVE_CANDIDATE).write_bytes(b"actual target drift\n")
    monkeypatch.setenv("GIT_DIR", str(fixture.root / "absent-git-dir"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "17")
    original_environment = dict(os.environ)
    with pytest.raises(ControllerError, match="authoritative target drifted"):
        fixture.stage0(run_state)
    assert dict(os.environ) == original_environment


def _recover_receipt(fixture: BoundaryFixture, receipt: Path) -> None:
    """Recovery records a return only from one valid canonical Feature Forge receipt."""
    original_head: dict[str, object] | None = None
    try:
        head = fixture._load_head()
        original_head = head
        review = head["review"]
        if review["state"] != "review_active":
            raise ValueError("recovery requires an active review")
        canonical = fixture.receipt_path(str(review["dispatch_id"]))
        current = fixture.repository
        for part in receipt.relative_to(current).parts:
            current /= part
            if current.is_symlink():
                raise ValueError("canonical receipt follows a symlink")
        if not receipt.is_file():
            raise ValueError("canonical receipt is not a regular file")
        if receipt != canonical:
            raise ValueError("invalid receipt")
        projected, checked = FF_API["recover_review_return"](
            fixture.repository, fixture.ledger_path.parent, head,
        )
        if checked.status != "pass" or projected is None:
            raise ValueError("invalid receipt")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        fixture.block_recovery()
        return
    fixture.apply_projected_review(projected)
    audited = subprocess.run(
        [sys.executable, str(FF_CHECK), "audit", "--repo", str(fixture.repository),
         "--run", str(fixture.ledger_path.parent)],
        text=True, capture_output=True,
    )
    if audited.returncode != 0:
        assert original_head is not None
        fixture._write_head(original_head)
        fixture.block_recovery()


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
        "feature_forge_charter_id": "feature-forge/specification-review/v1",
        "completion_criterion": COMPLETION,
        "raw_report_ids": sorted(report.report_id for report in first.round1_outcome.raw_reports),
        "triage_artifact_id": receipt_data["triage_artifact_id"],
        "triage_finding_ids": [], "stable_id_mapping": [],
    }
    assert receipt_data["triage_artifact_id"]
    assert receipt_data["raw_report_ids"]
    assert first.run_root.is_relative_to(first.root)
    assert not first.run_root.is_relative_to(first.target)
    assert receipt_one.relative_to(first.repository).as_posix().startswith(
        "docs/feature-forge/runs/2026-08-25-alpha/reviews/"
    )
    assert receipt_one != first.run_root
    assert first._load_head()["status"] == "active"
    assert first._load_head()["stage"] == {"id": 5, "state": "complete"}
    assert first._load_head()["next_action"] == "freeze the reviewed specification"
    assert first._load_head()["review"]["round"] == 0
    _assert_production_audit_passes(first)

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
    stopped_run = stopped.begin_review("stop-1")
    stopped_stage0 = stopped.stage0(stopped_run, scout_fails=True)
    assert stopped_stage0.run_state.stage == "INDETERMINATE"
    assert stopped.events == ["scout", "scout"]
    stopped_receipt = stopped.record_controller_return("stop-1", stopped_stage0)
    assert json.loads(stopped_receipt.read_text())["result"] == stopped._load_head()["review"]["state"] == "blocked"
    assert stopped._load_head()["stage"] == {"id": 5, "state": "blocked"}

    failed_gate = BoundaryFixture(tmp_path, b"failed gate\n", "failed-gate")
    failed_gate_run = failed_gate.begin_review("gate-1")
    failed_stage0 = failed_gate.stage0(failed_gate_run, gate_fails=True)
    assert not failed_stage0.review_may_start
    assert failed_gate.events == ["scout", "gate:tests", "inventory-owner", "inventory-challenge"]
    failed_gate_receipt = failed_gate.record_controller_return("gate-1", failed_stage0)
    assert json.loads(failed_gate_receipt.read_text())["result"] == failed_gate._load_head()["review"]["state"] == "blocked"

    failed_round = BoundaryFixture(tmp_path, b"failed review\n", "failed-round")
    failed_round_run = failed_round.begin_review("round-1")
    reviewable = failed_round.stage0(failed_round_run)
    with pytest.raises(ControllerError, match="synthetic reviewer unavailable") as round1_failure:
        failed_round.run_round1(reviewable, dispatch_role=failed_round.reviewer(fail=True))
    assert "triage" not in failed_round.events
    failed_round_receipt = failed_round.record_controller_return("round-1", reviewable, round1_error=round1_failure.value)
    assert json.loads(failed_round_receipt.read_text())["result"] == failed_round._load_head()["review"]["state"] == "blocked"

    first.source.write_bytes(b"changed after return\n")
    with pytest.raises(ValueError, match="identity drifted"):
        first.write_receipt("drifted", triage_one, "pass", [], identity_one)


def test_boundary_containment_and_recovery_use_only_bound_evidence(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "containment")
    run_state = fixture.begin_review("recovery-1")
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
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.run_triage(round1, triager=fixture.triager())
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
    recovery_run = recovery.begin_review("recovery-2")
    transcript = fixture.run_root / "transcript.md"
    transcript.write_text("review-loop status is not a Feature Forge receipt\n")
    _recover_receipt(recovery, transcript)
    blocked = recovery._load_head()
    assert blocked["status"] == "blocked" and blocked["stage"]["state"] == "blocked"
    assert blocked["review"]["state"] == "review_active"
    with pytest.raises(ValueError, match="filename-safe"):
        recovery.receipt_path("../transcript")

    malformed = BoundaryFixture(tmp_path, b"candidate\n", "recovery-malformed")
    malformed_run = malformed.begin_review("malformed-1")
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


@pytest.mark.parametrize("severity", ["Important", "Critical"])
def test_actionable_triage_maps_changes_required_with_sorted_ids(tmp_path, severity):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "actionable")
    run_state = fixture.begin_review("actionable-1")
    stage0 = fixture.stage0(run_state)
    source_finding = ({"id": "raw-b", "claim": "needs a correction", "severity": severity,
                       "locator_ids": [RELATIVE_CANDIDATE.as_posix()]},)
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer(findings=source_finding))
    triage = fixture.run_triage(round1, triager=fixture.triager(actionable=True))
    actionable_ids = sorted(row["id"] for row in triage.snapshot["processor_state"]["apply_ledger_decisions"]["rows"])
    receipt = fixture.record_controller_return("actionable-1", triage)
    payload = json.loads(receipt.read_text())
    assert payload["result"] == fixture._load_head()["review"]["state"] == "changes_required"
    assert payload["triage_finding_ids"] == actionable_ids
    assert sorted(row["feature_forge_finding_id"] for row in payload["stable_id_mapping"]) == payload["actionable_finding_ids"]
    assert len(set(payload["actionable_finding_ids"])) == len(actionable_ids)
    assert fixture._load_head()["status"] == "active"
    assert fixture._load_head()["stage"] == {"id": 3, "state": "active"}
    assert fixture._load_head()["next_action"] == "correct the specification"

    recovery = BoundaryFixture(tmp_path, b"candidate\n", "actionable-recovery")
    recovery_run = recovery.begin_review("actionable-recovery-1")
    recovery_receipt = _nonempty_receipt(recovery, "actionable-recovery-1", recovery_run)
    _recover_receipt(recovery, recovery_receipt)
    assert recovery._load_head()["stage"] == {"id": 3, "state": "active"}
    assert recovery._load_head()["next_action"] == "correct the specification"


def test_residual_minor_triage_requires_correction(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "minor")
    run_state = fixture.begin_review("minor-1")
    stage0 = fixture.stage0(run_state)
    source_finding = ({"id": "raw-minor", "claim": "minor residual", "severity": "Minor",
                       "locator_ids": [RELATIVE_CANDIDATE.as_posix()]},)
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer(findings=source_finding))
    triage = fixture.run_triage(round1, triager=fixture.triager(actionable=True))
    receipt = fixture.record_controller_return("minor-1", triage)
    assert json.loads(receipt.read_text())["result"] == "changes_required"
    assert fixture._load_head()["review"]["open_finding_ids"]


@pytest.mark.parametrize("reuse", [False, True])
def test_completed_triage_blocks_at_cap_or_repeated_stable_set(tmp_path, reuse):
    previous = None
    for number in range(1, 3 if reuse else 4):
        fixture = BoundaryFixture(tmp_path, f"candidate {number}\\n".encode(), f"round-{number}",
                                  repository=previous.repository if previous else None)
        dispatch = f"round-{number}"
        run_state = fixture.begin_review(dispatch)
        if reuse:
            fixture.triage_id_overrides = ["red", "blue"] if number == 1 else ["seven", "eight"]
        if previous:
            assert fixture._load_head()["review"]["round"] == number - 1
        if reuse and previous:
            def mapper(packet):
                assert set(packet) == {"prior_findings", "current_findings", "materially_same_criterion"}
                assert packet["materially_same_criterion"] == CRITERION
                assert len(packet["prior_findings"]) == len(packet["current_findings"])
                decisions = []
                for prior, current in zip(packet["prior_findings"], packet["current_findings"]):
                    assert prior["triage_finding"]["id"] != current["id"]
                    assert prior["triage_finding"]["id"] in {"red", "blue"}
                    assert current["id"] in {"seven", "eight"}
                    assert prior["triage_finding"]["sources"][0]["claim"] == current["sources"][0]["claim"] == "REQ-007 has no acceptance check"
                    assert prior["triage_finding"]["evidence_locators"] == current["evidence_locators"]
                    assert set(current) == {"id", "sources", "source_ids", "reported_severity", "current_severity",
                                            "factual", "state", "evidence_locators", "target_seal"}
                    assert set(current["sources"][0]) == {"report_id", "finding_id", "claim", "severity", "locators"}
                    decisions.append({"triage_finding_id": current["id"], "decision": prior["feature_forge_finding_id"],
                                      "rationale": "same missing REQ-007 acceptance check"})
                return {"decisions": decisions}
            fixture.mapper = mapper
        receipt = _nonempty_receipt(fixture, dispatch, run_state)
        _recover_receipt(fixture, receipt)
        review = fixture._load_head()["review"]
        assert review["round"] == number
        if previous:
            assert review["root_identity"] == previous._load_head()["review"]["root_identity"]
        expected = "blocked" if number == (2 if reuse else 3) else "changes_required"
        assert review["state"] == expected
        payload = json.loads(receipt.read_text())
        assert payload["result"] == expected and payload["triage_artifact_id"]
        assert len(payload["stable_id_mapping"]) == len(payload["actionable_finding_ids"]) >= 1
        assert "MAPPING " in fixture.ledger_path.read_text()
        _assert_production_audit_passes(fixture)
        previous = fixture


def test_boundary_persists_reservation_before_create_run_and_review_active_before_stage0(
    tmp_path, monkeypatch,
):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "durable-head")
    create_run = fixture.controller.create_run

    def assert_reserved_before_create(intent):
        reserved_head = fixture._load_head()
        reservations = fixture._load_reservations()
        assert reserved_head["status"] == "blocked"
        assert reserved_head["next_action"] == "create-or-recover"
        assert reservations == [{
            "dispatch_id": "durable-1",
            "run_ref": str(fixture.run_root),
            "evidence_path": "docs/feature-forge/runs/2026-08-25-alpha/reviews/durable-1.json",
            "source_identity": fixture.captured_identity,
        }]
        return create_run(intent)

    monkeypatch.setattr(fixture.controller, "create_run", assert_reserved_before_create)
    run_state = fixture.begin_review("durable-1")
    head = fixture._load_head()
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


def test_boundary_stays_blocked_after_create_run_before_review_active_promotion(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "create-crash")
    reservation = fixture.reserve_review("crash-1")
    fixture.create_run(fixture.intent())
    fixture.reservations.clear()
    recovered = fixture._load_head()
    assert recovered["status"] == "blocked"
    assert recovered["next_action"] == "create-or-recover"
    assert reservation["run_ref"] == str(fixture.run_root)
    assert fixture.run_root.exists()
    assert fixture.events == []
    assert fixture.create_or_recover_review("crash-1") is None
    assert fixture._load_head()["next_action"] == "resolve existing external review run root"
    assert fixture.events == []


def test_boundary_rejects_a_symlinked_receipt_ancestor_before_create_run(
    tmp_path, monkeypatch,
):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "receipt-ancestor")
    reviews = fixture.receipt_path("symlinked-1").parent
    outside = fixture.root / "outside-reviews"
    outside.mkdir()
    reviews.symlink_to(outside, target_is_directory=True)
    create_run = fixture.controller.create_run
    calls = []

    def observed_create(intent):
        calls.append(intent)
        return create_run(intent)

    monkeypatch.setattr(fixture.controller, "create_run", observed_create)
    with pytest.raises(ValueError, match="receipt path is unavailable"):
        fixture.begin_review("symlinked-1")
    assert calls == []
    assert fixture._load_reservations() == []


def test_recovery_rejects_changes_required_when_the_candidate_drifted(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "recovery-drift")
    run_state = fixture.begin_review("drift-1")
    receipt = _nonempty_receipt(fixture, "drift-1", run_state)
    fixture.source.write_bytes(b"changed after review\n")
    _recover_receipt(fixture, receipt)
    recovered = fixture._load_head()
    assert recovered["status"] == "blocked"
    assert recovered["stage"] == {"id": 5, "state": "blocked"}
    assert recovered["review"]["state"] == "review_active"


def test_recovery_rejects_a_same_byte_candidate_symlink(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "recovery-symlink")
    run_state = fixture.begin_review("symlink-1")
    receipt = _nonempty_receipt(fixture, "symlink-1", run_state)
    same_bytes = fixture.root / "same-bytes.md"
    same_bytes.write_bytes(fixture.captured_candidate)
    fixture.source.unlink()
    fixture.source.symlink_to(same_bytes)
    _recover_receipt(fixture, receipt)
    recovered = fixture._load_head()
    assert recovered["status"] == "blocked"
    assert recovered["stage"] == {"id": 5, "state": "blocked"}
    assert recovered["review"]["state"] == "review_active"


def test_return_rejects_a_receipt_ancestor_swapped_to_a_symlink(tmp_path):
    fixture = BoundaryFixture(tmp_path, b"candidate\n", "return-symlink")
    run_state = fixture.begin_review("late-symlink-1")
    stage0 = fixture.stage0(run_state)
    round1 = fixture.run_round1(stage0, dispatch_role=fixture.reviewer())
    triage = fixture.run_triage(round1, triager=fixture.triager())
    receipt = fixture.receipt_path("late-symlink-1")
    outside = fixture.root / "outside-return-receipts"
    outside.mkdir()
    receipt.parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="receipt path is unavailable"):
        fixture.record_controller_return("late-symlink-1", triage)
    assert not (outside / receipt.name).exists()
    recovered = fixture._load_head()
    assert recovered["review"]["state"] == "review_active"
    assert recovered["stage"] == {"id": 5, "state": "active"}
