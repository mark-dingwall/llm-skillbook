"""multi_review.core.fanout — pure async reviewer runners, no rich.Live.

Contains the core fan-out logic: spawn one subprocess per reviewer CLI,
stream JSONL output through the relevant ProgressAdapter, walk fallback
chains on capacity failures, and collect ReviewerResult values.

No rich.Live, no Console. UI glue (dashboard, progress table) lives in the
legacy multi_review.py script only. State updates are emitted via an optional
``state_callback`` so callers can wire any display layer they choose.
"""
from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from multi_review.core.adapters import ProgressAdapter, Usage
from multi_review.core.reviewers import (
    CAPACITY_PATTERNS,
    CLI_SPEC,
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
    attempts: list[str] = field(default_factory=list)
    fallback_fired: bool = False


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
    attempts: list[str] = field(default_factory=list)

    @property
    def elapsed(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.finished_at or time.time()
        return end - self.started_at


# -------- Chain resolution --------

def resolve_chain(
    cli: str,
    *,
    explicit_model: str | None = None,
    fallback_disabled: bool = False,
    override_chain: list[str] | None = None,
) -> list[str | None]:
    """Compute the model chain for a reviewer.

    - explicit_model pins to [model] (no fallback, regardless of fallback_disabled).
    - override_chain replaces the built-in CLI_SPEC chain entirely.
    - fallback_disabled truncates the resolved chain to its first hop.
    - Default: built-in CLI_SPEC[cli]["fallback_chain"], or [None] when empty
      (None = no model flag; CLI uses its own default).
    """
    if explicit_model is not None:
        return [explicit_model]
    chain: list[str | None]
    if override_chain:
        chain = list(override_chain)
    else:
        spec_chain = CLI_SPEC[cli].get("fallback_chain") or []
        chain = list(spec_chain) if spec_chain else [None]
    if fallback_disabled and len(chain) > 1:
        chain = chain[:1]
    return chain


# -------- Capacity failure detection --------

def _is_capacity_failure(stderr_tail: str, text: str, pattern: "re.Pattern[str]") -> bool:
    """Capacity-class match against stderr (primary) and accumulated text
    (fallback for CLIs that surface 429 inside their event stream)."""
    if pattern.search(stderr_tail or ""):
        return True
    if text and pattern.search(text):
        return True
    return False


# -------- Process helpers --------

async def kill_proc(proc: asyncio.subprocess.Process) -> None:
    try:
        proc.kill()
        await proc.wait()
    except ProcessLookupError:
        pass


# -------- Core attempt runner --------

async def _run_reviewer_attempt(
    cli: str,
    prompt: str,
    model: str | None,
    timeout: int | None,
    state: ReviewerState,
    state_callback: "Callable[[str, ReviewerState], None] | None" = None,
) -> ReviewerResult:
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
    )


# -------- Chain-walking runner --------

async def run_reviewer(
    cli: str,
    prompt: str,
    timeout: int | None,
    state: ReviewerState,
    *,
    chain: list[str | None],
    capacity_pattern: "re.Pattern[str] | None",
    state_callback: "Callable[[str, ReviewerState], None] | None" = None,
) -> ReviewerResult:
    """Walk the model chain. One spawn per hop. Stops on success, on a
    non-capacity failure, or after the chain is exhausted. capacity_pattern=
    None disables fallback semantics (single attempt only)."""
    attempts: list[str] = []
    last: ReviewerResult | None = None
    for m in chain:
        label = m if m is not None else "<default>"
        attempts.append(label)
        state.attempts = list(attempts)
        state.current_model = label
        # Fresh adapter per hop so usage/text don't leak across attempts.
        state.adapter = make_adapter(cli)
        last = await _run_reviewer_attempt(cli, prompt, m, timeout, state, state_callback)
        last.model_used = label
        last.attempts = list(attempts)
        if last.ok:
            last.fallback_fired = len(attempts) > 1
            return last
        if capacity_pattern is None:
            break
        if not _is_capacity_failure(last.stderr_tail, last.text, capacity_pattern):
            break  # real failure (auth/network/prompt) — don't burn the chain
        if last.text and len(last.text.encode()) >= FAILURE_MIN_BYTES:
            break  # mid-stream 429 with usable partial — keep it
    if last is not None:
        last.attempts = list(attempts)
        last.fallback_fired = len(attempts) > 1
    return last  # type: ignore[return-value]


# -------- Fan-out orchestrator --------

async def run_all_reviewers(
    reviewers: list[str],
    prompt: str,
    models: dict[str, str],
    timeout: int | None,
    *,
    fallback_overrides: dict[str, list[str]] | None = None,
    no_fallback: bool = False,
    state_callback: "Callable[[str, ReviewerState], None] | None" = None,
) -> list[ReviewerResult]:
    """Spawn one asyncio Task per reviewer, await all, return results.

    ``state_callback(cli, state)`` fires on each per-CLI state transition so
    callers can drive any display layer (rich.Live table, JSON file writes, etc.)
    without this function touching the console directly.
    """
    states = [ReviewerState(cli=c, adapter=make_adapter(c)) for c in reviewers]
    fb = fallback_overrides or {}

    chains: dict[str, list[str | None]] = {}
    patterns: dict[str, "re.Pattern[str] | None"] = {}
    for c in reviewers:
        chain = resolve_chain(
            c,
            explicit_model=models.get(c),
            fallback_disabled=no_fallback,
            override_chain=fb.get(c),
        )
        chains[c] = chain
        head = chain[0]
        head_label = head if head is not None else "<default>"
        for s in states:
            if s.cli == c:
                s.current_model = head_label
                break
        if no_fallback or len(chain) == 1:
            patterns[c] = None
        else:
            patterns[c] = CAPACITY_PATTERNS.get(c)

    async def runner_for(state: ReviewerState) -> ReviewerResult:
        return await run_reviewer(
            state.cli, prompt, timeout, state,
            chain=chains[state.cli],
            capacity_pattern=patterns[state.cli],
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
