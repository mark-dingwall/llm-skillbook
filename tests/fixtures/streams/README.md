# Adapter JSONL fixtures

Captured upstream-CLI JSONL output used to test ProgressAdapter parsers without network calls.

## Capture commands

Verified working as of 2026-05-19. Cross-check against `CLI_SPEC` in `multi_review.py`
when re-capturing — upstream flags drift.

```bash
# claude (sanitize after — see Sanitization note below)
claude -p --output-format=stream-json --include-partial-messages 'echo "hello world"' \
  > tests/fixtures/streams/claude/success.jsonl

# gemini
gemini -p "" -o stream-json -m gemini-3.1-pro-preview 'echo "hello world"' \
  > tests/fixtures/streams/gemini/success.jsonl

# codex
codex exec --skip-git-repo-check --json - <<<'echo "hello world"' \
  > tests/fixtures/streams/codex/success.jsonl

# opencode
opencode run --format json - <<<'echo "hello world"' \
  > tests/fixtures/streams/opencode/success.jsonl
```

## Sanitization

The `claude -p` capture inlines hook outputs, full plugin/skill/agent inventories,
absolute `cwd`, and session UUIDs. Before committing:

- Drop `hook_started` / `hook_response` events (not consumed by `ClaudeAdapter`).
- Replace `cwd` with `/path/to/repo`.
- Trim `tools`/`slash_commands`/`agents`/`skills`/`plugins` arrays to 2-3 placeholder entries.
- Replace session_id / UUIDs / request_ids with `session-xxxxx` / `uuid-yyyyy` / `req_zzzzz`.

Preserved fields the adapter reads (see `multi_review.py` adapter classes):
`type`, `subtype`, `event.type`, `event.delta.type`/`text`, `event.content_block.type`/`name`,
`message.usage.{input_tokens,output_tokens,cache_read_input_tokens}`,
`message.content[].{type,text}`, `result` (string on the `result` event).

## Synthetic fixtures

`gemini/capacity_429.jsonl` and `claude/empty.jsonl` are hand-written; both reproduce
known failure modes.

Re-capture on every release prep to catch upstream schema drift.
