"""Standalone file-based memory query tool. Reads index.json directly, bypasses MCP.

Usage:
    python memory_controller.py --query "auth refactor" --repo "my-project"
    python memory_controller.py --query "deploy" --cross-repo --max-tokens 300
    python memory_controller.py --local-only --working-dir "A:/my-project"
"""

import argparse
import json
import os
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "memory_root": str(Path.home() / ".claude_memory"),
        "memory_server_modules": str(Path.home() / ".claude_memory" / "server"),
    }


def setup_imports():
    """Add memory server modules to sys.path for scoring imports."""
    config = load_config()
    server_path = config.get("memory_server_modules", "")
    if server_path and server_path not in sys.path:
        sys.path.insert(0, server_path)


def load_index(memory_root: str) -> list:
    index_path = Path(memory_root) / "index.json"
    if not index_path.exists():
        return []
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def load_entry_file(memory_root: str, entry: dict) -> str:
    """Load the content of a memory entry file."""
    file_path = entry.get("file_path", "")
    if not file_path:
        return entry.get("content", "")

    full_path = Path(memory_root) / file_path if not Path(file_path).is_absolute() else Path(file_path)
    if full_path.exists():
        try:
            return full_path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return entry.get("content", "")


def keyword_score(query_terms: list[str], text: str) -> float:
    """Simple keyword matching score."""
    text_lower = text.lower()
    if not query_terms:
        return 0.5
    matches = sum(1 for t in query_terms if t in text_lower)
    return matches / len(query_terms)


def query_global(args):
    config = load_config()
    memory_root = config["memory_root"]

    setup_imports()
    try:
        from memory_scorer import composite_score, estimate_tokens
    except ImportError:
        # Fallback if server modules unavailable
        def composite_score(entry):
            return entry.get("relevance_score", 50)
        def estimate_tokens(text):
            return int(len(text.split()) * 1.3) if text else 0

    index = load_index(memory_root)
    if not index:
        print(json.dumps({"memories": [], "token_count": 0, "sources": "index_empty", "entries_scanned": 0}))
        return

    query_terms = args.query.lower().split() if args.query else []
    max_tokens = args.max_tokens

    # Filter by repo unless cross-repo
    if args.repo and not args.cross_repo:
        index = [e for e in index if e.get("repo", "") == args.repo]

    # Score and rank entries
    scored = []
    for entry in index:
        # Combine composite score with query relevance
        cs = composite_score(entry)
        searchable = f"{entry.get('content', '')} {' '.join(entry.get('tags', []))}"
        ks = keyword_score(query_terms, searchable)
        entry["_combined_score"] = cs * 0.6 + ks * 100 * 0.4
        scored.append(entry)

    scored.sort(key=lambda x: x["_combined_score"], reverse=True)

    # Accumulate within token budget
    results = []
    total_tokens = 0
    for entry in scored:
        content = load_entry_file(memory_root, entry)
        tokens = estimate_tokens(content)
        if total_tokens + tokens > max_tokens and results:
            break
        results.append({
            "id": entry.get("id", ""),
            "type": entry.get("type", ""),
            "repo": entry.get("repo", ""),
            "content": content[:500],  # Truncate for safety
            "score": round(entry["_combined_score"], 2),
            "tokens": tokens,
            "created": entry.get("created", ""),
            "tags": entry.get("tags", []),
        })
        total_tokens += tokens

    output = {
        "memories": results,
        "token_count": total_tokens,
        "sources": "global_index",
        "entries_scanned": len(index),
    }
    print(json.dumps(output, indent=2))


def query_local(args):
    working_dir = args.working_dir or os.getcwd()
    local_path = Path(working_dir) / ".repo_memory"

    results = []
    total_tokens = 0

    # Check hot.md
    hot_md = local_path / "hot.md"
    if hot_md.exists():
        content = hot_md.read_text(encoding="utf-8")
        tokens = int(len(content.split()) * 1.3)
        results.append({
            "source": "hot.md",
            "content": content,
            "tokens": tokens,
        })
        total_tokens += tokens

    # Check recent_sessions.json
    recent = local_path / "recent_sessions.json"
    if recent.exists():
        try:
            sessions = json.loads(recent.read_text(encoding="utf-8"))
            for session in sessions[:5]:
                content = json.dumps(session) if isinstance(session, dict) else str(session)
                tokens = int(len(content.split()) * 1.3)
                if total_tokens + tokens > args.max_tokens and results:
                    break
                results.append({
                    "source": "recent_sessions",
                    "content": content[:300],
                    "tokens": tokens,
                })
                total_tokens += tokens
        except (json.JSONDecodeError, OSError):
            pass

    output = {
        "memories": results,
        "token_count": total_tokens,
        "sources": "local_cache",
        "local_path": str(local_path),
    }
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Query memory directly from index files")
    parser.add_argument("--query", type=str, default="", help="Search keywords")
    parser.add_argument("--repo", type=str, default="", help="Filter by repo name")
    parser.add_argument("--cross-repo", action="store_true", help="Search across all repos")
    parser.add_argument("--max-tokens", type=int, default=500, help="Token budget (default: 500)")
    parser.add_argument("--local-only", action="store_true", help="Only check .repo_memory/ in working dir")
    parser.add_argument("--working-dir", type=str, default="", help="Working directory for local-only mode")
    parser.add_argument("--type", type=str, default="", help="Filter by entry type")
    args = parser.parse_args()

    if args.local_only:
        query_local(args)
    else:
        query_global(args)


if __name__ == "__main__":
    main()
