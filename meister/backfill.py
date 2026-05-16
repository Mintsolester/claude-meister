"""Seed `.repo_memory/conversation.jsonl` from git history so the first
`meister last` after install is never empty.

Each commit becomes one synthetic session:

    session id: git_<short-sha>
    prompt    : commit subject (reconstructs "what was I trying to do")
    tool[]    : one Edit event per file changed (capped at FILES_PER_COMMIT)
    close     : commit body (if any)

Every synthesized event carries `source: "git"` so consumers can filter out
the backfill from real captured turns. The function is idempotent — commits
whose `git_<sha>` session is already in the log are skipped.

Merge commits are skipped (--no-merges) because they rarely represent
intentional work and inflate the log with no signal.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import retrieve, store

FILES_PER_COMMIT = 20
DEFAULT_LIMIT = 50

# Stable separator that won't appear in commit content. ASCII unit-separator
# + a label so we can split robustly even if the body itself has newlines.
_SEP = "\x1f---meister-sep---\x1f"
_FORMAT = f"%H%n%aI%n%an%n%s%n%b%n{_SEP}"


def _run_git(args: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return ""
    if r.returncode != 0:
        return ""
    return r.stdout


def _is_git_repo(repo_root: Path) -> bool:
    return (repo_root / ".git").exists()


def _existing_git_sessions(repo_root: Path) -> set[str]:
    sids = set()
    for ev in store.read_events(repo_root):
        sid = ev.get("session") or ""
        if sid.startswith("git_"):
            sids.add(sid)
    return sids


def _files_for_commit(sha: str, cwd: Path) -> list[str]:
    out = _run_git(["show", "--name-only", "--pretty=format:", sha], cwd)
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return files[:FILES_PER_COMMIT]


def _parse_log(raw: str) -> list[dict]:
    """Parse our custom-format `git log` output into commit dicts."""
    commits: list[dict] = []
    for block in raw.split(_SEP):
        block = block.strip("\n")
        if not block:
            continue
        lines = block.split("\n", 4)
        if len(lines) < 4:
            continue
        sha, ts, author, subject = lines[0], lines[1], lines[2], lines[3]
        body = lines[4] if len(lines) > 4 else ""
        commits.append(
            {
                "sha": sha,
                "ts": ts,
                "author": author,
                "subject": subject,
                "body": body.strip(),
            }
        )
    return commits


def _normalize_ts(ts: str) -> str:
    """Git's %aI is already ISO-8601 with timezone, but normalize to UTC."""
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return ts


def from_git(limit: int = DEFAULT_LIMIT, repo_root: Path | None = None) -> dict:
    """Synthesize events from the last `limit` non-merge commits.

    Returns a small summary dict with counts so the CLI can print something
    informative.
    """
    root = repo_root or store.find_repo_root()
    if not _is_git_repo(root):
        return {"ok": False, "reason": "not a git repo", "added_sessions": 0}

    store.ensure_memory_dir(root)
    already = _existing_git_sessions(root)

    raw = _run_git(
        ["log", f"-n{limit}", "--no-merges", f"--pretty=format:{_FORMAT}"],
        root,
    )
    if not raw.strip():
        return {"ok": False, "reason": "no commits found", "added_sessions": 0}

    commits = _parse_log(raw)

    added = 0
    skipped = 0
    oldest_ts = ""
    newest_ts = ""
    for c in commits:
        sid = f"git_{c['sha'][:12]}"
        if sid in already:
            skipped += 1
            continue
        ts = _normalize_ts(c["ts"])
        oldest_ts = ts if not oldest_ts or ts < oldest_ts else oldest_ts
        newest_ts = ts if not newest_ts or ts > newest_ts else newest_ts

        # Reconstruct one session as: prompt + N tool events + close.
        store.append(
            {
                "kind": "prompt",
                "ts": ts,
                "session": sid,
                "text": store.safe_summary(c["subject"], 400),
                "source": "git",
                "author": c["author"],
            },
            root,
        )
        for fpath in _files_for_commit(c["sha"], root):
            store.append(
                {
                    "kind": "tool",
                    "ts": ts,
                    "session": sid,
                    "name": "Edit",
                    "summary": fpath,
                    "files": [fpath],
                    "ok": True,
                    "source": "git",
                },
                root,
            )
        if c["body"]:
            store.append(
                {
                    "kind": "close",
                    "ts": ts,
                    "session": sid,
                    "snippet": store.safe_summary(c["body"], 300),
                    "source": "git",
                },
                root,
            )
        added += 1

    return {
        "ok": True,
        "added_sessions": added,
        "skipped_existing": skipped,
        "oldest_ts": oldest_ts,
        "newest_ts": newest_ts,
        "repo_root": str(root),
    }


def format_summary(result: dict) -> str:
    if not result.get("ok"):
        return f"(backfill skipped: {result.get('reason', 'unknown')})"
    added = result["added_sessions"]
    skipped = result["skipped_existing"]
    if added == 0 and skipped > 0:
        return f"OK  backfill already complete ({skipped} commits previously seeded, nothing new)"
    if added == 0:
        return "(no commits to backfill)"
    oldest = result["oldest_ts"][:10]
    newest = result["newest_ts"][:10]
    extra = f", {skipped} already present" if skipped else ""
    return f"OK  backfilled {added} sessions from git ({oldest} -> {newest}{extra})"
