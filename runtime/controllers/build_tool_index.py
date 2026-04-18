"""Build or refresh tool_index.json — a deterministic tool capability map.

Usage:
    python build_tool_index.py                  # Reads tools_dirs from runtime_config.json
    python build_tool_index.py --scan-dir PATH  # Override directories to scan
    python build_tool_index.py --output PATH    # Write index to a specific location

The index format:
    {
      "generated": "2026-04-18T12:00:00+00:00",
      "tools": [
        {
          "name": "advisor",
          "path": ".../advisor.py",
          "description": "Consult a stronger reviewer model",
          "capabilities": ["advisor", "consult", "reviewer", "model"]
        }
      ]
    }

Capabilities are content words extracted from the docstring's first line
plus the filename, with stopwords removed. Deterministic — same input
always yields the same capabilities list.
"""

import argparse
import ast
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude_runtime" / "configs" / "runtime_config.json"
DEFAULT_INDEX_PATH = Path.home() / ".claude_runtime" / "controllers" / "tool_index.json"

# Common English stopwords and mechanical tokens that contribute no retrieval signal.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "for", "of", "to", "in",
    "on", "at", "by", "with", "from", "as", "is", "it", "this", "that", "these",
    "those", "be", "been", "was", "were", "are", "have", "has", "had", "will",
    "would", "can", "could", "should", "may", "might", "must", "do", "does",
    "did", "so", "not", "no", "yes", "also", "just", "only", "any", "all",
    "some", "more", "most", "other", "such", "than", "into", "over", "out",
    "up", "down", "about", "via", "using", "use", "uses", "used",
}


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"tools_dirs": []}


def extract_capabilities(name: str, description: str) -> list:
    """Return a stable, ordered list of lowercase capability terms.

    Strategy: include the file stem (split on _ and -), add content words from
    the docstring's first line, drop stopwords and sub-3-char tokens.
    """
    terms = []
    seen = set()

    def add(token: str):
        t = token.lower().strip()
        if len(t) < 3 or t in _STOPWORDS or t in seen:
            return
        seen.add(t)
        terms.append(t)

    # Filename parts carry strong signal ("memory_retriever" -> memory, retriever)
    for part in re.split(r"[_\-]+", name):
        add(part)

    # Tokenize description into content words
    for token in re.split(r"[^A-Za-z0-9]+", description):
        add(token)

    return terms


def extract_tool_info(file_path: Path) -> dict:
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree) or ""
    except Exception:
        docstring = ""

    description = docstring.split("\n")[0] if docstring else "(no description)"
    name = file_path.stem
    return {
        "name": name,
        "path": str(file_path).replace("\\", "/"),
        "description": description,
        "capabilities": extract_capabilities(name, description),
    }


def scan_directory(directory: Path) -> list:
    tools = []
    if not directory.is_dir():
        return tools
    for f in sorted(directory.glob("*.py")):
        if f.name.startswith("_"):
            continue
        tools.append(extract_tool_info(f))
    return tools


def build_index(scan_dirs: list) -> dict:
    all_tools = []
    for d in scan_dirs:
        all_tools.extend(scan_directory(Path(d)))
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "tools": all_tools,
    }


def main():
    parser = argparse.ArgumentParser(description="Build tool_index.json from tools_dirs")
    parser.add_argument("--scan-dir", action="append", dest="scan_dirs", help="Directory to scan (repeatable)")
    parser.add_argument("--output", type=str, default=None, help="Path to write the index")
    args = parser.parse_args()

    if args.scan_dirs:
        dirs = args.scan_dirs
    else:
        dirs = load_config().get("tools_dirs", [])

    index = build_index(dirs)
    output_path = Path(args.output) if args.output else DEFAULT_INDEX_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "tools_indexed": len(index["tools"]),
        "output": str(output_path).replace("\\", "/"),
    }, indent=2))


if __name__ == "__main__":
    main()
