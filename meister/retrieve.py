"""Layered retrieval over the conversation log.

L0  one-line session titles (cheapest; ~50 tokens for 10 sessions)
L1  one expanded session: prompts + tool counts + files touched (~300 tokens)
L2  raw events for a session (full fidelity; only on explicit drill-down)

Ranking is plain TF-IDF over the L0 row text. We deliberately avoid embeddings
in the MVP — they add a heavy install footprint and the wedge demo doesn't
need them. The MCP server already has an embedding path for users who want it.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from . import store

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokens(s: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(s or "")]


def _score(query: str, document: str) -> float:
    q = set(_tokens(query))
    if not q:
        return 0.0
    d_tokens = _tokens(document)
    if not d_tokens:
        return 0.0
    d_set = set(d_tokens)
    overlap = q & d_set
    if not overlap:
        return 0.0
    # Simple Jaccard + length-normalized term boost.
    jaccard = len(overlap) / len(q | d_set)
    freq = sum(d_tokens.count(t) for t in overlap) / math.sqrt(len(d_tokens))
    return jaccard + 0.1 * freq


def l0_sessions(repo_root: Path | None = None) -> list[dict]:
    """All sessions, summarized to one row each, newest first."""
    events = store.read_events(repo_root)
    grouped = store.group_by_session(events)
    rows = [store.summarize_session(evs) for evs in grouped.values()]
    rows.sort(key=lambda r: r.get("ts_last", ""), reverse=True)
    return rows


def recall(query: str, repo_root: Path | None = None, top_k: int = 5) -> list[dict]:
    """L0 layer: return top-k sessions matching `query`.

    Empty query returns the most recent sessions (the "last" command's fallback).
    """
    rows = l0_sessions(repo_root)
    if not query.strip():
        return rows[:top_k]
    scored: list[tuple[float, dict]] = []
    for row in rows:
        document = " ".join(
            [
                row.get("title", ""),
                " ".join(row.get("files", [])),
                " ".join(row.get("tool_counts", {}).keys()),
            ]
        )
        s = _score(query, document)
        if s > 0:
            scored.append((s, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:top_k]]


def expand_session(session: str, repo_root: Path | None = None) -> dict[str, Any]:
    """L1 layer: prompts + per-tool summary + files touched for one session."""
    events = store.read_events(repo_root)
    evs = [e for e in events if e.get("session") == session]
    if not evs:
        return {"session": session, "found": False}
    prompts = [e.get("text", "") for e in evs if e.get("kind") == "prompt"]
    tools = [e for e in evs if e.get("kind") == "tool"]
    closes = [e for e in evs if e.get("kind") == "close"]
    files: dict[str, int] = {}
    for e in tools:
        for f in e.get("files", []) or []:
            files[f] = files.get(f, 0) + 1
    return {
        "session": session,
        "found": True,
        "ts_first": min((e.get("ts", "") for e in evs), default=""),
        "ts_last": max((e.get("ts", "") for e in evs), default=""),
        "prompts": prompts,
        "tool_count": len(tools),
        "files": sorted(files.items(), key=lambda kv: -kv[1]),
        "closes": [c.get("snippet", "") for c in closes if c.get("snippet")],
    }


def raw_events(session: str, repo_root: Path | None = None) -> list[dict]:
    """L2 layer: full event stream for a session, in order."""
    events = store.read_events(repo_root)
    return [e for e in events if e.get("session") == session]
