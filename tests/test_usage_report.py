"""Tests for runtime/controllers/usage_report.py (Phase 1.3)."""

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "runtime" / "controllers"))


def _write_log(path: Path, entries: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries), encoding="utf-8")


def _iso(offset_days: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=offset_days)).isoformat()


def test_empty_log():
    """Empty log produces zero-task report, no crash."""
    import usage_report

    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "runtime_usage.json"
        _write_log(log_path, [])

        entries = usage_report.load_entries(log_path)
        stats = usage_report.aggregate(entries)

        if stats["total_tasks"] == 0 and stats["mode_breakdown"] == {}:
            print(f"  [PASS] Empty log aggregates to zero tasks")
            passed += 1
        else:
            print(f"  [FAIL] Unexpected stats for empty log: {stats}")
            failed += 1

        text = usage_report.format_text(stats, None)
        if "No usage data yet" in text:
            print(f"  [PASS] Empty log text output is friendly")
            passed += 1
        else:
            print(f"  [FAIL] Empty log text unexpected: {text!r}")
            failed += 1

    print(f"\n  Empty log: {passed} passed, {failed} failed")
    return failed == 0


def test_aggregate_counts():
    """Mode breakdown, tool counts, memory hit rate, avg tokens per mode."""
    import usage_report

    passed = 0
    failed = 0

    entries = [
        {"timestamp": _iso(0), "mode": "LIGHT", "tools_used": [], "memory_tokens": 0, "repo": "r1"},
        {"timestamp": _iso(0), "mode": "STANDARD", "tools_used": ["tool_loader.py"], "memory_tokens": 200, "repo": "r1"},
        {"timestamp": _iso(0), "mode": "STANDARD", "tools_used": ["tool_loader.py", "advisor.py"], "memory_tokens": 300, "repo": "r1"},
        {"timestamp": _iso(0), "mode": "DEEP", "tools_used": ["advisor.py"], "memory_tokens": 500, "repo": "r2"},
    ]
    stats = usage_report.aggregate(entries)

    # Total
    if stats["total_tasks"] == 4:
        print(f"  [PASS] total_tasks = 4")
        passed += 1
    else:
        print(f"  [FAIL] total_tasks = {stats['total_tasks']}")
        failed += 1

    # Mode breakdown
    if stats["mode_breakdown"] == {"LIGHT": 1, "STANDARD": 2, "DEEP": 1}:
        print(f"  [PASS] mode_breakdown correct")
        passed += 1
    else:
        print(f"  [FAIL] mode_breakdown = {stats['mode_breakdown']}")
        failed += 1

    # Avg tokens per mode
    expected = {"LIGHT": 0.0, "STANDARD": 250.0, "DEEP": 500.0}
    if stats["avg_tokens_per_mode"] == expected:
        print(f"  [PASS] avg_tokens_per_mode correct")
        passed += 1
    else:
        print(f"  [FAIL] avg_tokens_per_mode = {stats['avg_tokens_per_mode']}")
        failed += 1

    # Top tools
    if stats["top_tools"].get("tool_loader.py") == 2 and stats["top_tools"].get("advisor.py") == 2:
        print(f"  [PASS] top_tools counts tools across tasks")
        passed += 1
    else:
        print(f"  [FAIL] top_tools = {stats['top_tools']}")
        failed += 1

    # Memory hit rate: 3 of 4 entries have memory_tokens > 0
    if stats["memory_hit_rate"] == 0.75:
        print(f"  [PASS] memory_hit_rate = 0.75")
        passed += 1
    else:
        print(f"  [FAIL] memory_hit_rate = {stats['memory_hit_rate']}")
        failed += 1

    # Success rate is None (no success field set)
    if stats["success_rate"] is None:
        print(f"  [PASS] success_rate is None when no outcomes finalized")
        passed += 1
    else:
        print(f"  [FAIL] success_rate = {stats['success_rate']}")
        failed += 1

    print(f"\n  Aggregate counts: {passed} passed, {failed} failed")
    return failed == 0


def test_day_window_filter():
    """--days N restricts to entries within the window."""
    import usage_report

    passed = 0
    failed = 0

    entries = [
        {"timestamp": _iso(0), "mode": "LIGHT", "tools_used": [], "memory_tokens": 0},
        {"timestamp": _iso(3), "mode": "STANDARD", "tools_used": [], "memory_tokens": 100},
        {"timestamp": _iso(15), "mode": "DEEP", "tools_used": [], "memory_tokens": 300},
    ]

    # Last 7 days: expect 2 entries (today + 3 days ago)
    within_7 = usage_report.filter_by_window(entries, 7)
    if len(within_7) == 2:
        print(f"  [PASS] --days 7 kept 2 entries")
        passed += 1
    else:
        print(f"  [FAIL] --days 7 kept {len(within_7)}")
        failed += 1

    # Last 1 day: expect only today's entry
    within_1 = usage_report.filter_by_window(entries, 1)
    if len(within_1) == 1:
        print(f"  [PASS] --days 1 kept 1 entry")
        passed += 1
    else:
        print(f"  [FAIL] --days 1 kept {len(within_1)}")
        failed += 1

    # No window: all entries
    all_entries = usage_report.filter_by_window(entries, None)
    if len(all_entries) == 3:
        print(f"  [PASS] No --days returns all")
        passed += 1
    else:
        print(f"  [FAIL] No --days returned {len(all_entries)}")
        failed += 1

    print(f"\n  Day window: {passed} passed, {failed} failed")
    return failed == 0


def test_success_rate_phase23_preview():
    """Once --finalize ships in Phase 2.3, entries will have a success field.
    Verify aggregation handles it correctly now so Phase 2.3 is a drop-in."""
    import usage_report

    passed = 0
    failed = 0

    entries = [
        {"timestamp": _iso(0), "mode": "STANDARD", "tools_used": [], "memory_tokens": 0, "success": True},
        {"timestamp": _iso(0), "mode": "STANDARD", "tools_used": [], "memory_tokens": 0, "success": True},
        {"timestamp": _iso(0), "mode": "STANDARD", "tools_used": [], "memory_tokens": 0, "success": False},
        {"timestamp": _iso(0), "mode": "LIGHT", "tools_used": [], "memory_tokens": 0},  # no success field
    ]
    stats = usage_report.aggregate(entries)

    # 2 of 3 finalized = 0.667
    if stats["success_rate"] == 0.667:
        print(f"  [PASS] success_rate = 0.667 (2 of 3 finalized)")
        passed += 1
    else:
        print(f"  [FAIL] success_rate = {stats['success_rate']}")
        failed += 1

    print(f"\n  Success rate: {passed} passed, {failed} failed")
    return failed == 0


def test_cli_runs():
    """usage_report.py --help must succeed (verify.py check_controller_runs)."""
    import subprocess

    passed = 0
    failed = 0

    script = PROJECT_ROOT / "runtime" / "controllers" / "usage_report.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and "--days" in result.stdout and "--json" in result.stdout:
        print(f"  [PASS] --help exits 0 and documents --days/--json")
        passed += 1
    else:
        print(f"  [FAIL] --help broken: rc={result.returncode}, stdout={result.stdout[:200]}")
        failed += 1

    print(f"\n  CLI: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("  USAGE REPORT TESTS (Phase 1.3)")
    print("=" * 60)

    results = {}
    for name, func in [
        ("empty_log", test_empty_log),
        ("aggregate_counts", test_aggregate_counts),
        ("day_window", test_day_window_filter),
        ("success_rate", test_success_rate_phase23_preview),
        ("cli_help", test_cli_runs),
    ]:
        print(f"\nRunning: {name}")
        results[name] = func()

    total_pass = sum(1 for v in results.values() if v)
    total_fail = sum(1 for v in results.values() if not v)
    print(f"\n{'=' * 60}")
    print(f"  TOTAL: {total_pass} groups passed, {total_fail} groups failed")
    print(f"  STATUS: {'ALL PASSED' if total_fail == 0 else 'SOME FAILED'}")
    print(f"{'=' * 60}")
    sys.exit(0 if total_fail == 0 else 1)
