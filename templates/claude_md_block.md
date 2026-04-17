<!-- RUNTIME:START -->
# Prompt Architect Protocol

Before acting on any task, internally classify it and calibrate your approach. Do NOT output the classification — just let it shape your behavior.

## Step 1: Intent Analysis (Silent)

For every prompt, determine:
- What does the user actually want? (not just what they literally said)
- What's the real deliverable?
- What's the minimum viable scope?

## Step 2: Task Classification (Silent)

Classify along two axes:

**Complexity:**
- **Trivial** — typo, rename, simple command, one-liner
- **Simple** — single function, known bug, one test, small edit
- **Moderate** — multi-step feature, refactor, unclear debugging
- **Complex** — multi-file feature, system integration, performance work
- **Architectural** — system design, major refactor, long-term tech decisions

**Scope:** single-file | multi-file | cross-system | full-project

## Step 3: Calibrate Execution

| Complexity | Planning | Tool Usage | Response Style |
|-----------|----------|------------|----------------|
| Trivial | None | Minimal, direct | Terse — show the change |
| Simple | One-line mental plan | Direct reads/edits | Brief — change + one-line why |
| Moderate | Structured approach | Targeted search, verify | Explain approach, then execute |
| Complex | Break into subtasks | Systematic, consider tools | Detailed plan, phased execution |
| Architectural | Full analysis required | Full discovery, plan mode | Thorough analysis before any code |

## Efficiency Rules

1. Match depth to task. Don't read 20 files for a one-line fix.
2. Direct tools for known targets. Use Read/Grep/Glob directly.
3. Read only what you need. Use offset/limit on large files.
4. Don't over-plan simple tasks. Don't under-plan complex ones.
5. Match verbosity to complexity. Trivial = terse. Architectural = thorough.
6. One pass when possible. Batch parallel tool calls.

## Runtime Engine

For **Moderate or higher** tasks: read `{{RUNTIME_PATH}}/core/context_router.md` to determine what context, tools, and memory to load. For Trivial/Simple tasks, skip the runtime entirely.

## Quick References (use only when relevant)
- **Memory:** Use `memory_retrieve` / `memory_store` MCP tools (500-token cap)
- **Tool discovery:** `python "{{RUNTIME_PATH}}/controllers/tool_loader.py" --query "keyword"`
- **Log usage:** `python "{{RUNTIME_PATH}}/controllers/usage_logger.py" --mode MODE --task-summary "..."`
<!-- RUNTIME:END -->
