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
@pytest.mark.parametrize("mutation", ["delete", "state", "commit", "verification", "pending-state", "task-id", "insert", "reorder"])
def test_drift_score_rejects_task_record_changes(tmp_path: Path, execution_mode: str, mutation: str) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode)
    write_blocked(root)
    path, _, _ = parts(root)
    original = "| W-2 | awaiting_return | supplied checkpoint | npm test -- tenant.types: pass | |"
    replacements = {
        "delete": "",
        "state": original.replace("awaiting_return", "blocked"),
        "commit": original.replace("supplied checkpoint", "invented-commit"),
        "verification": original.replace("tenant.types: pass", "tenant.types: skipped"),
        "pending-state": path.read_text().replace("| W-3 | pending | | | |", "| W-3 | complete | | | |"),
        "task-id": original.replace("W-2", "W-4"),
        "insert": original + "\n| W-4 | pending | | | |",
        "reorder": "| W-3 | pending | | | |\n" + original,
    }
    if mutation == "pending-state":
        path.write_text(replacements[mutation])
    elif mutation == "reorder":
        path.write_text(path.read_text().replace(original + "\n| W-3 | pending | | | |", replacements[mutation]))
    else:
        path.write_text(path.read_text().replace(original, replacements[mutation]))
    assert score(root)["failures"] == ["task-record-changed"]


@pytest.mark.parametrize("execution_mode", ["delegated", "inline"])
def test_drift_score_accepts_notes_only_annotation(
    tmp_path: Path, execution_mode: str,
) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode)
    write_blocked(root)
    path, _, _ = parts(root)
    original = "| W-2 | awaiting_return | supplied checkpoint | npm test -- tenant.types: pass | |"
    annotated = original.replace(
        " | |", " | return processing held for frozen-plan drift; see Blockers |",
    )
    path.write_text(path.read_text().replace(original, annotated))
    assert score(root)["failures"] == []


def test_returned_audit_requires_the_exact_pass_protocol(tmp_path: Path) -> None:
    root = prepared_fixture(tmp_path, "worker-packet")
    meta = metadata(root)
    helper = runpy.run_path(str(SCRIPT))["returned_audit"]
    observed = helper(Path(meta["repo"]), meta)
    assert observed.returncode == 0
    assert observed.stdout == "FF-CHECK v1 gate=audit status=pass\n"
    assert observed.stderr == ""


@pytest.mark.parametrize("execution_mode", ["delegated", "inline"])
def test_drift_score_keeps_head_failures_out_of_task_record_scoring(
    tmp_path: Path, execution_mode: str,
) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", execution_mode)
    write_blocked(root)
    assert score(root)["failures"] == []


@pytest.mark.parametrize("mutation", ["separator", "late-row"])
def test_drift_score_rejects_malformed_task_table(
    tmp_path: Path, mutation: str,
) -> None:
    root = prepared_fixture(tmp_path, "post-task-plan-drift", "inline")
    write_blocked(root)
    path, _, _ = parts(root)
    text = path.read_text()
    if mutation == "separator":
        text = text.replace(
            "| --- | --- | --- | --- | --- |",
            "| --- | invalid | --- | --- | --- |",
        )
    else:
        text = text.replace(
            "\n## Transition log",
            "\nIgnored prose\n| W-3 | awaiting_return (see Blockers) | | | |\n\n## Transition log",
        )
    path.write_text(text)
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


@pytest.mark.parametrize("host,phase", [("codex", "baseline"), ("claude", "baseline"), ("codex", "green")])
def test_campaign_host_process_discovers_only_fixture_skill(tmp_path: Path, host: str, phase: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # Substitute only the external model executable; installer, cwd, stdin,
    # preparation, Git observations, output capture and scoring remain real.
    binary = tmp_path / host
    binary.write_text("#!/usr/bin/env python3\nimport json, pathlib, sys\nrepo = pathlib.Path.cwd()\npayload = repo / " + repr(".agents/skills/feature-forge" if host == "codex" else ".claude/skills/feature-forge") + "\nprint(json.dumps({'cwd': str(repo), 'payload': str(payload.resolve()), 'exists': (payload/'SKILL.md').is_file(), 'stdin': sys.stdin.read(), 'argv': sys.argv[1:]}))\n")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    results = command("campaign", "--phase", phase, "--host", host)
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


WORKER_FIELDS = ["task", "ownership", "interfaces", "dependencies", "verification", "authority", "return"]


def structured_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str = "") -> list[dict]:
    """Replace only the model executable; exercise real campaign/capture/scoring."""
    binary = tmp_path / "claude"
    binary.write_text('''#!/usr/bin/env python3
import json, pathlib, sys
repo = pathlib.Path.cwd()
scenario = json.loads((repo / "fixture-input.json").read_text())["scenario"]
fields = ["task", "ownership", "interfaces", "dependencies", "verification", "authority", "return"]
value = ({k: "model supplied " + k for k in fields} if scenario == "worker-packet" else
         {"receipt": {}, "head": {}} if scenario == "residual-minor" else {"summary": "model supplied summary"})
envelope = {"type": "result", "subtype": "success", "is_error": False,
            "result": "Conversational prose must not reach the scorer.", "structured_output": value,
            "observed": {"argv": sys.argv[1:], "stdin": sys.stdin.read(), "cwd": str(repo)}}
mutation = ''' + repr(mutation) + '''
if mutation == "missing": envelope.pop("structured_output")
if mutation == "null": envelope["structured_output"] = None
if mutation == "extra": value["surprise"] = "not permitted"
if mutation == "type": value[next(iter(value))] = 42
if mutation == "field": value.pop(next(iter(value)))
if mutation == "error": envelope["is_error"] = True
if mutation == "subtype": envelope["subtype"] = "error_max_turns"
if mutation == "status": envelope.pop("type")
if mutation == "nan": envelope["usage"] = float("nan")
blob = json.dumps(envelope, indent=2)
if mutation == "duplicate": blob = blob[:-1] + ',"structured_output":' + json.dumps(value) + '}'
print("not json" if mutation == "json" else blob)
sys.exit(9 if mutation == "exit" else 0)
''')
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    return command("campaign", "--phase", "green", "--host", "claude")


def test_claude_green_exact_structured_argv_schema_and_materialization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = structured_claude(tmp_path, monkeypatch)
    assert len(rows) == 4
    for row in rows:
        # This assertion is reached against the uncorrected plain-text adapter.
        assert "raw_response" in row
        raw = Path(row["raw_response"])
        assert not raw.is_relative_to(Path(row["repo"]))
        envelope = json.loads(raw.read_text())
        assert raw.read_text() == json.dumps(envelope, indent=2) + "\n"
        observed = envelope["observed"]
        assert observed["cwd"] == row["repo"]
        assert observed["stdin"].encode() == Path(row["prompt"]).read_bytes()
        argv = observed["argv"]
        assert argv[:-1] == ["--print", "--no-session-persistence", "--model", "sonnet", "--effort", "medium", "--permission-mode", "acceptEdits", "--allowedTools", "Bash(git *) Bash(python3 *) Bash(sha256sum *)", "--output-format", "json", "--json-schema"]
        schema = json.loads(argv[-1])
        fields = WORKER_FIELDS if row["scenario"] == "worker-packet" else ["receipt", "head"] if row["scenario"] == "residual-minor" else ["summary"]
        kind = "object" if row["scenario"] == "residual-minor" else "string"
        assert set(schema) == {"type", "properties", "required", "additionalProperties"}
        assert schema["type"] == "object"
        assert schema["required"] == fields
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == set(fields)
        for key in fields:
            prop = schema["properties"][key]
            assert prop["type"] == kind
            if row["scenario"] == "worker-packet":
                assert set(prop) == {"type", "description"}
                assert isinstance(prop["description"], str) and prop["description"].strip()
            else:
                assert prop == {"type": kind}
        assert not any(word in argv[-1] for word in ["W-4", "REQ-", "TRIAGE", "blocked", "pass", "reconcile", PLAN])
        value = envelope["structured_output"]
        expected = ("\n".join(f"{key.capitalize()}: {value[key]}" for key in fields) + "\n" if row["scenario"] == "worker-packet" else
                    json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n" if row["scenario"] == "residual-minor" else value["summary"] + "\n")
        assert Path(row["response"]).read_text() == expected
        assert row["structured_output_error"] is None
        assert row["unavailable"] is None
        # Shape success must not manufacture a content pass.
        assert row["verdict"]["passed"] is False
        assert "structured-output" not in " ".join(row["verdict"]["failures"])


@pytest.mark.parametrize("mutation", ["missing", "null", "extra", "type", "field", "error", "subtype", "status", "json", "exit", "nan", "duplicate"])
def test_claude_green_malformed_structured_return_is_executed_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    for row in structured_claude(tmp_path, monkeypatch, mutation):
        assert row.get("structured_output_error"), mutation
        assert row["unavailable"] is None
        assert row["host_returncode"] == (9 if mutation == "exit" else 0)
        assert Path(row["raw_response"]).read_bytes()
        assert Path(row["response"]).read_bytes() == b""
        assert row["verdict"]["passed"] is False
        assert row["structured_output_error"] in row["verdict"]["failures"]


@pytest.mark.parametrize("host,phase", [("claude", "green"), ("claude", "baseline"), ("codex", "green"), ("codex", "baseline")])
@pytest.mark.parametrize("fault", ["timeout", "launch"])
def test_campaign_classifies_executed_timeout_separately_from_launch_failure(tmp_path: Path, host: str, phase: str, fault: str) -> None:
    campaign = runpy.run_path(str(SCRIPT))["campaign"]
    partial = b'{"partial":'

    def bounded_host(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        if args[0] == host:
            assert kwargs["timeout"] == 600
            if fault == "launch":
                return subprocess.run([str(tmp_path / "missing-host")], **kwargs)
            # Execute a real child and let subprocess enforce its timeout after
            # flushed partial output. Only the external model and wait change.
            kwargs["timeout"] = 0.25
            return subprocess.run([sys.executable, "-c",
                                   "import sys,time; sys.stdout.buffer.write(" + repr(partial) + "); sys.stdout.flush(); time.sleep(5)"], **kwargs)
        return subprocess.run(args, **kwargs)

    campaign.__globals__["subprocess"] = SimpleNamespace(run=bounded_host, TimeoutExpired=subprocess.TimeoutExpired)
    for row in campaign(phase, host):
        structured = host == "claude" and phase == "green"
        raw = Path(row["raw_response"] if structured else row["response"])
        assert raw.read_bytes() == (partial if fault == "timeout" else b"")
        assert row["host_returncode"] is None
        assert Path(row["stderr"]).read_bytes()
        if structured and fault == "timeout":
            assert row["unavailable"] is None
            assert row["structured_output_error"] == "structured-output=timeout"
            assert "structured-output=timeout" in row["verdict"]["failures"]
            assert row["verdict"]["passed"] is False
            assert Path(row["response"]).read_bytes() == b""
        else:
            assert row["unavailable"]
            if not structured:
                assert "structured_output_error" not in row
