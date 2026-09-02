#!/usr/bin/env python3
"""Run one work-team scenario and capture its transcript artefacts.

usage: run-eval.sh <red|green|refactor> <A|B|C> <claude|codex> [attempt-N]
"""

import hashlib
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scenario_body(source, scenario, fixture):
    selected = []
    active = False
    for line in source.read_text().splitlines():
        if line.startswith(f"## Scenario {scenario}"):
            active = True
            continue
        if active and line.startswith("## "):
            break
        if active and not line.startswith(("Fixture:", "Fresh empty directory")):
            selected.append(line.replace("<FIXTURE>", str(fixture)))
    return "\n".join(selected).strip()


def harness_command(harness, workspace, prompt):
    if harness == "claude":
        display = (
            "claude --model sonnet --output-format stream-json --verbose "
            "--allowedTools Agent,Read,Write,Edit,Bash,Glob,Grep -p <prompt>"
        )
        command = [
            "claude",
            "--model",
            "sonnet",
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
            "codex exec --json --enable multi_agent --skip-git-repo-check "
            f"-C {workspace} -m gpt-5.6-terra "
            '-c model_reasoning_effort="medium" -s workspace-write - </dev/null'
        )
        command = [
            "codex",
            "exec",
            "--json",
            "--enable",
            "multi_agent",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "-m",
            "gpt-5.6-terra",
            "-c",
            'model_reasoning_effort="medium"',
            "-s",
            "workspace-write",
            prompt,
        ]
    return display, command


def copy_run_artefacts(workspace, output):
    run_dir = workspace / ".work-team"
    if run_dir.is_dir():
        shutil.copytree(run_dir, output / "run-artefacts", symlinks=True)
    for log in workspace.rglob("workflow-log.jsonl"):
        relative = log.relative_to(workspace)
        if ".work-team" in relative.parts:
            continue
        shutil.copy2(log, output / "_".join(relative.parts))
    files = []
    for candidate in workspace.rglob("*"):
        relative = candidate.relative_to(workspace)
        if "node_modules" in relative.parts or ".venv" in relative.parts:
            continue
        if candidate.is_file() and not candidate.is_symlink():
            files.append(f"./{relative.as_posix()}")
    listing = "\n".join(sorted(files))
    (output / "workspace-files.txt").write_text(
        listing + ("\n" if listing else "")
    )


def write_checksums(output):
    names = ["prompt.txt", "stdout.jsonl", "metadata.txt"]
    rows = []
    for name in names:
        digest = hashlib.sha256((output / name).read_bytes()).hexdigest()
        rows.append(f"{digest}  {name}")
    (output / "attempt.sha256").write_text("\n".join(rows) + "\n")


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
    )
    workspace = workspace_base / suffix
    if output.exists() or workspace.exists():
        sys.exit("refusing colliding evaluation: output or workspace already exists")
    output.mkdir(parents=True)
    workspace.mkdir(parents=True)

    fixture = ""
    if scenario == "B":
        fixture = workspace / "audit-target"
        shutil.copytree(here / "fixtures/audit-target", fixture)
    elif scenario == "C":
        fixture = workspace / "run-dir"
        shutil.copytree(here / "fixtures/run-dir", fixture)

    body = scenario_body(here / "scenarios.md", scenario, fixture)
    prefix = ""
    if phase != "red":
        prefix = (
            "Use the work-team skill for the task below. Before dispatching, "
            "state the skill name and the resolved SKILL.md path you loaded.\n\n"
        )
    prompt = prefix + body
    (output / "prompt.txt").write_text(prompt + "\n")

    display, command = harness_command(harness, workspace, prompt)
    started = utc_now()
    with (output / "stdout.jsonl").open("w") as stdout, (
        output / "stderr.txt"
    ).open("w") as stderr:
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                text=True,
            )
            exit_code = completed.returncode
        except OSError as error:
            print(error, file=stderr)
            exit_code = 127

    with (output / "final-response.md").open("w") as final_response:
        extracted = subprocess.run(
            [
                sys.executable,
                str(here / "extract-response.py"),
                harness,
                str(output / "stdout.jsonl"),
            ],
            stdout=final_response,
        ).returncode
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

    ended = utc_now()
    copy_run_artefacts(workspace, output)
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
    (output / "metadata.txt").write_text(metadata)
    write_checksums(output)
    print(f"{output} exit={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
