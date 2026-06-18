# agy reviewer manual smoke

## Setup
- `agy --version` ≥ 1.0.9
- `which agy` resolves to `~/.local/bin/agy` or wherever it's installed

## Procedure
1. From this repo root:
   ```bash
   uv run python -m multi_review.cli.spawn --cli agy --prompt-file <(echo "Review this file:
   $(cat README.md | head -50)
   Are there any bugs?") --out-dir /tmp/agy-smoke --timeout 120
   ```
2. Wait for completion.
3. Check `/tmp/agy-smoke/REVIEW.md` exists, ≥50 bytes, plain prose review.
4. Check `/tmp/agy-smoke/state.json` — `ok: true`, `usage.input_tokens` and friends all 0 (expected — agy --print has no telemetry).
5. With `--model` override:
   ```bash
   uv run python -m multi_review.cli.spawn --cli agy --model "Gemini 3.5 Flash (Low)" ...
   ```
   Confirm faster + smaller output.

## Pass criteria
- rc 0
- REVIEW.md plausible
- state.json valid JSON with `ok: true`
- No crashes from empty stream_flags

## Failure modes seen
- agy refusing to read `/proc/...` etc. — use real cwd files.
- `--print-timeout 5m0s` default; our default `--timeout None` overrides.
