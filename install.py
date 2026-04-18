#!/usr/bin/env python3
"""Claude_Meister Installer — intelligence runtime for Claude Code.

Usage:
    python install.py                # Interactive install
    python install.py --full         # Full install (runtime + memory + wiki + CLAUDE.md)
    python install.py --runtime-only # Runtime engine only
    python install.py --memory-only  # Memory MCP server only
    python install.py --wiki-only    # Wiki knowledge base only
    python install.py --no-wiki      # Full install minus wiki
    python install.py --update       # Update existing installation
    python install.py --uninstall    # Remove everything
    python install.py --verify       # Post-install health check
    python install.py --stats        # Usage dashboard
"""

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

# Force UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from installer.paths import (
    check_prerequisites, get_paths, build_substitutions, detect_os
)
from installer.runtime import (
    install_runtime, update_runtime, remove_runtime, check_existing_installation
)
from installer.memory import install_memory, update_memory, remove_memory, check_dependencies
from installer.wiki import install_wiki, update_wiki, remove_wiki
from installer.claude_md import setup_claude_md, remove_claude_md_block, check_claude_md
from installer.mcp import register_mcp, remove_mcp, check_mcp
from installer.verify import run_verification


BANNER = """
================================================================
   Claude_Meister — Intelligence Runtime for Claude Code
================================================================
"""


def print_banner():
    print(BANNER)


def interactive_install():
    """Run the interactive installation flow."""
    print_banner()
    paths = get_paths()

    print(f"  Detected:")
    print(f"    OS:          {detect_os()}")
    print(f"    Home:        {paths['home']}")
    print(f"    Python:      {sys.version.split()[0]}")

    # Check prerequisites
    prereqs = check_prerequisites("full")
    if prereqs["claude_cli"]:
        print(f"    Claude Code: installed")
    else:
        print(f"    Claude Code: not found")

    print()

    # Check existing installation
    existing = check_existing_installation(paths)
    if existing["exists"]:
        if existing["complete"]:
            print("  Existing installation detected.")
            print("  [1] Update (refresh code, keep config & logs)")
            print("  [2] Clean install (start fresh)")
            print("  [3] Verify current installation")
            print("  [4] Exit")
            choice = input("\n  Choice [1]: ").strip() or "1"
            if choice == "1":
                do_update(paths)
                return
            elif choice == "2":
                pass  # Continue to install
            elif choice == "3":
                do_verify(paths, "full")
                return
            else:
                print("  Exiting.")
                return
        else:
            print("  Incomplete installation detected. Running clean install.")

    print("\n  What would you like to install?")
    print("    [1] Full install (recommended) -- Runtime + Memory + Wiki + CLAUDE.md")
    print("    [2] Runtime only -- Context routing, tool discovery, usage tracking")
    print("    [3] Memory only -- MCP memory server with scoring and evolution")
    print("    [4] Wiki only -- Knowledge base with tiered retrieval")
    print()
    choice = input("  Choice [1]: ").strip() or "1"

    mode_map = {"1": "full", "2": "runtime-only", "3": "memory-only", "4": "wiki-only"}
    install_mode = mode_map.get(choice, "full")

    do_install(paths, install_mode)


def do_install(paths: dict, mode: str):
    """Execute installation for the given mode."""
    print(f"\n  Installing ({mode})...\n")

    subs = build_substitutions(paths)
    results = []

    # Prerequisites
    prereqs = check_prerequisites(mode)
    if not prereqs["ok"]:
        print("  Prerequisites not met:\n")
        for issue in prereqs["issues"]:
            print(f"    - {issue}\n")
        sys.exit(1)
    for warning in prereqs.get("warnings", []):
        print(f"  Warning: {warning}")

    # Runtime
    if mode in ("full", "runtime-only"):
        print("  [1/5] Installing runtime engine...")
        result = install_runtime(paths, subs)
        print(f"         {result['message']}")
        results.append(("Runtime", result))

    # Memory
    if mode in ("full", "memory-only"):
        print("  [2/5] Installing memory server...")
        result = install_memory(paths)
        print(f"         {result['message']}")
        results.append(("Memory", result))

    # Wiki
    if mode in ("full", "wiki-only"):
        print("  [3/5] Installing wiki knowledge base...")
        result = install_wiki(paths)
        print(f"         {result['message']}")
        results.append(("Wiki", result))

    # CLAUDE.md
    if mode == "full":
        print("  [4/5] Setting up CLAUDE.md...")
        claude_state = check_claude_md(paths)

        if not claude_state["exists"]:
            result = setup_claude_md(paths, subs, mode="create")
        elif claude_state["has_markers"]:
            result = setup_claude_md(paths, subs, mode="update")
        else:
            # Existing CLAUDE.md without markers — ask
            print(f"\n         You have an existing CLAUDE.md ({claude_state['line_count']} lines).")
            for w in claude_state.get("warnings", []):
                print(f"         Warning: {w}")
            print(f"         Options:")
            print(f"           [1] Add runtime block to your existing file")
            print(f"           [2] Show me what to add (I'll do it manually)")
            print(f"           [3] Skip")
            sub_choice = input("         Choice [1]: ").strip() or "1"

            if sub_choice == "1":
                result = setup_claude_md(paths, subs, mode="append")
            elif sub_choice == "2":
                block_path = Path(paths["repo_root"]) / "templates" / "claude_md_block.md"
                if block_path.exists():
                    from installer.paths import apply_substitutions
                    content = apply_substitutions(
                        block_path.read_text(encoding="utf-8"), subs
                    )
                    print(f"\n         Add this to your ~/.claude/CLAUDE.md:\n")
                    print(content)
                result = {"status": "skipped", "message": "Printed block for manual addition."}
            else:
                result = {"status": "skipped", "message": "CLAUDE.md modification skipped."}

        print(f"         {result['message']}")
        results.append(("CLAUDE.md", result))

    # MCP registration
    if mode in ("full", "memory-only"):
        print("  [5/5] Registering MCP server...")
        result = register_mcp(paths)
        print(f"         {result['message']}")
        results.append(("MCP", result))

    # Summary
    print(f"\n  {'=' * 50}")
    ok = all(r[1]["status"] in ("success", "skipped") for r in results)
    if ok:
        print("  Installation complete!\n")
        print("  Next steps:")
        print("    1. Open a new Claude Code session in any repo")
        print("    2. Try a simple task (should use LIGHT mode)")
        print("    3. Try a complex task (should use DEEP mode)")
        print(f"    4. Run: python \"{__file__}\" --verify")
    else:
        print("  Installation completed with issues:\n")
        for name, result in results:
            status = "OK" if result["status"] in ("success", "skipped") else "ISSUE"
            print(f"    {name}: {status} - {result['message']}")


def do_inject_here(paths: dict):
    """Inject the runtime block into ./CLAUDE.md in the current working directory.

    Uses repo_scanner to pick between the full and minimal block templates
    based on the scanned repo's size and stack profile.
    """
    from installer.repo_scanner import scan_repo, choose_block_variant

    target = Path.cwd() / "CLAUDE.md"
    print_banner()
    print(f"  Target: {target}\n")

    subs = build_substitutions(paths)
    scan = scan_repo(Path.cwd())
    variant = choose_block_variant(scan)

    print(f"  Repo scan: language={scan['primary_language']} size={scan['size_bucket']} "
          f"files={scan['file_count']} tests={scan['has_tests']}")
    print(f"  Selected block variant: {variant}\n")

    result = setup_claude_md(paths, subs, mode="auto", target_override=target, block_variant=variant)
    print(f"  {result['message']}")

    if result["status"] != "success":
        sys.exit(1)


def do_update(paths: dict):
    """Update existing installation."""
    print("\n  Updating...\n")
    subs = build_substitutions(paths)

    print("  [1/4] Updating runtime...")
    result = update_runtime(paths, subs)
    print(f"         {result['message']}")

    print("  [2/4] Updating memory server...")
    result = update_memory(paths)
    print(f"         {result['message']}")

    print("  [3/4] Updating wiki...")
    result = update_wiki(paths)
    print(f"         {result['message']}")

    print("  [4/4] Refreshing CLAUDE.md runtime block...")
    state = check_claude_md(paths)
    if not state["exists"]:
        print("         Skipped: CLAUDE.md does not exist. Run --full to create it.")
    elif not state["has_markers"]:
        print("         Skipped: no runtime block found. Run --full to inject one.")
    else:
        result = setup_claude_md(paths, subs, mode="update")
        print(f"         {result['message']}")

    print("\n  Update complete. Config, logs, and memories preserved.")


def do_uninstall(paths: dict):
    """Remove Claude_Meister."""
    print_banner()
    print("  This will remove Claude_Meister from your system.\n")

    # CLAUDE.md
    print("  [1/4] Removing runtime block from CLAUDE.md...")
    result = remove_claude_md_block(paths)
    print(f"         {result['message']}")

    # MCP
    print("  [2/4] Unregistering MCP server...")
    result = remove_mcp()
    print(f"         {result['message']}")

    # Memory
    print("  [3/4] Removing memory server...")
    keep = input("         Keep stored memories? [Y/n]: ").strip().lower() != "n"
    result = remove_memory(paths, confirm=False, keep_data=keep)
    print(f"         {result['message']}")

    # Runtime
    print("  [4/4] Removing runtime engine...")
    result = remove_runtime(paths, confirm=False)
    print(f"         {result['message']}")

    # Wiki
    wiki_dir = Path(paths["wiki_path"])
    if wiki_dir.exists():
        remove_wiki_choice = input("  Remove wiki? [y/N]: ").strip().lower()
        if remove_wiki_choice == "y":
            result = remove_wiki(paths, confirm=False)
            print(f"         {result['message']}")

    print("\n  Claude_Meister has been removed.")


def do_verify(paths: dict, mode: str):
    """Run verification checks."""
    print("\n  Running verification...\n")
    results = run_verification(paths, mode)

    for check in results["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"  [{status}] {check['name']} - {check.get('detail', '')}")
        if not check["passed"] and check.get("fix"):
            print(f"         Fix: {check['fix']}")

    print(f"\n  {results['passed']} passed, {results['failed']} failed")
    if results["ok"]:
        print("  All checks passed!")
    else:
        print("  Some checks failed. See fixes above.")


def do_stats(paths: dict):
    """Show usage statistics dashboard."""
    log_path = Path(paths["runtime_path"]) / "logs" / "runtime_usage.json"

    if not log_path.exists():
        print("  No usage data yet. Use Claude Code with the runtime and check back.")
        return

    try:
        entries = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception):
        print("  Usage log is corrupted. Delete it and it will be recreated.")
        return

    if not entries:
        print("  No usage data yet. Use Claude Code with the runtime and check back.")
        return

    total = len(entries)
    modes = {}
    memory_tokens = []
    for e in entries:
        mode = e.get("mode", "unknown")
        modes[mode] = modes.get(mode, 0) + 1
        mt = e.get("memory_tokens", 0)
        if mt:
            memory_tokens.append(mt)

    light_count = modes.get("LIGHT", 0)

    print(f"\n  Claude_Meister Usage Report")
    print(f"  {'=' * 45}")
    print(f"  Tasks logged:           {total}")

    mode_str = " | ".join(f"{m} {c}" for m, c in sorted(modes.items()))
    print(f"  Mode distribution:      {mode_str}")

    if memory_tokens:
        avg = sum(memory_tokens) / len(memory_tokens)
        print(f"  Avg memory tokens:      {avg:.0f} / 500 cap")
        print(f"  Tasks with memory:      {len(memory_tokens)} ({len(memory_tokens)*100//total}%)")

    if light_count:
        print(f"  Tasks skipping runtime: {light_count} ({light_count*100//total}%)")
        print(f"\n  Estimated savings:      ~{light_count * 600:,} tokens saved by LIGHT mode")


def main():
    parser = argparse.ArgumentParser(
        description="Claude_Meister — Intelligence Runtime for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--full", action="store_true", help="Full install")
    parser.add_argument("--runtime-only", action="store_true", help="Runtime engine only")
    parser.add_argument("--memory-only", action="store_true", help="Memory server only")
    parser.add_argument("--wiki-only", action="store_true", help="Wiki knowledge base only")
    parser.add_argument("--no-wiki", action="store_true", help="Full install minus wiki")
    parser.add_argument("--update", action="store_true", help="Update existing installation")
    parser.add_argument("--uninstall", action="store_true", help="Remove everything")
    parser.add_argument("--verify", action="store_true", help="Post-install health check")
    parser.add_argument("--stats", action="store_true", help="Usage dashboard")
    parser.add_argument("--inject-here", action="store_true",
                        help="Inject runtime block into ./CLAUDE.md in the current directory")

    args = parser.parse_args()
    paths = get_paths()

    if args.update:
        do_update(paths)
    elif args.inject_here:
        do_inject_here(paths)
    elif args.uninstall:
        do_uninstall(paths)
    elif args.verify:
        mode = "full"
        if args.runtime_only:
            mode = "runtime-only"
        elif args.memory_only:
            mode = "memory-only"
        do_verify(paths, mode)
    elif args.stats:
        do_stats(paths)
    elif args.full:
        do_install(paths, "full")
    elif args.runtime_only:
        do_install(paths, "runtime-only")
    elif args.memory_only:
        do_install(paths, "memory-only")
    elif args.wiki_only:
        do_install(paths, "wiki-only")
    elif args.no_wiki:
        # Full minus wiki: install runtime, memory, claude_md, mcp
        subs = build_substitutions(paths)
        prereqs = check_prerequisites("full")
        if not prereqs["ok"]:
            for issue in prereqs["issues"]:
                print(f"  Error: {issue}")
            sys.exit(1)
        print_banner()
        print("  Installing (full, no wiki)...\n")
        print("  [1/4] Runtime..."); r = install_runtime(paths, subs); print(f"         {r['message']}")
        print("  [2/4] Memory..."); r = install_memory(paths); print(f"         {r['message']}")
        print("  [3/4] CLAUDE.md..."); r = setup_claude_md(paths, subs); print(f"         {r['message']}")
        print("  [4/4] MCP..."); r = register_mcp(paths); print(f"         {r['message']}")
        print("\n  Done! Run --verify to check installation.")
    else:
        interactive_install()


if __name__ == "__main__":
    main()
