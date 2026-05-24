"""Status-line script: one-line live signal that meister is capturing.

Wired into ~/.claude/settings.json under "statusLine". Claude Code runs this
on every prompt and renders the stdout as the footer.

Reads JSON on stdin (session/workspace info), looks up the repo's
.repo_memory/conversation.jsonl, and prints:

    meister: 14 sessions · 67 events · last 2m ago

Fails open: any exception prints nothing (empty status line, not an error).

Performance: this runs on every prompt, so it must be fast. Implementation
counts JSONL lines without parsing JSON — line count == event count.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from . import store


def _relative_ago(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    return f"{int(seconds / 86400)}d ago"


def _human_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_}B"
    if bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.1f}KB"
    return f"{bytes_ / (1024 * 1024):.1f}MB"


def _count_sessions_and_events(path: Path) -> tuple[int, int, float]:
    """Return (sessions, events, last_event_unix_ts). Avoids json.loads per line."""
    if not path.exists():
        return 0, 0, 0.0
    sessions = set()
    events = 0
    last_ts = 0.0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events += 1
                # Cheap field extraction without full JSON parse — just look for
                # `"session":"<id>"` and `"ts":"<iso>"` substrings.
                sidx = line.find('"session":"')
                if sidx >= 0:
                    start = sidx + len('"session":"')
                    end = line.find('"', start)
                    if end > start:
                        sessions.add(line[start:end])
                tidx = line.find('"ts":"')
                if tidx >= 0:
                    start = tidx + len('"ts":"')
                    end = line.find('"', start)
                    if end > start:
                        try:
                            # 2026-05-17T18:42:11+00:00 — strip Z/offset, parse
                            from datetime import datetime, timezone
                            iso = line[start:end]
                            dt = datetime.fromisoformat(iso)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            ts = dt.timestamp()
                            if ts > last_ts:
                                last_ts = ts
                        except Exception:
                            pass
    except Exception:
        return 0, 0, 0.0
    return len(sessions), events, last_ts


def _cwd_from_stdin() -> str | None:
    """Claude Code passes session info on stdin. Extract cwd if present."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    cwd = payload.get("cwd") or payload.get("workspace") or payload.get("project_dir")
    return str(cwd) if cwd else None


def main() -> int:
    try:
        cwd = _cwd_from_stdin() or os.getcwd()
        root = store.find_repo_root(cwd)
        log = root / store.MEMORY_DIRNAME / store.CONVERSATION_FILE

        sessions, events, last_ts = _count_sessions_and_events(log)
        if events == 0:
            print("meister: ready (no captures yet)")
            return 0

        size = log.stat().st_size if log.exists() else 0
        ago = _relative_ago(time.time() - last_ts) if last_ts > 0 else "—"
        print(f"meister: {sessions} sessions · {events} events · {_human_size(size)} · last {ago}")
    except Exception:
        # Status line failure must be invisible.
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
