# Paralife Phase 19 — External Multi-Review Prompt

## Scope

You are reviewing **Phase 19** of Paralife: a Spring Boot 3.4 / Java 21 distributed living simulation server. Phase 19 ships two scale-path infrastructure components plus a semantic-equivalence verification gate, executed across 4 sequential plans (waves):

- **Plan 01 — `EligibleCellIndex`** (SCALE-06): O(1) sparse-set replacing the previous 50-retry random-scan placement for `r|` register/respawn ingress. Three eligibility constraints (no occupant, not OVERCROWDED, no would-overcrowd-neighbour). Bit-exact deterministic placement under `paralife.simulation.spawn.seed`.
- **Plan 02 — `LiveEntityRegistry`** (SCALE-07 substrate): sparse-set (`ArrayList<EntityEntry>` + `HashMap<String,Integer>` id→index) maintaining the authoritative live-grid-occupant list. O(1) register/unregister/updatePosition. `snapshot()` returns row-major-sorted shallow copy. Lifecycle hooks at all 13 structural grid-mutation sites across `SimulationEngine`, `EnvironmentEngine`, `ActionResolver`, `DeathFinalizer`, `WorldWebSocketHandler`.
- **Plan 03 — `GoldenTraceEquivalenceTest`** (D-10 gate): per-session SHA-256 digest map across a fixed-seed 30-bot 16x16 200-tick dual-run, with pinned 26-session JSON baseline, asserting byte-identical outbound WebSocket encoding. Wired via a new `OutboundSender.FrameEmitListener` test seam invoked **inside** `synchronized(session)` after `sendMessage`.
- **Plan 04 — Entity-list iteration refactor** (SCALE-07 consumer): replaces 7 `SimulationEngine` and 2 `EnvironmentEngine` per-tick O(width×height) grid scans with `liveEntityRegistry.snapshot()` (O(N)). `TickBroadcaster` intentionally **NOT** migrated (CONSENSUS-H1 OPTION B, user-locked). Diffusion/CA passes (toxin/mutagen/lightning/fertility) preserved as grid-walks.

Treat this as **one cohesive phase**, not four independent reviews. The interesting bugs are in the seams between waves.

## Project context (read first)

The full architectural ground rules live in `CLAUDE.md` at the repo root. Key invariants Phase 19 must not violate:

- **Single-threaded mutation core.** All world mutations happen inside `@EventListener(TickEvent)` handlers ordered by `@Order`, on one thread. Outbound WebSocket sender VTs (Phase 17 D-10) are the only concurrency in the hot path. Phase 19 must not introduce new mutation parallelism.
- **WS:entity 1:1.** Every WebSocket session owns exactly one entity during its Alive phase. Many connections = scale; multiplexing entities over a session is forbidden.
- **Tick pipeline `@Order`** (do not reorder): SimulationEngine(10) → EnvironmentEngine(14) → ActionResolver(20) → EnvPostActionReconciler(25) → PerceptionBroadcaster(50) → TickBroadcaster(100). Per-tick state visible to a handler must be the post-state of all lower-`@Order` handlers.
- **Env state projection three layers**: shadow grids (authoritative) → per-tick status caches (read-only projection) → wire bitmask (zero-trust, vision-scoped). Phase 19 Plan 01 made `cellStatusCache` a `volatile Map.copyOf` snapshot (CONSENSUS-H4 fix); the staging map is tick-thread-only.
- **Locked artefacts** Phase 19 must not touch: `RockGenerator.java` (Phase 15 D-34/D-35 deterministic rock placement), wire grammar in `15-SCHEMA.md`, `RejectionToken.GRID_FULL` taxonomy from Phase 17 D-07.

## What I want from you

Phase 19 was already internally peer-reviewed (`.planning/phases/19-.../19-REVIEWS.md`) and ships with `19-VERIFICATION.md` flagging three latent warnings (WR-01, WR-02, WR-03) plus two info notes (IN-01, IN-02). I am asking you for **independent depth**, not a re-checklist of items the in-tree reviews already enumerate. In particular I want:

### 1. Cross-wave interaction bugs

The four plans share state and Spring beans. Look for problems that only appear when waves compose:

- **Spring `@Lazy` circular bean cycle.** `EligibleCellIndex` ↔ `EnvironmentEngine` ↔ `DeathFinalizer`/`ActionResolver`/`SimulationEngine` was a real cycle hit during Plan 01 execution; the fix uses `@Autowired @Lazy` setter injection at multiple sites. Is the lazy-proxy pattern sound? Are there bean-creation-order assumptions in `@PostConstruct` paths that would fail in a different startup ordering (e.g. test slice contexts, `@DependsOn("rockGenerator")` chain)? Any path where a `@Lazy` proxy is dereferenced before the real bean is initialised?
- **Hook coverage at structural mutation sites.** Plan 01 wires 22 `EligibleCellIndex.notifyChanged` calls; Plan 02 wires 13 `LiveEntityRegistry.register/unregister/updatePosition` calls. Are both hook sets coherent at every site? Specifically: bond-formation, composite-formation, panic-zone composite collapse, composite reproducer-bud, `executeCompositeMovement` per-member loop, `revertToBondedPair`, `dissolveToParticles`, `cleanupCompositeMemberCellViaFinalizer`. Look for sites where the registry is updated but the index is not (or vice versa) — a missed pair leaves the two structures inconsistent.
- **Iteration-ordering vs `Collections.shuffle` determinism.** `LiveEntityRegistry.snapshot()` sorts by row-major linear index `x*height+y` to preserve the existing shuffle-determinism contract that Plan 04 relies on. The acceptance gate hard-codes `Collections.shuffle` count = 3 and nested-loop count ≤ 2 in `SimulationEngine`. Is the row-major sort actually equivalent to the previous grid-scan iteration order at every site? What happens for two entities sharing an `x*height+y` (impossible if positions are unique — but is that invariant enforced anywhere)?
- **Golden trace as a contract.** The `GoldenTraceEquivalenceTest` baseline pins 26 SHA-256 digests. The seam (`OutboundSender.FrameEmitListener`) fires inside `synchronized(session)` after `sendMessage`. Is the test capturing what it claims to capture (byte-identical outbound encoding before/after the Plan 04 cut)? Could a future change pass the gate while changing observable behaviour the test does not encode? Is `resetAll()` actually exhaustive, or are there other per-entity `ConcurrentHashMap` fields (the kind that bit Plan 03 twice — `lastReproducedTick`, `lastRosterHashBySession`) still leaking state between in-test runs?

### 2. Adjudicate the three latent warnings

`19-VERIFICATION.md` flags these as "no current correctness impact". I want a second opinion — are they really latent, or are they active bugs hiding behind today's call paths?

- **WR-01: `entityStatusCache` is a plain `HashMap`.** `cellStatusCache` got the volatile + `Map.copyOf` snapshot fix (CONSENSUS-H4). `entityStatusCache` did not. `entityStatusCacheView()` returns a live `unmodifiableMap` wrapper. Today's only readers are tick-thread-only. Is there any path (admission gate? backpressure stall handling? metrics? composite-formation event?) where a non-tick thread reads it? If a future Phase 20.1 parallel perception reads it, what breaks first?
- **WR-02: `EligibleCellIndex.initialize()` not `synchronized`.** `rebuildForTest()` is synchronized and calls `initialize()`. `@PostConstruct` calls `initialize()` directly without the lock. Spring's `@PostConstruct` is single-threaded, so today this is fine. But package-private visibility means a future test could call `initialize()` directly. Is the lock-order documentation (`index-monitor → grid-read-lock`) clear enough that a future contributor will not invert it? Is there any visible-from-elsewhere mutation that could race with `initialize()`?
- **WR-03: `entitySnapshot()` fallback creates `EntityEntry("_", ...)` sentinel.** Plan 04 helper falls back to a grid-scan when the registry is null or empty (back-compat for tests that bypass `LiveEntityRegistry.register()`). `processDeaths` reads only `entry.position()` and re-fetches the entity from the grid cell, so the `"_"` sentinel never reaches user code. But does *every* caller of `entitySnapshot()` only consume `position()`? What if a future caller reads `entry.entityId()` expecting the real id?

### 3. The deliberately-deferred `TickBroadcaster` migration

CONSENSUS-H1 was the most contentious decision in the in-tree review rounds. Two options were explored:

- **OPTION A** — migrate `TickBroadcaster` to consume `LiveEntityRegistry.snapshot()`, deepening Plan 04's blast radius
- **OPTION B (chosen, user-locked)** — leave `TickBroadcaster` consuming the existing roster, defer the migration to Phase 20.1+. `EntityEntry.sessionId` is an `Optional<String>` field that is populated only at WS handshake and `Optional.empty()` for all server-internal entity creations.

Is OPTION B durable? Specifically:
- Does the vestigial `Optional<String> sessionId` field cause any subtle bugs today? (E.g., bond-formation creates a `BondedPair` with `Optional.empty()` sessionId — does anything downstream rely on session-attribution that this leaves unsatisfied?)
- Will Phase 20.1 actually be able to migrate `TickBroadcaster` without a wire-protocol change, given the Phase 17 D-10 VT-per-session outbound queue contract?
- Is the Javadoc on `LiveEntityRegistry.java:21` (which documents the OPTION B choice) sufficient, or is there a load-bearing assumption elsewhere that should be commented at its actual location?

### 4. Things specifically out of scope — do not flag

- The 3 IN-* notes from `19-VERIFICATION.md` (`clearStateForTest()` public visibility, `CLAUDE.md` `@PostConstruct` doc staleness) are tracked.
- Performance numbers / benchmark results — Phase 21 owns this (SCALE-10).
- `processNutrientSpawning` keeping its grid-walk shape — explicitly out of scope per CONTEXT.md.
- Initial rock placement (`RockGenerator.java`) — locked Phase 15 D-34/D-35, do not touch.
- Renames, doc fixes, comment polishing — give us substance only.
- TODOs explicitly deferred to Phase 19.1 (parallel `PerceptionBroadcaster` / parallel `TickBroadcaster` encode) or to Phase 20+ backlog (conflict-graph parallel dispatch, spatial tile decomposition, striped lock granularity).

## Output format

For every finding, give:

- **Severity** — HIGH (active bug, blocks ship), MEDIUM (latent hazard with realistic activation path), LOW (style / brittleness), INFO (observation).
- **Location** — `path/to/File.java:LINENO` or `<file>:<symbol>` if line numbers are unstable.
- **What's wrong** — one or two sentences. Cite the concrete code path.
- **Why it matters** — what behaviour breaks under what conditions. Be specific about the trigger.
- **Suggested fix** — concrete patch direction, not a generality.

Group findings by area: cross-wave interactions / WR-1 / WR-2 / WR-3 / OPTION B durability / other. Within each area, severity-descending.

If you find nothing in an area, say so explicitly — "no issues" beats silence.

## Anti-asks

- Do not ask for files. You have the source tree; read what you need.
- Do not summarise the phase plan back to me — I wrote it.
- Do not produce a "next steps" or "recommendations" wrap-up. Findings are the deliverable.
- Do not flag `Collections.shuffle` randomness ordering as suspicious — it is the locked semantic-equivalence contract; the row-major sort exists specifically to preserve it.
- Do not propose migrating `TickBroadcaster` in this phase — that is the OPTION B decision; argue against the decision substantively if you must, but don't pretend it isn't made.

## Appendix — files most worth reading

Production code (Phase 19 net-new or substantively modified):

- `src/main/java/com/paralife/engine/EligibleCellIndex.java` (new, 256 lines)
- `src/main/java/com/paralife/engine/LiveEntityRegistry.java` (new, 169 lines)
- `src/main/java/com/paralife/engine/SimulationEngine.java` (Plan 04 — 7 grid-scan sites cut; 9 `notifyChanged` hooks; 7 `LiveEntityRegistry` lifecycle hooks)
- `src/main/java/com/paralife/engine/EnvironmentEngine.java` (Plan 01 — `cellStatusCache` volatile snapshot; Plan 04 — 2 grid-scan sites cut)
- `src/main/java/com/paralife/engine/ActionResolver.java` (11 `notifyChanged` hooks, 3 `LiveEntityRegistry` hooks, `clearStateForTest()`)
- `src/main/java/com/paralife/engine/DeathFinalizer.java` (placement-clear hooks, `LiveEntityRegistry` unregister hooks)
- `src/main/java/com/paralife/engine/TickEngine.java` (Wave-1 hotfix: `@PostConstruct` → `@EventListener(ApplicationReadyEvent.class)`)
- `src/main/java/com/paralife/websocket/WorldWebSocketHandler.java` (placement path swap; `cleanupByEntityId` / `cleanupBot` hooks)
- `src/main/java/com/paralife/admission/OutboundSender.java` (`FrameEmitListener` test seam)
- `src/main/java/com/paralife/admission/AdmissionMetrics.java` (`paralife.placement.lost-race.total` counter)
- `src/main/java/com/paralife/websocket/TickBroadcaster.java` (`clearStateForTest()`; intentionally NOT consuming `LiveEntityRegistry`)

Tests (not in your context — read them via your own tools if a contract claim needs verifying; they encode part of the deliverable):

- `src/test/java/com/paralife/engine/GoldenTraceEquivalenceTest.java` (D-10 gate)
- `src/test/java/com/paralife/engine/GoldenTraceCapture.java`
- `src/test/resources/golden-trace-phase19.json` (pinned 26-session digest baseline)
- `src/test/java/com/paralife/engine/LiveEntityRegistryInvariantTest.java` (4 lifecycle scenarios incl. bond / composite formation)
- `src/test/java/com/paralife/engine/LiveEntityRegistryTest.java` (14 unit tests)
- `src/test/java/com/paralife/engine/PlacementDeterminismTest.java` (D-06 bit-exact)
- `src/test/java/com/paralife/engine/EligibleCellIndexTest.java`
- `src/test/java/com/paralife/engine/EligibleCellIndexRectangularTest.java`
- `src/test/java/com/paralife/engine/EntityListIterationTest.java` (Plan 04 RED→GREEN gate)
- `src/test/java/com/paralife/websocket/PlacementDensityIntegrationTest.java` (live WS frame fill of 8x8 grid → `E|503|GRID_FULL`)
- `src/test/java/com/paralife/engine/CompositeFormationDeterminismTest.java` (modified — registry sync between dual-run scenarios)
- `src/test/java/com/paralife/metrics/EmergenceMetricsWiringTest.java` (modified — `liveEntityRegistry.clearForTest()` per-test)

Phase planning documents (context only — code is ground truth):

- `.planning/phases/19-high-density-placement-partition-aware-world-execution/19-CONTEXT.md` (decisions D-01..D-12)
- `.planning/phases/19-high-density-placement-partition-aware-world-execution/19-VERIFICATION.md` (the 4-truth verification, the 3 WR-* warnings, the 2 IN-* notes)
- `.planning/phases/19-high-density-placement-partition-aware-world-execution/19-REVIEWS.md` (in-tree multi-AI review rounds — to *avoid* re-finding what was already found)
- `.planning/phases/19-high-density-placement-partition-aware-world-execution/19-01-placement-index-SUMMARY.md`
- `.planning/phases/19-high-density-placement-partition-aware-world-execution/19-02-live-entity-registry-SUMMARY.md`
- `.planning/phases/19-high-density-placement-partition-aware-world-execution/19-03-golden-trace-equivalence-SUMMARY.md`
- `.planning/phases/19-high-density-placement-partition-aware-world-execution/19-04-entity-list-iteration-SUMMARY.md`

`CLAUDE.md` at repo root encodes the invariants Phase 19 was designed around — read its "Conventions", "Architecture", "Outbound concurrency", and "Connection model" sections before forming opinions about whether a finding is real.
