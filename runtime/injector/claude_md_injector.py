"""Safely inject runtime reference into per-repo CLAUDE.md files.

Backs up before modifying. Idempotent — won't duplicate if already injected.
Never overwrites user content — prepends a runtime block at the top.

Usage:
    python claude_md_injector.py --repo-dir "A:/my-project"
    python claude_md_injector.py --repo-dir "A:/my-project" --dry-run
    python claude_md_injector.py --repo-dir "A:/my-project" --remove
    python claude_md_injector.py --scan-and-inject "A:/"
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_PATH = Path.home() / ".claude_runtime"

INJECTION_MARKER_START = "<!-- RUNTIME:START -->"
INJECTION_MARKER_END = "<!-- RUNTIME:END -->"

INJECTION_BLOCK = f"""{INJECTION_MARKER_START}
# Global Runtime Engine

This repo inherits the global Claude runtime. For Moderate+ tasks, the runtime is loaded automatically via the global CLAUDE.md at `~/.claude/CLAUDE.md`.

**Runtime location:** `{RUNTIME_PATH}`

**What this provides:**
- Context routing — loads only what's needed per task complexity
- Mode selection — LIGHT / STANDARD / DEEP based on task classification
- Tool discovery — `python "{RUNTIME_PATH}/controllers/tool_loader.py" --query "keyword"`
- Memory access — `python "{RUNTIME_PATH}/controllers/memory_controller.py" --query "topic"`
- Usage logging — `python "{RUNTIME_PATH}/controllers/usage_logger.py" --mode MODE --task-summary "..."`

**Quick start for this task:**
```bash
python "{RUNTIME_PATH}/injector/runtime_loader.py" --task "DESCRIBE_TASK" --complexity moderate
```
{INJECTION_MARKER_END}
"""


def load_injection_rules() -> dict:
    rules_path = RUNTIME_PATH / "configs" / "injection_rules.json"
    if rules_path.exists():
        return json.loads(rules_path.read_text(encoding="utf-8"))
    return {
        "prepend_not_append": True,
        "backup_before_modify": True,
        "skip_if_already_injected": True,
        "create_if_missing": True,
        "excluded_dirs": [".git", "node_modules", ".venv", "__pycache__", ".tmp"],
    }


def is_already_injected(content: str) -> bool:
    return INJECTION_MARKER_START in content


def backup_file(file_path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / f".CLAUDE.md.backup.{timestamp}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def inject_into_file(file_path: Path, dry_run: bool = False) -> dict:
    """Inject runtime block into a CLAUDE.md file."""
    rules = load_injection_rules()
    result = {"path": str(file_path), "action": "none", "backup": None}

    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")

        # Check if already injected
        if rules["skip_if_already_injected"] and is_already_injected(content):
            result["action"] = "skipped_already_injected"
            return result

        if dry_run:
            result["action"] = "would_inject"
            return result

        # Backup
        if rules["backup_before_modify"]:
            backup = backup_file(file_path)
            result["backup"] = str(backup)

        # Inject
        if rules["prepend_not_append"]:
            new_content = INJECTION_BLOCK + "\n\n" + content
        else:
            new_content = content + "\n\n" + INJECTION_BLOCK

        file_path.write_text(new_content, encoding="utf-8")
        result["action"] = "injected"

    else:
        if not rules["create_if_missing"]:
            result["action"] = "skipped_no_file"
            return result

        if dry_run:
            result["action"] = "would_create"
            return result

        file_path.write_text(INJECTION_BLOCK + "\n", encoding="utf-8")
        result["action"] = "created"

    return result


def remove_injection(file_path: Path, dry_run: bool = False) -> dict:
    """Remove the runtime injection block from a CLAUDE.md file."""
    result = {"path": str(file_path), "action": "none"}

    if not file_path.exists():
        result["action"] = "no_file"
        return result

    content = file_path.read_text(encoding="utf-8")
    if not is_already_injected(content):
        result["action"] = "not_injected"
        return result

    if dry_run:
        result["action"] = "would_remove"
        return result

    # Backup before removal
    backup = backup_file(file_path)
    result["backup"] = str(backup)

    # Remove the injection block
    start_idx = content.find(INJECTION_MARKER_START)
    end_idx = content.find(INJECTION_MARKER_END)
    if start_idx != -1 and end_idx != -1:
        end_idx += len(INJECTION_MARKER_END)
        # Remove trailing newlines after the block
        while end_idx < len(content) and content[end_idx] == "\n":
            end_idx += 1
        new_content = content[:start_idx] + content[end_idx:]
        new_content = new_content.strip()

        if new_content:
            file_path.write_text(new_content + "\n", encoding="utf-8")
            result["action"] = "removed"
        else:
            # File would be empty after removal — delete it
            file_path.unlink()
            result["action"] = "removed_and_deleted_empty_file"

    return result


def find_repos(root_dir: str) -> list[Path]:
    """Find all git repos under a root directory."""
    rules = load_injection_rules()
    excluded = set(rules.get("excluded_dirs", []))
    repos = []

    root = Path(root_dir)
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in excluded]

        if ".git" in os.listdir(dirpath):
            repos.append(Path(dirpath))
            # Don't descend into git repos (they won't have nested repos normally)
            dirnames.clear()

    return repos


def scan_and_inject(root_dir: str, dry_run: bool = False) -> list[dict]:
    """Scan for repos and inject runtime into each."""
    repos = find_repos(root_dir)
    results = []

    for repo_path in repos:
        claude_md = repo_path / "CLAUDE.md"
        result = inject_into_file(claude_md, dry_run=dry_run)
        result["repo"] = str(repo_path)
        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Inject runtime reference into repo CLAUDE.md files")
    parser.add_argument("--repo-dir", type=str, help="Path to a specific repo")
    parser.add_argument("--scan-and-inject", type=str, help="Root dir to scan for repos and inject all")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--remove", action="store_true", help="Remove injection from CLAUDE.md")
    parser.add_argument("--check", action="store_true", help="Check if a repo has the injection")
    args = parser.parse_args()

    if args.scan_and_inject:
        results = scan_and_inject(args.scan_and_inject, dry_run=args.dry_run)
        print(json.dumps({"repos_found": len(results), "results": results}, indent=2))

    elif args.repo_dir:
        claude_md = Path(args.repo_dir) / "CLAUDE.md"

        if args.check:
            exists = claude_md.exists()
            injected = False
            if exists:
                injected = is_already_injected(claude_md.read_text(encoding="utf-8"))
            print(json.dumps({"path": str(claude_md), "exists": exists, "injected": injected}))

        elif args.remove:
            result = remove_injection(claude_md, dry_run=args.dry_run)
            print(json.dumps(result, indent=2))

        else:
            result = inject_into_file(claude_md, dry_run=args.dry_run)
            print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
