"""Caller-contained fixed-pair multi-review holistic slot (Task 11).

Wraps exactly one whole-call Bubblewrap invocation of the multi-review v2
headless driver (`multi-review/multi_review.py`), running the fixed
claude+codex reviewer pair, for the Round 1 "holistic" role. No sandbox
auto-detection and no native per-reviewer containment lives here or anywhere
else in review-loop -- this is the only contained multi-review call shape.

`MultiReviewAdapter.invoke()` returns exactly one of:
  * a validated aggregate -- two qualified raw reports, one per reviewer --
    or
  * a structured ordinary-fallback reason (the caller dispatches the existing
    single-reviewer ordinary path unchanged).
Target/round-input seal drift (observed before OR after the sandboxed call)
is never a fallback: it raises `MultiReviewIndeterminate`, which the caller
must let stop the round, never retry, never fall back from (design: "a
failed fallback also makes the round INDETERMINATE" -- fallback is
attempted by the *caller*, using the pre-existing ordinary dispatch path,
exactly once; this module never retries the sandboxed call itself).

`state.py` must never import this module.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import yaml

from .prompts import RESOURCES, ReviewRecord, SourceFinding, ValidatedReview
from .seals import GitPolicy, SealEntry, seal_target

# The only environment variables the outer wrapper ever sets inside the
# sandbox via `--setenv` (plus bwrap's own hardcoded `--clearenv` survivor,
# PWD -- see execution.py's identical note). `CLAUDE_CODE_OAUTH_TOKEN` is
# never in this list: it reaches the process only via the wrapper command's
# own stdin-read/export, never `--setenv`, never argv.
ENV_ALLOWLIST = ("HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "UV_CACHE_DIR", "PATH", "LANG")

_MULTI_REVIEW_REVIEWERS = ("claude", "codex")
_shell_quote = shlex.quote

_HOLISTIC_FRAGMENT = RESOURCES / "holistic.md"

_SUBJECT_TEXT = (
    "The complete sealed target tree named in this dispatch's `files` "
    "manifest below. Read it with your file-reading tools; nothing has been "
    "inlined into this prompt."
)


class MultiReviewError(Exception):
    """The multi-review call cannot be safely constructed or dispatched;
    callers fail closed (never a soft fallback for a construction-time
    misconfiguration such as a target-intersecting runtime closure)."""


class MultiReviewIndeterminate(Exception):
    """Target or round-input seal drift was observed before or after the
    sandboxed call. Never a fallback signal -- the caller must stop the
    round, never retry this call, and never attempt the ordinary fallback
    path either (a fix or an adversary may have touched the real target)."""


# --- host path resolution (mirrors execution.py's CodexHostPaths idiom) ----


@dataclass(frozen=True)
class MultiReviewHostPaths:
    bwrap: Path
    uv: Path
    claude: Path
    codex_package_root: Path
    codex_entry: Path
    codex_auth_file: Path
    multi_review_root: Path
    resolv_conf: Path
    nsswitch_conf: Path
    ca_certificates: Path
    ca_certificates_dir: Path
    hosts: Path
    hostname: Path
    uv_cache_source: Path
    uv_python_install_source: Path
    usr: Path = Path("/usr")
    wsl: bool = False
    mnt_wsl: Path | None = None


def _require_file(path: Path, message: str) -> Path:
    if not path.is_file():
        raise MultiReviewError(message)
    return path


def _require_dir(path: Path, message: str) -> Path:
    if not path.is_dir():
        raise MultiReviewError(message)
    return path


def resolve_multi_review_host_paths(
    *,
    repo_root: Path,
    uv_bin: Path | None = None,
    claude_bin: Path | None = None,
    codex_bin: Path | None = None,
    codex_home: Path | None = None,
) -> MultiReviewHostPaths:
    """Resolve every runtime and auth source as a stable path outside the
    target, before any argv is constructed. Fails closed on any absent
    prerequisite."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise MultiReviewError("bwrap is not installed; contained multi-review dispatch is unavailable")
    uv_bin = uv_bin or Path(shutil.which("uv") or "")
    if not uv_bin or not uv_bin.is_file():
        raise MultiReviewError("uv is not installed; the multi-review mapping is unavailable")
    claude_bin = claude_bin or Path(shutil.which("claude") or "")
    if not claude_bin or not Path(claude_bin).resolve().is_file():
        raise MultiReviewError("claude CLI is not installed; the multi-review mapping is unavailable")
    codex_bin = codex_bin or Path(shutil.which("codex") or "")
    if not codex_bin or not Path(codex_bin).exists():
        raise MultiReviewError("codex CLI is not installed; the multi-review mapping is unavailable")
    codex_entry = Path(codex_bin).resolve()
    codex_package_root = codex_entry.parent.parent
    codex_home = codex_home or Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    codex_auth_file = _require_file(
        Path(codex_home) / "auth.json", f"codex auth file is absent: {codex_home}/auth.json"
    )
    multi_review_root = _require_dir(
        Path(repo_root) / "multi-review", f"multi-review workspace is absent: {repo_root}/multi-review"
    )
    _require_file(multi_review_root / "multi_review.py", "multi-review driver entry point is absent")

    mnt_wsl = Path("/mnt/wsl")
    wsl = mnt_wsl.is_dir() and (mnt_wsl / "resolv.conf").exists()
    resolv_conf = _require_file(Path("/etc/resolv.conf"), "no /etc/resolv.conf to bind for DNS")
    nsswitch_conf = _require_file(Path("/etc/nsswitch.conf"), "no /etc/nsswitch.conf to bind for DNS")
    ca_certificates_dir = _require_dir(Path("/etc/ssl"), "no /etc/ssl to bind for TLS")
    ca_certificates = _require_file(
        Path("/etc/ssl/certs/ca-certificates.crt"), "no CA bundle to bind for TLS"
    )
    hosts = _require_file(Path("/etc/hosts"), "no /etc/hosts to bind")
    hostname = _require_file(Path("/etc/hostname"), "no /etc/hostname to bind")

    uv_cache_source = Path(os.environ.get("UV_CACHE_DIR") or (Path.home() / ".cache" / "uv"))
    uv_python_install_source = Path(
        os.environ.get("UV_PYTHON_INSTALL_DIR") or (Path.home() / ".local" / "share" / "uv" / "python")
    )

    return MultiReviewHostPaths(
        bwrap=Path(bwrap).resolve(),
        uv=Path(uv_bin).resolve(),
        claude=Path(claude_bin).resolve(),
        codex_package_root=codex_package_root,
        codex_entry=codex_entry,
        codex_auth_file=codex_auth_file,
        multi_review_root=multi_review_root.resolve(),
        resolv_conf=resolv_conf,
        nsswitch_conf=nsswitch_conf,
        ca_certificates=ca_certificates,
        ca_certificates_dir=ca_certificates_dir,
        hosts=hosts,
        hostname=hostname,
        uv_cache_source=uv_cache_source,
        uv_python_install_source=uv_python_install_source,
        wsl=wsl,
        mnt_wsl=mnt_wsl if wsl else None,
    )


def _check_no_target_intersection(host: MultiReviewHostPaths, target_root: Path) -> None:
    """A runtime/auth closure that intersects the sealed target must fail
    closed before any argv is built -- never a soft fallback, since it means
    the mapping itself cannot be trusted to keep the target read-only-exact."""
    target_root = Path(target_root).resolve()
    candidates = (
        host.uv, host.claude, host.codex_package_root, host.codex_entry,
        host.codex_auth_file, host.multi_review_root,
    )
    for candidate in candidates:
        candidate = Path(candidate).resolve()
        if candidate == target_root or candidate.is_relative_to(target_root) or target_root.is_relative_to(candidate):
            raise MultiReviewError(
                f"runtime/auth closure intersects the sealed target and cannot be safely mounted: {candidate}"
            )


# --- policy / request / result types ----------------------------------------


@dataclass(frozen=True)
class MultiReviewPolicy:
    """Narrowed run policy for the holistic multi-review slot (see
    profiles.RunPolicy.holistic_multi_review_models). `models` is either
    empty (unpinned -- `use_cli_defaults: true` is sent) or pins the full
    claude+codex pair exactly (profiles.py's own `_multi_review` validator
    already enforces "the full non-empty pair" upstream of this type)."""

    models: Mapping[str, str] = field(default_factory=dict)
    deadline: datetime | None = None
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class HolisticRequest:
    call_id: str
    request_id: str
    target_seal: str
    round_input_seal: str | None
    scope_locator_ids: tuple[str, ...]
    target_root: Path
    target_entries: tuple[SealEntry, ...]
    run_root: Path
    raw_report_ids: Mapping[str, str]  # {"claude": <id>, "codex": <id>} -- preallocated by the caller


@dataclass(frozen=True)
class QualifiedReport:
    report_id: str  # the preallocated raw_report_id -- NOT the shared record request_id
    reviewer: str
    review: ValidatedReview


# Disclosed, accepted interim limitations of this whole-call (not
# per-reviewer) containment shape. Written to every call's on-disk run
# evidence (`<call_dir>/diagnostics/LIMITATIONS.txt`) and carried on every
# `MultiReviewResult` -- never silently true, always surfaced (fix round 1,
# I1/I2 from review):
#
#  * shared-namespace: reviewer subprocesses (real or fake) run inside the
#    SAME sandbox instance as the driver's own transport/output files
#    (prompt.txt, .REVIEW.md.tmp, REVIEW.md). Native per-reviewer
#    containment is deferred (out of this task's scope).
#  * cross-reviewer token exposure (I1): the wrapper exports
#    CLAUDE_CODE_OAUTH_TOKEN into the ONE process tree the driver's fanout
#    spawns both reviewers from, with no per-reviewer env isolation
#    (multi_review.core.fanout.run_reviewer sets no per-CLI `env=`). The
#    codex reviewer therefore inherits the Claude token even though it never
#    needs it. With the retained provider network, a prompt-injected codex
#    reviewer -- the exact untrusted-target threat this containment exists
#    for -- could exfiltrate it. This is inherent to whole-call (vs
#    per-reviewer) containment; the fixed 6-variable `--clearenv` allowlist
#    is still satisfied (this is the app's own token, not an injected HOST
#    secret), so it is not a mount/env-policy defect, but it is a real,
#    accepted residual risk of this MVP shape.
#  * post-publish forge race (I2): a reviewer that wins the narrow window
#    between the driver's own atomic `REVIEW.md` publish (`.replace()`) and
#    the whole sandbox's teardown (when the wrapped command exits, the
#    kernel tears down the `--unshare-pid` namespace and everything still
#    running in it) can overwrite `/out/REVIEW.md` with a forged aggregate.
#    Every field this adapter's `_collect()` re-verifies (request_id/role/
#    charter_id/target_seal/round_input_seal/scope_locator_ids from the
#    shared `/request.yaml`; both `--raw-report-id` values, readable from
#    `/proc/*/cmdline` in the shared PID namespace; the constant
#    `reviewers_succeeded` shape) is itself readable inside the sandbox by
#    ANY process in it, including a malicious reviewer's own detached
#    background process -- so a forged aggregate CAN pass every check this
#    adapter runs. The real (and only) barrier is process-teardown timing,
#    not validation. See
#    tests/integration/test_multi_review_containment.py::
#    EndToEndAdapterTests::test_post_publish_forge_race_is_sometimes_accepted_documented_residual_risk.
#    Full closure needs native per-reviewer containment (deferred).
#  * interpreter-seed: `seed_uv_python_toolchain` (below) seeds HOME's
#    uv-managed Python toolchain from a dereferenced host copy because the
#    brief's literal fixed env/mount list alone cannot resolve a `>=3.11`
#    interpreter inside a synthetic `HOME` on this host (system Python is
#    3.10). Disclosed as a deviation from the literal brief, not a security
#    concern -- content into an already-writable, already-listed mount, no
#    new mount or `--setenv`.
KNOWN_LIMITATIONS: tuple[str, ...] = (
    "shared-namespace: fake/real reviewer subprocesses run inside the same sandbox "
    "instance as the driver's own transport/output files (prompt.txt, .REVIEW.md.tmp, "
    "REVIEW.md); native per-reviewer containment is deferred.",
    "cross-reviewer token exposure: the driver spawns both reviewers from one process "
    "tree with no per-reviewer env isolation, so the codex reviewer inherits "
    "CLAUDE_CODE_OAUTH_TOKEN despite never needing it; with the retained provider "
    "network, a prompt-injected codex reviewer could exfiltrate it. Per-reviewer env "
    "isolation is out of scope for this whole-call wrapper.",
    "post-publish forge race: a reviewer that wins the race immediately after the "
    "driver's atomic REVIEW.md publish can produce a forged aggregate that passes "
    "every adapter-side validation check (every field re-verified is itself readable "
    "inside the shared sandbox); the only real barrier is bwrap's process-teardown "
    "timing, not validation.",
    "interpreter-seed: HOME's uv-managed Python toolchain is seeded from a "
    "dereferenced host copy (see seed_uv_python_toolchain) because the fixed env/mount "
    "list alone cannot resolve a >=3.11 interpreter inside a synthetic HOME; disclosed "
    "as a deviation from the literal brief, not a security concern.",
)


@dataclass(frozen=True)
class MultiReviewResult:
    reports: tuple[QualifiedReport, QualifiedReport] | None
    fallback_reason: str | None
    limitations: tuple[str, ...] = KNOWN_LIMITATIONS

    def __post_init__(self) -> None:
        if (self.reports is None) == (self.fallback_reason is None):
            raise MultiReviewError("MultiReviewResult must carry exactly one of reports/fallback_reason")


# --- verbatim prompt: byte-identical to parse_verbatim_dispatch_header -----


_REVIEW_TEMPLATE_TITLE = "# Review dispatch\n\n"


def render_verbatim_prompt(request: HolisticRequest) -> str:
    """Render the exact custom_prompt bytes sent to both reviewers.

    `multi_review.core.aggregate.parse_verbatim_dispatch_header` (Task 10)
    requires the six `key: value` dispatch fields to be the FIRST lines of
    the prompt, ending in a blank line before anything else -- it stops
    scanning at the first blank line it meets. review_loop/resources/
    review.md instead leads with a `# Review dispatch` title line before
    those same six fields, for the ordinary (non-verbatim) dispatch path.
    This reuses review.md's own field stringification and fragment
    composition byte-for-byte, only dropping that one leading title line so
    the header lands first, exactly as Task 10's parser requires.

    M4 (fix round 1, noted not fixed): the `safety.md`/`round-one.md`
    fragment set and order below is hand-duplicated from
    `prompts.py`'s own composition, not delegated to
    `prompts.render_prompt`'s `FRAGMENTS` registry, because `"holistic"`
    isn't (and can't cheaply become) a registered fragment there and
    `prompts.py` is out of this task's file scope. If `prompts.py`'s
    fragment set or order ever changes, this function's fragment list must
    be updated to match by hand -- there is no shared source of truth
    enforcing that beyond this comment.
    """
    review_text = (RESOURCES / "review.md").read_text(encoding="utf-8")
    if not review_text.startswith(_REVIEW_TEMPLATE_TITLE):
        raise MultiReviewError("review.md no longer starts with the expected title line; header alignment broke")
    header_first_template = review_text[len(_REVIEW_TEMPLATE_TITLE):]

    context = {
        "request_id": request.request_id,
        "role": "holistic",
        "charter_id": "holistic",
        "target_seal": request.target_seal,
        "round_input_seal": request.round_input_seal if request.round_input_seal is not None else "null",
        "scope_locator_ids": json.dumps(list(request.scope_locator_ids)),
        "subject": _SUBJECT_TEXT,
    }
    try:
        base = header_first_template.format(**context)
    except (KeyError, ValueError, IndexError) as exc:
        raise MultiReviewError(f"cannot render the verbatim multi-review prompt: {exc}") from exc

    fragments = [(RESOURCES / name).read_text(encoding="utf-8") for name in ("safety.md", "round-one.md")]
    holistic_text = _HOLISTIC_FRAGMENT.read_text(encoding="utf-8")
    return base + "".join(fragments) + holistic_text


# --- request.yaml (PromptFile) construction ---------------------------------


def _target_file_paths(request: HolisticRequest) -> tuple[Path, ...]:
    out = []
    for entry in request.target_entries:
        if entry.kind != "file":
            continue
        if entry.path.startswith("/") or ".." in Path(entry.path).parts:
            raise MultiReviewError(f"target entry escapes the sealed scope: {entry.path!r}")
        out.append((request.target_root / entry.path).resolve())
    return tuple(out)


def build_prompt_yaml_text(request: HolisticRequest, policy: MultiReviewPolicy, prompt_text: str) -> str:
    """Build the exact `request.yaml` (multi-review PromptFile) text.

    Always: `reviewers: [claude, codex]`, `synthesizer: none`, `task:
    custom`, `verbatim_custom_prompt: true`, `require_complete_status:
    true`, exact `files` (every sealed target file, absolute path), and
    exactly the `models`/`use_cli_defaults` pair the configured pins imply
    -- never both, never neither.
    """
    files = [str(p) for p in _target_file_paths(request)]
    if not files:
        raise MultiReviewError("multi-review holistic dispatch requires at least one target file")
    doc: dict[str, object] = {
        "prompt_format_version": 2,
        "task": "custom",
        "files": files,
        "reviewers": list(_MULTI_REVIEW_REVIEWERS),
        "synthesizer": "none",
        "verbatim_custom_prompt": True,
        "require_complete_status": True,
        "custom_prompt": prompt_text,
    }
    if policy.models:
        missing = set(_MULTI_REVIEW_REVIEWERS) - set(policy.models)
        if missing:
            raise MultiReviewError(f"policy pins an incomplete reviewer pair, missing: {sorted(missing)}")
        doc["models"] = {cli: policy.models[cli] for cli in _MULTI_REVIEW_REVIEWERS}
        doc["use_cli_defaults"] = False
    else:
        doc["use_cli_defaults"] = True
    return yaml.safe_dump(doc, default_flow_style=False, sort_keys=False)


# --- namespace-only ancestor directory tracking -----------------------------


class _NamespaceDirs:
    """Emits `--dir` entries for every ancestor path component exactly once,
    parents before children, so multiple absolute-path binds (target files,
    HOME) can share overlapping ancestors without a duplicate/out-of-order
    `--dir`."""

    def __init__(self) -> None:
        self._created: set[Path] = set()

    def ensure(self, argv: list[str], path: Path) -> None:
        parts = path.parts
        acc = Path(parts[0])
        for part in parts[1:]:
            acc = acc / part
            if acc not in self._created:
                argv.extend(["--dir", str(acc)])
                self._created.add(acc)


# --- mount policy / argv construction ---------------------------------------


@dataclass(frozen=True)
class MultiReviewCallPaths:
    request_yaml: Path
    out_dir: Path
    home_dir: Path
    uv_cache_dir: Path


def build_multi_review_call(
    request: HolisticRequest,
    policy: MultiReviewPolicy,
    host: MultiReviewHostPaths,
    call_dir: Path,
    *,
    timeout_seconds: int,
) -> tuple[list[str], str, MultiReviewCallPaths]:
    """Build the fixed whole-call Bubblewrap argv for one multi-review pass.

    Returns (argv, oauth_stdin_placeholder_unused, paths). The OAuth token
    itself is never part of this return value -- see `MultiReviewAdapter`,
    which writes it directly to the launched process's stdin and never holds
    it any longer than that.
    """
    _check_no_target_intersection(host, request.target_root)
    raw_ids = [request.raw_report_ids.get(cli) for cli in _MULTI_REVIEW_REVIEWERS]
    if any(not rid for rid in raw_ids) or len(set(raw_ids)) != len(raw_ids):
        raise MultiReviewError("raw_report_ids must preallocate one distinct, non-empty ID per reviewer")

    home_dir = call_dir / "home"
    uv_cache_dir = call_dir / "uv-cache"
    out_dir = call_dir / "out"
    for d in (home_dir, uv_cache_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)
    (home_dir / ".codex").mkdir(parents=True, exist_ok=True)

    request_yaml = call_dir / "request.yaml"
    prompt_text = render_verbatim_prompt(request)
    request_yaml.write_text(build_prompt_yaml_text(request, policy, prompt_text), encoding="utf-8")

    argv: list[str] = [str(host.bwrap), "--clearenv", "--unshare-pid", "--die-with-parent"]

    def ro(src: Path, dst: str) -> None:
        argv.extend(["--ro-bind", str(src), dst])

    ro(host.usr, "/usr")
    argv.extend(["--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64"])

    argv.extend(["--dir", "/etc"])
    ro(host.ca_certificates_dir, "/etc/ssl")
    if Path("/etc/ca-certificates").is_dir():
        ro(Path("/etc/ca-certificates"), "/etc/ca-certificates")
    ro(host.hosts, "/etc/hosts")
    ro(host.hostname, "/etc/hostname")
    ro(host.nsswitch_conf, "/etc/nsswitch.conf")
    if host.wsl and host.mnt_wsl is not None:
        argv.extend(["--dir", "/mnt", "--ro-bind", str(host.mnt_wsl), "/mnt/wsl"])
        argv.extend(["--symlink", "/mnt/wsl/resolv.conf", "/etc/resolv.conf"])
    else:
        ro(host.resolv_conf, "/etc/resolv.conf")

    argv.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"])

    argv.extend(["--dir", "/workspace"])
    ro(host.multi_review_root, "/workspace/multi-review")
    argv.extend(["--dir", "/opt", "--dir", "/opt/uv"])
    ro(host.uv, "/opt/uv/uv")
    argv.extend(["--dir", "/opt/bin"])
    ro(host.claude, "/opt/bin/claude")
    argv.extend(["--dir", "/opt/codex"])
    ro(host.codex_package_root, "/opt/codex/package")
    codex_rel = host.codex_entry.relative_to(host.codex_package_root)
    argv.extend(["--symlink", f"/opt/codex/package/{codex_rel.as_posix()}", "/opt/bin/codex"])

    ro(request_yaml, "/request.yaml")
    ns = _NamespaceDirs()
    for path in _target_file_paths(request):
        ns.ensure(argv, path.parent)
        ro(path, str(path))

    argv.extend(["--dir", "/home"])
    ns.ensure(argv, Path("/home"))
    argv.extend(["--dir", "/home/review"])
    argv.extend(["--bind", str(home_dir), "/home/review"])
    argv.extend(["--dir", "/home/review/.codex"])
    ro(host.codex_auth_file, "/home/review/.codex/auth.json")

    argv.extend(["--bind", str(uv_cache_dir), "/uv-cache"])
    argv.extend(["--bind", str(out_dir), "/out"])

    env = {
        "HOME": "/home/review",
        "CLAUDE_CONFIG_DIR": "/home/review/.claude",
        "CODEX_HOME": "/home/review/.codex",
        "UV_CACHE_DIR": "/uv-cache",
        "PATH": "/opt/bin:/opt/uv:/usr/bin:/bin",
        "LANG": "C.UTF-8",
    }
    for key, value in env.items():
        argv.extend(["--setenv", key, value])

    raw_report_id_flags = " ".join(
        f"--raw-report-id {cli}={_shell_quote(request.raw_report_ids[cli])}" for cli in _MULTI_REVIEW_REVIEWERS
    )
    wrapper = (
        "set +x; IFS= read -r CLAUDE_CODE_OAUTH_TOKEN || exit 91; exec </dev/null; "
        "export CLAUDE_CODE_OAUTH_TOKEN; "
        "exec /opt/uv/uv run --offline --isolated "
        "/workspace/multi-review/multi_review.py --prompt-file /request.yaml "
        f"--out-dir /out --timeout {int(timeout_seconds)} {raw_report_id_flags}"
    )
    argv.extend(["/bin/bash", "-c", wrapper])

    return argv, wrapper, MultiReviewCallPaths(
        request_yaml=request_yaml, out_dir=out_dir, home_dir=home_dir, uv_cache_dir=uv_cache_dir,
    )


# --- runtime seeding: /uv-cache and HOME's managed Python toolchain --------


def seed_uv_cache(dest: Path, source: Path) -> None:
    """Seed a fresh, empty `/uv-cache` staging dir from already-present
    runtime content only -- never triggers a network fetch itself. An
    absent or empty source fails closed here, before any dispatch, rather
    than resolving over the retained provider network under
    `--offline --isolated`."""
    if not source.is_dir() or not any(source.iterdir()):
        raise MultiReviewError(f"uv cache source is absent or empty: {source}")
    result = subprocess.run(
        ["cp", "-a", "--reflink=auto", f"{source}/.", str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise MultiReviewError(f"failed to seed /uv-cache from {source}: {result.stderr.strip()}")


def seed_uv_python_toolchain(home_dir: Path, source_root: Path) -> None:
    """Seed HOME's uv-managed Python installs directory from already-present
    concrete (non-alias, non-symlink) toolchain directories, dereferencing
    any internal symlinks.

    uv's own wheel/venv CACHE (`/uv-cache`) stores cached environments'
    interpreter binaries as symlinks to this SEPARATE, host-absolute
    managed-installs directory -- which the mount policy never binds
    directly (a synthetic `HOME=/home/review` makes that directory identity
    change every call anyway). Without this, `uv run --offline --isolated`
    cannot resolve a `>=3.11` interpreter inside the sandbox at all (the
    fixed PATH's only interpreter is whatever system Python `/usr` carries,
    which is not guaranteed to satisfy the driver's own `requires-python`).
    Seeding real, self-contained copies into the already-writable `/home/
    review` mount needs no new mount or env var -- it is exactly the same
    "seed from already-present runtime content" idiom this design already
    applies to `/uv-cache`, just targeting HOME's own tree instead of a
    second read-only bind.
    """
    dest_root = home_dir / ".local" / "share" / "uv" / "python"
    dest_root.mkdir(parents=True, exist_ok=True)
    if not source_root.is_dir():
        raise MultiReviewError(f"uv python install source is absent: {source_root}")
    found = False
    for entry in sorted(source_root.iterdir()):
        if entry.is_symlink():
            continue  # alias (e.g. "cpython-3.11-..." -> "cpython-3.11.14-...")
        if not entry.is_dir():
            continue
        shutil.copytree(entry, dest_root / entry.name, symlinks=False, dirs_exist_ok=True)
        found = True
    if not found:
        raise MultiReviewError(f"no concrete uv-managed Python install found under {source_root}")


# --- process lifecycle -------------------------------------------------------


@dataclass(frozen=True)
class _RunOutcome:
    exit_status: int | None
    timed_out: bool
    process_tree_terminated: bool


def _write_limitations_evidence(diagnostics_dir: Path) -> None:
    """Write the disclosed interim-limitation note into this call's own
    on-disk run evidence, unconditionally, before dispatch -- not just an
    in-memory `MultiReviewResult.limitations` field."""
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    (diagnostics_dir / "LIMITATIONS.txt").write_text("\n\n".join(KNOWN_LIMITATIONS) + "\n", encoding="utf-8")


def _run_call(
    argv: list[str],
    oauth_token: str,
    *,
    deadline: datetime | None,
    term_grace_seconds: float,
    kill_grace_seconds: float,
    diagnostics_dir: Path,
    popen=subprocess.Popen,
) -> _RunOutcome:
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    with open(diagnostics_dir / "stdout.log", "wb") as stdout_f, open(diagnostics_dir / "stderr.log", "wb") as stderr_f:
        proc = popen(
            argv, env=dict(os.environ), stdin=subprocess.PIPE,
            stdout=stdout_f, stderr=stderr_f, start_new_session=True, text=True,
        )
    try:
        if proc.stdin is not None:
            proc.stdin.write(oauth_token.rstrip("\n") + "\n")
            proc.stdin.close()
    except (BrokenPipeError, OSError):
        pass

    timeout = None
    if deadline is not None:
        timeout = max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds())
    try:
        exit_status = proc.wait(timeout=timeout)
        return _RunOutcome(exit_status=exit_status, timed_out=False, process_tree_terminated=True)
    except subprocess.TimeoutExpired:
        terminated = _terminate(proc, term_grace_seconds, kill_grace_seconds)
        return _RunOutcome(exit_status=None, timed_out=True, process_tree_terminated=terminated)


def _terminate(proc: subprocess.Popen, term_grace_seconds: float, kill_grace_seconds: float) -> bool:
    """Send termination to the wrapper itself; bwrap's own `--die-with-parent`
    plus `--unshare-pid` means the whole contained tree dies with it. Waits
    for full reap before returning, so a caller never accepts output from a
    call whose descendants might still be running."""
    try:
        proc.terminate()
        proc.wait(timeout=term_grace_seconds)
        return True
    except subprocess.TimeoutExpired:
        pass
    try:
        proc.kill()
        proc.wait(timeout=kill_grace_seconds)
        return True
    except subprocess.TimeoutExpired:
        return False


# --- REVIEW.md parsing -------------------------------------------------------


_FENCE_RE = re.compile(r"```review-record\r?\n(.*?)\r?\n```", re.DOTALL)
_TERMINAL_COMPLETE = "REVIEW-STATUS: COMPLETE"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Parse ONLY the leading `--- ... ---` frontmatter block; anything that
    looks like a second `---`-delimited block later in the body is body
    content, never re-parsed as structure (design: "parse only leading
    frontmatter; reject special or inconsistent output artifacts")."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise MultiReviewError("REVIEW.md is missing its leading frontmatter")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise MultiReviewError("REVIEW.md frontmatter is not terminated")
    raw_yaml = "\n".join(lines[1:end])
    try:
        front = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        raise MultiReviewError(f"REVIEW.md frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(front, dict):
        raise MultiReviewError("REVIEW.md frontmatter must be a mapping")
    body = "\n".join(lines[end + 1:])
    return front, body


def _extract_reviewer_section(body: str, cli: str) -> str:
    header = f"## {cli.capitalize()} Review"
    marker = body.find(header)
    if marker == -1:
        raise MultiReviewError(f"REVIEW.md has no {header!r} section")
    start = body.index("\n", marker) + 1
    end = body.find("\n---\n", start)
    section = body[start:end if end != -1 else len(body)]
    return section.strip("\n")


def _record_to_review_record(record: dict) -> ReviewRecord:
    findings = tuple(
        SourceFinding(f["id"], f["claim"], f["severity"], tuple(f["locator_ids"]))
        for f in record["source_findings"]
    )
    return ReviewRecord(
        request_id=record["request_id"], role=record["role"], charter_id=record["charter_id"],
        target_seal=record["target_seal"], round_input_seal=record["round_input_seal"],
        scope_locator_ids=tuple(record["scope_locator_ids"]), source_findings=findings,
    )


# --- the adapter --------------------------------------------------------------


class MultiReviewAdapter:
    def __init__(
        self,
        host: MultiReviewHostPaths,
        oauth_token: str,
        *,
        term_grace_seconds: float = 5.0,
        kill_grace_seconds: float = 5.0,
        popen=subprocess.Popen,
    ) -> None:
        self._host = host
        self._oauth_token = oauth_token
        self._term_grace_seconds = term_grace_seconds
        self._kill_grace_seconds = kill_grace_seconds
        self._popen = popen

    def invoke(self, request: HolisticRequest, policy: MultiReviewPolicy) -> MultiReviewResult:
        unavailable = self._unavailable_prerequisite()
        if unavailable is not None:
            return MultiReviewResult(reports=None, fallback_reason=f"multi-review runtime unavailable: {unavailable}")

        before = seal_target(Path(request.target_root), GitPolicy(enabled=False))
        if before.digest != request.target_seal:
            raise MultiReviewIndeterminate(
                f"target seal drifted before dispatch: expected {request.target_seal!r}, found {before.digest!r}"
            )

        call_dir = Path(request.run_root) / "multi-review-calls" / request.call_id
        deadline = policy.deadline
        remaining = (
            max(1, int((deadline - datetime.now(timezone.utc)).total_seconds())) if deadline is not None
            else (policy.timeout_seconds or 1800)
        )
        if deadline is not None and remaining <= 0:
            return MultiReviewResult(reports=None, fallback_reason="deadline already expired before dispatch")

        # Construction-time failures (missing prerequisite, target-intersecting
        # runtime closure, malformed raw_report_ids) fail closed -- they
        # propagate as MultiReviewError, never a soft fallback.
        argv, _wrapper, paths = build_multi_review_call(
            request, policy, self._host, call_dir, timeout_seconds=remaining,
        )
        _write_limitations_evidence(call_dir / "diagnostics")

        request_yaml_before = paths.request_yaml.read_bytes()

        try:
            seed_uv_cache(paths.uv_cache_dir, self._host.uv_cache_source)
            seed_uv_python_toolchain(paths.home_dir, self._host.uv_python_install_source)
        except MultiReviewError as exc:
            return MultiReviewResult(reports=None, fallback_reason=f"offline runtime seed incomplete: {exc}")

        outcome = _run_call(
            argv, self._oauth_token, deadline=deadline,
            term_grace_seconds=self._term_grace_seconds, kill_grace_seconds=self._kill_grace_seconds,
            diagnostics_dir=call_dir / "diagnostics", popen=self._popen,
        )

        # The seal-drift recheck runs unconditionally, before any other
        # post-call outcome is decided (M3 fix round 1): a timed-out or
        # non-terminating call is still INDETERMINATE, never a fallback, if
        # the target actually drifted during it -- "seal drift is
        # INDETERMINATE, never fallback" has no exception for "and also the
        # call misbehaved in some other way."
        after = seal_target(Path(request.target_root), GitPolicy(enabled=False))
        if after.digest != request.target_seal:
            raise MultiReviewIndeterminate(
                f"target seal drifted during the sandboxed call: expected {request.target_seal!r}, "
                f"found {after.digest!r}"
            )

        if not outcome.process_tree_terminated:
            return MultiReviewResult(reports=None, fallback_reason="multi-review call tree did not terminate")
        if outcome.timed_out:
            return MultiReviewResult(reports=None, fallback_reason="multi-review call exceeded its deadline")

        if paths.request_yaml.read_bytes() != request_yaml_before:
            return MultiReviewResult(
                reports=None, fallback_reason="driver-config request.yaml drifted during the call",
            )

        if outcome.exit_status != 0:
            return MultiReviewResult(reports=None, fallback_reason=f"driver exited {outcome.exit_status}")

        return self._collect(request, policy, paths)

    def _unavailable_prerequisite(self) -> str | None:
        """Re-verify every resolved host prerequisite is still a real,
        reachable file/tree right before dispatch (it may have been resolved
        well before this call, or injected by a test). Any miss here is a
        plain fallback -- the ordinary single-reviewer path does not depend
        on any of these -- never a hard failure."""
        host = self._host
        checks = (
            (host.bwrap, "is_file", "bwrap"),
            (host.uv, "is_file", "uv"),
            (host.claude, "is_file", "claude"),
            (host.codex_entry, "is_file", "codex"),
            (host.codex_auth_file, "is_file", "codex auth file"),
            (host.multi_review_root, "is_dir", "multi-review workspace"),
        )
        for path, kind, label in checks:
            ok = path.is_file() if kind == "is_file" else path.is_dir()
            if not ok:
                return f"{label} is absent: {path}"
        return None

    def _collect(
        self, request: HolisticRequest, policy: MultiReviewPolicy, paths: MultiReviewCallPaths,
    ) -> MultiReviewResult:
        review_md = paths.out_dir / "REVIEW.md"
        if not review_md.is_file() or os.path.islink(review_md):
            return MultiReviewResult(reports=None, fallback_reason="driver did not publish REVIEW.md")
        try:
            text = review_md.read_text(encoding="utf-8")
        except OSError as exc:
            return MultiReviewResult(reports=None, fallback_reason=f"REVIEW.md is unreadable: {exc}")

        try:
            front, body = _split_frontmatter(text)
        except MultiReviewError as exc:
            return MultiReviewResult(reports=None, fallback_reason=str(exc))

        succeeded = front.get("reviewers_succeeded")
        if succeeded != list(_MULTI_REVIEW_REVIEWERS):
            return MultiReviewResult(
                reports=None,
                fallback_reason=f"multi-review pair did not both succeed: reviewers_succeeded={succeeded!r}",
            )

        if policy.models:
            reported_models = front.get("models") or {}
            for cli in _MULTI_REVIEW_REVIEWERS:
                if reported_models.get(cli) != policy.models[cli]:
                    return MultiReviewResult(
                        reports=None,
                        fallback_reason=(
                            f"reported model for {cli} ({reported_models.get(cli)!r}) does not match "
                            f"the configured pin ({policy.models[cli]!r})"
                        ),
                    )

        review_records = front.get("review_records") or {}
        reports: list[QualifiedReport] = []
        for cli in _MULTI_REVIEW_REVIEWERS:
            record = review_records.get(cli)
            if not isinstance(record, dict):
                return MultiReviewResult(reports=None, fallback_reason=f"REVIEW.md has no qualified record for {cli}")
            if record.get("terminal_status") != "COMPLETE":
                return MultiReviewResult(reports=None, fallback_reason=f"{cli}'s record is not terminally COMPLETE")
            raw_report_id = request.raw_report_ids.get(cli)
            if not raw_report_id or record.get("raw_report_id") != raw_report_id:
                return MultiReviewResult(
                    reports=None, fallback_reason=f"{cli}'s raw_report_id does not match the preallocated ID",
                )
            try:
                review_record = _record_to_review_record(record)
            except (KeyError, TypeError) as exc:
                return MultiReviewResult(reports=None, fallback_reason=f"{cli}'s review-record is malformed: {exc}")
            if (
                review_record.request_id != request.request_id
                or review_record.role != "holistic"
                or review_record.charter_id != "holistic"
                or review_record.target_seal != request.target_seal
                or review_record.round_input_seal != request.round_input_seal
                or review_record.scope_locator_ids != request.scope_locator_ids
            ):
                return MultiReviewResult(
                    reports=None, fallback_reason=f"{cli}'s review-record does not match the dispatch expectation",
                )
            try:
                section = _extract_reviewer_section(body, cli)
            except MultiReviewError as exc:
                return MultiReviewResult(reports=None, fallback_reason=str(exc))
            if not section.rstrip().endswith(_TERMINAL_COMPLETE):
                return MultiReviewResult(reports=None, fallback_reason=f"{cli}'s raw body lacks its terminal line")
            if not _FENCE_RE.search(section):
                return MultiReviewResult(reports=None, fallback_reason=f"{cli}'s raw body lacks its fenced record")
            validated = ValidatedReview(
                body=section.encode("utf-8"), record=review_record, terminal_status="COMPLETE", usable=True,
            )
            reports.append(QualifiedReport(report_id=raw_report_id, reviewer=cli, review=validated))

        return MultiReviewResult(reports=(reports[0], reports[1]), fallback_reason=None)
