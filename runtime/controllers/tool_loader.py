"""Scan tool directories and return tools matching a keyword query.

Usage:
    python tool_loader.py --query "api"
    python tool_loader.py --query "scrape" --scan-dir path1 --scan-dir path2
    python tool_loader.py --all
    python tool_loader.py --rebuild-index

Lookup order:
    1. Consult tool_index.json (fast, deterministic capabilities).
    2. On miss or absent index, fall back to docstring scanning.
"""

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"
INDEX_PATH = Path(__file__).parent / "tool_index.json"
BUILDER_PATH = Path(__file__).parent / "build_tool_index.py"


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


def load_index() -> dict | None:
    """Load tool_index.json if present and well-formed."""
    if not INDEX_PATH.exists():
        return None
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("tools"), list):
            return data
    except (json.JSONDecodeError, OSError):
        return None
    return None


def score_index_entry(entry: dict, query_terms: list[str]) -> float:
    """Score an index entry. Capability hits weigh more than name/description hits."""
    if not query_terms:
        return 0.0

    name = entry.get("name", "").lower()
    description = entry.get("description", "").lower()
    capabilities = {c.lower() for c in entry.get("capabilities", [])}
    text = f"{name} {description}"

    hits = 0.0
    for term in query_terms:
        if term in capabilities:
            hits += 1.0
        elif term in text:
            hits += 0.5
    return hits / len(query_terms)


def query_index(index: dict, query_terms: list[str]) -> list[dict]:
    """Return index entries scoring > 0, sorted by match_score desc."""
    results = []
    for entry in index.get("tools", []):
        score = score_index_entry(entry, query_terms)
        if score > 0:
            results.append({
                "name": entry.get("name", ""),
                "path": entry.get("path", ""),
                "description": entry.get("description", ""),
                "match_score": round(score, 3),
                "source": "index",
            })
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results


def rebuild_index() -> int:
    """Invoke build_tool_index.py in-process equivalent via subprocess."""
    if not BUILDER_PATH.exists():
        print(json.dumps({"status": "error", "reason": "builder not found", "path": str(BUILDER_PATH)}))
        return 1
    result = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Discover tools by keyword")
    parser.add_argument("--query", type=str, default="", help="Keyword to search for")
    parser.add_argument("--scan-dir", action="append", dest="scan_dirs", help="Directory to scan")
    parser.add_argument("--all", action="store_true", help="List all tools without filtering")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild tool_index.json from tools_dirs")
    parser.add_argument("--no-index", action="store_true", help="Skip the index; force docstring walk")
    parser.add_argument("--json", action="store_true", default=True, help="Output as JSON")
    args = parser.parse_args()

    if args.rebuild_index:
        sys.exit(rebuild_index())

    query_terms = args.query.lower().split() if args.query else []

    # Index-first path: only used when the caller provided a query and didn't opt out,
    # and no explicit --scan-dir override was given (overrides imply ad-hoc scanning).
    if query_terms and not args.no_index and not args.scan_dirs:
        index = load_index()
        if index is not None:
            hits = query_index(index, query_terms)
            if hits:
                print(json.dumps(hits, indent=2))
                return

    # Fallback: docstring walk
    config = load_config()
    dirs = args.scan_dirs or config.get("tools_dirs", [])

    all_tools = []
    for d in dirs:
        all_tools.extend(scan_directory(Path(d)))

    if args.all or not args.query:
        for t in all_tools:
            t["match_score"] = 1.0
            t["source"] = "scan"
        results = all_tools
    else:
        for t in all_tools:
            t["match_score"] = score_match(t, query_terms)
            t["source"] = "scan"
        results = [t for t in all_tools if t["match_score"] > 0]
        results.sort(key=lambda x: x["match_score"], reverse=True)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
