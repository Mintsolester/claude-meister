---
name: install-claude-meister
description: Install or update Claude_Meister using commands that are implemented in install.py.
user-invokable: true
argument-hint: "[full|runtime-only|memory-only|wiki-only|no-wiki|update|inject-here]"
compatibility: claude-code
license: MIT
metadata:
  plugin: claude-meister
---

Use this skill to run installation workflows for this repository.

## Arguments

Optional mode argument:
- `full`
- `runtime-only`
- `memory-only`
- `wiki-only`
- `no-wiki`
- `update`
- `inject-here`

Default mode: `full`.

## Workflow

1. Confirm the current working directory is the repo root containing `install.py`.
2. Choose one command:
   - `full` -> `python install.py --full`
   - `runtime-only` -> `python install.py --runtime-only`
   - `memory-only` -> `python install.py --memory-only`
   - `wiki-only` -> `python install.py --wiki-only`
   - `no-wiki` -> `python install.py --no-wiki`
   - `update` -> `python install.py --update`
   - `inject-here` -> `python install.py --inject-here`
3. After installation or update, run `python install.py --verify`.
4. If verification fails, invoke `/troubleshoot-claude-meister` and include the failing check output.

## Guardrails

- Use only flags supported by `install.py`.
- Keep commands non-interactive unless the user asks for interactive mode.
- Do not invent paths outside this repository.
