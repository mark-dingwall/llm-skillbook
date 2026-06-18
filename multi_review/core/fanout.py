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

from multi_review.core.adapters import ProgressAdapter, Usage
from multi_review.core.reviewers import (
    build_command,
    make_adapter,
)

# Dual failure threshold: captured output must be at least this many bytes for
# a zero-exit run to be considered successful. Don't lower this — both checks
# (rc==0 AND size>=threshold) have caught real breakage.
FAILURE_MIN_BYTES = 50

# Max stderr kept for failure diagnosis (chars, UTF-8 decoded).
STDERR_TAIL_CHARS = 2000

# asyncio StreamReader buffer — gemini stream-json can emit cumulative
# assistant messages larger than the 64 KiB default.
STREAM_BUFFER_LIMIT = 64 * 1024 * 1024


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
        await proc.wait()
    except ProcessLookupError:
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
) -> ReviewerResult:
    """Spawn one subprocess for cli, stream output, return ReviewerResult."""
    adapter = state.adapter
    cmd = build_command(cli, model, streaming=True)
    state.status = "starting"
    state.started_at = time.time()
    state.finished_at = 0.0
    if state_callback is not None:
        state_callback(cli, state)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            limit=STREAM_BUFFER_LIMIT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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

    state.status = "running"
    if state_callback is not None:
        state_callback(cli, state)

    if proc.stdin is not None:
        try:
            proc.stdin.write(prompt.encode())
            await proc.stdin.drain()
            proc.stdin.close()
        except (BrokenPipeError, ConnectionResetError):
            pass

    stderr_chunks: list[bytes] = []

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

    try:
        if timeout is None:
            await asyncio.gather(drain_stdout(), drain_stderr(), proc.wait())
        else:
            await asyncio.wait_for(
                asyncio.gather(drain_stdout(), drain_stderr(), proc.wait()),
                timeout=timeout,
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
    ok = (rc == 0) and (len(text.encode()) >= FAILURE_MIN_BYTES)
    state.status = "done" if ok else "failed"
    if state_callback is not None:
        state_callback(cli, state)
    err = None
    if not ok:
        if rc != 0:
            err = f"exit {rc}"
        elif len(text.encode()) < FAILURE_MIN_BYTES:
            err = f"empty output (<{FAILURE_MIN_BYTES} bytes)"
    return ReviewerResult(
        cli, ok, text, stderr_tail, adapter.usage,
        state.elapsed, error=err,
        model_used=model if model is not None else "<default>",
    )


# -------- Fan-out orchestrator --------

async def run_all_reviewers(
    reviewers: list[str],
    prompt: str,
    models: dict[str, str],
    timeout: int | None,
    *,
    state_callback: "Callable[[str, ReviewerState], None] | None" = None,
) -> list[ReviewerResult]:
    """Spawn one asyncio Task per reviewer, await all, return results.

    ``state_callback(cli, state)`` fires on each per-CLI state transition so
    callers can drive any display layer (rich.Live table, JSON file writes, etc.)
    without this function touching the console directly.
    """
    states = [ReviewerState(cli=c, adapter=make_adapter(c)) for c in reviewers]

    async def runner_for(state: ReviewerState) -> ReviewerResult:
        return await run_reviewer(
            state.cli, prompt,
            model=models.get(state.cli),
            timeout=timeout,
            state=state,
            state_callback=state_callback,
        )

    tasks = [asyncio.create_task(runner_for(s)) for s in states]

    try:
        await asyncio.gather(*tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    results = []
    for s, t in zip(states, tasks):
        try:
            res = t.result()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            s.status = "error"
            if not s.finished_at:
                s.finished_at = time.time()
            res = ReviewerResult(
                cli=s.cli, ok=False, text=s.adapter.get_response_text(),
                stderr_tail="", usage=s.adapter.usage, elapsed=s.elapsed,
                error=f"unhandled {type(exc).__name__}: {exc}",
            )
        s.result = res
        results.append(res)
    return results
