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
binary="codex-aarch64-apple-darwin"
asset="$binary.tar.gz"
release_url="https://github.com/celados/codex-build/releases/latest/download"
latest_release_url="https://github.com/celados/codex-build/releases/latest"

# Resolve the tag before downloading the 80+ MB artifact so repeated updates are cheap.
latest_url="$(curl -fsSIL -o /dev/null -w '%{url_effective}' "$latest_release_url")"
latest_tag="${latest_url%/}"
latest_tag="${latest_tag##*/}"
latest_version="${latest_tag#rust-v}"
if [[ ! "$latest_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Could not resolve the latest codex-build version from $latest_url" >&2
  exit 1
fi

installed="$install_dir/codex"
if [[ -x "$installed" ]]; then
  installed_version="$("$installed" --version 2>/dev/null || true)"
  installed_version="${installed_version##* }"
  if [[ "$installed_version" == "$latest_version" ]]; then
    echo "codex $latest_version is already installed at $installed"
    exit 0
  fi
fi

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT

curl -fL "$release_url/$asset" -o "$temporary_dir/$asset"
curl -fL "$release_url/$asset.sha256" -o "$temporary_dir/$asset.sha256"
(cd "$temporary_dir" && shasum -a 256 -c "$asset.sha256")
(cd "$temporary_dir" && tar -xzf "$asset")
chmod 0755 "$temporary_dir/$binary"
"$temporary_dir/$binary" --version

mkdir -p "$install_dir"
install -m 0755 "$temporary_dir/$binary" "$install_dir/.codex.new"
mv -f "$install_dir/.codex.new" "$install_dir/codex"
echo "Installed codex to $install_dir/codex"
