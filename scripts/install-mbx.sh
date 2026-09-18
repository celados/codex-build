#!/usr/bin/env bash
set -euo pipefail

# Pin the reviewed release and bytes; release builds must not install a moving tool.
destination="${1:?installation directory required}"
mkdir -p "$destination"
archive="$destination/mbx.tar.gz"
curl --fail --location --retry 3 --output "$archive" \
  https://github.com/jdx/mr-boxington/releases/download/v1.13.0/mbx-aarch64-apple-darwin.tar.gz
echo "690fe9a52398eb816c416c7573c9f847cdfcab5aacf03bc60f6c00f1ef596d2f  $archive" | shasum -a 256 -c -
tar -xzf "$archive" -C "$destination" mbx
rm "$archive"
"$destination/mbx" --version
