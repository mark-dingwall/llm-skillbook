"""Deterministic regression gate over the role resource files.

These tests never dispatch a model; they assert that the durable prose in
each `review_loop/resources/*.md` role file still declares the boundaries
Task 3's brief requires, and that it still names the field-level shape the
Task-2 validators in `prompts.py` actually accept. A model that follows a
role resource whose content these tests protect should produce output that
passes the matching `validate_role_json`/`validate_review_report` validator.
"""
import unittest
from pathlib import Path

RESOURCES = Path(__file__).parents[2] / "review_loop" / "resources"

NON_FIX_ROLE_FILES = [
    "evidence-discovery.md",
    "inventory.md",
    "inventory-challenge.md",
    "rating.md",
    "triage.md",
    "adjudication.md",
    "holistic.md",
    "adversarial.md",
    "specialist.md",
    "final-readiness.md",
]


def _read(name: str) -> str:
    return (RESOURCES / name).read_text(encoding="utf-8")


class NonFixRoleBoundaryTests(unittest.TestCase):
    """Every non-FIX target-accessing role must declare the same boundary."""

    def test_every_non_fix_role_file_exists(self):
        for name in NON_FIX_ROLE_FILES:
            with self.subTest(role=name):
                self.assertTrue((RESOURCES / name).is_file())

    def test_every_non_fix_role_declares_the_untrusted_data_boundary(self):
        for name in NON_FIX_ROLE_FILES:
            with self.subTest(role=name):
                text = _read(name)
                self.assertIn("untrusted data", text)
                self.assertIn("do not modify, execute", text)

    def test_every_non_fix_role_declares_report_never_fix(self):
        for name in NON_FIX_ROLE_FILES:
            with self.subTest(role=name):
                self.assertIn("REPORT, NEVER FIX", _read(name))

    def test_every_non_fix_role_declares_non_delegation(self):
        for name in NON_FIX_ROLE_FILES:
            with self.subTest(role=name):
                self.assertIn("delegate", _read(name).lower())


class RoleFieldContractTests(unittest.TestCase):
    """Each strict-JSON role file names the exact fields its Task-2 validator
    checks in prompts.py, so a resource edit that drifts from the validator
    is caught here rather than at first live dispatch."""

    def test_evidence_discovery_matches_validate_evidence(self):
        text = _read("evidence-discovery.md")
        for token in ("evidence", "gates", "evidence_gaps", "argv", "applicability",
                      "classification", "rationale", "required", "supporting", "tests"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_inventory_matches_validate_inventory_owner_and_revision(self):
        text = _read("inventory.md")
        for token in ("inventory-owner", "inventory-revision", "areas", "priority_order",
                      "mappings", "resolutions", "consequence", "generalist_miss",
                      "generalist_miss_evidence", "surfaces", "owning_file_ids", "charter",
                      "continuing", "successor", "retired", "retirement_reason",
                      "invalidators", "surface_changed", "dependency_changed",
                      "contract_changed", "finding_reopened", "identity_changed",
                      "new_depth_evidence"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_inventory_challenge_matches_validate_inventory_challenge(self):
        text = _read("inventory-challenge.md")
        for token in ("inventory-challenge", "UPHOLD", "CHALLENGE", "challenges", "category",
                      "omission", "unsupported_claim", "fragmentation", "unusable_charter",
                      "statement", "evidence"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_rating_matches_validate_rating(self):
        text = _read("rating.md")
        for token in ("rating", "complexity", "risk", "evidence", "gestalt", "factors",
                      "low", "med", "high", "max"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_triage_matches_validate_triage(self):
        text = _read("triage.md")
        for token in ("triage", "report_ids", "findings", "canonical_id", "sources",
                       "report_id", "finding_id", "claim", "severity", "locators",
                       "current_severity", "factual", "state", "evidence_locators",
                       "UNVERIFIABLE", "OPEN"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_adjudication_matches_validate_adjudication(self):
        text = _read("adjudication.md")
        for token in ("adjudication", "decisions", "UPHOLD", "BOUNCE", "UNDECIDED",
                      "evidence_locator", "fact_linkage", "authority_identity"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_final_readiness_matches_validate_final_readiness(self):
        text = _read("final-readiness.md")
        for token in ("final-readiness", "UPHOLD", "BLOCK", "evidence", "procedural_blocker",
                      "source_findings", "claim", "severity", "locator_ids"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_review_roles_declare_review_record_contract(self):
        for name, role in (("holistic.md", "holistic"), ("adversarial.md", "adversarial"),
                            ("specialist.md", "specialist")):
            with self.subTest(role=name):
                text = _read(name)
                self.assertIn("review-record", text)
                self.assertIn("REVIEW-STATUS", text)
                self.assertIn(f"`{role}`", text)


class FixRoleContractTests(unittest.TestCase):
    """FIX alone gets the mutation-window contract; it must not carry the
    read-only/report-only marker the other ten roles share."""

    def test_fix_declares_authorized_target_root(self):
        self.assertIn("AUTHORIZED TARGET ROOT", _read("fix.md"))

    def test_fix_declares_exact_open_ledger_id_placeholder(self):
        self.assertIn("{open_ledger_ids}", _read("fix.md"))

    def test_fix_prohibits_delegation(self):
        self.assertIn("delegate", _read("fix.md").lower())

    def test_fix_prohibits_installation(self):
        self.assertIn("never install", _read("fix.md").lower())

    def test_fix_prohibits_commit_stage_deploy(self):
        text = _read("fix.md").lower()
        for word in ("commit", "stage", "deploy"):
            with self.subTest(word=word):
                self.assertIn(word, text)

    def test_fix_prohibits_agent_initiated_network(self):
        self.assertIn("no agent-initiated network", _read("fix.md").lower())

    def test_fix_prohibits_production_credentials_beyond_control_channel(self):
        text = _read("fix.md").lower()
        self.assertIn("production credentials", text)
        self.assertIn("provider control channel", text)

    def test_fix_declares_manifest_output(self):
        self.assertIn("manifest", _read("fix.md").lower())

    def test_fix_matches_validate_fix_fields(self):
        text = _read("fix.md")
        for token in ("changes", "test_trace", "external_actions_attempted",
                      "external_actions_note", "path", "description", "ledger_ids",
                      "twin_search_pattern", "twin_search_count"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_fix_does_not_carry_the_report_never_fix_marker(self):
        self.assertNotIn("REPORT, NEVER FIX", _read("fix.md"))

    def test_fix_is_not_in_the_non_fix_role_set(self):
        self.assertNotIn("fix.md", NON_FIX_ROLE_FILES)


if __name__ == "__main__":
    unittest.main()
