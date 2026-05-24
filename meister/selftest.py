"""`meister test` — self-test that proves the system works on your machine.

Runs five checks, prints PASS / FAIL with reasons, exits 0 if all pass.

  1. .repo_memory/ exists and is writable
  2. Capture path: synthetic event round-trips through store.append + read
  3. Recall returns a meaningful result on the synthetic event
  4. Hook scripts are wired into ~/.claude/settings.json
  5. Token math: print captured tokens vs layered-recall cost (the value claim)

Designed to be run by a brand-new user immediately after install-hooks.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from . import retrieve, store


# Rough Anthropic-tokenizer heuristic: ~4 chars per token for English text.
# Good enough for an order-of-magnitude claim.
def _est_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def _ok(name: str, detail: str = "") -> None:
    print(f"  [PASS] {name}" + (f"  {detail}" if detail else ""))


def _fail(name: str, reason: str) -> None:
    print(f"  [FAIL] {name}  -> {reason}")


def _check_memory_dir() -> bool:
    try:
        d = store.ensure_memory_dir()
        if not d.exists():
            _fail("memory dir exists", str(d))
            return False
        _ok("memory dir exists & writable", f"{d}")
        return True
    except Exception as exc:
        _fail("memory dir exists", str(exc))
        return False


def _check_capture_roundtrip() -> tuple[bool, str | None]:
    marker = f"selftest-{uuid.uuid4().hex[:8]}"
    sid = f"test_{marker}"
    try:
        store.append(
            {
                "kind": "prompt",
                "ts": store.now_iso(),
                "session": sid,
                "text": f"MEISTER SELFTEST MARKER {marker} — recall me",
            }
        )
        store.append(
            {
                "kind": "tool",
                "ts": store.now_iso(),
                "session": sid,
                "name": "Edit",
                "summary": f"selftest/{marker}.py",
                "files": [f"selftest/{marker}.py"],
                "ok": True,
            }
        )
        events = store.read_events()
        found = [e for e in events if e.get("session") == sid]
        if len(found) >= 2:
            _ok("capture roundtrip", f"wrote 2 events, read back {len(found)}")
            return True, sid
        _fail("capture roundtrip", f"wrote 2 events, read back {len(found)}")
        return False, None
    except Exception as exc:
        _fail("capture roundtrip", str(exc))
        return False, None


def _check_recall(marker_session: str | None) -> bool:
    if not marker_session:
        _fail("recall returns marker", "no marker session to query")
        return False
    try:
        # Recall over the marker session's distinctive id
        query = marker_session.split("_", 1)[-1]
        rows = retrieve.recall(query, top_k=3)
        if any(r["session"] == marker_session for r in rows):
            _ok("recall returns marker", f"top-3 contains {marker_session[:14]}")
            return True
        _fail(
            "recall returns marker",
            f"top-3 sessions: {[r['session'][:14] for r in rows]}",
        )
        return False
    except Exception as exc:
        _fail("recall returns marker", str(exc))
        return False


def _check_hooks_installed() -> bool:
    settings = Path.home() / ".claude" / "settings.json"
    if not settings.exists():
        _fail("hooks wired", f"{settings} not found")
        return False
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except Exception as exc:
        _fail("hooks wired", f"settings.json not parseable: {exc}")
        return False
    hooks = data.get("hooks") or {}
    needed = ("UserPromptSubmit", "PostToolUse", "Stop")
    missing = []
    for event in needed:
        present = any(
            "meister" in h.get("command", "").lower()
            for entry in hooks.get(event, [])
            for h in entry.get("hooks", [])
        )
        if not present:
            missing.append(event)
    if missing:
        _fail(
            "hooks wired",
            f"missing: {', '.join(missing)} — run `python -m meister install-hooks`",
        )
        return False
    _ok("hooks wired", "UserPromptSubmit + PostToolUse + Stop present")

    # SessionStart and statusLine are optional but checked separately.
    if any(
        "session_inject" in h.get("command", "")
        for entry in hooks.get("SessionStart", [])
        for h in entry.get("hooks", [])
    ):
        _ok("SessionStart inject wired", "Claude will see meister context on session start")
    else:
        print(
            "  [INFO] SessionStart inject NOT wired — Claude will NOT see meister context automatically."
        )
        print(
            "         Run `python -m meister install-hooks` to enable it (added in this build)."
        )

    sl = data.get("statusLine")
    if isinstance(sl, dict) and "meister" in (sl.get("command") or "").lower():
        _ok("statusLine wired", "footer shows live capture state")
    else:
        print("  [INFO] statusLine NOT wired — you won't see a live capture indicator.")
    return True


def _check_token_math() -> bool:
    try:
        rows = retrieve.l0_sessions()
        if not rows:
            print("  [INFO] token math skipped — no sessions captured yet.")
            return True
        # Naive baseline: dump full conversation.jsonl into context.
        log_path = store.memory_dir() / store.CONVERSATION_FILE
        naive_tokens = _est_tokens(log_path.read_text(encoding="utf-8", errors="replace"))
        # Layered baseline: L0 listing of top-10 sessions only.
        l0_text = "\n".join(
            f"{r['session']} {r['ts_last']} {r['title']} {','.join(r['files'])}"
            for r in rows[:10]
        )
        l0_tokens = _est_tokens(l0_text)
        if naive_tokens == 0:
            return True
        ratio = (1 - l0_tokens / naive_tokens) * 100
        print(
            f"  [INFO] token math: full log = ~{naive_tokens} tokens, L0 recall = ~{l0_tokens} tokens "
            f"({ratio:.0f}% saved on default recall)"
        )
        return True
    except Exception as exc:
        print(f"  [INFO] token math skipped: {exc}")
        return True


def main() -> int:
    print("meister self-test")
    print("-" * 60)
    print(f"Repo root:  {store.find_repo_root()}")
    print(f"Memory dir: {store.memory_dir()}")
    print()

    passed = 0
    total = 4

    if _check_memory_dir():
        passed += 1
    ok, marker_sid = _check_capture_roundtrip()
    if ok:
        passed += 1
    if _check_recall(marker_sid):
        passed += 1
    if _check_hooks_installed():
        passed += 1
    _check_token_math()  # informational, doesn't affect pass count

    print()
    print("-" * 60)
    print(f"Result: {passed}/{total} programmatic checks passed.")
    print()
    if passed == total:
        print("All programmatic checks passed. For the cross-session test")
        print("(does Claude actually USE the captured memory in a new session?)")
        print("follow docs/VERIFY.md — that part requires a real Claude Code")
        print("session reset and can't be tested in-process.")
        return 0
    print("Some checks failed. Fix the FAIL lines above before launching.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
