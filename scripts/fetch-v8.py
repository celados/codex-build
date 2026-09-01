#!/usr/bin/env python3
"""Point Cargo at Codex's own sandbox-enabled rusty_v8 artifacts.

The `v8` crate defaults to `denoland/rusty_v8` prebuilts, which publish no
`ptrcomp_sandbox` archive for aarch64-apple-darwin. Upstream builds that archive
itself and publishes it on its own `rusty-v8-v<crate_version>` tag; the naming
contract and the reason Cargo cannot use `RUSTY_V8_MIRROR` are documented in
`sources/third_party/v8/README.md`. A rename during upstream's sandbox rollout
surfaces here as a 404, which is the intended drift signal.
"""

from __future__ import annotations

import argparse
import hashlib
import tomllib
import urllib.request
from pathlib import Path

# Upstream's Bazel graph enables V8's in-process sandbox on Darwin, so the CLI's
# host must link the matching archive rather than the plain release build.
PROFILE = "ptrcomp_sandbox_release"
RELEASE_URL = "https://github.com/openai/codex/releases/download"
CHUNK = 1024 * 1024


def resolve_v8_version(cargo_lock: Path) -> str:
    packages = tomllib.loads(cargo_lock.read_text(encoding="utf-8"))["package"]
    versions = sorted({package["version"] for package in packages if package["name"] == "v8"})
    if len(versions) != 1:
        raise SystemExit(f"expected exactly one resolved v8 crate version, found: {versions}")
    return versions[0]


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(CHUNK), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f"{destination.name}.partial")
    try:
        with urllib.request.urlopen(url, timeout=300) as response:
            partial.write_bytes(response.read())
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def ensure(url: str, destination: Path, expected: str) -> None:
    # The runner keeps this cache across builds, so re-download only on drift.
    if destination.is_file() and digest(destination) == expected:
        return
    download(url, destination)
    if digest(destination) != expected:
        destination.unlink(missing_ok=True)
        raise SystemExit(f"checksum mismatch for {url}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cargo-lock", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    version = resolve_v8_version(args.cargo_lock)
    base = f"{RELEASE_URL}/rusty-v8-v{version}"
    cache = args.cache / f"rusty-v8-{version}-{args.target}"

    archive = cache / f"librusty_v8_{PROFILE}_{args.target}.a.gz"
    binding = cache / f"src_binding_{PROFILE}_{args.target}.rs"
    checksums = cache / f"rusty_v8_{PROFILE}_{args.target}.sha256"

    download(f"{base}/{checksums.name}", checksums)
    expected = {}
    for line in checksums.read_text(encoding="utf-8").splitlines():
        value, _, name = line.strip().partition(" ")
        expected[name.strip()] = value
    for artifact in (archive, binding):
        if artifact.name not in expected:
            raise SystemExit(f"{checksums.name} does not cover {artifact.name}")
        ensure(f"{base}/{artifact.name}", artifact, expected[artifact.name])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"RUSTY_V8_ARCHIVE={archive}\nRUSTY_V8_SRC_BINDING_PATH={binding}\n",
        encoding="utf-8",
    )
    print(f"resolved Codex-built V8 {version} artifacts for {args.target}")


if __name__ == "__main__":
    main()
