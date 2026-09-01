# Zeroshot investigation

## 1. Overview

- **What**: Autonomous multi-agent coding orchestrator at `~/tools/zeroshot`. Takes an issue/task, classifies it, spins up a cluster of LLM agents (planner/worker/validators) coordinated over a SQLite pub/sub ledger, and only ships when independent validators produce fresh evidence.
- **Thesis**: *Separation of authorship and judgment.* The executor never self-certifies. Enforcement is structural (schemas, hooks, gates) rather than exhortative — "ENFORCE > DOCUMENT" (AGENTS.md:1130).
- **Size/maturity**: Substantial production TS/JS codebase (`isolation-manager.js` alone is 2506 lines), Docker/worktree isolation, crash-resume, a pinned wire protocol (`protocol/openengine-cluster/v1/` with 144 fixtures + 15 golden transcripts), and a native Rust v2 underway with a documented parity matrix. Mature, actively hardened (dated bug precedents, security containment modules).

## 2. Core methodology

| Stage | Agent(s) | Output topic |
|---|---|---|
| 1. Classify | junior conductor (cheap model) → senior on UNCERTAIN | routing decision |
| 2. Route | `getConfig()` picks template + validator count + model level | cluster config |
| 3. Plan | planner: numbered steps + testable acceptance criteria | `PLAN_READY` |
| 4. Implement | worker (bounded iterations, `canValidate` gate) | `IMPLEMENTATION_READY` |
| 5. Validate | 0–4 validators in parallel, evidence required | `VALIDATION_RESULT` |
| 6. Reject loop | any `approved:false` re-fires worker (max 5 iters) | back to 4 |
| 7. Ship | git-pusher, only with fresh PASS evidence | push/PR |

- **Classification is 2D**: complexity (TRIVIAL/SIMPLE/STANDARD/CRITICAL) × taskType (INQUIRY/TASK/DEBUG). Routing (`src/config-router.ts:56-129`): DEBUG→debug-workflow, TRIVIAL→single-worker, SIMPLE→worker-validator, STANDARD/CRITICAL→full-workflow. Validators: 0/1/2, and 0 for CRITICAL — a sentinel meaning "skip inline validators; the real 4 arrive via two-stage loading."
- **CRITICAL two-stage validation**: a `meta-coordinator` dynamically loads `quick-validation` (requirements+code, 30-60s) first; only on `QUICK_VALIDATION_PASSED` does it load `heavy-validation` (security+adversarial tester, 120-180s). Cheap gate before expensive gate.
- **Debug variant**: investigator → fixer (maxIterations:10) → tester, with an explicit `stop_cluster` completion-detector agent.

## 3. Architecture & code-vs-LLM split

Core loop: `Agent publishes → SQLite Ledger → LogicEngine → trigger match → next agent executes`.

| Layer | Form | Why |
|---|---|---|
| Coordination (topics, triggers, hooks) | JS predicates + JSON wiring | Deterministic routing; no LLM in the control plane |
| Ledger | SQLite per cluster (`~/.zeroshot/<id>.db`), WAL, split reader/writer connections | Crash-resume; CLI reads never write-lock a live daemon |
| Workflows | JSON templates with embedded prompts, JS trigger scripts, hooks (`cluster-templates/`) | Workflows are data → statically validated AND behaviorally simulated |
| Agent behavior | Prose prompts + strict JSON output schemas | LLM judgment constrained by schema enums/required fields |
| Context assembly | Code: `contextStrategy.sources` with priority/budget selection, compact fallbacks, 100k-token budget + 500k-char hard guard | Prompt construction is deterministic, not agent-chosen |
| Safety | Code: PreToolUse deny hooks, copy-containment (device+inode root pinning), overlay-dir verification | Rules the LLM cannot argue with |

Split principle: **LLMs decide within schemas; code decides everything between agents.** Every prose rule with teeth has a mechanical twin (e.g. "no AskUserQuestion" prose ↔ `block-ask-user-question.py` deny hook).

## 4. Enforcement & verification

**Making the LLM comply:**
- **Evidence-or-reject**: validator results require `command + exitCode + output` per criterion; `CANNOT_VALIDATE` = pass-with-warning, narrowly scoped (tool missing, no network).
- **Freshness gate**: git-pusher (`src/agents/git-pusher-template.js:150-200`) rejects PASS evidence timestamped before the last `IMPLEMENTATION_READY` — stale proofs from a prior push don't count. Missing gate → throw. No bypass path.
- **PreToolUse deny hooks** (`cluster-hooks/`): `AskUserQuestion` blocked outright (`ZEROSHOT_BLOCK_ASK_USER=1`); dangerous git (`stash`, `reset --hard`, `push -f`, `clean -f`, …) blocked with what/why/alternative in the deny message, ending "NO BYPASS EXISTS". Hooks are inert without their env flag — harmless outside zeroshot runs.
- **Instant-reject lists**: TODO/placeholder, "Phase 2 deferred", "will add tests later", any MUST criterion failing, and "Lazy Debugging Red Flags" (restart the service / clear the cache / works on my machine / blames the test).
- **Bounded everything**: worker maxIterations (5; debug 10), validator maxRetries (3), token budgets, char guard, capped AGENT_OUTPUT tail (8MB/8192 msgs), capped diagnostics.

**Testing itself:**
- **Two-stage template validation** (`src/template-validation/`): static schema check, then behavioral simulation — consensus-gate scenarios run through the real logic engine (both approve/reject branches), plus seeded random-topology simulation with step/wall-clock budgets and per-agent iteration caps.
- **Cycle detection** ("Gap 6", `src/config-validator.js:1564-1685`): DFS over the agent graph; cycle without escape logic = error, with escape logic = warning (simulation budgets backstop the warning case).
- **Protocol pinning**: golden request/response NDJSON transcripts (byte-level), one negative fixture per validation rule, and canonicalization fixtures (`base.json`/`base.canonical.json`/`base.sha256` + reordered variants) proving canonical-form idempotence — hash verified on disk.
- **Self-verifying exports**: trace/semantic JSONL exports seal a running SHA-256 and explicit `complete` flag + `issues[]` into the footer (`cli/export-stream.ts:98-118`).

## 5. Unique features & clever techniques

- **Junior/senior conductor with UNCERTAIN escape** (`cluster-templates/conductor-bootstrap.json`): cheap classifier may output `UNCERTAIN` → escalates to senior (which must decide). Prompts contain literal dollar costs ("$15/M Opus vs $3/M Sonnet"), an explicit "if unsure, choose STANDARD" bias, and a 7-item "NOT CRITICAL (common false positives)" list.
- **Two-persona worker prompts** (`full-workflow.json`): `prompt.initial` ("DO THE WORK. DON'T REPORT STATUS.") vs `prompt.subsequent` ("YOU FAILED. FIX IT.") with a 5-question self-verification gate ("Would I bet my salary this passes?") and named excuse anti-patterns.
- **Acceptance-criteria schema** (planner): `id/criterion/verification/priority`, minItems:3, ≥1 MUST, with contrastive BAD/GOOD examples (❌"Dark mode works" ✅"Toggle → contrast ratio >4.5:1, background #1a1a1a").
- **CLEAN DESIGN CHECK** (validator-code): instant-rejects backward-compat shims, re-export wrappers, `_unused` renames, legacy fallbacks — "a senior architect demolishes old scaffolding."
- **GENERALIZATION CHECK**: worker fixed one instance → validator greps for the pattern; N>1 unfixed → reject.
- **cmdproof pattern** (`src/command-proofs.ts`): prove an expensive command once, converted into a quality gate all agents (incl. git-pusher) must see satisfied; declarable inline via a ` ```zeroshot-command-proofs ` fenced block in the issue text.
- **`_republished:true` guards**: agents republishing their own trigger topic tag the message so they don't re-trigger themselves — cheap loop-breaker in the message graph.
- **Copy-containment** (`src/copy-containment.ts`): roots pinned by (device, inode) via `realpathSync.native`, re-asserted before every resolve — defeats symlink-swap TOCTOU; no `.`/`..` components allowed at all.
- **Stuck-provider detector** (`src/agent/agent-stuck-detector.ts`): two-sample /proc heuristic (state, wchan, CPU, ctx switches, socket queues); live network I/O subtracts 2 from the stuck score, overriding all idle signals.
- **Split completeness flags** (`cli/semantic-export.ts:169-180`): `source_complete` (raw bytes trustworthy) vs `semantic_complete` (parsed events trustworthy) — independently auditable.
- **Log-immutability proof**: full fstat snapshot equality (dev/ino/size/mtimeNs/ctimeNs) before/after streaming, `O_NOFOLLOW`, create-only `O_EXCL` outputs (`cli/trace-output.ts`, `cli/export-stream.ts`).

## 6. Strengths & weaknesses

**Strengths**
- Verifier thesis enforced structurally end-to-end: schemas → evidence → freshness → fail-closed ship gate.
- Cost-awareness baked into classification and staging (cheap-bias, cheap-before-expensive validation).
- Workflows-as-data enables static + simulated validation of the orchestration itself.
- Serious security engineering (containment, overlay verification, export hardening) unusual for an agent framework.
- Everything bounded; no unbounded loop or stream found.

**Weaknesses**
- **Dead config**: full-workflow's inline security/tester agents fire at `validator_count == 3`, but the router only ever emits 0/1/2 — unreachable unless invoked manually (verified against `src/config-router.ts:85-93`).
- Prompt discipline relies on verbatim duplicated blocks across templates — drift risk with no single source.
- Hard-coded dollar figures in prompts will rot as pricing changes (the bias rule is the durable part).
- Heuristic thresholds (stuck score 3.5/4.5) are tuning, Linux-only.
- Termination is asymmetric: debug-workflow has an explicit stop agent; full-workflow relies on orchestrator-side detection.
- Heavy machinery: SQLite ledger + JS predicates + template loading is a lot of substrate for small tasks (mitigated by TRIVIAL→single-worker routing).

## 7. Adaptable ideas

Raw candidates for other skill projects:

1. Evidence-or-reject validation schema (command/exitCode/output per criterion; CANNOT_VALIDATE = pass-with-warning).
2. Freshness-gated handoff: downstream step refuses evidence older than the latest implementation event.
3. Two-tier classifier: cheap model + UNCERTAIN escape hatch + cost-bias rule + explicit false-positive list.
4. Testable acceptance criteria: id/criterion/verification/priority schema with BAD/GOOD contrastive examples.
5. Two-persona prompts: separate initial vs post-rejection prompts, with a self-verification question gate.
6. Cheap-then-expensive staged validation; expensive stage loads only after cheap gate passes.
7. Mechanical rule enforcement: back every prose "don't" with a deny hook whose message gives what/why/alternative.
8. Self-verifying export format: running hash sealed in footer, explicit `complete` flag, fixed diagnostic vocabulary.
9. Static cycle detection + seeded simulation with step/time/iteration budgets as paired safety layers.
10. Shared verbatim rule blocks reused across personas (with the caveat: single-source them to avoid drift).
11. `_republished:true`-style self-trigger guards on any republish loop.
12. Sentinel values with documented meaning (`validator_count=0` for CRITICAL = "validators come from elsewhere").
13. Inline declarable proofs in free text (fenced block parsed into quality gates).
14. Instant-reject phrase lists ("works on my machine", "will add tests later") as validator tripwires.
15. Enforcement hierarchy as policy: Type system > linter > hook > documentation; "if enforceable, don't document."
