"""Install, update, and remove the runtime engine (~/.claude_runtime/)."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from installer.paths import apply_substitutions


# Files that contain {{PLACEHOLDER}} tokens and need substitution
TEMPLATED_FILES = {
    "core/context_router.md",
    "hooks/runtime_bootstrap.md",
}

# Files that are generated from templates/ rather than copied from runtime/
TEMPLATE_GENERATED = {
    "configs/runtime_config.json": "templates/runtime_config.json",
}

# Directories the installer creates (not in source)
GENERATED_DIRS = ["logs", "integrations"]

# Files the installer generates fresh
GENERATED_FILES = {
    "logs/runtime_usage.json": "[]",
}

# Directories/files preserved during --update
PRESERVE_ON_UPDATE = {
    "logs/runtime_usage.json",
    "logs/runtime_usage.archive.json",
    "configs/runtime_config.json",
}


def install_runtime(paths: dict, substitutions: dict) -> dict:
    """Copy runtime/ to ~/.claude_runtime/, resolving all template tokens.

    Args:
        paths: from get_paths()
        substitutions: from build_substitutions()

    Returns:
        dict with 'status', 'files_copied', 'message'
    """
    repo_root = Path(paths["repo_root"])
    source_dir = repo_root / "runtime"
    target_dir = Path(paths["runtime_path"])

    if not source_dir.exists():
        return {"status": "error", "message": f"Source directory not found: {source_dir}"}

    files_copied = 0

    try:
        # Create target directory structure
        target_dir.mkdir(parents=True, exist_ok=True)
        for gen_dir in GENERATED_DIRS:
            (target_dir / gen_dir).mkdir(parents=True, exist_ok=True)

        # Copy all files from runtime/ source
        for source_file in source_dir.rglob("*"):
            if source_file.is_dir():
                continue
            if "__pycache__" in str(source_file):
                continue

            relative = source_file.relative_to(source_dir)
            target_file = target_dir / relative
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Read content
            if source_file.suffix in (".py", ".md", ".json", ".txt"):
                content = source_file.read_text(encoding="utf-8")
                # Apply substitutions if this file needs templating
                if str(relative).replace("\\", "/") in TEMPLATED_FILES:
                    content = apply_substitutions(content, substitutions)
                target_file.write_text(content, encoding="utf-8")
            else:
                shutil.copy2(str(source_file), str(target_file))

            files_copied += 1

        # Generate files from templates
        for target_rel, template_rel in TEMPLATE_GENERATED.items():
            template_path = repo_root / template_rel
            if template_path.exists():
                content = template_path.read_text(encoding="utf-8")
                content = apply_substitutions(content, substitutions)
                target_path = target_dir / target_rel
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                files_copied += 1

        # Generate fresh files
        for file_rel, default_content in GENERATED_FILES.items():
            file_path = target_dir / file_rel
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(default_content, encoding="utf-8")
                files_copied += 1

        # Build tool_index.json so tool_loader can use index-first lookup
        _build_tool_index(target_dir)

        return {
            "status": "success",
            "files_copied": files_copied,
            "target": str(target_dir),
            "message": f"Runtime installed to {target_dir} ({files_copied} files)",
        }

    except PermissionError as e:
        return {"status": "error", "message": f"Permission denied: {e}. Check directory ownership."}
    except Exception as e:
        return {"status": "error", "message": f"Installation failed: {e}"}


def update_runtime(paths: dict, substitutions: dict) -> dict:
    """Re-install runtime, preserving user data (logs, modified config).

    Returns:
        dict with 'status', 'preserved', 'overwritten', 'message'
    """
    target_dir = Path(paths["runtime_path"])
    preserved = []
    backups = {}

    # Backup files to preserve
    for rel_path in PRESERVE_ON_UPDATE:
        file_path = target_dir / rel_path
        if file_path.exists():
            backups[rel_path] = file_path.read_text(encoding="utf-8")
            preserved.append(rel_path)

    # Re-install
    result = install_runtime(paths, substitutions)

    # Restore preserved files
    if result["status"] == "success":
        for rel_path, content in backups.items():
            file_path = target_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        # Rebuild the tool index now that the user's tools_dirs config is back in place.
        # (install_runtime also runs it, but against the freshly-templated empty config.)
        _build_tool_index(target_dir)

        result["preserved"] = preserved
        result["message"] = (
            f"Runtime updated. {result['files_copied']} files refreshed. "
            f"{len(preserved)} files preserved: {', '.join(preserved)}"
        )

    return result


def remove_runtime(paths: dict, confirm: bool = True) -> dict:
    """Remove ~/.claude_runtime/ entirely.

    Args:
        confirm: if True, print warning and require user input
    """
    target_dir = Path(paths["runtime_path"])

    if not target_dir.exists():
        return {"status": "skipped", "message": "Runtime directory does not exist."}

    if confirm:
        print(f"\n  This will delete: {target_dir}")
        print(f"  Including logs and any custom files.")
        response = input("  Proceed? [y/N]: ").strip().lower()
        if response != "y":
            return {"status": "cancelled", "message": "Removal cancelled by user."}

    try:
        shutil.rmtree(str(target_dir))
        return {"status": "success", "message": f"Removed {target_dir}"}
    except PermissionError as e:
        return {"status": "error", "message": f"Permission denied: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Removal failed: {e}"}


def _build_tool_index(target_dir: Path) -> None:
    """Best-effort: run build_tool_index.py after install. Never hard-fail the install."""
    builder = target_dir / "controllers" / "build_tool_index.py"
    if not builder.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(builder)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        pass


def check_existing_installation(paths: dict) -> dict:
    """Check if a runtime installation already exists and its state."""
    target_dir = Path(paths["runtime_path"])

    if not target_dir.exists():
        return {"exists": False}

    config_path = target_dir / "configs" / "runtime_config.json"
    has_config = config_path.exists()

    if has_config:
        try:
            json.loads(config_path.read_text(encoding="utf-8"))
            config_valid = True
        except (json.JSONDecodeError, Exception):
            config_valid = False
    else:
        config_valid = False

    return {
        "exists": True,
        "complete": has_config and config_valid,
        "has_config": has_config,
        "config_valid": config_valid,
        "path": str(target_dir),
    }
