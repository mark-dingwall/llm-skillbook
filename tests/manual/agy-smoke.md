# agy reviewer manual smoke

## Setup
- `agy --version` — verified against 1.0.16, 1.1.1 and 1.1.10
- `which agy` resolves to `~/.local/bin/agy` or wherever it's installed

## Invocation shape

`build_command` emits `agy --print <prompt-file instruction> --dangerously-skip-permissions [--model X]`.
Two rules make that ordering load-bearing:

- Headless agy denies every permission-gated tool call, including reading its own
  prompt file, so without the bypass flag the review is always empty.
- `--print` consumes the next argv token as its prompt, whatever it is. A flag
  placed directly after `--print` is silently used as the prompt instead.

If a run returns no review, check argv order before suspecting the model.

## Procedure
1. From this repo root:
   ```bash
   uv run python -m multi_review.cli.spawn --cli agy --prompt-file <(echo "Review this file:
   $(cat README.md | head -50)
   Are there any bugs?") --out-dir /tmp/agy-smoke --timeout 120
   ```
2. Wait for completion.
3. Check `/tmp/agy-smoke/agy.md` exists, ≥50 bytes, plain prose review.
4. Check `/tmp/agy-smoke/agy.state.json` — `ok: true`, `usage.input_tokens` and friends all 0 (expected — agy --print has no telemetry).
5. With `--model` override:
   ```bash
   uv run python -m multi_review.cli.spawn --cli agy --model "Gemini 3.5 Flash (Low)" ...
   ```
   Confirm faster + smaller output.

## Pass criteria
- rc 0
- agy.md plausible
- agy.state.json valid JSON with `ok: true`
- No crashes from empty stream_flags

## Failure modes seen
- agy refusing to read `/proc/...` etc. — use real cwd files.
- An unset multi-review `--timeout` does not pass or override an agy timeout flag.
- Empty output + a permission-denial line on stderr — the bypass flag is missing or landed immediately after `--print` (see Invocation shape).
