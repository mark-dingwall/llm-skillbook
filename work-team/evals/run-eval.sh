#!/usr/bin/env bash
# Run one scenario on one harness; capture transcript artefacts.
# usage: run-eval.sh <red|green|refactor> <A|B|C> <claude|codex> [attempt-N]
set -euo pipefail
PHASE=$1 SCEN=$2 HARNESS=$3 ATTEMPT=${4:-attempt-1}
HERE=$(cd "$(dirname "$0")" && pwd)
TS=${EVAL_TS:-$(date -u +%Y%m%dT%H%M%SZ)}
OUT="$HERE/transcripts/$PHASE/$TS/Scenario-$SCEN-$HARNESS/$ATTEMPT"
WS=${EVAL_WS:-${CLAUDE_JOB_DIR:-/tmp}/tmp/evals}/$PHASE-$TS-$SCEN-$HARNESS-$ATTEMPT
mkdir -p "$OUT" "$WS"

case $SCEN in
  A) FIX="" ;;
  B) cp -r "$HERE/fixtures/audit-target" "$WS/"; FIX="$WS/audit-target" ;;
  C) cp -r "$HERE/fixtures/run-dir" "$WS/"; FIX="$WS/run-dir" ;;
esac

# Extract the scenario body (after the heading, up to the next "## ").
BODY=$(awk -v s="## Scenario $SCEN" '$0 ~ "^"s {p=1; next} /^## /{p=0} p' "$HERE/scenarios.md" \
  | sed -e "s|<FIXTURE>|$FIX|g" -e '/^Fixture:/d' -e '/^Fresh empty directory/d')
PREFIX=""
[ "$PHASE" != red ] && PREFIX=$'Use the work-team skill for the task below. Before dispatching, state the skill name and the resolved SKILL.md path you loaded.\n\n'
PROMPT="$PREFIX$BODY"
printf '%s\n' "$PROMPT" > "$OUT/prompt.txt"

START=$(date -u +%FT%TZ)
case $HARNESS in
  claude)
    CMD="claude --model sonnet --output-format stream-json --verbose --allowedTools Agent,Read,Write,Edit,Bash,Glob,Grep -p <prompt>"
    (cd "$WS" && claude --model sonnet --output-format stream-json --verbose \
      --allowedTools "Agent,Read,Write,Edit,Bash,Glob,Grep" -p "$PROMPT" \
      > "$OUT/stdout.jsonl" 2> "$OUT/stderr.txt") && EXIT=0 || EXIT=$?
    jq -r 'select(.type=="result") | .result' "$OUT/stdout.jsonl" > "$OUT/final-response.md" || true
    ;;
  codex)
    CMD="codex exec --json --enable multi_agent --skip-git-repo-check -C $WS -m gpt-5.6-terra -c model_reasoning_effort=\"medium\" -s workspace-write - </dev/null"
    (codex exec --json --enable multi_agent --skip-git-repo-check -C "$WS" \
      -m gpt-5.6-terra -c model_reasoning_effort='"medium"' -s workspace-write "$PROMPT" \
      < /dev/null > "$OUT/stdout.jsonl" 2> "$OUT/stderr.txt") && EXIT=0 || EXIT=$?
    jq -r 'select(.type=="item.completed" and .item.type=="agent_message") | .item.text' "$OUT/stdout.jsonl" \
      | tail -n 60 > "$OUT/final-response.md" || true
    ;;
esac
END=$(date -u +%FT%TZ)

# Keep produced logs and any work-team run directory, not the whole workspace.
[ -d "$WS/.work-team" ] && cp -r "$WS/.work-team" "$OUT/run-artefacts"
find "$WS" -path "$WS/.work-team" -prune -o -name workflow-log.jsonl -print 2>/dev/null \
  | while read -r f; do cp "$f" "$OUT/$(echo "${f#$WS/}" | tr / _)"; done
(cd "$WS" && find . -type f -not -path '*/node_modules/*' -not -path '*/.venv/*' | sort) > "$OUT/workspace-files.txt"
printf 'command=%s\nworkspace=%s\nharness=%s\nphase=%s\nscenario=%s\nstart=%s\nend=%s\nexit=%s\n' \
  "$CMD" "$WS" "$HARNESS" "$PHASE" "$SCEN" "$START" "$END" "$EXIT" > "$OUT/metadata.txt"
(cd "$OUT" && sha256sum prompt.txt stdout.jsonl metadata.txt > attempt.sha256)
echo "$OUT exit=$EXIT"
