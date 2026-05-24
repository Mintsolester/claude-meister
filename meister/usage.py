"""Usage telemetry — local, file-based, opt-out via MEISTER_NO_USAGE=1.

Every recall, show, last, and auto-inject appends one row to
.repo_memory/usage.jsonl. This file answers a question the user
explicitly asked: "how and when is meister actually being used?"

Schema (one row per invocation):

    {"ts": "...", "kind": "recall|show|last|auto_session|auto_inject",
     "trigger": "cli|session_start|prompt_auto|claude_tool",
     "query": "<text or null>",
     "result_count": int,
     "tokens_saved_est": int}

Kept separate from conversation.jsonl so capture/recall stay clean and the
usage log can be rotated or deleted independently. Never read back into
Claude's context — pure operator-side telemetry.

Why local-only: the project's whole pitch is "no cloud, plaintext, your
machine." Sending usage anywhere would break that. Users who want
aggregated stats run `meister usage` themselves.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import store

USAGE_FILE = "usage.jsonl"
OPT_OUT_ENV = "MEISTER_NO_USAGE"


def _enabled() -> bool:
    return os.environ.get(OPT_OUT_ENV) not in ("1", "true", "yes")


def usage_path(repo_root: Path | None = None) -> Path:
    return store.memory_dir(repo_root) / USAGE_FILE


def log(
    kind: str,
    trigger: str,
    query: str | None = None,
    result_count: int = 0,
    tokens_saved_est: int = 0,
    repo_root: Path | None = None,
) -> None:
    """Append one usage event. Fails open: any exception is swallowed."""
    if not _enabled():
        return
    try:
        store.ensure_memory_dir(repo_root)
        path = usage_path(repo_root)
        row = {
            "ts": store.now_iso(),
            "kind": kind,
            "trigger": trigger,
            "query": (query or "")[:200],
            "result_count": int(result_count),
            "tokens_saved_est": int(tokens_saved_est),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception:
        pass


def read_all(repo_root: Path | None = None) -> list[dict]:
    path = usage_path(repo_root)
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return out
