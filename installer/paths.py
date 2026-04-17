"""OS detection, path resolution, prerequisite checking, and template substitution.

All paths are normalized to forward slashes — Claude Code uses forward slashes
even on Windows.
"""

import io
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def detect_os() -> str:
    """Return 'Windows', 'macOS', or 'Linux'."""
    system = platform.system()
    if system == "Darwin":
        return "macOS"
    if system == "Windows":
        # Check for WSL
        try:
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return "Linux"  # WSL acts as Linux
        except (FileNotFoundError, PermissionError):
            pass
        return "Windows"
    return "Linux"


def get_home() -> str:
    """Return user's home directory with forward slashes.

    On Windows, checks for OneDrive redirection and warns if detected.
    """
    home = str(Path.home())
    # Normalize to forward slashes
    home = home.replace("\\", "/")

    # Check for OneDrive redirection on Windows
    if detect_os() == "Windows" and "OneDrive" in home:
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile and "OneDrive" not in userprofile:
            print(f"  Warning: Home directory appears to be OneDrive-redirected.")
            print(f"  Detected: {home}")
            print(f"  USERPROFILE: {userprofile}")
            print(f"  Using USERPROFILE instead to avoid sync issues.")
            home = userprofile.replace("\\", "/")

    return home


def get_paths() -> dict:
    """Return dict of all resolved installation paths."""
    home = get_home()
    return {
        "home": home,
        "runtime_path": f"{home}/.claude_runtime",
        "memory_root": f"{home}/.claude_memory",
        "claude_dir": f"{home}/.claude",
        "wiki_path": f"{home}/.claude_wiki",
        "repo_root": str(Path(__file__).parent.parent).replace("\\", "/"),
    }


def build_substitutions(paths: dict) -> dict:
    """Build the {{TOKEN}} -> resolved_value mapping."""
    return {
        "{{HOME}}": paths["home"],
        "{{RUNTIME_PATH}}": paths["runtime_path"],
        "{{MEMORY_ROOT}}": paths["memory_root"],
        "{{CLAUDE_DIR}}": paths["claude_dir"],
        "{{WIKI_PATH}}": paths["wiki_path"],
    }


def apply_substitutions(content: str, substitutions: dict) -> str:
    """Replace all {{TOKEN}} placeholders in content with resolved values."""
    for token, value in substitutions.items():
        content = content.replace(token, value)
    return content


def check_prerequisites(install_mode: str = "full") -> dict:
    """Check system prerequisites. Returns dict with status and issues.

    Args:
        install_mode: 'full', 'runtime-only', 'memory-only', 'wiki-only'
    """
    issues = []
    warnings = []

    # Python version
    if sys.version_info < (3, 8):
        issues.append(
            f"Python 3.8+ required. You have {sys.version_info.major}.{sys.version_info.minor}. "
            f"Download from https://python.org"
        )

    # Claude Code CLI
    claude_path = shutil.which("claude")
    if not claude_path:
        if install_mode in ("full", "memory-only"):
            issues.append(
                "Claude Code CLI not found. Install it from: https://docs.anthropic.com/en/docs/claude-code\n"
                "  After installing, make sure 'claude' is in your PATH."
            )
        else:
            warnings.append("Claude Code CLI not found. MCP registration will be skipped.")

    # pip packages for memory server
    if install_mode in ("full", "memory-only"):
        for pkg in ("mcp", "fastmcp"):
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import {pkg}"],
                    capture_output=True, timeout=10
                )
                if result.returncode != 0:
                    issues.append(f"Python package '{pkg}' not found. Run: pip install {pkg}")
            except Exception:
                issues.append(f"Could not check for '{pkg}' package. Run: pip install {pkg}")

    # Write permission
    home = Path(get_home())
    if not os.access(str(home), os.W_OK):
        issues.append(f"Cannot write to home directory: {home}. Check directory permissions.")

    # Disk space
    try:
        usage = shutil.disk_usage(str(home))
        free_mb = usage.free / (1024 * 1024)
        if free_mb < 50:
            warnings.append(f"Low disk space: {free_mb:.0f}MB free. Installation needs ~5MB but memories grow over time.")
    except Exception:
        pass

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os": detect_os(),
        "home": get_home(),
        "claude_cli": claude_path is not None,
    }
