"""Scoring, decay, and token-counting utilities for memory entries."""

import math
from datetime import datetime, timezone


def estimate_tokens(text: str) -> int:
    """Approximate token count: words * 1.3."""
    if not text:
        return 0
    return int(len(text.split()) * 1.3)


def recency_boost(last_used: str) -> float:
    """Exponential decay based on days since last use. Returns 0-100."""
    try:
        last = datetime.fromisoformat(last_used)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days = max(0, (now - last).total_seconds() / 86400)
        return 100.0 * math.exp(-days / 30.0)
    except Exception:
        return 0.0


def frequency_normalized(frequency: int) -> float:
    """Normalize frequency to 0-100 scale."""
    return min(100.0, frequency * 10.0)


def composite_score(entry: dict) -> float:
    """
    Calculate composite score for a memory entry.

    Score = (relevance*0.4 + recency*0.25 + frequency*0.15 + success*0.2) * (1 - decay)
    """
    relevance = entry.get("relevance_score", 50)
    recency = recency_boost(entry.get("last_used", entry.get("created", "")))
    freq = frequency_normalized(entry.get("frequency", 0))

    sr = entry.get("success_rate")
    success = sr * 100 if sr is not None else 100.0

    decay = entry.get("decay_factor", 0.0)

    raw = (relevance * 0.4 + recency * 0.25 + freq * 0.15 + success * 0.2)
    return raw * (1.0 - min(decay, 1.0))


def apply_decay(entry: dict, days_since_last_access: float) -> dict:
    """
    Apply decay to an entry based on inactivity.
    +0.05 per 7 days unused. High success_rate entries decay 50% slower.
    Returns updated entry (mutates in place).
    """
    weeks = days_since_last_access / 7.0
    sr = entry.get("success_rate")
    rate = 0.05 if sr is None or sr < 0.8 else 0.025
    entry["decay_factor"] = min(1.0, entry.get("decay_factor", 0.0) + weeks * rate)
    return entry


def record_access(entry: dict) -> dict:
    """Mark an entry as accessed: reset decay, bump frequency, update last_used."""
    entry["decay_factor"] = max(0.0, entry.get("decay_factor", 0.0) - 0.1)
    entry["frequency"] = entry.get("frequency", 0) + 1
    entry["last_used"] = datetime.now(timezone.utc).isoformat()
    return entry
