---
title: Adaptive Thinking
type: concept
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Adaptive thinking]]", "[[raw/What's new in Claude 4.6]]", "[[raw/Building with extended thinking]]", "[[raw/Prompting best practices]]"]
tags: [thinking, reasoning, effort, adaptive]
---

# Adaptive Thinking

Adaptive thinking (`thinking: {type: "adaptive"}`) is the **recommended thinking mode** for Claude Opus 4.6 and Sonnet 4.6. Claude dynamically decides when and how much to think based on two factors: the **effort parameter** and **query complexity**.

## How It Works

- At `high` effort (default): Claude almost always thinks
- At lower effort: may skip thinking for simpler problems
- Automatically enables **interleaved thinking** (thinking between tool calls)
- Thinking blocks are billed as output tokens

```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={"type": "adaptive"},
    messages=[{"role": "user", "content": "Solve this complex problem..."}],
)
```

## Effort Parameter (GA)

Controls thinking depth. No beta header required.

| Level | Behavior | Best for |
|---|---|---|
| `max` | Absolute highest capability (Opus 4.6 only) | Hardest problems |
| `high` | Default. Deep reasoning | Complex tasks, agents |
| `medium` | Balanced | Most Sonnet 4.6 use cases |
| `low` | Minimal thinking | High-volume, latency-sensitive |

```python
output_config={"effort": "medium"}
```

## Deprecations

- `thinking: {type: "enabled", budget_tokens: N}` — **deprecated** on 4.6 models. Still functional but will be removed.
- `interleaved-thinking-2025-05-14` beta header — **deprecated** on Opus 4.6 (safely ignored). Still functional on Sonnet 4.6 for manual mode.

## In Claude Code

- Extended thinking enabled by default
- `/effort` or `/model` to adjust effort level
- `Option+T` / `Alt+T` to toggle thinking on/off
- "ultrathink" keyword in prompt → sets effort to high for that turn
- `Ctrl+O` (verbose mode) to see thinking process
- `MAX_THINKING_TOKENS` env var for budget limits (only `0` applies on 4.6 unless adaptive disabled)

## When to Use

Best for:
- Autonomous multi-step agents
- Computer use agents
- Bimodal workloads (mix of easy and hard tasks)
- Complex coding, reasoning, research

## Tips

- Prefer general instructions ("think thoroughly") over prescriptive step-by-step
- If overthinking: lower effort, or prompt "choose an approach and commit"
- Use `<thinking>` tags in few-shot examples to show reasoning patterns
- At `low` effort with thinking disabled, Sonnet 4.6 ≈ Sonnet 4.5 performance

## See Also
- [[context-windows|Context Windows]]
- [[claude-models|Claude Models]]
- [[prompt-engineering|Prompt Engineering]]
