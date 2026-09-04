#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")" && pwd)"
source_dir="$repo_dir/sources"
workspace_dir="$source_dir/codex-rs"
upstream_ref=""
version=""
check_only=0

while (($#)); do
  case "$1" in
    --upstream-ref)
      upstream_ref="$2"
      shift 2
      ;;
    --version)
      version="$2"
      shift 2
      ;;
    --check)
      check_only=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$upstream_ref" ]]; then
  echo "--upstream-ref is required" >&2
  exit 2
fi
if [[ "$check_only" -eq 0 && -z "$version" ]]; then
  echo "--version is required for a build" >&2
  exit 2
fi

if [[ ! -d "$source_dir/.git" ]]; then
  git clone --filter=blob:none --no-checkout https://github.com/openai/codex.git "$source_dir"
fi
# A cancelled runner can leave this cache-only lock after its Git process has exited.
rm -f "$source_dir/.git/index.lock"

git -C "$source_dir" fetch --force --depth=1 origin "refs/tags/$upstream_ref:refs/tags/$upstream_ref"
# sources/ is a builder-owned cache; force checkout recovers an interrupted prior patch.
git -C "$source_dir" checkout --detach --force "$upstream_ref"
# Keep ignored Cargo artifacts, but remove non-ignored debris from interrupted jobs.
git -C "$source_dir" clean -ffd
python3 "$repo_dir/scripts/apply-patches.py" --source "$source_dir" --check

if [[ "$check_only" -eq 1 ]]; then
  exit 0
fi

restore_sources() {
  # Patch rules may touch upstream test literals as the catalog contract evolves.
  git -C "$source_dir" restore --source=HEAD -- codex-rs
  # Overlay modules are custom-build-owned and therefore untracked by upstream.
  git -C "$source_dir" clean -ffd -- codex-rs
}
trap restore_sources EXIT

python3 "$repo_dir/scripts/apply-patches.py" --source "$source_dir"
python3 "$repo_dir/scripts/set-workspace-version.py" \
  "$source_dir/codex-rs/Cargo.toml" "${upstream_ref#rust-v}" "$version"
if [[ -n "${CARGO_TARGET_DIR:-}" ]]; then
  if [[ "$CARGO_TARGET_DIR" = /* ]]; then
    cargo_target_dir="$CARGO_TARGET_DIR"
  else
    cargo_target_dir="$workspace_dir/$CARGO_TARGET_DIR"
  fi
else
  cargo_target_dir="$workspace_dir/target"
fi
mkdir -p "$cargo_target_dir"
cargo_target_dir="$(cd "$cargo_target_dir" && pwd)"
# The v8 crate's default prebuilts carry no sandbox-enabled aarch64-apple-darwin
# archive, so the code-mode host links Codex's own published pair instead.
v8_cache_dir="${CODEX_BUILD_V8_CACHE_DIR:-$repo_dir/.v8-cache}"
# The downloaded archives are reusable; the generated environment embeds build-local
# paths and therefore stays with the disposable builder.
v8_env="$repo_dir/.v8-cache/cargo-env"
python3 "$repo_dir/scripts/fetch-v8.py" \
  --cargo-lock "$source_dir/codex-rs/Cargo.lock" \
  --cache "$v8_cache_dir" \
  --target aarch64-apple-darwin \
  --output "$v8_env"

(
  cd "$source_dir/codex-rs"
  set -a
  # shellcheck source=/dev/null
  . "$v8_env"
  set +a
  # Running here activates upstream's pinned rust-toolchain.toml.
  cargo fmt --all
  cargo fmt --all -- --check
  cargo build \
    --target aarch64-apple-darwin \
    --release \
    -p codex-cli --bin codex \
    -p codex-code-mode-host --bin codex-code-mode-host \
    -p codex-file-search --bin codex-file-search
)

python3 "$repo_dir/scripts/check-mention.py" \
  "$cargo_target_dir/aarch64-apple-darwin/release/codex-file-search"

mkdir -p "$repo_dir/dist"

stage_binary() {
  local staged="$repo_dir/dist/$1-aarch64-apple-darwin"
  cp "$cargo_target_dir/aarch64-apple-darwin/release/$1" "$staged"
  # Match upstream's macOS release staging so downloads do not carry debug symbols.
  strip -S -x "$staged"
  chmod 0755 "$staged"
  # Stripping invalidates the signature, so sign the stripped bytes.
  codesign --force --sign - "$staged"
  codesign --verify --strict "$staged"
}

stage_binary codex
stage_binary codex-code-mode-host

"$repo_dir/dist/codex-aarch64-apple-darwin" --version
# The host reports no version; --help proves the stripped, re-signed binary still starts.
"$repo_dir/dist/codex-code-mode-host-aarch64-apple-darwin" --help > /dev/null

(
  cd "$repo_dir/dist"
  # Codex resolves the code-mode host next to its own executable and the two speak an IPC
  # schema that upstream changes without bumping its protocol version, so a mismatched pair
  # fails every tool call before it reaches a shell. One archive keeps them inseparable.
  tar -czf codex-aarch64-apple-darwin.tar.gz \
    codex-aarch64-apple-darwin \
    codex-code-mode-host-aarch64-apple-darwin
  shasum -a 256 codex-aarch64-apple-darwin.tar.gz \
    > codex-aarch64-apple-darwin.tar.gz.sha256
)
