import unittest

from review_loop import process


def rater(complexity: str, risk: str, gestalt: bool = False) -> dict[str, object]:
    sample: dict[str, object] = {"complexity": complexity, "risk": risk}
    if gestalt:
        sample["gestalt"] = {
            "decision": "+1",
            "factors": [
                {"factor": "cross-file", "evidence": "three contracts move together"},
                {"factor": "irreversible", "evidence": "migration changes stored state"},
                {"factor": "novel", "evidence": "no established local pattern"},
            ],
        }
    return sample


def request(explicit_tier: object, raters: list[dict[str, object]], no_confirm: bool = False):
    return {
        "schema_version": 1,
        "operation": "derive_policy",
        "input": {
            "explicit_tier": explicit_tier,
            "no_confirm": no_confirm,
            "raters": raters,
        },
    }


class ExplicitPolicyTests(unittest.TestCase):
    def test_each_explicit_tier_returns_its_complete_policy_without_confirmation(self) -> None:
        expected = {
            "low": (2, "mid-tier", "Critical", []),
            "med": (3, "mid-tier", "Important", []),
            "high": (5, "one-above-mid", "Important", [1]),
            "max": (5, "most-capable", "every", [1, 2]),
        }
        for tier, (round_cap, capability, threshold, multi_rounds) in expected.items():
            with self.subTest(tier=tier):
                response = process(request(tier, []))
                self.assertIs(response["ok"], True)
                self.assertEqual(
                    response["result"],
                    {
                        "tier": tier,
                        "source": "explicit",
                        "confirmation_required": False,
                        "round_cap": round_cap,
                        "normal_capability": capability,
                        "specialist_threshold": threshold,
                        "multi_review_rounds": multi_rounds,
                    },
                )

    def test_explicit_tier_rejects_supplied_raters(self) -> None:
        response = process(request("high", [rater("low", "low")]))
        self.assertIs(response["ok"], False)
        self.assertIn(
            ("$.input.raters", "forbidden"),
            [(item["path"], item["code"]) for item in response["errors"]],
        )

    def test_returned_policy_cannot_mutate_later_policy_results(self) -> None:
        first = process(request("max", []))["result"]
        first["multi_review_rounds"].append(99)
        second = process(request("max", []))["result"]
        self.assertEqual(second["multi_review_rounds"], [1, 2])


class AutomaticPolicyTests(unittest.TestCase):
    def derive(self, first: dict[str, object], second: dict[str, object], no_confirm=False):
        response = process(request(None, [first, second], no_confirm))
        self.assertIs(response["ok"], True, response)
        return response["result"]

    def test_combines_complexity_and_risk_independently(self) -> None:
        result = self.derive(rater("high", "low"), rater("low", "med"))
        self.assertEqual(result["tier"], "high")

    def test_both_merged_axes_high_step_up_once(self) -> None:
        result = self.derive(rater("high", "low"), rater("low", "high"))
        self.assertEqual(result["tier"], "max")

    def test_one_valid_gestalt_steps_up_once(self) -> None:
        result = self.derive(rater("med", "med", True), rater("med", "low", True))
        self.assertEqual(result["tier"], "high")

    def test_gestalt_and_axis_steps_saturate_at_max(self) -> None:
        result = self.derive(rater("high", "high", True), rater("high", "high", True))
        self.assertEqual(result["tier"], "max")

    def test_only_automatic_max_without_override_requires_confirmation(self) -> None:
        automatic = self.derive(rater("high", "high"), rater("high", "high"))
        overridden = self.derive(
            rater("high", "high"), rater("high", "high"), no_confirm=True
        )
        self.assertIs(automatic["confirmation_required"], True)
        self.assertIs(overridden["confirmation_required"], False)

    def test_automatic_selection_requires_exactly_two_raters(self) -> None:
        for samples in ([], [rater("low", "low")], [rater("low", "low")] * 3):
            with self.subTest(count=len(samples)):
                response = process(request(None, samples))
                self.assertIs(response["ok"], False)
                self.assertEqual(response["errors"][0]["path"], "$.input.raters")

    def test_rejects_malformed_gestalt(self) -> None:
        malformed = rater("med", "med")
        malformed["gestalt"] = {
            "decision": "+1",
            "factors": [
                {"factor": "one", "evidence": "present"},
                {"factor": "two", "evidence": ""},
            ],
        }
        response = process(request(None, [malformed, rater("low", "low")]))
        self.assertIs(response["ok"], False)
        paths = [item["path"] for item in response["errors"]]
        self.assertIn("$.input.raters[0].gestalt.factors", paths)

    def test_rejects_unknown_rating_and_input_fields(self) -> None:
        bad = request(None, [rater("low", "low"), rater("low", "low")])
        bad["input"]["extra"] = True
        bad["input"]["raters"][0]["extra"] = True
        response = process(bad)
        self.assertIs(response["ok"], False)
        pairs = [(item["path"], item["code"]) for item in response["errors"]]
        self.assertIn(("$.input.extra", "unknown"), pairs)
        self.assertIn(("$.input.raters[0].extra", "unknown"), pairs)


if __name__ == "__main__":
    unittest.main()
