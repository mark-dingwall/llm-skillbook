#!/usr/bin/env bash

# Reproducible live acceptance gate for multi_review.py.
#
# Secret inputs are file parameters, never argv values:
#   CLAUDE_TOKEN_FILE     raw token from `claude setup-token`, mode 0600
#   PYKRETE_ENV_FILE      one NANOGPT_API_KEY=... assignment, mode 0600
#   PYKRETE_CONFIG_FILE   normal non-secret pykrete.toml
#
# Set KEEP_SMOKE_ARTIFACTS=1 to retain the temporary evidence directory. Scratch
# shutdown homes are always removed because a CLI may persist refreshed auth.
# Single-quoted child-shell snippets intentionally expand only after entering
# their credential-reading process or sandbox.
# shellcheck disable=SC2016

set +x
set -Eeuo pipefail

shutdown_clis=(claude agy codex opencode pykrete grok)
if [[ -z ${1:-} || ${1:-} == --prereq-check || ${1:-} == --workload-path-check ]]; then
  missing_harness_commands=""
  for harness_command in awk chmod cp dirname env find getent git id ln mkdir mktemp ps \
    readlink rg rm setsid sleep sort stat wc; do
    command -v "$harness_command" >/dev/null 2>&1 || \
      missing_harness_commands="${missing_harness_commands:+$missing_harness_commands,}$harness_command"
  done
  if [[ -n "$missing_harness_commands" ]]; then
    for shutdown_cli in "${shutdown_clis[@]}"; do
      printf 'shutdown_%s=BLOCKED scopes=plain,bwrap missing_harness_commands=%s\n' \
        "$shutdown_cli" "$missing_harness_commands"
    done
    printf 'headless-driver-smoke: shutdown matrix has BLOCKED prerequisites\n' >&2
    exit 1
  fi
fi

script_path=$(readlink -f "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_path")
# multi-review/ is not always its own Git repository (e.g. nested inside a
# monorepo worktree), so `git -C "$script_dir" rev-parse --show-toplevel`
# can resolve to an ENCLOSING repo root instead of this directory -- every
# use of $repo_root below expects multi-review/ itself (multi_review.py,
# pyproject.toml). Derive it from the script's own fixed location instead.
repo_root=$(cd "$script_dir/../.." && pwd)
fixture_dir="$script_dir/fixtures/headless-driver-smoke"

die() {
  printf 'headless-driver-smoke: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

resolve_executable() {
  local override=$1
  local command_name=$2
  local label=$3
  local candidate
  if [[ -n "$override" ]]; then
    candidate=$override
  else
    require_command "$command_name"
    candidate=$(command -v "$command_name")
  fi
  candidate=$(readlink -f -- "$candidate") || die "cannot resolve $label: $candidate"
  [[ -f "$candidate" && -x "$candidate" ]] || die "$label is not an executable file: $candidate"
  printf '%s\n' "$candidate"
}

resolve_entry() {
  local override=$1
  local command_name=$2
  local label=$3
  local candidate
  if [[ -n "$override" ]]; then
    candidate=$override
  else
    require_command "$command_name"
    candidate=$(command -v "$command_name")
  fi
  candidate=$(readlink -f -- "$candidate") || die "cannot resolve $label: $candidate"
  [[ -f "$candidate" && -x "$candidate" ]] || die "$label is not an executable file: $candidate"
  printf '%s\n' "$candidate"
}

shutdown_subject_path() {
  case "$1" in
    plain) printf '%s\n' "$fixture_dir/subject.py" ;;
    bwrap) printf '%s\n' /workspace/tests/manual/fixtures/headless-driver-smoke/subject.py ;;
    *) die "unknown shutdown scope: $1" ;;
  esac
}

shutdown_patterns() {
  local cli=$1
  local scope=$2
  case "$cli:$scope" in
    claude:plain|claude:bwrap) printf '%s\n' 'claude -p' '' ;;
    agy:plain|agy:bwrap) printf '%s\n' 'agy --print' '' ;;
    codex:plain|codex:bwrap) printf '%s\n' 'node .*codex' 'codex.*exec' ;;
    opencode:plain) printf '%s\n' 'node .*/opencode' 'opencode.*run' ;;
    opencode:bwrap) printf '%s\n' 'node .*opencode' 'opencode.*run' ;;
    pykrete:plain) printf '%s\n' 'node .*/pykrete( |$)' 'node .*/pi( |$)' ;;
    pykrete:bwrap) printf '%s\n' 'node /opt/bin/pykrete( |$)' 'node /opt/bin/pi( |$)' ;;
    grok:plain|grok:bwrap) printf '%s\n' 'grok --sandbox workspace' '' ;;
  esac
}

run_self_check() {
  local uv_binary patterns=()
  [[ -x "$script_path" ]] || die "harness is not executable: $script_path"
  bash -n "$script_path"
  uv_binary=$(resolve_executable "${UV_BIN:-}" uv "uv executable")
  "$uv_binary" run --project "$repo_root" python - \
    "$fixture_dir" "$(shutdown_subject_path plain)" "$(shutdown_subject_path bwrap)" \
    "${shutdown_clis[@]}" <<'PY'
from pathlib import Path
import sys

from multi_review.core.prompt import build_prompt
from multi_review.core.promptfile import load_promptfile
from multi_review.core.reviewers import ALL_REVIEWERS

root = Path(sys.argv[1])
host_subject = Path(sys.argv[2])
sandbox_subject = sys.argv[3]
assert sys.argv[4:] == ALL_REVIEWERS, "shutdown matrix does not cover every advertised CLI"
subject = root / "subject.py"
required = [subject, root / "reference.yaml", root / "shutdown.yaml"]
assert all(path.is_file() for path in required), "checked-in smoke fixture missing"
assert host_subject == subject.resolve() and host_subject.is_file()
assert sandbox_subject == "/workspace/tests/manual/fixtures/headless-driver-smoke/subject.py"

reference = load_promptfile(root / "reference.yaml")
shutdown = load_promptfile(root / "shutdown.yaml")
assert reference.reviewers == ["claude"]
assert shutdown.reviewers == ["pykrete"] and shutdown.synthesizer == "none"

reference_prompt = build_prompt(
    task=reference.task,
    files=[subject],
    custom_prompt=reference.custom_prompt,
    nonce="staticcheck",
)
assert "REFERENCE_TOOL_READ_20260807" not in reference_prompt
assert str(subject.resolve()) in reference_prompt
PY
  mapfile -t patterns < <(shutdown_patterns claude bwrap)
  [[ ${patterns[0]} == 'claude -p' ]] || die "Claude bwrap process pattern does not match argv"
  mapfile -t patterns < <(shutdown_patterns agy bwrap)
  [[ ${patterns[0]} == 'agy --print' ]] || die "agy bwrap process pattern does not match argv"
  mapfile -t patterns < <(shutdown_patterns grok bwrap)
  [[ ${patterns[0]} == 'grok --sandbox workspace' ]] || \
    die "Grok bwrap process pattern does not match argv"
  mapfile -t patterns < <(shutdown_patterns codex plain)
  [[ ${patterns[0]} == 'node .*codex' ]] || die "Codex process pattern does not match launcher argv"
  printf 'shutdown_prompt_paths=PASS\n'
  printf 'shutdown_process_patterns=PASS\n'
  printf 'codex_process_pattern=%s\n' "${patterns[0]}"
  printf 'headless_driver_smoke_check=PASS\n'
}

usage() {
  cat <<'EOF'
Usage:
  tests/manual/headless-driver-smoke.sh --check
  tests/manual/headless-driver-smoke.sh --prereq-check
  CLAUDE_TOKEN_FILE=/secure/token \
  PYKRETE_ENV_FILE=/secure/pykrete.env \
  PYKRETE_CONFIG_FILE=/path/to/pykrete.toml \
    tests/manual/headless-driver-smoke.sh

Optional environment:
  KEEP_SMOKE_ARTIFACTS=1  retain the temporary evidence directory
  UV_CACHE_SOURCE=...     source cache copied into the sandbox scratch tree
  CLAUDE_BIN=...          explicit Claude Code executable
  UV_BIN=...              explicit uv executable
  AGY_BIN=...             explicit Antigravity CLI executable
  CODEX_ENTRY=...         explicit Codex entry script
  OPENCODE_ENTRY=...      explicit OpenCode entry script
  PYKRETE_ENTRY=...       explicit pykrete entry script
  PI_ENTRY=...            explicit pi entry script
  GROK_BIN=...            explicit Grok executable
  AGY_TOKEN_FILE=...      Antigravity OAuth token (default: ~/.gemini/...)
  CODEX_AUTH_FILE=...     Codex auth.json (default: ~/.codex/auth.json)
  OPENCODE_AUTH_FILE=...  OpenCode auth.json (default: ~/.local/share/...)
  OPENCODE_MODEL_FILE=... OpenCode model selection state (optional)
  GROK_AUTH_FILE=...      Grok auth.json (default: ~/.grok/auth.json)
EOF
}

collect_descendants() {
  local pending=$1
  local found=""
  local next parent children child
  while [[ -n "$pending" ]]; do
    next=""
    for parent in $pending; do
      children=$(ps -eo pid=,ppid= | awk -v p="$parent" '$2 == p {print $1}')
      for child in $children; do
        found="$found $child"
        next="$next $child"
      done
    done
    pending=$next
  done
  printf '%s\n' "$found"
}

snapshot_tree() {
  local root_pid=$1
  local destination=$2
  local pid
  : > "$destination"
  for pid in $(collect_descendants "$root_pid"); do
    ps -p "$pid" -o pid=,ppid=,stat=,args= >> "$destination" 2>/dev/null || true
  done
}

snapshot_has_distinct_patterns() {
  local snapshot=$1
  local first_pattern=$2
  local second_pattern=${3:-}
  local first_pids second_pids first_pid second_pid
  first_pids=$(rg "$first_pattern" "$snapshot" | awk '{print $1}' | sort -u) || return 1
  [[ -n "$first_pids" ]] || return 1
  [[ -n "$second_pattern" ]] || return 0
  second_pids=$(rg "$second_pattern" "$snapshot" | awk '{print $1}' | sort -u) || return 1
  [[ -n "$second_pids" ]] || return 1
  for first_pid in $first_pids; do
    for second_pid in $second_pids; do
      snapshot_pid_is_descendant "$snapshot" "$second_pid" "$first_pid" && return 0
    done
  done
  return 1
}

snapshot_pid_is_descendant() {
  local snapshot=$1
  local pid=$2
  local ancestor=$3
  local parent=$pid
  local depth=0
  while ((depth < 100)); do
    parent=$(awk -v p="$parent" '$1 == p {print $2; exit}' "$snapshot")
    [[ -n "$parent" && "$parent" != 0 ]] || return 1
    [[ "$parent" == "$ancestor" ]] && return 0
    ((depth += 1))
  done
  return 1
}

wait_for_tree_patterns() {
  local root_pid=$1
  local snapshot=$2
  local first_pattern=$3
  local second_pattern=${4:-}
  local attempt
  local attempts=${PATTERN_WAIT_ATTEMPTS:-1200}
  for ((attempt = 0; attempt < attempts; attempt++)); do
    snapshot_tree "$root_pid" "$snapshot"
    if snapshot_has_distinct_patterns "$snapshot" "$first_pattern" "$second_pattern"; then
      return 0
    fi
    kill -0 "$root_pid" 2>/dev/null || return 1
    sleep 0.05
  done
  return 1
}

process_group_survivors() {
  local pgid=$1
  ps -eo pid=,pgid=,stat= | awk -v p="$pgid" '$2 == p && $3 !~ /^Z/ {print $1}'
}

assert_process_group_gone() {
  local pgid=$1
  local label=$2
  local survivors
  survivors=$(process_group_survivors "$pgid")
  [[ -z "$survivors" ]] || die "$label left process-group PIDs alive: $survivors"
}

validate_and_report_shutdown() {
  local scope=$1
  local cli=$2
  local rc=$3
  local case_out=$4
  local stderr_log=$5
  local captured=$6
  local survivor_count=$7
  local cleanup_result=$8
  [[ ! -e "$case_out/REVIEW.md" ]] || die "$scope $cli shutdown wrote REVIEW.md"
  ! rg -q 'Traceback \(most recent call last\)' "$stderr_log" || \
    die "$scope $cli shutdown emitted a traceback"
  [[ "$cleanup_result" == gone ]] || die "$scope $cli cleanup result was $cleanup_result"
  case "$scope" in
    plain)
      [[ "$rc" == 1 ]] || die "plain $cli driver exited $rc, expected 1"
      printf 'shutdown_%s_plain=PASS driver_rc=%s captured=%s post_driver_survivors=%s harness_cleanup=%s environment=clean process_group_check=passed\n' \
        "$cli" "$rc" "$captured" "$survivor_count" "$cleanup_result"
      ;;
    bwrap)
      [[ "$rc" == 143 ]] || die "bwrap $cli wrapper exited $rc, expected 143"
      printf 'shutdown_%s_bwrap=PASS wrapper_rc=%s captured=%s post_wrapper_survivors=%s harness_cleanup=%s environment=clean process_group_check=passed\n' \
        "$cli" "$rc" "$captured" "$survivor_count" "$cleanup_result"
      ;;
    *) die "unknown shutdown result scope: $scope" ;;
  esac
}

build_plain_workload_path() {
  local destination=$1
  mkdir -p "$destination"
  ln -s -- "$claude_binary" "$destination/claude"
  ln -s -- "$agy_binary" "$destination/agy"
  ln -s -- "$codex_entry" "$destination/codex"
  ln -s -- "$opencode_entry" "$destination/opencode"
  ln -s -- "$pykrete_entry" "$destination/pykrete"
  ln -s -- "$pi_entry" "$destination/pi"
  ln -s -- "$grok_binary" "$destination/grok"
}

smoke_root=""
plain_workload_bin=""
active_plain_wrapper=""
active_plain_pgid=""
active_plain_snapshot=""
active_bwrap_wrapper=""
active_bwrap_pgid=""
active_bwrap_snapshot=""
scratch_secret_copies=()
scratch_auth_homes=()

scrub_scratch_secrets() {
  local path
  for path in "${scratch_secret_copies[@]}"; do
    [[ -n "$path" ]] && rm -f -- "$path"
  done
  for path in "${scratch_auth_homes[@]}"; do
    [[ -n "$path" ]] && rm -rf -- "$path"
  done
  scratch_secret_copies=()
  scratch_auth_homes=()
}

signal_group() {
  local signal_name=$1
  local pgid=$2
  if [[ -n "$pgid" ]] && kill -0 -- "-$pgid" 2>/dev/null; then
    kill "-$signal_name" -- "-$pgid" 2>/dev/null || true
  fi
}

signal_snapshot_reverse() {
  local signal_name=$1
  local snapshot=$2
  local pids=()
  local pid _
  [[ -n "$snapshot" && -f "$snapshot" ]] || return 0
  while read -r pid _; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < "$snapshot"
  local index
  for ((index = ${#pids[@]} - 1; index >= 0; index--)); do
    kill "-$signal_name" "${pids[index]}" 2>/dev/null || true
  done
}

cleanup() {
  local status=$?
  set +e
  signal_group TERM "$active_plain_pgid"
  signal_group TERM "$active_bwrap_pgid"
  signal_snapshot_reverse TERM "$active_plain_snapshot"
  signal_snapshot_reverse TERM "$active_bwrap_snapshot"
  sleep 0.2
  signal_group KILL "$active_plain_pgid"
  signal_group KILL "$active_bwrap_pgid"
  signal_snapshot_reverse KILL "$active_plain_snapshot"
  signal_snapshot_reverse KILL "$active_bwrap_snapshot"
  [[ -n "$active_plain_wrapper" ]] && wait "$active_plain_wrapper" 2>/dev/null || true
  [[ -n "$active_bwrap_wrapper" ]] && wait "$active_bwrap_wrapper" 2>/dev/null || true
  scrub_scratch_secrets
  if [[ -n "$smoke_root" ]]; then
    if [[ ${KEEP_SMOKE_ARTIFACTS:-0} == 1 ]]; then
      printf 'smoke_artifacts=%s\n' "$smoke_root"
    else
      rm -rf -- "$smoke_root"
    fi
  fi
  exit "$status"
}
trap cleanup EXIT

run_cleanup_check() {
  local snapshot=$1
  local attempt
  smoke_root=$(mktemp -d "${TMPDIR:-/tmp}/mr-headless-cleanup-check.XXXXXXXX")
  setsid /bin/bash -c '
    trap "" TERM
    /bin/bash -c '\''
      trap "" TERM
      /bin/sleep 600 &
      wait
    '\'' &
    wait
  ' >/dev/null 2>&1 &
  active_plain_wrapper=$!
  active_plain_pgid=$!
  active_plain_snapshot=$snapshot
  for ((attempt = 0; attempt < 100; attempt++)); do
    snapshot_tree "$active_plain_wrapper" "$snapshot"
    if [[ $(wc -l < "$snapshot") -ge 2 ]]; then
      die "intentional cleanup-check failure"
    fi
    sleep 0.02
  done
  die "cleanup-check could not observe fake child and grandchild"
}

run_mode=full
case "${1:-}" in
  --check)
    run_self_check
    exit 0
    ;;
  --help|-h)
    usage
    exit 0
    ;;
  --cleanup-check)
    [[ $# == 2 ]] || die "--cleanup-check requires a snapshot path"
    run_cleanup_check "$2"
    ;;
  --pattern-check)
    [[ $# == 5 ]] || die "--pattern-check requires root, snapshot, and two patterns"
    require_command awk
    require_command ps
    require_command rg
    wait_for_tree_patterns "$2" "$3" "$4" "$5" || \
      die "process patterns did not match launcher/descendant PIDs"
    matched_pids=$(rg "$4|$5" "$3" | awk '{print $1}' | sort -u | wc -l)
    printf 'matched_pids=%s\nprocess_patterns=PASS\n' "$matched_pids"
    exit 0
    ;;
  --process-group-check)
    [[ $# == 3 ]] || die "--process-group-check requires pgid and label"
    require_command ps
    assert_process_group_gone "$2" "$3"
    printf 'process_group=PASS\n'
    exit 0
    ;;
  --result-check)
    [[ $# == 9 ]] || die "--result-check requires scope, CLI, rc, out, stderr, captured, survivors, cleanup"
    require_command rg
    validate_and_report_shutdown "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9"
    exit 0
    ;;
  --prereq-check)
    run_mode=prereq
    ;;
  --workload-path-check)
    run_mode=workload
    ;;
  "") ;;
  *)
    usage >&2
    exit 2
    ;;
esac

require_command awk
require_command cp
require_command find
require_command git
require_command ps
require_command rg
require_command setsid
require_command stat

claude_token_file=${CLAUDE_TOKEN_FILE:-}
pykrete_env_file=${PYKRETE_ENV_FILE:-}
pykrete_config_file=${PYKRETE_CONFIG_FILE:-}
user_home=$(getent passwd "$(id -u)" | awk -F: '{print $6}')
uv_cache_source=${UV_CACHE_SOURCE:-"$user_home/.cache/uv"}
agy_token_file=${AGY_TOKEN_FILE:-"$user_home/.gemini/antigravity-cli/antigravity-oauth-token"}
codex_auth_file=${CODEX_AUTH_FILE:-"$user_home/.codex/auth.json"}
opencode_auth_file=${OPENCODE_AUTH_FILE:-"$user_home/.local/share/opencode/auth.json"}
opencode_model_file=${OPENCODE_MODEL_FILE:-"$user_home/.local/state/opencode/model.json"}
grok_auth_file=${GROK_AUTH_FILE:-"$user_home/.grok/auth.json"}

declare -A prereq_reasons=()
append_prereq() {
  local cli=$1
  local reason=$2
  prereq_reasons[$cli]="${prereq_reasons[$cli]:+${prereq_reasons[$cli]} }$reason"
}

is_regular_executable() {
  local candidate=$1
  local resolved
  [[ -f "$candidate" && -x "$candidate" ]] || return 1
  resolved=$(readlink -f -- "$candidate") || return 1
  [[ -f "$resolved" && -x "$resolved" ]]
}

is_regular_nonempty_file() {
  [[ -f "$1" && -s "$1" ]]
}

check_binary_prereq() {
  local cli=$1
  local override=$2
  local command_name=$3
  local label=$4
  local candidate
  if [[ -n "$override" ]]; then
    is_regular_executable "$override" || append_prereq "$cli" "missing_binary=$label:$override"
  else
    candidate=$(command -v "$command_name" 2>/dev/null || true)
    is_regular_executable "$candidate" || append_prereq "$cli" "missing_binary=$command_name"
  fi
}

check_entry_prereq() {
  local cli=$1
  local override=$2
  local command_name=$3
  local label=$4
  local candidate
  if [[ -n "$override" ]]; then
    is_regular_executable "$override" || \
      append_prereq "$cli" "missing_binary=$label:$override"
  else
    candidate=$(command -v "$command_name" 2>/dev/null || true)
    is_regular_executable "$candidate" || append_prereq "$cli" "missing_binary=$command_name"
  fi
}

check_secret_prereq() {
  local cli=$1
  local path=$2
  local label=$3
  is_regular_nonempty_file "$path" || return 0
  [[ $(stat -c '%a' "$path") == 600 ]] || \
    append_prereq "$cli" "invalid_auth_mode=$label:$path"
  [[ $(stat -c '%u' "$path") == "$(id -u)" ]] || \
    append_prereq "$cli" "invalid_auth_owner=$label:$path"
}

check_package_prereq() {
  local cli=$1
  local entry=$2
  local label=$3
  shift 3
  [[ -f "$entry" && -x "$entry" ]] || return 0
  local resolved root required
  resolved=$(readlink -f -- "$entry") || {
    append_prereq "$cli" "invalid_package_root=$label:$entry"
    return 0
  }
  root=$(dirname "$(dirname "$resolved")")
  for required in "$@"; do
    [[ -d "$root/$required" ]] || \
      append_prereq "$cli" "invalid_package_root=$label:$root/$required"
  done
}

for shutdown_cli in "${shutdown_clis[@]}"; do
  bwrap_prereq=$(command -v bwrap 2>/dev/null || true)
  is_regular_executable "$bwrap_prereq" || append_prereq "$shutdown_cli" missing_containment=bwrap
  if [[ -n ${UV_BIN:-} ]]; then
    is_regular_executable "${UV_BIN}" || append_prereq "$shutdown_cli" "missing_runner=uv:${UV_BIN}"
  else
    uv_prereq=$(command -v uv 2>/dev/null || true)
    is_regular_executable "$uv_prereq" || append_prereq "$shutdown_cli" missing_runner=uv
  fi
  [[ -d "$uv_cache_source" ]] || append_prereq "$shutdown_cli" "missing_cache=$uv_cache_source"
  [[ -f /mnt/wsl/resolv.conf ]] || \
    append_prereq "$shutdown_cli" missing_containment=/mnt/wsl/resolv.conf
done
check_binary_prereq claude "${CLAUDE_BIN:-}" claude claude
check_binary_prereq agy "${AGY_BIN:-}" agy agy
check_entry_prereq codex "${CODEX_ENTRY:-}" codex codex
check_entry_prereq opencode "${OPENCODE_ENTRY:-}" opencode opencode
check_entry_prereq pykrete "${PYKRETE_ENTRY:-}" pykrete pykrete
check_entry_prereq pykrete "${PI_ENTRY:-}" pi pi
check_binary_prereq grok "${GROK_BIN:-}" grok grok
if [[ -z "$claude_token_file" ]] || ! is_regular_nonempty_file "$claude_token_file"; then
  append_prereq claude "missing_auth=${claude_token_file:-CLAUDE_TOKEN_FILE}"
fi
is_regular_nonempty_file "$agy_token_file" || append_prereq agy "missing_auth=$agy_token_file"
is_regular_nonempty_file "$codex_auth_file" || append_prereq codex "missing_auth=$codex_auth_file"
is_regular_nonempty_file "$opencode_auth_file" || append_prereq opencode "missing_auth=$opencode_auth_file"
if [[ -z "$pykrete_env_file" ]] || ! is_regular_nonempty_file "$pykrete_env_file"; then
  append_prereq pykrete "missing_auth=${pykrete_env_file:-PYKRETE_ENV_FILE}"
fi
[[ -n "$pykrete_config_file" && -f "$pykrete_config_file" && -r "$pykrete_config_file" ]] || \
  append_prereq pykrete "missing_config=${pykrete_config_file:-PYKRETE_CONFIG_FILE}"
is_regular_nonempty_file "$grok_auth_file" || append_prereq grok "missing_auth=$grok_auth_file"
check_secret_prereq claude "$claude_token_file" CLAUDE_TOKEN_FILE
check_secret_prereq agy "$agy_token_file" AGY_TOKEN_FILE
check_secret_prereq codex "$codex_auth_file" CODEX_AUTH_FILE
check_secret_prereq opencode "$opencode_auth_file" OPENCODE_AUTH_FILE
check_secret_prereq pykrete "$pykrete_env_file" PYKRETE_ENV_FILE
check_secret_prereq grok "$grok_auth_file" GROK_AUTH_FILE
if is_regular_nonempty_file "$pykrete_env_file"; then
  pykrete_noncomment_lines=$(awk 'NF && $1 !~ /^#/ {count++} END {print count + 0}' "$pykrete_env_file")
  pykrete_key_lines=$(awk '/^NANOGPT_API_KEY=.+$/ {count++} END {print count + 0}' "$pykrete_env_file")
  [[ "$pykrete_noncomment_lines" == 1 && "$pykrete_key_lines" == 1 ]] || \
    append_prereq pykrete "invalid_auth_format=PYKRETE_ENV_FILE:$pykrete_env_file"
fi
codex_prereq_entry=${CODEX_ENTRY:-$(command -v codex 2>/dev/null || true)}
opencode_prereq_entry=${OPENCODE_ENTRY:-$(command -v opencode 2>/dev/null || true)}
pykrete_prereq_entry=${PYKRETE_ENTRY:-$(command -v pykrete 2>/dev/null || true)}
pi_prereq_entry=${PI_ENTRY:-$(command -v pi 2>/dev/null || true)}
check_package_prereq codex "$codex_prereq_entry" codex node_modules
check_package_prereq opencode "$opencode_prereq_entry" opencode node_modules
check_package_prereq pykrete "$pykrete_prereq_entry" pykrete src node_modules extensions
check_package_prereq pykrete "$pi_prereq_entry" pi node_modules

shutdown_prereq_blocked=0
for shutdown_cli in "${shutdown_clis[@]}"; do
  if [[ -n ${prereq_reasons[$shutdown_cli]:-} ]]; then
    printf 'shutdown_%s=BLOCKED scopes=plain,bwrap %s\n' \
      "$shutdown_cli" "${prereq_reasons[$shutdown_cli]}"
    shutdown_prereq_blocked=1
  fi
done
[[ "$shutdown_prereq_blocked" == 0 ]] || \
  die "shutdown matrix has BLOCKED prerequisites"

require_secret_file() {
  local path=$1
  local label=$2
  [[ -f "$path" ]] || die "$label is not a regular file: $path"
  [[ -s "$path" ]] || die "$label is empty: $path"
  [[ $(stat -c '%a' "$path") == 600 ]] || die "$label must have mode 0600: $path"
  [[ $(stat -c '%u' "$path") == "$(id -u)" ]] || die "$label must be owned by the current user: $path"
}

require_secret_file "$claude_token_file" "CLAUDE_TOKEN_FILE"
require_secret_file "$pykrete_env_file" "PYKRETE_ENV_FILE"
[[ -r "$pykrete_config_file" ]] || die "PYKRETE_CONFIG_FILE is not readable: $pykrete_config_file"

uv_binary=$(resolve_executable "${UV_BIN:-}" uv "uv executable")
claude_binary=$(resolve_executable "${CLAUDE_BIN:-}" claude "Claude executable")
agy_binary=$(resolve_executable "${AGY_BIN:-}" agy "agy executable")
codex_entry=$(resolve_entry "${CODEX_ENTRY:-}" codex "Codex entry")
opencode_entry=$(resolve_entry "${OPENCODE_ENTRY:-}" opencode "OpenCode entry")
pykrete_entry=$(resolve_entry "${PYKRETE_ENTRY:-}" pykrete "pykrete entry")
pi_entry=$(resolve_entry "${PI_ENTRY:-}" pi "pi entry")
grok_binary=$(resolve_executable "${GROK_BIN:-}" grok "Grok executable")
codex_root=$(dirname "$(dirname "$codex_entry")")
opencode_root=$(dirname "$(dirname "$opencode_entry")")
pykrete_root=$(dirname "$(dirname "$pykrete_entry")")
pi_package_root=$(dirname "$(dirname "$pi_entry")")

[[ -x "$uv_binary" ]] || die "uv executable is not executable: $uv_binary"
[[ -x "$claude_binary" ]] || die "Claude executable is not executable: $claude_binary"
[[ -x "$agy_binary" ]] || die "agy executable is not executable: $agy_binary"
[[ -f "$codex_entry" ]] || die "Codex entry is missing: $codex_entry"
[[ -f "$opencode_entry" ]] || die "OpenCode entry is missing: $opencode_entry"
[[ -f "$pykrete_entry" ]] || die "pykrete entry is missing: $pykrete_entry"
[[ -f "$pi_entry" ]] || die "pi entry is missing: $pi_entry"
[[ -x "$grok_binary" ]] || die "Grok executable is not executable: $grok_binary"
[[ -d "$codex_root/node_modules" ]] || die "cannot derive Codex package root from $codex_entry"
[[ -d "$opencode_root/node_modules" ]] || die "cannot derive OpenCode package root from $opencode_entry"
[[ -d "$pykrete_root/src" && -d "$pykrete_root/node_modules" ]] || \
  die "cannot derive pykrete source root from $pykrete_entry"
[[ -d "$pi_package_root/node_modules" ]] || die "cannot derive pi package root from $pi_entry"
if [[ "$run_mode" == workload ]]; then
  smoke_root=$(mktemp -d "${TMPDIR:-/tmp}/mr-headless-workload-check.XXXXXXXX")
  plain_workload_bin="$smoke_root/plain-bin"
  build_plain_workload_path "$plain_workload_bin"
  workload_home="$smoke_root/home"
  workload_cwd="$smoke_root/cwd"
  workload_out="$smoke_root/out"
  workload_prompt="$smoke_root/prompt.yaml"
  workload_uv_cache="$smoke_root/uv-cache"
  mkdir -p "$workload_home" "$workload_cwd" "$workload_out" "$workload_uv_cache" \
    "$workload_home/.config" "$workload_home/.local/share" "$workload_home/.local/state"
  cp -a --reflink=auto "$uv_cache_source/." "$workload_uv_cache/"
  chmod -R u+rwX "$workload_uv_cache"
  printf '%s\n' \
    'prompt_format_version: 2' \
    'task: code' \
    "files: [$fixture_dir/subject.py]" \
    'reviewers: [claude, agy, codex, opencode, pykrete, grok]' \
    'synthesizer: none' > "$workload_prompt"
  set +e
  (
    cd "$workload_cwd"
    env -i \
      HOME="$workload_home" \
      PATH="$plain_workload_bin:/usr/bin:/bin" \
      PYKRETE_CONFIG="$pykrete_config_file" \
      UV_CACHE_DIR="$workload_uv_cache" \
      LANG=C.UTF-8 \
      FAKE_LAUNCH_LOG="${FAKE_LAUNCH_LOG:-}" \
      "$uv_binary" run --offline --isolated "$repo_root/multi_review.py" \
        --prompt-file "$workload_prompt" --out-dir "$workload_out" --timeout 5
  ) </dev/null > "$smoke_root/workload.stdout.log" 2> "$smoke_root/workload.stderr.log"
  workload_rc=$?
  set -e
  if [[ "$workload_rc" != 0 && "$workload_rc" != 1 ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      printf 'plain workload stderr: %s\n' "$line" >&2
    done < "$smoke_root/workload.stderr.log"
    die "plain workload override probe exited $workload_rc"
  fi
  env -i \
    HOME="$workload_home" \
    XDG_CONFIG_HOME="$workload_home/.config" \
    XDG_DATA_HOME="$workload_home/.local/share" \
    XDG_STATE_HOME="$workload_home/.local/state" \
    PATH="$plain_workload_bin:/usr/bin:/bin" \
    UV_CACHE_DIR="$workload_uv_cache" \
    FAKE_LAUNCH_LOG="${FAKE_LAUNCH_LOG:-}" \
    "$plain_workload_bin/pi" --help
  printf 'plain_workload_driver_rc=%s\n' "$workload_rc"
  printf 'plain_workload_uv_environment=isolated\n'
  printf 'plain_workload_overrides=PASS\n'
  exit 0
fi
if [[ "$run_mode" == prereq ]]; then
  printf 'headless_driver_smoke_prereq=PASS\n'
  exit 0
fi

smoke_root=$(mktemp -d "${TMPDIR:-/tmp}/mr-headless-smoke.XXXXXXXX")
plain_workload_bin="$smoke_root/plain-bin"
build_plain_workload_path "$plain_workload_bin"

mkdir -p "$smoke_root/uv-cache"
cp -a --reflink=auto "$uv_cache_source/." "$smoke_root/uv-cache/"
chmod -R u+rwX "$smoke_root/uv-cache"

bwrap_system=(
  --clearenv
  --unshare-pid
  --die-with-parent
  --ro-bind /usr /usr
  --symlink usr/bin /bin
  --symlink usr/lib /lib
  --symlink usr/lib64 /lib64
  --symlink usr/sbin /sbin
  --proc /proc
  --dev /dev
  --tmpfs /tmp
  --dir /etc
  --ro-bind /etc/ssl /etc/ssl
  --ro-bind /etc/ca-certificates /etc/ca-certificates
  --ro-bind /etc/hosts /etc/hosts
  --ro-bind /etc/hostname /etc/hostname
  --ro-bind /etc/nsswitch.conf /etc/nsswitch.conf
  --dir /mnt
  --ro-bind /mnt/wsl /mnt/wsl
  --symlink /mnt/wsl/resolv.conf /etc/resolv.conf
)

run_claude_case() {
  local case_name=$1
  local prompt_name=$2
  local host_cwd=${3:-}
  local case_home="$smoke_root/home-$case_name"
  local case_out="$smoke_root/out-$case_name"
  local sandbox_cwd=/workspace
  local cwd_mount=()
  mkdir -p "$case_home/.claude" "$case_out"
  if [[ -n "$host_cwd" ]]; then
    sandbox_cwd=/foreign
    cwd_mount=(--bind "$host_cwd" /foreign)
  fi

  set +e
  bwrap "${bwrap_system[@]}" \
    --dir /opt \
    --dir /opt/claude \
    --ro-bind "$claude_binary" /opt/claude/claude \
    --dir /opt/uv \
    --ro-bind "$uv_binary" /opt/uv/uv \
    --ro-bind "$repo_root" /workspace \
    --dir /home \
    --dir /home/smoke \
    --bind "$case_home" /home/smoke \
    --bind "$smoke_root/uv-cache" /uv-cache \
    --bind "$case_out" /out \
    "${cwd_mount[@]}" \
    --setenv HOME /home/smoke \
    --setenv CLAUDE_CONFIG_DIR /home/smoke/.claude \
    --setenv UV_CACHE_DIR /uv-cache \
    --setenv PATH /opt/claude:/opt/uv:/usr/bin:/bin \
    --setenv LANG C.UTF-8 \
    --chdir "$sandbox_cwd" \
    /bin/bash -c 'set +x; IFS= read -r CLAUDE_CODE_OAUTH_TOKEN || exit 91; exec </dev/null; export CLAUDE_CODE_OAUTH_TOKEN; exec /opt/uv/uv run /workspace/multi_review.py --prompt-file "$1" --out-dir /out --timeout 180' \
    smoke "/workspace/tests/manual/fixtures/headless-driver-smoke/$prompt_name" \
    < "$claude_token_file" \
    > "$smoke_root/$case_name.stdout.log" \
    2> "$smoke_root/$case_name.stderr.log"
  local rc=$?
  set -e
  [[ "$rc" == 0 ]] || die "$case_name exited $rc (see $smoke_root/$case_name.stderr.log)"
  [[ -s "$case_out/REVIEW.md" ]] || die "$case_name did not create REVIEW.md"
  rg -q 'reviewers_succeeded: \["claude"\]' "$case_out/REVIEW.md" || \
    die "$case_name did not record Claude success"
  if find "$case_home" -type f -name .credentials.json -print -quit | rg -q .; then
    die "$case_name persisted .credentials.json"
  fi
}

wait_for_direct_driver() {
  local wrapper_pid=$1
  local driver_pid=""
  local attempt
  for ((attempt = 0; attempt < 400; attempt++)); do
    driver_pid=$(ps -eo pid=,ppid=,args= | \
      awk -v p="$wrapper_pid" '$2 == p && /multi_review\.py/ {print $1; exit}')
    if [[ -n "$driver_pid" ]]; then
      printf '%s\n' "$driver_pid"
      return 0
    fi
    kill -0 "$wrapper_pid" 2>/dev/null || return 1
    sleep 0.05
  done
  return 1
}

snapshot_survivors() {
  local snapshot=$1
  local survivors=""
  local pid _
  while read -r pid _; do
    [[ -n "$pid" ]] || continue
    kill -0 "$pid" 2>/dev/null && survivors="$survivors $pid"
  done < "$snapshot"
  printf '%s\n' "${survivors# }"
}

assert_snapshot_gone() {
  local snapshot=$1
  local label=$2
  local survivors=""
  local pid
  while read -r pid _; do
    [[ -n "$pid" ]] || continue
    if kill -0 "$pid" 2>/dev/null; then
      survivors="$survivors $pid"
    fi
  done < "$snapshot"
  if [[ -n "$survivors" ]]; then
    for pid in $survivors; do
      kill -TERM "$pid" 2>/dev/null || true
    done
    sleep 0.5
    for pid in $survivors; do
      kill -KILL "$pid" 2>/dev/null || true
    done
    die "$label left descendant PIDs alive:$survivors"
  fi
}

copy_scratch_secret() {
  local source=$1
  local destination=$2
  mkdir -p "$(dirname "$destination")"
  cp -- "$source" "$destination"
  chmod 600 "$destination"
  scratch_secret_copies+=("$destination")
}

prepare_shutdown_home() {
  local cli=$1
  local case_home=$2
  mkdir -p "$case_home"
  chmod 700 "$case_home"
  scratch_auth_homes+=("$case_home")
  case "$cli" in
    claude)
      mkdir -p "$case_home/.claude"
      ;;
    agy)
      [[ -s "$agy_token_file" ]] || die "agy auth prerequisite disappeared: $agy_token_file"
      copy_scratch_secret "$agy_token_file" \
        "$case_home/.gemini/antigravity-cli/antigravity-oauth-token"
      ;;
    codex)
      [[ -s "$codex_auth_file" ]] || die "Codex auth prerequisite disappeared: $codex_auth_file"
      copy_scratch_secret "$codex_auth_file" "$case_home/.codex/auth.json"
      ;;
    opencode)
      [[ -s "$opencode_auth_file" ]] || die "OpenCode auth prerequisite disappeared: $opencode_auth_file"
      copy_scratch_secret "$opencode_auth_file" \
        "$case_home/.local/share/opencode/auth.json"
      if [[ -f "$opencode_model_file" ]]; then
        copy_scratch_secret "$opencode_model_file" \
          "$case_home/.local/state/opencode/model.json"
      fi
      ;;
    pykrete)
      ;;
    grok)
      [[ -s "$grok_auth_file" ]] || die "Grok auth prerequisite disappeared: $grok_auth_file"
      copy_scratch_secret "$grok_auth_file" "$case_home/.grok/auth.json"
      ;;
  esac
}

write_shutdown_prompt() {
  local cli=$1
  local destination=$2
  local scope=$3
  local subject_path
  subject_path=$(shutdown_subject_path "$scope")
  printf '%s\n' \
    'prompt_format_version: 2' \
    'task: code' \
    "files: [$subject_path]" \
    "reviewers: [$cli]" \
    'synthesizer: none' > "$destination"
}

shutdown_secret_input() {
  case "$1" in
    claude) printf '%s\n' "$claude_token_file" ;;
    pykrete) printf '%s\n' "$pykrete_env_file" ;;
    *) printf '%s\n' /dev/null ;;
  esac
}

complete_shutdown() {
  local scope=$1
  local cli=$2
  local signal_pid=$3
  local wrapper_pid=$4
  local pgid=$5
  local snapshot=$6
  local case_out=$7
  local stderr_log=$8
  local captured=$9
  local label="$scope $cli shutdown"
  local survivor_count=0
  local survivors=""

  kill -TERM "$signal_pid"
  set +e
  wait "$wrapper_pid"
  local rc=$?
  set -e
  sleep 2

  if [[ "$scope" == plain && ( "$cli" == codex || "$cli" == opencode ) ]]; then
    survivors=$(process_group_survivors "$pgid")
    [[ -z "$survivors" ]] || survivor_count=$(wc -w <<< "$survivors")
    signal_group TERM "$pgid"
    sleep 0.2
    signal_group KILL "$pgid"
    signal_snapshot_reverse KILL "$snapshot"
    sleep 0.2
    assert_process_group_gone "$pgid" "$label harness cleanup"
    assert_snapshot_gone "$snapshot" "$label harness cleanup"
  else
    assert_process_group_gone "$pgid" "$label"
    assert_snapshot_gone "$snapshot" "$label"
  fi

  validate_and_report_shutdown "$scope" "$cli" "$rc" "$case_out" "$stderr_log" \
    "$captured" "$survivor_count" gone
  case "$scope" in
    plain)
      active_plain_wrapper=""
      active_plain_pgid=""
      active_plain_snapshot=""
      ;;
    bwrap)
      active_bwrap_wrapper=""
      active_bwrap_pgid=""
      active_bwrap_snapshot=""
      ;;
    *) die "unknown shutdown completion scope: $scope" ;;
  esac
  scrub_scratch_secrets
}

run_plain_shutdown() {
  local cli=$1
  local case_home="$smoke_root/home-shutdown-plain-$cli"
  local case_cwd="$smoke_root/cwd-shutdown-plain-$cli"
  local case_out="$smoke_root/out-shutdown-plain-$cli"
  local prompt="$smoke_root/shutdown-$cli.yaml"
  local snapshot="$smoke_root/plain-$cli.snapshot.before"
  local stdout_log="$smoke_root/plain-$cli.stdout.log"
  local stderr_log="$smoke_root/plain-$cli.stderr.log"
  local secret_input
  local patterns=()
  mapfile -t patterns < <(shutdown_patterns "$cli" plain)
  secret_input=$(shutdown_secret_input "$cli")
  prepare_shutdown_home "$cli" "$case_home"
  mkdir -p "$case_cwd" "$case_out"
  write_shutdown_prompt "$cli" "$prompt" plain
  active_plain_snapshot=$snapshot
  (
    cd "$case_cwd"
    exec setsid env -i \
      HOME="$case_home" \
      CLAUDE_CONFIG_DIR="$case_home/.claude" \
      CODEX_HOME="$case_home/.codex" \
      GROK_HOME="$case_home/.grok" \
      XDG_CONFIG_HOME="$case_home/.config" \
      XDG_DATA_HOME="$case_home/.local/share" \
      XDG_STATE_HOME="$case_home/.local/state" \
      UV_CACHE_DIR="$smoke_root/uv-cache" \
      PATH="$plain_workload_bin:/usr/bin:/bin" \
      PYKRETE_CONFIG="$pykrete_config_file" \
      PYKRETE_HEARTBEAT_SECONDS=1 \
      LANG=C.UTF-8 \
      /bin/bash -c '
        set +x
        cli=$1
        shift
        case "$cli" in
          claude)
            IFS= read -r CLAUDE_CODE_OAUTH_TOKEN || exit 91
            export CLAUDE_CODE_OAUTH_TOKEN
            ;;
          pykrete)
            while IFS= read -r line; do
              case "$line" in
                NANOGPT_API_KEY=*) NANOGPT_API_KEY=${line#*=} ;;
              esac
            done
            export NANOGPT_API_KEY
            ;;
        esac
        exec </dev/null
        exec "$@"
      ' smoke "$cli" \
      "$uv_binary" run "$repo_root/multi_review.py" \
      --prompt-file "$prompt" --out-dir "$case_out" --timeout 600 \
      < "$secret_input"
  ) > "$stdout_log" 2> "$stderr_log" &
  active_plain_wrapper=$!
  active_plain_pgid=$!

  local driver_pid
  driver_pid=$(wait_for_direct_driver "$active_plain_wrapper") || \
    die "plain $cli shutdown could not resolve the Python driver PID (see $stderr_log)"
  wait_for_tree_patterns "$driver_pid" "$snapshot" "${patterns[0]}" "${patterns[1]}" || \
    die "plain $cli shutdown did not observe its expected process tree (see $stderr_log)"
  local captured
  captured=$(wc -l < "$snapshot")
  complete_shutdown plain "$cli" "$driver_pid" "$active_plain_wrapper" \
    "$active_plain_pgid" "$snapshot" "$case_out" "$stderr_log" "$captured"
}

run_bwrap_shutdown() {
  local cli=$1
  local case_home="$smoke_root/home-shutdown-bwrap-$cli"
  local case_out="$smoke_root/out-shutdown-bwrap-$cli"
  local prompt="$smoke_root/shutdown-$cli.yaml"
  local snapshot="$smoke_root/bwrap-$cli.snapshot.before"
  local stdout_log="$smoke_root/bwrap-$cli.stdout.log"
  local stderr_log="$smoke_root/bwrap-$cli.stderr.log"
  local secret_input
  local patterns=()
  local cli_mounts=(--dir /opt/bin)
  local cli_env=()
  mapfile -t patterns < <(shutdown_patterns "$cli" bwrap)
  secret_input=$(shutdown_secret_input "$cli")
  prepare_shutdown_home "$cli" "$case_home"
  mkdir -p "$case_out"
  write_shutdown_prompt "$cli" "$prompt" bwrap
  case "$cli" in
    claude)
      cli_mounts+=(--ro-bind "$claude_binary" /opt/bin/claude)
      ;;
    agy)
      cli_mounts+=(--ro-bind "$agy_binary" /opt/bin/agy)
      ;;
    codex)
      cli_mounts+=(--dir /opt/codex --ro-bind "$codex_root" /opt/codex/package
        --symlink /opt/codex/package/bin/codex.js /opt/bin/codex)
      ;;
    opencode)
      cli_mounts+=(--dir /opt/opencode --ro-bind "$opencode_root" /opt/opencode/package
        --symlink /opt/opencode/package/bin/opencode /opt/bin/opencode)
      ;;
    pykrete)
      cli_mounts+=(--dir /opt/pykrete
        --ro-bind "$pykrete_root/bin" /opt/pykrete/bin
        --ro-bind "$pykrete_root/src" /opt/pykrete/src
        --ro-bind "$pykrete_root/node_modules" /opt/pykrete/node_modules
        --ro-bind "$pykrete_root/extensions" /opt/pykrete/extensions
        --ro-bind "$pykrete_config_file" /opt/pykrete/pykrete.toml
        --dir /opt/pi --ro-bind "$pi_package_root" /opt/pi/package
        --symlink /opt/pykrete/bin/pykrete.ts /opt/bin/pykrete
        --symlink /opt/pi/package/dist/cli.js /opt/bin/pi)
      cli_env+=(--setenv PYKRETE_CONFIG /opt/pykrete/pykrete.toml
        --setenv PYKRETE_HEARTBEAT_SECONDS 1)
      ;;
    grok)
      cli_mounts+=(--ro-bind "$grok_binary" /opt/bin/grok)
      ;;
  esac
  active_bwrap_snapshot=$snapshot

  setsid bwrap "${bwrap_system[@]}" \
    --dir /opt \
    --dir /opt/uv \
    --ro-bind "$uv_binary" /opt/uv/uv \
    "${cli_mounts[@]}" \
    --ro-bind "$repo_root" /workspace \
    --ro-bind "$prompt" /prompt.yaml \
    --dir /home \
    --dir /home/smoke \
    --bind "$case_home" /home/smoke \
    --bind "$smoke_root/uv-cache" /uv-cache \
    --bind "$case_out" /out \
    --setenv HOME /home/smoke \
    --setenv CLAUDE_CONFIG_DIR /home/smoke/.claude \
    --setenv CODEX_HOME /home/smoke/.codex \
    --setenv GROK_HOME /home/smoke/.grok \
    --setenv XDG_CONFIG_HOME /home/smoke/.config \
    --setenv XDG_DATA_HOME /home/smoke/.local/share \
    --setenv XDG_STATE_HOME /home/smoke/.local/state \
    --setenv UV_CACHE_DIR /uv-cache \
    --setenv PATH /opt/bin:/opt/uv:/usr/bin:/bin \
    --setenv LANG C.UTF-8 \
    "${cli_env[@]}" \
    --chdir /workspace \
    /bin/bash -c '
      set +x
      cli=$1
      case "$cli" in
        claude)
          IFS= read -r CLAUDE_CODE_OAUTH_TOKEN || exit 91
          export CLAUDE_CODE_OAUTH_TOKEN
          ;;
        pykrete)
          while IFS= read -r line; do
            case "$line" in
              NANOGPT_API_KEY=*) NANOGPT_API_KEY=${line#*=} ;;
            esac
          done
          export NANOGPT_API_KEY
          ;;
      esac
      exec </dev/null
      exec /opt/uv/uv run /workspace/multi_review.py \
        --prompt-file /prompt.yaml --out-dir /out --timeout 600
    ' smoke "$cli" < "$secret_input" > "$stdout_log" 2> "$stderr_log" &
  active_bwrap_wrapper=$!
  active_bwrap_pgid=$!

  wait_for_tree_patterns "$active_bwrap_wrapper" "$snapshot" \
    "${patterns[0]}" "${patterns[1]}" || \
    die "bwrap $cli shutdown did not observe its expected process tree (see $stderr_log)"
  local captured
  captured=$(wc -l < "$snapshot")
  complete_shutdown bwrap "$cli" "$active_bwrap_wrapper" "$active_bwrap_wrapper" \
    "$active_bwrap_pgid" "$snapshot" "$case_out" "$stderr_log" "$captured"
}

run_claude_case reference reference.yaml
! rg -q 'REFERENCE_TOOL_READ_20260807' "$smoke_root/out-reference/prompt.txt" || \
  die "reference marker leaked into prompt.txt"
rg -q 'REFERENCE_TOOL_READ_20260807' "$smoke_root/out-reference/REVIEW.md" || \
  die "reference review omitted the file-only marker"
rg -l '"name":"Read"|"name": "Read"' \
  "$smoke_root/home-reference/.claude/projects" >/dev/null || \
  die "reference session recorded no Read tool call"
printf 'case1=PASS sandboxed_claude_and_reference_read=ok\n'
printf 'case2=PASS wsl_dns_and_anthropic_endpoint=ok\n'

mkdir -p "$smoke_root/foreign-no-project" "$smoke_root/foreign-with-project"
cp "$repo_root/pyproject.toml" "$smoke_root/foreign-with-project/pyproject.toml"
run_claude_case foreign-no-project reference.yaml "$smoke_root/foreign-no-project"
run_claude_case foreign-with-project reference.yaml "$smoke_root/foreign-with-project"
if find "$smoke_root/foreign-no-project" "$smoke_root/foreign-with-project" \
  -mindepth 1 -maxdepth 1 \( -name .venv -o -name uv.lock \) -print -quit | rg -q .; then
  die "foreign cwd gained .venv or uv.lock"
fi
[[ -z $(find "$smoke_root/foreign-no-project" -mindepth 1 -maxdepth 1 -print -quit) ]] || \
  die "no-project foreign cwd was modified"
[[ $(find "$smoke_root/foreign-with-project" -mindepth 1 -maxdepth 1 -printf '%f\n') == pyproject.toml ]] || \
  die "project foreign cwd gained unexpected files"
printf 'case3=PASS foreign_cwds_clean=ok\n'

for shutdown_cli in "${shutdown_clis[@]}"; do
  run_plain_shutdown "$shutdown_cli"
  run_bwrap_shutdown "$shutdown_cli"
done
printf 'case4=PASS shutdown_clis=%s plain_and_bwrap=ok\n' "${#shutdown_clis[@]}"
printf 'headless_driver_smoke=PASS cases=4\n'
