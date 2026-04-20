---
name: troubleshoot-claude-meister
description: Diagnose and resolve Claude_Meister install, verification, and runtime issues using repo troubleshooting guidance.
user-invokable: true
argument-hint: "[install|verify|memory|mcp|runtime|wiki]"
compatibility: claude-code
license: MIT
metadata:
  plugin: claude-meister
---

Use this skill when installation or verification commands fail.

## Arguments

Optional issue category:
- `install`
- `verify`
- `memory`
- `mcp`
- `runtime`
- `wiki`

Default category: `verify`.

## Workflow

1. Reproduce the issue with the relevant command (usually `python install.py --verify`).
2. Read `docs/troubleshooting.md` and find the matching failure pattern.
3. Apply the smallest fix that addresses the observed error.
4. Re-run verification and report what changed.
5. If the issue persists, gather precise diagnostics and propose a targeted next step.

## Guardrails

- Use repository commands and docs as the source of truth.
- Avoid destructive commands unless the user explicitly asks for them.
