# Dispatch waiting fixture — results (2026-07-20)

RED evidence is real-world (see GROUND-TRUTH.md): the planted waiter
hung a production loop ~100 min and recurred twice more in a
prompt-only orchestration with no dispatch guidance. GREEN = agent
given dispatch.md refuses it.

| Tier | Reject waiter | Idle-predicate check | PID wait + ceiling | Status harvest | Score |
|---|---|---|---|---|---|
| sonnet | ✓ self-match cited | ✓ stated explicitly | ✓ (+setsid group kill, mtime progress, durations recorded) | ✓ errexit-safe | **4/4** |
| haiku | ✓ self-match cited | ✗ not mentioned | ✓ ceiling in predicate, TERM/KILL/UNREAPED | ✓ errexit-safe | **3/4** |

Haiku's miss is noted, not treated as a skill defect: its produced
waiter is PID-based, for which the idle assertion is trivially
satisfied (`for p in $PIDS` with empty PIDS returns immediately) —
the operative behavior was safe; only the explicit pre-check
statement was absent. Revisit only if a real run shows an executor
adopting a pattern-based waiter *after* reading dispatch.md.

Neither tier fell for the planted failure modes (cosmetic pattern
tweak, timeout-on-broken-waiter, "it worked for the colleague").
