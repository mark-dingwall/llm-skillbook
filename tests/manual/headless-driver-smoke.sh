#!/usr/bin/env bash

# Reproducible live acceptance gate for multi_review.py.
#
# Secret inputs are file parameters, never argv values:
#   CLAUDE_TOKEN_FILE     raw token from `claude setup-token`, mode 0600
#   PYKRETE_ENV_FILE      one NANOGPT_API_KEY=... assignment, mode 0600
#   PYKRETE_CONFIG_FILE   normal non-secret pykrete.toml
#
# Set KEEP_SMOKE_ARTIFACTS=1 to retain the temporary evidence directory.
# Single-quoted child-shell snippets intentionally expand only after entering
# their credential-reading process or sandbox.
# shellcheck disable=SC2016

set +x
set -Eeuo pipefail

script_path=$(readlink -f "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_path")
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)
fixture_dir="$script_dir/fixtures/headless-driver-smoke"

die() {
  printf 'headless-driver-smoke: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

run_self_check() {
  [[ -x "$script_path" ]] || die "harness is not executable: $script_path"
  bash -n "$script_path"
  require_command uv
  uv run --project "$repo_root" python - "$fixture_dir" <<'PY'
from pathlib import Path
import sys

from multi_review.core.prompt import build_prompt
from multi_review.core.promptfile import load_promptfile

root = Path(sys.argv[1])
subject = root / "subject.py"
required = [subject, root / "inline.yaml", root / "reference.yaml", root / "shutdown.yaml"]
assert all(path.is_file() for path in required), "checked-in smoke fixture missing"

inline = load_promptfile(root / "inline.yaml")
reference = load_promptfile(root / "reference.yaml")
shutdown = load_promptfile(root / "shutdown.yaml")
assert inline.reviewers == ["claude"] and inline.mode == "inline"
assert reference.reviewers == ["claude"] and reference.mode == "reference"
assert shutdown.reviewers == ["pykrete"] and shutdown.synthesizer == "none"

reference_prompt = build_prompt(
    task=reference.task,
    files=[subject],
    custom_prompt=reference.custom_prompt,
    mode="reference",
    nonce="staticcheck",
)
assert "REFERENCE_TOOL_READ_20260807" not in reference_prompt
assert str(subject.resolve()) in reference_prompt
PY
  printf 'headless_driver_smoke_check=PASS\n'
}

usage() {
  cat <<'EOF'
Usage:
  tests/manual/headless-driver-smoke.sh --check
  CLAUDE_TOKEN_FILE=/secure/token \
  PYKRETE_ENV_FILE=/secure/pykrete.env \
  PYKRETE_CONFIG_FILE=/path/to/pykrete.toml \
    tests/manual/headless-driver-smoke.sh

Optional environment:
  KEEP_SMOKE_ARTIFACTS=1  retain the temporary evidence directory
  UV_CACHE_SOURCE=...     source cache copied into the sandbox scratch tree
  CLAUDE_BIN=...          explicit Claude Code executable
  UV_BIN=...              explicit uv executable
  PYKRETE_ENTRY=...       explicit pykrete entry script
  PI_ENTRY=...            explicit pi entry script
EOF
}

case "${1:-}" in
  --check)
    run_self_check
    exit 0
    ;;
  --help|-h)
    usage
    exit 0
    ;;
  "") ;;
  *)
    usage >&2
    exit 2
    ;;
esac

require_command awk
require_command bwrap
require_command cp
require_command find
require_command git
require_command ps
require_command rg
require_command stat
require_command uv
require_command claude
require_command pykrete
require_command pi

claude_token_file=${CLAUDE_TOKEN_FILE:-}
pykrete_env_file=${PYKRETE_ENV_FILE:-}
pykrete_config_file=${PYKRETE_CONFIG_FILE:-}
[[ -n "$claude_token_file" ]] || die "CLAUDE_TOKEN_FILE is required"
[[ -n "$pykrete_env_file" ]] || die "PYKRETE_ENV_FILE is required"
[[ -n "$pykrete_config_file" ]] || die "PYKRETE_CONFIG_FILE is required"

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

pykrete_noncomment_lines=$(awk 'NF && $1 !~ /^#/ {count++} END {print count + 0}' "$pykrete_env_file")
pykrete_key_lines=$(awk '/^NANOGPT_API_KEY=.+$/ {count++} END {print count + 0}' "$pykrete_env_file")
[[ "$pykrete_noncomment_lines" == 1 && "$pykrete_key_lines" == 1 ]] || \
  die "PYKRETE_ENV_FILE must contain exactly one NANOGPT_API_KEY assignment"

uv_binary=${UV_BIN:-$(readlink -f "$(command -v uv)")}
claude_binary=${CLAUDE_BIN:-$(readlink -f "$(command -v claude)")}
pykrete_entry=${PYKRETE_ENTRY:-$(readlink -f "$(command -v pykrete)")}
pi_entry=${PI_ENTRY:-$(readlink -f "$(command -v pi)")}
pykrete_root=$(dirname "$(dirname "$pykrete_entry")")
pi_package_root=$(dirname "$(dirname "$pi_entry")")
user_home=$(getent passwd "$(id -u)" | awk -F: '{print $6}')
uv_cache_source=${UV_CACHE_SOURCE:-"$user_home/.cache/uv"}

[[ -x "$uv_binary" ]] || die "uv executable is not executable: $uv_binary"
[[ -x "$claude_binary" ]] || die "Claude executable is not executable: $claude_binary"
[[ -f "$pykrete_entry" ]] || die "pykrete entry is missing: $pykrete_entry"
[[ -f "$pi_entry" ]] || die "pi entry is missing: $pi_entry"
[[ -d "$pykrete_root/src" && -d "$pykrete_root/node_modules" ]] || \
  die "cannot derive pykrete source root from $pykrete_entry"
[[ -d "$pi_package_root/node_modules" ]] || die "cannot derive pi package root from $pi_entry"
[[ -d "$uv_cache_source" ]] || die "UV cache source is missing: $uv_cache_source"
[[ -f /mnt/wsl/resolv.conf ]] || die "WSL resolver prerequisite missing: /mnt/wsl/resolv.conf"

smoke_root=$(mktemp -d "${TMPDIR:-/tmp}/mr-headless-smoke.XXXXXXXX")
active_plain_wrapper=""
active_bwrap_wrapper=""

cleanup() {
  local status=$?
  set +e
  for pid in "$active_plain_wrapper" "$active_bwrap_wrapper"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null
    fi
  done
  sleep 0.2
  for pid in "$active_plain_wrapper" "$active_bwrap_wrapper"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null
    fi
  done
  if [[ ${KEEP_SMOKE_ARTIFACTS:-0} == 1 ]]; then
    printf 'smoke_artifacts=%s\n' "$smoke_root"
  else
    rm -rf -- "$smoke_root"
  fi
  exit "$status"
}
trap cleanup EXIT

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

wait_for_tree_patterns() {
  local root_pid=$1
  local snapshot=$2
  local first_pattern=$3
  local second_pattern=$4
  local attempt
  for ((attempt = 0; attempt < 1200; attempt++)); do
    snapshot_tree "$root_pid" "$snapshot"
    if rg -q "$first_pattern" "$snapshot" && rg -q "$second_pattern" "$snapshot"; then
      return 0
    fi
    kill -0 "$root_pid" 2>/dev/null || return 1
    sleep 0.05
  done
  return 1
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

run_plain_shutdown() {
  local case_out="$smoke_root/out-shutdown-plain"
  local snapshot="$smoke_root/plain.snapshot.before"
  mkdir -p "$case_out"
  (
    cd "$repo_root"
    exec env \
      UV_CACHE_DIR="$smoke_root/uv-cache" \
      PYKRETE_CONFIG="$pykrete_config_file" \
      PYKRETE_HEARTBEAT_SECONDS=1 \
      /bin/bash -c '
        set +x
        while IFS= read -r line; do
          case "$line" in
            NANOGPT_API_KEY=*) NANOGPT_API_KEY=${line#*=} ;;
          esac
        done
        exec </dev/null
        export NANOGPT_API_KEY
        exec "$@"
      ' smoke \
      "$uv_binary" run "$repo_root/multi_review.py" \
      --prompt-file "$fixture_dir/shutdown.yaml" \
      --out-dir "$case_out" --timeout 600 \
      < "$pykrete_env_file"
  ) > "$smoke_root/plain.stdout.log" 2> "$smoke_root/plain.stderr.log" &
  active_plain_wrapper=$!

  local driver_pid
  driver_pid=$(wait_for_direct_driver "$active_plain_wrapper") || \
    die "plain shutdown could not resolve the Python driver PID"
  wait_for_tree_patterns "$driver_pid" "$snapshot" \
    'node .*/pykrete( |$)' 'node .*/pi( |$)' || \
    die "plain shutdown did not observe both pykrete and pi"

  kill -TERM "$driver_pid"
  set +e
  wait "$active_plain_wrapper"
  local rc=$?
  set -e
  active_plain_wrapper=""
  [[ "$rc" == 1 ]] || die "plain driver exited $rc, expected 1"
  sleep 2
  assert_snapshot_gone "$snapshot" "plain shutdown"
  [[ ! -e "$case_out/REVIEW.md" ]] || die "plain shutdown wrote REVIEW.md"
  ! rg -q 'Traceback \(most recent call last\)' "$smoke_root/plain.stderr.log" || \
    die "plain shutdown emitted a traceback"
}

run_bwrap_shutdown() {
  local case_home="$smoke_root/home-shutdown-bwrap"
  local case_out="$smoke_root/out-shutdown-bwrap"
  local snapshot="$smoke_root/bwrap.snapshot.before"
  mkdir -p "$case_home" "$case_out"

  bwrap "${bwrap_system[@]}" \
    --dir /opt \
    --dir /opt/uv \
    --ro-bind "$uv_binary" /opt/uv/uv \
    --dir /opt/pykrete \
    --ro-bind "$pykrete_root/bin" /opt/pykrete/bin \
    --ro-bind "$pykrete_root/src" /opt/pykrete/src \
    --ro-bind "$pykrete_root/node_modules" /opt/pykrete/node_modules \
    --ro-bind "$pykrete_root/extensions" /opt/pykrete/extensions \
    --ro-bind "$pykrete_config_file" /opt/pykrete/pykrete.toml \
    --dir /opt/pi \
    --ro-bind "$pi_package_root" /opt/pi/package \
    --dir /opt/bin \
    --symlink /opt/pykrete/bin/pykrete.ts /opt/bin/pykrete \
    --symlink /opt/pi/package/dist/cli.js /opt/bin/pi \
    --ro-bind "$repo_root" /workspace \
    --dir /home \
    --dir /home/smoke \
    --bind "$case_home" /home/smoke \
    --bind "$smoke_root/uv-cache" /uv-cache \
    --bind "$case_out" /out \
    --setenv HOME /home/smoke \
    --setenv UV_CACHE_DIR /uv-cache \
    --setenv PATH /opt/bin:/opt/uv:/usr/bin:/bin \
    --setenv LANG C.UTF-8 \
    --setenv PYKRETE_CONFIG /opt/pykrete/pykrete.toml \
    --setenv PYKRETE_HEARTBEAT_SECONDS 1 \
    --chdir /workspace \
    /bin/bash -c '
      set +x
      while IFS= read -r line; do
        case "$line" in
          NANOGPT_API_KEY=*) NANOGPT_API_KEY=${line#*=} ;;
        esac
      done
      exec </dev/null
      export NANOGPT_API_KEY
      exec /opt/uv/uv run /workspace/multi_review.py \
        --prompt-file /workspace/tests/manual/fixtures/headless-driver-smoke/shutdown.yaml \
        --out-dir /out --timeout 600
    ' < "$pykrete_env_file" \
    > "$smoke_root/bwrap.stdout.log" \
    2> "$smoke_root/bwrap.stderr.log" &
  active_bwrap_wrapper=$!

  wait_for_tree_patterns "$active_bwrap_wrapper" "$snapshot" \
    'node /opt/bin/pykrete( |$)' 'node /opt/bin/pi( |$)' || \
    die "bwrap shutdown did not observe both pykrete and pi"

  kill -TERM "$active_bwrap_wrapper"
  set +e
  wait "$active_bwrap_wrapper"
  local rc=$?
  set -e
  active_bwrap_wrapper=""
  [[ "$rc" == 143 ]] || die "bwrap wrapper exited $rc, expected 143"
  sleep 2
  assert_snapshot_gone "$snapshot" "bwrap shutdown"
  [[ ! -e "$case_out/REVIEW.md" ]] || die "bwrap shutdown wrote REVIEW.md"
}

run_claude_case inline inline.yaml
rg -q 'INLINE_DRIVER_SMOKE_20260807' "$smoke_root/out-inline/REVIEW.md" || \
  die "inline review omitted the fixture marker"
printf 'case1=PASS sandboxed_claude=ok\n'
printf 'case3=PASS wsl_dns_and_anthropic_endpoint=ok\n'

run_claude_case reference reference.yaml
! rg -q 'REFERENCE_TOOL_READ_20260807' "$smoke_root/out-reference/prompt.txt" || \
  die "reference marker leaked into prompt.txt"
rg -q 'REFERENCE_TOOL_READ_20260807' "$smoke_root/out-reference/REVIEW.md" || \
  die "reference review omitted the file-only marker"
rg -l '"name":"Read"|"name": "Read"' \
  "$smoke_root/home-reference/.claude/projects" >/dev/null || \
  die "reference session recorded no Read tool call"
printf 'case2=PASS reference_read=ok\n'

mkdir -p "$smoke_root/foreign-no-project" "$smoke_root/foreign-with-project"
cp "$repo_root/pyproject.toml" "$smoke_root/foreign-with-project/pyproject.toml"
run_claude_case foreign-no-project inline.yaml "$smoke_root/foreign-no-project"
run_claude_case foreign-with-project inline.yaml "$smoke_root/foreign-with-project"
if find "$smoke_root/foreign-no-project" "$smoke_root/foreign-with-project" \
  -mindepth 1 -maxdepth 1 \( -name .venv -o -name uv.lock \) -print -quit | rg -q .; then
  die "foreign cwd gained .venv or uv.lock"
fi
[[ -z $(find "$smoke_root/foreign-no-project" -mindepth 1 -maxdepth 1 -print -quit) ]] || \
  die "no-project foreign cwd was modified"
[[ $(find "$smoke_root/foreign-with-project" -mindepth 1 -maxdepth 1 -printf '%f\n') == pyproject.toml ]] || \
  die "project foreign cwd gained unexpected files"
printf 'case4=PASS foreign_cwds_clean=ok\n'

run_plain_shutdown
run_bwrap_shutdown
printf 'case5=PASS plain_and_bwrap_shutdown=ok\n'
printf 'headless_driver_smoke=PASS cases=5\n'
