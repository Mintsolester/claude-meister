"""Memory cleanup: remove stale, low-score, and orphan entries."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from repo_detector import MEMORY_ROOT, REPOS_DIR
from memory_scorer import composite_score

INDEX_PATH = MEMORY_ROOT / "index.json"
CLEANUP_LOG = MEMORY_ROOT / "cleanup_log.json"

SCORE_THRESHOLD = 10
DAYS_THRESHOLD = 90


def _load_json(path: Path) -> list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_cleanup(repo: str = None, dry_run: bool = False) -> dict:
    """
    Remove stale and orphan memory entries.

    Criteria:
    - composite_score < 10
    - Not accessed in > 90 days
    - Orphan references (decision_id pointing to deleted entry)
    """
    now = datetime.now(timezone.utc)
    removed = []
    scanned = 0

    # Determine which repos to clean
    if repo:
        repos_to_clean = [REPOS_DIR / repo] if (REPOS_DIR / repo).exists() else []
    else:
        repos_to_clean = [d for d in REPOS_DIR.iterdir() if d.is_dir()]

    for repo_path in repos_to_clean:
        repo_name = repo_path.name
        for type_dir in ["sessions", "decisions", "patterns", "structure"]:
            dir_path = repo_path / type_dir
            if not dir_path.exists():
                continue

            for entry_file in dir_path.glob("*.json"):
                scanned += 1
                # Capture size up-front: after unlink() the file is gone and
                # any later .stat() call will return 0 (or fail), making the
                # cleanup report claim it freed no space.
                try:
                    file_size = entry_file.stat().st_size
                except OSError:
                    file_size = 0

                try:
                    entry = json.loads(entry_file.read_text(encoding="utf-8"))
                except Exception:
                    # Corrupt file — mark for removal
                    removed.append({
                        "id": entry_file.stem,
                        "repo": repo_name,
                        "type": type_dir,
                        "reason": "corrupt_file",
                        "path": str(entry_file),
                        "size": file_size,
                    })
                    if not dry_run:
                        entry_file.unlink()
                    continue

                # Check score
                score = composite_score(entry)
                if score < SCORE_THRESHOLD:
                    removed.append({
                        "id": entry.get("id", entry_file.stem),
                        "repo": repo_name,
                        "type": type_dir,
                        "reason": f"low_score ({score:.1f})",
                        "path": str(entry_file),
                        "size": file_size,
                    })
                    if not dry_run:
                        entry_file.unlink()
                    continue

                # Check last access age
                last_used = entry.get("last_used", entry.get("created", ""))
                if last_used:
                    try:
                        last = datetime.fromisoformat(last_used)
                        if last.tzinfo is None:
                            last = last.replace(tzinfo=timezone.utc)
                        days_old = (now - last).total_seconds() / 86400
                        if days_old > DAYS_THRESHOLD:
                            removed.append({
                                "id": entry.get("id", entry_file.stem),
                                "repo": repo_name,
                                "type": type_dir,
                                "reason": f"stale ({days_old:.0f} days)",
                                "path": str(entry_file),
                                "size": file_size,
                            })
                            if not dry_run:
                                entry_file.unlink()
                            continue
                    except Exception:
                        pass

        # Check for orphan outcomes (decision_id pointing to deleted decisions)
        outcomes_dir = repo_path / "outcomes"
        if outcomes_dir.exists():
            # Build set of existing decision IDs
            decisions_dir = repo_path / "decisions"
            existing_decisions = set()
            if decisions_dir.exists():
                for f in decisions_dir.glob("*.json"):
                    existing_decisions.add(f.stem)

            for outcome_file in outcomes_dir.glob("*.json"):
                scanned += 1
                try:
                    file_size = outcome_file.stat().st_size
                except OSError:
                    file_size = 0
                try:
                    outcome = json.loads(outcome_file.read_text(encoding="utf-8"))
                    decision_id = outcome.get("decision_id", "")
                    if decision_id and decision_id not in existing_decisions:
                        removed.append({
                            "id": outcome.get("id", outcome_file.stem),
                            "repo": repo_name,
                            "type": "outcome",
                            "reason": f"orphan (decision {decision_id[:8]}... deleted)",
                            "path": str(outcome_file),
                            "size": file_size,
                        })
                        if not dry_run:
                            outcome_file.unlink()
                except Exception:
                    pass

    # Update index (remove entries for deleted files)
    if not dry_run and removed:
        removed_ids = {r["id"] for r in removed}
        index = _load_json(INDEX_PATH)
        index = [e for e in index if e.get("id") not in removed_ids]
        _save_json(INDEX_PATH, index)

    # Sum the sizes captured BEFORE we unlinked each file. We can't stat()
    # them now — they no longer exist (or do, when dry_run=True; in that
    # case the size is still accurate as of the scan).
    freed_bytes = sum(int(r.get("size", 0)) for r in removed)

    # Log cleanup
    log_entry = {
        "timestamp": now.isoformat(),
        "repo": repo or "all",
        "scanned": scanned,
        "removed": len(removed),
        "freed_bytes": freed_bytes,
        "dry_run": dry_run,
    }

    log = _load_json(CLEANUP_LOG)
    log.append(log_entry)
    log = log[-100:]
    _save_json(CLEANUP_LOG, log)

    return {
        "removed": len(removed),
        "scanned": scanned,
        "freed_bytes": freed_bytes,
        "dry_run": dry_run,
        "details": removed,
    }


def run_decay(repo: str = None) -> dict:
    """Apply decay to all entries based on inactivity."""
    from memory_scorer import apply_decay

    now = datetime.now(timezone.utc)
    updated = 0

    if repo:
        repos_to_decay = [REPOS_DIR / repo] if (REPOS_DIR / repo).exists() else []
    else:
        repos_to_decay = [d for d in REPOS_DIR.iterdir() if d.is_dir()]

    for repo_path in repos_to_decay:
        for type_dir in ["sessions", "decisions", "patterns", "structure"]:
            dir_path = repo_path / type_dir
            if not dir_path.exists():
                continue

            for entry_file in dir_path.glob("*.json"):
                try:
                    entry = json.loads(entry_file.read_text(encoding="utf-8"))
                    last_used = entry.get("last_used", entry.get("created", ""))
                    if not last_used:
                        continue

                    last = datetime.fromisoformat(last_used)
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    days = (now - last).total_seconds() / 86400

                    if days > 7:
                        apply_decay(entry, days)
                        entry_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
                        updated += 1
                except Exception:
                    continue

    # Log decay run
    decay_log = MEMORY_ROOT / "decay_log.json"
    log = _load_json(decay_log)
    log.append({
        "timestamp": now.isoformat(),
        "repo": repo or "all",
        "entries_updated": updated,
    })
    log = log[-100:]
    _save_json(decay_log, log)

    return {"entries_updated": updated, "repo": repo or "all"}
