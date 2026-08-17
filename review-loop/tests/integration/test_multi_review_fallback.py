"""Failure/fallback tests for the caller-contained multi-review holistic slot
(Task 11).

`MultiReviewAdapterFallbackTests` covers `MultiReviewAdapter.invoke()`'s
decision table (fallback vs `MultiReviewIndeterminate`) with a faked
subprocess (a Popen stand-in performing the filesystem side effects a real
sandboxed run would have left behind) -- no real Bubblewrap.
`ControllerHolisticFallbackTests` covers `Controller.run_round1`'s
integration of it end to end through the same CLEAN tracer harness
test_controller_clean.py uses, which DOES run one real gate under real
Bubblewrap (skipped when unavailable). See
tests/integration/test_multi_review_containment.py for the real-bwrap
multi-review mount/tampering proof.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from review_loop.controller import ControllerError
from review_loop.multi_review import (
    HolisticRequest,
    MultiReviewAdapter,
    MultiReviewError,
    MultiReviewHostPaths,
    MultiReviewIndeterminate,
    MultiReviewPolicy,
    MultiReviewResult,
    QualifiedReport,
)
from review_loop.prompts import DispatchExpectation, ProcessCompletion, ReviewRecord, SourceFinding, ValidatedReview
from review_loop.seals import GitPolicy, seal_target

from tests.unit.test_multi_review_adapter import _make_host


def _valid_record(request: HolisticRequest, cli: str, raw_id: str) -> dict:
    return {
        "request_id": request.request_id, "role": "holistic", "charter_id": "holistic",
        "target_seal": request.target_seal, "round_input_seal": request.round_input_seal,
        "scope_locator_ids": list(request.scope_locator_ids), "raw_report_id": raw_id,
        "terminal_status": "COMPLETE",
        "source_findings": [{"id": f"{cli}-f1", "claim": f"{cli} finding", "severity": "Minor", "locator_ids": ["foo.py:1"]}],
    }


def _section_body(record: dict) -> str:
    import json
    return (
        "## Summary\nlooks fine\n\n"
        "```review-record\n" + json.dumps({k: v for k, v in record.items() if k not in ("raw_report_id", "terminal_status")}) + "\n```\n"
        "REVIEW-STATUS: COMPLETE"
    )


def _write_review_md(
    out_dir: Path, request: HolisticRequest, *,
    reviewers_succeeded=("claude", "codex"),
    models: dict | None = None,
    tamper_claude_section: str | None = None,
    omit_record_for: str | None = None,
) -> None:
    records = {}
    for cli in ("claude", "codex"):
        if cli == omit_record_for:
            continue
        records[cli] = _valid_record(request, cli, request.raw_report_ids[cli])
    frontmatter = {
        "task": "custom",
        "reviewers_succeeded": list(reviewers_succeeded),
        "reviewers_failed": [c for c in ("claude", "codex") if c not in reviewers_succeeded],
        "models": models or {},
        "review_records": records,
    }
    lines = ["---", yaml.safe_dump(frontmatter, sort_keys=False).rstrip("\n"), "---", "", "# Cross-AI Review", ""]
    for cli in ("claude", "codex"):
        lines.append(f"## {cli.capitalize()} Review")
        lines.append("")
        if cli == "claude" and tamper_claude_section is not None:
            lines.append(tamper_claude_section)
        elif cli in records:
            lines.append(_section_body(records[cli]))
        else:
            lines.append(f"**Status:** failed — {cli} did not respond")
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## Consensus Summary")
    lines.append("")
    (out_dir / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


class _FakeProc:
    def __init__(self, exit_status: int, *, hang: bool = False, unterminable: bool = False):
        self.exit_status = exit_status
        self.hang = hang
        self.unterminable = unterminable
        self.stdin = _FakeStdin()
        self.pid = 4242
        self._terminated = False
        self._killed = False

    def wait(self, timeout=None):
        if self.hang and not self._terminated and not self._killed:
            import subprocess
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 0)
        if self.hang and self.unterminable:
            import subprocess
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 0)
        return self.exit_status

    def terminate(self):
        self._terminated = True

    def kill(self):
        self._killed = True


class _FakeStdin:
    def __init__(self):
        self.written = b""
        self.closed = False

    def write(self, data):
        self.written += data.encode() if isinstance(data, str) else data

    def close(self):
        self.closed = True


class _FakePopenFactory:
    """Records every invocation and lets each test script the resulting
    filesystem side effects + exit status per call, proving `invoke()` never
    launches a second sandboxed attempt on its own (no multi-review retry)."""

    def __init__(self, on_call):
        self.on_call = on_call
        self.calls = 0

    def __call__(self, argv, **kwargs):
        self.calls += 1
        return self.on_call(argv, self.calls)


class MultiReviewAdapterFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "target"
        self.target.mkdir()
        (self.target / "foo.py").write_text("x = 1\n")
        self.host = _make_host(self.root / "host")
        # a real uv-cache/python source so seed_* succeed by default
        (self.host.uv_cache_source / "seed").write_text("x")
        (self.host.uv_python_install_source / "cpython-3.11.0-linux").mkdir()
        (self.host.uv_python_install_source / "cpython-3.11.0-linux" / "bin").mkdir()
        (self.host.uv_python_install_source / "cpython-3.11.0-linux" / "bin" / "python3.11").write_text("x")
        self.run_root = self.root / "run"
        self.seal = seal_target(self.target, GitPolicy(enabled=False))
        self.request = HolisticRequest(
            call_id="call-1", request_id="req-1", target_seal=self.seal.digest, round_input_seal=None,
            scope_locator_ids=("target-root",), target_root=self.target, target_entries=self.seal.entries,
            run_root=self.run_root, raw_report_ids={"claude": "raw-c", "codex": "raw-x"},
        )
        self.call_dir = self.run_root / "multi-review-calls" / "call-1"
        self.out_dir = self.call_dir / "out"

    def _adapter(self, on_call, **kwargs) -> tuple[MultiReviewAdapter, _FakePopenFactory]:
        factory = _FakePopenFactory(on_call)
        adapter = MultiReviewAdapter(self.host, "fake-oauth-token", popen=factory, **kwargs)
        return adapter, factory

    # --- missing/unusable Bubblewrap -> fallback, never a hard failure ---

    def test_missing_bwrap_is_a_fallback_not_an_exception(self):
        broken = MultiReviewHostPaths(**{**self.host.__dict__, "bwrap": self.host.bwrap.parent / "nonexistent"})
        adapter = MultiReviewAdapter(broken, "tok")
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.reports)
        self.assertIn("bwrap", result.fallback_reason)

    # --- incomplete offline cache before reviewer launch -> fallback, never dispatched ---

    def test_incomplete_uv_cache_is_a_fallback_and_never_launches(self):
        empty_cache_host = MultiReviewHostPaths(
            **{**self.host.__dict__, "uv_cache_source": self.root / "empty-cache-src"}
        )
        (self.root / "empty-cache-src").mkdir()

        def on_call(argv, n):
            self.fail("the process must never launch when the offline cache is incomplete")

        adapter, factory = self._adapter(on_call)
        adapter._host = empty_cache_host
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.reports)
        self.assertIn("offline runtime seed incomplete", result.fallback_reason)
        self.assertEqual(factory.calls, 0)

    # --- target-intersecting runtime closure fails closed (not a fallback) ---

    def test_target_intersecting_closure_raises_not_falls_back(self):
        bad_host = MultiReviewHostPaths(**{**self.host.__dict__, "multi_review_root": self.target})
        adapter = MultiReviewAdapter(bad_host, "tok")
        with self.assertRaises(MultiReviewError):
            adapter.invoke(self.request, MultiReviewPolicy())

    # --- driver failure (nonzero exit) -> fallback ---

    def test_nonzero_driver_exit_is_a_fallback(self):
        def on_call(argv, n):
            return _FakeProc(exit_status=1)

        adapter, factory = self._adapter(on_call)
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.reports)
        self.assertIn("exited 1", result.fallback_reason)
        self.assertEqual(factory.calls, 1)

    # --- malformed / single-participant result -> fallback ---

    def test_single_participant_success_is_a_fallback_not_partial_credit(self):
        def on_call(argv, n):
            _write_review_md(self.out_dir, self.request, reviewers_succeeded=("claude",))
            return _FakeProc(exit_status=1)

        adapter, factory = self._adapter(on_call)
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.reports)

    def test_malformed_review_md_is_a_fallback(self):
        def on_call(argv, n):
            (self.out_dir / "REVIEW.md").write_text("not frontmatter at all")
            return _FakeProc(exit_status=0)

        adapter, factory = self._adapter(on_call)
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.reports)
        self.assertIn("frontmatter", result.fallback_reason)

    def test_missing_review_md_is_a_fallback(self):
        def on_call(argv, n):
            return _FakeProc(exit_status=0)

        adapter, factory = self._adapter(on_call)
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.reports)
        self.assertIn("REVIEW.md", result.fallback_reason)

    # --- pin rejection: reported model disagrees with the configured pin ---

    def test_reported_model_mismatch_against_pin_is_a_fallback(self):
        policy = MultiReviewPolicy(models={"claude": "opus", "codex": "gpt-codex"})

        def on_call(argv, n):
            _write_review_md(self.out_dir, self.request, models={"claude": "haiku", "codex": "gpt-codex"})
            return _FakeProc(exit_status=0)

        adapter, factory = self._adapter(on_call)
        result = adapter.invoke(self.request, policy)
        self.assertIsNone(result.reports)
        self.assertIn("does not match", result.fallback_reason)

    # --- deadline / process-tree termination ---

    def test_deadline_expiry_terminates_and_falls_back(self):
        def on_call(argv, n):
            return _FakeProc(exit_status=0, hang=True)

        adapter, factory = self._adapter(on_call, term_grace_seconds=0.05, kill_grace_seconds=0.05)
        policy = MultiReviewPolicy(deadline=datetime.now(timezone.utc) + timedelta(seconds=0))
        result = adapter.invoke(self.request, policy)
        self.assertIsNone(result.reports)
        self.assertIn("deadline", result.fallback_reason)

    def test_unterminable_process_tree_is_a_fallback_never_accepts_output(self):
        def on_call(argv, n):
            proc = _FakeProc(exit_status=0, hang=True, unterminable=True)
            return proc

        adapter, factory = self._adapter(on_call, term_grace_seconds=0.02, kill_grace_seconds=0.02)
        policy = MultiReviewPolicy(deadline=datetime.now(timezone.utc) + timedelta(seconds=0))
        result = adapter.invoke(self.request, policy)
        self.assertIsNone(result.reports)
        self.assertIn("did not terminate", result.fallback_reason)

    # --- pre/post driver-config (request.yaml) YAML drift -> fallback ---

    def test_request_yaml_drift_during_the_call_is_a_fallback(self):
        def on_call(argv, n):
            self.call_dir_written = True
            request_yaml = self.call_dir / "request.yaml"
            request_yaml.write_text(request_yaml.read_text() + "\n# tampered\n")
            _write_review_md(self.out_dir, self.request)
            return _FakeProc(exit_status=0)

        adapter, factory = self._adapter(on_call)
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.reports)
        self.assertIn("request.yaml drifted", result.fallback_reason)

    # --- pre/post target seal drift -> INDETERMINATE, never fallback ---

    def test_target_seal_drift_before_dispatch_is_indeterminate(self):
        (self.target / "extra.py").write_text("mutated before dispatch")

        def on_call(argv, n):
            self.fail("must never dispatch once a pre-existing seal mismatch is detected")

        adapter, factory = self._adapter(on_call)
        with self.assertRaises(MultiReviewIndeterminate):
            adapter.invoke(self.request, MultiReviewPolicy())
        self.assertEqual(factory.calls, 0)

    def test_target_seal_drift_during_the_call_is_indeterminate(self):
        def on_call(argv, n):
            (self.target / "mutated-during-call.py").write_text("surprise")
            _write_review_md(self.out_dir, self.request)
            return _FakeProc(exit_status=0)

        adapter, factory = self._adapter(on_call)
        with self.assertRaises(MultiReviewIndeterminate):
            adapter.invoke(self.request, MultiReviewPolicy())

    # --- no multi-review retry: exactly one launch attempt per invoke() ---

    def test_invoke_never_retries_the_sandboxed_call_itself(self):
        def on_call(argv, n):
            return _FakeProc(exit_status=1)  # always fails

        adapter, factory = self._adapter(on_call)
        adapter.invoke(self.request, MultiReviewPolicy())
        self.assertEqual(factory.calls, 1)

    # --- happy path: both qualified reports come back ---

    def test_successful_pair_yields_two_distinct_qualified_reports(self):
        def on_call(argv, n):
            _write_review_md(self.out_dir, self.request)
            return _FakeProc(exit_status=0)

        adapter, factory = self._adapter(on_call)
        result = adapter.invoke(self.request, MultiReviewPolicy())
        self.assertIsNone(result.fallback_reason)
        self.assertEqual(len(result.reports), 2)
        ids = {r.report_id for r in result.reports}
        self.assertEqual(ids, {"raw-c", "raw-x"})
        for r in result.reports:
            self.assertTrue(r.review.usable)
            self.assertEqual(r.review.record.role, "holistic")


from tests.integration.test_controller_clean import BWRAP_AVAILABLE, CleanTracerFixture


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class ControllerHolisticFallbackTests(CleanTracerFixture, unittest.TestCase):
    """`Controller.run_round1`'s real integration of the multi-review
    holistic slot, through the same end-to-end CLEAN tracer harness
    test_controller_clean.py uses (real Stage0 + gate execution; every
    reviewer/inventory/rating role stays a fake callable). Only `run_round1`
    itself is under test here."""

    def _run_to_round1_ready_stage0(self):
        run_state = self.controller.create_run(self.intent())
        return self.controller.run_stage0(
            run_state,
            scout=self.scout(),
            gate_dispatch=self.gate_dispatch(),
            inventory_owner=self.inventory_owner(),
            inventory_challenger=self.inventory_challenger(),
            explicit_tier="low",
            no_confirm=False,
        )

    def test_multi_review_success_appends_two_raw_reports_for_one_roster_entry(self):
        stage0 = self._run_to_round1_ready_stage0()

        def multi_review_dispatch(expectation: DispatchExpectation) -> MultiReviewResult:
            self.assertEqual(expectation.role, "holistic")
            reports = tuple(
                QualifiedReport(
                    report_id=f"raw-{cli}",
                    reviewer=cli,
                    review=ValidatedReview(
                        body=b"fake",
                        record=ReviewRecord(
                            request_id=expectation.request_id, role="holistic", charter_id="holistic",
                            target_seal=expectation.target_seal, round_input_seal=expectation.round_input_seal,
                            scope_locator_ids=expectation.scope_locator_ids,
                            source_findings=(SourceFinding(f"{cli}-f1", f"{cli} claim", "Minor", ("greet.py:1",)),),
                        ),
                        terminal_status="COMPLETE", usable=True,
                    ),
                )
                for cli in ("claude", "codex")
            )
            return MultiReviewResult(reports=reports, fallback_reason=None)

        round1 = self.controller.run_round1(
            stage0, dispatch_role=self.dispatch_role(), multi_review_dispatch=multi_review_dispatch,
        )
        self.assertEqual(round1.run_state.stage, "REVIEW")
        holistic_reports = [r for r in round1.raw_reports if r.role == "holistic"]
        self.assertEqual({r.report_id for r in holistic_reports}, {"raw-claude", "raw-codex"})
        self.assertEqual(len(round1.raw_reports), 3)  # holistic x2 + adversarial x1
        # dispatch_role was never called for holistic (only adversarial)
        self.assertNotIn("holistic", self.events)
        self.assertIn("adversarial", self.events)

    def test_fallback_dispatches_the_ordinary_path_with_the_same_expectation(self):
        stage0 = self._run_to_round1_ready_stage0()
        seen = []

        def multi_review_dispatch(expectation: DispatchExpectation) -> MultiReviewResult:
            seen.append(expectation)
            return MultiReviewResult(reports=None, fallback_reason="uv cache incomplete")

        round1 = self.controller.run_round1(
            stage0, dispatch_role=self.dispatch_role(), multi_review_dispatch=multi_review_dispatch,
        )
        self.assertEqual(round1.run_state.stage, "REVIEW")
        self.assertEqual(len(seen), 1)
        # the ordinary path was reached for holistic with the identical expectation
        self.assertEqual(self.events[-2:], ["holistic", "adversarial"])
        holistic_reports = [r for r in round1.raw_reports if r.role == "holistic"]
        self.assertEqual(len(holistic_reports), 1)
        self.assertEqual(holistic_reports[0].review.record.request_id, seen[0].request_id)

    def test_failed_fallback_raises_controllererror_never_dispatches_adversarial(self):
        stage0 = self._run_to_round1_ready_stage0()

        def multi_review_dispatch(expectation: DispatchExpectation) -> MultiReviewResult:
            return MultiReviewResult(reports=None, fallback_reason="driver exited 1")

        def bad_dispatch_role(expectation: DispatchExpectation):
            self.events.append(expectation.role)
            process = ProcessCompletion(request_id=expectation.request_id, exit_status=1, process_tree_terminated=True)
            return b"not a valid report at all", process

        with self.assertRaises(ControllerError):
            self.controller.run_round1(
                stage0, dispatch_role=bad_dispatch_role, multi_review_dispatch=multi_review_dispatch,
            )
        # the roster loop stops at the first unusable report -- adversarial,
        # ordered after holistic, is never reached.
        self.assertEqual(self.events[-1:], ["holistic"])

    def test_seal_drift_indeterminate_propagates_uncaught_out_of_run_round1(self):
        stage0 = self._run_to_round1_ready_stage0()

        def multi_review_dispatch(expectation: DispatchExpectation) -> MultiReviewResult:
            raise MultiReviewIndeterminate("target seal drifted during the sandboxed call")

        def dispatch_role_must_not_be_called(expectation):
            self.fail("a seal-drift MultiReviewIndeterminate must never fall through to the ordinary path")

        with self.assertRaises(MultiReviewIndeterminate):
            self.controller.run_round1(
                stage0, dispatch_role=dispatch_role_must_not_be_called, multi_review_dispatch=multi_review_dispatch,
            )


if __name__ == "__main__":
    unittest.main()
