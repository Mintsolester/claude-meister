"""Append usage records to the runtime log for analysis over time.

Usage:
    python usage_logger.py --mode STANDARD --tools-used "advisor.py,tool_loader.py" --memory-tokens 312 --task-summary "Refactored auth"
    python usage_logger.py --stats
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"runtime_path": str(Path.home() / ".claude_runtime")}


def get_log_path():
    config = load_config()
    return Path(config["runtime_path"]) / "logs" / "runtime_usage.json"


def detect_repo():
    """Detect repo name from .git/config in cwd."""
    git_config = Path.cwd() / ".git" / "config"
    if git_config.exists():
        try:
            import configparser
            cfg = configparser.ConfigParser()
            cfg.read(str(git_config))
            for section in cfg.sections():
                if section.startswith('remote "'):
                    url = cfg.get(section, "url", fallback="")
                    if url:
                        import re
                        match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
                        if match:
                            return match.group(1).replace("/", "_")
        except Exception:
            pass
    return os.path.basename(os.getcwd())


def load_log(log_path: Path) -> list:
    if log_path.exists():
        try:
            return json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_log(log_path: Path, entries: list):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def rotate_if_needed(log_path: Path, entries: list, max_entries=1000):
    """Archive oldest entries if log exceeds max size."""
    if len(entries) <= max_entries:
        return entries
    archive_path = log_path.parent / "runtime_usage.archive.json"
    archived = load_log(archive_path)
    cutoff = len(entries) - max_entries // 2
    archived.extend(entries[:cutoff])
    save_log(archive_path, archived)
    return entries[cutoff:]


def log_usage(args):
    log_path = get_log_path()
    entries = load_log(log_path)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode or "UNKNOWN",
        "tools_used": [t.strip() for t in args.tools_used.split(",") if t.strip()] if args.tools_used else [],
        "memory_tokens": args.memory_tokens or 0,
        "task_summary": args.task_summary or "",
        "repo": detect_repo(),
    }

    entries.append(record)
    entries = rotate_if_needed(log_path, entries)
    save_log(log_path, entries)
    print(json.dumps({"status": "logged", "record": record}, indent=2))


def show_stats():
    log_path = get_log_path()
    entries = load_log(log_path)

    if not entries:
        print(json.dumps({"total_entries": 0, "message": "No usage data yet"}))
        return

    mode_counts = {}
    tool_counts = {}
    total_memory = 0

    for e in entries:
        mode = e.get("mode", "UNKNOWN")
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        for tool in e.get("tools_used", []):
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        total_memory += e.get("memory_tokens", 0)

    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    stats = {
        "total_entries": len(entries),
        "mode_distribution": mode_counts,
        "top_tools": dict(top_tools),
        "avg_memory_tokens": round(total_memory / len(entries), 1),
        "date_range": {
            "first": entries[0].get("timestamp", ""),
            "last": entries[-1].get("timestamp", ""),
        },
    }
    print(json.dumps(stats, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Log runtime usage")
    parser.add_argument("--mode", type=str, help="LIGHT, STANDARD, or DEEP")
    parser.add_argument("--tools-used", type=str, default="", help="Comma-separated tool names")
    parser.add_argument("--memory-tokens", type=int, default=0, help="Tokens used for memory retrieval")
    parser.add_argument("--task-summary", type=str, default="", help="Brief task description")
    parser.add_argument("--stats", action="store_true", help="Show usage statistics")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        log_usage(args)


if __name__ == "__main__":
    main()
