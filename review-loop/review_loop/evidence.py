"""Stage 0 evidence discovery and contained gate execution.

Merges operator, repository, and scout-proposed evidence gates (design Sec.
4, "Preflight and Stage 0") and executes each applicable gate under a
dedicated, stricter containment mapping than ordinary review dispatch: no
provider credential, no network, writes confined to disposable scratch
(design: "supplies no host credentials, denies network access and writes
outside the copy/scratch"). This module owns gate command safety policy and
gate execution; it never dispatches an ordinary reviewer and never imports
state.py's kernel beyond its fixed gate-policy constants.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .prompts import RoleValidationError, ValidatedRoleArtifact
from .seals import GitPolicy, SealEntry, TargetSeal, seal_target
from .state import REQUIRED_GATE_IDS

GATE_TIMEOUT_SECONDS = 300


class EvidenceError(Exception):
    """Evidence discovery or gate execution cannot proceed; callers fail closed."""


class UnsafeGateCommand(EvidenceError):
    """A gate argv is rejected by the closed safe-command policy."""


class EvidenceDiscoveryIndeterminate(EvidenceError):
    """The evidence scout failed twice; Stage 0 becomes INDETERMINATE."""


class GateContainmentError(EvidenceError):
    """A gate execution mapping does not meet the no-credential/no-network policy."""


# --- gate command safety policy (closed allowlist, not a shell) -----------

# Deliberately narrow: only common test/build/lint executables a baseline or
# repository-declared gate would invoke directly (never through a shell).
# Extending this list is a conscious policy decision, not a default.
_SAFE_COMMAND_BASENAMES = frozenset(
    {
        "pytest", "python3", "python", "unittest",
        "node", "npm", "npx", "yarn", "pnpm", "jest", "tsc", "eslint",
        "make", "cargo", "go", "ruff", "mypy",
        "rspec", "bundle", "rake",
        "gradle", "mvn", "phpunit", "composer",
    }
)

# Executables that exist specifically to interpret further shell syntax; a
# safe baseline/gate command must never be one of these, even if a future
# edit widened the allowlist above by mistake.
_SHELL_BASENAMES = frozenset(
    {
        "sh", "bash", "zsh", "dash", "ksh", "csh", "tcsh",
        "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh",
        "eval", "exec", "env",
    }
)

# POSIX shell control operators plus the classic injection vectors
# (backtick/`$(`). argv is always exec'd directly (never shell=True), but
# rejecting these defends against a future accidental shell=True and against
# a tool that reinterprets its own argv.
_CONTROL_CHARACTERS = frozenset(";&|`$<>\n\r")


def validate_gate_argv(argv: Sequence[str]) -> None:
    if not isinstance(argv, (list, tuple)) or not argv or not all(
        isinstance(a, str) and a for a in argv
    ):
        raise UnsafeGateCommand("argv must be a non-empty list of non-empty strings")
    basename = Path(argv[0]).name
    if basename in _SHELL_BASENAMES:
        raise UnsafeGateCommand(f"command is a shell interpreter, rejected: {basename!r}")
    if basename not in _SAFE_COMMAND_BASENAMES:
        raise UnsafeGateCommand(f"command is not in the closed safe-command allowlist: {basename!r}")
    for arg in argv:
        if any(ch in _CONTROL_CHARACTERS for ch in arg):
            raise UnsafeGateCommand(f"argv element contains a rejected control character: {arg!r}")


# --- gate proposals and the merged plan ------------------------------------


@dataclass(frozen=True)
class GateProposal:
    """One operator- or repository-declared gate (not LLM output)."""

    id: str
    argv: tuple[str, ...]
    applicability: str  # "applicable" | "not_applicable"
    rationale: str


@dataclass(frozen=True)
class Gate:
    id: str
    argv: tuple[str, ...]
    applicability: str
    classification: str  # derived: "required" iff id in REQUIRED_GATE_IDS
    rationale: str
    provenance: str  # "operator" | "repository" | "scout"


@dataclass(frozen=True)
class EvidencePlan:
    gates: tuple[Gate, ...]
    evidence_gaps: tuple[str, ...]


def _classification_for(gate_id: str) -> str:
    return "required" if gate_id in REQUIRED_GATE_IDS else "supporting"


def _validate_proposal(proposal: GateProposal, where: str) -> None:
    if not isinstance(proposal, GateProposal):
        raise EvidenceError(f"{where} must be a GateProposal")
    if not isinstance(proposal.id, str) or not proposal.id:
        raise EvidenceError(f"{where}.id must be a non-empty string")
    if proposal.applicability not in {"applicable", "not_applicable"}:
        raise EvidenceError(f"{where}.applicability is invalid")
    if not isinstance(proposal.rationale, str) or not proposal.rationale:
        raise EvidenceError(f"{where}.rationale must be a non-empty string")
    validate_gate_argv(proposal.argv)


def _gate_from_proposal(proposal: GateProposal, provenance: str, where: str) -> Gate:
    _validate_proposal(proposal, where)
    return Gate(
        id=proposal.id,
        argv=tuple(proposal.argv),
        applicability=proposal.applicability,
        classification=_classification_for(proposal.id),
        rationale=proposal.rationale,
        provenance=provenance,
    )


def _gate_from_scout_dict(raw: dict, where: str) -> Gate:
    # raw comes from prompts._validate_evidence's returned artifact, which
    # already enforced id/argv/applicability/classification/rationale shape
    # and that classification agrees with the fixed gate policy.
    validate_gate_argv(raw["argv"])
    return Gate(
        id=raw["id"],
        argv=tuple(raw["argv"]),
        applicability=raw["applicability"],
        classification=_classification_for(raw["id"]),
        rationale=raw["rationale"],
        provenance="scout",
    )


def discover_evidence(
    operator: Sequence[GateProposal],
    repository: Sequence[GateProposal],
    scout: Callable[[], ValidatedRoleArtifact],
) -> EvidencePlan:
    """Merge evidence sources; operator beats repository beats scout.

    ``scout`` is invoked once per dispatch attempt (it performs the real
    dispatch + ``validate_role_json("evidence", ...)`` each call). A
    ``RoleValidationError`` from the first attempt is retried once (design:
    "A malformed result receives one retry"); a second failure raises
    ``EvidenceDiscoveryIndeterminate`` (design: "a second failure makes Stage
    0 INDETERMINATE"). A valid empty gate list is a disclosed gap, not an
    error -- state.py's own ``reconcile_gates`` records that gap.
    """
    try:
        result = scout()
    except RoleValidationError:
        try:
            result = scout()
        except RoleValidationError as exc:
            raise EvidenceDiscoveryIndeterminate(
                "evidence scout output was malformed twice"
            ) from exc
    if not isinstance(result, ValidatedRoleArtifact) or result.role_id != "evidence":
        raise EvidenceError("scout must return a validated 'evidence' role artifact")

    merged: dict[str, Gate] = {}
    for i, raw in enumerate(result.artifact["gates"]):
        gate = _gate_from_scout_dict(raw, f"scout.gates[{i}]")
        merged[gate.id] = gate
    for i, proposal in enumerate(repository):
        merged[proposal.id] = _gate_from_proposal(proposal, "repository", f"repository[{i}]")
    for i, proposal in enumerate(operator):
        merged[proposal.id] = _gate_from_proposal(proposal, "operator", f"operator[{i}]")

    gaps = list(result.artifact["evidence_gaps"])
    return EvidencePlan(gates=tuple(merged.values()), evidence_gaps=tuple(gaps))


# --- contained gate execution: no credential, no network, scratch-only ----


@dataclass(frozen=True)
class GateHostPaths:
    bwrap: Path
    usr: Path = Path("/usr")


def resolve_gate_host_paths() -> GateHostPaths:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise GateContainmentError("bwrap is not installed; contained gate dispatch is unavailable")
    return GateHostPaths(bwrap=Path(bwrap).resolve())


@dataclass(frozen=True)
class ExecutionMapping:
    """Declarative gate containment description (evidence-gate specific).

    Deliberately not execution.py's ``ExecutionMapping``: that type's fixed
    ordinary mapping always mounts ``auth.json`` and leaves network on
    (execution.py's ``build_codex_call``). Reusing it here risked a reviewer
    silently assuming those same defaults apply to gates; a distinct type
    with no ``credentials``/``network`` fields defaulting "on" removes that
    class of mistake entirely -- ``network`` is always False and
    ``credentials`` is always empty for a gate mapping, enforced below.
    """

    target_ro: tuple[Path, ...]
    inputs_ro: tuple[Path, ...]
    scratch_rw: Path
    diagnostics_rw: Path
    network: bool
    credentials: tuple[Path, ...]


def build_gate_mapping(
    host: GateHostPaths, seal: TargetSeal, call_dir: Path, inputs_ro: Sequence[Path] = ()
) -> ExecutionMapping:
    scratch = call_dir / "scratch"
    diagnostics = call_dir / "diagnostics"
    scratch.mkdir(parents=True, exist_ok=True)
    diagnostics.mkdir(parents=True, exist_ok=True)
    target_ro = tuple(Path(seal.root) / entry.path for entry in seal.entries)
    return ExecutionMapping(
        target_ro=target_ro,
        inputs_ro=tuple(Path(p) for p in inputs_ro),
        scratch_rw=scratch,
        diagnostics_rw=diagnostics,
        network=False,
        credentials=(),
    )


def _check_relative(entry: SealEntry) -> None:
    if entry.path.startswith("/") or ".." in Path(entry.path).parts:
        raise GateContainmentError(f"target entry escapes the sealed scope: {entry.path!r}")


def _build_gate_argv(host: GateHostPaths, mapping: ExecutionMapping, seal: TargetSeal, command: Sequence[str]) -> list[str]:
    argv: list[str] = [
        str(host.bwrap), "--clearenv", "--unshare-pid", "--unshare-net", "--die-with-parent",
    ]
    argv += ["--ro-bind", str(host.usr), "/usr"]
    argv += ["--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64"]
    argv += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]

    argv += ["--dir", "/subject"]
    for entry in seal.entries:
        _check_relative(entry)
        src = Path(seal.root) / entry.path
        dst = f"/subject/{entry.path}"
        if entry.kind == "dir":
            argv += ["--dir", dst]
        else:
            argv += ["--ro-bind", str(src), dst]

    for i, path in enumerate(mapping.inputs_ro):
        argv += ["--ro-bind", str(path), f"/inputs/{i}/{Path(path).name}"]

    argv += ["--bind", str(mapping.scratch_rw), "/scratch"]
    argv += ["--chdir", "/subject"]
    argv += ["--setenv", "HOME", "/tmp", "--setenv", "PATH", "/usr/bin", "--setenv", "LANG", "C.UTF-8"]
    argv += list(command)
    return argv


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    argv: tuple[str, ...]
    classification: str
    applicability: str
    provenance: str
    rationale: str
    target_seal: str
    status: str  # "PASSED" | "FAILED"
    exit_status: int | None
    stdout_excerpt: str
    stderr_excerpt: str


_EXCERPT_LIMIT = 4000


def execute_gate(
    gate: Gate,
    mapping: ExecutionMapping,
    seal: TargetSeal,
    *,
    host: GateHostPaths | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    timeout: float = GATE_TIMEOUT_SECONDS,
) -> GateResult:
    """Run one applicable gate command under the no-credential/no-network mapping.

    Never called for a ``not_applicable`` gate -- the caller filters those
    (state.py rejects an executed non-applicable gate outright). Validates
    the safe-command policy again here as a second, defense-in-depth check
    even though ``discover_evidence`` already validated it at plan time.
    """
    validate_gate_argv(gate.argv)
    if mapping.network or mapping.credentials:
        raise GateContainmentError(
            "gate execution mapping must have no network and no credentials"
        )
    resolved_host = host or resolve_gate_host_paths()
    argv = _build_gate_argv(resolved_host, mapping, seal, gate.argv)

    try:
        completed = run(argv, capture_output=True, timeout=timeout, text=True)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        return GateResult(
            gate_id=gate.id,
            argv=tuple(gate.argv),
            classification=gate.classification,
            applicability=gate.applicability,
            provenance=gate.provenance,
            rationale=gate.rationale,
            target_seal=seal.digest,
            status="FAILED",
            exit_status=None,
            stdout_excerpt=stdout[-_EXCERPT_LIMIT:],
            stderr_excerpt=(stderr + "\ngate execution timed out")[-_EXCERPT_LIMIT:],
        )

    (mapping.diagnostics_rw / "stdout.log").write_text(completed.stdout or "")
    (mapping.diagnostics_rw / "stderr.log").write_text(completed.stderr or "")
    status = "PASSED" if completed.returncode == 0 else "FAILED"
    return GateResult(
        gate_id=gate.id,
        argv=tuple(gate.argv),
        classification=gate.classification,
        applicability=gate.applicability,
        provenance=gate.provenance,
        rationale=gate.rationale,
        target_seal=seal.digest,
        status=status,
        exit_status=completed.returncode,
        stdout_excerpt=(completed.stdout or "")[-_EXCERPT_LIMIT:],
        stderr_excerpt=(completed.stderr or "")[-_EXCERPT_LIMIT:],
    )


def make_disposable_copy(seal: TargetSeal, dest: Path) -> Path:
    """Materialize a writable copy of ``seal``'s exact entries at ``dest``.

    Reads only ``seal.root``; never writes there. This copy is the sole
    surface bounded manual mutation may write to (design: "disposable exact
    copy ... transient execution substrate, not a durable review artifact")
    -- the caller discards ``dest`` once mutation evidence collection ends.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = Path(seal.root)
    for entry in seal.entries:
        _check_relative(entry)
        dst = dest / entry.path
        if entry.kind == "dir":
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / entry.path, dst)
    # Apply directory modes after populating descendants so a restrictive
    # source mode cannot prevent construction of its own sealed children.
    for entry in reversed(seal.entries):
        if entry.kind == "dir":
            (dest / entry.path).chmod(entry.mode)
    return dest


# --- opportunistic mutation evidence: always supporting, never blocking ---


class MutationPlanError(EvidenceError):
    """A mutation plan is internally inconsistent; the caller built it wrong."""


@dataclass(frozen=True)
class ManualMutation:
    """One bounded, hand-authored mutation applied only to the disposable copy.

    ``mutate`` is a pure function from the original file's text to the
    mutated text. It is applied in-process to a file inside the disposable
    copy and reverted immediately after that mutant's run -- the sealed
    target is never referenced here. ``equivalence_claim`` records whether
    whoever proposed the mutation expects it to be behaviorally equivalent
    (design: "each non-equivalent mutant must make it fail"); a mutant that
    still fails the targeted test is always "caught" regardless of the
    claim -- the claim only disambiguates a passing run.
    """

    id: str
    target_path: str  # POSIX-relative path within the disposable copy
    mutate: Callable[[str], str]
    rationale: str
    equivalence_claim: bool = False


@dataclass(frozen=True)
class MutationPlan:
    """What ``run_mutation_evidence`` may run, resolved before dispatch.

    Never installs or initializes tooling itself: ``tool_argv`` must already
    be a working, pre-configured invocation the caller discovered
    opportunistically (design: "an already installed, configured mutation
    tool"). When neither ``tool_argv`` nor ``manual_mutations`` is supplied,
    mutation evidence is simply unavailable -- that is not an error.
    """

    baseline_argv: tuple[str, ...] | None
    tool_argv: tuple[str, ...] | None = None
    manual_mutations: tuple[ManualMutation, ...] = ()
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class MutantOutcome:
    id: str
    target_path: str
    classification: str  # "caught" | "equivalent" | "surviving"
    rationale: str


@dataclass(frozen=True)
class MutationResult:
    status: str  # "EVALUATED" | "BASELINE_FAILED" | "UNAVAILABLE"
    source: str  # "tool" | "manual" | "none"
    baseline: GateResult | None
    tool_result: GateResult | None
    mutants: tuple[MutantOutcome, ...]
    follow_up: str | None  # the one-line suggestion when UNAVAILABLE


_MUTATION_FOLLOW_UP = (
    "no configured mutation tool and no bounded manual mutations were available "
    "for this change; consider adding mutation coverage in a follow-up"
)


def _validate_mutation_plan(plan: MutationPlan) -> None:
    if not isinstance(plan, MutationPlan):
        raise MutationPlanError("plan must be a MutationPlan")
    if plan.tool_argv is None and not plan.manual_mutations:
        return
    if plan.baseline_argv is None:
        raise MutationPlanError("a baseline command is required whenever mutation is attempted")
    validate_gate_argv(plan.baseline_argv)
    if plan.tool_argv is not None:
        validate_gate_argv(plan.tool_argv)
    seen: set[str] = set()
    for mutation in plan.manual_mutations:
        if not isinstance(mutation, ManualMutation):
            raise MutationPlanError("manual_mutations must contain ManualMutation entries")
        if not mutation.id or mutation.id in seen:
            raise MutationPlanError(f"manual mutation id must be unique and non-empty: {mutation.id!r}")
        seen.add(mutation.id)
        path = mutation.target_path
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in Path(path).parts:
            raise MutationPlanError(f"manual mutation target_path escapes the disposable copy: {path!r}")


def run_mutation_evidence(
    plan: MutationPlan,
    disposable_copy: Path,
    *,
    call_root: Path | None = None,
    host: GateHostPaths | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    timeout: float = GATE_TIMEOUT_SECONDS,
) -> MutationResult:
    """Opportunistic, always-supporting mutation evidence.

    Every command -- the baseline run, a configured tool, or a manual
    mutant's rerun -- executes against ``disposable_copy`` through the same
    no-credential/no-network gate containment ``execute_gate`` already
    enforces for baseline gates; this function never receives or references
    the sealed target's root, so it cannot mutate it. A failing baseline
    invalidates the whole run (design: "the unmutated targeted test must
    pass") -- caught/surviving counts from a broken baseline would be
    meaningless, so none are computed. Mutation evidence is never terminal:
    this never raises for a surviving mutant and computes no score.
    """
    _validate_mutation_plan(plan)
    disposable_copy = Path(disposable_copy)
    if plan.tool_argv is None and not plan.manual_mutations:
        return MutationResult(
            status="UNAVAILABLE", source="none", baseline=None, tool_result=None,
            mutants=(), follow_up=plan.unavailable_reason or _MUTATION_FOLLOW_UP,
        )

    resolved_host = host or resolve_gate_host_paths()
    calls = Path(call_root) if call_root is not None else disposable_copy.parent / f"{disposable_copy.name}.calls"

    def _dispatch(label: str, argv: tuple[str, ...]) -> GateResult:
        seal = seal_target(disposable_copy, GitPolicy(enabled=False))
        mapping = build_gate_mapping(resolved_host, seal, calls / label)
        gate = Gate(
            id=label, argv=tuple(argv), applicability="applicable", classification="supporting",
            rationale="mutation evidence", provenance="operator",
        )
        return execute_gate(gate, mapping, seal, host=resolved_host, run=run, timeout=timeout)

    source = "tool" if plan.tool_argv is not None else "manual"
    baseline = _dispatch("mutation-baseline", plan.baseline_argv)
    if baseline.status != "PASSED":
        return MutationResult(
            status="BASELINE_FAILED", source=source, baseline=baseline, tool_result=None,
            mutants=(), follow_up=None,
        )

    if plan.tool_argv is not None:
        tool_result = _dispatch("mutation-tool", plan.tool_argv)
        return MutationResult(
            status="EVALUATED", source="tool", baseline=baseline, tool_result=tool_result,
            mutants=(), follow_up=None,
        )

    mutants: list[MutantOutcome] = []
    for mutation in plan.manual_mutations:
        target = disposable_copy / mutation.target_path
        original_text = target.read_text()
        target.write_text(mutation.mutate(original_text))
        try:
            result = _dispatch(f"mutation-{mutation.id}", plan.baseline_argv)
        finally:
            target.write_text(original_text)
        if result.status == "FAILED":
            classification = "caught"
        elif mutation.equivalence_claim:
            classification = "equivalent"
        else:
            classification = "surviving"
        mutants.append(MutantOutcome(
            id=mutation.id, target_path=mutation.target_path,
            classification=classification, rationale=mutation.rationale,
        ))

    return MutationResult(
        status="EVALUATED", source="manual", baseline=baseline, tool_result=None,
        mutants=tuple(mutants), follow_up=None,
    )


def default_gate_dispatcher(
    run_root: Path,
    seal: TargetSeal,
    host: GateHostPaths | None = None,
    inputs_ro: Sequence[Path] = (),
) -> Callable[[Gate], GateResult]:
    """One fresh containment mapping (fresh scratch) per gate, real bwrap."""
    resolved_host = host or resolve_gate_host_paths()

    def _dispatch(gate: Gate) -> GateResult:
        call_dir = Path(run_root) / "calls" / f"gate-{gate.id}"
        mapping = build_gate_mapping(resolved_host, seal, call_dir, inputs_ro)
        return execute_gate(gate, mapping, seal, host=resolved_host)

    return _dispatch
