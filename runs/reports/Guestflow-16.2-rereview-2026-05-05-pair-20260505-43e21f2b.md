---
report_format_version: 1
pair_id: pair-20260505-43e21f2b
pair_type: paired
comparison_eligible: true
---


## Headline

_TBD — synthesizer will fill_

## Mode-divergence observations

_TBD — synthesizer will fill_

## Per-reviewer notes

## Guestflow — Phase 16.2 repo-clarity-cleanup re-review (2026-05-05)

Paired re-review one day after the round-1 pair. Same input set (29 source/config + 4 docs), same context (3 × `CLAUDE.md` + 3 × phase docs). Prompt swap: `16.2-REREVIEW-PROMPT.md` (~7 KB on disk) explicitly listed 13 closed findings from round 1 + commits `2d815f4` / `9134dc5` / `441b8f5` and instructed reviewers not to re-flag. Distinct outputs (`-REF2.md` / `-INL2.md`). `--skip-self` (host = claude). `--project-tag Guestflow-16.2-rereview` partitions runs.jsonl from the 2026-05-04 pair. REF first (00:38Z, 7m), 20m gap, INL (01:07Z, 11m).

Round-2 verdict from all 6 reviews: **SHIP WITH FIXES**. No blockers; consensus is two MEDIUM items + cleanup.

### Headline: codex token inversion did NOT repeat

| Reviewer | REF1 in | INL1 in | REF2 in | INL2 in | REF1 wall | INL1 wall | REF2 wall | INL2 wall |
|----------|---------|---------|---------|---------|-----------|-----------|-----------|-----------|
| gemini   | 844K    | 67K     | **1.42M** | 189K    | 206s     | 233s     | 343s     | **117s**  |
| codex    | 2.70M   | **4.42M** | 2.60M   | **2.12M** | 336s   | 396s     | 276s     | 252s     |
| opencode | (0/0)   | (0/0)   | (0/0)   | (0/0)   | 348s     | **762s** | 421s     | **632s** |

Round-1 anomaly: codex INL > REF (2.70M → 4.42M). Round-2 reversed: codex INL < REF (2.60M → 2.12M). Codex INL2 made 32 tool calls vs INL1's 57. **n=1 for inversion in round 1; round-2 contradicts.** Tentative read: round-1 was a transient codex behaviour, not a stable property of config-heavy inputs. Worth one more paired run on configs to settle.

Gemini swung the other way: REF2 input >> REF1 (844K → 1.42M, 36 → 46 tool calls). Same model, same files, more thorough this time. INL2 only 2 tool calls (pure prompt ingestion, no FS exploration). Both modes wider behaviour gap than round 1. **Mode-driven gemini behaviour stable across runs; absolute volume isn't.**

Opencode INL still worst latency (632s), but down from 762s round-1. Latency improvement of ~17% with a similar prompt shape. Not a fix — likely upstream serving variance. Still the worst-of-paired in both rounds.

### Closed-finding discipline (the point of round 2)

The prompt's closed-findings table listed 13 items (12 fixed + 1 deferred). Reviewers were told "do not re-flag unless fix is incomplete; flag incompleteness explicitly with cite."

**Both reviews held the line.** No reviewer re-listed a closed item as new. Two items flagged as **incomplete** (consistent across both modes, all 6 reviews):

1. **`admin/CLAUDE.md` Project Structure tree** — claimed fixed by `9134dc5`, NOT fixed in current tree. Still omits `scripts/`, `migrations/`, `tenant-config/`, `deploy-targets.json`, `docs/`. All 6 reviewers, both modes flagged. **Strong consensus this is a regression vs claimed fix.** This is the cleanest "in-tree fix claim diverged from reality" signal multi-review has produced — six independent voices, two modes, identical pinpoint location.
2. **`client/CLAUDE.md` Commands block** — closed-finding claim said `deploy:verify` was added; codex (REF2 + INL2) and opencode (INL2) say `deploy:preflight` is listed but `deploy:verify` is not. Worth manual verification — gemini and others didn't flag, so either the fix is partial or codex/opencode read the wrong section. **Investigate before declaring incomplete.**

The discipline worked: **prompt-led incomplete-fix detection scales**. Loud closed-findings table → reviewers focus on verifying claims rather than rediscovering bugs. Methodology recommendation: future re-reviews should always pair an explicit closed-findings table with cite-the-commit-claims framing.

### Cross-run output leakage

Round 1 had opencode INL1 reading `16.2-IMPL-REVIEW-REF1.md` from disk and citing it explicitly. Round 2 prompt mentioned both round-1 reviews by path in the "context" section ("Read these to avoid re-flagging closed items, NOT to inherit their conclusions") — explicitly inviting tool-driven discovery.

**No round-2 review cites a prior review file by path.** Reviewers used the prompt's closed-findings table directly; none surfaced the round-1 outputs in their findings. The prompt's explicit framing channelled what would otherwise be unintentional leakage into intentional signal. This is the cleanest demonstration so far that **prompt-engineered leakage** (loud reference, explicit do/don't) is preferable to **incidental leakage** (file lying in tree, reviewer stumbles on it).

### Severity drift, same finding

CI OpenNext gap — gemini ranked **HIGH** in both REF2 and INL2; codex/opencode ranked **MEDIUM** in both. Round-2 gemini severity stable across modes. Round-1 had gemini swing CRITICAL→IMPORTANT on the cwd bug between modes. **One round-2 reviewer is consistent within rounds; the same reviewer was inconsistent in round 1.** Suggestive that severity drift is per-finding-class, not per-reviewer — gemini was confident on CI gaps both times, was uncertain on cwd bugs.

Cross-reviewer drift on the same finding: gemini HIGH, codex/opencode MEDIUM on CI OpenNext. Round-2 confirms drift between *reviewers* on severity is normal, not noise.

### What both modes found (consensus, both rounds combined)

Round 2 surfaced 5 items that round 1 missed:

- **`client/package.json:24-25` `dependencies` block contradicts D5 (locked: scripts-only, no deps)** — gemini INL2, opencode INL2. Round-1 didn't catch despite the file being in scope.
- **`SNAPSHOT_ALLOWLIST` includes `client/next-env.d.ts` (gitignored, never copied)** — codex INL2 only. Dead allowlist entry.
- **`admin/src/app/clients/new/wizard/step-4-review.tsx:234` wizard handoff cites stale `docs/DEPLOY_RUNBOOK.md` path** — codex REF2, gemini INL2, opencode INL2 (MEDIUM). File is OUT of the input manifest, all three discovered it via tool calls. **Reference-mode + inline-mode both surfaced an out-of-manifest finding because the prompt's "operator-facing doc accuracy" framing pushed them to grep for stale paths broadly.** Methodology lesson: if you want out-of-manifest discoveries, make a category in the prompt that names them.
- **`admin/scripts/seed-tenant0.ts:44/57` `.dev.vars` path mismatch** — codex INL2 (LOW), opencode INL2 (HIGH, runtime-crash framing). Severity drift on the same line.
- **Top-level `permissions: contents: read` missing from `test.yml`** — all 3 INL2 reviewers, codex REF2. Round-1 didn't reach this because the build job was new in `441b8f5`.

Round 2 also surfaced 4 opencode-INL-only findings (D4 e2e count, D5 `GET /api/build` endpoint table omission, D6 broken `--watch` invocation, D7 client-script doc-comments) — typical opencode high-recall-low-precision. Worth manually triaging; D6 in particular looks real and trivial to verify (`npm test -- --watch` under `vitest run` is silently a no-op).

### What this run *shows*

1. **Codex INL>REF inversion was a one-off**, not a property of config-heavy inputs.
2. **Prompt-led closed-finding verification works**. Six reviewers, two modes, zero re-flags of resolved items, two incomplete-fix detections with strong consensus.
3. **In-tree fix claims can diverge from reality and reviewers will catch it** — `9134dc5`'s claim about `admin/CLAUDE.md` tree update was wrong; six independent voices nailed it.
4. **Mode-driven divergence is real but not noise** — INL2 produced 5+ findings absent from REF2, REF2 produced 1+ absent from INL2. Both modes still complementary even on a re-review.
5. **Out-of-manifest discoveries follow prompt framing** — `step-4-review.tsx` (not in input set) was found by 3 reviewers because the prompt asked about operator-facing copy.

### What this run *doesn't* show

- Whether closed-finding-table discipline survives prompts with 30+ closed items. n=1 for the technique on a 13-item table.
- Whether opencode latency improvement is upstream variance or genuine; need ≥3 more paired runs to call.
- Whether codex token inversion can recur on different config-heavy input shapes — round-2 reversal narrows the search space but doesn't close it.

### Recommended follow-up

- **Apply the agreed fixes** to Phase 16.2 (admin/CLAUDE.md tree, CI OpenNext step, allowlist redundancy, deploy:verify in client/CLAUDE.md, step-4-review.tsx path, SLUG_REGEX consolidation, test.yml permissions block).
- **Verify codex/opencode's `deploy:verify` claim against the actual file** — gemini didn't flag, so possibly a false positive driven by the closed-findings table phrasing.
- **Probe `seed-tenant0.ts` `.dev.vars` location** — codex says fix the message, opencode says fix the path. Whichever is right, the other framing is wrong.
- **Promote re-review prompt template** to multi-review docs as a methodology pattern: closed-findings table + commit-claim-cite + explicit "flag incomplete only" wording. Highest closed-finding-discipline result yet observed.
- **Claude inline adapter** still under-reports tokens (separate backlog) — not exercised here since claude was synth-only via `--skip-self`.
