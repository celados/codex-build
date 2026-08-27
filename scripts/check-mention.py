#!/usr/bin/env python3
"""Assert that the downstream mention exclusion hides dot paths only."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="codex-build-mention-") as directory:
        root = Path(directory)
        (root / ".cache").mkdir()
        (root / "visible").mkdir()
        (root / ".cache" / "needle-hidden.txt").touch()
        (root / "visible" / "needle-visible.txt").touch()
        result = subprocess.run(
            [str(args.binary.resolve()), "--json", "-C", str(root), "--exclude", "**/.*", "needle"],
            check=True,
            capture_output=True,
            text=True,
        )
        paths = [json.loads(line)["path"] for line in result.stdout.splitlines() if line]
        if paths != ["visible/needle-visible.txt"]:
            raise SystemExit(f"mention hidden-path contract failed: {paths}")
        print("mention hidden-path contract passed")


if __name__ == "__main__":
    main()
