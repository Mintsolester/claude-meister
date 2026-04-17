"""Install, update, and remove the memory MCP server (~/.claude_memory/)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def install_memory(paths: dict) -> dict:
    """Copy memory/server/ to ~/.claude_memory/server/, create index.json if missing.

    Args:
        paths: from get_paths()

    Returns:
        dict with 'status', 'files_copied', 'message'
    """
    repo_root = Path(paths["repo_root"])
    source_dir = repo_root / "memory" / "server"
    target_dir = Path(paths["memory_root"])
    server_dir = target_dir / "server"

    if not source_dir.exists():
        return {"status": "error", "message": f"Source directory not found: {source_dir}"}

    files_copied = 0

    try:
        server_dir.mkdir(parents=True, exist_ok=True)

        # Copy server files
        for source_file in source_dir.iterdir():
            if source_file.is_dir() or source_file.name.startswith("__"):
                continue
            target_file = server_dir / source_file.name
            if source_file.suffix == ".py":
                content = source_file.read_text(encoding="utf-8")
                target_file.write_text(content, encoding="utf-8")
            else:
                shutil.copy2(str(source_file), str(target_file))
            files_copied += 1

        # Create index.json if it doesn't exist (never overwrite user data)
        index_path = target_dir / "index.json"
        if not index_path.exists():
            index_path.write_text("[]", encoding="utf-8")

        return {
            "status": "success",
            "files_copied": files_copied,
            "target": str(server_dir),
            "message": f"Memory server installed to {server_dir} ({files_copied} files)",
        }

    except PermissionError as e:
        return {"status": "error", "message": f"Permission denied: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Installation failed: {e}"}


def update_memory(paths: dict) -> dict:
    """Re-install server files, preserving index.json and stored memories."""
    target_dir = Path(paths["memory_root"])

    # Backup index and entries
    index_path = target_dir / "index.json"
    index_backup = None
    if index_path.exists():
        index_backup = index_path.read_text(encoding="utf-8")

    entries_dir = target_dir / "entries"
    entries_backup = {}
    if entries_dir.exists():
        for entry_file in entries_dir.iterdir():
            if entry_file.is_file():
                entries_backup[entry_file.name] = entry_file.read_text(encoding="utf-8")

    # Re-install server
    result = install_memory(paths)

    # Restore preserved data
    if result["status"] == "success":
        if index_backup is not None:
            index_path.write_text(index_backup, encoding="utf-8")
        if entries_backup:
            entries_dir.mkdir(parents=True, exist_ok=True)
            for name, content in entries_backup.items():
                (entries_dir / name).write_text(content, encoding="utf-8")
        result["message"] += " (user data preserved)"

    return result


def remove_memory(paths: dict, confirm: bool = True, keep_data: bool = True) -> dict:
    """Remove memory server files.

    Args:
        confirm: if True, ask user before deleting
        keep_data: if True, preserve index.json and entries/
    """
    target_dir = Path(paths["memory_root"])
    server_dir = target_dir / "server"

    if not target_dir.exists():
        return {"status": "skipped", "message": "Memory directory does not exist."}

    if confirm:
        print(f"\n  This will remove the memory server from: {server_dir}")
        if not keep_data:
            print(f"  WARNING: This will also delete all stored memories!")
        response = input("  Proceed? [y/N]: ").strip().lower()
        if response != "y":
            return {"status": "cancelled", "message": "Removal cancelled by user."}

    try:
        if keep_data:
            # Only remove server/ directory
            if server_dir.exists():
                shutil.rmtree(str(server_dir))
            return {"status": "success", "message": f"Server files removed. Memory data preserved in {target_dir}"}
        else:
            shutil.rmtree(str(target_dir))
            return {"status": "success", "message": f"Removed {target_dir} and all data"}

    except PermissionError as e:
        return {"status": "error", "message": f"Permission denied: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Removal failed: {e}"}


def check_dependencies() -> dict:
    """Check if required pip packages are installed.

    Returns:
        dict mapping package name to {'installed': bool, 'version': str|None}
    """
    result = {}
    for pkg in ("mcp", "fastmcp"):
        try:
            proc = subprocess.run(
                [sys.executable, "-c", f"import {pkg}; print({pkg}.__version__ if hasattr({pkg}, '__version__') else 'unknown')"],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0:
                result[pkg] = {"installed": True, "version": proc.stdout.strip()}
            else:
                result[pkg] = {"installed": False, "version": None}
        except Exception:
            result[pkg] = {"installed": False, "version": None}

    return result
