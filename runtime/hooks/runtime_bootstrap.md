# Runtime Bootstrap

This document defines what happens at the START of every Claude session. The global CLAUDE.md triggers this behavior automatically — no manual setup needed.

## Bootstrap Sequence

### Step 1: Task Classification (Automatic)
The Prompt Architect Protocol in global CLAUDE.md silently classifies the task:
- **Trivial/Simple** → LIGHT mode. Stop here. No runtime loaded.
- **Moderate** → STANDARD mode. Continue to Step 2.
- **Complex/Architectural** → DEEP mode. Continue to Step 2.

### Step 2: Load Runtime (Moderate+ Only)
Run the unified runtime loader to get the load plan:
```bash
python "{{RUNTIME_PATH}}/injector/runtime_loader.py" --task "TASK_DESCRIPTION" --complexity LEVEL
```

The loader returns:
- Which mode to use
- What to load (memory, wiki, tools, skills)
- What to skip
- Exact commands to run

### Step 3: Execute Load Plan
Follow the commands in the load plan output. Each command either:
- Reads a file (wiki, local memory)
- Runs a controller (tool_loader, memory_controller)
- Invokes a skill (brainstorming, debugging)

### Step 4: Do the Work
With context loaded, execute the actual task.

### Step 5: Post-Task (STANDARD/DEEP only)
Log usage for tracking:
```bash
python "{{RUNTIME_PATH}}/controllers/usage_logger.py" --mode MODE --task-summary "what was done"
```

For DEEP mode, also store reusable insights via `memory_store` MCP tool.

## Why This Exists
Without the bootstrap, Claude would either:
1. Load everything upfront (wastes tokens on trivial tasks)
2. Load nothing (misses context on complex tasks)

The bootstrap ensures the RIGHT amount of context for the RIGHT task.
