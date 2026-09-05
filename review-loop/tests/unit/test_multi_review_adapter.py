"""Adapter construction tests for the caller-contained multi-review holistic
slot (Task 11). No subprocess/bwrap here -- pure argv/mount/prompt/YAML
construction, using a fake host paths fixture (see
tests/integration/test_multi_review_containment.py for the real-bwrap proof).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from review_loop.multi_review import (
    _SUBJECT_TEXT,
    HolisticRequest,
    MultiReviewError,
    MultiReviewHostPaths,
    MultiReviewPolicy,
    build_multi_review_call,
    build_prompt_yaml_text,
    render_verbatim_prompt,
)
from review_loop.prompts import render_prompt
from review_loop.seals import GitPolicy, SealEntry, seal_target

REPO_ROOT = Path(__file__).resolve().parents[3]
MULTI_REVIEW_ROOT = REPO_ROOT / "multi-review"
sys.path.insert(0, str(MULTI_REVIEW_ROOT))
from multi_review.core.aggregate import parse_verbatim_dispatch_header  # noqa: E402
from multi_review.core.promptfile import load_promptfile  # noqa: E402


def _make_host(root: Path) -> MultiReviewHostPaths:
    root.mkdir(parents=True, exist_ok=True)
    fake = root / "fake"
    for name in ("bwrap", "uv", "claude"):
        p = fake / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/bin/sh\n")
        p.chmod(0o755)
    mr_root = root / "mr"
    mr_root.mkdir()
    (mr_root / "multi_review.py").write_text("# stub")
    codex_pkg = root / "codexpkg"
    (codex_pkg / "bin").mkdir(parents=True)
    codex_entry = codex_pkg / "bin" / "codex.js"
    codex_entry.write_text("// stub")
    auth = root / "auth.json"
    auth.write_text("{}")
    resolv = root / "resolv.conf"
    resolv.write_text("nameserver 1.1.1.1\n")
    nsswitch = root / "nsswitch.conf"
    nsswitch.write_text("hosts: files dns\n")
    ca = root / "ca.crt"
    ca.write_text("cert")
    ca_dir = root / "ssl"
    ca_dir.mkdir()
    hosts = root / "hosts"
    hosts.write_text("127.0.0.1 localhost\n")
    hostname = root / "hostname"
    hostname.write_text("host\n")
    uv_cache_src = root / "uvcachesrc"
    uv_cache_src.mkdir()
    (uv_cache_src / "seed").write_text("cached")
    uv_py_src = root / "uvpysrc"
    uv_py_src.mkdir()
    return MultiReviewHostPaths(
        bwrap=fake / "bwrap", uv=fake / "uv", claude=fake / "claude",
        codex_package_root=codex_pkg, codex_entry=codex_entry, codex_auth_file=auth,
        multi_review_root=mr_root, resolv_conf=resolv, nsswitch_conf=nsswitch,
        ca_certificates=ca, ca_certificates_dir=ca_dir, hosts=hosts, hostname=hostname,
        uv_cache_source=uv_cache_src, uv_python_install_source=uv_py_src, wsl=False,
    )


class AdapterConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "target"
        self.target.mkdir()
        (self.target / "foo.py").write_text("x = 1\n")
        (self.target / "bar.py").write_text("y = 2\n")
        self.host = _make_host(self.root)
        seal = seal_target(self.target, GitPolicy(enabled=False))
        self.request = HolisticRequest(
            call_id="call-1",
            request_id="req-1",
            target_seal=seal.digest,
            round_input_seal=None,
            scope_locator_ids=("target-root",),
            target_root=self.target,
            target_entries=seal.entries,
            run_root=self.root / "run",
            raw_report_ids={"claude": "raw-claude-1", "codex": "raw-codex-1"},
        )

    def _build(self, policy=None):
        return build_multi_review_call(
            self.request, policy or MultiReviewPolicy(), self.host, self.root / "call",
            timeout_seconds=300,
        )

    # --- one fresh empty output directory; driver YAML outside it ---

    def test_out_dir_is_fresh_and_empty_and_request_yaml_lives_outside_it(self):
        argv, wrapper, paths = self._build()
        self.assertTrue(paths.out_dir.is_dir())
        self.assertEqual(list(paths.out_dir.iterdir()), [])
        self.assertFalse(paths.request_yaml.is_relative_to(paths.out_dir))
        self.assertTrue(paths.request_yaml.is_file())

    # --- exact fixed pair ---

    def test_exact_fixed_reviewer_pair(self):
        argv, wrapper, paths = self._build()
        pf = load_promptfile(paths.request_yaml)
        self.assertEqual(pf.reviewers, ["claude", "codex"])
        self.assertEqual(pf.synthesizer, "none")
        self.assertEqual(pf.task, "custom")
        self.assertTrue(pf.verbatim_custom_prompt)
        self.assertTrue(pf.require_complete_status)

    def test_exact_files_list_matches_sealed_target_entries(self):
        argv, wrapper, paths = self._build()
        pf = load_promptfile(paths.request_yaml)
        self.assertEqual(
            sorted(pf.files),
            sorted(str((self.target / e.path).resolve()) for e in self.request.target_entries if e.kind == "file"),
        )

    def test_caller_cannot_replace_full_target_with_a_subset(self):
        subset = tuple(e for e in self.request.target_entries if e.path == "foo.py")
        bad = HolisticRequest(**{**self.request.__dict__, "target_entries": subset})
        with self.assertRaises(MultiReviewError):
            build_multi_review_call(
                bad, MultiReviewPolicy(), self.host, self.root / "subset-call", timeout_seconds=60,
            )

    def test_git_backed_request_uses_its_governing_seal_policy(self):
        subprocess.run(["git", "-C", str(self.target), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.target), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.target), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.target), "add", "foo.py", "bar.py"], check=True)
        subprocess.run(["git", "-C", str(self.target), "commit", "-q", "-m", "initial"], check=True)
        policy = GitPolicy(enabled=True, base="HEAD", include_untracked=True)
        seal = seal_target(self.target, policy)
        request = HolisticRequest(**{
            **self.request.__dict__, "target_seal": seal.digest,
            "target_entries": seal.entries, "git_policy": policy,
        })

        _argv, _wrapper, paths = build_multi_review_call(
            request, MultiReviewPolicy(), self.host, self.root / "git-call", timeout_seconds=60,
        )
        self.assertTrue(paths.request_yaml.is_file())

    # --- no generic CLI defaults for unpinned reviewers ---

    def test_unpinned_policy_sets_use_cli_defaults_not_a_synthesized_model(self):
        argv, wrapper, paths = self._build(MultiReviewPolicy())
        pf = load_promptfile(paths.request_yaml)
        self.assertTrue(pf.use_cli_defaults)
        self.assertEqual(pf.models, {})

    def test_pinned_policy_sets_exact_models_and_clears_use_cli_defaults(self):
        policy = MultiReviewPolicy(models={"claude": "opus", "codex": "gpt-codex"})
        argv, wrapper, paths = self._build(policy)
        pf = load_promptfile(paths.request_yaml)
        self.assertFalse(pf.use_cli_defaults)
        self.assertEqual(pf.models, {"claude": "opus", "codex": "gpt-codex"})

    def test_incomplete_pin_pair_is_rejected(self):
        policy = MultiReviewPolicy(models={"claude": "opus"})
        with self.assertRaises(MultiReviewError):
            self._build(policy)

    # --- no prompt bytes in argv ---

    def test_no_prompt_bytes_in_argv(self):
        argv, wrapper, paths = self._build()
        prompt_text = render_verbatim_prompt(self.request)
        haystack = " ".join(argv) + " " + wrapper
        self.assertNotIn(prompt_text, haystack)
        self.assertNotIn("## Subject", haystack)
        self.assertNotIn("request_id: req-1", haystack)

    # --- distinct preallocated raw IDs ---

    def test_distinct_preallocated_raw_ids_reach_argv(self):
        argv, wrapper, paths = self._build()
        self.assertIn("--raw-report-id claude=raw-claude-1", wrapper)
        self.assertIn("--raw-report-id codex=raw-codex-1", wrapper)

    def test_duplicate_raw_ids_are_rejected(self):
        bad = HolisticRequest(**{**self.request.__dict__, "raw_report_ids": {"claude": "same", "codex": "same"}})
        with self.assertRaises(MultiReviewError):
            build_multi_review_call(bad, MultiReviewPolicy(), self.host, self.root / "call2", timeout_seconds=60)

    # --- driver-config seal (request.yaml is a stable, hashable artifact) ---

    def test_request_yaml_is_deterministic_for_the_same_request(self):
        argv1, _, paths1 = self._build()
        argv2, _, paths2 = build_multi_review_call(
            self.request, MultiReviewPolicy(), self.host, self.root / "call-again", timeout_seconds=300,
        )
        self.assertEqual(paths1.request_yaml.read_bytes(), paths2.request_yaml.read_bytes())

    # --- exact canonical prompt bytes ---

    def test_verbatim_prompt_equals_canonical_rendering(self):
        context = {
            "request_id": self.request.request_id,
            "role": "holistic",
            "charter_id": "holistic",
            "target_seal": self.request.target_seal,
            "round_input_seal": "null",
            "scope_locator_ids": json.dumps(list(self.request.scope_locator_ids)),
            "subject": _SUBJECT_TEXT,
        }
        canonical = render_prompt("review", ("safety", "round-one", "holistic"), context)
        rendered = render_verbatim_prompt(self.request)

        self.assertEqual(rendered.encode("utf-8"), canonical)

    def test_canonical_prompt_matches_task10_verbatim_header_parser(self):
        prompt_text = render_verbatim_prompt(self.request)
        header = parse_verbatim_dispatch_header(prompt_text)
        self.assertEqual(header["request_id"], "req-1")
        self.assertEqual(header["role"], "holistic")
        self.assertEqual(header["charter_id"], "holistic")
        self.assertEqual(header["target_seal"], self.request.target_seal)
        self.assertIsNone(header["round_input_seal"])
        self.assertEqual(header["scope_locator_ids"], ["target-root"])

    def test_round_input_seal_renders_as_literal_null_token(self):
        prompt_text = render_verbatim_prompt(self.request)
        lines = prompt_text.splitlines()
        self.assertIn("round_input_seal: null", lines)

    def test_round_input_seal_renders_the_actual_seal_when_present(self):
        req = HolisticRequest(**{**self.request.__dict__, "round_input_seal": "prior-seal-abc"})
        prompt_text = render_verbatim_prompt(req)
        self.assertIn("round_input_seal: prior-seal-abc", prompt_text.splitlines())

    def test_scope_locator_ids_render_as_a_json_array(self):
        req = HolisticRequest(**{**self.request.__dict__, "scope_locator_ids": ("a", "b")})
        prompt_text = render_verbatim_prompt(req)
        line = next(ln for ln in prompt_text.splitlines() if ln.startswith("scope_locator_ids:"))
        self.assertEqual(json.loads(line.split(": ", 1)[1]), ["a", "b"])

    def test_prompt_round_trips_byte_identical_through_the_yaml_file(self):
        argv, wrapper, paths = self._build()
        prompt_text = render_verbatim_prompt(self.request)
        pf = load_promptfile(paths.request_yaml)
        self.assertEqual(pf.custom_prompt, prompt_text)

    # --- target-intersecting runtime closure fails closed at construction ---

    def test_target_intersecting_multi_review_root_fails_closed(self):
        bad_host = _make_host(self.root / "hostB")
        bad_host = MultiReviewHostPaths(**{**bad_host.__dict__, "multi_review_root": self.target})
        with self.assertRaises(MultiReviewError):
            build_multi_review_call(self.request, MultiReviewPolicy(), bad_host, self.root / "call3", timeout_seconds=60)

    def test_target_intersecting_codex_auth_file_fails_closed(self):
        bad_host = _make_host(self.root / "hostC")
        nested_auth = self.target / "auth.json"
        nested_auth.write_text("{}")
        bad_host = MultiReviewHostPaths(**{**bad_host.__dict__, "codex_auth_file": nested_auth})
        with self.assertRaises(MultiReviewError):
            build_multi_review_call(self.request, MultiReviewPolicy(), bad_host, self.root / "call4", timeout_seconds=60)


if __name__ == "__main__":
    unittest.main()
