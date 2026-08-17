import json
import unittest
from pathlib import Path

from review_loop.prompts import (
    DispatchExpectation,
    ProcessCompletion,
    RoleExpectation,
    RoleValidationError,
    UnusableReview,
    ValidatedReview,
    validate_review_report,
    validate_role_json,
)

FIXTURES = Path(__file__).parents[1] / "contract" / "fixtures"
REPORTS = FIXTURES / "review-reports"
TRIAGE = FIXTURES / "triage-results"

DISPATCH = DispatchExpectation(
    request_id="req-100",
    role="holistic",
    charter_id="charter-1",
    target_seal="seal-A",
    round_input_seal=None,
    scope_locator_ids=("loc-1", "loc-2"),
)
COMPLETION = ProcessCompletion(
    request_id="req-100", exit_status=0, process_tree_terminated=True
)


def load(name: str) -> bytes:
    return (REPORTS / name).read_bytes()


class ReviewReportClassifierTests(unittest.TestCase):
    def test_valid_complete_report_is_usable(self):
        result = validate_review_report(load("valid-complete.md"), DISPATCH, COMPLETION)
        self.assertIsInstance(result, ValidatedReview)
        self.assertTrue(result.usable)
        self.assertEqual(result.terminal_status, "COMPLETE")
        self.assertEqual(len(result.record.source_findings), 1)

    def test_empty_findings_array_is_valid_and_usable(self):
        result = validate_review_report(load("valid-empty-findings.md"), DISPATCH, COMPLETION)
        self.assertIsInstance(result, ValidatedReview)
        self.assertTrue(result.usable)
        self.assertEqual(result.record.source_findings, ())

    def test_unable_report_parses_but_is_not_usable(self):
        result = validate_review_report(load("valid-unable.md"), DISPATCH, COMPLETION)
        self.assertIsInstance(result, ValidatedReview)
        self.assertEqual(result.terminal_status, "UNABLE")
        self.assertFalse(result.usable)

    def test_preamble_before_summary_heading_is_valid(self):
        result = validate_review_report(load("valid-complete.md"), DISPATCH, COMPLETION)
        self.assertIsInstance(result, ValidatedReview)

    def test_quoted_status_like_text_in_body_does_not_confuse_classifier(self):
        result = validate_review_report(
            load("valid-quoted-status-in-body.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, ValidatedReview)
        self.assertTrue(result.usable)

    def test_nonzero_process_completion_makes_report_unusable(self):
        failed = ProcessCompletion(
            request_id="req-100", exit_status=1, process_tree_terminated=True
        )
        result = validate_review_report(load("valid-complete.md"), DISPATCH, failed)
        self.assertIsInstance(result, ValidatedReview)
        self.assertFalse(result.usable)

    def test_mismatched_process_request_id_makes_report_unusable(self):
        mismatched = ProcessCompletion(
            request_id="other-req", exit_status=0, process_tree_terminated=True
        )
        result = validate_review_report(load("valid-complete.md"), DISPATCH, mismatched)
        self.assertIsInstance(result, ValidatedReview)
        self.assertFalse(result.usable)

    def test_unterminated_process_tree_makes_report_unusable(self):
        unterminated = ProcessCompletion(
            request_id="req-100", exit_status=0, process_tree_terminated=False
        )
        result = validate_review_report(load("valid-complete.md"), DISPATCH, unterminated)
        self.assertIsInstance(result, ValidatedReview)
        self.assertFalse(result.usable)

    def test_trailing_prose_after_status_is_rejected(self):
        result = validate_review_report(
            load("invalid-trailing-prose.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, UnusableReview)

    def test_duplicate_fence_is_rejected(self):
        result = validate_review_report(
            load("invalid-duplicate-fence.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, UnusableReview)

    def test_malformed_json_is_rejected(self):
        result = validate_review_report(
            load("invalid-malformed-json.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, UnusableReview)

    def test_mismatched_request_id_is_rejected(self):
        result = validate_review_report(
            load("invalid-mismatched-request-id.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, UnusableReview)

    def test_mismatched_scope_is_rejected(self):
        result = validate_review_report(
            load("invalid-mismatched-scope.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, UnusableReview)

    def test_duplicate_finding_ids_are_rejected(self):
        result = validate_review_report(
            load("invalid-duplicate-finding-ids.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, UnusableReview)

    def test_missing_terminal_line_is_rejected(self):
        result = validate_review_report(
            load("invalid-no-terminal-line.md"), DISPATCH, COMPLETION
        )
        self.assertIsInstance(result, UnusableReview)


# --- TRIAGE ------------------------------------------------------------

RAW_FINDINGS = {
    "rep-1": {
        "f1": ("Missing null check", "Important", ("a.py:10",)),
        "f2": ("Unused import", "Minor", ("b.py:1",)),
    },
    "rep-2": {
        "g1": ("Race condition", "Critical", ("c.py:5", "c.py:9")),
    },
    "rep-3": {},
}


def triage_expectation() -> RoleExpectation:
    return RoleExpectation(
        request_id="tri-1",
        role_id="triage",
        target_seal="seal-A",
        round_input_seal="seal-round-1",
        expected_ids=("rep-1", "rep-2", "rep-3"),
        extra={"raw_findings": RAW_FINDINGS},
    )


def load_triage(name: str) -> bytes:
    return (TRIAGE / name).read_bytes()


class TriageValidatorTests(unittest.TestCase):
    def test_valid_reconciliation_is_accepted(self):
        artifact = validate_role_json(
            "triage", load_triage("valid-reconciliation.json"), triage_expectation()
        )
        self.assertEqual(artifact.role_id, "triage")
        self.assertEqual(len(artifact.artifact["findings"]), 3)

    def test_missing_report_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-missing-report.json"), triage_expectation()
            )

    def test_duplicate_report_id_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-duplicate-report.json"), triage_expectation()
            )

    def test_foreign_report_id_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-foreign-report.json"), triage_expectation()
            )

    def test_altered_claim_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-altered-claim.json"), triage_expectation()
            )

    def test_altered_severity_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-altered-severity.json"), triage_expectation()
            )

    def test_missing_required_locator_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-missing-locator.json"), triage_expectation()
            )

    def test_omitted_empty_report_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-omitted-empty-report.json"), triage_expectation()
            )

    def test_invalid_factual_state_combination_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage",
                load_triage("invalid-factual-state-combination.json"),
                triage_expectation(),
            )

    def test_wrong_target_seal_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-wrong-target-seal.json"), triage_expectation()
            )

    def test_wrong_round_input_seal_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage", load_triage("invalid-wrong-round-seal.json"), triage_expectation()
            )

    def test_duplicate_canonical_id_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage",
                load_triage("invalid-duplicate-canonical-id.json"),
                triage_expectation(),
            )

    def test_duplicate_source_mapping_is_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json(
                "triage",
                load_triage("invalid-duplicate-source-mapping.json"),
                triage_expectation(),
            )


if __name__ == "__main__":
    unittest.main()
