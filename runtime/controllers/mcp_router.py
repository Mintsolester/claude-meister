"""Recommend which memory source to use based on what's available locally.

Usage:
    python mcp_router.py --check --working-dir "A:/my-project" --query "test"
"""

import argparse
import json
import os
import time
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"memory_root": str(Path.home() / ".claude_memory")}


def detect_repo_name(working_dir: str) -> str:
    """Detect repo name from .git/config."""
    git_config = Path(working_dir) / ".git" / "config"
    if git_config.exists():
        try:
            import configparser
            import re
            cfg = configparser.ConfigParser()
            cfg.read(str(git_config))
            for section in cfg.sections():
                if section.startswith('remote "'):
                    url = cfg.get(section, "url", fallback="")
                    if url:
                        match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
                        if match:
                            return match.group(1).replace("/", "_")
        except Exception:
            pass
    return os.path.basename(os.path.abspath(working_dir))


def check_local_cache(working_dir: str) -> dict:
    """Check if .repo_memory/hot.md exists and is fresh."""
    hot_md = Path(working_dir) / ".repo_memory" / "hot.md"
    if not hot_md.exists():
        return {"available": False}

    mod_time = hot_md.stat().st_mtime
    age_hours = (time.time() - mod_time) / 3600
    content_size = hot_md.stat().st_size

    return {
        "available": True,
        "age_hours": round(age_hours, 1),
        "fresh": age_hours < 24,
        "has_content": content_size > 50,
        "path": str(hot_md),
    }


def check_global_index(memory_root: str, repo_name: str) -> dict:
    """Check if global index has entries for this repo."""
    index_path = Path(memory_root) / "index.json"
    if not index_path.exists():
        return {"available": False, "entry_count": 0}

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        repo_entries = [e for e in index if e.get("repo", "") == repo_name]
        return {
            "available": len(repo_entries) > 0,
            "entry_count": len(repo_entries),
            "total_entries": len(index),
        }
    except (json.JSONDecodeError, OSError):
        return {"available": False, "entry_count": 0}


def recommend(args):
    config = load_config()
    working_dir = args.working_dir or os.getcwd()
    repo_name = detect_repo_name(working_dir)
    query = args.query or ""

    local = check_local_cache(working_dir)
    global_idx = check_global_index(config["memory_root"], repo_name)

    runtime_path = config.get("runtime_path", str(Path.home() / ".claude_runtime"))
    mc_path = f"{runtime_path}/controllers/memory_controller.py"

    # Decision logic
    if local["available"] and local.get("fresh") and local.get("has_content"):
        recommendation = {
            "source": "local_cache",
            "reason": f"Local hot.md is fresh ({local['age_hours']}h old) and has content",
            "command": f"Read {local['path']}",
            "fallback": f'python "{mc_path}" --query "{query}" --repo "{repo_name}"' if global_idx["available"] else None,
        }
    elif global_idx["available"]:
        recommendation = {
            "source": "memory_controller",
            "reason": f"Global index has {global_idx['entry_count']} entries for repo '{repo_name}'",
            "command": f'python "{mc_path}" --query "{query}" --repo "{repo_name}"',
            "fallback": None,
        }
    elif global_idx.get("total_entries", 0) > 0:
        recommendation = {
            "source": "memory_controller",
            "reason": f"No entries for '{repo_name}' but global index has {global_idx['total_entries']} entries from other repos",
            "command": f'python "{mc_path}" --query "{query}" --cross-repo --max-tokens 300',
            "fallback": None,
        }
    else:
        recommendation = {
            "source": "mcp",
            "reason": "No local cache or global index entries found. Use MCP memory_retrieve for full search.",
            "command": "Call memory_retrieve MCP tool directly",
            "fallback": None,
        }

    recommendation["repo"] = repo_name
    recommendation["local_cache"] = local
    recommendation["global_index"] = global_idx
    print(json.dumps(recommendation, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Recommend memory source")
    parser.add_argument("--check", action="store_true", help="Run recommendation check")
    parser.add_argument("--working-dir", type=str, default="", help="Working directory to check")
    parser.add_argument("--query", type=str, default="", help="Task query for context")
    args = parser.parse_args()

    if args.check:
        recommend(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
