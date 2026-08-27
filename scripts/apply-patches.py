#!/usr/bin/env python3
"""Apply the downstream Codex patch set with explicit drift detection."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Patch:
    name: str
    source: str
    apply_rule: str
    satisfied_rule: str
    expected: int = 1


PATCHES = (
    Patch("mention hidden paths", "codex-rs/tui/src/file_search.rs", "patches/mention/apply.yml", "patches/mention/satisfied.yml"),
    Patch("update release URL", "codex-rs/tui/src/updates.rs", "patches/update-channel/release-url-apply.yml", "patches/update-channel/release-url-satisfied.yml"),
    Patch("standalone installer", "codex-rs/tui/src/update_action.rs", "patches/update-channel/installer-apply.yml", "patches/update-channel/installer-satisfied.yml", 2),
    Patch("standalone update action", "codex-rs/tui/src/update_action.rs", "patches/update-channel/action-apply.yml", "patches/update-channel/action-satisfied.yml"),
    Patch("Computer Use MCP", "codex-rs/core/src/config/mod.rs", "patches/computer-use/apply.yml", "patches/computer-use/satisfied.yml"),
)


def matches(repo: Path, rule: Path, source: Path) -> int:
    result = subprocess.run(
        ["ast-grep", "scan", "--rule", str(rule), "--json=compact", str(source)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return len(json.loads(result.stdout))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    source_root = args.source.resolve()
    for patch in PATCHES:
        apply_rule = repo / patch.apply_rule
        satisfied_rule = repo / patch.satisfied_rule
        source = source_root / patch.source
        apply_count = matches(repo, apply_rule, source)
        satisfied_count = matches(repo, satisfied_rule, source)

        if satisfied_count == patch.expected and apply_count == 0:
            print(f"satisfied: {patch.name}")
            continue
        if apply_count != patch.expected or satisfied_count != 0:
            raise SystemExit(
                f"unknown upstream drift for {patch.name}: "
                f"apply={apply_count}, satisfied={satisfied_count}, expected={patch.expected}"
            )
        if args.check:
            print(f"applicable: {patch.name}")
            continue

        subprocess.run(
            ["ast-grep", "scan", "--rule", str(apply_rule), "--update-all", str(source)],
            cwd=repo,
            check=True,
        )
        post_count = matches(repo, satisfied_rule, source)
        if post_count != patch.expected:
            raise SystemExit(f"patch did not reach its postcondition: {patch.name}")
        print(f"applied: {patch.name}")


if __name__ == "__main__":
    main()
