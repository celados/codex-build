#!/usr/bin/env python3
"""Apply the downstream Codex patch set with explicit drift detection."""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Patch:
    name: str
    source: str
    apply_rule: str
    satisfied_rule: str
    expected: int = 1


@dataclass(frozen=True)
class Overlay:
    name: str
    source: str
    destination: str


OVERLAYS = (
    Overlay(
        "selection accessory module",
        "overlays/codex-rs/tui/src/bottom_pane/selection_accessory.rs",
        "codex-rs/tui/src/bottom_pane/selection_accessory.rs",
    ),
    Overlay(
        "selection accessory tests",
        "overlays/codex-rs/tui/src/bottom_pane/selection_accessory_tests.rs",
        "codex-rs/tui/src/bottom_pane/selection_accessory_tests.rs",
    ),
    Overlay(
        "custom model picker module",
        "overlays/codex-rs/tui/src/chatwidget/custom_model_picker.rs",
        "codex-rs/tui/src/chatwidget/custom_model_picker.rs",
    ),
    Overlay(
        "async completion module",
        "overlays/codex-rs/core/src/session/async_completion.rs",
        "codex-rs/core/src/session/async_completion.rs",
    ),
    Overlay(
        "async completion unit tests",
        "overlays/codex-rs/core/src/session/async_completion_tests.rs",
        "codex-rs/core/src/session/async_completion_tests.rs",
    ),
    Overlay(
        "async completion integration test",
        "overlays/codex-rs/core/tests/suite/async_completion.rs",
        "codex-rs/core/tests/suite/async_completion.rs",
    ),
    Overlay(
        "unified exec background completion",
        "overlays/codex-rs/core/src/unified_exec/background_completion.rs",
        "codex-rs/core/src/unified_exec/background_completion.rs",
    ),
)


PATCHES = (
    Patch("mention hidden paths", "codex-rs/tui/src/file_search.rs", "patches/mention/apply.yml", "patches/mention/satisfied.yml"),
    Patch("update release URL", "codex-rs/tui/src/updates.rs", "patches/update-channel/release-url-apply.yml", "patches/update-channel/release-url-satisfied.yml"),
    Patch("standalone installer", "codex-rs/tui/src/update_action.rs", "patches/update-channel/installer-apply.yml", "patches/update-channel/installer-satisfied.yml", 2),
    Patch("standalone update action", "codex-rs/tui/src/update_action.rs", "patches/update-channel/action-apply.yml", "patches/update-channel/action-satisfied.yml"),
    Patch("Computer Use MCP", "codex-rs/core/src/config/mod.rs", "patches/computer-use/apply.yml", "patches/computer-use/satisfied.yml"),
    Patch("async completion session module", "codex-rs/core/src/session/mod.rs", "patches/async-completion/session-module-apply.yml", "patches/async-completion/session-module-satisfied.yml"),
    Patch("generalized mailbox storage", "codex-rs/core/src/session/input_queue.rs", "patches/async-completion/mailbox-storage-apply.yml", "patches/async-completion/mailbox-storage-satisfied.yml"),
    Patch("generalized mailbox input type", "codex-rs/core/src/session/input_queue.rs", "patches/async-completion/mailbox-input-type-apply.yml", "patches/async-completion/mailbox-input-type-satisfied.yml"),
    Patch("generalized mailbox constructor", "codex-rs/core/src/session/input_queue.rs", "patches/async-completion/mailbox-constructor-apply.yml", "patches/async-completion/mailbox-constructor-satisfied.yml"),
    Patch("standalone mailbox enqueue", "codex-rs/core/src/session/input_queue.rs", "patches/async-completion/mailbox-enqueue-apply.yml", "patches/async-completion/mailbox-enqueue-satisfied.yml"),
    Patch("generalized mailbox pending check", "codex-rs/core/src/session/input_queue.rs", "patches/async-completion/mailbox-pending-apply.yml", "patches/async-completion/mailbox-pending-satisfied.yml"),
    Patch("standalone mailbox wake-up", "codex-rs/core/src/session/input_queue.rs", "patches/async-completion/mailbox-trigger-apply.yml", "patches/async-completion/mailbox-trigger-satisfied.yml"),
    Patch("generalized mailbox drain", "codex-rs/core/src/session/input_queue.rs", "patches/async-completion/mailbox-drain-apply.yml", "patches/async-completion/mailbox-drain-satisfied.yml"),
    Patch("subagent control completion wake-up", "codex-rs/core/src/agent/control.rs", "patches/async-completion/subagent-control-wake-apply.yml", "patches/async-completion/subagent-control-wake-satisfied.yml"),
    Patch("subagent session completion wake-up", "codex-rs/core/src/session/mod.rs", "patches/async-completion/subagent-session-wake-apply.yml", "patches/async-completion/subagent-session-wake-satisfied.yml"),
    Patch("subagent completion test expectation", "codex-rs/core/src/agent/control_tests.rs", "patches/async-completion/subagent-control-tests-apply.yml", "patches/async-completion/subagent-control-tests-satisfied.yml"),
    Patch("unified exec background completion module", "codex-rs/core/src/unified_exec/mod.rs", "patches/async-completion/unified-exec-module-apply.yml", "patches/async-completion/unified-exec-module-satisfied.yml"),
    Patch("durable output-drained signal", "codex-rs/core/src/unified_exec/process.rs", "patches/async-completion/output-drained-signal-apply.yml", "patches/async-completion/output-drained-signal-satisfied.yml"),
    Patch("durable output-drained construction", "codex-rs/core/src/unified_exec/process.rs", "patches/async-completion/output-drained-constructor-apply.yml", "patches/async-completion/output-drained-constructor-satisfied.yml"),
    Patch("durable output-drained accessor", "codex-rs/core/src/unified_exec/process.rs", "patches/async-completion/output-drained-accessor-apply.yml", "patches/async-completion/output-drained-accessor-satisfied.yml"),
    Patch("terminal-result claim field", "codex-rs/core/src/unified_exec/process.rs", "patches/async-completion/terminal-result-claim-field-apply.yml", "patches/async-completion/terminal-result-claim-field-satisfied.yml"),
    Patch("terminal-result claim construction", "codex-rs/core/src/unified_exec/process.rs", "patches/async-completion/terminal-result-claim-constructor-apply.yml", "patches/async-completion/terminal-result-claim-constructor-satisfied.yml"),
    Patch("terminal-result claim accessors", "codex-rs/core/src/unified_exec/process.rs", "patches/async-completion/terminal-result-claim-accessors-apply.yml", "patches/async-completion/terminal-result-claim-accessors-satisfied.yml"),
    Patch("durable output-drained completion", "codex-rs/core/src/unified_exec/async_watcher.rs", "patches/async-completion/output-drained-complete-apply.yml", "patches/async-completion/output-drained-complete-satisfied.yml"),
    Patch("durable output-drained wait", "codex-rs/core/src/unified_exec/async_watcher.rs", "patches/async-completion/output-drained-wait-apply.yml", "patches/async-completion/output-drained-wait-satisfied.yml"),
    Patch("durable output-drained test waits", "codex-rs/core/src/unified_exec/async_watcher_tests.rs", "patches/async-completion/output-drained-tests-apply.yml", "patches/async-completion/output-drained-tests-satisfied.yml", 3),
    Patch("network completion finalizer access", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/network-finish-visibility-apply.yml", "patches/async-completion/network-finish-visibility-satisfied.yml"),
    Patch("released terminal-result claim", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/release-claims-terminal-result-apply.yml", "patches/async-completion/release-claims-terminal-result-satisfied.yml"),
    Patch("refreshed terminal-result claim", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/refresh-claims-terminal-result-apply.yml", "patches/async-completion/refresh-claims-terminal-result-satisfied.yml"),
    Patch("session-close terminal-result claim", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/terminate-all-claims-terminal-results-apply.yml", "patches/async-completion/terminate-all-claims-terminal-results-satisfied.yml"),
    Patch("serialized process termination", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/terminate-process-serialization-apply.yml", "patches/async-completion/terminate-process-serialization-satisfied.yml"),
    Patch("serialized process exit recheck", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/terminate-process-recheck-apply.yml", "patches/async-completion/terminate-process-recheck-satisfied.yml"),
    Patch("immediate exec yield", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/zero-yield-apply.yml", "patches/async-completion/zero-yield-satisfied.yml"),
    Patch("spawn exec completion", "codex-rs/core/src/unified_exec/process_manager.rs", "patches/async-completion/spawn-exec-completion-apply.yml", "patches/async-completion/spawn-exec-completion-satisfied.yml"),
    Patch("async completion integration module", "codex-rs/core/tests/suite/mod.rs", "patches/async-completion/integration-module-apply.yml", "patches/async-completion/integration-module-satisfied.yml"),
    Patch("model picker config action", "codex-rs/config/src/tui_keymap.rs", "patches/model-picker/config-apply.yml", "patches/model-picker/config-satisfied.yml"),
    Patch("model picker runtime field", "codex-rs/tui/src/keymap.rs", "patches/model-picker/runtime-field-apply.yml", "patches/model-picker/runtime-field-satisfied.yml"),
    Patch("model picker runtime resolution", "codex-rs/tui/src/keymap.rs", "patches/model-picker/runtime-resolution-apply.yml", "patches/model-picker/runtime-resolution-satisfied.yml"),
    Patch("model picker default binding", "codex-rs/tui/src/keymap.rs", "patches/model-picker/default-binding-apply.yml", "patches/model-picker/default-binding-satisfied.yml"),
    Patch("model picker binding inventory", "codex-rs/tui/src/keymap.rs", "patches/model-picker/main-bindings-apply.yml", "patches/model-picker/main-bindings-satisfied.yml"),
    Patch("model picker conflict validation", "codex-rs/tui/src/keymap.rs", "patches/model-picker/conflicts-apply.yml", "patches/model-picker/conflicts-satisfied.yml"),
    Patch("model picker action binding inventory", "codex-rs/tui/src/keymap/bindings.rs", "patches/model-picker/bindings-apply.yml", "patches/model-picker/bindings-satisfied.yml"),
    Patch("model picker action catalog", "codex-rs/tui/src/keymap_setup/actions.rs", "patches/model-picker/action-catalog-apply.yml", "patches/model-picker/action-catalog-satisfied.yml"),
    Patch("model picker configurable slot", "codex-rs/tui/src/keymap_setup/actions.rs", "patches/model-picker/binding-slot-apply.yml", "patches/model-picker/binding-slot-satisfied.yml"),
    Patch("model picker chat dispatch", "codex-rs/tui/src/chatwidget/interaction.rs", "patches/model-picker/dispatch-apply.yml", "patches/model-picker/dispatch-satisfied.yml"),
    Patch("model picker keymap tests", "codex-rs/tui/src/keymap.rs", "patches/model-picker/keymap-tests-apply.yml", "patches/model-picker/keymap-tests-satisfied.yml"),
    Patch("model picker draft test", "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs", "patches/model-picker/draft-test-apply.yml", "patches/model-picker/draft-test-satisfied.yml"),
    Patch("model picker accessory module seam", "codex-rs/tui/src/bottom_pane/mod.rs", "patches/model-picker/accessory-module-apply.yml", "patches/model-picker/accessory-module-satisfied.yml"),
    Patch("custom model picker module seam", "codex-rs/tui/src/chatwidget.rs", "patches/model-picker/custom-module-apply.yml", "patches/model-picker/custom-module-satisfied.yml"),
    Patch("model picker accessory imports", "codex-rs/tui/src/bottom_pane/list_selection_view.rs", "patches/model-picker/accessory-imports-apply.yml", "patches/model-picker/accessory-imports-satisfied.yml"),
    Patch("model picker accessory field", "codex-rs/tui/src/bottom_pane/list_selection_view.rs", "patches/model-picker/accessory-field-apply.yml", "patches/model-picker/accessory-field-satisfied.yml"),
    Patch("model picker accessory state", "codex-rs/tui/src/bottom_pane/list_selection_view.rs", "patches/model-picker/accessory-state-apply.yml", "patches/model-picker/accessory-state-satisfied.yml"),
    Patch("model picker accessory rendering", "codex-rs/tui/src/bottom_pane/list_selection_view.rs", "patches/model-picker/accessory-render-apply.yml", "patches/model-picker/accessory-render-satisfied.yml"),
    Patch("model picker accessory acceptance", "codex-rs/tui/src/bottom_pane/list_selection_view.rs", "patches/model-picker/accessory-accept-apply.yml", "patches/model-picker/accessory-accept-satisfied.yml"),
    Patch("model picker accessory keys", "codex-rs/tui/src/bottom_pane/list_selection_view.rs", "patches/model-picker/accessory-keys-apply.yml", "patches/model-picker/accessory-keys-satisfied.yml"),
)


def matches(repo: Path, rule: Path, source: Path) -> int:
    result = subprocess.run(
        ["ast-grep", "scan", "--rule", str(rule), "--json=compact", str(source)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return len(json.loads(result.stdout))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    source_root = args.source.resolve()
    if not args.check:
        # Preflight every seam before the first write so a later drift failure cannot leave a
        # partially patched source tree when this script is invoked outside build.sh.
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--source",
                str(source_root),
                "--check",
            ],
            cwd=repo,
            check=True,
        )
    for overlay in OVERLAYS:
        source = repo / overlay.source
        destination = source_root / overlay.destination
        if destination.exists():
            if not filecmp.cmp(source, destination, shallow=False):
                raise SystemExit(
                    f"unknown upstream drift for {overlay.name}: destination already exists"
                )
            print(f"satisfied: {overlay.name}")
            continue
        if args.check:
            print(f"applicable: {overlay.name}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"applied: {overlay.name}")

    for patch in PATCHES:
        apply_rule = repo / patch.apply_rule
        satisfied_rule = repo / patch.satisfied_rule
        source = source_root / patch.source
        apply_count = matches(repo, apply_rule, source)
        satisfied_count = matches(repo, satisfied_rule, source)

        if satisfied_count == patch.expected and apply_count == 0:
            print(f"satisfied: {patch.name}")
            continue
        if apply_count != patch.expected or satisfied_count != 0:
            raise SystemExit(
                f"unknown upstream drift for {patch.name}: "
                f"apply={apply_count}, satisfied={satisfied_count}, expected={patch.expected}"
            )
        if args.check:
            print(f"applicable: {patch.name}")
            continue

        subprocess.run(
            ["ast-grep", "scan", "--rule", str(apply_rule), "--update-all", str(source)],
            cwd=repo,
            check=True,
        )
        post_count = matches(repo, satisfied_rule, source)
        if post_count != patch.expected:
            raise SystemExit(f"patch did not reach its postcondition: {patch.name}")
        print(f"applied: {patch.name}")


if __name__ == "__main__":
    main()
