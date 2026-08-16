import copy
import unittest

from review_loop import process


def challenge_attempt(
    status="UPHOLD",
    *,
    seal="seal-final",
    material=False,
    reason=None,
    source_ids=None,
    failure_kind=None,
):
    return {
        "status": status,
        "target_seal": seal,
        "material": material,
        "reason": reason,
        "source_finding_ids": source_ids or [],
        "failure_kind": failure_kind,
    }


def challenge_request(attempts, current_seal="seal-final"):
    return {
        "schema_version": 1,
        "operation": "record_final_challenge",
        "input": {"current_seal": current_seal, "attempts": attempts},
    }


def raw_finding(severity="Important"):
    return {
        "report_id": "report-1",
        "finding_id": "raw-1",
        "claim": "claim",
        "severity": severity,
        "source_locators": ["src/file.py:1"],
    }


def ledger_row(state="FIX_VERIFIED", severity="Important", finding_id="F1"):
    source = raw_finding(severity)
    return {
        "id": finding_id,
        "reported_severity": severity,
        "current_severity": severity,
        "claim": source["claim"],
        "source_locators": source["source_locators"],
        "source_findings": [source],
        "factual": "CONFIRMED",
        "state": state,
        "evidence": ["src/file.py:1"],
        "history": [],
        "manifest_id": "M1" if state in {"FIX_APPLIED", "FIX_VERIFIED"} else None,
        "fix_evidence": [
            {"seal": "seal-final", "locator": "src/file.py:1", "result": "fixed"}
        ] if state == "FIX_VERIFIED" else [],
        "authority": "none",
        "authority_proof": None,
    }


def active_area(current=True, consequence="Important", generalist_miss=True):
    owning = ["src/area.py"]
    coverage = (
        {
            "status": "CURRENT",
            "report_id": "specialist-1",
            "seal": "seal-final",
            "owning_files": owning,
            "reviewed_files": owning,
        }
        if current
        else {"status": "STALE"}
    )
    return {
        "id": "area-1",
        "aliases": [],
        "consequence": consequence,
        "consequence_evidence": ["spec:1"],
        "generalist_miss": ["depth required"] if generalist_miss else [],
        "surfaces": owning,
        "surface_files": owning,
        "charter": "challenge area",
        "coverage": coverage,
    }


def green_challenge():
    return {
        "state": "UPHELD",
        "fresh": True,
        "target_seal": "seal-final",
        "source_finding_ids": [],
        "procedural_block": False,
        "reason": None,
        "retry_required": False,
    }


def green_gates():
    return {
        "gates": [],
        "evidence_gaps": ["no applicable evidence gates discovered"],
        "blocking_reasons": [],
        "review_may_start": True,
        "merge_readiness_eligible": True,
    }


def gate_result(*gates):
    response = process(
        {
            "schema_version": 1,
            "operation": "reconcile_gates",
            "input": {"target_seal": "seal-final", "gates": list(gates)},
        }
    )
    if not response["ok"]:
        raise AssertionError(response)
    return response["result"]


def gate_record(
    *,
    status="PASSED",
    classification="required",
    command="pytest",
    result="passed",
    reason=None,
):
    return {
        "id": "tests",
        "target_seal": "seal-final",
        "applicability": "applicable",
        "applicability_reason": "tests exist",
        "timing": "post_fix",
        "classification": classification,
        "status": status,
        "command": command,
        "result": result,
        "reason": reason,
    }


def terminal_input():
    return {
        "lifecycle": {
            "confirmation": "not_required",
            "deadline_expired": False,
            "round1_triage_complete": True,
            "scheduled_reports_usable": True,
            "raw_reports_reconciled": True,
            "any_indeterminate": False,
            "expected_final_seal": "seal-final",
            "actual_final_seal": "seal-final",
        },
        "ledger": [ledger_row()],
        "gates": green_gates(),
        "areas": [active_area()],
        "final_challenge": green_challenge(),
    }


def terminal_request(value):
    return {"schema_version": 1, "operation": "compute_terminal", "input": value}


class FinalChallengeTests(unittest.TestCase):
    def record(self, attempts, current_seal="seal-final"):
        response = process(challenge_request(attempts, current_seal))
        self.assertIs(response["ok"], True, response)
        return response["result"]

    def test_uphold_is_fresh_supporting_evidence(self) -> None:
        result = self.record([challenge_attempt()])
        self.assertEqual(result, green_challenge())

    def test_material_procedural_block_prevents_readiness(self) -> None:
        result = self.record(
            [challenge_attempt("BLOCK", material=True, reason="required work omitted")]
        )
        self.assertEqual(result["state"], "BLOCKED")
        self.assertIs(result["procedural_block"], True)

    def test_source_findings_require_supplemental_triage(self) -> None:
        result = self.record(
            [
                challenge_attempt(
                    "BLOCK", material=True, reason="target defect", source_ids=["final-raw-1"]
                )
            ]
        )
        self.assertEqual(result["state"], "NEEDS_TRIAGE")
        self.assertEqual(result["source_finding_ids"], ["final-raw-1"])

    def test_one_failed_call_requests_retry_and_two_failures_are_indeterminate(self) -> None:
        failed = challenge_attempt(
            "FAILED", reason="bad output", failure_kind="malformed", seal="seal-final"
        )
        first = self.record([failed])
        second = self.record([failed, failed])
        self.assertEqual(first["state"], "RETRY_REQUIRED")
        self.assertIs(first["retry_required"], True)
        self.assertEqual(second["state"], "INDETERMINATE")

    def test_result_is_stale_when_bound_to_another_target_seal(self) -> None:
        result = self.record([challenge_attempt(seal="seal-old")])
        self.assertEqual(result["state"], "STALE")
        self.assertIs(result["fresh"], False)


class TerminalRollupTests(unittest.TestCase):
    def compute(self, value):
        response = process(terminal_request(value))
        self.assertIs(response["ok"], True, response)
        return response["result"]

    def test_all_conjuncts_produce_both_positive_verdicts_and_qualified_claim(self) -> None:
        result = self.compute(terminal_input())
        self.assertEqual(result["lifecycle_outcome"], "CONVERGED")
        self.assertEqual(result["terminal_verdict"], "CONVERGED")
        self.assertIs(result["merge_ready"], True)
        self.assertIs(result["qualified_claim_eligible"], True)
        self.assertEqual(result["failed_conditions"], [])

    def test_terminal_rejects_fix_verified_row_without_manifest_or_fix_evidence(self) -> None:
        for manifest_id, fix_evidence in (
            (None, []),
            ("", [{"seal": "seal-final", "locator": "src/file.py:1", "result": "fixed"}]),
        ):
            with self.subTest(manifest_id=manifest_id):
                value = terminal_input()
                value["ledger"][0]["manifest_id"] = manifest_id
                value["ledger"][0]["fix_evidence"] = fix_evidence
                response = process(terminal_request(value))
                self.assertIs(response["ok"], False)

    def test_terminal_rejects_forged_gate_rollup(self) -> None:
        value = terminal_input()
        value["gates"] = {
            "gates": [{
                "id": "tests",
                "target_seal": "seal-final",
                "applicability": "applicable",
                "applicability_reason": "tests exist",
                "timing": "post_fix",
                "classification": "required",
                "status": "FAILED",
                "command": "pytest",
                "result": "1 failed",
                "reason": None,
            }],
            "evidence_gaps": [],
            "blocking_reasons": [],
            "review_may_start": True,
            "merge_readiness_eligible": True,
        }
        response = process(terminal_request(value))
        self.assertIs(response["ok"], False)
        self.assertTrue(any(item["code"] == "consistency" for item in response["errors"]))

    def test_terminal_rejects_forged_upheld_challenge_with_source_findings(self) -> None:
        value = terminal_input()
        value["final_challenge"]["source_finding_ids"] = ["final-raw-1"]
        response = process(terminal_request(value))
        self.assertIs(response["ok"], False)
        self.assertTrue(any(item["code"] == "state" for item in response["errors"]))

    def test_terminal_rejects_refutation_without_retained_adjudication_proof(self) -> None:
        value = terminal_input()
        value["ledger"] = [ledger_row("REFUTED")]
        response = process(terminal_request(value))
        self.assertIs(response["ok"], False)
        self.assertTrue(any(item["code"] == "adjudication" for item in response["errors"]))

    def test_terminal_rejects_user_intentional_without_bound_acceptance(self) -> None:
        value = terminal_input()
        forged = ledger_row("INTENTIONAL")
        forged["authority"] = "user"
        forged["evidence"] = [
            {
                "kind": "adjudication",
                "seal": "seal-final",
                "fact": "unrelated independent fact",
                "linkage": "claims to resolve F1",
                "authority_identity": None,
            }
        ]
        value["ledger"] = [forged]
        response = process(terminal_request(value))
        self.assertIs(response["ok"], False)
        self.assertTrue(any(item["code"] == "authority" for item in response["errors"]))

    def test_each_convergence_prerequisite_is_reported_without_early_return(self) -> None:
        value = terminal_input()
        value["lifecycle"].update(
            {
                "confirmation": "awaiting",
                "round1_triage_complete": False,
                "scheduled_reports_usable": False,
                "raw_reports_reconciled": False,
                "any_indeterminate": True,
                "actual_final_seal": "drifted",
            }
        )
        value["ledger"] = [ledger_row("OPEN")]
        result = self.compute(value)
        self.assertEqual(result["terminal_verdict"], "NOT_CONVERGED")
        self.assertGreaterEqual(len(result["failed_conditions"]), 7)
        self.assertTrue(any("confirmation" in reason for reason in result["failed_conditions"]))
        self.assertTrue(any("Important+ row F1" in reason for reason in result["failed_conditions"]))

    def test_declined_confirmation_cancels_without_either_verdict(self) -> None:
        value = terminal_input()
        value["lifecycle"]["confirmation"] = "declined"
        result = self.compute(value)
        self.assertEqual(result["lifecycle_outcome"], "CANCELLED_BEFORE_REVIEW")
        self.assertIsNone(result["terminal_verdict"])
        self.assertIsNone(result["merge_ready"])
        self.assertIs(result["qualified_claim_eligible"], False)

    def test_deadline_expiry_while_awaiting_confirmation_overrides_cancellation(self) -> None:
        value = terminal_input()
        value["lifecycle"]["confirmation"] = "declined"
        value["lifecycle"]["deadline_expired"] = True
        result = self.compute(value)
        self.assertEqual(result["lifecycle_outcome"], "NOT_CONVERGED")
        self.assertEqual(result["terminal_verdict"], "NOT_CONVERGED")
        self.assertIs(result["merge_ready"], False)

    def test_merge_readiness_requires_fresh_uphold_gate_conditions_and_coverage(self) -> None:
        value = terminal_input()
        value["final_challenge"]["state"] = "BLOCKED"
        value["final_challenge"]["procedural_block"] = True
        value["final_challenge"]["reason"] = "material evidence gap"
        value["gates"] = gate_result(gate_record(status="FAILED", result="1 failed"))
        value["areas"] = [active_area(current=False)]
        result = self.compute(value)
        self.assertEqual(result["terminal_verdict"], "CONVERGED")
        self.assertIs(result["merge_ready"], False)
        self.assertTrue(any("final challenge" in reason for reason in result["failed_conditions"]))
        self.assertTrue(any("gate tests" in reason for reason in result["failed_conditions"]))
        self.assertTrue(any("coverage" in reason for reason in result["failed_conditions"]))

    def test_open_minor_and_unavailable_supporting_gate_are_disclosed_not_blocking(self) -> None:
        value = terminal_input()
        value["ledger"] = [ledger_row("OPEN", severity="Minor")]
        value["gates"] = gate_result(
            gate_record(
                status="NOT_RUN",
                classification="supporting",
                result=None,
                reason="tooling unavailable",
            )
        )
        result = self.compute(value)
        self.assertEqual(result["terminal_verdict"], "CONVERGED")
        self.assertIs(result["merge_ready"], True)
        self.assertIn("open Minor row F1", result["limitations"])
        self.assertIn("gate tests not run: tooling unavailable", result["limitations"])


if __name__ == "__main__":
    unittest.main()
