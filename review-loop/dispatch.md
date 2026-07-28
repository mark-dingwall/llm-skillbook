# Dispatch mechanics

Operational how-to for running external reviewer CLIs. Every rule here
was paid for by a real failure in a live loop (2026-07-20); the
protocol-level consequences live in SKILL.md — this file is the how.

## Waiting

- Wait on captured PIDs, never on a command-line pattern — `pgrep -f`
  matches the waiting shell's own command line and can spin forever.
- The whole-round wall-clock ceiling must be *in the wait predicate* —
  a ceiling that lives only in the round notes can never fire on a
  deadlocked reviewer process (per-call timeouts don't observe a broken
  waiter either):

  ```bash
  deadline=$(( $(date +%s) + CEILING_SECS ))
  for p in $PIDS; do
    while kill -0 "$p" 2>/dev/null; do
      if [ "$(date +%s)" -ge "$deadline" ]; then
        kill $PIDS 2>/dev/null || :                                 # polite TERM
        for i in 1 2 3 4 5; do sleep 2; kill -0 $PIDS 2>/dev/null || break; done
        kill -KILL $PIDS 2>/dev/null || :                           # kills anything schedulable
        for i in 1 2 3; do sleep 1; kill -0 $PIDS 2>/dev/null || break; done
        for q in $PIDS; do                                          # verify death — never block on wait here
          kill -0 "$q" 2>/dev/null && echo "UNREAPED $q" >> "$ROUND_NOTES" || :
        done
        break 2                                                     # INDETERMINATE now, unconditionally
      fi
      sleep 20
    done
    if wait "$p"; then s=0; else s=$?; fi                           # errexit-safe status harvest
    echo "REVIEWER-EXIT $p: $s" >> "$ROUND_NOTES"
  done
  ```

  The normal path must `wait "$p"` per reviewer — `kill -0` proves
  liveness, not exit status, and SKILL.md's completion contract
  requires exit 0. On expiry: TERM is a request; KILL kills any
  schedulable process, but a process stuck in uninterruptible kernel
  I/O (dead NFS/FUSE mount) can outlive it until the I/O returns — so
  the expiry path never blocks on `wait`: it verifies death with
  `kill -0`, records survivors as UNREAPED, and proceeds to
  INDETERMINATE regardless. `wait` only ever names reviewer PIDs — a
  bare `wait` also blocks on every unrelated background child of the
  shell. If a reviewer command spawns children, start it with
  `setsid` and signal the process group (`kill -- -PID`) so
  descendants die with it. Wrapping each reviewer in
  `timeout -k 10 <secs>` is complementary — the round ceiling still
  needs its own enforced deadline. On expiry, record the round
  INDETERMINATE (SKILL.md); cleanup is bounded best effort — kill
  what can be killed, record any survivor as UNREAPED, and never
  block on it.
- Before waiting, assert the wait predicate is false while nothing is
  dispatched — it should return immediately.

## Timeouts

- High-effort external reviewers on a large diff routinely run 5–15
  minutes; scoped later rounds 2–5. Scope size and reasoning effort are
  the drivers — size the timeout from the round's scope, not habit.
- "Still working" ≠ "hung": check the report/output file's mtime or
  growth before declaring failure; prefer a no-progress timeout over a
  bare wall-clock one.
- Record the chosen timeout and each reviewer's observed duration in the
  round notes — a genuine INDETERMINATE must be distinguishable from a
  too-tight knob (a mis-set timeout otherwise becomes a false NOT
  CONVERGED).

## Harvest

- The reviewer writes its final report to the file path given in the
  prompt (`{{ report_path }}`); that file is the completion-contract
  region. Stdout is kept only as a diagnostic. The path must be
  *outside the sealed tree* (as must every loop artifact — ledger,
  prompts, manifests): an in-tree write after the seal voids the round
  it belongs to.
- Never evaluate the completion contract against raw CLI stdout: typical
  traces run thousands of lines and contain draft findings, severity
  words, echoed prompt text, and a duplicated tail — a whole-file grep
  passes on a reviewer that produced no final verdict.
- Sanity check: the report file must not contain the dispatched prompt's
  distinctive opening line.

## Concurrency

- Run at most `min(10, cpu_cores - 2)` reviewers concurrently; queue the
  rest and start each as a slot frees. Larger fan-outs bog down the host
  and trip provider rate limits (HTTP 429) — a rate-limited reviewer
  fails its call and burns its one retry on the same contention.
- Reviewers verifying findings may each run the project's test suite;
  concurrent runs can stall each other and surface phantom
  timing failures. The addendum tells reviewers to re-verify in
  isolation. At triage a clean serial re-run alone refutes nothing —
  REFUTED needs evidence isolating contention as the cause; otherwise
  the row stays PLAUSIBLE (SKILL.md). If the suite is known to be
  contention-sensitive,
  stagger the reviewers that will run it, or steer them to focused tests.
