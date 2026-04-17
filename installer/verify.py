"""Post-install verification checks."""

import json
import subprocess
import sys
from pathlib import Path


def run_verification(paths: dict, install_mode: str = "full") -> dict:
    """Run comprehensive post-install health checks.

    Args:
        paths: from get_paths()
        install_mode: 'full', 'runtime-only', 'memory-only', 'wiki-only'

    Returns:
        dict with 'checks' (list), 'passed' (int), 'failed' (int), 'ok' (bool)
    """
    checks = []

    # Runtime checks
    if install_mode in ("full", "runtime-only"):
        runtime_dir = Path(paths["runtime_path"])
        checks.append(_check_exists(runtime_dir / "core" / "context_router.md", "context_router.md"))
        checks.append(_check_exists(runtime_dir / "core" / "mode_selector.md", "mode_selector.md"))
        checks.append(_check_exists(runtime_dir / "core" / "skill_router.md", "skill_router.md"))
        checks.append(_check_exists(runtime_dir / "core" / "token_budget.md", "token_budget.md"))
        checks.append(_check_exists(runtime_dir / "controllers" / "tool_loader.py", "tool_loader.py"))
        checks.append(_check_exists(runtime_dir / "controllers" / "memory_controller.py", "memory_controller.py"))
        checks.append(_check_exists(runtime_dir / "controllers" / "mcp_router.py", "mcp_router.py"))
        checks.append(_check_exists(runtime_dir / "controllers" / "usage_logger.py", "usage_logger.py"))

        # Config valid JSON
        config_path = runtime_dir / "configs" / "runtime_config.json"
        checks.append(_check_valid_json(config_path, "runtime_config.json"))

        # Config has required fields
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                required = ["version", "runtime_path", "memory_root", "defaults"]
                missing = [k for k in required if k not in config]
                checks.append({
                    "name": "Config has required fields",
                    "passed": len(missing) == 0,
                    "detail": f"Missing: {missing}" if missing else "All present",
                })
            except Exception:
                pass

        # No unresolved tokens
        checks.append(_check_no_tokens(runtime_dir / "core" / "context_router.md", "context_router tokens"))
        checks.append(_check_no_tokens(config_path, "config tokens"))

        # Usage log initialized
        log_path = runtime_dir / "logs" / "runtime_usage.json"
        checks.append(_check_valid_json(log_path, "runtime_usage.json"))

        # Controllers run without errors
        for controller in ["tool_loader.py", "usage_logger.py"]:
            script = runtime_dir / "controllers" / controller
            checks.append(_check_controller_runs(script, controller))

    # Memory checks
    if install_mode in ("full", "memory-only"):
        memory_dir = Path(paths["memory_root"])
        checks.append(_check_exists(memory_dir / "server" / "main.py", "memory server main.py"))
        checks.append(_check_exists(memory_dir / "server" / "memory_scorer.py", "memory_scorer.py"))
        checks.append(_check_valid_json(memory_dir / "index.json", "memory index.json"))

    # Wiki checks
    if install_mode in ("full", "wiki-only"):
        wiki_dir = Path(paths["wiki_path"])
        checks.append(_check_exists(wiki_dir / "_hot.md", "wiki _hot.md"))
        checks.append(_check_exists(wiki_dir / "index.md", "wiki index.md"))
        checks.append(_check_exists(wiki_dir / "overview.md", "wiki overview.md"))

    # CLAUDE.md checks
    if install_mode == "full":
        claude_md = Path(paths["claude_dir"]) / "CLAUDE.md"
        checks.append(_check_exists(claude_md, "CLAUDE.md"))
        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8")
            checks.append({
                "name": "CLAUDE.md has runtime markers",
                "passed": "<!-- RUNTIME:START -->" in content and "<!-- RUNTIME:END -->" in content,
                "detail": "Markers present" if "<!-- RUNTIME:START -->" in content else "Markers missing",
            })

    passed = sum(1 for c in checks if c["passed"])
    failed = sum(1 for c in checks if not c["passed"])

    return {
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "ok": failed == 0,
    }


def _check_exists(path: Path, name: str) -> dict:
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    return {
        "name": f"{name} exists",
        "passed": exists and size > 0,
        "detail": f"{size} bytes" if exists else "Not found",
        "fix": f"Re-run installer to create {path}" if not exists else None,
    }


def _check_valid_json(path: Path, name: str) -> dict:
    if not path.exists():
        return {"name": f"{name} valid JSON", "passed": False, "detail": "File not found"}
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return {"name": f"{name} valid JSON", "passed": True, "detail": "OK"}
    except json.JSONDecodeError as e:
        return {"name": f"{name} valid JSON", "passed": False, "detail": f"Parse error: {e}",
                "fix": f"Delete {path} and re-run installer"}


def _check_no_tokens(path: Path, name: str) -> dict:
    if not path.exists():
        return {"name": f"{name} resolved", "passed": False, "detail": "File not found"}
    content = path.read_text(encoding="utf-8")
    if "{{" in content and "}}" in content:
        return {"name": f"{name} resolved", "passed": False,
                "detail": "Unresolved {{TOKENS}} found",
                "fix": "Re-run installer to resolve path tokens"}
    return {"name": f"{name} resolved", "passed": True, "detail": "No unresolved tokens"}


def _check_controller_runs(script: Path, name: str) -> dict:
    if not script.exists():
        return {"name": f"{name} runs", "passed": False, "detail": "Script not found"}
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True, timeout=10
        )
        # --help returns 0 for argparse scripts
        return {"name": f"{name} runs", "passed": result.returncode == 0,
                "detail": "OK" if result.returncode == 0 else result.stderr[:100]}
    except Exception as e:
        return {"name": f"{name} runs", "passed": False, "detail": str(e)[:100]}
