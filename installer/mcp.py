"""Register, check, and remove the memory MCP server in Claude Code."""

import shutil
import subprocess
import sys
from pathlib import Path


def register_mcp(paths: dict, python_override: str = "") -> dict:
    """Register the memory MCP server with Claude Code.

    Runs: claude mcp add memory -- <python_abs_path> <memory_root>/server/main.py

    Always uses an absolute interpreter path (sys.executable, an mcp-bearing
    candidate, or python_override) so the registration is not subject to the
    user's PATH at MCP launch time.
    """
    claude_path = shutil.which("claude")
    if not claude_path:
        return {
            "status": "error",
            "message": (
                "Claude Code CLI not found in PATH.\n"
                "Install it from: https://docs.anthropic.com/en/docs/claude-code\n"
                "Then run this installer again, or register manually:\n"
                f"  claude mcp add memory -- python \"{paths['memory_root']}/server/main.py\""
            ),
        }

    expected_script = f"{paths['memory_root']}/server/main.py"

    # Pick the interpreter we want to use
    if python_override:
        python_path = python_override
        # Verify the override actually has mcp
        try:
            proc = subprocess.run(
                [python_path, "-c", "import mcp"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode != 0:
                return {
                    "status": "error",
                    "message": f"--python override {python_path} does not have 'mcp' installed.",
                }
        except Exception as e:
            return {"status": "error", "message": f"--python override unusable: {e}"}
    else:
        python_path = get_python_with_mcp()
        if not python_path:
            return {
                "status": "error",
                "message": (
                    "Could not find a Python installation with the 'mcp' package.\n"
                    "Run: pip install mcp\n"
                    "Then re-run the installer."
                ),
            }

    # Check if 'memory' already registered, and whether it matches what we want
    existing = check_mcp()
    if existing.get("registered"):
        current_cmd = existing.get("path", "")
        current_norm = current_cmd.replace("\\", "/")
        script_matches = expected_script in current_norm
        # Bare-token check: registered command uses bare `python` rather than abs path
        is_bare_python = " python " in f" {current_norm} " or current_norm.endswith(" python")
        interp_matches = python_path.replace("\\", "/") in current_norm

        if script_matches and interp_matches:
            return {"status": "skipped", "message": "Memory MCP server already registered with correct interpreter and path."}

        if script_matches and is_bare_python and not interp_matches:
            # Registered with bare `python` — upgrade to absolute interpreter path
            rm = subprocess.run(["claude", "mcp", "remove", "memory"], capture_output=True, text=True, timeout=15)
            if rm.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Failed to remove stale 'memory' registration: {rm.stderr.strip() or rm.stdout.strip()}",
                }
            # Fall through to re-register below

        elif not script_matches:
            return {
                "status": "conflict",
                "message": (
                    f"An MCP server named 'memory' is already registered with a different script:\n"
                    f"  Current: {current_cmd}\n"
                    f"  Expected: {expected_script}\n"
                    f"  To replace, run:\n"
                    f"    claude mcp remove memory\n"
                    f"    claude mcp add memory -- \"{python_path}\" \"{expected_script}\""
                ),
            }

    cmd = build_mcp_command(paths, python_path)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return {"status": "success", "message": "Memory MCP server registered with Claude Code."}
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return {
                "status": "error",
                "message": (
                    f"claude mcp add failed:\n  {error}\n\n"
                    f"Try manually:\n"
                    f"  claude mcp add memory -- {python_path} \"{paths['memory_root']}/server/main.py\""
                ),
            }
    except FileNotFoundError:
        return {"status": "error", "message": "Claude CLI not found. Ensure it's in your PATH."}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "claude mcp add timed out. Try running manually."}


def check_mcp() -> dict:
    """Check if the memory MCP server is registered."""
    claude_path = shutil.which("claude")
    if not claude_path:
        return {"registered": False, "cli_available": False}

    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout + result.stderr
        # Look for 'memory:' line in output
        for line in output.splitlines():
            if line.strip().startswith("memory:") or "memory:" in line.lower():
                return {"registered": True, "cli_available": True, "path": line.strip()}

        return {"registered": False, "cli_available": True}
    except Exception:
        return {"registered": False, "cli_available": True, "error": "Failed to check MCP status"}


def remove_mcp() -> dict:
    """Unregister the memory MCP server."""
    claude_path = shutil.which("claude")
    if not claude_path:
        return {"status": "skipped", "message": "Claude CLI not found."}

    try:
        result = subprocess.run(
            ["claude", "mcp", "remove", "memory"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return {"status": "success", "message": "Memory MCP server unregistered."}
        else:
            return {"status": "error", "message": f"Failed: {result.stderr.strip()}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}


def get_python_with_mcp() -> str:
    """Find a Python executable that has the mcp package installed."""
    candidates = [sys.executable, "python3", "python"]

    for candidate in candidates:
        try:
            path = shutil.which(candidate) or candidate
            result = subprocess.run(
                [path, "-c", "import mcp; print('ok')"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "ok" in result.stdout:
                return path
        except Exception:
            continue

    return ""


def build_mcp_command(paths: dict, python_path: str = None) -> list:
    """Build the claude mcp add command."""
    if python_path is None:
        python_path = get_python_with_mcp() or sys.executable

    server_path = f"{paths['memory_root']}/server/main.py"
    return ["claude", "mcp", "add", "memory", "--", python_path, server_path]
