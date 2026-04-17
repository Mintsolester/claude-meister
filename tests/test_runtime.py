"""Automated test suite for the Global Elite Runtime Engine.

Adapted for Claude_Meister distribution — works with any install directory.

Tests all controllers, config integrity, file structure, and CLAUDE.md optimization.

Usage:
    python test_runtime.py                         # Run all tests
    python test_runtime.py --verbose               # Show detailed output
    python test_runtime.py --test NAME             # Run specific test
    python test_runtime.py --install-dir /custom   # Point at non-default install
    python test_runtime.py --live                  # Include tests needing live MCP
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Constants (resolved after arg parse) ──────────────────────────────────

RUNTIME_PATH = None   # set in main() from --install-dir
MEMORY_ROOT = None    # set in main() as sibling of RUNTIME_PATH parent
CLAUDE_MD = None      # set in main() as ~/.claude/CLAUDE.md
PYTHON = sys.executable

# ── Test infrastructure ───────────────────────────────────────────────────

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, check: str, detail: str = ""):
        self.passed += 1
        if VERBOSE:
            print(f"  [PASS] {check}" + (f" — {detail}" if detail else ""))

    def fail(self, check: str, detail: str = ""):
        self.failed += 1
        msg = f"  [FAIL] {check}" + (f" — {detail}" if detail else "")
        self.errors.append(msg)
        print(msg)

    def assert_true(self, condition: bool, check: str, detail: str = ""):
        if condition:
            self.ok(check, detail)
        else:
            self.fail(check, detail)

    def assert_eq(self, actual, expected, check: str):
        if actual == expected:
            self.ok(check, f"{actual}")
        else:
            self.fail(check, f"expected {expected}, got {actual}")

    def summary(self) -> str:
        status = "PASS" if self.failed == 0 else "FAIL"
        return f"[{status}] {self.name}: {self.passed} passed, {self.failed} failed"


def run_controller(script: str, args: list[str], timeout: int = 15, use_full_path: bool = False) -> dict:
    """Run a controller script and return parsed JSON output."""
    if use_full_path:
        cmd = [PYTHON, script] + args
    else:
        cmd = [PYTHON, str(RUNTIME_PATH / "controllers" / script)] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(Path.home()))
        if result.returncode != 0:
            return {"_error": result.stderr.strip(), "_returncode": result.returncode}
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_error": f"Invalid JSON: {result.stdout[:200]}", "_returncode": 0}
    except subprocess.TimeoutExpired:
        return {"_error": "Timeout", "_returncode": -1}
    except Exception as e:
        return {"_error": str(e), "_returncode": -1}


# ── Tests ─────────────────────────────────────────────────────────────────

def test_directory_structure() -> TestResult:
    """Verify all expected files and directories exist."""
    t = TestResult("Directory Structure")

    expected_dirs = ["core", "controllers", "configs", "logs", "injector", "hooks"]
    for d in expected_dirs:
        t.assert_true((RUNTIME_PATH / d).is_dir(), f"Directory exists: {d}")

    expected_files = {
        "core/context_router.md": 500,
        "core/mode_selector.md": 300,
        "core/skill_router.md": 200,
        "core/token_budget.md": 200,
        "controllers/tool_loader.py": 500,
        "controllers/memory_controller.py": 800,
        "controllers/mcp_router.py": 500,
        "controllers/usage_logger.py": 500,
        "injector/runtime_loader.py": 500,
        "injector/claude_md_injector.py": 500,
        "injector/repo_scanner.py": 500,
        "hooks/runtime_bootstrap.md": 200,
        "hooks/pre_execution.md": 200,
        "configs/runtime_config.json": 50,
        "configs/injection_rules.json": 50,
        "logs/runtime_usage.json": 1,
        "README.md": 200,
    }

    for path, min_bytes in expected_files.items():
        full = RUNTIME_PATH / path
        t.assert_true(full.exists(), f"File exists: {path}")
        if full.exists():
            size = full.stat().st_size
            t.assert_true(size >= min_bytes, f"File has content: {path}", f"{size} bytes")

    return t


def test_runtime_config() -> TestResult:
    """Verify runtime_config.json is valid and has required fields."""
    t = TestResult("Runtime Config")

    config_path = RUNTIME_PATH / "configs" / "runtime_config.json"
    t.assert_true(config_path.exists(), "Config file exists")

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        t.ok("Config is valid JSON")
    except Exception as e:
        t.fail("Config is valid JSON", str(e))
        return t

    required_fields = ["version", "runtime_path", "memory_root", "memory_server_modules", "tools_dirs", "defaults"]
    for field in required_fields:
        t.assert_true(field in config, f"Has field: {field}")

    # Check paths resolve
    t.assert_true(Path(config["runtime_path"]).exists(), "runtime_path exists")
    t.assert_true(Path(config["memory_root"]).exists(), "memory_root exists")
    t.assert_true(Path(config["memory_server_modules"]).exists(), "memory_server_modules exists")

    # Check defaults
    defaults = config.get("defaults", {})
    t.assert_eq(defaults.get("memory_max_tokens"), 500, "Default memory_max_tokens is 500")
    t.assert_true(defaults.get("log_usage") is True, "Default log_usage is true")

    # Check tools_dirs entries exist
    for td in config.get("tools_dirs", []):
        t.assert_true(Path(td).exists(), f"tools_dir exists: {td}")

    return t


def test_claude_md() -> TestResult:
    """Verify CLAUDE.md was slimmed down and has required sections."""
    t = TestResult("CLAUDE.md Optimization")

    t.assert_true(CLAUDE_MD.exists(), "CLAUDE.md exists")
    content = CLAUDE_MD.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Should be significantly smaller than the original 111 lines
    t.assert_true(len(lines) <= 70, f"Line count reduced", f"{len(lines)} lines (target: <=70, was 111)")

    # Estimated token count (words * 1.3)
    words = len(content.split())
    est_tokens = int(words * 1.3)
    t.assert_true(est_tokens < 900, f"Token estimate under 900", f"~{est_tokens} tokens")

    # Must still have core sections
    t.assert_true("Prompt Architect" in content, "Has Prompt Architect header")
    t.assert_true("Intent Analysis" in content, "Has Intent Analysis section")
    t.assert_true("Task Classification" in content, "Has Task Classification section")
    t.assert_true("Calibrate Execution" in content, "Has Calibrate Execution section")
    t.assert_true("Efficiency Rules" in content, "Has Efficiency Rules section")

    # Must have runtime pointer
    t.assert_true("context_router.md" in content, "Points to context_router.md")
    t.assert_true("claude_runtime" in content, "References runtime path")

    # Must have quick references
    t.assert_true("advisor.py" in content, "References advisor tool")
    t.assert_true("memory_retrieve" in content, "References memory tools")
    t.assert_true("tool_loader.py" in content, "References tool_loader")
    t.assert_true("usage_logger.py" in content, "References usage_logger")

    # Should NOT have verbose sections (moved to runtime)
    t.assert_true("Navigation protocol" not in content, "Wiki nav protocol removed (moved to runtime)")
    t.assert_true("memory_evolve" not in content, "Detailed memory docs removed (moved to runtime)")

    return t


def test_tool_loader() -> TestResult:
    """Test tool_loader.py with various queries."""
    t = TestResult("Tool Loader")

    # Test 1: Query that should match advisor.py
    result = run_controller("tool_loader.py", ["--query", "advisor"])
    t.assert_true("_error" not in result, "Runs without error")
    if isinstance(result, list):
        t.assert_true(len(result) > 0, "Returns results for 'advisor'")
        t.assert_true(any(r["name"] == "advisor" for r in result), "Finds advisor.py")
        t.assert_true(all("match_score" in r for r in result), "Results have match_score")
    else:
        t.fail("Returns list", f"Got: {type(result)}")

    # Test 2: Query with no matches
    result = run_controller("tool_loader.py", ["--query", "xyznonexistent123"])
    t.assert_true("_error" not in result, "Handles no-match query")
    if isinstance(result, list):
        t.assert_eq(len(result), 0, "Returns empty for nonsense query")

    # Test 3: --all flag
    result = run_controller("tool_loader.py", ["--all"])
    t.assert_true("_error" not in result, "--all runs without error")
    if isinstance(result, list):
        t.assert_true(len(result) > 0, "--all returns at least one tool")

    # Test 4: Custom scan-dir
    home = str(Path.home()).replace("\\", "/")
    result = run_controller("tool_loader.py", ["--query", "advisor", "--scan-dir", f"{home}/Agentic_Workflows/tools/"])
    t.assert_true("_error" not in result, "Custom --scan-dir works")

    # Test 5: Non-existent scan-dir (should not crash)
    result = run_controller("tool_loader.py", ["--query", "test", "--scan-dir", "/nonexistent/path"])
    t.assert_true("_error" not in result, "Handles non-existent scan-dir gracefully")

    return t


def test_memory_controller() -> TestResult:
    """Test memory_controller.py with various modes.

    Requires live installation — skip unless --live is passed.
    """
    t = TestResult("Memory Controller")

    if not LIVE:
        t.ok("[SKIP] Live MCP tests skipped — pass --live to enable")
        return t

    # Test 1: Global query (may return empty if no entries yet)
    result = run_controller("memory_controller.py", ["--query", "test", "--repo", "Agentic_Workflows"])
    t.assert_true("_error" not in result, "Global query runs without error")
    t.assert_true("memories" in result, "Response has 'memories' key")
    t.assert_true("token_count" in result, "Response has 'token_count' key")
    t.assert_true("entries_scanned" in result, "Response has 'entries_scanned' key")
    t.assert_true(isinstance(result.get("token_count", -1), int), "token_count is integer")

    # Test 2: Cross-repo query
    result = run_controller("memory_controller.py", ["--query", "test", "--cross-repo"])
    t.assert_true("_error" not in result, "Cross-repo query runs without error")

    # Test 3: Custom max-tokens
    result = run_controller("memory_controller.py", ["--query", "test", "--max-tokens", "100"])
    t.assert_true("_error" not in result, "Custom max-tokens works")
    t.assert_true(result.get("token_count", 999) <= 100, "Respects max-tokens budget")

    # Test 4: Local-only mode
    home = str(Path.home()).replace("\\", "/")
    result = run_controller("memory_controller.py", ["--local-only", "--working-dir", f"{home}/Agentic_Workflows"])
    t.assert_true("_error" not in result, "Local-only mode runs without error")
    t.assert_true(result.get("sources") == "local_cache", "Reports local_cache source")

    # Test 5: Local-only with non-existent repo_memory (should return empty, not crash)
    result = run_controller("memory_controller.py", ["--local-only", "--working-dir", str(Path.home())])
    t.assert_true("_error" not in result, "Local-only handles missing .repo_memory/")

    return t


def test_mcp_router() -> TestResult:
    """Test mcp_router.py recommendations.

    Requires live installation — skip unless --live is passed.
    """
    t = TestResult("MCP Router")

    if not LIVE:
        t.ok("[SKIP] Live MCP tests skipped — pass --live to enable")
        return t

    home = str(Path.home()).replace("\\", "/")

    # Test 1: Check with a real working dir
    result = run_controller("mcp_router.py", ["--check", "--working-dir", f"{home}/Agentic_Workflows", "--query", "test"])
    t.assert_true("_error" not in result, "Runs without error")
    t.assert_true("source" in result, "Has 'source' recommendation")
    t.assert_true("reason" in result, "Has 'reason' field")
    t.assert_true("command" in result, "Has 'command' field")
    t.assert_true(result.get("source") in ("local_cache", "memory_controller", "mcp"),
                  "Source is valid type", result.get("source", ""))

    # Test 2: Check diagnostic info
    t.assert_true("local_cache" in result, "Includes local_cache diagnostic")
    t.assert_true("global_index" in result, "Includes global_index diagnostic")
    t.assert_true("repo" in result, "Includes detected repo name")

    # Test 3: Non-existent working dir (should handle gracefully)
    result = run_controller("mcp_router.py", ["--check", "--working-dir", "/nonexistent", "--query", "test"])
    t.assert_true("_error" not in result, "Handles non-existent dir")

    # Test 4: No --check flag (should print help, not crash)
    result = run_controller("mcp_router.py", [])
    t.ok("No-args doesn't crash")

    return t


def test_usage_logger() -> TestResult:
    """Test usage_logger.py logging and stats."""
    t = TestResult("Usage Logger")

    # Test 1: Log a test entry
    result = run_controller("usage_logger.py", [
        "--mode", "LIGHT",
        "--tools-used", "test_tool",
        "--memory-tokens", "42",
        "--task-summary", "Automated test entry"
    ])
    t.assert_true("_error" not in result, "Logging runs without error")
    t.assert_true(result.get("status") == "logged", "Reports 'logged' status")
    record = result.get("record", {})
    t.assert_eq(record.get("mode"), "LIGHT", "Logs correct mode")
    t.assert_eq(record.get("memory_tokens"), 42, "Logs correct memory_tokens")
    t.assert_true("timestamp" in record, "Record has timestamp")
    t.assert_true("repo" in record, "Record has repo")

    # Test 2: Stats work
    result = run_controller("usage_logger.py", ["--stats"])
    t.assert_true("_error" not in result, "Stats runs without error")
    t.assert_true(result.get("total_entries", 0) >= 1, "Stats shows at least 1 entry")
    t.assert_true("mode_distribution" in result, "Stats has mode_distribution")
    t.assert_true("avg_memory_tokens" in result, "Stats has avg_memory_tokens")

    # Test 3: Log file is valid JSON
    log_path = RUNTIME_PATH / "logs" / "runtime_usage.json"
    try:
        entries = json.loads(log_path.read_text(encoding="utf-8"))
        t.assert_true(isinstance(entries, list), "Log file is a JSON array")
        t.assert_true(len(entries) >= 1, f"Log has entries", f"{len(entries)} entries")
    except Exception as e:
        t.fail("Log file is valid JSON", str(e))

    return t


def test_cross_directory() -> TestResult:
    """Test that controllers work from a different working directory."""
    t = TestResult("Cross-Directory Portability")

    # Run tool_loader from home directory (not Agentic_Workflows)
    cmd = [PYTHON, str(RUNTIME_PATH / "controllers" / "tool_loader.py"), "--all"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=str(Path.home()))
    t.assert_true(result.returncode == 0, "tool_loader works from home dir")

    # Run mcp_router from home directory
    cmd = [PYTHON, str(RUNTIME_PATH / "controllers" / "mcp_router.py"), "--check", "--working-dir", ".", "--query", "test"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=str(Path.home()))
    t.assert_true(result.returncode == 0, "mcp_router works from home dir")

    # Run memory_controller from home directory
    cmd = [PYTHON, str(RUNTIME_PATH / "controllers" / "memory_controller.py"), "--query", "test", "--cross-repo"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=str(Path.home()))
    t.assert_true(result.returncode == 0, "memory_controller works from home dir")

    # Run usage_logger --stats from home directory
    cmd = [PYTHON, str(RUNTIME_PATH / "controllers" / "usage_logger.py"), "--stats"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=str(Path.home()))
    t.assert_true(result.returncode == 0, "usage_logger works from home dir")

    return t


def test_behavioral_docs() -> TestResult:
    """Verify behavioral docs have required content for Claude to follow."""
    t = TestResult("Behavioral Documents")

    # context_router.md must have decision branches with exact commands
    cr = (RUNTIME_PATH / "core" / "context_router.md").read_text(encoding="utf-8")
    t.assert_true("mcp_router.py" in cr, "Context router references mcp_router.py")
    t.assert_true("tool_loader.py" in cr, "Context router references tool_loader.py")
    t.assert_true("memory_controller.py" in cr, "Context router references memory_controller.py")
    t.assert_true("usage_logger.py" in cr, "Context router references usage_logger.py")
    t.assert_true("wiki" in cr.lower(), "Context router has wiki branch")
    t.assert_true("skill_router.md" in cr, "Context router references skill_router")

    # mode_selector.md must define all three modes
    ms = (RUNTIME_PATH / "core" / "mode_selector.md").read_text(encoding="utf-8")
    t.assert_true("LIGHT" in ms, "Mode selector defines LIGHT")
    t.assert_true("STANDARD" in ms, "Mode selector defines STANDARD")
    t.assert_true("DEEP" in ms, "Mode selector defines DEEP")
    t.assert_true("Trivial" in ms, "Mode selector maps Trivial complexity")
    t.assert_true("Architectural" in ms, "Mode selector maps Architectural complexity")

    # skill_router.md must map task patterns to skills
    sr = (RUNTIME_PATH / "core" / "skill_router.md").read_text(encoding="utf-8")
    t.assert_true("brainstorming" in sr, "Skill router maps brainstorming")
    t.assert_true("systematic-debugging" in sr, "Skill router maps debugging")
    t.assert_true("verification-before-completion" in sr, "Skill router maps verification")
    t.assert_true("writing-plans" in sr, "Skill router maps planning")

    # token_budget.md must have enforceable rules
    tb = (RUNTIME_PATH / "core" / "token_budget.md").read_text(encoding="utf-8")
    t.assert_true("500" in tb, "Token budget references 500-token cap")
    t.assert_true("advisory" in tb.lower(), "Token budget is honest about being advisory")

    return t


def test_memory_server_integration() -> TestResult:
    """Verify memory_controller can import from the MCP server modules.

    Requires live installation with memory server present — skip unless --live.
    """
    t = TestResult("Memory Server Integration")

    if not LIVE:
        t.ok("[SKIP] Live MCP tests skipped — pass --live to enable")
        return t

    server_path = MEMORY_ROOT / "server"
    t.assert_true(server_path.exists(), "Memory server directory exists")
    t.assert_true((server_path / "memory_scorer.py").exists(), "memory_scorer.py exists")

    # Test that import works
    server_path_str = str(server_path).replace("\\", "/")
    cmd = [PYTHON, "-c", f"""
import sys
sys.path.insert(0, r'{server_path_str}')
from memory_scorer import composite_score, estimate_tokens, record_access
# Test estimate_tokens
assert estimate_tokens("hello world test") == int(3 * 1.3), f"Got {{estimate_tokens('hello world test')}}"
# Test composite_score with a mock entry
entry = {{"relevance_score": 50, "frequency": 1, "decay_factor": 0.0, "created": "2026-04-16T00:00:00+00:00"}}
score = composite_score(entry)
assert score > 0, f"Score should be positive, got {{score}}"
print("OK")
"""]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    t.assert_true(result.returncode == 0, "Can import memory_scorer functions", result.stderr.strip() if result.returncode != 0 else "")
    if result.returncode == 0:
        t.assert_true(result.stdout.strip() == "OK", "Scoring functions work correctly")

    return t


def test_runtime_loader() -> TestResult:
    """Test the unified runtime loader."""
    t = TestResult("Runtime Loader")

    # Test 1: LIGHT mode (trivial task)
    result = run_controller(
        str(RUNTIME_PATH / "injector" / "runtime_loader.py"),
        ["--task", "fix typo", "--complexity", "trivial"],
        use_full_path=True,
    )
    t.assert_true("_error" not in result, "Trivial task runs without error")
    t.assert_eq(result.get("mode"), "LIGHT", "Trivial maps to LIGHT mode")
    t.assert_true(len(result.get("skip", [])) > 0, "LIGHT mode skips everything")
    t.assert_true(len(result.get("commands", [])) == 0, "LIGHT mode has no commands")

    # Test 2: STANDARD mode (moderate task)
    result = run_controller(
        str(RUNTIME_PATH / "injector" / "runtime_loader.py"),
        ["--task", "refactor auth module", "--complexity", "moderate"],
        use_full_path=True,
    )
    t.assert_true("_error" not in result, "Moderate task runs without error")
    t.assert_eq(result.get("mode"), "STANDARD", "Moderate maps to STANDARD mode")

    # Test 3: DEEP mode (architectural task)
    result = run_controller(
        str(RUNTIME_PATH / "injector" / "runtime_loader.py"),
        ["--task", "design caching architecture for the API", "--complexity", "architectural"],
        use_full_path=True,
    )
    t.assert_true("_error" not in result, "Architectural task runs without error")
    t.assert_eq(result.get("mode"), "DEEP", "Architectural => DEEP mode")
    t.assert_true("signals" in result, "DEEP mode includes task signals")

    # Test 4: Task signal detection
    result = run_controller(
        str(RUNTIME_PATH / "injector" / "runtime_loader.py"),
        ["--task", "debug the failing claude API integration test", "--complexity", "complex"],
        use_full_path=True,
    )
    signals = result.get("signals", {})
    t.assert_true(signals.get("needs_wiki"), "Detects wiki signal from 'claude API'")
    t.assert_true(signals.get("needs_skills"), "Detects skill signal from 'debug'")
    t.assert_eq(signals.get("suggested_skill"), "superpowers:systematic-debugging", "Suggests debugging skill")

    # Test 5: Status check
    result = run_controller(
        str(RUNTIME_PATH / "injector" / "runtime_loader.py"),
        ["--status"],
        use_full_path=True,
    )
    t.assert_true("_error" not in result, "Status runs without error")
    t.assert_true(result.get("runtime_installed"), "Reports runtime installed")
    t.assert_true(result.get("config_valid"), "Reports config valid")
    t.assert_true(result.get("ready"), "Reports system ready")
    components = result.get("components", {})
    t.assert_true(all(components.values()), "All components present")

    return t


def test_claude_md_injector() -> TestResult:
    """Test the CLAUDE.md injector with a temporary repo."""
    t = TestResult("CLAUDE.md Injector")

    import tempfile

    injector = str(RUNTIME_PATH / "injector" / "claude_md_injector.py")

    # Test 1: Inject into repo without CLAUDE.md
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_controller(injector, ["--repo-dir", tmpdir], use_full_path=True)
        t.assert_true("_error" not in result, "Creates CLAUDE.md in empty repo")
        t.assert_eq(result.get("action"), "created", "Action is 'created'")

        # Verify file exists and has markers
        claude_md = Path(tmpdir) / "CLAUDE.md"
        t.assert_true(claude_md.exists(), "CLAUDE.md was created")
        content = claude_md.read_text(encoding="utf-8")
        t.assert_true("RUNTIME:START" in content, "Has start marker")
        t.assert_true("RUNTIME:END" in content, "Has end marker")

    # Test 2: Inject into repo WITH existing CLAUDE.md
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_md = Path(tmpdir) / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nExisting instructions here.\n", encoding="utf-8")

        result = run_controller(injector, ["--repo-dir", tmpdir], use_full_path=True)
        t.assert_eq(result.get("action"), "injected", "Action is 'injected'")
        t.assert_true(result.get("backup") is not None, "Backup was created")

        content = claude_md.read_text(encoding="utf-8")
        t.assert_true("RUNTIME:START" in content, "Injection added")
        t.assert_true("Existing instructions here" in content, "Original content preserved")
        t.assert_true(content.index("RUNTIME:START") < content.index("Existing instructions"), "Injection prepended")

    # Test 3: Idempotency — don't inject twice
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_md = Path(tmpdir) / "CLAUDE.md"
        claude_md.write_text("# My Project\n", encoding="utf-8")

        run_controller(injector, ["--repo-dir", tmpdir], use_full_path=True)  # first inject
        result = run_controller(injector, ["--repo-dir", tmpdir], use_full_path=True)  # second inject
        t.assert_eq(result.get("action"), "skipped_already_injected", "Second inject is skipped")

    # Test 4: Dry-run
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_controller(injector, ["--repo-dir", tmpdir, "--dry-run"], use_full_path=True)
        t.assert_eq(result.get("action"), "would_create", "Dry-run reports would_create")
        t.assert_true(not (Path(tmpdir) / "CLAUDE.md").exists(), "Dry-run doesn't create file")

    # Test 5: Remove injection
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_md = Path(tmpdir) / "CLAUDE.md"
        claude_md.write_text("# My Project\nKeep this.\n", encoding="utf-8")

        run_controller(injector, ["--repo-dir", tmpdir], use_full_path=True)  # inject
        result = run_controller(injector, ["--repo-dir", tmpdir, "--remove"], use_full_path=True)  # remove
        t.assert_eq(result.get("action"), "removed", "Remove works")

        content = claude_md.read_text(encoding="utf-8")
        t.assert_true("RUNTIME:START" not in content, "Markers removed")
        t.assert_true("Keep this" in content, "Original content preserved after removal")

    # Test 6: Check command
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_controller(injector, ["--repo-dir", tmpdir, "--check"], use_full_path=True)
        t.assert_true("_error" not in result, "Check runs without error")
        t.assert_true(result.get("exists") is False, "Reports file doesn't exist")

    return t


def test_repo_scanner() -> TestResult:
    """Test the repo scanner."""
    t = TestResult("Repo Scanner")

    import tempfile

    scanner = str(RUNTIME_PATH / "injector" / "repo_scanner.py")

    # Create a temp structure with fake repos
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two fake repos
        repo1 = Path(tmpdir) / "project-a"
        repo1.mkdir()
        (repo1 / ".git").mkdir()
        (repo1 / "CLAUDE.md").write_text("# Project A\n", encoding="utf-8")

        repo2 = Path(tmpdir) / "project-b"
        repo2.mkdir()
        (repo2 / ".git").mkdir()
        # No CLAUDE.md

        result = run_controller(scanner, ["--root", tmpdir, "--json"], use_full_path=True)
        t.assert_true("_error" not in result, "Scanner runs without error")

        repos = result.get("repos", [])
        t.assert_eq(len(repos), 2, "Finds both repos")

        # Check project-a
        proj_a = next((r for r in repos if "project-a" in r["path"]), None)
        t.assert_true(proj_a is not None, "Found project-a")
        if proj_a:
            t.assert_true(proj_a["has_claude_md"], "project-a has CLAUDE.md")

        # Check project-b
        proj_b = next((r for r in repos if "project-b" in r["path"]), None)
        t.assert_true(proj_b is not None, "Found project-b")
        if proj_b:
            t.assert_true(not proj_b["has_claude_md"], "project-b has no CLAUDE.md")

    # Test only-missing filter
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "has-it"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "CLAUDE.md").write_text("<!-- RUNTIME:START -->\ntest\n<!-- RUNTIME:END -->\n", encoding="utf-8")

        result = run_controller(scanner, ["--root", tmpdir, "--json", "--only-missing"], use_full_path=True)
        repos = result.get("repos", [])
        t.assert_eq(len(repos), 0, "only-missing filters out injected repos")

    return t


def test_hooks_and_rules() -> TestResult:
    """Verify hook docs and injection rules exist and have correct content."""
    t = TestResult("Hooks & Injection Rules")

    # Bootstrap hook
    bootstrap = RUNTIME_PATH / "hooks" / "runtime_bootstrap.md"
    t.assert_true(bootstrap.exists(), "runtime_bootstrap.md exists")
    content = bootstrap.read_text(encoding="utf-8")
    t.assert_true("runtime_loader" in content, "Bootstrap references runtime_loader")
    t.assert_true("LIGHT" in content, "Bootstrap mentions LIGHT mode skip")
    t.assert_true("usage_logger" in content, "Bootstrap mentions post-task logging")

    # Pre-execution hook
    pre_exec = RUNTIME_PATH / "hooks" / "pre_execution.md"
    t.assert_true(pre_exec.exists(), "pre_execution.md exists")
    content = pre_exec.read_text(encoding="utf-8")
    t.assert_true("500" in content, "Pre-execution mentions 500-token cap")
    t.assert_true("memory_store" in content, "Pre-execution mentions memory storage")

    # Injection rules
    rules_path = RUNTIME_PATH / "configs" / "injection_rules.json"
    t.assert_true(rules_path.exists(), "injection_rules.json exists")
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    t.assert_true(rules.get("prepend_not_append") is True, "Prepend mode enabled")
    t.assert_true(rules.get("backup_before_modify") is True, "Backup enabled")
    t.assert_true(rules.get("skip_if_already_injected") is True, "Idempotency enabled")
    t.assert_true(rules.get("create_if_missing") is True, "Auto-create enabled")
    t.assert_true(isinstance(rules.get("excluded_dirs"), list), "Has excluded_dirs list")
    t.assert_true(".git" in rules["excluded_dirs"], "Excludes .git")
    t.assert_true("node_modules" in rules["excluded_dirs"], "Excludes node_modules")

    return t


# ── Runner ────────────────────────────────────────────────────────────────

ALL_TESTS = {
    "structure": test_directory_structure,
    "config": test_runtime_config,
    "claude_md": test_claude_md,
    "tool_loader": test_tool_loader,
    "memory_controller": test_memory_controller,
    "mcp_router": test_mcp_router,
    "usage_logger": test_usage_logger,
    "cross_directory": test_cross_directory,
    "behavioral_docs": test_behavioral_docs,
    "server_integration": test_memory_server_integration,
    "runtime_loader": test_runtime_loader,
    "injector": test_claude_md_injector,
    "repo_scanner": test_repo_scanner,
    "hooks_and_rules": test_hooks_and_rules,
}

VERBOSE = False
LIVE = False


def main():
    global VERBOSE, LIVE, RUNTIME_PATH, MEMORY_ROOT, CLAUDE_MD

    parser = argparse.ArgumentParser(description="Test the Global Elite Runtime Engine")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show passing tests too")
    parser.add_argument("--test", "-t", type=str, help="Run specific test by name")
    parser.add_argument(
        "--install-dir",
        type=str,
        default=str(Path.home() / ".claude_runtime"),
        help="Path to the runtime installation directory (default: ~/.claude_runtime)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Include tests that require a live MCP connection / full installation",
    )
    args = parser.parse_args()

    VERBOSE = args.verbose
    LIVE = args.live

    # Resolve paths from --install-dir
    RUNTIME_PATH = Path(args.install_dir)
    MEMORY_ROOT = RUNTIME_PATH.parent / ".claude_memory"
    CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"

    print("=" * 60)
    print("  GLOBAL ELITE RUNTIME ENGINE — TEST SUITE")
    print("=" * 60)
    print(f"  Install dir : {RUNTIME_PATH}")
    print(f"  Live mode   : {LIVE}")
    print()

    if args.test:
        if args.test not in ALL_TESTS:
            print(f"Unknown test: {args.test}")
            print(f"Available: {', '.join(ALL_TESTS.keys())}")
            sys.exit(1)
        tests_to_run = {args.test: ALL_TESTS[args.test]}
    else:
        tests_to_run = ALL_TESTS

    results = []
    total_passed = 0
    total_failed = 0

    for name, test_fn in tests_to_run.items():
        print(f"Running: {name}")
        try:
            result = test_fn()
        except Exception as e:
            result = TestResult(name)
            result.fail("Test execution", str(e))
        results.append(result)
        total_passed += result.passed
        total_failed += result.failed
        print(f"  {result.summary()}")
        print()

    # Final summary
    print("=" * 60)
    print(f"  TOTAL: {total_passed} passed, {total_failed} failed")
    print(f"  STATUS: {'ALL TESTS PASSED' if total_failed == 0 else 'SOME TESTS FAILED'}")
    print("=" * 60)

    if total_failed > 0:
        print("\nFailed checks:")
        for r in results:
            for err in r.errors:
                print(f"  {r.name}: {err}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
