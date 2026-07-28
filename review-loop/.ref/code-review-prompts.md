# /code-review — reconstructed prompt text (Claude Code 2.1.215)

Extracted from the bundled CLI binary (`~/.local/share/claude/versions/2.1.215`).
The prompt is assembled per effort tier from shared fragments. Placeholders
rendered here: `${$o}` = the subagent (Task/Agent) tool, `${Iue}` =
ReportFindings tool, `${Fk}` = Artifact tool, `${z$e}` = artifact-design skill.
Each tier has (a) a subagent fan-out version and (b) a single-pass inline
fallback used when the subagent tool is unavailable. At high/xhigh/max with
workflows enabled, a Workflow script version runs instead (see end).

Tier ladder (subagent versions):

| Tier | Tag |
|---|---|
| low | `low effort → 1 diff pass → no verify → ≤4 findings` |
| medium | `medium effort → 3+5 angles × 6 candidates → 1-vote verify → ≤8 findings` |
| high | `high effort → 3+5 angles × 6 candidates → 1-vote verify (recall-biased) → ≤10 findings` |
| xhigh | `xhigh effort → 5+5 angles × 8 candidates → 1-vote verify → sweep → ≤15 findings` |
| max | `max effort → 5+5 angles × 8 candidates → 1-vote verify → sweep → ≤15 findings` |

---

## LOW effort (full text)

`low effort → 1 diff pass → no verify → ≤4 findings`

## Turn 1 — read

One tool call: read the unified diff (`git diff @{upstream}...HEAD; git diff HEAD`
to cover both committed and uncommitted changes, or `git diff main...HEAD` /
the target passed as an argument). Skip test/fixture
hunks (`test/`, `spec/`, `__tests__/`, `*_test.*`, `*.test.*`,
`fixtures/`, `testdata/`) — test-file changes are not reviewed at this level.
No subagents, no full-file reads.

## Turn 2 — findings

Flag runtime-correctness bugs visible from the hunk alone: inverted/wrong
condition, off-by-one, null/undefined deref where adjacent lines show the value
can be absent, removed guard, falsy-zero check, missing `await`,
wrong-variable copy-paste, error swallowed in a catch that should propagate.
Also flag — still from the hunk alone — new code that duplicates an existing
helper visible in the diff context, and dead code the diff leaves behind.

Do **not** flag style, naming, perf, missing tests, or anything outside the
hunk.

Output at most **4 findings**, most-severe first, one line each:
`path/to/file.ext:123 — what's wrong and the concrete failure`. If nothing
qualifies, output exactly `(none)`.

> Variant (also in the binary): identical except the target is
> "Target **min(files_changed, 4) findings** … If you have fewer, do one more
> pass focused on the largest changed file and on any **removed** code blocks.
> Output `(none)` only if the diff is trivially correct after that pass."

---

## Shared fragments (used by medium/high/xhigh/max)

### Phase 0 — Gather the diff

Run `git diff @{upstream}...HEAD` (or `git diff main...HEAD` / `git diff HEAD~1`
if there's no upstream) to get the unified diff under review. If there are
uncommitted changes, or the range diff is empty, also run `git diff HEAD` and
include the working-tree changes in scope — the review often runs before the
commit. If a PR number, branch name, or file path was passed as an argument,
review that target instead. Treat this diff as the review scope.

### Correctness angles

### Angle A — line-by-line diff scan

Read every hunk in the diff, line by line. Then Read the enclosing function for
each hunk — bugs in unchanged lines of a touched function are in scope (the PR
re-exposes or fails to fix them). For every line ask: what input, state, timing,
or platform makes this line wrong? Look for inverted/wrong conditions,
off-by-one, null/undefined deref, missing `await`, falsy-zero checks,
wrong-variable copy-paste, error swallowed in catch, unescaped regex metachars.

### Angle B — removed-behavior auditor

For every line the diff DELETES or replaces, name the invariant or behavior it
enforced, then search the new code for where that invariant is re-established.
If you can't find it, that's a candidate: a removed guard, a dropped error
path, a narrowed validation, a deleted test that was covering a real case.

### Angle C — cross-file tracer

For each function the diff changes, find its callers (Grep for the symbol) and
check whether the change breaks any call site: a new precondition, a changed
return shape, a new exception, a timing/ordering dependency. Also check callees:
does a parallel change in the same PR make a call unsafe?

### Angle D — language-pitfall specialist   *(xhigh/max only)*

Scan for the classic pitfalls of the diff's language/framework — for example:
JS falsy-zero, `==` coercion, closure-captured loop var; Python mutable default
args, late-binding closures; Go nil-map write, range-var capture; SQL injection;
timezone/DST drift; float equality. Flag any instance the diff introduces.

### Angle E — wrapper/proxy correctness   *(xhigh/max only)*

When the PR adds or modifies a type that wraps another (cache, proxy, decorator,
adapter): check that every method routes to the wrapped instance and not back
through a registry/session/global — e.g. a caching provider holding a
`delegate` field that resolves IDs via `session.get(...)` instead of
`delegate.get(...)` will re-enter the cache or recurse. Also check that the
wrapper forwards all the methods the callers actually use.

### Cleanup / altitude / conventions angles

### Reuse

The angles above hunt for bugs; this one and the next two hunt for cleanup in
the changed code. Flag new code that re-implements something the codebase
already has — Grep shared/utility modules and files adjacent to the change,
and name the existing helper to call instead.

### Simplification

Flag unnecessary complexity the diff adds: redundant or derivable state,
copy-paste with slight variation, deep nesting, dead code left behind. Name
the simpler form that does the same job.

### Efficiency

Flag wasted work the diff introduces: redundant computation or repeated I/O,
independent operations run sequentially, blocking work added to startup or
hot paths. Also flag long-lived objects built from closures or captured
environments — they keep the entire enclosing scope alive for the object's
lifetime (a memory leak when that scope holds large values); prefer a
class/struct that copies only the fields it needs. Name the cheaper
alternative.

### Altitude

Check that each change is implemented at the right depth, not as a fragile
bandaid. Special cases layered on shared infrastructure are a sign the fix
isn't deep enough — prefer generalizing the underlying mechanism over adding
special cases.

### Conventions (CLAUDE.md)

Find the CLAUDE.md files that govern the changed code: the user-level
~/.claude/CLAUDE.md, the repo-root CLAUDE.md, plus any CLAUDE.md or
CLAUDE.local.md in a directory that is an ancestor of a changed file (a
directory's CLAUDE.md only applies to files at or below it). Read each one
that exists, then check the diff for clear violations of the rules they state.

Only flag a violation when you can quote the exact rule and the exact line
that breaks it — no style preferences, no vague "spirit of the doc"
inferences. In the finding, name the CLAUDE.md path and quote the rule so the
report can cite it. If no CLAUDE.md applies, return nothing for this angle.

### Cleanup precedence note (follows the angle list in every tier)

Cleanup, altitude, and conventions candidates use the same
`file`/`line`/`summary` shape; in `failure_scenario`, state the concrete
cost (what is duplicated, wasted, harder to maintain, or which CLAUDE.md rule
is broken) instead of a crash. Correctness bugs always outrank cleanup,
altitude, and conventions findings when the output cap forces a cut.

### Verdict ladder (3-state)

- **CONFIRMED** — can name the inputs/state that trigger it and the wrong
  output or crash. Quote the line.
- **PLAUSIBLE** — mechanism is real, trigger is uncertain (timing, env,
  config). State what would confirm it.
- **REFUTED** — factually wrong (code doesn't say that) or guarded elsewhere.
  Quote the line that proves it.

### Recall-biased verdict rules

**PLAUSIBLE by default** — do not refute a candidate for being "speculative" or
"depends on runtime state" when the state is realistic: concurrency races,
nil/undefined on a rare-but-reachable path (error handler, cold cache, missing
optional field), falsy-zero treated as missing, off-by-one on a boundary the
code does not exclude, retry storms / partial failures, regex/allowlist that
lost an anchor. These are PLAUSIBLE.

**REFUTED** only when constructible from the code: factually wrong (quote the
actual line); provably impossible (type/constant/invariant — show it); already
handled in this diff (cite the guard); or pure style with no observable effect.

### Phase 2 — Verify (1-vote, 3-state)   *(medium; also xhigh/max)*

Dedup candidates that point at the same line/mechanism, keeping the one with
the most concrete failure scenario. For each remaining candidate, run **one
verifier** via the Agent tool: give it the diff, the relevant
file(s), and the candidate, and have it return exactly one of:

[Verdict ladder above]

Keep candidates where the vote is CONFIRMED or PLAUSIBLE.

### Phase 2 — Verify (1-vote, recall-biased)   *(high)*

Dedup near-duplicates (same defect, same location, same reason → keep one). For
each remaining candidate, run **one verifier** via the Agent tool:
give it the diff, the relevant file(s), and the candidate; it returns exactly
one of **CONFIRMED / PLAUSIBLE / REFUTED**.

[Recall-biased verdict rules above]

Keep **CONFIRMED and PLAUSIBLE**. Drop REFUTED.

### Phase 3 — Sweep for gaps   *(xhigh/max only)*

Run **one more finder** as a fresh reviewer who has the verified list. Re-read
the diff and enclosing functions looking ONLY for defects not already listed.
Do not re-derive or re-confirm anything already there — the job is gaps. Focus
on what the first pass tends to miss: moved/extracted code that dropped a guard
or anchor; second-tier footguns (dataclass default evaluated once, `hash()`
non-determinism, lock-scope shrink, predicate methods with side effects);
setup/teardown asymmetry in tests; config defaults flipped.

Surface **up to 8 additional candidates**, each naming a defect not already on
the list. If nothing new, return an empty sweep — do not pad.

### Output — plain-text variant (cap N = 8/10/15 by tier)

## Output

Return findings as a JSON array of at most N objects:

```json
[
  {
    "file": "path/to/file.ext",
    "line": 123,
    "summary": "one-sentence statement of the bug",
    "failure_scenario": "concrete inputs/state → wrong output/crash"
  }
]
```

Ranked most-severe first. If more than N survive, keep the N most
severe. If nothing survives verification, return `[]`.

### Output — ReportFindings variant

## Output

Call the ReportFindings tool once to report this review's results
with `{level, findings}`. `findings` is at most N entries ranked
most-severe first; each entry has `file`, `line`, `summary`,
`short_summary` — the claim compressed to ≤60 characters, no rationale
or consequence clause — `failure_scenario`, and `category` — a short kebab-case
slug for the angle that produced it (`correctness`, `simplification`,
`efficiency`, `reuse`, `altitude`, `conventions`, or a more specific slug like
`test-coverage` when one fits better) — plus `verdict` when a verify pass
produced one. If more than N survive, keep the N most severe. If
nothing survives verification, call it with an empty array. Do not also print
the findings as text.

### Artifact appendix (appended when publishing applies)

## Publishing a shareable review (Artifact)

After the findings are produced, also publish them as an artifact so they can
be shared and iterated on outside the terminal:

1. Load the `artifact-design` skill (utilitarian treatment —
   this is a document).
2. Write the findings to an HTML file: one section per finding with the file
   path and line, the one-line summary, the concrete failure scenario, and the
   relevant code snippet. If nothing survived verification, the page says so
   in one line.
3. Call the Artifact tool with that file path.
4. End the page body with this line verbatim:

   > Paste this URL back into Claude Code to keep iterating on these findings.

Skip this step if the review was invoked only to feed another tool (e.g. a
workflow step whose caller handles its own output).

---

## MEDIUM effort (assembled)

`medium effort → 3+5 angles × 6 candidates → 1-vote verify → ≤8 findings`

You are reviewing for **precision** at medium effort: every finding you surface
should be one a maintainer would act on.

[Phase 0]

## Phase 1 — Find candidates (3 correctness angles + 3 cleanup angles + 1 altitude angle + 1 conventions angle, up to 6 each)

Run **8 independent finder angles** via the Agent tool. Each
surfaces **up to 6 candidate findings** with `file`, `line`, a one-line
`summary`, and a concrete `failure_scenario`.

[Angles A, B, C, Reuse, Simplification, Efficiency, Altitude, Conventions]
[Cleanup precedence note]
Pass every candidate with a nameable failure scenario through — finders that
silently drop half-believed candidates bypass the verify step and are the
dominant cause of misses.

[Phase 2 — Verify (1-vote, 3-state)]
[Output, cap 8]

---

## HIGH effort (assembled — the default)

`high effort → 3+5 angles × 6 candidates → 1-vote verify (recall-biased) → ≤10 findings`

You are reviewing for **recall** at high effort: catch every real bug a careful
reviewer would catch in one sitting. At this level, catching real bugs matters
more than avoiding false positives. Err on the side of surfacing.

[Phase 0]

## Phase 1 — Find candidates (3 correctness angles + 3 cleanup angles + 1 altitude angle + 1 conventions angle, up to 6 each)

Run **8 independent finder angles** via the Agent tool. Each
surfaces **up to 6 candidate findings** with `file`, `line`, a one-line
`summary`, and a concrete `failure_scenario`.

[Angles A, B, C, Reuse, Simplification, Efficiency, Altitude, Conventions]
[Cleanup precedence note]
Pass every candidate with a nameable failure scenario through — finders that
silently drop half-believed candidates bypass the verify step and are the
dominant cause of misses.

[Phase 2 — Verify (1-vote, recall-biased)]
[Output, cap 10]

---

## XHIGH / MAX effort (assembled; identical text except "extra-high"/"maximum")

`xhigh effort → 5+5 angles × 8 candidates → 1-vote verify → sweep → ≤15 findings`

You are reviewing for **recall** at extra-high effort: catch every real bug. At
this level, catching real bugs matters more than avoiding false positives — a
missed bug ships. Err on the side of surfacing.

[Phase 0]

## Phase 1 — Find candidates (5 correctness angles + 3 cleanup angles + 1 altitude angle + 1 conventions angle, up to 8 each)

Run **10 independent finder angles** via the Agent tool. Each
surfaces **up to 8 candidate findings**. Do NOT let one angle's conclusions
suppress another's — if two angles flag the same line for different reasons,
record both.

[Angles A, B, C, D, E, Reuse, Simplification, Efficiency, Altitude, Conventions]
[Cleanup precedence note]
[Phase 2 — Verify (1-vote, 3-state)]
This is recall mode — a single non-REFUTED vote carries the finding. Do NOT
drop on uncertainty.

[Phase 3 — Sweep for gaps]
[Output, cap 15]

---

## Single-pass fallback (any tier medium+, when the subagent tool is unavailable)

`<tier> effort → Agent tool unavailable → single-pass inline → ≤<cap> findings`

[Tier lead-in paragraph]

The Agent tool isn't available in this context, so the usual
multi-agent fan-out and subagent verify pass can't run. Work through every
angle below yourself, in this same context, in one pass — do not skip angles
for lack of fan-out. Re-check each candidate against the diff before keeping
it; drop anything you can't back up with a concrete failure scenario.

[Phase 0]

## Phase 1 — Find candidates (<n> angles, single pass)

Work through **<n> angles** yourself, in sequence, in this same
context — do not spawn subagents. Each surfaces candidate findings with
`file`, `line`, a one-line `summary`, and a concrete `failure_scenario`.

[Angle list for the tier]
[Cleanup precedence note]

## Phase 2 — Dedup and self-check (no subagent verify)

Dedup near-duplicates (same defect, same location, same reason → keep one).
Re-check each remaining candidate yourself against the diff before keeping it.

[xhigh/max only:]
## Phase 3 — Sweep for gaps

Take one more pass yourself (same context, no subagent) as a fresh reviewer
who has the deduplicated list. Re-read the diff and enclosing functions
looking ONLY for defects not already listed: [sweep gap-focus list]

[Output for the tier]

State clearly in your summary that this was a single-pass review done without
the Agent tool, not the full multi-agent fan-out, so whoever reads
it isn't misled about what actually ran.

---

## Workflow-backed variant (high/xhigh/max when workflows enabled)

Meta: "Workflow-backed code review — one finder per correctness angle plus one
finder covering all cleanup angles, an independent verifier for every distinct
(file, line) location across the pooled candidates, then a ranked, capped
findings report."

Phases: Scope → Find (barrier) → group-by-location → Verify → Sweep (xhigh/max)
→ Synthesize. Params: high = 3 correctness angles × 6, ≤10 findings, no sweep;
xhigh/max = 5 × 8, ≤15 findings, sweep (≤8 extra candidates).

Key agent prompts (verbatim fragments; SCOPE_BLOCK = diff command, changed
files, applicable CLAUDE.md files, change summary, conventions, plus the
user's verbatim review target framed as scope-only data):

**Scope agent:** "Establish the scope of a code review. … 1. Determine the
exact diff command(s) for the review and run them to confirm they produce a
non-empty diff. 2. List the changed files. 3. Summarize what changed in one
paragraph. 4. List the CLAUDE.md files that apply to the changed files … Read
each one that exists and note conventions a reviewer should know."

**Finder:** "## Code-review finder — <angle label> … Run the diff command
above and review ONLY through the lens of your assigned angle: <angle text> …
Surface up to <cap> candidate findings, each with file, line, a one-line
summary, and a concrete failure_scenario — the user-visible consequence
(error, wrong output, data loss), not an intermediate state (value stale, set
grows). Pass every candidate with a nameable failure scenario through — do not
silently drop half-believed candidates; an independent verifier judges them
next. If nothing qualifies, return an empty list."
(The cleanup finder is one agent covering all cleanup lenses: "Cover whichever
lenses apply — you do not need findings from every lens; prioritize the
highest-cost issues across all of them.")

**Verifier (one per distinct file:line, all candidates at that location):**
"## Code-review verifier … ## Candidate findings at <loc> … Run the diff
command above, read the relevant file(s), and return one verdict per
candidate. Judge EACH candidate independently on its own claim — candidates at
the same location may describe distinct issues, the same issue, or a mix. …
[Verdict ladder] [Recall-biased verdict rules] … Evidence must quote or cite
the relevant line(s)."

**Sweep (xhigh/max):** "## Code-review sweep — gaps only … ## Already-found
candidates (do NOT re-derive or re-confirm these) <list> … Re-read the diff
and the enclosing functions looking ONLY for defects not already listed. Focus
on what the first pass tends to miss: [gap-focus list] … Surface up to 8
additional candidates. If nothing new, return an empty list — do not pad."

**Synthesizer:** "## Synthesis: final code-review report … Return decisions
about findings BY INDEX — never re-emit finding text. 1. For each distinct
defect, emit one decision with its index. When several findings describe the
same defect (same root cause), keep one entry and list the others in its merge
array. 2. Order decisions most-severe first. Correctness bugs always outrank
cleanup findings. 3. Keep at most <cap> decisions; omit the least severe
beyond the cap. 4. Write a 2-3 sentence summary of the review."

Ranking: correctness outranks cleanup; CONFIRMED outranks PLAUSIBLE. The
assembler backfills unmerged verified findings up to the cap so nothing is
silently dropped while there is room, and reports refuted findings separately.

---

## Apply mode (when asked to fix, e.g. `/code-review` with apply)

"…apply the findings to the working tree instead of stopping at the report:
fix each one directly — correctness bugs and reuse/simplification/efficiency
cleanups alike. Skip any finding whose fix would change intended behavior,
require changes well outside the reviewed diff, or that you judge to be a
false positive — note the skip rather than arguing with it. … give one line
per skipped finding saying why."
