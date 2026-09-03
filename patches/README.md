# Patch layout

Each feature gets its own directory containing structural apply and satisfied
rules plus any regression rule or test fixture needed to detect upstream drift.

Patch groups:

- `mention/` — patches Codex's existing module using `mention-fs` behavior;
  it must not add a replacement provider
- `update-channel/`
- `computer-use/` — skips only the signing-bound MCP registration
- `provider-reasoning/` — lets model catalogs opt individual efforts out of the
  built-in Max/Ultra confirmation gate while preserving the safe default
- `model-picker/` — mounts the custom model-plus-effort picker through narrow
  list-row and shortcut seams; its implementation remains under `overlays/`

Each group has an apply rule and a satisfied rule. `scripts/apply-patches.py`
requires exactly one recognized state and rejects ambiguous or unknown upstream
changes.
