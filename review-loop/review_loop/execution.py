"""Contained ordinary review execution: mapping, dispatch, deadlines, recovery.

Launches the sole tested ordinary MVP backend -- the Codex CLI under a fixed,
empirically-tested Bubblewrap mapping (design Sec. "Every non-FIX
target-accessing call ... uses a tested host execution mapping"). No reviewer
semantic dispatch (rating, inventory, adjudication) happens here; this module
only builds the mapping, launches, times, proves termination of, and recovers
contained calls. state.py must never import this module.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from .artifacts import canonical_bytes
from .seals import SealEntry

SCHEMA_VERSION = 1

# The only environment variables ever visible inside the contained call.
CODEX_ENV_ALLOWLIST = ("HOME", "CODEX_HOME", "PATH", "LANG")

# The fixed ordinary backend command (design Sec. "Ordinary review
# containment"). `--model <pin>` is appended only when policy resolved an
# explicit pin; the trailing `-` (stdin prompt) is always last.
_CODEX_EXEC_FLAGS = (
    "exec",
    "--sandbox", "read-only",
    "--ignore-user-config",
    "--ignore-rules",
    "--ephemeral",
    "--skip-git-repo-check",
    "--json",
    "--output-last-message", "/report/report.md",
    "-C", "/subject",
)

# Flags a preflight probe must observe in `codex exec --help` output before
# any dispatch is permitted (design Sec. "an absent prerequisite or flag
# stops preflight without dispatch").
REQUIRED_CODEX_HELP_FLAGS = (
    "--sandbox",
    "--ignore-user-config",
    "--ignore-rules",
    "--ephemeral",
    "--skip-git-repo-check",
    "--json",
    "--output-last-message",
    "-C",
)


class ExecutionError(Exception):
    """A call cannot be safely mapped, dispatched, or proven; callers fail closed."""


# --- declarative mapping (design's three disjoint read-only mount classes) ---


@dataclass(frozen=True)
class ExecutionMapping:
    target_ro: tuple[Path, ...]
    inputs_ro: tuple[Path, ...]
    runtime_ro: tuple[Path, ...]
    output_rw: Path
    scratch_rw: Path
    network: bool
    credentials: tuple[Path, ...]


# --- call lifecycle types ---


@dataclass(frozen=True)
class CallRequest:
    call_id: str
    role: str
    target_root: Path
    target_entries: tuple[SealEntry, ...]  # () means no target bytes are exposed
    input_paths: tuple[Path, ...]
    run_root: Path
    prompt: str
    model: str | None = None
    verify_target_unchanged: Callable[[], None] | None = None
    exclusions: tuple[str, ...] = ()


@dataclass(frozen=True)
class CallStarted:
    call_id: str
    role: str
    started_at: str
    pid: int
    report_path: Path
    call_dir: Path


@dataclass(frozen=True)
class CallCompletion:
    call_id: str
    outcome: str  # "COMPLETED" | "FAILED" | "INDETERMINATE"
    reason: str | None
    report_path: Path | None
    report_text: str | None
    exit_status: int | None
    finished_at: str


@dataclass(frozen=True)
class TerminationProof:
    call_id: str
    proven: bool
    method: str


# --- Codex host path resolution (Step 3: stable paths outside the target) ---


@dataclass(frozen=True)
class CodexHostPaths:
    bwrap: Path
    node: Path
    codex_package_root: Path
    codex_entry: Path
    auth_file: Path
    resolv_conf: Path
    nsswitch_conf: Path
    ca_certificates: Path
    usr: Path = Path("/usr")


def _require_file(path: Path, message: str) -> Path:
    if not path.is_file():
        raise ExecutionError(message)
    return path


def resolve_codex_host_paths(
    *,
    codex_bin: Path | None = None,
    codex_home: Path | None = None,
) -> CodexHostPaths:
    """Resolve every host prerequisite as a stable path outside the target.

    Fails closed (`ExecutionError`) if any prerequisite is absent -- this is
    called during preflight, before any dispatch.
    """
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise ExecutionError("bwrap is not installed; contained dispatch is unavailable")
    node = shutil.which("node")
    if not node:
        raise ExecutionError("node is not installed; the Codex mapping is unavailable")
    codex_bin = codex_bin or Path(shutil.which("codex") or "")
    if not codex_bin or not codex_bin.exists():
        raise ExecutionError("codex CLI is not installed; the Codex mapping is unavailable")
    codex_entry = Path(codex_bin).resolve()
    codex_package_root = codex_entry.parent.parent
    codex_home = codex_home or Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    auth_file = _require_file(
        Path(codex_home) / "auth.json", f"codex auth file is absent: {codex_home}/auth.json"
    )
    resolv_conf = _require_file(Path("/etc/resolv.conf"), "no /etc/resolv.conf to bind for DNS")
    nsswitch_conf = _require_file(Path("/etc/nsswitch.conf"), "no /etc/nsswitch.conf to bind for DNS")
    ca_certificates = _require_file(
        Path("/etc/ssl/certs/ca-certificates.crt"), "no CA bundle to bind for TLS"
    )
    return CodexHostPaths(
        bwrap=Path(bwrap).resolve(),
        node=Path(node).resolve(),
        codex_package_root=codex_package_root,
        codex_entry=_require_file(codex_entry, f"codex entry point is absent: {codex_entry}"),
        auth_file=auth_file,
        resolv_conf=resolv_conf,
        nsswitch_conf=nsswitch_conf,
        ca_certificates=ca_certificates,
    )


def preflight_codex_mapping(host: CodexHostPaths, *, run_bwrap_help_probe: bool = True) -> None:
    """Run the contained `codex exec --help` probe; stop before dispatch on any miss.

    Uses the *real* outer Bubblewrap mapping (minus target/input mounts) so a
    broken mapping is caught here, never discovered mid-dispatch.
    """
    if not run_bwrap_help_probe:
        return
    argv = [str(host.bwrap), "--clearenv", "--unshare-pid", "--die-with-parent"]
    argv += ["--ro-bind", str(host.usr), "/usr"]
    argv += ["--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64"]
    argv += ["--ro-bind", str(host.codex_package_root), str(host.codex_package_root)]
    argv += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    argv += ["--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/tmp"]
    argv += [str(host.node), str(host.codex_entry), "exec", "--help"]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExecutionError(f"codex exec --help probe could not run: {exc}") from exc
    if result.returncode != 0:
        raise ExecutionError(f"codex exec --help probe failed (exit {result.returncode}): {result.stderr}")
    missing = [flag for flag in REQUIRED_CODEX_HELP_FLAGS if flag not in result.stdout]
    if missing:
        raise ExecutionError(f"codex exec --help is missing required flags: {missing}")


# --- mapping construction: the fixed, tested outer Bubblewrap wrapper ---


def _check_relative(entry: SealEntry) -> None:
    if entry.path.startswith("/") or ".." in Path(entry.path).parts:
        raise ExecutionError(f"target entry escapes the sealed scope: {entry.path!r}")


def build_codex_call(
    request: CallRequest, host: CodexHostPaths, call_dir: Path
) -> tuple[list[str], dict[str, str], ExecutionMapping]:
    """Build the fixed outer Bubblewrap argv for one Codex ordinary call.

    Every readable path is bound individually and read-only: `/subject` is a
    synthetic, initially empty directory populated only with the exact sealed
    `target_entries`, never a live bind of the whole target directory (design:
    "synthetic empty /subject").
    """
    home_dir = call_dir / "home"
    scratch_dir = call_dir / "scratch"
    report_dir = call_dir / "report"
    for d in (home_dir, scratch_dir, report_dir):
        d.mkdir(parents=True, exist_ok=True)

    argv: list[str] = [str(host.bwrap), "--clearenv", "--unshare-pid", "--die-with-parent"]

    def ro(src: Path, dst: str) -> None:
        argv.extend(["--ro-bind", str(src), dst])

    ro(host.usr, "/usr")
    argv.extend(["--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64"])
    ro(host.codex_package_root, str(host.codex_package_root))
    ro(host.resolv_conf, "/etc/resolv.conf")
    ro(host.nsswitch_conf, "/etc/nsswitch.conf")
    ro(host.ca_certificates, "/etc/ssl/certs/ca-certificates.crt")
    argv.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"])

    argv.extend(["--bind", str(home_dir), "/home/reviewer"])
    argv.extend(["--dir", "/home/reviewer/.codex"])
    ro(host.auth_file, "/home/reviewer/.codex/auth.json")
    argv.extend(["--bind", str(scratch_dir), "/scratch"])
    argv.extend(["--bind", str(report_dir), "/report"])

    argv.extend(["--dir", "/subject"])
    target_ro: list[Path] = []
    for entry in request.target_entries:
        _check_relative(entry)
        if any(
            entry.path == excluded or entry.path.startswith(f"{excluded}/")
            for excluded in request.exclusions
        ):
            raise ExecutionError(f"excluded target entry reached the execution mapping: {entry.path!r}")
        src = request.target_root / entry.path
        dst = f"/subject/{entry.path}"
        if entry.kind == "dir":
            argv.extend(["--dir", dst])
        else:
            ro(src, dst)
        target_ro.append(src)

    inputs_ro: list[Path] = []
    for i, raw in enumerate(request.input_paths):
        p = Path(raw)
        dst = f"/inputs/{i}/{p.name}"
        ro(p, dst)
        inputs_ro.append(p)

    argv.extend(["--chdir", "/subject"])
    env = {"HOME": "/home/reviewer", "CODEX_HOME": "/home/reviewer/.codex", "PATH": "/usr/bin", "LANG": "C.UTF-8"}
    for key, value in env.items():
        argv.extend(["--setenv", key, value])
    # bwrap hardcodes PWD as a `--clearenv` survivor ("except for PWD"); it is
    # not something this mapping sets, cannot be unset (`--unsetenv PWD` is a
    # documented no-op for it), and always carries the synthetic `/subject`
    # chdir target -- never host-derived information.

    inner = [str(host.node), str(host.codex_entry), *_CODEX_EXEC_FLAGS]
    if request.model:
        inner.extend(["--model", request.model])
    inner.append("-")
    argv.extend(inner)

    mapping = ExecutionMapping(
        target_ro=tuple(target_ro),
        inputs_ro=tuple(inputs_ro),
        runtime_ro=(
            host.usr,
            host.codex_package_root,
            host.resolv_conf,
            host.nsswitch_conf,
            host.ca_certificates,
            host.auth_file,
        ),
        output_rw=report_dir,
        scratch_rw=scratch_dir,
        network=True,
        credentials=(host.auth_file,),
    )
    return argv, env, mapping


def codex_builder(host: CodexHostPaths) -> Callable[[CallRequest, Path], tuple[list[str], dict[str, str], ExecutionMapping]]:
    def _build(request: CallRequest, call_dir: Path) -> tuple[list[str], dict[str, str], ExecutionMapping]:
        return build_codex_call(request, host, call_dir)

    return _build


# --- capacity ---


def default_capacity(advertised: int | None = None) -> int:
    """Host-advertised concurrency limit, or a conservative default when absent."""
    if advertised is not None:
        if advertised < 1:
            raise ExecutionError("advertised capacity must be a positive integer")
        return advertised
    n = os.cpu_count()
    return n if n else 1


# --- atomic CALL_STARTED persistence ---


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    data = canonical_bytes(payload)
    with open(tmp, "xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    dir_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def load_call_started(path: Path) -> CallStarted:
    data = json.loads(Path(path).read_text())
    return CallStarted(
        call_id=data["call_id"],
        role=data["role"],
        started_at=data["started_at"],
        pid=data["pid"],
        report_path=Path(data["report_path"]),
        call_dir=Path(data["call_dir"]),
    )


# --- executor ---

Builder = Callable[[CallRequest, Path], tuple[Sequence[str], dict, ExecutionMapping]]


class Executor:
    """Launches, times out, proves termination of, and recovers contained calls.

    Backend-agnostic: `builder` supplies the argv/env/mapping for one call.
    The default is the tested Codex Bubblewrap mapping; unit tests may inject
    a fake-process builder and never touch Bubblewrap.
    """

    def __init__(
        self,
        builder: Builder,
        *,
        term_grace_seconds: float = 5.0,
        kill_grace_seconds: float = 5.0,
        recovery_poll_attempts: int = 20,
        recovery_poll_interval: float = 0.1,
        popen: Callable[..., subprocess.Popen] = subprocess.Popen,
        kill_fn: Callable[[int, int], None] = os.kill,
        probe_alive_fn: Callable[[int], bool] | None = None,
    ) -> None:
        self._builder = builder
        self._term_grace_seconds = term_grace_seconds
        self._kill_grace_seconds = kill_grace_seconds
        self._recovery_poll_attempts = recovery_poll_attempts
        self._recovery_poll_interval = recovery_poll_interval
        self._popen = popen
        self._kill_fn = kill_fn
        self._probe_alive_fn = probe_alive_fn or self._default_probe_alive
        self._live: dict[str, tuple[subprocess.Popen, CallRequest]] = {}

    @staticmethod
    def _default_probe_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def start(self, request: CallRequest) -> CallStarted:
        call_dir = Path(request.run_root) / "calls" / request.call_id
        argv, env, mapping = self._builder(request, call_dir)
        report_path = mapping.output_rw / "report.md"
        diagnostics_dir = call_dir / "diagnostics"
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        stdout_f = open(diagnostics_dir / "stdout.log", "wb")
        stderr_f = open(diagnostics_dir / "stderr.log", "wb")
        try:
            # The outer process inherits this launcher's real environment --
            # that is realistic (a controller is not itself scrubbed) and
            # matches the actual security boundary: `--clearenv` inside the
            # Bubblewrap argv, not a Python-side env substitution. `env`
            # (returned by the builder) declares only the allowlisted names
            # `--setenv` rebuilds inside the sandbox.
            proc = self._popen(
                list(argv),
                env=dict(os.environ),
                stdin=subprocess.PIPE,
                stdout=stdout_f,
                stderr=stderr_f,
                start_new_session=True,
            )
        finally:
            stdout_f.close()
            stderr_f.close()
        try:
            if proc.stdin is not None:
                proc.stdin.write(request.prompt.encode("utf-8"))
                proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass  # the process may have exited immediately; finish() observes that

        started_at = datetime.now(timezone.utc).isoformat()
        started = CallStarted(
            call_id=request.call_id,
            role=request.role,
            started_at=started_at,
            pid=proc.pid,
            report_path=report_path,
            call_dir=call_dir,
        )
        _atomic_write_json(
            call_dir / "call_started.json",
            {
                "schema_version": SCHEMA_VERSION,
                "call_id": started.call_id,
                "role": started.role,
                "started_at": started.started_at,
                "pid": started.pid,
                "report_path": str(started.report_path),
                "call_dir": str(started.call_dir),
            },
        )
        self._live[request.call_id] = (proc, request)
        return started

    def finish(self, started: CallStarted, *, deadline: datetime | None = None) -> CallCompletion:
        entry = self._live.get(started.call_id)
        if entry is None:
            raise ExecutionError(f"finish() called for an unknown or already-finished call: {started.call_id}")
        proc, request = entry
        timeout = None
        if deadline is not None:
            timeout = max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds())
        try:
            exit_status = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.terminate(started)
            return CallCompletion(
                call_id=started.call_id,
                outcome="INDETERMINATE",
                reason="deadline_expired",
                report_path=None,
                report_text=None,
                exit_status=None,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        del self._live[started.call_id]
        finished_at = datetime.now(timezone.utc).isoformat()
        if exit_status != 0:
            return CallCompletion(started.call_id, "FAILED", f"nonzero_exit:{exit_status}", None, None, exit_status, finished_at)
        report_text = self._validate_report(started.report_path)
        if report_text is None:
            return CallCompletion(started.call_id, "FAILED", "invalid_report", None, None, exit_status, finished_at)
        if request.verify_target_unchanged is not None:
            request.verify_target_unchanged()  # raises; never soft-downgraded (no fallback on mutation)
        return CallCompletion(started.call_id, "COMPLETED", None, started.report_path, report_text, exit_status, finished_at)

    @staticmethod
    def _validate_report(report_path: Path) -> str | None:
        try:
            if not report_path.is_file() or os.path.islink(report_path):
                return None
            text = report_path.read_text()
        except OSError:
            return None
        if not text.strip():
            return None
        return text

    def terminate(self, started: CallStarted) -> TerminationProof:
        entry = self._live.pop(started.call_id, None)
        if entry is not None:
            proc, _request = entry
            return self._terminate_live(started.call_id, proc)
        return self._terminate_recovered(started)

    def _terminate_live(self, call_id: str, proc: subprocess.Popen) -> TerminationProof:
        proc.terminate()
        try:
            proc.wait(timeout=self._term_grace_seconds)
            return TerminationProof(call_id, True, "term")
        except subprocess.TimeoutExpired:
            pass
        proc.kill()
        try:
            proc.wait(timeout=self._kill_grace_seconds)
            return TerminationProof(call_id, True, "kill")
        except subprocess.TimeoutExpired:
            return TerminationProof(call_id, False, "unprovable")

    def _terminate_recovered(self, started: CallStarted) -> TerminationProof:
        pid = started.pid
        for sig, label in ((signal.SIGTERM, "term"), (signal.SIGKILL, "kill")):
            try:
                self._kill_fn(pid, sig)
            except ProcessLookupError:
                return TerminationProof(started.call_id, True, "already_gone")
            for _ in range(self._recovery_poll_attempts):
                time.sleep(self._recovery_poll_interval)
                if not self._probe_alive_fn(pid):
                    return TerminationProof(started.call_id, True, label)
        return TerminationProof(started.call_id, False, "unprovable")

    def run_waves(
        self, requests: Sequence[CallRequest], capacity: int, expiry: datetime | None
    ) -> tuple[CallCompletion, ...]:
        capacity = max(1, capacity)
        completions: list[CallCompletion] = []
        remaining = list(requests)
        while remaining:
            wave = remaining[:capacity]
            remaining = remaining[capacity:]
            started_in_wave: list[tuple[CallRequest, CallStarted]] = []
            deadline_hit = False
            for request in wave:
                if expiry is not None and datetime.now(timezone.utc) >= expiry:
                    completions.append(self._not_dispatched(request))
                    deadline_hit = True
                    continue
                started_in_wave.append((request, self.start(request)))
            for _request, started in started_in_wave:
                completions.append(self.finish(started, deadline=expiry))
            if deadline_hit:
                for request in remaining:
                    completions.append(self._not_dispatched(request))
                remaining = []
        return tuple(completions)

    @staticmethod
    def _not_dispatched(request: CallRequest) -> CallCompletion:
        return CallCompletion(
            call_id=request.call_id,
            outcome="INDETERMINATE",
            reason="deadline_expired_before_launch",
            report_path=None,
            report_text=None,
            exit_status=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
