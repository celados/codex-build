# Patch layout

Each feature gets its own directory containing structural apply and satisfied
rules plus any regression rule or test fixture needed to detect upstream drift.

Planned groups:

- `mention/` — patches Codex's existing module using `mention-fs` behavior;
  it must not add a replacement provider
- `update-channel/`
- `computer-use/`, only if the signing boundary requires an explicit policy

Patch specifications are added only after their target seams have been verified
against a pinned upstream commit.
