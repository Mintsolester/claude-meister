# `meister` CLI — repo-local conversation memory

A platform-independent surface over the same memory store the Claude_Meister
MCP server uses. The CLI works whether or not Claude Code is running, and it's
the only path for users on Cursor, Codex, Aider, or any client that doesn't
support MCP yet.

## Install

```bash
# 1) Clone + install (makes `meister` a global console command)
git clone https://github.com/Mintsolester/claude-meister
cd claude-meister && pip install -e .

# 2) Capture hooks + SessionStart inject + statusLine — all in one
meister install-hooks

# 3) Restart Claude Code (or open /hooks once) so the watcher reloads.

# 4) Verify
meister test     # programmatic 4/4 PASS check
meister doctor   # hook wiring sanity check
```

After `pip install -e .` you can use either `meister <cmd>` or
`python -m meister <cmd>` — both work, from any directory.

On non-Claude clients there is nothing to install: the `meister` CLI reads
`.repo_memory/conversation.jsonl` directly. If the file is empty because the
client doesn't fire hooks, populate it via the MCP `memory_store` tool or by
piping events into `meister.capture` from a wrapper script.

## Commands

| Command | What it does |
|---|---|
| `python -m meister init` | Create `.repo_memory/` in the current repo (idempotent). |
| `python -m meister last [-n N]` | Show the most recent N sessions as L0 rows. |
| `python -m meister recall "<query>" [-k K]` | TF-IDF rank sessions by title + files + tool names. Returns top K L0 rows. |
| `python -m meister show <session_id>` | Expand one session: prompts, tool count, files touched, final notes. (L1) |
| `python -m meister show <session_id> --raw` | Dump every event for the session as JSONL. (L2) |
| `python -m meister status` | Counts: events, sessions, log size, ts range. |
| `python -m meister install-hooks` | Idempotently add capture hooks to `~/.claude/settings.json`. |
| `python -m meister doctor` | Verify hooks are installed and memory dir is reachable. |

## The three retrieval layers

Inspired by the **selective-read mechanic** (progressive L0 → L1 → L2 reads of
source files). Each layer only descends if the previous one didn't answer.

| Layer | Cost (approx) | What you get | When to use |
|---|---|---|---|
| **L0** | ~50 tokens for 10 sessions | One-line session titles + file + tool counts | "What was I doing recently?" / fuzzy search by topic |
| **L1** | ~300 tokens per session | All prompts, files touched (ranked), final notes | "Tell me more about session X" |
| **L2** | full event count | Every prompt + tool call + close, as JSONL | Replay / export / debugging |

This is the wedge: existing memory tools dump everything at every call. Meister
returns the *index* first, body on demand. Memory recall stops growing with
your history.

## Event schema

The log is append-only JSONL at `.repo_memory/conversation.jsonl`. One event
per line. Three kinds:

```jsonl
{"kind":"prompt","ts":"2026-05-14T18:42:11+00:00","session":"abc123","text":"fix the dedup bug"}
{"kind":"tool",  "ts":"2026-05-14T18:42:14+00:00","session":"abc123","name":"Edit","summary":"db/repository.py","files":["db/repository.py"],"ok":true}
{"kind":"close", "ts":"2026-05-14T18:42:55+00:00","session":"abc123","snippet":"tests pass, dedup behavior verified"}
```

Stable fields: `kind`, `ts`, `session`. Everything else is best-effort and may
vary by client. Readers must skip unknown keys.

## Security notes

- The capture hook applies a tiny regex scrubber that masks
  `api_key|token|secret|password` patterns in summaries. It is **not** a
  comprehensive secret scanner. If your repo handles credentials, gitignore
  `.repo_memory/` or run a real scanner against it before committing.
- The log is plaintext. It contains your prompts. Treat it like your shell
  history.
- Hooks fail open: any exception swallowed, exit 0. They will never block your
  tool calls — but they will silently miss events if Python isn't on PATH.
  `meister doctor` flags this.

## Roadmap

- v2.1 — semantic recall via the existing MCP server's embedding path (opt-in).
- v2.2 — `meister watch` daemon for clients without hook surfaces.
- v2.3 — repo-change tracking so stale entries auto-invalidate.
- v2.4 — Cursor / Codex adapters that normalize their transcript shape into
  the meister event schema.

See `DEVIATIONS.md` for what was deliberately *not* built in v2.0.
