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
codex_binary="codex-aarch64-apple-darwin"
host_binary="codex-code-mode-host-aarch64-apple-darwin"
asset="$codex_binary.tar.gz"
release_url="https://github.com/celados/codex-build/releases/latest/download"
latest_release_url="https://github.com/celados/codex-build/releases/latest"
# Codex resolves the code-mode host next to its own executable. The host reports no
# version of its own, so record the pair's version here; without it a host left behind
# by another installer looks current and breaks every tool call at the IPC layer.
host_version_file="$install_dir/.codex-code-mode-host.version"

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
installed_host="$install_dir/codex-code-mode-host"
if [[ -x "$installed" && -x "$installed_host" ]]; then
  installed_version="$("$installed" --version 2>/dev/null || true)"
  installed_version="${installed_version##* }"
  installed_host_version="$(cat "$host_version_file" 2>/dev/null || true)"
  if [[ "$installed_version" == "$latest_version" &&
    "$installed_host_version" == "$latest_version" ]]; then
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
chmod 0755 "$temporary_dir/$codex_binary" "$temporary_dir/$host_binary"
"$temporary_dir/$codex_binary" --version
"$temporary_dir/$host_binary" --help > /dev/null

mkdir -p "$install_dir"
# Install the host and stamp its version before codex: an interrupted run must never leave
# a new codex beside an old host, which is the failure this pairing exists to prevent.
install -m 0755 "$temporary_dir/$host_binary" "$install_dir/.codex-code-mode-host.new"
mv -f "$install_dir/.codex-code-mode-host.new" "$install_dir/codex-code-mode-host"
printf '%s\n' "$latest_version" > "$host_version_file"
install -m 0755 "$temporary_dir/$codex_binary" "$install_dir/.codex.new"
mv -f "$install_dir/.codex.new" "$install_dir/codex"
echo "Installed codex $latest_version and its code-mode host to $install_dir"
