## Guestflow — Phase 16.2 repo-clarity-cleanup paired review (2026-05-04)

REF first (19:52Z), INL ~20 min later (20:12Z). 29 input files (mixed: TS scripts, `package.json` × 4, `wrangler.json` × 2, `tsconfig`, `vitest.config`, 3 GH workflows, `webflow.json` tenant configs, `.gitignore`). 6 contexts (3 × `CLAUDE.md` + 3 × phase docs). Distinct outputs (`-REF1.md` / `-INL1.md`). Synthesizer claude both runs. `--skip-self` (host = claude).

Reviewer-mode pair this is **first paired run on Guestflow with a config-heavy input set** (prior G16.1 runs were source-file-heavy). Worth flagging because mode behaviour skewed differently.

### Headline anomaly: codex INL used MORE tokens than REF

| Reviewer | REF input | INL input | REF wall | INL wall |
|----------|-----------|-----------|----------|----------|
| claude   | 83        | 40        | 286s     | 193s     |
| gemini   | 844K      | 67K       | 206s     | 233s     |
| codex    | 2.70M     | **4.42M** | 336s     | 396s     |
| opencode | (0/0)     | (0/0)     | 348s     | **762s** |

Prompt: REF 69 KB, INL 183 KB (2.6× larger). Naive expectation: INL prompt larger but reviewers explore less → INL total cheaper. **Codex inverted that.** Codex INL did 57 tool calls (vs 82 REF) and pulled 4.42M input tokens — re-read most files even with content embedded. Reference mode was *cheaper* for codex on this input set.

Gemini behaved as expected (REF 36 calls / 844K in; INL 0 calls / 67K in — pure prompt ingestion). Opencode INL pathologically slow (762s) for 81K bytes output — worst latency-to-signal seen across all paired runs.

### What both runs found
- cwd-coupling in `sync-deploy-repos.ts:313` (`repoRoot = process.cwd()`) and `verify-tenant.ts:167` (`process.cwd()` default for deploy-target lookup). 3-4 reviewers each run. CI works (cwd = repo root) but contract violation.
- `client/README.md:15` claims `client/src/index.ts` is Worker entry — file absent, this is OpenNext/Next App Router (entry = `.open-next/worker.js`).
- Workspace docs advertise retired `npm run deploy` / workspace-dir invocation of root-only scripts.
- Stale `scripts/<name>.ts` paths in admin script doc-comments after the reorg moved them to `admin/scripts/`.
- All 4 reviewers agree: SNAPSHOT_ALLOWLIST prefix-strip correct, import boundaries clean, `__dirname`-relative resolution sound, `client/.next/` cleared.

### What only REF surfaced
- **opencode**: `types/cloudflare-workers.d.ts` orphan at root (2 lines, unreferenced); `build-widgets.ts:15-16` cwd-coupling via `process.cwd()`; `admin/scripts/legacy/README.md:1` heading still says `# scripts/legacy`.
- **codex**: `generate-tenant-env.ts:168` stale path; CI admin-build gap (claude also flagged in REF).
- **claude**: `sync-deploy-repos.ts:84` README_BANNER write — operator-noise complaint, but a real cleanup.

### What only INL surfaced
- **opencode**: `admin/tests/scripts/__snapshots__/__snapshots__/` duplicate dir — likely git-move artefact from the reorg, vitest reads the parent only so it's dead but confusable. Also `register-webhook.ts` dead code (test exists, no production consumer); `client/package.json:21` `webhook-tui` lives at `src/scripts/` not `client/scripts/` (taxonomy mismatch with import-boundary table).
- **claude**: `.gitignore` `/test-results/` + `/playwright-report/` are root-anchored — `client/test-results/` would not be ignored. Also `admin/CLAUDE.md` Project Structure tree omits `admin/scripts/`, `admin/tenant-config/`, `admin/deploy-targets.json`, `admin/migrations/`.
- **codex**: `docs/DEPLOY_RUNBOOK.md` references in `admin/CLAUDE.md:162` + `client/CLAUDE.md:206` should be `admin/docs/DEPLOY_RUNBOOK.md`.
- **gemini**: `client/package.json` is in `SNAPSHOT_ALLOWLIST` (line 34) AND overwritten by `rewritePackageJson` — redundant double-write. Concrete and worth confirming whether intentional.

### Severity drift, same model
**Gemini ranked the cwd-coupling bugs CRITICAL in REF, IMPORTANT in INL.** Same bugs, same lines, same model. No mechanistic explanation in the review text. File as confirmed mode-noise on severity classification — the *finding* is stable, the *severity* isn't.

### Cross-run context leakage (new)
**INL opencode read `16.2-IMPL-REVIEW-REF1.md` from the on-disk tree and cited it explicitly** ("flagged in prior review (`16.2-IMPL-REVIEW-REF1.md:160`)"). The prior-run output was sitting in `.planning/phases/16.2-…/`, opencode discovered it via tool calls, and re-flagged the `types/cloudflare-workers.d.ts` orphan with that pedigree. Prompt did not list this file. **Reference mode's tool-driven discovery pulls in artefacts that weren't in the input set.** Worth tracking — this is the first paired run where the second mode demonstrably contaminated itself with the first mode's output. Mitigation options: gitignore review outputs from the working tree until comparison is done, or write to a tmpdir.

### Telemetry quirks
- **Claude INL: in=40, out=734, 13 tool calls, 192s, 281 KB bytes.** 734 output tokens cannot account for 281 KB of stdout. Fifth paired run in a row with the same under-reporting shape (paralife pairs ×3 + this). Adapter is broken, not flaky. Same backlog item.
- Claude REF healthy: in=83, out=3334, 50 tool calls, 286s, 814 KB. Cache 7.4M.
- Codex INL cached 4.26M of its 4.42M total input — cache reuse high, but raw input still climbed past REF.
- Opencode 0/0/0 both modes (known adapter limitation).

### What this run *shows this time*
1. **First config-heavy paired run.** Findings still split mode-uniquely (~4-5 each). The "INL/REF surfaces different bugs" pattern holds across input shapes (TS source vs configs+TS).
2. **Codex token inversion is new.** First paired run where INL > REF total tokens for a reviewer that does heavy tool-calling. Not an adapter bug — codex genuinely re-read 57 files via tool calls in INL on top of the embedded content. Suggests codex doesn't trust embedded content for config-shaped inputs (`wrangler.json`, `package.json`, workflow YAMLs).
3. **Cross-run output leakage** is a real artefact of reference-mode + on-disk prior reviews. Document it before running more pairs in `.planning/`-tracked dirs.
4. **Severity is mode-sensitive even when finding is stable** — gemini swung the same cwd bug from CRITICAL to IMPORTANT between runs. Stop reading severity columns as ground truth on single runs.
5. **Opencode INL 762s wall time** — worst observed. Not a finding-quality issue (still found 3 unique INL bugs), but a latency outlier. Watch whether this repeats on configs-heavy inputs.

### What this run does *not* show
- Cannot claim codex INL > REF tokens generalises beyond config-heavy inputs. n=1 for that pattern.
- The cross-run leakage observation is from a single instance — opencode's behaviour, may or may not repeat across reviewers/runs. But the mechanism (tool calls discover working-tree artefacts) is general.
- Severity drift on cwd-coupling is one bug × one reviewer × one pair. Suggestive, not load-bearing.

### Recommended follow-up
- **Triage cwd bugs.** All 4 reviewers (across both runs) agree on `sync-deploy-repos.ts:313` + `verify-tenant.ts:167`. Probably promote to ship-fix even though CI happens to work.
- **Verify `admin/tests/scripts/__snapshots__/__snapshots__/` duplicate** (opencode INL only, but concrete and likely real).
- **Verify gemini's `client/package.json` redundant allowlist entry** — is the double-write intentional (defensive) or accidental?
- **Document cross-run leakage** in BACKLOG / README cautions for paired-run methodology.
- **Claude inline adapter** still broken — no progress, escalate.
