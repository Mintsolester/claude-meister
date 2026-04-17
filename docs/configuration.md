# Configuration Reference — Claude_Meister

This document covers every field in `runtime_config.json`, how to extend the system with your own tool directories and wikis, how to tune memory budgets, and how to customize the CLAUDE.md block.

> For installation instructions, see [docs/quickstart.md](quickstart.md) or the [README](../README.md#quick-start).

---

## Where the Config Lives

```
~/.claude_runtime/configs/runtime_config.json
```

On Windows this resolves to something like:

```
C:/Users/yourname/.claude_runtime/configs/runtime_config.json
```

On macOS/Linux:

```
/home/yourname/.claude_runtime/configs/runtime_config.json
```

The installer creates this file and fills in the correct paths for your machine. You edit it after installation to customize behavior.

---

## Full Config With Defaults

After a fresh install, the file looks like this (paths shown for Windows):

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

---

## Field Reference

### `version`

**Type:** string
**Default:** `"1.0"`
**Do not change.** This is the config schema version. The runtime uses it to detect incompatible configs. If you manually set this to a different value, the runtime may behave unexpectedly.

---

### `runtime_path`

**Type:** string
**Default:** auto-set by installer (`~/.claude_runtime`)

The directory where the runtime engine is installed. Controllers, behavioral documents, hooks, and logs all live here.

Do not change this unless you intentionally moved your runtime installation. If you change it and the path does not exist, the runtime falls back to defaults.

**Example:**
```json
"runtime_path": "C:/Users/yourname/.claude_runtime"
```

---

### `memory_root`

**Type:** string
**Default:** auto-set by installer (`~/.claude_memory`)

Root directory of the memory system. Stored memories (as JSON files) and the fast-lookup index live here.

Do not change this unless you moved your memory directory. If the path does not exist, the memory system initializes an empty index at the new location.

**Example:**
```json
"memory_root": "C:/Users/yourname/.claude_memory"
```

---

### `memory_server_modules`

**Type:** string
**Default:** auto-derived as `memory_root + "/server"`

Path to the MCP server Python modules. This is auto-derived from `memory_root` — you almost never need to set it manually.

If you see import errors from the memory server, verify this path exists and contains `main.py`.

---

### `tools_dirs`

**Type:** list of strings
**Default:** `[]` (empty — only built-in tools are discoverable)

A list of directories Claude scans when you ask it to find tool scripts. When Claude calls `tool_loader.py --query "keyword"`, it searches these directories for Python scripts whose names or docstrings match.

**How to add your project's tools:**

```json
{
  "tools_dirs": [
    "C:/Users/yourname/my-project/tools",
    "C:/Users/yourname/shared-scripts"
  ]
}
```

On macOS/Linux:

```json
{
  "tools_dirs": [
    "/home/yourname/my-project/tools",
    "/home/yourname/shared-scripts"
  ]
}
```

After saving, Claude can discover matching scripts:

```bash
python ~/.claude_runtime/controllers/tool_loader.py --query "scrape"
```

Expected output:

```json
[
  {
    "name": "scrape_single_site",
    "path": "C:/Users/yourname/my-project/tools/scrape_single_site.py",
    "description": "Fetch and parse a single web page",
    "match_score": 1.0
  }
]
```

**Tips:**
- Use absolute paths. Relative paths are not resolved and will silently produce no results.
- Directories that do not exist are skipped with a warning in the output — they do not cause errors.
- The tool scanner looks at file names and Python docstrings. A descriptive module-level docstring improves match quality.

---

### `wiki_path`

**Type:** string
**Default:** `""` (empty — wiki disabled)

Path to a directory of Markdown documentation that Claude can query offline. If you have personal notes, internal docs, or project wikis in Markdown format, point `wiki_path` at them.

**Requirement:** The directory must contain an `index.md` file. Claude reads the index first to find relevant pages.

**Example:**

```json
{
  "wiki_path": "C:/Users/yourname/my-notes/wiki"
}
```

On macOS/Linux:

```json
{
  "wiki_path": "/home/yourname/my-notes/wiki"
}
```

After setting this, Claude can read your wiki in STANDARD and DEEP modes without an internet connection.

**Windows note:** If the wiki directory is inside OneDrive, file locking during sync can cause intermittent read failures. Store the wiki in a local (non-synced) directory for best results.

---

### `defaults.memory_max_tokens`

**Type:** integer
**Default:** `500`
**Range:** 100–2000 (practical)

The maximum number of tokens the memory system can inject per session. When memory retrieval returns results, they are ranked by score and trimmed to fit within this budget.

**Increasing the budget** (useful for complex projects with rich history):

```json
{
  "defaults": {
    "memory_max_tokens": 800
  }
}
```

**Decreasing the budget** (useful when you want to minimize context cost):

```json
{
  "defaults": {
    "memory_max_tokens": 300
  }
}
```

The default of 500 tokens is calibrated to surface 2–4 high-quality memories without significantly impacting context cost. Values above 1000 may noticeably increase context overhead on every STANDARD and DEEP session.

---

### `defaults.mode`

**Type:** string
**Default:** `"STANDARD"`
**Options:** `"LIGHT"`, `"STANDARD"`, `"DEEP"`

The fallback mode when task classification is ambiguous. In practice, classification is clear most of the time — this field is a tiebreaker.

Change this to `"DEEP"` if you consistently do complex work and want Claude to default to loading full context. Change to `"LIGHT"` if you want zero overhead by default and will manually signal complexity when needed.

```json
{
  "defaults": {
    "mode": "DEEP"
  }
}
```

---

### `defaults.log_usage`

**Type:** boolean
**Default:** `true`

When `true`, each task is logged to `~/.claude_runtime/logs/runtime_usage.json`. This enables the `--stats` dashboard.

Disable logging if you have privacy concerns about logging task summaries locally, or if disk writes are a concern:

```json
{
  "defaults": {
    "log_usage": false
  }
}
```

Note: with `log_usage: false`, running `python install.py --stats` will show no data.

---

## Customizing the CLAUDE.md Block

The installer appends a runtime block to `~/.claude/CLAUDE.md` between these HTML comment markers:

```
<!-- RUNTIME:START -->
... runtime instructions ...
<!-- RUNTIME:END -->
```

**What you can safely edit:**
- The text content between the markers — Claude reads this as instructions.
- The Quick References section — update paths if you move directories.
- The mode classification examples — add project-specific examples to improve accuracy.

**What you must not change:**
- The marker lines themselves (`<!-- RUNTIME:START -->` and `<!-- RUNTIME:END -->`). These are required for the updater and uninstaller to find and manage the block.
- Path references inside the block — these are templated by the installer. If you edit them and then run `python install.py --update`, the installer will re-template them correctly, overwriting your manual edits.

**Adding your own instructions outside the markers:**

Everything outside the `<!-- RUNTIME:START -->` / `<!-- RUNTIME:END -->` block is untouched by Claude_Meister. Add your own project-specific instructions before or after the block:

```markdown
# My Custom Instructions
... your content here ...

<!-- RUNTIME:START -->
... Claude_Meister block (do not edit manually) ...
<!-- RUNTIME:END -->

# More Custom Instructions
... your content here ...
```

---

## Platform-Specific Notes

### Windows

- All paths in `runtime_config.json` should use **forward slashes** (`/`), not backslashes (`\`). Claude Code uses forward slashes internally, even on Windows.
- Correct: `"C:/Users/yourname/.claude_runtime"`
- Incorrect: `"C:\\Users\\yourname\\.claude_runtime"`

- If your username contains spaces (e.g., `C:/Users/John Doe/`), the installer wraps paths in quotes automatically. You do not need to escape spaces in `runtime_config.json`.

- If your home directory is inside OneDrive (`C:/Users/yourname/OneDrive/...`), consider pointing `tools_dirs` and `wiki_path` at local directories to avoid sync-related file locking.

### WSL (Windows Subsystem for Linux)

- If you are running Claude Code inside WSL, use Linux-style paths in your config: `/home/yourname/.claude_runtime`.
- Do not mix Windows paths (starting with `C:/`) with a WSL-based Claude Code installation. The paths must match the environment where Claude Code runs.

### macOS

- On macOS with Homebrew Python, `python` may point to an older system Python. If you installed Python via Homebrew, use `python3` for all commands. The runtime itself uses `Path.home()` dynamically, so it resolves correctly regardless.
- The default home is `/Users/yourname/`, so paths look like `/Users/yourname/.claude_runtime`.

### Linux

- Home is `/home/yourname/` by default.
- If `$HOME` is overridden in your environment, `Path.home()` follows it. The installer uses `Path.home()` at install time, so the resolved paths in `runtime_config.json` reflect your environment at installation.

---

## Editing Tips

- After editing `runtime_config.json`, no restart is required — the runtime reads the config fresh each session.
- If you introduce a JSON syntax error, the runtime falls back to built-in defaults and logs a warning. Validate your edits at [jsonlint.com](https://jsonlint.com) if you are unsure.
- A corrupted `runtime_config.json` does not break Claude Code — it just disables custom tools and wiki. Run `python install.py --verify` to detect config issues.
- Running `python install.py --update` **preserves** your `runtime_config.json` if you have made changes to it. It will not be overwritten unless you run `python install.py --full` (clean install).
