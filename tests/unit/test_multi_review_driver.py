import asyncio
import importlib.util
import textwrap
from pathlib import Path

import pytest

from multi_review.core.adapters import Usage
from multi_review.core.fanout import ReviewerResult

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_driver():
    spec = importlib.util.spec_from_file_location("mr_driver", REPO_ROOT / "multi_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = _load_driver()


def _write_promptfile(tmp_path: Path, body: str) -> Path:
    """Write a prompt YAML plus the one input file it references."""
    (tmp_path / "target.py").write_text("def f():\n    return 1\n")
    pf = tmp_path / "prompt.yaml"
    pf.write_text(textwrap.dedent(body))
    return pf


BASE_YAML = """\
    prompt_format_version: 1
    task: code
    files: [target.py]
    reviewers: [codex]
    synthesizer: none
"""


def test_out_dir_created_when_missing(tmp_path, monkeypatch):
    _, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    assert (out / "prompt.txt").exists()


def test_prompt_txt_contains_the_input_file_body(tmp_path, monkeypatch):
    _, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    assert "return 1" in (out / "prompt.txt").read_text()


def test_non_empty_out_dir_is_rejected(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    (out / "REVIEW.md").write_text("stale")
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_empty_out_dir_is_accepted(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    monkeypatch.setattr(driver, "run_all_reviewers", _RecordingFanout())
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert (out / "prompt.txt").exists()


def test_mode_both_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML + "    mode: both\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_malformed_yaml_exits_2_without_traceback(tmp_path):
    pf = _write_promptfile(tmp_path, "    task: [unclosed\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_unknown_top_level_key_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML + "    bogus_field: 3\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_missing_prompt_file_exits_2(tmp_path):
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(tmp_path / "nope.yaml"), "--out-dir", str(out)]) == 2


def test_invalid_utf8_prompt_file_exits_2_without_traceback(tmp_path, capsys):
    pf = tmp_path / "prompt.yaml"
    pf.write_bytes(b"\xff\xfe")
    out = tmp_path / "round-1"

    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    err = capsys.readouterr().err
    assert "UTF-8" in err
    assert "Traceback" not in err


def test_nul_path_prompt_file_exits_2_without_traceback(tmp_path, capsys):
    pf = _write_promptfile(
        tmp_path,
        'prompt_format_version: 1\ntask: code\nfiles: ["bad\\0path"]\n',
    )
    out = tmp_path / "round-1"

    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    err = capsys.readouterr().err
    assert "invalid path" in err
    assert "Traceback" not in err


def test_schema_violation_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML.replace("task: code", "task: nonsense"))
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_validation_failure_does_not_create_out_dir(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML.replace("task: code", "task: nonsense"))
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    assert not out.exists()


def test_unreadable_input_file_exits_1(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"

    def _boom(*args, **kwargs):
        raise SystemExit("error: cannot read target.py")

    monkeypatch.setattr(driver, "build_prompt", _boom)
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_prompt_output_write_failure_exits_1_without_traceback(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    real_write_text = Path.write_text

    def _write(path, text, *args, **kwargs):
        if path.name == "prompt.txt":
            raise OSError("read-only output")
        return real_write_text(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _write)
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_argparse_usage_error_raises_systemexit(tmp_path):
    with pytest.raises(SystemExit):
        driver.main(["--prompt-file", "only-one-arg"])


SUMMARY_BODY = "## Summary\n\nLooks fine.\n"


def _result(cli, ok=True, text=SUMMARY_BODY, error=None):
    return ReviewerResult(cli=cli, ok=ok, text=text, stderr_tail="",
                          usage=Usage(), elapsed=1.0, error=error)


class _RecordingFanout:
    """Stand-in for run_all_reviewers that records one orchestration call."""

    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    async def __call__(self, reviewers, prompt, models, timeout, **kwargs):
        self.calls.append({"reviewers": reviewers, "prompt": prompt, "models": models,
                           "timeout": timeout, **kwargs})
        results = [self.results.get(cli, _result(cli)) for cli in reviewers]
        if kwargs.get("result_callback"):
            for result in results:
                kwargs["result_callback"](result)
        return results

    @property
    def clis(self):
        return self.calls[0]["reviewers"]


def _run(tmp_path, monkeypatch, yaml_body, fanout, extra_argv=()):
    """Run the driver with run_all_reviewers faked out."""
    pf = _write_promptfile(tmp_path, yaml_body)
    out = tmp_path / "round-1"
    monkeypatch.setattr(driver, "run_all_reviewers", fanout)
    code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out), *extra_argv])
    return code, out


THREE_YAML = """\
    prompt_format_version: 1
    task: code
    files: [target.py]
    reviewers: [codex, codex, agy]
    synthesizer: none
"""


def test_duplicate_reviewers_are_dispatched_once(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.clis == ["codex", "agy"]


def test_fanout_receives_the_on_disk_prompt_path(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.calls[0]["prompt_path"] == out / "prompt.txt"


def test_fanout_receives_prompt_task(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.calls[0]["task"] == "code"


def test_model_is_forwarded_only_when_configured(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML + "    models: {codex: gpt-5.6-sol}\n", fanout)
    assert fanout.calls[0]["models"] == {"codex": "gpt-5.6-sol"}


def test_timeout_is_forwarded_when_given(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout, extra_argv=["--timeout", "600"])
    assert fanout.calls[0]["timeout"] == 600


def test_timeout_defaults_to_none(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.calls[0]["timeout"] is None


def test_review_md_is_written_with_both_reviewers(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    code, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert 'reviewers_succeeded: ["codex", "agy"]' in text
    assert 'reviewers_failed: []' in text


def test_all_reviewers_failing_exits_1(tmp_path, monkeypatch):
    fanout = _RecordingFanout(results={
        "codex": _result("codex", ok=False, text="", error="rc=1"),
        "agy": _result("agy", ok=False, text="", error="rc=1"),
    })
    code, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert code == 1
    assert 'reviewers_failed: ["codex", "agy"]' in (out / "REVIEW.md").read_text()


def test_exit_code_uses_classified_not_raw_ok(tmp_path, monkeypatch):
    fanout = _RecordingFanout(results={
        "codex": _result("codex", ok=True, text="I reviewed it. No heading here."),
        "agy": _result("agy", ok=False, text="", error="rc=1"),
    })
    code, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    text = (out / "REVIEW.md").read_text()
    assert code == 1
    assert 'reviewers_failed: ["codex", "agy"]' in text
    assert "failed — no ## Summary heading in review body" in text
    assert "unknown error" not in text


def test_progress_lines_go_to_stderr(tmp_path, monkeypatch, capsys):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    err = capsys.readouterr().err
    assert "[multi_review] codex: ok" in err
    assert "[multi_review] agy: ok" in err


def test_review_write_failure_returns_1_without_raising(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(driver, "write_review_md",
                        lambda **kwargs: (_ for _ in ()).throw(SystemExit("disk full")))
    code, _ = _run(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout())
    assert code == 1
    assert "disk full" in capsys.readouterr().err


class _RecordingSynth:
    def __init__(self, ok=True, text="## Consensus Summary\n\nAgreed.\n", raises=None):
        self.ok, self.text, self.raises = ok, text, raises
        self.calls = []

    async def __call__(self, cli, body, nonce, model=None, timeout=None):
        self.calls.append({"cli": cli, "body": body, "nonce": nonce,
                           "model": model, "timeout": timeout})
        if self.raises is not None:
            raise self.raises
        return self.ok, self.text, "", None, ["<default>"]


SYNTH_YAML = """\
    prompt_format_version: 1
    task: code
    files: [target.py]
    reviewers: [codex, agy]
    synthesizer: claude
"""


def _run_with_synth(tmp_path, monkeypatch, yaml_body, reviewer, synth, extra_argv=()):
    monkeypatch.setattr(driver, "run_synthesis", synth)
    return _run(tmp_path, monkeypatch, yaml_body, reviewer, extra_argv)


def test_synthesizer_none_never_calls_run_synthesis(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _run_with_synth(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout(), synth)
    assert synth.calls == []


def test_one_raw_success_does_not_reach_the_synthesizer(tmp_path, monkeypatch):
    rev = _RecordingFanout(results={"agy": _result("agy", ok=False, text="", error="rc=1")})
    synth = _RecordingSynth()
    _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, rev, synth)
    assert synth.calls == []


def test_two_raw_successes_reach_the_synthesizer(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert [c["cli"] for c in synth.calls] == ["claude"]
    assert "Agreed." in text


def test_synthesis_frontmatter_records_attribution(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert "synthesizer: claude" in text
    assert "synthesized_at: " in text


def test_successful_empty_synthesis_still_records_attribution(tmp_path, monkeypatch):
    synth = _RecordingSynth(ok=True, text="")
    _, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML,
                             _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert "synthesizer: claude" in text
    assert "synthesized_at: " in text


def test_synthesis_receives_model_and_timeout(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML + "    models: {claude: opus}\n",
                    _RecordingFanout(), synth, extra_argv=["--timeout", "600"])
    assert synth.calls[0]["model"] == "opus"
    assert synth.calls[0]["timeout"] == 600


def test_synthesis_gate_is_raw_while_exit_code_is_classified(tmp_path, monkeypatch):
    # Both raw-ok (gate fires) but one lacks a "## Summary" heading (classified fail).
    rev = _RecordingFanout(results={
        "codex": _result("codex", ok=True, text="no heading anywhere in this body"),
    })
    synth = _RecordingSynth()
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, rev, synth)
    text = (out / "REVIEW.md").read_text()
    assert len(synth.calls) == 1          # gate saw 2 raw successes
    assert code == 0                      # agy still classified-ok
    assert 'reviewers_succeeded: ["agy"]' in text
    assert 'reviewers_failed: ["codex"]' in text


def test_synthesis_raising_does_not_lose_the_review(tmp_path, monkeypatch):
    # run_synthesis genuinely can raise: NamedTemporaryFile in
    # _run_synthesis_attempt executes before its own try block, so an OSError
    # (unwritable /tmp under `bwrap --tmpfs /tmp`) propagates out. Unwrapped,
    # that would discard every collected reviewer result at the last moment.
    synth = _RecordingSynth(raises=OSError("read-only /tmp"))
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert 'reviewers_succeeded: ["codex", "agy"]' in text
    assert "synthesizer: claude" not in text


def test_synthesis_returning_not_ok_leaves_review_intact(tmp_path, monkeypatch):
    synth = _RecordingSynth(ok=False, text="")
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    assert code == 0
    assert "synthesizer: claude" not in (out / "REVIEW.md").read_text()


def test_cancellation_during_fanout_returns_1_not_a_traceback(tmp_path, monkeypatch):
    # The outer cancellation a SIGTERM triggers propagates through the shared
    # fanout, out of the coroutine, and out of asyncio.run(). Without the catch
    # in main(), the process dies on an uncaught traceback instead of honouring
    # the `main() -> int` contract.
    async def _cancelled(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(driver, "_amain", _cancelled)
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_sigterm_handler_is_installed(tmp_path, monkeypatch):
    installed = []
    real_get_loop = driver.asyncio.get_running_loop

    class _Spy:
        def __init__(self, loop):
            self._loop = loop

        def __getattr__(self, name):
            return getattr(self._loop, name)

        def add_signal_handler(self, sig, cb):
            installed.append(sig)
            return self._loop.add_signal_handler(sig, cb)

    monkeypatch.setattr(driver.asyncio, "get_running_loop", lambda: _Spy(real_get_loop()))
    _run(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout())
    assert driver.signal.SIGTERM in installed
