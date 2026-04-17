---
title: Agentic Patterns
type: concept
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Prompting best practices]]", "[[raw/Best Practices for Claude Code]]", "[[raw/How Claude Code works]]", "[[raw/Common workflows]]"]
tags: [agents, patterns, architecture, best-practices]
---

# Agentic Patterns

Design patterns for building effective AI agents with Claude. These emerge from Anthropic's internal teams and the broader Claude Code community.

## The Agentic Loop

All Claude agents work through a loop: **gather context → take action → verify results → repeat**. The agent decides what each step requires based on what it learned from the previous step.

## Key Patterns

### 1. Explore → Plan → Execute
Separate research from implementation. Use read-only analysis first (Plan Mode in Claude Code), then execute.

Best for: multi-file changes, unfamiliar code, architectural decisions.
Skip for: trivial fixes, one-line changes.

### 2. Writer/Reviewer
Two separate sessions — one implements, another reviews. Fresh context improves review quality since the reviewer isn't biased toward code it just wrote.

### 3. Subagent Delegation
Spawn specialized agents for isolated tasks. Each gets fresh context, keeping the main conversation clean. Claude 4.6 proactively delegates to subagents — sometimes too aggressively.

When to use subagents: parallel tasks, isolated context needed, independent workstreams.
When NOT to: simple tasks, sequential operations, single-file edits.

### 4. Fan-Out
Distribute work across parallel Claude invocations for migrations or analyses:
```bash
for file in *.py; do claude -p "Review $file" --output-format json &; done
```

### 5. Multi-Context Window Workflows
For tasks spanning beyond a single context window:
1. First window: set up framework (tests, scripts, todo list)
2. Subsequent windows: iterate on the todo list
3. Use git for state tracking
4. Create `init.sh` scripts for graceful restarts
5. Consider fresh context over compaction — Claude 4.6 discovers state from filesystem effectively

### 6. Self-Correction Chain
Generate draft → review against criteria → refine. Each step is a separate API call for inspect/branch/log capability.

## State Management

- **Structured formats (JSON):** For test results, task status, schema data
- **Unstructured text:** For progress notes, general context
- **Git:** For state tracking, checkpoints, rollback
- **Memory tool:** For cross-session persistence

## Autonomy vs Safety

Claude 4.6 may take hard-to-reverse actions without asking. Add explicit guidance:
```
Consider reversibility and impact. Take local, reversible actions freely.
For destructive/shared-system actions, ask first.
```

## Verification is Everything

The single highest-leverage practice: give Claude ways to verify its own work.
- Tests that can be run
- Screenshots to compare
- Expected outputs to check against
- Linter/type-checker output

Without verification, Claude produces plausible-looking but potentially broken code.

## Common Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| Kitchen sink session (mixed tasks) | `/clear` between unrelated tasks |
| Repeated corrections | After 2 failures, `/clear` + better prompt |
| Over-specified CLAUDE.md | Prune ruthlessly |
| Trust-then-verify gap | Always provide verification |
| Infinite exploration | Scope narrowly, use subagents |

## See Also
- [[claude-code|Claude Code]]
- [[prompt-engineering|Prompt Engineering]]
- [[agent-sdk|Agent SDK]]
- [[context-windows|Context Windows]]
