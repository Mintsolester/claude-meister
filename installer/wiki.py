"""Install, update, and remove the shipped wiki (~/.claude_wiki/)."""

import json
import shutil
from pathlib import Path


def install_wiki(paths: dict) -> dict:
    """Copy wiki/ to the wiki install location and update runtime config.

    Args:
        paths: from get_paths()

    Returns:
        dict with 'status', 'files_copied', 'message'
    """
    repo_root = Path(paths["repo_root"])
    source_dir = repo_root / "wiki"
    target_dir = Path(paths["wiki_path"])

    if not source_dir.exists():
        return {"status": "error", "message": f"Wiki source not found: {source_dir}"}

    files_copied = 0

    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy all files and directories
        for item in source_dir.rglob("*"):
            if item.is_dir():
                continue
            if "__pycache__" in str(item):
                continue

            relative = item.relative_to(source_dir)
            target_file = target_dir / relative
            target_file.parent.mkdir(parents=True, exist_ok=True)

            content = item.read_text(encoding="utf-8")
            target_file.write_text(content, encoding="utf-8")
            files_copied += 1

        # Create empty starter directories
        for subdir in ["comparisons", "guides", "queries", "sources"]:
            (target_dir / subdir).mkdir(exist_ok=True)

        # Update runtime_config.json with wiki_path
        _update_config_wiki_path(paths)

        return {
            "status": "success",
            "files_copied": files_copied,
            "target": str(target_dir),
            "message": f"Wiki installed to {target_dir} ({files_copied} files)",
        }

    except PermissionError as e:
        return {"status": "error", "message": f"Permission denied: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Installation failed: {e}"}


def update_wiki(paths: dict) -> dict:
    """Re-install wiki files. Preserves any user-added files in the wiki directory."""
    target_dir = Path(paths["wiki_path"])

    # Track user-added files (not in source)
    repo_root = Path(paths["repo_root"])
    source_dir = repo_root / "wiki"
    source_files = set()
    if source_dir.exists():
        for item in source_dir.rglob("*"):
            if item.is_file():
                source_files.add(str(item.relative_to(source_dir)))

    user_files = {}
    if target_dir.exists():
        for item in target_dir.rglob("*"):
            if item.is_file():
                rel = str(item.relative_to(target_dir))
                if rel not in source_files:
                    user_files[rel] = item.read_text(encoding="utf-8")

    # Re-install
    result = install_wiki(paths)

    # Restore user files
    if result["status"] == "success" and user_files:
        for rel, content in user_files.items():
            file_path = target_dir / rel
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        result["message"] += f" ({len(user_files)} user files preserved)"

    return result


def remove_wiki(paths: dict, confirm: bool = True) -> dict:
    """Remove the installed wiki."""
    target_dir = Path(paths["wiki_path"])

    if not target_dir.exists():
        return {"status": "skipped", "message": "Wiki directory does not exist."}

    if confirm:
        print(f"\n  This will delete: {target_dir}")
        response = input("  Proceed? [y/N]: ").strip().lower()
        if response != "y":
            return {"status": "cancelled", "message": "Removal cancelled by user."}

    try:
        shutil.rmtree(str(target_dir))
        # Clear wiki_path in config
        _update_config_wiki_path(paths, clear=True)
        return {"status": "success", "message": f"Removed {target_dir}"}
    except Exception as e:
        return {"status": "error", "message": f"Removal failed: {e}"}


def _update_config_wiki_path(paths: dict, clear: bool = False):
    """Set or clear wiki_path in runtime_config.json."""
    config_path = Path(paths["runtime_path"]) / "configs" / "runtime_config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["wiki_path"] = "" if clear else paths["wiki_path"]
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, Exception):
            pass  # Config corrupted — runtime handles this gracefully
