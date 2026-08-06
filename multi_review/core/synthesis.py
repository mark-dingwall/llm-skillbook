"""multi_review.core.synthesis — synthesis pass helpers.

Contains:
- build_synthesis_input: wrap reviewer outputs for the synthesizer prompt
- _run_synthesis_attempt: single async synthesis attempt
- run_synthesis: single synthesis attempt wrapper around _run_synthesis_attempt
- extract_filename_from_synthesis: parse FILENAME: prefix from synthesizer output
- strip_filename_prefix: remove FILENAME: line (and separator) from text
- sanitize_review_filename: validate/sanitise model-suggested filenames
- suggest_filename_haiku: one-shot haiku call for filename suggestion
"""
from __future__ import annotations

import asyncio
import html
import json
import re
import secrets
import shutil
import tempfile
from pathlib import Path

from multi_review.core.fanout import (
    STDERR_TAIL_CHARS,
    STREAM_BUFFER_LIMIT,
    ReviewerResult,
    kill_proc,
    reviewer_ok,
)
from multi_review.core.prompt import synthesis_prompt
from multi_review.core.reviewers import CLI_SPEC, build_command


# -------- Synthesis input builder --------

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


# -------- Synthesis runner --------

async def _run_synthesis_attempt(
    cli: str,
    review_body: str,
    nonce: str,
    model: str | None,
    timeout: int | None,
) -> tuple[bool, str, str, str | None]:
    prompt = synthesis_prompt(nonce) + "\n\n---\n\n" + review_body
    # argv_file delivery (agy): write the combined prompt to a temp file and
    # pass its path on argv; agy reads it itself (no stdin, avoids E2BIG).
    delivery = CLI_SPEC[cli].get("prompt_delivery", "stdin")
    tmp_path: Path | None = None
    if delivery == "argv_file":
        tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        tf.write(prompt)
        tf.close()
        tmp_path = Path(tf.name)
    try:
        cmd = build_command(cli, model, streaming=False, prompt_path=tmp_path)
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

        stdin_payload = None if delivery == "argv_file" else prompt.encode()
        try:
            if timeout is None:
                stdout_b, stderr_b = await proc.communicate(stdin_payload)
            else:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(stdin_payload),
                    timeout=timeout,
                )
        except asyncio.TimeoutError:
            await kill_proc(proc)
            return False, "", f"synthesis timeout after {timeout}s", None
        except asyncio.CancelledError:
            await kill_proc(proc)
            raise
    except ValueError as e:
        return False, "", str(e), None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    text = stdout_b.decode("utf-8", errors="replace").strip()
    err = stderr_b.decode("utf-8", errors="replace")[-STDERR_TAIL_CHARS:]
    suggested = extract_filename_from_synthesis(text)
    if suggested is not None:
        text = strip_filename_prefix(text)
    ok = reviewer_ok(cli, proc.returncode, text)
    return ok, text, err, suggested if ok else None


async def run_synthesis(
    cli: str,
    review_body: str,
    nonce: str,
    model: str | None,
    timeout: int | None,
) -> tuple[bool, str, str, str | None, list[str]]:
    """Single synthesis attempt. Returns (ok, text, err, suggested_filename, attempts)."""
    label = model if model is not None else "<default>"
    ok, text, err, suggested = await _run_synthesis_attempt(cli, review_body, nonce, model, timeout)
    return ok, text, err, suggested, [label]


# -------- Filename extraction + sanitisation --------

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


# -------- Filename sanitisation --------

FILENAME_MAX_STEM = 80


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


# -------- Filename suggestion via haiku --------

HAIKU_PROMPT_CTX_CAP = 8 * 1024


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
