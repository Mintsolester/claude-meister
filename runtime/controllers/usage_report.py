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

# Mirror the cost table from usage_logger so historical entries (logged before
# the savings fields were added) can still be scored. Keep these two in sync.
COMPONENT_COSTS = {
    "context_router": 495, "mode_selector": 451, "skill_router": 395,
    "token_budget": 397, "wiki": 641, "wiki_hot": 185,
    "tool_discovery": 500, "skill": 800, "advisor": 200,
}
_MEMORY_COMPONENT_NAMES = {"memory", "local_memory", "global_memory", "mcp_memory"}
NAIVE_BASELINE_TOKENS = 5879


def _tokens_loaded(components: list, memory_tokens: int) -> int:
    static = sum(
        COMPONENT_COSTS.get(c, 0)
        for c in components or []
        if c not in _MEMORY_COMPONENT_NAMES
    )
    return static + max(0, int(memory_tokens or 0))


def _tokens_saved(components: list, memory_tokens: int) -> int:
    return max(0, NAIVE_BASELINE_TOKENS - _tokens_loaded(components, memory_tokens))


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
            "tokens_saved_total": 0,
            "tokens_loaded_total": 0,
            "tokens_saved_avg_per_task": 0.0,
            "tokens_baseline_per_task": NAIVE_BASELINE_TOKENS,
            "savings_pct_vs_baseline": 0.0,
            "tokens_saved_by_mode": {},
            "date_range": {"first": None, "last": None},
        }

    mode_counts = defaultdict(int)
    mode_tokens = defaultdict(int)
    mode_saved = defaultdict(int)
    tool_counts = defaultdict(int)
    with_memory = 0
    successes = 0
    finalized = 0
    total_saved = 0
    total_loaded = 0

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

        # Token savings — prefer the value stored at log time; backfill for
        # older records that pre-date the metric.
        if "tokens_saved" in e:
            saved = e.get("tokens_saved", 0) or 0
            loaded = e.get("tokens_loaded", 0) or 0
        else:
            comps = e.get("components_loaded", [])
            saved = _tokens_saved(comps, tokens)
            loaded = _tokens_loaded(comps, tokens)
        total_saved += saved
        total_loaded += loaded
        mode_saved[mode] += saved

    avg_tokens_per_mode = {
        mode: round(mode_tokens[mode] / mode_counts[mode], 1)
        for mode in mode_counts
    }
    top_tools = dict(
        sorted(tool_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    )

    n = len(entries)
    return {
        "total_tasks": n,
        "mode_breakdown": dict(mode_counts),
        "avg_tokens_per_mode": avg_tokens_per_mode,
        "top_tools": top_tools,
        "memory_hit_rate": round(with_memory / n, 3),
        "success_rate": round(successes / finalized, 3) if finalized else None,
        "tokens_saved_total": total_saved,
        "tokens_loaded_total": total_loaded,
        "tokens_saved_avg_per_task": round(total_saved / n, 1),
        "tokens_baseline_per_task": NAIVE_BASELINE_TOKENS,
        "savings_pct_vs_baseline": round(100.0 * total_saved / (NAIVE_BASELINE_TOKENS * n), 1),
        "tokens_saved_by_mode": {m: mode_saved[m] for m in mode_counts},
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

    saved_total = stats.get("tokens_saved_total", 0)
    saved_avg = stats.get("tokens_saved_avg_per_task", 0.0)
    pct = stats.get("savings_pct_vs_baseline", 0.0)
    baseline = stats.get("tokens_baseline_per_task", 0)
    lines.append("Token savings vs naive baseline:")
    lines.append(f"  Baseline per task:   {baseline:>8} tokens (everything always loaded)")
    lines.append(f"  Total saved:         {saved_total:>8} tokens")
    lines.append(f"  Avg saved per task:  {saved_avg:>8.1f} tokens")
    lines.append(f"  Savings rate:        {pct:>8.1f}% of baseline")
    by_mode = stats.get("tokens_saved_by_mode", {})
    if by_mode:
        for mode, saved in sorted(by_mode.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"    {mode:<10} {saved:>8} tokens saved across all {mode} tasks")
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
