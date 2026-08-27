---
type: Playbook
title: Celados Codex Build Distribution
description: Build and release boundary for a minimally patched Codex CLI on Apple Silicon macOS.
status: design
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
- Treat Computer Use as unavailable until a runtime test proves that a custom
  signature is accepted. A successful CLI build is not evidence for that
  capability.

## Patch contract

Every downstream behavior change should use a structural seam with three
observable states:

1. apply when the known upstream seam exists;
2. skip only when a recognized equivalent upstream implementation exists;
3. fail on unknown drift.

Regression tests belong with behavior patches. Build scripts must restore their
temporary source rewrites even when compilation fails.

## Release gate

Do not add a scheduled release workflow until the mention patch, updater
routing, and the Computer Use policy are implemented and tested together. The
first workflow should begin as manual dispatch on the persistent Mac mini,
retain `sources/target`, cap its disk use, and publish only from `main`.
