"""Unified runtime loader — single command to bootstrap the full runtime for a task.

Replaces the manual chain of: read context_router, read mode_selector, run mcp_router, etc.
Claude calls this ONCE at the start of a Moderate+ task and gets back exactly what to load.

Usage:
    python runtime_loader.py --task "refactor auth module" --complexity moderate
    python runtime_loader.py --task "fix typo" --complexity trivial
    python runtime_loader.py --task "design caching layer" --complexity architectural
    python runtime_loader.py --status
"""

import argparse
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RUNTIME_PATH = Path.home() / ".claude_runtime"
CONFIG_PATH = RUNTIME_PATH / "configs" / "runtime_config.json"
MEMORY_ROOT = Path.home() / ".claude_memory"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def detect_repo(working_dir: str = None) -> str:
    wd = working_dir or os.getcwd()
    git_config = Path(wd) / ".git" / "config"
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
    return os.path.basename(os.path.abspath(wd))


def classify_mode(complexity: str) -> str:
    complexity = complexity.lower().strip()
    if complexity in ("trivial", "simple"):
        return "LIGHT"
    elif complexity == "moderate":
        return "STANDARD"
    elif complexity in ("complex", "architectural"):
        return "DEEP"
    return "STANDARD"


def check_local_memory(working_dir: str) -> dict:
    hot_md = Path(working_dir) / ".repo_memory" / "hot.md"
    if hot_md.exists():
        age_hours = (time.time() - hot_md.stat().st_mtime) / 3600
        return {
            "available": True,
            "fresh": age_hours < 24,
            "age_hours": round(age_hours, 1),
            "path": str(hot_md),
        }
    return {"available": False}


def check_global_memory(repo_name: str) -> dict:
    index_path = MEMORY_ROOT / "index.json"
    if not index_path.exists():
        return {"available": False, "entry_count": 0}
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        repo_entries = [e for e in index if e.get("repo", "") == repo_name]
        return {"available": len(repo_entries) > 0, "entry_count": len(repo_entries)}
    except Exception:
        return {"available": False, "entry_count": 0}


def detect_task_signals(task: str) -> dict:
    """Detect what the task needs based on keywords."""
    task_lower = task.lower()
    signals = {
        "needs_memory": False,
        "needs_wiki": False,
        "needs_advisor": False,
        "needs_tool_discovery": False,
        "needs_skills": False,
        "suggested_skill": None,
    }

    # Memory signals
    memory_words = ["prior", "previous", "last time", "before", "history", "continue", "resume", "again"]
    if any(w in task_lower for w in memory_words):
        signals["needs_memory"] = True

    # Wiki signals (Claude/Anthropic capabilities)
    wiki_words = ["claude", "anthropic", "api", "mcp", "agent sdk", "prompt", "model", "token", "pricing"]
    if any(w in task_lower for w in wiki_words):
        signals["needs_wiki"] = True

    # Advisor signals
    advisor_words = ["design", "architect", "trade-off", "approach", "strategy", "which method"]
    if any(w in task_lower for w in advisor_words):
        signals["needs_advisor"] = True

    # Tool discovery signals
    tool_words = ["tool", "script", "utility", "available", "what can"]
    if any(w in task_lower for w in tool_words):
        signals["needs_tool_discovery"] = True

    # Skill mapping
    skill_map = [
        (["build", "create", "add", "implement", "feature", "new"], "superpowers:brainstorming"),
        (["bug", "fix", "error", "fail", "broken", "crash", "debug"], "superpowers:systematic-debugging"),
        (["plan", "design", "architect", "strategy"], "superpowers:writing-plans"),
        (["review", "check", "audit"], "superpowers:requesting-code-review"),
        (["test", "tdd", "spec"], "superpowers:test-driven-development"),
    ]
    for keywords, skill in skill_map:
        if any(w in task_lower for w in keywords):
            signals["needs_skills"] = True
            signals["suggested_skill"] = skill
            break

    return signals


def build_load_plan(mode: str, task: str, repo: str, working_dir: str) -> dict:
    """Build the complete load plan for this task."""
    config = load_config()
    runtime = str(RUNTIME_PATH)
    signals = detect_task_signals(task)
    local_mem = check_local_memory(working_dir)
    global_mem = check_global_memory(repo)

    plan = {
        "mode": mode,
        "repo": repo,
        "working_dir": working_dir,
        "signals": signals,
        "load": [],
        "skip": [],
        "commands": [],
    }

    # LIGHT mode: load nothing extra
    if mode == "LIGHT":
        plan["skip"] = ["context_router", "mode_selector", "memory", "wiki", "skills", "tool_discovery"]
        plan["instructions"] = "LIGHT mode — do the work directly, no runtime overhead."
        return plan

    # STANDARD/DEEP: build load list
    # Memory
    if mode == "DEEP" or signals["needs_memory"]:
        if local_mem["available"] and local_mem.get("fresh"):
            plan["load"].append("local_memory")
            plan["commands"].append(f"Read {local_mem['path']}")
        elif global_mem["available"]:
            plan["load"].append("global_memory")
            plan["commands"].append(
                f'python "{runtime}/controllers/memory_controller.py" --query "{task[:50]}" --repo "{repo}"'
            )
        else:
            plan["load"].append("mcp_memory")
            plan["commands"].append("Call memory_retrieve MCP tool")
    else:
        plan["skip"].append("memory")

    # Wiki
    if signals["needs_wiki"]:
        wiki_path = config.get("wiki_path", "")
        plan["load"].append("wiki")
        plan["commands"].append(f"Read {wiki_path}/_hot.md")
    else:
        plan["skip"].append("wiki")

    # Tool discovery
    if signals["needs_tool_discovery"] or mode == "DEEP":
        plan["load"].append("tool_discovery")
        keyword = task.split()[0] if task else "all"
        plan["commands"].append(
            f'python "{runtime}/controllers/tool_loader.py" --query "{keyword}"'
        )
    else:
        plan["skip"].append("tool_discovery")

    # Skills
    if signals["needs_skills"] and mode != "LIGHT":
        plan["load"].append("skill")
        plan["commands"].append(f"Invoke Skill: {signals['suggested_skill']}")
    else:
        plan["skip"].append("skills")

    # Advisor (DEEP mode only, and only on non-Opus models)
    if signals["needs_advisor"] and mode == "DEEP":
        advisor_path = config.get("tools_dirs", [""])[0]
        plan["load"].append("advisor")
        plan["commands"].append(f'python "{advisor_path}advisor.py" -p "{task[:80]}"')
    else:
        plan["skip"].append("advisor")

    # Post-task logging
    plan["post_task"] = (
        f'python "{runtime}/controllers/usage_logger.py" '
        f'--mode {mode} --task-summary "{{SUMMARY}}"'
    )

    plan["instructions"] = (
        f"{mode} mode — execute the {len(plan['commands'])} commands above in order, "
        f"then do the work. Log usage when done."
    )

    return plan


def show_status():
    """Show runtime readiness status."""
    config = load_config()
    repo = detect_repo()

    status = {
        "runtime_installed": RUNTIME_PATH.exists(),
        "config_valid": CONFIG_PATH.exists(),
        "repo": repo,
        "working_dir": os.getcwd(),
        "components": {
            "context_router": (RUNTIME_PATH / "core" / "context_router.md").exists(),
            "mode_selector": (RUNTIME_PATH / "core" / "mode_selector.md").exists(),
            "skill_router": (RUNTIME_PATH / "core" / "skill_router.md").exists(),
            "token_budget": (RUNTIME_PATH / "core" / "token_budget.md").exists(),
            "tool_loader": (RUNTIME_PATH / "controllers" / "tool_loader.py").exists(),
            "memory_controller": (RUNTIME_PATH / "controllers" / "memory_controller.py").exists(),
            "mcp_router": (RUNTIME_PATH / "controllers" / "mcp_router.py").exists(),
            "usage_logger": (RUNTIME_PATH / "controllers" / "usage_logger.py").exists(),
        },
        "local_memory": check_local_memory(os.getcwd()),
        "global_memory": check_global_memory(repo),
        "global_claude_md": (Path.home() / ".claude" / "CLAUDE.md").exists(),
        "project_claude_md": (Path.cwd() / "CLAUDE.md").exists(),
    }

    all_components = all(status["components"].values())
    status["ready"] = all_components and status["runtime_installed"] and status["config_valid"]
    print(json.dumps(status, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Load global runtime for current task")
    parser.add_argument("--task", type=str, default="", help="Task description")
    parser.add_argument("--complexity", type=str, default="moderate",
                        help="Task complexity: trivial, simple, moderate, complex, architectural")
    parser.add_argument("--working-dir", type=str, default="", help="Override working directory")
    parser.add_argument("--status", action="store_true", help="Show runtime readiness")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    working_dir = args.working_dir or os.getcwd()
    repo = detect_repo(working_dir)
    mode = classify_mode(args.complexity)
    plan = build_load_plan(mode, args.task, repo, working_dir)
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
