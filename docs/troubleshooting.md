# Troubleshooting — Claude_Meister

Categorized by symptom. Each section starts with the most common cause and works down to edge cases.

> For a quick overview of common issues during first-time setup, see the [README — Troubleshooting section](../README.md#troubleshooting). This document goes deeper and covers more scenarios.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Runtime Issues](#runtime-issues)
3. [Memory Issues](#memory-issues)
4. [Platform-Specific Issues](#platform-specific-issues)
5. [Nuclear Option](#nuclear-option)

---

## Installation Issues

### "Python not found" / "python is not recognized as an internal or external command"

**What it means:** Python is not installed, or it is installed but not on your system PATH (the list of directories the terminal searches for executables).

**Fix on Windows:**
1. Download the installer from [python.org/downloads](https://www.python.org/downloads/).
2. Run the installer. On the first screen, **check "Add Python to PATH"** before clicking Install.
3. Close your terminal and open a fresh one.
4. Retry `python --version`.

**Fix on macOS:**
Try `python3 --version` instead of `python`. If that works, use `python3` for all Claude_Meister commands:
```bash
python3 install.py --full
python3 install.py --verify
```
If `python3` also fails, install Python via [Homebrew](https://brew.sh): `brew install python3`.

**Fix on Linux:**
```bash
sudo apt install python3   # Debian/Ubuntu
sudo dnf install python3   # Fedora/RHEL
```

---

### Python version is too old ("Python 3.x.x" where x < 8)

**What it means:** Claude_Meister requires Python 3.8 or newer. Python 2 is not supported.

**Check your version:**
```bash
python --version
python3 --version
```

**Fix:** Download Python 3.11 or newer from [python.org](https://www.python.org/downloads/). On Windows, uninstall the old version first (or install the new one alongside it and update your PATH to point to the newer one).

---

### "No module named mcp" / "No module named fastmcp"

**What it means:** The Python packages required for the memory server are not installed in the Python environment that is running the installer.

**Fix (most cases):**
```bash
pip install mcp fastmcp
```

**Fix when multiple Python versions are installed:**
```bash
python -m pip install mcp fastmcp
```
Using `python -m pip` ensures you install into the same Python that runs `python install.py`.

**Verify the install:**
```bash
python -c "import mcp; import fastmcp; print('OK')"
```
If this prints `OK`, you are set.

---

### "Claude Code not found" / "'claude' is not recognized"

**What it means:** The Claude Code CLI is not installed, or it is not on your PATH.

**Fix:**
1. Install Claude Code from [claude.ai/code](https://claude.ai/code).
2. Follow its setup instructions, which add `claude` to your PATH.
3. Open a **fresh terminal** (PATH changes do not apply to open terminals).
4. Verify: `claude --version` — expected output: `claude/1.x.x`

---

### "Permission denied" writing to home directory

**What it means:** The installer cannot create files in your home directory due to filesystem permissions.

**Fix on macOS/Linux:**
```bash
ls -la ~
```
Check that you own your home directory. If you do not (e.g., shared system), contact your administrator. If you do own it but permissions are wrong:
```bash
chmod 755 ~
```

**Fix on Windows:**
Run Command Prompt as Administrator:
- Press `Win + S`, search for "Command Prompt"
- Right-click → "Run as administrator"
- Retry the installer from that window.

---

### "Existing installation detected"

**What it means:** The installer found a previous Claude_Meister install at the expected locations.

**Your three options:**
- **Update (recommended):** Refreshes all core files, preserves memories, config, and logs. Same as running `python install.py --update`.
- **Clean install:** Deletes the existing installation and starts fresh. You will lose stored memories unless you back up `~/.claude_memory/` first.
- **Abort:** Does nothing. Safe to choose if you were not expecting this prompt.

---

### "Incomplete install detected. Running clean."

**What it means:** The installer found a directory (`~/.claude_runtime/` or `~/.claude_memory/`) but the config file is missing — usually the result of a previous install that was interrupted.

**What happens:** The installer automatically runs a clean install. This is safe — no memories are lost because incomplete installs typically did not reach the memory writing stage.

---

### Antivirus software blocks the installer

**What it means:** Windows Defender or a third-party antivirus is quarantining `install.py` or one of the generated scripts.

**The installer cannot detect this proactively.**

**Fix:**
1. Check your antivirus quarantine log for file names containing `claude_meister` or `install.py`.
2. Mark the quarantined files as trusted / add an exception for the `claude-meister` directory.
3. Re-run the installer.

If you are on a corporate machine with managed antivirus, you may need to request an exception from your IT department.

---

### "OneDrive-redirected home directory" warning

**What it means:** Your Windows home directory is inside OneDrive (e.g., `C:/Users/yourname/OneDrive/Documents`). OneDrive sync can cause file locking conflicts with runtime files.

**Fix:**
Option A — proceed and monitor. Most users do not experience issues. If you see random `PermissionError` messages during operation, switch to Option B.

Option B — set `USERPROFILE` to a local directory before installing:
```cmd
set USERPROFILE=C:\local_home\yourname
python install.py --full
```
This installs everything to `C:/local_home/yourname/.claude_runtime/` and `C:/local_home/yourname/.claude_memory/` — outside OneDrive.

---

### Disk space warning (< 50 MB free)

**What it means:** The installer detected less than 50 MB of free disk space. The install itself is about 5 MB, but memories grow over time.

**Fix:** Free up disk space before installing. A minimum of 200 MB free is recommended for comfortable long-term use.

---

## Runtime Issues

### Mode classification seems wrong (simple task → DEEP, complex task → LIGHT)

**What it means:** Claude is misclassifying task complexity.

**Fix — add an explicit signal to your prompt:**

For simple tasks, prefix with a signal:
```
Quick fix: there's a typo on line 42.
Simple question: what does this function return?
```

For complex tasks:
```
Architecture question: should I redesign the auth module?
Complex feature: I need to add OAuth2 to the entire app.
```

**If misclassification is consistent** (Claude always picks the wrong mode for a whole category of tasks), you can edit the classification examples in `~/.claude_runtime/core/mode_selector.md`. Note that running `python install.py --update` will overwrite this file — keep a copy or fork the repo if you want permanent changes.

---

### `context_router.md` cannot be found

**What it means:** The `runtime_path` in your config points to a directory that either does not exist or is missing `core/context_router.md`.

**Diagnosis:**
```bash
python install.py --verify
```

If the "Runtime engine" check fails, run:
```bash
python install.py --runtime-only
```
This reinstalls just the runtime engine without touching memories or the CLAUDE.md block.

**Manual check (Windows):**
```cmd
dir "C:\Users\yourname\.claude_runtime\core\"
```

**Manual check (macOS/Linux):**
```bash
ls ~/.claude_runtime/core/
```
Expected files: `context_router.md`, `mode_selector.md`, `skill_router.md`, `token_budget.md`

---

### `runtime_config.json` shows a bad JSON error

**What it means:** The config file has a syntax error. This happens if you edited the JSON manually and made a mistake (missing comma, trailing comma, unquoted key, etc.).

**Behavior:** The runtime falls back to built-in defaults automatically — Claude Code keeps working, but your custom tools directories and wiki path are ignored.

**Fix:**
1. Open `~/.claude_runtime/configs/runtime_config.json` in a text editor.
2. Paste the contents into [jsonlint.com](https://jsonlint.com) and click Validate.
3. Fix any reported errors.
4. Save and verify: `python install.py --verify`

---

### `runtime_usage.json` corrupted

**What it means:** The usage log file has invalid JSON (e.g., interrupted write during a crash).

**Behavior:** The runtime detects this, renames the corrupted file to `runtime_usage.json.corrupted`, and creates a fresh one. Usage history before the corruption is lost, but no other functionality is affected.

**Manually triggering recovery:**
```bash
# Backup the corrupted file
cp ~/.claude_runtime/logs/runtime_usage.json ~/.claude_runtime/logs/runtime_usage.json.bak

# Delete it — a fresh one will be created on next use
rm ~/.claude_runtime/logs/runtime_usage.json
```

---

### Tool directory not being searched

**What it means:** A directory in `tools_dirs` is not being searched by `tool_loader.py`.

**Common causes:**
1. The path does not exist on disk.
2. The path uses backslashes (`\`) instead of forward slashes (`/`) on Windows.
3. The path is relative instead of absolute.

**Diagnosis:**
```bash
python ~/.claude_runtime/controllers/tool_loader.py --query "test" --verbose
```
The `--verbose` flag (if supported) shows which directories were scanned and which were skipped.

**Fix:** Open `~/.claude_runtime/configs/runtime_config.json` and correct the path. Use absolute paths with forward slashes:
```json
{
  "tools_dirs": ["C:/Users/yourname/my-project/tools"]
}
```

---

### Usage stats show 0 entries

**What it means:** Either logging is disabled in config, or `runtime_usage.json` does not exist yet.

**Check your config:**
```bash
cat ~/.claude_runtime/configs/runtime_config.json
```
Look for `"log_usage": false`. If that is the issue, change it to `true` and start a new session.

**Check the log file exists:**
```bash
# macOS/Linux
ls ~/.claude_runtime/logs/

# Windows (PowerShell)
dir "$env:USERPROFILE\.claude_runtime\logs\"
```

If the file exists but is empty after confirmed use, verify that Claude Code has write access to that directory.

---

### `memory_scorer` import fails (fallback to keyword-only scoring)

**What it means:** The runtime could not import `memory_scorer.py` from the memory server modules directory. The system falls back to keyword-only scoring — memories are still retrieved, but ranking quality degrades.

**Diagnosis:**
```bash
python -c "import sys; sys.path.insert(0, '$HOME/.claude_memory/server'); import memory_scorer; print('OK')"
```
Replace `$HOME` with your actual home path.

**Common causes:**
- `~/.claude_memory/server/` is missing (memory server not installed).
- `fastmcp` is not installed in the Python environment.
- File permissions prevent reading the module.

**Fix:**
```bash
python install.py --memory-only
```

---

## Memory Issues

### Memories are not being retrieved

**Step 1 — Verify the MCP server is registered:**
```bash
claude mcp list
```
You should see `memory` in the output. If not, continue to Step 2.

**Step 2 — Re-register the memory server:**
```bash
python install.py --memory-only
```
Then **restart Claude Code completely** (close all windows, reopen).

**Step 3 — Verify it appears after restart:**
```bash
claude mcp list
```

**Step 4 — If still missing, register manually:**
```bash
claude mcp add memory python "C:/Users/yourname/.claude_memory/server/main.py"
```
Replace the path with your actual `memory_root` from `runtime_config.json`.

**Important:** MCP tools only become available after a fresh session start. Registering the server while Claude Code is running requires a restart before tools appear.

---

### "memory" name conflict during MCP registration

**What it means:** You already have an MCP server named "memory" registered (possibly from a different project or a previous Claude_Meister install).

**Options the installer presents:**
- **Replace:** Removes the old registration and registers the new one. Choose this if the old "memory" server is a stale Claude_Meister install.
- **Rename:** Registers the new server under a different name (e.g., `meister_memory`). You will need to update your CLAUDE.md to reference the new name.
- **Skip:** Does not register. The memory server will not be available until you manually register it.

**Manual check of existing MCP servers:**
```bash
claude mcp list
```
Review the output to identify which server is named "memory" and where it points.

---

### Wrong Python version running the memory server

**What it means:** `mcp` and `fastmcp` are installed under one Python version, but the memory server is launching with a different Python that does not have those packages.

**Diagnosis:**
```bash
# macOS/Linux — see which python is on PATH
which python
which python3

# Windows
where python
```

**Verify mcp is accessible from the PATH python:**
```bash
python -c "import mcp; print('OK')"
```

**If mcp is only available in python3:**
Manually re-register the memory server using the correct Python path:
```bash
claude mcp remove memory
claude mcp add memory python3 "~/.claude_memory/server/main.py"
```
Use the full path to python3 if needed (e.g., `/usr/bin/python3`).

---

### `index.json` corrupted

**What it means:** The memory index file has invalid JSON. The memory system falls back to returning empty results and logs a warning.

**Fix:**
```bash
# Back up the corrupted file
cp ~/.claude_memory/index.json ~/.claude_memory/index.json.bak

# Delete the index — it will be rebuilt on next memory_store call
rm ~/.claude_memory/index.json
```
The index is a lookup accelerator — it does not contain the memory content itself. Individual memory files (`<uuid>.json`) are unaffected. The index rebuilds automatically when you next store a memory.

---

### Memories exist but are not surfacing for a project

**What it means:** Memories were stored under a different project identifier than the current repo.

**How project detection works:** The memory system identifies the current project by the directory name or an explicit project tag. If you moved a project, renamed its directory, or stored memories with `--repo project-a` and then queried with `--repo project-b`, the memories will not match.

**Diagnosis:**
```bash
python ~/.claude_runtime/controllers/memory_controller.py --query "" --repo ""
```
Omit both filters to see all stored memories. Look at the `repo` tags on returned entries.

**Fix:** Use `memory_evolve` to update the `repo` tag on relevant memories, or store new memories with the correct project identifier.

---

### Disk full — memory system stops writing

**What it means:** Memories are small (typically 1–5 KB each), but if your disk is nearly full, writes will fail silently.

**Check disk space:**
```bash
# macOS/Linux
df -h ~

# Windows (PowerShell)
Get-PSDrive C
```

**Clean up old memories:**
```bash
# From within Claude Code, ask Claude to run:
# memory_cleanup — removes stale and low-scoring memories
```

Or manually delete individual memory files from `~/.claude_memory/` and then delete `index.json` to force a rebuild.

---

### `fastmcp` wrong version

**What it means:** The installed `fastmcp` version is incompatible with the server modules.

**Diagnosis:**
```bash
python -c "import fastmcp; print(fastmcp.__version__)"
```

**Fix:**
```bash
pip install --upgrade fastmcp
```
If upgrading breaks something else, pin to the version the installer recommends:
```bash
pip install "fastmcp==X.Y.Z"
```
(The required version will be documented in the installer output if the version check fails.)

---

## Platform-Specific Issues

### Windows: Encoding errors ("charmap codec can't encode character")

**What it means:** The Windows legacy console (cmd.exe) uses a restricted character encoding (usually CP1252) that cannot represent some Unicode characters in output.

**Fix — set encoding before running:**
```cmd
set PYTHONIOENCODING=utf-8
python install.py --full
```

**Better fix — use Windows Terminal:**
Windows Terminal (available from the Microsoft Store) uses UTF-8 by default. All Claude_Meister output renders correctly there.

**Permanent fix — add to your environment:**
1. Open System Properties → Advanced → Environment Variables.
2. Add a new System variable: `PYTHONIOENCODING` = `utf-8`.
3. Open a new terminal — this will be the default going forward.

---

### Windows: Path length errors ("The system cannot find the path specified" or "Filename too long")

**What it means:** Windows limits paths to 260 characters by default. If you cloned the repo deep inside a nested directory, generated paths can exceed this limit.

**Fix Option A — move the repo closer to root:**
```cmd
move claude-meister C:\claude-meister
```
Then re-run the installer from `C:/claude-meister/`.

**Fix Option B — enable long path support:**
1. Open Group Policy Editor: `Win + R` → `gpedit.msc`
2. Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
3. Enable "Enable Win32 long paths"
4. Restart your computer.

Or via PowerShell (Administrator):
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

---

### Windows: Scripts blocked by execution policy (PowerShell)

**What it means:** PowerShell's execution policy prevents running Python scripts directly in some configurations.

**Fix:** Run from Command Prompt instead of PowerShell, or explicitly invoke Python:
```bash
python install.py --full
```
(not `./install.py`)

---

### WSL: MCP server not appearing in Claude Code

**What it means:** You registered the memory server from inside WSL, but Claude Code is running on the Windows side (or vice versa). MCP registrations do not cross the WSL/Windows boundary.

**Rule:** The memory server must be registered in the same environment where Claude Code runs.

**If your Claude Code runs on Windows:**
- Install and register from a Windows terminal (not WSL).
- The paths in `runtime_config.json` should use Windows paths (`C:/Users/...`).

**If your Claude Code runs inside WSL:**
- Install and register from inside WSL.
- The paths should use Linux paths (`/home/yourname/...`).

**Diagnosis:** Run `claude mcp list` from inside WSL and from a Windows terminal. The registrations are separate; check both.

---

### WSL: Path resolution mismatch

**What it means:** Windows paths (like `C:/Users/yourname`) are not valid inside WSL and will cause `FileNotFoundError`.

**Fix:** When running inside WSL, use Linux-style paths in `runtime_config.json`:
```json
{
  "runtime_path": "/home/yourname/.claude_runtime",
  "memory_root": "/home/yourname/.claude_memory"
}
```
The installer detects WSL automatically and uses Linux paths. If you edited the config manually with Windows paths, revert to Linux paths.

---

### macOS: "Cannot be opened because the developer cannot be verified" (Gatekeeper)

**What it means:** macOS Gatekeeper is blocking the script because it was downloaded from the internet and the developer is not notarized with Apple.

**Fix Option A — remove the quarantine attribute:**
```bash
xattr -d com.apple.quarantine install.py
```

**Fix Option B — right-click bypass:**
1. In Finder, right-click `install.py`.
2. Choose "Open".
3. In the dialog that appears, click "Open" again.

**Fix Option C — allow all scripts from the directory:**
```bash
xattr -dr com.apple.quarantine /path/to/claude-meister/
```

---

### macOS: System Python vs Homebrew Python

**What it means:** macOS ships with Python 3, but it may be an older version (e.g., 3.9 from Xcode command line tools). If you installed a newer Python via Homebrew, the two can conflict.

**Check which Python has the required packages:**
```bash
python3 -c "import mcp; import fastmcp; print('OK')"
/opt/homebrew/bin/python3 -c "import mcp; import fastmcp; print('OK')"
```

**Fix:** Use the explicit path to the Python that has the packages:
```bash
/opt/homebrew/bin/python3 install.py --full
```

Or install the packages into the system Python:
```bash
python3 -m pip install mcp fastmcp
```

---

### macOS: `mcp` or `fastmcp` install fails with permission error

**What it means:** The system Python's site-packages directory is not writable without sudo.

**Fix — install with user flag (preferred):**
```bash
pip3 install --user mcp fastmcp
```

This installs into `~/Library/Python/X.Y/lib/python/site-packages`, which is user-writable.

---

### Linux: Locale errors ("locale.Error: unsupported locale setting")

**What it means:** Your Linux environment does not have the expected locale set.

**Fix:**
```bash
export PYTHONIOENCODING=utf-8
export LC_ALL=C.UTF-8
python install.py --full
```

**Permanent fix:** Add these exports to your `~/.bashrc` or `~/.zshrc`.

---

### Linux: Case-sensitive filesystem causes file not found

**What it means:** Linux filesystems are case-sensitive. If any path token resolves to a differently-cased path than expected, the file will not be found.

**Example:** The config has `Runtime_Config.json` but the file is `runtime_config.json`.

**Fix:** All Claude_Meister filenames are lowercase. If you renamed any files, rename them back to all lowercase. The installer enforces lowercase names on copy.

---

### All Platforms: Unicode in home directory path

**What it means:** Your username contains non-ASCII characters (e.g., `C:/Users/José/`). This can cause encoding issues in some terminals and subprocess calls.

**Behavior:** The installer uses `Path.home()` throughout, which handles Unicode paths correctly. If you see encoding-related errors, the issue is likely in your terminal's encoding, not in Claude_Meister.

**Fix:** See "Windows: Encoding errors" above. Set `PYTHONIOENCODING=utf-8` before running.

---

## Nuclear Option

If nothing works and you want a completely clean slate:

### Step 1: Uninstall via the installer (if it still runs)

```bash
python install.py --uninstall
```

This is the safest path — it removes the CLAUDE.md block cleanly and unregisters the MCP server.

### Step 2: Manual removal (if the installer won't run)

**macOS/Linux:**
```bash
# Remove runtime engine
rm -rf ~/.claude_runtime

# Remove memory server code (NOT memory data)
rm -rf ~/.claude_memory/server

# If you also want to delete stored memories:
rm -rf ~/.claude_memory
```

**Windows (PowerShell):**
```powershell
# Remove runtime engine
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude_runtime"

# Remove memory server code only
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude_memory\server"

# If you also want to delete stored memories:
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude_memory"
```

### Step 3: Remove the CLAUDE.md block manually

Open `~/.claude/CLAUDE.md` in any text editor and delete everything between (and including) the marker lines:

```
<!-- RUNTIME:START -->
... everything here ...
<!-- RUNTIME:END -->
```

Save the file. Your content outside those markers is untouched.

### Step 4: Unregister the MCP server

```bash
claude mcp remove memory
```

Verify it is gone:
```bash
claude mcp list
```

### Step 5: Verify Claude Code is back to normal

Restart Claude Code and open a project. It should behave as if Claude_Meister was never installed.

### Step 6: Reinstall from scratch

```bash
git clone https://github.com/Mintsolester/claude-meister.git
cd claude-meister
python install.py --full
```

---

## Getting More Help

If you have followed these steps and the issue persists:

1. Run `python install.py --verify` and copy the full output.
2. Run `python --version` and `claude --version`.
3. Copy the full error message (text, not screenshot).
4. Open an issue at the GitHub repo with all three pieces of information.

Include what you expected to happen and what actually happened. The more specific, the faster the fix.
