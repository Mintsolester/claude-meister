"""Compact cross-repo registry of failure patterns.

On each unsuccessful outcome, we record a signature (failure_type +
distilled tokens from the error text). When a new task is similar to a
past failure, memory_retrieve surfaces the old note so we don't repeat
the mistake.

Storage: a single JSON file at ~/.claude_memory/failure_registry.json.
Entries are deduplicated by signature — repeats bump `count` and refresh
`last_seen`, keeping the registry compact.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from repo_detector import MEMORY_ROOT

REGISTRY_PATH = MEMORY_ROOT / "failure_registry.json"

# Cap at N entries total — oldest by last_seen evicted first.
MAX_REGISTRY_ENTRIES = 200

# Discard very common English words when extracting signature tokens.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on",
    "at", "by", "for", "with", "from", "is", "was", "were", "are", "be",
    "been", "this", "that", "it", "its", "as", "not", "no", "so", "do",
    "did", "does", "has", "have", "had", "i", "we", "you", "they", "he",
    "she", "will", "would", "could", "should", "can", "may", "might",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}")


def _load_registry() -> list:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_registry(entries: list):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def extract_signature_tokens(text: str, limit: int = 5) -> list[str]:
    """Pick the most informative content tokens from an error-like string.

    Deterministic: same input → same tokens. Stopwords dropped, tokens
    lowercased, unique-preserving order, capped at `limit`.
    """
    if not text:
        return []
    tokens = []
    seen = set()
    for raw in _TOKEN_RE.findall(text.lower()):
        if raw in _STOPWORDS or raw in seen:
            continue
        seen.add(raw)
        tokens.append(raw)
        if len(tokens) >= limit:
            break
    return tokens


def _signature(failure_type: str, tokens: list[str]) -> str:
    """SHA-256 over failure_type + sorted tokens. Short-form (first 16 hex)."""
    payload = failure_type + "|" + "|".join(sorted(tokens))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def register_failure(
    repo: str,
    failure_type: str,
    error_analysis: str,
    note: str = "",
) -> dict:
    """Record or increment a failure pattern. Returns the stored record."""
    tokens = extract_signature_tokens(error_analysis)
    sig = _signature(failure_type or "unknown", tokens)
    now = datetime.now(timezone.utc).isoformat()

    entries = _load_registry()
    for record in entries:
        if record.get("signature") == sig:
            record["count"] = int(record.get("count", 1)) + 1
            record["last_seen"] = now
            # Track repos the pattern has hit without unbounded growth.
            repos_list = record.setdefault("repos", [])
            if repo and repo not in repos_list:
                repos_list.append(repo)
                record["repos"] = repos_list[-10:]
            if note and note not in (record.get("note") or ""):
                # Keep the latest note; older guidance is less useful.
                record["note"] = note
            _save_registry(entries)
            return record

    record = {
        "id": str(uuid.uuid4()),
        "signature": sig,
        "failure_type": failure_type or "unknown",
        "tokens": tokens,
        "repos": [repo] if repo else [],
        "note": note or "",
        "count": 1,
        "first_seen": now,
        "last_seen": now,
    }
    entries.append(record)

    # Cap registry: evict oldest by last_seen first
    if len(entries) > MAX_REGISTRY_ENTRIES:
        entries.sort(key=lambda e: e.get("last_seen", ""), reverse=True)
        entries = entries[:MAX_REGISTRY_ENTRIES]

    _save_registry(entries)
    return record


def _query_tokens(query: str) -> set[str]:
    return {t for t in extract_signature_tokens(query, limit=20)}


def find_similar_failures(
    query: str,
    repo: str | None = None,
    query_intent: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """Return up to `limit` registry entries whose tokens overlap the query.

    Same-repo entries rank first. Ties broken by count (recurrence),
    then by recency of last_seen. Results only include entries with
    at least one token match — no speculative hits.
    """
    entries = _load_registry()
    if not entries:
        return []

    q_tokens = _query_tokens(query)
    if not q_tokens:
        return []

    scored = []
    for record in entries:
        rec_tokens = set(record.get("tokens", []) or [])
        overlap = len(q_tokens & rec_tokens)
        if overlap == 0:
            continue
        same_repo = 1 if (repo and repo in (record.get("repos") or [])) else 0
        same_intent = 1 if (query_intent and query_intent == record.get("failure_type")) else 0
        scored.append((same_repo, overlap, same_intent, record.get("count", 1), record.get("last_seen", ""), record))

    scored.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]), reverse=True)
    return [r[-1] for r in scored[:limit]]


def summarize_for_avoidance(records: list[dict]) -> list[dict]:
    """Shape registry records into the compact 'avoid' form used by memory_retrieve."""
    out = []
    for r in records:
        out.append({
            "signature": r.get("signature"),
            "failure_type": r.get("failure_type"),
            "count": r.get("count", 1),
            "last_seen": r.get("last_seen"),
            "note": r.get("note") or "",
        })
    return out
