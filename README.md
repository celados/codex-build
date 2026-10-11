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
- `Alt+P` opens the custom model-and-effort picker without clearing the composer
  draft; Up/Down selects a model, Left/Right adjusts that row's effort, and Enter
  commits both; every effort declared by the provider remains directly selectable;
- the Computer Use MCP server is skipped because custom-signature startup has
  not been proven compatible. Other plugin MCP servers remain enabled.

Install or update the latest release with:

```sh
curl -fsSL https://raw.githubusercontent.com/celados/codex-build/main/install.sh | sh
```

The installer checks the installed version before downloading an artifact and
validates its checksum. It requires `rg` (ripgrep), which it copies into the local
package alongside the CLI, code-mode host and package metadata. Versioned packages
live under `$CODEX_INSTALL_DIR/.codex-build/releases/` (default
`~/.local/bin/.codex-build/releases/`); the public executables are symlinks.

When a managed daemon is running, the installer selects and pins the new CLI
package with `codex app-server daemon update --from-cli --yes`. Upstream restarts
the running daemon during that update. Active or queued work may be interrupted.
The installer verifies that the CLI, daemon package and running server versions
match, and fails if synchronization fails. Re-running an installation also repairs
a stale running daemon without downloading the archive again. A first install
leaves daemon startup to the next interactive CLI invocation.

## Picker models

Set `CODEX_PICKER_MODELS` in the environment that launches Codex to choose which
models the custom `Alt+P` picker offers, and in what order:

```sh
CODEX_PICKER_MODELS='6/{sol,astra,luna};5.6/sol' codex
```

Groups are separated by `;`. Each group is `<version>/{<codename>,...}`
(braces optional for one codename) and expands to `gpt-<version>-<codename>`;
a bare `<version>` such as `5.5` names `gpt-5.5`. The picker shows only the
listed models, in the written order, without marking a default. Listed
models the provider does not currently offer are skipped.

For a persistent preference, export the variable from your shell startup file
(for fish: `set -gx CODEX_PICKER_MODELS '6/{sol,astra,luna}'`) and start Codex
from a new shell. Desktop launchers must receive the variable separately.

This controls only the picker; the `model` configuration still controls the
startup model. The picker marks the current model and follows upstream in omitting
default labels.
If the variable is unset, malformed (the whole value is then ignored), or
matches no offered model, the provider's list and order are unchanged.
No model name is hardcoded as the fallback.

## Binary pairing

Releases ship `codex` and `codex-code-mode-host` in a single archive, and the
installer writes both. Codex resolves the host from its own directory and the
two exchange an IPC schema that upstream extends without bumping the protocol
version, so a host from a different upstream tag fails every tool call before
it reaches a shell. The CLI embeds no V8, so there is no in-process fallback to
absorb the mismatch. The installer switches the host symlink before the CLI symlink so an interrupted
run never leaves a new CLI next to an old host.

## Build policy

macOS artifacts are checked daily at 04:17 in Asia/Shanghai and built only when
the latest stable upstream tag changes. They are built and smoke-tested on the
Celados Apple Silicon Mac mini runners. Apple Silicon macOS is the distribution's
only supported build target. A manual workflow dispatch can force a rebuild of
an already released upstream tag.

Small upstream seams belong in `patches/`. Custom-build-owned modules live in
`overlays/` and are copied into the disposable upstream checkout before those
seams are applied. CI creates a fresh builder checkout and ignored `sources/`
directory from the release tag on every run, then deletes that workspace after
the attempt. CI uses a pinned, checksum-verified [mbx](https://mr-boxington.jdx.dev/)
binary for local compiler caching. The Cargo target stays inside the disposable
builder; only mbx objects (12 GiB budget, 13 GiB physical fallback ceiling), Cargo
downloads (4 GiB), and V8 downloads (1 GiB) survive. Learned incremental state and
managed targets are disabled. Build scripts execute normally because V8 writes
its native archive outside Cargo's `OUT_DIR`, which build-script caching does not
restore. These are per-runner retention limits, not limits
on temporary build space; builds still require 30 GiB free before starting.

Cleanup runs after success and failure, and daily no-op checks enforce the
physical ceilings. The old persistent Cargo target is removed during migration.
No remote compiler cache or global Cargo shim is installed. A failed mbx
collection discards its rebuildable cache rather than leaving unbounded data.

The manual `cache_trial` input builds the currently published upstream version
with mbx, then rebuilds from an empty target to verify reuse. It never publishes.
Step summaries record elapsed time, sampled peak storage (15-second intervals),
and retained storage after cleanup; mbx logs report hits and bypass reasons.
The ordinary release path runs just one mbx build. Explicit-target native linking
is currently not cached by mbx, so cache hits do not eliminate final link time.

The [2026-09-18 trial](https://github.com/celados/codex-build/actions/runs/35318454314)
on upstream `0.154.0` passed both builds and smoke checks: 15m15s cold, 13m58s
from an empty target with 1,622 cache hits. The preceding Cargo retained-target
baseline was 12m50s, so this trial does not establish a speed improvement over
Cargo's warm cache. The mbx runner retained 7.2 GiB including dependencies after
cleanup; sampled build peaks were 10.9 GiB cold and 12.6 GiB on reuse. Treat this
as bounded-cache adoption, not a demonstrated build-speed optimization.

The code-mode host links V8. The `v8` crate's default prebuilts ship no
sandbox-enabled aarch64-apple-darwin archive, so `scripts/fetch-v8.py` points
Cargo at the pair Codex publishes on its own `rusty-v8-v<crate_version>` tag,
verifies the checksums, and caches them in the ignored `.v8-cache` directory.
Building V8 from source is not part of this pipeline; if upstream renames those
assets the download 404s and the build fails loudly.

`build.sh --check --upstream-ref <tag>` validates every structural seam without
rewriting source. A full build temporarily applies the patches, embeds a custom
SemVer, signs the binary ad hoc, runs the hidden-path regression check, and
restores the upstream checkout on exit.

Grok Build remains an independent release repository at
[`celados/grok-build`](https://github.com/celados/grok-build). Keeping the two
repositories separate prevents their repository-wide GitHub `latest` releases
from corrupting each other's updater channel.
