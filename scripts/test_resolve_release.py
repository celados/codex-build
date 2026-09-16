#!/usr/bin/env python3
"""Regression tests for fail-closed release resolution."""

from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("resolve-release.py")
SPEC = importlib.util.spec_from_file_location("resolve_release", SCRIPT)
assert SPEC and SPEC.loader
resolve_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolve_release)


class ResolveReleaseTests(unittest.TestCase):
    def test_github_api_failure_is_not_treated_as_missing_data(self) -> None:
        failure = subprocess.CompletedProcess(
            args=["gh", "api"],
            returncode=1,
            stdout="",
            stderr="temporary API failure\n",
        )

        with mock.patch.object(resolve_release.subprocess, "run", return_value=failure):
            with self.assertRaisesRegex(
                SystemExit,
                "GitHub API request failed.*temporary API failure",
            ):
                resolve_release.gh_json("repos/celados/codex-build/releases/latest")

    def test_invalid_github_json_fails_closed(self) -> None:
        response = subprocess.CompletedProcess(
            args=["gh", "api"],
            returncode=0,
            stdout="not-json",
            stderr="",
        )

        with mock.patch.object(resolve_release.subprocess, "run", return_value=response):
            with self.assertRaisesRegex(SystemExit, "returned invalid JSON"):
                resolve_release.gh_json("repos/openai/codex/releases/latest")

    def test_downstream_release_requires_provenance(self) -> None:
        release = {"tag_name": "rust-v0.154.1000", "assets": []}

        with self.assertRaisesRegex(SystemExit, "no provenance.json asset"):
            resolve_release.release_provenance(release)


if __name__ == "__main__":
    unittest.main()
