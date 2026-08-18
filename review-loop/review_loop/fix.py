"""The sole authorized mutation window: FIX containment, candidate validation,
FIX_APPLIED recording, and per-round sealed reviewer/triage/adjudication scopes.

Unlike an evidence GATE child (evidence.py: no credential, no network), the FIX
child is an LLM implementer that WRITES code, so it needs the tested provider
control channel to run. ``build_fix_call`` is therefore a WRITE-ENABLED variant
of the ordinary provider mapping (execution.build_codex_call): auth.json mounted
and provider network ON, but ``/subject`` bound READ-WRITE to a DISPOSABLE COPY
of the target rather than the per-entry read-only sealed target. Its FIX
prohibitions -- no product/production credentials, no dependency/lockfile/tooling
install, no commit/stage/deploy, no agent network beyond the provider channel --
are enforced by ``FixController.validate_candidate`` against the canonical delta,
never trusted from prompt compliance.

This module records FIX_APPLIED against the run's anchor governing seal with the
verified delta + manifest retained as canonical evidence, and (Task 9 Slice 2)
provides ``write_back`` -- wired into ``Controller.promote_post_fix_baseline`` --
to replay a verified single-round FIX from its disposable copy onto the REAL
target. Seal ADVANCEMENT across rounds (promoting a verified post-FIX identity
to the NEXT round's governing baseline) is a different thing -- it needs a
canonical seal-advancement surface in artifacts.py/state.py and stays deferred
(progress.md: recovery + seal-drift); the governing seal is a fixed anchor for
the whole run either way.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .artifacts import CanonicalStore, EvidenceArtifact, digest
from .execution import CodexHostPaths, _CODEX_EXEC_FLAGS
from .prompts import ValidatedRoleArtifact
from .seals import DeltaArtifact, TargetSeal, apply_delta_to_target, materialize_delta


class FixError(Exception):
    """A FIX candidate cannot be authorized, contained, or applied; fail closed."""


def _new_id() -> str:
    return uuid.uuid4().hex


# --- write-enabled provider containment (distinct from the gate mapping) ----


# Same as execution._CODEX_EXEC_FLAGS but the sandbox permits writes inside the
# workspace (/subject) -- the FIX child is an implementer, not a read-only
# reviewer. The outer Bubblewrap RW bind of the disposable copy is the real
# boundary; the codex sandbox flag is defense in depth.
_FIX_EXEC_FLAGS = tuple(
    "workspace-write" if flag == "read-only" else flag for flag in _CODEX_EXEC_FLAGS
)


@dataclass(frozen=True)
class FixExecutionMapping:
    """Declarative FIX containment: write-enabled provider mapping.

    ``target_rw`` is the disposable copy bound READ-WRITE at /subject -- the sole
    surface the implementer may mutate. ``network`` is always True and
    ``credentials`` always exactly the provider ``auth.json``: the FIX child
    needs the provider control channel to run, and nothing else.
    """

    target_rw: Path
    inputs_ro: tuple[Path, ...]
    runtime_ro: tuple[Path, ...]
    output_rw: Path
    scratch_rw: Path
    network: bool
    credentials: tuple[Path, ...]


def build_fix_call(
    *,
    prompt: str,
    host: CodexHostPaths,
    call_dir: Path,
    disposable_copy: Path,
    input_paths: Sequence[Path] = (),
    model: str | None = None,
) -> tuple[list[str], dict[str, str], FixExecutionMapping]:
    """Build the outer Bubblewrap argv for one FIX implementer call.

    Differs from ``execution.build_codex_call`` in exactly the ways FIX requires:
    ``/subject`` is a single ``--bind`` (READ-WRITE) of the disposable copy
    (never per-entry ``--ro-bind`` of the sealed target), and the sandbox flag is
    ``workspace-write``. It keeps the provider channel the ordinary mapping has
    (auth.json + resolv/nsswitch/CA + ``--unshare-net`` ABSENT) so the child can
    run; it does NOT reuse the no-cred/no-net gate mapping.
    """
    home_dir = call_dir / "home"
    scratch_dir = call_dir / "scratch"
    report_dir = call_dir / "report"
    for d in (home_dir, scratch_dir, report_dir):
        d.mkdir(parents=True, exist_ok=True)
    disposable_copy = Path(disposable_copy)

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

    # The one WRITE-enabled mount: the disposable copy at /subject.
    argv.extend(["--bind", str(disposable_copy), "/subject"])

    inputs_ro: list[Path] = []
    for i, raw in enumerate(input_paths):
        p = Path(raw)
        ro(p, f"/inputs/{i}/{p.name}")
        inputs_ro.append(p)

    argv.extend(["--chdir", "/subject"])
    env = {"HOME": "/home/reviewer", "CODEX_HOME": "/home/reviewer/.codex", "PATH": "/usr/bin", "LANG": "C.UTF-8"}
    for key, value in env.items():
        argv.extend(["--setenv", key, value])

    inner = [str(host.node), str(host.codex_entry), *_FIX_EXEC_FLAGS]
    if model:
        inner.extend(["--model", model])
    inner.append("-")
    argv.extend(inner)

    mapping = FixExecutionMapping(
        target_rw=disposable_copy,
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


# --- test-file classification for the Task-2 carry-forward ------------------


def is_test_path(path: str) -> bool:
    """Classify a changed path as a test file (Task-2 carry-forward (a)).

    A pure JSON validator cannot do this (it never sees the delta); FIX owns the
    canonical delta, so the "a changed test needs a spec trace" rule is enforced
    here. Conservative and convention-based: a ``tests``/``test`` path component,
    or a ``test_*``/``*_test`` Python basename.
    """
    parts = Path(path).parts
    if any(part in {"tests", "test"} for part in parts):
        return True
    name = Path(path).name
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


# Dependency manifests + lockfiles a FIX must never alter (design: "never alter
# dependency manifests or lockfiles" / "never install dependencies or initialize
# tooling"). A pure JSON validator can't see the delta; FIX owns it, so the
# rejection lives here. Conservative + fail-closed: a changed path with any of
# these basenames is rejected even when declared and bound to an authorized ID.
_DEPENDENCY_TOOLING_BASENAMES = frozenset({
    "poetry.lock", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock",
    "pnpm-lock.yaml", "pipfile.lock", "cargo.lock", "gemfile.lock", "composer.lock",
    "go.sum", "go.mod", "pyproject.toml", "setup.py", "setup.cfg", "pipfile",
    "package.json", "cargo.toml", "gemfile", "composer.json",
})


def is_dependency_or_tooling_path(path: str) -> bool:
    """A dependency manifest / lockfile a FIX may not alter (fail-closed)."""
    name = Path(path).name.lower()
    if name in _DEPENDENCY_TOOLING_BASENAMES:
        return True
    return name.startswith("requirements") and name.endswith(".txt")


# --- FIX request / validated candidate / applied transition -----------------


@dataclass(frozen=True)
class FixRequest:
    open_ids: tuple[str, ...]
    target_seal: str
    approved_gate_argvs: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ValidatedFix:
    request: FixRequest
    manifest: Mapping[str, object]
    bound_ids: tuple[str, ...]
    changed_paths: tuple[str, ...]
    delta: DeltaArtifact
    before_seal: str
    after_seal: str
    strategy: str  # "disposable_copy" | "direct_write"
    copy_root: Path | None = None  # the disposable-copy root ``write_back`` replays from


@dataclass(frozen=True)
class FixTransition:
    run_state: object  # controller.RunState after FIX_APPLIED
    validated: ValidatedFix
    applied_ids: tuple[str, ...]
    manifest_ids: Mapping[str, str]  # ledger id -> its per-finding manifest artifact id


class FixController:
    def __init__(self, run_state, work_dir: Path, *, new_id: Callable[[], str] = _new_id) -> None:
        self._run_state = run_state
        self._work_dir = Path(work_dir)
        self._new_id = new_id

    # -- prepare: authorize exactly the OPEN rows this window may resolve -----

    def prepare(self, open_rows: Sequence[Mapping[str, object]], target_seal: str, evidence_plan) -> FixRequest:
        open_ids: list[str] = []
        for row in open_rows:
            if row.get("state") != "OPEN":
                raise FixError(f"FIX may only be authorized for OPEN rows: {row.get('id')!r} is {row.get('state')!r}")
            ident = row.get("id")
            if not isinstance(ident, str) or not ident or ident in open_ids:
                raise FixError("open rows must have unique non-empty IDs")
            open_ids.append(ident)
        if not open_ids:
            raise FixError("FIX requires at least one authorized OPEN row")
        if not isinstance(target_seal, str) or not target_seal:
            raise FixError("FIX requires the verified target-baseline seal")
        argvs = tuple(
            tuple(gate.argv) for gate in getattr(evidence_plan, "gates", ()) if gate.applicability == "applicable"
        )
        return FixRequest(open_ids=tuple(open_ids), target_seal=target_seal, approved_gate_argvs=argvs)

    # -- validate_candidate: compare candidate target state + manifest -------

    def validate_candidate(
        self,
        request: FixRequest,
        before: TargetSeal,
        after: TargetSeal,
        manifest: ValidatedRoleArtifact,
        *,
        strategy: str = "disposable_copy",
        copy_root: Path | None = None,
    ) -> ValidatedFix:
        """Reject a FIX candidate before ``apply`` records FIX_APPLIED.

        Enforces changed-path equality (declared == the actual verified delta),
        exact OPEN-ID authorization, no bound-index mutation, no external
        actions, and the test-to-spec trace whenever a changed path is a test.
        """
        if not isinstance(manifest, ValidatedRoleArtifact) or manifest.role_id != "fix":
            raise FixError("candidate manifest must be a validated 'fix' role artifact")
        art = manifest.artifact
        if art["external_actions_attempted"]:
            raise FixError(
                "FIX declared an external action beyond the provider channel: "
                f"{art['external_actions_note']!r}"
            )

        delta_path = self._work_dir / f"delta-{self._new_id()}.json"
        self._work_dir.mkdir(parents=True, exist_ok=True)
        delta = materialize_delta(before, after, delta_path)
        if delta.git_index_changed:
            raise FixError("FIX must not mutate the bound Git index")

        actual_paths = {e.path for e in delta.entries}
        # Reject a dependency/lockfile/tooling change even when declared+authorized:
        # net is ON and the copy is writable, so an install would land as an
        # accepted filesystem change otherwise (design: no dep/lockfile/tooling
        # mutation to obtain evidence).
        tooling = sorted(p for p in actual_paths if is_dependency_or_tooling_path(p))
        if tooling:
            raise FixError(f"FIX must not alter dependency/lockfile/tooling paths: {tooling}")
        declared_paths: set[str] = set()
        bound_ids: set[str] = set()
        for change in art["changes"]:
            path = change["path"]
            if path.startswith("/") or ".." in Path(path).parts:
                raise FixError(f"FIX changed path escapes the target: {path!r}")
            declared_paths.add(path)
            bound_ids |= set(change["ledger_ids"])
        if declared_paths != actual_paths:
            missing = actual_paths - declared_paths
            extra = declared_paths - actual_paths
            raise FixError(
                "FIX manifest does not equal the verified delta "
                f"(undeclared changes: {sorted(missing)}; declared-but-absent: {sorted(extra)})"
            )
        if not bound_ids <= set(request.open_ids):
            raise FixError(
                f"FIX bound unauthorized ledger IDs: {sorted(bound_ids - set(request.open_ids))}"
            )

        # Task-2 carry-forward (a): a changed TEST file requires a non-empty
        # spec trace binding it to spec IDs. The pure JSON validator cannot do
        # this; the delta classifies the path.
        traced = {t["test_path"]: t["spec_ids"] for t in art["test_trace"]}
        entries = {entry.path: entry for entry in delta.entries}
        for path in sorted(actual_paths):
            if is_test_path(path) and "file" in (entries[path].before_type, entries[path].after_type):
                if entries[path].change != "added":
                    raise FixError(f"FIX may add regression tests but must not modify or remove existing test {path!r}")
                spec_ids = traced.get(path)
                if not spec_ids:
                    raise FixError(
                        f"FIX changed test file {path!r} without a non-empty test-to-spec trace"
                    )

        return ValidatedFix(
            request=request,
            manifest=art,
            bound_ids=tuple(sorted(bound_ids)),
            changed_paths=tuple(sorted(actual_paths)),
            delta=delta,
            before_seal=before.digest,
            after_seal=after.digest,
            strategy=strategy,
            copy_root=copy_root,
        )

    # -- write_back: replay the verified delta onto the REAL target ----------

    def write_back(self, validated: ValidatedFix, target_root: Path) -> None:
        """Replay ``validated``'s already-verified delta onto the real target.

        Pure mechanics, called by ``Controller.promote_post_fix_baseline``
        (Task 9 Slice 2), sandwiched between its own before/after reseal
        checks. Fails closed if the candidate was never given a
        disposable-copy root to replay from, and re-derives the
        changed file paths from the delta as defense in depth: even though
        ``validate_candidate`` already proved ``changed_paths`` equals the
        verified delta, this re-checks it here rather than trusting a
        ``ValidatedFix`` handed in from elsewhere.
        """
        if validated.copy_root is None:
            raise FixError("write_back requires a validated candidate with a disposable-copy root")
        actual_paths = {e.path for e in validated.delta.entries}
        if actual_paths != set(validated.changed_paths):
            raise FixError(
                "write_back delta does not match the validated changed_paths "
                f"(delta: {sorted(actual_paths)}, changed_paths: {sorted(validated.changed_paths)})"
            )
        apply_delta_to_target(validated.delta, source_root=validated.copy_root, dest_root=target_root)

    # -- apply: record OPEN -> FIX_APPLIED for the bound IDs -----------------

    def apply(self, validated: ValidatedFix) -> FixTransition:
        from .controller import RunState, _artifact  # local import avoids a cycle

        run_state = self._run_state
        seal = run_state.governing_seal
        store = CanonicalStore(run_state.run_root)
        rows = run_state.snapshot["processor_state"]["apply_ledger_decisions"]["rows"]
        by_id = {r["id"]: r for r in rows}
        for row in rows:
            if row["state"] != "OPEN":
                raise FixError(
                    f"this task records FIX_APPLIED only over an all-OPEN ledger; "
                    f"row {row['id']!r} is {row['state']!r} (round-N reconcile is Task 9)"
                )

        manifest_ids: dict[str, str] = {}
        manifests: list[dict[str, object]] = []
        decisions: list[dict[str, object]] = []
        evidence: list[EvidenceArtifact] = [
            _artifact(self._new_id(), "fix-delta", seal, {
                "before_seal": validated.before_seal,
                "after_seal": validated.after_seal,
                "changed_paths": list(validated.changed_paths),
                "strategy": validated.strategy,
                "delta_digest": validated.delta.digest,
            })
        ]
        for ident, row in by_id.items():
            if ident in validated.bound_ids:
                mid = self._new_id()
                manifest_ids[ident] = mid
                manifests.append({"id": mid, "finding_id": ident})
                evidence.append(_artifact(mid, "fix-manifest", seal, dict(validated.manifest)))
                decisions.append({
                    "id": ident, "state": "FIX_APPLIED",
                    "proof_artifact_ids": [], "manifest_artifact_id": mid,
                })
            else:
                decisions.append({
                    "id": ident, "state": "OPEN",
                    "proof_artifact_ids": [], "manifest_artifact_id": None,
                })

        projection = {
            "target_seal": seal, "decisions": decisions,
            "manifests": manifests, "adjudication": None,
        }
        updated = store.issue_transition(
            operation="apply_ledger_decisions", evidence=tuple(evidence), projection=projection,
        )
        new_state = RunState(run_state.run_root, run_state.governing_seal, updated, "FIX", None)
        self._run_state = new_state
        return FixTransition(
            run_state=new_state, validated=validated,
            applied_ids=validated.bound_ids, manifest_ids=manifest_ids,
        )


# --- per-round four sealed boundaries ---------------------------------------


def _seal(name: str, inputs: Sequence[str]) -> str:
    return digest({"scope": name, "inputs": sorted(inputs)})


@dataclass(frozen=True)
class SealedScope:
    name: str
    inputs: tuple[str, ...]
    seal: str


@dataclass(frozen=True)
class ReviewerScope:
    role: str
    charter_id: str
    target_files: tuple[str, ...]
    review_data: tuple[str, ...]
    seal: str


@dataclass(frozen=True)
class RoundScopes:
    inventory_refresh: SealedScope
    reviewers: tuple[ReviewerScope, ...]
    triage: SealedScope
    adjudication: SealedScope


def build_round_scopes(round_state: Mapping[str, object], delta: DeltaArtifact, manifest: Mapping[str, object], inventory: Mapping[str, object]) -> RoundScopes:
    """Build the four distinct sealed boundaries for a later round.

    Ordering is structural: the inventory-refresh seal is built FIRST from prior
    mappings/coverage + the verified delta + manifest; every reviewer seal
    INCLUDES that refresh seal as an input, so a reviewer scope cannot be sealed
    before refresh. Later holistic/adversarial scopes are exactly the changed
    target files plus delta/patch/manifest/relevant-ledger/refreshed-inventory
    review data; each specialist adds exactly its current resolved owning files.
    """
    changed_files = tuple(sorted(e.path for e in delta.entries))
    manifest_paths = tuple(sorted(c["path"] for c in manifest.get("changes", [])))
    prior_mappings = [str(m) for m in round_state.get("prior_mapping_ids", ())]
    prior_coverage = [str(c) for c in round_state.get("prior_coverage_refs", ())]

    refresh_inputs = tuple(sorted(
        [f"mapping:{m}" for m in prior_mappings]
        + [f"coverage:{c}" for c in prior_coverage]
        + [f"delta:{delta.after_seal}"]
        + [f"manifest-path:{p}" for p in manifest_paths]
    ))
    inventory_refresh = SealedScope("inventory-refresh", refresh_inputs, _seal("inventory-refresh", refresh_inputs))

    optional_patch = [f"patch:{delta.after_seal}"] if round_state.get("content_patch") else []
    ledger_refs = [f"ledger:{i}" for i in round_state.get("relevant_ledger_ids", ())]
    inventory_ref = f"inventory:{inventory_refresh.seal}"
    base_review_data = tuple(
        [f"delta:{delta.after_seal}", *optional_patch, *[f"manifest:{p}" for p in manifest_paths], *ledger_refs, inventory_ref]
    )

    areas_by_id = {a["id"]: a for a in inventory.get("active_areas", [])}
    reviewers: list[ReviewerScope] = []
    for entry in round_state.get("roster", ()):
        role = entry["role"]
        if role == "specialist":
            area = areas_by_id[entry["area_id"]]
            target_files = tuple(sorted(set(changed_files) | set(area["owning_file_ids"])))
            charter_id = entry["area_id"]
        else:
            target_files = changed_files
            charter_id = role
        review_data = base_review_data
        seal = _seal(
            f"reviewer:{role}:{charter_id}",
            [f"target:{f}" for f in target_files]
            + [f"data:{d}" for d in review_data]
            + [f"refresh:{inventory_refresh.seal}"],
        )
        reviewers.append(ReviewerScope(role, charter_id, target_files, review_data, seal))

    triage_inputs = tuple(sorted(f"raw-report:{r}" for r in round_state.get("usable_report_ids", ())))
    triage = SealedScope("triage", triage_inputs, _seal("triage", triage_inputs))

    adjudication_inputs = tuple(sorted(
        [f"pending:{i}" for i in round_state.get("pending_adjudication_ids", ())]
        + [f"authority:{k}:{v}" for k, v in round_state.get("authority_kinds", {}).items()]
    ))
    adjudication = SealedScope("adjudication", adjudication_inputs, _seal("adjudication", adjudication_inputs))

    return RoundScopes(inventory_refresh, tuple(reviewers), triage, adjudication)
