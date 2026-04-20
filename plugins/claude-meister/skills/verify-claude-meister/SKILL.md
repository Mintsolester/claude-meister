---
name: verify-claude-meister
description: Run verification and test checks for Claude_Meister using repo-defined commands.
user-invokable: true
argument-hint: "[full|runtime-only|memory-only|stats|ship-check]"
compatibility: claude-code
license: MIT
metadata:
  plugin: claude-meister
---

Use this skill to validate installation health and core test status.

## Arguments

Optional mode argument:
- `full`
- `runtime-only`
- `memory-only`
- `stats`
- `ship-check`

Default mode: `full`.

## Workflow

1. Run the primary validation command:
   - `full` -> `python install.py --verify`
   - `runtime-only` -> `python install.py --verify --runtime-only`
   - `memory-only` -> `python install.py --verify --memory-only`
   - `stats` -> `python install.py --stats`
2. If mode is `ship-check`, run this extended regression sequence:
   - `python install.py --verify`
   - `python tests/test_installer.py`
   - `python tests/test_memory_server.py`
   - `python tests/test_usage_report.py`
   - `python tests/test_runtime.py`
3. Report pass or fail for each command and summarize blockers.

## Guardrails

- Do not skip failed commands.
- Keep command output focused on failing lines and summaries.
