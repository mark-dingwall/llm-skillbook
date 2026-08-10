"""tests/unit/test_fanout.py — unit tests for core/fanout.py"""
import asyncio
import sys
import pytest
from multi_review.core.fanout import (
    ReviewerResult, ReviewerState, kill_proc, run_all_reviewers, run_reviewer,
)
from multi_review.core.adapters import ClaudeAdapter, Usage


def test_run_reviewer_no_chain_walk(tmp_path, monkeypatch):
    """A 429-style failure from the subprocess produces a failed result — no second attempt."""
    script = tmp_path / "fake_cli.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('RESOURCE_EXHAUSTED: 429\\n')\n"
        "sys.exit(1)\n"
    )

    import multi_review.core.fanout as fanout_mod
    # **_ absorbs future kwargs (task=, …) — a TypeError here escapes
    # run_reviewer's ValueError-only guard and fails this test misleadingly.
    monkeypatch.setattr(fanout_mod, "build_command", lambda cli, model, **_: [sys.executable, str(script)])
    monkeypatch.setattr(fanout_mod, "make_adapter", lambda cli: ClaudeAdapter())

    state = ReviewerState(cli="claude", adapter=ClaudeAdapter())
    result = asyncio.run(
        run_reviewer("claude", "x", model=None, timeout=None, state=state)
    )
    assert result.ok is False


def test_run_reviewer_missing_config_is_failed_not_raised(monkeypatch):
    """A missing PYKRETE_CONFIG raises ValueError inside build_command; run_reviewer
    must catch it and return a failed ReviewerResult, never let it escape (it would
    otherwise blow up asyncio.gather and abort the whole fanout)."""
    monkeypatch.delenv("PYKRETE_CONFIG", raising=False)
    from multi_review.core.reviewers import make_adapter
    state = ReviewerState(cli="pykrete", adapter=make_adapter("pykrete"))
    r = asyncio.run(run_reviewer("pykrete", "p", model=None, timeout=None, state=state))
    assert r.ok is False
    assert "PYKRETE_CONFIG" in (r.error or "")   # recorded, not raised


def test_reviewer_ok_pykrete_accepts_downgrade_exit3():
    from multi_review.core.fanout import reviewer_ok
    body = "x" * 100
    assert reviewer_ok("pykrete", 3, body) is True
    assert reviewer_ok("pykrete", 0, body) is True
    assert reviewer_ok("pykrete", 1, body) is False
    assert reviewer_ok("pykrete", 4, body) is False
    assert reviewer_ok("pykrete", 0, "tiny") is False   # byte floor preserved
    assert reviewer_ok("codex", 3, body) is False        # default (0,) unchanged
    assert reviewer_ok("codex", 0, body) is True


def test_run_all_forwards_prompt_path_isolates_crashes_and_reports_results(tmp_path, monkeypatch):
    calls = []
    completed = []

    async def fake_run(cli, prompt, **kwargs):
        calls.append((cli, kwargs["prompt_path"], kwargs["task"]))
        if cli == "codex":
            raise RuntimeError("boom")
        return ReviewerResult(cli, True, "## Summary\n\n" + "x" * 60, "",
                              Usage(), 1.0)

    monkeypatch.setattr("multi_review.core.fanout.run_reviewer", fake_run)
    prompt_path = tmp_path / "prompt.txt"
    results = asyncio.run(run_all_reviewers(
        ["codex", "agy"], "prompt", {}, None,
        prompt_path=prompt_path, task="code", result_callback=completed.append,
    ))

    assert calls == [("codex", prompt_path, "code"),
                     ("agy", prompt_path, "code")]
    assert [r.cli for r in results] == ["codex", "agy"]
    assert results[0].ok is False and "boom" in (results[0].error or "")
    assert results[1].ok is True
    assert {r.cli for r in completed} == {"codex", "agy"}


def test_run_all_normalizes_independently_cancelled_reviewer(tmp_path, monkeypatch):
    sibling_completed = False

    async def fake_run(cli, prompt, **kwargs):
        nonlocal sibling_completed
        if cli == "codex":
            raise asyncio.CancelledError()
        await asyncio.sleep(0)
        sibling_completed = True
        return ReviewerResult(cli, True, "## Summary\n\n" + "x" * 60, "", Usage(), 1.0)

    monkeypatch.setattr("multi_review.core.fanout.run_reviewer", fake_run)
    results = asyncio.run(run_all_reviewers(["codex", "agy"], "prompt", {}, None))

    assert [r.cli for r in results] == ["codex", "agy"]
    assert results[0].ok is False and "CancelledError" in (results[0].error or "")
    assert results[1].ok is True
    assert sibling_completed is True


def test_run_all_outer_cancellation_cancels_and_awaits_children(monkeypatch):
    started = set()
    cancelled = set()

    async def fake_run(cli, prompt, **kwargs):
        started.add(cli)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.add(cli)
            raise

    async def scenario():
        monkeypatch.setattr("multi_review.core.fanout.run_reviewer", fake_run)
        outer = asyncio.create_task(run_all_reviewers(["codex", "agy"], "prompt", {}, None))
        while started != {"codex", "agy"}:
            await asyncio.sleep(0)
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer

    asyncio.run(scenario())
    assert cancelled == {"codex", "agy"}


def test_run_all_observer_failures_are_reported_without_affecting_results(monkeypatch):
    loop_errors = []

    def bad_state(*args):
        raise RuntimeError("state observer failed")

    def bad_result(*args):
        raise RuntimeError("result observer failed")

    async def fake_run(cli, prompt, **kwargs):
        kwargs["state_callback"](cli, kwargs["state"])
        await asyncio.sleep(0)
        return ReviewerResult(cli, True, "## Summary\n\n" + "x" * 60, "", Usage(), 1.0)

    async def scenario():
        loop = asyncio.get_running_loop()
        old_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: loop_errors.append(context))
        try:
            monkeypatch.setattr("multi_review.core.fanout.run_reviewer", fake_run)
            return await run_all_reviewers(
                ["codex", "agy"], "prompt", {}, None,
                state_callback=bad_state, result_callback=bad_result,
            )
        finally:
            loop.set_exception_handler(old_handler)

    results = asyncio.run(scenario())
    assert [r.ok for r in results] == [True, True]
    assert len(loop_errors) == 4
    assert all(error["message"] == "multi-review observer callback failed" for error in loop_errors)


def test_run_reviewer_cancellation_during_stdin_drain_kills_process(monkeypatch):
    class FakeStdin:
        def write(self, data):
            pass

        async def drain(self):
            raise asyncio.CancelledError()

        def close(self):
            pass

    class FakeProc:
        stdin = FakeStdin()

    proc = FakeProc()
    killed = []

    async def fake_create(*args, **kwargs):
        return proc

    async def fake_kill(actual_proc):
        killed.append(actual_proc)

    import multi_review.core.fanout as fanout_mod
    monkeypatch.setattr(fanout_mod, "build_command", lambda *args, **kwargs: ["fake"])
    monkeypatch.setattr(fanout_mod.asyncio, "create_subprocess_exec", fake_create)
    monkeypatch.setattr(fanout_mod, "kill_proc", fake_kill)
    state = ReviewerState(cli="codex", adapter=ClaudeAdapter())

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run_reviewer("codex", "prompt", model=None, timeout=None, state=state))
    assert killed == [proc]


def test_kill_proc_does_not_hang_when_process_wait_never_resolves():
    """Break caught: a dead child could leave cancellation waiting on proc.wait()."""
    class StuckProcess:
        def __init__(self):
            self.killed = False

        def kill(self):
            self.killed = True

        async def wait(self):
            await asyncio.Event().wait()

    process = StuckProcess()

    async def scenario():
        await asyncio.wait_for(kill_proc(process), timeout=0.2)

    asyncio.run(scenario())
    assert process.killed is True


def test_run_reviewer_timeout_covers_blocked_stdin_drain(monkeypatch):
    """Break caught: the deadline started only after prompt delivery completed."""
    class BlockingStdin:
        def write(self, data):
            pass

        async def drain(self):
            await asyncio.Event().wait()

        def close(self):
            pass

    class FakeProc:
        stdin = BlockingStdin()

    proc = FakeProc()
    killed = []

    async def fake_create(*args, **kwargs):
        return proc

    async def fake_kill(actual_proc):
        killed.append(actual_proc)

    import multi_review.core.fanout as fanout_mod
    monkeypatch.setattr(fanout_mod, "build_command", lambda *args, **kwargs: ["fake"])
    monkeypatch.setattr(fanout_mod.asyncio, "create_subprocess_exec", fake_create)
    monkeypatch.setattr(fanout_mod, "kill_proc", fake_kill)
    state = ReviewerState(cli="codex", adapter=ClaudeAdapter())

    async def scenario():
        return await asyncio.wait_for(
            run_reviewer("codex", "x" * 10_000_000, model=None, timeout=0.01, state=state),
            timeout=0.2,
        )

    result = asyncio.run(scenario())
    assert result.ok is False
    assert result.error == "timeout after 0.01s"
    assert killed == [proc]


def test_run_reviewer_timeout_covers_blocked_process_creation(monkeypatch):
    """Break caught: the deadline started only after subprocess creation."""
    async def blocked_create(*args, **kwargs):
        await asyncio.Event().wait()

    import multi_review.core.fanout as fanout_mod
    monkeypatch.setattr(fanout_mod, "build_command", lambda *args, **kwargs: ["fake"])
    monkeypatch.setattr(fanout_mod.asyncio, "create_subprocess_exec", blocked_create)
    state = ReviewerState(cli="codex", adapter=ClaudeAdapter())

    async def scenario():
        return await asyncio.wait_for(
            run_reviewer("codex", "prompt", model=None, timeout=0.01, state=state),
            timeout=0.2,
        )

    result = asyncio.run(scenario())
    assert result.ok is False
    assert result.error == "timeout after 0.01s"
    assert state.status == "timeout"
