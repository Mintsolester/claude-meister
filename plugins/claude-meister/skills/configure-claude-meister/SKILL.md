---
name: configure-claude-meister
description: Configure Claude_Meister behavior using documented settings and runtime controllers in this repository.
user-invokable: true
argument-hint: "[memory-budget|default-mode|tools-dirs|wiki-path|rebuild-tool-index]"
compatibility: claude-code
license: MIT
metadata:
  plugin: claude-meister
---

Use this skill to apply safe configuration changes aligned with `docs/configuration.md`.

## Arguments

Optional focus argument:
- `memory-budget`
- `default-mode`
- `tools-dirs`
- `wiki-path`
- `rebuild-tool-index`

If no argument is provided, inspect current configuration first and then suggest minimal changes.

## Workflow

1. Read `docs/configuration.md` for field behavior and constraints.
2. Locate and update runtime configuration at `~/.claude_runtime/configs/runtime_config.json` using the requested focus area.
3. Keep JSON valid and preserve unrelated keys.
4. If `rebuild-tool-index` is requested, run `python runtime/controllers/build_tool_index.py` after configuration updates.
5. Confirm changes with a short summary and next verification step (`python install.py --verify`).

## Guardrails

- Prefer minimal edits over broad rewrites.
- Keep settings consistent with values documented in this repository.
