"""Store, compress, and index memory entries."""

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
    if entry_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {entry_type}. Must be one of {VALID_TYPES}")

    # Ensure directories
    repo_path = ensure_repo_dirs(repo)

    # Compress
    compressed = compress_content(content)

    # Build entry
    now = datetime.now(timezone.utc).isoformat()
    entry_id = str(uuid.uuid4())
    entry = {
        "id": entry_id,
        "type": entry_type,
        "repo": repo,
        "content": compressed,
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

    # Update global index
    index = _load_index()
    index.append({
        "id": entry_id,
        "type": entry_type,
        "repo": repo,
        "tags": tags or [],
        "created": now,
        "path": str(entry_dir / f"{entry_id}.json"),
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
