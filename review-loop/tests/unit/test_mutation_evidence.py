"""Opportunistic mutation evidence: always supporting, never blocking, never
installs or initializes tooling. Every gate execution here is faked (no real
bwrap) -- ``tests/integration/test_evidence_execution.py`` proves the same
machinery under real containment.
"""
import dataclasses
import subprocess
import tempfile
import unittest
from pathlib import Path

from review_loop.evidence import (
    ManualMutation,
    MutationPlan,
    MutationPlanError,
    MutationResult,
    make_disposable_copy,
    run_mutation_evidence,
)
from review_loop.seals import GitPolicy, seal_target

FAKE_HOST = type("Host", (), {"bwrap": Path("/usr/bin/bwrap"), "usr": Path("/usr")})()


def call_counter(exit_codes):
    """A fake ``run`` returning ``exit_codes[n]`` on its (n+1)th call."""
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(tuple(argv))
        code = exit_codes[len(calls) - 1]
        return subprocess.CompletedProcess(argv, code, stdout="", stderr="" if code == 0 else "assertion failed")

    return fake_run, calls


class MakeDisposableCopyTests(unittest.TestCase):
    def test_copy_is_isolated_from_the_sealed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "a.py").write_text("value = 1\n")
            seal = seal_target(source, GitPolicy(enabled=False))

            dest = root / "copy"
            make_disposable_copy(seal, dest)
            (dest / "a.py").write_text("value = 2\n")

            self.assertEqual((source / "a.py").read_text(), "value = 1\n")
            self.assertEqual((dest / "a.py").read_text(), "value = 2\n")


class MutationPlanValidationTests(unittest.TestCase):
    def test_unavailable_plan_needs_no_baseline(self):
        MutationPlan(baseline_argv=None)  # does not raise -- validated lazily

    def test_manual_mutation_without_baseline_argv_is_rejected(self):
        mutation = ManualMutation(id="m1", target_path="a.py", mutate=lambda t: t, rationale="x")
        plan = MutationPlan(baseline_argv=None, manual_mutations=(mutation,))
        with self.assertRaises(MutationPlanError):
            run_mutation_evidence(plan, Path("/nonexistent"), host=FAKE_HOST)

    def test_manual_mutation_target_path_escaping_the_copy_is_rejected(self):
        mutation = ManualMutation(id="m1", target_path="../escape.py", mutate=lambda t: t, rationale="x")
        plan = MutationPlan(baseline_argv=("pytest", "-q"), manual_mutations=(mutation,))
        with self.assertRaises(MutationPlanError):
            run_mutation_evidence(plan, Path("/nonexistent"), host=FAKE_HOST)


class UnavailableMutationTests(unittest.TestCase):
    def test_no_tool_and_no_manual_mutations_is_unavailable_and_dispatches_nothing(self):
        fake_run, calls = call_counter([])
        plan = MutationPlan(baseline_argv=None)
        result = run_mutation_evidence(plan, Path("/nonexistent"), host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(calls, [], "unavailable mutation evidence must never dispatch a command")
        self.assertTrue(result.follow_up)

    def test_unavailable_follow_up_is_the_callers_own_reason_when_supplied(self):
        plan = MutationPlan(baseline_argv=None, unavailable_reason="no mutation tool configured for this stack")
        result = run_mutation_evidence(plan, Path("/nonexistent"), host=FAKE_HOST)
        self.assertEqual(result.follow_up, "no mutation tool configured for this stack")

    def test_never_installs_or_initializes_tooling(self):
        # The closed argv policy would reject pip/npm-install anyway (evidence.py's
        # validate_gate_argv); this asserts the higher-level behavioral guarantee:
        # unavailability produces a follow-up, never a fallback install attempt.
        fake_run, calls = call_counter([])
        plan = MutationPlan(baseline_argv=None, unavailable_reason="no tool")
        run_mutation_evidence(plan, Path("/nonexistent"), host=FAKE_HOST, run=fake_run)
        self.assertEqual(calls, [])


class ConfiguredToolMutationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.copy = Path(self._tmp.name) / "copy"
        self.copy.mkdir()
        (self.copy / "calc.py").write_text("def add(a, b):\n    return a + b\n")

    def test_configured_tool_success_never_produces_itemized_mutants(self):
        fake_run, calls = call_counter([0, 0])  # baseline PASSED, tool PASSED
        plan = MutationPlan(baseline_argv=("pytest", "-q"), tool_argv=("cargo", "mutants"))
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.status, "EVALUATED")
        self.assertEqual(result.source, "tool")
        self.assertEqual(result.mutants, ())
        self.assertEqual(len(calls), 2, "must run the baseline before the configured tool")

    def test_baseline_failure_invalidates_a_configured_tool_run(self):
        fake_run, calls = call_counter([1])  # baseline FAILED
        plan = MutationPlan(baseline_argv=("pytest", "-q"), tool_argv=("cargo", "mutants"))
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.status, "BASELINE_FAILED")
        self.assertIsNone(result.tool_result)
        self.assertEqual(len(calls), 1, "the configured tool must never run against a broken baseline")


class ManualMutationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.copy = Path(self._tmp.name) / "copy"
        self.copy.mkdir()
        (self.copy / "calc.py").write_text("def add(a, b):\n    return a + b\n")

    def _plan(self, mutations, exit_codes):
        fake_run, calls = call_counter(exit_codes)
        plan = MutationPlan(baseline_argv=("pytest", "-q"), manual_mutations=tuple(mutations))
        return plan, fake_run, calls

    def test_baseline_failure_invalidates_manual_mutation_evidence(self):
        mutation = ManualMutation(id="flip", target_path="calc.py", mutate=lambda t: t.replace("+", "-"), rationale="flip operator")
        plan, fake_run, calls = self._plan([mutation], exit_codes=[1])  # baseline FAILED
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.status, "BASELINE_FAILED")
        self.assertEqual(result.mutants, ())
        self.assertEqual(len(calls), 1, "no mutant may run once the baseline itself failed")
        self.assertEqual((self.copy / "calc.py").read_text(), "def add(a, b):\n    return a + b\n")

    def test_a_mutant_that_fails_the_baseline_test_is_caught(self):
        mutation = ManualMutation(id="flip", target_path="calc.py", mutate=lambda t: t.replace("+", "-"), rationale="flip operator")
        plan, fake_run, calls = self._plan([mutation], exit_codes=[0, 1])  # baseline PASSED, mutant FAILED
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.status, "EVALUATED")
        self.assertEqual(result.mutants[0].classification, "caught")

    def test_a_surviving_mutant_without_an_equivalence_claim_is_surviving(self):
        mutation = ManualMutation(
            id="noop", target_path="calc.py",
            mutate=lambda t: t + "\n# untested comment\n", rationale="dead code, no equivalence claim",
        )
        plan, fake_run, calls = self._plan([mutation], exit_codes=[0, 0])  # baseline PASSED, mutant PASSED
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.mutants[0].classification, "surviving")

    def test_a_passing_mutant_with_an_equivalence_claim_is_equivalent_not_surviving(self):
        mutation = ManualMutation(
            id="reorder", target_path="calc.py",
            mutate=lambda t: t, rationale="behaviorally identical rewrite", equivalence_claim=True,
        )
        plan, fake_run, calls = self._plan([mutation], exit_codes=[0, 0])  # baseline PASSED, mutant PASSED
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.mutants[0].classification, "equivalent")

    def test_a_failing_mutant_is_caught_even_if_equivalence_was_claimed(self):
        # The test differentiated it, so any equivalence claim was simply wrong.
        mutation = ManualMutation(
            id="flip", target_path="calc.py", mutate=lambda t: t.replace("+", "-"),
            rationale="mistaken equivalence claim", equivalence_claim=True,
        )
        plan, fake_run, calls = self._plan([mutation], exit_codes=[0, 1])
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(result.mutants[0].classification, "caught")

    def test_mutation_is_reverted_from_the_disposable_copy_after_each_mutant(self):
        mutation = ManualMutation(id="flip", target_path="calc.py", mutate=lambda t: t.replace("+", "-"), rationale="flip operator")
        plan, fake_run, calls = self._plan([mutation], exit_codes=[0, 1])
        run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual((self.copy / "calc.py").read_text(), "def add(a, b):\n    return a + b\n")

    def test_never_mutates_anything_outside_the_disposable_copy(self):
        source_marker = self.copy.parent / "outside.py"
        source_marker.write_text("untouched = True\n")
        mutation = ManualMutation(id="flip", target_path="calc.py", mutate=lambda t: t.replace("+", "-"), rationale="flip operator")
        plan, fake_run, calls = self._plan([mutation], exit_codes=[0, 1])
        run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        self.assertEqual(source_marker.read_text(), "untouched = True\n")

    def test_multiple_mutants_are_individually_classified_no_score(self):
        caught = ManualMutation(id="flip", target_path="calc.py", mutate=lambda t: t.replace("+", "-"), rationale="flip operator")
        surviving = ManualMutation(id="noop", target_path="calc.py", mutate=lambda t: t + "\n# x\n", rationale="dead code")
        plan, fake_run, calls = self._plan([caught, surviving], exit_codes=[0, 1, 0])
        result = run_mutation_evidence(plan, self.copy, host=FAKE_HOST, run=fake_run)
        classifications = {m.id: m.classification for m in result.mutants}
        self.assertEqual(classifications, {"flip": "caught", "noop": "surviving"})
        field_names = {f.name for f in dataclasses.fields(MutationResult)}
        self.assertNotIn("score", field_names)
        self.assertFalse(any("score" in f for f in field_names), "mutation evidence must carry no numeric score field")


if __name__ == "__main__":
    unittest.main()
