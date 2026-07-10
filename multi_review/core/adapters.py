"""Progress adapters: parse each CLI's JSONL event stream into Usage + text.

One subclass per reviewer CLI. Keep adapters defensive — upstream event schemas
drift without notice.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from multi_review.core.prompt import SUMMARY_HEADING_RE


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    tool_calls: int = 0

    def as_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "tool_calls": self.tool_calls,
        }


class ProgressAdapter:
    """Base adapter. Subclasses parse a CLI's stdout stream into usage + text."""

    label_cols = "tokens"  # header hint for dashboard

    def __init__(self) -> None:
        self.usage = Usage()
        self.text_parts: list[str] = []
        self.bytes_seen = 0
        self.phase = "starting"
        self.last_error: str | None = None  # promoted public attribute

    def feed_line(self, line: str) -> None:
        self.bytes_seen += len(line)

    def get_response_text(self) -> str:
        return "".join(self.text_parts).strip()

    @property
    def text(self) -> str:
        return self.get_response_text()


class ClaudeAdapter(ProgressAdapter):
    def feed_line(self, line: str) -> None:
        super().feed_line(line)
        line = line.strip()
        if not line:
            return
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            return
        t = ev.get("type")
        if t == "system":
            sub = ev.get("subtype")
            if sub == "init":
                self.phase = "running"
        elif t == "stream_event":
            inner = ev.get("event", {})
            itype = inner.get("type")
            if itype == "content_block_delta":
                delta = inner.get("delta", {})
                if delta.get("type") == "text_delta":
                    # progress signal; we also collect text as fallback
                    self.text_parts.append(delta.get("text", ""))
            elif itype == "content_block_start":
                cb = inner.get("content_block", {})
                if cb.get("type") == "tool_use":
                    self.usage.tool_calls += 1
                    self.phase = f"tool:{cb.get('name', '?')}"
        elif t == "assistant":
            msg = ev.get("message", {})
            u = msg.get("usage", {})
            # Sum across turns: each turn's usage is billed independently
            # (prompt + accumulated tool results), not cumulative.
            self.usage.input_tokens += u.get("input_tokens", 0)
            self.usage.output_tokens += u.get("output_tokens", 0)
            self.usage.cached_tokens += u.get("cache_read_input_tokens", 0)
            contents = msg.get("content") or []
            final = "".join(
                c.get("text", "") for c in contents if c.get("type") == "text"
            )
            if final:
                self.text_parts = [final]
        elif t == "result":
            self.phase = "done"
            # Don't read usage from result envelope — its shape is inconsistent
            # across claude versions and would risk double-counting.
            result = ev.get("result")
            if isinstance(result, str) and result:
                self.text_parts = [result]


class AgyAdapter(ProgressAdapter):
    """Plain-text buffer for agy --print (no event stream).

    agy does not expose a JSONL --output-format. The whole stdout is the
    review body. Token telemetry is not available via --print; usage stays
    zero. v0.2.1 may probe --log-file for recoverable counters (BACKLOG).
    """
    def feed_line(self, line: str) -> None:
        super().feed_line(line)
        if not line:
            return
        if self.phase == "starting":
            self.phase = "running"
        self.text_parts.append(line + "\n")

    def get_response_text(self) -> str:
        # agy --print is agentic: it narrates its steps ("I will read the
        # file…", "I will run pytest…") before emitting the review. Trim to the
        # first review heading so that preamble doesn't pollute REVIEW.md. If no
        # heading is present (pure narration / failure), return the raw text so
        # the aggregator's ## Summary check can still demote it.
        raw = "".join(self.text_parts).strip()
        m = SUMMARY_HEADING_RE.search(raw)
        return raw[m.start():].strip() if m else raw


class CodexAdapter(ProgressAdapter):
    def feed_line(self, line: str) -> None:
        super().feed_line(line)
        line = line.strip()
        if not line:
            return
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            return
        t = ev.get("type")
        if t == "thread.started":
            self.phase = "running"
        elif t == "item.completed":
            item = ev.get("item", {})
            itype = item.get("type")
            if itype == "agent_message":
                # last agent_message wins as the final response
                self.text_parts = [item.get("text", "")]
            elif itype in ("tool_call", "function_call", "command_execution"):
                self.usage.tool_calls += 1
                self.phase = f"tool:{item.get('name') or itype}"
        elif t == "turn.completed":
            self.phase = "done"
            u = ev.get("usage") or {}
            self.usage.input_tokens = u.get("input_tokens", 0)
            self.usage.output_tokens = u.get("output_tokens", 0)
            self.usage.cached_tokens = u.get("cached_input_tokens", 0)


class OpenCodeAdapter(ProgressAdapter):
    """Parses `opencode run --format json` event stream.

    Event types: text, reasoning, tool_use, step_start, step_finish, error.
    """

    def feed_line(self, line: str) -> None:
        super().feed_line(line)
        line = line.strip()
        if not line:
            return
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            return
        t = ev.get("type")
        part = ev.get("part") or {}
        if t == "text":
            txt = part.get("text", "")
            if txt:
                self.text_parts.append(txt)
        elif t == "tool_use":
            status = (part.get("state") or {}).get("status") or part.get("status")
            if status in ("completed", "error"):
                self.usage.tool_calls += 1
            tool_name = part.get("tool") or "?"
            self.phase = f"tool:{tool_name}"
        elif t in ("step_start", "step_finish"):
            if t == "step_start":
                self.phase = "running"
            else:
                self.phase = "done"
            # opencode emits usage under part.tokens, part.usage, or ev.usage
            # depending on version; part.tokens uses {input, output, cache.read}.
            tok = part.get("tokens")
            if tok:
                self.usage.input_tokens += tok.get("input", 0)
                self.usage.output_tokens += tok.get("output", 0)
                self.usage.cached_tokens += (tok.get("cache") or {}).get("read", 0)
            else:
                u = part.get("usage") or ev.get("usage") or {}
                if u:
                    self.usage.input_tokens += u.get(
                        "input_tokens", u.get("input", 0)
                    )
                    self.usage.output_tokens += u.get(
                        "output_tokens", u.get("output", 0)
                    )
                    self.usage.cached_tokens += u.get(
                        "cached_tokens", u.get("cached", 0)
                    )
        elif t == "error":
            err = ev.get("error") or {}
            self.phase = f"error:{err.get('name', 'error')}"


ADAPTER_FOR = {
    "claude": ClaudeAdapter,
    "agy": AgyAdapter,
    "codex": CodexAdapter,
    "opencode": OpenCodeAdapter,
}

__all__ = [
    "Usage",
    "ProgressAdapter",
    "ClaudeAdapter",
    "AgyAdapter",
    "CodexAdapter",
    "OpenCodeAdapter",
    "ADAPTER_FOR",
]
