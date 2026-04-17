# Architecture — Claude_Meister

How the system works internally: the three modes, context routing, memory scoring, the MCP server, and the injector system.

> This document is for developers and curious users. You do not need to understand any of this to use Claude_Meister — it runs silently. Start with [docs/quickstart.md](quickstart.md) if you haven't installed yet.

---

## Overview

Claude_Meister is a **runtime intelligence layer** that sits between you and Claude Code. It intercepts the start of every conversation, classifies the task's complexity, and loads only the context that complexity warrants.

The core insight: most Claude Code interactions are simple — typo fixes, quick questions, one-line edits. Today, all of them pay the same context cost as an architectural redesign. Claude_Meister eliminates that waste.

Three installed components:

| Component | Location | Purpose |
|---|---|---|
| Runtime engine | `~/.claude_runtime/` | Behavioral docs, controllers, routing logic |
| Memory server | `~/.claude_memory/` | FastMCP-based memory store with scoring |
| CLAUDE.md block | `~/.claude/CLAUDE.md` | Teaches Claude how to invoke the runtime |

---

## The Three Modes

Every conversation begins with a silent classification step before Claude does anything else. The classification produces one of three modes:

| Mode | Triggers On | Context Loaded | Memory | Response Ceiling |
|---|---|---|---|---|
| **LIGHT** | Trivial / Simple tasks | CLAUDE.md baseline only | Skipped entirely | ~200 words |
| **STANDARD** | Moderate tasks | Baseline + `context_router.md` + targeted files | Retrieve only (≤500 tokens) | Proportional |
| **DEEP** | Complex / Architectural | Baseline + full router + all relevant files | Retrieve + Store + Evolve | Thorough |

**LIGHT mode is the key differentiator.** When a task is simple, the runtime files on disk are never read. A typo fix costs roughly 847 tokens (slim CLAUDE.md baseline) instead of 1,400+ (a bloated CLAUDE.md with no routing).

### Complexity Classification

Claude classifies complexity along two axes before selecting a mode:

**Complexity tiers:**
- Trivial — single word change, rename, one-liner
- Simple — single function, known bug, small edit
- Moderate — multi-step feature, unclear debugging
- Complex — multi-file feature, system integration
- Architectural — system design, major refactor

**Scope:**
- single-file | multi-file | cross-system | full-project

A Trivial or Simple task with any scope selects LIGHT. A Moderate task selects STANDARD. Complex or Architectural selects DEEP.

---

## Context Routing Flow

Here is what happens on every user prompt, from message to response:

```
User message arrives
        │
        ▼
┌───────────────────────────────────┐
│  CLAUDE.md baseline loaded        │  ← Always (slim, ~847 tokens)
│  (Mode selector instructions)     │
└────────────────┬──────────────────┘
                 │
          Classify complexity
          (silent, no output)
                 │
        ┌────────┴────────┐
        │                 │
   TRIVIAL / SIMPLE   MODERATE or higher
        │                 │
        ▼                 ▼
  Direct response    Read context_router.md
  (no extra load)         │
                    Route by task type
                          │
                    Load targeted context
                    (mode_selector, skill_router,
                     token_budget docs as needed)
                          │
                    Retrieve memories
                    (scored, ≤500 token cap)
                          │
                    Discover tools if needed
                    (tool_loader.py)
                          │
                    Execute + respond
                          │
                    (DEEP mode only)
                    Store/evolve memories
                    Log usage
```

### Context Router (`context_router.md`)

The context router is the main behavioral document for STANDARD and DEEP modes. It defines:

- Which additional files to load for each task type (debugging vs. feature work vs. refactor)
- When to call `tool_loader.py` for tool discovery
- When to invoke memory retrieval
- Token budget enforcement rules

Claude reads this document as instructions — it is not executable code, it is a Markdown SOP (Standard Operating Procedure) that Claude follows.

### Mode Selector (`mode_selector.md`)

Defines the classification rules in detail. Includes worked examples of Trivial vs. Moderate vs. Architectural tasks so Claude calibrates correctly.

### Token Budget (`token_budget.md`)

Defines hard limits per mode. In LIGHT mode, additional context loads are prohibited. In STANDARD mode, a soft cap of ~1,600 tokens total (baseline + routing + memory) is enforced. DEEP has a higher cap but still enforces the memory token ceiling.

---

## Memory Scoring Formula

The memory system does not return all stored memories. It scores and ranks them, then trims to fit within the configured token budget.

**Composite score formula:**

```
score = (relevance × 0.4 + recency × 0.25 + frequency × 0.15 + success_rate × 0.2)
        × (1 − decay_factor)
```

**Factor definitions:**

| Factor | Weight | What it measures |
|---|---|---|
| `relevance` | 0.40 | Keyword and semantic match between the query and memory content |
| `recency` | 0.25 | How recently the memory was last accessed (decays over time) |
| `frequency` | 0.15 | How often the memory has been retrieved and used |
| `success_rate` | 0.20 | Proportion of retrievals where the memory was marked helpful |
| `decay_factor` | modifier | Time-based decay; older, unused memories score lower |

A memory scoring below approximately 0.35 is excluded even if the budget allows it. This threshold prevents low-confidence noise from entering the context.

**Example from a real retrieval (Walkthrough 3 in README):**

```
Query: "database migration"
Results:
  migration_plan.json    score: 0.91  ← included
  schema_notes.json      score: 0.78  ← included
  unrelated_note.json    score: 0.32  ← excluded (below threshold)
Total retrieved: 312 tokens (within 500-token cap)
```

The scoring implementation lives in `~/.claude_memory/server/memory_scorer.py` (source: `memory/server/memory_scorer.py` in the repo). At runtime, `memory_controller.py` imports the scoring module directly — no MCP call needed for the standalone controller path.

---

## MCP Server Architecture

**What is MCP?** MCP (Model Context Protocol) is a standard that lets external tools communicate with Claude Code. Claude Code calls MCP tools the same way it calls built-in capabilities.

The memory server is a FastMCP application registered with Claude Code under the name `"memory"`. It communicates via stdio transport — a local pipe between Claude Code and the server process. No network is involved.

### Server Modules

All modules live in `~/.claude_memory/server/`:

| Module | Purpose |
|---|---|
| `main.py` | FastMCP app entry point; registers all 6 tools |
| `memory_store.py` | Write a new memory entry to disk + update index |
| `memory_retriever.py` | Query the index, load matching entries |
| `memory_scorer.py` | Compute composite scores for retrieval ranking |
| `evolution_engine.py` | Update an existing memory with new evidence |
| `debate_engine.py` | Resolve contradictory memories, keep the stronger one |
| `cleanup.py` | Remove stale or low-scoring entries |

### Exposed MCP Tools

Claude Code can call these tools by name in any conversation:

```
memory_retrieve   — query by keyword + repo, returns scored results
memory_store      — save a new memory with metadata
memory_evolve     — update an existing memory
memory_debate     — compare contradictory memories, keep the winner
memory_cleanup    — remove stale or low-scoring entries
memory_status     — report health and statistics
```

### Storage Layout

```
~/.claude_memory/
├── index.json          ← fast-lookup metadata index
├── <uuid>.json         ← individual memory entry
├── <uuid>.json
└── server/
    ├── main.py
    ├── memory_store.py
    ├── memory_retriever.py
    ├── memory_scorer.py
    ├── evolution_engine.py
    ├── debate_engine.py
    └── cleanup.py
```

Each `<uuid>.json` is one memory entry. The index holds metadata (tags, scores, timestamps) for fast querying without loading every memory file.

### Standalone Access (No MCP Required)

`memory_controller.py` in `~/.claude_runtime/controllers/` can read memories directly from `index.json`, bypassing the MCP server. Useful for debugging or when the MCP server is not available.

`mcp_router.py` decides whether to use the MCP server or the direct controller path based on availability.

---

## Injector System

The injector is how Claude_Meister survives repo changes and new projects without requiring per-project setup.

### The CLAUDE.md Block

The installer appends a block to `~/.claude/CLAUDE.md` between two HTML comment markers:

```markdown
<!-- RUNTIME:START -->
# Prompt Architect Protocol
... (task classification instructions) ...

## Runtime Engine
For Moderate or higher tasks: read `C:/Users/yourname/.claude_runtime/core/context_router.md`

## Quick References
- Memory: Use `memory_retrieve` / `memory_store` MCP tools (500-token cap)
- Tool discovery: `python "C:/Users/yourname/.claude_runtime/controllers/tool_loader.py" --query "keyword"`
<!-- RUNTIME:END -->
```

Because `~/.claude/CLAUDE.md` is a global file, this block is available in every Claude Code session, regardless of which project you are in.

### Path Templating

All paths in the injected block use tokens at source (`{{RUNTIME_PATH}}`, `{{MEMORY_ROOT}}`) that the installer resolves to real paths at install time. This means the same source template works across Windows, macOS, and Linux.

Template resolution happens in `installer/paths.py`:

```python
# Simplified from installer/paths.py
substitutions = {
    "{{HOME}}":         str(Path.home()),
    "{{RUNTIME_PATH}}": str(Path.home() / ".claude_runtime"),
    "{{MEMORY_ROOT}}":  str(Path.home() / ".claude_memory"),
}
```

On Windows, all paths are normalized to forward slashes — Claude Code expects forward slashes even on Windows.

### Repo Scanner (`repo_scanner.py`)

For DEEP mode, the injector includes a repo scanner that detects the current project type and surfaces relevant context. It looks for markers like `package.json`, `pyproject.toml`, `Cargo.toml`, etc., to suggest appropriate tool directories and wiki sections.

### Update and Removal

The `<!-- RUNTIME:START -->` and `<!-- RUNTIME:END -->` markers make block management surgical:

- **Update (`python install.py --update`):** Re-templates everything between the markers. Content outside the markers is never touched.
- **Uninstall:** Strips everything between (and including) the markers. Your CLAUDE.md is left exactly as it was before installation, minus the block.

---

## Runtime File Structure

After installation, the full layout:

```
~/.claude_runtime/
├── configs/
│   └── runtime_config.json      ← your configuration (preserved on update)
├── controllers/
│   ├── tool_loader.py            ← discover tools by keyword
│   ├── usage_logger.py           ← log task stats and view dashboard
│   ├── memory_controller.py      ← direct memory access (no MCP needed)
│   └── mcp_router.py             ← routes memory queries to best source
├── core/
│   ├── context_router.md         ← main routing instructions (STANDARD/DEEP)
│   ├── mode_selector.md          ← complexity classification rules
│   ├── skill_router.md           ← skill and tool discovery routing
│   └── token_budget.md           ← hard token limits per mode
├── hooks/
│   ├── runtime_bootstrap.md      ← session initialization instructions
│   └── pre_execution.md          ← pre-action checks
├── injector/
│   ├── runtime_loader.py         ← loads runtime context on demand
│   ├── claude_md_injector.py     ← manages CLAUDE.md block
│   └── repo_scanner.py           ← detects project type
└── logs/
    └── runtime_usage.json        ← usage history (preserved on update)
```

---

## Design Principles

**1. Zero overhead for simple tasks.** LIGHT mode is the common path. The majority of interactions never load any runtime file. Overhead is proportional to complexity, not uniform.

**2. Deterministic execution, probabilistic reasoning.** Claude (probabilistic) handles classification and judgment. Python scripts (deterministic) handle file I/O, scoring math, and tool discovery. The split keeps accuracy high as pipelines grow.

**3. Local-only.** No API calls, no network traffic, no keys. All operations are file reads/writes and subprocess calls on the local machine.

**4. Graceful degradation.** If any component fails — bad JSON config, missing file, import error — the runtime falls back to defaults rather than crashing. Claude Code keeps working.

**5. Update-safe user data.** Memories, config customizations, and usage logs are explicitly preserved across updates. Only the "brains" (behavioral docs, controllers, server modules) are refreshed.
