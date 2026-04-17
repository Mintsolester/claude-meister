"""Tests for the Claude_Meister installer."""

import json
import os
import platform
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_paths():
    """Test installer/paths.py functions."""
    from installer.paths import detect_os, get_home, get_paths, build_substitutions

    passed = 0
    failed = 0

    # detect_os returns valid value
    os_name = detect_os()
    if os_name in ("Windows", "macOS", "Linux"):
        print(f"  [PASS] detect_os returns valid: {os_name}")
        passed += 1
    else:
        print(f"  [FAIL] detect_os returned: {os_name}")
        failed += 1

    # get_home returns a string with no backslashes
    home = get_home()
    if "\\" not in home:
        print(f"  [PASS] get_home uses forward slashes: {home}")
        passed += 1
    else:
        print(f"  [FAIL] get_home has backslashes: {home}")
        failed += 1

    # get_home returns existing directory
    if Path(home).exists():
        print(f"  [PASS] get_home path exists")
        passed += 1
    else:
        print(f"  [FAIL] get_home path does not exist: {home}")
        failed += 1

    # get_paths returns dict with required keys
    paths = get_paths()
    required_keys = ["home", "runtime_path", "memory_root", "claude_dir", "wiki_path"]
    for key in required_keys:
        if key in paths:
            print(f"  [PASS] get_paths has key: {key}")
            passed += 1
        else:
            print(f"  [FAIL] get_paths missing key: {key}")
            failed += 1

    # All paths use forward slashes
    for key, val in paths.items():
        if "\\" in str(val):
            print(f"  [FAIL] {key} has backslashes: {val}")
            failed += 1
        else:
            print(f"  [PASS] {key} uses forward slashes")
            passed += 1

    # build_substitutions returns dict with token keys
    subs = build_substitutions(paths)
    required_tokens = ["{{HOME}}", "{{RUNTIME_PATH}}", "{{MEMORY_ROOT}}", "{{CLAUDE_DIR}}"]
    for token in required_tokens:
        if token in subs:
            print(f"  [PASS] substitutions has token: {token}")
            passed += 1
        else:
            print(f"  [FAIL] substitutions missing token: {token}")
            failed += 1

    # Substitution values contain no tokens themselves
    for token, val in subs.items():
        if "{{" in val:
            print(f"  [FAIL] substitution {token} still has unresolved token: {val}")
            failed += 1
        else:
            print(f"  [PASS] {token} fully resolved: {val}")
            passed += 1

    print(f"\n  Paths: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("  CLAUDE_MEISTER INSTALLER TESTS")
    print("=" * 60)

    results = {}
    results["paths"] = test_paths()

    total_pass = sum(1 for v in results.values() if v)
    total_fail = sum(1 for v in results.values() if not v)
    print(f"\nTOTAL: {total_pass} groups passed, {total_fail} groups failed")
    sys.exit(0 if total_fail == 0 else 1)
