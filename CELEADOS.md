---
type: Playbook
title: Celados Codex Build Distribution
description: Build and release boundary for a minimally patched Codex CLI on Apple Silicon macOS.
status: active
when: Building, patching, releasing, or diagnosing the custom Codex distribution.
---

# Celados Codex Build Distribution

This repository owns only the downstream patch set, build and release scripts,
and the mapping from custom versions to upstream Codex commits. It must not
become a long-lived source fork.

## Accepted boundaries

- Build macOS arm64 artifacts on `[self-hosted, macOS, ARM64]`; do not maintain
  an Apple SDK or osxcross toolchain on Linux.
- Patch Codex's existing mention module in place. `mention-fs` is the behavioral
  reference and reusable implementation source, not a replacement provider or
  a parallel mention stack.
- Preserve the native Codex update prompt. Patch both the version source and
  install action so accepting the prompt cannot escape to an OpenAI, npm, Bun,
  pnpm, or Homebrew distribution.
- Keep this repository separate from Grok Build because GitHub's latest release
  is repository-wide rather than product-scoped.
- Skip only the Computer Use MCP registration until a runtime test proves that
  a custom signature is accepted. A successful CLI build is not evidence for
  that capability; other plugin MCP registrations remain intact.

## Patch contract

Every downstream behavior change should use a structural seam with three
observable states:

1. apply when the known upstream seam exists;
2. skip only when a recognized equivalent upstream implementation exists;
3. fail on unknown drift.

Regression tests belong with behavior patches. `scripts/check-mention.py`
proves the hidden-path behavior against the upstream file-search binary. Build
scripts restore temporary source rewrites even when compilation fails.

## Release gate

The release workflow checks upstream once daily and supports a forceful manual
dispatch. It runs on the persistent Mac mini, retains the Cargo target cache,
caps its disk use, and publishes only from `main`. An unchanged upstream tag is
a successful no-op; patch validation and builds run only for a new tag or an
explicit forced rebuild.
