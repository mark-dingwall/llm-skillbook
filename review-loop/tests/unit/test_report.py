"""Focused RED/GREEN coverage for report.py's narrative sections.

Both the whole-branch spec-compliance and code-quality reviews (Task 12
final review) independently flagged the same defect: report.py's "Seals"
and "Residual limitations" sections contained stale strings left over from
an earlier implementation state -- they contradicted what Controller.close()
and Controller.run_adjudication actually do (a genuine fresh re-seal
comparison; adjudication fully implemented and wired). generate_report is
pure formatting over a snapshot, so these are cheap, targeted unit tests
against hand-built snapshots rather than a full integration run.
"""
import unittest

from review_loop.controller import RunState
from review_loop.report import generate_report


def _terminal(**overrides):
    base = {
        "terminal_verdict": "CONVERGED", "merge_ready": True,
        "failed_conditions": [], "lifecycle_outcome": "CONVERGED",
        "qualified_claim_eligible": True,
    }
    base.update(overrides)
    return base


def _run_state(processor_state, stage="COMPLETE"):
    snapshot = {"governing_seal": "seal-x", "processor_state": processor_state}
    return RunState(run_root=None, governing_seal="seal-x", snapshot=snapshot, stage=stage, reason=None)


class SealsSectionTests(unittest.TestCase):
    def test_seal_match_is_described_as_a_real_comparison_not_as_unperformed(self):
        # RED (pre-fix report.py): this contained "no fresh re-seal was
        # performed (seal-drift check deferred to Task 9)" unconditionally --
        # false since Task 9 Slice 2, which made close() always reseal.
        report = generate_report(_run_state({"compute_terminal": _terminal()}))
        self.assertNotIn("no fresh re-seal", report)
        self.assertNotIn("deferred to Task 9", report)
        self.assertIn("CLOSE recomputed a fresh seal", report)
        self.assertIn("matched.", report)

    def test_seal_mismatch_is_disclosed_not_silently_matched(self):
        terminal = _terminal(terminal_verdict="NOT_CONVERGED", merge_ready=False, failed_conditions=["seal"])
        report = generate_report(_run_state({"compute_terminal": terminal}))
        self.assertIn("mismatch detected (NOT CONVERGED).", report)
        self.assertNotIn("matched.", report)

    def test_no_seal_comparison_line_before_close_has_run(self):
        report = generate_report(_run_state({}, stage="PREFLIGHT"))
        self.assertNotIn("CLOSE recomputed a fresh seal", report)


class ResidualLimitationsSectionTests(unittest.TestCase):
    def test_residual_section_does_not_claim_adjudication_is_unwired(self):
        # RED (pre-fix report.py): claimed the MVP "does not implement ...
        # adjudication in this task's controller wiring" -- false;
        # Controller.run_adjudication is implemented and wired (Task 8).
        report = generate_report(_run_state({}, stage="PREFLIGHT"))
        self.assertNotIn("or adjudication in this task's controller wiring", report)
        self.assertIn("Adjudication and single-round FIX", report)
        self.assertIn("implemented and wired", report)


if __name__ == "__main__":
    unittest.main()
