# Manual smoke — headless driver (`multi_review.py`)

The unit suite mocks all CLI dispatch. Run these against the real binaries before
`review-loop` commits to this driver's shape. Record outcomes inline (date + result).
The executable procedure is `tests/manual/headless-driver-smoke.sh`; its sanitized
fixtures are checked in under `tests/manual/fixtures/headless-driver-smoke/`.

## 1. `claude -p` under `bwrap`

Run the driver with `reviewers: [claude]` under `bwrap --clearenv`, using a fresh
writable scratch `HOME`/`CLAUDE_CONFIG_DIR` and a script-scoped token from
`claude setup-token` supplied as `CLAUDE_CODE_OAUTH_TOKEN`. Do not bind the real
`~/.claude`. Expect a populated Claude section in `REVIEW.md`, not a failure.

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

### 2026-08-07 checked-in harness rerun — PASS

Environment: Ubuntu 22.04.5 LTS on WSL2
(`6.18.33.2-microsoft-standard-WSL2`, x86_64), `uv 0.10.7`,
`bubblewrap 0.6.1`, Claude Code 2.1.223, pykrete 0.1.0, and pi 0.80.10.
The earlier ad hoc commands and ignored fixtures are superseded by the committed
harness and fixtures named above. Reproduce the exact gate with mode-0600 secret
files (values are read on stdin with tracing disabled, never passed on argv):

```bash
tests/manual/headless-driver-smoke.sh --check

CLAUDE_TOKEN_FILE=/secure/claude-token \
PYKRETE_ENV_FILE=/secure/pykrete.env \
PYKRETE_CONFIG_FILE=/path/to/pykrete.toml \
KEEP_SMOKE_ARTIFACTS=1 \
  tests/manual/headless-driver-smoke.sh
```

The harness contains the complete bwrap mount mappings, fresh-home setup,
token-to-stdin shell sequence, foreign-cwd construction, driver-PID resolution,
recursive descendant snapshots, targeted signals, and per-PID liveness checks.
`bash -n`, ShellCheck, the harness `--check`, and its unit contract all passed
before this live run.

1. **PASS — `claude -p` under `bwrap`.** Exit 0 in 8.7s. `REVIEW.md` recorded
   Claude as succeeded and contained `INLINE_DRIVER_SMOKE_20260807` plus the
   intended zero-denominator finding. No scratch home contained `.credentials.json`.
2. **PASS — reference-mode file tool.** Exit 0 in 8.6s. The value
   `REFERENCE_TOOL_READ_20260807` was absent from `prompt.txt`, present in the
   review, and the isolated session recorded a `Read` tool call.
3. **PASS — WSL2 DNS.** The read-only `/mnt/wsl` mount supported the successful
   sandboxed Anthropic calls in cases 1 and 2.
4. **PASS — foreign cwd.** The no-project run completed in 9.0s and its directory
   stayed empty; the own-project run completed in 7.6s and retained only its
   original `pyproject.toml`. Neither directory gained `.venv/` or `uv.lock`.
5. **PASS — shutdown.** The plain harness resolved Python driver PID 793336 before
   signaling it; captured pykrete PID 793346 and pi PID 793365 were both gone,
   the wrapper returned 1, no traceback appeared, and no `REVIEW.md` existed.
   The separate bwrap wrapper PID 793419 reached descendants 793424, 793425,
   795588, 795661, and 796048 (namespace/reaper, uv, Python, pykrete, pi). The
   wrapper returned 143 after SIGTERM; every captured PID was gone and no
   `REVIEW.md` existed.

The harness emitted `headless_driver_smoke=PASS cases=5`. Only this checked-in,
reproducible rerun is the binding acceptance evidence.
