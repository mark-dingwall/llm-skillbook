#!/usr/bin/env bash
# Manual smoke test for the ordinary Codex containment mapping
# (review_loop.execution). See ordinary-codex-smoke.md for what each mode
# proves and why it is manual (real Bubblewrap, real Codex CLI, optionally a
# real network call) rather than part of the automated suite.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REVIEW_LOOP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REVIEW_LOOP_ROOT"

usage() {
  cat <<'EOF'
Usage: ordinary-codex-smoke.sh --preflight | --live

  --preflight  No Codex credentials required. Proves: the real codex CLI
               (real node + real codex.js) starts inside the declared
               Bubblewrap namespace; injected host secrets are invisible to
               a contained process; a contained process cannot write a
               read-only target; it can write only report/scratch.

  --live       Requires valid Codex credentials ($CODEX_HOME/auth.json or
               ~/.codex/auth.json). Sends one minimal review fixture through
               the real mapping and requires exactly one valid report. Makes
               a real network call to the model provider. If credentials are
               absent, records NOT RUN and exits 0 (never weakens the
               deterministic preflight checks above).
EOF
}

MODE=""
case "${1:-}" in
  --preflight) MODE="preflight" ;;
  --live) MODE="live" ;;
  -h|--help) usage; exit 0 ;;
  *) usage; exit 2 ;;
esac

if ! command -v bwrap >/dev/null 2>&1; then
  echo "SKIP: bwrap is not installed; contained dispatch is unavailable" >&2
  exit 0
fi
if ! command -v codex >/dev/null 2>&1; then
  echo "SKIP: codex CLI is not installed" >&2
  exit 0
fi

python3 "$SCRIPT_DIR/ordinary_codex_smoke.py" "--$MODE"
