import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "tests" / "manual" / "headless-driver-smoke.sh"


@contextmanager
def fake_process_tree(script: str):
    process = subprocess.Popen(
        ["setsid", "/bin/bash", "-c", script],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield process
    finally:
        try:
            os.killpg(process.pid, 9)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)


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


def test_prereq_check_reports_precise_blockers_for_every_cli_before_live_work(tmp_path):
    """Break caught: early die hid binary, containment, auth, and config blockers."""
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir()
    for command in (
        "awk", "cp", "dirname", "find", "getent", "git", "id", "ps", "readlink",
        "rg", "setsid", "sleep", "sort", "stat", "wc",
    ):
        target = shutil.which(command)
        assert target is not None
        (tool_dir / command).symlink_to(target)
    missing = tmp_path / "missing"
    env = {
        **os.environ,
        "PATH": str(tool_dir),
        "UV_BIN": str(missing / "uv"),
        "CLAUDE_BIN": str(missing / "claude"),
        "AGY_BIN": str(missing / "agy"),
        "CODEX_ENTRY": str(missing / "codex.js"),
        "OPENCODE_ENTRY": str(missing / "opencode"),
        "PYKRETE_ENTRY": str(missing / "pykrete.ts"),
        "PI_ENTRY": str(missing / "pi.js"),
        "GROK_BIN": str(missing / "grok"),
        "CLAUDE_TOKEN_FILE": str(missing / "claude.token"),
        "PYKRETE_ENV_FILE": str(missing / "pykrete.env"),
        "PYKRETE_CONFIG_FILE": str(missing / "pykrete.toml"),
        "UV_CACHE_SOURCE": str(missing / "uv-cache"),
        "AGY_TOKEN_FILE": str(missing / "agy.auth"),
        "CODEX_AUTH_FILE": str(missing / "codex.auth"),
        "OPENCODE_AUTH_FILE": str(missing / "opencode.auth"),
        "GROK_AUTH_FILE": str(missing / "grok.auth"),
    }

    result = subprocess.run(
        ["/bin/bash", str(HARNESS), "--prereq-check"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    for cli in ("claude", "agy", "codex", "opencode", "pykrete", "grok"):
        assert f"shutdown_{cli}=BLOCKED scopes=plain,bwrap" in result.stdout
    assert "missing_containment=bwrap" in result.stdout
    assert "shutdown_claude=BLOCKED" in result.stdout and "missing_auth=" in result.stdout
    assert "shutdown_pykrete=BLOCKED" in result.stdout and "missing_config=" in result.stdout
    assert "shutdown matrix has BLOCKED prerequisites" in result.stderr


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


def test_process_pattern_check_rejects_one_pid_matching_both_patterns(tmp_path):
    """Break caught: one Codex snapshot row previously satisfied both regexes."""
    snapshot = tmp_path / "same-pid.snapshot"
    with fake_process_tree(
        "/bin/bash -c \"exec -a 'node /tmp/codex exec --skip-git-repo-check' "
        "/bin/sleep 30\" & wait"
    ) as process:
        result = subprocess.run(
            [
                "/bin/bash", str(HARNESS), "--pattern-check", str(process.pid),
                str(snapshot), "node .*codex", "codex.*exec",
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "PATTERN_WAIT_ATTEMPTS": "5"},
            text=True,
            capture_output=True,
            timeout=5,
        )

    assert result.returncode == 1
    assert "distinct PIDs" in result.stderr
    assert "process_patterns=PASS" not in result.stdout


def test_process_pattern_check_accepts_distinct_launcher_and_engine_pids(tmp_path):
    """Break caught: distinct launcher/engine evidence must remain observable."""
    snapshot = tmp_path / "distinct-pids.snapshot"
    with fake_process_tree(
        "/bin/bash -c \"exec -a 'node /tmp/codex' /bin/sleep 30\" & "
        "/bin/bash -c \"exec -a 'codex-engine exec' /bin/sleep 30\" & wait"
    ) as process:
        result = subprocess.run(
            [
                "/bin/bash", str(HARNESS), "--pattern-check", str(process.pid),
                str(snapshot), "node .*codex", "codex.*exec",
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "PATTERN_WAIT_ATTEMPTS": "20"},
            text=True,
            capture_output=True,
            timeout=5,
        )

    assert result.returncode == 0, result.stderr
    assert "matched_pids=2" in result.stdout
    assert result.stdout.strip().endswith("process_patterns=PASS")


def run_result_check(tmp_path: Path, scope: str, *, rc: int, traceback: bool = False):
    case_out = tmp_path / f"out-{scope}"
    case_out.mkdir()
    stderr_log = tmp_path / f"{scope}.stderr.log"
    stderr_log.write_text(
        "Traceback (most recent call last):\nRuntimeError: fake\n" if traceback else ""
    )
    survivor_count = "1" if scope == "plain" else "0"
    return subprocess.run(
        [
            "/bin/bash", str(HARNESS), "--result-check", scope, "codex", str(rc),
            str(case_out), str(stderr_log), "5", survivor_count, "gone",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_plain_result_check_never_prints_pass_before_return_code_validation(tmp_path):
    """Break caught: plain PASS used to precede the required driver_rc assertion."""
    result = run_result_check(tmp_path, "plain", rc=9)

    assert result.returncode == 1
    assert "expected 1" in result.stderr
    assert "=PASS" not in result.stdout


def test_bwrap_result_check_rejects_python_traceback_before_printing_pass(tmp_path):
    """Break caught: bwrap stderr was not checked despite the evidence claim."""
    result = run_result_check(tmp_path, "bwrap", rc=143, traceback=True)

    assert result.returncode == 1
    assert "emitted a traceback" in result.stderr
    assert "=PASS" not in result.stdout


def test_result_check_emits_exact_mechanical_fields_after_all_assertions(tmp_path):
    """Break caught: tracked evidence must preserve every emitted result field."""
    plain = run_result_check(tmp_path, "plain", rc=1)
    bwrap = run_result_check(tmp_path, "bwrap", rc=143)

    assert plain.returncode == 0, plain.stderr
    assert plain.stdout.strip() == (
        "shutdown_codex_plain=PASS driver_rc=1 captured=5 "
        "post_driver_survivors=1 harness_cleanup=gone"
    )
    assert bwrap.returncode == 0, bwrap.stderr
    assert bwrap.stdout.strip() == (
        "shutdown_codex_bwrap=PASS wrapper_rc=143 captured=5 "
        "post_wrapper_survivors=0 harness_cleanup=gone"
    )


def test_plain_workload_resolves_every_reviewer_from_overrides_with_restricted_path(tmp_path):
    """Break caught: the plain driver inherited PATH and ignored resolved overrides."""
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir()
    for command in (
        "awk", "bwrap", "cp", "dirname", "find", "getent", "git", "id", "ln",
        "mkdir", "mktemp", "ps", "readlink", "rg", "rm", "setsid", "sleep",
        "sort", "stat", "wc",
    ):
        target = shutil.which(command)
        assert target is not None
        (tool_dir / command).symlink_to(target)
    launch_log = tmp_path / "launch.log"

    def fake_entry(path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nprintf '%s\\n' \"${0##*/}\" >> \"$FAKE_LAUNCH_LOG\"\n")
        path.chmod(0o755)

    fake_cli = tmp_path / "fake-cli"
    fake_entry(fake_cli)
    codex_entry = tmp_path / "codex" / "bin" / "codex.js"
    opencode_entry = tmp_path / "opencode" / "bin" / "opencode"
    pykrete_entry = tmp_path / "pykrete" / "bin" / "pykrete.ts"
    pi_entry = tmp_path / "pi" / "dist" / "cli.js"
    for entry in (codex_entry, opencode_entry, pykrete_entry, pi_entry):
        fake_entry(entry)
    for directory in (
        tmp_path / "codex" / "node_modules", tmp_path / "opencode" / "node_modules",
        tmp_path / "pykrete" / "src", tmp_path / "pykrete" / "node_modules",
        tmp_path / "pi" / "node_modules", tmp_path / "uv-cache",
    ):
        directory.mkdir()
    secret = tmp_path / "secret"
    pykrete_env = tmp_path / "pykrete.env"
    config = tmp_path / "pykrete.toml"
    secret.write_text("test-secret\n")
    pykrete_env.write_text("NANOGPT_API_KEY=test-key\n")
    config.write_text("[models]\n")
    secret.chmod(0o600)
    pykrete_env.chmod(0o600)
    env = {
        **os.environ,
        "PATH": str(tool_dir),
        "FAKE_LAUNCH_LOG": str(launch_log),
        "UV_BIN": str(fake_cli), "CLAUDE_BIN": str(fake_cli),
        "AGY_BIN": str(fake_cli), "CODEX_ENTRY": str(codex_entry),
        "OPENCODE_ENTRY": str(opencode_entry), "PYKRETE_ENTRY": str(pykrete_entry),
        "PI_ENTRY": str(pi_entry), "GROK_BIN": str(fake_cli),
        "CLAUDE_TOKEN_FILE": str(secret), "PYKRETE_ENV_FILE": str(pykrete_env),
        "PYKRETE_CONFIG_FILE": str(config), "UV_CACHE_SOURCE": str(tmp_path / "uv-cache"),
        "AGY_TOKEN_FILE": str(secret), "CODEX_AUTH_FILE": str(secret),
        "OPENCODE_AUTH_FILE": str(secret), "GROK_AUTH_FILE": str(secret),
    }

    result = subprocess.run(
        ["/bin/bash", str(HARNESS), "--workload-path-check"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert launch_log.read_text().splitlines() == [
        "claude", "agy", "codex", "opencode", "pykrete", "pi", "grok"
    ]
    assert result.stdout.strip().endswith("plain_workload_overrides=PASS")
