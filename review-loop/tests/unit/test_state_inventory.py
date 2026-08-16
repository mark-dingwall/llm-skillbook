import copy
import unittest

from review_loop import process


INVALIDATORS = {
    "surface_changed": False,
    "dependency_changed": False,
    "contract_changed": False,
    "finding_reopened": False,
    "identity_changed": False,
    "new_depth_evidence": False,
}


def area(area_id="payments", consequence="Important", surfaces=None):
    resolved_surfaces = surfaces or [f"src/{area_id}.py"]
    return {
        "id": area_id,
        "aliases": [],
        "consequence": consequence,
        "consequence_evidence": [f"spec:{area_id}"],
        "generalist_miss": ["domain invariant requires depth"],
        "surfaces": resolved_surfaces,
        "surface_files": resolved_surfaces,
        "charter": f"challenge {area_id} invariants",
    }


def coverage(area_id="payments"):
    owning = [f"src/{area_id}.py"]
    return {
        "status": "CURRENT",
        "report_id": f"report-{area_id}",
        "seal": "seal-1",
        "owning_files": owning,
        "reviewed_files": owning,
    }


def prior_area(area_id="payments", consequence="Important"):
    value = area(area_id, consequence)
    value["coverage"] = coverage(area_id)
    return value


def refresh_request(
    prior_areas,
    current_areas,
    mappings,
    priority_order,
    invalidators=None,
):
    return {
        "schema_version": 1,
        "operation": "refresh_inventory",
        "input": {
            "prior_areas": prior_areas,
            "current_areas": current_areas,
            "mappings": mappings,
            "priority_order": priority_order,
            "invalidators": invalidators or {},
        },
    }


def coverage_request(areas, *coverage_events, target_seal="seal-new", scheduled_area_ids=None):
    return {
        "schema_version": 1,
        "operation": "record_specialist_coverage",
        "input": {
            "areas": areas,
            "coverage_events": list(coverage_events),
            "target_seal": target_seal,
            "scheduled_area_ids": scheduled_area_ids
            if scheduled_area_ids is not None
            else [event["area_id"] for event in coverage_events],
        },
    }


class InventoryCoverageTests(unittest.TestCase):
    def test_usable_report_covering_every_owning_file_makes_area_current(self) -> None:
        event = {
            "area_id": "payments",
            "report_id": "r-new",
            "seal": "seal-new",
            "owning_files": ["src/payments.py", "src/shared.py"],
            "reviewed_files": ["src/shared.py", "src/payments.py"],
            "usable": True,
        }
        stale = area(surfaces=event["owning_files"])
        stale["coverage"] = {"status": "STALE"}
        response = process(coverage_request([stale], event))
        self.assertIs(response["ok"], True, response)
        current = response["result"]["areas"][0]["coverage"]
        self.assertEqual(current["status"], "CURRENT")
        self.assertEqual(current["report_id"], "r-new")
        self.assertEqual(current["owning_files"], event["owning_files"])

    def test_report_missing_an_owning_file_is_rejected(self) -> None:
        event = {
            "area_id": "payments",
            "report_id": "r-new",
            "seal": "seal-new",
            "owning_files": ["src/payments.py", "src/shared.py"],
            "reviewed_files": ["src/payments.py"],
            "usable": True,
        }
        stale = area(surfaces=event["owning_files"])
        stale["coverage"] = {"status": "STALE"}
        response = process(coverage_request([stale], event))
        self.assertIs(response["ok"], False)
        self.assertIn("coverage_events[0].reviewed_files", response["errors"][0]["path"])

    def test_report_owning_set_must_equal_active_lineage_surface_files(self) -> None:
        event = {
            "area_id": "payments",
            "report_id": "r-new",
            "seal": "seal-new",
            "owning_files": ["src/payments.py"],
            "reviewed_files": ["src/payments.py"],
            "usable": True,
        }
        stale = area(surfaces=["src/payments.py", "src/shared.py"])
        stale["coverage"] = {"status": "STALE"}
        response = process(coverage_request([stale], event))
        self.assertIs(response["ok"], False)
        self.assertIn(
            ("$.input.coverage_events[0].owning_files", "coverage"),
            [(item["path"], item["code"]) for item in response["errors"]],
        )

    def test_each_named_invalidator_makes_retained_coverage_stale(self) -> None:
        for name in INVALIDATORS:
            with self.subTest(invalidator=name):
                flags = dict(INVALIDATORS)
                flags[name] = True
                response = process(
                    refresh_request(
                        [prior_area()],
                        [area()],
                        [{"prior_id": "payments", "resolution": "continuing", "active_id": "payments"}],
                        ["payments"],
                        {"payments": flags},
                    )
                )
                self.assertIs(response["ok"], True, response)
                self.assertEqual(
                    response["result"]["active_areas"][0]["coverage"], {"status": "STALE"}
                )

    def test_continuing_area_requires_explicit_invalidator_record(self) -> None:
        response = process(
            refresh_request(
                [prior_area()],
                [area()],
                [{"prior_id": "payments", "resolution": "continuing", "active_id": "payments"}],
                ["payments"],
                {},
            )
        )
        self.assertIs(response["ok"], False)
        self.assertIn(
            ("$.input.invalidators.payments", "missing"),
            [(item["path"], item["code"]) for item in response["errors"]],
        )

    def test_new_and_successor_start_stale_then_can_become_current_after_review(self) -> None:
        event = {
            "area_id": "new",
            "report_id": "r-old",
            "seal": "seal-new",
            "owning_files": ["src/old.py", "src/new.py"],
            "reviewed_files": ["src/old.py", "src/new.py"],
            "usable": True,
        }
        new_response = process(refresh_request([], [area("new")], [], ["new"], {}))
        successor_response = process(
            refresh_request(
                [prior_area("old")],
                [area("new")],
                [{"prior_id": "old", "resolution": "successor", "active_id": "new"}],
                ["new"],
                {"new": dict(INVALIDATORS)},
            )
        )
        self.assertIs(new_response["ok"], True, new_response)
        self.assertIs(successor_response["ok"], True, successor_response)
        self.assertEqual(new_response["result"]["active_areas"][0]["coverage"], {"status": "STALE"})
        self.assertEqual(
            successor_response["result"]["active_areas"][0]["coverage"], {"status": "STALE"}
        )
        completed = process(
            coverage_request(successor_response["result"]["active_areas"], event)
        )
        self.assertIs(completed["ok"], True, completed)
        self.assertEqual(completed["result"]["areas"][0]["coverage"]["status"], "CURRENT")

    def test_post_review_coverage_requires_current_seal_and_scheduled_area(self) -> None:
        stale = area()
        stale["coverage"] = {"status": "STALE"}
        event = {
            "area_id": "payments",
            "report_id": "r-old",
            "seal": "seal-old",
            "owning_files": ["src/payments.py"],
            "reviewed_files": ["src/payments.py"],
            "usable": True,
        }
        old = process(coverage_request([stale], event, target_seal="seal-new"))
        event["seal"] = "seal-new"
        unscheduled = process(
            coverage_request([stale], event, scheduled_area_ids=[])
        )
        self.assertIs(old["ok"], False)
        self.assertIs(unscheduled["ok"], False)
    def test_successor_starts_stale_and_preserves_lineage_maxima_and_unions(self) -> None:
        old = prior_area("old", "Critical")
        old["aliases"] = ["legacy"]
        old["surfaces"] = ["src/old.py"]
        old["surface_files"] = ["src/old.py"]
        new = area("new", "Minor", ["src/new.py"])
        response = process(
            refresh_request(
                [old],
                [new],
                [{"prior_id": "old", "resolution": "successor", "active_id": "new"}],
                ["new"],
                {"new": dict(INVALIDATORS)},
            )
        )
        self.assertIs(response["ok"], True, response)
        current = response["result"]["active_areas"][0]
        self.assertEqual(current["consequence"], "Critical")
        self.assertEqual(current["coverage"], {"status": "STALE"})
        self.assertEqual(current["aliases"], ["legacy"])
        self.assertEqual(current["surfaces"], ["src/old.py", "src/new.py"])
        self.assertEqual(current["surface_files"], ["src/old.py", "src/new.py"])


class InventoryIdentityTests(unittest.TestCase):
    def test_retirement_requires_nonblank_single_line_reason_and_preserves_audit_record(self) -> None:
        mapping = {
            "prior_id": "payments",
            "resolution": "retired",
            "retirement_reason": "risk-bearing surface was removed",
        }
        response = process(refresh_request([prior_area()], [], [mapping], []))
        self.assertIs(response["ok"], True, response)
        self.assertEqual(response["result"]["active_areas"], [])
        self.assertEqual(
            response["result"]["retired_areas"][0]["retirement_reason"],
            "risk-bearing surface was removed",
        )
        for reason in ("", "  ", "line one\nline two"):
            with self.subTest(reason=reason):
                bad = copy.deepcopy(mapping)
                bad["retirement_reason"] = reason
                rejected = process(refresh_request([prior_area()], [], [bad], []))
                self.assertIs(rejected["ok"], False)

    def test_every_prior_id_must_be_mapped_exactly_once(self) -> None:
        omitted = process(refresh_request([prior_area()], [area()], [], ["payments"]))
        duplicate = process(
            refresh_request(
                [prior_area()],
                [area()],
                [
                    {"prior_id": "payments", "resolution": "continuing", "active_id": "payments"},
                    {"prior_id": "payments", "resolution": "successor", "active_id": "payments"},
                ],
                ["payments"],
            )
        )
        self.assertIs(omitted["ok"], False)
        self.assertIs(duplicate["ok"], False)

    def test_active_ids_and_priority_order_are_bijective(self) -> None:
        duplicate_area = process(refresh_request([], [area(), area()], [], ["payments"]))
        missing_priority = process(
            refresh_request([], [area("payments"), area("auth")], [], ["payments"])
        )
        unknown_priority = process(refresh_request([], [area()], [], ["payments", "unknown"]))
        duplicate_priority = process(refresh_request([], [area()], [], ["payments", "payments"]))
        for response in (duplicate_area, missing_priority, unknown_priority, duplicate_priority):
            self.assertIs(response["ok"], False)


if __name__ == "__main__":
    unittest.main()
