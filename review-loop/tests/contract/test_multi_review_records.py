"""tests/contract/test_multi_review_records.py — cross-codebase fixture contract.

multi-review's narrow review-loop driver opt-in (Task 10:
multi_review.core.aggregate.parse_qualified_review_record) implements its own
review-record classifier, independent of review-loop's existing one
(review_loop.prompts.validate_review_report). Neither codebase imports the
other in production — multi-review must stay usable by callers that have
never heard of review-loop, and review-loop's state kernel must not depend on
multi-review's process. This test is the only thing pinning the two
classifiers to the same report shape: for every fixture body below, both
classifiers must reach the same accept/reject verdict.

Fixtures live in tests/contract/fixtures/multi-review-records/*.json, each
holding a dispatch-expectation object, a raw report body, and the expected
verdict.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

from review_loop.prompts import (
    DispatchExpectation,
    ProcessCompletion,
    ValidatedReview,
    validate_review_report,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MULTI_REVIEW_ROOT = REPO_ROOT / "multi-review"
FIXTURES = Path(__file__).parent / "fixtures" / "multi-review-records"


def _load_multi_review_aggregate():
    """Import multi_review.core.aggregate from the sibling multi-review repo.

    multi-review is not an installed dependency of review-loop (and must not
    become one — production review-loop code never imports it). This test
    reaches across the worktree boundary purely to compare classifier
    behavior, the same way it would load any other external fixture.
    """
    if str(MULTI_REVIEW_ROOT) not in sys.path:
        sys.path.insert(0, str(MULTI_REVIEW_ROOT))
    spec = importlib.util.find_spec("multi_review.core.aggregate")
    if spec is None:
        raise unittest.SkipTest(f"multi_review package not found under {MULTI_REVIEW_ROOT}")
    import multi_review.core.aggregate as aggregate

    return aggregate


class MultiReviewRecordContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aggregate = _load_multi_review_aggregate()

    @staticmethod
    def _dispatch_expectation(dispatch: dict) -> DispatchExpectation:
        return DispatchExpectation(
            request_id=dispatch["request_id"],
            role=dispatch["role"],
            charter_id=dispatch["charter_id"],
            target_seal=dispatch["target_seal"],
            round_input_seal=dispatch["round_input_seal"],
            scope_locator_ids=tuple(dispatch["scope_locator_ids"]),
        )

    @staticmethod
    def _process_completion(dispatch: dict) -> ProcessCompletion:
        # multi-review's classifier has no notion of subprocess reaping — that
        # is out of its scope entirely (the caller/driver handles it). Supply
        # a clean completion here so review-loop's usable-gate reduces to
        # exactly the same record-shape question multi-review answers.
        return ProcessCompletion(
            request_id=dispatch["request_id"], exit_status=0, process_tree_terminated=True,
        )

    @staticmethod
    def _mr_expectation(dispatch: dict) -> dict:
        expectation = dict(dispatch)
        expectation.setdefault("raw_report_id", "raw-fixture")
        return expectation

    def _multi_review_accepts(self, body: str, dispatch: dict) -> bool:
        try:
            self.aggregate.parse_qualified_review_record(body, self._mr_expectation(dispatch))
            return True
        except self.aggregate.ReviewRecordError:
            return False

    def _review_loop_accepts(self, body: str, dispatch: dict) -> bool:
        result = validate_review_report(
            body.encode("utf-8"),
            self._dispatch_expectation(dispatch),
            self._process_completion(dispatch),
        )
        return isinstance(result, ValidatedReview) and result.usable

    def test_fixtures_agree_between_classifiers(self) -> None:
        fixture_paths = sorted(FIXTURES.glob("*.json"))
        self.assertTrue(fixture_paths, f"no fixtures found under {FIXTURES}")
        for path in fixture_paths:
            with self.subTest(fixture=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                dispatch, body, expect_accept = data["dispatch"], data["body"], data["expect_accept"]

                mr_accept = self._multi_review_accepts(body, dispatch)
                rl_accept = self._review_loop_accepts(body, dispatch)

                self.assertEqual(
                    mr_accept, expect_accept,
                    f"{path.name}: multi-review classifier verdict disagreed with fixture",
                )
                self.assertEqual(
                    rl_accept, expect_accept,
                    f"{path.name}: review-loop classifier verdict disagreed with fixture",
                )


if __name__ == "__main__":
    unittest.main()
