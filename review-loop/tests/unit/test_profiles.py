import tempfile
import unittest
from pathlib import Path

from review_loop.profiles import (
    InvocationIntent,
    ProfileError,
    ReviewProfile,
    RunPolicy,
    load_profile,
    resolve_policy,
)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class LoadProfileNameResolutionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.xdg = Path(self._tmp.name)

    def test_bare_name_resolves_under_xdg_profiles_dir(self):
        write(self.xdg / "review-loop" / "profiles" / "mine.yaml", "version: 1\n")
        profile = load_profile("mine", self.xdg)
        self.assertIsInstance(profile, ReviewProfile)
        self.assertEqual(profile.version, 1)

    def test_missing_bare_name_raises_profile_error(self):
        with self.assertRaises(ProfileError):
            load_profile("nope", self.xdg)

    def test_traversal_bare_name_is_rejected(self):
        with self.assertRaises(ProfileError):
            load_profile("../escape", self.xdg)

    def test_dot_dot_alone_is_rejected(self):
        with self.assertRaises(ProfileError):
            load_profile("..", self.xdg)

    def test_separator_in_bare_name_is_rejected(self):
        with self.assertRaises(ProfileError):
            load_profile("sub/name", self.xdg)

    def test_explicit_path_is_used_directly(self):
        explicit = self.xdg / "elsewhere" / "custom.yaml"
        write(explicit, "version: 1\n")
        profile = load_profile(str(explicit), self.xdg)
        self.assertEqual(profile.version, 1)

    def test_missing_explicit_path_raises_profile_error(self):
        with self.assertRaises(ProfileError):
            load_profile(str(self.xdg / "elsewhere" / "missing.yaml"), self.xdg)


class ProfileSchemaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.xdg = Path(self._tmp.name)
        self.path = self.xdg / "review-loop" / "profiles" / "p.yaml"

    def load(self, text):
        write(self.path, text)
        return load_profile("p", self.xdg)

    def test_minimal_valid_profile(self):
        profile = self.load("version: 1\n")
        self.assertEqual(profile.version, 1)
        self.assertIsNone(profile.max_time_seconds)

    def test_positive_max_time_seconds(self):
        profile = self.load("version: 1\nmax_time_seconds: 1800\n")
        self.assertEqual(profile.max_time_seconds, 1800)

    def test_non_positive_max_time_seconds_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\nmax_time_seconds: 0\n")

    def test_non_integer_max_time_seconds_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\nmax_time_seconds: 12.5\n")

    def test_holistic_capability_and_model_pins(self):
        profile = self.load(
            "version: 1\n"
            "holistic:\n"
            "  capability: mid-tier\n"
            "  model: local-model-id\n"
        )
        self.assertEqual(profile.holistic.capability, "mid-tier")
        self.assertEqual(profile.holistic.model, "local-model-id")

    def test_holistic_fallback_inherits_when_absent(self):
        profile = self.load(
            "version: 1\n"
            "holistic:\n"
            "  capability: mid-tier\n"
            "  model: local-model-id\n"
        )
        self.assertEqual(profile.holistic.fallback_capability, "mid-tier")
        self.assertEqual(profile.holistic.fallback_model, "local-model-id")

    def test_holistic_fallback_overrides_when_present(self):
        profile = self.load(
            "version: 1\n"
            "holistic:\n"
            "  capability: mid-tier\n"
            "  model: local-model-id\n"
            "  fallback_capability: most-capable\n"
            "  fallback_model: other-model\n"
        )
        self.assertEqual(profile.holistic.fallback_capability, "most-capable")
        self.assertEqual(profile.holistic.fallback_model, "other-model")

    def test_adversarial_and_specialists_pins(self):
        profile = self.load(
            "version: 1\n"
            "adversarial:\n"
            "  capability: one-above-mid\n"
            "  model: adv-model\n"
            "specialists:\n"
            "  capability: most-capable\n"
            "  model: spec-model\n"
        )
        self.assertEqual(profile.adversarial.capability, "one-above-mid")
        self.assertEqual(profile.specialists.model, "spec-model")

    def test_multi_review_models_claude_and_codex(self):
        profile = self.load(
            "version: 1\n"
            "holistic:\n"
            "  multi_review:\n"
            "    models:\n"
            "      claude: provider-model-a\n"
            "      codex: provider-model-b\n"
        )
        self.assertEqual(
            profile.holistic.multi_review_models,
            {"claude": "provider-model-a", "codex": "provider-model-b"},
        )

    def test_multi_review_models_rejects_unknown_key(self):
        with self.assertRaises(ProfileError):
            self.load(
                "version: 1\n"
                "holistic:\n"
                "  multi_review:\n"
                "    models:\n"
                "      gemini: provider-model-a\n"
            )

    def test_multi_review_models_rejects_claude_only(self):
        with self.assertRaises(ProfileError):
            self.load(
                "version: 1\n"
                "holistic:\n"
                "  multi_review:\n"
                "    models:\n"
                "      claude: provider-model-a\n"
            )

    def test_multi_review_models_rejects_codex_only(self):
        with self.assertRaises(ProfileError):
            self.load(
                "version: 1\n"
                "holistic:\n"
                "  multi_review:\n"
                "    models:\n"
                "      codex: provider-model-b\n"
            )

    def test_multi_review_models_rejects_empty_pair(self):
        with self.assertRaises(ProfileError):
            self.load(
                "version: 1\n"
                "holistic:\n"
                "  multi_review:\n"
                "    models: {}\n"
            )

    def test_multi_review_models_rejects_empty_value(self):
        with self.assertRaises(ProfileError):
            self.load(
                "version: 1\n"
                "holistic:\n"
                "  multi_review:\n"
                "    models:\n"
                "      claude: ''\n"
                "      codex: provider-model-b\n"
            )

    def test_unsupported_capability_label_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\nholistic:\n  capability: super-max\n")

    def test_unknown_top_level_key_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\nbogus: true\n")

    def test_unknown_holistic_key_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\nholistic:\n  bogus: true\n")

    def test_unknown_version_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 2\n")

    def test_boolean_version_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: true\n")

    def test_missing_version_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("holistic:\n  capability: mid-tier\n")

    def test_wrong_type_for_holistic_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\nholistic: not-a-mapping\n")

    def test_non_overridable_field_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\ntier: max\n")


class DuplicateKeyRejectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.xdg = Path(self._tmp.name)
        self.path = self.xdg / "review-loop" / "profiles" / "p.yaml"

    def load(self, text):
        write(self.path, text)
        return load_profile("p", self.xdg)

    def test_duplicate_top_level_key_rejected(self):
        with self.assertRaises(ProfileError):
            self.load("version: 1\nversion: 1\n")

    def test_duplicate_nested_key_rejected(self):
        with self.assertRaises(ProfileError):
            self.load(
                "version: 1\n"
                "holistic:\n"
                "  capability: mid-tier\n"
                "  capability: most-capable\n"
            )

    def test_duplicate_deeply_nested_key_rejected(self):
        with self.assertRaises(ProfileError):
            self.load(
                "version: 1\n"
                "holistic:\n"
                "  multi_review:\n"
                "    models:\n"
                "      claude: a\n"
                "      claude: b\n"
            )


class ResolvePolicyTests(unittest.TestCase):
    def intent(self, **overrides):
        base = dict(
            target=Path("/tmp/target"),
            base=None,
            head=None,
            exclusions=(),
            review_profile=None,
            max_time_seconds=None,
            no_confirm=False,
            ground_truth=(),
        )
        base.update(overrides)
        return InvocationIntent(**base)

    def test_no_profile_uses_tier_defaults(self):
        policy = resolve_policy(self.intent(), None, "med")
        self.assertIsInstance(policy, RunPolicy)
        self.assertEqual(policy.tier, "med")
        self.assertIsNone(policy.max_time_seconds)

    def test_profile_overlays_holistic_pins_leaving_others_default(self):
        profile = load_profile_from_text(
            "version: 1\n"
            "holistic:\n"
            "  capability: mid-tier\n"
            "  model: local-model-id\n"
        )
        policy = resolve_policy(self.intent(), profile, "high")
        self.assertEqual(policy.holistic_model, "local-model-id")
        self.assertEqual(policy.tier, "high")

    def test_invocation_max_time_overrides_profile(self):
        profile = load_profile_from_text("version: 1\nmax_time_seconds: 1800\n")
        policy = resolve_policy(self.intent(max_time_seconds=60), profile, "low")
        self.assertEqual(policy.max_time_seconds, 60)

    def test_profile_max_time_used_when_invocation_absent(self):
        profile = load_profile_from_text("version: 1\nmax_time_seconds: 1800\n")
        policy = resolve_policy(self.intent(), profile, "low")
        self.assertEqual(policy.max_time_seconds, 1800)


def load_profile_from_text(text):
    with tempfile.TemporaryDirectory() as tmp:
        xdg = Path(tmp)
        write(xdg / "review-loop" / "profiles" / "t.yaml", text)
        return load_profile("t", xdg)


if __name__ == "__main__":
    unittest.main()
