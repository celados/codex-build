#!/usr/bin/env bash
set -euo pipefail

label="${1:?measurement label required}"
shift
builder="$(cd "$(dirname "$0")/.." && pwd)"
cache="${RUNNER_TOOL_CACHE:?}/codex-build"
samples="$(mktemp)"
started=$SECONDS

sample() {
  # Sample both persistent storage and temporary compiler output, not just CAS.
  du -sk "$cache" "$builder" | awk '{total += $1} END {print total}' >> "$samples"
}
sample
(
  while true; do
    sleep 15
    sample
  done
) &
sampler=$!
finish() {
  status=$?
  trap - EXIT
  kill "$sampler" 2>/dev/null || true
  wait "$sampler" 2>/dev/null || true
  sample
  peak="$(awk 'BEGIN {max=0} $1>max {max=$1} END {print max}' "$samples")"
  result="$label: exit=$status elapsed=$((SECONDS-started))s sampled_peak=${peak}KiB"
  echo "$result"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    echo "$result" >> "$GITHUB_STEP_SUMMARY"
  fi
  rm "$samples"
  exit "$status"
}
trap finish EXIT
"$@"
