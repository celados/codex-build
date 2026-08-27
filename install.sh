#!/usr/bin/env bash
set -euo pipefail

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) ;;
  *)
    echo "codex-build currently supports only Apple Silicon macOS" >&2
    exit 1
    ;;
esac

install_dir="${CODEX_INSTALL_DIR:-$HOME/.local/bin}"
asset="codex-aarch64-apple-darwin"
release_url="https://github.com/celados/codex-build/releases/latest/download"
temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT

curl -fL "$release_url/$asset" -o "$temporary_dir/$asset"
curl -fL "$release_url/$asset.sha256" -o "$temporary_dir/$asset.sha256"
(cd "$temporary_dir" && shasum -a 256 -c "$asset.sha256")
chmod 0755 "$temporary_dir/$asset"
"$temporary_dir/$asset" --version

mkdir -p "$install_dir"
install -m 0755 "$temporary_dir/$asset" "$install_dir/.codex.new"
mv -f "$install_dir/.codex.new" "$install_dir/codex"
echo "Installed codex to $install_dir/codex"
