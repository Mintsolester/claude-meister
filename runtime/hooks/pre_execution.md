# Pre-Execution Checklist

Before executing any Moderate+ task, verify these conditions are met. This runs AFTER the bootstrap and BEFORE writing any code.

## Checklist

### 1. Mode Confirmed
- [ ] Task classified as Trivial / Simple / Moderate / Complex / Architectural
- [ ] Mode selected: LIGHT / STANDARD / DEEP
- [ ] If LIGHT → skip this entire checklist, just do the work

### 2. Context Loaded
- [ ] Runtime loader was called (or context_router was read)
- [ ] All recommended commands from the load plan were executed
- [ ] Memory retrieved if task involves prior work
- [ ] Wiki consulted if task involves Claude capabilities

### 3. Tools Available
- [ ] For unfamiliar codebases: tool_loader.py was run to discover available tools
- [ ] Required tools exist and are accessible
- [ ] No missing dependencies that would block execution

### 4. Skill Invoked
- [ ] If skill_router mapped this task to a skill → that skill was invoked
- [ ] brainstorming before features, debugging before fixes, planning before complex work

### 5. Token Budget
- [ ] Memory retrieval stayed within 500-token cap
- [ ] Wiki reads limited to 5 pages max
- [ ] Not re-reading files already in context

## After Execution

### For STANDARD mode:
- Log usage via usage_logger.py

### For DEEP mode:
- Log usage via usage_logger.py
- Store reusable insights via memory_store (max 200 tokens, compressed)
- Record outcome via memory_evolve if measurable result
