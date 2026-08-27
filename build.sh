#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")" && pwd)"
source_dir="$repo_dir/sources"
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
  git -C "$source_dir" restore --source=HEAD -- \
    codex-rs/Cargo.toml \
    codex-rs/Cargo.lock \
    codex-rs/core/src/config/mod.rs \
    codex-rs/tui/src/file_search.rs \
    codex-rs/tui/src/update_action.rs \
    codex-rs/tui/src/updates.rs
}
trap restore_sources EXIT

python3 "$repo_dir/scripts/apply-patches.py" --source "$source_dir"
python3 "$repo_dir/scripts/set-workspace-version.py" \
  "$source_dir/codex-rs/Cargo.toml" "${upstream_ref#rust-v}" "$version"
(
  cd "$source_dir/codex-rs"
  # Running here activates upstream's pinned rust-toolchain.toml.
  cargo fmt --all -- --check
  cargo build \
    --target aarch64-apple-darwin \
    --release \
    -p codex-cli --bin codex \
    -p codex-file-search --bin codex-file-search
)

python3 "$repo_dir/scripts/check-mention.py" \
  "$source_dir/codex-rs/target/aarch64-apple-darwin/release/codex-file-search"

mkdir -p "$repo_dir/dist"
cp "$source_dir/codex-rs/target/aarch64-apple-darwin/release/codex" \
  "$repo_dir/dist/codex-aarch64-apple-darwin"
# Match upstream's macOS release staging so downloads do not carry debug symbols.
strip -S -x "$repo_dir/dist/codex-aarch64-apple-darwin"
chmod 0755 "$repo_dir/dist/codex-aarch64-apple-darwin"
codesign --force --sign - "$repo_dir/dist/codex-aarch64-apple-darwin"
codesign --verify --strict "$repo_dir/dist/codex-aarch64-apple-darwin"
"$repo_dir/dist/codex-aarch64-apple-darwin" --version

(
  cd "$repo_dir/dist"
  tar -czf codex-aarch64-apple-darwin.tar.gz codex-aarch64-apple-darwin
  shasum -a 256 codex-aarch64-apple-darwin.tar.gz \
    > codex-aarch64-apple-darwin.tar.gz.sha256
)
