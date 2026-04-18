"""Append usage records to the runtime log for analysis over time.

Usage:
    python usage_logger.py --mode STANDARD --tools-used "advisor.py,tool_loader.py" --memory-tokens 312 --task-summary "Refactored auth"
    python usage_logger.py --stats
    python usage_logger.py --finalize <task_id> --success true --outcome-note "All tests green"
    python usage_logger.py --finalize <task_id> --success false --outcome-note "Hit API rate limit"

Records carry an `id`, `success` (tri-state: true/false/null), and `outcome_note`.
A fresh log call starts with success=null; --finalize sets the outcome later.
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"

# Per-component token cost when the runtime actually loads it.
# Values measured against the installed v1.3.0 templates; close enough for
# trend comparison even if individual files drift a few tokens.
COMPONENT_COSTS = {
    "context_router":   495,
    "mode_selector":    451,
    "skill_router":     395,
    "token_budget":     397,
    "wiki":             641,   # _hot.md + index.md combined
    "wiki_hot":         185,
    "tool_discovery":   500,
    "skill":            800,
    "advisor":          200,
}
# Memory components (local_memory / global_memory / mcp_memory) are dynamic —
# we read the actual returned size from the per-record `memory_tokens` field
# rather than the table.
_MEMORY_COMPONENT_NAMES = {"memory", "local_memory", "global_memory", "mcp_memory"}

# Naive baseline: what each task would cost if every runtime component were
# loaded blindly (no LIGHT/STANDARD/DEEP gating, no memory cap). Used as the
# denominator for the "tokens saved" metric.
NAIVE_BASELINE_TOKENS = (
    495 + 451 + 395 + 397    # all four core docs
    + 641                     # full wiki
    + 2000                    # uncapped memory dump (vs. our 500 cap)
    + 500                     # full tool discovery walk
    + 800                     # default skill content
    + 200                     # advisor
)  # = 5879


def compute_tokens_loaded(components_loaded: list[str], memory_tokens: int) -> int:
    """Sum the static cost of loaded components plus the actual memory cost."""
    static = sum(
        COMPONENT_COSTS.get(c, 0)
        for c in components_loaded
        if c not in _MEMORY_COMPONENT_NAMES
    )
    return static + max(0, int(memory_tokens or 0))


def compute_tokens_saved(components_loaded: list[str], memory_tokens: int) -> int:
    """Savings vs. the naive baseline. Floored at 0 — never report negative."""
    return max(0, NAIVE_BASELINE_TOKENS - compute_tokens_loaded(components_loaded, memory_tokens))


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


def _parse_success(raw: str | None) -> bool | None:
    """Parse a string truthy/falsy value. None stays None."""
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in ("true", "1", "yes", "y", "ok", "pass", "passed"):
        return True
    if val in ("false", "0", "no", "n", "fail", "failed"):
        return False
    raise ValueError(f"--success must be true/false, got: {raw}")


def log_usage(args):
    log_path = get_log_path()
    entries = load_log(log_path)

    components = (
        [c.strip() for c in args.components_loaded.split(",") if c.strip()]
        if args.components_loaded else []
    )
    memory_tokens = args.memory_tokens or 0
    tokens_loaded = compute_tokens_loaded(components, memory_tokens)
    tokens_saved = compute_tokens_saved(components, memory_tokens)

    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode or "UNKNOWN",
        "tools_used": [t.strip() for t in args.tools_used.split(",") if t.strip()] if args.tools_used else [],
        "memory_tokens": memory_tokens,
        "components_loaded": components,
        "tokens_loaded": tokens_loaded,
        "tokens_saved": tokens_saved,
        "baseline_tokens": NAIVE_BASELINE_TOKENS,
        "task_summary": args.task_summary or "",
        "repo": detect_repo(),
        "success": _parse_success(args.success),
        "outcome_note": args.outcome_note or "",
    }

    entries.append(record)
    entries = rotate_if_needed(log_path, entries)
    save_log(log_path, entries)
    print(json.dumps({"status": "logged", "record": record}, indent=2))


def finalize(args):
    """Update success + outcome_note on an existing record by id."""
    log_path = get_log_path()
    entries = load_log(log_path)

    target_id = args.finalize
    success_value = _parse_success(args.success)
    note = args.outcome_note or ""

    for record in entries:
        if record.get("id") == target_id:
            record["success"] = success_value
            if note:
                record["outcome_note"] = note
            record["finalized_at"] = datetime.now(timezone.utc).isoformat()
            save_log(log_path, entries)
            print(json.dumps({"status": "finalized", "record": record}, indent=2))
            return

    print(json.dumps({"status": "not_found", "id": target_id}), file=sys.stderr)
    sys.exit(2)


def show_stats():
    log_path = get_log_path()
    entries = load_log(log_path)

    if not entries:
        print(json.dumps({"total_entries": 0, "message": "No usage data yet"}))
        return

    mode_counts = {}
    tool_counts = {}
    total_memory = 0
    total_saved = 0
    total_loaded = 0
    success_by_mode = {}  # mode -> [wins, losses, unknown]

    for e in entries:
        mode = e.get("mode", "UNKNOWN")
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        for tool in e.get("tools_used", []):
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        total_memory += e.get("memory_tokens", 0)
        # Backfill: older records lack these fields. Compute on the fly so
        # historical data still contributes to the savings rollup.
        if "tokens_saved" in e:
            total_saved += e.get("tokens_saved", 0)
            total_loaded += e.get("tokens_loaded", 0)
        else:
            comps = e.get("components_loaded", [])
            mt = e.get("memory_tokens", 0)
            total_saved += compute_tokens_saved(comps, mt)
            total_loaded += compute_tokens_loaded(comps, mt)

        bucket = success_by_mode.setdefault(mode, [0, 0, 0])
        s = e.get("success")
        if s is True:
            bucket[0] += 1
        elif s is False:
            bucket[1] += 1
        else:
            bucket[2] += 1

    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    success_rate = {}
    for mode, (wins, losses, _unknown) in success_by_mode.items():
        finalized = wins + losses
        success_rate[mode] = round(wins / finalized, 3) if finalized else None

    n = len(entries)
    stats = {
        "total_entries": n,
        "mode_distribution": mode_counts,
        "top_tools": dict(top_tools),
        "avg_memory_tokens": round(total_memory / n, 1),
        "tokens_saved_total": total_saved,
        "tokens_loaded_total": total_loaded,
        "tokens_saved_avg_per_task": round(total_saved / n, 1),
        "tokens_baseline_per_task": NAIVE_BASELINE_TOKENS,
        "savings_pct_vs_baseline": round(
            100.0 * total_saved / (NAIVE_BASELINE_TOKENS * n), 1
        ) if n else 0.0,
        "success_rate_by_mode": success_rate,
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
    parser.add_argument("--components-loaded", type=str, default="",
                        help="Comma-separated list of runtime components actually loaded "
                             "(e.g. 'wiki,tool_discovery,advisor'). Drives tokens_saved metric.")
    parser.add_argument("--task-summary", type=str, default="", help="Brief task description")
    parser.add_argument("--success", type=str, default=None, help="true/false; set on log or finalize")
    parser.add_argument("--outcome-note", type=str, default="", help="Optional free-form outcome note")
    parser.add_argument("--finalize", type=str, default=None, help="Task id to finalize")
    parser.add_argument("--stats", action="store_true", help="Show usage statistics")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.finalize:
        finalize(args)
    else:
        log_usage(args)


if __name__ == "__main__":
    main()
