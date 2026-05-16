"""Repo-local conversation store: append-only JSONL + lazy reads.

Schema (one event per line in .repo_memory/conversation.jsonl):

    {"kind":"prompt", "ts":..., "session":..., "text":...}
    {"kind":"tool",   "ts":..., "session":..., "name":..., "summary":..., "ok":bool}
    {"kind":"close",  "ts":..., "session":..., "files":[...], "snippet":...}

Sessions are grouped on read by `session` id. The store deliberately does NOT
maintain an index; reads are cheap until the file gets large, at which point a
compactor runs in cli.py. This keeps the write path zero-dependency and
crash-safe.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

MEMORY_DIRNAME = ".repo_memory"
CONVERSATION_FILE = "conversation.jsonl"
SESSION_ENV = "MEISTER_SESSION_ID"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def find_repo_root(start: str | None = None) -> Path:
    """Walk up from `start` (cwd default) until we find a .git or a .repo_memory.

    Falls back to the start directory if neither is found, so a non-git folder
    still works on first use.
    """
    cur = Path(start or os.getcwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists() or (candidate / MEMORY_DIRNAME).exists():
            return candidate
    return cur


def memory_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / MEMORY_DIRNAME


def ensure_memory_dir(repo_root: Path | None = None) -> Path:
    d = memory_dir(repo_root)
    d.mkdir(exist_ok=True)
    (d / CONVERSATION_FILE).touch(exist_ok=True)
    return d


def session_id(payload_session: str | None = None) -> str:
    """Resolve the session id for an event, in priority order:
      1. the hook payload's `session_id` (Claude Code, Cursor MCP, etc. all send one)
      2. MEISTER_SESSION_ID env var (manual override)
      3. a fresh id (only happens outside a real hook context — e.g. CLI tests)
    """
    if payload_session:
        return str(payload_session)[:64]
    sid = os.environ.get(SESSION_ENV)
    if sid:
        return sid
    return f"s_{int(time.time())}_{uuid.uuid4().hex[:6]}"


def append(event: dict, repo_root: Path | None = None) -> None:
    """Append one event to the conversation log. Crash-safe (single write call)."""
    d = ensure_memory_dir(repo_root)
    path = d / CONVERSATION_FILE
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def read_events(repo_root: Path | None = None) -> list[dict]:
    """Read all events. Skips malformed lines silently — the log keeps growing
    even if one hook invocation got corrupted, and we don't want recall to die.
    """
    path = memory_dir(repo_root) / CONVERSATION_FILE
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def group_by_session(events: Iterable[dict]) -> dict[str, list[dict]]:
    sessions: dict[str, list[dict]] = {}
    for ev in events:
        sid = ev.get("session") or "unknown"
        sessions.setdefault(sid, []).append(ev)
    return sessions


def summarize_session(session_events: list[dict]) -> dict:
    """Compress one session's events into a one-line title + small bag of facts.

    This is the L0 row for layered retrieval.
    """
    ts_first = min((e.get("ts", "") for e in session_events if e.get("ts")), default="")
    ts_last = max((e.get("ts", "") for e in session_events if e.get("ts")), default="")
    prompts = [e.get("text", "") for e in session_events if e.get("kind") == "prompt"]
    tools = [e for e in session_events if e.get("kind") == "tool"]
    closes = [e for e in session_events if e.get("kind") == "close"]

    files: set[str] = set()
    for e in tools + closes:
        for f in e.get("files", []) or []:
            files.add(f)
        s = e.get("summary") or ""
        # If summary looks like "path L1-50", grab the path.
        m = re.match(r"([\w./\\-]+)", s)
        if m and ("/" in m.group(1) or "\\" in m.group(1) or "." in m.group(1)):
            files.add(m.group(1))

    title = prompts[0][:120] if prompts else (
        closes[-1].get("snippet", "")[:120] if closes else "(no prompt captured)"
    )
    tool_counts: dict[str, int] = {}
    for t in tools:
        n = t.get("name", "?")
        tool_counts[n] = tool_counts.get(n, 0) + 1

    return {
        "session": session_events[0].get("session", "unknown"),
        "ts_first": ts_first,
        "ts_last": ts_last,
        "title": title.replace("\n", " ").strip(),
        "prompt_count": len(prompts),
        "tool_counts": tool_counts,
        "files": sorted(files)[:10],
        "event_count": len(session_events),
    }


def safe_summary(s: str, limit: int = 80) -> str:
    """Trim a string for log records — strip secrets-ish patterns and clip length."""
    if not s:
        return ""
    s = re.sub(r"(api[_-]?key|token|secret|password)\s*[:=]\s*\S+", r"\1=<redacted>", s, flags=re.I)
    s = s.replace("\n", " ").strip()
    return s[:limit]
