# Patch layout

Each feature gets its own directory containing structural apply and satisfied
rules plus any regression rule or test fixture needed to detect upstream drift.

Patch groups:

- `mention/` — patches Codex's existing module using `mention-fs` behavior;
  it must not add a replacement provider
- `update-channel/`
- `computer-use/` — skips only the signing-bound MCP registration
- `model-picker/` — mounts the custom model-plus-effort picker through narrow
  list-row and shortcut seams; its implementation remains under `overlays/`
- `background-completion/` — adds an opt-in `exec_command.on_exit=resume_turn`
  policy. Exited processes enqueue a bounded completion item through Codex's
  session input queue, which resumes an idle thread or follows the existing
  active-turn delivery semantics. Plan mode keeps the item queued until a
  user-driven turn starts.

Each group has an apply rule and a satisfied rule. `scripts/apply-patches.py`
requires exactly one recognized state and rejects ambiguous or unknown upstream
changes. Multi-file changes may use a unified diff when their forward and
reverse checks provide the same applicable/satisfied/drift contract.
