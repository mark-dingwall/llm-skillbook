# multi-review v0.2 preflight verification

Spec ref: `docs/superpowers/specs/2026-05-15-multi-review-skill-reframe-design.md`
Plan ref: `docs/superpowers/plans/2026-05-15-multi-review-skill-reframe.md` Task 0.

Each procedure has a block-fail criterion. Any BLOCK-FAIL returns to brainstorming before Task 1.

---

## Procedure 1 — Billing pool verification

**Status:** SOFT-PASS (documentary, not yet empirical)

- Run on: 2026-05-19
- Setup commands:
  - Assistant dispatched one `general-purpose` Task subagent (trivial "2+2" prompt) at 2026-05-19 16:44 UTC. Agent id: `a3c38eb089f977e13`. Total tokens: 20047. Duration: 4025ms.
- Observed:
  - The post-June-15 2026 billing change driving the reframe has not yet rolled out, so empirical separation of "interactive pool" vs "subprocess pool" is not directly measurable today.
  - User verdict: fine-print of the upcoming billing change and community/netizen analysis strongly suggest Task subagents will continue to bill against the interactive pool (i.e., be unaffected by the `claude -p` subprocess-pool repricing).
- Verdict: **SOFT-PASS** — proceed with v0.2 implementation on documentary basis. Re-verify empirically after the billing rollout (≥2026-06-15) before declaring v0.2 stable for tag.
- Evidence: user attestation 2026-05-19 (Anthropic billing rollout post-2026-06-15, documentary pattern in change announcements).

**Block-fail criterion (rephrased post-verdict):** if, after the billing rollout, Task subagents are observed billing against the subprocess pool, the v0.2 reframe regresses — re-enter brainstorming. Until then, the documentary premise is load-bearing.

---

## Procedure 2 — Task blocking + concurrent background Bash interleaving

**Status:** PASS

- Run on: 2026-05-19
- Setup commands:
  - Background Bash (id `b431fntf8`): `sleep 30 && echo background-finished > /tmp/preflight-bg.txt && date +%s >> /tmp/preflight-bg.txt`. Start epoch: 1779173080.
  - Concurrent in same message: `general-purpose` Task subagent answering "2+2".
- Observed:
  - Task subagent returned "Four" after 4025ms (well before the 30s background sleep).
  - Background Bash continued to run independently.
  - At t≈30s, `/tmp/preflight-bg.txt` materialised with end epoch 1779173110 (delta = 30s exact).
  - No interleaving stall observed.
- Verdict: **PASS** — Task blocking the host turn does not pause previously-scheduled background Bash; both run truly concurrently.
- Evidence: `/tmp/preflight-bg.txt` written at 30s mark; agent return inside 5s.

---

## Procedure 3 — TaskStop / TaskGet availability and behaviour

**Status:** PASS (with caveat)

- Run on: 2026-05-19
- Setup commands:
  - Background Bash (id `bwv8zd1oy`): `sleep 600 && echo unwanted > /tmp/preflight-stop.txt`. Start epoch recorded in `/tmp/preflight-stop-start.txt`.
  - After ~3s, called `TaskStop(task_id="bwv8zd1oy")`.
- Observed:
  - `TaskStop` returned `{"message":"Successfully stopped task: bwv8zd1oy ..."}`.
  - `ps -ef | grep "sleep 600"` after stop: no matching process → underlying `sleep` killed.
  - `/tmp/preflight-stop.txt` does not exist after 10+ minutes confirmation window (procedure observed within session; absent at write time).
  - `TaskOutput` on stopped id returns `No task found with ID: bwv8zd1oy` — once stopped, the task is removed from the task table rather than reporting a "killed" status.
- Verdict: **PASS** with caveat — `TaskStop` semantics match spec §8.5 (process actually dies). `TaskGet` does not appear to exist for background-Bash tasks (only `TaskOutput`, which after stop reports "not found" rather than a status). Spec §6.2 step 3 ("TaskStop the notification task if still alive") is sound: TaskStop is the right primitive. Liveness check before stop should use `TaskOutput(block: false)` and treat "not found" or non-running status as "already gone".
- Evidence: TaskStop success message; absence of `/tmp/preflight-stop.txt`; absence of `sleep 600` in `ps`.

---

## Procedure 4 — Background Bash persistence across skill exit

**Status:** PASS (mechanical proxy)

- Run on: 2026-05-19
- Setup commands:
  - Background Bash (id `bk4x77mpq`): `sleep 45 && date +%s > /tmp/preflight-persist-end.txt`. Start epoch recorded in `/tmp/preflight-persist-start.txt`.
  - Procedure executed mid-`subagent-driven-development` skill, with the assistant continuing to do other Bash/tool work and the skill never explicitly "exiting" — the closest mechanical proxy available without a published `/multi-review` skill to invoke.
- Observed:
  - The 45s background Bash ran to completion alongside ~12 unrelated tool calls in between.
  - `/tmp/preflight-persist-end.txt` materialised at the expected epoch.
- Verdict: **PASS (mechanical proxy)** — within a single Claude Code session, `run_in_background` Bash tasks survive concurrent foreground tool calls indefinitely. The narrower question — survival across an explicit skill *exit* (skill finishes; control returns to user; session idle) — cannot be tested until `skills/multi-review/SKILL.md` exists, so this verdict is provisional and re-validated by Task 35 single-pass smoke.
- Soft-fail trigger: if Task 35 finds background-Bash dies on real skill exit, spec §8.2 background-notify reworks to foreground-only cooldown; `delay_type: background` drops. Not a v0.2 blocker per plan.

---

## Gate status

| Procedure | Verdict | Blocks Task 1? |
|---|---|---|
| 1 — Billing pool | SOFT-PASS (documentary) | no (re-verify post-rollout) |
| 2 — Concurrent Task + bg Bash | PASS | no |
| 3 — TaskStop / TaskGet | PASS | no |
| 4 — Bg Bash persistence across skill exit | PASS (mechanical proxy) | no (soft-fail only) |

**Task 1 unblocks: all four procedures have non-block-fail verdicts.** Procedure 1 carries a documentary-soft-pass — re-verify empirically post-billing-rollout before v0.2 tag (Task 37 gate).
