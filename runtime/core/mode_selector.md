# Mode Selector

Select your operating mode based on the task classification from Prompt Architect (Step 2). The mode determines how much context you load and how deeply you engage the runtime.

## Mode Definitions

### LIGHT Mode
**Triggers:** Trivial or Simple tasks (typo, rename, one-liner, single function, known bug)

| Dimension | Constraint |
|-----------|-----------|
| Context loading | None beyond what CLAUDE.md already provides |
| Memory | Skip entirely — do not call memory tools |
| Tool discovery | Skip — use direct Read/Grep/Glob |
| Skills | Skip — no skill routing needed |
| Response | Under 200 words. Terse. Show the change. |
| Logging | Skip — not worth the overhead |

**In LIGHT mode, do NOT read any other runtime files.** Just do the work.

### STANDARD Mode
**Triggers:** Moderate tasks (multi-step feature, refactor, unclear debugging)

| Dimension | Constraint |
|-----------|-----------|
| Context loading | Read context_router.md, follow matching branches only |
| Memory | Retrieve only — max 500 tokens. Do not store or evolve. |
| Tool discovery | On-demand via tool_loader.py if needed |
| Skills | Check skill_router.md, invoke if a match exists |
| Response | Proportional to task complexity |
| Logging | Log usage at task completion |

### DEEP Mode
**Triggers:** Complex or Architectural tasks (multi-file feature, system design, major refactor)

| Dimension | Constraint |
|-----------|-----------|
| Context loading | Full context_router.md — walk all matching branches |
| Memory | Retrieve (500 tok max) + Store insights + Evolve outcomes |
| Tool discovery | Full scan via tool_loader.py |
| Skills | Always check skill_router.md |
| Response | Thorough — no artificial word limit |
| Logging | Always log usage. Store memory if task produced reusable insights. |

## Mode Override

A repo's own CLAUDE.md can override the default mode. For example:
- "Always use DEEP mode for this repo" — follow it.
- "Skip memory for this repo" — respect it even in DEEP mode.

User instructions always take precedence over mode defaults.
