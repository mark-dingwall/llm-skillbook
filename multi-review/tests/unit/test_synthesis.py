"""tests/unit/test_synthesis.py — unit tests for core/synthesis.py"""
import asyncio
import sys
import pytest
from multi_review.core.synthesis import (
    build_synthesis_input, extract_filename_from_synthesis,
    strip_filename_prefix, sanitize_review_filename, run_synthesis,
    _communicate_with_stderr_tail, _run_synthesis_attempt, suggest_filename_haiku,
)
from multi_review.core.fanout import ReviewerResult


def _r(cli: str, text: str) -> ReviewerResult:
    return ReviewerResult(
        cli=cli, ok=True, text=text, stderr_tail="",
        usage=None, elapsed=0.0,
    )


def test_build_synthesis_input_wraps_each_review():
    body, nonce = build_synthesis_input([_r("claude", "A"), _r("gemini", "B")])
    assert nonce in body
    assert "<review" in body
    assert "reviewer=" in body


def test_extract_filename_from_synthesis_finds_marker():
    text = "FILENAME: auth-review\nrest of body"
    assert extract_filename_from_synthesis(text) == "REVIEW-auth-review.md"


def test_sanitize_review_filename_rejects_path_traversal():
    assert sanitize_review_filename("../etc/passwd") is None
    assert sanitize_review_filename("review/sub") is None


def test_sanitize_review_filename_accepts_clean():
    assert sanitize_review_filename("auth-review") == "REVIEW-auth-review.md"


def test_run_synthesis_missing_config_is_failed_not_raised(monkeypatch):
    """As synthesizer, a missing PYKRETE_CONFIG must come back as a failed
    tuple — not raise ValueError out of run_synthesis (that would abort the
    whole synthesis pass instead of just recording it as a no-op)."""
    monkeypatch.delenv("PYKRETE_CONFIG", raising=False)
    ok, text, err, suggested, attempts = asyncio.run(
        run_synthesis("pykrete", "review body", "nonce123", model=None, timeout=None)
    )
    assert ok is False
    assert "PYKRETE_CONFIG" in err


def test_external_synthesis_rejects_unstructured_success_output(tmp_path, monkeypatch):
    """Break caught: a zero-exit external synthesizer could publish arbitrary prose."""
    script = tmp_path / "synth.py"
    script.write_text(
        "import sys\n"
        "sys.stdout.write('I cannot produce a consensus today. ' * 3)\n"
    )
    monkeypatch.setattr(
        "multi_review.core.synthesis.build_command",
        lambda *args, **kwargs: [sys.executable, str(script)],
    )

    ok, text, error, suggested = asyncio.run(
        _run_synthesis_attempt("codex", "review body", "nonce", None, None)
    )

    assert ok is False
    assert text.startswith("I cannot produce")
    assert "consensus sections" in error
    assert suggested is None


def test_synthesis_drains_stdout_while_writing_large_stdin():
    """A child may fill stdout before it starts reading its prompt."""
    async def scenario():
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import sys; "
            "sys.stdout.buffer.write(b'x' * 1048576); sys.stdout.buffer.flush(); "
            "data = sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(str(len(data)).encode())",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            return await asyncio.wait_for(
                _communicate_with_stderr_tail(proc, b"y" * 1048576),
                timeout=1,
            )
        finally:
            if proc.returncode is None:
                proc.kill()
                await asyncio.wait_for(proc.communicate(), timeout=1)

    stdout, stderr = asyncio.run(scenario())
    assert stdout.endswith(b"1048576")
    assert stderr == ""


def test_cancelled_synthesis_kills_child(monkeypatch):
    killed = []

    class Stream:
        async def read(self, _size=-1):
            raise asyncio.CancelledError()

    class Proc:
        stdin = None
        stdout = Stream()
        stderr = Stream()

        async def wait(self):
            await asyncio.Event().wait()

    async def fake_exec(*args, **kwargs):
        return Proc()

    async def fake_kill(proc):
        killed.append(proc)

    monkeypatch.setattr("multi_review.core.synthesis.build_command",
                        lambda *args, **kwargs: ["fake"])
    monkeypatch.setattr("multi_review.core.synthesis.asyncio.create_subprocess_exec", fake_exec)
    monkeypatch.setattr("multi_review.core.synthesis.kill_proc", fake_kill)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_run_synthesis_attempt("codex", "body", "nonce", None, None))
    assert len(killed) == 1


def test_synthesis_timeout_covers_blocked_process_creation(monkeypatch):
    """The configured budget starts before the synthesizer process launch."""
    async def blocked_create(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(
        "multi_review.core.synthesis.build_command",
        lambda *args, **kwargs: ["fake"],
    )
    monkeypatch.setattr(
        "multi_review.core.synthesis.asyncio.create_subprocess_exec",
        blocked_create,
    )

    async def scenario():
        return await asyncio.wait_for(
            _run_synthesis_attempt("codex", "body", "nonce", None, 0.01),
            timeout=0.2,
        )

    ok, text, error, suggested = asyncio.run(scenario())
    assert ok is False
    assert text == ""
    assert error == "synthesis timeout after 0.01s"
    assert suggested is None


def test_filename_suggestion_uses_bounded_stderr_drain(monkeypatch):
    """The auxiliary Claude call must not reintroduce unbounded communicate()."""
    class Proc:
        returncode = 0

    proc = Proc()
    calls = []

    async def fake_exec(*args, **kwargs):
        return proc

    async def bounded_communicate(got_proc, stdin_payload):
        calls.append((got_proc, stdin_payload))
        return b"auth-review", ""

    async def noop_kill(_proc):
        pass

    monkeypatch.setattr("multi_review.core.synthesis.shutil.which", lambda _: "claude")
    monkeypatch.setattr("multi_review.core.synthesis.asyncio.create_subprocess_exec", fake_exec)
    monkeypatch.setattr("multi_review.core.synthesis._communicate_with_stderr_tail", bounded_communicate)
    monkeypatch.setattr("multi_review.core.synthesis.kill_proc", noop_kill)

    assert asyncio.run(suggest_filename_haiku("review this", timeout=None)) == "REVIEW-auth-review.md"
    assert calls[0][0] is proc
    assert b"review this" in calls[0][1]
