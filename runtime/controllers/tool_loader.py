"""Scan tool directories and return tools matching a keyword query.

Usage:
    python tool_loader.py --query "api"
    python tool_loader.py --query "scrape" --scan-dir path1 --scan-dir path2
    python tool_loader.py --all
"""

import argparse
import ast
import json
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"tools_dirs": []}


def extract_tool_info(file_path: Path) -> dict:
    """Extract name, path, and docstring from a Python tool file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree) or ""
    except Exception:
        docstring = ""

    return {
        "name": file_path.stem,
        "path": str(file_path),
        "description": docstring.split("\n")[0] if docstring else "(no description)",
    }


def score_match(tool: dict, query_terms: list[str]) -> float:
    """Score how well a tool matches query terms. Higher = better match."""
    text = f"{tool['name']} {tool['description']}".lower()
    matches = sum(1 for term in query_terms if term in text)
    if not query_terms:
        return 0
    return matches / len(query_terms)


def scan_directory(directory: Path) -> list[dict]:
    """Find all .py files in a directory (non-recursive) and extract info."""
    tools = []
    if not directory.is_dir():
        return tools
    for f in sorted(directory.glob("*.py")):
        if f.name.startswith("_"):
            continue
        tools.append(extract_tool_info(f))
    return tools


def main():
    parser = argparse.ArgumentParser(description="Discover tools by keyword")
    parser.add_argument("--query", type=str, default="", help="Keyword to search for")
    parser.add_argument("--scan-dir", action="append", dest="scan_dirs", help="Directory to scan")
    parser.add_argument("--all", action="store_true", help="List all tools without filtering")
    parser.add_argument("--json", action="store_true", default=True, help="Output as JSON")
    args = parser.parse_args()

    config = load_config()
    dirs = args.scan_dirs or config.get("tools_dirs", [])

    all_tools = []
    for d in dirs:
        all_tools.extend(scan_directory(Path(d)))

    if args.all or not args.query:
        for t in all_tools:
            t["match_score"] = 1.0
        results = all_tools
    else:
        query_terms = args.query.lower().split()
        for t in all_tools:
            t["match_score"] = score_match(t, query_terms)
        results = [t for t in all_tools if t["match_score"] > 0]
        results.sort(key=lambda x: x["match_score"], reverse=True)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
