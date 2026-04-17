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


def test_runtime_install():
    """Test installer/runtime.py with a temp directory as target."""
    from installer.paths import build_substitutions
    from installer.runtime import install_runtime, remove_runtime

    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_home = tmpdir.replace("\\", "/")
        paths = {
            "home": tmp_home,
            "runtime_path": f"{tmp_home}/.claude_runtime",
            "memory_root": f"{tmp_home}/.claude_memory",
            "claude_dir": f"{tmp_home}/.claude",
            "wiki_path": f"{tmp_home}/.claude_wiki",
            "repo_root": str(Path(__file__).parent.parent).replace("\\", "/"),
        }
        subs = build_substitutions(paths)

        # Install
        result = install_runtime(paths, subs)
        if result["status"] == "success":
            print(f"  [PASS] install_runtime succeeded")
            passed += 1
        else:
            print(f"  [FAIL] install_runtime failed: {result}")
            failed += 1

        # Check core files exist
        runtime_dir = Path(paths["runtime_path"])
        expected_files = [
            "core/context_router.md",
            "core/mode_selector.md",
            "core/skill_router.md",
            "core/token_budget.md",
            "controllers/tool_loader.py",
            "controllers/memory_controller.py",
            "controllers/mcp_router.py",
            "controllers/usage_logger.py",
            "configs/runtime_config.json",
            "hooks/runtime_bootstrap.md",
            "hooks/pre_execution.md",
        ]
        for f in expected_files:
            if (runtime_dir / f).exists():
                print(f"  [PASS] Installed: {f}")
                passed += 1
            else:
                print(f"  [FAIL] Missing: {f}")
                failed += 1

        # Check templating worked (no {{TOKENS}} remain)
        config = json.loads((runtime_dir / "configs/runtime_config.json").read_text(encoding="utf-8"))
        if "{{" not in config.get("runtime_path", ""):
            print(f"  [PASS] Config paths resolved: {config['runtime_path']}")
            passed += 1
        else:
            print(f"  [FAIL] Config still has tokens: {config['runtime_path']}")
            failed += 1

        # Check templating ran on context_router (no unreplaced tokens)
        router_content = (runtime_dir / "core/context_router.md").read_text(encoding="utf-8")
        if "{{RUNTIME_PATH}}" not in router_content and "{{WIKI_PATH}}" not in router_content:
            print(f"  [PASS] context_router tokens resolved")
            passed += 1
        else:
            print(f"  [FAIL] context_router still has unresolved tokens")
            failed += 1

        # Check logs initialized
        usage_log = runtime_dir / "logs" / "runtime_usage.json"
        if usage_log.exists():
            data = json.loads(usage_log.read_text(encoding="utf-8"))
            if data == []:
                print(f"  [PASS] Usage log initialized as empty array")
                passed += 1
            else:
                print(f"  [FAIL] Usage log not empty: {data}")
                failed += 1
        else:
            print(f"  [FAIL] Usage log not created")
            failed += 1

        # Test removal
        result = remove_runtime(paths, confirm=False)
        if not runtime_dir.exists():
            print(f"  [PASS] remove_runtime cleaned up")
            passed += 1
        else:
            print(f"  [FAIL] remove_runtime did not clean up")
            failed += 1

    print(f"\n  Runtime Install: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("  CLAUDE_MEISTER INSTALLER TESTS")
    print("=" * 60)

    results = {}
    print("\nRunning: paths")
    results["paths"] = test_paths()
    print("\nRunning: runtime_install")
    results["runtime_install"] = test_runtime_install()

    total_pass = sum(1 for v in results.values() if v)
    total_fail = sum(1 for v in results.values() if not v)
    print(f"\nTOTAL: {total_pass} groups passed, {total_fail} groups failed")
    sys.exit(0 if total_fail == 0 else 1)
