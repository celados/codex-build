#!/usr/bin/env python3
"""Benchmark the published build independently of newer upstream patch drift."""

import importlib.util
import json
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "release", Path(__file__).with_name("resolve-release.py")
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
latest = release.gh_json(f"repos/{release.REPOSITORY}/releases/latest")
provenance = release.release_provenance(latest)
upstream_tag = provenance["upstream_tag"]
version = provenance["version"]
release.parse(upstream_tag)
release.parse(f"rust-v{version}")
values = {"upstream_tag": upstream_tag, "version": version, "release": "true"}
with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
    for key, value in values.items():
        output.write(f"{key}={value}\n")
print(json.dumps(values))
