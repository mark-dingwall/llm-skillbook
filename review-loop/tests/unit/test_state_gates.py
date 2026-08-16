import copy
import unittest

from review_loop import process


def gate(
    gate_id="tests",
    *,
    classification="required",
    status="PASSED",
    timing="baseline",
    applicability="applicable",
    target_seal="seal-1",
):
    executed = status in {"PASSED", "FAILED"}
    return {
        "id": gate_id,
        "target_seal": target_seal,
        "applicability": applicability,
        "applicability_reason": "relevant project test contract",
        "timing": timing,
        "classification": classification,
        "status": status,
        "command": "python3 -m unittest" if applicability == "applicable" else None,
        "result": f"exit {'0' if status == 'PASSED' else '1'}" if executed else None,
        "reason": "tooling unavailable" if status == "NOT_RUN" else None,
    }


def request(gates, target_seal="seal-1"):
    return {
        "schema_version": 1,
        "operation": "reconcile_gates",
        "input": {"target_seal": target_seal, "gates": gates},
    }


class GateOutcomeTests(unittest.TestCase):
    def reconcile(self, gates):
        response = process(request(gates))
        self.assertIs(response["ok"], True, response)
        return response["result"]

    def test_empty_discovery_is_disclosed_gap_not_failed_run(self) -> None:
        result = self.reconcile([])
        self.assertIs(result["review_may_start"], True)
        self.assertIs(result["merge_readiness_eligible"], True)
        self.assertEqual(result["blocking_reasons"], [])
        self.assertEqual(result["evidence_gaps"], ["no applicable evidence gates discovered"])

    def test_any_executed_applicable_failure_blocks_even_when_supporting(self) -> None:
        for classification in ("required", "supporting"):
            with self.subTest(classification=classification):
                result = self.reconcile(
                    [gate(classification=classification, status="FAILED")]
                )
                self.assertIs(result["review_may_start"], False)
                self.assertIs(result["merge_readiness_eligible"], False)
                self.assertEqual(result["blocking_reasons"], ["gate tests failed"])

    def test_required_gate_must_run_and_pass_for_merge_readiness(self) -> None:
        result = self.reconcile([gate(status="NOT_RUN")])
        self.assertIs(result["review_may_start"], True)
        self.assertIs(result["merge_readiness_eligible"], False)
        self.assertEqual(result["blocking_reasons"], ["required gate tests did not pass"])
        self.assertEqual(result["evidence_gaps"], ["gate tests not run: tooling unavailable"])

    def test_unavailable_supporting_gate_is_gap_but_not_independent_blocker(self) -> None:
        result = self.reconcile([gate(classification="supporting", status="NOT_RUN")])
        self.assertIs(result["review_may_start"], True)
        self.assertIs(result["merge_readiness_eligible"], True)
        self.assertEqual(result["blocking_reasons"], [])
        self.assertEqual(result["evidence_gaps"], ["gate tests not run: tooling unavailable"])

    def test_baseline_and_post_fix_records_remain_distinct_and_ordered(self) -> None:
        gates = [gate("baseline-tests"), gate("post-fix-tests", timing="post_fix")]
        result = self.reconcile(gates)
        self.assertEqual(result["gates"], gates)

    def test_non_applicable_opportunity_is_disclosed_not_executed(self) -> None:
        item = gate(
            "mutation",
            classification="supporting",
            status="NOT_RUN",
            applicability="not_applicable",
        )
        result = self.reconcile([item])
        self.assertIs(result["merge_readiness_eligible"], True)
        self.assertEqual(result["evidence_gaps"], ["gate mutation not applicable: tooling unavailable"])


class GateSchemaTests(unittest.TestCase):
    def test_rejects_gate_bound_to_another_seal(self) -> None:
        response = process(request([gate(target_seal="seal-other")]))
        self.assertIs(response["ok"], False)
        self.assertEqual(response["errors"][0]["path"], "$.input.gates[0].target_seal")

    def test_rejects_duplicate_gate_ids(self) -> None:
        response = process(request([gate(), gate(timing="post_fix")]))
        self.assertIs(response["ok"], False)
        self.assertIn(
            ("$.input.gates[1].id", "duplicate"),
            [(item["path"], item["code"]) for item in response["errors"]],
        )

    def test_rejects_missing_command_result_or_reason(self) -> None:
        missing_command = gate()
        missing_command["command"] = None
        missing_result = gate()
        missing_result["result"] = None
        missing_reason = gate(status="NOT_RUN")
        missing_reason["reason"] = None
        for item, field in (
            (missing_command, "command"),
            (missing_result, "result"),
            (missing_reason, "reason"),
        ):
            with self.subTest(field=field):
                response = process(request([item]))
                self.assertIs(response["ok"], False)
                self.assertIn(f".{field}", response["errors"][0]["path"])

    def test_rejects_non_applicable_gate_that_claims_execution(self) -> None:
        item = gate(applicability="not_applicable")
        response = process(request([item]))
        self.assertIs(response["ok"], False)
        paths = [issue["path"] for issue in response["errors"]]
        self.assertIn("$.input.gates[0].status", paths)

    def test_rejects_unknown_fields(self) -> None:
        item = copy.deepcopy(gate())
        item["safe"] = True
        response = process(request([item]))
        self.assertIs(response["ok"], False)
        self.assertIn(
            ("$.input.gates[0].safe", "unknown"),
            [(issue["path"], issue["code"]) for issue in response["errors"]],
        )


if __name__ == "__main__":
    unittest.main()
