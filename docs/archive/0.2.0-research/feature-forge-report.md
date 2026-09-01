# Feature Forge, Autoprompt, Procoder, Zeroshot, and Fable Method: Comparative Analysis

## Executive synthesis

These repositories are adjacent, not equivalent:

- **Feature Forge** is a rigorous, instruction-only outer controller for one bounded Git work unit. Its differentiators are durable authority, artifact identity, invalidation, requirement-level acceptance, and recoverable branch finishing.
- **Autoprompt** is a multi-agent orchestration protocol and cross-provider deployment product. Its differentiators are adaptive fan-out, specialized roles, context-efficient dispatch, independent assurance, generated provider adapters, and substantial installer/runtime plumbing.
- **Procoder** is an executable repository-governance and quality harness. Its differentiators are deterministic refusal gates, explicit `unchecked` states, plain-file project controllers, a broad quality/tooling surface, and hooks that make some checks difficult for an agent to skip.
- **Zeroshot** is an executable, general-purpose multi-agent coordination engine centered on independent executor–verifier loops. Its established Node product adds conductor-based routing, custom message-driven workflows, a SQLite-backed resumable operational ledger with documented retention/closure limits, provider/session management, worktree or Docker isolation, and optional PR/merge delivery. The same repository now also ships a separate Rust-native one-run graph engine and OpenEngine Cluster protocol stack; it is not merely a port of the Node runtime.
- **Fable Method** is a compact, instruction-level operating procedure for agent work: classify, define done, gather primary evidence, decide, act surgically, verify by observation, and report honestly. Its four-skill family adds prompt-level fan-out, adversarial claim checking, and domain-evidence adapters. It has an unusually candid trap-evaluation culture, but no durable runtime, ledger, effect enforcement, or resume protocol.

The cleanest conceptual stack is therefore **Feature Forge as delivery authority**, **an execution engine such as Autoprompt or a deliberately constrained Zeroshot workflow behind a bounded adapter**, **Procoder-like deterministic checks as evidence providers**, and **Fable's intent/evidence/judge disciplines inside existing worker and review boundaries**. In current form, however, these projects cannot simply be nested: Feature Forge, Autoprompt and Zeroshot can each own lifecycle state, while `fable-loop` can introduce a competing prompt-level plan/dispatch loop. Zeroshot's built-in PR/ship paths and ledger/resume semantics make the ownership conflict especially concrete.

The strongest near-term direction for Feature Forge is not to import more stages. It is to make its existing guarantees executable: versioned adapter capabilities, a ledger/schema validator, concrete review-loop integration, deterministic readiness checks, an explicit verification inventory, and focused recovery fixtures. From Autoprompt, borrow input-bound dispatch and overlap-aware scheduling. From Procoder, borrow `unchecked is not clean`, structural spec/plan lint, and bounded exception closure. From Zeroshot, borrow workflow admission/graph validation, durable lease and ownership patterns, bounded evidence/observability, and isolation capability checks—but not its second scheduler, second ledger, automatic delivery, or native v2's terminal-on-loss/no-recovery semantics. From Fable, borrow decision-point evidence artifacts, defect-twin searches, adversarial claim reconciliation, and the discipline of publishing null and failed evals—but not a fifth lifecycle. Keep Feature Forge's authority, invalidation, UAT, and Finish models intact.

## Scope, method, and comparison caveat

This report evaluates the checked-out repositories as of **2026-08-22**:

| Repository | Snapshot inspected | Broad shape |
|---|---|---|
| Feature Forge | `c62f2d4` | 20 tracked files; almost entirely Markdown contracts/templates |
| Autoprompt | `8044d17` / package `1.0.3` | 494 tracked files; generated provider packages, Node CLI, Bash/PowerShell lifecycle code, tests and docs |
| Procoder | `2bc26c7` / documented release `1.1.1` | 522 tracked files; Go CLI, per-host adapters, repository templates/state, tests, docs and committed binaries |
| Zeroshot | `9feda13` / merged Node tag `v6.41.1`, Rust tag `zeroshot-rust-v0.1.1` | 1,884 tracked files; established Node/TypeScript orchestrator plus a separate Rust engine, cluster protocol, hosted/target surfaces, extensive tests and release machinery |
| Fable Method | `88b5cf3` / tag and plugin `v1.4.0` | 143 tracked files; four instruction skills, eight domain adapters, trap fixtures, raw eval results, small Python consistency CI and Claude plugin metadata |

The inspection combined a broad inventory, authoritative entry-point reading, implementation/test inspection, and independent repository/cross-cut analyses, including dedicated Zeroshot Node architecture, platform/security, Rust v2, Fable architecture/evaluation/platform, normalized-comparison and Feature Forge-adaptation passes. Current implementation and tests outrank marketing copy and historical design records. Claims about external hosts were treated as supported only to the degree the repository has executable or live-host evidence.

### Evaluation rubric

The common rubric covers: product job; abstraction level; lifecycle/state authority; planning and scope control; persistence/resume/recovery; delegation and concurrency; execution; review and verification; human authority; safety; portability; configuration; installation; licensing/release provenance; auditability; maturity evidence; and operational cost. “Best” and “strongest” below are qualitative judgments within that rubric, not statistically weighted scores; the decision-profile table makes the intended use-case weighting explicit.

### Evidence policy and limitations

There is a fundamental category asymmetry:

- Feature Forge's guarantees are predominantly **contractual**: an agent is instructed to maintain them in Markdown. Its maintainer contract explicitly says it has no separate runtime suite; prescribed checks validate documentation entry points and links, not end-to-end run semantics. [Feature Forge maintainer contract](/home/mark/kramtime/llm-skillbook/feature-forge/AGENTS.md:136)
- Autoprompt combines prompt-level orchestration rules with executable generation, installation, configuration, hashing, lifecycle checks, and tests. Its role and gate policies are not uniformly host-enforced.
- Procoder implements many checks in a compiled binary, but some workflow rules remain agent instructions, many domains are advisory by default, and hard hook enforcement varies by host.
- Zeroshot is the broadest executable orchestration system in the roster, but its two product lines have different contracts. The Node product is a resumable multi-agent cluster runtime; native v2 is an intentionally lean, exactly-one-run graph engine where runtime, controller, workspace, session loss, or force-stop is terminal and replay/resume/recovery are explicit non-goals. Treating them as one maturity or feature claim would be misleading. [Native-v2 boundary](/home/mark/tools/zeroshot/AGENTS.md:243)
- Fable Method is instruction-only at execution time, like Feature Forge, but unlike Feature Forge it carries a behavioral smoke-eval corpus and a small structural CI checker. Those artifacts are meaningful evidence of scenario-specific prompt behavior, not runtime enforcement or a general benchmark. [Eval limits](/home/mark/tools/fable-method/eval/README.md:58)

Autoprompt's published 73/89 versus 60/89 Terminal-Bench result is useful directional evidence, not a fully reconstructible benchmark: the original per-task Autoprompt result map was not retained. [Benchmark evidence boundary](/home/mark/tools/autoprompt-skill/docs/benchmarks/terminal-bench-2.1.md:3) Its stated roughly 3× time and 2× token cost is explicitly an estimate, not a measurement. [Autoprompt README](/home/mark/tools/autoprompt-skill/README.md:114)

Feature Forge's two focused entry-point/link tests passed, but it remains instruction-only and has no behavioral suite to execute. Autoprompt's provider-contract and payload checks also passed. Procoder's committed binary reports version `1.1.1`, but its Go tests could not be executed because Go is absent in this environment; its test assessment is static. Zeroshot's repository contains hundreds of Node and Rust test files, but a full test run is too broad for this report and no credit-consuming provider run was attempted; the project explicitly requires permission before `zeroshot run`. Fable's `python3 .github/checks.py`, plugin validation and shell syntax checks passed, but no model/API eval was run; its CI validates repository structure and JSON parseability rather than replaying behavioral results.

Two Zeroshot Node contract checks were attempted but are **unavailable**, not passing: template validation cannot load the unbuilt generated `lib/settings` runtime, and the Rust-distribution repository check cannot load `js-yaml`, because this checkout has no `node_modules` or generated build output. A focused offline Rust protocol test also could not resolve locked `tokio-stream 0.1.19` from the local cache; no network dependency fetch was performed. These environment failures do not imply defects in Zeroshot, and the maturity assessment below therefore relies on code, test inventory and CI configuration rather than a current local green suite.

Licensing is not symmetric: Autoprompt, Zeroshot and Fable Method are [MIT-licensed](/home/mark/tools/autoprompt-skill/LICENSE:1), [respectively](/home/mark/tools/zeroshot/LICENSE:1), [and](/home/mark/tools/fable-method/LICENSE:1); Procoder is [Apache-2.0-licensed](/home/mark/tools/procoder/LICENSE:1); and no LICENSE file is tracked in the inspected Feature Forge component or skillbook root. That absence is not proof of prohibition or permission; redistribution/adaptation needs clarification from its owner before code or prose is copied.

## Feature Forge interim report

### Purpose and architecture

Feature Forge is a single-run outer workflow for a bounded feature, migration, refactor, or comparable Git work unit whose ambiguity, risk, or coordination warrants more ceremony than a focused skill. Its entry contract is intentionally small: one canonical run, one durable ledger, and one next permitted action. Native task views are disposable projections; subskills return to the controller and cannot advance the run themselves. [Feature Forge skill](/home/mark/kramtime/llm-skillbook/feature-forge/SKILL.md:8)

Its live authority is split cleanly across four sources:

- the entry skill for controller sovereignty;
- the workflow contract for paths, stages, state, identities, checkpoints and Finish;
- the authority contract for modes, materiality, scope, specification and acceptance;
- the adapter/review contract for the four delegated boundaries and worker packets.

The four canonical artifacts are a specification, plan, ledger and final report. Only a passing reviewed specification and plan become frozen `<path>@<git-blob-id>` authorities; the ledger and report remain mutable evidence records. [Workflow: artifacts and identity](/home/mark/kramtime/llm-skillbook/feature-forge/references/workflow.md:8)

### Lifecycle and authority model

The lifecycle has fourteen ordered stages:

`Preflight → Brainstorm → Harden → Candidate gate → Specification review → Specification freeze → Plan → Plan review → Implement → Implementation review → Final verification → Acceptance → Report → Finish`

The details matter more than the count. Preflight resolves run identity, slug/branch collisions, isolated worktree, dirty-state attribution and reviewer-runner authority. Harden closes the complete material decision frontier. Candidate and plan reviews seal exact content. Implementation review seals a committed whole-tree subject. Final verification proves the reviewed tree did not drift. Acceptance is traced per requirement/scenario. Report records readiness without pretending the run is finished. [Ordered stages](/home/mark/kramtime/llm-skillbook/feature-forge/references/workflow.md:160)

The ledger is a manual write-ahead log: it is persisted before each external dispatch and immediately after each return; every nonterminal state exposes exactly one next action; `review_active` permits only waiting for or recovering the existing review. Resume rereads every named artifact and revalidates blob identities, seals, worktree, branch, commits and evidence rather than trusting conversation memory. [State and resume contract](/home/mark/kramtime/llm-skillbook/feature-forge/references/workflow.md:25)

Scope control is unusually explicit. Modes are interactive, supervised (default), and unattended; uncertain decisions classify upward. The specification requires stable requirement/scenario IDs, observable normative behavior, decisions and authority, test strategy, acceptance classification, and an empty `Open questions` section. New work is deferred unless the user explicitly expands the work unit. [Authority contract](/home/mark/kramtime/llm-skillbook/feature-forge/references/authority.md:9)

### Distinctive capabilities

1. **Separate candidate seals and frozen Git identities.** A candidate may be repaired between review rounds without becoming authority; only the passing snapshot is committed and frozen.
2. **Fixed invalidation graph.** Specification, plan, implementation, and acceptance defects invalidate the correct downstream evidence; later green results cannot survive a changed root cause. [Invalidation graph](/home/mark/kramtime/llm-skillbook/feature-forge/references/workflow.md:98)
3. **Requirement-level acceptance and honest UAT.** Unattended mode never fabricates human approval. It may record a waiver only when a predeclared automated substitute meets the same evidence criterion; otherwise acceptance is infeasible and blocks. [UAT contract](/home/mark/kramtime/llm-skillbook/feature-forge/references/authority.md:147)
4. **Strong worker packets.** Every task dispatch binds task and requirement/scenario IDs, owned paths, interfaces, invariants, dependencies, verified inputs, exact evidence, and a prohibition on changing frozen authority. [Worker packet](/home/mark/kramtime/llm-skillbook/feature-forge/references/adapters-and-reviews.md:126)
5. **Recoverable logical Finish.** Stage 13 allocates `finish_id`; Stage 14 uses durable `ready → claimed → menu_pending → choice_recorded → executing → terminal` receipts, a resumable blocked overlay, pre-side-effect write-ahead commits, and read-only reconciliation. It explicitly avoids the false claim that external effects are physically atomic. [Finish protocol](/home/mark/kramtime/llm-skillbook/feature-forge/references/workflow.md:279)

### Strengths and advantages

- **Best delivery-authority and acceptance traceability model of the five.** It distinguishes transient UI, mutable records, review seals, frozen authority, implementation evidence, acceptance authority and external effects.
- **Best upstream-change discipline.** The invalidation graph makes stale downstream evidence visibly invalid rather than merely outdated.
- **Best human-decision semantics.** Materiality, standing authority, new-request deferral, explicit waivers and non-fabricated UAT are unusually careful.
- **Best crash-safe finishing design.** It treats merge/push/PR/cleanup ambiguity as a distributed-systems problem and blocks instead of replaying an uncertain effect.
- **Low implementation footprint.** The skill is inspectable and portable because its core is plain Markdown, with no runtime dependency of its own.

### Weaknesses, costs, and risks

1. **The central guarantees are not mechanically enforced.** There is no schema validator, atomic transition API, lease/lock, packet validator, adapter handshake, or effect executor. The ledger template is a checklist, so “one next action,” identity checks, dispatch receipts and journal sequencing depend on agent compliance.
2. **The current review integration is not executable as described.** Feature Forge requires sealed read-only review rounds with controller-owned fixes between rounds. The live `review-loop` instead owns a mutation-capable FIX phase; its round-N triage/reconciliation path explicitly fails closed as deferred; and its production invocation accepts `target`, Git range/exclusions, profile/time/tier, `ground_truth` and `run_root`, but no first-class subject set, deployment context or completion criterion. [Feature Forge review mapping](/home/mark/kramtime/llm-skillbook/feature-forge/references/adapters-and-reviews.md:179) [review-loop lifecycle](/home/mark/kramtime/llm-skillbook/review-loop/SKILL.md:59) [round-N refusal](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/controller.py:787) [production request schema](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/profiles.py:204) It also rejects a non-directory target, so exact-file candidate review needs an adapter-owned materialization/mapping that Feature Forge does not currently define; directory-only input does not make exact-file review impossible, but it makes the advertised direct mapping incomplete. [Directory precondition](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/controller.py:360) This is a present compatibility gap, not a theoretical weakness.
3. **Execution and Finish adapters also rely on overriding live skill behavior.** The wrapped execution skills require their own ledgers/reviews and ultimately `finishing-a-development-branch`, while Feature Forge says the adapter must halt before that finishing step; the live finishing skill requires presenting a human menu and waiting. [Executing-plans terminal step](/home/mark/.codex/plugins/cache/openai-curated-remote/superpowers/6.3.0/skills/executing-plans/SKILL.md:31) [Subagent-driven state and terminal step](/home/mark/.codex/plugins/cache/openai-curated-remote/superpowers/6.3.0/skills/subagent-driven-development/SKILL.md:86) [Finishing menu](/home/mark/.codex/plugins/cache/openai-curated-remote/superpowers/6.3.0/skills/finishing-a-development-branch/SKILL.md:53) No technical containment or capability negotiation demonstrates the required override.
4. **No mixed DAG scheduler.** Execution is classified wholesale as parallel subagents or inline coupled work. It lacks launch groups, integration-lane modeling, retries/cancellation/timeouts, conflict handling, resource budgets and partial re-planning.
5. **High manual ceremony and synchronization cost.** Four canonical artifacts, fourteen stages, three reviews, blob IDs, seals, eight checkpoint categories, per-requirement acceptance and Finish receipts create a broad error surface, especially without tooling.
6. **Dependency/version skew is implicit.** Feature Forge depends on review-loop and several Superpowers skills, but its package/installer does not express compatible versions or capabilities and its tests do not exercise an end-to-end run.

### Best fit

High-risk or ambiguous bounded Git work where scope authority, auditability, truthful acceptance and safe finishing matter more than speed. It is a poor fit for trivial edits, highly exploratory work without a stable work-unit boundary, or environments where its delegated skill versions cannot prove the required adapter semantics.

## Autoprompt interim report

### Purpose and architecture

Autoprompt is a useful-first multi-agent orchestration loop: explicit invocation captures one mission, produces one independently approved executable roadmap, fans implementation into dependency-safe lanes, then converges through independent review and verification. Unlike Feature Forge, it is also a distribution product: a canonical provider-neutral contract generates native packages for Claude, Codex, OpenCode, Kilo, VS Code and Prime. The current contract defines 25 named personas and 18 frameworks. [Contract overview](/home/mark/tools/autoprompt-skill/agents/contracts/README.md:1) [Codex skill](/home/mark/tools/autoprompt-skill/agents/codex/SKILL.md:6)

Its logical hierarchy separates L0 reporting, L1 coordination, optional L2 management, L3 execution, and L4 terminal assurance/record roles. A worker must be a registered `ap-*` persona, validate its activation marker, and avoid recursive Autoprompt invocation. The dispatcher retains integration and final judgment. [Hierarchy contract](/home/mark/tools/autoprompt-skill/agents/codex/SKILL.md:74)

### Lifecycle and authority model

Invocation itself authorizes the mission; Autoprompt asks only for undefined concurrency/model controls. A bare skill load does not start or resume a run. The first scope pass produces one canonical `ROADMAP.md`, with mission binding, repository intelligence, stable items, owned boundaries, dependency/launch groups, integration lane, tests, unhappy paths, real verification and conditional detailed-planning flags. Implementation-ready items skip a separate plan gate. [Start and roadmap contract](/home/mark/tools/autoprompt-skill/agents/codex/SKILL.md:10)

Topology is adaptive:

- bounded scope: roadmap author plus concurrent independent reviewer and blind verifier;
- multi-surface scope: author, two complementary scouts, then reviewer and blind verifier;
- unusually large scope: may exceed the ordinary six-agent budget only with a recorded reason.

Concurrency is `tokensaver`, `wide`, or a custom cap. Disjoint ready work is spawn-all-then-collect, overlapping writes are invalid, and integration becomes an explicit lane. [Decomposition and parallelism](/home/mark/tools/autoprompt-skill/agents/codex/PLAYBOOKS.md:11)

Governance is exactly three files outside the target working tree: append-only `PROMPTS.txt`, canonical `ROADMAP.md`, and append-only `GATELOG.md`. Later briefs carry a mission path, SHA-256, byte length and nonce rather than copying the mission/transcript. Resume is explicit and starts from the final GATELOG frontier; workers reopen substantive evidence. [Governance and compact briefs](/home/mark/tools/autoprompt-skill/agents/codex/SKILL.md:51)

### Distinctive capabilities

1. **Context-efficient, input-bound dispatch.** Mission and roadmap content are stored once; workers receive minimal role/boundary/acceptance/evidence pointers and fail on mismatched bindings. This reduces repeated context and helps preserve blind review.
2. **Adaptive decomposition with explicit integration lanes.** Category, playbook tag and tier are independent axes; actual dependencies determine launch groups rather than a single global sequential/parallel choice.
3. **Specialized assurance.** Roadmap review, blind fresh verification, implementation review, runtime verification, optional juries, sweep convergence and adversarial goal check separate authorship from acceptance. [Gate contracts](/home/mark/tools/autoprompt-skill/agents/codex/GATES.md:30)
4. **Debug depth-lock.** Defect work requires a genuine red reproduction and independent search for the deepest responsible decision point, resisting symptom-layer patches. [Depth-lock](/home/mark/tools/autoprompt-skill/agents/codex/GATES.md:113)
5. **Generated provider-native packages.** One canonical capability/topology contract generates hundreds of provider files plus sorted SHA-256 runtime inventories. Installers use receipts, atomic placement, re-verification, scoped uninstall and provider-specific activation.
6. **Advanced provider-specific hardening.** Codex supports private cast profiles, root/role-shadow checks, staged configuration and rollback; Prime uses sealed dispatch bindings; OpenCode/Kilo profiles restrict task/skill behavior. These controls are uneven because host capabilities differ.

### Strengths and advantages

- **Best multi-agent execution model.** It offers truthful disjoint ownership, launch groups, integration lanes, concurrency budgets and a role hierarchy designed to avoid self-review.
- **Best context economics.** Hash/nonce-bound pointer briefs reduce transcript duplication and keep reviewers from inheriting success claims.
- **Best cross-provider contract packaging of the five.** Generated native adapters, payload manifests, receipt-owned installation, doctor/repair/uninstall flows and release checks make this much more than a prompt repository.
- **Strong assurance vocabulary.** Debug, research, user-facing, polish and external-target work receive different checks instead of one undifferentiated swarm.
- **Good operational maturity signals.** Contract generation and payload consistency are tested; prepublish runs the full verify suite; CI actions are pinned; benchmark limitations are disclosed rather than hidden.

### Weaknesses, costs, and risks

1. **Prompt policy is not uniformly capability policy.** On Codex, activation markers, no-recursion and per-role dispatch rules are largely instructions; the private profile registers installed roles but does not mechanically encode every persona's child allowlist. Other providers enforce different subsets. [Codex profile generation](/home/mark/tools/autoprompt-skill/agents/codex/workflow/codex-agent-profile.js:74)
2. **Rigid quality rules can misfit real repositories.** Universal strict TDD, no mocked system-under-test/integration database, and a fixed ≥95% changed-line/touched-module coverage floor can be infeasible or encourage metric gaming for infrastructure, generated code, legacy systems or unavailable external services. [Build and verification gates](/home/mark/tools/autoprompt-skill/agents/codex/GATES.md:133)
3. **Large coordination and compatibility surface.** Twenty-five roles, eighteen frameworks, six providers, multiple model-routing paths, supervisors, installers, legacy migration and two large Bash/PowerShell lifecycle implementations create substantial maintenance cost.
4. **Token/latency overhead.** The repository itself estimates about 3× time and 2× tokens. Bounded topology reduces needless fan-out, but the assurance pipeline can still dominate small tasks.
5. **Provider support evidence is not equal to live semantic proof.** Generated bytes and lifecycle fixtures can prove parity and installation behavior, not that six changing vendor runtimes preserve dispatch, isolation and failure semantics. The compatibility guide itself requires real-host lifecycle testing, and four providers lack custom agent routing. [Compatibility proof requirements](/home/mark/tools/autoprompt-skill/docs/guides/custom-agent-compatibility.md:55) [Routing matrix](/home/mark/tools/autoprompt-skill/README.md:127)
6. **Pre-merge coverage gap.** Ordinary pull requests run `npm test`, while full lifecycle/prepublish verification runs in the separate release-readiness workflow on main/schedule; some installer/provider regressions may therefore be detected after merge. [PR CI](/home/mark/tools/autoprompt-skill/.github/workflows/ci.yml:19) [Release readiness](/home/mark/tools/autoprompt-skill/.github/workflows/release-readiness.yml:28)
7. **Supply-chain and environment footprint.** Node 20, Python 3.11/PyYAML, modern Bash and provider-specific configuration are nontrivial prerequisites. Interactive startup may self-update from npm/GitHub discovery; managed environments may reject that trust model. [Runtime requirements](/home/mark/tools/autoprompt-skill/README.md:60) [Update path](/home/mark/tools/autoprompt-skill/bin/autoprompt.cjs:875)
8. **Governance is lighter than Feature Forge's.** GATELOG frontier recovery is efficient, but it does not provide the same artifact-by-artifact Git identity, invalidation graph, requirement-level acceptance, or external-effect Finish journal.

### Best fit

Large or multi-surface coding missions where parallelism, independent assurance and reduced supervision justify higher compute and operational complexity—especially across supported coding-agent hosts. It is overkill for very small changes and a poor fit where fixed coverage/mocking rules or provider/runtime drift cannot be accommodated.

## Procoder interim report

### Purpose and architecture

Procoder is a compiled repository governance and quality harness. Its thesis is: the binary computes; the agent acts. It returns findings, formatted output or proposed diffs, but does not silently rewrite user code. A missing, failed, timed-out or unreadable check is `unchecked`, never clean. Repository-local `.procoder/` files override defaults. [Architecture contracts](/home/mark/tools/procoder/docs/architecture.md:44)

The product consists of one static Go binary, thin skill/command adapters, hooks, committed per-platform binaries, and human-readable repository state. Its manual dispatcher exposes workflow controllers (`spec`, `plan`, `todo`, `backlog`, `sprint`, `adr`, `release`), deterministic gates (`check`, formatting, lint, security, docs, CI, infra, tests), environment/dependency/performance tooling, a code index, and host/upgrade support. [CLI dispatcher](/home/mark/tools/procoder/cmd/procoder/main.go:405)

### Lifecycle and authority model

Procoder offers a quality chain rather than one global run state machine:

`classify → spec → plan → backlog/story or todo → sprint → TDD/build → test → gate → PR/review/lessons → merge/retro → release`

Each link has a refusing controller. `spec check` rejects empty sections, unresolved human questions and vague criteria. `plan check` requires a stranger-executable plan with files and concrete steps. Story/todo close requires checked criteria, evidence and a clean gate; test policy may additionally require a verified green suite. Sprints enforce one active scope and explicit carry-over/retro. Release aggregates version sync, changelog, clean tree, gate and optionally tests, then prints rather than runs the tag command. [Procoder work contract](/home/mark/tools/procoder/AGENTS.md:30) [Workflow guide](/home/mark/tools/procoder/docs/workflow.md:24)

State is distributed among plain files: specs, plans, backlog, sprints, todos, ADRs, answers, lessons, debt and configuration. This is excellent for repository visibility but is not equivalent to Feature Forge's single authoritative ledger or Autoprompt's run frontier.

### Distinctive capabilities

1. **`Unchecked` is a first-class failing state.** Formatter/tool/scanner/test failures cannot be presented as green. [Gate implementation](/home/mark/tools/procoder/internal/gate/gate.go:22)
2. **One shared gate collection path.** `check`, Git reports and commit interception reuse common formatting/hygiene/lint/secrets/docs/CI/infra machinery, reducing verdict drift.
3. **P-CONTROL and D-OVERRIDE.** The agent retains edit judgment; repository configuration/rubrics/templates win over built-in defaults.
4. **Broad deterministic domain tooling.** Formatting, secrets, lint, documentation obligations, CI pinning/timeouts, infrastructure checks, real test runners, dependency freshness, benchmarks, environment drift and code indexing are unified in one CLI.
5. **Self-learning escape closure.** A lesson without a concrete adaptation remains `UNLEARNED`; Copilot review findings can be sanitized, consented, filed and recorded for future gate/rubric/test adaptation. [Lessons loop](/home/mark/tools/procoder/internal/lessons/lessons.go:1)
6. **Code map without a resident MCP server.** ctags plus optional SCIP provide find/refs/callers/impact/unused/entrypoints and a Go rename diff, with explicit textual fallback.
7. **Cross-host policy delivery.** A canonical AGENTS body is mirrored into skills/rules/plugins for many agents; hooks enforce some lifecycle points, and drift between mirrors is itself a gate finding. [Portability](/home/mark/tools/procoder/docs/portability.md:1)
8. **Reproducible distribution and cautious upgrades.** Cross-build flags, checksum comparison, version-pinned gate tools, consent, manager ownership checks, size/hash verification and atomic replacement are above-average operational details.

### Strengths and advantages

- **Best executable evidence machinery.** It turns many quality claims into deterministic exit codes and machine-generated findings rather than reviewer prose.
- **Best explicit-unknown semantics.** Missing tools and unavailable suites are visible; this is exactly the behavior an autonomous agent needs to avoid false completion.
- **Broadest day-to-day developer toolbox.** It spans planning, task control, formatting, tests, security, docs, CI, infra, release, code navigation and learning.
- **Strong refusal-path test philosophy.** The repository has a large test inventory centered on missing tools, drift, malformed input, incomplete artifacts, bypasses and failure aggregation—not only happy paths.
- **Good consent boundary.** Formatting and rename output remain reviewable; release does not tag; upgrades and issue publication require consent.
- **Low hook-time runtime complexity.** One static binary requires no network at hook time and can work in air-gapped environments.

### Weaknesses, costs, and risks

1. **The advertised chain is only partly enforced.** Plans do not mechanically validate their source spec; todos need not link to plans/specs; orphan stories can exist; TDD red-before-green evidence is instructional; closure evidence is structural rather than semantic. [Plan checker](/home/mark/tools/procoder/internal/plan/plan.go:106) [Todo closure](/home/mark/tools/procoder/internal/todo/todo.go:134) [Orphan reporting](/home/mark/tools/procoder/internal/backlog/board.go:121)
2. **A clean default gate does not prove working behavior.** Tests are not in `procoder check` and default test blocking is off. Lint, docs obligations, deep security and much infrastructure policy can also remain advisory. Users must distinguish “gate clean” from “all relevant domains verified.” [Gate composition](/home/mark/tools/procoder/internal/gate/gate.go:81) [Default policies](/home/mark/tools/procoder/internal/config/config.go:38)
3. **Breadth is uneven.** Test runners cover fewer ecosystems than formatting/lint; benchmark and rename support are Go-centric; precise indexing requires several external tools; audit does not actually run every advertised domain. [Test-runner ecosystems](/home/mark/tools/procoder/internal/testrun/testrun.go:56) [Audit implementation](/home/mark/tools/procoder/internal/audit/audit.go:29)
4. **Host enforcement is inconsistent.** Claude is the continuously tested reference host. Static adapter tests cannot prove other hosts. A concrete documentation/configuration contradiction exists for Copilot CLI: the portability guide later claims shared pre-tool commit blocking, while the shipped hook manifest appears to provide session-start only. [Host-test boundary and enforcement claims](/home/mark/tools/procoder/docs/portability.md:54) [Copilot hook manifest](/home/mark/tools/procoder/hooks/copilot-hooks.json:1)
5. **Concurrency safety is weak for repository state.** Several task/sprint/answer transitions rewrite whole files without locks or transaction coordination; parallel agents can race and lose state. [Todo rewrite](/home/mark/tools/procoder/internal/todo/todo.go:187) [Sprint rewrite](/home/mark/tools/procoder/internal/backlog/sprint.go:192) [Answer rewrite](/home/mark/tools/procoder/internal/ask/file.go:100)
6. **CI has meaningful omissions.** CI runs `go test ./internal/...` but not `cmd/procoder/main_test.go`, leaving CLI usage/dispatch behavior outside the normal test invocation; docs deployment installs an unpinned dependency. [CI test scope](/home/mark/tools/procoder/.github/workflows/ci.yml:33) [CLI tests](/home/mark/tools/procoder/cmd/procoder/main_test.go:13) [Docs deployment](/home/mark/tools/procoder/.github/workflows/ci.yml:286)
7. **External toolchain cost.** Honest `unchecked` reporting is correct but can create setup friction in polyglot repositories. Many deeper guarantees exist only when their external tools are installed and correctly configured.
8. **Documentation and CLI drift exists.** One concrete example is the documented backlog seed path argument versus the implementation's spec-name handling. [Documented invocation](/home/mark/tools/procoder/docs/workflow.md:53) [Implemented lookup](/home/mark/tools/procoder/internal/backlog/seed.go:61)

### Best fit

Repositories that want deterministic, reviewable agent guardrails and a broad quality toolbox while keeping humans/agents in control of edits and external effects. It complements an orchestrator well. It is less suitable as the sole end-to-end delivery controller or where teams expect every advertised domain and host integration to be blocking and equally proven out of the box.

## Zeroshot interim report

### Purpose and architecture

Zeroshot is an executable, general-purpose multi-agent coordination engine for well-bounded software changes with measurable acceptance criteria. Its established Node product drives an executor–verifier loop: a conductor classifies the task, a workflow template wires topic-triggered agents, an executor changes an isolated workspace, and separate validator turns approve or reject the observable result. Durable messages flow through a SQLite ledger and pub/sub façade. [Product thesis](/home/mark/tools/zeroshot/README.md:25) [Node ledger and bus](/home/mark/tools/zeroshot/src/ledger.js:60)

The repository also contains a separate native Rust product and OpenEngine Cluster protocol stack. Native v2 admits a typed `GraphSpec`, compiles and bounds it through a production semantic verifier, fixes a graph-wide provider plus per-node model/effort/session/environment plan, and executes exactly one run through a lean controller and ledger. The Node and Rust products have independent releases and materially different persistence/recovery semantics; one must not be used as evidence that the other implements the same behavior. [Native-v2 boundary](/home/mark/tools/zeroshot/AGENTS.md:243) [Graph contract](/home/mark/tools/zeroshot/crates/openengine-cluster-protocol/src/graph.rs:145)

### Lifecycle and authority model

The Node default begins with a model-driven two-level conductor. It classifies complexity (`TRIVIAL`, `SIMPLE`, `STANDARD`, `CRITICAL`) and type (`INQUIRY`, `TASK`, `DEBUG`); an uncertain junior result escalates to a senior model. Deterministic routing then selects single-worker, worker-validator, debug, or full workflow. TRIVIAL is an important exception to the headline executor–verifier thesis: it uses one worker and no validator. STANDARD adds planning and two validators; CRITICAL dynamically stages four validators. [Conductor](/home/mark/tools/zeroshot/cluster-templates/conductor-bootstrap.json:6) [Routing](/home/mark/tools/zeroshot/src/config-router.ts:56) [Documented exception](/home/mark/tools/zeroshot/README.md:85)

Custom workflows are JSON message graphs. Agent IDs, roles and topics are open strings; triggers can carry JavaScript predicates; retry cycles are legal; sub-clusters may nest five levels. Template resolution preserves typed whole-value parameters and rejects unresolved variables/path traversal; configuration admission checks bootstrap/completion reachability, cycles, role/topic semantics, nesting and provider declarations. The orchestrator may also validate and apply topology operations during a run. This is far more flexible—and a far larger correctness/security surface—than Feature Forge's fixed sequence. [Custom workflows](/home/mark/tools/zeroshot/README.md:100) [Config validator](/home/mark/tools/zeroshot/src/config-validator.js:78)

Node state is operational rather than repository-authoritative. Each cluster persists metadata plus a SQLite ledger under `~/.zeroshot`; stop preserves the worktree/container for resume, while kill removes it. Resume reconstructs durable workflow signals, refuses ambiguous states, restores agents/isolation, and resumes either the failed agent or eligible handlers. Context is rebuilt from prioritized ledger packs, a durable derived `STATE_SNAPSHOT`, compact variants, a token budget and a hard character guard. [Resume implementation](/home/mark/tools/zeroshot/src/orchestrator.js:2600) [Context packs](/home/mark/tools/zeroshot/src/agent/context-pack-builder.ts:59)

Native v2 intentionally chooses a different boundary. One run owns one workspace; ordinary verifiers are read-only and may overlap, while workers and Git delivery require exclusive write access. Reducer-authorized dispatches are made durable before execution. A filesystem controller lease and lean SQLite ledger record immutable admission, ordered events/cursors, node outcomes, safe logs, force intent and one terminal result. Runtime, controller, workspace or reusable-session loss—and force-stop—are terminal. There is no execution replay, resume, workspace replacement, recovery engine, artifact store or CAS. [Native scheduling boundary](/home/mark/tools/zeroshot/AGENTS.md:277) [V2 ledger](/home/mark/tools/zeroshot/zeroshot-rust/src/v2_run_ledger.rs:1)

### Distinctive capabilities

1. **Executable workflow-graph admission.** The Node validator rejects many dead or malformed topic graphs. Separately, the OECP full-v1 production verifier proves typed payload/control flow, worker compatibility, structural bounds, writer overlap and finite resource ceilings; native-v2 admission applies additional restrictions before its runtime executes the verified plan. [Node admission](/home/mark/tools/zeroshot/src/config-validator.js:78) [OECP verifier](/home/mark/tools/zeroshot/crates/openengine-cluster-server/src/graph_verifier.rs:21) [Native-v2 admission](/home/mark/tools/zeroshot/zeroshot-rust/src/native_v2_admission.rs:1)
2. **Concrete Node executor–verifier runtime.** On SIMPLE+ default paths, validators run distinct provider turns, are instructed to reproduce claims with commands, and rejection loops back to execution under bounded iterations/retries. Final validator exhaustion becomes rejection rather than approval. [Agent lifecycle](/home/mark/tools/zeroshot/src/agent/agent-lifecycle.js:629)
3. **Durable Node runtime forensics.** The ledger supplies ordered causal state; exact prompts and task-log bytes can be exported as a deterministic, provider-neutral, create-only trace with explicit missing/changing evidence and an incomplete footer. A separate semantic projection uses registered stateful provider parsers without rewriting the native evidence. [Trace export](/home/mark/tools/zeroshot/cli/trace-export.ts:48) [README evidence contract](/home/mark/tools/zeroshot/README.md:169)
4. **Registry-driven providers and capability probes.** The Node registry binds provider identity, invocation lane, credentials, isolation/session/schema/search capabilities and model levels for Claude, Codex, Gateway, Gemini, OpenCode, Pi, OMP, Kiro and Copilot. Adapters probe version/flag support rather than assuming every installed CLI is equivalent. [Provider registry](/home/mark/tools/zeroshot/src/agent-cli-provider/provider-registry.ts:267)
5. **Isolation and delivery as product features.** Guided setup defaults to worktrees; Docker and an explicit current-checkout escape hatch exist; `--pr` and `--ship` cascade into branch/PR/merge delivery. Fresh command evidence gates the git-pusher handoff. [Isolation matrix](/home/mark/tools/zeroshot/README.md:125) [Delivery gate](/home/mark/tools/zeroshot/src/agents/git-pusher-template.js:164)
6. **Strong ownership/containment machinery in selected paths.** Copy operations pin canonical roots and filesystem identities and revalidate containment; OMP continuation uses bounded descriptor-pinned artifact checks plus owner-fenced SQL compare-and-swap transitions; Rust secrets stay outside protocol/ledger state and faults/observations use closed redacted types. [Copy containment](/home/mark/tools/zeroshot/src/copy-containment.ts:73) [Closed faults](/home/mark/tools/zeroshot/zeroshot-rust/src/fault.rs:20)
7. **Portable native engine and protocol.** Rust packages five native archives plus checksums and a self-hosted target image; OECP exposes typed submit/observe/watch/log/attach/force surfaces. Local and hosted compositions reuse the same one-run engine behind different host adapters. [Distribution contract](/home/mark/tools/zeroshot/docs/zeroshot-rust-distribution.md:1) [Native observation](/home/mark/tools/zeroshot/crates/openengine-cluster-protocol/src/native_v2_observation.rs:1)

### Strengths and advantages

- **Strongest executable orchestration/runtime machinery in the roster.** Zeroshot supplies real scheduling, durable messaging, provider process ownership, isolation, bounded retries, resume (Node), terminal faulting (Rust), monitoring and delivery rather than only instructions.
- **Strong Node independent-verification implementation on non-TRIVIAL defaults.** Validator turns are separated from executor sessions/reasoning, consume explicit handoffs, and are expected to run/reproduce observable checks; failures re-enter the workflow.
- **Best Node workflow configurability.** Topic graphs, conditions, parameterized templates, cycles and nested clusters can express topologies well beyond either Feature Forge or Autoprompt.
- **Best Node run-level raw evidence export.** Create-only trace bundles preserve exact selected prompts and raw task bytes with completeness accounting instead of only summaries or reviewer claims.
- **Sophisticated process/session/filesystem safety in modern paths.** Bounded output, exact session ownership, pinned descriptors, closed cleanup receipts, redacted diagnostics and Rust typed fault/effect contracts show substantial adversarial engineering.
- **Broad repository-level operational surface.** Node supplies nine provider engines, five issue sources, foreground/daemon/attach modes, worktree/Docker and PR/ship; native v2 adds hosted targets and native binaries. Together they form standalone products rather than an orchestration specification.

### Weaknesses, costs, and risks

1. **Product and compatibility surface is enormous.** The repository simultaneously carries the established Node orchestrator, multiple provider invocation protocols, task/session runtimes, issue/delivery systems, Docker/worktree handling, hosted/cluster protocol layers and a separate Rust product. Provider truth and safety semantics are not fully unified across Node, Rust, hosted and docs; drift risk is structural.
2. **“Independent verification” is conditional, not universal.** Node TRIVIAL omits a verifier. The default Node full-workflow schema also describes `CANNOT_VALIDATE` as “PASS with warning,” while its prompt and formatter treat incomplete validation more strictly—an internal contract inconsistency and a direct incompatibility with Feature Forge's unavailable-evidence/infeasibility rules. [Requirements validator schema](/home/mark/tools/zeroshot/cluster-templates/base-templates/full-workflow.json:380)
3. **Node conductor routing is an LLM judgment.** Schema-constrained escalation helps, but there is no deterministic proof that a security-sensitive or cross-cutting task was classified at the correct rigor. A misclassified TRIVIAL task can bypass independent review.
4. **Custom Node workflows are executable trusted configuration, not harmless data.** JavaScript predicates run in a time-bounded VM and hooks/transforms can drive topology and effects. The VM improves liveness but is not demonstrated as a hostile-configuration security boundary; untrusted workflow files need a separate threat model. [Logic engine](/home/mark/tools/zeroshot/src/logic-engine.js:94) [Hook executor](/home/mark/tools/zeroshot/src/agent/agent-hook-executor.js:303)
5. **Node crash safety has defined limits.** The cluster can resume many durable states, but raw `AGENT_OUTPUT` is compacted to an 8 MiB/8192-message tail with omission receipts and task logs as full authority; writes after ledger close are deliberately dropped. Native v2 goes further in the opposite direction: any runtime/workspace/session/controller loss is terminal, so it cannot supply Feature Forge's reconciliation/recovery contract. [Ledger compaction](/home/mark/tools/zeroshot/src/ledger.js:24) [V2 non-goals](/home/mark/tools/zeroshot/AGENTS.md:291)
6. **Node Docker is not a strong hostile-code sandbox while it mounts the host Docker socket.** Containers receive `/var/run/docker.sock`; code inside can ask the host daemon for privileged containers or broad host mounts, bypassing otherwise careful workspace/credential boundaries. Treat this as environment isolation unless the socket is removed or replaced with a narrower/rootless service. [Docker socket mount](/home/mark/tools/zeroshot/src/isolation-manager.js:481)
7. **Legacy Node delivery has credential and cleanup hazards.** One Docker PR path can persist a GitHub token in the isolated repository's remote URL; worktree cleanup signals every process whose command line contains the worktree path; repository-configured worktree setup executes through inherited host Bash. These Node paths require a separate security assessment; native-v2 GitHub delivery uses a narrower clean-environment, per-command credential and bounded-process contract. [Credential-bearing remote](/home/mark/tools/zeroshot/src/isolation-manager.js:1242) [Process matching](/home/mark/tools/zeroshot/src/isolation-manager.js:2347) [Setup hook](/home/mark/tools/zeroshot/src/isolation-manager.js:2167) [Native-v2 GitHub execution](/home/mark/tools/zeroshot/zeroshot-rust/src/native_v2_delivery/github.rs:384)
8. **Node user authority is intentionally thin.** Autonomous agents never ask questions. This prevents deadlock but does not provide Feature Forge-grade materiality, scope-expansion, UAT, waiver or ambiguous-side-effect decisions. `--ship` can own PR/merge delivery, which is precisely the authority an outer controller must retain.
9. **Operational and compute cost is high.** Node 22, native dependencies, provider CLIs/authentication, optional Docker/GitHub tooling and potentially a planner plus four validators create installation, token, latency and support cost. The project calls itself pre-1.0 in spirit and recommends version pinning. [Status boundary](/home/mark/tools/zeroshot/README.md:196)
10. **Repository-level tests are broad, but maturity must remain product-specific.** The established Node product has extensive orchestration/provider/isolation fixtures; native v2/OECP has its own Rust protocol/runtime suites and is newer. Neither fixture inventory proves live changing provider CLIs, and OECP admission/testkit surfaces must not be mistaken for native execution.

### Best fit

Zeroshot Node best fits teams wanting a standalone, configurable, unattended coding-agent runtime with persistent operations, independent validation on non-TRIVIAL paths, strong trace export, multiple providers and optional isolation/delivery. Native v2 best fits a typed one-run graph/target composition where terminal-on-runtime-loss is acceptable. Both favor bounded tasks with crisp acceptance criteria. They are poor unmodified children of Feature Forge, and Node is a poor fit for exploratory discovery, frequent human checkpoints, or environments where its Docker-socket/provider-drift surface is unacceptable.

## Fable Method interim report

### Purpose and architecture

Fable Method is a portable behavioral workflow, not a runtime. Its four skills are presented as **think** (`fable-method`), **act** (`fable-loop`), **prove** (`fable-judge`), and **grow** (`fable-domain`). The core method is a short decision procedure: a conservative triviality gate, a fit/evidence gate, ask-shape classification, explicit done criteria, primary-source evidence, one recommendation, surgical action, observed verification, and an outcome-first report. [Core method](/home/mark/tools/fable-method/skills/fable-method/SKILL.md:24) [Family positioning](/home/mark/tools/fable-method/README.md:9)

The architecture is entirely prompt-level. `fable-loop` asks the main agent to fan out evidence gathering, retain decisions and edits in the main thread, and use one to three adversarial verifier agents for consequential work. `fable-judge` treats a completion report as untrusted claims, diffs actual work, reruns stated checks, and returns `VERIFIED`, `VERIFIED WITH CAVEATS`, or `REFUTED`. `fable-domain` generates a researched domain adapter plus workflow, trap fixture and smoke eval. None supplies a scheduler, state database, process owner, worktree manager, or effect executor. [Loop](/home/mark/tools/fable-method/skills/fable-loop/SKILL.md:12) [Judge](/home/mark/tools/fable-method/skills/fable-judge/SKILL.md:8) [Domain maker](/home/mark/tools/fable-method/skills/fable-domain/SKILL.md:19)

### Lifecycle and authority model

Fable's lifecycle is a behavioral router rather than a durable run state machine:

`triviality → fit → classify → define done → gather evidence → decide → act → verify → report`

Plan-first work stops for approval; reversible task-shaped work proceeds. Irreversible or outward-facing action requires a verbatim user authorization line, and project documentation or an installed skill explicitly does not count as authority. Before behavior changes, the `INTENT` gate reconciles current behavior, the check, and the governing spec. Before using an unopened API, figure, endpoint, or configuration fact, the recall gate requires opening its source or labeling it unverified. Defect work owes a whole-project `TWINS:` search; the final artifact sweep restores any owed `INTENT`, `AUTH`, `PENDING`, or `TWINS` line. [Authority and intent](/home/mark/tools/fable-method/AGENTS.md:63) [Verification and artifacts](/home/mark/tools/fable-method/AGENTS.md:87)

These are useful decision-point obligations, but their authority is session-local. There is no persistent run identity, legal-transition schema, frozen specification/plan, dispatch receipt, recovery reconciliation, idempotency key, or Finish journal. “Opened this session” and the execution checklist disappear with context unless the host supplies its own persistence. Fable itself recognizes the composition boundary: a multi-phase outer workflow such as GSD should own stages while Fable rules apply inside them, rather than nesting `fable-loop`. [Family router](/home/mark/tools/fable-method/skills/fable-method/references/flowcharts.md:117) [Outer-workflow boundary](/home/mark/tools/fable-method/skills/fable-loop/SKILL.md:43)

### Distinctive capabilities

1. **Decision-point evidence artifacts.** `INTENT`, `AUTH`, `PENDING`, and `TWINS` turn otherwise easy-to-ignore prose into named outputs at the moment a risky decision is made.
2. **Honest fit routing.** The method distinguishes reachable evidence, researchable uncertainty, unsupported judgment, and reusable domain procedure, explicitly guarding against “costume rigor.” [Fit gate](/home/mark/tools/fable-method/skills/fable-method/SKILL.md:26)
3. **Adversarial claim reconciliation.** The judge believes the diff and rerun output over the agent's completion story, and hunts weakened tests, false completion, scope creep, unauthorized action, spec betrayal and debris. [Judge procedure](/home/mark/tools/fable-method/skills/fable-judge/SKILL.md:14)
4. **Evidence adapters rather than alternate lifecycles.** Eight lazy domain adapters change the minimum evidence set, authority order, verification meaning and fraud table while retaining one loop. The maker refuses medical and other high-harm/credentialed skill generation and stops when ordinary coding already fits. [Domain adapters](/home/mark/tools/fable-method/README.md:131) [Maker red lines](/home/mark/tools/fable-method/skills/fable-domain/SKILL.md:21)
5. **Failure-driven prompt development.** Fifteen recorded rounds preserve wins, nulls, known failures, fixture mistakes and removed features. This is unusually transparent for an instruction package. [Results log](/home/mark/tools/fable-method/eval/RESULTS.md:1)

### Strengths and advantages

- **Best lightweight behavioral discipline in the roster.** The core is small enough to embed in ordinary agent work while covering ask shape, evidence, scope, authorization, verification and report honesty.
- **Best explicit prompt-evaluation culture.** Trap fixtures have ground truth and many mechanically checkable outcomes; the repository publishes regressions, ceiling nulls, failed rule wordings and known weak-tier limitations rather than only headline wins.
- **Strongest post-hoc claim-checking prompt.** `fable-judge` supplies a compact, reusable fraud-hunting model that complements deterministic tools and independent review.
- **Lowest runtime and installation burden.** The core can be supplied as skill text or an `AGENTS.md`; there is no compiled binary, daemon, database, provider registry or runtime dependency.
- **Good cross-domain evidence vocabulary.** Minimum evidence sets and fraud tables make “verify” concrete outside code without changing the general procedure.

### Weaknesses, costs, and risks

1. **Every operational guarantee depends on model/host compliance.** The flowcharts call themselves “executable pseudocode,” but no parser, hook, state machine, effect guard, or mandatory judge invocation enforces them. The base method ends in hostile self-review; `fable-judge` remains optional.
2. **No durable state, resume, identity, containment, or effect recovery.** Fable cannot replace any of Feature Forge's ledger/freeze/Finish contract, Autoprompt's gate log, Zeroshot's runtime ledger, or Procoder's executable refusal checks.
3. **The eval evidence is narrow and smoke-grade.** Typical cells have one to four runs, synthetic fixtures, subjective LLM-judge fields, no confidence estimates or stable model/settings manifest, and repeated rule tuning on the same headline trap. It supports scenario-specific behavioral findings, not a general “mid-tier beats frontier” claim. [Standing limitations](/home/mark/tools/fable-method/eval/RESULTS.md:218)
4. **Reproduction is incomplete.** The committed workflow script defines five scenarios but its `RUNS` array schedules only S1/S2; later rounds do not share one executable, versioned run manifest. CI parses result JSON and checks structure but neither replays evals nor validates reported aggregates. [Workflow runs](/home/mark/tools/fable-method/eval/workflow.js:48) [CI checker](/home/mark/tools/fable-method/.github/checks.py:74)
5. **Some headline language outruns the artifacts.** Judges do read and score reports in addition to diffing/executing, despite README wording that says “never by reading reports”; the “more than 260 agent runs” aggregate is not machine-auditable from one canonical run registry; and round 15 downgraded several apparently safe outcomes because the trap never armed. [Judge prompt](/home/mark/tools/fable-method/eval/workflow.js:82) [Round 15](/home/mark/tools/fable-method/eval/RESULTS.md:222)
6. **Known weak-tier and internal consistency defects remain.** The `PENDING` artifact surfaced in only 1 of 12 weak-tier runs across three wordings. `fable-loop`'s report rule mentions only `INTENT` and `AUTH`, omitting the base method's `PENDING` and `TWINS` obligations. Documentation also calls a four-skill family “Three skills” and elsewhere says the failure catalogue has 14 entries when it has 18. [Weak-tier result](/home/mark/tools/fable-method/eval/RESULTS.md:127) [Loop report rule](/home/mark/tools/fable-method/skills/fable-loop/SKILL.md:38)
7. **Distribution is currently inconsistent.** Both standalone installers omit `fable-domain`; reinstall can nest or leave stale files; `AGENTS.md` claims identity with the canonical skill but omits its current domain-router/reference content; and CI does not test installer or mirror parity. [Shell installer](/home/mark/tools/fable-method/install.sh:9) [PowerShell installer](/home/mark/tools/fable-method/install.ps1:9) [Portable contract](/home/mark/tools/fable-method/AGENTS.md:3)
8. **Safety and adapter boundaries remain judgment calls.** Legal/finance analysis adapters coexist with a generator that refuses legal/financial advice, leaving the acting model to decide where analysis becomes licensed advice. Older hand-written adapters are also grandfathered without the generated-adapter Sources requirement. [Maker red lines](/home/mark/tools/fable-method/skills/fable-domain/SKILL.md:21) [Adapter template provenance boundary](/home/mark/tools/fable-method/skills/fable-method/references/domains/TEMPLATE.md:53)

### Best fit

Fable best fits evidence-reachable, multi-step tasks where the main risks are procedural: misclassifying a question as a task, trusting a wrong test over a spec, inventing an API, overreaching scope, taking an unauthorized outward action, missing sibling defects, or reporting unobserved success. It is especially attractive as a worker/reviewer discipline inside a host that already owns state and effects. It is a poor fit as the sole controller for long-running resumable delivery, as a security boundary independent of the agent, as evidence of domain expertise, or as a peer outer loop inside Feature Forge, Autoprompt, Zeroshot, or another orchestrator.

## Direct comparison

### Comparison matrix

| Dimension | Feature Forge | Autoprompt | Procoder | Zeroshot | Fable Method |
|---|---|---|---|---|---|
| Primary job | Govern one bounded Git work unit from intent through acceptance and branch finishing | Autonomously orchestrate a coding mission across specialized agents | Make repository quality/process checks executable and hard to hand-wave | Node: execute a bounded software task through configurable persistent executor–verifier workflows; native v2: execute one admitted graph | Make an agent classify, evidence, act, verify and report a task with fewer procedural failures |
| Product category | Instruction-only outer workflow contract | Multi-agent protocol plus cross-provider deployment/runtime package | Compiled quality/governance CLI plus hooks and plain-file controllers | Executable Node orchestration runtime plus independently released Rust one-run graph engine/protocol | Portable instruction-level operating procedure, optional prompt orchestration, adversarial judge and domain-adapter maker |
| Core authority | Tracked ledger; exactly one next action | `ROADMAP.md` scope plus append-only prompt/gate logs | Distributed `.procoder/` files and command-specific controllers; no single run authority | Node cluster metadata + per-run SQLite ledger; native v2 has a separate lean one-run ledger/controller lease | Acting model and conversation context; no durable authority artifact or transition owner |
| Lifecycle | Fixed 14-stage sequence | Adaptive roadmap/gate topology by scope, tier and tag | Optional/scalable quality chain from spec through release | Node classification chooses a built-in/custom topic graph; native v2 executes one admitted typed graph to a terminal result | Fixed behavioral router and seven-step loop; optional PLAN/EXECUTE/VERIFY/AUDIT prompt wrapper |
| Planning | Mandatory hardened/frozen spec and reviewed/frozen plan | One executable roadmap; detailed planning only when needed | Structural spec and plan controllers; chain partly advisory | Node STANDARD/CRITICAL planner emits executable plan and acceptance checks; neither product has frozen Feature Forge spec/plan authority | Names done, verification, evidence, scope and one recommendation; plan-first stops, but nothing is frozen or independently sealed |
| Scope control | Strongest: materiality, authority, deferred new requests, frozen IDs, invalidation graph | Strong lane ownership and topology classification; mission invocation grants broad execution authority | Work-class guidance, backlog/sprint WIP and repo-local policy; weaker global scope authority | Both expect crisp input; Node adds autonomous choices/free-form topology, while native v2 executes a pre-admitted graph; neither has comparable human scope authority | Strong prompt rules for ask shape, declared scope, smallest change and surprise routing; no durable scope identity/invalidation |
| Delegation | One selected parallel-or-inline adapter; strong packets, weak runtime machinery | Strong prompt-protocol hierarchy, launch groups, disjoint lanes, integration items and caps | Not a scheduler; provides delegation principles and deterministic tools | Node: topic agents, retries/cycles and nested graphs; native v2: bounded admitted seq/choice/par/loop/map with exclusive writers | Evidence fan-out and 1–3 adversarial agents under main-thread ownership; no scheduler, ownership admission or retry runtime |
| Context handling | Reopen full named run evidence on resume | Strongest compression: hash/length/nonce pointer briefs and blind-review isolation | Session status/handoff and code index; no run-context protocol | Node only: ledger-derived priority packs, compact variants, durable state snapshot, token/character bounds and session continuation | Read narrow, quote load-bearing lines and avoid rereads; session-local only |
| Persistence/resume | Strongest formal reconstruction and drift reconciliation | Efficient explicit GATELOG-tail frontier plus re-anchor | Durable project artifacts but no end-to-end orchestration recovery | Node provides crash-safe operational resume and preserved workspaces; native v2 deliberately terminalizes runtime/session/workspace loss and has no resume/replay | None; no run ledger, checkpoint, replay, recovery or reconciliation contract |
| Change invalidation | Explicit fixed downstream invalidation graph | Repair named rejected items and re-anchor, but no comparable Git-identity graph | Fingerprints/drift findings in selected controllers; no global invalidation model | Node message/outcome retries and fresh delivery gates; native v2 durable reducer outcomes; neither has a frozen-authority invalidation graph | Surprises route back to classification/evidence, but no durable dependency graph or stale-evidence invalidation |
| Review | Three stage-specific reviews with sealed subjects and fixed result mapping; live adapter mismatch | Multi-role independent roadmap/build/runtime/goal assurance | Fresh PR review instructions plus deterministic gates/lessons | Node independent validators on SIMPLE+ defaults, none on TRIVIAL; native v2 executes admitted verifier nodes read-only | Optional hostile self-review, verifier fan-out and post-hoc judge; no mandatory sealed subject or enforced independence |
| Verification | Worker-local evidence, sealed post-review verification, requirement/scenario acceptance | Strict TDD, real-system verification, fixed coverage floor, goal check | Broad deterministic tool runners; default gate omits tests/deep domains | Node command-evidence/adversarial/delivery checks, with inconsistent `CANNOT_VALIDATE` wording; native v2 enforces typed verifier outcomes | Named check plus surrounding-system health, defect-twin search, diff/rerun-based claim audit; prompt-enforced |
| Human authority | Strongest explicit modes, materiality and UAT/waiver semantics | Minimal interruption; arbiter resolves technical forks, user owns destructive/cost/product decisions | `ask` records human decisions; consent around tag/upgrade/publication | Node agents never ask; CLI effect boundaries exist, but neither product has comparable materiality/UAT/waiver semantics | Plan-first and exact user quote for outward/irreversible action; no durable materiality, UAT or waiver record |
| Finish/external effects | Strongest recoverable `finish_id` write-ahead journal | Explicitly lacks implicit commit/push/deploy authority; no equivalent finish transaction | P-CONTROL prints actions such as tag; no equivalent exactly-once finish journal | Node `--pr`/`--ship` and native-v2 graph-visible delivery can create/merge PRs, but neither is an outer exactly-once authority journal | Prohibits unrequested commit/push/deploy and records pending action; no effect transaction or recovery |
| Enforcement | Lowest mechanically; prose and Markdown templates | Mixed: orchestration largely prompt-enforced, deployment/config heavily executable | Strongest deterministic repository-check enforcement; workflow chain and some hosts remain advisory | Strongest runtime enforcement: graph/config admission, SQLite transitions, leases, process ownership and typed Rust contracts; policy still partly prompt-driven | Prompt-only during work; CI checks repository consistency, not agent compliance or eval outcomes |
| Extensibility | Narrow four-adapter boundary; no capability negotiation | 25 roles/18 frameworks, framework generation, six provider renderers | Broad commands/config/rubrics/templates; external tools supply depth | Node: custom graphs/predicates/subclusters, nine engines and five issue sources; native v2/OECP: typed graph/host/target protocol | Four skills, eight lazy evidence adapters and a template-backed adapter generator |
| Portability | Skill-level Claude/Codex use; depends on external skills/reviewer | Six audited provider packages; differing host capabilities | Broadest declared agent-host reach; hard enforcement and live testing are uneven | Node supports Linux/macOS and nine provider engines; Windows deferred; Rust distributes five native targets independently | Broadest instruction portability claim via `AGENTS.md`; only Claude has packaged activation, and that mirror currently drifts |
| Installation | Small skill payload; dependencies not resolved/versioned | npm CLI, Python/Bash, receipts/manifests/doctor/update/uninstall | Static binaries/plugins; no runtime dependencies at hook time, external check tools optional/required by domain | Node 22/npm plus native/provider dependencies; optional Docker/hosted tooling; separate checksummed native Rust archives/image | Claude marketplace or direct skill copies; current standalone installers omit `fable-domain` and have weak update/collision semantics |
| License / release provenance | No LICENSE found in the inspected component or skillbook root; clarify before copying/redistribution; no standalone release gate | MIT; npm/GitHub releases, provenance publication, checksummed kits and prepublish verification | Apache-2.0; committed cross-platform binaries, SHA-256 sums, byte-reproducibility checks and guarded self-upgrade | MIT; separate Node trusted-publishing and Rust exact-commit/checksummed archive, image and optional downloader-shim trains | MIT; versioned plugin metadata, but no release workflow, checksums, signatures or immutable standalone bootstrap |
| Auditability | Best delivery-authority trace: transitions, seals, identities, acceptance, Finish receipts | Strong provenance: prompt/roadmap hashes, role/model/effort/verdict/frontier | Strong findings and durable project artifacts, no unified run timeline | Node has the best raw task forensics via causal ledger/create-only trace; native v2 has a lean safe-log/event ledger, not the Node trace format | Strong after-the-fact claim audit and committed eval stories/results; no unified per-run authority or complete run registry |
| Maturity evidence | Documentation/link tests only; no behavioral runtime suite | Generated-contract, CLI/provider/lifecycle/release tests; bounded benchmark evidence | Large Go refusal-path suite and reproducible builds; current suite not runnable here and CI misses command tests | Node has extensive orchestration/provider/isolation tests; newer native v2/OECP has separate Rust suites; both lack current local green/live-provider proof | Rich trap corpus and candid A/B/null log; tiny cells, LLM judges, partial runner and structural-only CI make it smoke evidence, not a benchmark |
| Main cost | Ceremony, manual synchronization, dependency mismatch | Tokens, latency, provider/runtime complexity, rigid assurance | Tool installation, policy friction, broad-but-uneven coverage, state races | Largest code/operations surface, provider/auth/native dependencies, compute/latency, isolation risk and two product semantics | Low install/runtime burden; full loop adds model fan-out and verification time; instruction duplication creates drift |
| Standout feature | Artifact identity + invalidation + truthful acceptance + recoverable Finish | Adaptive multi-agent protocol + compact bound briefs + generated provider packages | `unchecked is not clean` + deterministic common gate + learning loop | Node persistent executor–verifier operations/raw trace; native v2 typed one-run graph runtime | Decision-point evidence artifacts + adversarial claim judge + unusually candid trap-eval discipline |

### Decision profiles

| Use case | Recommended primary | Borrow | Do not embed as a peer authority |
|---|---|---|---|
| High-risk, bounded delivery with human acceptance or consequential Git finishing | Feature Forge, after its adapter gaps are resolved | Procoder-style deterministic evidence; Autoprompt-style bound dispatch and overlap classification | Autoprompt governance files or Procoder project/release state |
| Large, multi-surface mission where throughput and independent agent assurance dominate | Autoprompt, if its fixed TDD/coverage policies and provider constraints fit | Feature Forge's requirement acceptance and Finish concepts; Procoder checks as explicit frameworks | A second Feature Forge outer controller unless a real adapter assigns lifecycle ownership |
| Standalone unattended executor–verifier operations with persistent monitoring, custom workflows, isolation and optional PR delivery | Zeroshot Node, with version pinning and an isolation threat model | Feature Forge authority/acceptance for consequential work; Procoder deterministic checks | A peer Feature Forge controller, or Rust-v2 recovery assumptions applied to Node |
| Typed one-run graph execution or self-hosted target composition with closed protocol/fault contracts | Zeroshot Rust, only if terminal-on-runtime-loss is acceptable | Feature Forge/Procoder evidence mapping outside the engine | Node-resume claims, an outer Finish role, or a general recovery engine |
| Ongoing repository quality, developer guardrails and cross-agent policy | Procoder | Feature Forge for selected high-risk work units; Autoprompt for selected large missions | Treating `procoder check` as a complete delivery or test verdict |
| Lightweight cross-domain agent discipline or adversarial audit without installing a runtime | Fable Method / `fable-judge` | Host-native deterministic checks and durable artifacts where available | Treating prompt compliance or a self-audit as mechanical enforcement |
| Minimal/trivial change | A focused native skill or direct work | Individual checks only; optionally Fable's conservative pre-invocation triviality rule | Any full five-project stack |

### Important similarities

All five reject “the agent says it is done” as sufficient evidence. They externalize some truth into artifacts or observations, prefer explicit boundaries and value test/review evidence, although they enforce that distinction at different layers. Feature Forge, Autoprompt, Procoder and Fable deliberately withhold implicit external-effect authority; Zeroshot Node instead exposes explicit user-selected PR/ship delivery, so it shares the consent instinct but owns a broader effect boundary.

Feature Forge, Autoprompt and Zeroshot are agent orchestrators with durable run metadata, delegated execution and bounded worker authority. Fable can orchestrate prompt-level fan-out but has none of that durable machinery. Feature Forge and Autoprompt require independent review; Zeroshot Node provides independent validation on non-TRIVIAL default paths, while custom graphs can vary that assurance; Fable's judge is opt-in and report-oriented. Feature Forge and Procoder both favor repo-visible plain files, specification/plan readiness, fail-closed missing evidence and deliberate user authority. Fable shares their evidence/authority instincts but encodes them as portable instructions. Autoprompt, Procoder and Zeroshot are full distribution products with provider/host artifacts, release tests, installation/update concerns and inevitable vendor drift; Fable's distribution surface is much smaller but already shows mirror/installer drift.

Each also embodies the same general safety instinct: surface uncertainty rather than silently treating it as success. Feature Forge calls it blocked/infeasible and classifies authority upward; Autoprompt rejects invalid briefs/capabilities and invokes arbitration; Procoder emits unchecked/not-run and nonzero outcomes; Zeroshot Node rejects malformed output, ambiguous resume and unsafe containment, while native v2 rejects invalid admission and uses closed faults; Fable's fit gate labels low-confidence inference and its judge labels unreproduced claims as caveats or refutations. The Node `CANNOT_VALIDATE` template wording and Fable's known weak-tier `PENDING` dropout are notable exceptions that need normalization or mechanical guarding before integration.

### Important differences

The largest difference is **what owns truth**:

- Feature Forge owns one delivery run and every transition.
- Autoprompt owns decomposition, dispatch and convergence of a mission.
- Procoder owns the result of individual controllers/checks, not the overall mission.
- Zeroshot Node owns the operational cluster, workflow graph, workspace lifecycle, validators and optional delivery; Rust owns exactly one admitted graph run and one terminal result.
- Fable owns only a model's decision procedure and claim-audit rubric; it has no durable run truth.

The second is **contract versus enforcement**. Feature Forge has the deepest formal delivery-authority model but little executable machinery. Fable is also instruction-only, with a shallower lifecycle but a substantially richer behavioral eval corpus. Procoder has the strongest deterministic repository-quality enforcement but no comparable global lifecycle. Zeroshot Node has the strongest persistent scheduling/process machinery, though role decisions and validation judgments still come from prompts; native v2 has a narrower, strongly typed one-run engine. Autoprompt occupies the middle: its provider/install runtime is heavily engineered, while actual orchestration invariants remain substantially prompt- and host-dependent.

The third is **fixed rigor versus adaptive throughput**. Feature Forge deliberately serializes specification, freeze, plan, review, implementation, verification and acceptance to protect authority. Autoprompt seeks the maximum honest parallelism and skips detailed planning when the roadmap is executable. Zeroshot Node routes through heuristic classification into executable graphs and can express cycles/nesting/concurrency; native v2 executes a caller-selected admitted graph. Procoder scales ceremony by work class and lets teams opt policies into blocking. Fable keeps one small fixed loop, bypasses it for truly trivial work, and adds fan-out only for independent evidence or adversarial checking.

The fourth is **where state lives**. Feature Forge deliberately commits run artifacts into the target repository for durable audit. Autoprompt keeps its three governance files outside the mission tree to avoid polluting the diff. Procoder stores durable project governance under `.procoder/`, while the binary also manages derived indices/baselines and selected transitions. Zeroshot Node stores cluster databases, task logs, provider sessions and workspaces under user/runtime roots and can export an exact trace; native v2 stores a separate lean event/safe-log ledger. Fable persists no run state at all; its committed artifacts are method/eval fixtures, not records of the current task.

The fifth is **quality philosophy**. Feature Forge is risk- and requirement-proportionate. Autoprompt encodes universal strict TDD and a numeric coverage floor. Procoder exposes a broad domain catalog, but defaults intentionally distinguish blocking from advisory and do not make the test suite part of the ordinary gate unless configured. Zeroshot Node emphasizes independent use-it-yourself validation and repeated rejection loops, but assurance depends on conductor/template configuration and is absent on its default TRIVIAL path; native v2 enforces the verifier nodes present in its admitted graph. Fable focuses on procedural failure and observed claims, explicitly admitting small-task ceiling nulls and knowledge limits.

The sixth is **recovery philosophy**. Feature Forge reconstructs all authority and blocks on ambiguous external effects. Autoprompt re-anchors a compact frontier. Zeroshot Node resumes many durable workflow states and preserves isolation resources; native v2 deliberately terminalizes lost runtime/workspace/session authority rather than rebuilding it. Procoder persists project state but is not a run-recovery engine. Fable has no recovery model and must inherit one from its host.

### Complementarity and overlap

The projects can complement one another only with explicit ownership boundaries:

- A Feature Forge run could use Procoder commands as deterministic evidence in Plan, Implement or Final verification. Procoder must not become a second workflow authority, and an absent command must be recorded as unavailable rather than silently substituted.
- Feature Forge could use Autoprompt-like execution behind `execute-return` if the adapter maps frozen task IDs, ownership, launch groups and return evidence into the Feature Forge ledger, prevents Autoprompt's governance from advancing the outer run, and stops before any finishing action.
- Feature Forge could use one locked Zeroshot **Node** workflow behind `execute-return` if Feature Forge supplies the existing worktree, fixes the template/provider/cost bounds, maps raw trace and validator outputs to REQ/SCN evidence, owns every resume decision, and disables Zeroshot worktree/PR/ship/merge authority. A supplied-worktree compatibility contract must be proven, not assumed.
- Autoprompt could use Procoder as a repository-specific verification framework, but should not equate a default `procoder check` with tests or full-domain validation.
- Zeroshot workers could invoke Procoder checks or an Autoprompt-like role protocol, but the Node ledger/graph must remain the only inner runtime authority and provider sessions must not launch another uncontrolled outer scheduler.
- Feature Forge could apply Fable's method rules inside Brainstorm/Plan/Implement/Review packets and use a bounded `fable-judge`-style review input. It must not run `fable-loop` as another plan/dispatch authority or treat `INTENT`/`AUTH`/`TWINS` report lines as substitutes for ledger identities and receipts.
- Autoprompt or Zeroshot workers could use Fable's intent, recall, twin and claim-audit rubric, but their own roadmap/graph, provider sessions and retry/terminal semantics must remain the only inner orchestration authority.
- Procoder results are strong deterministic observations for a Fable-style report, while Fable can supply the cross-checking question “does this command actually prove the claim?” Neither turns the other's partial evidence into a complete delivery verdict.

Without those boundaries, integration creates multiple controllers, scope truths, worktree owners and resume semantics, plus ambiguous ownership of validation, acceptance, PR/merge and Finish. A coherent five-part stack therefore uses **one outer authority, at most one inner execution engine, deterministic tools as evidence, and Fable only as behavioral/evaluation discipline**.

## Recommendations for enhancing Feature Forge

### Prioritized shortlist

The recommendations below intentionally add **validation inside existing Feature Forge stages**. They do not add a second state machine or relax the ledger's sole authority.

| Priority | Recommendation | Borrowed from | Decision |
|---|---|---|---|
| P0 | Implement and capability-version the live adapters, starting with review-loop; add integration fixtures | Autoprompt provider contracts; Procoder controllers; OECP worker/capability descriptor pattern | Adopt the machinery pattern |
| P0 | Add a small ledger/artifact/packet/return validator | Autoprompt payload validation; Procoder refusal gates; OECP verifier + native-v2 admission pattern | Adopt |
| P0 | Record a complete verification inventory where unavailable/not-run is non-passing | Procoder's explicit unchecked state | Adapt |
| P0 | Mechanically lint specification/plan readiness before review dispatch | Procoder spec/plan controllers | Adapt |
| P0 | Bind each dispatch/return to one canonical idempotency identity and recover it before redispatch | Autoprompt compact hash/nonce briefs; OECP lifecycle idempotency design | Adapt |
| P0 | Add failure-first behavioral fixtures and preserve raw/null/failed outcomes | Fable trap-eval covenant | Adopt, with stronger reproducibility |
| P1 | Require an intent-source tuple, defect red baseline, deepest-root-cause evidence and a scoped twin search | Fable intent/recall/twin gates; Autoprompt depth-lock; Procoder TDD evidence | Adapt conditionally |
| P1 | Standardize typed evidence receipts and a closed adapter outcome/error algebra | OECP worker shape + native-v2 closed faults; not native-v2 artifacts | Adapt narrowly |
| P1 | Revalidate the pinned Feature Forge worktree root immediately before adapter effects | Zeroshot Node copy-containment boundary | Adopt |
| P1 | Classify disjoint ownership, shared-state execution and explicit integration tasks | Autoprompt launch groups/integration lanes | Adapt |
| P1 | Probe required evidence capabilities after the plan is known, before implementation | Autoprompt capability check; Procoder doctor | Adapt narrowly |
| P1 | Bind outward-action receipts to the exact user-authority excerpt and requested effect | Fable authorization gate | Adapt as evidence, not a new authority model |
| P2 | Give authorized exceptions a ceiling and revisit trigger | Procoder debt/lessons | Adapt only when an exception exists |
| P2 | Add an outer admission hint for truly trivial or evidence-inaccessible work | Fable triviality/fit gates | Adapt before invocation only |
| P2 | Permit optional domain evidence profiles with minimum sources and fraud checks | Fable domain adapters | Adapt narrowly |

The first item is a prerequisite more than an enhancement. Feature Forge currently promises review semantics that the live reviewer does not expose. Adding more orchestration policy before resolving that mismatch would make the contract less executable.

### Ideas to adopt or adapt

#### 1. Executable, versioned adapter capabilities — P0

Define a machine-readable adapter return schema and capability handshake for review, execution and Finish. For review-loop specifically, resolve whether the reviewer or Feature Forge owns fixes; map exact subject, frozen ground truth, deployment context, completion criterion and run root; support or explicitly reject multi-round re-review; and bridge nested recovery IDs into the Feature Forge ledger. The need is visible in review-loop's [directory-only target precondition](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/controller.py:360), [deferred round-N reconciliation](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/controller.py:787), and [narrow production request schema](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/profiles.py:204). Add end-to-end fixtures for spec review, plan review, actionable implementation findings, interrupted recovery and Finish.

This borrows Autoprompt's canonical capability contract rendered/tested against adapters, Procoder's refusal-controller principle, and the **OECP protocol design's** versioned worker descriptors/pre-admission checks. That OECP design is an interface pattern, not evidence that native v2 supplies arbitrary production worker capabilities; advertised profiles may be empty and testkit vectors are not production conformance. The Feature Forge descriptor should state exact subject form, read-only versus mutation boundary, return/error schema, recovery/observation support and ability to halt before Finish. If any required capability is absent or incompatible, Preflight or the relevant stage blocks with a concrete reason. [OECP lifecycle boundary](/home/mark/tools/zeroshot/docs/openengine-cluster-protocol/v1/lifecycle.md:9) [Worker-profile boundary](/home/mark/tools/zeroshot/docs/openengine-cluster-protocol/v1/worker-profiles.md:3)

#### 2. Small runtime validator, not a new engine — P0

Validate:

- ledger schema and exactly one next action;
- legal stage/review/Finish transitions;
- frozen artifact identities and content seals;
- worker packet completeness and non-overlapping ownership classification;
- adapter dispatch/return receipts;
- acceptance-row completeness;
- every owed evidence reference, authorization receipt, verification result and caveat;
- Finish journal preconditions.

The validator reports and refuses; the ledger remains authority and the agent remains controller. This imports Procoder's `compute, report, refuse` shape, Autoprompt's strict manifest/hash validation, and the OECP production verifier/native-v2 admission pattern of rejecting structurally or semantically invalid input before effects. The production verifier proves and compiles a graph but does not itself schedule or execute it; Feature Forge is borrowing pre-admission validation, not the graph runtime. Unknown fields and malformed adapter returns should fail closed. [OECP production verifier](/home/mark/tools/zeroshot/crates/openengine-cluster-server/src/graph_verifier.rs:21) [Native-v2 admission boundary](/home/mark/tools/zeroshot/zeroshot-rust/src/native_v2_admission.rs:1)

#### 3. Verification inventory with explicit unknown states — P0

At Plan review, enumerate every applicable requirement-specific and repository-standard deterministic check. At Final verification, record `passed | failed | unavailable/not-run | not-applicable`, the exact command, reviewed snapshot and evidence reference. A required item that is not `passed` blocks; `not-applicable` needs rationale.

This is the highest-value Procoder idea for Feature Forge. It closes the gap between “run risk-proportionate checks” and proving that no applicable check was silently omitted. Procoder itself may be one optional evidence provider; `procoder check` must not be treated as tests or full-domain proof.

#### 4. Structural specification/plan readiness lint — P0

Before existing review dispatches, mechanically check unique REQ/SCN IDs, empty open questions, complete acceptance classification, concrete task ownership, interface/dependency declarations, exact verification, no placeholders, and task-to-requirement coverage. Record one validator receipt in the existing ledger. This should reduce predictable review churn without granting the validator transition authority.

#### 5. Canonical input-bound dispatch identity — P0

Extend each existing pre-dispatch ledger write with one canonical `dispatch_id` derived from adapter and capability version, stage, frozen spec/plan identities, candidate seal or implementation commit, task/REQ/SCN IDs, owned paths, criterion and canonical worktree identity. The child must echo that ID in a closed return envelope. On resume, Feature Forge observes or recovers that exact dispatch before considering redispatch; changed inputs require a new ID.

This combines Autoprompt's compact hash/length/nonce pointer briefs with the **OECP lifecycle design's** canonical idempotency/receipt model. It does **not** claim physical exactly-once delivery or prove an external effect did not occur; uncertain outcomes still enter Feature Forge's existing blocked reconciliation path. Do not create Autoprompt's `PROMPTS.txt`, `ROADMAP.md` or `GATELOG.md`, and do not adopt Zeroshot's ledger as authority. [OECP admission idempotency](/home/mark/tools/zeroshot/docs/openengine-cluster-protocol/v1/admission.md:43)

#### 6. Failure-first behavioral and recovery fixtures — P0

Adopt Fable's most valuable maintainer discipline: a new behavioral rule needs a fixture that fails without it, the changed rule is tested against that fixture, raw outputs are retained, and nulls or regressions are published. For Feature Forge, prioritize sole-controller recovery, frozen-identity drift, forged/malformed adapter returns, review-result recovery, unavailable acceptance evidence, authority-before-effect, Finish ambiguity, and claim-versus-observation traps.

Improve on Fable's current harness rather than copying it literally: use a machine-readable run registry with exact executor/judge versions, settings, prompts, fixture/skill hashes and seeds; separate deterministic assertions from subjective scoring; use held-out variants after rule tuning; blind multiple judges or include human adjudication for headline claims; and make CI validate aggregates and runnable manifests. Small synthetic cells remain smoke tests and must not be called a benchmark. [Fable methodology](/home/mark/tools/fable-method/eval/README.md:3) [Fable limitations](/home/mark/tools/fable-method/eval/RESULTS.md:218)

#### 7. Intent-source and defect depth/twin lock — P1, conditional

For defect-classified work only, require the specification/plan and implementation evidence to include:

- an `intent_source` tuple: observed behavior, failing/required check, governing source opened for this run, and any contradiction;
- observed failure and reproducible pre-change scenario;
- competing root-cause hypotheses;
- the deepest evidenced decision point;
- red baseline and post-fix regression result;
- a scoped twin-search receipt: wrong construct, search command/pattern, candidates and disposition.

If evidence contradicts frozen authority, the worker returns the surprise to Feature Forge; it may not silently rewrite the specification, plan or acceptance criterion. If reproduction is infeasible, record that limitation through existing authority/acceptance rules; never manufacture a red result. Twin discovery does not authorize fixing every match: candidates outside frozen scope go through Feature Forge's materiality/invalidation rules. This combines Fable's strongest decision-point artifacts with Autoprompt's task-specific assurance rather than importing either full gate ladder. [Fable intent gate](/home/mark/tools/fable-method/skills/fable-method/SKILL.md:82) [Fable twin gate](/home/mark/tools/fable-method/skills/fable-method/SKILL.md:95)

#### 8. Typed evidence and closed adapter outcomes — P1

Give every worker, reviewer and deterministic-check return a small typed evidence envelope: kind, digest, byte length, producer/adapter/capability version, frozen-input lineage, commit/seal, redaction class and storage reference. Standardize adapter outcomes to a closed set such as `completed`, `changes_required`, `blocked`, `refusal`, `malformed`, `timeout` and `crash`; Feature Forge alone maps those into stage transitions.

This adapts the OECP worker-profile/error **shape** and native-v2's closed redacted fault projection without claiming that native v2 has an artifact store—it explicitly does not. Feature Forge should implement only a metadata envelope around its existing evidence references. Raw paths, credentials and unbounded output stay outside the receipt. Invalid, partial or unknown fields become `malformed`, never a guessed success. [OECP worker profile contract](/home/mark/tools/zeroshot/docs/openengine-cluster-protocol/v1/worker-profiles.md:3) [Native-v2 closed faults](/home/mark/tools/zeroshot/zeroshot-rust/src/fault.rs:20) [Feature Forge review mapping](/home/mark/kramtime/llm-skillbook/feature-forge/references/adapters-and-reviews.md:179)

#### 9. Pinned-root pre-effect revalidation — P1

Bind execution and Finish adapter receipts to the Feature Forge worktree's canonical physical root, branch and expected commit, then revalidate them immediately before every filesystem or Git effect. Zeroshot's shared copy-containment code demonstrates the right check/use discipline: pin the root and filesystem identity, reject traversal/symlinks, and recheck at the effect boundary. [Zeroshot containment](/home/mark/tools/zeroshot/src/copy-containment.ts:73)

This strengthens Feature Forge's existing isolated-worktree rule; it must not introduce Zeroshot's worktree manager or allow an inner engine to allocate a competing checkout.

#### 10. Overlap and integration classification — P1

Before choosing execution mode, classify each writable boundary as:

- disjoint and parallel-safe;
- intentionally shared and therefore inline/serialized; or
- followed by an explicit integration task.

Overlapping writable paths without such a classification block the subagent branch. This is a modest, compatible slice of Autoprompt's DAG machinery and Zeroshot native v2's writer-overlap admission, not an invitation to import either scheduler.

#### 11. Early evidence-capability receipt — P1

After the reviewed plan declares exact verification/acceptance methods, prove required runners, credentials/access and environments are available before implementation. Optional checks remain advisory; missing required capability blocks early. This is more precise than Autoprompt's generic scratch probe and more useful than discovering at Stage 11 that a declared acceptance method cannot run. A Zeroshot adapter must additionally pin provider, template, isolation, validator count, iteration/token/time bounds and supported resume behavior.

#### 12. Exact authority evidence for outward effects — P1

When Stage 14 records a requested external effect, store a verbatim excerpt of the user's authorization plus a structured binding to the exact action, target and `finish_id`. Documentation, installed skills, inferred completion and earlier generic permission are not substitutes. Fable's `AUTH:` rule is a useful audit cue, but the quote is only evidence inside Feature Forge's existing authority/materiality and exactly-once Finish protocol; it does not independently grant authority. [Fable authorization gate](/home/mark/tools/fable-method/skills/fable-method/SKILL.md:76)

#### 13. Bounded exception closure — P2

When an authorized defect/exception is permitted, require affected REQ/SCN IDs, granting authority, safety ceiling and a concrete revisit trigger. Do not add a cross-run lessons/debt ledger to Feature Forge; use the existing final report and do not permit an exception to masquerade as accepted required behavior.

#### 14. Pre-invocation fit and triviality admission hint — P2

Before a Feature Forge run exists, a small router may recommend direct work only when the task is one known file, under roughly ten changed lines, introduces no behavior, and needs no searching; uncertainty routes into Feature Forge. It may also record whether decisive evidence is reachable, needs bounded research, or is unavailable and therefore requires an explicit low-confidence assessment/authority decision. Once a Feature Forge ledger exists, this router cannot downgrade or exit the run. Fable's thresholds are conservative heuristics, not a replacement mini-workflow. [Fable entry gates](/home/mark/tools/fable-method/skills/fable-method/SKILL.md:24)

#### 15. Optional domain evidence profiles — P2

For genuinely non-code work, allow a bounded adapter to supply only four things: minimum evidence sources, authority hierarchy, observable verification criteria and fraud checks. These enrich Brainstorm/Plan/Review packets but cannot change stages, frozen authority, acceptance/UAT or Finish. Ordinary coding/debugging remains the default; require a “coding in disguise” scope stop, provenance for profile claims, and qualified-human review wherever licensure or high harm is plausible. [Fable domain template](/home/mark/tools/fable-method/skills/fable-method/references/domains/TEMPLATE.md:3)

### Ideas not to import

- **Autoprompt's three-file governance.** It would compete directly with Feature Forge's frozen spec/plan and ledger-as-sole-authority.
- **Autoprompt's useful-first/no dedicated preflight-agent topology and tail-only initial resume read.** Autoprompt still requires a version-bound capability attestation or RUN/READ/WRITE scratch probe, which is worth adapting. What Feature Forge should reject is replacing its own worktree/run/reviewer identity gate or full artifact/seal reconstruction with the lighter topology. [Autoprompt capability fast path](/home/mark/tools/autoprompt-skill/agents/codex/SKILL.md:27)
- **Autoprompt's full coordinator/manager/persona hierarchy or direct G1–G8 ladder.** That would create a second outer controller. Import only bounded execution mechanics behind `execute-return`.
- **A universal ≥95% coverage floor or universal no-mocks rule.** Feature Forge's requirement/risk-proportionate evidence is more robust across domains and less gameable.
- **Procoder backlog, sprint, release or merge as Feature Forge workflow state.** They address project portfolio/governance, while Feature Forge owns one work unit and has a stronger Finish journal.
- **Procoder's default gate as proof of completion.** It omits tests and several deeper domains unless separately run/configured.
- **A mandatory cross-run lessons artifact.** Valuable organizationally, but outside one bounded run and contrary to Feature Forge's minimal-authorized-machinery rule.
- **Zeroshot's Node ledger, conductor, arbitrary graph/message bus, JavaScript predicates or nested clusters as outer workflow state.** They would create a second independently advancing controller beside Feature Forge's one-next-action ledger. Only one locked, bounded execution template may sit behind an adapter.
- **Zeroshot-owned worktree, `--pr`, `--ship`, merge or cleanup.** Feature Forge Preflight owns the checkout and `finish_id` owns the authorized external effect. An inner engine must use the supplied workspace, return before delivery and never interpret validator approval as Finish authority.
- **Native v2 terminal-on-loss semantics.** Runtime/session/workspace/controller loss is terminal by design in Zeroshot Rust; Feature Forge must preserve blocked read-only reconciliation and must not convert an ambiguous review or Finish effect into terminal success/failure. [Native-v2 non-goals](/home/mark/tools/zeroshot/AGENTS.md:291)
- **Zeroshot's `CANNOT_VALIDATE` pass-with-warning wording or universal “never ask questions” rule.** Required unavailable evidence remains non-passing, and Feature Forge's materiality/UAT authority must still reach the user when required.
- **Zeroshot's provider, issue-source, Docker/session, hosted-target or dual Node/Rust platform surface.** Feature Forge needs a small versioned adapter—not another portability/runtime product. In particular, the current host Docker-socket mount is not an appropriate sandbox boundary for untrusted work.
- **Fable's `fable-loop`, checklist or report artifacts as another lifecycle/state machine.** Feature Forge's ledger remains the sole next-action authority. Apply selected rules inside stages; do not create a second plan, agent fan-out controller, self-audit gate or Finish path.
- **Self-review or an `INTENT`/`AUTH`/`TWINS` line as proof.** Named artifacts make omissions inspectable, but Feature Forge still needs independent sealed review, deterministic observations, identity binding and recovery receipts.
- **Fable's rules as universal policy.** The triviality and fit gates are entry heuristics; domain profiles must not create a costume of competence; an exact quote does not replace Feature Forge materiality/UAT authority; and a twin search does not authorize out-of-scope fixes.
- **Fable's aggregate eval claims as a general benchmark.** Tiny cells, tuned fixtures, partial run manifests, LLM judges and incomplete aggregate metadata support narrow smoke findings only. Feature Forge should borrow the failure-first covenant while building a more reproducible harness.
- **Broad provider claims without live semantic tests.** Autoprompt, Procoder, Zeroshot and Fable all show how generated/static or textual parity can still diverge from actual host behavior.

### Suggested sequencing

1. **Compatibility first:** specify the actual review-loop adapter and a generic versioned capability descriptor; add one happy-path, one actionable-finding and one incompatible-capability fixture.
2. **Validate existing invariants:** implement ledger/artifact/packet/return/transition validation and wire it into current stages without adding new stages.
3. **Bind recovery:** introduce canonical input-bound dispatch identities, closed return outcomes and recovered-return-before-redispatch tests.
4. **Strengthen evidence:** add spec/plan readiness lint, typed evidence receipts, the Stage 11 verification inventory with explicit unknown states, and a deterministic owed-artifact sweep.
5. **Build the fixture covenant:** cover malformed returns, drift, recovery, unavailable evidence, authority-before-effect and Finish ambiguity with versioned raw run manifests; publish nulls and failures.
6. **Improve execution safely:** add pinned-root pre-effect revalidation, overlap classification and early capability/cost receipts.
7. **Add targeted rigor:** intent-source/depth/twin evidence, exact authority excerpts and bounded exception closure only where the work-unit type requires them.
8. **Only then prototype an engine adapter:** use one delivery-disabled, supplied-worktree Zeroshot Node workflow or one Autoprompt execution profile and prove that it cannot advance acceptance/Finish or create a second checkout.
9. **Defer convenience layers:** pre-invocation triviality/fit routing and domain evidence profiles come after the controller/adapter invariants are executable; a richer scheduler comes only after mixed parallel/inline execution preserves single-controller authority.

## Bottom line

Qualitatively, for the use cases stated in the decision profiles, Feature Forge has the strongest **delivery-authority and recovery model**, Autoprompt the strongest **portable multi-agent protocol and compact dispatch model**, and Procoder the strongest **deterministic repository-quality machinery**. Zeroshot Node has the strongest **persistent executable executor–verifier operations and raw-task trace**, while native v2 has the strongest **typed, bounded one-run graph/runtime contract**—with terminal-on-loss semantics rather than Node-style recovery. Fable Method has the strongest **lightweight decision-point discipline and candid prompt-level trap-evaluation culture**. These strengths exist at different layers; scoring them as five substitute implementations would be a category error.

Feature Forge should not become a copy of any of them. Its best evolution is to preserve its unusually good authority/invalidation/acceptance/Finish semantics while borrowing executable discipline: validate contracts, negotiate adapter capabilities, bind dispatch inputs, type returns/evidence, revalidate containment at effects, model overlap, and treat unavailable evidence as non-passing. Fable adds a complementary lesson: put evidence obligations at the decision point, make completion claims re-runnable, and require failed/null fixtures before adding policy. Zeroshot makes the ownership boundary concrete because its Node product demonstrates how much machinery a scheduler, ledger, session manager, isolation layer and delivery product require—and how quickly that machinery becomes a competing authority—while native v2 demonstrates the value and explicit recovery trade-off of a narrower typed engine.

The immediate risk is not missing another feature. It is that Feature Forge's current prose claims stronger adapter behavior than the live review/execution dependencies expose. Fixing that seam will produce more real reliability than adding more stages, roles or reports.

## Source map

Primary sources used for current behavior:

- Feature Forge: [SKILL.md](/home/mark/kramtime/llm-skillbook/feature-forge/SKILL.md:1), [workflow contract](/home/mark/kramtime/llm-skillbook/feature-forge/references/workflow.md:1), [authority contract](/home/mark/kramtime/llm-skillbook/feature-forge/references/authority.md:1), [adapter/review contract](/home/mark/kramtime/llm-skillbook/feature-forge/references/adapters-and-reviews.md:1), [ledger template](/home/mark/kramtime/llm-skillbook/feature-forge/assets/ledger-template.md:1), [final-report template](/home/mark/kramtime/llm-skillbook/feature-forge/assets/final-report-template.md:1).
- Feature Forge dependency compatibility: [review-loop skill](/home/mark/kramtime/llm-skillbook/review-loop/SKILL.md:1), [review-loop dispatch interface](/home/mark/kramtime/llm-skillbook/review-loop/dispatch.md:1), [directory target validation](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/controller.py:360), [round-N limitation](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/controller.py:787), [request schema](/home/mark/kramtime/llm-skillbook/review-loop/review_loop/profiles.py:204).
- Autoprompt: [provider-neutral contract](/home/mark/tools/autoprompt-skill/agents/contracts/autoprompt.contract.json:1), [contract overview](/home/mark/tools/autoprompt-skill/agents/contracts/README.md:1), [Codex skill](/home/mark/tools/autoprompt-skill/agents/codex/SKILL.md:1), [playbooks](/home/mark/tools/autoprompt-skill/agents/codex/PLAYBOOKS.md:1), [gates](/home/mark/tools/autoprompt-skill/agents/codex/GATES.md:1), [modes](/home/mark/tools/autoprompt-skill/agents/codex/MODES.md:1), [package scripts](/home/mark/tools/autoprompt-skill/package.json:53), [provider generator](/home/mark/tools/autoprompt-skill/scripts/generate-provider-contracts.cjs:852), [runtime payload](/home/mark/tools/autoprompt-skill/scripts/runtime-payload.cjs:128), [support/benchmark README](/home/mark/tools/autoprompt-skill/README.md:60).
- Procoder: [AGENTS contract](/home/mark/tools/procoder/AGENTS.md:1), [architecture](/home/mark/tools/procoder/docs/architecture.md:1), [workflow](/home/mark/tools/procoder/docs/workflow.md:1), [quality chain](/home/mark/tools/procoder/docs/quality-chain.md:1), [domains](/home/mark/tools/procoder/docs/domains.md:1), [portability](/home/mark/tools/procoder/docs/portability.md:1), [CLI dispatcher](/home/mark/tools/procoder/cmd/procoder/main.go:405), [gate](/home/mark/tools/procoder/internal/gate/gate.go:1), [configuration](/home/mark/tools/procoder/internal/config/config.go:1), [test runner](/home/mark/tools/procoder/internal/testrun/testrun.go:1), [release controller](/home/mark/tools/procoder/internal/release/release.go:1).
- Zeroshot Node: [README](/home/mark/tools/zeroshot/README.md:25), [repository rules](/home/mark/tools/zeroshot/AGENTS.md:1), [orchestrator](/home/mark/tools/zeroshot/src/orchestrator.js:286), [SQLite ledger](/home/mark/tools/zeroshot/src/ledger.js:29), [agent lifecycle](/home/mark/tools/zeroshot/src/agent/agent-lifecycle.js:181), [conductor/router](/home/mark/tools/zeroshot/src/config-router.ts:56), [full-workflow validator schema](/home/mark/tools/zeroshot/cluster-templates/base-templates/full-workflow.json:380), [configuration admission](/home/mark/tools/zeroshot/src/config-validator.js:78), [predicate engine](/home/mark/tools/zeroshot/src/logic-engine.js:94), [provider registry](/home/mark/tools/zeroshot/src/agent-cli-provider/provider-registry.ts:267), [isolation manager](/home/mark/tools/zeroshot/src/isolation-manager.js:481), [copy containment](/home/mark/tools/zeroshot/src/copy-containment.ts:73), [context management](/home/mark/tools/zeroshot/docs/context-management.md:1), [trace export](/home/mark/tools/zeroshot/cli/trace-export.ts:48), [package/test scripts](/home/mark/tools/zeroshot/package.json:1).
- Zeroshot Rust/OECP: [native-v2 contract](/home/mark/tools/zeroshot/AGENTS.md:243), [graph types](/home/mark/tools/zeroshot/crates/openengine-cluster-protocol/src/graph.rs:145), [production graph verifier](/home/mark/tools/zeroshot/crates/openengine-cluster-server/src/graph_verifier.rs:21), [OECP lifecycle](/home/mark/tools/zeroshot/docs/openengine-cluster-protocol/v1/lifecycle.md:1), [worker profiles](/home/mark/tools/zeroshot/docs/openengine-cluster-protocol/v1/worker-profiles.md:1), [native admission](/home/mark/tools/zeroshot/zeroshot-rust/src/native_v2_admission.rs:1), [supervisor](/home/mark/tools/zeroshot/zeroshot-rust/src/native_v2_supervisor.rs:1), [one-run ledger](/home/mark/tools/zeroshot/zeroshot-rust/src/v2_run_ledger.rs:1), [fault contract](/home/mark/tools/zeroshot/zeroshot-rust/src/fault.rs:20), [native delivery](/home/mark/tools/zeroshot/zeroshot-rust/src/native_v2_delivery/github.rs:384), [distribution contract](/home/mark/tools/zeroshot/docs/zeroshot-rust-distribution.md:1), [CI](/home/mark/tools/zeroshot/.github/workflows/ci.yml:140).
- Fable Method: [portable contract](/home/mark/tools/fable-method/AGENTS.md:1), [core skill](/home/mark/tools/fable-method/skills/fable-method/SKILL.md:1), [loop](/home/mark/tools/fable-method/skills/fable-loop/SKILL.md:1), [judge](/home/mark/tools/fable-method/skills/fable-judge/SKILL.md:1), [domain maker](/home/mark/tools/fable-method/skills/fable-domain/SKILL.md:1), [domain template](/home/mark/tools/fable-method/skills/fable-method/references/domains/TEMPLATE.md:1), [flowcharts](/home/mark/tools/fable-method/skills/fable-method/references/flowcharts.md:1), [failure modes](/home/mark/tools/fable-method/skills/fable-method/references/failure-modes.md:1), [eval methodology](/home/mark/tools/fable-method/eval/README.md:1), [results log](/home/mark/tools/fable-method/eval/RESULTS.md:1), [workflow script](/home/mark/tools/fable-method/eval/workflow.js:1), [CI checker](/home/mark/tools/fable-method/.github/checks.py:1), [shell installer](/home/mark/tools/fable-method/install.sh:1), [PowerShell installer](/home/mark/tools/fable-method/install.ps1:1), [plugin manifest](/home/mark/tools/fable-method/.claude-plugin/plugin.json:1).

Historical plans/designs were used only for lineage when consistent with live sources. Marketing claims were qualified where current implementation, configuration or test evidence was narrower.
