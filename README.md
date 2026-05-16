# Claude_Meister

**Intelligence Runtime for Claude Code**

Claude_Meister is a lightweight runtime layer that makes Claude Code smarter, cheaper, and faster — without changing how you use it. It installs in under two minutes and works silently in the background from that point on.

---

## New in v2: `meister` — cross-tool conversation memory

The same conversation memory, available from Claude Code, Cursor, Codex, Aider, or your shell. Captures every turn into a repo-local `.repo_memory/conversation.jsonl`, then surfaces it back with **layered retrieval** — so recall costs ~50 tokens, not 5,000.

**30-second demo:**

```bash
# One-time install (writes capture hooks to ~/.claude/settings.json)
python -m meister install-hooks

# ...work in Claude Code as usual. Hooks silently capture every turn.

# Next day, in any repo:
$ python -m meister last
Last 1 session(s) in ~/your-repo:

  s_1715692800  2026-05-14 18:42  events=12  tools=[Edit:5,Bash:3,Read:4]
                files: db/repository.py, tests/test_repo.py
                title: fix the dedup bug in batch_insert_personas

# Find a past session by topic:
$ python -m meister recall "auth middleware"
# Drill in:
$ python -m meister show s_1715692800
```

**Why this is different from CLAUDE.md or built-in memory:**

- **Platform-agnostic.** Same `.repo_memory/` works whether you used Claude Code, Cursor, or a shell-only client. Your memory follows the repo, not the tool.
- **Layered retrieval (L0 → L1 → L2).** Default recall returns one-line session titles. Drill in only when you need the detail. The recall cost stays bounded as your history grows.
- **Repo-local.** The log lives in `your-repo/.repo_memory/`. Commit it, gitignore it, sync it with the repo — your call.
- **Zero embedding install.** Pure TF-IDF over events. No vector DB, no model download, no daemon. ~400 LOC. Upgrade to embedded recall later via the MCP server if you want.
- **Fails open.** Capture hooks swallow all errors. They never block your tool calls.

Full reference: [`docs/MEISTER_CLI.md`](docs/MEISTER_CLI.md).

---

## Before / After

| Scenario | Without Claude_Meister | With Claude_Meister | Difference |
|---|---|---|---|
| Typo fix — tokens loaded into context | ~1,400 (full CLAUDE.md always loaded) | ~847 (slim baseline only) | **-40% context overhead** |
| Typo fix — extra runtime cost | 0 (paid full CLAUDE.md cost regardless) | 0 (LIGHT mode, runtime skipped entirely) | Same task, cheaper |
| Moderate refactor — context | 1,400 (no routing, same cost every time) | 847 + ~800 (targeted context loaded) | Only loads what's needed |
| Complex feature — memory | Manual, no scoring, often too much retrieved | Scored, ranked, 500-token cap enforced | Controlled, relevant memory |
| Architectural task — finding tools | Manual directory search, minutes | `tool_loader.py` ranked matches, seconds | Seconds vs. minutes |

> **What is a "token"?** A token is roughly 3/4 of a word. Claude Code has a "context window" (a limit on how much text it can consider at once). Every token loaded costs money and uses up that window. Claude_Meister keeps that number low.

---

## Table of Contents

1. [Why Claude_Meister?](#why-claude_meister)
2. [Quick Start](#quick-start)
3. [Plugin Install and Distribution](#plugin-install-and-distribution)
4. [Detailed Installation Guide](#detailed-installation-guide)
5. [How It Works](#how-it-works)
6. [Example Walkthroughs](#example-walkthroughs)
7. [Configuration](#configuration)
8. [Commands Reference](#commands-reference)
9. [Updating](#updating)
10. [Uninstalling](#uninstalling)
11. [Troubleshooting](#troubleshooting)
12. [FAQ](#faq)
13. [Contributing](#contributing)
14. [License & Credits](#license--credits)

---

## Why Claude_Meister?

### The Problem

Claude Code loads its instruction file (`~/.claude/CLAUDE.md`) at the start of every single conversation — a typo fix and a full architectural redesign both pay the same context cost. There is no built-in way to load only what a task actually needs.

On top of that:
- Memory must be managed manually. There is no built-in way to score, rank, or cap retrieved memories.
- Finding the right tool script in a large project requires manual search.
- Nothing tracks which mode Claude is operating in or whether the context spend was worthwhile.

### The Solution

Claude_Meister installs three things:

1. **Runtime engine** (`~/.claude_runtime/`) — a set of behavioral documents and controller scripts. The router reads your task, classifies its complexity, and loads only the context that complexity warrants.
2. **Memory server** (`~/.claude_memory/`) — an MCP (Model Context Protocol — a standard way for tools to communicate with Claude Code) server that stores, scores, and retrieves memories automatically.
3. **Wiki knowledge base** (`~/.claude_wiki/`) — optional offline documentation that Claude can query without an internet connection.

Your `~/.claude/CLAUDE.md` gets a small block appended that teaches Claude how to invoke the runtime. That is the only change to any file you already have.

### Results

Running `python install.py --stats` shows your own data:

```
Claude_Meister Usage Report (last 30 days)
-------------------------------------------
Tasks logged:           47
Mode distribution:      LIGHT 62% | STANDARD 30% | DEEP 8%
Avg memory tokens:      287 / 500 cap
Tasks with memory:      14 (30%)
Tasks skipping runtime: 29 (62%)  <-- saved ~600 tokens each

Estimated savings:      ~17,400 tokens saved by LIGHT mode skipping runtime
```

---

## Quick Start

If you are comfortable with the command line and just want to get started:

```bash
# 1. Clone the repo
git clone https://github.com/Mintsolester/claude-meister.git
cd claude-meister

# 2. Run the installer
python install.py --full

# 3. Verify everything installed correctly
python install.py --verify
```

Then restart Claude Code. That is it.

Not sure what any of those commands mean? Read the [Detailed Installation Guide](#detailed-installation-guide) below — it walks through every step with screenshots and expected output.

---

## Plugin Install and Distribution

If you want to use Claude_Meister as a plugin through Claude Code marketplaces:

```bash
# 1. Add this repository as a marketplace
claude plugin marketplace add Mintsolester/claude-meister

# 2. Install the plugin from this marketplace
claude plugin install claude-meister@claude-meister-marketplace
```

For local plugin development and testing without marketplace install:

```bash
claude --plugin-dir ./plugins/claude-meister
```

Before publishing plugin changes, run validation locally:

```bash
claude plugin validate .
claude plugin validate plugins/claude-meister
```

For official public listing, submit the plugin using Claude.ai or Console plugin submission forms.

---

## Detailed Installation Guide

### What You Need First (Prerequisites)

Before installing Claude_Meister, you need three things on your computer. Here is how to check each one.

#### 1. Python 3.8 or newer

**What is Python?** Python is a programming language. Claude_Meister is written in Python, so Python must be installed to run it.

Open a terminal:
- **Windows:** Press `Win + R`, type `cmd`, press Enter
- **macOS:** Press `Cmd + Space`, type `Terminal`, press Enter
- **Linux / WSL:** Open your terminal application

Type this and press Enter:

```
python --version
```

You should see something like:

```
Python 3.11.4
```

As long as the number is 3.8 or higher, you are good. If you see `Python 2.x` or an error, [download Python from python.org](https://www.python.org/downloads/) and install it. On macOS/Linux you may need `python3 --version` instead.

> **If you see an error:** Python is not installed or not on your PATH (the list of places your computer looks for programs). Download it from python.org and run the installer. On Windows, check "Add Python to PATH" during installation.

#### 2. Two Python packages: `mcp` and `fastmcp`

These packages enable the memory server. Install them by running:

```
pip install mcp fastmcp
```

Expected output (abbreviated):

```
Collecting mcp
  Downloading mcp-...
Collecting fastmcp
  Downloading fastmcp-...
Successfully installed mcp-... fastmcp-...
```

> **If pip is not found:** Try `pip3 install mcp fastmcp` on macOS/Linux. On Windows, try `python -m pip install mcp fastmcp`.

#### 3. Claude Code CLI

Claude_Meister registers its memory server with Claude Code during installation. The `claude` command must be available.

Test it:

```
claude --version
```

Expected output:

```
claude/1.x.x
```

If you see an error, install Claude Code from [claude.ai/code](https://claude.ai/code) and follow its setup instructions before continuing.

---

### Step-by-Step Installation

#### Step 1: Get the files

If you have Git installed:

```bash
git clone https://github.com/Mintsolester/claude-meister.git
cd claude-meister
```

If you do not have Git, download the ZIP from the GitHub page, unzip it, and open a terminal in that folder.

#### Step 2: Run the installer

```bash
python install.py --full
```

The installer will work through these stages. Here is what to expect:

```
Claude_Meister Installer
========================
[1/7] Checking Python version...          OK  (Python 3.11.4)
[2/7] Checking dependencies (mcp, fastmcp)... OK
[3/7] Installing runtime engine to ~/.claude_runtime/...  OK
[4/7] Installing memory server to ~/.claude_memory/...    OK
[5/7] Installing wiki knowledge base to ~/.claude_wiki/... OK
[6/7] Updating ~/.claude/CLAUDE.md...     OK  (block appended)
[7/7] Registering MCP memory server...    OK  (registered as "memory")

Installation complete. Restart Claude Code to activate.
```

> **If you see "Claude Code not found" at step 7:** Make sure `claude --version` works in your terminal, then re-run the installer. The `claude mcp add` command requires the CLI to be on your PATH.

> **If you see "Permission denied":** On macOS/Linux, you may need to prefix with `sudo`. On Windows, run Command Prompt as Administrator.

> **If you see a message about an existing installation:** The installer will ask whether to update, do a clean reinstall, or abort. Choose "update" to preserve your memories and logs.

#### Step 3: Verify the installation

```bash
python install.py --verify
```

Expected output:

```
Verification Results
====================
Runtime engine:      PASS  (~/.claude_runtime/ present, 4 core files found)
Memory server:       PASS  (~/.claude_memory/ present, index.json OK)
Wiki knowledge base: PASS  (~/.claude_wiki/ present, index.md found)
CLAUDE.md block:     PASS  (markers found, paths correctly substituted)
MCP registration:    PASS  ("memory" server registered with Claude Code)

All checks passed. You are ready to go.
```

If any check shows FAIL, see the [Troubleshooting](#troubleshooting) section for that specific failure.

#### Step 4: Restart Claude Code

Close all Claude Code windows and reopen. The memory server only becomes available to Claude after a fresh session start.

#### Step 5: Your first interaction

Open Claude Code in any project and type something. Nothing looks different — Claude_Meister works silently. Behind the scenes, your task has been classified, the right amount of context was loaded, and Claude is operating in the appropriate mode.

To confirm it is running, ask Claude directly:

```
What mode are you operating in right now?
```

Claude will respond with something like:

```
LIGHT mode — this is a simple question, so I'm not loading the full runtime. 
No extra context cost.
```

---

## How It Works

### The Three Modes

Every conversation starts with a silent classification step. Claude reads your request, determines its complexity, and selects one of three operating modes:

| Mode | When it activates | What gets loaded | Memory | Response style |
|---|---|---|---|---|
| **LIGHT** | Trivial / Simple tasks | Nothing beyond CLAUDE.md baseline | Skipped | Under 200 words |
| **STANDARD** | Moderate tasks | `context_router.md` + targeted files | Retrieve only (500-token cap) | Proportional |
| **DEEP** | Complex / Architectural | Full router + all relevant files | Retrieve + store + evolve | Thorough |

**LIGHT mode is the key innovation.** Most interactions — quick edits, questions, small fixes — are simple. LIGHT mode ensures these never pay extra context cost. The runtime files stay on disk, unread.

### Architecture Diagram

```
Your message
     │
     ▼
┌─────────────────────────────────┐
│  CLAUDE.md baseline             │  ← Always loaded (slim)
│  (Mode selector instructions)   │
└─────────────────┬───────────────┘
                  │
         Classify complexity
                  │
         ┌────────┴────────┐
         │                 │
    LIGHT / SIMPLE    MODERATE or higher
         │                 │
         ▼                 ▼
   Direct response   Read context_router.md
                          │
                    Load targeted context
                          │
                    Retrieve memories (≤500 tok)
                          │
                    Discover tools if needed
                          │
                     Execute + respond
```

### The Memory System

**What is it?** The memory system gives Claude a long-term memory that persists across sessions. When you work on a project today, key facts are stored. Tomorrow, they are retrieved automatically.

**How memories are scored:**

Each memory gets a composite score when retrieved:

```
score = (relevance × 0.4 + recency × 0.25 + frequency × 0.15 + success_rate × 0.2)
        × (1 − decay_factor)
```

Only the highest-scoring memories within the 500-token budget are passed to Claude. This keeps context lean while ensuring the most useful memories surface.

**Storage location:** `~/.claude_memory/` — one JSON file per memory entry, plus `index.json` for fast lookup.

**Memory tools available to Claude:**

| Tool | What it does |
|---|---|
| `memory_retrieve` | Query memories by keyword + project, returns scored results |
| `memory_store` | Save a new memory with metadata |
| `memory_evolve` | Update an existing memory when new evidence arrives |
| `memory_debate` | Compare contradictory memories, keep the stronger one |
| `memory_cleanup` | Remove stale or low-scoring entries |
| `memory_status` | Report memory system health and stats |

### Runtime File Locations

After installation, files live here:

```
~/.claude_runtime/
├── configs/
│   └── runtime_config.json      # Your configuration
├── controllers/
│   ├── tool_loader.py            # Discovers tools by keyword
│   ├── usage_logger.py           # Logs task stats
│   ├── memory_controller.py      # Direct memory access (no MCP needed)
│   └── mcp_router.py             # Routes memory queries
├── core/
│   ├── context_router.md         # Main routing logic
│   ├── mode_selector.md          # Mode classification rules
│   ├── skill_router.md           # Skill discovery
│   └── token_budget.md           # Budget enforcement rules
├── hooks/                        # Event hooks
├── injector/                     # Context injection
└── logs/
    └── runtime_usage.json        # Usage history

~/.claude_memory/
├── index.json                    # Fast-lookup index
└── server/                       # MCP server modules

~/.claude_wiki/                   # Offline documentation
```

---

## Example Walkthroughs

### Walkthrough 1: "Fix a typo"

**Your message:** `There's a typo in line 42 of README.md — "recieve" should be "receive"`

**Internal flow:**

```
1. Classify: Trivial (single word, single file)
2. Mode selected: LIGHT
3. Context loaded: CLAUDE.md baseline only (~847 tokens)
4. Memory: skipped
5. Tools: skipped
6. Action: read line 42, apply fix
```

**Response:** Claude opens the file, fixes the typo, confirms the change. No extra context was loaded. Token cost: minimal.

**What Claude says if you ask:** `"LIGHT mode — trivial fix, zero runtime overhead."`

---

### Walkthrough 2: "Refactor the auth module"

**Your message:** `The auth module is getting messy. Refactor it to separate concerns — auth logic, token handling, and session management should be in their own files.`

**Internal flow:**

```
1. Classify: Complex (multi-file, architectural judgment needed)
2. Mode selected: DEEP
3. Context loaded: CLAUDE.md baseline + context_router.md + relevant architecture files
4. Memory: retrieve memories tagged "auth" or this project (scored, ≤500 tokens)
5. Tools: tool_loader.py scans for any existing auth-related scripts
6. Plan: break into subtasks, propose file structure
7. Execute: read current module, write three new files, update imports
```

**Response:** Claude reads the existing module, retrieves any prior context about the project's conventions, proposes the new structure, and executes each file change with explanation.

**After the session:** The refactoring approach is stored as a memory, scored for relevance and success. Next time you ask about auth, it surfaces automatically.

---

### Walkthrough 3: "Continue what we did yesterday"

**Your message:** `Let's continue the database migration we started yesterday.`

**Internal flow:**

```
1. Classify: Moderate (continuation task, memory keyword detected: "yesterday")
2. Mode selected: STANDARD
3. Context loaded: CLAUDE.md baseline + context_router.md
4. Memory: retrieve — keywords "database migration" + current repo
   Scores: migration_plan.json (0.91), schema_notes.json (0.78), unrelated (0.32 — excluded)
   Total retrieved: 312 tokens (within 500-token cap)
5. Claude reads the retrieved memories
6. Responds with full context of what was done and what comes next
```

**Response:** Claude accurately recalls the migration plan, the tables already processed, and the next step — without you having to re-explain anything.

**What makes this work:** The 0.32-scored memory was excluded because it scored below the relevance threshold. Only the two high-confidence memories were included, keeping context tight.

---

## Configuration

Your configuration lives at `~/.claude_runtime/configs/runtime_config.json`. After installation it looks like this (paths shown for each platform):

```json
{
  "version": "1.0",
  "runtime_path": "C:/Users/yourname/.claude_runtime",
  "memory_root": "C:/Users/yourname/.claude_memory",
  "memory_server_modules": "C:/Users/yourname/.claude_memory/server",
  "tools_dirs": [],
  "wiki_path": "",
  "defaults": {
    "memory_max_tokens": 500,
    "mode": "STANDARD",
    "log_usage": true
  }
}
```

> On macOS/Linux, paths use `/home/yourname/` or `/Users/yourname/` instead of `C:/Users/yourname/`. The installer fills these in automatically.

### Field Reference

| Field | Type | What it does |
|---|---|---|
| `version` | string | Config schema version. Do not change. |
| `runtime_path` | string | Where the runtime engine is installed. Auto-set by installer. |
| `memory_root` | string | Root directory for the memory system. Auto-set by installer. |
| `memory_server_modules` | string | Path to MCP server code. Auto-derived from `memory_root`. |
| `tools_dirs` | list of strings | Directories Claude searches when looking for tool scripts. |
| `wiki_path` | string | Path to an additional wiki directory (if you have one). |
| `defaults.memory_max_tokens` | integer | Maximum tokens the memory system can inject per session. Default: 500. |
| `defaults.mode` | string | Default mode if classification is ambiguous. Options: `LIGHT`, `STANDARD`, `DEEP`. |
| `defaults.log_usage` | boolean | Whether to log task usage to `runtime_usage.json`. Default: true. |

### Adding Your Own Tool Directories

If you have a `tools/` folder in your project, add it to `tools_dirs` so Claude can discover scripts by keyword:

```json
{
  "tools_dirs": [
    "/home/yourname/my-project/tools",
    "/home/yourname/shared-scripts"
  ]
}
```

After saving, Claude can run:

```
python ~/.claude_runtime/controllers/tool_loader.py --query "scrape"
```

And get back a ranked list of matching scripts from your directories.

### Adding a Wiki Knowledge Base

If you have a folder of Markdown documentation you want Claude to query:

```json
{
  "wiki_path": "/home/yourname/my-notes/wiki"
}
```

The wiki system expects an `index.md` file in that directory. Claude will use the index to find relevant pages before reading them.

### Adjusting the Memory Budget

To increase the token cap for memory retrieval (useful for complex projects with rich history):

```json
{
  "defaults": {
    "memory_max_tokens": 800
  }
}
```

Keep in mind that higher budgets mean more context used per session. The default of 500 is calibrated to balance recall quality against cost.

### Disabling Usage Logging

```json
{
  "defaults": {
    "log_usage": false
  }
}
```

This stops writes to `runtime_usage.json`. The `--stats` command will have no data to show.

---

## Commands Reference

### Installer Commands (`python install.py`)

Run these from the `claude-meister` directory you cloned.

| Flag | What it does |
|---|---|
| `--full` | Full installation: runtime engine + memory server + wiki knowledge base |
| `--runtime-only` | Install the runtime engine only (skips memory and wiki) |
| `--memory-only` | Install the memory server only |
| `--wiki-only` | Install the wiki knowledge base only |
| `--no-wiki` | Full install minus the wiki (runtime + memory) |
| `--update` | Update an existing installation (preserves memories, config, and logs) |
| `--uninstall` | Remove everything (prompts before deleting memories) |
| `--verify` | Run post-install health checks and report what passed/failed |
| `--stats` | Show usage dashboard for the last 30 days |

**Examples:**

```bash
# First-time install, everything
python install.py --full

# Install without wiki (faster, smaller)
python install.py --no-wiki

# Check if everything is healthy
python install.py --verify

# View your usage stats
python install.py --stats

# Update after pulling new version
python install.py --update

# Remove Claude_Meister completely
python install.py --uninstall
```

### Controller Commands

These scripts live in `~/.claude_runtime/controllers/` after installation. Claude calls them automatically, but you can also run them directly.

#### `tool_loader.py` — Discover tools by keyword

```bash
# Find tools matching a keyword
python ~/.claude_runtime/controllers/tool_loader.py --query "scrape"

# Scan a specific directory instead of config dirs
python ~/.claude_runtime/controllers/tool_loader.py --query "api" --scan-dir /path/to/tools

# List all tools without filtering
python ~/.claude_runtime/controllers/tool_loader.py --all
```

Example output:

```json
[
  {"name": "scrape_single_site", "path": "/path/to/tools/scrape_single_site.py",
   "description": "Fetch and parse a single web page", "match_score": 1.0},
  {"name": "scrape_batch", "path": "/path/to/tools/scrape_batch.py",
   "description": "Batch scrape multiple URLs", "match_score": 0.5}
]
```

#### `usage_logger.py` — Log task usage and view stats

```bash
# Log a completed task
python ~/.claude_runtime/controllers/usage_logger.py \
  --mode STANDARD \
  --tools-used "tool_loader.py,advisor.py" \
  --memory-tokens 312 \
  --task-summary "Refactored auth module"

# View usage stats
python ~/.claude_runtime/controllers/usage_logger.py --stats
```

#### `memory_controller.py` — Direct memory access (no MCP required)

```bash
# Query memories directly (useful for debugging)
python ~/.claude_runtime/controllers/memory_controller.py --query "auth" --repo my-project
```

---

## Updating

When a new version of Claude_Meister is released:

```bash
# Pull the latest code
git pull

# Run the updater
python install.py --update
```

**What the updater preserves:**
- `~/.claude_runtime/logs/runtime_usage.json` — your usage history
- `~/.claude_runtime/configs/runtime_config.json` — your configuration (if you have edited it)
- All stored memories in `~/.claude_memory/`

**What the updater overwrites:**
- All core behavioral documents (`context_router.md`, `mode_selector.md`, etc.)
- All controller scripts (`tool_loader.py`, `usage_logger.py`, etc.)
- All MCP server modules
- All template-derived files (re-substituted with your current home directory)

**What this means in practice:** Your memories, config customizations, and usage logs survive an update. The brains of the system get refreshed with the latest version.

---

## Uninstalling

```bash
python install.py --uninstall
```

The uninstaller does the following, in order:

1. Removes the Claude_Meister block from `~/.claude/CLAUDE.md` — your content outside the markers is untouched.
2. Unregisters the memory server: runs `claude mcp remove memory`.
3. **Asks you** whether to keep your stored memories (default: yes, keep them).
4. Deletes `~/.claude_runtime/`.
5. Optionally deletes `~/.claude_memory/server/` — the server code. Your actual memory data at `~/.claude_memory/` is kept by default.

After uninstalling, Claude Code returns to its default behavior. Your `CLAUDE.md` is left in the state it was in before Claude_Meister appended its block.

---

## Troubleshooting

### Installation Issues

#### "Python not found" or "python is not recognized"

Python is not on your PATH. Fix:
- **Windows:** Re-run the Python installer from python.org and check "Add Python to PATH". Then open a fresh terminal.
- **macOS:** Try `python3 --version`. If that works, use `python3 install.py --full` throughout.
- **Linux:** Run `sudo apt install python3` (Debian/Ubuntu) or the equivalent for your distro.

#### "No module named mcp" or "No module named fastmcp"

The packages are not installed. Run:

```bash
pip install mcp fastmcp
```

If you have multiple Python versions, make sure you are installing into the same Python that runs `install.py`. Use:

```bash
python -m pip install mcp fastmcp
```

#### "Claude Code not found"

The `claude` CLI is not installed or not on PATH. Install Claude Code from [claude.ai/code](https://claude.ai/code), then open a fresh terminal and retry.

#### "Permission denied" writing to home directory

- **macOS/Linux:** Run `ls -la ~` to check ownership. If you do not own your home directory, contact your system administrator.
- **Windows:** Run Command Prompt as Administrator.

#### "Existing installation detected"

The installer found a previous installation. You have three options:
- **Update** — recommended. Preserves all your data.
- **Clean install** — deletes everything and starts fresh. You will lose stored memories.
- **Abort** — does nothing.

#### "Incomplete install detected"

The installer found a partial previous install (directory exists but config is missing). It will run a clean installation automatically.

#### OneDrive-redirected home directory (Windows)

If your home directory is inside OneDrive (e.g. `C:/Users/yourname/OneDrive/...`), the installer will warn you. OneDrive sync can cause file locking issues. You can set the `USERPROFILE` environment variable to a local directory, or proceed and watch for any sync conflicts.

---

### Runtime Issues

#### Mode classification seems wrong

Claude is classifying a simple task as DEEP, or a complex task as LIGHT. This is usually a prompt phrasing issue. Add explicit context:

- For a simple task: "Quick fix:" at the start of your message signals simple.
- For a complex task: "Architecture question:" signals DEEP.

#### `context_router.md` cannot be found

The runtime path in `runtime_config.json` does not match where the files actually are. Run:

```bash
python install.py --verify
```

If the runtime engine check fails, run `python install.py --runtime-only` to reinstall the engine.

#### `runtime_config.json` shows bad JSON error

The config file was corrupted (e.g., you made an edit with a syntax error). The runtime falls back to defaults automatically. To fix:

1. Open `~/.claude_runtime/configs/runtime_config.json` in a text editor.
2. Validate it at [jsonlint.com](https://jsonlint.com).
3. Fix any errors and save.

#### Usage stats show 0 entries

Either `log_usage` is set to `false` in your config, or you have not used Claude Code since installing. Check your config:

```bash
python install.py --stats
```

If stats are empty after confirmed use, check that `~/.claude_runtime/logs/runtime_usage.json` exists and is writable.

---

### Memory Issues

#### Memories are not being retrieved

First, confirm the MCP server is registered:

```bash
claude mcp list
```

You should see `memory` in the output. If not, re-run:

```bash
python install.py --memory-only
```

Then restart Claude Code. MCP tools only become available after a fresh session.

#### "memory" name conflict during registration

If you already have an MCP server named "memory", the installer will ask: replace it, rename the new one, or skip. Replacing is usually correct unless you have a different memory server you depend on.

#### Wrong Python version running the memory server

If `mcp` is installed under Python 3.11 but the memory server launches with Python 3.8, the import will fail. The installer tries to detect the correct Python, but on machines with multiple versions you may need to confirm:

```bash
which python  # macOS/Linux
where python  # Windows
```

Make sure this is the Python where you ran `pip install mcp fastmcp`.

#### `index.json` corrupted

If you see an error about `index.json` being invalid JSON, the memory system will return empty results and log a warning. Fix:

```bash
# Back up the corrupted index
cp ~/.claude_memory/index.json ~/.claude_memory/index.json.bak

# Delete and let the system rebuild it
rm ~/.claude_memory/index.json
```

The index will be rebuilt on the next memory store operation. Existing memory files are unaffected.

---

### Platform-Specific Issues

#### Windows: Encoding errors ("charmap codec can't encode")

This is a Windows console encoding issue. Fix by setting the environment variable before running:

```cmd
set PYTHONIOENCODING=utf-8
python install.py --full
```

Or run in Windows Terminal (which uses UTF-8 by default) instead of the legacy Command Prompt.

#### Windows: Path length errors

Windows has a 260-character path limit by default. If you installed deep in a nested directory, this can trigger errors. Fix:
1. Move the `claude-meister` folder closer to the root: `C:/claude-meister/`
2. Or enable long paths in Windows: search "Enable Win32 long paths" in Group Policy Editor.

#### macOS: "Cannot be opened because the developer cannot be verified"

Gatekeeper is blocking the scripts. Run:

```bash
xattr -d com.apple.quarantine install.py
```

Or right-click `install.py` in Finder, choose Open, then confirm you want to open it.

#### macOS: System Python vs Homebrew Python

macOS ships with Python 3 but it may be an older version. If you installed a newer Python via Homebrew, use `python3` explicitly:

```bash
python3 install.py --full
```

Check which Python has your packages:

```bash
python3 -c "import mcp; print('OK')"
```

#### Linux: Locale errors

If you see locale-related errors, set:

```bash
export PYTHONIOENCODING=utf-8
python install.py --full
```

#### WSL (Windows Subsystem for Linux)

Claude_Meister detects WSL automatically and uses Linux-style paths. Important: your Claude Code installation must also be running inside WSL (not the Windows-side Claude Code) for the MCP registration to work. Mixed WSL/Windows setups are not supported.

---

### The Nuclear Option

If nothing works and you want a completely clean slate:

```bash
# Uninstall via installer if it runs
python install.py --uninstall

# Manual removal if installer won't run
rm -rf ~/.claude_runtime
rm -rf ~/.claude_memory/server   # Keep ~/.claude_memory/ itself if you want your memories

# On Windows (run in PowerShell):
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude_runtime"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude_memory\server"

# Remove the block from CLAUDE.md manually
# Open ~/.claude/CLAUDE.md and delete everything between:
# === Claude_Meister Runtime ===
# and
# === End Claude_Meister Runtime ===

# Unregister the MCP server
claude mcp remove memory
```

After this, reinstall from scratch with `python install.py --full`.

---

## FAQ

**Does Claude_Meister send any data anywhere?**

No. Everything runs locally. The memory server runs on your machine via stdio (standard input/output — a local communication channel, not a network). No data leaves your computer.

**Does it call any external APIs?**

No. Claude_Meister has no API keys and makes no outbound network requests. It is purely local file operations and subprocess calls.

**Will it slow Claude Code down?**

No. In LIGHT mode (the majority of interactions), the runtime is not loaded at all — there is zero overhead. In STANDARD and DEEP modes, reading a few local Markdown files adds milliseconds.

**Will it conflict with my existing CLAUDE.md?**

No. The installer appends a clearly marked block to your existing CLAUDE.md. Everything outside the markers is untouched. When you uninstall, the block is removed and your file is restored to its previous state.

**Can I use this on multiple machines?**

Yes. Install it on each machine separately. Memories are local to each machine — they do not sync automatically. If you want to share memories, you can copy `~/.claude_memory/` between machines.

**What if I update Claude Code — will Claude_Meister break?**

The memory server registration should persist across Claude Code updates. If the `claude` CLI changes how it handles MCP servers, run `python install.py --verify` to check, and `python install.py --update` to re-register if needed.

**Does it work with Claude's paid tiers?**

Yes. Claude_Meister reduces the tokens Claude Code loads per session. This benefits all tiers — fewer tokens means lower cost and more context available for your actual work.

**Can I contribute to or modify the behavioral documents?**

Yes — they are plain Markdown files in `~/.claude_runtime/core/`. Edit them freely. Note that running `python install.py --update` will overwrite them with the latest versions from the repo. Keep a backup or fork the repo if you want permanent customizations.

---

## Contributing

### Reporting Bugs

Open an issue on GitHub with:
1. Your OS and Python version (`python --version`)
2. The full error message (copy-paste, do not screenshot)
3. The output of `python install.py --verify`
4. What you expected to happen vs. what actually happened

### Requesting Features

Open an issue with the label `enhancement`. Describe:
1. The problem you are trying to solve (not just the feature you want)
2. How you currently work around it
3. What success looks like

### Development Setup

```bash
git clone https://github.com/Mintsolester/claude-meister.git
cd claude-meister

# Install test dependencies
pip install pytest

# Run the test suite
pytest tests/ -v
```

The test suite covers all 8 installer modules, the memory server, the controller scripts, and the verification system. All tests must pass before opening a pull request.

**Project structure:**

```
install.py          # Entry point — orchestrates all installer modules
installer/          # 8 installer modules (paths, runtime, memory, wiki,
                    #   claude_md, mcp, verify, + __init__)
runtime/            # Files that get installed to ~/.claude_runtime/
memory/             # Files that get installed to ~/.claude_memory/
wiki/               # Files that get installed to ~/.claude_wiki/
templates/          # Template files with {{PLACEHOLDER}} tokens
tests/              # Full test suite
docs/               # Architecture and design documentation
DEVIATIONS.md       # Audit trail of deliberate plan deviations
```

---

## License & Credits

**License:** MIT — see [LICENSE](LICENSE) for full text.

**Author:** Mintsolester

**Built on:**
- [Claude Code](https://claude.ai/code) — the AI coding assistant this runtime extends
- [FastMCP](https://github.com/jlowin/fastmcp) — the framework powering the memory MCP server
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io) — the standard that enables Claude Code to call external tools

---

*Claude_Meister is not affiliated with Anthropic. It is an independent project that extends Claude Code's behavior using its public plugin interfaces.*
