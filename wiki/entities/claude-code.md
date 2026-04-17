---
title: Claude Code
type: entity
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Claude Code overview]]", "[[raw/How Claude Code works]]", "[[raw/Best Practices for Claude Code]]", "[[raw/Common workflows]]", "[[raw/Features overview]]"]
tags: [claude-code, agent, coding, cli, ide]
---

# Claude Code

Claude Code is Anthropic's agentic coding tool. It reads your codebase, edits files, runs commands, and integrates with development tools. Available as CLI, IDE extension (VS Code, JetBrains), desktop app, and web app (claude.ai/code).

## How It Works: The Agentic Loop

Claude Code operates through three phases that blend together:
1. **Gather context** — search files, read code, understand the problem
2. **Take action** — edit files, run commands, make changes
3. **Verify results** — run tests, check output, confirm the fix

The loop repeats until the task is complete. You can interrupt at any point to steer.

## Built-in Tools

| Category | Capabilities |
|---|---|
| **File operations** | Read, edit, create, rename files |
| **Search** | Glob (file patterns), Grep (content search) |
| **Execution** | Shell commands, builds, tests, git |
| **Web** | Web search, fetch documentation |
| **Code intelligence** | Type errors, jump to definition (via plugins) |

## Key Features

### CLAUDE.md (Memory)
A markdown file at project root read every session. Contains coding standards, architecture decisions, workflow rules. Use `/init` to generate a starter. Keep it short — bloated files cause Claude to ignore instructions.

CLAUDE.md locations (all loaded):
- `~/.claude/CLAUDE.md` — global, all sessions
- `./CLAUDE.md` — project root, shared via git
- `./CLAUDE.local.md` — personal, gitignored
- Parent/child directories — automatic hierarchical loading

### Auto Memory
Claude saves learnings automatically (build commands, patterns, preferences) across sessions. Stored in `MEMORY.md`. First 200 lines or 25KB load at session start.

### Permissions & Safety
- **Default mode:** asks before file edits and shell commands
- **Auto-accept edits:** edits freely, asks for commands
- **Plan mode:** read-only analysis, produces a plan for approval
- **Auto mode:** background safety classifier approves/blocks actions
- **Checkpoints:** every edit is snapshotted, reversible with `Esc+Esc` or `/rewind`

### Skills
`SKILL.md` files in `.claude/skills/` — domain knowledge and reusable workflows. Loaded on demand (not every session). Invoked with `/skill-name`. Can be user-invokable only with `disable-model-invocation: true`.

### Hooks
Shell commands that run automatically at specific points (before/after file edits, before commits). Configured in `.claude/settings.json`. Deterministic — unlike CLAUDE.md instructions which are advisory.

### Subagents
Specialized agents in `.claude/agents/` with their own context windows and tool access. Great for isolated research, code review, security audits. Each gets fresh context, keeping main conversation clean.

### Plugins
Bundled packages of skills, hooks, agents, MCP servers. Install with `/plugin`. Code intelligence plugins are especially valuable for typed languages.

## Best Practices

### #1: Give Claude verification
Include tests, screenshots, expected outputs. This is the single highest-leverage thing.

### #2: Explore first, then plan, then code
Use Plan Mode (`Shift+Tab` twice) for complex problems. Skip for trivial fixes.

### #3: Be specific upfront
Reference files, mention constraints, point to patterns. Vague prompts work but need more steering.

### #4: Manage context aggressively
- `/clear` between unrelated tasks
- `/compact <focus>` to summarize selectively
- Use subagents for research (they don't bloat your context)
- After 2 failed corrections, `/clear` and start fresh with a better prompt

### #5: Delegate, don't dictate
Give context and direction. Don't specify which files to read or commands to run.

## Execution Environments

| Environment | Where | Use case |
|---|---|---|
| Local | Your machine | Default. Full access |
| Cloud | Anthropic VMs | Web app, offload tasks |
| Remote Control | Your machine via browser | Web UI + local files |

## Interfaces

Terminal CLI, VS Code, JetBrains, Desktop app, Web (claude.ai/code), Slack, GitHub Actions, GitLab CI/CD, Chrome extension.

## Common Workflows
- Explore unfamiliar codebases
- Fix bugs (paste error, let Claude trace + fix + verify)
- Refactor code
- Write tests
- Create PRs (`/commit`, direct git integration)
- Schedule recurring tasks (cloud, desktop, `/loop`)
- Unix-style piping (`cat log | claude -p "explain"`)
- Parallel sessions via git worktrees (`claude --worktree feature-auth`)

## See Also
- [[claude-models|Claude Models]]
- [[agent-sdk|Agent SDK]]
- [[mcp|Model Context Protocol]]
- [[agentic-patterns|Agentic Patterns]]
- [[prompt-engineering|Prompt Engineering]]
