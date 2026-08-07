import os
import shutil
import subprocess
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "tests" / "manual" / "headless-driver-smoke.sh"


def test_headless_driver_smoke_harness_has_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", str(HARNESS)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr


def test_headless_driver_smoke_harness_self_check_validates_fixtures():
    result = subprocess.run(
        ["bash", str(HARNESS), "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "shutdown_prompt_paths=PASS" in result.stdout
    assert "shutdown_process_patterns=PASS" in result.stdout
    assert "codex_process_pattern=node .*codex" in result.stdout
    assert result.stdout.strip().endswith("headless_driver_smoke_check=PASS")


def test_headless_driver_smoke_self_check_does_not_use_ambient_python3(tmp_path):
    blocked_python = tmp_path / "python3"
    blocked_python.write_text("#!/bin/sh\nexit 97\n")
    blocked_python.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}

    result = subprocess.run(
        ["bash", str(HARNESS), "--check"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("headless_driver_smoke_check=PASS")


def test_self_check_honors_uv_bin_without_ambient_uv():
    uv = shutil.which("uv")
    assert uv is not None
    env = {**os.environ, "PATH": "/usr/bin:/bin", "UV_BIN": uv}

    result = subprocess.run(
        ["/bin/bash", str(HARNESS), "--check"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("headless_driver_smoke_check=PASS")


def test_prereq_check_honors_all_cli_overrides_without_ambient_commands(tmp_path):
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir()
    for command in (
        "awk", "bwrap", "cp", "dirname", "find", "getent", "git", "id", "ps", "readlink",
        "rg", "setsid", "sleep", "stat",
    ):
        target = shutil.which(command)
        assert target is not None
        (tool_dir / command).symlink_to(target)
    fake_cli = tmp_path / "fake-cli"
    fake_cli.write_text("#!/bin/sh\nexit 0\n")
    fake_cli.chmod(0o755)
    codex_entry = tmp_path / "codex" / "bin" / "codex.js"
    opencode_entry = tmp_path / "opencode" / "bin" / "opencode"
    pykrete_entry = tmp_path / "pykrete" / "bin" / "pykrete.ts"
    pi_entry = tmp_path / "pi" / "dist" / "cli.js"
    for entry in (codex_entry, opencode_entry, pykrete_entry, pi_entry):
        entry.parent.mkdir(parents=True)
        entry.write_text("#!/bin/sh\nexit 0\n")
        entry.chmod(0o755)
    for directory in (
        tmp_path / "codex" / "node_modules",
        tmp_path / "opencode" / "node_modules",
        tmp_path / "pykrete" / "src",
        tmp_path / "pykrete" / "node_modules",
        tmp_path / "pi" / "node_modules",
        tmp_path / "uv-cache",
    ):
        directory.mkdir()
    claude_token = tmp_path / "claude.token"
    pykrete_env = tmp_path / "pykrete.env"
    pykrete_config = tmp_path / "pykrete.toml"
    claude_token.write_text("test-token\n")
    pykrete_env.write_text("NANOGPT_API_KEY=test-key\n")
    pykrete_config.write_text("[models]\n")
    claude_token.chmod(0o600)
    pykrete_env.chmod(0o600)
    env = {
        **os.environ,
        "PATH": str(tool_dir),
        "UV_BIN": str(fake_cli),
        "CLAUDE_BIN": str(fake_cli),
        "AGY_BIN": str(fake_cli),
        "CODEX_ENTRY": str(codex_entry),
        "OPENCODE_ENTRY": str(opencode_entry),
        "PYKRETE_ENTRY": str(pykrete_entry),
        "PI_ENTRY": str(pi_entry),
        "GROK_BIN": str(fake_cli),
        "CLAUDE_TOKEN_FILE": str(claude_token),
        "PYKRETE_ENV_FILE": str(pykrete_env),
        "PYKRETE_CONFIG_FILE": str(pykrete_config),
        "UV_CACHE_SOURCE": str(tmp_path / "uv-cache"),
        "AGY_TOKEN_FILE": str(claude_token),
        "CODEX_AUTH_FILE": str(claude_token),
        "OPENCODE_AUTH_FILE": str(claude_token),
        "GROK_AUTH_FILE": str(claude_token),
    }

    result = subprocess.run(
        ["/bin/bash", str(HARNESS), "--prereq-check"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("headless_driver_smoke_prereq=PASS")
    assert "required command not found" not in result.stderr


def test_exit_trap_kills_fake_child_and_grandchild_without_network(tmp_path):
    snapshot = tmp_path / "cleanup.snapshot"

    result = subprocess.run(
        ["/bin/bash", str(HARNESS), "--cleanup-check", str(snapshot)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "intentional cleanup-check failure" in result.stderr
    pids = [int(line.split()[0]) for line in snapshot.read_text().splitlines()]
    assert len(pids) >= 2

    deadline = time.monotonic() + 3
    survivors = pids
    while survivors and time.monotonic() < deadline:
        survivors = [pid for pid in survivors if Path(f"/proc/{pid}").exists()]
        if survivors:
            time.sleep(0.05)
    if survivors:
        for pid in survivors:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
    assert survivors == []
