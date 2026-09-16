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


def gh_json(endpoint: str, *, accept: str | None = None) -> dict[str, object]:
    command = ["gh", "api"]
    if accept:
        command.extend(["-H", f"Accept: {accept}"])
    command.append(endpoint)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or "gh api exited without an error message"
        raise SystemExit(f"GitHub API request failed for {endpoint}: {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"GitHub API returned invalid JSON for {endpoint}: {error}") from error
    if not isinstance(payload, dict):
        raise SystemExit(f"GitHub API returned a non-object response for {endpoint}")
    return payload


def parse(tag: str) -> tuple[int, int, int]:
    match = TAG.fullmatch(tag)
    if not match:
        raise SystemExit(f"unsupported release tag: {tag}")
    return tuple(int(match.group(part)) for part in ("major", "minor", "patch"))


def release_provenance(release: dict[str, object]) -> dict[str, object]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise SystemExit("latest downstream release has no valid assets list")
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("name") != "provenance.json":
            continue
        asset_id = asset.get("id")
        if not isinstance(asset_id, int):
            raise SystemExit("latest downstream provenance asset has no valid id")
        return gh_json(
            f"repos/{REPOSITORY}/releases/assets/{asset_id}",
            accept="application/octet-stream",
        )
    raise SystemExit("latest downstream release has no provenance.json asset")


def main() -> None:
    upstream = gh_json("repos/openai/codex/releases/latest")
    if not isinstance(upstream.get("tag_name"), str):
        raise SystemExit("could not resolve the latest upstream Codex release")

    upstream_tag = str(upstream["tag_name"])
    major, minor, upstream_patch = parse(upstream_tag)
    custom_patch = upstream_patch + 1000

    latest = gh_json(f"repos/{REPOSITORY}/releases/latest")
    if not isinstance(latest.get("tag_name"), str):
        raise SystemExit("could not resolve the latest downstream Codex release")
    force_release = os.environ.get("FORCE_RELEASE", "false").lower() == "true"
    release = True
    latest_tag = str(latest["tag_name"])
    latest_major, latest_minor, latest_patch = parse(latest_tag)
    if (latest_major, latest_minor) > (major, minor):
        raise SystemExit("custom release channel is ahead of upstream; refusing to regress")
    provenance = release_provenance(latest)
    if not force_release and provenance.get("upstream_tag") == upstream_tag:
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
