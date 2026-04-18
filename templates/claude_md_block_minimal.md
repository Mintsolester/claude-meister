<!-- RUNTIME:START -->
# Runtime Engine (Minimal)

Quick calibration for small repos — skip overhead on trivial work.

**Complexity:** Trivial / Simple → just do it. Moderate+ → read `{{RUNTIME_PATH}}/core/context_router.md`.

**Efficiency:**
- Match depth to task. Don't read 20 files for a one-line fix.
- Direct tools (Read/Grep/Glob) for known targets.
- Batch independent tool calls in parallel.

**Quick refs:**
- Memory: `memory_retrieve` / `memory_store` (500-token cap)
- Tools: `python "{{RUNTIME_PATH}}/controllers/tool_loader.py" --query "keyword"`
<!-- RUNTIME:END -->
