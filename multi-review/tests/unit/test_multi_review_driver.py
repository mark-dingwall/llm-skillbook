import asyncio
import importlib.util
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
import yaml

from multi_review.core.adapters import Usage
from multi_review.core.fanout import ReviewerResult
from multi_review.core.prompt import SUMMARY_HEADING_CONTRACT

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
    prompt_format_version: 2
    task: code
    files: [target.py]
    reviewers: [codex]
    synthesizer: none
"""


def test_out_dir_created_when_missing(tmp_path, monkeypatch):
    _, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    assert (out / "prompt.txt").exists()


def test_prompt_txt_manifests_input_file_not_body(tmp_path, monkeypatch):
    _, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    body = (out / "prompt.txt").read_text()
    assert str((tmp_path / "target.py").resolve()) in body
    assert "return 1" not in body


def test_custom_yaml_prompt_txt_ends_with_runner_owned_summary_contract(tmp_path, monkeypatch):
    yaml_body = BASE_YAML.replace("task: code", "task: custom") + (
        '    custom_prompt: "CUSTOM_YAML_REVIEW_CHARTER"\n'
    )
    _, out = _run(tmp_path, monkeypatch, yaml_body, _RecordingFanout())
    body = (out / "prompt.txt").read_text()

    assert "CUSTOM_YAML_REVIEW_CHARTER" in body
    assert body.rstrip().endswith(SUMMARY_HEADING_CONTRACT)


def test_non_empty_out_dir_is_rejected(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    (out / "REVIEW.md").write_text("stale")
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_stale_claim_reports_already_claimed(tmp_path, capsys):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    (out / ".multi-review.claim").touch()

    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    assert "already claimed" in capsys.readouterr().err


def test_empty_out_dir_is_accepted(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    monkeypatch.setattr(driver, "run_all_reviewers", _RecordingFanout())
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert (out / "prompt.txt").exists()


def test_output_claim_allows_only_one_active_owner(tmp_path):
    """Break caught: two racing drivers could both write a fresh output directory."""
    out = tmp_path / "round-1"

    claim = driver.claim_output_dir(out)

    assert claim == out / ".multi-review.claim"
    with pytest.raises(FileExistsError):
        driver.claim_output_dir(out)
    claim.unlink()


def test_output_claim_rejects_directory_that_became_non_empty(tmp_path):
    """Break caught: an output created after preflight could still be overwritten."""
    out = tmp_path / "round-1"
    out.mkdir()
    (out / "other-run.txt").write_text("do not overwrite")

    with pytest.raises(FileExistsError):
        driver.claim_output_dir(out)

    assert not (out / ".multi-review.claim").exists()


@pytest.mark.parametrize(
    "key,yaml_value",
    [
        ("mode", '""'),
        ("if_drift", '""'),
        ("harvest", "false"),
        ("output_dir", "null"),
        ("save_as", "null"),
        ("model_effort", "{}"),
    ],
)
def test_removed_key_in_promptfile_exits_2(tmp_path, capsys, key, yaml_value):
    pf = _write_promptfile(tmp_path, BASE_YAML + f"    {key}: {yaml_value}\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    assert key in capsys.readouterr().err


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


def test_symlink_loop_prompt_file_exits_2_without_traceback(tmp_path, capsys):
    """The CLI prompt path itself is invalid input, not an internal crash."""
    prompt = tmp_path / "prompt.yaml"
    prompt.symlink_to(prompt.name)
    out = tmp_path / "round-1"

    try:
        code = driver.main(["--prompt-file", str(prompt), "--out-dir", str(out)])
    except RuntimeError as exc:
        pytest.fail(f"prompt path RuntimeError escaped the CLI boundary: {exc}")

    assert code == 2
    assert "Traceback" not in capsys.readouterr().err


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
        'prompt_format_version: 2\ntask: code\nfiles: ["bad\\0path"]\n',
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


def test_unreadable_input_file_is_rejected_before_fanout(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    source = (tmp_path / "target.py").resolve()
    real_open = Path.open
    fanout = _RecordingFanout()

    def deny_input_read(path, mode="r", *args, **kwargs):
        if path == source and mode == "rb":
            raise PermissionError("read denied")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_input_read)
    monkeypatch.setattr(driver, "run_all_reviewers", fanout)
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1
    assert fanout.calls == []
    assert not out.exists()


def test_build_time_path_validation_error_exits_2(tmp_path, monkeypatch, capsys):
    """A path that becomes invalid after prompt-file validation stays a CLI error."""
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"

    def invalid_path(*args, **kwargs):
        raise driver.ValidationError("path changed after validation")

    monkeypatch.setattr(driver, "_resolve_path", invalid_path)

    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    assert "path changed after validation" in capsys.readouterr().err


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
    assert not (out / ".multi-review.claim").exists()


def test_prompt_artifact_is_utf8_under_ascii_locale(tmp_path):
    """Valid Unicode prompt content must not depend on the process locale."""
    prompt = _write_promptfile(
        tmp_path,
        BASE_YAML.replace("task: code", "task: custom")
        + '    custom_prompt: "Review café handling."\n',
    )
    out = tmp_path / "round-1"
    env = {
        **os.environ,
        "LC_ALL": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "multi_review.py"),
         "--prompt-file", str(prompt), "--out-dir", str(out), "--timeout", "0"],
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert "Traceback" not in result.stderr
    assert "café" in (out / "prompt.txt").read_bytes().decode("utf-8")


def test_sigterm_during_prompt_write_releases_output_claim(tmp_path, monkeypatch):
    """Break caught: TERM before asyncio started stranded the claim marker."""
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    handlers = []
    real_write_text = Path.write_text

    def record_signal(sig, handler):
        handlers.append(handler)
        return driver.signal.getsignal(sig)

    def interrupt_prompt_write(path, text, *args, **kwargs):
        if path.name == "prompt.txt":
            handlers[-1](driver.signal.SIGTERM, None)
        return real_write_text(path, text, *args, **kwargs)

    monkeypatch.setattr(driver.signal, "signal", record_signal)
    monkeypatch.setattr(Path, "write_text", interrupt_prompt_write)
    code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])

    assert code == 1
    assert not (out / ".multi-review.claim").exists()


@pytest.mark.skipif(not hasattr(signal, "pthread_sigmask"), reason="requires POSIX signals")
def test_sigterm_during_claim_creation_releases_output_claim(tmp_path, monkeypatch):
    """Break caught: TERM between O_EXCL claim creation and assignment stranded it."""
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    real_touch = Path.touch

    def interrupt_claim_touch(path, *args, **kwargs):
        result = real_touch(path, *args, **kwargs)
        if path.name == ".multi-review.claim":
            os.kill(os.getpid(), signal.SIGTERM)
        return result

    monkeypatch.setattr(Path, "touch", interrupt_claim_touch)
    code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])

    assert code == 1
    assert not (out / ".multi-review.claim").exists()


@pytest.mark.skipif(not hasattr(signal, "pthread_sigmask"), reason="requires POSIX signals")
def test_sigint_during_claim_creation_returns_1_and_releases_claim(tmp_path, monkeypatch):
    """Ctrl-C after O_EXCL creation must be delivered after claim_ref owns cleanup."""
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    real_touch = Path.touch

    def interrupt_claim_touch(path, *args, **kwargs):
        result = real_touch(path, *args, **kwargs)
        if path.name == ".multi-review.claim":
            os.kill(os.getpid(), signal.SIGINT)
        return result

    monkeypatch.setattr(Path, "touch", interrupt_claim_touch)
    try:
        code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    except KeyboardInterrupt:
        pytest.fail("SIGINT escaped the startup CLI boundary")

    assert code == 1
    assert not (out / ".multi-review.claim").exists()


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
    prior_sigterm_handler = signal.getsignal(signal.SIGTERM)
    prior_sigint_handler = signal.getsignal(signal.SIGINT)
    try:
        code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out), *extra_argv])
    finally:
        signal.signal(signal.SIGTERM, prior_sigterm_handler)
        signal.signal(signal.SIGINT, prior_sigint_handler)
    return code, out


THREE_YAML = """\
    prompt_format_version: 2
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


VERBATIM_YAML = """\
    prompt_format_version: 2
    task: custom
    files: [target.py]
    reviewers: [codex]
    synthesizer: none
    verbatim_custom_prompt: true
    custom_prompt: "EXACT BODY, no wrapping."
"""


def test_verbatim_custom_prompt_writes_exact_prompt_txt(tmp_path, monkeypatch):
    _, out = _run(tmp_path, monkeypatch, VERBATIM_YAML, _RecordingFanout())
    assert (out / "prompt.txt").read_text() == "EXACT BODY, no wrapping."


def test_use_cli_defaults_forwards_empty_models(tmp_path, monkeypatch):
    """Exact unpinned CLI defaults: use_cli_defaults=true means no --model is
    ever passed — fanout must receive an empty models dict, not a silently
    synthesized default."""
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML + "    use_cli_defaults: true\n", fanout)
    assert fanout.calls[0]["models"] == {}


def test_pinned_models_forwarded_exactly_with_no_fallback_substitution(tmp_path, monkeypatch):
    """Exact pinned models: a caller pinning only one of two reviewers must not
    have a fallback synthesized for the other."""
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML + "    models: {codex: gpt-5.6-sol}\n", fanout)
    assert fanout.calls[0]["models"] == {"codex": "gpt-5.6-sol"}


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
    assert text.count("no ## Summary heading in review body") == 1
    assert "unknown error" not in text


def test_progress_lines_go_to_stderr(tmp_path, monkeypatch, capsys):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    err = capsys.readouterr().err
    assert "[multi_review] codex: ok" in err
    assert "[multi_review] agy: ok" in err


# -- Task 10: review-loop opt-in — prompt transport integrity ---------------

DISPATCH_HEADER_FIELDS = {
    "request_id": "req-1", "role": "adversarial", "charter_id": "chart-1",
    "target_seal": "seal-1", "round_input_seal": None, "scope_locator_ids": ["loc-1"],
}


def _dispatch_header_text(fields=None, subject="Review this."):
    d = dict(DISPATCH_HEADER_FIELDS)
    if fields:
        d.update(fields)
    seal = "null" if d["round_input_seal"] is None else d["round_input_seal"]
    return (
        f"request_id: {d['request_id']}\n"
        f"role: {d['role']}\n"
        f"charter_id: {d['charter_id']}\n"
        f"target_seal: {d['target_seal']}\n"
        f"round_input_seal: {seal}\n"
        f"scope_locator_ids: {json.dumps(d['scope_locator_ids'])}\n"
        f"\n{subject}"
    )


def _write_require_complete_promptfile(tmp_path, reviewers=("codex", "agy"), fields=None):
    """A verbatim_custom_prompt=true + require_complete_status=true prompt
    file whose custom_prompt carries the review_loop/resources/review.md-shaped
    dispatch header this driver derives expectations from."""
    (tmp_path / "target.py").write_text("def f():\n    return 1\n")
    pf = tmp_path / "prompt.yaml"
    pf.write_text(yaml.safe_dump({
        "prompt_format_version": 2,
        "task": "custom",
        "files": ["target.py"],
        "reviewers": list(reviewers),
        "synthesizer": "none",
        "verbatim_custom_prompt": True,
        "require_complete_status": True,
        "custom_prompt": _dispatch_header_text(fields),
    }))
    return pf


def _run_require_complete(tmp_path, monkeypatch, fanout, reviewers=("codex", "agy"),
                          fields=None, extra_argv=()):
    pf = _write_require_complete_promptfile(tmp_path, reviewers, fields)
    out = tmp_path / "round-1"
    monkeypatch.setattr(driver, "run_all_reviewers", fanout)
    prior_sigterm_handler = signal.getsignal(signal.SIGTERM)
    prior_sigint_handler = signal.getsignal(signal.SIGINT)
    try:
        code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out), *extra_argv])
    finally:
        signal.signal(signal.SIGTERM, prior_sigterm_handler)
        signal.signal(signal.SIGINT, prior_sigint_handler)
    return code, out


def _raw_report_id_argv(clis):
    argv = []
    for cli in clis:
        argv += ["--raw-report-id", f"{cli}=raw-{cli}"]
    return argv


def _record_body(fields=None, source_findings=(), terminal="REVIEW-STATUS: COMPLETE"):
    d = dict(DISPATCH_HEADER_FIELDS)
    if fields:
        d.update(fields)
    record = {
        "request_id": d["request_id"], "role": d["role"], "charter_id": d["charter_id"],
        "target_seal": d["target_seal"], "round_input_seal": d["round_input_seal"],
        "scope_locator_ids": d["scope_locator_ids"], "source_findings": list(source_findings),
    }
    return (
        "## Summary\n\nLooks fine.\n\n"
        f"```review-record\n{json.dumps(record)}\n```\n{terminal}"
    )


class _TamperingFanout(_RecordingFanout):
    """Simulates a reviewer subprocess that rewrites prompt.txt during fanout."""

    async def __call__(self, reviewers, prompt, models, timeout, **kwargs):
        results = await super().__call__(reviewers, prompt, models, timeout, **kwargs)
        kwargs["prompt_path"].write_bytes(b"TAMPERED BY FAKE REVIEWER")
        return results


def test_require_complete_status_clean_run_dispatches_and_publishes(tmp_path, monkeypatch):
    codex_body = _record_body()
    agy_body = _record_body()
    fanout = _RecordingFanout(results={
        "codex": _result("codex", text=codex_body),
        "agy": _result("agy", text=agy_body),
    })
    code, out = _run_require_complete(tmp_path, monkeypatch, fanout,
                                      extra_argv=_raw_report_id_argv(["codex", "agy"]))
    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert fanout.calls  # dispatch happened
    assert 'reviewers_succeeded: ["codex", "agy"]' in text
    assert "review_records:" in text
    assert "raw_report_id: raw-codex" in text
    assert "raw_report_id: raw-agy" in text


def test_require_complete_status_needs_raw_report_id_for_every_reviewer(tmp_path):
    """Startup-time config error: a raw_report_id is required for every fixed
    slot whenever the opt-in is set — fail closed, never proceed with a
    missing slot."""
    pf = _write_require_complete_promptfile(tmp_path)
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    assert not out.exists()


def test_raw_report_id_rejected_without_require_complete_status(tmp_path):
    """Fail closed on flag misuse in the other direction too: --raw-report-id
    means nothing (and is refused rather than silently ignored) unless the
    opt-in that consumes it is active."""
    pf = _write_promptfile(tmp_path, THREE_YAML)
    out = tmp_path / "round-1"
    code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out),
                        "--raw-report-id", "codex=raw-codex"])
    assert code == 2


def test_argv_has_no_channel_to_name_dispatch_identity_fields(tmp_path):
    """The prompt-vs-flag mismatch class this design closes: there is no flag
    at all (--request-id, --target-seal, --review-record-expect, ...) that
    could name a dispatch field independently of the verbatim prompt. The
    only per-CLI argv input is --raw-report-id, and that carries an opaque
    label, never an identity field a review-record is validated against."""
    pf = _write_require_complete_promptfile(tmp_path)
    out = tmp_path / "round-1"
    for flag in ("--request-id", "--target-seal", "--round-input-seal",
                "--scope-locator-ids", "--review-record-expect", "--charter-id", "--role"):
        with pytest.raises(SystemExit):
            driver.main(["--prompt-file", str(pf), "--out-dir", str(out), flag, "anything"])


def test_expectation_tracks_whichever_prompt_was_actually_sent(tmp_path, monkeypatch):
    """Structural proof that the expectation can't drift from what was sent:
    change only the prompt's target_seal (no separate expectation channel
    exists to update in lockstep), and a review-record correct for the OLD
    seal must now fail, while one matching the NEW seal succeeds — because
    the expectation is derived fresh from prompt_text on every run, not
    pinned by some independent argv value that could go stale."""
    tmp_a, tmp_b = tmp_path / "a", tmp_path / "b"
    tmp_a.mkdir()
    tmp_b.mkdir()

    old_seal_body = _record_body()  # target_seal: seal-1, the default
    fanout = _RecordingFanout(results={"codex": _result("codex", text=old_seal_body)})
    code, out = _run_require_complete(
        tmp_a, monkeypatch, fanout, reviewers=("codex",),
        fields={"target_seal": "seal-DIFFERENT"},
        extra_argv=_raw_report_id_argv(["codex"]),
    )
    text = (out / "REVIEW.md").read_text()
    assert code == 1
    assert 'reviewers_failed: ["codex"]' in text
    assert "does not match dispatch expectation" in text

    new_seal_body = _record_body({"target_seal": "seal-DIFFERENT"})
    fanout2 = _RecordingFanout(results={"codex": _result("codex", text=new_seal_body)})
    code2, out2 = _run_require_complete(
        tmp_b, monkeypatch, fanout2, reviewers=("codex",),
        fields={"target_seal": "seal-DIFFERENT"},
        extra_argv=_raw_report_id_argv(["codex"]),
    )
    assert code2 == 0
    assert 'reviewers_succeeded: ["codex"]' in (out2 / "REVIEW.md").read_text()


def test_require_complete_status_rejects_prompt_tampered_before_dispatch(tmp_path, monkeypatch):
    """Break caught: a reviewer (or anything with fs access) rewrites prompt.txt
    between the driver's write and dispatch. The driver must catch this before
    launching any fixed client, not merely after."""
    fanout = _RecordingFanout()
    pf = _write_require_complete_promptfile(tmp_path)
    out = tmp_path / "round-1"
    real_write_text = Path.write_text

    def tamper_after_prompt_write(path, text, *args, **kwargs):
        result = real_write_text(path, text, *args, **kwargs)
        if path.name == "prompt.txt":
            path.write_bytes(b"TAMPERED BEFORE DISPATCH")
        return result

    monkeypatch.setattr(Path, "write_text", tamper_after_prompt_write)
    monkeypatch.setattr(driver, "run_all_reviewers", fanout)
    code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out),
                        *_raw_report_id_argv(["codex", "agy"])])

    assert code == 1
    assert fanout.calls == [], "reviewers must never be dispatched against a drifted transport"
    assert not (out / "REVIEW.md").exists()


@pytest.mark.parametrize("replace_kind", ["rewrite", "truncate", "symlink"])
def test_require_complete_status_rejects_prompt_tampered_during_fanout(tmp_path, monkeypatch, replace_kind):
    """Break caught: prompt.txt survives dispatch but is replaced/truncated/
    symlinked by a reviewer while fanout is in flight. Re-checked after every
    reviewer subprocess is reaped, before REVIEW.md is published."""
    class _Tamper(_RecordingFanout):
        async def __call__(self, reviewers, prompt, models, timeout, **kwargs):
            results = await super().__call__(reviewers, prompt, models, timeout, **kwargs)
            path = kwargs["prompt_path"]
            if replace_kind == "rewrite":
                path.write_bytes(b"REPLACED CONTENT")
            elif replace_kind == "truncate":
                path.write_bytes(b"")
            elif replace_kind == "symlink":
                decoy = path.parent / "decoy.txt"
                decoy.write_bytes(b"DECOY")
                path.unlink()
                path.symlink_to(decoy)
            return results

    fanout = _Tamper()
    code, out = _run_require_complete(tmp_path, monkeypatch, fanout,
                                      extra_argv=_raw_report_id_argv(["codex", "agy"]))

    assert code == 1
    assert fanout.calls, "tampering happens mid/post-fanout, so dispatch did occur"
    assert not (out / "REVIEW.md").exists()
    assert not (out / ".REVIEW.md.tmp").exists()


def test_require_complete_status_false_does_not_recheck_transport(tmp_path, monkeypatch):
    """Regression guard: the transport re-check is opt-in only. Existing
    non-opt-in callers must be unaffected even if something rewrites prompt.txt
    mid-fanout."""
    fanout = _TamperingFanout()
    code, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert code == 0
    assert (out / "REVIEW.md").exists()


def test_review_write_failure_returns_1_without_raising(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(driver, "write_review_md",
                        lambda **kwargs: (_ for _ in ()).throw(SystemExit("disk full")))
    code, _ = _run(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout())
    assert code == 1
    assert "disk full" in capsys.readouterr().err


class _RecordingSynth:
    def __init__(self, ok=True, text=(
        "### Agreed Strengths\n- Clear API.\n\n"
        "### Agreed Concerns\n- Missing validation.\n\n"
        "### Divergent Views\n- None.\n"
    ), err="", raises=None):
        self.ok, self.text, self.err, self.raises = ok, text, err, raises
        self.calls = []

    async def __call__(self, cli, body, nonce, model=None, timeout=None, task=None):
        self.calls.append({"cli": cli, "body": body, "nonce": nonce,
                           "model": model, "timeout": timeout, "task": task})
        if self.raises is not None:
            raise self.raises
        return self.ok, self.text, self.err, None, ["<default>"]


SYNTH_YAML = """\
    prompt_format_version: 2
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
    assert "Missing validation." in text


def test_synthesis_frontmatter_records_attribution(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert "synthesizer: claude" in text
    assert "synthesized_at: " in text


def test_empty_synthesis_is_rejected_before_publication(tmp_path, monkeypatch):
    synth = _RecordingSynth(ok=True, text="")
    _, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML,
                             _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert "synthesizer: claude" not in text
    assert "Consensus synthesis failed" in text


def test_synthesis_receives_model_and_timeout(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML + "    models: {claude: opus}\n",
                    _RecordingFanout(), synth, extra_argv=["--timeout", "600"])
    assert synth.calls[0]["model"] == "opus"
    assert synth.calls[0]["timeout"] == 600
    assert synth.calls[0]["task"] == "code"


def test_synthesis_uses_only_classified_reviews(tmp_path, monkeypatch):
    # One raw-ok reviewer lacks a Summary heading, so only one qualified slot remains.
    rev = _RecordingFanout(results={
        "codex": _result("codex", ok=True, text="no heading anywhere in this body"),
    })
    synth = _RecordingSynth()
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, rev, synth)
    text = (out / "REVIEW.md").read_text()
    assert synth.calls == []
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


def test_failed_synthesis_is_reported_in_review_md(tmp_path, monkeypatch):
    """Break caught: an attempted failed synthesis was rendered as "skipped"."""
    synth = _RecordingSynth(ok=False, text="", err="synthesis timeout after 1s")
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)

    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert "Consensus synthesis failed" in text
    assert "synthesis timeout after 1s" in text
    assert "Consensus synthesis skipped" not in text


def test_failed_synthesis_diagnostic_cannot_inject_markdown_structure(tmp_path, monkeypatch):
    synth = _RecordingSynth(ok=False, text="", err="bad` detail\n## forged heading")
    _, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)

    text = (out / "REVIEW.md").read_text()
    assert 'Diagnostic: "bad` detail\\n## forged heading"' in text
    assert text.count("## forged heading") == 1


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


def test_keyboard_interrupt_from_asyncio_run_returns_1_and_releases_claim(tmp_path, monkeypatch):
    """asyncio.run translates a real fanout SIGINT into KeyboardInterrupt."""
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"

    def interrupted_run(coro):
        coro.close()
        raise KeyboardInterrupt()

    monkeypatch.setattr(driver.asyncio, "run", interrupted_run)
    try:
        code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    except KeyboardInterrupt:
        pytest.fail("KeyboardInterrupt escaped the fanout CLI boundary")

    assert code == 1
    assert not (out / ".multi-review.claim").exists()


def test_system_exit_during_startup_returns_1_and_releases_claim(tmp_path, monkeypatch):
    """A startup SIGTERM must stay inside the ``main() -> int`` boundary."""
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"

    def interrupted_claim(out_dir, claim_ref):
        out_dir.mkdir(parents=True)
        claim = out_dir / ".multi-review.claim"
        claim.touch()
        claim_ref[0] = claim
        raise SystemExit(1)

    monkeypatch.setattr(driver, "claim_output_dir_with_sigterm_mask", interrupted_claim)
    try:
        code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    except SystemExit:
        pytest.fail("SystemExit escaped the startup CLI boundary")

    assert code == 1
    assert not (out / ".multi-review.claim").exists()


def test_repeated_sigterm_requests_cancellation_only_once(tmp_path, monkeypatch):
    """A second TERM must not interrupt cleanup started by the first."""
    callbacks = {}
    started = asyncio.Event()

    class ActiveTask:
        cancel_calls = 0

        def cancel(self):
            self.cancel_calls += 1

    active_task = ActiveTask()

    async def blocking_fanout(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()

    class Prompt:
        models = {}
        task = "code"
        synthesizer = "none"
        require_complete_status = False

    async def scenario():
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(
            loop,
            "add_signal_handler",
            lambda sig, callback: callbacks.__setitem__(sig, callback),
        )
        monkeypatch.setattr(driver.asyncio, "current_task", lambda: active_task)
        monkeypatch.setattr(driver, "run_all_reviewers", blocking_fanout)
        task = asyncio.create_task(driver._amain(
            Prompt(), ["codex"], "prompt", tmp_path / "prompt.txt",
            tmp_path, None, tmp_path / "prompt.yaml",
        ))
        await started.wait()

        callbacks[signal.SIGTERM]()
        callbacks[signal.SIGTERM]()

        assert active_task.cancel_calls == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_sigterm_during_report_rendering_returns_1_without_publishing_review(tmp_path, monkeypatch):
    """Break caught: a queued SIGTERM was ignored after the last await in _amain."""
    def interrupted_write(**kwargs):
        kwargs["path"].write_text("incomplete")
        os.kill(os.getpid(), driver.signal.SIGTERM)

    monkeypatch.setattr(driver, "write_review_md", interrupted_write)
    code, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())

    assert code == 1
    assert not (out / "REVIEW.md").exists()


def test_sigint_during_report_rendering_returns_1_without_publishing_review(tmp_path, monkeypatch):
    """Ctrl-C during synchronous rendering must not publish a cancelled run."""
    def interrupted_write(**kwargs):
        kwargs["path"].write_text("incomplete")
        os.kill(os.getpid(), driver.signal.SIGINT)

    monkeypatch.setattr(driver, "write_review_md", interrupted_write)
    try:
        code, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    except KeyboardInterrupt:
        pytest.fail("SIGINT escaped after report publication")

    assert code == 1
    assert not (out / "REVIEW.md").exists()


def test_sigterm_queued_before_report_handler_handoff_returns_1(tmp_path, monkeypatch):
    """Break caught: removing asyncio's handler discarded a pending SIGTERM."""
    async def fanout_then_signal(*args, **kwargs):
        loop = asyncio.get_running_loop()
        active_task = asyncio.current_task()
        assert active_task is not None
        loop.call_soon(active_task.cancel)
        return [_result("codex")]

    code, out = _run(tmp_path, monkeypatch, BASE_YAML, fanout_then_signal)

    assert code == 1
    assert not (out / "REVIEW.md").exists()


@pytest.mark.skipif(not hasattr(signal, "pthread_sigmask"), reason="requires POSIX signals")
def test_sigterm_queued_during_report_handler_handoff_returns_1(tmp_path, monkeypatch):
    """Break caught: a self-pipe SIGTERM was discarded while changing handlers."""
    real_install = driver.install_report_signal_handlers

    def queue_sigterm_before_install(loop, out_dir):
        os.kill(os.getpid(), signal.SIGTERM)
        return real_install(loop, out_dir)

    monkeypatch.setattr(driver, "install_report_signal_handlers", queue_sigterm_before_install)
    code, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())

    assert code == 1
    assert not (out / "REVIEW.md").exists()


def test_sigterm_immediately_after_report_publication_removes_review(tmp_path, monkeypatch):
    """Break caught: cancellation queued after replace was never observed."""
    real_replace = Path.replace

    def interrupted_replace(path, target):
        result = real_replace(path, target)
        if path.name == ".REVIEW.md.tmp":
            os.kill(os.getpid(), driver.signal.SIGTERM)
        return result

    monkeypatch.setattr(Path, "replace", interrupted_replace)
    code, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())

    assert code == 1
    assert not (out / "REVIEW.md").exists()


def test_sigint_immediately_after_report_publication_removes_review(tmp_path, monkeypatch):
    """Ctrl-C after replace must remove the just-published report."""
    real_replace = Path.replace

    def interrupted_replace(path, target):
        result = real_replace(path, target)
        if path.name == ".REVIEW.md.tmp":
            os.kill(os.getpid(), driver.signal.SIGINT)
        return result

    monkeypatch.setattr(Path, "replace", interrupted_replace)
    try:
        code, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    except KeyboardInterrupt:
        pytest.fail("SIGINT escaped after publishing REVIEW.md")

    assert code == 1
    assert not (out / "REVIEW.md").exists()


def test_main_restores_caller_signal_handlers_after_success(tmp_path, monkeypatch):
    """An embedded run must not retain handlers that can delete its finished report."""
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    monkeypatch.setattr(driver, "run_all_reviewers", _RecordingFanout())

    def caller_sigterm(_signum, _frame):
        pass

    def caller_sigint(_signum, _frame):
        pass

    prior_sigterm = signal.signal(signal.SIGTERM, caller_sigterm)
    prior_sigint = signal.signal(signal.SIGINT, caller_sigint)
    try:
        code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])

        assert code == 0
        assert signal.getsignal(signal.SIGTERM) is caller_sigterm
        assert signal.getsignal(signal.SIGINT) is caller_sigint
        assert (out / "REVIEW.md").exists()
    finally:
        signal.signal(signal.SIGTERM, prior_sigterm)
        signal.signal(signal.SIGINT, prior_sigint)


def test_main_restores_signal_handlers_when_claim_cleanup_fails(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    monkeypatch.setattr(driver, "run_all_reviewers", _RecordingFanout())
    real_unlink = Path.unlink

    def failed_claim_cleanup(path, *args, **kwargs):
        if path.name == ".multi-review.claim":
            raise OSError("claim cleanup failed")
        return real_unlink(path, *args, **kwargs)

    def caller_sigterm(_signum, _frame):
        pass

    def caller_sigint(_signum, _frame):
        pass

    monkeypatch.setattr(Path, "unlink", failed_claim_cleanup)
    prior_sigterm = signal.signal(signal.SIGTERM, caller_sigterm)
    prior_sigint = signal.signal(signal.SIGINT, caller_sigint)
    try:
        with pytest.raises(OSError, match="claim cleanup failed"):
            driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])

        assert signal.getsignal(signal.SIGTERM) is caller_sigterm
        assert signal.getsignal(signal.SIGINT) is caller_sigint
    finally:
        signal.signal(signal.SIGTERM, prior_sigterm)
        signal.signal(signal.SIGINT, prior_sigint)


def test_cli_keeps_report_signal_handler_until_process_exit(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    monkeypatch.setattr(driver, "run_all_reviewers", _RecordingFanout())
    prior_sigterm = signal.getsignal(signal.SIGTERM)
    prior_sigint = signal.getsignal(signal.SIGINT)
    try:
        code = driver.cli(["--prompt-file", str(pf), "--out-dir", str(out)])

        assert code == 0
        report_handler = signal.getsignal(signal.SIGTERM)
        assert callable(report_handler)
        with pytest.raises(SystemExit) as exc:
            report_handler(signal.SIGTERM, None)
        assert exc.value.code == 1
        assert not (out / "REVIEW.md").exists()
    finally:
        signal.signal(signal.SIGTERM, prior_sigterm)
        signal.signal(signal.SIGINT, prior_sigint)


def test_sigterm_after_event_loop_closes_removes_review_and_exits_1(tmp_path, monkeypatch):
    handlers = []

    def record_handler(sig, handler):
        handlers.append((sig, handler))
        return driver.signal.getsignal(sig)

    monkeypatch.setattr(driver.signal, "signal", record_handler)
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    monkeypatch.setattr(driver, "run_all_reviewers", _RecordingFanout())
    prior_sigterm_handler = signal.getsignal(signal.SIGTERM)
    try:
        code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])

        assert code == 0
        report_handler = [
            handler for sig, handler in handlers
            if sig == driver.signal.SIGTERM and callable(handler)
        ][-1]
        with pytest.raises(SystemExit) as exc:
            report_handler(driver.signal.SIGTERM, None)
        assert exc.value.code == 1
    finally:
        signal.signal(signal.SIGTERM, prior_sigterm_handler)
    assert not (out / "REVIEW.md").exists()


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT], ids=["sigterm", "sigint"])
def test_signal_to_real_driver_kills_direct_reviewer_and_publishes_no_review(tmp_path, signum):
    """Break caught: driver cancellation could regress without exercising a real child process."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    reviewer_pid = tmp_path / "reviewer.pid"
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$$\" > \"$REVIEWER_PID_FILE\"\nexec /bin/sleep 30\n"
    )
    fake_claude.chmod(0o755)
    prompt_file = _write_promptfile(
        tmp_path, BASE_YAML.replace("reviewers: [codex]", "reviewers: [claude]")
    )
    out = tmp_path / "round-1"
    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "multi_review.py"),
         "--prompt-file", str(prompt_file), "--out-dir", str(out)],
        env={
            **os.environ,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            "REVIEWER_PID_FILE": str(reviewer_pid),
        },
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child_pid = None
    try:
        deadline = time.monotonic() + 5
        while not reviewer_pid.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert reviewer_pid.exists(), "fake reviewer did not start"
        child_pid = int(reviewer_pid.read_text().strip())

        proc.send_signal(signum)
        assert proc.wait(timeout=5) == 1
        assert not (out / "REVIEW.md").exists()

        deadline = time.monotonic() + 2
        while Path(f"/proc/{child_pid}").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not Path(f"/proc/{child_pid}").exists()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        if child_pid is not None and Path(f"/proc/{child_pid}").exists():
            os.kill(child_pid, signal.SIGKILL)


def test_sigterm_handler_is_installed_synchronously(tmp_path, monkeypatch):
    installed = []

    real_signal = driver.signal.signal

    def recording_signal(sig, handler):
        installed.append(sig)
        return real_signal(sig, handler)

    monkeypatch.setattr(driver.signal, "signal", recording_signal)
    _run(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout())
    assert driver.signal.SIGTERM in installed
