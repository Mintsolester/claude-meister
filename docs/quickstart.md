# Quick Start — Claude_Meister

**You're a busy developer. Here's the short version.**

> For a full installation walkthrough with explanations of every step, see the [README — Detailed Installation Guide](../README.md#detailed-installation-guide).

---

## Prerequisites (30 seconds)

You need three things. Open a terminal and verify each:

```bash
# 1. Python 3.8 or newer
python --version
# Expected: Python 3.x.x  (where x >= 8)

# 2. pip packages for the memory server
pip install mcp fastmcp

# 3. Claude Code CLI
claude --version
# Expected: claude/1.x.x
```

If any of these fail, see [Troubleshooting — Installation Issues](troubleshooting.md#installation-issues).

---

## Three Commands

```bash
# 1. Clone and enter the repo
git clone https://github.com/Mintsolester/claude-meister.git
cd claude-meister

# 2. Install everything
python install.py --full

# 3. Verify the install
python install.py --verify
```

That is it. Then **restart Claude Code**.

---

## What You Should See

After `python install.py --full`:

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

After `python install.py --verify`:

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

If any line shows `FAIL`, go to [Troubleshooting](troubleshooting.md).

---

## You're Done

Restart Claude Code, open any project, and start working normally. Claude_Meister runs silently in the background.

To confirm it is active, ask Claude:

```
What mode are you operating in right now?
```

You should get something like:

```
LIGHT mode — this is a simple question, so I'm not loading the full runtime.
No extra context cost.
```

---

## Common Flags

```bash
python install.py --full          # Everything (recommended for first install)
python install.py --no-wiki       # Runtime + memory only (faster)
python install.py --verify        # Check health at any time
python install.py --stats         # Usage dashboard (last 30 days)
python install.py --update        # Update after git pull
python install.py --uninstall     # Remove Claude_Meister
```

---

## Next Steps

- **Configure tool directories and wiki:** [docs/configuration.md](configuration.md)
- **Understand how it works:** [docs/architecture.md](architecture.md)
- **Something went wrong:** [docs/troubleshooting.md](troubleshooting.md)
- **Full reference:** [README.md](../README.md)
