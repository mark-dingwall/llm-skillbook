import unittest

from review_loop import process


def area(area_id="payments", consequence="Important"):
    return {
        "id": area_id,
        "aliases": [],
        "consequence": consequence,
        "consequence_evidence": [f"spec:{area_id}"],
        "generalist_miss": ["domain invariant requires depth"],
        "surfaces": [f"src/{area_id}.py"],
        "surface_files": [f"src/{area_id}.py"],
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


def roster_area(area_id, consequence, current=False, generalist_miss=True):
    value = area(area_id, consequence)
    value["generalist_miss"] = ["specialist depth needed"] if generalist_miss else []
    value["coverage"] = coverage(area_id) if current else {"status": "STALE"}
    return value


def roster_request(tier, areas, priority_order, capacity=4):
    return {
        "schema_version": 1,
        "operation": "plan_roster",
        "input": {
            "tier": tier,
            "areas": areas,
            "priority_order": priority_order,
            "capacity": capacity,
        },
    }


class RosterEligibilityTests(unittest.TestCase):
    def specialist_ids(self, tier, areas):
        response = process(roster_request(tier, areas, [item["id"] for item in areas]))
        self.assertIs(response["ok"], True, response)
        return [item["area_id"] for item in response["result"]["roster"] if item["role"] == "specialist"]

    def test_low_requires_critical_generalist_miss(self) -> None:
        areas = [
            roster_area("minor", "Minor"),
            roster_area("important", "Important"),
            roster_area("critical", "Critical"),
            roster_area("no-miss", "Critical", generalist_miss=False),
        ]
        self.assertEqual(self.specialist_ids("low", areas), ["critical"])

    def test_med_and_high_require_important_or_critical_generalist_miss(self) -> None:
        areas = [
            roster_area("minor", "Minor"),
            roster_area("important", "Important"),
            roster_area("critical", "Critical"),
        ]
        self.assertEqual(self.specialist_ids("med", areas), ["important", "critical"])
        self.assertEqual(self.specialist_ids("high", areas), ["important", "critical"])

    def test_max_makes_every_named_area_eligible_without_generalist_miss(self) -> None:
        areas = [roster_area("minor", "Minor", generalist_miss=False)]
        self.assertEqual(self.specialist_ids("max", areas), ["minor"])

    def test_only_eligible_critical_is_restaffed_when_current(self) -> None:
        areas = [
            roster_area("important", "Important", current=True),
            roster_area("critical", "Critical", current=True),
        ]
        self.assertEqual(self.specialist_ids("med", areas), ["critical"])


class RosterWaveTests(unittest.TestCase):
    def test_priority_places_stale_before_current_critical_without_omission(self) -> None:
        areas = [
            roster_area("current-critical", "Critical", current=True),
            roster_area("stale-important", "Important"),
        ]
        response = process(
            roster_request("med", areas, ["current-critical", "stale-important"], capacity=3)
        )
        self.assertIs(response["ok"], True, response)
        specialists = [
            item["area_id"]
            for item in response["result"]["roster"]
            if item["role"] == "specialist"
        ]
        self.assertEqual(specialists, ["stale-important", "current-critical"])

    def test_capacity_splits_complete_roster_into_waves_and_reserves_controller_slot(self) -> None:
        areas = [roster_area(f"area-{index}", "Important") for index in range(10)]
        response = process(
            roster_request("med", areas, [item["id"] for item in areas], capacity=4)
        )
        self.assertIs(response["ok"], True, response)
        result = response["result"]
        self.assertEqual(len(result["roster"]), 12)
        self.assertEqual([len(wave) for wave in result["waves"]], [3, 3, 3, 3])
        flattened = [entry for wave in result["waves"] for entry in wave]
        self.assertEqual(flattened, result["roster"])

    def test_capacity_below_two_is_rejected(self) -> None:
        response = process(roster_request("med", [], [], capacity=1))
        self.assertIs(response["ok"], False)
        self.assertEqual(response["errors"][0]["path"], "$.input.capacity")


if __name__ == "__main__":
    unittest.main()
