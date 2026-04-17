---
title: Prompt Engineering
type: concept
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Prompt engineering overview]]", "[[raw/Prompting best practices]]", "[[raw/Best Practices for Claude Code]]"]
tags: [prompting, best-practices, techniques]
---

# Prompt Engineering

Techniques for getting the best results from [[claude-models|Claude models]]. This page covers the consolidated best practices from Anthropic's official guidance.

## Prerequisites

Before prompt engineering, you need:
1. Clear success criteria for your use case
2. Ways to empirically test against those criteria
3. A first draft prompt to improve

## General Principles

### Be Clear and Direct
Claude responds to explicit instructions. Think of Claude as a brilliant new employee lacking context on your norms. The **golden rule:** show your prompt to a colleague with minimal context — if they'd be confused, Claude will be too.

### Add Context
Explain *why* behind instructions. Claude generalizes from explanations.

### Use Examples (Few-Shot)
3-5 well-crafted examples dramatically improve accuracy. Make them relevant, diverse, and wrapped in `<example>` tags.

### Structure with XML Tags
Use `<instructions>`, `<context>`, `<input>` tags to separate content types. Nest tags for hierarchy. This reduces misinterpretation.

### Give Claude a Role
Set a role in the system prompt: `"You are a helpful coding assistant specializing in Python."` Even one sentence makes a difference.

### Long Context Tips
- Put long documents **at the top** of your prompt, query at the bottom (up to 30% quality improvement)
- Wrap documents in `<document>` tags with metadata
- Ask Claude to quote relevant parts before answering

## Output Control

### Communication Style (Claude 4.6)
Claude 4.6 models are more concise, direct, and conversational. They may skip summaries after tool calls. If you want more visibility:
```
After completing a task that involves tool use, provide a quick summary.
```

### Formatting
1. Tell Claude what to do, not what NOT to do
2. Use XML format indicators (`<smoothly_flowing_prose_paragraphs>`)
3. Match your prompt style to desired output
4. Opus 4.6 defaults to LaTeX for math — explicitly request plain text if needed

## Tool Use Prompting

Claude 4.6 models are trained for precise instruction following. Be explicit about taking action vs. suggesting:
- **Action:** "Implement changes rather than only suggesting them"
- **Research:** "Do not jump into implementation unless clearly instructed"

Claude excels at **parallel tool calling** — reads multiple files, runs multiple commands simultaneously.

## Thinking & Reasoning

### Adaptive Thinking (Recommended for 4.6)
```python
thinking={"type": "adaptive"}
output_config={"effort": "high"}  # or max, medium, low
```
Claude dynamically decides when/how much to think. Replaces manual `budget_tokens`.

### Tips
- Prefer general instructions ("think thoroughly") over prescriptive steps
- Use `<thinking>` tags in few-shot examples
- Ask Claude to self-check before finishing
- If overthinking: lower effort, or add "choose an approach and commit to it"

## Agentic Prompting

### Long-Horizon Reasoning
Claude 4.6 excels at state tracking across extended sessions. Key strategies:
- Use structured formats (JSON) for state data
- Use git for state tracking
- First context window: set up framework (tests, scripts). Subsequent: iterate on todo list.
- Prompt: "Save progress before context window refreshes"

### Balancing Autonomy and Safety
Add explicit guidance about confirming before destructive actions (delete files, force-push, post to external services).

### Subagent Orchestration
Claude 4.6 proactively delegates to subagents. To reduce excessive spawning:
```
Use subagents when tasks can run in parallel or require isolated context.
For simple tasks, work directly rather than delegating.
```

### Overeagerness
Claude 4.6 may overengineer. Counter with:
```
Avoid over-engineering. Only make changes directly requested.
Don't add features, abstractions, or documentation beyond what was asked.
```

## Migration to Claude 4.6

1. Be specific about desired behavior
2. Frame instructions with modifiers (e.g., "fully-featured implementation")
3. Update thinking to adaptive mode
4. Remove prefill (deprecated on 4.6)
5. Dial back anti-laziness prompting — 4.6 is significantly more proactive

## See Also
- [[claude-models|Claude Models]]
- [[adaptive-thinking|Adaptive Thinking]]
- [[tool-use|Tool Use]]
- [[agentic-patterns|Agentic Patterns]]
