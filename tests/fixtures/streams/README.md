# Adapter JSONL fixtures

Captured upstream-CLI JSONL output used to test ProgressAdapter parsers without network calls.

## Capture commands

```bash
# claude
claude -p --output-format=stream-json --include-partial-messages 'echo "hello world"' \
  > tests/fixtures/streams/claude/success.jsonl

# gemini
gemini --output-format json 'echo "hello world"' \
  > tests/fixtures/streams/gemini/success.jsonl

# codex (verify --jsonl flag for current build)
codex exec --json 'echo "hello world"' \
  > tests/fixtures/streams/codex/success.jsonl

# opencode
opencode run --output stream-json 'echo "hello world"' \
  > tests/fixtures/streams/opencode/success.jsonl
```

## Synthetic fixtures

`gemini/capacity_429.jsonl` and `claude/empty.jsonl` are hand-written; both reproduce
known failure modes.

Re-capture on every release prep to catch upstream schema drift.
