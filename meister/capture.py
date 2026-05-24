"""Hook entry points for auto-capture. Each function reads a JSON payload from
stdin (Claude Code's hook protocol) and appends one event to the repo-local
log.

All hooks fail OPEN: any exception is swallowed and exits 0. Capturing memory
must never block tool execution.

Wire-up (one-time): `python -m meister install-hooks`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import re

from . import store, usage

# File paths that match these substrings are skipped — Claude Code's own
# scratch directories produce a lot of internal Read/Bash noise that has no
# bearing on what the user was actually doing.
_INTERNAL_PATH_NOISE = (
    "AppData/Local/Temp/claude",
    "AppData\\Local\\Temp\\claude",
    "/.claude/projects/",
    "\\.claude\\projects\\",
    "/tmp/claude",
)


def _is_internal_noise(path_or_cmd: str) -> bool:
    return any(needle in path_or_cmd for needle in _INTERNAL_PATH_NOISE)


def _read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _cwd_from_payload(payload: dict) -> Path | None:
    # Claude Code passes cwd; other clients vary. Fall back to os.getcwd in store.
    cwd = payload.get("cwd") or payload.get("workspace") or payload.get("project_dir")
    return Path(cwd) if cwd else None


# Ambient context injection: on EVERY user prompt, run a recall against the
# prompt text and inject the most-relevant past session(s) into Claude's view
# BEFORE Claude reads the prompt. The user never needs to ask for memory —
# Claude just has the right context to do the task correctly.
#
# Why no memory-cue regex anymore: the user has better memory than the model;
# they don't need help recalling. The model is the one that needs context to
# do new work that builds on past work. So inject on every prompt, not just
# when the user phrases a memory question.
#
# Bounded: caps total injected length, uses TF-IDF score-gate so unrelated
# prompts don't pull in random past sessions. If no past session shares any
# terms with the prompt, nothing is injected.
_AUTO_INJECT_OPT_OUT = "MEISTER_NO_AUTO_INJECT"
_MIN_PROMPT_CHARS_FOR_INJECT = 8  # skip "ok", "yes", "thanks", etc.
_MAX_INJECT_CHARS = 600


def _maybe_auto_inject(prompt_text: str, repo_root, current_session: str | None) -> str:
    """Always-on ambient context injection. Returns the context block to
    inject, or empty string if no relevant past session exists.

    Behavior:
      - Skips trivially-short prompts (acknowledgments like "ok", "go ahead")
      - Runs TF-IDF recall on the prompt text against captured sessions
      - Filters out the CURRENT session (we don't inject the prompt back at
        Claude — that's noise, not signal)
      - If no past session has term overlap, nothing is injected
      - Otherwise returns top 2 past sessions, capped at MAX_INJECT_CHARS total
    """
    import os
    if os.environ.get(_AUTO_INJECT_OPT_OUT) in ("1", "true", "yes"):
        return ""
    if len(prompt_text.strip()) < _MIN_PROMPT_CHARS_FOR_INJECT:
        return ""

    from . import retrieve
    # Pull a few extra in case the current session is among them and we filter
    # it out.
    rows = retrieve.recall(prompt_text, repo_root=repo_root, top_k=5, trigger="prompt_auto")
    if current_session:
        rows = [r for r in rows if r.get("session") != current_session]
    rows = rows[:2]
    if not rows:
        return ""

    lines = ["[meister context — past sessions relevant to this prompt]"]
    for r in rows:
        ts = (r.get("ts_last") or "")[:10]
        title = (r.get("title") or "").strip()[:120]
        files = ", ".join((r.get("files") or [])[:3])
        line = f"  [{ts}] {title}"
        if files:
            line += f"  (files: {files})"
        lines.append(line)
    text = "\n".join(lines)
    if len(text) > _MAX_INJECT_CHARS:
        text = text[: _MAX_INJECT_CHARS - 3] + "..."
    return text


def on_user_prompt() -> None:
    p = _read_payload()
    text = p.get("prompt") or p.get("user_prompt") or p.get("text") or ""
    if not text:
        return
    repo_root = store.find_repo_root(str(_cwd_from_payload(p)) if _cwd_from_payload(p) else None)
    current_session = store.session_id(p.get("session_id"))

    # ORDER MATTERS:
    # 1) Run the ambient-context recall FIRST, against everything captured so
    #    far. We must do this before appending the current prompt, otherwise
    #    the prompt becomes its own top match.
    # 2) Then capture the current prompt to the log.
    ctx = _maybe_auto_inject(text, repo_root, current_session)

    store.append(
        {
            "kind": "prompt",
            "ts": store.now_iso(),
            "session": current_session,
            "text": store.safe_summary(text, 400),
        },
        repo_root,
    )
    if ctx:
        out = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ctx,
            }
        }
        sys.stdout.write(json.dumps(out))


def on_post_tool() -> None:
    p = _read_payload()
    name = p.get("tool_name") or "?"
    tool_input = p.get("tool_input") or {}
    tool_response = p.get("tool_response") or {}

    # Build a short summary depending on tool shape.
    summary = ""
    files: list[str] = []
    if isinstance(tool_input, dict):
        if tool_input.get("file_path"):
            if _is_internal_noise(tool_input["file_path"]):
                return  # drop the whole event — Claude Code internal scratch
            files.append(tool_input["file_path"])
            offset = tool_input.get("offset")
            limit = tool_input.get("limit")
            if offset or limit:
                summary = f"{tool_input['file_path']} offset={offset} limit={limit}"
            else:
                summary = tool_input["file_path"]
        elif tool_input.get("command"):
            if _is_internal_noise(tool_input["command"]):
                return
            summary = store.safe_summary(tool_input["command"], 120)
        elif tool_input.get("pattern"):
            summary = f"pattern={store.safe_summary(tool_input['pattern'], 60)}"
        elif tool_input.get("url"):
            summary = tool_input["url"][:120]

    ok = True
    if isinstance(tool_response, dict):
        ok = not tool_response.get("error") and tool_response.get("success", True) is not False

    store.append(
        {
            "kind": "tool",
            "ts": store.now_iso(),
            "session": store.session_id(p.get("session_id")),
            "name": name,
            "summary": summary,
            "files": files,
            "ok": ok,
        },
        store.find_repo_root(str(_cwd_from_payload(p)) if _cwd_from_payload(p) else None),
    )


def on_stop() -> None:
    p = _read_payload()
    # Stop hook has no canonical message field across clients; best-effort capture.
    snippet = p.get("final_text") or p.get("message") or ""
    store.append(
        {
            "kind": "close",
            "ts": store.now_iso(),
            "session": store.session_id(p.get("session_id")),
            "snippet": store.safe_summary(snippet, 300),
        },
        store.find_repo_root(str(_cwd_from_payload(p)) if _cwd_from_payload(p) else None),
    )


_ENTRYPOINTS = {
    "prompt": on_user_prompt,
    "tool": on_post_tool,
    "stop": on_stop,
}


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in _ENTRYPOINTS:
        # Always exit 0 — hook failures must never break the user's flow.
        return 0
    try:
        _ENTRYPOINTS[argv[0]]()
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
