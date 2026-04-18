"""Store, compress, and index memory entries."""

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from repo_detector import MEMORY_ROOT, ensure_repo_dirs, ensure_local_memory
from memory_scorer import estimate_tokens

INDEX_PATH = MEMORY_ROOT / "index.json"

FILLER_WORDS = {
    "just", "really", "very", "quite", "basically", "actually", "simply",
    "obviously", "clearly", "literally", "definitely", "probably", "maybe",
    "certainly", "essentially", "furthermore", "moreover", "however",
    "nevertheless", "accordingly", "consequently", "in order to",
}

VALID_TYPES = {"session", "decision", "pattern", "structure", "outcome"}

# Map singular type to plural directory name
TYPE_TO_DIR = {
    "session": "sessions",
    "decision": "decisions",
    "pattern": "patterns",
    "structure": "structure",
    "outcome": "outcomes",
}


def compress_content(text: str, max_tokens: int = 200) -> str:
    """Rule-based compression: strip filler, trim to token budget."""
    # Remove filler words
    words = text.split()
    filtered = []
    for w in words:
        if w.lower().strip(".,!?;:") not in FILLER_WORDS:
            filtered.append(w)
    text = " ".join(filtered)

    # Remove redundant whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Trim to token budget
    current_tokens = estimate_tokens(text)
    if current_tokens > max_tokens:
        words = text.split()
        target_words = int(max_tokens / 1.3)
        text = " ".join(words[:target_words]) + "..."

    return text


def _load_index() -> list:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_index(index: list):
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")


def _normalize_for_hash(text: str) -> str:
    """Lowercase + collapse whitespace so trivial variants hash identically."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _content_hash(content: str) -> str:
    return hashlib.sha256(_normalize_for_hash(content).encode("utf-8")).hexdigest()


def _find_duplicate(index: list, repo: str, entry_type: str, content_hash: str) -> dict | None:
    """Return the matching index record, or None. Same repo + type + hash required."""
    for record in index:
        if (
            record.get("repo") == repo
            and record.get("type") == entry_type
            and record.get("content_hash") == content_hash
        ):
            return record
    return None


def _validate_inputs(repo: str, entry_type: str, content: str, tags):
    """Fast-fail validation so malformed calls never create garbage entries."""
    if entry_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {entry_type}. Must be one of {VALID_TYPES}")
    if not isinstance(repo, str) or not repo.strip():
        raise ValueError("repo must be a non-empty string")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("content must be a non-empty string")
    if tags is not None and not isinstance(tags, list):
        raise ValueError("tags must be a list of strings or None")
    if tags and not all(isinstance(t, str) for t in tags):
        raise ValueError("tags must contain only strings")


def _bump_existing_entry(record: dict, working_dir: str = None) -> dict:
    """Increment frequency and refresh last_used on an existing entry; return it."""
    entry_path = Path(record["path"])
    if not entry_path.exists():
        return None
    try:
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    now = datetime.now(timezone.utc).isoformat()
    entry["frequency"] = int(entry.get("frequency", 1)) + 1
    entry["last_used"] = now
    entry_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    _update_local_memory(entry["repo"], entry, working_dir)
    return entry


def store_entry(
    repo: str,
    entry_type: str,
    content: str,
    tags: list[str] = None,
    outcome: dict = None,
    working_dir: str = None,
) -> dict:
    """
    Compress and store a memory entry.

    Returns the stored entry dict.
    """
    _validate_inputs(repo, entry_type, content, tags)

    # Ensure directories
    repo_path = ensure_repo_dirs(repo)

    # Compress
    compressed = compress_content(content)
    if not compressed.strip():
        raise ValueError("content is empty after compression (all filler words)")

    # Dedup: outcomes are event records (each one matters); everything else is knowledge
    # and duplicates should be merged into the existing entry.
    index = _load_index()
    hash_value = _content_hash(compressed)
    if entry_type != "outcome":
        duplicate = _find_duplicate(index, repo, entry_type, hash_value)
        if duplicate:
            bumped = _bump_existing_entry(duplicate, working_dir)
            if bumped:
                return bumped
            # If the referenced file vanished, fall through and create fresh.

    # Build entry
    now = datetime.now(timezone.utc).isoformat()
    entry_id = str(uuid.uuid4())
    entry = {
        "id": entry_id,
        "type": entry_type,
        "repo": repo,
        "content": compressed,
        "content_hash": hash_value,
        "tags": tags or [],
        "created": now,
        "last_used": now,
        "relevance_score": 50,
        "frequency": 1,
        "decay_factor": 0.0,
        "success_rate": None,
        "confidence_weight": 1.0,
    }

    # Write entry file
    entry_dir = repo_path / TYPE_TO_DIR.get(entry_type, entry_type)
    if entry_type != "outcome":
        entry_path = entry_dir / f"{entry_id}.json"
        entry_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    # Handle outcome separately
    if outcome and entry_type == "outcome":
        outcome_record = {
            "id": entry_id,
            "decision_id": outcome.get("decision_id", ""),
            "expected_result": outcome.get("expected_result", ""),
            "actual_result": outcome.get("actual_result", ""),
            "success": outcome.get("success", True),
            "error_analysis": outcome.get("error_analysis", ""),
            "improvement_signal": outcome.get("improvement_signal", ""),
            "timestamp": now,
        }
        outcome_path = repo_path / "outcomes" / f"{entry_id}.json"
        outcome_path.write_text(json.dumps(outcome_record, indent=2), encoding="utf-8")
        entry["outcome"] = outcome_record
    elif outcome and entry_type != "outcome":
        # Store companion outcome alongside a decision
        outcome_id = str(uuid.uuid4())
        outcome_record = {
            "id": outcome_id,
            "decision_id": entry_id,
            "expected_result": outcome.get("expected_result", ""),
            "actual_result": outcome.get("actual_result", ""),
            "success": outcome.get("success", True),
            "error_analysis": outcome.get("error_analysis", ""),
            "improvement_signal": outcome.get("improvement_signal", ""),
            "timestamp": now,
        }
        outcome_path = repo_path / "outcomes" / f"{outcome_id}.json"
        outcome_path.write_text(json.dumps(outcome_record, indent=2), encoding="utf-8")

    # Update global index (reuse `index` loaded above for the dedup scan)
    index.append({
        "id": entry_id,
        "type": entry_type,
        "repo": repo,
        "tags": tags or [],
        "created": now,
        "path": str(entry_dir / f"{entry_id}.json"),
        "content_hash": hash_value,
    })
    _save_index(index)

    # Update local repo memory
    _update_local_memory(repo, entry, working_dir)

    return entry


def _update_local_memory(repo: str, entry: dict, working_dir: str = None):
    """Update .repo_memory/hot.md and recent_sessions.json."""
    local_path = ensure_local_memory(working_dir)

    # Update hot.md with latest entry summary
    hot_md = local_path / "hot.md"
    lines = [
        f"# Active Context — {repo}\n",
        f"\n**Last updated:** {entry['created']}\n",
        f"\n## Latest ({entry['type']})\n",
        f"\n{entry['content']}\n",
    ]

    # Preserve existing entries but cap at ~100 tokens
    existing = ""
    if hot_md.exists():
        existing = hot_md.read_text(encoding="utf-8")
        # Extract previous entries section if it exists
        prev_marker = "\n## Previous\n"
        if prev_marker in existing:
            prev_section = existing.split(prev_marker)[1]
            prev_tokens = estimate_tokens(prev_section)
            if prev_tokens < 60:
                lines.append(f"{prev_marker}{prev_section}")

    lines.append(f"\n## Previous\n\n{entry['type']}: {entry['content'][:80]}...\n")
    hot_md.write_text("".join(lines), encoding="utf-8")

    # Update recent_sessions.json (keep last 5)
    recent_path = local_path / "recent_sessions.json"
    try:
        recent = json.loads(recent_path.read_text(encoding="utf-8"))
    except Exception:
        recent = []

    recent.insert(0, {
        "id": entry["id"],
        "type": entry["type"],
        "summary": entry["content"][:150],
        "timestamp": entry["created"],
    })
    recent = recent[:5]
    recent_path.write_text(json.dumps(recent, indent=2), encoding="utf-8")

    # Update local_index.json
    local_index_path = local_path / "local_index.json"
    try:
        local_index = json.loads(local_index_path.read_text(encoding="utf-8"))
    except Exception:
        local_index = []
    local_index.append(entry["id"])
    local_index = local_index[-50:]  # Keep last 50 pointers
    local_index_path.write_text(json.dumps(local_index, indent=2), encoding="utf-8")
