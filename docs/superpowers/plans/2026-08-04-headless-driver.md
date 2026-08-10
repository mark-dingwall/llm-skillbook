# Headless Single-Pass Driver Implementation Plan

> **Completed historical plan.** The headless driver shipped through PR #1,
> merged at `6e48d3f`. Retain this plan for rationale; do not execute its
> unchecked steps against the current tree.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revive `multi_review.py` at the repo root as a headless, no-LLM-in-the-loop driver that runs one multi-review fan-out pass from an arbitrary working directory and writes `<out-dir>/REVIEW.md`.

**Architecture:** A single ~200-line script at the repo root delegates prompt loading, fan-out,
synthesis, and report writing to `multi_review.core.*` — **never** through the
`multi_review.cli.*` subprocess wrappers, which resolve `python -m` against cwd and break from a
foreign cwd. Existing core boundaries receive narrow compatibility fixes: prompt-file construction
and field types report `ValidationError`; `run_all_reviewers` accepts the on-disk prompt path, task,
and non-owning completion callbacks while isolating one reviewer cancellation; prompt-file
frontmatter is YAML-safe; and synthesis cancellation kills its child process. The reviewer CLIs
remain real subprocesses spawned by `run_reviewer`.

**Tech Stack:** Python 3.11+, `asyncio`, `argparse`, PyYAML, pytest. Run via `uv run <absolute-path>/multi_review.py`, which resolves dependencies from the script's own PEP 723 header.

**Source spec:** `docs/superpowers/specs/2026-08-04-headless-driver-design.md` (revised through 3 review rounds). Read it if any step here seems arbitrary — nearly every design choice below has a live-reproduced failure behind it.

**Reviewed plan corrections:** This plan intentionally supersedes the source spec where later plan review found incompatibilities: output-directory creation happens after validation; prompt-schema `TypeError` translation is narrow and paired with explicit schema type validation; path normalization reuses `_resolve_path`; fan-out extends/reuses `run_all_reviewers` while preserving per-reviewer cancellation isolation and current `main`'s pykrete task routing; callback failures are non-owning observer failures; classification preserves a real subprocess `error` but uses the classifier note when none exists; prompt-file attribution is absolute and YAML-safe; report-write `SystemExit` becomes return code 1; synthesis cancellation kills its child; and synthesis attribution follows `ok`, not body truthiness.

## Global Constraints

- Python `>=3.11`. Linux/WSL only (`add_signal_handler`, `/dev/stdin` assumptions already repo-wide).
- Ruff `line-length = 110`, `target-version = "py311"` (`pyproject.toml`). Keep lines under 110.
- The driver file **must** carry a PEP 723 header declaring `dependencies = ["rich>=13.7", "pyyaml>=6.0"]`. Without it, `uv run` performs project discovery from the *invoking* cwd, and `import yaml` fails from a foreign directory (live-reproduced). This is not optional polish.
- The driver's imports must be **bare names** (`from multi_review.core.fanout import run_all_reviewers`), never dotted access (`multi_review.core.fanout.run_all_reviewers(...)`) — the tests monkeypatch module-level attributes on the driver, and the dotted form leaves nothing to patch.
- `--timeout` default is `None` (repo-wide "no default timeout" invariant). It is a **per-call** budget forwarded to each `run_reviewer` and to `run_synthesis` — not one overall wall-clock cap.
- Exit codes: `0` = ≥1 **classified**-ok reviewer, `1` = none, `2` = usage/config error.
- Before SDD starts, this reviewed plan must be tracked in git. The controller must not begin from an
  untracked plan: task briefs, the recovery ledger, and final branch history all depend on it remaining
  available across the rebase and later commits.
- Baseline test command: `uv run pytest tests/ -q`. The pre-existing `PytestConfigWarning: Unknown config option: asyncio_mode` is expected and harmless — every test in this plan is a plain sync `def test_...`. Do **not** write `async def` tests here; they would be silently collected as never-run passes.
- Never edit `EXPERIMENTS.md` by hand.

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `multi_review.py` | The whole driver: argparse + validation + prompt build (`main`, sync), then shared fan-out + classify + synthesis + write (`_amain`, async). Currently a 28-line deprecation stub — fully replaced. | 1–4 |
| `tests/unit/test_multi_review_driver.py` | All driver unit tests. Loads the driver via `importlib.util.spec_from_file_location` (see Task 1 Step 1 for why a plain `import multi_review` cannot work). | 1–4 |
| `multi_review/core/promptfile.py` | Converts only `PromptFile(**raw)` constructor failures into user-facing `ValidationError`; `validate` rejects malformed field types explicitly, while internal `TypeError`s still propagate. | 1 |
| `tests/unit/test_promptfile.py` | Pins the prompt-schema error boundary and consumed-field types. | 1 |
| `multi_review/core/fanout.py` | Shared fan-out orchestration, extended with `prompt_path`/`task` forwarding, non-owning callbacks, per-reviewer cancellation isolation, and child cleanup during prompt delivery. | 2 |
| `tests/unit/test_fanout.py` | Pins shared fan-out prompt/task delivery, crash isolation, callbacks, and cancellation at both prompt delivery and process wait. | 2 |
| `multi_review/core/aggregate.py` | YAML-quotes prompt-file attribution. | 2 |
| `tests/unit/test_aggregate.py` | Pins prompt-file frontmatter round-tripping. | 2 |
| `multi_review/core/synthesis.py` | Kills an in-flight synthesizer subprocess when its task is cancelled. | 3 |
| `tests/unit/test_synthesis.py` | Pins synthesis cancellation cleanup. | 3 |
| `tests/manual/headless-driver-smoke.md` | The five required manual smoke procedures and recorded outcomes the mocked suite cannot cover. | 5 |
| `CLAUDE.md` | Document the revived entry point and add `claude -p` through this driver to the "uncontained agentic reviewer / do not point at untrusted code" list. | 5 |
| `README.md` | Replace the stale claim that `multi_review.py` is a removed/deprecated stub with the new single-pass invocation and scope. | 5 |

---

### Pre-execution SDD setup: rebase onto `main` and establish a clean baseline

**Files:**
- Modify: none (git operation only)

This is controller setup, **not an SDD implementation task**. Perform it before recording the first
task's `BASE`, generating a task brief, or dispatching an implementer. Otherwise the mandatory Task 1
review package would contain the entire upstream rebase instead of a task-scoped implementation diff.

**Interfaces:**
- Consumes: the reviewed plan already tracked in git
- Produces: a clean baseline containing `main`'s agy `bypass_perms_flag` fix and pykrete `task`
  forwarding contract, on which every implementation task builds

This branch is behind `main` and is missing the agy `bypass_perms_flag` fix. Every agy review fails on
this branch as-is. Since the spec was written, `main` also added pykrete `task` forwarding across
`spawn.py`, `fanout.py`, and `reviewers.py`; the headless driver must preserve that newer invariant.
The spec's citations are historical rationale, not post-rebase coordinates. Re-anchor any source
citation used during implementation against the rebased tree rather than applying the spec's old
fixed offsets.

- [ ] **Step 1: Confirm how far behind `main` this branch is**

```bash
git fetch --all
git log --oneline -1
git rev-list --count HEAD..main
```

Expected: a non-zero count (12 at the latest plan-review time; a different non-zero count means
`main` moved and the source-drift checks below must be repeated before continuing).

- [ ] **Step 2: Rebase**

```bash
git rebase main
```

Expected: clean. If a conflict appears, stop and report rather than resolving it inside setup.

- [ ] **Step 3: Confirm the agy fix is present**

```bash
grep -n "bypass_perms_flag" multi_review/core/reviewers.py
```

Expected: at least two hits (the spec definition and its use in `build_command`). Zero hits means the rebase did not bring in what it should have — stop and report.

- [ ] **Step 4: Confirm the pykrete task-routing contract is present**

```bash
grep -n "task: str | None" multi_review/core/fanout.py
grep -n '"task_flag": "--task"' multi_review/core/reviewers.py
```

Expected: both commands find the current-main contract. The implementation plan must extend it,
not replace it with the older pre-rebase signature.

- [ ] **Step 5: Run the baseline suite**

Run: `uv run pytest tests/ -q`
Expected: all tests pass (237 green at plan-writing time; a higher number is fine, failures are not). If anything fails **before** you have written a line of driver code, stop and report — do not build on a red baseline.

- [ ] **Step 6: Record the implementation baseline**

Do not create an empty commit. Only now record the first implementation task's `BASE` and generate
its brief/review workspace.

---

### Task 1: Driver skeleton — argv, `--out-dir` freshness, prompt-file loading, prompt build

**Files:**
- Modify: `multi_review.py` (replace the entire 28-line deprecation stub)
- Modify: `multi_review/core/promptfile.py` (`fill_defaults` exception boundary + `validate` type checks)
- Test: `tests/unit/test_multi_review_driver.py` (create)
- Test: `tests/unit/test_promptfile.py`

**Interfaces:**
- Consumes: `multi_review.core.promptfile.load_promptfile`/`ValidationError`, `multi_review.core.prompt.build_prompt`
- Produces:
  - `main(argv: list[str] | None = None) -> int` — the driver's entire callable surface. Returns `2` on usage/config errors, `1` on an unreadable input or output failure, `0` on success at this task's stage (Task 2 replaces the success return with a fan-out-driven exit code).
  - Module-level `prompt_text` is *not* produced; it is a local. The on-disk artifact `<out-dir>/prompt.txt` is what later tasks pass through `run_all_reviewers` to each `run_reviewer` call.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_multi_review_driver.py`.

The import block at the top is load-bearing and unusual. `multi_review.py` (the driver script) and `multi_review/` (the package directory) share a stem. Python's `FileFinder` prefers the **package**, so a plain `import multi_review` inside a test resolves to the package and never to the driver — verified live via `importlib.util.find_spec('multi_review').origin`. `tests/conftest.py` only prepends the repo root to `sys.path`, which does not change that. Load the driver explicitly by path instead:

```python
import importlib.util
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_driver():
    spec = importlib.util.spec_from_file_location("mr_driver", REPO_ROOT / "multi_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = _load_driver()


def _write_promptfile(tmp_path: Path, body: str) -> Path:
    """Write a prompt YAML plus the one input file it references."""
    (tmp_path / "target.py").write_text("def f():\n    return 1\n")
    pf = tmp_path / "prompt.yaml"
    pf.write_text(textwrap.dedent(body))
    return pf


BASE_YAML = """\
    prompt_format_version: 1
    task: code
    files: [target.py]
    reviewers: [codex]
    synthesizer: none
"""


def test_out_dir_created_when_missing(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert (out / "prompt.txt").exists()


def test_prompt_txt_contains_the_input_file_body(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert "return 1" in (out / "prompt.txt").read_text()


def test_non_empty_out_dir_is_rejected(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    (out / "REVIEW.md").write_text("stale")
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_empty_out_dir_is_accepted(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert (out / "prompt.txt").exists()


def test_mode_both_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML + "    mode: both\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_malformed_yaml_exits_2_without_traceback(tmp_path):
    pf = _write_promptfile(tmp_path, "    task: [unclosed\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_unknown_top_level_key_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML + "    bogus_field: 3\n")
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_missing_prompt_file_exits_2(tmp_path):
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(tmp_path / "nope.yaml"), "--out-dir", str(out)]) == 2


def test_schema_violation_exits_2(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML.replace("task: code", "task: nonsense"))
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2


def test_validation_failure_does_not_create_out_dir(tmp_path):
    pf = _write_promptfile(tmp_path, BASE_YAML.replace("task: code", "task: nonsense"))
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 2
    assert not out.exists()


def test_unreadable_input_file_exits_1(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"

    def _boom(*args, **kwargs):
        raise SystemExit("error: cannot read target.py")

    monkeypatch.setattr(driver, "build_prompt", _boom)
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_prompt_output_write_failure_exits_1_without_traceback(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    real_write_text = Path.write_text

    def _write(path, text, *args, **kwargs):
        if path.name == "prompt.txt":
            raise OSError("read-only output")
        return real_write_text(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _write)
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_argparse_usage_error_raises_systemexit(tmp_path):
    with pytest.raises(SystemExit):
        driver.main(["--prompt-file", "only-one-arg"])
```

In `tests/unit/test_promptfile.py`, change `test_dead_fallback_delay_schema_removed` and `test_legacy_delay_key_rejected` to expect `ValidationError` instead of `TypeError`, then append this boundary test:

```python
def test_internal_typeerror_is_not_relabelled_as_invalid_config(tmp_path, monkeypatch):
    src = tmp_path / "x.py"
    src.write_text("")
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(f"prompt_format_version: 1\ntask: code\nfiles: [{src}]\n")

    def _bug(*args, **kwargs):
        raise TypeError("internal bug")

    monkeypatch.setattr("multi_review.core.promptfile.validate", _bug)
    with pytest.raises(TypeError, match="internal bug"):
        load_promptfile(prompt)
```

Also add parameterized malformed-type coverage that drives `fill_defaults` + `validate` with an
otherwise-valid existing file. At minimum cover: boolean/non-integer `prompt_format_version`;
non-string `task`/`mode`/`synthesizer`/`if_drift`; scalar or non-string-member
`files`/`context_files`/`reviewers`; non-mapping or non-string-key/value `models`/`model_effort`;
non-string non-null `custom_prompt`/`output_dir`/`save_as`; and non-boolean `harvest`. Every case is
user configuration and must raise `ValidationError`, never a raw `TypeError` later in the driver.

`fill_defaults` owns the `PromptFile(**raw)` call, so it is the correct place to translate that
call's unknown-key `TypeError` into `ValidationError`. Dataclass construction does **not** enforce
annotations, so `validate` must perform the field-type checks above before membership, iteration,
path construction, or `.get()` use. The driver must not catch `TypeError` around the whole
`load_promptfile` call: doing so would misreport bugs in YAML loading, defaulting, or validation as
bad user configuration.

Note on `test_argparse_usage_error_raises_systemexit`: argparse usage errors intentionally raise. Known user-facing validation and I/O failures return an `int`; unexpected programming errors such as an internal `TypeError` intentionally propagate.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_multi_review_driver.py tests/unit/test_promptfile.py -q`
Expected: FAIL — collection error or `AttributeError`, since `multi_review.py` currently has no `build_prompt` attribute and its `main()` takes no argv.

- [ ] **Step 3: Replace `multi_review.py` with the skeleton**

Replace the file's entire contents:

```python
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
import secrets
import sys
from pathlib import Path

import yaml

from multi_review.core.prompt import build_prompt
from multi_review.core.promptfile import ValidationError, _resolve_path, load_promptfile


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="multi_review.py")
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=None)
    args = p.parse_args(argv)

    # Resolve once while the caller's foreign cwd is still the reference point.
    # This same absolute path drives loading, relative input resolution, and
    # REVIEW.md attribution.
    prompt_file = args.prompt_file.resolve()

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

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = out_dir / "prompt.txt"
        prompt_path.write_text(prompt_text)
    except OSError as exc:
        # Operational output failure, before dispatch: failed run, no traceback.
        print(f"error: cannot write driver output: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`reviewers` is unused at this stage — Task 2 consumes it. Leave it; do not "clean it up".

In `multi_review/core/promptfile.py`, replace the last line of `fill_defaults` with the narrow constructor boundary:

```python
    try:
        return PromptFile(**raw)
    except TypeError as exc:
        raise ValidationError(str(exc)) from exc
```

At the top of `validate`, add the explicit schema type checks listed in Step 1. Use exact boolean and
integer checks where Python's `bool`-is-an-`int` relationship would otherwise accept the wrong YAML
type. These checks are part of the public prompt-file boundary, not defensive checks in the driver.

Do not add broad cleanup of a failed output directory. The caller owns a unique directory per round,
and deleting an existing path is outside the driver's authority; a failed attempt remains failed and
the caller retries with a fresh directory.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_multi_review_driver.py tests/unit/test_promptfile.py -q`
Expected: PASS (12 driver tests), plus the promptfile tests.

- [ ] **Step 5: Confirm nothing else regressed**

Run: `uv run pytest tests/ -q`
Expected: PASS. Anything that referenced the old deprecation banner would fail here.

- [ ] **Step 6: Commit**

```bash
git add multi_review.py multi_review/core/promptfile.py \
  tests/unit/test_multi_review_driver.py tests/unit/test_promptfile.py
git commit -m "feat(driver): revive multi_review.py as headless driver skeleton"
```

---

### Task 2: Fan-out, crash isolation, classification, `REVIEW.md`, exit code

**Files:**
- Modify: `multi_review.py`
- Modify: `multi_review/core/fanout.py` (`run_all_reviewers` plus `run_reviewer` cancellation scope)
- Modify: `multi_review/core/aggregate.py` (`prompt_file` YAML encoding only)
- Test: `tests/unit/test_multi_review_driver.py`
- Test: `tests/unit/test_fanout.py`
- Test: `tests/unit/test_aggregate.py`

**Interfaces:**
- Consumes: `main`'s locals from Task 1; shared `multi_review.core.fanout.run_all_reviewers`, `multi_review.core.prompt.classify_review_ok`, `multi_review.core.aggregate.write_review_md`
- Produces:
  - `async def _amain(pf, reviewers: list[str], prompt_text: str, prompt_path: Path, out_dir: Path, timeout: int | None, prompt_file: Path) -> int` — Task 3 adds synthesis inside it, Task 4 adds the signal handler at its top.
  - `main` now returns `asyncio.run(_amain(...))` on the success path.
  - `<out-dir>/REVIEW.md`.

Task 2 extends the shared orchestrator instead of duplicating its task creation, cancellation cleanup, crash isolation, and `ReviewerState` construction in the driver:

```python
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
) -> list[ReviewerResult]
```

The callbacks are **non-owning observers**. `run_all_reviewers` contains and reports callback
exceptions through the event loop's exception handler; an observer failure must never escape the
orchestrator, change a reviewer's result, orphan its subprocess, or abandon sibling tasks. Wrap the
pre-existing `state_callback` before passing it to `run_reviewer`, and use the same safe-notify policy
for the new `result_callback`.

Cancellation has two distinct contracts: cancellation of the outer `run_all_reviewers` task cancels
and awaits every reviewer then propagates; an independently cancelled reviewer task is normalized to
one failed `ReviewerResult` while its peers finish. Ordinary reviewer exceptions are normalized the
same way. Process-control `SystemExit`/`KeyboardInterrupt` are not promised as per-reviewer values.

`run_reviewer`'s ownership scope must begin immediately after subprocess creation, **before** writing
or draining stdin. Current `main` starts its `CancelledError` cleanup only around the later stdout /
stderr / `proc.wait()` gather; cancellation while a large inline prompt is blocked in
`proc.stdin.drain()` otherwise loses the only reference that can kill the child. Move prompt delivery
inside the same cancellation/exception cleanup scope. This is what makes Task 4's best-effort
single-binary SIGTERM claim true for the whole post-launch lifecycle.

`ReviewerResult` is a plain, **non-frozen** dataclass: `cli, ok, text, stderr_tail, usage, elapsed, error=None, model_used=None, downgraded=False`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_multi_review_driver.py`. Add these imports at the top of the file, next to the existing ones:

```python
import asyncio

from multi_review.core.adapters import Usage
from multi_review.core.fanout import ReviewerResult
```

Then add the shared fakes and the tests:

```python
SUMMARY_BODY = "## Summary\n\nLooks fine.\n"


def _result(cli, ok=True, text=SUMMARY_BODY, error=None):
    return ReviewerResult(cli=cli, ok=ok, text=text, stderr_tail="",
                          usage=Usage(), elapsed=1.0, error=error)


class _RecordingFanout:
    """Stand-in for run_all_reviewers that records one orchestration call."""

    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    async def __call__(self, reviewers, prompt, models, timeout, **kwargs):
        self.calls.append({"reviewers": reviewers, "prompt": prompt, "models": models,
                           "timeout": timeout, **kwargs})
        results = [self.results.get(cli, _result(cli)) for cli in reviewers]
        if kwargs.get("result_callback"):
            for result in results:
                kwargs["result_callback"](result)
        return results

    @property
    def clis(self):
        return self.calls[0]["reviewers"]


def _run(tmp_path, monkeypatch, yaml_body, fanout, extra_argv=()):
    """Run the driver with run_all_reviewers faked out."""
    pf = _write_promptfile(tmp_path, yaml_body)
    out = tmp_path / "round-1"
    monkeypatch.setattr(driver, "run_all_reviewers", fanout)
    code = driver.main(["--prompt-file", str(pf), "--out-dir", str(out), *extra_argv])
    return code, out


THREE_YAML = """\
    prompt_format_version: 1
    task: code
    files: [target.py]
    reviewers: [codex, codex, agy]
    synthesizer: none
"""


def test_duplicate_reviewers_are_dispatched_once(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.clis == ["codex", "agy"]


def test_fanout_receives_the_on_disk_prompt_path(tmp_path, monkeypatch):
    # agy's argv_file delivery reads the prompt from this path; dropping it
    # breaks agy on every real run while the suite stays green.
    fanout = _RecordingFanout()
    _, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.calls[0]["prompt_path"] == out / "prompt.txt"


def test_fanout_receives_prompt_task(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.calls[0]["task"] == "code"


def test_model_is_forwarded_only_when_configured(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML + "    models: {codex: gpt-5.6-sol}\n", fanout)
    assert fanout.calls[0]["models"] == {"codex": "gpt-5.6-sol"}


def test_timeout_is_forwarded_when_given(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout, extra_argv=["--timeout", "600"])
    assert fanout.calls[0]["timeout"] == 600


def test_timeout_defaults_to_none(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert fanout.calls[0]["timeout"] is None


def test_review_md_is_written_with_both_reviewers(tmp_path, monkeypatch):
    fanout = _RecordingFanout()
    code, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert 'reviewers_succeeded: ["codex", "agy"]' in text
    assert 'reviewers_failed: []' in text


def test_all_reviewers_failing_exits_1(tmp_path, monkeypatch):
    fanout = _RecordingFanout(results={
        "codex": _result("codex", ok=False, text="", error="rc=1"),
        "agy": _result("agy", ok=False, text="", error="rc=1"),
    })
    code, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    assert code == 1
    assert 'reviewers_failed: ["codex", "agy"]' in (out / "REVIEW.md").read_text()


def test_exit_code_uses_classified_not_raw_ok(tmp_path, monkeypatch):
    # raw ok=True but no "## Summary" heading -> classify_review_ok demotes it.
    fanout = _RecordingFanout(results={
        "codex": _result("codex", ok=True, text="I reviewed it. No heading here."),
        "agy": _result("agy", ok=False, text="", error="rc=1"),
    })
    code, out = _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    text = (out / "REVIEW.md").read_text()
    assert code == 1
    assert 'reviewers_failed: ["codex", "agy"]' in text
    assert "failed — no ## Summary heading in review body" in text
    assert "unknown error" not in text


def test_progress_lines_go_to_stderr(tmp_path, monkeypatch, capsys):
    fanout = _RecordingFanout()
    _run(tmp_path, monkeypatch, THREE_YAML, fanout)
    err = capsys.readouterr().err
    assert "[multi_review] codex: ok" in err
    assert "[multi_review] agy: ok" in err


def test_review_write_failure_returns_1_without_raising(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(driver, "write_review_md",
                        lambda **kwargs: (_ for _ in ()).throw(SystemExit("disk full")))
    code, _ = _run(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout())
    assert code == 1
    assert "disk full" in capsys.readouterr().err
```

Also update the two Task-1 happy-path tests, which would otherwise dispatch **real** reviewer CLIs now that `main` calls `_amain`. Replace their bodies:

```python
def test_out_dir_created_when_missing(tmp_path, monkeypatch):
    _, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    assert (out / "prompt.txt").exists()


def test_prompt_txt_contains_the_input_file_body(tmp_path, monkeypatch):
    _, out = _run(tmp_path, monkeypatch, BASE_YAML, _RecordingFanout())
    assert "return 1" in (out / "prompt.txt").read_text()


def test_empty_out_dir_is_accepted(tmp_path, monkeypatch):
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    out.mkdir()
    monkeypatch.setattr(driver, "run_all_reviewers", _RecordingFanout())
    driver.main(["--prompt-file", str(pf), "--out-dir", str(out)])
    assert (out / "prompt.txt").exists()
```

Append this shared-orchestrator regression test to `tests/unit/test_fanout.py`, importing `Usage` and `run_all_reviewers` there:

```python
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
```

Add three more shared-orchestrator regressions at the contract level:

- one `run_reviewer` fake raises an independent `asyncio.CancelledError` while a sibling completes;
  assert two ordered results, only the cancelled reviewer failed, and the sibling was not cancelled;
- cancel the outer `run_all_reviewers` task while reviewers are in flight; assert both children were
  cancelled/awaited and outer cancellation still propagates;
- make both `state_callback` (after launch) and `result_callback` raise while a sibling is in flight;
  assert observer failures are sent to the loop exception handler, all reviewer work remains owned,
  and real reviewer results are returned unchanged.
- drive `run_reviewer` with a fake subprocess whose `stdin.drain()` raises
  `asyncio.CancelledError`; assert `kill_proc` receives that subprocess and cancellation propagates.

In `tests/unit/test_aggregate.py`, add a YAML round-trip regression for `prompt_file` using an
absolute filename containing `: ` and `#`; parse the emitted frontmatter with `yaml.safe_load` and
assert the exact string survives. This pins attribution as data rather than executable YAML syntax.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_multi_review_driver.py tests/unit/test_fanout.py tests/unit/test_aggregate.py -q`
Expected: FAIL — `AttributeError: module 'mr_driver' has no attribute 'run_all_reviewers'` from `monkeypatch.setattr`.

- [ ] **Step 3: Implement fan-out, classification, and the write**

First, widen `run_reviewer`'s existing post-launch cleanup `try` to include stdin prompt delivery, as
specified above. Keep its current `BrokenPipeError`/`ConnectionResetError` handling, but make every
`CancelledError` after `create_subprocess_exec` kill and await `proc` before re-raising.

Then extend `run_all_reviewers` in `multi_review/core/fanout.py`. Outer cancellation remains
cancellation; an independently cancelled reviewer becomes its own failed result, and ordinary
reviewer crashes remain isolated:

```python
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
                model=models.get(state.cli), timeout=timeout,
                state=state, state_callback=_state_notify,
                prompt_path=prompt_path, task=task,
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
        for task in tasks:
            if not task.done():
                task.cancel()
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
```

Then extend the driver's import block:

```python
import asyncio
import dataclasses

from multi_review.core.aggregate import write_review_md
from multi_review.core.fanout import ReviewerResult, run_all_reviewers
from multi_review.core.prompt import build_prompt, classify_review_ok
```

Replace the final `return 0` of `main` with:

```python
    return asyncio.run(_amain(pf, reviewers, prompt_text, prompt_path, out_dir,
                              args.timeout, prompt_file))
```

Add `_amain` above `main`:

```python
async def _amain(pf, reviewers: list[str], prompt_text: str, prompt_path: Path,
                 out_dir: Path, timeout: int | None, prompt_file: Path) -> int:
    def _report(result: ReviewerResult) -> None:
        print(f"[multi_review] {result.cli}: {'ok' if result.ok else 'failed'} "
              f"({result.elapsed:.1f}s) [raw]", file=sys.stderr, flush=True)

    raw_results = await run_all_reviewers(
        reviewers, prompt_text, pf.models, timeout,
        prompt_path=prompt_path, task=pf.task, result_callback=_report,
    )

    # dataclasses.replace, not in-place mutation: ReviewerResult is non-frozen, so
    # `r.ok = ok` would corrupt raw_results out from under the synthesis gate.
    classified_results = []
    for r in raw_results:
        ok, note = classify_review_ok(r.ok, r.text)
        classified_results.append(dataclasses.replace(
            r,
            ok=ok,
            # Preserve a real subprocess error; a raw-ok demotion has none, so
            # the classifier note becomes the primary user-facing failure cause.
            error=(r.error or note),
            stderr_tail=(f"{r.stderr_tail}\n{note}" if r.stderr_tail and note
                         else note or r.stderr_tail),
        ))

    synthesis_text = None

    try:
        write_review_md(
            path=out_dir / "REVIEW.md",
            results=classified_results,
            synthesis_text=synthesis_text,
            mode=pf.mode,
            task=pf.task,
            reviewers_attempted=reviewers,
            models=pf.models,
            prompt_file=str(prompt_file),
        )
    except SystemExit as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0 if sum(1 for r in classified_results if r.ok) >= 1 else 1
```

In `multi_review/core/aggregate.py`, render prompt-file attribution with YAML-safe quoting:

```python
    if prompt_file is not None:
        lines.append(f"prompt_file: {json.dumps(prompt_file)}")
```

The driver passes the absolute `prompt_file` resolved in Task 1, so the attribution remains
meaningful after `REVIEW.md` leaves the caller's foreign cwd.

`classified_results` — not `raw_results` — drives both the exit code and what `write_review_md` renders. Computing them from one list is what stops the driver exiting `0` while every section in the file it just wrote is marked failed.

`input_files=` is deliberately not passed: `review-loop`'s contract only needs `reviewers_failed`, and populating it would be cosmetic.

There is deliberately **no** `detect_available()` pre-filter. Under `bwrap` the sandbox's `PATH` is not this process's `PATH`, so a host-side probe would be meaningless. A genuinely missing CLI dispatches, `run_reviewer` reports `CLI not found: …`, and it lands in `reviewers_failed` like any other failure.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_multi_review_driver.py tests/unit/test_fanout.py tests/unit/test_aggregate.py -q`
Expected: PASS (22 driver tests), plus the fanout tests.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add multi_review.py multi_review/core/fanout.py multi_review/core/aggregate.py \
  tests/unit/test_multi_review_driver.py tests/unit/test_fanout.py tests/unit/test_aggregate.py
git commit -m "feat(driver): reuse shared fanout and write classified review"
```

---

### Task 3: Synthesis pass

**Files:**
- Modify: `multi_review.py` (`_amain` only)
- Modify: `multi_review/core/synthesis.py` (`_run_synthesis_attempt` cancellation branch)
- Test: `tests/unit/test_multi_review_driver.py`
- Test: `tests/unit/test_synthesis.py`

**Interfaces:**
- Consumes: `raw_results` and `classified_results` from Task 2; `multi_review.core.synthesis.build_synthesis_input`/`run_synthesis`
- Produces: `synthesis_text: str | None` fed to `write_review_md`, plus an independent `synthesis_ok: bool` that controls `synthesizer=`/`synthesized_at=` attribution

Real signatures (verified against `multi_review/core/synthesis.py`):

```python
def build_synthesis_input(results: list[ReviewerResult]) -> tuple[str, str]      # -> (body, nonce)
async def run_synthesis(cli, review_body, nonce, model, timeout) \
    -> tuple[bool, str, str, str | None, list[str]]                              # -> (ok, text, err, suggested, attempts)
```

The gate counts **raw** `ok`, while the exit code counts **classified** `ok`. This split is deliberate, not an oversight: the gate asks "is there enough raw material to synthesize from" (matching `SKILL.md` Step 6, which also reads raw `state.json` `ok`), while the exit code asks "did this round produce anything the caller can trust". Do not unify them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_multi_review_driver.py`:

```python
class _RecordingSynth:
    def __init__(self, ok=True, text="## Consensus Summary\n\nAgreed.\n", raises=None):
        self.ok, self.text, self.raises = ok, text, raises
        self.calls = []

    async def __call__(self, cli, body, nonce, model=None, timeout=None):
        self.calls.append({"cli": cli, "body": body, "nonce": nonce,
                           "model": model, "timeout": timeout})
        if self.raises is not None:
            raise self.raises
        return self.ok, self.text, "", None, ["<default>"]


SYNTH_YAML = """\
    prompt_format_version: 1
    task: code
    files: [target.py]
    reviewers: [codex, agy]
    synthesizer: claude
"""


def _run_with_synth(tmp_path, monkeypatch, yaml_body, reviewer, synth, extra_argv=()):
    monkeypatch.setattr(driver, "run_synthesis", synth)
    return _run(tmp_path, monkeypatch, yaml_body, reviewer, extra_argv)


def test_synthesizer_none_never_calls_run_synthesis(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _run_with_synth(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout(), synth)
    assert synth.calls == []


def test_one_raw_success_does_not_reach_the_synthesizer(tmp_path, monkeypatch):
    rev = _RecordingFanout(results={"agy": _result("agy", ok=False, text="", error="rc=1")})
    synth = _RecordingSynth()
    _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, rev, synth)
    assert synth.calls == []


def test_two_raw_successes_reach_the_synthesizer(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert [c["cli"] for c in synth.calls] == ["claude"]
    assert "Agreed." in text


def test_synthesis_frontmatter_records_attribution(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert "synthesizer: claude" in text
    assert "synthesized_at: " in text


def test_successful_empty_synthesis_still_records_attribution(tmp_path, monkeypatch):
    synth = _RecordingSynth(ok=True, text="")
    _, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML,
                             _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert "synthesizer: claude" in text
    assert "synthesized_at: " in text


def test_synthesis_receives_model_and_timeout(tmp_path, monkeypatch):
    synth = _RecordingSynth()
    _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML + "    models: {claude: opus}\n",
                    _RecordingFanout(), synth, extra_argv=["--timeout", "600"])
    assert synth.calls[0]["model"] == "opus"
    assert synth.calls[0]["timeout"] == 600


def test_synthesis_gate_is_raw_while_exit_code_is_classified(tmp_path, monkeypatch):
    # Both raw-ok (gate fires) but one lacks a "## Summary" heading (classified fail).
    rev = _RecordingFanout(results={
        "codex": _result("codex", ok=True, text="no heading anywhere in this body"),
    })
    synth = _RecordingSynth()
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, rev, synth)
    text = (out / "REVIEW.md").read_text()
    assert len(synth.calls) == 1          # gate saw 2 raw successes
    assert code == 0                      # agy still classified-ok
    assert 'reviewers_succeeded: ["agy"]' in text
    assert 'reviewers_failed: ["codex"]' in text


def test_synthesis_raising_does_not_lose_the_review(tmp_path, monkeypatch):
    # run_synthesis genuinely can raise: NamedTemporaryFile in
    # _run_synthesis_attempt executes before its own try block, so an OSError
    # (unwritable /tmp under `bwrap --tmpfs /tmp`) propagates out. Unwrapped,
    # that would discard every collected reviewer result at the last moment.
    synth = _RecordingSynth(raises=OSError("read-only /tmp"))
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    text = (out / "REVIEW.md").read_text()
    assert code == 0
    assert 'reviewers_succeeded: ["codex", "agy"]' in text
    assert "synthesizer: claude" not in text


def test_synthesis_returning_not_ok_leaves_review_intact(tmp_path, monkeypatch):
    synth = _RecordingSynth(ok=False, text="")
    code, out = _run_with_synth(tmp_path, monkeypatch, SYNTH_YAML, _RecordingFanout(), synth)
    assert code == 0
    assert "synthesizer: claude" not in (out / "REVIEW.md").read_text()
```

Append this cancellation regression to `tests/unit/test_synthesis.py`, importing `pytest` and `_run_synthesis_attempt` there:

```python
def test_cancelled_synthesis_kills_child(monkeypatch):
    killed = []

    class Proc:
        async def communicate(self, payload):
            raise asyncio.CancelledError()

    async def fake_exec(*args, **kwargs):
        return Proc()

    async def fake_kill(proc):
        killed.append(proc)

    monkeypatch.setattr("multi_review.core.synthesis.build_command",
                        lambda *args, **kwargs: ["fake"])
    monkeypatch.setattr("multi_review.core.synthesis.asyncio.create_subprocess_exec", fake_exec)
    monkeypatch.setattr("multi_review.core.synthesis.kill_proc", fake_kill)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_run_synthesis_attempt("codex", "body", "nonce", None, None))
    assert len(killed) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_multi_review_driver.py tests/unit/test_synthesis.py -q`
Expected: FAIL — the driver lacks `run_synthesis`, and the synthesis cancellation test records no kill.

- [ ] **Step 3: Implement the synthesis step**

First, add cancellation cleanup beside the timeout cleanup in `_run_synthesis_attempt`:

```python
        except asyncio.TimeoutError:
            await kill_proc(proc)
            return False, "", f"synthesis timeout after {timeout}s", None
        except asyncio.CancelledError:
            await kill_proc(proc)
            raise
```

Cancellation must remain observable to `run_all_reviewers`/`main`; this branch only guarantees the child is reaped before it propagates.

Extend the driver's imports:

```python
import time

from multi_review.core.synthesis import build_synthesis_input, run_synthesis
```

Replace `synthesis_text = None` in `_amain` with:

```python
    synthesis_text = None
    synthesis_ok = False
    if pf.synthesizer != "none" and sum(1 for r in raw_results if r.ok) >= 2:
        body, nonce = build_synthesis_input(raw_results)
        try:
            ok, text, err, suggested, attempts = await run_synthesis(
                pf.synthesizer, body, nonce,
                model=pf.models.get(pf.synthesizer), timeout=timeout,
            )
        except Exception as exc:
            # Required, not defensive padding: NamedTemporaryFile in
            # _run_synthesis_attempt runs before its own try block, so an OSError
            # there escapes. Unwrapped, step 9 never runs and no REVIEW.md is
            # written at all — discarding every reviewer result at the last moment.
            # All five names are bound in both branches to avoid a latent NameError.
            ok, text, err, suggested, attempts = False, "", str(exc), None, []
            print(f"[multi_review] synthesis ({pf.synthesizer}): crashed: {exc}",
                  file=sys.stderr, flush=True)
        synthesis_ok = ok
        if synthesis_ok:
            synthesis_text = text
        print(f"[multi_review] synthesis ({pf.synthesizer}): {'ok' if ok else 'failed'}",
              file=sys.stderr, flush=True)
```

Then add the attribution kwargs to the `write_review_md` call. Attribution is keyed off the explicit outcome, not body truthiness: `ok=True, text=""` still records that the configured synthesizer completed successfully.

```python
        synthesizer=(pf.synthesizer if synthesis_ok else None),
        synthesized_at=(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        if synthesis_ok else None),
```

Known cosmetic wart, out of scope: when `synthesis_text is None`, `write_review_md` still renders a `## Consensus Summary` heading, and picks its fallback body off the **classified** success count. With 2+ classified successes it prints `_Consensus synthesis skipped (run without --no-synthesize to populate)._`, naming a flag this driver has no equivalent of. That is pre-existing behaviour in `write_review_md`, not something the driver introduces or can suppress without a core change.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_multi_review_driver.py tests/unit/test_synthesis.py -q`
Expected: PASS (31 driver tests), plus the synthesis tests.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add multi_review.py multi_review/core/synthesis.py \
  tests/unit/test_multi_review_driver.py tests/unit/test_synthesis.py
git commit -m "feat(driver): synthesis pass with raw gate and crash containment"
```

---

### Task 4: `SIGTERM` handler and the cancellation exit contract

**Files:**
- Modify: `multi_review.py` (`main` + top of `_amain`)
- Test: `tests/unit/test_multi_review_driver.py`

**Interfaces:**
- Consumes: `_amain` from Tasks 2–3
- Produces: `main` returns `1` (not an uncaught traceback) when `_amain` is cancelled

`asyncio.run()` already handles `Ctrl-C`/`SIGINT` — cancellation reaches `run_reviewer`, which kills its child before re-raising. **`SIGTERM` does not**: its default disposition terminates the process immediately, no Python cleanup runs, every in-flight reviewer subprocess is orphaned. Measured live: 0 of 3 reviewer children survived a `SIGINT`; 3 of 3 survived a `SIGTERM`. The orphans are uncontained agentic CLIs still running against the tree under review.

**The two mitigations are not peers.**

- **Caller-side (load-bearing):** `review-loop` must run the driver under `bwrap --unshare-pid --die-with-parent` and signal the `bwrap` process, never the driver. Verified live to tear down the whole tree. This is the actual guarantee.
- **Driver-side (best-effort, partial):** the handler below. `kill_proc` calls `proc.kill()` — `SIGKILL` to the **direct** child only. `claude`/`agy`/`grok` are ELF executables, so the direct child is the reviewer. `codex` and `opencode` are `#!/usr/bin/env node` shims whose real engine is a **grandchild** that survives. (`pykrete` unconfirmed — Task 5's smoke resolves it.)

Do not let the handler read as making the `bwrap` contract optional. It doesn't.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_multi_review_driver.py`:

```python
def test_cancellation_during_fanout_returns_1_not_a_traceback(tmp_path, monkeypatch):
    # The outer cancellation a SIGTERM triggers propagates through the shared
    # fanout, out of the coroutine, and out of asyncio.run(). Without the catch
    # in main(), the process dies on an uncaught traceback instead of honouring
    # the `main() -> int` contract.
    async def _cancelled(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(driver, "_amain", _cancelled)
    pf = _write_promptfile(tmp_path, BASE_YAML)
    out = tmp_path / "round-1"
    assert driver.main(["--prompt-file", str(pf), "--out-dir", str(out)]) == 1


def test_sigterm_handler_is_installed(tmp_path, monkeypatch):
    installed = []
    real_get_loop = driver.asyncio.get_running_loop

    class _Spy:
        def __init__(self, loop):
            self._loop = loop

        def __getattr__(self, name):
            return getattr(self._loop, name)

        def add_signal_handler(self, sig, cb):
            installed.append(sig)
            return self._loop.add_signal_handler(sig, cb)

    monkeypatch.setattr(driver.asyncio, "get_running_loop", lambda: _Spy(real_get_loop()))
    _run(tmp_path, monkeypatch, THREE_YAML, _RecordingFanout())
    assert driver.signal.SIGTERM in installed
```

These unit tests pin the two composition points without sending a real signal into pytest's own
process. Task 5's required Shutdown smoke is the connected acceptance test: it sends `SIGTERM` to a
real driver and must observe cancellation, exit `1`, no `REVIEW.md`, and the documented descendant
cleanup behavior.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_multi_review_driver.py -q`
Expected: FAIL — `AttributeError: module 'mr_driver' has no attribute 'signal'`, and the cancellation test fails with an uncaught `CancelledError`.

- [ ] **Step 3: Install the handler and catch the cancellation**

Add `import signal` to the driver's imports.

At the very top of `_amain`, before `_report` is defined:

```python
    # Must be installed from inside the coroutine, not from main(): before
    # asyncio.run() starts there is no running loop and no current task to cancel.
    # Best-effort only — see the spec's Shutdown section; the caller-side
    # `bwrap --unshare-pid --die-with-parent` contract is the load-bearing one,
    # because SIGKILL to a node shim does not reach codex/opencode's real engine.
    asyncio.get_running_loop().add_signal_handler(
        signal.SIGTERM, asyncio.current_task().cancel)
```

In `main`, wrap the `asyncio.run` call:

```python
    try:
        return asyncio.run(_amain(pf, reviewers, prompt_text, prompt_path, out_dir,
                                  args.timeout, prompt_file))
    except asyncio.CancelledError:
        # SIGTERM during fanout or synthesis: no REVIEW.md was written; the caller
        # sees a failed round. review-loop treats any non-zero exit identically.
        return 1
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_multi_review_driver.py -q`
Expected: PASS (33 tests).

- [ ] **Step 5: Lint the finished driver**

Run: `uv run ruff check multi_review.py` (skip if ruff is not installed — it is a dev extra, not guaranteed present; do not install it just for this).
Expected: no findings. If ruff is unavailable, eyeball for lines over 110 chars instead.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest tests/ -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add multi_review.py tests/unit/test_multi_review_driver.py
git commit -m "feat(driver): SIGTERM handler and cancellation exit contract"
```

---

### Task 5: Manual smoke execution gate and the CLAUDE.md posture note

**Files:**
- Create: `tests/manual/headless-driver-smoke.md`
- Modify: `CLAUDE.md` (Project overview + Invariants section)
- Modify: `README.md` (Limitations / entry-point status)

**Interfaces:**
- Consumes: the finished driver from Tasks 1–4
- Produces: the smoke procedure, dated recorded outcomes for all five checks, and the posture note;
  no importable surface

The suite mocks every CLI dispatch, so a green run says nothing about real subprocess or sandboxed behaviour. These five procedures are the gap.

The posture change is real and must be recorded: through this driver, `claude -p` gets its full default toolset, unlike the skill's Task-subagent reviewer restricted to `Read`/`Grep`/`Glob`. It becomes a fifth uncontained, agentic reviewer. Current `main` also says in both `CLAUDE.md` and `README.md` that `multi_review.py` is a deprecation stub scheduled for removal; reviving the file without replacing both statements would leave authoritative docs directing maintainers to delete the new entry point.

- [ ] **Step 1: Write the smoke document**

Create `tests/manual/headless-driver-smoke.md`:

```markdown
# Manual smoke — headless driver (`multi_review.py`)

The unit suite mocks all CLI dispatch. Run these against the real binaries before
`review-loop` commits to this driver's shape. Record outcomes inline (date + result).

## 1. `claude -p` under `bwrap`

Run the driver with `reviewers: [claude]` under `bwrap --clearenv` with `~/.claude`
bound **writable**. Expect a populated Claude section in `REVIEW.md`, not a failure.

## 2. Does headless `claude -p` auto-deny permission-gated tool calls?

`agy --print` does (CLAUDE.md documents it). If `claude -p` does too, **reference
mode systematically fails for `claude` through this driver** and needs its own fix,
not a caveat. Test: a `mode: reference` run with `reviewers: [claude]`, and check
whether the review body shows it actually read the manifest's files.

## 3. WSL2 DNS

`--ro-bind /mnt/wsl` is required in the `bwrap` invocation or DNS breaks inside the
sandbox. Confirm a sandboxed reviewer reaches its API endpoint.

## 4. Invocation contract from a foreign cwd

Run `uv run <repo>/multi_review.py ...` twice:
- from a foreign cwd with **no** `pyproject.toml`
- from a foreign cwd that **has** its own `pyproject.toml`

Both must succeed, and neither may write `.venv/` or `uv.lock` into that foreign
tree. This is what the PEP 723 header exists for; it was verified against the
design, and this pass verifies it against the implementation.

## 5. Shutdown

Send `kill -TERM <driver-pid>` **specifically** — not `Ctrl-C`, not a process-group
signal (`kill -TERM -<pgid>`). Either of those can let a reviewer CLI's own signal
forwarding do the cleanup instead of the driver's handler, measuring the wrong thing.

Procedure:
1. Snapshot the full descendant tree: `ps -eo pid,ppid,args` or recursive `pgrep -P`.
   Not a name grep — a surviving `node` engine may not share its shim's name.
2. Send `kill -TERM <driver-pid>`.
3. Wait for the driver and record its status. It must exit `1`, without an uncaught traceback, and
   `<out-dir>/REVIEW.md` must not exist.
4. Re-check every PID from the snapshot individually.

Expect `claude`/`agy`/`grok` children gone. `codex`/`opencode` grandchildren may
survive this specific test — that is exactly the scenario the caller-side
`bwrap --unshare-pid --die-with-parent` contract exists for, so also confirm
separately that killing a `bwrap`-wrapped driver that way tears down the *entire*
tree including those grandchildren, regardless of the driver's own handler.

**Also record whether `pykrete`'s engine survives the plain (non-`bwrap`) kill.**
The design leaves it as "possibly affected" but unconfirmed; this pass resolves it.
If it survives, it needs the same `bwrap` contract as `codex`/`opencode`. If not,
drop the "possibly" hedge from the design's Shutdown section.

## Outcome record

Do not mark this task complete with blank outcomes. For each case above record:

- date, host/WSL environment, relevant CLI versions;
- exact command or a checked-in reusable script path;
- PASS / FAIL / BLOCKED and the observed evidence;
- for BLOCKED, the missing binary/auth/containment prerequisite;
- for FAIL, the plan task reopened and the contract change or implementation fix required.
```

- [ ] **Step 2: Update entry-point documentation and add the posture note**

In `CLAUDE.md`'s Project section, replace the statement that `multi_review.py` is a deprecation stub
scheduled for removal. Preserve `/multi-review` as the v0.2 interactive skill entry point, then state
that the root script is the separate headless single-pass entry point:

```markdown
v0.2's interactive entry point remains the **Claude Code skill** `/multi-review`;
`skills/multi-review/SKILL.md` drives its multi-step procedure. The root `multi_review.py` is a
separate headless single-pass driver for contained callers: invoke
`uv run <absolute-repo-path>/multi_review.py --prompt-file <yaml> --out-dir <dir> [--timeout <sec>]`.
It does not implement the skill's pairing, drift, harvest, promotion, or cleanup workflow.
```

In `README.md`'s Limitations section, replace `**v0.1 standalone CLI removed.**` with the same
distinction: the old positional `./multi_review.py file.ts` interface remains removed, while the
script path now hosts the prompt-file/out-dir single-pass contract above. Do not describe the new
driver as the v0.1 CLI or as a replacement for `/multi-review`.

In the `### Invariants to preserve` section, immediately after the `**agy is an agentic, uncontained reviewer.**` bullet, insert:

```markdown
- **`claude -p` through the headless driver is uncontained too.** The skill's `claude` reviewer runs
  as a Task subagent restricted to `Read`/`Grep`/`Glob` (spec §5.2). `multi_review.py`
  (the headless driver) dispatches it as `claude -p` through the same in-process fanout as every
  other reviewer, with its full default toolset — a fifth uncontained, agentic reviewer, same posture
  as agy/pykrete/grok. **Do not point the driver at untrusted code** until the bwrap/`--sandbox`
  containment in BACKLOG lands.
```

- [ ] **Step 3: Verify the suite is still green**

Run: `uv run pytest tests/ -q`
Expected: PASS. `tests/integration/test_skill_contract.py` asserts against the repo copies of skill/agent files; this change touches neither, so it must stay green. If it goes red, the CLAUDE.md edit landed somewhere it should not have.

- [ ] **Step 4: Execute all five smoke cases and record their outcomes**

Run the checked-in procedure against the real driver and real reviewer binaries. This is a
load-bearing acceptance gate, not optional follow-up documentation. A missing binary, authentication
context, `bwrap`, or WSL environment is `BLOCKED`: record the exact prerequisite and stop SDD rather
than declaring the branch deployment-ready. A failed case reopens the task that owns that contract;
fix it with RED → GREEN coverage where automatable, rerun the affected smoke, then rerun the full
five-case gate. In particular:

- Claude reference mode must demonstrably read the manifest files before Claude is enabled for that
  mode through this driver;
- both foreign-cwd runs must leave the foreign trees free of `.venv` and `uv.lock`;
- killing the plain driver must produce exit `1` and no `REVIEW.md`;
- killing the load-bearing `bwrap --unshare-pid --die-with-parent` wrapper must leave no descendant
  from the captured process tree alive.

Expected: five dated PASS records. Anything else means this task is not complete.

- [ ] **Step 5: Commit the procedure, evidence, and posture note**

```bash
git add tests/manual/headless-driver-smoke.md CLAUDE.md README.md
git commit -m "docs: record headless driver acceptance smoke"
```

---

## Not in this plan

Deliberately out of scope, per the spec's Non-goals:

- pending-pair GC, pass-order/drift posture, harvest rows, paired pass 2, drift report, promotion, cleanup, summary steps
- `mode: both` support (rejected with exit 2)
- any change to the skill's Task-dispatch branches — the driver is a second, parallel entry point, not a replacement
- persisting per-reviewer `.md`/`.state.json` files. Results are in-memory objects. Note this means failed/demoted reviewers' bodies stay truncated to 1000 chars by `write_review_md` with no on-disk copy to recover from — matches every other caller, not a regression this driver introduces.
- `BACKLOG.md:1154` and `README.md:166,186` both claim `output_dir` overriding is wired; nothing reads `PromptFile.output_dir`. A correction pass unrelated to this driver.
