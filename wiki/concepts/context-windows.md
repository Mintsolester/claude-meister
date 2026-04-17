---
title: Context Windows
type: concept
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Context windows]]", "[[raw/Best Practices for Claude Code]]", "[[raw/How Claude Code works]]"]
tags: [context, tokens, memory, performance]
---

# Context Windows

The context window is Claude's "working memory" — all text it can reference when generating a response, including the response itself. Larger context enables more complex tasks, but more context isn't automatically better.

## Window Sizes

| Model | Context Window | Max Output |
|---|---|---|
| Opus 4.6, Sonnet 4.6, Mythos | 1M tokens | 128k (Opus), 64k (Sonnet) |
| Haiku 4.5 | 200k tokens | 64k |
| Older models | 200k tokens | varies |

Full 1M context at **standard pricing** — no long-context premium.

## Context Rot

As token count grows, accuracy and recall degrade. This is the fundamental constraint. Curating what's *in* context is as important as how much space is available.

## Context Awareness

Sonnet 4.6, Sonnet 4.5, and Haiku 4.5 can **track their remaining token budget** throughout a conversation:
```
<budget:token_budget>1000000</budget:token_budget>
```
After each tool call, they receive: `Token usage: 35000/1000000; 965000 remaining`

This enables better execution on long-running agent sessions.

## Extended Thinking & Context

- Thinking tokens count toward the context window AND are billed as output
- **Previous thinking blocks are automatically stripped** from context for subsequent turns
- During tool use, thinking blocks must be preserved until the tool cycle completes
- Formula: `context_window = (input_tokens - previous_thinking_tokens) + current_turn_tokens`

## Management Strategies

### Compaction (Beta)
Server-side summarization for Opus 4.6 and Sonnet 4.6. When context approaches limits, the API automatically summarizes earlier parts. Enables effectively infinite conversations.

### Context Editing (Beta)
- **Tool result clearing** — remove old tool outputs in agentic workflows
- **Thinking block clearing** — manage thinking blocks

### Prompt Caching
Not the same as context management, but reduces cost by reusing processed prompt portions. See [[prompt-caching|Prompt Caching]].

### Token Counting API
Estimate token usage before sending: `POST /v1/messages/count_tokens`

## In Claude Code

Context fills fast — a single debugging session can consume tens of thousands of tokens. Key practices:
- `/clear` between unrelated tasks
- `/compact <focus>` for targeted summarization
- `/context` to see what's using space
- Subagents run in separate context (their research doesn't bloat yours)
- Skills load on demand
- MCP tools deferred by default
- `/btw` for side questions that don't enter history

Newer models (3.7+) return validation errors when exceeding context, rather than silently truncating.

## See Also
- [[claude-models|Claude Models]]
- [[adaptive-thinking|Adaptive Thinking]]
- [[prompt-caching|Prompt Caching]]
- [[claude-code|Claude Code]]
