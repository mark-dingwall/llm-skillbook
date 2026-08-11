"""multi_review.core.fanout — pure async reviewer runners, no rich.Live.

Contains the core fan-out logic: spawn one subprocess per reviewer CLI,
stream JSONL output through the relevant ProgressAdapter, and collect
ReviewerResult values.

No rich.Live, no Console. UI glue (dashboard, progress table) lives in the
legacy multi_review.py script only. State updates are emitted via an optional
``state_callback`` so callers can wire any display layer they choose.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from multi_review.core.adapters import ProgressAdapter, Usage
from multi_review.core.reviewers import (
    CLI_SPEC,
    build_command,
    make_adapter,
)

# Dual failure threshold: captured output must be at least this many bytes for
# a run to be considered successful. Don't lower this — both checks (exit code
# in the CLI's success set AND size>=threshold) have caught real breakage.
FAILURE_MIN_BYTES = 50

# Max stderr kept for failure diagnosis (chars, UTF-8 decoded).
STDERR_TAIL_CHARS = 2000

# Some reviewer CLIs emit individual stream records larger than asyncio's
# 64 KiB StreamReader default.
STREAM_BUFFER_LIMIT = 64 * 1024 * 1024

# SIGKILL normally reaps immediately. Bound the exceptional wait so a broken
# subprocess watcher cannot turn a cancellation into an indefinite hang.
PROCESS_REAP_TIMEOUT = 0.1


# -------- Data types --------

@dataclass
class ReviewerResult:
    cli: str
    ok: bool
    text: str
    stderr_tail: str
    usage: Usage
    elapsed: float
    error: str | None = None
    model_used: str | None = None
    downgraded: bool = False


def reviewer_ok(cli: str, rc: "int | None", text: str) -> bool:
    """Success iff rc is in the CLI's success set AND output >= FAILURE_MIN_BYTES.
    Most CLIs succeed only on 0; pykrete also succeeds on 3 (model downgrade)."""
    return rc in CLI_SPEC[cli].get("success_exit_codes", (0,)) \
        and len(text.encode()) >= FAILURE_MIN_BYTES


@dataclass
class ReviewerState:
    cli: str
    adapter: ProgressAdapter
    status: str = "queued"
    started_at: float = 0.0
    finished_at: float = 0.0
    result: ReviewerResult | None = None
    error: str | None = None
    current_model: str | None = None

    @property
    def elapsed(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.finished_at or time.time()
        return end - self.started_at


# -------- Process helpers --------

async def kill_proc(proc: asyncio.subprocess.Process) -> None:
    try:
        proc.kill()
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(proc.wait(), timeout=PROCESS_REAP_TIMEOUT)
    except (asyncio.TimeoutError, ProcessLookupError):
        pass


# -------- Core runner --------

async def run_reviewer(
    cli: str,
    prompt: str,
    *,
    model: str | None,
    timeout: int | None,
    state: ReviewerState,
    state_callback: "Callable[[str, ReviewerState], None] | None" = None,
    prompt_path: Path | None = None,
    task: str | None = None,
) -> ReviewerResult:
    """Spawn one subprocess for cli, stream output, return ReviewerResult.

    Most CLIs receive ``prompt`` on stdin. CLIs with ``argv_file`` delivery
    (agy) instead read the prompt from ``prompt_path`` — the caller must pass
    the on-disk prompt file for those.
    """
    adapter = state.adapter
    delivery = CLI_SPEC[cli].get("prompt_delivery", "stdin")
    state.status = "starting"
    state.started_at = time.time()
    try:
        cmd = build_command(cli, model, streaming=True,
                            prompt_path=prompt_path, task=task)
    except ValueError as e:
        state.status = "error"
        state.finished_at = time.time()
        if state_callback is not None:
            state_callback(cli, state)
        return ReviewerResult(cli, False, "", "", Usage(), state.elapsed, error=str(e))
    state.finished_at = 0.0
    if state_callback is not None:
        state_callback(cli, state)

    stderr_chunks: list[bytes] = []
    deadline = time.monotonic() + timeout if timeout is not None else None
    try:
        create_process = asyncio.create_subprocess_exec(
            *cmd,
            limit=STREAM_BUFFER_LIMIT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if deadline is None:
            proc = await create_process
        else:
            proc = await asyncio.wait_for(
                create_process, timeout=max(0.0, deadline - time.monotonic()),
            )
    except asyncio.TimeoutError:
        state.status = "timeout"
        state.finished_at = time.time()
        if state_callback is not None:
            state_callback(cli, state)
        return ReviewerResult(
            cli, False, "", "", adapter.usage, state.elapsed,
            error=f"timeout after {timeout}s",
        )
    except FileNotFoundError as e:
        state.status = "error"
        state.finished_at = time.time()
        if state_callback is not None:
            state_callback(cli, state)
        return ReviewerResult(cli, False, "", "", Usage(), state.elapsed, error=f"CLI not found: {e}")
    except Exception as e:
        state.status = "error"
        state.finished_at = time.time()
        if state_callback is not None:
            state_callback(cli, state)
        return ReviewerResult(cli, False, "", "", Usage(), state.elapsed, error=str(e))

    try:
        state.status = "running"
        if state_callback is not None:
            state_callback(cli, state)

        async def drain_stdout() -> None:
            assert proc.stdout is not None
            while True:
                line = await proc.stdout.readline()
                if not line:
                    return
                try:
                    decoded = line.decode("utf-8", errors="replace")
                except Exception:
                    continue
                adapter.feed_line(decoded)

        async def drain_stderr() -> None:
            assert proc.stderr is not None
            while True:
                chunk = await proc.stderr.read(4096)
                if not chunk:
                    return
                stderr_chunks.append(chunk)

        async def run_process() -> None:
            if proc.stdin is not None:
                try:
                    if delivery == "stdin":
                        proc.stdin.write(prompt.encode())
                        await proc.stdin.drain()
                    proc.stdin.close()
                except (BrokenPipeError, ConnectionResetError):
                    pass
            await asyncio.gather(drain_stdout(), drain_stderr(), proc.wait())

        if timeout is None:
            await run_process()
        else:
            assert deadline is not None
            await asyncio.wait_for(
                run_process(), timeout=max(0.0, deadline - time.monotonic()),
            )
    except asyncio.TimeoutError:
        await kill_proc(proc)
        state.status = "timeout"
        state.finished_at = time.time()
        if state_callback is not None:
            state_callback(cli, state)
        stderr_tail = b"".join(stderr_chunks).decode("utf-8", errors="replace")[-STDERR_TAIL_CHARS:]
        return ReviewerResult(
            cli, False, adapter.get_response_text(), stderr_tail,
            adapter.usage, state.elapsed,
            error=f"timeout after {timeout}s",
        )
    except asyncio.CancelledError:
        await kill_proc(proc)
        raise
    except Exception as exc:
        await kill_proc(proc)
        state.status = "failed"
        state.finished_at = time.time()
        if state_callback is not None:
            state_callback(cli, state)
        stderr_tail = b"".join(stderr_chunks).decode("utf-8", errors="replace")[-STDERR_TAIL_CHARS:]
        return ReviewerResult(
            cli, False, adapter.get_response_text(), stderr_tail,
            adapter.usage, state.elapsed,
            error=f"{type(exc).__name__}: {exc}",
        )

    state.finished_at = time.time()
    rc = proc.returncode
    stderr_tail = b"".join(stderr_chunks).decode("utf-8", errors="replace")[-STDERR_TAIL_CHARS:]
    text = adapter.get_response_text()
    success_codes = CLI_SPEC[cli].get("success_exit_codes", (0,))
    base_ok = reviewer_ok(cli, rc, text)
    # Demote on an adapter-reported terminal error (currently only GrokAdapter
    # sets last_error, on a non-EndTurn stopReason or an {"type":"error"}
    # event) — rc+bytes alone would record a refusal/abort as a successful
    # review. No-op for every other reviewer, whose adapters never set it.
    ok = base_ok and not adapter.last_error
    downgraded = ok and rc != 0            # rc is a non-zero success code
    state.status = "done" if ok else "failed"
    if state_callback is not None:
        state_callback(cli, state)
    err = None
    if not ok:
        if adapter.last_error:
            err = adapter.last_error
        else:
            err = f"exit {rc}" if rc not in success_codes else f"empty output (<{FAILURE_MIN_BYTES} bytes)"
    if CLI_SPEC[cli].get("records_family_not_model"):
        recorded_model = f"family:{model}" if model is not None else None
    else:
        recorded_model = model if model is not None else "<default>"
    return ReviewerResult(
        cli, ok, text, stderr_tail, adapter.usage,
        state.elapsed, error=err,
        model_used=recorded_model,
        downgraded=downgraded,
    )


# -------- Fan-out orchestrator --------

async def run_all_reviewers(
    reviewers: list[str],
    prompt: str,
    models: dict[str, str],
    timeout: int | None,
    *,
    state_callback: "Callable[[str, ReviewerState], None] | None" = None,
    prompt_path: Path | None = None,
    task: str | None = None,
    result_callback: "Callable[[ReviewerResult], None] | None" = None,
) -> list[ReviewerResult]:
    """Spawn one asyncio Task per reviewer, await all, return results.

    ``state_callback(cli, state)`` fires on each per-CLI state transition so
    callers can drive any display layer (rich.Live table, JSON file writes, etc.)
    without this function touching the console directly.
    """
    states = [ReviewerState(cli=c, adapter=make_adapter(c)) for c in reviewers]

    def _notify(callback, *args) -> None:
        if callback is None:
            return
        try:
            callback(*args)
        except Exception as exc:
            asyncio.get_running_loop().call_exception_handler({
                "message": "multi-review observer callback failed",
                "exception": exc,
            })

    def _state_notify(cli: str, state: ReviewerState) -> None:
        _notify(state_callback, cli, state)

    async def runner_for(state: ReviewerState) -> ReviewerResult:
        try:
            result = await run_reviewer(
                state.cli, prompt,
                model=models.get(state.cli),
                timeout=timeout,
                state=state,
                state_callback=_state_notify,
                prompt_path=prompt_path,
                task=task,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state.status = "error"
            if not state.finished_at:
                state.finished_at = time.time()
            result = ReviewerResult(
                cli=state.cli, ok=False, text=state.adapter.get_response_text(),
                stderr_tail="", usage=state.adapter.usage, elapsed=state.elapsed,
                error=f"unhandled {type(exc).__name__}: {exc}",
            )
        state.result = result
        _notify(result_callback, result)
        return result

    tasks = [asyncio.create_task(runner_for(s)) for s in states]

    try:
        raw = await asyncio.gather(*tasks, return_exceptions=True)
    except (asyncio.CancelledError, KeyboardInterrupt):
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    results = []
    for state, item in zip(states, raw):
        if isinstance(item, ReviewerResult):
            results.append(item)
            continue
        state.status = "error"
        if not state.finished_at:
            state.finished_at = time.time()
        result = ReviewerResult(
            cli=state.cli, ok=False, text=state.adapter.get_response_text(),
            stderr_tail="", usage=state.adapter.usage, elapsed=state.elapsed,
            error=f"unhandled {type(item).__name__}: {item}",
        )
        state.result = result
        _notify(result_callback, result)
        results.append(result)
    return results
