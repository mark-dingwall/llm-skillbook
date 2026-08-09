#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.7", "pyyaml>=6.0"]
# ///
"""multi-review headless single-pass driver.

Runs one fan-out pass with no LLM in the loop, from any working directory:

    uv run <absolute-path-to-repo>/multi_review.py --prompt-file <yaml> --out-dir <dir>

Design: docs/superpowers/specs/2026-08-04-headless-driver-design.md

The PEP 723 header above is load-bearing: uv's project discovery runs from the
invoking cwd, so without it a run from a foreign directory resolves no
third-party dependencies at all and `import yaml` fails.

Imports below are bare names on purpose — the unit tests monkeypatch them as
module-level attributes, which dotted access would not allow.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import secrets
import signal
import sys
import time
from pathlib import Path

import yaml

from multi_review.core.aggregate import write_review_md
from multi_review.core.fanout import ReviewerResult, run_all_reviewers
from multi_review.core.prompt import build_prompt, classify_review_ok
from multi_review.core.promptfile import ValidationError, _resolve_path, load_promptfile
from multi_review.core.synthesis import build_synthesis_input, run_synthesis


def claim_output_dir(out_dir: Path) -> Path:
    """Atomically claim an otherwise-fresh output directory for one driver."""
    out_dir.mkdir(parents=True, exist_ok=True)
    claim = out_dir / ".multi-review.claim"
    claim.touch(exist_ok=False)
    try:
        if any(path != claim for path in out_dir.iterdir()):
            raise FileExistsError(out_dir)
    except OSError:
        claim.unlink(missing_ok=True)
        raise
    return claim


def abort_report_on_signal(out_dir: Path):
    """Return the report-phase TERM/INT handler for this one-shot driver."""
    def _abort(_signum, _frame) -> None:
        for path in (out_dir / ".REVIEW.md.tmp", out_dir / "REVIEW.md"):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise SystemExit(1)

    return _abort


async def install_report_signal_handlers(
    loop: asyncio.AbstractEventLoop,
    out_dir: Path,
) -> None:
    """Atomically hand TERM/INT from cancellation to report cleanup."""
    report_signals = {signal.SIGTERM, signal.SIGINT}
    abort = abort_report_on_signal(out_dir)
    if not hasattr(signal, "pthread_sigmask"):
        await asyncio.sleep(0)
        loop.remove_signal_handler(signal.SIGTERM)
        signal.signal(signal.SIGTERM, abort)
        signal.signal(signal.SIGINT, abort)
        return

    # Block future delivery before servicing asyncio's existing signal state.
    # A TERM received just before this handoff has already reached the loop's
    # self-pipe; the checkpoint below runs its cancellation callback while no
    # new TERM or INT can arrive. Only then is it safe to replace the handlers.
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, report_signals)
    try:
        # A positive delay leaves this task waiting while the selector drains
        # the existing self-pipe and runs its cancellation callback. (A zero
        # delay requeues this task ahead of that callback.)
        await asyncio.sleep(0.001)
        loop.remove_signal_handler(signal.SIGTERM)
        signal.signal(signal.SIGTERM, abort)
        signal.signal(signal.SIGINT, abort)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def claim_output_dir_with_sigterm_mask(out_dir: Path, claim_ref: list[Path | None]) -> None:
    """Claim ``out_dir`` without leaving a TERM window before cleanup owns it."""
    if not hasattr(signal, "pthread_sigmask"):
        claim_ref[0] = claim_output_dir(out_dir)
        return

    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
    try:
        claim_ref[0] = claim_output_dir(out_dir)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


async def _amain(pf, reviewers: list[str], prompt_text: str, prompt_path: Path,
                 out_dir: Path, timeout: int | None, prompt_file: Path) -> int:
    # Fanout and synthesis retain asyncio's native signal wakeup handler so a
    # TERM cancels active subprocess work and awaits its cleanup.
    loop = asyncio.get_running_loop()
    active_task = asyncio.current_task()
    assert active_task is not None
    cancellation_requested = False

    def cancel_once() -> None:
        nonlocal cancellation_requested
        if cancellation_requested:
            return
        cancellation_requested = True
        active_task.cancel()

    loop.add_signal_handler(signal.SIGTERM, cancel_once)

    def _report(result: ReviewerResult) -> None:
        print(f"[multi_review] {result.cli}: {'ok' if result.ok else 'failed'} "
              f"({result.elapsed:.1f}s) [raw]", file=sys.stderr, flush=True)

    raw_results = await run_all_reviewers(
        reviewers, prompt_text, pf.models, timeout,
        prompt_path=prompt_path, task=pf.task, result_callback=_report,
    )

    classified_results = []
    for result in raw_results:
        ok, note = classify_review_ok(result.ok, result.text)
        classified_results.append(dataclasses.replace(
            result,
            ok=ok,
            error=(result.error or note),
            stderr_tail=(f"{result.stderr_tail}\n{note}" if result.stderr_tail and note
                         else note or result.stderr_tail),
        ))

    synthesis_text = None
    synthesis_ok = False
    synthesis_error = None
    if pf.synthesizer != "none" and sum(1 for r in raw_results if r.ok) >= 2:
        body, nonce = build_synthesis_input(raw_results)
        try:
            ok, text, synthesis_error, _suggested, _attempts = await run_synthesis(
                pf.synthesizer, body, nonce,
                model=pf.models.get(pf.synthesizer), timeout=timeout,
            )
        except Exception as exc:
            # NamedTemporaryFile in _run_synthesis_attempt runs before its own
            # try block, so an OSError there can escape. Preserve the collected
            # reviewer results and write REVIEW.md even when synthesis crashes.
            ok, text, synthesis_error, _suggested, _attempts = False, "", str(exc), None, []
            print(f"[multi_review] synthesis ({pf.synthesizer}): crashed: {exc}",
                  file=sys.stderr, flush=True)
        synthesis_ok = ok
        if synthesis_ok:
            synthesis_text = text
        print(f"[multi_review] synthesis ({pf.synthesizer}): {'ok' if ok else 'failed'}",
              file=sys.stderr, flush=True)

    staged_review = out_dir / ".REVIEW.md.tmp"
    final_review = out_dir / "REVIEW.md"
    # No reviewer or synthesizer process remains at this point. Replace the
    # loop/Runner handlers with synchronous report-phase handlers, so TERM or
    # INT cannot be queued past the final event-loop checkpoint after publication.
    try:
        await install_report_signal_handlers(loop, out_dir)
        write_review_md(
            path=staged_review,
            results=classified_results,
            synthesis_text=synthesis_text,
            synthesis_error=(synthesis_error if not synthesis_ok else None),
            mode=pf.mode,
            task=pf.task,
            reviewers_attempted=reviewers,
            models=pf.models,
            prompt_file=str(prompt_file),
            synthesizer=(pf.synthesizer if synthesis_ok else None),
            synthesized_at=(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                            if synthesis_ok else None),
        )
        staged_review.replace(final_review)
    except asyncio.CancelledError:
        staged_review.unlink(missing_ok=True)
        final_review.unlink(missing_ok=True)
        raise
    except SystemExit as exc:
        staged_review.unlink(missing_ok=True)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        staged_review.unlink(missing_ok=True)
        print(f"error: cannot publish REVIEW.md: {exc}", file=sys.stderr)
        return 1
    return 0 if any(result.ok for result in classified_results) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="multi_review.py")
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=None)
    args = p.parse_args(argv)

    # Resolve once while the caller's foreign cwd is still the reference point.
    # This same absolute path drives loading, relative input resolution, and
    # REVIEW.md attribution.
    try:
        prompt_file = args.prompt_file.resolve()
    except (OSError, RuntimeError) as exc:
        print(f"error: invalid --prompt-file {args.prompt_file}: {exc}", file=sys.stderr)
        return 2

    out_dir: Path = args.out_dir
    try:
        if out_dir.exists():
            if not out_dir.is_dir():
                print(f"error: --out-dir is not a directory: {out_dir}", file=sys.stderr)
                return 2
            if any(out_dir.iterdir()):
                print(f"error: --out-dir must be empty: {out_dir}", file=sys.stderr)
                return 2
    except OSError as exc:
        print(f"error: cannot inspect --out-dir {out_dir}: {exc}", file=sys.stderr)
        return 2
    try:
        pf = load_promptfile(prompt_file)
    except (ValidationError, yaml.YAMLError, OSError) as exc:
        print(f"error: {prompt_file}: {exc}", file=sys.stderr)
        return 2
    if pf.mode == "both":
        print("error: driver takes mode inline|reference, not both", file=sys.stderr)
        return 2

    # validate() checks ALL_REVIEWERS membership but not uniqueness: [codex, codex]
    # passes today. Two concurrent run_reviewer calls for one CLI would be
    # indistinguishable in the results list and double-count toward the synthesis gate.
    reviewers = list(dict.fromkeys(pf.reviewers))

    base = prompt_file.parent

    try:
        prompt_text = build_prompt(
            task=pf.task,
            files=[_resolve_path(f, base) for f in pf.files],
            context_files=[_resolve_path(f, base) for f in pf.context_files],
            custom_prompt=pf.custom_prompt,
            mode=pf.mode,
            nonce=secrets.token_hex(4),
        )
    except SystemExit as exc:
        # build_prompt raises SystemExit on an unreadable file. Nothing has been
        # dispatched yet, so there is nothing to salvage.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    claim_ref: list[Path | None] = [None]
    async_started = False
    prior_sigterm_handler = signal.getsignal(signal.SIGTERM)

    def abort_startup_on_sigterm(_signum, _frame) -> None:
        if claim_ref[0] is not None:
            claim_ref[0].unlink(missing_ok=True)
        raise SystemExit(1)

    # Protect the claim/prompt setup interval before _amain installs asyncio's
    # active-process handler. A TERM here must not strand a claim marker.
    signal.signal(signal.SIGTERM, abort_startup_on_sigterm)
    try:
        try:
            claim_output_dir_with_sigterm_mask(out_dir, claim_ref)
            prompt_path = out_dir / "prompt.txt"
            prompt_path.write_text(prompt_text, encoding="utf-8")
        except FileExistsError:
            print(f"error: --out-dir is already claimed: {out_dir}", file=sys.stderr)
            return 2
        except OSError as exc:
            # Operational output failure, before dispatch: failed run, no traceback.
            print(f"error: cannot write driver output: {exc}", file=sys.stderr)
            return 1
        try:
            async_started = True
            return asyncio.run(_amain(pf, reviewers, prompt_text, prompt_path, out_dir,
                                      args.timeout, prompt_file))
        except asyncio.CancelledError:
            # SIGTERM during fanout or synthesis: no REVIEW.md was written; the caller
            # sees a failed round. review-loop treats any non-zero exit identically.
            return 1
    finally:
        if claim_ref[0] is not None:
            claim_ref[0].unlink(missing_ok=True)
        if not async_started:
            signal.signal(signal.SIGTERM, prior_sigterm_handler)


if __name__ == "__main__":
    sys.exit(main())
