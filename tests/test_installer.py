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


def test_memory_install():
    """Test installer/memory.py with a temp directory."""
    from installer.memory import install_memory, check_dependencies, remove_memory

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

        result = install_memory(paths)
        if result["status"] == "success":
            print(f"  [PASS] install_memory succeeded")
            passed += 1
        else:
            print(f"  [FAIL] install_memory failed: {result}")
            failed += 1

        # Check server files exist
        server_dir = Path(paths["memory_root"]) / "server"
        expected = ["main.py", "memory_store.py", "memory_retriever.py",
                    "memory_scorer.py", "evolution_engine.py", "debate_engine.py",
                    "cleanup.py", "repo_detector.py"]
        for f in expected:
            if (server_dir / f).exists():
                print(f"  [PASS] Installed: server/{f}")
                passed += 1
            else:
                print(f"  [FAIL] Missing: server/{f}")
                failed += 1

        # Check index.json created
        index_path = Path(paths["memory_root"]) / "index.json"
        if index_path.exists():
            data = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                print(f"  [PASS] index.json initialized as list")
                passed += 1
            else:
                print(f"  [FAIL] index.json not a list: {type(data)}")
                failed += 1
        else:
            print(f"  [FAIL] index.json not created")
            failed += 1

        # Test removal (keep data)
        result = remove_memory(paths, confirm=False, keep_data=True)
        if not (server_dir / "main.py").exists():
            print(f"  [PASS] Server files removed")
            passed += 1
        else:
            print(f"  [FAIL] Server files not removed")
            failed += 1

        # index.json should be preserved when keep_data=True
        if index_path.exists():
            print(f"  [PASS] index.json preserved")
            passed += 1
        else:
            print(f"  [FAIL] index.json was deleted")
            failed += 1

    # Dependency check (always runs, may warn)
    deps = check_dependencies()
    if "mcp" in deps and "fastmcp" in deps:
        print(f"  [PASS] check_dependencies returns status for both packages")
        passed += 1
    else:
        print(f"  [FAIL] check_dependencies incomplete: {deps}")
        failed += 1

    print(f"\n  Memory Install: {passed} passed, {failed} failed")
    return failed == 0


def test_wiki_install():
    """Test installer/wiki.py with a temp directory."""
    from installer.wiki import install_wiki, remove_wiki

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

        # Need runtime config to exist for wiki_path injection
        rt_config_dir = Path(paths["runtime_path"]) / "configs"
        rt_config_dir.mkdir(parents=True, exist_ok=True)
        (rt_config_dir / "runtime_config.json").write_text(json.dumps({
            "version": "1.0", "runtime_path": paths["runtime_path"],
            "memory_root": paths["memory_root"], "tools_dirs": [],
            "wiki_path": "", "defaults": {}
        }), encoding="utf-8")

        result = install_wiki(paths)
        if result["status"] == "success":
            print(f"  [PASS] install_wiki succeeded")
            passed += 1
        else:
            print(f"  [FAIL] install_wiki failed: {result}")
            failed += 1

        # Check key files exist
        wiki_dir = Path(paths["wiki_path"])
        for f in ["_hot.md", "index.md", "overview.md"]:
            if (wiki_dir / f).exists():
                print(f"  [PASS] Installed: {f}")
                passed += 1
            else:
                print(f"  [FAIL] Missing: {f}")
                failed += 1

        # Check entities and concepts copied
        if (wiki_dir / "entities").is_dir() and any((wiki_dir / "entities").iterdir()):
            print(f"  [PASS] entities/ has files")
            passed += 1
        else:
            print(f"  [FAIL] entities/ missing or empty")
            failed += 1

        if (wiki_dir / "concepts").is_dir() and any((wiki_dir / "concepts").iterdir()):
            print(f"  [PASS] concepts/ has files")
            passed += 1
        else:
            print(f"  [FAIL] concepts/ missing or empty")
            failed += 1

        # Check runtime_config.json updated with wiki_path
        config = json.loads((rt_config_dir / "runtime_config.json").read_text(encoding="utf-8"))
        if config.get("wiki_path") == paths["wiki_path"]:
            print(f"  [PASS] runtime_config.json wiki_path set")
            passed += 1
        else:
            print(f"  [FAIL] wiki_path not set in config: {config.get('wiki_path')}")
            failed += 1

        # Test removal
        result = remove_wiki(paths, confirm=False)
        if not wiki_dir.exists():
            print(f"  [PASS] remove_wiki cleaned up")
            passed += 1
        else:
            print(f"  [FAIL] remove_wiki did not clean up")
            failed += 1

    print(f"\n  Wiki Install: {passed} passed, {failed} failed")
    return failed == 0


def test_claude_md():
    """Test installer/claude_md.py with temp files."""
    from installer.claude_md import setup_claude_md, remove_claude_md_block

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
        from installer.paths import build_substitutions
        subs = build_substitutions(paths)

        # Test 1: No CLAUDE.md exists — should create from template
        claude_dir = Path(paths["claude_dir"])
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_md = claude_dir / "CLAUDE.md"

        result = setup_claude_md(paths, subs, mode="create")
        if result["status"] == "success" and claude_md.exists():
            print(f"  [PASS] Created CLAUDE.md from template")
            passed += 1
        else:
            print(f"  [FAIL] Create failed: {result}")
            failed += 1

        # Check markers present
        content = claude_md.read_text(encoding="utf-8")
        if "<!-- RUNTIME:START -->" in content and "<!-- RUNTIME:END -->" in content:
            print(f"  [PASS] Has start and end markers")
            passed += 1
        else:
            print(f"  [FAIL] Missing markers")
            failed += 1

        # Check tokens resolved
        if "{{" not in content:
            print(f"  [PASS] All tokens resolved")
            passed += 1
        else:
            print(f"  [FAIL] Unresolved tokens in CLAUDE.md")
            failed += 1

        # Check runtime path present
        if paths["runtime_path"] in content:
            print(f"  [PASS] Runtime path in CLAUDE.md")
            passed += 1
        else:
            print(f"  [FAIL] Runtime path not found in CLAUDE.md")
            failed += 1

        # Test 2: Existing CLAUDE.md with custom content — append
        claude_md.write_text("# My Custom Instructions\n\nDo things my way.\n", encoding="utf-8")
        result = setup_claude_md(paths, subs, mode="append")
        content = claude_md.read_text(encoding="utf-8")
        if "My Custom Instructions" in content and "<!-- RUNTIME:START -->" in content:
            print(f"  [PASS] Appended to existing, preserved custom content")
            passed += 1
        else:
            print(f"  [FAIL] Append failed: custom={('My Custom' in content)}, markers={('RUNTIME:START' in content)}")
            failed += 1

        # Test 3: Remove runtime block
        result = remove_claude_md_block(paths)
        content = claude_md.read_text(encoding="utf-8")
        if "<!-- RUNTIME:START -->" not in content and "My Custom Instructions" in content:
            print(f"  [PASS] Removed runtime block, preserved custom content")
            passed += 1
        else:
            print(f"  [FAIL] Remove failed")
            failed += 1

        # Test 4: Already has markers — update between them
        claude_md.write_text(
            "# My Stuff\n\n<!-- RUNTIME:START -->\nOLD BLOCK\n<!-- RUNTIME:END -->\n\n# More stuff\n",
            encoding="utf-8"
        )
        result = setup_claude_md(paths, subs, mode="update")
        content = claude_md.read_text(encoding="utf-8")
        if "My Stuff" in content and "OLD BLOCK" not in content and "Prompt Architect" in content:
            print(f"  [PASS] Updated between markers, preserved surrounding content")
            passed += 1
        else:
            print(f"  [FAIL] Update between markers failed")
            failed += 1

    print(f"\n  CLAUDE.md: {passed} passed, {failed} failed")
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
    print("\nRunning: memory_install")
    results["memory_install"] = test_memory_install()
    print("\nRunning: wiki_install")
    results["wiki_install"] = test_wiki_install()
    print("\nRunning: claude_md")
    results["claude_md"] = test_claude_md()

    total_pass = sum(1 for v in results.values() if v)
    total_fail = sum(1 for v in results.values() if not v)
    print(f"\nTOTAL: {total_pass} groups passed, {total_fail} groups failed")
    sys.exit(0 if total_fail == 0 else 1)
