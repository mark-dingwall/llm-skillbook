"""Contract: the TRIAGE role projection is exactly what the ledger kernel
accepts to initialize unsettled OPEN rows, and malformed triage is rejected
before any ledger state exists.

The valid fixture is validated through the REAL ``validate_role_json`` and then
initialized through the REAL ``apply_ledger_decisions`` (as the controller does)
to prove: each source finding maps exactly once to a canonical ledger ID, the
immutable raw claim/severity/locators are preserved, and a CLEAN empty report
still passes through TRIAGE. Every invalid fixture -- missing/duplicate/foreign
report or finding IDs, an altered raw premise, an invalid factual/state pair, a
seal mismatch, or an omitted clean report -- is rejected.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from review_loop.artifacts import CanonicalStore, EvidenceArtifact, canonical_bytes
from review_loop.prompts import RoleExpectation, RoleValidationError, validate_role_json

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "triage-results"
TARGET_SEAL = "seal-A"
ROUND_SEAL = "seal-round-1"

# The immutable raw-report premises the usable round-1 reviewers actually
# emitted; TRIAGE may not alter them. rep-3 is a CLEAN (empty) report that must
# still be enumerated.
RAW_FINDINGS = {
    "rep-1": {
        "f1": ("Missing null check", "Important", ["a.py:10"]),
        "f2": ("Unused import", "Minor", ["b.py:1"]),
    },
    "rep-2": {"g1": ("Race condition", "Critical", ["c.py:5", "c.py:9"])},
    "rep-3": {},
}


def _expectation():
    return RoleExpectation(
        request_id="tri-1", role_id="triage", target_seal=TARGET_SEAL,
        round_input_seal=ROUND_SEAL, expected_ids=("rep-1", "rep-2", "rep-3"),
        extra={"raw_findings": RAW_FINDINGS},
    )


def _validate(fixture_name):
    body = (FIXTURES / fixture_name).read_bytes()
    return validate_role_json("triage", body, _expectation())


class TriageProjectionContractTests(unittest.TestCase):
    def test_valid_reconciliation_maps_each_finding_once_preserving_premises(self):
        result = _validate("valid-reconciliation.json")
        rows = result.projection["rows"]
        self.assertEqual([r["id"] for r in rows], ["LEDGER-1", "LEDGER-2", "LEDGER-3"])
        # each source finding maps exactly once to a canonical ledger ID
        self.assertEqual(rows[0]["source_ids"], ["rep-1:f1"])
        self.assertEqual(rows[2]["source_ids"], ["rep-2:g1"])
        # immutable raw premise preserved: reported_severity == the raw severity
        self.assertEqual(rows[0]["reported_severity"], "Important")
        self.assertEqual(rows[2]["reported_severity"], "Critical")
        all_sources = [s for f in result.artifact["findings"] for s in f["sources"]]
        self.assertEqual({(s["report_id"], s["finding_id"]) for s in all_sources},
                         {("rep-1", "f1"), ("rep-1", "f2"), ("rep-2", "g1")})

    def test_valid_projection_initializes_open_rows_through_the_kernel(self):
        result = _validate("valid-reconciliation.json")
        rows = result.projection["rows"]
        with tempfile.TemporaryDirectory() as tmp:
            store = CanonicalStore(Path(tmp) / "run")
            store.initialize(TARGET_SEAL, {})
            initial_rows = [{**r, "proof_artifact_ids": [], "manifest_artifact_id": None} for r in rows]
            decisions = [
                {"id": r["id"], "state": "OPEN", "proof_artifact_ids": [], "manifest_artifact_id": None}
                for r in rows
            ]
            projection = {
                "target_seal": TARGET_SEAL, "initial_rows": initial_rows, "decisions": decisions,
                "manifests": [], "adjudication": None,
            }
            evidence = (EvidenceArtifact("tri-1", "triage-result", 1, TARGET_SEAL, canonical_bytes(result.artifact)),)
            updated = store.issue_transition(
                operation="apply_ledger_decisions", evidence=evidence, projection=projection,
            )
        ledger = updated["processor_state"]["apply_ledger_decisions"]
        self.assertEqual([r["state"] for r in ledger["rows"]], ["OPEN", "OPEN", "OPEN"])
        self.assertEqual(ledger["pending_fix_ids"], ["LEDGER-1", "LEDGER-2", "LEDGER-3"])
        self.assertEqual(ledger["rows"][0]["reported_severity"], "Important")

    def test_clean_empty_report_still_passes_through_triage(self):
        # Every report is enumerated but has no findings: TRIAGE runs and yields
        # zero rows (a clean report is not skipped).
        clean = {rid: {} for rid in ("rep-1", "rep-2", "rep-3")}
        expectation = RoleExpectation(
            request_id="tri-1", role_id="triage", target_seal=TARGET_SEAL, round_input_seal=ROUND_SEAL,
            expected_ids=("rep-1", "rep-2", "rep-3"), extra={"raw_findings": clean},
        )
        body = json.dumps({
            "request_id": "tri-1", "role_id": "triage", "target_seal": TARGET_SEAL,
            "round_input_seal": ROUND_SEAL, "payload": {"report_ids": ["rep-1", "rep-2", "rep-3"], "findings": []},
        }).encode("utf-8")
        result = validate_role_json("triage", body, expectation)
        self.assertEqual(result.projection["rows"], [])

    def test_every_invalid_fixture_is_rejected(self):
        invalid = sorted(p.name for p in FIXTURES.glob("invalid-*.json"))
        self.assertGreaterEqual(len(invalid), 11)
        for name in invalid:
            with self.subTest(fixture=name), self.assertRaises(RoleValidationError):
                _validate(name)


if __name__ == "__main__":
    unittest.main()
