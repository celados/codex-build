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
- `async-completion/` — extends the existing `exec_command` lifecycle.
  `yield_time_ms: 0` immediately returns its normal session ID; the existing
  process manager and `write_stdin` retain management authority. Whichever of
  `write_stdin` or the completion waiter first claims terminal state wins;
  otherwise one bounded standalone result enters Codex's session mailbox.
  The claim is scoped to a live Codex session; restart-persistent delivery is out of scope.
  Background subagent completion keeps its existing mailbox shape with
  `trigger_turn=true`.

Each group has an apply rule and a satisfied rule. `scripts/apply-patches.py`
requires exactly one recognized state and rejects ambiguous or unknown upstream
changes.
