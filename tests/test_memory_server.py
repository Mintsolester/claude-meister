"""Tests for the memory server (Phase 1.2 onward)."""

import json
import sys
import tempfile
from pathlib import Path

# Add memory server to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "memory" / "server"))


def _sandbox_memory(tmpdir: str):
    """Point repo_detector + memory_store at a temp home so tests don't touch real data."""
    import repo_detector
    import memory_store

    tmp = Path(tmpdir)
    memory_root = tmp / ".claude_memory"
    memory_root.mkdir(parents=True, exist_ok=True)
    (memory_root / "repos").mkdir(exist_ok=True)
    index_path = memory_root / "index.json"
    index_path.write_text("[]", encoding="utf-8")

    repo_detector.MEMORY_ROOT = memory_root
    repo_detector.REPOS_DIR = memory_root / "repos"
    memory_store.INDEX_PATH = index_path
    return memory_store, repo_detector


def test_dedup():
    """Phase 1.2: identical content in the same repo should be merged, not duplicated."""
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_store, _ = _sandbox_memory(tmpdir)
        working_dir = str(Path(tmpdir) / "fake_repo")
        Path(working_dir).mkdir()

        # Case 1: exact duplicate → same entry id, frequency=2
        first = memory_store.store_entry(
            repo="test_repo",
            entry_type="pattern",
            content="Always use forward slashes for paths in configs.",
            tags=["paths"],
            working_dir=working_dir,
        )
        second = memory_store.store_entry(
            repo="test_repo",
            entry_type="pattern",
            content="Always use forward slashes for paths in configs.",
            tags=["paths"],
            working_dir=working_dir,
        )
        if first["id"] == second["id"] and second["frequency"] == 2:
            print(f"  [PASS] Exact duplicate merged: id unchanged, frequency=2")
            passed += 1
        else:
            print(f"  [FAIL] Dedup failed: first_id={first['id']}, second_id={second['id']}, freq={second['frequency']}")
            failed += 1

        # Index has one record, not two
        index = json.loads(memory_store.INDEX_PATH.read_text(encoding="utf-8"))
        pattern_records = [r for r in index if r.get("repo") == "test_repo" and r.get("type") == "pattern"]
        if len(pattern_records) == 1:
            print(f"  [PASS] Index has single pattern record, not duplicate")
            passed += 1
        else:
            print(f"  [FAIL] Expected 1 record, got {len(pattern_records)}")
            failed += 1

        # Case 2: whitespace + case variation should still hash-collide
        third = memory_store.store_entry(
            repo="test_repo",
            entry_type="pattern",
            content="  ALWAYS use  forward   slashes for paths in configs.  ",
            tags=["paths"],
            working_dir=working_dir,
        )
        if third["id"] == first["id"] and third["frequency"] == 3:
            print(f"  [PASS] Whitespace/case variant merged: frequency=3")
            passed += 1
        else:
            print(f"  [FAIL] Variant not deduped: id={third['id']}, freq={third['frequency']}")
            failed += 1

        # Case 3: genuinely different content → new entry
        fourth = memory_store.store_entry(
            repo="test_repo",
            entry_type="pattern",
            content="Compress long docstrings before storing.",
            tags=["docs"],
            working_dir=working_dir,
        )
        if fourth["id"] != first["id"] and fourth["frequency"] == 1:
            print(f"  [PASS] Different content creates new entry")
            passed += 1
        else:
            print(f"  [FAIL] Unique content did not create new entry")
            failed += 1

        # Case 4: same content, different repo → NOT deduped (dedup is per-repo)
        fifth = memory_store.store_entry(
            repo="other_repo",
            entry_type="pattern",
            content="Always use forward slashes for paths in configs.",
            tags=["paths"],
            working_dir=working_dir,
        )
        if fifth["id"] != first["id"] and fifth["frequency"] == 1:
            print(f"  [PASS] Same content in different repo creates separate entry")
            passed += 1
        else:
            print(f"  [FAIL] Cross-repo content was unexpectedly merged")
            failed += 1

        # Case 5: same content, different type → NOT deduped
        sixth = memory_store.store_entry(
            repo="test_repo",
            entry_type="session",
            content="Always use forward slashes for paths in configs.",
            tags=["paths"],
            working_dir=working_dir,
        )
        if sixth["id"] != first["id"] and sixth["frequency"] == 1:
            print(f"  [PASS] Same content, different type creates separate entry")
            passed += 1
        else:
            print(f"  [FAIL] Cross-type content was unexpectedly merged")
            failed += 1

        # Case 6: content_hash field is populated on new entries
        if fourth.get("content_hash") and len(fourth["content_hash"]) == 64:
            print(f"  [PASS] content_hash populated (SHA-256, 64 hex chars)")
            passed += 1
        else:
            print(f"  [FAIL] content_hash missing or malformed: {fourth.get('content_hash')}")
            failed += 1

    print(f"\n  Memory dedup: {passed} passed, {failed} failed")
    return failed == 0


def test_outcomes_not_deduped():
    """Phase 1.2: outcomes are event records — duplicates must be preserved."""
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_store, _ = _sandbox_memory(tmpdir)
        working_dir = str(Path(tmpdir) / "fake_repo")
        Path(working_dir).mkdir()

        first = memory_store.store_entry(
            repo="test_repo",
            entry_type="outcome",
            content="Build succeeded.",
            outcome={
                "decision_id": "d1",
                "expected_result": "green",
                "actual_result": "green",
                "success": True,
            },
            working_dir=working_dir,
        )
        second = memory_store.store_entry(
            repo="test_repo",
            entry_type="outcome",
            content="Build succeeded.",
            outcome={
                "decision_id": "d2",
                "expected_result": "green",
                "actual_result": "green",
                "success": True,
            },
            working_dir=working_dir,
        )

        if first["id"] != second["id"]:
            print(f"  [PASS] Outcomes with identical content are preserved as separate events")
            passed += 1
        else:
            print(f"  [FAIL] Outcomes were unexpectedly deduped: {first['id']} == {second['id']}")
            failed += 1

    print(f"\n  Outcomes not deduped: {passed} passed, {failed} failed")
    return failed == 0


def test_validation():
    """Phase 1.4: malformed inputs must fail fast with clear errors."""
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_store, _ = _sandbox_memory(tmpdir)
        working_dir = str(Path(tmpdir) / "fake_repo")
        Path(working_dir).mkdir()

        def expect_value_error(name, **kwargs):
            nonlocal passed, failed
            try:
                memory_store.store_entry(working_dir=working_dir, **kwargs)
                print(f"  [FAIL] {name}: expected ValueError, got success")
                failed += 1
            except ValueError as e:
                print(f"  [PASS] {name}: ValueError: {e}")
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {name}: expected ValueError, got {type(e).__name__}: {e}")
                failed += 1

        # Empty / whitespace content
        expect_value_error("empty content", repo="r", entry_type="pattern", content="", tags=[])
        expect_value_error("whitespace content", repo="r", entry_type="pattern", content="   \n\t  ", tags=[])

        # All-filler content (non-empty raw, empty after compression)
        expect_value_error(
            "all-filler content",
            repo="r", entry_type="pattern",
            content="just really very quite basically actually simply",
            tags=[],
        )

        # Non-string content
        expect_value_error("None content", repo="r", entry_type="pattern", content=None, tags=[])
        expect_value_error("int content", repo="r", entry_type="pattern", content=123, tags=[])

        # Empty / whitespace repo
        expect_value_error("empty repo", repo="", entry_type="pattern", content="hi", tags=[])
        expect_value_error("whitespace repo", repo="   ", entry_type="pattern", content="hi", tags=[])

        # Non-string repo
        expect_value_error("None repo", repo=None, entry_type="pattern", content="hi", tags=[])

        # Invalid type (existed pre-1.4, regression check)
        expect_value_error("invalid type", repo="r", entry_type="bogus", content="hi", tags=[])

        # Non-list tags
        expect_value_error("string tags", repo="r", entry_type="pattern", content="hi", tags="not-a-list")
        expect_value_error("dict tags", repo="r", entry_type="pattern", content="hi", tags={"a": 1})

        # Non-string tag element
        expect_value_error("int in tags", repo="r", entry_type="pattern", content="hi", tags=["ok", 42])

        # Valid inputs still succeed (sanity check that validation doesn't over-reject)
        try:
            entry = memory_store.store_entry(
                repo="r", entry_type="pattern",
                content="valid content survives compression",
                tags=["ok"],
                working_dir=working_dir,
            )
            if entry.get("id") and entry.get("content"):
                print(f"  [PASS] Valid inputs still succeed")
                passed += 1
            else:
                print(f"  [FAIL] Valid inputs returned unexpected entry: {entry}")
                failed += 1
        except Exception as e:
            print(f"  [FAIL] Valid inputs unexpectedly rejected: {e}")
            failed += 1

        # Valid with tags=None (optional parameter)
        try:
            memory_store.store_entry(
                repo="r", entry_type="session",
                content="another valid entry",
                tags=None,
                working_dir=working_dir,
            )
            print(f"  [PASS] tags=None accepted")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] tags=None rejected: {e}")
            failed += 1

    print(f"\n  Validation: {passed} passed, {failed} failed")
    return failed == 0


def test_legacy_index_without_hash():
    """Existing entries written before dedup shipped won't have content_hash. System must not crash."""
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_store, _ = _sandbox_memory(tmpdir)
        working_dir = str(Path(tmpdir) / "fake_repo")
        Path(working_dir).mkdir()

        # Pre-seed the index with a legacy record (no content_hash field)
        legacy = [{
            "id": "legacy-uuid",
            "type": "pattern",
            "repo": "test_repo",
            "tags": ["legacy"],
            "created": "2026-01-01T00:00:00+00:00",
            "path": str(Path(tmpdir) / ".claude_memory/repos/test_repo/patterns/legacy-uuid.json"),
        }]
        memory_store.INDEX_PATH.write_text(json.dumps(legacy), encoding="utf-8")

        # Should not raise; new entry goes in cleanly
        try:
            new_entry = memory_store.store_entry(
                repo="test_repo",
                entry_type="pattern",
                content="Brand new pattern.",
                tags=["new"],
                working_dir=working_dir,
            )
            if new_entry.get("content_hash"):
                print(f"  [PASS] Legacy index handled without crash; new entry has content_hash")
                passed += 1
            else:
                print(f"  [FAIL] New entry missing content_hash")
                failed += 1
        except Exception as e:
            print(f"  [FAIL] Crashed on legacy index: {e}")
            failed += 1

    print(f"\n  Legacy index compat: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("  CLAUDE_MEISTER MEMORY SERVER TESTS")
    print("=" * 60)

    results = {}
    for name, func in [
        ("dedup", test_dedup),
        ("outcomes_not_deduped", test_outcomes_not_deduped),
        ("validation", test_validation),
        ("legacy_index_compat", test_legacy_index_without_hash),
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
