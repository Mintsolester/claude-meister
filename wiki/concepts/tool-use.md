---
title: Tool Use
type: concept
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Tool use with Claude]]", "[[raw/Features overview]]", "[[raw/How tool use works]]", "[[raw/Define tools]]", "[[raw/Handle tool calls]]"]
tags: [tools, function-calling, agents, api]
---

# Tool Use

Tool use lets Claude call functions you define or that Anthropic provides. Claude decides when to call a tool based on the user's request and the tool's description.

## Two Types of Tools

### Client-Side Tools
**You implement and execute.** Claude returns `stop_reason: "tool_use"` with `tool_use` blocks. You execute the operation and send back a `tool_result`.

Includes:
- **User-defined tools** — any function you define with a JSON schema
- **Anthropic-schema tools** — bash, text editor, computer use (you still execute them)
- **Memory tool** — persistent storage across conversations

### Server-Side Tools
**Anthropic executes.** Results appear directly in the response.

| Tool | What it does | Pricing |
|---|---|---|
| **Web Search** | Search the web | $10/1000 searches + tokens |
| **Web Fetch** | Fetch full page content | Free (tokens only) |
| **Code Execution** | Run code in sandbox | Free with web tools; otherwise billed by execution time |
| **Tool Search** | Discover tools from large catalogs | Token-based |

## How the Loop Works

1. You send a message with `tools` definitions
2. Claude decides to use a tool → responds with `tool_use` block
3. You execute the tool and send `tool_result`
4. Claude uses the result to continue reasoning
5. Repeat until `stop_reason: "end_turn"`

## Key Features

### Strict Tool Use
Add `strict: true` to tool definitions for guaranteed schema conformance.

### Parallel Tool Calling
Claude 4.6 excels at running multiple tools simultaneously. Boost with prompting:
```
Make all independent tool calls in parallel. Never use placeholders.
```

### Tool Search
Scale to thousands of tools — Claude discovers and loads them on demand via regex search. Only names consume context until used.

### Programmatic Tool Calling (GA)
Claude calls your tools from within code execution containers, reducing latency.

### Fine-Grained Tool Streaming (GA)
Stream tool parameters without buffering/JSON validation.

## Pricing

Tool use adds tokens from:
- `tools` parameter (names, descriptions, schemas)
- `tool_use` blocks (requests)
- `tool_result` blocks (responses)
- System prompt overhead: ~346 tokens for `auto`/`none`, ~313 for `any`/`tool` (Claude 4.x)

Individual tool costs:
- **Bash:** +245 input tokens
- **Text editor:** +700 input tokens
- **Computer use:** +735 input tokens + screenshot tokens
- **Web search:** $10/1000 searches
- **Code execution:** Free with web tools, or $0.05/hr after 1,550 free hours/month

## MCP Integration

For connecting to external tools via [[mcp|MCP]], use the **MCP connector** (beta) directly from Messages API, or build your own MCP client.

## See Also
- [[claude-api|Claude API]]
- [[mcp|Model Context Protocol]]
- [[pricing-and-costs|Pricing & Costs]]
- [[structured-outputs|Structured Outputs]]
