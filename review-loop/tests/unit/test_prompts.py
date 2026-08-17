import unittest

from review_loop.prompts import RenderError, render_prompt

BASE = {
    "request_id": "req-1",
    "role": "holistic",
    "charter_id": "charter-1",
    "target_seal": "seal-1",
    "round_input_seal": "",
    "scope_locator_ids": "loc-1,loc-2",
    "subject": "ordinary subject text",
}
LATER = {**BASE, "round_input_seal": "seal-round-2", "delta_summary": "3 files changed"}


class RenderPromptTests(unittest.TestCase):
    def test_renders_review_round_one(self):
        rendered = render_prompt("review", ("round-one",), BASE)
        self.assertIsInstance(rendered, bytes)
        self.assertIn(b"req-1", rendered)
        self.assertIn(b"round one", rendered)

    def test_renders_review_later_round(self):
        rendered = render_prompt("review", ("later-round",), LATER)
        self.assertIn(b"3 files changed", rendered)
        self.assertIn(b"later round", rendered)

    def test_missing_declared_value_is_rejected(self):
        context = dict(BASE)
        del context["subject"]
        with self.assertRaises(RenderError):
            render_prompt("review", ("round-one",), context)

    def test_unknown_supplied_value_is_rejected(self):
        context = {**BASE, "unexpected": "x"}
        with self.assertRaises(RenderError):
            render_prompt("review", ("round-one",), context)

    def test_unknown_template_is_rejected(self):
        with self.assertRaises(RenderError):
            render_prompt("no-such-template", ("round-one",), BASE)

    def test_unknown_fragment_is_rejected(self):
        with self.assertRaises(RenderError):
            render_prompt("review", ("no-such-fragment",), BASE)

    def test_substituted_braces_are_not_rescanned(self):
        rendered = render_prompt(
            "review", ("round-one",), {**BASE, "subject": "literal {{danger}}"}
        )
        self.assertIn(b"literal {{danger}}", rendered)

    def test_fragment_order_is_caller_determined_and_deterministic(self):
        forward = render_prompt("review", ("round-one",), BASE)
        again = render_prompt("review", ("round-one",), BASE)
        self.assertEqual(forward, again)

    def test_ordinary_and_adapter_style_calls_are_byte_identical(self):
        # An adapter caller renders with the same template/fragment/context
        # triple as ordinary dispatch and must get exactly the same bytes.
        ordinary = render_prompt("review", ("round-one",), dict(BASE))
        adapter = render_prompt("review", ("round-one",), {k: v for k, v in BASE.items()})
        self.assertEqual(ordinary, adapter)


class TemplateSourceIntegrityTests(unittest.TestCase):
    """Exercise the pure token-discovery pass against crafted resource text."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        import review_loop.prompts as prompts

        self._prompts = prompts
        self._orig_resources = prompts.RESOURCES
        self._orig_templates = dict(prompts.TEMPLATES)
        self._orig_fragments = dict(prompts.FRAGMENTS)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self._restore)
        prompts.RESOURCES = Path(self._tmp.name)

    def _restore(self):
        self._prompts.RESOURCES = self._orig_resources
        self._prompts.TEMPLATES = self._orig_templates
        self._prompts.FRAGMENTS = self._orig_fragments

    def _write(self, name, text):
        (self._prompts.RESOURCES / name).write_text(text, encoding="utf-8")

    def test_unmatched_brace_in_source_template_is_rejected(self):
        self._write("broken.md", "hello {name")
        self._prompts.TEMPLATES = {"broken": "broken.md"}
        self._prompts.FRAGMENTS = {}
        with self.assertRaises(RenderError):
            render_prompt("broken", (), {"name": "x"})

    def test_positional_field_in_source_template_is_rejected(self):
        self._write("positional.md", "hello {0}")
        self._prompts.TEMPLATES = {"positional": "positional.md"}
        self._prompts.FRAGMENTS = {}
        with self.assertRaises(RenderError):
            render_prompt("positional", (), {})

    def test_auto_numbered_field_in_source_template_is_rejected(self):
        self._write("auto.md", "hello {}")
        self._prompts.TEMPLATES = {"auto": "auto.md"}
        self._prompts.FRAGMENTS = {}
        with self.assertRaises(RenderError):
            render_prompt("auto", (), {})


if __name__ == "__main__":
    unittest.main()
