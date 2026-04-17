---
title: Agent SDK
type: entity
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Agent SDK overview]]", "[[raw/Agent SDK reference - Python]]", "[[raw/Agent SDK reference - TypeScript]]"]
tags: [agent-sdk, sdk, agents, python, typescript]
---

# Claude Agent SDK

Build production AI agents with Claude Code as a library. Formerly "Claude Code SDK" — renamed to Claude Agent SDK.

Available in **Python** (`claude_agent_sdk`) and **TypeScript** (`@anthropic-ai/claude-agent-sdk`).

## What It Does

The Agent SDK gives you the same tools, agent loop, and context management that power [[claude-code|Claude Code]], programmable:

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"]),
    ):
        print(message)

asyncio.run(main())
```

Key difference from the Client SDK: with the **Client SDK**, you implement the tool loop yourself. With the **Agent SDK**, Claude handles tools autonomously.

## Built-in Tools

| Tool | What it does |
|---|---|
| Read | Read any file |
| Write | Create new files |
| Edit | Precise edits to existing files |
| Bash | Run terminal commands |
| Glob | Find files by pattern |
| Grep | Search content with regex |
| WebSearch | Search the web |
| WebFetch | Fetch web page content |
| AskUserQuestion | Ask user clarifying questions |

## Claude Code Features in SDK

Set `setting_sources=["project"]` to enable:
- **Skills** (`.claude/skills/*/SKILL.md`)
- **Slash commands** (`.claude/commands/*.md`)
- **Memory** (`CLAUDE.md`)
- **Plugins** (programmatic via `plugins` option)
- **Hooks** — intercept and control agent behavior
- **Subagents** — delegate work to specialized agents
- **MCP** — connect to external tools
- **Sessions** — persist and resume conversations

## Agent SDK vs Client SDK

| | Client SDK | Agent SDK |
|---|---|---|
| Tool execution | You implement | Built-in |
| Agent loop | You build | Provided |
| Use case | Direct API access | Full autonomous agents |

## Branding

If using in products:
- Allowed: "Claude Agent", "Powered by Claude"
- Not allowed: "Claude Code" or Claude Code branding

## See Also
- [[claude-code|Claude Code]]
- [[claude-api|Claude API]]
- [[tool-use|Tool Use]]
- [[agentic-patterns|Agentic Patterns]]
