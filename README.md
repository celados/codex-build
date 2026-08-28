# Codex Build

Custom Apple Silicon macOS distribution of
[OpenAI Codex](https://github.com/openai/codex), maintained as a thin patch
layer rather than a source fork.

## Status

The repository builds the latest stable upstream Codex release for Apple
Silicon macOS with a small, drift-detecting patch set:

- the existing mention search excludes hidden paths while continuing to honor
  Codex's normal ignore-file behavior; both mention v1 and v2 share this path;
- the native update prompt remains enabled, but release checks and accepted
  updates stay on `celados/codex-build`;
- the Computer Use MCP server is skipped because custom-signature startup has
  not been proven compatible. Other plugin MCP servers remain enabled.

Install or update the latest release with:

```sh
curl -fsSL https://raw.githubusercontent.com/celados/codex-build/main/install.sh | sh
```

The installer checks the target binary's version before downloading an
artifact. Re-running it at the latest version is a no-op. Downloaded artifacts
use a temporary directory that is removed on exit; the installer does not keep
a version cache to prune.

## Build policy

macOS artifacts are checked daily and built only when the latest stable upstream
tag changes. They are built and smoke-tested on the Celados Apple Silicon Mac
mini runners. Linux may perform source and patch checks, but is not a supported
macOS cross-compilation environment. A manual workflow dispatch can force a
rebuild of an already released upstream tag.

Downstream changes belong in `patches/`. The upstream checkout and Cargo output
will live in the ignored `sources/` directory so persistent runners can reuse
incremental build state without committing upstream code.

`build.sh --check --upstream-ref <tag>` validates every structural seam without
rewriting source. A full build temporarily applies the patches, embeds a custom
SemVer, signs the binary ad hoc, runs the hidden-path regression check, and
restores the upstream checkout on exit.

Grok Build remains an independent release repository at
[`celados/grok-build`](https://github.com/celados/grok-build). Keeping the two
repositories separate prevents their repository-wide GitHub `latest` releases
from corrupting each other's updater channel.
