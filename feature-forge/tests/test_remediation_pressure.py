"""Black-box oracle regressions; no behavior subject receives this test module."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).parent / "behavior/remediation_pressure.py"
CASES = SCRIPT.parent / "pr7-remediation"
SPEC = "docs/superpowers/specs/2026-09-09-alpha-design.md"
PLAN = "docs/superpowers/plans/2026-09-09-alpha.md"
LEDGER = "docs/feature-forge/runs/2026-09-09-alpha/ledger.md"
OLD_HEAD = {"schema", "run_id", "status", "worktree", "branch", "base_identity", "stage", "next_action", "frozen", "review"}
OLD_RECEIPT = {"schema", "kind", "dispatch_id", "run_ref", "target_seal", "source_identity", "result", "actionable_finding_ids"}
NEW_RECEIPT = OLD_RECEIPT | {"feature_forge_charter_id", "completion_criterion", "raw_report_ids", "triage_artifact_id", "triage_finding_ids", "stable_id_mapping"}


def command(*args: str) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def prepared_fixture(tmp_path: Path, scenario: str, execution_mode: str | None = None, host: str = "codex") -> Path:
    root = tmp_path / "fixture"
    args = ["prepare", "--root", str(root), "--scenario", scenario, "--host", host]
    if execution_mode:
        args += ["--execution-mode", execution_mode]
    command(*args)
    return root


def metadata(root: Path) -> dict:
    return json.loads((root / "metadata.json").read_text())


def response_path(root: Path) -> Path:
    return Path(metadata(root)["response"])


def score(root: Path) -> dict:
    return command("score", "--root", str(root))


def parts(root: Path) -> tuple[Path, dict, str]:
    path = Path(metadata(root)["repo"]) / LEDGER
    match = re.fullmatch(r"```json\n(.*?)\n```\n(.*)", path.read_text(), re.S)
    assert match
    return path, json.loads(match[1]), match[2]


def write_blocked(root: Path, complete: bool = False) -> None:
    path, head, tail = parts(root)
    head.update(status="blocked", stage={"id": 9, "state": "blocked"}, next_action=f"reconcile or correct {PLAN}")
    tail += f"\n| return-drift | W-2 | blocked | {PLAN} |\n"
    if complete:
        tail += "\n| W-2 | complete | c222 | npm test -- tenant.types: pass |\n"
    path.write_text("```json\n" + json.dumps(head, indent=2) + "\n```\n" + tail)


def write_residual_response(root: Path, result: str = "changes_required", raw_report_ids: list[str] | None = None) -> None:
    _, head, _ = parts(root)
    finding = "FF-" + hashlib.sha256(b'["specification-2","TRIAGE-MINOR-1"]').hexdigest()
    head["review"].update(state=result, round=2, previous_open_finding_ids=["FF-OLD"], open_finding_ids=[finding])
    head.update(status="active", next_action="correct REQ-007 verification and re-review")
    if "mode" in head:
        head["stage"] = {"id": 4, "state": "active"}
    source = json.loads((Path(metadata(root)["repo"]) / "fixture-input.json").read_text())["public_return"]["source_identity"]
    receipt = {
        "schema": "feature-forge/review-receipt/v1", "kind": "specification",
        "dispatch_id": "specification-2", "run_ref": head["review"]["run_ref"],
        "target_seal": head["review"]["target_seal"], "source_identity": source,
        "result": result, "actionable_finding_ids": [finding],
        "feature_forge_charter_id": "feature-forge/specification-review/v1",
        "completion_criterion": "no unresolved in-scope findings",
        "raw_report_ids": ["report-empty", "report-minor"] if raw_report_ids is None else raw_report_ids,
        "triage_artifact_id": "triage-2", "triage_finding_ids": ["TRIAGE-MINOR-1"],
        "stable_id_mapping": [{"triage_finding_id": "TRIAGE-MINOR-1", "feature_forge_finding_id": finding}],
    }
    response_path(root).write_text(json.dumps({"receipt": receipt, "head": head}))


WORKER = """W-4; REQ-001; SCN-001
Owned paths: src/tenant/normalize.ts; tests/tenant/normalize.test.ts
Consumes: export type CanonicalTenant = { id: string; displayName: string }
Produces: export function normalizeTenantName(tenant: CanonicalTenant): string
trim displayName and collapse internal whitespace to one ASCII space; never write tenant.id
Dependency: W-2 commit c222 verified with npm test -- tenant.types: pass.
Authority: do not change frozen specification or plan; do not invent cross-task authority.
Goal: return commit and verification evidence for npm test -- tenant.normalize.
Failure: return blocked if required inputs, authority, or verification are missing.
"""


def test_worker_packet_score_requires_every_interface_and_boundary(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "worker-packet")
    response_path(root).write_text("Dispatch W-4 to implement normalizeTenantName.\n")
    assert score(root)["failures"] == ["authority-boundary", "consumed-interface", "dependency-evidence", "failure-condition", "goal-condition", "owned-paths", "produced-interface"]


def test_worker_packet_complete_output_passes(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "worker-packet")
    response_path(root).write_text(WORKER)
    assert score(root)["passed"] is True


def test_residual_minor_score_rejects_pass_and_missing_inventory(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "residual-minor")
    write_residual_response(root, result="pass", raw_report_ids=["report-minor"])
    assert score(root)["failures"] == ["all-findings-actionable", "raw-report-inventory"]


def test_residual_minor_complete_receipt_and_head_pass(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "residual-minor")
    write_residual_response(root)
    assert score(root)["passed"] is True


def test_residual_minor_no_op_fails(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "residual-minor")
    response_path(root).write_text("{}")
    assert "response-shape" in score(root)["failures"]


@pytest.mark.parametrize("execution_mode", ["delegated", "inline"])
def test_post_task_drift_score_rejects_completion_or_forward_mutation(tmp_path: Path, execution_mode: str) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode)
    write_blocked(root, complete=True)
    repo = Path(metadata(root)["repo"])
    for args in [("add", LEDGER), ("commit", "-qm", "incorrectly record completed return")]:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    assert score(root)["failures"] == ["head-advanced", "task-return-recorded"]


@pytest.mark.parametrize("execution_mode", ["delegated", "inline"])
def test_post_task_drift_requires_durable_block_then_accepts_conforming_return(tmp_path: Path, execution_mode: str) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode)
    assert score(root)["failures"] == ["drift-not-reconciled"]
    write_blocked(root)
    assert score(root)["passed"] is True


@pytest.mark.parametrize("execution_mode", ["delegated", "inline"])
def test_drift_subject_inputs_exclude_scorer_expected_action(tmp_path: Path, execution_mode: str) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode)
    inputs = json.loads((Path(metadata(root)["repo"]) / "fixture-input.json").read_text())
    assert set(inputs["facts"]) == {"stage", "task_id", "execution_modes", "frozen_plan"}
    assert "expected_next_action" not in json.dumps(inputs)
    assert f"reconcile or correct {PLAN}" not in json.dumps(inputs)
    # The test-only registry retains the oracle's expectation.
    assert json.loads((CASES / "cases.json").read_text())["post-task-plan-drift"]["expected_next_action"] == f"reconcile or correct {PLAN}"


@pytest.mark.parametrize("execution_mode", ["delegated", "inline"])
@pytest.mark.parametrize("mutation", ["delete", "state", "commit", "verification"])
def test_drift_score_rejects_task_record_changes(tmp_path: Path, execution_mode: str, mutation: str) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode)
    write_blocked(root)
    path, _, _ = parts(root)
    original = "| W-2 | awaiting_return | supplied checkpoint | npm test -- tenant.types: pass |"
    replacements = {
        "delete": "",
        "state": original.replace("awaiting_return", "blocked"),
        "commit": original.replace("supplied checkpoint", "invented-commit"),
        "verification": original.replace("tenant.types: pass", "tenant.types: skipped"),
    }
    path.write_text(path.read_text().replace(original, replacements[mutation]))
    assert score(root)["failures"] == ["task-record-changed"]


@pytest.mark.parametrize("scenario,mode", [("worker-packet", None), ("residual-minor", None), ("post-task-plan-drift", "inline")])
def test_preparation_pins_inputs_and_excludes_oracle(tmp_path: Path, scenario: str, mode: str | None) -> None:
    root = prepared_fixture(tmp_path, scenario, mode)
    meta = metadata(root)
    installed = Path(meta["installed_skill_root"])
    harness = runpy.run_path(str(SCRIPT))
    assert meta["payload_digest"] == harness["payload_digest"](installed)
    assert not any(p.name in {"remediation_pressure.py", "cases.json", "test_remediation_pressure.py"} for p in installed.rglob("*"))
    assert Path(meta["prompt"]).read_bytes() == (CASES / f"{scenario}.md").read_bytes()
    assert set(meta["protected_paths"]) == {SPEC, PLAN}
    assert score(root)["payload_digest_preserved"] is True
    assert score(root)["unexpected_status_paths"] == []
    assert meta["clean_seed_audit"] == "FF-CHECK v1 gate=audit status=pass\n"
    assert not Path(meta["response"]).is_relative_to(Path(meta["repo"]))


@pytest.mark.parametrize("mutation,expected", [("protected", "protected-paths-changed"), ("payload", "payload-changed"), ("unexpected", "unexpected-status-paths")])
def test_score_rejects_mutation_even_with_conforming_response(tmp_path: Path, mutation: str, expected: str) -> None:
    root = prepared_fixture(tmp_path, "worker-packet")
    meta = metadata(root)
    response_path(root).write_text(WORKER)
    target = {"protected": Path(meta["repo"]) / SPEC, "payload": Path(meta["installed_skill_root"]) / "SKILL.md", "unexpected": Path(meta["repo"]) / "surprise.txt"}[mutation]
    target.write_text("changed\n")
    assert expected in score(root)["failures"]


@pytest.mark.parametrize("expanded", [False, True])
def test_schema_builder_emits_only_known_checker_keys(tmp_path: Path, expanded: bool) -> None:
    root = prepared_fixture(tmp_path, "worker-packet")
    harness = runpy.run_path(str(SCRIPT))
    head_keys = OLD_HEAD | ({"mode"} if expanded else set())
    receipt_keys = NEW_RECEIPT if expanded else OLD_RECEIPT
    head, receipt = harness["build_seed"](Path(metadata(root)["repo"]), head_keys, receipt_keys)
    assert set(head) == head_keys
    assert set(receipt) == receipt_keys
    assert head["review"]["kind"] == "plan"
    assert head["review"]["state"] == receipt["result"] == "pass"
    if expanded:
        assert head["mode"] == "supervised"
        assert receipt["raw_report_ids"] == ["plan-report-empty"]
        assert receipt["triage_artifact_id"] == "plan-triage"
    with pytest.raises(ValueError, match="unsupported checker schema"):
        harness["build_seed"](Path(metadata(root)["repo"]), head_keys | {"unknown"}, receipt_keys)


def prepared_residual_schema(tmp_path: Path, head_keys: set[str]) -> Path:
    # The historical checker is not shipped. Substitute only its schema/audit
    # observations; preparation, installation, Git, and ledger writes stay real.
    # Other preparation tests exercise the actual current installed audit.
    prepare = runpy.run_path(str(SCRIPT))["prepare"]
    prepare.__globals__["runpy"] = SimpleNamespace(run_path=lambda _path: {
        "HEAD_KEYS": head_keys, "RECEIPT_KEYS": OLD_RECEIPT,
    })

    def checker_observation(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        if len(args) > 2 and str(args[1]).endswith("/scripts/ff-check") and args[2] == "audit":
            return subprocess.CompletedProcess(args, 0, "FF-CHECK v1 gate=audit status=pass\n", "")
        return subprocess.run(args, **kwargs)

    prepare.__globals__["subprocess"] = SimpleNamespace(run=checker_observation)
    root = tmp_path / "fixture"
    prepare(root, "residual-minor", "codex")
    return root


@pytest.mark.parametrize("head_keys,expected_stage", [(OLD_HEAD, 4), (OLD_HEAD | {"mode"}, 5)])
def test_residual_preparation_uses_the_owning_stage_for_each_known_schema(
    tmp_path: Path, head_keys: set[str], expected_stage: int,
) -> None:
    root = prepared_residual_schema(tmp_path, head_keys)
    _, observed, _ = parts(root)
    assert observed["stage"] == {"id": expected_stage, "state": "active"}
    assert observed["review"]["kind"] == "specification"
    assert observed["review"]["state"] == "review_active"
    assert set(observed) == head_keys


@pytest.mark.parametrize("expanded,stage,state,accepted", [
    (False, 4, "active", True),
    (False, 3, "active", False),
    (False, 4, "complete", False),
    (True, 3, "active", True),
    (True, 3, "complete", True),
    (True, 4, "active", True),
    (True, 4, "complete", True),
    (True, 5, "active", False),
    (True, 5, "complete", False),
    (True, 4, "blocked", False),
    (True, 4, "pending", False),
    (True, 4, "invalidated", False),
])
def test_residual_scorer_enforces_schema_compatible_correction_return(
    tmp_path: Path, expanded: bool, stage: int, state: str, accepted: bool,
) -> None:
    root = prepared_residual_schema(tmp_path, OLD_HEAD | ({"mode"} if expanded else set()))
    write_residual_response(root)
    response = json.loads(response_path(root).read_text())
    response["head"]["stage"] = {"id": stage, "state": state}
    response_path(root).write_text(json.dumps(response))
    observed = score(root)
    assert observed["passed"] is accepted
    assert observed["failures"] == ([] if accepted else ["resulting-head"])


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_campaign_host_process_discovers_only_fixture_skill(tmp_path: Path, host: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # Substitute only the external model executable; installer, cwd, stdin,
    # preparation, Git observations, output capture and scoring remain real.
    binary = tmp_path / host
    binary.write_text("#!/usr/bin/env python3\nimport json, pathlib, sys\nrepo = pathlib.Path.cwd()\npayload = repo / " + repr(".agents/skills/feature-forge" if host == "codex" else ".claude/skills/feature-forge") + "\nprint(json.dumps({'cwd': str(repo), 'payload': str(payload.resolve()), 'exists': (payload/'SKILL.md').is_file(), 'stdin': sys.stdin.read(), 'argv': sys.argv[1:]}))\n")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    results = command("campaign", "--phase", "baseline", "--host", host)
    assert len(results) == 4
    for item in results:
        observed = json.loads(Path(item["response"]).read_text())
        assert observed["cwd"] == item["repo"]
        assert observed["payload"] == item["installed_skill_root"]
        assert observed["exists"] is True
        assert not Path(item["repo"]).is_relative_to(SCRIPT.resolve().parents[3])
        assert observed["stdin"].encode() == Path(item["prompt"]).read_bytes()
        assert item["host_returncode"] == 0
        if host == "codex":
            assert observed["argv"] == ["exec", "--ephemeral", "--model", "gpt-5.6-terra", "--config", 'model_reasoning_effort="medium"', "--approve-for-me", "--cd", item["repo"], "-"]
        else:
            assert observed["argv"] == ["--print", "--no-session-persistence", "--model", "sonnet", "--effort", "medium", "--permission-mode", "acceptEdits", "--allowedTools", "Bash(git *) Bash(python3 *) Bash(sha256sum *)"]
