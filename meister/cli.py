"""meister — CLI surface for repo-local conversation memory.

Usage:
    python -m meister init                       Create .repo_memory/ in this repo
    python -m meister last                       Show the most recent session (L0)
    python -m meister recall "<query>"           Top-K sessions matching query (L0)
    python -m meister show <session_id>          Expand one session (L1)
    python -m meister show <session_id> --raw    Dump full event stream (L2)
    python -m meister status                     Health + counts
    python -m meister install-hooks              Wire capture hooks into Claude Code
    python -m meister doctor                     Verify the install
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import backfill, retrieve, store


def _fmt_session_row(row: dict) -> str:
    files = ", ".join(row["files"][:3])
    if len(row["files"]) > 3:
        files += f" (+{len(row['files']) - 3})"
    tools = ",".join(f"{k}:{v}" for k, v in row["tool_counts"].items())
    ts = row["ts_last"][:16].replace("T", " ")
    return (
        f"  {row['session'][:12]:12}  {ts}  events={row['event_count']:<3}  "
        f"tools=[{tools}]\n"
        f"               files: {files or '-'}\n"
        f"               title: {row['title'] or '-'}"
    )


def cmd_init(args: argparse.Namespace) -> int:
    d = store.ensure_memory_dir()
    print(f"OK  memory dir ready: {d}")
    return 0


def cmd_last(args: argparse.Namespace) -> int:
    rows = retrieve.l0_sessions()
    if not rows:
        print("(no sessions captured yet — run `meister install-hooks` and use Claude Code)")
        return 0
    print(f"Last {min(args.n, len(rows))} session(s) in {store.find_repo_root()}:\n")
    for r in rows[: args.n]:
        print(_fmt_session_row(r))
        print()
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    rows = retrieve.recall(args.query, top_k=args.k)
    if not rows:
        print(f"(no sessions match {args.query!r})")
        return 0
    print(f"Top {len(rows)} matches for {args.query!r}:\n")
    for r in rows:
        print(_fmt_session_row(r))
        print()
    print("Drill down: python -m meister show <session_id>")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    if args.raw:
        events = retrieve.raw_events(args.session)
        if not events:
            print(f"(no events for session {args.session!r})")
            return 1
        for e in events:
            print(json.dumps(e, ensure_ascii=False))
        return 0

    d = retrieve.expand_session(args.session)
    if not d.get("found"):
        print(f"(no events for session {args.session!r})")
        return 1
    print(f"Session {d['session']}  ({d['ts_first']} -> {d['ts_last']})\n")
    print(f"Tools called: {d['tool_count']}")
    if d["files"]:
        print("Files touched:")
        for f, n in d["files"]:
            print(f"  {n:3d}  {f}")
    if d["prompts"]:
        print("\nPrompts:")
        for p in d["prompts"]:
            print(f"  - {p}")
    if d["closes"]:
        print("\nFinal notes:")
        for c in d["closes"]:
            print(f"  {c}")
    print(f"\nFull stream: python -m meister show {args.session} --raw")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Detailed token-economics breakdown — the numbers behind the status line."""
    root = store.find_repo_root()
    d = store.memory_dir(root)
    log = d / store.CONVERSATION_FILE
    if not log.exists() or log.stat().st_size == 0:
        print("(no events captured yet — use Claude Code with hooks installed)")
        return 0

    events = store.read_events(root)
    rows = retrieve.l0_sessions(root)
    size = log.stat().st_size

    # 4 chars/token approximation, same as statusline.
    naive_tokens = max(1, size // 4)

    # Real measured L0 cost: serialize what `meister last -n N` would print.
    def _l0_chars(n: int) -> int:
        sel = rows[:n]
        if not sel:
            return 0
        text = "\n".join(
            f"{r['session']} {r['ts_last']} events={r['event_count']} "
            f"tools={','.join(f'{k}:{v}' for k, v in r['tool_counts'].items())} "
            f"files={','.join(r['files'][:3])} title={r['title']}"
            for r in sel
        )
        return len(text)

    l0_10 = _l0_chars(10) // 4
    l0_all = _l0_chars(len(rows)) // 4

    saved_per_recall = max(0, naive_tokens - l0_10)
    saved_pct = int((saved_per_recall / naive_tokens) * 100) if naive_tokens else 0

    print(f"Repo:       {root}")
    print(f"Log file:   {log}  ({size / 1024:.1f} KB)")
    print(f"Events:     {len(events)}")
    print(f"Sessions:   {len(rows)}")
    print()
    print("Token economics  (4 chars/token approx):")
    print(f"  Full log dumped naively into context:  ~{naive_tokens:>7,} tokens")
    print(f"  `meister last` (default top 10):       ~{l0_10:>7,} tokens")
    print(f"  `meister last -n {len(rows)}` (all sessions): ~{l0_all:>7,} tokens")
    print()
    print(f"  Saved per default recall: ~{saved_per_recall:,} tokens ({saved_pct}%)")
    print()
    print("Honest framing: 'saved' assumes the alternative is dumping the full")
    print("conversation log into Claude's context every recall. If you never")
    print("recall at all, the savings are unrealized.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = store.find_repo_root()
    d = store.memory_dir(root)
    print(f"Repo root:   {root}")
    print(f"Memory dir:  {d}  ({'exists' if d.exists() else 'NOT YET INITIALIZED'})")
    if not d.exists():
        print("\nRun: python -m meister init")
        return 0
    events = store.read_events(root)
    rows = retrieve.l0_sessions(root)
    print(f"Events:      {len(events)}")
    print(f"Sessions:    {len(rows)}")
    if rows:
        print(f"Newest:      {rows[0]['ts_last']}  {rows[0]['session']}")
        print(f"Oldest:      {rows[-1]['ts_first']}  {rows[-1]['session']}")
    path = d / store.CONVERSATION_FILE
    if path.exists():
        kb = path.stat().st_size / 1024
        print(f"Log size:    {kb:.1f} KB")
    return 0


def _claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _hook_command(event: str) -> str:
    py = sys.executable.replace("\\", "/")
    repo = Path(__file__).resolve().parent.parent.as_posix()
    return f'"{py}" -c "import sys; sys.path.insert(0, r\'{repo}\'); from meister.capture import main; raise SystemExit(main([\'{event}\']))"'


def _module_command(module: str) -> str:
    py = sys.executable.replace("\\", "/")
    repo = Path(__file__).resolve().parent.parent.as_posix()
    return f'"{py}" -c "import sys; sys.path.insert(0, r\'{repo}\'); from meister.{module} import main; raise SystemExit(main())"'


def cmd_install_hooks(args: argparse.Namespace) -> int:
    """Idempotently add capture hooks to ~/.claude/settings.json.

    UserPromptSubmit -> meister.capture prompt
    PostToolUse      -> meister.capture tool
    Stop             -> meister.capture stop

    Existing user hooks are preserved. Reruns are safe: if a hook with the
    exact same command exists, we don't duplicate it.
    """
    path = _claude_settings_path()
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: existing settings.json is not valid JSON: {e}")
            return 2
    else:
        data = {}
    hooks = data.setdefault("hooks", {})

    plan = [
        ("UserPromptSubmit", None, _hook_command("prompt")),
        ("PostToolUse", "*", _hook_command("tool")),
        ("Stop", None, _hook_command("stop")),
        ("SessionStart", None, _module_command("session_inject")),
    ]
    added = []
    for event, matcher, cmd in plan:
        entries = hooks.setdefault(event, [])
        already = False
        for e in entries:
            for h in e.get("hooks", []):
                if h.get("command") == cmd:
                    already = True
                    break
            if already:
                break
        if already:
            continue
        entry: dict = {"hooks": [{"type": "command", "command": cmd, "timeout": 10}]}
        if matcher:
            entry["matcher"] = matcher
        entries.append(entry)
        added.append(event)

    # Wire the status line — visible health signal in the Claude Code footer.
    statusline_cmd = _module_command("statusline")
    if data.get("statusLine", {}).get("command") != statusline_cmd:
        data["statusLine"] = {"type": "command", "command": statusline_cmd}
        added.append("statusLine")

    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if added:
        print(f"OK  installed: {', '.join(added)}")
    else:
        print("OK  hooks + statusLine already installed (no change)")
    print(f"    settings: {path}")

    # Killer first-run: seed memory from git so `meister last` isn't empty.
    if not args.no_backfill:
        result = backfill.from_git(limit=args.backfill_limit)
        print(backfill.format_summary(result))

    print("\nOpen /hooks in Claude Code once (or restart) so the watcher reloads.")
    print("Try it:")
    print("  python -m meister last")
    print("  python -m meister recall \"<topic>\"")
    return 0


def cmd_backfill(args: argparse.Namespace) -> int:
    result = backfill.from_git(limit=args.limit)
    print(backfill.format_summary(result))
    if result.get("ok") and result.get("added_sessions", 0):
        print("\nPreview:")
        rows = retrieve.l0_sessions()[:3]
        for r in rows:
            print(_fmt_session_row(r))
            print()
    return 0 if result.get("ok") else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    ok = True
    path = _claude_settings_path()
    print(f"Claude settings:  {path}  ({'found' if path.exists() else 'MISSING'})")
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  WARN: invalid JSON: {e}")
            ok = False
            data = {}
        hooks = (data.get("hooks") or {})
        for event in ("UserPromptSubmit", "PostToolUse", "Stop"):
            present = any(
                "meister.capture" in h.get("command", "")
                for entry in hooks.get(event, [])
                for h in entry.get("hooks", [])
            )
            print(f"  {event:18}  {'OK' if present else 'MISSING'}")
            if not present:
                ok = False
    root = store.find_repo_root()
    d = store.memory_dir(root)
    print(f"Memory dir:       {d}  ({'OK' if d.exists() else 'will auto-create on first hook fire'})")
    print(f"Python:           {sys.executable}")
    print()
    print("HEALTHY" if ok else "ATTENTION NEEDED — run: python -m meister install-hooks")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="meister", description="Repo-local conversation memory")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create .repo_memory/ in the current repo").set_defaults(func=cmd_init)

    last = sub.add_parser("last", help="Show the most recent session(s)")
    last.add_argument("-n", type=int, default=1)
    last.set_defaults(func=cmd_last)

    rec = sub.add_parser("recall", help="Search sessions by query (L0 output)")
    rec.add_argument("query", nargs="+")
    rec.add_argument("-k", type=int, default=5)
    rec.set_defaults(func=lambda a: cmd_recall(argparse.Namespace(query=" ".join(a.query), k=a.k)))

    show = sub.add_parser("show", help="Expand one session (L1, or --raw for L2)")
    show.add_argument("session")
    show.add_argument("--raw", action="store_true")
    show.set_defaults(func=cmd_show)

    sub.add_parser("status", help="Health + counts for this repo's memory").set_defaults(func=cmd_status)
    sub.add_parser("stats", help="Token-economics breakdown (saved tokens, recall cost vs naive)").set_defaults(func=cmd_stats)

    ih = sub.add_parser("install-hooks", help="Wire capture hooks into ~/.claude/settings.json (auto-seeds from git)")
    ih.add_argument("--no-backfill", action="store_true", help="Skip the git-history seed step")
    ih.add_argument("--backfill-limit", type=int, default=50, help="How many recent commits to seed (default 50)")
    ih.set_defaults(func=cmd_install_hooks)

    bf = sub.add_parser("backfill", help="Seed memory from git history (idempotent)")
    bf.add_argument("--limit", type=int, default=50)
    bf.set_defaults(func=cmd_backfill)

    sub.add_parser("doctor", help="Verify install").set_defaults(func=cmd_doctor)

    def _run_selftest(_a: argparse.Namespace) -> int:
        from . import selftest
        return selftest.main()

    sub.add_parser(
        "test",
        help="Self-test: capture, recall, hooks, token math (run after install-hooks)",
    ).set_defaults(func=_run_selftest)

    def _run_statusline(_a: argparse.Namespace) -> int:
        from . import statusline
        return statusline.main()

    sub.add_parser(
        "statusline",
        help="Print the status-line text (used by Claude Code statusLine config)",
    ).set_defaults(func=_run_statusline)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
