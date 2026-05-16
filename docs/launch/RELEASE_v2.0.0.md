# v2.0.0 — Memory follows the repo, not the tool

> Paste this as the body of the GitHub Release at
> `https://github.com/Mintsolester/claude-meister/releases/new`.
> Attach the 60-second demo gif at the top before publishing.

---

![60-second demo](../images/demo-v2.gif)

**`meister`** is a platform-independent conversation memory layer for AI
coding tools. Captures every turn you have with Claude Code into a
repo-local `.repo_memory/conversation.jsonl`, then surfaces it back through
a CLI with layered retrieval — so recall costs ~50 tokens, not 5,000.

The same memory works in Cursor, Codex, and Aider via MCP. Your memory
follows the *repo*, not the tool.

## Install in 30 seconds

```bash
git clone https://github.com/Mintsolester/claude-meister.git
cd claude-meister
python -m meister install-hooks
```

On the way out, `install-hooks` seeds your memory from the last 50 git
commits so `meister last` is never empty on day one.

## Why this is different

- **Cross-tool.** Same `.repo_memory/` works whether you used Claude Code,
  Cursor, Codex, or a shell-only client. Anthropic's native memory is
  Claude-only.
- **Layered retrieval (L0 → L1 → L2).** Default recall returns one-line
  session titles. Drill in only when you need the detail. Recall cost stays
  bounded as your history grows.
- **Repo-local plaintext.** The log lives in `your-repo/.repo_memory/`.
  Commit it, gitignore it, sync it with the repo — your call.
- **Zero install footprint.** No embeddings, no vector DB, no daemon. Pure
  Python stdlib. TF-IDF over short summaries is fast enough.
- **Fails open.** Capture hooks swallow every exception. They never block
  your tool calls.

## First-run experience

```
$ python -m meister install-hooks
OK  installed hooks: UserPromptSubmit, PostToolUse, Stop
    settings: ~/.claude/settings.json
OK  backfilled 47 sessions from git (2026-03-22 -> 2026-05-17)

Try it:
  python -m meister last
  python -m meister recall "<topic>"
```

```
$ python -m meister recall "auth middleware"
Top 2 matches for 'auth middleware':

  git_a3f9d2e8  2026-05-12 09:34  events=8   tools=[Edit:7]
                files: middleware/auth.py, middleware/session.py
                title: feat(auth): rotate session tokens on privilege change

  git_b1c0883f  2026-05-08 14:21  events=4   tools=[Edit:3]
                files: middleware/auth.py
                title: fix(auth): handle missing Bearer prefix on legacy headers
```

## Compatibility

| Client | Status |
|---|---|
| Claude Code | Primary target — captures via hooks |
| Cursor | Read path via MCP works; write/capture adapter in v2.1 |
| Codex | Adapter on roadmap (v2.4) |
| Aider | Adapter on roadmap (v2.4) |
| Shell-only / CI | CLI works standalone over `.repo_memory/conversation.jsonl` |

Tested on Windows 11. macOS / Linux *should* work — bug reports welcome.

## What's NOT in v2.0 (deliberately)

- No daemon. Hooks-only capture. Reversible.
- No embeddings. TF-IDF is sufficient for the layered design.
- No cloud sync. Repo-local plaintext only.

## Roadmap

- **v2.1** — Semantic recall via the existing MCP server's embedding path (opt-in).
- **v2.2** — `meister watch` daemon for clients without hook surfaces.
- **v2.3** — Repo-change tracking so stale entries auto-invalidate.
- **v2.4** — Cursor / Codex adapters with normalized event schemas.

## Full reference

- [`docs/MEISTER_CLI.md`](../MEISTER_CLI.md)
- [`CHANGELOG.md`](../../CHANGELOG.md)
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
