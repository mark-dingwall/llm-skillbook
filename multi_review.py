#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.7"]
# ///
"""multi-review — standalone cross-AI peer review.

Runs the same review prompt through multiple AI CLIs in parallel (claude,
gemini, codex, opencode), aggregates output into REVIEW.md, and optionally
synthesises a consensus section. Different models surface different blind
spots; a prompt that survives 2-3 independents is more robust.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

__version__ = "0.1.0"

HARVEST_SCHEMA_VERSION = 1
FAILURE_MIN_BYTES = 50
DEFAULT_SYNTHESIZER = "claude"
DEFAULT_OUTPUT = Path("REVIEW.md")
STDERR_TAIL_CHARS = 2000
# asyncio's default StreamReader limit is 64 KiB; gemini stream-json can emit
# cumulative assistant messages larger than that, raising LimitOverrunError /
# ValueError("Separator is not found, and chunk exceed the limit") on readline.
STREAM_BUFFER_LIMIT = 64 * 1024 * 1024

# -------- Reviewers module (extracted to multi_review/core/reviewers.py) --------

from multi_review.core.reviewers import (  # noqa: E402
    ALL_REVIEWERS,
    detect_self,
    detect_available,
    resolve_reviewers,
    GEMINI_FALLBACK_CHAIN,
    CAPACITY_PATTERNS,
    CLI_SPEC,
    build_command,
    make_adapter,
)

# -------- Prompt module (extracted to multi_review/core/prompt.py) --------

from multi_review.core.prompt import (  # noqa: E402
    TEMPLATES,
    SUMMARY_HEADING_CONTRACT,
    injection_preamble,
    reference_preamble,
    synthesis_prompt,
    build_prompt,
)


# -------- Progress adapters (re-exported from multi_review.core.adapters) --------

from multi_review.core.adapters import (  # noqa: E402
    Usage,
    ProgressAdapter,
    ClaudeAdapter,
    GeminiAdapter,
    CodexAdapter,
    OpenCodeAdapter,
    ADAPTER_FOR,
)



def _is_capacity_failure(stderr_tail: str, text: str, pattern: "re.Pattern[str]") -> bool:
    """Capacity-class match against stderr (primary) and accumulated text
    (fallback for CLIs that surface 429 inside their event stream)."""
    if pattern.search(stderr_tail or ""):
        return True
    if text and pattern.search(text):
        return True
    return False


def resolve_chain(
    cli: str,
    model_override: str | None,
    fallback_override: list[str] | None,
    no_fallback: bool,
) -> list[str | None]:
    """Compute the model chain for a reviewer.

    - --model REVIEWER=X pins to [X] (no fallback).
    - --no-fallback truncates to the first hop only.
    - --fallback-model REVIEWER=A,B,C overrides the built-in chain.
    - Default: built-in CLI_SPEC[cli]["fallback_chain"], or [None] when empty
      (None = no model flag, CLI uses its own default).
    """
    if model_override is not None:
        return [model_override]
    chain: list[str | None]
    if fallback_override:
        chain = list(fallback_override)
    else:
        spec_chain = CLI_SPEC[cli].get("fallback_chain") or []
        chain = list(spec_chain) if spec_chain else [None]
    if no_fallback and len(chain) > 1:
        chain = chain[:1]
    return chain


# -------- Reviewer runner --------

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


async def kill_proc(proc: asyncio.subprocess.Process) -> None:
    try:
        proc.kill()
        await proc.wait()
    except ProcessLookupError:
        pass


async def _run_reviewer_attempt(
    cli: str,
    prompt: str,
    model: str | None,
    timeout: int | None,
    state: ReviewerState,
) -> ReviewerResult:
    adapter = state.adapter
    cmd = build_command(cli, model, streaming=True)
    state.status = "starting"
    state.started_at = time.time()
    state.finished_at = 0.0

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
        return ReviewerResult(cli, False, "", "", Usage(), state.elapsed, error=f"CLI not found: {e}")
    except Exception as e:
        state.status = "error"
        state.finished_at = time.time()
        return ReviewerResult(cli, False, "", "", Usage(), state.elapsed, error=str(e))

    state.status = "running"

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


async def run_reviewer(
    cli: str,
    prompt: str,
    timeout: int | None,
    state: ReviewerState,
    *,
    chain: list[str | None],
    capacity_pattern: "re.Pattern[str] | None",
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
        last = await _run_reviewer_attempt(cli, prompt, m, timeout, state)
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


# -------- Dashboard --------

STATUS_STYLE = {
    "queued": "dim",
    "starting": "cyan",
    "running": "yellow",
    "done": "green",
    "failed": "red",
    "timeout": "red",
    "error": "red",
}


def build_table(states: list[ReviewerState]) -> Table:
    tbl = Table(title="multi-review", expand=True)
    tbl.add_column("Reviewer", style="bold")
    tbl.add_column("Model")
    tbl.add_column("Status")
    tbl.add_column("In tok", justify="right")
    tbl.add_column("Out tok", justify="right")
    tbl.add_column("Tool calls", justify="right")
    tbl.add_column("Bytes", justify="right")
    tbl.add_column("Elapsed", justify="right")
    for s in states:
        u = s.adapter.usage
        status_text = Text(s.status, style=STATUS_STYLE.get(s.status, "white"))
        if s.status in ("running", "starting") and s.adapter.phase:
            status_text.append(f" · {s.adapter.phase[:24]}", style="dim")
        if s.current_model:
            model_text = Text(s.current_model)
            if len(s.attempts) > 1:
                model_text.append(f" *{len(s.attempts)}", style="dim yellow")
        else:
            model_text = Text("—", style="dim")
        tbl.add_row(
            s.cli,
            model_text,
            status_text,
            f"{u.input_tokens:,}" if u.input_tokens else "—",
            f"{u.output_tokens:,}" if u.output_tokens else "—",
            f"{u.tool_calls}" if u.tool_calls else "—",
            f"{s.adapter.bytes_seen:,}",
            f"{s.elapsed:5.1f}s",
        )
    return tbl


async def run_all_reviewers(
    reviewers: list[str],
    prompt: str,
    models: dict[str, str],
    timeout: int | None,
    console: Console,
    *,
    fallback_overrides: dict[str, list[str]] | None = None,
    no_fallback: bool = False,
) -> list[ReviewerResult]:
    states = [ReviewerState(cli=c, adapter=ADAPTER_FOR[c]()) for c in reviewers]
    fb = fallback_overrides or {}

    chains: dict[str, list[str | None]] = {}
    patterns: dict[str, "re.Pattern[str] | None"] = {}
    for c in reviewers:
        chain = resolve_chain(c, models.get(c), fb.get(c), no_fallback)
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
        )

    tasks = [asyncio.create_task(runner_for(s)) for s in states]

    try:
        with Live(build_table(states), console=console, refresh_per_second=6) as live:
            while not all(t.done() for t in tasks):
                live.update(build_table(states))
                await asyncio.sleep(0.15)
            live.update(build_table(states))
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


# -------- Synthesis --------

def build_synthesis_input(results: list[ReviewerResult]) -> tuple[str, str]:
    """Wrap each successful review in a nonce-tagged <review-NONCE> tag so the
    synthesizer treats the reviewer output as data rather than instructions.
    Returns (body, nonce) so the caller can build a matching preamble."""
    successful = [r for r in results if r.ok]
    nonce = secrets.token_hex(4)
    while any(f"</review-{nonce}>" in r.text for r in successful):
        nonce = secrets.token_hex(4)
    open_tag = f"review-{nonce}"
    close_tag = f"</review-{nonce}>"
    parts = []
    for r in successful:
        reviewer = html.escape(r.cli, quote=True)
        parts.append(f'<{open_tag} reviewer="{reviewer}">\n{r.text}\n{close_tag}\n')
    return "\n".join(parts), nonce


async def _run_synthesis_attempt(
    cli: str,
    review_body: str,
    nonce: str,
    model: str | None,
    timeout: int | None,
) -> tuple[bool, str, str, str | None]:
    prompt = synthesis_prompt(nonce) + "\n\n---\n\n" + review_body
    cmd = build_command(cli, model, streaming=False)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            limit=STREAM_BUFFER_LIMIT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as e:
        return False, "", f"synthesizer not found: {e}", None
    except Exception as e:
        return False, "", f"synthesizer launch failed: {e}", None

    try:
        if timeout is None:
            stdout_b, stderr_b = await proc.communicate(prompt.encode())
        else:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(prompt.encode()),
                timeout=timeout,
            )
    except asyncio.TimeoutError:
        await kill_proc(proc)
        return False, "", f"synthesis timeout after {timeout}s", None

    text = stdout_b.decode("utf-8", errors="replace").strip()
    err = stderr_b.decode("utf-8", errors="replace")[-STDERR_TAIL_CHARS:]
    suggested = extract_filename_from_synthesis(text)
    if suggested is not None:
        text = strip_filename_prefix(text)
    ok = proc.returncode == 0 and len(text.encode()) >= FAILURE_MIN_BYTES
    return ok, text, err, suggested if ok else None


async def run_synthesis(
    cli: str,
    review_body: str,
    nonce: str,
    model: str | None,
    timeout: int | None,
    *,
    chain: list[str | None] | None = None,
    capacity_pattern: "re.Pattern[str] | None" = None,
) -> tuple[bool, str, str, str | None, list[str]]:
    """Wraps `_run_synthesis_attempt` with a fallback chain. Returns
    (ok, text, err, suggested_filename, attempts)."""
    if chain is None:
        chain = [model]
    attempts: list[str] = []
    last: tuple[bool, str, str, str | None] = (False, "", "no synthesis attempt", None)
    for m in chain:
        label = m if m is not None else "<default>"
        attempts.append(label)
        last = await _run_synthesis_attempt(cli, review_body, nonce, m, timeout)
        ok, text, err, _ = last
        if ok:
            break
        if capacity_pattern is None:
            break
        if not _is_capacity_failure(err, text, capacity_pattern):
            break
        if text and len(text.encode()) >= FAILURE_MIN_BYTES:
            break
    ok, text, err, suggested = last
    return ok, text, err, suggested, attempts


def extract_filename_from_synthesis(text: str) -> str | None:
    """Look for `FILENAME: ...` on first non-blank line, return sanitized name."""
    if not text:
        return None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = re.match(r"^FILENAME:\s*(.+)$", line, re.IGNORECASE)
        if not m:
            return None
        return sanitize_review_filename(m.group(1))
    return None


def strip_filename_prefix(text: str) -> str:
    """Remove leading FILENAME line (and an immediately-following `---` separator)."""
    lines = text.splitlines()
    out_idx = 0
    seen_filename = False
    for i, line in enumerate(lines):
        s = line.strip()
        if not s and not seen_filename:
            continue
        if not seen_filename and re.match(r"^FILENAME:", s, re.IGNORECASE):
            seen_filename = True
            out_idx = i + 1
            continue
        if seen_filename:
            if s == "---" or s == "":
                out_idx = i + 1
                if s == "---":
                    break
                continue
            break
    return "\n".join(lines[out_idx:]).lstrip()


# -------- Filename suggestion + resolution --------

FILENAME_MAX_STEM = 80
HAIKU_PROMPT_CTX_CAP = 8 * 1024


def sanitize_review_filename(raw: str) -> str | None:
    """Sanitize untrusted model-suggested filename. Return None if unsalvageable."""
    if not raw:
        return None
    s = raw.strip()
    # strip code fences
    s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    # strip surrounding quotes (single, double, backtick)
    s = s.strip().strip("`'\"").strip()
    # strip leading "FILENAME:" or "Filename:" labels (defensive — usually pre-stripped)
    s = re.sub(r"^filename\s*[:\-]\s*", "", s, flags=re.IGNORECASE).strip()
    # take first whitespace-delimited token (filenames don't have spaces)
    s = s.split()[0] if s.split() else ""
    if not s:
        return None
    # reject path traversal / separators / absolute paths outright
    if "/" in s or "\\" in s or ".." in s or s.startswith("."):
        # allow leading-dot-only-component reject; but `.md` extension is fine inside
        if "/" in s or "\\" in s or ".." in s:
            return None
    # split off extension
    base = s
    if base.lower().endswith(".md"):
        base = base[:-3]
    elif "." in base:
        # strip any other extension entirely
        base = base.rsplit(".", 1)[0]
    # strip REVIEW- prefix if present (any case) — we'll re-add canonical
    base = re.sub(r"^review[-_]+", "", base, flags=re.IGNORECASE)
    # replace disallowed chars with -
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base)
    # collapse repeats of - and _
    base = re.sub(r"-{2,}", "-", base)
    base = re.sub(r"_{2,}", "_", base)
    # strip leading/trailing - and .
    base = base.strip("-.")
    # lowercase the slug
    base = base.lower()
    if not base:
        return None
    if len(base) > FILENAME_MAX_STEM:
        base = base[:FILENAME_MAX_STEM].rstrip("-.")
    if not base:
        return None
    return f"REVIEW-{base}.md"


async def suggest_filename_haiku(prompt: str, timeout: int | None) -> str | None:
    """One-shot non-streaming haiku call to suggest a filename. Never raises."""
    if not shutil.which("claude"):
        return None
    instruction = (
        "Suggest a short kebab-case filename describing the review request below. "
        "Output ONLY the filename, nothing else. "
        "Format: REVIEW-<short-kebab-stem>.md (max ~6 words in the stem, lowercase). "
        "No prose, no quotes, no code fences, no explanation.\n\n"
        "--- review request ---\n"
    )
    truncated = prompt[:HAIKU_PROMPT_CTX_CAP]
    stdin_payload = (instruction + truncated).encode()
    cmd = ["claude", "-p", "--model", "haiku", "--output-format", "json"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            limit=STREAM_BUFFER_LIMIT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (FileNotFoundError, OSError):
        return None
    except Exception:
        return None

    try:
        if timeout is None:
            stdout_b, _ = await proc.communicate(stdin_payload)
        else:
            stdout_b, _ = await asyncio.wait_for(
                proc.communicate(stdin_payload),
                timeout=timeout,
            )
    except asyncio.TimeoutError:
        await kill_proc(proc)
        return None
    except Exception:
        await kill_proc(proc)
        return None

    if proc.returncode != 0:
        return None
    raw = stdout_b.decode("utf-8", errors="replace").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return sanitize_review_filename(raw)
    result = obj.get("result") if isinstance(obj, dict) else None
    if not isinstance(result, str):
        return None
    return sanitize_review_filename(result)


def resolve_output_path(
    explicit: Path | None,
    suggested: str | None,
    cwd: Path,
) -> tuple[Path, str]:
    """Return (path, source) where source ∈ {'explicit','suggested','timestamp'}."""
    if explicit is not None:
        candidate = explicit
        source = "explicit"
    elif suggested:
        candidate = cwd / suggested
        source = "suggested"
    else:
        ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        candidate = cwd / f"REVIEW-{ts}.md"
        source = "timestamp"
    if not candidate.exists():
        return candidate, source
    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent
    for n in range(2, 100):
        c = parent / f"{stem}-{n}{suffix}"
        if not c.exists():
            return c, source
    raise SystemExit(f"error: too many existing files matching {candidate}")


# -------- REVIEW.md writer --------

def yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(json.dumps(i) for i in items) + "]"


def write_review_md(
    output: Path,
    task: str,
    input_files: list[Path],
    results: list[ReviewerResult],
    models: dict[str, str],
    consensus_text: str | None,
    synthesizer: str | None,
    synthesized_at: str | None,
    mode: str,
    synthesis_attempts: list[str] | None = None,
) -> None:
    succeeded = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    reviewed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    usage_block_lines = []
    for r in results:
        u = r.usage
        usage_block_lines.append(
            f"  {r.cli}: {{ input: {u.input_tokens}, output: {u.output_tokens}, "
            f"cached: {u.cached_tokens}, tool_calls: {u.tool_calls}, elapsed_s: {r.elapsed:.1f} }}"
        )

    lines = ["---"]
    lines.append(f"task: {task}")
    lines.append(f"mode: {mode}")
    lines.append(f"reviewers_succeeded: {yaml_list([r.cli for r in succeeded])}")
    lines.append(f"reviewers_failed: {yaml_list([r.cli for r in failed])}")
    lines.append(f"reviewed_at: {reviewed_at}")
    lines.append(f"files: {yaml_list([str(f) for f in input_files])}")
    if models:
        lines.append("models:")
        for k, v in models.items():
            lines.append(f"  {k}: {json.dumps(v)}")
    lines.append("usage:")
    lines.extend(usage_block_lines)
    if synthesizer and synthesized_at:
        lines.append(f"synthesizer: {synthesizer}")
        lines.append(f"synthesized_at: {synthesized_at}")

    fallback_entries: list[tuple[str, list[str], str]] = []
    for r in results:
        if r.fallback_fired and r.attempts:
            fallback_entries.append((r.cli, r.attempts, r.model_used or r.attempts[-1]))
    synthesis_walked = synthesis_attempts and len(synthesis_attempts) > 1
    if fallback_entries or synthesis_walked:
        lines.append("fallbacks:")
        for cli, attempts, used in fallback_entries:
            lines.append(f"  {cli}:")
            lines.append(f"    attempts: {yaml_list(attempts)}")
            lines.append(f"    used: {json.dumps(used)}")
        if synthesis_walked:
            assert synthesis_attempts is not None
            lines.append("  synthesis:")
            lines.append(f"    attempts: {yaml_list(synthesis_attempts)}")
            lines.append(f"    used: {json.dumps(synthesis_attempts[-1])}")
    lines.append("---")
    lines.append("")
    lines.append("# Cross-AI Review")
    lines.append("")

    for r in results:
        header = r.cli.capitalize() + " Review"
        if not r.ok:
            header += " (FAILED)"
        lines.append(f"## {header}")
        lines.append("")
        if r.ok:
            lines.append(r.text)
        else:
            lines.append(f"**Status:** failed — {r.error or 'unknown error'}")
            lines.append("")
            lines.append(f"Elapsed: {r.elapsed:.1f}s")
            if r.stderr_tail.strip():
                lines.append("")
                lines.append("Stderr tail:")
                lines.append("```")
                lines.append(r.stderr_tail.strip())
                lines.append("```")
            if r.text.strip():
                lines.append("")
                lines.append("Partial output:")
                lines.append("```")
                lines.append(r.text.strip()[:1000])
                lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Consensus Summary")
    lines.append("")
    if consensus_text:
        lines.append(consensus_text.strip())
    elif len(succeeded) < 2:
        lines.append("_Consensus: n/a (insufficient reviewers — need ≥2 successful reviews)_")
    else:
        lines.append("_Consensus synthesis skipped (run without --no-synthesize to populate)._")
    lines.append("")

    try:
        output.write_text("\n".join(lines))
    except OSError as e:
        raise SystemExit(f"Error writing {output}: {e}")


# -------- Harvest + report --------

def _iso_utc(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def derive_project(cwd: Path, override: str | None) -> str:
    """Stable project key for harvest rows.

    Precedence: explicit override > git remote origin basename > cwd basename.
    Worktrees inherit the parent repo's origin, so paired runs from
    `Guestflow-16.1/` and `Guestflow/` share one bucket.
    """
    if override:
        return override
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd, capture_output=True, text=True,
            timeout=2, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            url = out.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            for sep in ("/", ":"):
                if sep in url:
                    return url.rsplit(sep, 1)[-1]
            return url
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return cwd.name


def harvest_run(
    *,
    started_at: float,
    finished_at: float,
    mode: str,
    prompt_bytes: int,
    reviewers_succeeded: list[str],
    reviewers_failed: list[str],
    usage_by_reviewer: dict[str, dict],
    output_path: Path | None,
    output_bytes: int,
    fallback_attempts_by_reviewer: dict[str, list[str]],
    cwd: Path,
    invocation_argv: list[str],
    project_tag: str | None = None,
) -> None:
    """Append one JSONL row of run metadata to runs/runs.jsonl.

    Schema is flat for jq-friendly aggregation. Bump HARVEST_SCHEMA_VERSION
    on field rename/removal; additions are safe.
    """
    runs_dir = Path(__file__).resolve().parent / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    target = runs_dir / "runs.jsonl"

    row = {
        "schema_version": HARVEST_SCHEMA_VERSION,
        "started_at": _iso_utc(started_at),
        "finished_at": _iso_utc(finished_at),
        "wall_seconds": round(finished_at - started_at, 1),
        "mode": mode,
        "prompt_bytes": prompt_bytes,
        "cwd": str(cwd),
        "project": derive_project(cwd, project_tag),
        "reviewers_succeeded": reviewers_succeeded,
        "reviewers_failed": reviewers_failed,
        "usage": usage_by_reviewer,
        "output_path": str(output_path) if output_path else None,
        "output_bytes": output_bytes,
        "fallback_attempts": fallback_attempts_by_reviewer,
        "argv": invocation_argv,
    }

    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")


def _format_fallback_label(attempts: list[str] | None) -> str:
    if not attempts:
        return "0"
    return f"{len(attempts)} hops → {attempts[-1]}"


def render_experiments_markdown(
    rows: list[dict],
    sessions_reference_first: int,
    sessions_inline_first: int,
    next_order: str,
) -> str:
    runs_dir = Path(__file__).resolve().parent / "runs"
    notes_dir = runs_dir / "notes"

    parts: list[str] = []
    parts.append("# Inline-vs-reference comparison log\n")
    parts.append(
        "_Generated by `multi_review.py --report`. Do not edit by hand — "
        "your changes will be overwritten on the next regeneration. "
        "Source data: `runs/runs.jsonl`. Per-project narrative depth lives "
        "in `runs/notes/<project>-<YYYY-MM-DD>.md` sidecars._\n"
    )

    parts.append("## Status\n")
    parts.append(f"- sessions_reference_first: {sessions_reference_first}")
    parts.append(f"- sessions_inline_first: {sessions_inline_first}")
    parts.append(f"- **next_recommended_order: {next_order}**\n")
    parts.append(
        "Rule: `next_recommended_order` = mode whose count is lower; "
        "tie → alternate from the last-used order.\n"
    )

    parts.append("## Methodology\n")
    parts.append(
        "For a clean comparison run:\n"
        "- Run BOTH modes against identical inputs in the recommended order.\n"
        "- Wait at least 30 minutes between modes if gemini fallback fired in "
        "the first run (quota cooldown — exhaustion in run 1 cascades into "
        "run 2 and confounds the comparison).\n"
        "- Run from separate sessions when possible so cache state doesn't "
        "bias claude's tool-call behaviour.\n"
        "- The harness writes one row to `runs/runs.jsonl` per run "
        "automatically. Pass `--no-harvest` to opt out for a given run.\n"
    )

    parts.append("## Run log\n")
    parts.append(
        "| Date | Project | Mode | Order | Prompt bytes | Wall | "
        "Gemini fallback | Output bytes | OK / Total | Notes |\n"
        "|------|---------|------|-------|--------------|------|"
        "-----------------|--------------|------------|-------|"
    )
    for r in rows:
        date = r.get("started_at", "")[:10] or "n/a"
        project = r.get("project", "?")
        mode = r.get("mode", "?")
        order = r.get("_order_in_project", "?")
        pb = r.get("prompt_bytes")
        prompt_bytes = f"{pb:,}" if isinstance(pb, int) and pb > 0 else "n/a"
        wall_s = r.get("wall_seconds")
        wall = f"{wall_s:.1f}s" if isinstance(wall_s, (int, float)) else "n/a"
        gem_fb = (r.get("fallback_attempts") or {}).get("gemini")
        fb_label = _format_fallback_label(gem_fb)
        ob = r.get("output_bytes")
        output_bytes = f"{ob:,}" if isinstance(ob, int) and ob > 0 else "n/a"
        ok = len(r.get("reviewers_succeeded") or [])
        total = ok + len(r.get("reviewers_failed") or [])
        notes = (r.get("notes") or "").replace("|", "\\|").replace("\n", " ")
        parts.append(
            f"| {date} | {project} | {mode} | {order} | {prompt_bytes} | "
            f"{wall} | {fb_label} | {output_bytes} | {ok}/{total} | {notes} |"
        )
    parts.append("")

    parts.append("## Per-project narrative\n")
    by_project_dates: dict[str, set[str]] = {}
    for r in rows:
        by_project_dates.setdefault(r.get("project", "?"), set()).add(
            r.get("started_at", "")[:10]
        )
    found_any = False
    for project in sorted(by_project_dates):
        for date in sorted(by_project_dates[project]):
            if not date:
                continue
            sidecar = notes_dir / f"{project}-{date}.md"
            if sidecar.exists():
                found_any = True
                parts.append(f"### {project} ({date})\n")
                parts.append(sidecar.read_text(encoding="utf-8").strip())
                parts.append("")
    if not found_any:
        parts.append(
            "_No sidecar narrative files found in `runs/notes/`. "
            "Drop `runs/notes/<project>-<YYYY-MM-DD>.md` files to add per-run "
            "context — they're stitched in here at report time._\n"
        )

    parts.append("## Open questions\n")
    parts.append(
        "- Is the gemini-quota-cascade real or perceived? Need a session "
        "where inline runs first against fresh quota.\n"
        "- Does the diversity-of-findings benefit hold for prompts under "
        "100KB? Both Guestflow data points are large reviews.\n"
        "- Should `--mode auto` exist (run both for prompts ≥ N bytes)? "
        "Backlog candidate.\n"
    )

    return "\n".join(parts).rstrip() + "\n"


def cmd_report() -> int:
    """Read runs/runs.jsonl and emit EXPERIMENTS.md."""
    here = Path(__file__).resolve().parent
    jsonl_path = here / "runs" / "runs.jsonl"
    output_path = here / "EXPERIMENTS.md"

    if not jsonl_path.exists():
        print(
            f"No data at {jsonl_path}. Run multi-review at least once first.",
            file=sys.stderr,
        )
        return 1

    rows: list[dict] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"warning: skipping malformed row: {e}", file=sys.stderr)
    rows.sort(key=lambda r: r.get("started_at", ""))

    by_project: dict[str, list[dict]] = {}
    for r in rows:
        by_project.setdefault(r.get("project", "?"), []).append(r)
    for project_rows in by_project.values():
        project_rows.sort(key=lambda r: r.get("started_at", ""))
        for idx, r in enumerate(project_rows):
            r["_order_in_project"] = (
                "first" if idx == 0 else "second" if idx == 1 else f"#{idx + 1}"
            )

    sessions_reference_first = sum(
        1 for pr in by_project.values() if pr and pr[0].get("mode") == "reference"
    )
    sessions_inline_first = sum(
        1 for pr in by_project.values() if pr and pr[0].get("mode") == "inline"
    )
    if sessions_reference_first <= sessions_inline_first:
        next_order = "reference-first"
    else:
        next_order = "inline-first"

    md = render_experiments_markdown(
        rows=rows,
        sessions_reference_first=sessions_reference_first,
        sessions_inline_first=sessions_inline_first,
        next_order=next_order,
    )
    output_path.write_text(md, encoding="utf-8")
    print(
        f"Wrote {output_path} ({len(rows)} runs across {len(by_project)} projects)"
    )
    return 0


# -------- Argparse --------

def parse_model_overrides(values: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for v in values or []:
        if "=" not in v:
            raise SystemExit(f"--model must be <cli>=<model>, got: {v}")
        k, _, model = v.partition("=")
        if k not in ALL_REVIEWERS:
            raise SystemExit(f"--model: unknown reviewer '{k}' (valid: {','.join(ALL_REVIEWERS)})")
        out[k] = model
    return out


def parse_fallback_overrides(values: list[str] | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for v in values or []:
        if "=" not in v:
            raise SystemExit(f"--fallback-model must be <cli>=<m1>[,<m2>,...], got: {v}")
        k, _, chain = v.partition("=")
        if k not in ALL_REVIEWERS:
            raise SystemExit(f"--fallback-model: unknown reviewer '{k}' (valid: {','.join(ALL_REVIEWERS)})")
        models = [m.strip() for m in chain.split(",") if m.strip()]
        if not models:
            raise SystemExit(f"--fallback-model: empty chain for '{k}'")
        out[k] = models
    return out


def parse_args(argv: list[str]) -> argparse.Namespace:
    tasks = ",".join(TEMPLATES)
    reviewers = ",".join(ALL_REVIEWERS)
    p = argparse.ArgumentParser(
        prog="multi-review",
        description="Cross-AI peer review: run the same prompt through multiple AI CLIs in parallel.",
        epilog=(
            "Thorough mode: for high-stakes reviews, run twice against the same "
            "inputs — once with --mode inline and once with --mode reference. "
            "Each prompt shape elicits different reviewer behaviour. Each run "
            "writes a row to runs/runs.jsonl; --report regenerates EXPERIMENTS.md "
            "from that data with the next recommended ordering."
        ),
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=28),
    )
    p.add_argument("files", nargs="*", metavar="FILE",
                   help="Files to review (wrapped in <file> tags and appended to prompt)")
    p.add_argument("--task", choices=list(TEMPLATES), default="generic", metavar="TASK",
                   help=f"Preset review prompt template: {tasks} (default: generic)")
    p.add_argument("--prompt", metavar="TEXT",
                   help="Inline custom review prompt (overrides --task)")
    p.add_argument("--prompt-file", type=Path, metavar="PATH",
                   help="Read custom review prompt from file (overrides --task and --prompt)")
    p.add_argument("--context", type=Path, action="append", default=[], metavar="PATH",
                   help="Extra context file prepended to prompt, wrapped in <file> tags (repeatable)")
    p.add_argument("--reviewers", metavar="LIST",
                   help=f"Comma-separated reviewers to run, e.g. {reviewers} (default: all available)")
    p.add_argument("--skip-self", action="store_true", default=False,
                   help="If launched from an AI CLI (claude/gemini/codex/opencode, detected via env vars), "
                        "drop that CLI from the auto-resolved reviewer set. No-op when run from a plain shell "
                        "(no host detected) or when --reviewers is explicit. "
                        "Off by default — a fresh subprocess has independent context and is a valid reviewer.")
    p.add_argument("--output", type=Path, default=None, metavar="PATH",
                   help="Destination Markdown report (default: auto-named REVIEW-<slug>.md)")
    p.add_argument("--timeout", type=int, default=None, metavar="SECS",
                   help="Per-reviewer timeout in seconds; reviewer fails on exceed (default: no timeout — run to completion or Ctrl+C)")
    p.add_argument("--no-synthesize", dest="synthesize", action="store_false", default=True,
                   help="Skip the consensus-synthesis pass (default: run it when >=2 reviewers succeed)")
    p.add_argument("--synthesizer", choices=ALL_REVIEWERS, default=DEFAULT_SYNTHESIZER, metavar="REVIEWER",
                   help=f"Reviewer that runs the synthesis pass: {reviewers} (default: {DEFAULT_SYNTHESIZER})")
    p.add_argument("--model", action="append", default=[], metavar="REVIEWER=MODEL",
                   help="Per-reviewer model override, e.g. --model claude=claude-opus-4-7. "
                        "PINS the CLI to that exact model and DISABLES fallback for it. "
                        "Use --fallback-model REVIEWER=A,B,C for an explicit chain instead "
                        "(or omit --model REVIEWER to keep the built-in chain). Repeatable.")
    p.add_argument("--fallback-model", action="append", default=[], metavar="REVIEWER=A,B,C",
                   help="Override the built-in capacity-fallback chain for a CLI, e.g. "
                        "--fallback-model gemini=gemini-3.1-pro-preview,gemini-2.5-pro. Repeatable.")
    p.add_argument("--no-fallback", action="store_true",
                   help="Disable capacity-aware model fallback (gemini default chain). "
                        "Truncates each chain to its first hop.")
    p.add_argument("--mode", choices=["inline", "reference"], default="inline",
                   help="inline: file contents embedded in prompt (default). "
                        "reference: manifest of absolute paths only; model reads files via its own tools.")
    p.add_argument("--allow-missing", action="store_true",
                   help="Warn-and-skip missing input/context files instead of erroring (legacy v0.1 behaviour)")
    p.add_argument("--dry-run", action="store_true",
                   help="Assemble and print the prompt to stdout without invoking any reviewer")
    p.add_argument("--list-reviewers", action="store_true",
                   help="Print detected reviewer CLIs and self-detection result, then exit")
    p.add_argument("--no-harvest", action="store_true",
                   help="Skip writing per-run metadata row to runs/runs.jsonl (default: harvest on)")
    p.add_argument("--project-tag", default=None, metavar="NAME",
                   help="Override harvest project name "
                        "(default: git remote origin basename, fallback cwd basename)")
    p.add_argument("--report", action="store_true",
                   help="Regenerate EXPERIMENTS.md from runs/runs.jsonl and exit (no review run)")
    p.add_argument("--version", action="version", version=f"multi-review {__version__}",
                   help="Print version and exit")
    return p.parse_args(argv)


def cmd_list_reviewers(skip_self: bool = False) -> int:
    self_cli = detect_self()
    available = detect_available()
    print(f"Supported: {', '.join(ALL_REVIEWERS)}")
    print(f"Available: {', '.join(available) if available else '<none>'}")
    print(f"Self:      {self_cli or '<unknown>'}")
    print(f"Skip-self: {'on' if skip_self else 'off'}")
    effective = resolve_reviewers(
        explicit=None, skip_self=skip_self, self_cli=self_cli,
        available=set(available),
    )
    print(f"Effective: {', '.join(effective) if effective else '<none>'}")
    return 0


def print_usage_summary(results: list[ReviewerResult], console: Console) -> None:
    console.print()
    console.print("[bold]Usage summary[/bold]")
    for r in results:
        u = r.usage
        state = "OK" if r.ok else f"FAIL ({r.error})"
        console.print(
            f"  {r.cli:<10} {state:<24} in:{u.input_tokens:>7,}  out:{u.output_tokens:>6,}"
            f"  cached:{u.cached_tokens:>6,}  tools:{u.tool_calls:>3}  {r.elapsed:5.1f}s"
        )


async def async_main(args: argparse.Namespace) -> int:
    run_started_at = time.time()
    console = Console(stderr=False)
    models = parse_model_overrides(args.model)
    fallbacks = parse_fallback_overrides(args.fallback_model)
    self_cli = detect_self()
    requested = [r.strip() for r in args.reviewers.split(",")] if args.reviewers else None
    available = detect_available()
    reviewers = resolve_reviewers(
        explicit=requested, skip_self=args.skip_self, self_cli=self_cli,
        available=set(available),
    )
    unavailable = [c for c in ALL_REVIEWERS if c not in available]

    if not reviewers:
        console.print("[red]No reviewers available after filtering (availability + --skip-self).[/red]", style="red")
        console.print(f"Supported: {', '.join(ALL_REVIEWERS)}")
        console.print(f"Self:      {self_cli or '<unknown>'}")
        return 1

    input_files = [Path(f) for f in args.files]
    prompt = build_prompt(
        task=args.task,
        custom_prompt=args.prompt,
        prompt_file=args.prompt_file,
        context_files=args.context,
        files=input_files,
        allow_missing=args.allow_missing,
        mode=args.mode,
    )

    self_label = self_cli if (self_cli and self_cli != "none") else "none"
    skip_note = " (skipped)" if (args.skip_self and self_cli and self_cli not in reviewers) else ""
    status = (f"[dim]Prompt: {len(prompt):,} bytes · Reviewers: {', '.join(reviewers)} "
              f"· Self: {self_label}{skip_note}")
    if unavailable:
        status += f" · Unavailable: {', '.join(unavailable)}"
    status += "[/dim]"
    console.print(status)

    results = await run_all_reviewers(
        reviewers, prompt, models, args.timeout, console,
        fallback_overrides=fallbacks, no_fallback=args.no_fallback,
    )

    for r in results:
        if r.fallback_fired:
            console.print(
                f"[yellow]Fallback fired for {r.cli}: "
                f"walked {' → '.join(r.attempts)} (used {r.model_used}). "
                f"Stderr tail (capture for tuning): {r.stderr_tail.strip()[:200]}[/yellow]"
            )

    succeeded = [r for r in results if r.ok]
    consensus_text: str | None = None
    synthesizer_used: str | None = None
    synthesized_at: str | None = None
    synthesis_attempts: list[str] | None = None

    suggested_filename: str | None = None

    if args.synthesize and len(succeeded) >= 2:
        console.print(f"[dim]Synthesizing consensus with {args.synthesizer}...[/dim]")
        synth_body, synth_nonce = build_synthesis_input(results)
        synth_chain = resolve_chain(
            args.synthesizer, models.get(args.synthesizer),
            fallbacks.get(args.synthesizer), args.no_fallback,
        )
        synth_pattern = (
            None if (args.no_fallback or len(synth_chain) == 1)
            else CAPACITY_PATTERNS.get(args.synthesizer)
        )
        # First-hop concrete model passed for backward-compat with
        # _run_synthesis_attempt's signature; chain drives the loop.
        ok, text, err, suggested_filename, synthesis_attempts = await run_synthesis(
            args.synthesizer, synth_body, synth_nonce,
            synth_chain[0], args.timeout,
            chain=synth_chain, capacity_pattern=synth_pattern,
        )
        if ok:
            consensus_text = text
            synthesizer_used = args.synthesizer
            synthesized_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if synthesis_attempts and len(synthesis_attempts) > 1:
                console.print(
                    f"[yellow]Synthesis fallback fired: "
                    f"walked {' → '.join(synthesis_attempts)}[/yellow]"
                )
        else:
            console.print(f"[yellow]Synthesis failed: {err.strip()[:200]}[/yellow]")

    if args.output is None and consensus_text is None and suggested_filename is None:
        suggested_filename = await suggest_filename_haiku(prompt, args.timeout)

    output_path, name_source = resolve_output_path(
        args.output, suggested_filename, Path.cwd(),
    )

    if args.output is None:
        source_label = {
            "suggested": "via synthesizer" if consensus_text else "via haiku",
            "timestamp": "timestamp fallback",
        }.get(name_source, name_source)
        console.print(
            f"[dim]Suggested filename: {output_path.name} ({source_label})[/dim]"
        )
    elif output_path != args.output:
        console.print(
            f"[yellow]note: {args.output} exists; writing to {output_path.name} "
            f"to avoid overwrite[/yellow]"
        )

    write_review_md(
        output_path, args.task, input_files, results, models,
        consensus_text, synthesizer_used, synthesized_at,
        mode=args.mode,
        synthesis_attempts=synthesis_attempts,
    )

    print_usage_summary(results, console)
    console.print()
    console.print(f"[green]Wrote[/green] {output_path}  "
                  f"([bold]{len(succeeded)}[/bold]/{len(results)} reviewers succeeded)")

    if not args.no_harvest:
        try:
            output_size_bytes = 0
            try:
                output_size_bytes = output_path.stat().st_size
            except OSError:
                pass
            failed = [r for r in results if not r.ok]
            fallback_chain_walked = {
                r.cli: list(r.attempts) for r in results if r.fallback_fired
            }
            if synthesis_attempts and len(synthesis_attempts) > 1:
                fallback_chain_walked["synthesis"] = list(synthesis_attempts)
            harvest_run(
                started_at=run_started_at,
                finished_at=time.time(),
                mode=args.mode,
                prompt_bytes=len(prompt.encode("utf-8")),
                reviewers_succeeded=[r.cli for r in succeeded],
                reviewers_failed=[r.cli for r in failed],
                usage_by_reviewer={
                    r.cli: {**r.usage.as_dict(), "elapsed_s": round(r.elapsed, 1)}
                    for r in results
                },
                output_path=output_path,
                output_bytes=output_size_bytes,
                fallback_attempts_by_reviewer=fallback_chain_walked,
                cwd=Path.cwd(),
                invocation_argv=list(sys.argv),
                project_tag=args.project_tag,
            )
        except Exception as e:
            print(f"warning: harvest failed: {e}", file=sys.stderr)

    if not succeeded:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.report:
        return cmd_report()

    if not args.list_reviewers and not args.dry_run \
            and not args.files and not args.prompt and not args.prompt_file:
        parse_args(["-h"])

    if args.list_reviewers:
        return cmd_list_reviewers(skip_self=args.skip_self)

    if args.dry_run:
        models = parse_model_overrides(args.model)
        fallbacks = parse_fallback_overrides(args.fallback_model)
        self_cli = detect_self()
        requested = [r.strip() for r in args.reviewers.split(",")] if args.reviewers else None
        available = detect_available()
        reviewers = resolve_reviewers(
            explicit=requested, skip_self=args.skip_self, self_cli=self_cli,
            available=set(available),
        )
        unavailable = [c for c in ALL_REVIEWERS if c not in available]
        input_files = [Path(f) for f in args.files]
        prompt = build_prompt(
            task=args.task,
            custom_prompt=args.prompt,
            prompt_file=args.prompt_file,
            context_files=args.context,
            files=input_files,
            allow_missing=args.allow_missing,
            mode=args.mode,
        )
        print(f"Task:       {args.task}")
        print(f"Mode:       {args.mode}")
        print(f"Output:     {args.output if args.output is not None else '<auto>'}")
        print(f"Self:       {self_cli or '<none>'}")
        print(f"Reviewers:  {', '.join(reviewers) if reviewers else '<none>'}")
        if unavailable:
            print(f"Unavailable: {', '.join(unavailable)}")
        print(f"Synthesize: {args.synthesize} (via {args.synthesizer})")
        print(f"Models:     {models or '<defaults>'}")
        print(f"Fallback:   {'OFF' if args.no_fallback else 'ON'}")
        for c in reviewers:
            chain = resolve_chain(c, models.get(c), fallbacks.get(c), args.no_fallback)
            label = ", ".join(m if m is not None else "<default>" for m in chain)
            print(f"  {c}: {label}")
        print(f"Prompt:     {len(prompt)} bytes")
        print()
        print("=== PROMPT ===")
        print(prompt)
        return 0

    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
