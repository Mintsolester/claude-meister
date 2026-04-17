"""Scan the system for repos and report runtime readiness of each.

Usage:
    python repo_scanner.py --root "A:/"
    python repo_scanner.py --root "A:/" --json
    python repo_scanner.py --root "A:/" --only-missing
"""

import argparse
import json
import os
from pathlib import Path

RUNTIME_PATH = Path.home() / ".claude_runtime"
MEMORY_ROOT = Path.home() / ".claude_memory"
INJECTION_MARKER = "<!-- RUNTIME:START -->"

EXCLUDED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".tmp",
                 "vendor", "dist", "build", ".next", ".nuxt", "target"}


def find_repos(root: str, max_depth: int = 4) -> list[Path]:
    """Find git repos under root, respecting max depth."""
    repos = []
    root_path = Path(root).resolve()

    for dirpath, dirnames, _ in os.walk(root_path):
        # Enforce max depth
        depth = len(Path(dirpath).relative_to(root_path).parts)
        if depth > max_depth:
            dirnames.clear()
            continue

        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

        if ".git" in os.listdir(dirpath):
            repos.append(Path(dirpath))
            dirnames.clear()

    return sorted(repos)


def analyze_repo(repo_path: Path) -> dict:
    """Analyze a repo's runtime readiness."""
    claude_md = repo_path / "CLAUDE.md"
    repo_memory = repo_path / ".repo_memory"

    info = {
        "path": str(repo_path),
        "name": repo_path.name,
        "has_claude_md": claude_md.exists(),
        "has_injection": False,
        "has_repo_memory": repo_memory.exists(),
        "has_hot_md": (repo_memory / "hot.md").exists() if repo_memory.exists() else False,
        "runtime_ready": False,
    }

    # Check if CLAUDE.md has runtime injection
    if claude_md.exists():
        try:
            content = claude_md.read_text(encoding="utf-8")
            info["has_injection"] = INJECTION_MARKER in content
            info["claude_md_lines"] = len(content.strip().split("\n"))
        except Exception:
            info["claude_md_lines"] = 0

    # Check global memory for this repo
    index_path = MEMORY_ROOT / "index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            repo_name = repo_path.name
            info["global_memory_entries"] = sum(1 for e in index if repo_name in e.get("repo", ""))
        except Exception:
            info["global_memory_entries"] = 0
    else:
        info["global_memory_entries"] = 0

    # Runtime readiness: global CLAUDE.md exists (handles injection) OR local injection present
    global_claude = Path.home() / ".claude" / "CLAUDE.md"
    info["runtime_ready"] = global_claude.exists()

    return info


def print_table(repos: list[dict]):
    """Print a human-readable table."""
    if not repos:
        print("No repos found.")
        return

    print(f"\n{'Repo':<35} {'CLAUDE.md':<12} {'Injected':<10} {'Memory':<10} {'Ready':<8}")
    print("-" * 75)

    for r in repos:
        name = r["name"][:34]
        has_md = "Yes" if r["has_claude_md"] else "-"
        injected = "Yes" if r["has_injection"] else "-"
        memory = "Yes" if r["has_repo_memory"] else "-"
        ready = "Ready" if r["runtime_ready"] else "MISSING"
        print(f"{name:<35} {has_md:<12} {injected:<10} {memory:<10} {ready:<8}")

    total = len(repos)
    with_md = sum(1 for r in repos if r["has_claude_md"])
    with_injection = sum(1 for r in repos if r["has_injection"])
    with_memory = sum(1 for r in repos if r["has_repo_memory"])
    ready = sum(1 for r in repos if r["runtime_ready"])

    print("-" * 75)
    print(f"{'TOTAL':<35} {with_md:<12} {with_injection:<10} {with_memory:<10} {ready:<8}")
    print(f"\n{total} repos scanned. {ready} runtime-ready. {total - with_md} missing CLAUDE.md.")


def main():
    parser = argparse.ArgumentParser(description="Scan repos and report runtime readiness")
    parser.add_argument("--root", type=str, required=True, help="Root directory to scan")
    parser.add_argument("--max-depth", type=int, default=4, help="Max directory depth (default: 4)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    parser.add_argument("--only-missing", action="store_true", help="Show only repos without injection")
    args = parser.parse_args()

    repos = find_repos(args.root, max_depth=args.max_depth)
    results = [analyze_repo(r) for r in repos]

    if args.only_missing:
        results = [r for r in results if not r["has_injection"]]

    if args.json_output:
        print(json.dumps({"root": args.root, "repos": results}, indent=2))
    else:
        print_table(results)


if __name__ == "__main__":
    main()
