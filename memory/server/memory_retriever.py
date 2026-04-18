"""Hybrid retrieval: local cache + global search + TF-IDF ranking."""

import json
import math
import os
from collections import Counter
from pathlib import Path

from repo_detector import MEMORY_ROOT, ensure_local_memory
from memory_scorer import composite_score, record_access, estimate_tokens, compute_tier
from intent_classifier import classify_intent
from failure_registry import find_similar_failures, summarize_for_avoidance

INDEX_PATH = MEMORY_ROOT / "index.json"
GLOBAL_PATTERNS_DIR = MEMORY_ROOT / "global_patterns"

INTENT_MATCH_BOOST = 1.15  # Multiplicative bump when query and entry share a non-general intent

# Tier priority multipliers applied on top of composite_score.
# Hot entries float to the top, warm stays neutral, cold is heavily deprioritized
# but still eligible when the query strongly matches (high relevance_score wins).
TIER_MULTIPLIER = {"hot": 1.25, "warm": 1.0, "cold": 0.5}
COLD_TIER_MIN_RELEVANCE = 40.0  # Cold entries only included if TF-IDF/tag score clears this


def _load_index() -> list:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_entry(path: str) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _tfidf_score(query: str, content: str) -> float:
    """Simple TF-IDF relevance between query and content."""
    if not query or not content:
        return 0.0

    query_terms = query.lower().split()
    content_lower = content.lower()
    content_words = content_lower.split()

    if not content_words:
        return 0.0

    content_counts = Counter(content_words)
    total_words = len(content_words)

    score = 0.0
    for term in query_terms:
        tf = content_counts.get(term, 0) / total_words
        # IDF approximation: boost rarer terms
        idf = math.log(1 + 1.0 / (1 + content_counts.get(term, 0)))
        score += tf * idf

    # Normalize to 0-100
    if query_terms:
        score = min(100.0, (score / len(query_terms)) * 1000)

    return score


def _tag_match_score(query: str, tags: list[str]) -> float:
    """Score based on query term overlap with tags."""
    if not tags:
        return 0.0
    query_terms = set(query.lower().split())
    tag_terms = set(t.lower() for t in tags)
    overlap = len(query_terms & tag_terms)
    if not query_terms:
        return 0.0
    return (overlap / len(query_terms)) * 100.0


def retrieve(
    query: str,
    repo: str,
    context_type: str = "all",
    max_tokens: int = 500,
    working_dir: str = None,
) -> dict:
    """
    Retrieve relevant memory entries using hybrid search.

    Flow:
    1. Load local hot.md + recent_sessions.json
    2. Keyword match against index tags
    3. TF-IDF score against content
    4. Check global_patterns/
    5. Rank, merge, deduplicate, enforce token cap
    """
    results = []
    sources = []
    used_tokens = 0

    # Classify query intent once — used to boost entries with matching intent.
    query_intent = classify_intent(query)

    # --- Layer 1: Local repo cache ---
    local_path = ensure_local_memory(working_dir)

    # hot.md (always load)
    hot_md = local_path / "hot.md"
    hot_content = ""
    if hot_md.exists():
        hot_content = hot_md.read_text(encoding="utf-8")
        hot_tokens = estimate_tokens(hot_content)
        if hot_tokens > 100:
            words = hot_content.split()[:77]  # ~100 tokens
            hot_content = " ".join(words) + "..."
            hot_tokens = 100
        used_tokens += hot_tokens
        sources.append("local:hot.md")

    # recent_sessions.json
    recent_path = local_path / "recent_sessions.json"
    recent_entries = []
    if recent_path.exists():
        try:
            recent_entries = json.loads(recent_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    recent_text = ""
    for r in recent_entries[:3]:
        summary = r.get("summary", "")
        recent_text += f"[{r.get('type', '')}] {summary}\n"

    recent_tokens = estimate_tokens(recent_text)
    if recent_tokens > 100:
        words = recent_text.split()[:77]
        recent_text = " ".join(words) + "..."
        recent_tokens = 100
    used_tokens += recent_tokens
    if recent_text:
        sources.append("local:recent_sessions")

    # Check if local context is sufficient (simple heuristic: if query terms appear in local data)
    local_combined = hot_content + " " + recent_text
    local_relevance = _tfidf_score(query, local_combined)
    remaining_budget = max_tokens - used_tokens

    # --- Layer 2: Global memory search ---
    global_entries = []
    if remaining_budget > 50 and local_relevance < 60:
        index = _load_index()

        # Filter by repo and optionally by type
        candidates = []
        for idx_entry in index:
            if idx_entry.get("repo") != repo:
                continue
            if context_type != "all" and idx_entry.get("type") != context_type:
                continue
            candidates.append(idx_entry)

        # Score candidates
        scored = []
        for idx_entry in candidates:
            entry = _load_entry(idx_entry.get("path", ""))
            if entry is None:
                continue

            # Combined relevance: TF-IDF on content + tag matching
            tfidf = _tfidf_score(query, entry.get("content", ""))
            tag_score = _tag_match_score(query, entry.get("tags", []))
            relevance = min(100, tfidf * 0.7 + tag_score * 0.3)
            entry["relevance_score"] = relevance

            # Lazy intent backfill: classify from content once, persist on first access.
            entry_intent = entry.get("intent")
            if not entry_intent:
                entry_intent = classify_intent(entry.get("content", ""))
                entry["intent"] = entry_intent

            # Lazy tier backfill: compute from age/freq if missing, persist.
            tier = entry.get("tier")
            if tier not in ("hot", "warm", "cold"):
                tier = compute_tier(entry)
                entry["tier"] = tier

            # Cold entries only make it through if the query actually matches them.
            if tier == "cold" and relevance < COLD_TIER_MIN_RELEVANCE:
                continue

            score = composite_score(entry)
            if (
                query_intent != "general"
                and entry_intent == query_intent
            ):
                score *= INTENT_MATCH_BOOST
            score *= TIER_MULTIPLIER.get(tier, 1.0)
            scored.append((score, entry))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Take top entries within token budget
        for score, entry in scored[:10]:
            content = entry.get("content", "")
            entry_tokens = estimate_tokens(content)

            if used_tokens + entry_tokens > max_tokens:
                # Truncate to fit
                avail = max_tokens - used_tokens
                if avail > 20:
                    words = content.split()[:int(avail / 1.3)]
                    content = " ".join(words) + "..."
                    entry_tokens = avail
                else:
                    break

            # Record access
            record_access(entry)
            _save_entry(entry)

            global_entries.append({
                "id": entry["id"],
                "type": entry["type"],
                "content": content,
                "score": round(score, 2),
                "tier": entry.get("tier", "warm"),
            })
            used_tokens += entry_tokens

            if used_tokens >= max_tokens:
                break

        if global_entries:
            sources.append(f"global:{repo}")

    # --- Layer 2b: Cross-repo global patterns ---
    if remaining_budget > 50 and used_tokens < max_tokens - 50:
        global_pattern_entries = _search_global_patterns(query, max_tokens - used_tokens)
        if global_pattern_entries:
            for gp in global_pattern_entries:
                used_tokens += estimate_tokens(gp.get("content", ""))
                global_entries.append(gp)
            sources.append("global:patterns")

    # Build final result
    memories = []
    if hot_content:
        memories.append({"id": "local:hot", "type": "hot_context", "content": hot_content, "score": 100})
    if recent_text:
        memories.append({"id": "local:recent", "type": "recent_sessions", "content": recent_text, "score": 95})
    memories.extend(global_entries)

    # --- Layer 3: Failure pattern registry ---
    avoid = []
    try:
        similar = find_similar_failures(query=query, repo=repo, query_intent=query_intent, limit=3)
        if similar:
            avoid = summarize_for_avoidance(similar)
            sources.append("registry:failures")
    except Exception:
        avoid = []

    return {
        "memories": memories,
        "token_count": used_tokens,
        "sources": sources,
        "avoid": avoid,
    }


def _search_global_patterns(query: str, budget: int) -> list:
    """Search global_patterns/ for cross-repo patterns."""
    results = []
    if not GLOBAL_PATTERNS_DIR.exists():
        return results

    for f in GLOBAL_PATTERNS_DIR.glob("*.json"):
        try:
            pattern = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        content = pattern.get("content", "")
        relevance = _tfidf_score(query, content)
        if relevance < 20:
            continue

        tokens = estimate_tokens(content)
        if tokens > budget:
            continue

        results.append({
            "id": pattern.get("id", f.stem),
            "type": "global_pattern",
            "content": content,
            "score": round(relevance, 2),
        })
        budget -= tokens

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]


TYPE_TO_DIR = {
    "session": "sessions",
    "decision": "decisions",
    "pattern": "patterns",
    "structure": "structure",
    "outcome": "outcomes",
}


def _save_entry(entry: dict):
    """Save an updated entry back to disk."""
    repo = entry.get("repo", "")
    entry_type = entry.get("type", "")
    entry_id = entry.get("id", "")
    if not all([repo, entry_type, entry_id]):
        return

    dir_name = TYPE_TO_DIR.get(entry_type, entry_type)
    path = MEMORY_ROOT / "repos" / repo / dir_name / f"{entry_id}.json"
    if path.exists():
        try:
            path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        except Exception:
            pass
