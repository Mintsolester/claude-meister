"""Aggregate runtime_usage.json into human-readable and JSON reports.

Usage:
    python usage_report.py                   # Text table over all-time log
    python usage_report.py --days 7          # Restrict to last 7 days
    python usage_report.py --json            # JSON output instead of text
    python usage_report.py --log-path PATH   # Read a specific log file
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"runtime_path": str(Path.home() / ".claude_runtime")}


def default_log_path() -> Path:
    return Path(_load_config()["runtime_path"]) / "logs" / "runtime_usage.json"


def load_entries(log_path: Path) -> list:
    if not log_path.exists():
        return []
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def filter_by_window(entries: list, days: int | None) -> list:
    if not days:
        return entries
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = []
    for e in entries:
        ts = e.get("timestamp", "")
        try:
            when = datetime.fromisoformat(ts)
            if when >= cutoff:
                kept.append(e)
        except ValueError:
            # Malformed timestamp — include to be permissive; skip would lose signal
            kept.append(e)
    return kept


def aggregate(entries: list) -> dict:
    if not entries:
        return {
            "total_tasks": 0,
            "mode_breakdown": {},
            "avg_tokens_per_mode": {},
            "top_tools": {},
            "memory_hit_rate": 0.0,
            "success_rate": None,
            "date_range": {"first": None, "last": None},
        }

    mode_counts = defaultdict(int)
    mode_tokens = defaultdict(int)
    tool_counts = defaultdict(int)
    with_memory = 0
    successes = 0
    finalized = 0

    for e in entries:
        mode = e.get("mode", "UNKNOWN")
        mode_counts[mode] += 1
        tokens = e.get("memory_tokens", 0) or 0
        mode_tokens[mode] += tokens
        if tokens > 0:
            with_memory += 1
        for tool in e.get("tools_used", []) or []:
            tool_counts[tool] += 1
        # success field is set by Phase 2.3 --finalize; ignore null entries
        success = e.get("success")
        if success is True:
            successes += 1
            finalized += 1
        elif success is False:
            finalized += 1

    avg_tokens_per_mode = {
        mode: round(mode_tokens[mode] / mode_counts[mode], 1)
        for mode in mode_counts
    }
    top_tools = dict(
        sorted(tool_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    )

    return {
        "total_tasks": len(entries),
        "mode_breakdown": dict(mode_counts),
        "avg_tokens_per_mode": avg_tokens_per_mode,
        "top_tools": top_tools,
        "memory_hit_rate": round(with_memory / len(entries), 3),
        "success_rate": round(successes / finalized, 3) if finalized else None,
        "date_range": {
            "first": entries[0].get("timestamp"),
            "last": entries[-1].get("timestamp"),
        },
    }


def format_text(stats: dict, window_days: int | None) -> str:
    if stats["total_tasks"] == 0:
        return "No usage data yet.\n"

    lines = []
    header = f"Runtime Usage Report (last {window_days} days)" if window_days else "Runtime Usage Report (all time)"
    lines.append(header)
    lines.append("=" * len(header))
    lines.append(f"Total tasks:       {stats['total_tasks']}")
    lines.append(f"Memory hit rate:   {stats['memory_hit_rate'] * 100:.1f}%")
    if stats["success_rate"] is not None:
        lines.append(f"Success rate:      {stats['success_rate'] * 100:.1f}% (of finalized tasks)")
    else:
        lines.append(f"Success rate:      n/a (no finalized outcomes yet)")
    lines.append(f"Date range:        {stats['date_range']['first']} -> {stats['date_range']['last']}")
    lines.append("")

    lines.append("Mode breakdown:")
    for mode, count in sorted(stats["mode_breakdown"].items(), key=lambda kv: kv[1], reverse=True):
        avg = stats["avg_tokens_per_mode"].get(mode, 0)
        lines.append(f"  {mode:<10} {count:>5} tasks   avg {avg:>6.1f} memory tokens/task")
    lines.append("")

    if stats["top_tools"]:
        lines.append("Top tools:")
        for tool, count in stats["top_tools"].items():
            lines.append(f"  {tool:<30} {count:>5}")
    else:
        lines.append("Top tools: (none recorded)")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Aggregate runtime usage log into a report")
    parser.add_argument("--days", type=int, default=None, help="Restrict to last N days")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--log-path", type=str, default=None, help="Override the log file path")
    args = parser.parse_args()

    log_path = Path(args.log_path) if args.log_path else default_log_path()
    entries = filter_by_window(load_entries(log_path), args.days)
    stats = aggregate(entries)

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        sys.stdout.write(format_text(stats, args.days))


if __name__ == "__main__":
    main()
