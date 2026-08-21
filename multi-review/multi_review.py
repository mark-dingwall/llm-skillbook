#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.7", "pyyaml>=6.0"]
# ///
"""multi-review headless single-pass driver.

Runs one fan-out pass with no LLM in the loop, from any working directory:

    uv run <absolute-path-to-repo>/multi_review.py --prompt-file <yaml> --out-dir <dir>

Implementation history: docs/superpowers/plans/2026-08-04-headless-driver.md
(the linked design is historical and superseded where it conflicts with code).

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
import hashlib
import secrets
import signal
import sys
import time
from pathlib import Path

import yaml

from multi_review.core.aggregate import (
    ReviewRecordError,
    parse_qualified_review_record,
    parse_raw_report_ids,
    parse_verbatim_dispatch_header,
    write_review_md,
)
from multi_review.core.fanout import ReviewerResult, run_all_reviewers
from multi_review.core.prompt import (
    build_prompt,
    classify_review_ok,
    classify_synthesis_ok,
)
from multi_review.core.promptfile import ValidationError, _resolve_path, load_promptfile
from multi_review.core.synthesis import build_synthesis_input, run_synthesis


def _prompt_transport_digest(prompt_text: str) -> bytes:
    """Canonical digest of the prompt payload, held in trusted driver memory."""
    return hashlib.sha256(prompt_text.encode("utf-8")).digest()


def _verify_prompt_transport(prompt_path: Path, expected_digest: bytes) -> bool:
    """Re-hash the on-disk prompt transport and compare against the canonical digest.

    review-loop opt-in (require_complete_status): a reviewer subprocess could
    replace, symlink, truncate, or otherwise rewrite prompt.txt during fanout.
    Every fixed-client review derived from a drifted transport is untrustworthy,
    so the caller must fail closed rather than publish a report built on it.
    """
    try:
        on_disk = prompt_path.read_bytes()
    except OSError:
        return False
    return hashlib.sha256(on_disk).digest() == expected_digest


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
    """Claim ``out_dir`` without leaving a signal window before cleanup owns it."""
    if not hasattr(signal, "pthread_sigmask"):
        claim_ref[0] = claim_output_dir(out_dir)
        return

    previous_mask = signal.pthread_sigmask(
        signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT},
    )
    try:
        claim_ref[0] = claim_output_dir(out_dir)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


async def _amain(pf, reviewers: list[str], prompt_text: str, prompt_path: Path,
                 out_dir: Path, timeout: int | None, prompt_file: Path,
                 review_record_expectations: dict[str, dict] | None = None) -> int:
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

    # review-loop opt-in only: every other caller keeps the exact pre-existing
    # dispatch path with no transport re-check.
    prompt_digest = _prompt_transport_digest(prompt_text) if pf.require_complete_status else None
    if prompt_digest is not None and not _verify_prompt_transport(prompt_path, prompt_digest):
        print(f"[multi_review] error: prompt transport integrity check failed before dispatch: "
              f"{prompt_path}", file=sys.stderr)
        return 1

    raw_results = await run_all_reviewers(
        reviewers, prompt_text, pf.models, timeout,
        prompt_path=prompt_path, task=pf.task, result_callback=_report,
    )

    if prompt_digest is not None and not _verify_prompt_transport(prompt_path, prompt_digest):
        print(f"[multi_review] error: prompt transport integrity check failed after fan-out: "
              f"{prompt_path}", file=sys.stderr)
        (out_dir / ".REVIEW.md.tmp").unlink(missing_ok=True)
        (out_dir / "REVIEW.md").unlink(missing_ok=True)
        return 1

    classified_results = []
    review_records: dict[str, dict] = {}
    for result in raw_results:
        ok, note = classify_review_ok(result.ok, result.text)
        if ok and pf.require_complete_status:
            try:
                review_records[result.cli] = parse_qualified_review_record(
                    result.text, review_record_expectations[result.cli],
                )
            except ReviewRecordError as exc:
                ok = False
                note = str(exc)
        classified_results.append(dataclasses.replace(
            result,
            ok=ok,
            error=(result.error or note),
            stderr_tail=result.stderr_tail,
        ))

    synthesis_text = None
    synthesis_ok = False
    synthesis_error = None
    if pf.synthesizer != "none" and sum(1 for r in classified_results if r.ok) >= 2:
        body, nonce = build_synthesis_input(classified_results)
        try:
            ok, text, synthesis_error, _suggested, _attempts = await run_synthesis(
                pf.synthesizer, body, nonce,
                model=pf.models.get(pf.synthesizer), timeout=timeout, task=pf.task,
            )
        except Exception as exc:
            # NamedTemporaryFile in _run_synthesis_attempt runs before its own
            # try block, so an OSError there can escape. Preserve the collected
            # reviewer results and write REVIEW.md even when synthesis crashes.
            ok, text, synthesis_error, _suggested, _attempts = False, "", str(exc), None, []
            print(f"[multi_review] synthesis ({pf.synthesizer}): crashed: {exc}",
                  file=sys.stderr, flush=True)
        synthesis_ok, validation_error = classify_synthesis_ok(ok, text)
        if validation_error is not None:
            synthesis_error = (
                validation_error if not synthesis_error
                else f"{synthesis_error}\n{validation_error}"
            )
        if synthesis_ok:
            synthesis_text = text
        print(f"[multi_review] synthesis ({pf.synthesizer}): "
              f"{'ok' if synthesis_ok else 'failed'}",
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
            task=pf.task,
            reviewers_attempted=reviewers,
            models=pf.models,
            prompt_file=str(prompt_file),
            synthesizer=(pf.synthesizer if synthesis_ok else None),
            synthesized_at=(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                            if synthesis_ok else None),
            review_records=(review_records if pf.require_complete_status else None),
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


def _run_driver(argv: list[str] | None, *, restore_signal_handlers: bool) -> int:
    p = argparse.ArgumentParser(prog="multi_review.py")
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=None)
    # review-loop opt-in only (PromptFile.require_complete_status). Each
    # repeated CLI=ID pair is the controller-preallocated raw report ID for
    # that fixed slot — a short driver-side label, never the prompt body, so
    # this stays consistent with "prompt transport never in argv." Dispatch
    # identity fields (request_id/role/etc.) are NOT taken from argv at all —
    # they are derived from the verbatim prompt this driver actually sends
    # (see parse_verbatim_dispatch_header), so there is no second channel
    # that could drift from what was dispatched.
    p.add_argument("--raw-report-id", action="append", default=[], metavar="CLI=ID")
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
            if (out_dir / ".multi-review.claim").exists():
                print(f"error: --out-dir is already claimed: {out_dir}", file=sys.stderr)
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
    # validate() checks ALL_REVIEWERS membership but not uniqueness: [codex, codex]
    # passes today. Two concurrent run_reviewer calls for one CLI would be
    # indistinguishable in the results list and double-count toward the synthesis gate.
    reviewers = list(dict.fromkeys(pf.reviewers))

    # Fail closed on flag misuse in either direction: the raw-report-id
    # channel only makes sense paired with the opt-in that consumes it.
    raw_report_ids: dict[str, str] = {}
    if pf.require_complete_status:
        try:
            raw_report_ids = parse_raw_report_ids(args.raw_report_id, reviewers)
        except ReviewRecordError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    elif args.raw_report_id:
        print("error: --raw-report-id requires require_complete_status", file=sys.stderr)
        return 2

    base = prompt_file.parent

    try:
        prompt_text = build_prompt(
            task=pf.task,
            files=[_resolve_path(f, base) for f in pf.files],
            context_files=[_resolve_path(f, base) for f in pf.context_files],
            custom_prompt=pf.custom_prompt,
            nonce=secrets.token_hex(4),
            verbatim=pf.verbatim_custom_prompt,
        )
    except ValidationError as exc:
        # Inputs were valid when load_promptfile checked them, but path
        # resolution can fail on a later filesystem race.
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        # build_prompt raises SystemExit on an unreadable file. Nothing has been
        # dispatched yet, so there is nothing to salvage.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    review_record_expectations: dict[str, dict] | None = None
    if pf.require_complete_status:
        try:
            dispatch_header = parse_verbatim_dispatch_header(prompt_text)
        except ReviewRecordError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        review_record_expectations = {
            cli: {**dispatch_header, "raw_report_id": raw_report_ids[cli]}
            for cli in reviewers
        }

    claim_ref: list[Path | None] = [None]
    prior_sigterm_handler = signal.getsignal(signal.SIGTERM)
    prior_sigint_handler = signal.getsignal(signal.SIGINT)

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
            return asyncio.run(_amain(pf, reviewers, prompt_text, prompt_path, out_dir,
                                      args.timeout, prompt_file,
                                      review_record_expectations=review_record_expectations))
        except asyncio.CancelledError:
            # SIGTERM during fanout or synthesis: no REVIEW.md was written; the caller
            # sees a failed round. review-loop treats any non-zero exit identically.
            return 1
    except SystemExit as exc:
        # The synchronous startup SIGTERM handler raises SystemExit before
        # asyncio.run() owns signal delivery. Keep the embedded main() API's
        # integer-return contract while the outer CLI still exits with it.
        return exc.code if isinstance(exc.code, int) else 1
    except KeyboardInterrupt:
        # asyncio.run translates its first SIGINT cancellation into
        # KeyboardInterrupt after awaiting task cleanup. The same exception can
        # arrive during synchronous startup before asyncio owns signal handling.
        return 1
    finally:
        try:
            if claim_ref[0] is not None:
                claim_ref[0].unlink(missing_ok=True)
        finally:
            if restore_signal_handlers:
                signal.signal(signal.SIGTERM, prior_sigterm_handler)
                signal.signal(signal.SIGINT, prior_sigint_handler)


def main(argv: list[str] | None = None) -> int:
    """Run the driver as an embedded call and restore the caller's handlers."""
    return _run_driver(argv, restore_signal_handlers=True)


def cli(argv: list[str] | None = None) -> int:
    """Run the one-shot CLI, retaining report cleanup handlers until exit."""
    return _run_driver(argv, restore_signal_handlers=False)


if __name__ == "__main__":
    sys.exit(cli())
