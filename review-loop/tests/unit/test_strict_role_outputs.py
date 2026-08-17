import unittest
from pathlib import Path

from review_loop.prompts import RoleExpectation, RoleValidationError, validate_role_json

ROLE_RESULTS = Path(__file__).parents[1] / "contract" / "fixtures" / "role-results"


def load(role_dir: str, name: str) -> bytes:
    return (ROLE_RESULTS / role_dir / name).read_bytes()


def expect(role_id, request_id, target_seal, round_input_seal=None, expected_ids=(), extra=None):
    return RoleExpectation(
        request_id=request_id,
        role_id=role_id,
        target_seal=target_seal,
        round_input_seal=round_input_seal,
        expected_ids=expected_ids,
        extra=extra or {},
    )


class EnvelopeCrossCheckTests(unittest.TestCase):
    def test_wrong_target_seal_is_rejected_before_payload_considered(self):
        body = load("evidence", "valid.json")
        expectation = expect("evidence", "ev-1", "seal-WRONG")
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", body, expectation)

    def test_wrong_request_id_is_rejected(self):
        body = load("evidence", "valid.json")
        expectation = expect("evidence", "wrong-req", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", body, expectation)

    def test_unknown_role_id_is_rejected(self):
        body = load("evidence", "valid.json")
        expectation = expect("evidence", "ev-1", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("no-such-role", body, expectation)


class EvidenceValidatorTests(unittest.TestCase):
    def expectation(self):
        return expect("evidence", "ev-1", "seal-A")

    def test_valid_gates_accepted(self):
        artifact = validate_role_json("evidence", load("evidence", "valid.json"), self.expectation())
        self.assertEqual(len(artifact.artifact["gates"]), 2)
        self.assertEqual(artifact.projection["gates"][0]["id"], "tests")

    def test_duplicate_gate_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", load("evidence", "invalid-duplicate-id.json"), self.expectation())

    def test_classification_mismatch_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", load("evidence", "invalid-classification-mismatch.json"), self.expectation())

    def test_empty_argv_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", load("evidence", "invalid-empty-argv.json"), self.expectation())

    def test_missing_field_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", load("evidence", "invalid-missing-field.json"), self.expectation())

    def test_unknown_field_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", load("evidence", "invalid-unknown-field.json"), self.expectation())

    def test_bad_applicability_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("evidence", load("evidence", "invalid-bad-applicability.json"), self.expectation())


class InventoryValidatorTests(unittest.TestCase):
    def initial_expectation(self):
        return expect("inventory-owner", "inv-1", "seal-A")

    def refresh_expectation(self):
        return expect("inventory-owner", "inv-2", "seal-B", "seal-round-2", expected_ids=("A1", "A2"))

    def revision_expectation(self):
        return expect("inventory-revision", "inv-3", "seal-A", expected_ids=("c1", "c2"))

    def test_valid_initial_inventory_accepted(self):
        artifact = validate_role_json("inventory-owner", load("inventory", "valid-initial.json"), self.initial_expectation())
        self.assertEqual(len(artifact.artifact["areas"]), 2)
        self.assertEqual(artifact.projection["current_areas"][0]["id"], "A1")

    def test_valid_refresh_accepted(self):
        artifact = validate_role_json("inventory-owner", load("inventory", "valid-refresh.json"), self.refresh_expectation())
        self.assertEqual(len(artifact.projection["mappings"]), 2)
        self.assertIn("A1", artifact.projection["invalidators"])

    def test_valid_revision_accepted(self):
        artifact = validate_role_json("inventory-revision", load("inventory", "valid-revision.json"), self.revision_expectation())
        self.assertEqual(len(artifact.artifact["resolutions"]), 2)

    def test_refresh_missing_mapping_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-refresh-missing-mapping.json"), self.refresh_expectation())

    def test_refresh_duplicate_mapping_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-refresh-duplicate-mapping.json"), self.refresh_expectation())

    def test_refresh_retired_with_active_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-refresh-retired-with-active-id.json"), self.refresh_expectation())

    def test_refresh_continuing_wrong_active_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-refresh-continuing-wrong-active.json"), self.refresh_expectation())

    def test_refresh_bad_invalidators_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-refresh-bad-invalidators.json"), self.refresh_expectation())

    def test_non_bijective_priority_order_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-non-bijective-priority.json"), self.initial_expectation())

    def test_duplicate_area_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-duplicate-area-id.json"), self.initial_expectation())

    def test_generalist_miss_without_evidence_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-owner", load("inventory", "invalid-generalist-miss-without-evidence.json"), self.initial_expectation())

    def test_revision_incomplete_resolutions_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-revision", load("inventory", "invalid-revision-incomplete.json"), self.revision_expectation())

    def test_revision_foreign_challenge_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-revision", load("inventory", "invalid-revision-foreign.json"), self.revision_expectation())


class InventoryChallengeValidatorTests(unittest.TestCase):
    def expectation(self):
        return expect("inventory-challenge", "ic-1", "seal-A")

    def test_uphold_accepted(self):
        artifact = validate_role_json("inventory-challenge", load("inventory-challenge", "valid-uphold.json"), self.expectation())
        self.assertEqual(artifact.artifact["verdict"], "UPHOLD")

    def test_challenge_accepted(self):
        expectation = expect("inventory-challenge", "ic-2", "seal-A")
        artifact = validate_role_json("inventory-challenge", load("inventory-challenge", "valid-challenge.json"), expectation)
        self.assertEqual(len(artifact.artifact["challenges"]), 2)

    def test_empty_challenges_rejected(self):
        expectation = expect("inventory-challenge", "ic-2", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-challenge", load("inventory-challenge", "invalid-empty-challenges.json"), expectation)

    def test_duplicate_challenge_id_rejected(self):
        expectation = expect("inventory-challenge", "ic-2", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-challenge", load("inventory-challenge", "invalid-duplicate-challenge-id.json"), expectation)

    def test_bad_category_rejected(self):
        expectation = expect("inventory-challenge", "ic-2", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-challenge", load("inventory-challenge", "invalid-bad-category.json"), expectation)

    def test_uphold_with_challenges_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("inventory-challenge", load("inventory-challenge", "invalid-uphold-with-challenges.json"), self.expectation())


class RatingValidatorTests(unittest.TestCase):
    def test_no_gestalt_accepted(self):
        expectation = expect("rating", "rate-1", "seal-A")
        artifact = validate_role_json("rating", load("rating", "valid-no-gestalt.json"), expectation)
        self.assertEqual(artifact.projection, {"complexity": "high", "risk": "med", "gestalt_step": False})

    def test_with_gestalt_accepted(self):
        expectation = expect("rating", "rate-2", "seal-A")
        artifact = validate_role_json("rating", load("rating", "valid-with-gestalt.json"), expectation)
        self.assertEqual(artifact.projection["gestalt_step"], True)

    def test_bad_tier_rejected(self):
        expectation = expect("rating", "rate-1", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("rating", load("rating", "invalid-bad-tier.json"), expectation)

    def test_missing_axis_evidence_rejected(self):
        expectation = expect("rating", "rate-1", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("rating", load("rating", "invalid-missing-axis-evidence.json"), expectation)

    def test_gestalt_too_few_factors_rejected(self):
        expectation = expect("rating", "rate-2", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("rating", load("rating", "invalid-gestalt-too-few-factors.json"), expectation)

    def test_gestalt_duplicate_factors_rejected(self):
        expectation = expect("rating", "rate-2", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("rating", load("rating", "invalid-gestalt-duplicate-factors.json"), expectation)

    def test_empty_evidence_rejected(self):
        expectation = expect("rating", "rate-1", "seal-A")
        with self.assertRaises(RoleValidationError):
            validate_role_json("rating", load("rating", "invalid-empty-evidence.json"), expectation)


class AdjudicationValidatorTests(unittest.TestCase):
    def expectation(self):
        return expect(
            "adjudication", "adj-1", "seal-A", "seal-round-1",
            expected_ids=("ROW-1", "ROW-2", "ROW-3"),
            extra={"adjudication_kinds": {"ROW-1": "file_authorized", "ROW-2": "evidence_based", "ROW-3": "evidence_based"}},
        )

    def test_valid_mixed_decisions_accepted(self):
        artifact = validate_role_json("adjudication", load("adjudication", "valid.json"), self.expectation())
        self.assertEqual(len(artifact.projection), 3)

    def test_missing_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-missing-id.json"), self.expectation())

    def test_duplicate_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-duplicate-id.json"), self.expectation())

    def test_foreign_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-foreign-id.json"), self.expectation())

    def test_bad_decision_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-bad-decision.json"), self.expectation())

    def test_uphold_missing_fact_linkage_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-uphold-missing-fact-linkage.json"), self.expectation())

    def test_file_authorized_missing_identity_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-file-authorized-missing-identity.json"), self.expectation())

    def test_evidence_based_with_identity_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-evidence-based-with-identity.json"), self.expectation())

    def test_missing_evidence_locator_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("adjudication", load("adjudication", "invalid-missing-evidence-locator.json"), self.expectation())


class FixValidatorTests(unittest.TestCase):
    def expectation(self):
        return expect("fix", "fix-1", "seal-B", "seal-round-1", expected_ids=("ROW-10", "ROW-11", "ROW-12"))

    def test_valid_with_changes_accepted(self):
        artifact = validate_role_json("fix", load("fix", "valid-with-changes.json"), self.expectation())
        self.assertEqual(artifact.projection["bound_ledger_ids"], ["ROW-10"])

    def test_valid_no_changes_accepted(self):
        expectation = expect("fix", "fix-2", "seal-B", "seal-round-1", expected_ids=("ROW-10", "ROW-11", "ROW-12"))
        artifact = validate_role_json("fix", load("fix", "valid-no-changes.json"), expectation)
        self.assertEqual(artifact.projection["bound_ledger_ids"], [])

    def test_empty_ledger_ids_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("fix", load("fix", "invalid-empty-ledger-ids.json"), self.expectation())

    def test_foreign_ledger_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("fix", load("fix", "invalid-foreign-ledger-id.json"), self.expectation())

    def test_duplicate_path_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("fix", load("fix", "invalid-duplicate-path.json"), self.expectation())

    def test_external_flag_without_note_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("fix", load("fix", "invalid-external-flag-without-note.json"), self.expectation())

    def test_test_trace_foreign_path_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("fix", load("fix", "invalid-test-trace-foreign-path.json"), self.expectation())


class FinalReadinessValidatorTests(unittest.TestCase):
    def expectation(self, request_id="fr-1"):
        return expect("final-readiness", request_id, "seal-C")

    def test_uphold_accepted(self):
        artifact = validate_role_json("final-readiness", load("final-readiness", "valid-uphold.json"), self.expectation())
        self.assertEqual(artifact.artifact["verdict"], "UPHOLD")

    def test_block_procedural_accepted(self):
        artifact = validate_role_json("final-readiness", load("final-readiness", "valid-block-procedural.json"), self.expectation("fr-2"))
        self.assertEqual(artifact.artifact["procedural_blocker"], "required gate 'tests' has no passing record for the final seal")

    def test_block_with_findings_accepted(self):
        artifact = validate_role_json("final-readiness", load("final-readiness", "valid-block-with-findings.json"), self.expectation("fr-3"))
        self.assertEqual(len(artifact.artifact["source_findings"]), 1)

    def test_block_missing_evidence_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("final-readiness", load("final-readiness", "invalid-block-missing-evidence.json"), self.expectation("fr-2"))

    def test_block_duplicate_finding_id_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("final-readiness", load("final-readiness", "invalid-block-duplicate-finding-id.json"), self.expectation("fr-3"))

    def test_uphold_with_extra_field_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("final-readiness", load("final-readiness", "invalid-uphold-with-extra-field.json"), self.expectation())

    def test_bad_severity_rejected(self):
        with self.assertRaises(RoleValidationError):
            validate_role_json("final-readiness", load("final-readiness", "invalid-bad-severity.json"), self.expectation("fr-3"))


if __name__ == "__main__":
    unittest.main()
