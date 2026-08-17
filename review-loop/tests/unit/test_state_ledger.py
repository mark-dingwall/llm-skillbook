import copy
import unittest

from review_loop.state import process_test_fixture as process


def raw(finding_id="raw-1", severity="Important", report_id="report-1"):
    return {
        "report_id": report_id,
        "finding_id": finding_id,
        "claim": f"claim for {finding_id}",
        "severity": severity,
        "source_locators": [f"src/{finding_id}.py:1"],
    }


def fix_proof(seal="seal-2"):
    return {"seal": seal, "locator": "src/raw-1.py:1", "result": "failure no longer reproduces"}


def decision(
    canonical_id="F1",
    source_refs=None,
    *,
    severity="Important",
    factual="CONFIRMED",
    state="OPEN",
    authority="none",
    authority_proof=None,
    manifest_id=None,
    fix_evidence=None,
):
    return {
        "id": canonical_id,
        "source_refs": source_refs or ["report-1:raw-1"],
        "current_severity": severity,
        "factual": factual,
        "proposed_state": state,
        "evidence": ["src/evidence.py:2"],
        "authority": authority,
        "authority_proof": authority_proof,
        "manifest_id": manifest_id,
        "fix_evidence": fix_evidence or [],
    }


def row(
    state="OPEN",
    *,
    canonical_id="F1",
    reported="Important",
    current="Important",
    manifest_id=None,
    fix_evidence=None,
    authority="none",
    authority_proof=None,
):
    source = raw()
    evidence = ["src/evidence.py:2"]
    if state == "REFUTED":
        evidence.append(
            {
                "kind": "adjudication",
                "seal": "seal-1",
                "fact": "independent refutation fact",
                "linkage": "the fact resolves F1",
                "authority_identity": None,
            }
        )
    return {
        "id": canonical_id,
        "reported_severity": reported,
        "current_severity": current,
        "claim": source["claim"],
        "source_locators": source["source_locators"],
        "source_findings": [source],
        "factual": "CONFIRMED",
        "state": state,
        "evidence": evidence,
        "history": [],
        "manifest_id": manifest_id,
        "fix_evidence": fix_evidence or [],
        "authority": authority,
        "authority_proof": authority_proof,
    }


def request(
    rows,
    raw_findings,
    decisions,
    *,
    manifests=None,
    user_acceptances=None,
    adjudication=None,
    target_seal="seal-2",
):
    return {
        "schema_version": 1,
        "operation": "apply_ledger_decisions",
        "input": {
            "rows": rows,
            "raw_findings": raw_findings,
            "decisions": decisions,
            "manifests": manifests or [],
            "user_acceptances": user_acceptances or [],
            "adjudication": adjudication,
            "target_seal": target_seal,
        },
    }


def outcome(*items, status="clean"):
    return {"status": status, "decisions": list(items)}


def adjudication(
    ids,
    *,
    attempt=1,
    mode="full",
    settled=None,
    pending=None,
    call_outcome=None,
):
    return {
        "original_expected_ids": ids,
        "attempt_number": attempt,
        "retry_mode": mode,
        "settled_decisions": settled or [],
        "pending_ids": pending if pending is not None else ids,
        "outcome": call_outcome or outcome(status="failed"),
    }


def adjudication_decision(canonical_id, result, authority_identity=None):
    return {
        "id": canonical_id,
        "decision": result,
        "evidence": {
            "seal": "seal-2",
            "fact": f"independent fact for {canonical_id}",
            "linkage": f"the fact resolves {canonical_id}",
            "authority_identity": authority_identity,
        },
    }


class LedgerTransitionTests(unittest.TestCase):
    def apply(self, rows, raws, decisions, **kwargs):
        response = process(request(rows, raws, decisions, **kwargs))
        self.assertIs(response["ok"], True, response)
        return response["result"]

    def test_new_finding_enters_open_with_immutable_raw_provenance(self) -> None:
        source = raw()
        result = self.apply([], [source], [decision()])
        created = result["rows"][0]
        self.assertEqual(created["state"], "OPEN")
        self.assertEqual(created["reported_severity"], "Important")
        self.assertEqual(created["source_findings"], [source])

    def test_every_raw_finding_is_mapped_exactly_once(self) -> None:
        missing = process(request([], [raw()], []))
        duplicate = process(
            request([], [raw()], [decision("F1"), decision("F2")])
        )
        self.assertIs(missing["ok"], False)
        self.assertIs(duplicate["ok"], False)

    def test_reported_source_premise_cannot_be_rewritten(self) -> None:
        changed = raw()
        changed["claim"] = "changed reviewer claim"
        response = process(request([row()], [changed], [decision()]))
        self.assertIs(response["ok"], False)
        self.assertIn("source_findings", response["errors"][0]["path"])

    def test_open_to_fix_applied_requires_matching_manifest(self) -> None:
        proposed = decision(state="FIX_APPLIED", manifest_id="M1")
        missing = process(request([row()], [raw()], [proposed]))
        self.assertIs(missing["ok"], False)
        result = self.apply(
            [row()],
            [raw()],
            [proposed],
            manifests=[{"id": "M1", "finding_id": "F1"}],
        )
        self.assertEqual(result["rows"][0]["state"], "FIX_APPLIED")

    def test_fix_applied_to_verified_requires_manifest_and_sealed_fix_evidence(self) -> None:
        existing = row("FIX_APPLIED", manifest_id="M1")
        no_evidence = decision(state="FIX_VERIFIED", manifest_id="M1")
        rejected = process(
            request(
                [existing],
                [raw()],
                [no_evidence],
                manifests=[{"id": "M1", "finding_id": "F1"}],
            )
        )
        self.assertIs(rejected["ok"], False)
        verified = decision(
            state="FIX_VERIFIED",
            manifest_id="M1",
            fix_evidence=[fix_proof()],
        )
        result = self.apply(
            [existing],
            [raw()],
            [verified],
            manifests=[{"id": "M1", "finding_id": "F1"}],
        )
        self.assertEqual(result["rows"][0]["state"], "FIX_VERIFIED")
        stale = decision(
            state="FIX_VERIFIED",
            manifest_id="M1",
            fix_evidence=[fix_proof("seal-old")],
        )
        rejected_stale = process(
            request(
                [existing],
                [raw()],
                [stale],
                manifests=[{"id": "M1", "finding_id": "F1"}],
            )
        )
        self.assertIs(rejected_stale["ok"], False)

    def test_settled_row_can_reopen_with_new_evidence(self) -> None:
        existing = row("FIX_VERIFIED", manifest_id="M1", fix_evidence=[fix_proof("seal-1")])
        result = self.apply([existing], [raw()], [decision(state="OPEN")])
        reopened = result["rows"][0]
        self.assertEqual(reopened["state"], "OPEN")
        self.assertEqual(reopened["history"][0]["rejected_state"], "FIX_VERIFIED")

    def test_settled_row_cannot_jump_directly_to_another_settled_state(self) -> None:
        response = process(
            request([row("REFUTED")], [raw()], [decision(state="INTENTIONAL", authority="user")],
                    user_acceptances=[
                        {"finding_id": "F1", "quote": "accept F1", "round": 1, "time": "t1"}
                    ])
        )
        self.assertIs(response["ok"], False)
        self.assertTrue(any(item["code"] == "transition" for item in response["errors"]))

    def test_unverifiable_row_cannot_settle(self) -> None:
        response = process(
            request([], [raw()], [decision(factual="UNVERIFIABLE", state="REFUTED")])
        )
        self.assertIs(response["ok"], False)

    def test_ledger_bound_user_acceptance_is_direct_and_recorded(self) -> None:
        proposed = decision(state="INTENTIONAL", authority="user")
        acceptance = {"finding_id": "F1", "quote": "accept F1", "round": 1, "time": "t1"}
        result = self.apply([], [raw()], [proposed], user_acceptances=[acceptance])
        accepted = result["rows"][0]
        self.assertEqual(accepted["state"], "INTENTIONAL")
        self.assertIn(acceptance, accepted["evidence"])
        self.assertIsNone(result["next_adjudication"])

    def test_user_authority_without_ledger_bound_acceptance_is_rejected(self) -> None:
        proposed = decision(state="INTENTIONAL", authority="user")
        response = process(request([], [raw()], [proposed]))
        self.assertIs(response["ok"], False)
        self.assertIn("authority", response["errors"][0]["path"])

    def test_file_authority_requires_structured_sealed_linkage(self) -> None:
        missing = process(
            request([], [raw()], [decision(state="INTENTIONAL", authority="file")])
        )
        proof = {
            "locator": "spec.md:42",
            "identity": "sha256:spec-seal",
            "proposition": "the behavior is intentionally accepted",
            "linkage": "F1 is the behavior named by this clause",
        }
        proposed = decision(state="INTENTIONAL", authority="file", authority_proof=proof)
        first = process(request([], [raw()], [proposed]))
        self.assertIs(missing["ok"], False)
        self.assertIs(first["ok"], True, first)
        adjudicated = adjudication(
            ["F1"],
            call_outcome=outcome(
                adjudication_decision("F1", "UPHOLD", "sha256:spec-seal")
            ),
        )
        final = self.apply([], [raw()], [proposed], adjudication=adjudicated)
        self.assertEqual(final["rows"][0]["authority_proof"], proof)
        self.assertTrue(
            any(
                isinstance(item, dict) and item.get("kind") == "adjudication"
                for item in final["rows"][0]["evidence"]
            )
        )

    def test_adjudication_proof_is_structured_and_retained_for_refutation(self) -> None:
        malformed = adjudication(
            ["F1"],
            call_outcome=outcome(
                {"id": "F1", "decision": "UPHOLD", "evidence": "LGTM"}
            ),
        )
        self.assertIs(
            process(request([], [raw()], [decision(state="REFUTED")], adjudication=malformed))["ok"],
            False,
        )
        wrong_seal = adjudication_decision("F1", "UPHOLD")
        wrong_seal["evidence"]["seal"] = "seal-old"
        mismatched = adjudication(["F1"], call_outcome=outcome(wrong_seal))
        self.assertIs(
            process(request([], [raw()], [decision(state="REFUTED")], adjudication=mismatched))["ok"],
            False,
        )
        valid = adjudication(
            ["F1"], call_outcome=outcome(adjudication_decision("F1", "UPHOLD"))
        )
        result = self.apply([], [raw()], [decision(state="REFUTED")], adjudication=valid)
        proof = result["rows"][0]["evidence"][-1]
        self.assertEqual(proof["kind"], "adjudication")
        self.assertEqual(proof["seal"], "seal-2")

    def test_structured_user_acceptance_round_trips_as_canonical_state(self) -> None:
        proposed = decision(state="INTENTIONAL", authority="user")
        acceptance = {"finding_id": "F1", "quote": "accept F1", "round": 1, "time": "t1"}
        first = self.apply([], [raw()], [proposed], user_acceptances=[acceptance])
        second = process(
            request(
                first["rows"],
                [raw()],
                [proposed],
                user_acceptances=[acceptance],
            )
        )
        self.assertIs(second["ok"], True, second)


class AdjudicationAttemptTests(unittest.TestCase):
    def two_pending(self):
        raws = [raw("raw-1", report_id="report-1"), raw("raw-2", report_id="report-2")]
        decisions = [
            decision("F1", ["report-1:raw-1"], state="REFUTED"),
            decision("F2", ["report-2:raw-2"], state="REFUTED"),
        ]
        return raws, decisions

    def test_pending_green_decision_emits_full_first_attempt(self) -> None:
        result = process(request([], [raw()], [decision(state="REFUTED")]))["result"]
        self.assertEqual(result["rows"][0]["state"], "OPEN")
        self.assertEqual(
            result["next_adjudication"],
            {
                "original_expected_ids": ["F1"],
                "attempt_number": 1,
                "retry_mode": "full",
                "settled_decisions": [],
                "pending_ids": ["F1"],
            },
        )

    def test_failed_first_call_retries_the_full_set_without_applying_output(self) -> None:
        attempt = adjudication(["F1"], call_outcome=outcome(status="failed"))
        result = process(request([], [raw()], [decision(state="REFUTED")], adjudication=attempt))[
            "result"
        ]
        self.assertEqual(result["rows"][0]["state"], "OPEN")
        self.assertEqual(result["next_adjudication"]["attempt_number"], 2)
        self.assertEqual(result["next_adjudication"]["retry_mode"], "full")
        self.assertEqual(result["next_adjudication"]["pending_ids"], ["F1"])

    def test_clean_first_call_keeps_settled_and_retries_only_undecided_subset(self) -> None:
        raws, decisions = self.two_pending()
        call = outcome(
            adjudication_decision("F1", "UPHOLD"),
            adjudication_decision("F2", "UNDECIDED"),
        )
        attempt = adjudication(["F1", "F2"], call_outcome=call)
        result = process(request([], raws, decisions, adjudication=attempt))["result"]
        states = {item["id"]: item["state"] for item in result["rows"]}
        self.assertEqual(states, {"F1": "REFUTED", "F2": "OPEN"})
        retry = result["next_adjudication"]
        self.assertEqual(retry["retry_mode"], "undecided_subset")
        self.assertEqual(retry["pending_ids"], ["F2"])
        self.assertEqual(retry["settled_decisions"][0]["id"], "F1")

    def test_failed_second_subset_bounces_only_subset_and_keeps_first_settlement(self) -> None:
        raws, decisions = self.two_pending()
        settled = [adjudication_decision("F1", "UPHOLD")]
        attempt = adjudication(
            ["F1", "F2"],
            attempt=2,
            mode="undecided_subset",
            settled=settled,
            pending=["F2"],
            call_outcome=outcome(status="failed"),
        )
        result = process(request([], raws, decisions, adjudication=attempt))["result"]
        states = {item["id"]: item["state"] for item in result["rows"]}
        self.assertEqual(states, {"F1": "REFUTED", "F2": "OPEN"})
        self.assertIsNone(result["next_adjudication"])
        f2 = next(item for item in result["rows"] if item["id"] == "F2")
        self.assertEqual(f2["history"][0]["rejected_state"], "REFUTED")

    def test_clean_second_call_bounces_undecided_and_individual_bounce(self) -> None:
        raws, decisions = self.two_pending()
        call = outcome(
            adjudication_decision("F1", "BOUNCE"),
            adjudication_decision("F2", "UNDECIDED"),
        )
        attempt = adjudication(["F1", "F2"], attempt=2, call_outcome=call)
        result = process(request([], raws, decisions, adjudication=attempt))["result"]
        self.assertEqual([item["state"] for item in result["rows"]], ["OPEN", "OPEN"])
        self.assertIsNone(result["next_adjudication"])

    def test_attempt_sets_must_partition_original_obligation_and_forbid_third_call(self) -> None:
        raws, decisions = self.two_pending()
        bad_partition = adjudication(
            ["F1", "F2"], attempt=2, settled=[], pending=["F1"], call_outcome=outcome(status="failed")
        )
        bad_attempt = adjudication(["F1", "F2"], attempt=3, call_outcome=outcome(status="failed"))
        for value in (bad_partition, bad_attempt):
            with self.subTest(value=value):
                response = process(request([], raws, decisions, adjudication=value))
                self.assertIs(response["ok"], False)


if __name__ == "__main__":
    unittest.main()
