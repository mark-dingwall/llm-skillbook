# GROUND TRUTH — dispatch waiting. Do not show to the agent under test.

RED evidence is real-world, not synthetic: this exact waiter hung a
production loop ~100 minutes (2026-07-19) and recurred at least twice
more in the user's hand-rolled loop — `pgrep -f 'codex --model'`
matches the waiting shell's own command line (and the grep'd pattern
inside any orchestration process), so the predicate can never go
false. GREEN = an agent given dispatch.md refuses it.

**Expected (score /4):**
1. (1 pt) REJECT the pattern-based waiter, citing self-match.
2. (1 pt) State the idle-predicate check: run the wait predicate while
   nothing is dispatched — it must return immediately; this waiter
   fails that check (pgrep matches the checking shell itself).
3. (1 pt) Wait on captured PIDs instead (`$!` per reviewer;
   `kill -0`-based loop per dispatch.md), with the round wall-clock
   ceiling inside the wait predicate.
4. (1 pt) Normal-path status harvest: errexit-safe `wait "$p"` per
   reviewer and a recorded REVIEWER-EXIT status (completion needs
   exit 0, not just process exit).

Failure modes: adopting the waiter with a cosmetic tweak (tighter
pattern, `pgrep -x codex`) — still pattern-based, still fails the
idle-predicate check in orchestrators whose command line embeds the
pattern; adding only a timeout to the broken waiter; accepting it
because "it worked for the colleague".

Record tier, verbatim response excerpts, and score /4 in RESULTS.md.
