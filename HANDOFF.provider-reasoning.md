---
type: Handoff
title: Provider reasoning confirmation and model picker
description: >
  Handoff for implementing Codex provider-owned reasoning confirmation metadata
  and a draft-preserving model picker shortcut as ast-grep downstream patches.
status: complete
generated:
  by: agent/Codex-GPT-5
  at: 2026-09-02T22:49:00+0800
updated:
  by: agent/Codex-GPT-5
  at: 2026-09-03T09:54:04+0800
tags:
  - codex-build
  - prism
  - ast-grep
  - handoff
---

# Handoff: provider reasoning confirmation and model picker

## Why this is being handed off

The previous attempt produced a runnable prototype but chose the wrong delivery
mechanism: it generated a large unified Git diff, including generated schemas
and mechanical updates, instead of writing the required ast-grep patch rules.
That work was removed. Do not continue from that diff; start from the clean
state and the constraints below.

## Objective

Implement two related behaviors in the custom Codex distribution:

1. A model catalog may explicitly declare whether a reasoning effort requires
   confirmation. If the declaration is absent, current OpenAI behavior must be
   preserved: `Max` and `Ultra` still require explicit confirmation.
2. A configurable Chat action named `open_model_picker` opens the model picker
   directly. It must not clear or submit the composer draft. A proposed default
   is `Alt+M`, but it must be registered as a real, configurable keymap action.

For Prism-projected third-party models such as GLM with `low`, `high`, and
`max`, the provider's `max` should be selectable directly when the catalog
marks it as not requiring confirmation. Prism must not remap or rewrite the
provider's wire-level effort value.

## Current state

- `projects/codex-build` has a clean baseline at `dab2dfd`; the only intended
  untracked file is this handoff document.
- `./build.sh --check --upstream-ref rust-v0.152.0` passes on the clean baseline.
- There is no valid downstream Codex patch for this task yet.
- `projects/prism` contains a small, uncommitted design reference in
  `scripts/sync-codex-config.ts`: generated Codex reasoning levels currently add
  `requires_confirmation: false`. Focused tests were updated in
  `scripts/sync-codex-config.test.ts`.
- `projects/prism/docs/DESIGN.md` is also modified and is unrelated to this
  handoff; preserve it and do not stage or revert it as part of this task.
- `/Users/dio/Sources/agents/codex` may be used as a read-only upstream source
  reference, but it is not the deliverable location.

## Required implementation boundary

All Codex changes must live in `projects/codex-build/patches/**` and be wired
into `scripts/apply-patches.py` through the existing patch mechanism.

Use ast-grep apply and satisfied rules for every patch group. Do not add a
Git unified diff, binary generated artifact, broad schema dump, or opaque
catch-all patch. If a proposed field causes so much generated or mechanical
churn that it cannot be represented cleanly as ast-grep patches, stop and
narrow the design first.

Validate against the stable upstream tag used by the release pipeline, not an
unrelated main checkout. The current target is `rust-v0.152.0`. Treat
`projects/codex-build/sources` as builder-owned; use it for validation, but do
not make it the source of truth.

## Suggested patch groups

### Reasoning confirmation metadata

Expose a provider-owned confirmation flag through the model-catalog seam and
make the TUI reasoning shortcut use that declaration instead of hard-coding
every non-default tier as unavailable.

Relevant current seams include:

- `codex-rs/protocol/src/openai_models.rs` defines
  `ReasoningEffortPreset` and its supported effort metadata.
- `codex-rs/tui/src/chatwidget/reasoning_shortcuts.rs` partitions normal and
  advanced choices and blocks direct entry into `Max`/`Ultra`.
- `codex-rs/tui/src/chatwidget/model_popups.rs` owns the normal reasoning popup
  and explicit advanced reasoning popup.

Preserve these existing properties:

- Missing metadata must keep the old safe behavior for `Max` and `Ultra`.
- Explicit `requires_confirmation: false` must allow direct selection.
- Prism still forwards the original effort value unchanged.

### Model picker shortcut

Add a real keymap action rather than a hidden hard-coded key. It should be
registered consistently across the keymap definition, config type, action
catalog, default binding, and Chat event handling.

Relevant current seams include:

- `codex-rs/tui/src/keymap.rs`
- `codex-rs/tui/src/keymap/bindings.rs`
- `codex-rs/tui/src/keymap_setup/actions.rs`
- `codex-rs/config/src/tui_keymap.rs`
- `codex-rs/tui/src/chatwidget/model_popups.rs`
- `codex-rs/tui/src/chatwidget/interaction.rs`

The shortcut must be handled before normal composer input reaches the slash
dispatch path. `/model` currently goes through slash-command submission and
clears the composer draft; do not reuse that path for the shortcut.

## Suggested Prism projection

`projects/prism/scripts/sync-codex-config.ts` currently adds:

```ts
requires_confirmation: false
```

to each projected reasoning level. The rationale is that Prism forwards
provider-declared values unchanged, so provider effort ladders own their UI
semantics and must not inherit Codex/OpenAI's `Max` confirmation rule.

This small change may be retained, but only after the Codex catalog contract is
implemented and reviewed.

## Verification gates

Run at least these checks from a clean working state:

```sh
cd projects/codex-build
./build.sh --check --upstream-ref rust-v0.152.0
```

After applying the final patches to a validation checkout:

```sh
cargo check -p codex-tui -p codex-app-server-protocol -p codex-config
```

For the Prism design reference:

```sh
cd projects/prism
bun run config:typecheck
bun test scripts/sync-codex-config.test.ts
```

Add focused tests for both new behaviors:

- absent metadata keeps `Max` behind explicit confirmation;
- `requires_confirmation: false` allows the reasoning shortcut to select `max`;
- `Alt+M` opens the model picker while preserving a non-empty composer draft;
- remapping or unbinding `open_model_picker` behaves consistently.

If the change remains medium-sized after the ast-grep implementation, send it
for independent review before release work.

## Completion

Implemented as narrow ast-grep apply/satisfied rules under
`patches/provider-reasoning/` and `patches/model-picker/`, wired through
`scripts/apply-patches.py`.

- `requires_confirmation` is optional provider metadata. Missing metadata keeps
  the existing Max/Ultra confirmation boundary; explicit `false` permits direct
  selection.
- `chat.open_model_picker` is a configurable keymap action with an `Alt+M`
  default. It opens before composer input dispatch and preserves the draft.
- Prism's projection emits `requires_confirmation: false` without rewriting the
  provider effort value.
- Patch applicability and post-format idempotency pass against the current
  stable release, `rust-v0.153.0`. The TUI, app-server, app-server protocol,
  and config Cargo check passes; all seven focused behavior and model-list
  projection tests pass. Prism typechecking and its seven focused projection
  tests pass.

### Review resolution

The P1 review finding was valid and is resolved. `requires_confirmation` now
crosses every runtime boundary used by the TUI:

```text
ModelPreset
  -> app-server ReasoningEffortOption
  -> model/list JSON
  -> TUI ReasoningEffortPreset
```

Both server-side projection and TUI reconstruction have focused tests using
`Some(false)`, so Prism's provider-owned `max` semantics no longer disappear at
app-server bootstrap.

A broader `codex-tui` run before the final keymap-editor fix passed 4,006 tests
and failed 38. The structural action-coverage failure was then fixed and passed
in the focused rerun; the other reported failures were snapshot/rendering drift,
including expected keymap-picker changes plus update/status/terminal snapshots
outside this handoff's seams. The full suite was not rerun after that fix.
Snapshot artifacts are intentionally not added because this handoff forbids
generated downstream artifacts. Independent review remains a release gate.

## Explicit non-goals

- Do not remap GLM `max` to another effort value.
- Do not remove the existing OpenAI `Max`/`Ultra` safety behavior when metadata
  is absent.
- Do not make `/model` the mechanism for preserving drafts.
- Do not introduce a long-lived source fork of Codex.
- Do not turn generated schema churn into a downstream unified diff.
