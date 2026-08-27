#!/usr/bin/env python3
"""Set Codex's workspace version only when the known upstream sentinel exists."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("version")
    args = parser.parse_args()

    source = args.manifest.read_text(encoding="utf-8")
    sentinel = '[workspace.package]\nversion = "0.0.0"'
    replacement = f'[workspace.package]\nversion = "{args.version}"'
    if source.count(sentinel) != 1:
        raise SystemExit("workspace version sentinel drifted; refusing a broad replacement")
    args.manifest.write_text(source.replace(sentinel, replacement), encoding="utf-8")


if __name__ == "__main__":
    main()
