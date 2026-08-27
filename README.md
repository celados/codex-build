# Codex Build

Custom Apple Silicon macOS distribution of
[OpenAI Codex](https://github.com/openai/codex), maintained as a thin patch
layer rather than a source fork.

## Status

The distribution boundary is established, but no binary is published yet.
The first release is blocked on three explicit contracts:

- patch Codex's existing mention module so its filesystem discovery and ignore
  behavior adopts the proven `mention-fs` rules, without introducing a new
  provider or replacing the module boundary;
- retain the native update prompt while routing version checks and installation
  to this repository's releases;
- decide how the custom build handles Computer Use's OpenAI signing boundary.

## Build policy

macOS artifacts are built and smoke-tested on the Celados Apple Silicon Mac
mini runners. Linux may perform source and patch checks, but is not a supported
macOS cross-compilation environment.

Downstream changes belong in `patches/`. The upstream checkout and Cargo output
will live in the ignored `sources/` directory so persistent runners can reuse
incremental build state without committing upstream code.

Grok Build remains an independent release repository at
[`celados/grok-build`](https://github.com/celados/grok-build). Keeping the two
repositories separate prevents their repository-wide GitHub `latest` releases
from corrupting each other's updater channel.
