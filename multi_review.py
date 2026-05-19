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
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

__version__ = "0.1.0"

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

# -------- Fanout module (extracted to multi_review/core/fanout.py) --------

from multi_review.core.fanout import (  # noqa: E402
    FAILURE_MIN_BYTES,
    ReviewerResult,
    ReviewerState,
    kill_proc,
    _run_reviewer_attempt,
    run_reviewer,
    run_all_reviewers as _run_all_reviewers_core,
    resolve_chain,
    _is_capacity_failure,
)

# -------- Harvest module (extracted to multi_review/core/harvest.py) --------

from multi_review.core.harvest import (  # noqa: E402
    HARVEST_SCHEMA_VERSION,
    TELEMETRY_QUALITY,
    _iso_utc,
    derive_project,
    build_row,
    harvest_run as _harvest_run_new,
    legacy_harvest_run,
)

# Shim: keep the old bare name working for any code that calls harvest_run()
# with the legacy kwargs. The v0.2 callsite below uses legacy_harvest_run().
harvest_run = legacy_harvest_run


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
    """Legacy wrapper: delegates to core fanout, drives rich.Live via state_callback."""
    # Keep a local index of states so the callback and Live loop share the same
    # objects that the core module mutates as tasks progress.
    states_by_cli: dict[str, ReviewerState] = {}

    live_ref: list["Live"] = []  # mutable cell so the callback can reach Live

    def _state_callback(cli: str, state: ReviewerState) -> None:
        states_by_cli[cli] = state
        if live_ref:
            live_ref[0].update(build_table(list(states_by_cli.values())))

    done_event = asyncio.Event()

    async def _run() -> list[ReviewerResult]:
        result = await _run_all_reviewers_core(
            reviewers, prompt, models, timeout,
            fallback_overrides=fallback_overrides,
            no_fallback=no_fallback,
            state_callback=_state_callback,
        )
        done_event.set()
        return result

    run_task = asyncio.create_task(_run())

    try:
        with Live(build_table([]), console=console, refresh_per_second=6) as live:
            live_ref.append(live)
            while not done_event.is_set():
                live.update(build_table(list(states_by_cli.values())))
                await asyncio.sleep(0.15)
            live.update(build_table(list(states_by_cli.values())))
    except (asyncio.CancelledError, KeyboardInterrupt):
        run_task.cancel()
        await asyncio.gather(run_task, return_exceptions=True)
        raise

    return await run_task


# -------- Synthesis (extracted to multi_review/core/synthesis.py) --------

from multi_review.core.synthesis import (  # noqa: E402
    build_synthesis_input,
    _run_synthesis_attempt,
    run_synthesis,
    extract_filename_from_synthesis,
    strip_filename_prefix,
    sanitize_review_filename,
    suggest_filename_haiku,
    FILENAME_MAX_STEM,
    HAIKU_PROMPT_CTX_CAP,
)

# -------- Aggregate (extracted to multi_review/core/aggregate.py) --------

from multi_review.core.aggregate import (  # noqa: E402
    resolve_output_path as _resolve_output_path_new,
    yaml_list,
    write_review_md as _write_review_md_new,
)


def resolve_output_path(
    explicit: Path | None,
    suggested: str | None,
    cwd: Path,
) -> tuple[Path, str]:
    """Return (path, source) where source ∈ {'explicit','suggested','timestamp'}.

    Compat shim over the new core module's resolve_output_path which takes a
    single candidate path. This shim resolves the candidate from args then
    delegates collision-avoidance to the core function.
    """
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
    return _resolve_output_path_new(candidate, force=False), source


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
    """Compat shim: delegates to core/aggregate.py write_review_md."""
    _write_review_md_new(
        path=output,
        results=results,
        synthesis_text=consensus_text,
        mode=mode,
        task=task,
        reviewers_attempted=[r.cli for r in results],
        input_files=input_files,
        models=models,
        synthesizer=synthesizer,
        synthesized_at=synthesized_at,
        synthesis_attempts=synthesis_attempts,
    )


# -------- Report --------

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
        synth_nonce, synth_body = build_synthesis_input(results)
        synth_chain = resolve_chain(
            args.synthesizer,
            explicit_model=models.get(args.synthesizer),
            override_chain=fallbacks.get(args.synthesizer),
            fallback_disabled=args.no_fallback,
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
            chain = resolve_chain(
                c,
                explicit_model=models.get(c),
                override_chain=fallbacks.get(c),
                fallback_disabled=args.no_fallback,
            )
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
