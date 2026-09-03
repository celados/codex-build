#!/usr/bin/env python3
"""Apply the downstream Codex patch set with explicit drift detection."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Patch:
    name: str
    source: str
    apply_rule: str
    satisfied_rule: str
    expected: int = 1


PATCHES = (
    Patch("mention hidden paths", "codex-rs/tui/src/file_search.rs", "patches/mention/apply.yml", "patches/mention/satisfied.yml"),
    Patch("update release URL", "codex-rs/tui/src/updates.rs", "patches/update-channel/release-url-apply.yml", "patches/update-channel/release-url-satisfied.yml"),
    Patch("standalone installer", "codex-rs/tui/src/update_action.rs", "patches/update-channel/installer-apply.yml", "patches/update-channel/installer-satisfied.yml", 2),
    Patch("standalone update action", "codex-rs/tui/src/update_action.rs", "patches/update-channel/action-apply.yml", "patches/update-channel/action-satisfied.yml"),
    Patch("Computer Use MCP", "codex-rs/core/src/config/mod.rs", "patches/computer-use/apply.yml", "patches/computer-use/satisfied.yml"),
    Patch("reasoning confirmation metadata", "codex-rs/protocol/src/openai_models.rs", "patches/provider-reasoning/metadata-apply.yml", "patches/provider-reasoning/metadata-satisfied.yml"),
    Patch("app-server reasoning confirmation protocol", "codex-rs/app-server-protocol/src/protocol/v2/model.rs", "patches/provider-reasoning/app-server-protocol-apply.yml", "patches/provider-reasoning/app-server-protocol-satisfied.yml"),
    Patch("app-server reasoning confirmation test", "codex-rs/app-server/src/models.rs", "patches/provider-reasoning/app-server-test-apply.yml", "patches/provider-reasoning/app-server-test-satisfied.yml"),
    Patch("app-server reasoning confirmation projection", "codex-rs/app-server/src/models.rs", "patches/provider-reasoning/app-server-forward-apply.yml", "patches/provider-reasoning/app-server-forward-satisfied.yml"),
    Patch("app-server reasoning confirmation fixture", "codex-rs/app-server/tests/suite/v2/model_list.rs", "patches/provider-reasoning/app-server-fixture-apply.yml", "patches/provider-reasoning/app-server-fixture-satisfied.yml"),
    Patch("app-server reasoning confirmation expected vec", "codex-rs/app-server/tests/suite/v2/model_list.rs", "patches/provider-reasoning/app-server-expected-vec-apply.yml", "patches/provider-reasoning/app-server-expected-vec-satisfied.yml"),
    Patch("TUI reasoning confirmation projection", "codex-rs/tui/src/app_server_session.rs", "patches/provider-reasoning/tui-projection-apply.yml", "patches/provider-reasoning/tui-projection-satisfied.yml"),
    Patch("TUI reasoning confirmation round-trip test", "codex-rs/tui/src/app_server_session.rs", "patches/provider-reasoning/tui-roundtrip-test-apply.yml", "patches/provider-reasoning/tui-roundtrip-test-satisfied.yml"),
    Patch("reasoning confirmation literal defaults", "codex-rs", "patches/provider-reasoning/literals-apply.yml", "patches/provider-reasoning/literals-satisfied.yml", 18),
    Patch("reasoning confirmation popup vec defaults", "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs", "patches/provider-reasoning/popup-vec-apply.yml", "patches/provider-reasoning/popup-vec-satisfied.yml"),
    Patch("reasoning confirmation persistence vec default", "codex-rs/tui/src/app/config_persistence.rs", "patches/provider-reasoning/persistence-vec-apply.yml", "patches/provider-reasoning/persistence-vec-satisfied.yml"),
    Patch("reasoning confirmation dynamic vec default", "codex-rs/tui/src/chatwidget/tests/plan_mode.rs", "patches/provider-reasoning/dynamic-vec-apply.yml", "patches/provider-reasoning/dynamic-vec-satisfied.yml"),
    Patch("reasoning confirmation medium vec default", "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs", "patches/provider-reasoning/medium-vec-apply.yml", "patches/provider-reasoning/medium-vec-satisfied.yml"),
    Patch("reasoning confirmation max vec default", "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs", "patches/provider-reasoning/max-vec-apply.yml", "patches/provider-reasoning/max-vec-satisfied.yml"),
    Patch("reasoning confirmation high vec default", "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs", "patches/provider-reasoning/high-vec-apply.yml", "patches/provider-reasoning/high-vec-satisfied.yml"),
    Patch("reasoning confirmation ultra vec default", "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs", "patches/provider-reasoning/ultra-vec-apply.yml", "patches/provider-reasoning/ultra-vec-satisfied.yml"),
    Patch("reasoning confirmation helper", "codex-rs/tui/src/chatwidget/model_popups.rs", "patches/provider-reasoning/helper-apply.yml", "patches/provider-reasoning/helper-satisfied.yml"),
    Patch("auto model reasoning confirmation", "codex-rs/tui/src/chatwidget/model_popups.rs", "patches/provider-reasoning/auto-model-apply.yml", "patches/provider-reasoning/auto-model-satisfied.yml"),
    Patch("reasoning popup confirmation partition", "codex-rs/tui/src/chatwidget/model_popups.rs", "patches/provider-reasoning/popup-partition-apply.yml", "patches/provider-reasoning/popup-partition-satisfied.yml"),
    Patch("advanced reasoning popup confirmation filter", "codex-rs/tui/src/chatwidget/model_popups.rs", "patches/provider-reasoning/advanced-popup-apply.yml", "patches/provider-reasoning/advanced-popup-satisfied.yml"),
    Patch("advanced reasoning popup default confirmation", "codex-rs/tui/src/chatwidget/model_popups.rs", "patches/provider-reasoning/advanced-default-apply.yml", "patches/provider-reasoning/advanced-default-satisfied.yml"),
    Patch("provider confirmation popup description", "codex-rs/tui/src/chatwidget/model_popups.rs", "patches/provider-reasoning/advanced-description-apply.yml", "patches/provider-reasoning/advanced-description-satisfied.yml"),
    Patch("reasoning shortcut confirmation gate", "codex-rs/tui/src/chatwidget/reasoning_shortcuts.rs", "patches/provider-reasoning/shortcut-apply.yml", "patches/provider-reasoning/shortcut-satisfied.yml"),
    Patch("reasoning shortcut confirmation label", "codex-rs/tui/src/chatwidget/reasoning_shortcuts.rs", "patches/provider-reasoning/shortcut-label-apply.yml", "patches/provider-reasoning/shortcut-label-satisfied.yml"),
    Patch("reasoning shortcut preset borrow", "codex-rs/tui/src/chatwidget/reasoning_shortcuts.rs", "patches/provider-reasoning/shortcut-borrow-apply.yml", "patches/provider-reasoning/shortcut-borrow-satisfied.yml"),
    Patch("reasoning confirmation shortcut tests", "codex-rs/tui/src/chatwidget/tests/popups_and_settings.rs", "patches/provider-reasoning/tests-apply.yml", "patches/provider-reasoning/tests-satisfied.yml"),
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
