#!/usr/bin/env python3
"""Run one work-team scenario and capture its transcript artefacts.

usage: run-eval.sh <red|green|refactor> <A|B|C> <claude|codex> [attempt-N]
"""

import hashlib
import json
import os
import re
import secrets
import signal
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
PAYLOAD_ENTRIES = ("SKILL.md", "references", "scripts", "agents")


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scenario_body(source, scenario, fixture, fault_injector):
    selected = []
    active = False
    for line in source.read_text().splitlines():
        if line.startswith(f"## Scenario {scenario}"):
            active = True
            continue
        if active and line.startswith("## "):
            break
        if active and not line.startswith(("Fixture:", "Fresh empty directory")):
            selected.append(
                line.replace("<FIXTURE>", str(fixture)).replace(
                    "<FAULT_INJECTOR>", str(fault_injector)
                )
            )
    return "\n".join(selected).strip()


def harness_command(harness, workspace, prompt):
    if harness == "claude":
        display = (
            "claude --model sonnet --effort high "
            "--output-format stream-json --verbose "
            "--setting-sources project "
            "--allowedTools Agent,Read,Write,Edit,Bash,Glob,Grep -p <prompt>"
        )
        command = [
            "claude",
            "--setting-sources",
            "project",
            "--model",
            "sonnet",
            "--effort",
            "high",
            "--output-format",
            "stream-json",
            "--verbose",
            "--allowedTools",
            "Agent,Read,Write,Edit,Bash,Glob,Grep",
            "-p",
            prompt,
        ]
    else:
        display = (
            "codex exec --ignore-user-config --json --enable multi_agent "
            "--skip-git-repo-check "
            f"-C {workspace} -m gpt-5.6-terra "
            '-c model_reasoning_effort="high" -s workspace-write '
            "<prompt-argument>"
        )
        command = [
            "codex",
            "exec",
            "--ignore-user-config",
            "--json",
            "--enable",
            "multi_agent",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "-m",
            "gpt-5.6-terra",
            "-c",
            'model_reasoning_effort="high"',
            "-s",
            "workspace-write",
            prompt,
        ]
    return display, command


def require_safe_component(label, value):
    if not SAFE_COMPONENT.fullmatch(value):
        sys.exit(f"unsafe {label}: {value!r}")


def require_contained(root, candidate, label):
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    if not resolved_candidate.is_relative_to(resolved_root):
        sys.exit(f"{label} escapes {resolved_root}")


def require_manifest_path(relative):
    if any(ord(character) < 32 or ord(character) == 127 for character in relative):
        sys.exit(f"control character in archived path: {relative!r}")


def tree_hash_rows(root, excluded=()):
    rows = []
    for candidate in sorted(root.rglob("*")):
        relative = candidate.relative_to(root).as_posix()
        require_manifest_path(relative)
        if relative in excluded:
            continue
        if candidate.is_symlink():
            payload = b"symlink\0" + os.readlink(candidate).encode("utf-8")
        elif candidate.is_file():
            payload = candidate.read_bytes()
        else:
            continue
        rows.append(f"{hashlib.sha256(payload).hexdigest()}  {relative}")
    return rows


def write_tree_hashes(root, destination):
    rows = tree_hash_rows(root)
    destination.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def stage_filtered_skill(component, workspace, output):
    marker = f"<!-- eval-marker:{secrets.token_hex(16)} -->"
    for discovery in (".agents", ".claude"):
        destination = workspace / discovery / "skills" / "work-team"
        destination.mkdir(parents=True)
        for name in PAYLOAD_ENTRIES:
            source = component / name
            target = destination / name
            if source.is_dir():
                shutil.copytree(
                    source,
                    target,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
            elif source.is_file():
                shutil.copy2(source, target)
        with (destination / "SKILL.md").open("a", encoding="utf-8") as skill_file:
            skill_file.write(f"\n{marker}\n")
        label = discovery.removeprefix(".")
        write_tree_hashes(destination, output / f"skill-payload-{label}.sha256")
    return marker


def reject_symlinks(root, label):
    if root.is_symlink():
        sys.exit(f"refusing symlinked {label}: {root}")
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            sys.exit(f"refusing symlink in {label}: {candidate}")
        if candidate.is_file() and candidate.stat().st_nlink != 1:
            sys.exit(f"refusing hardlink in {label}: {candidate}")


def copy_run_artefacts(workspace, output):
    run_dir = workspace / ".work-team"
    if run_dir.is_symlink():
        sys.exit(f"refusing symlinked run directory: {run_dir}")
    if run_dir.is_dir():
        reject_symlinks(run_dir, "run directory")
        shutil.copytree(run_dir, output / "run-artefacts")
    for log in workspace.rglob("workflow-log.jsonl"):
        relative = log.relative_to(workspace)
        if ".work-team" in relative.parts:
            continue
        if log.is_symlink():
            sys.exit(f"refusing symlinked audit log: {log}")
        if log.stat().st_nlink != 1:
            sys.exit(f"refusing hardlinked audit log: {log}")
        require_contained(workspace, log, "audit log")
        require_manifest_path(relative.as_posix())
        destination = output / "audit-logs" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(log, destination)
    files = []
    for candidate in workspace.rglob("*"):
        relative = candidate.relative_to(workspace)
        require_manifest_path(relative.as_posix())
        if "node_modules" in relative.parts or ".venv" in relative.parts:
            continue
        if candidate.is_file() and not candidate.is_symlink():
            files.append(f"./{relative.as_posix()}")
    listing = "\n".join(sorted(files))
    (output / "workspace-files.txt").write_text(
        listing + ("\n" if listing else ""), encoding="utf-8"
    )


def write_checksums(output):
    reject_symlinks(output, "evaluation archive")
    rows = tree_hash_rows(output, excluded={"attempt.sha256"})
    (output / "attempt.sha256").write_text(
        "\n".join(rows) + "\n", encoding="utf-8"
    )


def run_harness(command, workspace, stdout, stderr, timeout_seconds):
    try:
        process = subprocess.Popen(
            command,
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            text=True,
            start_new_session=True,
        )
    except OSError as error:
        print(error, file=stderr)
        return 127
    try:
        exit_code = process.wait(timeout=timeout_seconds)
        for stop_signal in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, stop_signal)
            except ProcessLookupError:
                break
        return exit_code
    except subprocess.TimeoutExpired:
        print(f"evaluation timed out after {timeout_seconds}s", file=stderr)
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        return 124


def verify_staged_skill(harness, transcript, workspace, marker):
    discovery = ".claude" if harness == "claude" else ".agents"
    skill_dir = workspace / discovery / "skills" / "work-team"
    expected = skill_dir / "SKILL.md"
    events = []
    try:
        for line in transcript.read_text(encoding="utf-8").splitlines():
            events.append(json.loads(line))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if harness == "codex":
        targets = {str(expected), expected.relative_to(workspace).as_posix()}

        def tokens_read_expected_skill(tokens):
            if not tokens:
                return False
            return (
                Path(tokens[0]).name in {"cat", "head", "sed", "tail"}
                and any(token in targets for token in tokens[1:])
            )

        def staged_skill_read(command):
            try:
                tokens = shlex.split(command)
            except ValueError:
                return False, False
            if not tokens:
                return False, False
            command_name = Path(tokens[0]).name
            if (
                command_name in {"bash", "sh"}
                and len(tokens) == 3
                and tokens[1] == "-lc"
            ):
                try:
                    shell_tokens = shlex.split(tokens[2])
                except ValueError:
                    return False, False
                if "&&" in shell_tokens:
                    first_segment = shell_tokens[:shell_tokens.index("&&")]
                    return tokens_read_expected_skill(first_segment), True
                return tokens_read_expected_skill(shell_tokens), False
            return tokens_read_expected_skill(tokens), False

        def event_proves_staged_skill_read(event):
            item = event["item"]
            read_proven, read_precedes_chain = staged_skill_read(
                item.get("command", "")
            )
            return (
                read_proven
                and (item.get("exit_code") == 0 or read_precedes_chain)
                and marker in item.get("aggregated_output", "")
            )

        return any(
            event.get("type") == "item.completed"
            and isinstance(event.get("item"), dict)
            and event["item"].get("type") == "command_execution"
            and event_proves_staged_skill_read(event)
            for event in events
            if isinstance(event, dict)
        )
    def is_skill_invocation(event):
        if event.get("type") != "assistant":
            return False
        message = event.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            return False
        for block in message["content"]:
            if not isinstance(block, dict) or not isinstance(block.get("input"), dict):
                continue
            if (
                block.get("type") == "tool_use"
                and block.get("name") == "Skill"
                and block["input"].get("skill") == "work-team"
            ):
                return True
        return False

    invoked = any(
        is_skill_invocation(event) for event in events if isinstance(event, dict)
    )
    loaded = any(
        event.get("type") == "user"
        and event.get("isSynthetic") is True
        and f"Base directory for this skill: {skill_dir}" in json.dumps(
            event, ensure_ascii=False
        )
        and marker in json.dumps(event, ensure_ascii=False)
        for event in events
        if isinstance(event, dict)
    )
    return invoked and loaded


def record_post_skill_hashes(workspace, output):
    unchanged = True
    for discovery in (".agents", ".claude"):
        label = discovery.removeprefix(".")
        destination = workspace / discovery / "skills" / "work-team"
        after_path = output / f"skill-payload-{label}-after.sha256"
        write_tree_hashes(destination, after_path)
        before = (output / f"skill-payload-{label}.sha256").read_bytes()
        if after_path.read_bytes() != before:
            unchanged = False
    return unchanged


def validate_run_artefacts(workspace):
    run_root = workspace / ".work-team"
    results = sorted(run_root.glob("*/result.json")) if run_root.is_dir() else []
    if len(results) != 1 or results[0].is_symlink():
        return False, "expected exactly one regular .work-team/<run>/result.json"
    result_file = results[0]
    skill_root = workspace / ".agents" / "skills" / "work-team"
    validator = skill_root / "scripts" / "wt-validate"
    schemas = skill_root / "references" / "schemas"
    result_check = subprocess.run(
        [sys.executable, str(validator), str(schemas / "result.schema.json"), str(result_file)],
        cwd=workspace,
        text=True,
        capture_output=True,
    )
    if result_check.returncode:
        return False, result_check.stderr.strip() or "result.json is invalid"
    try:
        result = json.loads(result_file.read_text(encoding="utf-8"))
        plan_file = workspace / result["plan"]
    except (OSError, KeyError, json.JSONDecodeError) as error:
        return False, f"cannot read declared plan: {error}"
    if plan_file.is_symlink() or not plan_file.is_file():
        return False, "declared plan does not exist as a regular file"
    plan_check = subprocess.run(
        [sys.executable, str(validator), str(schemas / "plan.schema.json"), str(plan_file)],
        cwd=workspace,
        text=True,
        capture_output=True,
    )
    if plan_check.returncode:
        return False, plan_check.stderr.strip() or "plan.json is invalid"
    return True, ""


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    phase, scenario, harness = sys.argv[1:4]
    attempt = sys.argv[4] if len(sys.argv) == 5 else "attempt-1"
    if phase not in {"red", "green", "refactor"}:
        sys.exit(f"unknown phase: {phase}")
    if scenario not in {"A", "B", "C"}:
        sys.exit(f"unknown scenario: {scenario}")
    if harness not in {"claude", "codex"}:
        sys.exit(f"unknown harness: {harness}")

    here = Path(__file__).resolve().parent
    timestamp = os.environ.get("EVAL_TS") or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    require_safe_component("timestamp", timestamp)
    require_safe_component("attempt", attempt)
    timeout_raw = os.environ.get("EVAL_TIMEOUT_SECONDS", "180")
    try:
        timeout_seconds = int(timeout_raw)
    except ValueError:
        sys.exit("EVAL_TIMEOUT_SECONDS must be a positive integer")
    if timeout_seconds < 1:
        sys.exit("EVAL_TIMEOUT_SECONDS must be a positive integer")
    suffix = f"{phase}-{timestamp}-{scenario}-{harness}-{attempt}"
    output = (
        here
        / "transcripts"
        / phase
        / timestamp
        / f"Scenario-{scenario}-{harness}"
        / attempt
    )
    workspace_base = Path(
        os.environ.get("EVAL_WS")
        or Path(os.environ.get("CLAUDE_JOB_DIR", "/tmp")) / "tmp/evals"
    ).resolve()
    workspace = workspace_base / suffix
    require_contained(here / "transcripts", output, "evaluation output")
    require_contained(workspace_base, workspace, "evaluation workspace")
    if output.exists() or workspace.exists():
        sys.exit("refusing colliding evaluation: output or workspace already exists")
    output.mkdir(parents=True)
    workspace.mkdir(parents=True)

    fixture = ""
    fault_injector = ""
    if scenario == "B":
        fixture = workspace / "audit-target"
        shutil.copytree(here / "fixtures/audit-target", fixture)
        fault_injector = workspace / ".eval-tools" / "inject-partial-verifier.py"
        fault_injector.parent.mkdir()
        shutil.copy2(here / "inject-partial-verifier.py", fault_injector)
    elif scenario == "C":
        fixture = workspace / "run-dir"
        shutil.copytree(here / "fixtures/run-dir", fixture)
    fixture_protected_before = None
    if fixture:
        write_tree_hashes(fixture, output / "fixture-before.sha256")
        excluded = ("workflow-log.jsonl",) if scenario == "B" else ()
        fixture_protected_before = tree_hash_rows(fixture, excluded=excluded)

    skill_marker = stage_filtered_skill(here.parent, workspace, output)

    body = scenario_body(
        here / "scenarios.md", scenario, fixture, fault_injector
    )
    prefix = ""
    if phase != "red":
        prefix = (
            "Use the work-team skill for the task below. Before dispatching, "
            "state the skill name and the resolved SKILL.md path you loaded.\n\n"
        )
    prompt = prefix + body
    (output / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")

    display, command = harness_command(harness, workspace, prompt)
    started = utc_now()
    with (output / "stdout.jsonl").open("w") as stdout, (
        output / "stderr.txt"
    ).open("w") as stderr:
        exit_code = run_harness(
            command, workspace, stdout, stderr, timeout_seconds
        )

    codex_evidence_status = 1
    extraction_command = [
        sys.executable,
        str(here / "extract-response.py"),
        harness,
        str(output / "stdout.jsonl"),
    ]
    if harness == "codex":
        codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
        evidence_path = output / "codex-collaboration.json"
        evidence_command = [
            sys.executable,
            str(here / "extract-codex-collaboration.py"),
            str(output / "stdout.jsonl"),
            str(codex_home / "sessions"),
            str(workspace),
            str(evidence_path),
        ]
        if scenario == "C":
            evidence_command.append("--allow-no-dispatch")
        evidence_check = subprocess.run(
            evidence_command,
            text=True,
            capture_output=True,
        )
        codex_evidence_status = evidence_check.returncode
        if codex_evidence_status == 0:
            extraction_command.append(str(evidence_path))
        elif codex_evidence_status not in (1, 2):
            print(
                evidence_check.stderr.strip()
                or "invalid Codex collaboration evidence",
                file=sys.stderr,
            )
    if scenario == "C":
        extraction_command.append("--allow-no-dispatch")
    with (output / "final-response.md").open("w") as final_response:
        extracted = subprocess.run(
            extraction_command,
            stdout=final_response,
        ).returncode
    if (
        exit_code == 0
        and harness == "codex"
        and codex_evidence_status not in (0, 1)
    ):
        extracted = codex_evidence_status
    if exit_code == 0 and extracted:
        messages = {
            1: "evaluation produced no final agent response",
            2: "evaluation produced no worker dispatch",
        }
        print(
            messages.get(extracted, "evaluation produced an invalid harness transcript"),
            file=sys.stderr,
        )
        exit_code = extracted
    skill_unchanged = record_post_skill_hashes(workspace, output)
    if phase != "red" and exit_code == 0 and not skill_unchanged:
        print("staged skill changed during evaluation", file=sys.stderr)
        exit_code = 5
    if (
        phase != "red"
        and exit_code == 0
        and extracted == 0
        and not verify_staged_skill(
            harness, output / "stdout.jsonl", workspace, skill_marker
        )
    ):
        print("evaluation did not prove use of the staged skill", file=sys.stderr)
        exit_code = 4

    if phase != "red" and scenario in {"A", "B"} and exit_code == 0:
        valid_artefacts, detail = validate_run_artefacts(workspace)
        if not valid_artefacts:
            print(f"evaluation run artifacts failed validation: {detail}", file=sys.stderr)
            exit_code = 6

    ended = utc_now()
    copy_run_artefacts(workspace, output)
    if fixture:
        write_tree_hashes(fixture, output / "fixture-after.sha256")
        excluded = ("workflow-log.jsonl",) if scenario == "B" else ()
        if tree_hash_rows(fixture, excluded=excluded) != fixture_protected_before:
            print("evaluation modified protected fixture files", file=sys.stderr)
            if exit_code == 0:
                exit_code = 7
    metadata = (
        f"command={display}\n"
        f"workspace={workspace}\n"
        f"harness={harness}\n"
        f"phase={phase}\n"
        f"scenario={scenario}\n"
        f"start={started}\n"
        f"end={ended}\n"
        f"exit={exit_code}\n"
    )
    (output / "metadata.txt").write_text(metadata, encoding="utf-8")
    write_checksums(output)
    print(f"{output} exit={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
