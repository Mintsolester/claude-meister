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


# Memory-ish phrases: if a prompt contains any of these (case-insensitive),
# we auto-run a recall and inject the result into Claude's context BEFORE
# it sees the user prompt. This is the third leg of passive use — without
# it, mid-conversation recall requires the user to ask Claude to use meister.
_MEMORY_TRIGGERS = re.compile(
    r"\b("
    r"what did (i|we)|"
    r"when did (i|we)|"
    r"last time|"
    r"yesterday|"
    r"earlier|"
    r"previously|"
    r"remember when|"
    r"remind me|"
    r"what was i working on|"
    r"what were we doing|"
    r"where did i|"
    r"have i (already|ever)"
    r")\b",
    re.IGNORECASE,
)
_AUTO_INJECT_OPT_OUT = "MEISTER_NO_AUTO_INJECT"


def _maybe_auto_inject(prompt_text: str, repo_root) -> str:
    """If the prompt looks memory-ish, run a recall and return a context block
    to inject. Empty string = don't inject."""
    import os
    if os.environ.get(_AUTO_INJECT_OPT_OUT) in ("1", "true", "yes"):
        return ""
    if not _MEMORY_TRIGGERS.search(prompt_text):
        return ""

    from . import retrieve
    # Run recall on the prompt (the TF-IDF surfaces what's relevant from the
    # nouns/verbs in the question itself).
    rows = retrieve.recall(prompt_text, repo_root=repo_root, top_k=3, trigger="prompt_auto")
    if not rows:
        return ""
    lines = ["[meister auto-recall — your prompt looks like a memory question]"]
    for r in rows:
        ts = (r.get("ts_last") or "")[:10]
        title = (r.get("title") or "").strip()[:120]
        files = ", ".join((r.get("files") or [])[:3])
        line = f"  [{ts}] {title}"
        if files:
            line += f"  (files: {files})"
        lines.append(line)
    lines.append("Use `meister show <session>` for full detail.")
    return "\n".join(lines)


def on_user_prompt() -> None:
    p = _read_payload()
    text = p.get("prompt") or p.get("user_prompt") or p.get("text") or ""
    if not text:
        return
    repo_root = store.find_repo_root(str(_cwd_from_payload(p)) if _cwd_from_payload(p) else None)

    # 1) Always capture the prompt.
    store.append(
        {
            "kind": "prompt",
            "ts": store.now_iso(),
            "session": store.session_id(p.get("session_id")),
            "text": store.safe_summary(text, 400),
        },
        repo_root,
    )

    # 2) If it's a memory-ish question, auto-inject relevant past context
    #    via the UserPromptSubmit hook's additionalContext channel.
    ctx = _maybe_auto_inject(text, repo_root)
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
