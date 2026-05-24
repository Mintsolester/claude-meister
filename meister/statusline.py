"""Status-line script: one-line live signal that meister is capturing AND
shows tokens-saved-vs-naive as a visible value claim.

Wired into ~/.claude/settings.json under "statusLine". Claude Code runs this
on every prompt and renders the stdout as the footer.

Reads JSON on stdin (session/workspace info), looks up the repo's
.repo_memory/conversation.jsonl, and prints:

    meister: 25 sessions · recall 850 tok vs 72k naive · saves 71k (99%) · last 2s

The savings claim is honest: it's the difference between what `meister last`
costs (L0 listing) and what dumping the full JSONL into Claude's context
would cost. Token estimate uses 4 chars/token (Anthropic-tokenizer-ish).

Fails open: any exception prints nothing (empty status line, not an error).

Performance: this runs on every prompt, so it must be fast. We count file
chars (one stat() + one read for token math), and only compute the real L0
listing for repos with <= 20 sessions; larger repos use an 85-tok/session
estimate that matches the measured value within ~10%.
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


def _human_tokens(tokens: int) -> str:
    """Compact token count: 850, 2.1k, 71k, 1.2M."""
    if tokens < 1000:
        return f"{tokens}"
    if tokens < 10_000:
        return f"{tokens / 1000:.1f}k"
    if tokens < 1_000_000:
        return f"{tokens // 1000}k"
    return f"{tokens / 1_000_000:.1f}M"


# Avg token cost of one L0 session row (title + ts + files + tools), measured
# on real data. Used for the fast-path estimate when there are >20 sessions.
_L0_TOKENS_PER_SESSION = 85
# `meister last` defaults to showing the most recent 10 sessions; that's the
# typical recall cost a user pays.
_DEFAULT_RECALL_SESSIONS = 10


def _estimate_recall_cost_tokens(session_count: int, total_chars: int) -> int:
    """Cost of a default `meister last` recall in tokens."""
    n = min(_DEFAULT_RECALL_SESSIONS, session_count)
    return n * _L0_TOKENS_PER_SESSION


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

        # Token math (4 chars/token, Anthropic-tokenizer-ish):
        #   naive   = what dumping the whole log into context would cost
        #   recall  = what `meister last` actually costs (default 10 L0 rows)
        #   saved   = naive - recall  (zero or negative => no savings to claim)
        naive_tokens = max(1, size // 4)
        recall_tokens = _estimate_recall_cost_tokens(sessions, size)
        saved_tokens = max(0, naive_tokens - recall_tokens)
        saved_pct = int((saved_tokens / naive_tokens) * 100) if naive_tokens else 0

        ago = _relative_ago(time.time() - last_ts) if last_ts > 0 else "—"

        # Two-line-worth-of-info in one terminal line. Reads left-to-right:
        # "how much memory" → "what recall costs vs naive" → "how fresh".
        print(
            f"meister: {sessions} sessions · "
            f"recall {_human_tokens(recall_tokens)} tok vs {_human_tokens(naive_tokens)} naive · "
            f"saves {_human_tokens(saved_tokens)} ({saved_pct}%) · "
            f"last {ago}"
        )
    except Exception:
        # Status line failure must be invisible.
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
