#!/usr/bin/env python3
"""Resolve the upstream release and a monotonic custom SemVer."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


TAG = re.compile(r"^rust-v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
REPOSITORY = "celados/codex-build"


def gh_json(endpoint: str, *, accept: str | None = None) -> dict[str, object] | None:
    command = ["gh", "api"]
    if accept:
        command.extend(["-H", f"Accept: {accept}"])
    command.append(endpoint)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def parse(tag: str) -> tuple[int, int, int]:
    match = TAG.fullmatch(tag)
    if not match:
        raise SystemExit(f"unsupported release tag: {tag}")
    return tuple(int(match.group(part)) for part in ("major", "minor", "patch"))


def release_provenance(release: dict[str, object]) -> dict[str, object] | None:
    assets = release.get("assets")
    if not isinstance(assets, list):
        return None
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("name") != "provenance.json":
            continue
        asset_id = asset.get("id")
        if not isinstance(asset_id, int):
            return None
        return gh_json(
            f"repos/{REPOSITORY}/releases/assets/{asset_id}",
            accept="application/octet-stream",
        )
    return None


def main() -> None:
    upstream = gh_json("repos/openai/codex/releases/latest")
    if not upstream or not isinstance(upstream.get("tag_name"), str):
        raise SystemExit("could not resolve the latest upstream Codex release")

    upstream_tag = str(upstream["tag_name"])
    major, minor, upstream_patch = parse(upstream_tag)
    custom_patch = upstream_patch + 1000

    latest = gh_json(f"repos/{REPOSITORY}/releases/latest")
    force_release = os.environ.get("FORCE_RELEASE", "false").lower() == "true"
    release = True
    if latest and isinstance(latest.get("tag_name"), str):
        latest_tag = str(latest["tag_name"])
        latest_major, latest_minor, latest_patch = parse(latest_tag)
        if (latest_major, latest_minor) > (major, minor):
            raise SystemExit("custom release channel is ahead of upstream; refusing to regress")
        provenance = release_provenance(latest)
        if (
            not force_release
            and provenance
            and provenance.get("upstream_tag") == upstream_tag
        ):
            release = False
            custom_patch = latest_patch
        if (latest_major, latest_minor) == (major, minor):
            custom_patch = max(custom_patch, latest_patch + int(release))

    version = f"{major}.{minor}.{custom_patch}"
    values = {
        "upstream_tag": upstream_tag,
        "version": version,
        "release_tag": f"rust-v{version}",
        "release": str(release).lower(),
    }
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")
    print(json.dumps(values, sort_keys=True))


if __name__ == "__main__":
    main()
