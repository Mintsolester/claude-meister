---
title: Model Context Protocol (MCP)
type: entity
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/What is the Model Context Protocol (MCP)]]", "[[raw/Architecture overview]]", "[[raw/Build an MCP server]]", "[[raw/Build an MCP client]]"]
tags: [mcp, protocol, tools, integration, open-source]
---

# Model Context Protocol (MCP)

MCP is an **open-source standard** for connecting AI applications to external systems. Think of it as USB-C for AI — a standardized way to connect LLMs to data sources, tools, and workflows.

Supported by Claude, ChatGPT, VS Code (Copilot), Cursor, and many others.

## Architecture

### Participants

- **MCP Host** — the AI application (e.g., [[claude-code|Claude Code]], Claude Desktop, VS Code)
- **MCP Client** — component that maintains connection to a server (one per server)
- **MCP Server** — program that provides context to clients

### Two Layers

**Data Layer** (inner): JSON-RPC 2.0 protocol defining messages, lifecycle, and primitives
**Transport Layer** (outer): Communication mechanisms between clients and servers

### Transports

| Transport | How | Use case |
|---|---|---|
| **Stdio** | Standard input/output | Local processes, no network overhead |
| **Streamable HTTP** | HTTP POST + Server-Sent Events | Remote servers, web-based |

## Core Primitives

### Server Primitives (what servers expose)

| Primitive | Purpose | Example |
|---|---|---|
| **Tools** | Executable functions AI can invoke | File ops, API calls, DB queries |
| **Resources** | Data sources for context | File contents, DB records, API responses |
| **Prompts** | Reusable interaction templates | System prompts, few-shot examples |

Discovery via `*/list`, retrieval via `*/get`, execution via `tools/call`.

### Client Primitives (what clients expose)

| Primitive | Purpose |
|---|---|
| **Sampling** | Servers request LLM completions from the host (model-independent) |
| **Elicitation** | Servers request user input or confirmation |
| **Logging** | Servers send log messages for debugging |

### Experimental
- **Tasks** — durable execution wrappers for deferred/batch operations

## Using MCP with Claude Code

```bash
claude mcp add <server-name>    # Add an MCP server
claude mcp                       # Check per-server context costs
```

MCP tool definitions are deferred by default — only names load into context. Full definitions load on demand via [[tool-search|tool search]].

## What MCP Enables

- Access Google Calendar, Notion, Jira from your AI agent
- Generate web apps from Figma designs
- Query databases across an organization
- Connect to Slack, GitHub, Sentry, and hundreds more
- Build custom integrations for any API

## Ecosystem

- **Specification:** [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **SDKs:** TypeScript, Python, and more
- **Inspector:** Development/debugging tool for MCP servers
- **Server registry:** Community and reference implementations

## See Also
- [[claude-code|Claude Code]]
- [[tool-use|Tool Use]]
- [[agent-sdk|Agent SDK]]
