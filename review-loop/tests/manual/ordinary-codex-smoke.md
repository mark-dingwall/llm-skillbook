# Ordinary Codex containment smoke test

Manual, not part of `python3 -m unittest discover`. It exists because the
automated suite deliberately substitutes `tests/integration/fixtures/
fake_reviewer.py` for `node <codex.js>` inside the real Bubblewrap mapping
(`review_loop.execution.build_codex_call`) -- that proves the *mapping* is
safe without a network call or real Codex credentials, but it never proves
the *actual* Codex CLI binary starts under that same mapping. This script
closes that gap, and optionally exercises one real review call end to end.

## `--preflight` (no credentials required)

```
cd review-loop && ./tests/manual/ordinary-codex-smoke.sh --preflight
```

Uses a throwaway placeholder `auth.json` (never the operator's real
`~/.codex/auth.json`) so the mapping mounts and Codex starts, but proves:

1. `resolve_codex_host_paths()` finds `bwrap`, `node`, the installed Codex
   package, and (the placeholder) auth file.
2. The contained `codex exec --help` probe passes and has every required
   flag (`preflight_codex_mapping`).
3. **The real `node` + real `codex.js` actually start** inside the declared
   Bubblewrap namespace. Codex cannot complete a review without real
   credentials -- it is expected to fail with a 401/auth error reaching the
   provider -- but the script asserts stderr shows a *Codex-specific*
   failure (an HTTP/auth error), never a loader/exec failure
   (`execvp`, `No such file or directory`, `cannot execute binary file`).
   A loader failure would mean the merged-usr `/lib64` symlink mapping (or
   the resolved package/runtime paths) is broken.
4. Reusing the exact same mapping-construction function with
   `fake_reviewer.py` standing in for `node`/`codex.js` (identical to the
   automated containment suite): an injected host secret is invisible
   inside the sandbox, a read-only target file cannot be written, and
   `/scratch`+`/report` remain writable.

Why (3) and (4) are split: the real, uncredentialed Codex process never
gets a model turn, so it never itself attempts a target write or a
credential read for the script to observe -- the model orchestrates all
sandboxed filesystem access, and no local sandboxed action happens without
a successful API turn. Read/write/secret containment is therefore proven
mechanically (mapping-level, via the substitutable-binary trick), and the
*separate* real-binary-startup proof is proven with the real binary. Both
are needed; neither alone is sufficient.

## `--live` (requires valid Codex credentials; makes a real network call)

```
cd review-loop && ./tests/manual/ordinary-codex-smoke.sh --live
```

Sends one minimal, fixed review fixture (a two-line `fixture.py`, a
one-sentence prompt) through the real mapping using whatever credentials are
at `$CODEX_HOME/auth.json` or `~/.codex/auth.json`, and requires exactly one
valid, non-empty `report.md`. **Costs real API usage** -- run deliberately,
not in CI, not on a loop.

If no credentials are present, the script prints `NOT RUN: no credentials
at <path>` and exits 0. A missing credential is recorded as `NOT RUN`, never
folded into or used to weaken the `--preflight` (deterministic, credential-
free) result.

## Interpreting output

Each check line is `[PASS|FAIL|NOT RUN] <name> -- <detail>`, followed by an
`N/M checks passed` summary. Any `FAIL` is a real regression in the mapping
or the installed Codex/Bubblewrap toolchain, not a flaky external
dependency -- investigate before dismissing it.
