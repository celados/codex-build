#!/usr/bin/env python3
"""Write release provenance as deterministic JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--upstream-tag", required=True)
    parser.add_argument("--upstream-commit", required=True)
    parser.add_argument("--builder-commit", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    payload = {
        "builder_commit": args.builder_commit,
        "run_id": args.run_id,
        "upstream_commit": args.upstream_commit,
        "upstream_tag": args.upstream_tag,
        "version": args.version,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
