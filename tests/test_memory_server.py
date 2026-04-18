"""Tests for the memory server (Phase 1.2 onward)."""

import json
import sys
import tempfile
from pathlib import Path

# Add memory server to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "memory" / "server"))


def _sandbox_memory(tmpdir: str):
    """Point repo_detector + memory_store + memory_retriever at a temp home
    so tests don't touch real data."""
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

    # memory_retriever captures MEMORY_ROOT / INDEX_PATH at import time; patch them.
    import memory_retriever
    memory_retriever.MEMORY_ROOT = memory_root
    memory_retriever.INDEX_PATH = index_path
    memory_retriever.GLOBAL_PATTERNS_DIR = memory_root / "global_patterns"

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


def test_intent_classifier():
    """Phase 2.1: classify_intent buckets common phrasings correctly."""
    from intent_classifier import classify_intent

    passed = 0
    failed = 0

    cases = [
        # (text, expected intent)
        ("why is this function failing?", "debug"),
        ("traceback from the test run", "debug"),
        ("got a stack trace in prod", "debug"),
        ("let's refactor the architecture of this module", "architecture"),
        ("design pattern for the auth layer", "architecture"),
        ("need to decide between postgres and sqlite", "decision"),
        ("rationale for choosing async over threads", "decision"),
        ("implement a helper function for this", "code"),
        ("what's the method signature?", "code"),
        ("hello world", "general"),
        ("", "general"),
        ("   ", "general"),
    ]
    for text, expected in cases:
        got = classify_intent(text)
        if got == expected:
            print(f"  [PASS] {text!r} -> {got}")
            passed += 1
        else:
            print(f"  [FAIL] {text!r} -> {got} (expected {expected})")
            failed += 1

    # Priority: debug wins over code when both appear
    if classify_intent("this function has a bug") == "debug":
        print(f"  [PASS] debug beats code when both trigger (specificity order)")
        passed += 1
    else:
        print(f"  [FAIL] bug+function failed to route to debug")
        failed += 1

    print(f"\n  Intent classifier: {passed} passed, {failed} failed")
    return failed == 0


def test_intent_boost_in_retrieval():
    """Phase 2.1: entries matching the query's intent rank higher."""
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_store, _ = _sandbox_memory(tmpdir)
        import memory_retriever
        memory_retriever.INDEX_PATH = memory_store.INDEX_PATH

        working_dir = str(Path(tmpdir) / "fake_repo")
        Path(working_dir).mkdir()

        # Seed two entries in the same repo, both decent TF-IDF match for a debug query,
        # but only one is tagged as debug-intent.
        debug_entry = memory_store.store_entry(
            repo="r", entry_type="pattern",
            content="When the error traceback mentions circular imports, rename module",
            tags=["imports"],
            working_dir=working_dir,
        )
        code_entry = memory_store.store_entry(
            repo="r", entry_type="pattern",
            content="The import statement should come before any function definition",
            tags=["imports"],
            working_dir=working_dir,
        )

        # Sanity: intents were assigned at write time
        if debug_entry["intent"] == "debug" and code_entry["intent"] == "code":
            print(f"  [PASS] Intent assigned at write time (debug vs code)")
            passed += 1
        else:
            print(f"  [FAIL] Wrong intents: debug={debug_entry['intent']}, code={code_entry['intent']}")
            failed += 1

        # Query with debug intent should rank the debug entry first
        result = memory_retriever.retrieve(
            query="traceback error on import",
            repo="r",
            max_tokens=500,
            working_dir=working_dir,
        )
        global_memories = [m for m in result["memories"] if m["type"] not in ("hot_context", "recent_sessions")]
        if global_memories and global_memories[0]["id"] == debug_entry["id"]:
            print(f"  [PASS] Debug-intent query ranks debug-intent entry first")
            passed += 1
        else:
            order = [m["id"] for m in global_memories]
            print(f"  [FAIL] Expected {debug_entry['id']} first, got order: {order}")
            failed += 1

        # General-intent query should NOT boost either (both ranked by regular scoring only)
        # We verify this indirectly: with no intent match, the ordering depends on
        # TF-IDF, and we don't make claims about which wins — just that no crash happens.
        result2 = memory_retriever.retrieve(
            query="something random",
            repo="r",
            max_tokens=500,
            working_dir=working_dir,
        )
        if isinstance(result2.get("memories"), list):
            print(f"  [PASS] General-intent query returns a valid result without boost")
            passed += 1
        else:
            print(f"  [FAIL] General query broke retrieval: {result2}")
            failed += 1

    print(f"\n  Intent boost: {passed} passed, {failed} failed")
    return failed == 0


def test_intent_lazy_backfill():
    """Legacy entries without 'intent' get backfilled on first retrieval."""
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_store, _ = _sandbox_memory(tmpdir)
        import memory_retriever
        memory_retriever.INDEX_PATH = memory_store.INDEX_PATH

        working_dir = str(Path(tmpdir) / "fake_repo")
        Path(working_dir).mkdir()

        # Write an entry, then strip its intent field to simulate a pre-2.1 entry.
        entry = memory_store.store_entry(
            repo="r", entry_type="pattern",
            content="The error traceback pointed at the wrong module",
            tags=[],
            working_dir=working_dir,
        )
        entry_path = Path(memory_store._load_index()[0]["path"])
        data = json.loads(entry_path.read_text(encoding="utf-8"))
        data.pop("intent", None)
        entry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Retrieve; this should classify and save back.
        memory_retriever.retrieve(
            query="traceback error",
            repo="r",
            max_tokens=500,
            working_dir=working_dir,
        )

        refreshed = json.loads(entry_path.read_text(encoding="utf-8"))
        if refreshed.get("intent") == "debug":
            print(f"  [PASS] Legacy entry backfilled with intent='debug' on retrieval")
            passed += 1
        else:
            print(f"  [FAIL] Backfill did not persist: {refreshed.get('intent')}")
            failed += 1

    print(f"\n  Intent backfill: {passed} passed, {failed} failed")
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
        ("intent_classifier", test_intent_classifier),
        ("intent_boost", test_intent_boost_in_retrieval),
        ("intent_backfill", test_intent_lazy_backfill),
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
