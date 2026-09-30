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
# Keep an immutable complete package so daemon updates can copy the same runtime.
package_dir="$install_dir/.codex-build/releases"

sync_daemon() {
  # Older CLIs do not offer package selection. Do not start a daemon on first install.
  if ! "$installed" app-server daemon update --help 2>/dev/null | grep -q -- '--from-cli'; then
    return
  fi
  if ! "$installed" app-server daemon version > "$temporary_dir/daemon-before.json" 2>/dev/null; then
    return
  fi
  echo "Updating the running Codex daemon; active or queued work may be interrupted."
  if ! "$installed" app-server daemon update --from-cli --yes; then
    echo "CLI installed, but daemon update failed. Retry the installer before using Codex." >&2
    exit 1
  fi
  "$installed" app-server daemon version > "$temporary_dir/daemon-after.json"
  # macOS ships JXA; parse JSON without requiring a Python or Node installation.
  if ! osascript -l JavaScript - "$temporary_dir/daemon-after.json" "$latest_version" <<'JXA'
ObjC.import('Foundation');
function run(args) {
  const text = $.NSString.stringWithContentsOfFileEncodingError(args[0], $.NSUTF8StringEncoding, null);
  const state = JSON.parse(ObjC.unwrap(text));
  if (state.cliVersion !== args[1] || state.appServerVersion !== args[1] || state.managedCodexVersion !== args[1]) {
    throw new Error('CLI, managed package and running daemon versions must all match ' + args[1]);
  }
}
JXA
  then
    echo "Daemon version verification failed; CLI installation cannot be reported as complete." >&2
    exit 1
  fi
}

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
temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
release_dir="$package_dir/$latest_version"
if [[ -x "$installed" && -x "$installed_host" &&
      -f "$release_dir/codex-package.json" && -x "$release_dir/codex-path/rg" &&
      "$installed" -ef "$release_dir/bin/codex" &&
      "$installed_host" -ef "$release_dir/bin/codex-code-mode-host" ]]; then
  installed_version="$("$installed" --version 2>/dev/null || true)"
  installed_version="${installed_version##* }"
  if [[ "$installed_version" == "$latest_version" ]]; then
    sync_daemon
    echo "codex $latest_version is already installed at $installed"
    exit 0
  fi
fi

# The daemon's package validator requires a bundled executable ripgrep.
rg_binary="$(command -v rg || true)"
if [[ -z "$rg_binary" || ! -x "$rg_binary" ]]; then
  echo "ripgrep (rg) is required to install a complete Codex package; install it and retry." >&2
  exit 1
fi

curl -fL "$release_url/$asset" -o "$temporary_dir/$asset"
curl -fL "$release_url/$asset.sha256" -o "$temporary_dir/$asset.sha256"
(cd "$temporary_dir" && shasum -a 256 -c "$asset.sha256")
(cd "$temporary_dir" && tar -xzf "$asset")
chmod 0755 "$temporary_dir/$codex_binary" "$temporary_dir/$host_binary"
downloaded_version="$("$temporary_dir/$codex_binary" --version)"
if [[ "${downloaded_version##* }" != "$latest_version" ]]; then
  echo "Downloaded CLI version does not match release $latest_version" >&2
  exit 1
fi
"$temporary_dir/$host_binary" --help > /dev/null

staged_package="$temporary_dir/package"
mkdir -p "$staged_package/bin" "$staged_package/codex-path"
install -m 0755 "$temporary_dir/$codex_binary" "$staged_package/bin/codex"
install -m 0755 "$temporary_dir/$host_binary" "$staged_package/bin/codex-code-mode-host"
install -m 0755 "$rg_binary" "$staged_package/codex-path/rg"
printf '{"layoutVersion":1,"version":"%s","target":"aarch64-apple-darwin","entrypoint":"bin/codex"}\n' \
  "$latest_version" > "$staged_package/codex-package.json"
mkdir -p "$package_dir"
# Existing version directories must be complete; never overwrite a running package.
if [[ -e "$release_dir" ]]; then
  echo "Package directory already exists but installation is incomplete: $release_dir" >&2
  echo "Move that directory aside and retry the installer." >&2
  exit 1
fi
mv "$staged_package" "$release_dir"
release_dir="$(cd "$release_dir" && pwd)"
# Host first, then CLI, so a new CLI never resolves an old host.
ln -s "$release_dir/bin/codex-code-mode-host" "$install_dir/.codex-code-mode-host.new"
mv -f "$install_dir/.codex-code-mode-host.new" "$installed_host"
ln -s "$release_dir/bin/codex" "$install_dir/.codex.new"
mv -f "$install_dir/.codex.new" "$installed"
sync_daemon
echo "Installed codex $latest_version and its code-mode host to $install_dir"
