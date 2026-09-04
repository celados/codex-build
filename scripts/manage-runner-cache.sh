#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
runner_tool_cache="${2:-}"

if [[ "$mode" != "prepare" && "$mode" != "trim" ]]; then
  echo "usage: $0 <prepare|trim> <runner-tool-cache>" >&2
  exit 2
fi
if [[ -z "$runner_tool_cache" || "$runner_tool_cache" != /* || "$runner_tool_cache" == "/" ]]; then
  echo "runner tool cache must be a non-root absolute path" >&2
  exit 2
fi

cache_root="$runner_tool_cache/codex-build"
cargo_home="$cache_root/cargo-home"
target_cache="$cache_root/target"
v8_cache="$cache_root/v8-cache"

assert_cache_child() {
  local path="$1"
  if [[ -z "$path" || "$path" != "$cache_root/"* ]]; then
    echo "refusing to manage path outside $cache_root: $path" >&2
    exit 2
  fi
}

remove_cache() {
  local path="$1"
  assert_cache_child "$path"
  rm -rf -- "$path"
}

prune_cache() {
  local path="$1"
  local ceiling_kib="$2"
  local size_kib=0
  assert_cache_child "$path"
  if [[ -d "$path" ]]; then
    size_kib="$(du -sk "$path" | cut -f1)"
  fi
  if ((size_kib > ceiling_kib)); then
    echo "Pruning $path: ${size_kib} KiB exceeds ${ceiling_kib} KiB"
    remove_cache "$path"
  fi
}

# One current release target is roughly 7 GiB. These caps retain useful hot state
# while ensuring stale Cargo hash generations cannot grow without bound.
prune_cache "$target_cache" 12582912
prune_cache "$cargo_home" 4194304
prune_cache "$v8_cache" 1048576

if [[ "$mode" == "prepare" ]]; then
  mkdir -p "$cargo_home" "$target_cache" "$v8_cache"

  # Reusable data must never prevent a cold build. Drop the largest caches first,
  # stopping as soon as the compiler has enough headroom.
  for path in "$target_cache" "$cargo_home" "$v8_cache"; do
    available_kib="$(df -Pk "$cache_root" | awk 'NR == 2 {print $4}')"
    if ((available_kib >= 31457280)); then
      break
    fi
    echo "Only ${available_kib} KiB free; dropping reusable cache $path"
    remove_cache "$path"
    mkdir -p "$path"
  done
  available_kib="$(df -Pk "$cache_root" | awk 'NR == 2 {print $4}')"
  if ((available_kib < 31457280)); then
    echo "At least 30 GiB free is required for a Codex release build; ${available_kib} KiB available" >&2
    exit 1
  fi
fi
