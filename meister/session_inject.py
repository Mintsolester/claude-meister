"""SessionStart hook: inject recent meister context into Claude's view at the
start of every session.

THIS is the piece that closes the loop. Without it, capture is one-way: events
land in conversation.jsonl but Claude never sees them again. With it, every
new session begins with a brief "here's what you were doing recently" header.

Returns hookSpecificOutput.additionalContext per the Claude Code hook
protocol. Capped at ~500 chars so it never floods the context window.

Fails open: any exception → empty additionalContext (no injection, no harm).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import retrieve, store

MAX_SESSIONS = 5
MAX_CHARS = 800


def _build_context(root: Path) -> str:
    rows = retrieve.l0_sessions(root)
    if not rows:
        return ""

    lines = [f"Recent activity in {root.name} (from meister):"]
    for row in rows[:MAX_SESSIONS]:
        ts = (row.get("ts_last") or "")[:10]
        title = (row.get("title") or "").strip()[:100]
        files = ", ".join((row.get("files") or [])[:3])
        line = f"  [{ts}] {title}"
        if files:
            line += f"  (files: {files})"
        lines.append(line)
    lines.append(
        "Use `meister recall \"<topic>\"` or `meister show <session>` for more detail."
    )

    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 3] + "..."
    return text


def main() -> int:
    try:
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}

        cwd = (
            payload.get("cwd")
            or payload.get("workspace")
            or payload.get("project_dir")
        )
        root = store.find_repo_root(str(cwd) if cwd else None)
        ctx = _build_context(root)
        if not ctx:
            return 0

        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": ctx,
            }
        }
        sys.stdout.write(json.dumps(out))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
