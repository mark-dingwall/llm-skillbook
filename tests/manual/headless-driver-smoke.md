# Manual smoke — headless driver (`multi_review.py`)

The unit suite mocks all CLI dispatch. Run these against the real binaries before
`review-loop` commits to this driver's shape. Record outcomes inline (date + result).

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

### 2026-08-07 gate rerun — PASS

Environment: Ubuntu 22.04.5 LTS on WSL2
(`6.18.33.2-microsoft-standard-WSL2`, x86_64), `uv 0.10.7`,
`bubblewrap 0.6.1`, Claude Code 2.1.223, pykrete 0.1.0, and pi 0.80.10.
The synthetic fixture and prompt YAMLs used for this run are retained at
`.superpowers/sdd/2026-08-04-headless-driver/task-5-smoke/` in the acceptance
worktree. Each driver invocation had this exact argv shape (with the named YAML
and output directory varied per case):

```bash
uv run "$REPO/multi_review.py" \
  --prompt-file "$REPO/.superpowers/sdd/2026-08-04-headless-driver/task-5-smoke/<case>.yaml" \
  --out-dir <case-output> --timeout <180|600>
```

Claude runs used `bwrap --clearenv --unshare-pid --die-with-parent`, a read-only
system runtime, read-only `$REPO`, read-only `/mnt/wsl`, a scratch uv cache, and
case-specific writable `/out` and fresh `HOME`/`CLAUDE_CONFIG_DIR` mounts. No
real Claude configuration was mounted. The script-scoped OAuth token entered the
inner shell on stdin, was read directly into `CLAUDE_CODE_OAUTH_TOKEN`, and stdin
was then replaced with `/dev/null`; it was never placed on argv or persisted in a
credential file. `--bare` was not used. Pykrete's key was sourced from its
gitignored environment file and `PYKRETE_CONFIG` named its normal config; neither
secret value was printed or recorded.

1. **PASS — `claude -p` under `bwrap`.** The inline run returned exit 0 in 7.6s.
   `REVIEW.md` recorded `reviewers_succeeded: ["claude"]`, no failed reviewers,
   the fixture marker `INLINE_DRIVER_SMOKE_20260807`, and the deliberately missing
   zero-denominator policy. The fresh Claude home contained no `.credentials.json`.
2. **PASS — reference-mode file tool.** The corrected reference prompt requested
   the value of `REFERENCE_MARKER` without including that value. The value
   `REFERENCE_TOOL_READ_20260807` was absent from `prompt.txt`, present in the
   successful review, and the isolated Claude session recorded a `Read` tool call.
   The run returned exit 0 in 9.7s, proving headless Claude did not auto-deny the
   permission-gated manifest read.
3. **PASS — WSL2 DNS.** The sandbox mounted `/mnt/wsl` read-only and used
   `/mnt/wsl/resolv.conf`. Cases 1 and 2 both reached Anthropic and returned real
   reviews, directly confirming DNS and endpoint reachability inside the sandbox.
4. **PASS — foreign cwd.** The same absolute-script invocation returned exit 0
   from `/tmp/mr-headless-smoke-20260807/foreign-no-project` (8.4s) and from
   `/tmp/mr-headless-smoke-20260807/foreign-with-project` (10.8s). Both reviews
   contained the expected marker/finding. The first directory remained empty; the
   second retained only its original `pyproject.toml`. Neither contained `.venv/`
   nor `uv.lock`.
5. **PASS — shutdown.** For the plain run, `uv` PID 776616 launched the actual
   Python driver PID 776625. Its pre-signal descendant snapshot was pykrete PID
   776639 and pi engine PID 776673. `kill -TERM 776625` produced driver exit 1,
   no traceback, and no `REVIEW.md`; two seconds later both captured descendants
   were gone. Thus pykrete 0.1.0/pi 0.80.10 is confirmed clean under the driver's
   plain cancellation path, and the design's "possibly affected" hedge is removed.

   Separately, bwrap PID 781216 was allowed to reach a five-process descendant
   tree: namespace/reaper 781218, uv 781223, Python driver 783795, pykrete 783902,
   and pi 784298. `kill -TERM 781216` made the wrapper exit 143; two seconds later
   every captured PID was gone and no `REVIEW.md` existed. This confirms the
   load-bearing `--unshare-pid --die-with-parent` whole-tree teardown contract.

The initial authentication-blocked record and two invalid shutdown harness probes
were superseded rather than counted: one probe detected a process name too narrowly;
the other targeted uv's wrapper PID instead of the Python driver. Neither produced
accepted shutdown evidence. The results above come only from the corrected full
process-tree observations.
