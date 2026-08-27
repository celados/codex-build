#!/usr/bin/env python3
"""Resolve the upstream release and a monotonic custom SemVer."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


TAG = re.compile(r"^rust-v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


def gh_json(endpoint: str) -> dict[str, object] | None:
    result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def parse(tag: str) -> tuple[int, int, int]:
    match = TAG.fullmatch(tag)
    if not match:
        raise SystemExit(f"unsupported release tag: {tag}")
    return tuple(int(match.group(part)) for part in ("major", "minor", "patch"))


def main() -> None:
    upstream = gh_json("repos/openai/codex/releases/latest")
    if not upstream or not isinstance(upstream.get("tag_name"), str):
        raise SystemExit("could not resolve the latest upstream Codex release")

    upstream_tag = str(upstream["tag_name"])
    major, minor, upstream_patch = parse(upstream_tag)
    custom_patch = upstream_patch + 1000

    latest = gh_json("repos/celados/codex-build/releases/latest")
    if latest and isinstance(latest.get("tag_name"), str):
        latest_major, latest_minor, latest_patch = parse(str(latest["tag_name"]))
        if (latest_major, latest_minor) > (major, minor):
            raise SystemExit("custom release channel is ahead of upstream; refusing to regress")
        if (latest_major, latest_minor) == (major, minor):
            custom_patch = max(custom_patch, latest_patch + 1)

    version = f"{major}.{minor}.{custom_patch}"
    values = {
        "upstream_tag": upstream_tag,
        "version": version,
        "release_tag": f"rust-v{version}",
    }
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")
    print(json.dumps(values, sort_keys=True))


if __name__ == "__main__":
    main()
