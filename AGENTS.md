# Codex Build

## Platform boundary

- Ship exactly one target: Apple Silicon macOS (`aarch64-apple-darwin`).
- Keep CI, build scripts, artifacts, installer behavior, and release metadata single-target.
- Treat Linux, Windows, macOS x86_64, Rosetta, cross-compilation, and platform matrices as out of scope unless the user explicitly changes the product boundary.

## Build storage

- Keep compiler and dependency caches bounded on the persistent Mac runners; a cold rebuild is always preferable to unbounded artifact generations.
- Preserve the disposable builder boundary: source checkout and release output belong to one job, while only explicitly capped caches may survive it.
- Before changing cache policy, measure a real release build's peak disk use and verify cleanup after both success and failure.
